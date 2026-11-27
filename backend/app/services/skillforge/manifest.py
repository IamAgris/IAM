"""Skill manifest format and validation.

A manifest is *descriptive metadata*, never an authority mechanism. The runtime
must independently enforce permissions (see ``permissions.py``).
"""

import re
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

SKILL_ID_PATTERN = re.compile(
    r"^iam\.(native|imported)\.[a-z0-9][a-z0-9_-]*(?:\.[a-z0-9][a-z0-9_-]*)*$"
)
VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")

CLASSIFICATION_LEVELS: Dict[str, int] = {
    "personal": 1,
    "operational": 2,
    "sensitive": 3,
    "protected_core": 4,
}

PROVIDERS = ("openai", "nvidia", "google", "anthropic", "microsoft", "community")

ALLOWED_PERMISSIONS: Dict[str, frozenset] = {
    "personal": frozenset(
        {
            "knowledge",
            "reasoning",
            "task_workflow",
            "documentation",
            "code_review",
        }
    ),
    "operational": frozenset(
        {
            "knowledge",
            "reasoning",
            "task_workflow",
            "documentation",
            "code_review",
            "tool_use",
            "integration",
            "automation",
            "local_filesystem_scoped",
        }
    ),
    "sensitive": frozenset(
        {
            "knowledge",
            "reasoning",
            "task_workflow",
            "documentation",
            "code_review",
            "tool_use",
            "integration",
            "automation",
            "local_filesystem_scoped",
            "security_analysis",
            "vulnerability_assessment",
            "remediation_guidance",
            "financial_analysis",
            "infrastructure_analysis",
            "external_communication",
        }
    ),
    "protected_core": frozenset(
        {
            "knowledge",
            "reasoning",
            "task_workflow",
            "documentation",
            "code_review",
            "tool_use",
            "integration",
            "automation",
            "local_filesystem_scoped",
            "security_analysis",
            "vulnerability_assessment",
            "remediation_guidance",
            "financial_analysis",
            "infrastructure_analysis",
            "external_communication",
            "protected_core_configuration",
        }
    ),
}

FILESYSTEM_ACCESS_LEVELS: Dict[str, int] = {"none": 0, "scoped": 2, "full": 4}


class ManifestError(ValueError):
    """Raised when a skill manifest violates the format or policy."""


class SkillManifest(BaseModel):
    """Machine-readable description of a skill package."""

    id: str
    name: str = Field(min_length=1, max_length=120)
    version: str = "1.0.0"
    creator: str = "IAM"
    origin: Literal["native", "imported"] = "native"
    status: str = "draft"
    classification: str = "personal"
    permissions: List[str] = Field(default_factory=list)
    network_access: bool = False
    filesystem_access: str = "none"
    requires_creator_approval: bool = False
    description: Optional[str] = None
    provider: Optional[str] = None

    @field_validator("id")
    @classmethod
    def _validate_id(cls, value: str) -> str:
        if not SKILL_ID_PATTERN.match(value):
            raise ValueError(
                "skill id must match iam.(native|imported).<category>.<name> "
                "using lowercase letters, digits, '_' or '-'"
            )
        return value

    @field_validator("version")
    @classmethod
    def _validate_version(cls, value: str) -> str:
        if not VERSION_PATTERN.match(value):
            raise ValueError("version must be semantic versioning (e.g. 1.2.3)")
        return value

    @field_validator("classification")
    @classmethod
    def _validate_classification(cls, value: str) -> str:
        if value not in CLASSIFICATION_LEVELS:
            raise ValueError(
                "classification must be one of: " + ", ".join(CLASSIFICATION_LEVELS)
            )
        return value

    @field_validator("filesystem_access")
    @classmethod
    def _validate_filesystem_access(cls, value: str) -> str:
        if value not in FILESYSTEM_ACCESS_LEVELS:
            raise ValueError("filesystem_access must be one of: none, scoped, full")
        return value

    @field_validator("permissions")
    @classmethod
    def _validate_permissions(cls, value: List[str]) -> List[str]:
        if len(value) != len(set(value)):
            raise ValueError("permissions must not contain duplicates")
        for permission in value:
            if not re.match(r"^[a-z][a-z0-9_]*$", permission):
                raise ValueError(f"invalid permission token: {permission!r}")
        return value

    @model_validator(mode="after")
    def _validate_policy(self) -> "SkillManifest":
        level = CLASSIFICATION_LEVELS[self.classification]

        if self.origin == "imported":
            if not self.provider or self.provider not in PROVIDERS:
                raise ValueError(
                    "imported skills require provider in: " + ", ".join(PROVIDERS)
                )
        elif self.provider is not None:
            raise ValueError("native skills must not declare a provider")

        allowed = ALLOWED_PERMISSIONS[self.classification]
        excess = [p for p in self.permissions if p not in allowed]
        if excess:
            raise ValueError(
                f"permissions {excess} exceed those allowed for {self.classification}; "
                "a skill cannot grant itself new permissions"
            )

        if self.network_access and level < CLASSIFICATION_LEVELS["operational"]:
            raise ValueError("network_access requires at least 'operational' classification")

        fs_level = FILESYSTEM_ACCESS_LEVELS[self.filesystem_access]
        if fs_level > level:
            raise ValueError(
                f"filesystem_access '{self.filesystem_access}' requires classification "
                f"of level {fs_level} or higher"
            )

        if level >= CLASSIFICATION_LEVELS["sensitive"] and not self.requires_creator_approval:
            raise ValueError(
                "sensitive and protected_core skills must set requires_creator_approval=true"
            )

        return self

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


def validate_manifest(payload: Dict[str, Any]) -> SkillManifest:
    """Validate a manifest dictionary, raising ManifestError with a clear reason."""
    try:
        return SkillManifest.model_validate(payload)
    except Exception as exc:  # pydantic ValidationError and friends
        raise ManifestError(str(exc)) from exc
