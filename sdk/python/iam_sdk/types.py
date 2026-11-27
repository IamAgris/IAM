"""Shared IAM protocol types (v1). Align with sdk/typescript/src/types.ts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

PROTOCOL_VERSION = "1"


@dataclass
class IAMOptions:
    endpoint: str
    token: str | None = None
    api_version: str = PROTOCOL_VERSION
    timeout_ms: int = 30_000
    max_retries: int = 3
    # Optional Cloudflare Access service-token headers (private Core access).
    access_client_id: str | None = None
    access_client_secret: str | None = None


@dataclass
class TaskSubmit:
    type: str
    instruction: str
    extra: dict[str, Any] = field(default_factory=dict)

    def to_payload(self) -> dict[str, Any]:
        return {"type": self.type, "instruction": self.instruction, **self.extra}


@dataclass
class NodeRegistration:
    name: str
    architecture: str
    resources: dict[str, Any]
    capabilities: list[str] = field(default_factory=list)

    def to_payload(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "architecture": self.architecture,
            "resources": self.resources,
            "capabilities": self.capabilities,
        }


class IAMError(Exception):
    def __init__(
        self,
        message: str,
        status: int,
        code: str = "iam_error",
        request_id: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.request_id = request_id
