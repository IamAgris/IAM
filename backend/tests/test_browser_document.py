"""Doc 29 P2 tests: local document parsing with SSRF guard and provenance."""

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from app.api.routes import browser_intelligence as intelligence_routes
from app.services.browser_document_service import (
    BrowserDocumentService,
    DocumentParsingError,
    detect_kind,
    is_public_url,
)


def public_dns(*_args, **_kwargs):
    return [(2, 1, 6, "", ("93.184.216.34", 0))]


class UrlGuardTests(unittest.IsolatedAsyncioTestCase):
    async def test_public_url_accepted_with_dns(self):
        with patch(
            "app.services.browser_document_service.socket.getaddrinfo", new=public_dns
        ):
            self.assertTrue(await is_public_url("https://example.com/report.pdf"))

    async def test_private_and_non_http_targets_rejected(self):
        self.assertFalse(await is_public_url("http://127.0.0.1/admin"))
        self.assertFalse(await is_public_url("http://localhost/secret"))
        self.assertFalse(await is_public_url("file:///etc/passwd"))
        self.assertFalse(await is_public_url("http://user:pass@example.com/a"))


class ParsingTests(unittest.TestCase):
    def test_detect_kind(self):
        self.assertEqual(detect_kind("a.pdf"), "pdf")
        self.assertEqual(detect_kind("b", "application/pdf"), "pdf")
        self.assertEqual(detect_kind("c.docx"), "docx")
        self.assertEqual(detect_kind("d.xlsx"), "xlsx")
        self.assertEqual(detect_kind("e.html"), "html")
        self.assertEqual(detect_kind("f.txt"), "text")
        with self.assertRaises(DocumentParsingError):
            detect_kind("payload.exe")

    def test_plain_and_html_parsing(self):
        service = BrowserDocumentService(object())
        self.assertEqual(service.parse(b"hello world", "a.txt")["text"], "hello world")
        html = service.parse(b"<html><body><p>Hello <b>world</b></p></body></html>", "a.html")
        self.assertIn("Hello world", html["text"])
        self.assertTrue(html["untrusted"])

    def test_pdf_docx_xlsx_parsers(self):
        service = BrowserDocumentService(object())
        pages = [MagicMock(extract_text=lambda: "PDF text")]
        reader = MagicMock()
        reader.pages = pages
        with patch("app.services.browser_document_service.PdfReader", return_value=reader):
            pdf = service.parse(b"%PDF-fake", "a.pdf")
        self.assertEqual(pdf["kind"], "pdf")
        self.assertIn("PDF text", pdf["text"])

        document = MagicMock()
        document.paragraphs = [SimpleNamespace(text="Doc paragraph")]
        document.tables = []
        with patch("app.services.browser_document_service.Document", return_value=document):
            docx = service.parse(b"fake", "b.docx")
        self.assertIn("Doc paragraph", docx["text"])

        sheet = MagicMock()
        sheet.iter_rows.return_value = [("A1", "B1"), ("A2", "B2")]
        workbook = MagicMock()
        workbook.sheetnames = ["Sheet1"]
        workbook.__getitem__.return_value = sheet
        with patch("app.services.browser_document_service.load_workbook", return_value=workbook):
            xlsx = service.parse(b"fake", "c.xlsx")
        self.assertEqual(xlsx["kind"], "xlsx")
        self.assertEqual(xlsx["sheets"]["Sheet1"][0], ["A1", "B1"])


class ParseUrlTests(unittest.IsolatedAsyncioTestCase):
    async def test_provenance_evidence_and_envelope(self):
        service = BrowserDocumentService(object())
        service.evidence = MagicMock()
        service.evidence.record_evidence = AsyncMock(return_value="evidence-1")
        service.evidence.append_audit = AsyncMock(return_value="audit-1")
        service.evidence.envelope = AsyncMock(return_value={
            "task_id": "task-1", "status": "verifying", "evidence_refs": ["evidence-1"],
        })
        with patch.object(
            service, "fetch",
            new_callable=AsyncMock,
            return_value=(
                b"public report",
                "https://example.com/report.txt",
                "text/plain",
            ),
        ):
            result = await service.parse_url(
                "https://example.com/report.txt", task_id="task-1", actor="iam"
            )
        self.assertEqual(result["source"]["url"], "https://example.com/report.txt")
        self.assertEqual(len(result["source"]["sha256"]), 64)
        self.assertEqual(result["text"], "public report")
        self.assertTrue(result["untrusted"])
        self.assertEqual(result["envelope"]["evidence_refs"], ["evidence-1"])
        service.evidence.append_audit.assert_awaited_once()

    async def test_blocked_url_is_denied_before_fetch(self):
        service = BrowserDocumentService(object())
        with self.assertRaises(DocumentParsingError):
            await service.parse_url("http://127.0.0.1/secret")


class RouteTests(unittest.IsolatedAsyncioTestCase):
    async def test_document_route_delegates(self):
        payload = intelligence_routes.DocumentRequest(url="https://example.com/a.txt")
        request = SimpleNamespace(state=SimpleNamespace(credential=None))
        with patch.object(intelligence_routes, "BrowserDocumentService") as service_cls:
            service_cls.return_value.parse_url = AsyncMock(return_value={"kind": "text"})
            result = await intelligence_routes.parse_document(payload, request, object())
        self.assertEqual(result["kind"], "text")


if __name__ == "__main__":
    unittest.main()
