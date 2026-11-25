"""Skill Forge Engine — build, inspect, test and version skill packages."""

from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.core.config import settings
from app.services.skillforge.layout import LayoutError, SkillLayout
from app.services.skillforge.manifest import (
    ManifestError,
    SkillManifest,
    validate_manifest,
)
from app.services.skillforge.permissions import PermissionDenied, PermissionManager
from app.services.skillforge.security import Finding, SecurityValidator


class SkillBuildRequest(BaseModel):
    """Input for building a native or imported skill package."""

    skill_id: str
    name: str = Field(min_length=1, max_length=120)
    version: str = "1.0.0"
    description: Optional[str] = None
    classification: str = "personal"
    permissions: List[str] = Field(default_factory=list)
    network_access: bool = False
    filesystem_access: str = "none"
    requires_creator_approval: bool = False
    instructions: str = Field(min_length=1)
    resources: Dict[str, str] = Field(default_factory=dict)
    scripts: Dict[str, str] = Field(default_factory=dict)
    tests: Dict[str, str] = Field(default_factory=dict)
    created_by: str = "iam"
    provider: Optional[str] = None
    change_note: Optional[str] = None


class EngineError(ValueError):
    """Raised when the engine cannot complete a lifecycle operation."""


class SkillForgeEngine:
    """Coordinates the skill creation lifecycle without executing skill code."""

    def __init__(
        self,
        root: Optional[Path] = None,
        max_file_bytes: Optional[int] = None,
    ):
        self.layout = SkillLayout(Path(root or settings.skillforge_root))
        self.layout.ensure_structure()
        self.security = SecurityValidator(
            max_file_bytes or settings.skillforge_max_file_bytes
        )
        self.permissions = PermissionManager()

    def _manifest_from_request(self, request: SkillBuildRequest) -> SkillManifest:
        parts = request.skill_id.split(".")
        origin = parts[1] if len(parts) > 1 else "native"
        provider = request.provider
        if origin == "imported" and provider is None and len(parts) > 2:
            provider = parts[2]
        return validate_manifest(
            {
                "id": request.skill_id,
                "name": request.name,
                "version": request.version,
                "description": request.description,
                "creator": "IAM" if request.created_by == "iam" else request.created_by,
                "origin": origin,
                "provider": provider,
                "classification": request.classification,
                "permissions": request.permissions,
                "network_access": request.network_access,
                "filesystem_access": request.filesystem_access,
                "requires_creator_approval": request.requires_creator_approval,
                "status": "pending" if origin == "imported" else "draft",
            }
        )

    @staticmethod
    def _all_text(request: SkillBuildRequest) -> Dict[str, str]:
        files: Dict[str, str] = {"SKILL.md": request.instructions}
        for group in ("resources", "scripts", "tests"):
            for name, content in getattr(request, group).items():
                files[f"{group}/{name}"] = content
        return files

    def _inspect_generated(self, request: SkillBuildRequest) -> List[Finding]:
        findings: List[Finding] = []
        for name, text in self._all_text(request).items():
            findings.extend(self.security.scan_text(text, name))
        return findings

    def build(self, request: SkillBuildRequest) -> Dict[str, Any]:
        """Validate and write a new skill package; never executes skill content."""
        manifest = self._manifest_from_request(request)
        self.permissions.can_create(manifest, created_by=request.created_by)

        findings = self._inspect_generated(request)
        if self.security.has_blocking_findings(findings):
            raise EngineError(
                "Security inspection blocked skill creation: "
                + ", ".join(f"{f.code} ({f.path})" for f in findings if f.severity in {"high", "critical"})
            )

        stage = "pending" if manifest.origin == "imported" else "final"
        support_files = {
            k: v for k, v in self._all_text(request).items() if k != "SKILL.md"
        }
        directory = self.layout.write_package(
            manifest,
            instructions=request.instructions,
            files=support_files,
            stage=stage,
        )
        return {
            "manifest": manifest.to_dict(),
            "path": self.layout.relative(directory),
            "checksum": self.layout.checksum(manifest.id, directory),
            "findings": [f.to_dict() for f in findings],
            "staged": stage == "pending",
        }

    def create_version(
        self, skill_id: str, request: SkillBuildRequest, previous_version: str
    ) -> Dict[str, Any]:
        """Archive the current version before writing a replacement."""
        self.layout.archive(skill_id, previous_version)
        current = self.layout.current_dir(skill_id)
        if current.exists():
            import shutil

            shutil.rmtree(current)
        # A version update always stays in its original location; force 'final'
        # by clearing any imported staging marker through a direct write.
        manifest = self._manifest_from_request(request)
        findings = self._inspect_generated(request)
        if self.security.has_blocking_findings(findings):
            raise EngineError("Security inspection blocked the new version")
        target = self.layout.final_dir(skill_id)
        target.parent.mkdir(parents=True, exist_ok=True)
        support_files = {
            k: v for k, v in self._all_text(request).items() if k != "SKILL.md"
        }
        self.layout.write_package_at(
            target, manifest, request.instructions, support_files
        )
        return {
            "manifest": manifest.to_dict(),
            "path": self.layout.relative(target),
            "checksum": self.layout.checksum(skill_id, target),
            "findings": [f.to_dict() for f in findings],
        }

    def validate(self, skill_id: str) -> Dict[str, Any]:
        """Re-read a package from disk and inspect it without executing it."""
        findings: List[Dict[str, Any]] = []
        try:
            manifest = self.layout.read_manifest(skill_id)
            self.permissions.can_create(manifest, created_by=manifest.creator.lower())
        except (LayoutError, ManifestError, PermissionDenied) as exc:
            return {
                "valid": False,
                "findings": [
                    Finding("high", "MANIFEST_INVALID", "manifest.json", str(exc)).to_dict()
                ],
                "manifest": None,
            }

        raw_findings = self.security.scan_directory(self.layout.current_dir(skill_id))
        findings = [f.to_dict() for f in raw_findings]
        return {
            "valid": not self.security.has_blocking_findings(raw_findings),
            "findings": findings,
            "manifest": manifest.to_dict(),
            "checksum": self.layout.checksum(skill_id),
        }

    def run_tests(self, skill_id: str) -> List[Dict[str, Any]]:
        """Run deterministic structural and policy tests (no skill code executed)."""
        results: List[Dict[str, Any]] = []

        validation = self.validate(skill_id)
        results.append(
            {
                "test_type": "manifest",
                "passed": validation["valid"] and validation["manifest"] is not None,
                "details": validation["findings"],
            }
        )

        directory = self.layout.current_dir(skill_id)
        skill_md = directory / "SKILL.md"
        length = len(skill_md.read_text(encoding="utf-8").strip()) if skill_md.exists() else 0
        results.append(
            {
                "test_type": "functional",
                "passed": length >= 40
                and all((directory / d).is_dir() for d in ("resources", "scripts", "tests")),
                "details": [
                    {
                        "skill_md_chars": length,
                        "expected_structure": ["SKILL.md", "manifest.json", "permissions.json", "resources", "scripts", "tests"],
                    }
                ],
            }
        )

        security_findings = [f for f in validation["findings"] if f["severity"] in {"high", "critical"}]
        results.append(
            {
                "test_type": "security",
                "passed": not security_findings,
                "details": security_findings,
            }
        )
        return results

    def promote(self, skill_id: str) -> str:
        return self.layout.relative(self.layout.promote(skill_id))

    def quarantine(self, skill_id: str) -> str:
        target = self.layout.quarantine_dir(skill_id)
        if target.exists():
            return self.layout.relative(target)
        return self.layout.relative(self.layout.quarantine(skill_id))

    def restore(self, skill_id: str, version: str) -> str:
        return self.layout.relative(self.layout.restore(skill_id, version))

    def archive(self, skill_id: str, version: str) -> str:
        return self.layout.relative(self.layout.archive(skill_id, version))
