"""Autonomy boundary: routine work is autonomous; authority stays with the Creator (OD-41)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, Optional

from .base import CreatorApprovalRequired


class ActionKind(str, Enum):
    ROUTINE = "routine"  # research, training, benchmarking, recovery, scheduling
    PAID = "paid"
    BINDING = "binding"
    HUMAN_ACTION = "human_action"
    PROTECTED_CORE = "protected_core"


@dataclass(frozen=True)
class SignedApproval:
    request_id: str
    signed_by: str
    signature: str  # signed-challenge reference (OD-03/OD-19), never a bare email reply
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


AuditSink = Callable[[str, Dict[str, Any]], None]


class AutonomyGate:
    """Fail-closed gate for actions outside IAM's routine authority."""

    def __init__(self, audit_sink: Optional[AuditSink] = None) -> None:
        self.audit_sink = audit_sink

    def assert_allowed(
        self, kind: ActionKind, approval: Optional[SignedApproval] = None
    ) -> None:
        if kind == ActionKind.ROUTINE:
            return
        if approval is None or not approval.signature or not approval.signed_by:
            raise CreatorApprovalRequired(
                f"{kind.value} action requires signed Creator approval"
            )
        if self.audit_sink:
            self.audit_sink("creator_authority_used", {
                "action": kind.value,
                "request_id": approval.request_id,
                "signed_by": approval.signed_by,
            })
