"""IICS foundation tests — egress, permissions, budget, source TTL and QA.

Pending proposal overlay; no new top-level system and no new queue.
"""

import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.iics import (
    BudgetGovernor,
    BudgetLimit,
    BenchmarkCase,
    AdvisoryIngestor,
    BenchmarkSuite,
    ConfidenceCalibrator,
    CredentialRef,
    CredentialRotationPolicy,
    DLPEngine,
    CreatorEmailBridge,
    EgressGateway,
    MediaDocumentService,
    PermissionGate,
    ScheduledResearchError,
    ScheduledResearchService,
    SourceRegistry,
    sanitize_metadata,
    StrategySelector,
    label_for_confidence,
)


def public_gateway(**kwargs):
    return EgressGateway(resolver=lambda _: ["93.184.216.34"], **kwargs)


class EgressGatewayTests(unittest.TestCase):
    def test_public_host_allowed(self):
        decision = public_gateway().assess("https://example.com/docs")
        self.assertTrue(decision.allowed)
        self.assertEqual(decision.address, "93.184.216.34")

    def test_internal_address_blocked(self):
        gateway = EgressGateway(resolver=lambda _: ["10.0.0.5"])
        decision = gateway.assess("https://internal.example.test")
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "internal_or_metadata_address")

    def test_loopback_literal_blocked(self):
        decision = public_gateway().assess("http://127.0.0.1/latest/meta-data")
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "ip_literal_not_allowlisted")

    def test_metadata_hostname_blocked(self):
        decision = public_gateway().assess("http://metadata.google.internal/")
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "blocked_hostname")

    def test_credentials_in_url_blocked(self):
        decision = public_gateway().assess("https://user:pass@example.com")
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "credentials_in_url")

    def test_unsupported_scheme_blocked(self):
        decision = public_gateway().assess("file:///etc/passwd")
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "unsupported_scheme")

    def test_allowlist_denies_other_hosts(self):
        gateway = EgressGateway(
            allowed_hosts=["example.com"], resolver=lambda _: ["93.184.216.34"]
        )
        self.assertTrue(gateway.assess("https://example.com").allowed)
        self.assertFalse(gateway.assess("https://other.com").allowed)

    def test_dns_failure_fails_closed(self):
        gateway = EgressGateway(resolver=lambda _: [])
        self.assertFalse(gateway.assess("https://example.com").allowed)

    def test_decision_serialises_for_audit(self):
        decision = public_gateway().assess("https://example.com")
        self.assertIn("allowed", decision.as_dict())
        self.assertEqual(decision.as_dict()["policy_version"], "iics-egress-1")


class ConfidenceTests(unittest.TestCase):
    def test_thresholds(self):
        self.assertEqual(label_for_confidence(0.2), "unverified")
        self.assertEqual(label_for_confidence(0.55), "provisional")
        self.assertEqual(label_for_confidence(0.7), "verified")


class BudgetTests(unittest.TestCase):
    def test_within_budget(self):
        allowed, reason = BudgetGovernor.check(
            {"actions": 1, "bytes": 10, "cost_units": 0}, BudgetLimit(max_actions=2)
        )
        self.assertTrue(allowed)
        self.assertEqual(reason, "within_budget")

    def test_action_budget_exhausted(self):
        allowed, reason = BudgetGovernor.check(
            {"actions": 2, "bytes": 0, "cost_units": 0}, BudgetLimit(max_actions=2)
        )
        self.assertFalse(allowed)
        self.assertEqual(reason, "action_budget_exhausted")

    def test_cost_budget_exhausted(self):
        allowed, reason = BudgetGovernor.check(
            {"actions": 1, "bytes": 0, "cost_units": 1}, BudgetLimit(max_cost_units=1)
        )
        self.assertFalse(allowed)
        self.assertEqual(reason, "cost_budget_exhausted")


class SourceFreshnessTests(unittest.TestCase):
    @staticmethod
    def _row(freshness_class, last_checked=None, revoked=False):
        return SimpleNamespace(
            revoked_at=datetime.now(timezone.utc) if revoked else None,
            expires_at=None,
            last_checked_at=last_checked,
            created_at=datetime.now(timezone.utc) - timedelta(days=1),
            freshness_class=freshness_class,
        )

    def test_volatile_expires(self):
        old = datetime.now(timezone.utc) - timedelta(hours=25)
        self.assertFalse(SourceRegistry.is_fresh(self._row("volatile", old)))

    def test_stable_remains_fresh(self):
        old = datetime.now(timezone.utc) - timedelta(days=2)
        self.assertTrue(SourceRegistry.is_fresh(self._row("stable", old)))

    def test_revoked_is_not_fresh(self):
        self.assertFalse(SourceRegistry.is_fresh(self._row("stable", revoked=True)))


class PermissionGateTests(unittest.IsolatedAsyncioTestCase):
    @staticmethod
    def _gate(internet_decision, legal_decision):
        internet = MagicMock()
        internet.check_internet_permission_only = AsyncMock(return_value=internet_decision)
        legal = MagicMock()
        legal.store = MagicMock()
        legal.store.get_source = AsyncMock(return_value={"id": "src-1"})
        legal.register_source = AsyncMock()
        legal.gate_check = AsyncMock(return_value=legal_decision)
        return PermissionGate(object(), internet_service=internet, legal_service=legal)

    async def test_free_public_research_is_autonomous(self):
        gate = self._gate(
            {"permitted": True, "category": "exploration"},
            {"decision": "APPROVED", "decision_class": "LOW", "conditions": []},
        )
        result = await gate.authorize("browse_public", "https://example.com")
        self.assertTrue(result["permitted"])
        self.assertFalse(result["approval_required"])

    async def test_consequential_action_requires_approval(self):
        gate = self._gate(
            {"permitted": False},
            {"decision": "APPROVED", "decision_class": "LOW"},
        )
        result = await gate.authorize("spend_money", "https://example.com")
        self.assertFalse(result["permitted"])
        self.assertTrue(result["approval_required"])

    async def test_legal_block_fails_closed(self):
        gate = self._gate(
            {"permitted": True, "category": "exploration"},
            {"decision": "BLOCKED", "decision_class": "HIGH", "reason": "rights unknown"},
        )
        result = await gate.authorize("browse_public", "https://example.com")
        self.assertFalse(result["permitted"])
        self.assertTrue(result["approval_required"])

    async def test_high_risk_decision_requires_approval(self):
        gate = self._gate(
            {"permitted": True},
            {"decision": "CONDITIONAL", "decision_class": "CRITICAL", "conditions": []},
        )
        result = await gate.authorize("browse_public", "https://example.com")
        self.assertTrue(result["approval_required"])

    async def test_unavailable_internet_permission_denies(self):
        gate = self._gate(
            {"permitted": False},
            {"decision": "APPROVED", "decision_class": "LOW"},
        )
        result = await gate.authorize("browse_public", "https://example.com")
        self.assertIn("not autonomously permitted", result["reason"])


class QATests(unittest.IsolatedAsyncioTestCase):
    async def test_suite_scores_and_gates(self):
        suite = BenchmarkSuite(
            [
                BenchmarkCase("a", 0.8, lambda: 0.9),
                BenchmarkCase("b", 0.9, lambda: 0.5),
            ]
        )
        results = await suite.run()
        self.assertTrue(results[0]["passed"])
        self.assertFalse(results[1]["passed"])

    def test_regression_gate_detects_drop(self):
        allowed, regressions = BenchmarkSuite.regression_gate(
            {"x": 0.9, "y": 0.8}, {"x": 0.7, "y": 0.8}, 0.05
        )
        self.assertFalse(allowed)
        self.assertEqual(len(regressions), 1)

    def test_builtin_egress_benchmarks_pass(self):
        from app.api.routes.iics import _builtin_cases

        async def run():
            return await BenchmarkSuite(_builtin_cases()).run()

        import asyncio

        results = asyncio.run(run())
        self.assertTrue(all(item["passed"] for item in results))


class CreatorEmailBridgeTests(unittest.IsolatedAsyncioTestCase):
    @staticmethod
    def _bridge():
        communication = MagicMock()
        communication.send_status = AsyncMock(return_value={"status": "sent"})
        approvals = MagicMock()
        approvals.create_request = AsyncMock(
            return_value={"request_id": "cr_test", "status": "pending"}
        )
        approvals.deliver_request = AsyncMock(return_value={"status": "sent"})
        return CreatorEmailBridge(
            object(), communication=communication, approvals=approvals
        ), communication, approvals

    async def test_notify_is_informational(self):
        bridge, communication, _ = self._bridge()
        result = await bridge.notify("IICS check complete", context="iics_qa")
        self.assertEqual(result["status"], "sent")
        communication.send_status.assert_awaited_once_with("IICS check complete", context="iics_qa")

    async def test_qa_alert_without_regressions_is_skipped(self):
        bridge, communication, _ = self._bridge()
        result = await bridge.qa_alert([])
        self.assertEqual(result["status"], "skipped")
        communication.send_status.assert_not_awaited()

    async def test_qa_alert_reports_regressions(self):
        bridge, communication, _ = self._bridge()
        await bridge.qa_alert(["x: 0.7 < 0.9"])
        body = communication.send_status.await_args.args[0]
        self.assertIn("x: 0.7 < 0.9", body)
        self.assertEqual(communication.send_status.await_args.kwargs["context"], "iics_qa_regression_gate")

    async def test_monitoring_digest_empty_is_skipped(self):
        bridge, communication, _ = self._bridge()
        result = await bridge.monitoring_digest([])
        self.assertEqual(result["reason"], "no_changes")
        communication.send_status.assert_not_awaited()

    async def test_monitoring_digest_sends_summary(self):
        bridge, communication, _ = self._bridge()
        await bridge.monitoring_digest([{"target": "https://example.com", "change": "updated"}])
        body = communication.send_status.await_args.args[0]
        self.assertIn("https://example.com", body)

    async def test_approval_request_uses_signed_channel(self):
        bridge, _, approvals = self._bridge()
        result = await bridge.approval_request(
            "spend_money", "Paid search tier", target_ref="provider:example"
        )
        kwargs = approvals.create_request.await_args.kwargs
        self.assertEqual(kwargs["channel"], "creator_email")
        self.assertEqual(kwargs["requester"], "iics")
        self.assertEqual(kwargs["action_type"], "spend_money")
        approvals.deliver_request.assert_awaited_once_with("cr_test")
        self.assertFalse(result["authority_bearing"])
        self.assertIn("Pending signed Creator decision", result["note"])


class ResearchStrategyTests(unittest.TestCase):
    def test_contradiction_strategy(self):
        decision = StrategySelector().select("Do these sources contradict on X?")
        self.assertEqual(decision.strategy, "contradiction_focused")

    def test_source_first_strategy(self):
        decision = StrategySelector().select("current python docs", known_domains=["docs.python.org"])
        self.assertEqual(decision.strategy, "source_first")
        self.assertIn("site:docs.python.org current python docs", decision.queries)

    def test_decomposition_strategy(self):
        decision = StrategySelector().select("what is X and how does Y work")
        self.assertEqual(decision.strategy, "query_decomposition")
        self.assertEqual(len(decision.queries), 2)

    def test_single_query_strategy(self):
        decision = StrategySelector().select("capital of France")
        self.assertEqual(decision.strategy, "single_query")


class ConfidenceCalibratorTests(unittest.TestCase):
    def test_empty_sources(self):
        self.assertEqual(ConfidenceCalibrator.score([]), 0.0)

    def test_strong_evidence_is_verified(self):
        sources = [
            {"independent": True, "primary": True, "reliability": 0.9, "age_days": 2}
            for _ in range(3)
        ]
        score = ConfidenceCalibrator.score(sources)
        self.assertGreaterEqual(score, 0.7)
        self.assertEqual(ConfidenceCalibrator.label(score), "verified")
        self.assertTrue(ConfidenceCalibrator.sufficient_for_commit(score))

    def test_contradiction_lowers_score(self):
        base = {"independent": True, "primary": True, "reliability": 0.8, "age_days": 2}
        clean = ConfidenceCalibrator.score([base, base, base])
        conflicted = ConfidenceCalibrator.score(
            [base, base, {**base, "independent": False, "contradicts": True}]
        )
        self.assertLess(conflicted, clean)


class SchedulerTests(unittest.IsolatedAsyncioTestCase):
    async def test_cadence_validation(self):
        with self.assertRaises(ScheduledResearchError):
            await ScheduledResearchService(object()).create("g", "q", cadence_minutes=1)

    async def test_worker_completes_once(self):
        from app.workers import arq_iics_worker as worker

        service = MagicMock()
        service.get = AsyncMock(
            return_value={
                "task_id": "t1",
                "query": "python docs",
                "status": "scheduled",
                "last_run_at": "2026-11-27T00:00:00+00:00",
            }
        )
        service.start = AsyncMock(return_value=True)
        service.complete = AsyncMock(return_value=True)
        service.fail = AsyncMock()

        research = MagicMock()
        research.return_value.research_topic = AsyncMock(return_value={"sources": [1, 2]})
        ledger = MagicMock()
        ledger.return_value.record = AsyncMock()

        class FakeSessionContext:
            async def __aenter__(self):
                return object()

            async def __aexit__(self, *args):
                return None

        patches = (
            patch.object(worker, "AsyncSessionLocal", MagicMock(return_value=FakeSessionContext())),
            patch.object(worker, "ScheduledResearchService", MagicMock(return_value=service)),
            patch.object(worker, "ResearchService", research),
            patch.object(worker, "ActionLedger", ledger),
        )
        for item in patches:
            item.start()
        try:
            result = await worker.run_scheduled_research({}, task_id="t1")
        finally:
            for item in reversed(patches):
                item.stop()
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["sources"], 2)
        service.complete.assert_awaited_once_with("t1")
        service.fail.assert_not_awaited()


class MediaAdapterTests(unittest.TestCase):
    def test_sanitize_metadata_drops_secrets(self):
        clean = sanitize_metadata(
            {"title": "doc", "api_key": "abc", "note": "Bearer abcdefghijklmnop"}
        )
        self.assertEqual(clean, {"title": "doc"})

    def test_unsupported_type_fails_closed(self):
        with self.assertRaises(Exception):
            MediaDocumentService().prepare(b"hello", content_type="application/x-sh")

    def test_oversized_file_rejected(self):
        with self.assertRaises(Exception):
            MediaDocumentService().prepare(b"x" * 100, content_type="text/plain")

    def test_image_metadata_without_ocr(self):
        from io import BytesIO

        from PIL import Image

        buffer = BytesIO()
        Image.new("RGB", (2, 2), "white").save(buffer, format="PNG")
        result = MediaDocumentService().prepare(
            buffer.getvalue(), content_type="image/png", allow_ocr=False
        )
        self.assertEqual(result["metadata"]["width"], 2)
        self.assertEqual(result["label"], "unverified")


class ThreatIntelTests(unittest.TestCase):
    def test_parse_osv(self):
        payload = {
            "vulns": [
                {
                    "id": "CVE-2026-0001",
                    "summary": "test",
                    "published": "2026-01-01T00:00:00Z",
                    "database_specific": {"severity": "HIGH"},
                    "affected": [{"package": {"name": "requests"}}],
                    "references": [{"url": "https://example.test/advisory"}],
                }
            ]
        }
        parsed = AdvisoryIngestor.parse(payload)
        self.assertEqual(parsed[0]["cve_id"], "CVE-2026-0001")
        self.assertEqual(parsed[0]["affected"], ["requests"])

    def test_parse_nvd(self):
        payload = {
            "vulnerabilities": [
                {
                    "cve": {
                        "id": "CVE-2026-0002",
                        "descriptions": [{"value": "nvd test"}],
                        "published": "2026-02-01T00:00:00Z",
                        "metrics": {"cvssMetricV31": [{"cvssData": {"baseSeverity": "CRITICAL"}}]},
                    }
                }
            ]
        }
        parsed = AdvisoryIngestor.parse(payload, "nvd")
        self.assertEqual(parsed[0]["severity"], "CRITICAL")

    def test_dependency_mapping(self):
        matches = AdvisoryIngestor.map_dependencies(
            {"affected": ["requests", "urllib3"]},
            {"components": [{"name": "requests", "version": "2.0"}]},
        )
        self.assertEqual(matches, ["requests"])

    def test_dlp_blocks_secret_material(self):
        outcome = DLPEngine.check("-----BEGIN PRIVATE KEY-----\nabc", "browser_upload")
        self.assertFalse(outcome["allowed"])
        self.assertIn("private_key", outcome["matched_labels"])

    def test_dlp_allows_plain_text(self):
        self.assertTrue(DLPEngine.check("public documentation text")["allowed"])

    def test_rotation_due_by_reference(self):
        refs = [
            CredentialRef("provider:a", "2026-01-01T00:00:00+00:00"),
            CredentialRef("provider:b", None),
        ]
        due = CredentialRotationPolicy.due(
            refs, 90, datetime(2026, 11, 27, tzinfo=timezone.utc)
        )
        self.assertEqual(due, ["provider:a", "provider:b"])


class SitePolicyTests(unittest.TestCase):
    def test_policy_hash_changes_with_content(self):
        from app.services.iics.site_policy import policy_hash

        self.assertNotEqual(policy_hash("User-agent: *", ""), policy_hash("User-agent: bot", ""))


if __name__ == "__main__":
    unittest.main()
