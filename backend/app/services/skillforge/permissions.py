"""Independent permission enforcement for the Skill Forge and Skill Runtime.

Skill files and manifests are untrusted input. Authority comes from this module,
the owner-authorization records, and the database — never from a skill's own
instructions. A skill cannot grant itself permissions by editing SKILL.md.
"""

from typing import Any, Dict, Iterable, List, Optional

from app.services.skillforge.manifest import (
    ALLOWED_PERMISSIONS,
    CLASSIFICATION_LEVELS,
    SkillManifest,
)


class PermissionDenied(PermissionError):
    """Raised when an action is outside a skill's or caller's authority."""


# Explicit lifecycle transitions. Nothing may jump straight to 'active'.
ALLOWED_TRANSITIONS: Dict[str, set] = {
    "draft": {"testing", "quarantined", "archived"},
    "testing": {"draft", "pending_approval", "published", "quarantined", "archived"},
    "pending_approval": {"published", "draft", "quarantined", "archived"},
    "published": {"active", "draft", "quarantined", "archived"},
    "active": {"testing", "quarantined", "archived"},
    "quarantined": {"draft", "archived"},
    "archived": {"draft"},
}


class PermissionManager:
    """Policy decisions for skill creation, publication and execution."""

    @staticmethod
    def level(classification: str) -> int:
        return CLASSIFICATION_LEVELS.get(classification, 0)

    def can_create(self, manifest: SkillManifest, created_by: str = "iam") -> None:
        """Enforce rule: protected core components are creator-only."""
        if self.level(manifest.classification) >= 4 and created_by not in {"owner", "creator"}:
            raise PermissionDenied(
                "Protected-core skills can only be authored by the creator (owner). "
                "IAM cannot authorise changes to its own core."
            )
        if manifest.origin == "imported" and created_by == "iam":
            # Imported skills are candidates until verified; that is handled by
            # the engine staging them in 'pending'. Creation itself is allowed.
            return

    def require_transition(self, current: str, target: str) -> None:
        if target == current:
            return
        if target not in ALLOWED_TRANSITIONS.get(current, set()):
            raise PermissionDenied(
                f"Illegal skill state transition: {current} -> {target}"
            )

    def require_publish_authority(
        self,
        manifest: SkillManifest,
        *,
        approved_by: Optional[str] = None,
        tests_passed: bool = False,
        signed_authorization: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Gate publication on tests and creator authority."""
        if not tests_passed:
            raise PermissionDenied("Skill must pass testing before publication")

        level = self.level(manifest.classification)
        if level >= 3 and not approved_by:
            raise PermissionDenied(
                "This classification requires explicit creator approval before publication"
            )
        if level >= 4 and not (signed_authorization or {}).get("authorized"):
            raise PermissionDenied(
                "Protected-core publication requires a live owner authorization grant"
            )

    def require_activation_authority(
        self,
        manifest: SkillManifest,
        *,
        status: str,
        approved_by: Optional[str] = None,
    ) -> None:
        if status != "published":
            raise PermissionDenied("Only published skills can be activated")
        if self.level(manifest.classification) >= 3 and not approved_by:
            raise PermissionDenied("Creator approval is required before activation")

    @staticmethod
    def effective_permissions(
        manifest: SkillManifest,
        granted: Iterable[str] = (),
    ) -> List[str]:
        """Runtime authority = manifest ∩ active grants ∩ policy allow-list."""
        allowed = ALLOWED_PERMISSIONS.get(manifest.classification, frozenset())
        granted_set = set(granted)
        # Ordinary permissions declared by the manifest and permitted by policy
        # are available without a separate grant. Privileged permissions require
        # an explicit, owner-issued grant stored outside the skill package.
        privileged = {
            "security_analysis",
            "vulnerability_assessment",
            "remediation_guidance",
            "financial_analysis",
            "infrastructure_analysis",
            "external_communication",
            "protected_core_configuration",
        }
        result = []
        for permission in manifest.permissions:
            if permission not in allowed:
                continue
            if permission in privileged and permission not in granted_set:
                continue
            result.append(permission)
        return result

    @staticmethod
    def can_use_network(manifest: SkillManifest, *, granted: bool = False) -> bool:
        """Network access is never implied by a manifest flag alone."""
        return manifest.network_access and granted

    @staticmethod
    def can_use_filesystem(manifest: SkillManifest, mode: str, *, granted: bool = False) -> bool:
        if mode == "none":
            return False
        if manifest.filesystem_access == "full":
            return granted
        return manifest.filesystem_access == "scoped" and mode == "scoped"
