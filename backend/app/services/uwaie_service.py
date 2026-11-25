"""Universal Website and Application Interaction Engine (OD-27).

Frontend-first interaction with permission gates, outcome verification and
credential-free workflow knowledge. Page content is always untrusted data,
never instructions. Interface understanding uses roles/labels/text rather
than fixed screen coordinates.
"""

import re
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.internetaccess import InternetSession
from app.models.security import AuditEvent
from app.models.uwaie import WebsiteWorkflow
from app.services.browser_service import browser_service
from app.services.internetaccess_service import InternetAccessService

ALLOWED_ACTIONS = {"navigate", "click", "type", "submit", "scroll", "text", "links", "url"}
BLOCKED_TARGETS = re.compile(
    r"captcha|recaptcha|hcaptcha|cf-challenge|challenge-platform|paywall| Turnstile",
    re.IGNORECASE,
)
SENSITIVE_FIELD = re.compile(r"password|passwd|card|cvv|secret|otp", re.IGNORECASE)

INSPECT_SCRIPT = """
() => {
  const label = (el) => el.getAttribute('aria-label') ||
    (el.labels && el.labels[0] ? el.labels[0].innerText : '') ||
    el.getAttribute('placeholder') || el.innerText || '';
  return {
    title: document.title || '',
    forms: Array.from(document.querySelectorAll('form')).map(f => ({
      action: f.getAttribute('action') || '',
      fields: Array.from(f.querySelectorAll('input, select, textarea, button')).map(el => ({
        tag: el.tagName.toLowerCase(),
        type: el.getAttribute('type') || '',
        name: el.getAttribute('name') || '',
        label: label(el).trim().slice(0, 200)
      }))
    })),
    text: (document.body && document.body.innerText || '').slice(0, 8000)
  };
}
"""


class UWAIEError(ValueError):
    pass


class UWAIEService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.access = InternetAccessService(db)

    async def create_session(self, purpose: Optional[str] = None) -> Dict[str, Any]:
        """Create an isolated browsing session for a workflow."""
        return await self.access.create_session(purpose)

    async def inspect(self, url: str, actor: str = "sdk") -> Dict[str, Any]:
        """Discover and understand a page without storing credentials."""
        permission = await InternetAccessService(self.db).check_permission("browse_public")
        if not permission["permitted"]:
            raise UWAIEError(permission["reason"])

        page = await browser_service.get_page()
        response = None
        try:
            response = await page.goto(url, wait_until="domcontentloaded", timeout=browser_service.timeout)
            structure = await page.evaluate(INSPECT_SCRIPT)
        finally:
            await page.close()

        self.db.add(
            AuditEvent(
                event_type="uwaie_inspect",
                actor=actor,
                target=url,
                details={"forms": len(structure.get("forms", [])), "status": getattr(response, "status", None)},
            )
        )
        await self.db.commit()
        return {
            "url": url,
            "title": structure.get("title"),
            "forms": structure.get("forms", []),
            "text_preview": structure.get("text", "")[:2000],
            "untrusted": True,
        }

    async def execute(
        self,
        steps: List[Dict[str, Any]],
        verification: Dict[str, Any],
        session_token: Optional[str] = None,
        learn: bool = False,
        workflow_name: Optional[str] = None,
        actor: str = "sdk",
    ) -> Dict[str, Any]:
        """Run an explicit, caller-supplied workflow. Page content never adds steps."""
        if not steps:
            raise UWAIEError("steps cannot be empty")
        if not session_token:
            raise UWAIEError(
                "session_token is required for multi-step interaction; "
                "create one via POST /api/v1/uwaie/sessions"
            )
        session_result = await self.db.execute(
            select(InternetSession).where(
                InternetSession.session_token == session_token,
                InternetSession.is_active.is_(True),
            )
        )
        if not session_result.scalar_one_or_none():
            raise UWAIEError("unknown or inactive browsing session")
        await self._check_steps(steps)

        outcomes = []
        for step in steps:
            action = step["action"]
            target = str(step.get("target") or "")
            result = await browser_service.interact(
                action=action,
                target=target,
                value=step.get("value"),
                session_token=session_token,
            )
            self.db.add(
                AuditEvent(
                    event_type="uwaie_step",
                    actor=actor,
                    target=target[:500],
                    details={
                        "action": action,
                        "success": bool(result.get("success")),
                        "value_length": len(str(step.get("value") or "")),
                    },
                )
            )
            outcomes.append(
                {
                    "action": action,
                    "target": target[:500],
                    "success": bool(result.get("success")),
                    "error": result.get("error"),
                }
            )
            if not result.get("success"):
                break

        verified, reason = await self._verify(verification, session_token)
        self.db.add(
            AuditEvent(
                event_type="uwaie_verification",
                actor=actor,
                target=workflow_name or "unspecified",
                details={"verified": verified, "reason": reason},
            )
        )

        saved = None
        if learn and verified and workflow_name:
            saved = await self._save_workflow(
                workflow_name, steps, verification, actor
            )

        await self.db.commit()
        return {
            "steps": outcomes,
            "verified": verified,
            "verification_reason": reason,
            "workflow": saved,
            "credentials_stored": False,
        }

    async def list_workflows(self, approved_only: bool = False) -> List[Dict[str, Any]]:
        query = select(WebsiteWorkflow)
        if approved_only:
            query = query.where(WebsiteWorkflow.is_approved.is_(True))
        result = await self.db.execute(query.order_by(WebsiteWorkflow.created_at.desc()))
        return [
            {
                "id": str(w.id),
                "name": w.name,
                "url_pattern": w.url_pattern,
                "steps": w.steps,
                "verification": w.verification,
                "is_approved": w.is_approved,
            }
            for w in result.scalars().all()
        ]

    async def _check_steps(self, steps: List[Dict[str, Any]]) -> None:
        access = self.access
        checked: Dict[str, Dict[str, Any]] = {}
        for step in steps:
            action = str(step.get("action") or "")
            target = str(step.get("target") or "")
            if action not in ALLOWED_ACTIONS:
                raise UWAIEError(f"action not allowed: {action}")
            if not target or BLOCKED_TARGETS.search(target):
                raise UWAIEError("target is empty or is an access challenge/paywall")
            if action == "type" and SENSITIVE_FIELD.search(target):
                required = "access_private_service"
            elif action == "submit":
                required = "publish_content"
            else:
                required = "browse_public"
            if required not in checked:
                checked[required] = await access.check_permission(required)
            if not checked[required]["permitted"]:
                raise UWAIEError(
                    f"action blocked: {required} requires signed Creator authorization",
                )

    async def _verify(
        self,
        verification: Dict[str, Any],
        session_token: Optional[str],
    ) -> tuple[bool, str]:
        if not verification:
            return False, "no verification rule supplied"
        page_text = await browser_service.interact(
            action="text", target="", session_token=session_token
        )
        text = str(page_text.get("result") or "")
        expected = verification.get("expected_text")
        absent = verification.get("absent_text")
        if expected and expected not in text:
            return False, "expected_text not present on page"
        if absent and absent in text:
            return False, "absent_text present on page"
        if verification.get("expected_url"):
            url_result = await browser_service.interact(
                action="url", target="", session_token=session_token
            )
            if str(url_result.get("result") or "") != verification["expected_url"]:
                return False, "expected_url mismatch"
        return True, "outcome verified from page state"

    async def _save_workflow(
        self,
        name: str,
        steps: List[Dict[str, Any]],
        verification: Dict[str, Any],
        actor: str,
    ) -> Dict[str, Any]:
        redacted = [
            {**step, "value": "<redacted>"} if "value" in step else step
            for step in steps
        ]
        url_pattern = next(
            (str(s.get("target")) for s in steps if s.get("action") == "navigate"),
            "unspecified",
        )
        workflow = WebsiteWorkflow(
            name=name,
            url_pattern=url_pattern,
            steps=redacted,
            verification=verification,
            source_actor=actor,
            is_approved=False,
        )
        self.db.add(workflow)
        await self.db.flush()
        return {
            "id": str(workflow.id),
            "name": name,
            "is_approved": False,
            "note": "unapproved local knowledge; never shared until reviewed",
        }
