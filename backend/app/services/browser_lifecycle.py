"""Browser lifecycle and hardening evidence (Doc 29 P8).

Version snapshots, dependency floor checks, health reporting, backups,
signed update/retirement records and audit summaries. This module records and
validates; it never silently installs, patches or restores infrastructure.
"""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from packaging.version import InvalidVersion, Version
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.web_knowledge import BrowserAudit, BrowserLifecycleRecord
from app.services.creatorapproval_service import CreatorApprovalService
from app.services.tor_intelligence import OfficialTorBrowser

PACKAGES = (
    "playwright", "pytesseract", "stem", "socksio", "pypdf", "python-docx", "openpyxl",
)
MINIMUM_VERSIONS = {
    "playwright": "1.48.0",
    "pytesseract": "0.3.13",
    "stem": "1.8.2",
    "socksio": "1.0.0",
    "pypdf": "7.2.0",
    "python-docx": "1.2.0",
    "openpyxl": "3.1.5",
}
UPDATE_ACTION = "browser.lifecycle.update"
RETIRE_ACTION = "browser.lifecycle.retire"


class BrowserLifecycleError(PermissionError):
    """Raised when a lifecycle action lacks authority or evidence."""


def installed_version(package: str) -> str:
    try:
        return importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        return "unknown"


class BrowserLifecycleService:
    """Evidence-only lifecycle management for the browser subsystem."""

    def __init__(self, db: AsyncSession):
        self.db = db

    def snapshot(self) -> Dict[str, Any]:
        payload = {
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "engines": {
                "configured": settings.uwai_browser_engine,
                "allowlist": ["chromium", "firefox", "webkit"],
                "official_tor_browser_present": OfficialTorBrowser().executable() is not None,
            },
            "packages": {name: installed_version(name) for name in PACKAGES},
            "config": {
                "browser_enabled": settings.browser_enabled,
                "browser_ocr_enabled": settings.browser_ocr_enabled,
                "browser_max_concurrent_sessions": settings.browser_max_concurrent_sessions,
                "tor_enabled": settings.tor_enabled,
                "tor_onion_access_enabled": settings.tor_onion_access_enabled,
            },
        }
        encoded = json.dumps(payload, sort_keys=True).encode("utf-8")
        payload["sha256"] = hashlib.sha256(encoded).hexdigest()
        payload["note"] = "configuration snapshot; not proof of runtime health"
        return payload

    async def health(self) -> Dict[str, Any]:
        ocr_binary = bool(shutil.which("tesseract")) or Path("/usr/bin/tesseract").is_file()
        playwright_cache = Path("/ms-playwright").is_dir()
        evidence_root = self._root()
        checks = {
            "browser_engine": {
                "configured": settings.uwai_browser_engine,
                "runtime_cache_present": playwright_cache,
                "status": "present" if playwright_cache else "unverified",
            },
            "ocr": {
                "binding": installed_version("pytesseract"),
                "binary": ocr_binary,
                "status": "available" if ocr_binary and installed_version("pytesseract") != "unknown"
                          else "unavailable",
            },
            "tor": {
                "enabled": settings.tor_enabled,
                "official_browser_present": OfficialTorBrowser().executable() is not None,
                "status": "available" if settings.tor_enabled and OfficialTorBrowser().executable()
                          else "unavailable",
            },
            "evidence_storage": {
                "path": str(evidence_root),
                "writable": os.access(evidence_root, os.W_OK),
            },
        }
        audit_count = await self.db.execute(select(func.count(BrowserAudit.id)))
        checks["audit"] = {
            "event_count": audit_count.scalar_one() if hasattr(audit_count, "scalar_one") else 0,
        }
        healthy = (
            checks["evidence_storage"]["writable"]  # type: ignore[index]
            and checks["browser_engine"]["status"] == "present"  # type: ignore[index]
        )
        return {
            "healthy": healthy,
            "checks": checks,
            "claimed_operational": False,
            "note": "health checks are local evidence only; no live browser session is implied",
        }

    def vulnerability_scan(self) -> Dict[str, Any]:
        """Dependency floor check — not a full CVE scan."""
        results: Dict[str, Any] = {}
        for package, floor in MINIMUM_VERSIONS.items():
            version = installed_version(package)
            if version == "unknown":
                results[package] = {"version": version, "status": "unknown"}
                continue
            try:
                results[package] = {
                    "version": version,
                    "status": "ok" if Version(version) >= Version(floor) else "outdated",
                    "minimum": floor,
                }
            except InvalidVersion:
                results[package] = {"version": version, "status": "unknown"}
        return {
            "components": results,
            "scope": "declared minimum versions only",
            "cve_scan_claimed": False,
        }

    @staticmethod
    def _root() -> Path:
        root = Path(
            settings.browser_evidence_dir
            or str(Path(tempfile.gettempdir()) / "iam-browser-evidence")
        ).resolve()
        root.mkdir(parents=True, exist_ok=True)
        return root

    async def _record(
        self,
        component: str,
        event_type: str,
        actor: str,
        *,
        version: Optional[str] = None,
        checksum: Optional[str] = None,
        backup_ref: Optional[str] = None,
        status: str = "applied",
        payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        row = BrowserLifecycleRecord(
            component=component, event_type=event_type, status=status,
            version=version, checksum=checksum, backup_ref=backup_ref,
            actor=actor, payload=payload or {},
        )
        self.db.add(row)
        await self.db.flush()
        await self.db.commit()
        return {
            "id": str(row.id), "component": component, "event_type": event_type,
            "status": status, "version": version, "checksum": checksum,
            "backup_ref": backup_ref, "actor": actor,
        }

    async def snapshot_record(self, actor: str) -> Dict[str, Any]:
        snapshot = self.snapshot()
        return await self._record(
            "browser-subsystem", "snapshot", actor,
            checksum=snapshot["sha256"], payload=snapshot,
        )

    async def backup(self, actor: str) -> Dict[str, Any]:
        snapshot = self.snapshot()
        target = self._root() / f"lifecycle-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}.json"
        target.write_text(json.dumps(snapshot, sort_keys=True, indent=2), encoding="utf-8")
        checksum = hashlib.sha256(target.read_bytes()).hexdigest()
        return await self._record(
            "browser-subsystem", "backup", actor,
            checksum=checksum, backup_ref=str(target), status="verified",
        )

    async def verify_backup(self, backup_ref: str, actor: str) -> Dict[str, Any]:
        path = Path(backup_ref).resolve()
        if self._root() not in path.parents or not path.is_file():
            raise BrowserLifecycleError("backup reference is outside the evidence root")
        checksum = hashlib.sha256(path.read_bytes()).hexdigest()
        result = await self._record(
            "browser-subsystem", "recovery", actor,
            checksum=checksum, backup_ref=str(path), status="verified",
            payload={"note": "integrity verified; restore not applied"},
        )
        result["restore_applied"] = False
        return result

    async def apply_update(
        self,
        component: str,
        version: str,
        actor: str,
    ) -> Dict[str, Any]:
        auth = await CreatorApprovalService(self.db).check_authorization(UPDATE_ACTION, "3")
        if not auth.get("authorized"):
            raise BrowserLifecycleError("browser updates require signed Creator authorization")
        result = await self._record(
            component, "update", actor, version=version, status="applied",
            payload={"authorization_id": auth.get("authorization_id"),
                     "note": "record only; installation is an operator action"},
        )
        result["installation_performed"] = False
        return result

    async def retire(
        self,
        component: str,
        reason: str,
        actor: str,
    ) -> Dict[str, Any]:
        auth = await CreatorApprovalService(self.db).check_authorization(RETIRE_ACTION, "3")
        if not auth.get("authorized"):
            raise BrowserLifecycleError("retirement requires signed Creator authorization")
        if component == "tor":
            settings.tor_enabled = False
            settings.tor_onion_access_enabled = False
        elif component == "ocr":
            settings.browser_ocr_enabled = False
        return await self._record(
            component, "retire", actor, status="retired",
            payload={"reason": reason[:1000], "authorization_id": auth.get("authorization_id")},
        )

    async def audit_report(self) -> Dict[str, Any]:
        result = await self.db.execute(select(BrowserAudit.action, func.count(BrowserAudit.id)).group_by(BrowserAudit.action))
        rows = result.all() if hasattr(result, "all") else []
        return {
            "by_action": {str(action): int(count) for action, count in rows},
            "secret_values_logged": False,
        }

    def performance_budget(self) -> Dict[str, Any]:
        from app.services.browser_service import browser_service

        return {
            "max_concurrent_sessions": settings.browser_max_concurrent_sessions,
            "session_ttl_seconds": settings.browser_session_ttl_seconds,
            "active_runtime_contexts": len(getattr(browser_service, "_contexts", {})),
            "model_ram_governed_by": "IRWM (OD-39)",
            "measured": False,
        }
