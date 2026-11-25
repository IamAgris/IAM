"""IAM Security Guard — policy enforcement before any external security action.

This guard is IAM's own. It does not trust ARTEX (or any other engine) to enforce
scope, authorisation or operation limits. Every task and tool call is checked
here first. The default posture is deny: read-only, loopback-only, dry-run.
"""

import ipaddress
import re
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urlparse

FORBIDDEN_OPERATION_TOKENS = re.compile(
    r"(?i)\b(exploit|persistence|persist|evade|evasion|bypass|reverse[_-]?shell|"
    r"privilege[_-]?escalation|mass[_-]?scan|internet[_-]?wide|ddos|"
    r"destructive|wipe|ransom|crime|unauthori[sz]ed)\b"
)

READ_TOOLS = frozenset(
    {
        "list_tasks",
        "get_task",
        "get_task_graph",
        "list_task_findings",
        "list_companies",
        "list_task_categories",
        "list_llm_profiles",
    }
)
EXECUTION_TOOLS = frozenset(
    {"spawn_task", "pause_task", "resume_task", "add_task_hint"}
)
KNOWN_TOOLS = READ_TOOLS | EXECUTION_TOOLS


class SecurityGuardDenied(PermissionError):
    """Raised when a requested security action is outside IAM's authority."""


class SecurityGuard:
    """Enforces scope, authorisation and operation policy independently."""

    @staticmethod
    def validate_base_url(base_url: str, *, allow_private_network: bool = False) -> str:
        """Only loopback (or explicitly allowed private) engine endpoints."""
        try:
            parsed = urlparse(base_url)
        except ValueError as exc:
            raise SecurityGuardDenied("invalid engine base URL") from exc
        if parsed.scheme not in {"http", "https"}:
            raise SecurityGuardDenied("engine base URL must use http or https")
        if parsed.username or parsed.password:
            raise SecurityGuardDenied("engine base URL must not embed credentials")
        host = parsed.hostname
        if not host:
            raise SecurityGuardDenied("engine base URL has no host")
        if host.lower() in {"localhost", "127.0.0.1", "::1", "[::1]"}:
            return base_url
        try:
            address = ipaddress.ip_address(host.strip("[]"))
        except ValueError as exc:
            raise SecurityGuardDenied(
                "engine endpoint must be loopback; use an SSH tunnel or VPN for remote engines"
            ) from exc
        if address.is_loopback:
            return base_url
        if address.is_private and allow_private_network:
            return base_url
        raise SecurityGuardDenied(
            "public or non-loopback engine endpoints are not permitted"
        )

    @staticmethod
    def validate_source_allowlist(value: str) -> List[str]:
        """Validate the IP/CIDR allowlist configured at the engine side."""
        entries = [e.strip() for e in (value or "").split(",") if e.strip()]
        if not entries:
            raise SecurityGuardDenied("source allowlist must not be empty")
        for entry in entries:
            try:
                network = ipaddress.ip_network(entry, strict=False)
            except ValueError as exc:
                raise SecurityGuardDenied(f"invalid source allowlist entry: {entry}") from exc
            if not (network.is_loopback or network.is_private):
                raise SecurityGuardDenied(
                    f"source allowlist entry is not loopback/private: {entry}"
                )
            if network.num_addresses > 65536:
                raise SecurityGuardDenied(f"source allowlist entry is too broad: {entry}")
        return entries

    @staticmethod
    def validate_target(target: str, scopes: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
        """A target is legal only if it matches an explicit owner-registered scope."""
        if not target or not isinstance(target, str):
            raise SecurityGuardDenied("target is required")
        lowered = target.strip().lower()
        if "*" in lowered or lowered in {"0.0.0.0/0", "::/0", "internet", "all"}:
            raise SecurityGuardDenied("internet-wide or wildcard targets are forbidden")
        if any(token in lowered for token in ("exploit", "reverse", "payload", "shell")):
            raise SecurityGuardDenied("target must be a lab asset, not an attack description")

        try:
            target_address = ipaddress.ip_address(lowered)
        except ValueError:
            target_address = None

        for scope in scopes:
            allowed = str(scope.get("target", "")).strip().lower()
            if not allowed:
                continue
            if lowered == allowed:
                return scope
            if target_address is not None and "/" in allowed:
                try:
                    if target_address in ipaddress.ip_network(allowed, strict=False):
                        return scope
                except ValueError:
                    continue

        raise SecurityGuardDenied(
            "target is not in the owner-registered scope allowlist"
        )

    @staticmethod
    def validate_operation(operation: str) -> str:
        """Reject offensive, destructive and evasive operation descriptions."""
        if not operation or not isinstance(operation, str):
            raise SecurityGuardDenied("operation is required")
        if FORBIDDEN_OPERATION_TOKENS.search(operation):
            raise SecurityGuardDenied(
                "operation includes prohibited exploitation, evasion or destructive activity"
            )
        if operation not in KNOWN_TOOLS:
            raise SecurityGuardDenied(f"unknown or unsupported operation: {operation}")
        return operation

    @staticmethod
    def authorize_tool(
        tool: str,
        *,
        allowed_scopes: Iterable[str],
        enabled: bool,
        allow_execution: bool,
        approved_by: Optional[str],
        authorization: Optional[Dict[str, Any]],
    ) -> None:
        """Gate a single external tool call."""
        SecurityGuard.validate_operation(tool)
        if not enabled:
            raise SecurityGuardDenied("external security engine is disabled")
        scopes = set(allowed_scopes or [])
        if tool in READ_TOOLS:
            if "read" not in scopes:
                raise SecurityGuardDenied("engine has no 'read' scope")
            return
        if tool in EXECUTION_TOOLS:
            if "task:control" not in scopes and tool != "spawn_task":
                raise SecurityGuardDenied("engine has no 'task:control' scope")
            if "task:create" not in scopes and tool == "spawn_task":
                raise SecurityGuardDenied("engine has no 'task:create' scope")
            if not allow_execution:
                raise SecurityGuardDenied("engine execution is disabled by IAM policy")
            if not approved_by:
                raise SecurityGuardDenied("signed creator approval is required for execution tools")
            if not (authorization or {}).get("authorized"):
                raise SecurityGuardDenied(
                    "no active signed Creator authorization for security testing"
                )
            return
        raise SecurityGuardDenied(f"tool is not permitted: {tool}")

    @staticmethod
    def authorize_dispatch(
        *,
        enabled: bool,
        approved_by: Optional[str],
        authorization: Optional[Dict[str, Any]],
        scope: Dict[str, Any],
    ) -> None:
        """Final gate before a task is sent to the external engine."""
        if not enabled:
            raise SecurityGuardDenied("external security engine is disabled")
        if not approved_by:
            raise SecurityGuardDenied("signed creator approval is required before dispatch")
        if not (authorization or {}).get("authorized"):
            raise SecurityGuardDenied("no active signed Creator authorization for security testing")
        if not scope.get("allow_write") and str(scope.get("target_type")) == "wildcard":
            raise SecurityGuardDenied("wildcard scopes cannot be dispatched")

    @staticmethod
    def normalize_severity(value: Any) -> str:
        mapping = {
            "critical": "critical",
            "high": "high",
            "medium": "medium",
            "moderate": "medium",
            "low": "low",
            "info": "informational",
            "informational": "informational",
        }
        return mapping.get(str(value).lower(), "informational")

    @staticmethod
    def sanitize_finding_text(value: Any, limit: int = 4000) -> str:
        """Engine output is untrusted data, never instructions to IAM."""
        text = str(value or "")
        text = "".join(ch if ch.isprintable() or ch in "\n\t" else " " for ch in text)
        text = re.sub(r"\s+", " ", text).strip()
        return f"[untrusted engine output] {text[:limit]}"
