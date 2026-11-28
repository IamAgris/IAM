"""Regression tests for the four critical CodeQL SSRF findings.

Covers the shared pinned egress transport and each of the four call sites:
HBI HTTP fetcher, Tor onion availability, x402 discovery and browser documents.
No test performs a real network request.
"""

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.config import settings
from app.services.blockchain.providers.base import ProviderDenied
from app.services.blockchain.x402 import X402Service
from app.services.browser_document_service import (
    BrowserDocumentService,
    DocumentParsingError,
)
from app.services.hbi import http_fetcher
from app.services.iics.egress import (
    EgressGateway,
    PinnedFetchResult,
    _PinnedHTTPConnection,
    _PinnedHTTPSConnection,
    _http_request,
)
from app.services.tor_privacy import OnionServiceIntelligence

PUBLIC_IP = "93.184.216.34"
VALID_ONION = "a" * 56 + ".onion"


def public_gateway(**kwargs):
    return EgressGateway(resolver=lambda _: [PUBLIC_IP], **kwargs)


def fake_result(**kwargs) -> PinnedFetchResult:
    defaults = {
        "ok": True,
        "url": "https://example.com/api",
        "status_code": 200,
        "content_type": "text/plain",
        "body": b"public body",
    }
    defaults.update(kwargs)
    return PinnedFetchResult(**defaults)


class PinnedTransportTests(unittest.TestCase):
    def test_mixed_public_private_dns_answers_are_denied(self):
        gateway = EgressGateway(resolver=lambda _: [PUBLIC_IP, "10.0.0.5"])
        decision = gateway.assess("https://example.com/doc")
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "internal_or_metadata_address")

    def test_http_connect_uses_the_validated_address(self):
        with patch("app.services.iics.egress.socket.create_connection") as create:
            conn = _PinnedHTTPConnection("example.com", None, PUBLIC_IP, 5.0)
            conn.connect()
        create.assert_called_once()
        self.assertEqual(create.call_args.args[0], (PUBLIC_IP, 80))

    def test_https_pinning_preserves_tls_hostname_verification(self):
        context = MagicMock()
        with patch("app.services.iics.egress.socket.create_connection") as create:
            conn = _PinnedHTTPSConnection("example.com", 443, PUBLIC_IP, 5.0, context)
            conn.connect()
        create.assert_called_once()
        self.assertEqual(create.call_args.args[0], (PUBLIC_IP, 443))
        context.wrap_socket.assert_called_once()
        self.assertEqual(
            context.wrap_socket.call_args.kwargs["server_hostname"], "example.com"
        )

    def test_response_body_is_capped(self):
        class FakeResponse:
            status = 200

            def __init__(self):
                self.chunks = [b"a" * 100, b"b" * 100]

            def read(self, amount):
                return self.chunks.pop(0)[:amount] if self.chunks else b""

            def getheader(self, name):
                return "text/plain" if name.lower() == "content-type" else ""

            def getheaders(self):
                return [("Content-Type", "text/plain")]

        class FakeConnection:
            def __init__(self, *_args, **_kwargs):
                pass

            def request(self, *_args, **_kwargs):
                return None

            def getresponse(self):
                return FakeResponse()

            def close(self):
                return None

        with patch("app.services.iics.egress._PinnedHTTPConnection", FakeConnection):
            result = _http_request(
                "http://example.com/a", PUBLIC_IP, timeout=5.0, max_bytes=150
            )
        self.assertTrue(result.truncated)
        self.assertEqual(len(result.body), 150)


class RedirectTests(unittest.IsolatedAsyncioTestCase):
    async def test_redirect_to_internal_target_is_denied(self):
        gateway = public_gateway(max_redirects=3)
        redirect = fake_result(
            status_code=302, redirect_location="http://169.254.169.254/latest/meta-data"
        )
        with patch("app.services.iics.egress._http_request", return_value=redirect) as req:
            result = await gateway.fetch_pinned("https://example.com/start")
        self.assertFalse(result.ok)
        self.assertIn("egress_denied", result.error)
        self.assertEqual(req.call_count, 1)

    async def test_public_redirect_is_reassessed_and_followed(self):
        gateway = public_gateway(max_redirects=3)
        redirect = fake_result(status_code=302, redirect_location="/final")
        final = fake_result(url="https://example.com/final", body=b"done")
        with patch(
            "app.services.iics.egress._http_request", side_effect=[redirect, final]
        ) as req:
            result = await gateway.fetch_pinned("https://example.com/start")
        self.assertTrue(result.ok)
        self.assertEqual(result.url, "https://example.com/final")
        self.assertEqual(result.body, b"done")
        self.assertEqual(req.call_count, 2)


class X402Tests(unittest.IsolatedAsyncioTestCase):
    async def _enabled(self):
        patcher = patch.object(settings, "web3_x402_enabled", True)
        patcher.start()
        self.addCleanup(patcher.stop)

    async def test_internal_and_metadata_targets_are_denied(self):
        await self._enabled()
        for url in (
            "http://169.254.169.254/latest/meta-data/",
            "http://127.0.0.1:8080/admin",
            "http://metadata.google.internal/computeMetadata/v1/",
            "file:///etc/passwd",
        ):
            with self.subTest(url=url), self.assertRaises(ProviderDenied):
                await X402Service().discover(url)

    async def test_configured_host_allowlist_is_enforced(self):
        await self._enabled()
        patcher = patch.object(settings, "web3_x402_allowed_hosts", "api.example.com")
        patcher.start()
        self.addCleanup(patcher.stop)
        with self.assertRaises(ProviderDenied):
            await X402Service().discover("https://unapproved.example/api")

    async def test_discovery_uses_pinned_gateway_and_untrusted_response(self):
        await self._enabled()
        result = fake_result(
            status_code=402,
            headers={"x-price": "$1.00", "www-authenticate": "Bearer"},
            body=b'{"price": 1}',
        )
        with patch(
            "app.services.blockchain.x402.EgressGateway.fetch_pinned",
            new_callable=AsyncMock,
            return_value=result,
        ) as fetch:
            outcome = await X402Service().discover("https://api.example.com/pay")
        fetch.assert_awaited_once()
        self.assertTrue(outcome["paid_endpoint"])
        self.assertEqual(outcome["challenge_headers"]["x-price"], "$1.00")
        self.assertTrue(outcome["untrusted"])


class BrowserDocumentTests(unittest.IsolatedAsyncioTestCase):
    async def test_direct_internal_target_is_denied_before_network(self):
        service = BrowserDocumentService(object())
        with self.assertRaises(DocumentParsingError):
            await service.fetch("http://169.254.169.254/latest/meta-data/")

    async def test_fetch_uses_pinned_gateway_result(self):
        result = fake_result(
            url="https://example.com/final.txt", content_type="text/plain"
        )
        with patch(
            "app.services.browser_document_service.EgressGateway.fetch_pinned",
            new_callable=AsyncMock,
            return_value=result,
        ) as fetch:
            body, final_url, content_type = await BrowserDocumentService(object()).fetch(
                "https://example.com/report.txt"
            )
        fetch.assert_awaited_once()
        self.assertEqual(body, b"public body")
        self.assertEqual(final_url, "https://example.com/final.txt")
        self.assertEqual(content_type, "text/plain")


class HbiFetcherTests(unittest.IsolatedAsyncioTestCase):
    async def test_internal_targets_are_denied_by_json_and_document_fetch(self):
        for call in (http_fetcher.fetch_json, http_fetcher.fetch):
            with self.subTest(call=call.__name__), self.assertRaises(ValueError):
                call("http://169.254.169.254/latest/meta-data/")

    async def test_robots_and_document_use_pinned_transport(self):
        robots = fake_result(body=b"User-agent: *\nAllow: /")
        document = fake_result(url="https://example.com/doc.txt", body=b"allowed text")
        with (
            patch(
                "app.services.iics.egress.socket.getaddrinfo",
                new=lambda *_a, **_k: [(2, 1, 6, "", (PUBLIC_IP, 0))],
            ),
            patch.object(
                http_fetcher.EgressGateway,
                "fetch_pinned_sync",
                side_effect=[robots, document],
            ) as fetch,
        ):
            result = http_fetcher.fetch("https://example.com/doc.txt")
        self.assertEqual(fetch.call_count, 2)
        self.assertEqual(result["text"], "allowed text")
        self.assertTrue(result["robots_allowed"])


class TorPrivacyTests(unittest.IsolatedAsyncioTestCase):
    def _service(self):
        service = OnionServiceIntelligence(object())
        service.db = SimpleNamespace(commit=AsyncMock(return_value=None))
        service.evidence = MagicMock()
        service.evidence.append_audit = AsyncMock(return_value="audit-1")
        return service

    async def test_invalid_onion_address_opens_no_client(self):
        client = MagicMock()
        with (
            patch.object(settings, "tor_enabled", True),
            patch.object(settings, "tor_onion_access_enabled", True),
            patch("app.services.tor_privacy.httpx.AsyncClient", client),
        ):
            result = await self._service().check_availability("a" * 16 + ".onion")
        self.assertFalse(result["reachable"])
        client.assert_not_called()

    async def test_valid_onion_uses_fixed_loopback_proxy(self):
        instances = []

        class FakeClient:
            def __init__(self, **kwargs):
                self.kwargs = kwargs
                instances.append(self)

            async def __aenter__(self):
                return self

            async def __aexit__(self, *_args):
                return None

            async def get(self, url):
                return SimpleNamespace(status_code=200, content=b"ok")

        with (
            patch.object(settings, "tor_enabled", True),
            patch.object(settings, "tor_onion_access_enabled", True),
            patch("app.services.tor_privacy.httpx.AsyncClient", FakeClient),
        ):
            result = await self._service().check_availability(VALID_ONION)
        self.assertTrue(result["reachable"])
        self.assertEqual(
            instances[0].kwargs["proxy"],
            f"socks5://127.0.0.1:{settings.tor_socks_port}",
        )


if __name__ == "__main__":
    unittest.main()
