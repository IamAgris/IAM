"""Database-backed Skill Forge registry, lifecycle and creator approval gateway."""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.capability import CapabilityAssessment, CapabilityDefinition
from app.models.skillforge import (
    SkillAuditEvent,
    SkillPackage,
    SkillPermissionGrant,
    SkillTestResult,
    SkillVersion,
)
from app.services.creatorapproval_service import CreatorApprovalService
from app.services.skillforge.engine import EngineError, SkillBuildRequest, SkillForgeEngine
from app.services.skillforge.manifest import (
    ManifestError,
    SkillManifest,
    validate_manifest,
)
from app.services.skillforge.permissions import PermissionDenied


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: Optional[datetime]) -> Optional[str]:
    return value.isoformat() if value else None


def _version_tuple(version: str) -> Tuple[int, ...]:
    return tuple(int(p) for p in version.split("."))


class SkillForgeService:
    """Owns the registry, state machine, approvals and audit trail."""

    def __init__(self, db: AsyncSession, root: Optional[Path] = None):
        self.db = db
        self.engine = SkillForgeEngine(root=root)
        self.permissions = self.engine.permissions

    # ------------------------------------------------------------------ helpers

    async def _get(self, skill_id: str) -> Optional[SkillPackage]:
        result = await self.db.execute(
            select(SkillPackage).where(SkillPackage.skill_id == skill_id)
        )
        return result.scalar_one_or_none()

    async def _require(self, skill_id: str) -> SkillPackage:
        package = await self._get(skill_id)
        if not package:
            raise LookupError(f"Skill not found: {skill_id}")
        return package

    def _to_dict(self, package: SkillPackage) -> Dict[str, Any]:
        return {
            "id": str(package.id),
            "skill_id": package.skill_id,
            "name": package.name,
            "description": package.description,
            "origin": package.origin,
            "provider": package.provider,
            "category": package.category,
            "classification": package.classification,
            "status": package.status,
            "version": package.version,
            "permissions": package.permissions or [],
            "network_access": package.network_access,
            "filesystem_access": package.filesystem_access,
            "requires_creator_approval": package.requires_creator_approval,
            "path": package.path,
            "checksum": package.checksum,
            "created_by": package.created_by,
            "approved_by": package.approved_by,
            "approved_at": _iso(package.approved_at),  # type: ignore[arg-type]
            "published_at": _iso(package.published_at),  # type: ignore[arg-type]
            "activated_at": _iso(package.activated_at),  # type: ignore[arg-type]
            "created_at": _iso(package.created_at),  # type: ignore[arg-type]
            "updated_at": _iso(package.updated_at),  # type: ignore[arg-type]
        }

    async def _audit(
        self,
        action: str,
        *,
        package_id: Optional[str] = None,
        actor: str = "iam",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.db.add(
            SkillAuditEvent(
                package_id=package_id,
                action=action,
                actor=actor,
                details=details or {},
            )
        )

    async def _tests_passed(self, package: SkillPackage) -> bool:
        result = await self.db.execute(
            select(SkillTestResult).where(
                SkillTestResult.package_id == package.id,
                SkillTestResult.version == package.version,
            )
        )
        tests = result.scalars().all()
        required = {"manifest", "functional", "security"}
        if {t.test_type for t in tests} < required:
            return False
        return all(t.passed for t in tests)

    @staticmethod
    def _manifest(package: SkillPackage) -> SkillManifest:
        return validate_manifest(package.manifest)  # type: ignore[arg-type]

    # ------------------------------------------------------------------ creation

    async def create(self, request: SkillBuildRequest) -> Dict[str, Any]:
        """Build a skill and register it, or publish a new version of an existing one."""
        existing = await self._get(request.skill_id)
        if existing:
            if _version_tuple(request.version) <= _version_tuple(existing.version):  # type: ignore[arg-type]
                raise ValueError(
                    f"new version {request.version} must be greater than {existing.version}"
                )
            built = self.engine.create_version(
                request.skill_id, request, previous_version=existing.version  # type: ignore[arg-type]
            )
            manifest = validate_manifest(built["manifest"])
            existing.name = manifest.name  # type: ignore[assignment]
            existing.description = manifest.description  # type: ignore[assignment]
            existing.classification = manifest.classification  # type: ignore[assignment]
            existing.version = manifest.version  # type: ignore[assignment]
            existing.manifest = manifest.to_dict()  # type: ignore[assignment]
            existing.permissions = manifest.permissions  # type: ignore[assignment]
            existing.network_access = manifest.network_access  # type: ignore[assignment]
            existing.filesystem_access = manifest.filesystem_access  # type: ignore[assignment]
            existing.requires_creator_approval = manifest.requires_creator_approval  # type: ignore[assignment]
            existing.checksum = built["checksum"]
            existing.approved_by = None  # type: ignore[assignment]
            existing.approved_at = None  # type: ignore[assignment]
            existing.status = "testing"  # type: ignore[assignment]
            # Prior test evidence is keyed by version, so it no longer applies.
            for version_row in (
                await self.db.execute(
                    select(SkillVersion).where(SkillVersion.package_id == existing.id)
                )
            ).scalars().all():
                version_row.is_current = False  # type: ignore[assignment]
            self.db.add(
                SkillVersion(
                    package_id=existing.id,
                    version=manifest.version,
                    manifest=manifest.to_dict(),
                    permissions=manifest.permissions,
                    checksum=built["checksum"],
                    change_note=request.change_note,
                    is_current=True,
                )
            )
            await self._audit(
                "version_created",
                package_id=str(existing.id),
                actor=request.created_by,
                details={"from": request.version, "to": manifest.version},
            )
            await self.db.commit()
            await self.db.refresh(existing)
            result = self._to_dict(existing)
            result["findings"] = built["findings"]
            return result

        built = self.engine.build(request)
        manifest = validate_manifest(built["manifest"])
        kind = "native" if manifest.origin == "native" else "imported"
        parts = manifest.id.split(".")
        category = parts[3] if kind == "imported" and len(parts) > 3 else (
            parts[2] if len(parts) > 2 else None
        )
        package = SkillPackage(
            skill_id=manifest.id,
            name=manifest.name,
            description=manifest.description,
            origin=kind,
            provider=manifest.provider,
            category=category,
            classification=manifest.classification,
            # Imported candidates are staged on disk but remain 'draft' in the
            # registry until they pass tests and creator approval.
            status="draft",
            version=manifest.version,
            manifest=manifest.to_dict(),
            permissions=manifest.permissions,
            network_access=manifest.network_access,
            filesystem_access=manifest.filesystem_access,
            requires_creator_approval=manifest.requires_creator_approval,
            path=built["path"],
            checksum=built["checksum"],
            created_by=request.created_by,
        )
        self.db.add(package)
        await self.db.flush()
        self.db.add(
            SkillVersion(
                package_id=package.id,
                version=manifest.version,
                manifest=manifest.to_dict(),
                permissions=manifest.permissions,
                checksum=built["checksum"],
                change_note=request.change_note or "initial version",
                is_current=True,
            )
        )
        await self._audit(
            "skill_created",
            package_id=str(package.id),
            actor=request.created_by,
            details={"origin": kind, "staged": built["staged"]},
        )
        await self.db.commit()
        await self.db.refresh(package)
        result = self._to_dict(package)
        result["findings"] = built["findings"]
        return result

    # ------------------------------------------------------------------ queries

    async def list_skills(
        self, status: Optional[str] = None, origin: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        query = select(SkillPackage)
        if status:
            query = query.where(SkillPackage.status == status)
        if origin:
            query = query.where(SkillPackage.origin == origin)
        query = query.order_by(SkillPackage.created_at.desc())
        result = await self.db.execute(query)
        return [self._to_dict(p) for p in result.scalars().all()]

    async def get(self, skill_id: str) -> Dict[str, Any]:
        return self._to_dict(await self._require(skill_id))

    async def versions(self, skill_id: str) -> List[Dict[str, Any]]:
        package = await self._require(skill_id)
        result = await self.db.execute(
            select(SkillVersion)
            .where(SkillVersion.package_id == package.id)
            .order_by(SkillVersion.created_at.desc())
        )
        return [
            {
                "id": str(v.id),
                "version": v.version,
                "manifest": v.manifest,
                "checksum": v.checksum,
                "change_note": v.change_note,
                "is_current": v.is_current,
                "created_at": _iso(v.created_at),  # type: ignore[arg-type]
            }
            for v in result.scalars().all()
        ]

    async def audit(self, skill_id: str) -> List[Dict[str, Any]]:
        package = await self._require(skill_id)
        result = await self.db.execute(
            select(SkillAuditEvent)
            .where(SkillAuditEvent.package_id == package.id)
            .order_by(SkillAuditEvent.created_at.desc())
        )
        return [
            {
                "id": str(e.id),
                "action": e.action,
                "actor": e.actor,
                "details": e.details,
                "created_at": _iso(e.created_at),  # type: ignore[arg-type]
            }
            for e in result.scalars().all()
        ]

    async def test_history(self, skill_id: str) -> List[Dict[str, Any]]:
        package = await self._require(skill_id)
        result = await self.db.execute(
            select(SkillTestResult)
            .where(SkillTestResult.package_id == package.id)
            .order_by(SkillTestResult.executed_at.desc())
        )
        return [
            {
                "id": str(t.id),
                "version": t.version,
                "test_type": t.test_type,
                "passed": t.passed,
                "details": t.details,
                "executed_at": _iso(t.executed_at),  # type: ignore[arg-type]
            }
            for t in result.scalars().all()
        ]

    # ------------------------------------------------------------------ lifecycle

    async def validate(self, skill_id: str) -> Dict[str, Any]:
        package = await self._require(skill_id)
        result = self.engine.validate(skill_id)
        if not result["valid"]:
            # Rule 7: failed or suspicious skills are isolated immediately.
            if package.status != "quarantined":
                self.permissions.require_transition(package.status, "quarantined")  # type: ignore[arg-type]
                package.status = "quarantined"  # type: ignore[assignment]
                package.path = self.engine.quarantine(skill_id)  # type: ignore[assignment]
            await self._audit(
                "validation_failed",
                package_id=str(package.id),
                details={"findings": result["findings"]},
            )
        else:
            package.checksum = result.get("checksum") or package.checksum
            await self._audit("validation_passed", package_id=str(package.id))
        await self.db.commit()
        return result

    async def test(self, skill_id: str) -> Dict[str, Any]:
        package = await self._require(skill_id)
        if package.status == "quarantined":
            raise PermissionDenied("Quarantined skills cannot be tested until reviewed")
        self.permissions.require_transition(package.status, "testing")  # type: ignore[arg-type]
        results = self.engine.run_tests(skill_id)
        for item in results:
            self.db.add(
                SkillTestResult(
                    package_id=package.id,
                    version=package.version,
                    test_type=item["test_type"],
                    passed=item["passed"],
                    details=item["details"],
                )
            )
        package.status = "testing"  # type: ignore[assignment]
        await self._audit(
            "tests_run",
            package_id=str(package.id),
            details={"passed": all(r["passed"] for r in results)},
        )
        await self.db.commit()
        return {"skill_id": skill_id, "version": package.version, "results": results}

    async def request_approval(
        self, skill_id: str, reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """Creator Approval Gateway: send an explanatory email, not a UI approval.

        OD-19: no Creator dashboard. Email carries the request; authority is only
        created later by a verified signed challenge.
        """
        package = await self._require(skill_id)
        manifest = self._manifest(package)
        level = self.permissions.level(manifest.classification)
        request = await CreatorApprovalService(self.db).create_request(
            action_type="skillforge.publish",
            summary=f"Publish skill {skill_id} ({manifest.name} v{manifest.version})",
            consequences=[
                "Skill becomes publishable within its declared permissions",
                "Skill can be activated only through the normal runtime gates",
            ],
            risk_level=str(level),
            target_ref=skill_id,
            reason=reason,
        )
        await self._audit(
            "creator_approval_requested",
            package_id=str(package.id),
            details={"request_id": request["request_id"]},
        )
        await self.db.commit()
        return request

    async def publish(self, skill_id: str) -> Dict[str, Any]:
        package = await self._require(skill_id)
        manifest = self._manifest(package)
        level = self.permissions.level(manifest.classification)

        # Ordinary skills (levels 1-2) remain self-publishable — rule 1.
        signer_id = None
        authorization = None
        if level >= 3:
            authorization = await CreatorApprovalService(self.db).check_authorization(
                "skillforge.publish", str(level), target_ref=skill_id
            )
            if not authorization["authorized"]:
                raise PermissionDenied(authorization["reason"])
            signer_id = authorization["signer_id"]

        self.permissions.require_publish_authority(
            manifest,
            approved_by=signer_id,
            tests_passed=await self._tests_passed(package),
            signed_authorization=authorization,
        )
        if signer_id:
            package.approved_by = signer_id
            package.approved_at = _now()  # type: ignore[assignment]

        if package.origin == "imported" and package.path and package.path.startswith("pending/"):
            package.path = self.engine.promote(skill_id)  # type: ignore[assignment]

        self.permissions.require_transition(package.status, "published")  # type: ignore[arg-type]
        package.status = "published"  # type: ignore[assignment]
        package.published_at = _now()  # type: ignore[assignment]
        await self._audit("skill_published", package_id=str(package.id))
        await self.db.commit()
        await self.db.refresh(package)
        return self._to_dict(package)

    async def activate(self, skill_id: str) -> Dict[str, Any]:
        package = await self._require(skill_id)
        manifest = self._manifest(package)
        self.permissions.require_activation_authority(
            manifest, status=package.status, approved_by=package.approved_by  # type: ignore[arg-type]
        )
        self.permissions.require_transition(package.status, "active")  # type: ignore[arg-type]
        package.status = "active"  # type: ignore[assignment]
        package.activated_at = _now()  # type: ignore[assignment]
        await self._audit("skill_activated", package_id=str(package.id))
        await self.db.commit()
        await self.db.refresh(package)
        return self._to_dict(package)

    async def quarantine(self, skill_id: str, reason: str = "manual") -> Dict[str, Any]:
        package = await self._require(skill_id)
        self.permissions.require_transition(package.status, "quarantined")  # type: ignore[arg-type]
        package.path = self.engine.quarantine(skill_id)  # type: ignore[assignment]
        package.status = "quarantined"  # type: ignore[assignment]
        package.activated_at = None  # type: ignore[assignment]
        await self._audit(
            "skill_quarantined", package_id=str(package.id), details={"reason": reason}
        )
        await self.db.commit()
        await self.db.refresh(package)
        return self._to_dict(package)

    async def rollback(self, skill_id: str, version: str) -> Dict[str, Any]:
        package = await self._require(skill_id)
        result = await self.db.execute(
            select(SkillVersion).where(
                SkillVersion.package_id == package.id,
                SkillVersion.version == version,
            )
        )
        target = result.scalar_one_or_none()
        if not target:
            raise LookupError(f"Version {version} not found for {skill_id}")
        if version == package.version:
            raise ValueError("version is already current")

        restored_path = self.engine.restore(skill_id, version)
        restored_manifest = validate_manifest(target.manifest)  # type: ignore[arg-type]
        previous_version = package.version
        previous_status = package.status
        package.version = version  # type: ignore[assignment]
        package.manifest = target.manifest
        package.permissions = target.manifest.get("permissions", [])
        package.network_access = target.manifest.get("network_access", False)
        package.filesystem_access = target.manifest.get("filesystem_access", "none")
        package.requires_creator_approval = target.manifest.get(
            "requires_creator_approval", False
        )
        package.classification = restored_manifest.classification  # type: ignore[assignment]
        package.checksum = target.checksum
        package.path = restored_path  # type: ignore[assignment]
        package.status = "active" if previous_status == "active" else "published"  # type: ignore[assignment]

        versions = (
            await self.db.execute(
                select(SkillVersion).where(SkillVersion.package_id == package.id)
            )
        ).scalars().all()
        for row in versions:
            row.is_current = row.version == version  # type: ignore[assignment]
        await self._audit(
            "skill_rolled_back",
            package_id=str(package.id),
            details={"from": previous_version, "to": version},
        )
        await self.db.commit()
        await self.db.refresh(package)
        return self._to_dict(package)

    # ------------------------------------------------------------------ runtime authority

    async def grants(self, skill_id: str) -> List[Dict[str, Any]]:
        package = await self._require(skill_id)
        result = await self.db.execute(
            select(SkillPermissionGrant).where(
                SkillPermissionGrant.package_id == package.id,
                SkillPermissionGrant.is_active == True,  # noqa: E712
            )
        )
        return [
            {
                "id": str(g.id),
                "permission": g.permission,
                "granted_by": g.granted_by,
                "reason": g.reason,
                "created_at": _iso(g.created_at),  # type: ignore[arg-type]
            }
            for g in result.scalars().all()
        ]

    async def grant(
        self,
        skill_id: str,
        permission: str,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """A signed Creator authorization issues an explicit, skill-scoped grant."""
        package = await self._require(skill_id)
        manifest = self._manifest(package)
        auth = await CreatorApprovalService(self.db).check_authorization(
            "skillforge.grant", "4", target_ref=skill_id
        )
        if not auth["authorized"]:
            raise PermissionDenied(auth["reason"])
        granted_by = auth["signer_id"]
        capability_grants = {"network_access", "filesystem_full"}
        if permission in capability_grants:
            enabled = (
                manifest.network_access
                if permission == "network_access"
                else manifest.filesystem_access == "full"
            )
            if not enabled:
                raise PermissionDenied("Skill manifest does not request that capability")
        elif permission not in manifest.permissions:
            raise PermissionDenied("Grant must correspond to a permission declared by the skill")
        self.db.add(
            SkillPermissionGrant(
                package_id=package.id,
                permission=permission,
                granted_by=granted_by,
                reason=reason,
            )
        )
        await self._audit(
            "permission_granted",
            package_id=str(package.id),
            actor=granted_by,
            details={"permission": permission},
        )
        await self.db.commit()
        return {"skill_id": skill_id, "permission": permission, "granted": True}

    async def revoke(self, skill_id: str, permission: str) -> Dict[str, Any]:
        auth = await CreatorApprovalService(self.db).check_authorization(
            "skillforge.grant", "4", target_ref=skill_id
        )
        if not auth["authorized"]:
            raise PermissionDenied(auth["reason"])
        package = await self._require(skill_id)
        result = await self.db.execute(
            select(SkillPermissionGrant).where(
                SkillPermissionGrant.package_id == package.id,
                SkillPermissionGrant.permission == permission,
                SkillPermissionGrant.is_active == True,  # noqa: E712
            )
        )
        grants = result.scalars().all()
        if not grants:
            raise LookupError("Active grant not found")
        for grant in grants:
            grant.is_active = False  # type: ignore[assignment]
        await self._audit(
            "permission_revoked",
            package_id=str(package.id),
            actor=auth["signer_id"],
            details={"permission": permission},
        )
        await self.db.commit()
        return {"skill_id": skill_id, "permission": permission, "revoked": True}

    async def effective_permissions(self, skill_id: str) -> Dict[str, Any]:
        """The runtime's authoritative view of a skill's authority."""
        package = await self._require(skill_id)
        manifest = self._manifest(package)
        active_grants = await self.grants(skill_id)
        granted = [g["permission"] for g in active_grants]
        network_grant = "network_access" in granted
        return {
            "skill_id": skill_id,
            "classification": manifest.classification,
            "permissions": self.permissions.effective_permissions(manifest, granted),
            "network_access": self.permissions.can_use_network(
                manifest, granted=network_grant
            ),
            "filesystem_access": manifest.filesystem_access,
            "filesystem_full_granted": "filesystem_full" in granted,
            "status": package.status,
        }

    # ------------------------------------------------------------------ discovery

    async def discover_gaps(self) -> List[Dict[str, Any]]:
        """Capability Discovery: find learnable areas without demonstrated proficiency."""
        capabilities = (
            await self.db.execute(
                select(CapabilityDefinition).where(CapabilityDefinition.is_learnable == True)  # noqa: E712
            )
        ).scalars().all()
        assessments = (
            await self.db.execute(select(CapabilityAssessment))
        ).scalars().all()
        latest: Dict[str, Any] = {}
        for assessment in assessments:
            key = str(assessment.capability_id)
            if key not in latest or assessment.assessed_at > latest[key][0]:
                latest[key] = (assessment.assessed_at, assessment.proficiency_level)

        gaps = []
        for capability in capabilities:
            current = latest.get(str(capability.id), (None, 0))[1]
            gap = capability.target_proficiency - current
            if gap > 0:
                gaps.append(
                    {
                        "capability": capability.name,
                        "category": capability.category,
                        "current_proficiency": current,
                        "target_proficiency": capability.target_proficiency,
                        "gap": gap,
                        "suggested_skill_id": "iam.native."
                        + capability.category
                        + "."
                        + re_safe(capability.name),  # type: ignore[arg-type]
                    }
                )
        return sorted(gaps, key=lambda g: g["gap"], reverse=True)


def re_safe(value: str) -> str:
    """Turn a capability name into a skill-id-safe token."""
    import re

    token = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return token or "skill"
