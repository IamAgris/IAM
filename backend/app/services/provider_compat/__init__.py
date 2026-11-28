"""IAM's provider compatibility subsystem.

This is IAM's own implementation, independent of any development tool. It keeps
provider communication separate from tool authorisation and execution: the
provider adapter only formats requests and parses responses; IAM's ToolRegistry,
authorize_tool_call and tool executor remain the single governance boundary.
"""

from app.services.provider_compat.probes import ProbeResult, run_compatibility_probes
from app.services.provider_compat.profiles import (
    CompatibilityProfile,
    get_compatibility_profile,
    provider_for_model,
)
from app.services.provider_compat.request import (
    build_tool_schemas,
    filter_request_parameters,
    forced_tool_choice,
    preserve_reasoning,
    registered_tool_name,
    tool_name_for_profile,
)
from app.services.provider_compat.tool_calls import (
    ToolCallAssembler,
    validate_arguments,
)

__all__ = [
    "CompatibilityProfile",
    "ProbeResult",
    "run_compatibility_probes",
    "get_compatibility_profile",
    "provider_for_model",
    "build_tool_schemas",
    "filter_request_parameters",
    "forced_tool_choice",
    "preserve_reasoning",
    "registered_tool_name",
    "tool_name_for_profile",
    "ToolCallAssembler",
    "validate_arguments",
]
