"""TIPS P6 — onion intelligence, safe files, Creator controls, emergency stop.

Reachability is not trust. All onion access is Creator-controlled and fails
closed. Downloaded files are hashed, quarantined, legally gated and never
executed. No identity, credential or session is shared between projects.
"""

from __future__ import annotations

import re
import shutil
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.web_knowledge import OnionReputation
from app.services.browser_evidence_service import BrowserEvidenceService
from app.services.browser_security_gateway import BrowserSecurityGateway
from app.services.iplci.service import IPLCIService
from app.services.tor_intelligence import TorManager

V3_ONION = re.compile(r"^[a-z2-7]{56}\.onion$", re.IGNORECASE)
BRAND_TERMS = ("paypal", "google", "microsoft", "apple", "amazon", "bank", "github")


class TorPrivacyError(PermissionError):
    """Raised when a P6 privacy gate fails."""


def validate_onion_address(address: str) -> bool:
    """Accept only V3 (.onion v2/16-character addresses are refused)."""
    return bool(V3_ONION.match(str(address).strip().lower()))


class OnionServiceIntelligence:
    """Provenance and reputation records; never auto-confirms an operator."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.evidence = BrowserEvidenceService(db)

    async def _record(self, address: str) -> Optional[OnionReputation]:
        result = await self.db.execute(
            select(OnionReputation).where(OnionReputation.address == address)
        )
        return result.scalar_one_or_none() if hasattr(result, "scalar_one_or_none") else None

    async def observe(
        self,
        address: str,
        *,
        claimed_operator: Optional[str] = None,
        source_urls: Optional[List[str]] = None,
        actor: str = "sdk",
        task_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not validate_onion_address(address):
            raise TorPrivacyError("invalid V3 onion address")
        address = address.strip().lower()
        row = await self._record(address)
        if not row:
            row = OnionReputation(
                address=address,
                claimed_operator=claimed_operator,
                source_urls=list(source_urls or []),
                status="unknown",
                availability={},
                assessment={},
            )
            self.db.add(row)
        else:
            sources = list(row.source_urls or [])
            for url in source_urls or []:
                if url not in sources:
                    sources.append(url)
            row.source_urls = sources  # type: ignore[assignment]
            if claimed_operator:
                row.claimed_operator = claimed_operator  # type: ignore[assignment]
        row.updated_at = datetime.now(timezone.utc)  # type: ignore[assignment]
        await self.db.commit()
        if task_id:
            await self.evidence.append_audit(
                task_id, actor=actor, action="tor.onion.observe", target=address,
                outcome={"status": row.status, "source_count": len(row.source_urls or [])},
            )
        return self._row(row)

    async def check_availability(self, address: str) -> Dict[str, Any]:
        """Probe through the configured Tor SOCKS proxy; fail closed otherwise."""
        if not settings.tor_enabled or not settings.tor_onion_access_enabled:
            return {"reachable": False, "reason": "onion access is disabled"}
        if not validate_onion_address(address):
            return {"reachable": False, "reason": "invalid V3 onion address"}
        proxy = f"socks5://127.0.0.1:{settings.tor_socks_port}"
        try:
            async with httpx.AsyncClient(proxy=proxy, timeout=8.0) as client:
                response = await client.get(f"http://{address.strip().lower()}/")
            return {
                "reachable": True,
                "status_code": response.status_code,
                "bytes": len(response.content),
                "note": "reachability is not proof of operator identity",
            }
        except Exception as exc:
            return {"reachable": False, "reason": type(exc).__name__}

    async def assess(
        self,
        address: str,
        *,
        actor: str = "sdk",
        task_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not validate_onion_address(address):
            raise TorPrivacyError("invalid V3 onion address")
        address = address.strip().lower()
        row = await self._record(address)
        if not row:
            raise TorPrivacyError("onion address has not been observed")
        availability = await self.check_availability(address)
        claimed = str(row.claimed_operator or "").lower()
        impersonation = [term for term in BRAND_TERMS if term in claimed]
        sources = len(row.source_urls or [])
        status = (
            "suspicious" if impersonation
            else "observed" if availability.get("reachable") and sources >= 2
            else "unknown"
        )
        assessment = {
            "status": status,
            "availability": availability,
            "impersonation_terms": impersonation,
            "independent_sources": sources,
            "confidence": "low",
            "note": "reachability never establishes operator trust",
        }
        row.status = status  # type: ignore[assignment]
        row.availability = availability  # type: ignore[assignment]
        row.assessment = assessment  # type: ignore[assignment]
        row.updated_at = datetime.now(timezone.utc)  # type: ignore[assignment]
        await self.db.commit()
        if task_id:
            await self.evidence.append_audit(
                task_id, actor=actor, action="tor.onion.assess", target=address,
                outcome={"status": status, "reachable": bool(availability.get("reachable"))},
            )
        return assessment

    @staticmethod
    def _row(row: OnionReputation) -> Dict[str, Any]:
        return {
            "address": row.address,
            "claimed_operator": row.claimed_operator,
            "status": row.status,
            "source_urls": row.source_urls,
            "availability": row.availability,
            "assessment": row.assessment,
        }


class TorFilePipeline:
    """Quarantine → legal gate → explicit approval. Never executes a file."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.gateway = BrowserSecurityGateway(db)

    async def process(
        self,
        source_path: str,
        *,
        original_name: str = "",
        licence_source_id: Optional[str] = None,
        task_id: Optional[str] = None,
        actor: str = "sdk",
    ) -> Dict[str, Any]:
        quarantined = await self.gateway.quarantine_download(
            source_path,
            original_name=original_name,
            task_id=task_id,
            actor=actor,
        )
        legal = await IPLCIService(db=self.db).gate_check(
            {"operation": "store", "source_id": licence_source_id},
            actor=actor,
        )
        decision = str(legal.get("decision") or "BLOCKED")
        result = {
            **quarantined,
            "licence_decision": decision,
            "status": "quarantined",
            "executed": False,
            "note": "release requires signed Creator approval",
        }
        if task_id:
            await self.gateway.evidence.append_audit(
                task_id, actor=actor, action="tor.file.process",
                target=original_name or source_path,
                outcome={"sha256": quarantined["sha256"],
                         "licence_decision": decision, "executed": False},
            )
        return result


class TorCreatorControls:
    """Creator-only policy controls for Tor and onion access."""

    def __init__(self, manager: TorManager):
        self.manager = manager

    def policy(self) -> Dict[str, Any]:
        return {
            "tor_enabled": settings.tor_enabled,
            "onion_access_enabled": settings.tor_onion_access_enabled,
            "bandwidth_limit_kbps": settings.tor_bandwidth_limit_kbps,
            "session_ttl_seconds": settings.tor_session_ttl_seconds,
            "bridge_configured": settings.tor_bridge_configured,
            "kill_switch": self.manager.privacy.kill_switch,
        }

    def set_onion_access(self, enabled: bool, actor: str) -> Dict[str, Any]:
        settings.tor_onion_access_enabled = bool(enabled)
        return {"onion_access_enabled": bool(enabled), "changed_by": actor}

    def suspend_onion_access(self, actor: str) -> Dict[str, Any]:
        settings.tor_onion_access_enabled = False
        return {"onion_access_enabled": False, "suspended_by": actor}

    def set_bandwidth_limit(self, kbps: int, actor: str) -> Dict[str, Any]:
        if kbps < 0:
            raise TorPrivacyError("bandwidth limit cannot be negative")
        settings.tor_bandwidth_limit_kbps = int(kbps)
        return {"bandwidth_limit_kbps": int(kbps), "changed_by": actor}

    def set_session_duration(self, seconds: int, actor: str) -> Dict[str, Any]:
        if seconds < 60 or seconds > 86400:
            raise TorPrivacyError("session duration must be between 60 and 86400 seconds")
        settings.tor_session_ttl_seconds = int(seconds)
        return {"session_ttl_seconds": int(seconds), "changed_by": actor}

    def view_sessions(self) -> List[Dict[str, Any]]:
        return [
            {key: value for key, value in session.items() if key != "handle"}
            for session in self.manager.sessions.values()
        ]


class TorEmergencyController:
    """Immediate stop, credential isolation and crash recovery."""

    def __init__(self, manager: TorManager):
        self.manager = manager

    async def stop(self, actor: str, task_id: Optional[str] = None) -> Dict[str, Any]:
        result = await self.manager.terminate_all(actor=actor)
        controls = TorCreatorControls(self.manager)
        onion = controls.suspend_onion_access(actor)
        result.update({
            "onion_access": onion["onion_access_enabled"],
            "credential_isolation": True,
            "fallback_to_standard_browser": False,
        })
        if task_id:
            await self.manager.evidence.append_audit(
                task_id, actor=actor, actor_type="creator",
                action="tor.emergency.stop", target="tor",
                outcome=result,
            )
        return result

    async def cleanup_after_crash(self) -> Dict[str, Any]:
        await self.manager._reap_expired()
        root = self.manager._profile_root()
        removed = 0
        now = datetime.now(timezone.utc)
        for profile in root.iterdir():
            if not profile.is_dir() or profile.name in self.manager.sessions:
                continue
            age = (now - datetime.fromtimestamp(profile.stat().st_mtime, timezone.utc)).total_seconds()
            if age > settings.tor_session_ttl_seconds:
                shutil.rmtree(profile, ignore_errors=True)
                removed += 1
        return {"profiles_removed": removed, "active_sessions": len(self.manager.sessions)}

    async def suspicious_connections(self) -> Dict[str, Any]:
        health = await self.manager.monitor.health()
        reasons: List[str] = []
        if health.get("control_port") and not health.get("socks_port"):
            reasons.append("control port reachable but SOCKS port unavailable")
        if len(self.manager.sessions) > settings.tor_max_concurrent_sessions:
            reasons.append("session count exceeds configured limit")
        return {"suspicious": bool(reasons), "reasons": reasons}
