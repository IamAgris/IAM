"""Tests for the locally closable implementation gaps."""

import asyncio
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from fastapi import HTTPException

from app.api.routes.knowledge import (
    KnowledgeContributionCreate,
    validate_contribution,
)
from app.core.auth_policy import required_scope
from app.core.config import settings
from app.services.event_stream import audit_event_payload, format_sse, parse_since
from app.services.skillruntime.service import (
    _skill_limiters,
    audit_log_chunks,
    check_invocation_limit,
)


class KnowledgeContributionTests(unittest.TestCase):
    def test_valid_contribution_passes(self):
        validate_contribution(
            KnowledgeContributionCreate(title="A fact", content="With a source")
        )

    def test_title_and_content_required(self):
        with self.assertRaises(HTTPException) as empty_title:
            validate_contribution(KnowledgeContributionCreate(title="  ", content="x"))
        self.assertEqual(empty_title.exception.status_code, 400)
        with self.assertRaises(HTTPException) as empty_content:
            validate_contribution(KnowledgeContributionCreate(title="x", content=""))
        self.assertEqual(empty_content.exception.status_code, 400)

    def test_confidence_bounds(self):
        for value in (-0.1, 1.1):
            with self.assertRaises(HTTPException):
                validate_contribution(
                    KnowledgeContributionCreate(
                        title="x", content="y", confidence_level=value
                    )
                )

    def test_contribution_model_cannot_encode_verification_status(self):
        self.assertNotIn("verification_status", KnowledgeContributionCreate.model_fields)


class EventStreamTests(unittest.TestCase):
    def test_parse_since_accepts_zulu_and_naive(self):
        expected = datetime(2026, 11, 25, tzinfo=timezone.utc)
        self.assertEqual(parse_since("2026-11-25T00:00:00Z"), expected)
        self.assertEqual(parse_since("2026-11-25T00:00:00"), expected)
        self.assertIsNone(parse_since(None))

    def test_format_sse_is_single_line_json(self):
        frame = format_sse("audit", {"event_type": "x", "details": {"a": 1}})
        self.assertTrue(frame.startswith("event: audit\n"))
        data = frame.split("data: ", 1)[1].strip()
        self.assertIn('"event_type":"x"', data)
        self.assertEqual(len(data.splitlines()), 1)

    def test_payload_serialises_untrusted_details(self):
        class Row:
            id = "abc"
            event_type = "skill_runtime_log"
            actor = "iam"
            target = "exec-1"
            details = {"stream": "stdout"}
            created_at = datetime(2026, 11, 25, tzinfo=timezone.utc)

        payload = audit_event_payload(Row())
        self.assertEqual(payload["id"], "abc")
        self.assertEqual(payload["details"], {"stream": "stdout"})
        self.assertTrue(payload["created_at"].endswith("+00:00"))


class SkillRuntimeGapTests(unittest.TestCase):
    def test_audit_chunks_preserve_all_output(self):
        content = "x" * 25 + "y" * 25
        chunks = audit_log_chunks("stdout", content, chunk_size=10)
        self.assertEqual("".join(c["content"] for c in chunks), content)
        self.assertEqual([c["sequence"] for c in chunks], [0, 1, 2, 3, 4])
        self.assertTrue(all(len(c["content"]) <= 10 for c in chunks))

    def test_per_skill_limit_memory_backend(self):
        _skill_limiters.clear()
        with patch.object(settings, "rate_limit_backend", "memory"), patch.object(
            settings, "skill_runtime_per_skill_limit_per_minute", 1
        ):
            self.assertTrue(asyncio.run(check_invocation_limit("s1", "caller")))
            self.assertFalse(asyncio.run(check_invocation_limit("s1", "caller")))
            self.assertTrue(asyncio.run(check_invocation_limit("s2", "caller")))

    def test_new_paths_require_operator_scope(self):
        self.assertEqual(required_scope("/api/v1/events"), "operator")
        self.assertEqual(required_scope("/api/v1/knowledge/contributions"), "operator")

    def test_policy_reports_network_posture(self):
        from app.api.routes.skillruntime import policy

        with patch.object(settings, "skill_runtime_network_enabled", False):
            self.assertFalse(asyncio.run(policy())["network_execution"])
        with patch.object(settings, "skill_runtime_network_enabled", True), patch.object(
            settings, "skill_runtime_network_name", "iam-skills-egress"
        ):
            status = asyncio.run(policy())
            self.assertTrue(status["network_execution"])
            self.assertEqual(status["network_name"], "iam-skills-egress")


if __name__ == "__main__":
    unittest.main()
