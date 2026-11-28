"""Optional read-only Infisical Cloud secrets source (OD-58, default-off).

Docker secrets stay the default source. When ``SECRETS_BACKEND=infisical`` the
fields listed in ``SECRET_FIELDS`` are resolved through the Infisical REST API,
with Docker secret files and environment values remaining the fallback. The
production fail-closed policy in ``core.secrets`` is unchanged.

Safety rules:
- No secret value is logged, returned in a status report, or cached beyond a
  bounded in-memory TTL. Only ``SECRET_FIELDS`` names are cached.
- Requests go only to an HTTPS allowlisted Infisical host, with a short timeout.
- Fetch failures keep the last-known-good cache; they never substitute a
  placeholder or raise into the startup path.
"""

from __future__ import annotations

import os
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse

import httpx

from app.core.config import SECRET_FIELDS, settings

LOGIN_PATH = "/api/v1/auth/universal-auth/login"
SECRETS_PATH = "/api/v4/secrets"

_ALLOWED_FIELDS = frozenset(name.upper() for name in SECRET_FIELDS)
_ENVIRONMENTS = {
    "development": "dev",
    "dev": "dev",
    "staging": "staging",
    "production": "prod",
    "prod": "prod",
}


class InfisicalError(RuntimeError):
    """Configuration/transport failure. Messages are codes, never secret values."""


def _bootstrap_secret(env_name: str) -> str:
    """Read a machine-identity credential from ``<NAME>_FILE`` or the environment."""
    path = os.environ.get(f"{env_name}_FILE")
    if path:
        try:
            return Path(path).read_text(encoding="utf-8").strip()
        except OSError:
            return ""
    return (os.environ.get(env_name) or "").strip()


class InfisicalSecretsClient:
    """Bounded, read-only Infisical client with a last-known-good cache."""

    def __init__(
        self,
        site_url: Optional[str] = None,
        project_id: Optional[str] = None,
        environment: Optional[str] = None,
        client_id_env: Optional[str] = None,
        client_secret_env: Optional[str] = None,
        allowed_hosts: Optional[str] = None,
        cache_ttl_seconds: Optional[int] = None,
        refresh_margin_seconds: Optional[int] = None,
        timeout_seconds: Optional[float] = None,
        http_client: Any = None,
    ) -> None:
        self.site_url = (
            site_url if site_url is not None else settings.infisical_site_url
        ).rstrip("/")
        self.project_id = (
            project_id if project_id is not None else settings.infisical_project_id
        )
        self.environment = (
            environment if environment is not None else settings.infisical_environment
        )
        self.client_id_env = client_id_env or settings.infisical_client_id_env
        self.client_secret_env = client_secret_env or settings.infisical_client_secret_env
        self.allowed_hosts = [
            host.strip().lower()
            for host in (
                allowed_hosts
                if allowed_hosts is not None
                else settings.infisical_allowed_hosts
            ).split(",")
            if host.strip()
        ]
        self.cache_ttl = int(
            cache_ttl_seconds
            if cache_ttl_seconds is not None
            else settings.infisical_cache_ttl_seconds
        )
        self.refresh_margin = int(
            refresh_margin_seconds
            if refresh_margin_seconds is not None
            else settings.infisical_token_refresh_margin_seconds
        )
        self.timeout = float(
            timeout_seconds
            if timeout_seconds is not None
            else settings.infisical_timeout_seconds
        )
        self._http = http_client
        self._lock = threading.Lock()
        self._token = ""
        self._token_expires_at = 0.0
        self._secrets: Dict[str, str] = {}
        self._secrets_expires_at = 0.0
        self._last_error = ""
        self._reachable = False

    # -- redacted status ---------------------------------------------------
    def status(self) -> Dict[str, Any]:
        """Return names/status only. Never include a secret value."""
        with self._lock:
            names = sorted(self._secrets)
            error = self._last_error
            reachable = self._reachable
        return {
            "enabled": settings.secrets_backend.lower() == "infisical",
            "host_allowed": self.host_allowed(),
            "credentials_present": self.has_credentials(),
            "project_configured": bool(self.project_id),
            "reachable": reachable,
            "cached_names": names,
            "last_error": error,
        }

    def has_credentials(self) -> bool:
        return bool(
            _bootstrap_secret(self.client_id_env)
            and _bootstrap_secret(self.client_secret_env)
        )

    def host_allowed(self) -> bool:
        parsed = urlparse(self.site_url)
        host = (parsed.hostname or "").lower()
        if host not in self.allowed_hosts:
            return False
        if parsed.scheme != "https" and host not in {"localhost", "127.0.0.1", "::1"}:
            return False
        return parsed.path in ("", "/")

    def resolved_environment(self) -> str:
        if self.environment:
            return self.environment
        return _ENVIRONMENTS.get(settings.app_env.lower(), "dev")

    # -- public API --------------------------------------------------------
    def get(self, name: str) -> Optional[str]:
        """Return a cached remote value, or ``None``. Network errors are swallowed."""
        key = name.upper()
        if key not in _ALLOWED_FIELDS:
            return None
        with self._lock:
            fresh = bool(self._secrets) and time.monotonic() < self._secrets_expires_at
        if not fresh:
            self.refresh()
        with self._lock:
            return self._secrets.get(key)

    def refresh(self, force: bool = False) -> bool:
        """Fetch secrets; keep last-known-good data on failure. Returns success."""
        with self._lock:
            now = time.monotonic()
            if not force and self._secrets and now < self._secrets_expires_at:
                return True
        if not self.host_allowed():
            self._set_error("host_not_allowed")
            return False
        if not self.has_credentials():
            self._set_error("credentials_missing")
            return False
        if not self.project_id:
            self._set_error("project_missing")
            return False
        try:
            token = self._token_for_request()
            payload = self._fetch(token)
            secrets: Dict[str, str] = {}
            for item in payload.get("secrets", []):
                key = str(item.get("secretKey", "")).upper()
                value = item.get("secretValue")
                if key in _ALLOWED_FIELDS and isinstance(value, str):
                    secrets[key] = value
            with self._lock:
                self._secrets = secrets
                self._secrets_expires_at = time.monotonic() + max(self.cache_ttl, 1)
                self._reachable = True
                self._last_error = ""
            return True
        except Exception as exc:  # boundary: never leak values into logs
            self._set_error(type(exc).__name__)
            return False

    # -- internals ---------------------------------------------------------
    def _set_error(self, code: str) -> None:
        with self._lock:
            self._reachable = False
            self._last_error = code

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        url = self.site_url + path
        if self._http is not None:
            return self._http.request(method, url, **kwargs)
        with httpx.Client(timeout=self.timeout, follow_redirects=False) as client:
            return client.request(method, url, **kwargs)

    def _token_for_request(self) -> str:
        with self._lock:
            if self._token and time.monotonic() < self._token_expires_at:
                return self._token
        response = self._request(
            "POST",
            LOGIN_PATH,
            json={
                "clientId": _bootstrap_secret(self.client_id_env),
                "clientSecret": _bootstrap_secret(self.client_secret_env),
            },
        )
        response.raise_for_status()
        data = response.json()
        token = str(data.get("accessToken", ""))
        if not token:
            raise InfisicalError("token_missing")
        expires_in = int(data.get("expiresIn", 0) or 0)
        with self._lock:
            self._token = token
            self._token_expires_at = time.monotonic() + max(
                expires_in - self.refresh_margin, 30
            )
        return token

    def _fetch(self, token: str) -> Dict[str, Any]:
        response = self._request(
            "GET",
            SECRETS_PATH,
            params={
                "projectId": self.project_id,
                "environment": self.resolved_environment(),
                "secretPath": "/",
                "includeImports": "true",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            raise InfisicalError("bad_payload")
        return data


_client: Optional[InfisicalSecretsClient] = None


def get_infisical_client() -> InfisicalSecretsClient:
    """Process-wide client; constructed lazily so imports never touch the network."""
    global _client
    if _client is None:
        _client = InfisicalSecretsClient()
    return _client
