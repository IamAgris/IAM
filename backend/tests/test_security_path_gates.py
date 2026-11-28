"""Regression tests for the containment gates added for the CodeQL findings."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.config import settings
from app.services.aegis import AegisEngine
from app.services.browser_security_gateway import (
    BrowserSecurityGateway,
    BrowserSecurityGatewayError,
)
from app.services.hbi.corpus import load_manifest
from app.services.iics.search_strategy import split_subquestions
from app.services.path_safety import UnsafePathError, contained_path, safe_child_name
from app.services.tor_intelligence import TorManager, TorUnavailable


class ContainmentHelperTests(unittest.TestCase):
    def test_contained_path_rejects_traversal_and_outside_absolute(self) -> None:
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as outside:
            self.assertTrue(contained_path(root, "child/file.txt").is_absolute())
            for candidate in ("../file.txt", outside, str(Path(outside) / "file.txt")):
                with self.assertRaises(UnsafePathError):
                    contained_path(root, candidate)

    def test_safe_child_name_rejects_separators(self) -> None:
        self.assertEqual(safe_child_name("s1"), "s1")
        for name in ("..", ".", "a/b", "a\\b", "/tmp/x", ""):
            with self.assertRaises(UnsafePathError):
                safe_child_name(name)


class AegisAuditTests(unittest.TestCase):
    def test_audit_path_refuses_outside_root(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            outside = Path(tempfile.gettempdir()) / "iam-audit-outside.txt"
            outside.write_text("x", encoding="utf-8")
            try:
                result = AegisEngine().audit_path(str(outside), root=root)
                self.assertIn(
                    "path_outside_audit_root", [i["type"] for i in result["issues"]]
                )
            finally:
                outside.unlink(missing_ok=True)

    def test_audit_path_accepts_contained_file(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            inside = Path(root) / "inside.txt"
            inside.write_text("x", encoding="utf-8")
            result = AegisEngine().audit_path(str(inside), root=root)
            self.assertNotIn(
                "path_outside_audit_root", [i["type"] for i in result["issues"]]
            )


class QuarantineGateTests(unittest.IsolatedAsyncioTestCase):
    async def test_source_outside_evidence_root_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as evidence, tempfile.TemporaryDirectory() as outside:
            with patch.object(settings, "browser_evidence_dir", evidence):
                gateway = BrowserSecurityGateway(object())
                gateway.evidence = MagicMock()
                gateway.evidence.append_audit = AsyncMock(return_value="audit")
                source = Path(outside) / "payload.bin"
                source.write_bytes(b"x")
                with self.assertRaises(BrowserSecurityGatewayError):
                    await gateway.quarantine_download(str(source))


class CorpusGateTests(unittest.TestCase):
    def test_manifest_outside_root_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as outside:
            manifest = Path(outside) / "manifest.json"
            manifest.write_text("[]", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_manifest(str(manifest), root)


class TorSessionIdTests(unittest.IsolatedAsyncioTestCase):
    async def test_traversal_session_id_is_rejected(self) -> None:
        with patch.object(settings, "tor_enabled", True), patch.object(settings, "tor_data_root", ""):
            manager = TorManager(object())
            with self.assertRaises(TorUnavailable):
                await manager.open_session("../escape")


class SubquestionSplitTests(unittest.TestCase):
    def test_long_whitespace_input_is_bounded(self) -> None:
        parts = split_subquestions("word " * 20000)
        self.assertEqual(len(parts), 1)

    def test_join_words_and_question_marks(self) -> None:
        self.assertEqual(
            split_subquestions("what is X and how does Y work?"),
            ["what is X", "how does Y work"],
        )
