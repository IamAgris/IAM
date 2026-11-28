"""Request-side compatibility: schema translation and parameter filtering.

IAM keeps one canonical tool definition. This layer adapts it to what a
specific provider will accept. It never decides whether a tool may run.
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Tuple

from app.services.provider_compat.profiles import CompatibilityProfile

_JSON_TYPES: Dict[str, str] = {
    "string": "string",
    "integer": "integer",
    "number": "number",
    "list": "array",
    "object": "object",
    "boolean": "boolean",
}

# Required fields are canonical IAM facts, not provider-specific guesses.
REQUIRED_FIELDS: Mapping[str, Tuple[str, ...]] = {
    "tone.analyze": ("text",),
    "network.inspect": (),
    "sandbox.status": (),
    "finance.research.read": (),
    "iics.egress.check": ("url",),
    "iics.research.strategy": ("question",),
    "iics.source.register": ("url",),
    "iics.schedule.create": ("goal", "query"),
    "iics.creator.notify": ("update",),
}


def tool_name_for_profile(profile: CompatibilityProfile, registered: str) -> str:
    """Render a canonical tool name in the form this provider accepts."""
    return registered if profile.tool_name_style == "dotted" else registered.replace(".", "_")


def registered_tool_name(name: str) -> str:
    """Resolve a wire name (or an already-canonical name) to the registry name."""
    from app.services.iam_tool_manifest import executable_tool_names, wire_name

    for registered in executable_tool_names():
        if name == registered or name == wire_name(registered):
            return registered
    return name


def build_tool_schemas(
    profile: CompatibilityProfile,
    manifests: List[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    """Convert canonical manifests into provider-acceptable function schemas."""
    schemas: List[Dict[str, Any]] = []
    for manifest in manifests:
        canonical = registered_tool_name(str(manifest.get("name") or ""))
        properties: Dict[str, Any] = {}
        for key, kind in (manifest.get("parameters") or {}).items():
            properties[str(key)] = {
                "type": _JSON_TYPES.get(str(kind), "string"),
                "description": str(key).replace("_", " "),
            }
        required = list(REQUIRED_FIELDS.get(canonical, ()))
        function: Dict[str, Any] = {
            "name": tool_name_for_profile(profile, canonical),
            "description": str(manifest.get("description") or "")[:1000],
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        }
        if profile.strict_tools:
            function["parameters"]["additionalProperties"] = False
            function["parameters"]["required"] = list(properties)
        schemas.append({"type": "function", "function": function})
    return schemas


def filter_request_parameters(
    profile: CompatibilityProfile, payload: Mapping[str, Any]
) -> Tuple[Dict[str, Any], List[str]]:
    """Remove only parameters explicitly recorded as unsupported for the model."""
    filtered = dict(payload)
    removed: List[str] = []
    for key in profile.unsupported_parameters:
        if key in filtered:
            filtered.pop(key)
            removed.append(key)
    if profile.max_tokens_field != "max_tokens" and "max_tokens" in filtered:
        filtered[profile.max_tokens_field] = filtered.pop("max_tokens")
        removed.append("max_tokens")
    return filtered, removed


def forced_tool_choice(
    profile: CompatibilityProfile, name: str
) -> Optional[Dict[str, Any]]:
    """Build a provider-valid forced tool choice, or None if unsupported."""
    if not profile.supports_forced_tools:
        return None
    canonical = registered_tool_name(name)
    return {
        "type": "function",
        "function": {"name": tool_name_for_profile(profile, canonical)},
    }


def preserve_reasoning(
    profile: CompatibilityProfile, message: Mapping[str, Any]
) -> Dict[str, Any]:
    """Keep or drop reasoning fields according to the model profile."""
    result = dict(message)
    if not profile.preserve_reasoning:
        result.pop(profile.reasoning_field, None)
    return result
