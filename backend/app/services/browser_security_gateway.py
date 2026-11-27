"""Browser Security Gateway — unified browser protection gates (Doc 29 P3).

Enforces: permission checks via existing InternetAccessService, prompt-injection
detection via existing AegisEngine, phishing/impersonation heuristics, and a
quarantine pipeline for downloads. Nothing here executes a downloaded file and
no website instruction can change IAM's permissions.
"""

from __future__ import annotations

import hashlib
import ipaddress
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, cast
from urllib.parse import urlparse

from app.core.config import settings
from app.services.aegis import AegisEngine
from app.services.browser_evidence_service import BrowserEvidenceService
from app.services.creatorapproval_service import CreatorApprovalService
from app.services.internetaccess_service import InternetAccessService

BRANDS = ("paypal", "google", "microsoft", "apple", "amazon", "bank", "github", "facebook")
DANGEROUS_EXTENSIONS = {
    ".exe", ".dll", ".bat", ".cmd", ".ps1", ".sh", ".msi", ".scr", ".vbs",
    ".jar", ".app", ".deb", ".rpm", ".dmg", ".iso", ".js", ".vbe",
}
DOWNLOAD_ACTION = "browser.download.release"


class BrowserSecurityGatewayError(PermissionError):
    """Raised when a browser operation fails a mandatory security gate."""


def phishing_signals(url: str) -> List[str]:
    """Conservative, deterministic URL heuristics; signals never grant trust."""
    try:
        parsed = urlparse(url)
    except ValueError:
        return ["invalid_url"]
    host = (parsed.hostname or "").lower()
    if not host:
        return ["missing_host"]
    signals: List[str] = []
    if "xn--" in host:
        signals.append("punycode_host")
    try:
        ipaddress.ip_address(host)
        signals.append("ip_literal_host")
    except ValueError:
        pass
    if host.count(".") >= 3:
        signals.append("excessive_subdomains")
    if any(brand in host for brand in BRANDS) and host.count(".") >= 3:
        signals.append("brand_in_subdomain")
    if parsed.username or parsed.password:
        signals.append("credentials_in_url")
    return signals


class BrowserSecurityGateway:
    """Single enforcement point for browser security decisions."""

    def __init__(self, db: Any, *, aegis: Optional[AegisEngine] = None):
        self.db = db
        self.aegis = aegis or cast(AegisEngine, AegisEngine())
        self.evidence = BrowserEvidenceService(db)

    @staticmethod
    def quarantine_root() -> Path:
        root = Path(
            settings.browser_evidence_dir
            or str(Path(__import__("tempfile").gettempdir()) / "iam-browser-evidence")
        ).resolve() / "quarantine"
        root.mkdir(parents=True, exist_ok=True)
        return root

    async def inspect_content(
        self,
        text: str,
        *,
        url: str = "",
        task_id: Optional[str] = None,
        actor: str = "sdk",
        actor_type: str = "agent",
    ) -> Dict[str, Any]:
        """Treat page text as untrusted data; detect instructions and impersonation."""
        analysis = self.aegis.analyze_text(text, source="browser_page")
        signals = phishing_signals(url) if url else []
        result: Dict[str, Any] = {
            "safe": bool(analysis.get("safe")) and not signals,
            "risk": analysis.get("risk", "low"),
            "findings": analysis.get("findings", []),
            "phishing_signals": signals,
            "instructions_ignored": True,
        }
        if task_id:
            await self.evidence.append_audit(
                task_id, actor=actor, actor_type=actor_type,
                action="browser.security.inspect", target=url[:2000],
                outcome={"safe": result["safe"], "risk": result["risk"],
                         "phishing_signals": signals},
            )
        return result

    async def check_action(
        self,
        action_type: str,
        *,
        task_id: Optional[str] = None,
        actor: str = "sdk",
        actor_type: str = "agent",
    ) -> Dict[str, Any]:
        """Delegate to the existing permission/approval layer, never reimplement it."""
        result = await InternetAccessService(self.db).check_permission(action_type)
        if task_id:
            await self.evidence.append_audit(
                task_id, actor=actor, actor_type=actor_type,
                action="browser.security.permission", target=action_type,
                outcome={"permitted": bool(result.get("permitted")),
                         "source": result.get("source")},
            )
        return result

    async def quarantine_download(
        self,
        source_path: str,
        *,
        original_name: str = "",
        task_id: Optional[str] = None,
        actor: str = "sdk",
        actor_type: str = "agent",
    ) -> Dict[str, Any]:
        """Hash, classify and isolate a download. Never execute it."""
        source = Path(source_path).resolve()
        if not source.is_file():
            raise BrowserSecurityGatewayError("download file does not exist")
        raw = source.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        name = original_name or source.name
        suffix = Path(name).suffix.lower()
        risky = suffix in DANGEROUS_EXTENSIONS
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        target = self.quarantine_root() / f"{stamp}-{digest[:16]}-{Path(name).name}"
        shutil.move(str(source), str(target))
        result: Dict[str, Any] = {
            "status": "quarantined",
            "sha256": digest,
            "bytes": len(raw),
            "extension": suffix,
            "risky_extension": risky,
            "quarantine_path": str(target),
            "executed": False,
        }
        if task_id:
            await self.evidence.append_audit(
                task_id, actor=actor, actor_type=actor_type,
                action="browser.security.download", target=name[:500],
                outcome={"sha256": digest, "risky_extension": risky, "executed": False},
            )
        return result

    async def release_download(
        self,
        quarantine_path: str,
        *,
        actor: str = "sdk",
    ) -> Dict[str, Any]:
        """Release requires the existing signed Creator approval path."""
        auth = await CreatorApprovalService(self.db).check_authorization(DOWNLOAD_ACTION, "3")
        if not auth.get("authorized"):
            raise BrowserSecurityGatewayError(
                "releasing a download requires signed Creator authorization"
            )
        source = Path(quarantine_path).resolve()
        root = self.quarantine_root()
        if root not in source.parents:
            raise BrowserSecurityGatewayError("path is outside the quarantine root")
        if not source.is_file():
            raise BrowserSecurityGatewayError("quarantined file does not exist")
        return {
            "status": "approved_for_release",
            "path": str(source),
            "authorization_id": auth.get("authorization_id"),
            "signer_id": auth.get("signer_id"),
            "executed": False,
        }
