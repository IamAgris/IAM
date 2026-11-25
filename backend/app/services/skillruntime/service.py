"""Skill Runtime service — gates and records skill execution.

No package is executed unless it is active, its files match the recorded
checksum, the requested permission is in the runtime's effective permission set,
and the script passes a final static inspection.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.skillforge import SkillPackage
from app.models.skillruntime import SkillRuntimeExecution
from app.services.skillforge.permissions import PermissionDenied
from app.services.skillforge.service import SkillForgeService
from app.services.skillruntime.adapters import (
    ExecutionPlan,
    SkillRuntimeAdapterError,
    adapter_for,
)


class SkillRuntimeError(PermissionError):
    """Raised when a skill cannot be safely invoked."""


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
        return str(execution.id)

    async def capabilities(self, skill_id: str) -> Dict[str, Any]:
        """The authoritative runtime view of a skill's authority."""
        package = await self._package(skill_id)
        return await self.forge.effective_permissions(skill_id) | {
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
    ) -> Dict[str, Any]:
        adapter_name = settings.skill_runtime_adapter
        arguments = arguments or {}
        try:
            if not settings.skill_runtime_enabled:
                raise SkillRuntimeError("Skill Runtime is disabled")
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
            if effective["network_access"]:
                raise SkillRuntimeError(
                    "Network-enabled skill execution is not enabled in this deployment"
                )

            expected = package.checksum
            actual = self.layout.checksum(skill_id)
            if expected and actual != expected:
                raise SkillRuntimeError("Skill package checksum mismatch — refusing execution")

            directory = self.layout.current_dir(skill_id)
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
            )
            await self.db.commit()
            raise SkillRuntimeError(str(exc)) from exc

        plan = ExecutionPlan(
            skill_id=skill_id,
            skill_dir=directory,
            script=script,
            arguments=arguments,
            network=False,
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
