"""Browser Intelligence — DOM/page understanding and structured extraction (Doc 29 P2).

Local-first and deterministic: page understanding uses semantic DOM plus
screenshot metadata, not a hosted vision model. Page content is untrusted data,
never instructions. Input values are never captured; only field structure.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import importlib.util
from datetime import datetime, timezone
from io import BytesIO
from typing import Any, Dict, List, Optional, cast

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.services.browser_evidence_service import BrowserEvidenceService, redact
from app.services.browser_service import browser_service

# Semantic DOM: roles, accessible names and geometry. Values are deliberately
# excluded so passwords, tokens and typed content never enter evidence.
PAGE_UNDERSTANDING_SCRIPT = """
() => {
  const visible = (el) => {
    const style = window.getComputedStyle(el);
    const rect = el.getBoundingClientRect();
    return style.display !== 'none' && style.visibility !== 'hidden'
      && rect.width > 0 && rect.height > 0;
  };
  const name = (el) => (el.getAttribute('aria-label') ||
    (el.labels && el.labels[0] ? el.labels[0].innerText : '') ||
    el.getAttribute('placeholder') || el.getAttribute('title') ||
    (el.innerText || '').trim()).trim().slice(0, 200);
  const rect = (el) => {
    const r = el.getBoundingClientRect();
    return {x: Math.round(r.x), y: Math.round(r.y),
            width: Math.round(r.width), height: Math.round(r.height)};
  };
  const interactive = Array.from(document.querySelectorAll(
    'a[href],button,input,select,textarea,[role=button],[role=link],[tabindex]'
  )).filter(visible).slice(0, 300).map((el) => ({
    tag: el.tagName.toLowerCase(),
    role: el.getAttribute('role') || el.tagName.toLowerCase(),
    name: name(el),
    type: el.getAttribute('type') || '',
    disabled: Boolean(el.disabled),
    rect: rect(el)
  }));
  return {
    title: document.title || '',
    url: window.location.href,
    language: document.documentElement.lang || '',
    headings: Array.from(document.querySelectorAll('h1,h2,h3')).filter(visible)
      .slice(0, 40).map((el) => el.innerText.trim().slice(0, 200)),
    landmarks: Array.from(document.querySelectorAll(
      'header,nav,main,aside,footer,[role=main],[role=navigation]'
    )).filter(visible).slice(0, 30).map((el) => ({
      role: el.getAttribute('role') || el.tagName.toLowerCase(), name: name(el)
    })),
    interactive: interactive,
    forms: Array.from(document.querySelectorAll('form')).filter(visible)
      .slice(0, 20).map((form) => ({
        name: name(form),
        action: (form.getAttribute('action') || '').slice(0, 500),
        fields: Array.from(form.querySelectorAll('input,select,textarea,button'))
          .slice(0, 60).map((el) => ({
            tag: el.tagName.toLowerCase(),
            type: el.getAttribute('type') || '',
            name: (el.getAttribute('name') || '').slice(0, 100),
            label: name(el),
            required: Boolean(el.required)
          }))
      })),
    alerts: Array.from(document.querySelectorAll(
      '[role=alert],[role=status],.error,.notice'
    )).filter(visible).slice(0, 20).map((el) => el.innerText.trim().slice(0, 300)),
    pagination: Array.from(document.querySelectorAll(
      'a[rel=next],a[rel=prev],.pagination a,[aria-label*=next i],[aria-label*=page i]'
    )).filter(visible).slice(0, 40).map((el) => ({
      text: (el.innerText || '').trim().slice(0, 100),
      href: (el.href || '').slice(0, 500)
    })),
    meta: {
      description: (document.querySelector('meta[name=description]') || {}).content || '',
      canonical: (document.querySelector('link[rel=canonical]') || {}).href || '',
      json_ld: Boolean(document.querySelector('script[type="application/ld+json"]'))
    },
    viewport: {width: window.innerWidth, height: window.innerHeight,
               scroll_height: document.body.scrollHeight},
    text_preview: (document.body && document.body.innerText || '').slice(0, 4000)
  };
}
"""

TABLE_SCRIPT = """
() => Array.from(document.querySelectorAll('table')).slice(0, 20).map((table, i) => ({
  index: i,
  caption: (table.querySelector('caption') || {}).innerText?.trim().slice(0, 200) || '',
  headers: Array.from(table.querySelectorAll('thead th, tr:first-child th, tr:first-child td'))
    .slice(0, 40).map((el) => el.innerText.trim().slice(0, 120)),
  rows: Array.from(table.querySelectorAll('tbody tr, tr')).slice(1, 101).map((row) =>
    Array.from(row.querySelectorAll('td,th')).slice(0, 40)
      .map((cell) => cell.innerText.trim().slice(0, 200)))
}))
"""

LISTING_SCRIPT = """
() => {
  const nodes = document.querySelectorAll('article,li,[data-testid],.card,.result,.item')
  return Array.from(nodes).slice(0, 100).map((node, i) => {
    const anchor = node.querySelector('a[href]');
    return {
      index: i,
      text: (node.innerText || '').trim().slice(0, 500),
      url: anchor ? anchor.href.slice(0, 500) : '',
      tag: node.tagName.toLowerCase()
    };
  }).filter((item) => item.text.length > 0);
}
"""

LINK_SCRIPT = """
() => Array.from(document.querySelectorAll('a[href]')).slice(0, 300)
  .map((a) => ({text: (a.innerText || '').trim().slice(0, 200), url: a.href}))
  .filter((link) => link.url.startsWith('http'))
"""

METADATA_SCRIPT = """
() => ({
  title: document.title || '',
  url: window.location.href,
  language: document.documentElement.lang || '',
  description: (document.querySelector('meta[name=description]') || {}).content || '',
  canonical: (document.querySelector('link[rel=canonical]') || {}).href || '',
  published: (document.querySelector('meta[property="article:published_time"]') || {}).content || '',
  json_ld: Boolean(document.querySelector('script[type="application/ld+json"]'))
})
"""

SCRIPTS = {
    "tables": TABLE_SCRIPT,
    "listings": LISTING_SCRIPT,
    "links": LINK_SCRIPT,
    "metadata": METADATA_SCRIPT,
}
EXTRACTION_KINDS = tuple(SCRIPTS) + ("auto",)


class BrowserIntelligenceError(ValueError):
    """Raised when browser intelligence cannot be performed safely."""


class TesseractOcrAdapter:
    """Local OCR only. Missing binary or library is reported, never faked."""

    name = "tesseract"

    def available(self) -> bool:
        return importlib.util.find_spec("pytesseract") is not None

    async def recognize(self, raw: bytes) -> Dict[str, Any]:
        if not self.available():
            return {
                "engine": self.name, "available": False,
                "reason": "pytesseract is not installed",
            }
        try:
            from PIL import Image
            import pytesseract

            image = Image.open(BytesIO(raw))
            text = await asyncio.to_thread(pytesseract.image_to_string, image)
            languages = await asyncio.to_thread(pytesseract.get_languages, "")
            return {
                "engine": self.name,
                "available": True,
                "text": redact(str(text))[:4000],
                "languages": list(languages),
            }
        except Exception as exc:
            # Includes TesseractNotFoundError. Absence is an explicit result,
            # never an empty string that would look like successful OCR.
            return {
                "engine": self.name, "available": False,
                "reason": type(exc).__name__,
            }


def png_dimensions(raw: bytes) -> Optional[Dict[str, int]]:
    """Read PNG dimensions locally; return None for a non-PNG payload."""
    if not raw.startswith(b"\x89PNG\r\n\x1a\n") or len(raw) < 24:
        return None
    width = int.from_bytes(raw[16:20], byteorder="big")
    height = int.from_bytes(raw[20:24], byteorder="big")
    if width <= 0 or height <= 0:
        return None
    return {"width": width, "height": height}


def digest(payload: Any) -> str:
    """Stable digest of structured extraction results for verification."""
    import json

    encoded = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class BrowserIntelligenceService:
    """Semantic page understanding and structured evidence-backed extraction."""

    def __init__(self, db: AsyncSession, ocr_adapter: Optional[TesseractOcrAdapter] = None):
        self.db = db
        self.evidence = BrowserEvidenceService(db)
        self.ocr = ocr_adapter or TesseractOcrAdapter()

    async def _page(self, session_token: str):
        if not session_token:
            raise BrowserIntelligenceError("session_token is required")
        return await browser_service.get_persistent_page(session_token)

    async def _screenshot_metadata(self, page: Any) -> Dict[str, Any]:
        data = await page.screenshot()
        raw = cast(bytes, data)
        dimensions = png_dimensions(raw)
        return {
            "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "dimensions": dimensions,
            "image_base64": base64.b64encode(raw).decode("ascii"),
            "raw": raw,
        }

    async def understand(
        self,
        session_token: str,
        *,
        task_id: Optional[str] = None,
        actor: str = "sdk",
        actor_type: str = "agent",
    ) -> Dict[str, Any]:
        """Semantic DOM + screenshot understanding with visual element geometry."""
        page = await self._page(session_token)
        structure = cast(Dict[str, Any], await page.evaluate(PAGE_UNDERSTANDING_SCRIPT))
        visual = await self._screenshot_metadata(page)
        ocr_result = (
            await self.ocr.recognize(cast(bytes, visual["raw"]))
            if settings.browser_ocr_enabled else None
        )
        result: Dict[str, Any] = {
            "url": structure.get("url"),
            "title": structure.get("title"),
            "language": structure.get("language"),
            "headings": structure.get("headings", []),
            "landmarks": structure.get("landmarks", []),
            "interactive": structure.get("interactive", []),
            "forms": structure.get("forms", []),
            "alerts": structure.get("alerts", []),
            "pagination": structure.get("pagination", []),
            "meta": structure.get("meta", {}),
            "viewport": structure.get("viewport", {}),
            "visual": {
                key: value for key, value in visual.items()
                if key not in ("image_base64", "raw")
            },
            "ocr": ocr_result,
            "untrusted": True,
        }
        result["digest"] = digest(result)
        if task_id:
            await self.evidence.record_evidence(
                task_id,
                url=str(structure.get("url") or ""),
                screenshot_b64=visual["image_base64"],
                excerpt=str(structure.get("text_preview") or ""),
                source_metadata={
                    "title": structure.get("title"),
                    "language": structure.get("language"),
                    "interactive_count": len(result["interactive"]),
                    "visual_sha256": visual["sha256"],
                    "ocr": (
                        {
                            "engine": ocr_result.get("engine"),
                            "available": ocr_result.get("available"),
                            "text": ocr_result.get("text", ""),
                            "reason": ocr_result.get("reason"),
                        }
                        if ocr_result else None
                    ),
                },
                session_id=session_token,
            )
            await self.evidence.append_audit(
                task_id, actor=actor, actor_type=actor_type,
                action="browser.understand", target=str(structure.get("url") or ""),
                outcome={"digest": result["digest"], "untrusted": True},
            )
            result["envelope"] = await self.evidence.envelope(task_id, session_id=session_token)
        return result

    async def extract(
        self,
        session_token: str,
        kind: str = "auto",
        *,
        task_id: Optional[str] = None,
        actor: str = "sdk",
        actor_type: str = "agent",
    ) -> Dict[str, Any]:
        """Extract structured records with source provenance."""
        if kind not in EXTRACTION_KINDS:
            raise BrowserIntelligenceError(f"unsupported extraction kind: {kind}")
        page = await self._page(session_token)
        kinds = tuple(SCRIPTS) if kind == "auto" else (kind,)
        extracted: Dict[str, Any] = {}
        for item_kind in kinds:
            extracted[item_kind] = cast(
                Any, await page.evaluate(SCRIPTS[item_kind])
            )
        captured_at = datetime.now(timezone.utc).isoformat()
        source = {
            "url": page.url,
            "captured_at": captured_at,
            "session_id": session_token,
            "kinds": list(kinds),
        }
        result: Dict[str, Any] = {
            "kind": kind,
            "data": extracted,
            "source": source,
            "count": sum(
                len(rows) if isinstance(rows, list) else (1 if rows else 0)
                for rows in extracted.values()
            ),
            "untrusted": True,
        }
        result["digest"] = digest(result["data"])
        if task_id:
            await self.evidence.record_evidence(
                task_id,
                url=str(page.url),
                excerpt=str(extracted.get("metadata", {}).get("description") or ""),
                source_metadata={"kind": kind, "count": result["count"],
                                 "digest": result["digest"], "captured_at": captured_at},
                session_id=session_token,
            )
            await self.evidence.append_audit(
                task_id, actor=actor, actor_type=actor_type,
                action="browser.extract", target=str(page.url),
                outcome={"kind": kind, "count": result["count"]},
            )
            result["envelope"] = await self.evidence.envelope(task_id, session_id=session_token)
        return result

    async def verify_extraction(
        self,
        session_token: str,
        expected: Dict[str, Any],
        *,
        task_id: Optional[str] = None,
        actor: str = "sdk",
        actor_type: str = "agent",
    ) -> Dict[str, Any]:
        """Independently re-extract and compare; never trust the first claim."""
        kind = str(expected.get("kind") or "auto")
        fresh = await self.extract(session_token, kind)
        expected_digest = str(expected.get("digest") or "")
        verified = bool(expected_digest) and fresh["digest"] == expected_digest
        reason = (
            "independent re-extraction matches recorded digest"
            if verified else "independent re-extraction did not match"
        )
        result: Dict[str, Any] = {
            "verified": verified,
            "reason": reason,
            "expected_digest": expected_digest,
            "observed_digest": fresh["digest"],
            "observed_count": fresh["count"],
        }
        if task_id:
            await self.evidence.append_audit(
                task_id, actor=actor, actor_type=actor_type,
                action="browser.verify_extraction", target=session_token,
                outcome={"verified": verified, "reason": reason},
            )
            result["envelope"] = await self.evidence.envelope(
                task_id, session_id=session_token,
                status="completed" if verified else "failed",
            )
        return result

    async def coordinate_tabs(
        self,
        session_token: str,
        actions: List[Dict[str, Any]],
        *,
        task_id: Optional[str] = None,
        actor: str = "sdk",
        actor_type: str = "agent",
    ) -> Dict[str, Any]:
        """Run interactions across multiple tabs with per-tab attribution."""
        if not actions:
            raise BrowserIntelligenceError("actions cannot be empty")
        results: List[Dict[str, Any]] = []
        for action in actions:
            tab_id = action.get("tab_id")
            if tab_id:
                existing = await browser_service.get_tab(session_token, str(tab_id))
                if not existing:
                    raise BrowserIntelligenceError("unknown tab")
            elif action.get("new_tab"):
                tab_id = await browser_service.new_tab(session_token)
            outcome = await browser_service.interact(
                action=str(action.get("action") or ""),
                target=str(action.get("target") or ""),
                value=action.get("value"),
                session_token=session_token,
                tab_id=str(tab_id) if tab_id else None,
            )
            item = {"tab_id": tab_id, "action": action.get("action"), "result": outcome}
            results.append(item)
            if task_id:
                await self.evidence.append_audit(
                    task_id, actor=actor, actor_type=actor_type,
                    action="browser.tab_action", target=str(action.get("target") or ""),
                    outcome={"action": action.get("action"),
                             "success": bool(outcome.get("success")), "tab_id": tab_id},
                )
        result: Dict[str, Any] = {"actions": results, "verified": all(
            bool(item["result"].get("success")) for item in results
        )}
        if task_id:
            result["envelope"] = await self.evidence.envelope(task_id, session_id=session_token)
        return result
