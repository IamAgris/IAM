"""Provider-independent model discovery contract (OD-52 Phase B).

A provider supplies catalogue entries and metadata; it never authenticates a
sub-agent directly. IAM keeps one credential per provider and routes all
execution through LiteLLM.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ModelSpec:
    """Normalised catalogue entry. Never claims endpoint availability."""

    provider: str
    model_id: str
    display_name: str
    model_type: str = "llm"
    access_type: str = "free"
    endpoint_status: str = "unknown"
    context_length: Optional[int] = None
    input_capabilities: List[str] = field(default_factory=lambda: ["text"])
    output_capabilities: List[str] = field(default_factory=lambda: ["text"])
    tool_calling: bool = False
    reasoning: bool = False
    structured_output: bool = False
    api_protocol: str = "chat_completions"
    restrictions: Dict[str, Any] = field(default_factory=dict)
    metadata_source: str = "unknown"

    def as_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "model_id": self.model_id,
            "display_name": self.display_name,
            "model_type": self.model_type,
            "access_type": self.access_type,
            "endpoint_status": self.endpoint_status,
            "context_length": self.context_length,
            "input_capabilities": self.input_capabilities,
            "output_capabilities": self.output_capabilities,
            "tool_calling": self.tool_calling,
            "reasoning": self.reasoning,
            "structured_output": self.structured_output,
            "api_protocol": self.api_protocol,
            "restrictions": self.restrictions,
            "metadata_source": self.metadata_source,
        }


class BaseProvider(ABC):
    name: str = "base"

    @abstractmethod
    async def discover(self) -> List[ModelSpec]:
        """List models from the provider's own catalogue endpoint."""

    @abstractmethod
    async def metadata(self) -> Dict[str, ModelSpec]:
        """List model specifications from an external metadata catalogue."""
