"""Doc 29 P2 tests: DOM/visual understanding, extraction provenance and tab coordination."""

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from app.api.routes import browser_intelligence as intelligence_routes
from app.core.config import settings
from app.services.browser_intelligence_service import (
    PAGE_UNDERSTANDING_SCRIPT,
    SCRIPTS,
    BrowserIntelligenceError,
    BrowserIntelligenceService,
    TesseractOcrAdapter,
    png_dimensions,
)

PNG = (
    b"\x89PNG\r\n\x1a\n"
    + (13).to_bytes(4, "big")
    + b"IHDR"
    + (2).to_bytes(4, "big")
    + (3).to_bytes(4, "big")
    + b"\x00" * 8
)

STRUCTURE = {
    "url": "https://example.com",
    "title": "Example Domain",
    "language": "en",
    "headings": ["Example Domain"],
    "landmarks": [{"role": "main", "name": ""}],
    "interactive": [
        {"tag": "a", "role": "link", "name": "More information",
         "type": "", "disabled": False, "rect": {"x": 1, "y": 2, "width": 3, "height": 4}}
    ],
    "forms": [],
    "alerts": [],
    "pagination": [],
    "meta": {"description": "example", "canonical": "", "json_ld": False},
    "viewport": {"width": 1280, "height": 720, "scroll_height": 900},
    "text_preview": "Example Domain This domain is for use in documentation.",
}

DATA = {
    "tables": [{"index": 0, "caption": "", "headers": ["A"], "rows": [["1"]]}],
    "listings": [{"index": 0, "text": "Plan A", "url": "https://example.com/a", "tag": "article"}],
    "links": [{"text": "More", "url": "https://example.com/more"}],
    "metadata": {"title": "Example Domain", "description": "example"},
}


class FakePage:
    def __init__(self, structure=None, data=None):
        self.structure = structure or STRUCTURE
        self.data = data or DATA
        self.url = "https://example.com"

    async def evaluate(self, script):
        if script == PAGE_UNDERSTANDING_SCRIPT:
            return self.structure
        for kind, source in SCRIPTS.items():
            if script == source:
                return self.data.get(kind, [])
        return []

    async def screenshot(self):
        return PNG


def service_with(page):
    service = BrowserIntelligenceService(object())
    service.evidence = MagicMock()
    service.evidence.record_evidence = AsyncMock(return_value="evidence-1")
    service.evidence.append_audit = AsyncMock(return_value="audit-1")
    service.evidence.envelope = AsyncMock(return_value={
        "task_id": "task-1", "status": "completed", "evidence_refs": ["evidence-1"],
        "actor": "sdk", "actor_type": "agent",
    })
    return service, patch(
        "app.services.browser_intelligence_service.browser_service.get_persistent_page",
        new_callable=AsyncMock,
        return_value=page,
    )


class HelpersTests(unittest.TestCase):
    def test_png_dimensions_and_invalid_payload(self):
        self.assertEqual(png_dimensions(PNG), {"width": 2, "height": 3})
        self.assertIsNone(png_dimensions(b"not-a-png"))

    def test_page_script_never_captures_input_values(self):
        self.assertNotIn(".value", PAGE_UNDERSTANDING_SCRIPT)
        self.assertIn("aria-label", PAGE_UNDERSTANDING_SCRIPT)


class BrowserIntelligenceTests(unittest.IsolatedAsyncioTestCase):
    async def test_understanding_is_semantic_and_records_evidence(self):
        service, page_patch = service_with(FakePage())
        with page_patch:
            result = await service.understand("session-1", task_id="task-1")
        self.assertEqual(result["title"], "Example Domain")
        self.assertEqual(result["visual"]["dimensions"], {"width": 2, "height": 3})
        self.assertTrue(result["untrusted"])
        self.assertTrue(result["digest"])
        self.assertEqual(result["envelope"]["evidence_refs"], ["evidence-1"])
        service.evidence.record_evidence.assert_awaited_once()
        service.evidence.append_audit.assert_awaited_once()

    async def test_extraction_has_provenance_and_independent_verification(self):
        service, page_patch = service_with(FakePage())
        with page_patch:
            extracted = await service.extract("session-1", "auto")
            matching = await service.verify_extraction(
                "session-1", {"kind": "auto", "digest": extracted["digest"]}
            )
            mismatching = await service.verify_extraction(
                "session-1", {"kind": "auto", "digest": "wrong"}
            )
        self.assertEqual(extracted["source"]["url"], "https://example.com")
        self.assertEqual(set(extracted["data"]), set(SCRIPTS))
        self.assertTrue(extracted["untrusted"])
        self.assertTrue(matching["verified"])
        self.assertFalse(mismatching["verified"])

    async def test_ocr_is_opt_in_and_fails_closed(self):
        service, page_patch = service_with(FakePage())
        with page_patch:
            with patch.object(settings, "browser_ocr_enabled", False):
                disabled = await service.understand("session-1")
            self.assertIsNone(disabled["ocr"])

            fake_ocr = MagicMock()
            fake_ocr.recognize = AsyncMock(return_value={
                "engine": "tesseract", "available": False,
                "reason": "TesseractNotFoundError",
            })
            service.ocr = fake_ocr
            with patch.object(settings, "browser_ocr_enabled", True):
                enabled = await service.understand("session-1", task_id="task-1")
        self.assertFalse(enabled["ocr"]["available"])
        self.assertNotIn("text", enabled["ocr"])
        source = service.evidence.record_evidence.await_args.kwargs["source_metadata"]
        self.assertFalse(source["ocr"]["available"])

    async def test_ocr_adapter_reports_missing_library(self):
        with patch(
            "app.services.browser_intelligence_service.importlib.util.find_spec",
            return_value=None,
        ):
            result = await TesseractOcrAdapter().recognize(PNG)
        self.assertFalse(result["available"])
        self.assertNotIn("text", result)

    async def test_unknown_kind_is_denied(self):
        service, page_patch = service_with(FakePage())
        with page_patch:
            with self.assertRaises(BrowserIntelligenceError):
                await service.extract("session-1", "secrets")

    async def test_unknown_tab_is_denied(self):
        service, _ = service_with(FakePage())
        with patch(
            "app.services.browser_intelligence_service.browser_service.get_tab",
            new_callable=AsyncMock,
            return_value=None,
        ):
            with self.assertRaises(BrowserIntelligenceError):
                await service.coordinate_tabs(
                    "session-1", [{"action": "click", "target": "button", "tab_id": "missing"}]
                )

    async def test_tab_coordination_uses_requested_tab(self):
        service, _ = service_with(FakePage())
        with patch(
            "app.services.browser_intelligence_service.browser_service.get_tab",
            new_callable=AsyncMock,
            return_value=object(),
        ), patch(
            "app.services.browser_intelligence_service.browser_service.interact",
            new_callable=AsyncMock,
            return_value={"success": True},
        ) as interact:
            result = await service.coordinate_tabs(
                "session-1", [{"action": "click", "target": "button", "tab_id": "tab-7"}],
                task_id="task-1",
            )
        self.assertTrue(result["verified"])
        self.assertEqual(interact.await_args.kwargs["tab_id"], "tab-7")


class RouteTests(unittest.IsolatedAsyncioTestCase):
    async def test_understand_route_delegates(self):
        payload = intelligence_routes.UnderstandRequest(session_token="session-1")
        request = SimpleNamespace(state=SimpleNamespace(credential=None))
        with patch.object(intelligence_routes, "BrowserIntelligenceService") as service_cls:
            service_cls.return_value.understand = AsyncMock(return_value={"digest": "d"})
            result = await intelligence_routes.understand(payload, request, object())
        self.assertEqual(result["digest"], "d")

    async def test_admin_scope_covers_intelligence_routes(self):
        from app.core.auth_policy import required_scope

        self.assertEqual(
            required_scope("/api/v1/browser/intelligence/extract"), "admin"
        )


if __name__ == "__main__":
    unittest.main()
