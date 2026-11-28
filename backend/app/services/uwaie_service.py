"""Universal Website and Application Interaction Engine (OD-27).

Frontend-first interaction with permission gates, outcome verification and
credential-free workflow knowledge. Page content is always untrusted data,
never instructions. Interface understanding uses roles/labels/text rather
than fixed screen coordinates.
"""

import re
from typing import Any, Dict, List, Optional, cast
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.digital_access import AssistanceRequest
from app.models.internetaccess import InternetSession
from app.models.security import AuditEvent
from app.models.uwaie import WebsiteWorkflow
from app.services.browser_service import browser_service
from app.services.iics.egress import enforce as enforce_egress
from app.services.browser_evidence_service import BrowserEvidenceService
from app.services.internetaccess_service import InternetAccessService
from app.services.creatorapproval_service import CreatorApprovalService

ALLOWED_ACTIONS = {
    "navigate", "click", "type", "submit", "scroll", "text", "links", "url",
    "upload", "download", "new_tab", "list_tabs", "close_tab",
}
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
        target = str(url or "").strip()
        if not target or BLOCKED_TARGETS.search(target):
            raise UWAIEError("target is empty or is an access challenge/paywall")
        decision = enforce_egress(target)
        if not decision.allowed:
            raise UWAIEError(f"egress_denied:{decision.reason}")
        permission = await InternetAccessService(self.db).check_permission("browse_public")
        if not permission["permitted"]:
            raise UWAIEError(permission["reason"])

        page = await browser_service.get_page()
        response = None
        try:
            response = await page.goto(url, wait_until="domcontentloaded", timeout=browser_service.timeout)
            structure = await page.evaluate(INSPECT_SCRIPT)
        except Exception as exc:
            if "Executable doesn't exist" in str(exc) or "BrowserType.launch" in str(exc):
                raise UWAIEError(
                    "browser runtime unavailable; install Playwright chromium before using UWAIE"
                ) from exc
            raise
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
        recover: bool = True,
        task_id: Optional[str] = None,
        actor_type: str = "agent",
        permission_scope: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Run an explicit, caller-supplied workflow. Page content never adds steps.

        When task_id is supplied, Doc 29 WP-03 evidence and attribution records
        are written and a standard envelope is added to the result.
        """
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

        outcomes: List[Dict[str, Any]] = []
        current_url: Optional[str] = None
        for step in steps:
            action = step["action"]
            target = str(step.get("target") or "")
            result = await browser_service.interact(
                action=action,
                target=target,
                value=step.get("value"),
                session_token=session_token,
                tab_id=step.get("tab_id"),
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
            error_text = str(result.get("error") or "")
            if "Executable doesn't exist" in error_text or "BrowserType.launch" in error_text:
                raise UWAIEError(
                    "browser runtime unavailable; install Playwright chromium before using UWAIE"
                )
            if action == "navigate" and result.get("success"):
                current_url = target[:2000]
            outcomes.append(
                {
                    "action": action,
                    "target": target[:500],
                    "success": bool(result.get("success")),
                    "error": result.get("error"),
                }
            )
            if task_id:
                evidence = BrowserEvidenceService(self.db)
                await evidence.append_audit(
                    task_id,
                    actor=actor,
                    actor_type=actor_type,
                    action=f"uwaie.{action}",
                    target=target,
                    outcome={
                        "success": bool(result.get("success")),
                        "error": str(result.get("error") or "")[:500],
                    },
                )
                screenshot = (
                    result.get("result")
                    if action == "screenshot" and result.get("success") else None
                )
                excerpt = (
                    str(result.get("result") or "")
                    if action == "text" and result.get("success") else None
                )
                if screenshot or excerpt:
                    await evidence.record_evidence(
                        task_id,
                        url=current_url,
                        screenshot_b64=screenshot if isinstance(screenshot, str) else None,
                        excerpt=excerpt,
                        session_id=session_token,
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

        recovery = None
        if recover and any(not item["success"] for item in outcomes):
            recovery_url = next(
                (str(item.get("target") or "") for item in steps if item.get("action") == "navigate"),
                None,
            )
            if recovery_url:
                try:
                    recovery = await self.inspect(recovery_url, actor)
                except UWAIEError as exc:
                    recovery = {"error": str(exc), "human_handover": True}
                self.db.add(
                    AuditEvent(
                        event_type="uwaie_recovery",
                        actor=actor,
                        target=recovery_url[:500],
                        details={"re_inspected": bool(recovery and "error" not in recovery)},
                    )
                )

        saved = None
        if learn and verified and workflow_name:
            saved = await self._save_workflow(
                workflow_name, steps, verification, actor
            )

        if task_id:
            evidence = BrowserEvidenceService(self.db)
            await evidence.append_audit(
                task_id,
                actor=actor,
                actor_type=actor_type,
                action="uwaie.verification",
                target=workflow_name or "unspecified",
                outcome={"verified": verified, "reason": str(reason)[:500]},
            )
            for state in ("running", "verifying", "completed" if verified else "failed"):
                try:
                    await evidence.set_state(task_id, state)
                except PermissionError:
                    # Runs created before WP-03 or already advanced: never
                    # downgrade a recorded state.
                    pass

        await self.db.commit()
        response: Dict[str, Any] = {
            "steps": outcomes,
            "verified": verified,
            "verification_reason": reason,
            "workflow": saved,
            "recovery": recovery,
            "credentials_stored": False,
        }
        if task_id:
            response["envelope"] = await BrowserEvidenceService(self.db).envelope(
                task_id, session_id=session_token,
                status="completed" if verified else "failed",
            )
        return response

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

    async def _workflow(self, workflow_id: str) -> WebsiteWorkflow:
        try:
            identifier = UUID(str(workflow_id))
        except (ValueError, TypeError) as exc:
            raise LookupError("workflow not found") from exc
        result = await self.db.execute(
            select(WebsiteWorkflow).where(WebsiteWorkflow.id == identifier)
        )
        workflow = result.scalar_one_or_none()
        if not workflow:
            raise LookupError("workflow not found")
        return workflow

    async def approve_workflow(
        self, workflow_id: str, approval_id: str, actor: str
    ) -> Dict[str, Any]:
        """Stored workflows are inert until a signed Creator approves them."""
        workflow = await self._workflow(workflow_id)
        authority = await CreatorApprovalService(self.db).check_authorization(
            "uwaie.workflow_approve", requested_level="3", target_ref=str(workflow.id)
        )
        if not authority.get("authorized"):
            raise UWAIEError("no signed Creator authorization covers this workflow")
        if approval_id and authority.get("authorization_id") != approval_id:
            raise UWAIEError("approval_id does not match the active signed authorization")
        workflow.is_approved = True  # type: ignore[assignment]
        self.db.add(
            AuditEvent(
                event_type="uwaie_workflow_approved",
                actor=actor,
                target=str(workflow.id),
                details={"authorization_id": authority["authorization_id"]},
            )
        )
        await self.db.commit()
        return {
            "id": str(workflow.id),
            "is_approved": True,
            "authorization_id": authority["authorization_id"],
        }

    async def reuse_workflow(
        self,
        workflow_id: str,
        url: str,
        session_token: Optional[str],
        actor: str,
    ) -> Dict[str, Any]:
        """Replay an approved workflow with its recorded verification gate."""
        workflow = await self._workflow(workflow_id)
        if not workflow.is_approved:
            raise UWAIEError("workflow must be approved before reuse")
        pattern = str(workflow.url_pattern)
        if pattern and pattern not in url:
            raise UWAIEError("url does not match the approved workflow pattern")
        adapted, remapped = await self._adapt_steps(
            cast(List[Dict[str, Any]], workflow.steps or []), url, actor
        )
        result = await self.execute(
            steps=adapted,
            verification=workflow.verification or {},  # type: ignore[arg-type]
            session_token=session_token,
            learn=False,
            workflow_name=workflow.name,  # type: ignore[arg-type]
            actor=actor,
        )
        result["adapted_steps"] = remapped
        return result

    async def _adapt_steps(
        self, steps: List[Dict[str, Any]], url: str, actor: str
    ) -> tuple[List[Dict[str, Any]], int]:
        """Re-locate recorded steps by accessible label when a layout changed.

        Page structure is used only to find the target of a trusted step — it
        never adds or changes the action itself.
        """
        page = await self.inspect(url, actor)
        fields: List[Dict[str, Any]] = []
        for form in page.get("forms", []):
            fields.extend(form.get("fields", []) or [])
        adapted: List[Dict[str, Any]] = []
        remapped = 0
        for step in steps:
            item = dict(step)
            semantic = str(item.get("semantic") or item.get("label") or "").lower()
            if semantic and item.get("action") in {"click", "type", "submit"}:
                match = next(
                    (
                        f for f in fields
                        if semantic in f"{f.get('label', '')} {f.get('name', '')}".lower()
                    ),
                    None,
                )
                if match:
                    selector = ""
                    if match.get("name"):
                        selector = f'[name="{str(match["name"]).replace(chr(34), "")}"]'
                    elif match.get("label"):
                        selector = f'[aria-label="{str(match["label"]).replace(chr(34), "")}"]'
                    if selector and selector != item.get("target"):
                        item["target"] = selector
                        remapped += 1
            adapted.append(item)
        if remapped:
            self.db.add(
                AuditEvent(
                    event_type="uwaie_workflow_adapted",
                    actor=actor,
                    target=url[:500],
                    details={"remapped_steps": remapped},
                )
            )
            await self.db.commit()
        return adapted, remapped

    async def request_handover(
        self, url: str, reason: str, actor: str
    ) -> Dict[str, Any]:
        """Hand a sensitive step to a human; IAM takes no autonomous action."""
        if not url or not reason:
            raise UWAIEError("url and reason are required for a handover")
        handover_id = str(uuid4())
        self.db.add(
            AssistanceRequest(
                level="2",
                reason=reason[:2000],
                context={"url": url, "handover_id": handover_id},
                task_ref=handover_id,
                status="pending",
            )
        )
        self.db.add(
            AuditEvent(
                event_type="uwaie_human_handover_requested",
                actor=actor,
                target=url,
                details={"handover_id": handover_id, "reason": reason[:1000]},
            )
        )
        await self.db.commit()
        return {
            "handover_id": handover_id,
            "status": "pending_human",
            "autonomous_action_taken": False,
        }

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
            elif action == "upload":
                required = "uwai_upload_file"
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

    async def verify(
        self,
        verification: Dict[str, Any],
        session_token: str,
        *,
        task_id: Optional[str] = None,
        actor: str = "sdk",
        actor_type: str = "agent",
    ) -> Dict[str, Any]:
        """Public verification surface for Doc 29 §7.1 (independent outcome check)."""
        verified, reason = await self._verify(verification, session_token)
        result: Dict[str, Any] = {"verified": verified, "verification_reason": reason}
        if task_id:
            evidence = BrowserEvidenceService(self.db)
            await evidence.append_audit(
                task_id,
                actor=actor,
                actor_type=actor_type,
                action="uwaie.verify",
                target=session_token,
                outcome={"verified": verified, "reason": reason[:500]},
            )
            for state in ("running", "verifying", "completed" if verified else "failed"):
                try:
                    await evidence.set_state(task_id, state)
                except PermissionError:
                    pass
            result["envelope"] = await evidence.envelope(
                task_id, session_id=session_token,
                status="completed" if verified else "failed",
            )
        await self.db.commit()
        return result

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
