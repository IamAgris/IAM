"""Skill Runtime service — gates and records skill execution.

No package is executed unless it is active, its files match the recorded
checksum, the requested permission is in the runtime's effective permission set,
and the script passes a final static inspection.
"""

from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.rate_limit import RateLimiter, RedisRateLimiter
from app.models.skillforge import SkillPackage
from app.models.security import AuditEvent
from app.models.skillruntime import SkillRuntimeExecution, SkillRuntimeLog
from app.services.skillforge.permissions import PermissionDenied
from app.services.skillforge.service import SkillForgeService
from app.services.skillruntime.adapters import (
    ExecutionPlan,
    SkillRuntimeAdapterError,
    adapter_for,
)


class SkillRuntimeError(PermissionError):
    """Raised when a skill cannot be safely invoked."""


class SkillRuntimeRateLimited(SkillRuntimeError):
    """Raised when a skill has exceeded its per-skill invocation budget."""


_skill_limiters: Dict[str, RateLimiter] = {}
_shared_limiters: Dict[str, RedisRateLimiter] = {}


def audit_log_chunks(
    stream: str, content: str, chunk_size: Optional[int] = None
) -> List[Dict[str, Any]]:
    """Split execution output into bounded audit events without losing bytes."""
    size = max(1, chunk_size or settings.skill_runtime_audit_log_chunk_chars)
    return [
        {
            "event_type": "skill_runtime_log",
            "stream": stream,
            "sequence": index,
            "content": content[start : start + size],
        }
        for index, start in enumerate(range(0, len(content), size))
    ]


async def check_invocation_limit(skill_id: str, caller: str) -> bool:
    """Enforce the per-skill budget locally or across replicas via Redis."""
    key = f"skill-runtime:{skill_id}:{caller}"
    if settings.rate_limit_backend.lower() == "redis":
        limiter = _shared_limiters.setdefault(
            caller,
            RedisRateLimiter(
                settings.redis_url, settings.skill_runtime_per_skill_limit_per_minute
            ),
        )
        allowed, _ = await limiter.check(key)
        return bool(allowed)
    limiter = _skill_limiters.setdefault(
        caller, RateLimiter(settings.skill_runtime_per_skill_limit_per_minute)
    )
    allowed, _ = limiter.check(key)
    return bool(allowed)


class SkillRuntimeService:
    def __init__(self, db: AsyncSession, root: Optional[Path] = None):
        self.db = db
        self.forge = SkillForgeService(db, root=root)
        self.layout = self.forge.engine.layout

    async def _package(self, skill_id: str) -> SkillPackage:
        result = await self.db.execute(
            select(SkillPackage).where(SkillPackage.skill_id == skill_id)
        )
        package = result.scalar_one_or_none()
        if not package:
            raise LookupError(f"Skill not found: {skill_id}")
        return package

    async def _record(
        self,
        *,
        skill_id: str,
        permission: str,
        script: Optional[str],
        caller: str,
        adapter: str,
        status: str,
        dry_run: bool,
        result: Dict[str, Any],
        error: Optional[str] = None,
        network: bool = False,
    ) -> str:
        execution = SkillRuntimeExecution(
            skill_id=skill_id,
            permission=permission,
            script=script,
            caller=caller,
            adapter=adapter,
            status=status,
            dry_run=dry_run,
            result=result,
            error=error,
            completed_at=datetime.now(timezone.utc),
        )
        self.db.add(execution)
        await self.db.flush()
        self.db.add(
            AuditEvent(
                event_type="skill_runtime_invocation",
                actor=caller,
                target=str(execution.id),
                details={
                    "skill_id": skill_id,
                    "permission": permission,
                    "adapter": adapter,
                    "status": status,
                    "network": "isolated" if network else "none",
                    "error": error,
                },
            )
        )
        return str(execution.id)

    async def capabilities(self, skill_id: str) -> Dict[str, Any]:
        """The authoritative runtime view of a skill's authority."""
        package = await self._package(skill_id)
        return dict(await self.forge.effective_permissions(skill_id)) | {
            "status": package.status,
        }

    async def invoke(
        self,
        skill_id: str,
        *,
        permission: str,
        script: Optional[str] = None,
        arguments: Optional[Dict[str, Any]] = None,
        caller: str = "iam",
        governance_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        from app.services.iplci.context import resolve_governance_context
        from app.services.iplci.gateway import GovernanceRefusal
        from app.services.iplci.integration import enforce_agent_request

        resolved = resolve_governance_context(governance_context)
        if resolved:
            try:
                await enforce_agent_request(
                    self.db,
                    action="skill.invoke",
                    source_id=resolved["source_id"],
                    agent_id=str(resolved.get("agent_id") or caller),
                    jurisdiction=resolved.get("jurisdiction"),
                )
            except GovernanceRefusal as exc:
                raise SkillRuntimeError(f"IPLCI governance refused skill invocation: {exc}")
        adapter_name = settings.skill_runtime_adapter
        arguments = arguments or {}
        try:
            if not settings.skill_runtime_enabled:
                raise SkillRuntimeError("Skill Runtime is disabled")

            if not await check_invocation_limit(skill_id, caller):
                raise SkillRuntimeRateLimited(
                    "per-skill invocation limit exceeded; retry shortly"
                )

            package = await self._package(skill_id)
            if package.status != "active":
                raise SkillRuntimeError(
                    f"Skill must be active before execution (current: {package.status})"
                )

            effective = await self.forge.effective_permissions(skill_id)
            if permission not in effective["permissions"]:
                raise SkillRuntimeError(
                    f"Permission '{permission}' is not in the skill's effective permissions"
                )
            network_access = bool(effective["network_access"])
            configured_network = (
                settings.skill_runtime_network_name
                if settings.skill_runtime_network_enabled
                else None
            )
            if network_access and not configured_network:
                raise SkillRuntimeError(
                    "skill requires network_access but no restricted network is configured"
                )

            expected = package.checksum
            actual = self.layout.checksum(skill_id)
            if expected and actual != expected:
                raise SkillRuntimeError("Skill package checksum mismatch — refusing execution")

            directory = self.layout.current_dir(skill_id)
            if not isinstance(directory, Path):
                raise SkillRuntimeError("skill layout returned no package directory")
            if script:
                path = Path(script)
                if path.is_absolute() or path.parts[0] != "scripts" or any(
                    p in {".", ".."} for p in path.parts
                ):
                    raise SkillRuntimeError("script must be a relative path under scripts/")
                resolved = (directory / path).resolve()
                if directory not in resolved.parents or not resolved.is_file():
                    raise SkillRuntimeError("script does not exist inside the skill package")
                findings = self.forge.engine.security.scan_text(
                    resolved.read_text(encoding="utf-8", errors="replace"), script
                )
                if self.forge.engine.security.has_blocking_findings(findings):
                    raise SkillRuntimeError("script failed security inspection")
        except (SkillRuntimeError, PermissionDenied) as exc:
            execution_id = await self._record(
                skill_id=skill_id,
                permission=permission,
                script=script,
                caller=caller,
                adapter=adapter_name,
                status="denied",
                dry_run=True,
                result={},
                error=str(exc),
                network=bool(locals().get("network_access", False)),
            )
            await self.db.commit()
            raise SkillRuntimeError(str(exc)) from exc

        plan = ExecutionPlan(
            skill_id=skill_id,
            skill_dir=directory,
            script=script,
            arguments=arguments,
            network=network_access,
            network_name=configured_network if network_access else None,
            filesystem=effective["filesystem_access"],
            checksum=actual,
        )
        adapter = adapter_for(adapter_name)
        try:
            outcome = await adapter.execute(plan)
        except SkillRuntimeAdapterError as exc:
            await self._record(
                skill_id=skill_id,
                permission=permission,
                script=script,
                caller=caller,
                adapter=adapter_name,
                status="failed",
                dry_run=adapter_name != "docker",
                result={},
                error=str(exc),
                network=network_access,
            )
            await self.db.commit()
            raise SkillRuntimeError(str(exc)) from exc

        execution_id = await self._record(
            skill_id=skill_id,
            permission=permission,
            script=script,
            caller=caller,
            adapter=adapter_name,
            status=outcome["status"],
            dry_run=bool(outcome.get("dry_run")),
            result=outcome,
            network=network_access,
        )
        for stream in ("stdout", "stderr"):
            content = str(outcome.get(stream) or "")
            if not content:
                continue
            # Full output goes to the durable audit trail in bounded chunks;
            # the runtime table keeps only a preview for fast UI reads.
            for chunk in audit_log_chunks(stream, content):
                self.db.add(
                    AuditEvent(
                        event_type=chunk["event_type"],
                        actor=caller,
                        target=execution_id,
                        details={
                            "skill_id": skill_id,
                            "execution_id": execution_id,
                            "stream": chunk["stream"],
                            "sequence": chunk["sequence"],
                            "content": chunk["content"],
                        },
                    )
                )
            self.db.add(
                SkillRuntimeLog(
                    execution_id=UUID(execution_id),
                    stream=stream,
                    content=content[: settings.skill_runtime_max_log_chars],
                )
            )
        await self.db.commit()
        return {
            "skill_id": skill_id,
            "permission": permission,
            "effective_permissions": effective,
            "execution_id": execution_id,
            "execution": outcome,
        }

    async def executions(self, skill_id: Optional[str] = None) -> List[Dict[str, Any]]:
        query = select(SkillRuntimeExecution)
        if skill_id:
            query = query.where(SkillRuntimeExecution.skill_id == skill_id)
        query = query.order_by(SkillRuntimeExecution.created_at.desc())
        result = await self.db.execute(query)
        return [
            {
                "id": str(e.id),
                "skill_id": e.skill_id,
                "permission": e.permission,
                "script": e.script,
                "caller": e.caller,
                "adapter": e.adapter,
                "status": e.status,
                "dry_run": e.dry_run,
                "result": e.result,
                "error": e.error,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in result.scalars().all()
        ]

    async def logs(self, execution_id: str) -> List[Dict[str, Any]]:
        result = await self.db.execute(
            select(SkillRuntimeLog)
            .where(SkillRuntimeLog.execution_id == UUID(execution_id))
            .order_by(SkillRuntimeLog.id.asc())
        )
        return [
            {"stream": row.stream, "content": row.content}
            for row in result.scalars().all()
        ]
