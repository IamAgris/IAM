"""On-disk layout for IAM Skill Forge packages.

    iam/skills/
        native/<category>/<name>/{SKILL.md,manifest.json,permissions.json,resources,scripts,tests}
        imported/<provider>/<category>/<name>/...
        pending/        unverified imported candidates
        quarantine/     failed or suspicious packages
        archived/<skill-id>/<version>/  immutable version snapshots

All paths are derived from a validated skill id and are checked again before
any filesystem operation, so a crafted manifest cannot escape the skill root.
"""

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any, Dict, Optional

from app.services.skillforge.manifest import SkillManifest, validate_manifest

SUBDIRS = ("native", "imported", "pending", "quarantine", "archived")


class LayoutError(ValueError):
    """Raised for an unsafe or invalid skill path."""


class SkillLayout:
    """Manages skill package directories under a single root."""

    def __init__(self, root: Path):
        self.root = Path(root).resolve()

    def ensure_structure(self) -> None:
        for name in SUBDIRS:
            (self.root / name).mkdir(parents=True, exist_ok=True)
        for provider in ("openai", "nvidia", "google", "anthropic", "microsoft", "community"):
            (self.root / "imported" / provider).mkdir(parents=True, exist_ok=True)
        (self.root / "README.md").write_text(
            "# IAM Skill Forge packages\n\n"
            "Skills here are managed by IAM Skill Forge. `native/` contains IAM's own "
            "creations, `imported/` holds verified external skills, and `pending/`, "
            "`quarantine/` and `archived/` hold unverified, blocked and historical "
            "versions respectively.\n",
            encoding="utf-8",
        )

    @staticmethod
    def _segments(skill_id: str) -> list:  # type: ignore[type-arg]
        parts = skill_id.split(".")
        if len(parts) < 4 or parts[0] != "iam" or parts[1] not in ("native", "imported"):
            raise LayoutError(f"invalid skill id for path resolution: {skill_id!r}")
        for part in parts:
            if not part or part in {".", ".."} or part.startswith("-"):
                raise LayoutError("unsafe path segment in skill id")
        return parts

    def _join(self, *parts: str) -> Path:
        path = self.root.joinpath(*parts).resolve()
        if path != self.root and self.root not in path.parents:
            raise LayoutError("resolved path escapes the skill root")
        return path

    def pending_dir(self, skill_id: str) -> Path:
        parts = self._segments(skill_id)
        return self._join("pending", *parts)

    def final_dir(self, skill_id: str) -> Path:
        parts = self._segments(skill_id)
        if parts[1] == "native":
            return self._join("native", *parts[2:])
        if len(parts) < 5:
            raise LayoutError("imported skill ids require provider, category and name")
        return self._join("imported", parts[2], *parts[3:])

    def quarantine_dir(self, skill_id: str) -> Path:
        parts = self._segments(skill_id)
        return self._join("quarantine", *parts)

    def archive_dir(self, skill_id: str, version: str) -> Path:
        parts = self._segments(skill_id)
        if not version.replace(".", "").isdigit():
            raise LayoutError("invalid version string")
        return self._join("archived", *parts, version)

    def current_dir(self, skill_id: str) -> Path:
        """Return whichever directory currently holds the skill."""
        for candidate in (self.final_dir(skill_id), self.pending_dir(skill_id), self.quarantine_dir(skill_id)):
            if candidate.exists():
                return candidate
        return self.final_dir(skill_id)

    def relative(self, path: Path) -> str:
        return Path(path).resolve().relative_to(self.root).as_posix()

    @staticmethod
    def _safe_relative_file(name: str) -> Path:
        path = Path(name)
        if path.is_absolute() or any(p in {"", ".", ".."} for p in path.parts):
            raise LayoutError(f"unsafe relative file path: {name!r}")
        return path

    def write_package(
        self,
        manifest: SkillManifest,
        instructions: str,
        files: Optional[Dict[str, str]] = None,
        stage: str = "final",
    ) -> Path:
        """Create a skill directory with the standard file structure."""
        target = self.pending_dir(manifest.id) if stage == "pending" else self.final_dir(manifest.id)
        return self.write_package_at(target, manifest, instructions, files)

    def write_package_at(
        self,
        target: Path,
        manifest: SkillManifest,
        instructions: str,
        files: Optional[Dict[str, str]] = None,
    ) -> Path:
        """Write a complete package into an explicit, already-resolved directory."""
        target = target.resolve()
        if target != self.root and self.root not in target.parents:
            raise LayoutError("target escapes the skill root")
        if target.exists():
            raise LayoutError(f"skill directory already exists: {self.relative(target)}")
        target.mkdir(parents=True)

        (target / "SKILL.md").write_text(instructions, encoding="utf-8")
        (target / "manifest.json").write_text(
            json.dumps(manifest.to_dict(), indent=2, sort_keys=True), encoding="utf-8"
        )
        permissions_doc = {
            "classification": manifest.classification,
            "permissions": list(manifest.permissions),
            "network_access": manifest.network_access,
            "filesystem_access": manifest.filesystem_access,
            "requires_creator_approval": manifest.requires_creator_approval,
            "note": "Descriptive only. Authority is enforced by PermissionManager at runtime.",
        }
        (target / "permissions.json").write_text(
            json.dumps(permissions_doc, indent=2, sort_keys=True), encoding="utf-8"
        )
        for folder in ("resources", "scripts", "tests"):
            (target / folder).mkdir(exist_ok=True)

        for name, content in (files or {}).items():
            rel = self._safe_relative_file(name)
            dest = (target / rel).resolve()
            if target not in dest.parents:
                raise LayoutError("file path escapes the skill directory")
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content, encoding="utf-8")

        return target

    def read_manifest(self, skill_id: str, path: Optional[Path] = None) -> SkillManifest:
        directory = path or self.current_dir(skill_id)
        manifest_path = directory / "manifest.json"
        if not manifest_path.exists():
            raise LayoutError("manifest.json not found")
        try:
            data: Dict[str, Any] = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise LayoutError(f"manifest.json is not valid JSON: {exc}") from exc
        return validate_manifest(data)

    def checksum(self, skill_id: str, path: Optional[Path] = None) -> str:
        directory = path or self.current_dir(skill_id)
        digest = hashlib.sha256()
        for file in sorted(directory.rglob("*")):
            if not file.is_file():
                continue
            digest.update(self.relative(file).encode("utf-8"))
            digest.update(file.read_bytes())
        return digest.hexdigest()

    def promote(self, skill_id: str) -> Path:
        """Move a verified imported candidate from pending/ into imported/."""
        pending = self.pending_dir(skill_id)
        final = self.final_dir(skill_id)
        if not pending.exists():
            raise LayoutError("no pending skill candidate to promote")
        if final.exists():
            raise LayoutError("target skill directory already exists")
        final.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(pending), str(final))
        return final

    def archive(self, skill_id: str, version: str) -> Path:
        source = self.current_dir(skill_id)
        target = self.archive_dir(skill_id, version)
        if target.exists():
            raise LayoutError(f"version {version} is already archived")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(str(source), str(target))
        return target

    def quarantine(self, skill_id: str) -> Path:
        source = self.current_dir(skill_id)
        target = self.quarantine_dir(skill_id)
        if not source.exists():
            raise LayoutError("skill directory does not exist")
        if target.exists():
            shutil.rmtree(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(target))
        return target

    def restore(self, skill_id: str, version: str) -> Path:
        """Restore an archived version as the current skill directory."""
        source = self.archive_dir(skill_id, version)
        if not source.exists():
            raise LayoutError(f"archived version {version} not found")
        target = self.final_dir(skill_id)
        if target.exists():
            shutil.rmtree(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(str(source), str(target))
        return target
