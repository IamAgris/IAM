"""Provider-independent tool-call parsing and assembly.

Streaming gateways emit a tool call in fragments. Nothing is executable until
the name and arguments are complete, the JSON parses, and the canonical schema
validates. This module never authorises or executes anything.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional

from app.services.provider_compat.request import REQUIRED_FIELDS, registered_tool_name

_JSON_TYPES: Dict[str, Any] = {
    "string": str,
    "integer": int,
    "number": (int, float),
    "list": list,
    "object": dict,
    "boolean": bool,
}


@dataclass
class AssembledCall:
    index: int
    id: str = ""
    name: str = ""
    arguments: str = ""
    complete: bool = False
    error: Optional[str] = None

    def as_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "arguments": self.arguments,
            "complete": self.complete,
            "error": self.error,
        }


@dataclass
class ToolCallAssembler:
    """Accumulate streamed tool-call deltas with duplicate protection."""

    _calls: Dict[int, AssembledCall] = field(default_factory=dict)
    _seen: set[tuple[str, str, str]] = field(default_factory=set)

    def add_delta(
        self,
        index: int,
        *,
        call_id: Optional[str] = None,
        name: Optional[str] = None,
        arguments: Optional[str] = None,
    ) -> None:
        call = self._calls.setdefault(index, AssembledCall(index=index))
        if call_id and not call.id:
            call.id = str(call_id)
        if name and not call.name:
            call.name = str(name)
        if arguments:
            call.arguments += str(arguments)

    def add(self, call: Mapping[str, Any], index: int = 0) -> None:
        """Add a complete, non-streaming tool call."""
        function = call.get("function") or {}
        self.add_delta(
            index,
            call_id=str(call.get("id") or ""),
            name=str(function.get("name") or call.get("name") or ""),
            arguments=json.dumps(function.get("arguments") if isinstance(function.get("arguments"), (dict, list)) else call.get("arguments") or {}, ensure_ascii=False),
        )

    def calls(self) -> List[AssembledCall]:
        """Return validated calls; duplicates are ignored after the first."""
        results: List[AssembledCall] = []
        for index in sorted(self._calls):
            call = self._calls[index]
            call.complete = False
            call.error = None
            if not call.name:
                call.error = "missing_tool_name"
            elif not call.arguments.strip():
                call.error = "missing_arguments"
            else:
                try:
                    parsed = json.loads(call.arguments)
                except (TypeError, ValueError):
                    call.error = "incomplete_arguments"
                else:
                    if not isinstance(parsed, dict):
                        call.error = "arguments_not_object"
                    else:
                        call.error = next(iter(validate_arguments(call.name, parsed)), None)
            if not call.error:
                call.complete = True
                key = (call.id, call.name, call.arguments)
                if key in self._seen:
                    continue
                self._seen.add(key)
            results.append(call)
        return results

    def executable(self) -> List[AssembledCall]:
        return [call for call in self.calls() if call.complete]

    def incomplete(self) -> List[int]:
        return [call.index for call in self.calls() if not call.complete]


def validate_arguments(name: str, arguments: Mapping[str, Any]) -> List[str]:
    """Validate against IAM's canonical manifest; no provider input is trusted."""
    canonical = registered_tool_name(str(name))
    errors: List[str] = []
    from app.services.iam_tool_manifest import callable_manifests

    manifest = next(
        (m for m in callable_manifests() if str(m.get("name")) == canonical), None
    )
    if manifest is None:
        return ["unknown_tool"]
    specs = manifest.get("parameters") or {}
    for key in REQUIRED_FIELDS.get(canonical, ()):
        if key not in arguments:
            errors.append(f"missing:{key}")
    for key, value in arguments.items():
        kind = str(specs.get(key))
        expected = _JSON_TYPES.get(kind)
        if expected is not None and not isinstance(value, expected):
            errors.append(f"invalid_type:{key}")
    return errors
