"""Local document parsing for browser research (Doc 29 P2).

PDF, DOCX, XLSX and text/HTML documents are parsed locally — no hosted model
and no external parsing service. Public-http-only fetching with DNS/SSRF checks;
document content is untrusted data, never instructions.
"""

from __future__ import annotations

import asyncio
import hashlib
import ipaddress
import re
import socket
from datetime import datetime, timezone
from io import BytesIO
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import httpx
from docx import Document
from openpyxl import load_workbook
from pypdf import PdfReader

from app.services.browser_evidence_service import BrowserEvidenceService

MAX_DOWNLOAD_BYTES = 5_000_000
MAX_TEXT_CHARS = 30_000
MAX_PAGES = 50
MAX_SHEETS = 20
MAX_ROWS = 200
TAG = re.compile(r"<[^>]+>")


class DocumentParsingError(ValueError):
    """Raised when a document cannot be fetched or parsed safely."""


async def is_public_url(url: str) -> bool:
    """Fail closed: http(s) only, no credentials, no private/loopback targets."""
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return False
    if parsed.username or parsed.password:
        return False
    host = parsed.hostname.lower()
    if host in ("localhost", "localhost.localdomain") or host.endswith(".localhost"):
        return False
    try:
        try:
            literal = ipaddress.ip_address(host)
            addresses = [literal]
        except ValueError:
            resolved = await asyncio.to_thread(socket.getaddrinfo, host, None)
            addresses = [ipaddress.ip_address(item[4][0]) for item in resolved]
    except (ValueError, OSError, IndexError):
        return False
    if not addresses:
        return False
    return all(
        not addr.is_private
        and not addr.is_loopback
        and not addr.is_link_local
        and not addr.is_reserved
        and not addr.is_multicast
        for addr in addresses
    )


def parse_pdf(raw: bytes) -> Dict[str, Any]:
    reader = PdfReader(BytesIO(raw))
    pages = []
    for index, page in enumerate(reader.pages[:MAX_PAGES]):
        pages.append(str(page.extract_text() or "")[:MAX_TEXT_CHARS])
    return {
        "kind": "pdf",
        "page_count": len(reader.pages),
        "pages": pages,
        "text": "\n".join(pages)[:MAX_TEXT_CHARS],
    }


def parse_docx(raw: bytes) -> Dict[str, Any]:
    document = Document(BytesIO(raw))
    paragraphs = [p.text for p in document.paragraphs if p.text.strip()]
    tables = [
        [[cell.text for cell in row.cells] for row in table.rows[:MAX_ROWS]]
        for table in document.tables[:MAX_SHEETS]
    ]
    return {
        "kind": "docx",
        "paragraphs": paragraphs[:MAX_ROWS],
        "tables": tables,
        "text": "\n".join(paragraphs)[:MAX_TEXT_CHARS],
    }


def parse_xlsx(raw: bytes) -> Dict[str, Any]:
    workbook = load_workbook(BytesIO(raw), read_only=True, data_only=True)
    sheets: Dict[str, Any] = {}
    for name in workbook.sheetnames[:MAX_SHEETS]:
        sheet = workbook[name]
        rows: List[List[Any]] = []
        for row in sheet.iter_rows(max_row=MAX_ROWS, values_only=True):
            rows.append([value for value in row])
        sheets[name] = rows
    return {
        "kind": "xlsx",
        "sheets": sheets,
        "text": "\n".join(
            " ".join(str(cell) for cell in row)
            for rows in sheets.values() for row in rows
        )[:MAX_TEXT_CHARS],
    }


def parse_plain(raw: bytes) -> Dict[str, Any]:
    text = raw.decode("utf-8", errors="replace")[:MAX_TEXT_CHARS]
    return {"kind": "text", "text": text}


def parse_html(raw: bytes) -> Dict[str, Any]:
    text = TAG.sub(" ", raw.decode("utf-8", errors="replace"))
    text = re.sub(r"\s+", " ", text).strip()[:MAX_TEXT_CHARS]
    return {"kind": "html", "text": text}


PARSERS = {
    "pdf": parse_pdf,
    "docx": parse_docx,
    "xlsx": parse_xlsx,
    "text": parse_plain,
    "html": parse_html,
}


def detect_kind(name: str, content_type: str = "") -> str:
    lowered = name.lower()
    mime = content_type.lower().split(";")[0].strip()
    if lowered.endswith(".pdf") or mime == "application/pdf":
        return "pdf"
    if lowered.endswith(".docx") or mime.endswith("wordprocessingml.document"):
        return "docx"
    if lowered.endswith((".xlsx", ".xlsm")) or "spreadsheetml.sheet" in mime:
        return "xlsx"
    if lowered.endswith((".html", ".htm")) or mime in ("text/html", "application/xhtml+xml"):
        return "html"
    if lowered.endswith((".txt", ".md", ".csv")) or mime.startswith("text/"):
        return "text"
    raise DocumentParsingError("unsupported document type")


class BrowserDocumentService:
    """Fetch permitted public documents and extract structured local text."""

    def __init__(self, db: Any):
        self.db = db
        self.evidence = BrowserEvidenceService(db)

    async def fetch(self, url: str) -> tuple[bytes, str, str]:
        if not await is_public_url(url):
            raise DocumentParsingError("document URL is not a permitted public target")
        try:
            async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
                async with client.stream("GET", url) as response:
                    final_url = str(response.url)
                    if not await is_public_url(final_url):
                        raise DocumentParsingError("redirect target is not a permitted public URL")
                    if response.status_code >= 400:
                        raise DocumentParsingError(
                            f"document fetch failed with HTTP {response.status_code}"
                        )
                    content_type = str(response.headers.get("content-type", ""))
                    chunks: List[bytes] = []
                    total = 0
                    async for chunk in response.aiter_bytes():
                        total += len(chunk)
                        if total > MAX_DOWNLOAD_BYTES:
                            raise DocumentParsingError("document exceeds the download limit")
                        chunks.append(chunk)
                    return b"".join(chunks), final_url, content_type
        except httpx.HTTPError as exc:
            raise DocumentParsingError(f"document fetch failed: {type(exc).__name__}") from exc

    def parse(self, raw: bytes, name: str, content_type: str = "") -> Dict[str, Any]:
        kind = detect_kind(name, content_type)
        try:
            parsed = PARSERS[kind](raw)
        except Exception as exc:
            raise DocumentParsingError(
                f"document parsing failed: {type(exc).__name__}"
            ) from exc
        parsed["untrusted"] = True
        return parsed

    async def parse_url(
        self,
        url: str,
        *,
        task_id: Optional[str] = None,
        actor: str = "sdk",
        actor_type: str = "agent",
    ) -> Dict[str, Any]:
        raw, final_url, content_type = await self.fetch(url)
        name = urlparse(final_url).path.rsplit("/", 1)[-1] or "document"
        parsed = self.parse(raw, name, content_type)
        result: Dict[str, Any] = {
            **parsed,
            "source": {
                "url": final_url,
                "captured_at": datetime.now(timezone.utc).isoformat(),
                "sha256": hashlib.sha256(raw).hexdigest(),
                "bytes": len(raw),
                "content_type": content_type,
            },
        }
        result["digest"] = hashlib.sha256(
            str(parsed.get("text", "")).encode("utf-8")
        ).hexdigest()
        if task_id:
            await self.evidence.record_evidence(
                task_id,
                url=final_url,
                excerpt=str(parsed.get("text") or "")[:2000],
                source_metadata={
                    "kind": parsed["kind"],
                    "sha256": result["source"]["sha256"],
                    "bytes": len(raw),
                    "text_digest": result["digest"],
                },
            )
            await self.evidence.append_audit(
                task_id, actor=actor, actor_type=actor_type,
                action="browser.parse_document", target=final_url,
                outcome={"kind": parsed["kind"], "bytes": len(raw)},
            )
            result["envelope"] = await self.evidence.envelope(task_id)
        return result
