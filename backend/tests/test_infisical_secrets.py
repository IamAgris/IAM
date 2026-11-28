"""Unit tests for the opt-in Infisical Cloud secrets source (OD-58)."""

import os
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import urlparse

from app.core import secrets as secret_core
from app.core.config import Settings, settings
from app.core.infisical import InfisicalError, InfisicalSecretsClient
from app.services import deployment_preflight


class _Response:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise InfisicalError(f"http_{self.status_code}")

    def json(self):
        return self._payload


class _Transport:
    """In-memory HTTP double. Records paths only, never secret values."""

    def __init__(self, secrets=None, fail=False, token="remote-token"):
        self.calls = []
        self.fail = fail
        self.token = token
        self.payload = {
            "secrets": secrets
            if secrets is not None
            else [
                {"secretKey": "APP_SECRET_KEY", "secretValue": "remote-app-secret"},
                {"secretKey": "UNRELATED_KEY", "secretValue": "must-not-cache"},
            ]
        }

    def request(self, method, url, **kwargs):
        path = urlparse(url).path
        self.calls.append((method, path))
        if self.fail:
            raise InfisicalError("network_down")
        if path.endswith("/universal-auth/login"):
            return _Response({"accessToken": self.token, "expiresIn": 7200})
        return _Response(self.payload)


# Dummy bootstrap credentials for the test double only — never real secrets.
_CREDENTIALS = {
    "INFISICAL_CLIENT_ID": "test-client-id",
    "INFISICAL_CLIENT_SECRET": "test-client-secret",
}


def _client(transport=None, **overrides):
    options = dict(
        site_url="https://app.infisical.com",
        project_id="project-1",
        environment="dev",
        allowed_hosts="app.infisical.com,eu.infisical.com",
        http_client=transport or _Transport(),
    )
    options.update(overrides)
    return InfisicalSecretsClient(**options)


class InfisicalSecretsTests(unittest.TestCase):
    def test_default_backend_ignores_infisical(self):
        with (
            patch.object(settings, "secrets_backend", "docker"),
            patch.object(secret_core, "get_infisical_client") as mocked,
            patch.dict(os.environ, {}, clear=True),
        ):
            self.assertIsNone(secret_core.read_secret("APP_SECRET_KEY"))
        mocked.assert_not_called()

    def test_remote_value_used_and_only_allowed_names_cached(self):
        transport = _Transport()
        client = _client(transport)
        with (
            patch.object(settings, "secrets_backend", "infisical"),
            patch.object(secret_core, "get_infisical_client", return_value=client),
            patch.dict(os.environ, _CREDENTIALS, clear=True),
        ):
            self.assertEqual(
                secret_core.read_secret("APP_SECRET_KEY"), "remote-app-secret"
            )
        status = client.status()
        self.assertIn("APP_SECRET_KEY", status["cached_names"])
        self.assertNotIn("UNRELATED_KEY", status["cached_names"])
        self.assertTrue(status["reachable"])
        self.assertNotIn("remote-app-secret", repr(status))
        self.assertNotIn("must-not-cache", repr(status))

    def test_login_once_within_cache_ttl(self):
        transport = _Transport()
        client = _client(transport)
        with patch.dict(os.environ, _CREDENTIALS, clear=True):
            self.assertEqual(client.get("APP_SECRET_KEY"), "remote-app-secret")
            self.assertEqual(client.get("APP_SECRET_KEY"), "remote-app-secret")
        self.assertEqual(
            [path for _, path in transport.calls],
            ["/api/v1/auth/universal-auth/login", "/api/v4/secrets"],
        )

    def test_environment_fallback_when_remote_has_no_value(self):
        client = _client(_Transport(secrets=[]))
        with (
            patch.object(settings, "secrets_backend", "infisical"),
            patch.object(secret_core, "get_infisical_client", return_value=client),
            patch.dict(
                os.environ,
                {**_CREDENTIALS, "APP_SECRET_KEY": "env-value"},
                clear=True,
            ),
        ):
            self.assertEqual(secret_core.read_secret("APP_SECRET_KEY"), "env-value")

    def test_docker_secret_fallback_when_remote_unreachable(self):
        with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8") as tmp:
            tmp.write("file-secret\n")
            path = tmp.name
        try:
            client = _client(_Transport(fail=True))
            with (
                patch.object(settings, "secrets_backend", "infisical"),
                patch.object(secret_core, "get_infisical_client", return_value=client),
                patch.dict(
                    os.environ,
                    {**_CREDENTIALS, "APP_SECRET_KEY_FILE": path},
                    clear=True,
                ),
            ):
                self.assertEqual(
                    secret_core.read_secret("APP_SECRET_KEY"), "file-secret"
                )
            status = client.status()
            self.assertFalse(status["reachable"])
            self.assertEqual(status["last_error"], "InfisicalError")
        finally:
            os.unlink(path)

    def test_unknown_host_is_rejected_before_any_request(self):
        transport = _Transport()
        client = _client(
            transport,
            site_url="https://evil.example.com",
            allowed_hosts="app.infisical.com",
        )
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(client.refresh())
        self.assertEqual(transport.calls, [])
        self.assertEqual(client.status()["last_error"], "host_not_allowed")

    def test_placeholder_policy_uses_remote_value(self):
        client = _client()
        with (
            patch.object(settings, "secrets_backend", "infisical"),
            patch.object(
                settings, "app_secret_key", "change-me-to-a-secure-random-secret"
            ),
            patch.object(settings, "session_secret", "session-secret"),
            patch.object(settings, "postgres_password", "postgres-secret"),
            patch.object(settings, "litellm_master_key", "litellm-secret"),
            patch.object(settings, "s3_secret_key", "s3-secret"),
            patch.object(secret_core, "get_infisical_client", return_value=client),
            patch.dict(os.environ, _CREDENTIALS, clear=True),
        ):
            bad = secret_core.placeholder_secrets()
        self.assertNotIn("APP_SECRET_KEY", bad)

    def test_settings_defaults_and_environment_override(self):
        with patch.dict(os.environ, {}, clear=True):
            loaded = Settings()
        self.assertEqual(loaded.secrets_backend, "docker")
        self.assertEqual(loaded.infisical_site_url, "https://app.infisical.com")
        self.assertEqual(
            loaded.infisical_allowed_hosts, "app.infisical.com,eu.infisical.com"
        )
        with patch.dict(os.environ, {"SECRETS_BACKEND": "infisical"}, clear=True):
            self.assertEqual(Settings().secrets_backend, "infisical")


class InfisicalPreflightTests(unittest.TestCase):
    def test_preflight_reports_infisical_without_values(self):
        client = _client()
        with (
            patch.object(settings, "secrets_backend", "infisical"),
            patch.object(settings, "infisical_project_id", "project-1"),
            patch.object(settings, "creator_email", ""),
            patch.object(settings, "creator_public_key", ""),
            patch.object(settings, "creator_gateway_secret", ""),
            patch.object(settings, "creator_email_transport", "log"),
            patch.object(settings, "artex_enabled", False),
            patch.object(secret_core, "get_infisical_client", return_value=client),
            patch.object(
                deployment_preflight, "get_infisical_client", return_value=client
            ),
            patch.dict(os.environ, {}, clear=True),
        ):
            report = deployment_preflight.check_deployment()
        names = {check["name"] for check in report["checks"]}
        for expected in (
            "secrets_backend",
            "infisical_host",
            "infisical_credentials",
            "infisical_project",
            "infisical_reachability",
        ):
            self.assertIn(expected, names)
        self.assertNotIn("remote-app-secret", repr(report))
        credential = next(
            check for check in report["checks"] if check["name"] == "infisical_credentials"
        )
        self.assertEqual(credential["status"], "blocker")


if __name__ == "__main__":
    unittest.main()
