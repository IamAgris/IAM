"""WP1 — credential handling for temporary research platforms (OD-41).

Credentials are referenced by environment-variable name, resolved only at job
submission time, expire on schedule, and are never allowed to appear in job
specs, logs, results or repository files.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from ..free_sandboxes.base import CredentialMissing
from .base import CredentialLeak


@dataclass(frozen=True)
class CredentialRef:
    provider: str
    env_var: str
    expires_at: Optional[str] = None
    scope: str = "research"


class CredentialVault:
    def __init__(self, secrets: Optional[Dict[str, str]] = None) -> None:
        self._secrets: Dict[str, str] = dict(secrets or {})

    def register_from_env(
        self, provider: str, env_var: str, expires_at: Optional[str] = None
    ) -> CredentialRef:
        value = os.environ.get(env_var)
        if not value:
            raise CredentialMissing(f"{provider}: {env_var} is not configured")
        self._secrets[env_var] = value
        return CredentialRef(provider, env_var, expires_at)

    def register(self, ref: CredentialRef, value: str) -> None:
        self._secrets[ref.env_var] = value

    def resolve(self, ref: CredentialRef) -> str:
        if ref.expires_at and datetime.fromisoformat(ref.expires_at) <= datetime.now(timezone.utc):
            raise CredentialMissing(f"{ref.provider}: credential has expired")
        value = self._secrets.get(ref.env_var)
        if not value:
            raise CredentialMissing(f"{ref.provider}: {ref.env_var} is not configured")
        return value

    def redact(self, payload: Any) -> Any:
        text = payload if isinstance(payload, str) else json.dumps(payload, default=str)
        for value in self._secrets.values():
            if value:
                text = text.replace(value, "[REDACTED]")
        return text

    def assert_no_credentials(self, payload: Any) -> None:
        text = payload if isinstance(payload, str) else json.dumps(payload, default=str)
        for value in self._secrets.values():
            if value and value in text:
                raise CredentialLeak("credential value found in research payload")
