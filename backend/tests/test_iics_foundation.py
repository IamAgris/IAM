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
    BenchmarkSuite,
    EgressGateway,
    PermissionGate,
    SourceRegistry,
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
        internet.check_permission = AsyncMock(return_value=internet_decision)
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


if __name__ == "__main__":
    unittest.main()
