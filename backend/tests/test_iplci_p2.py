"""Document 28 (proposed OD-48): IPLCI Phase 2 tests.

Trademark, patent, design-right and software-IP screening. No network, no
database, no model calls: these are deterministic risk signals for review.
"""

import unittest

from app.services.iplci import IPLCIService, MemoryStore
from app.services.iplci import ip_rights, software


class IPLCIPhase2Tests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.service = IPLCIService(MemoryStore())

    async def _mark(self, **overrides):
        data = {
            "mark_text": "NovaTech",
            "owner": "Existing Owner",
            "jurisdiction": "ZA",
            "classes": ["9"],
            "status": "registered",
            "territory": ["ZA"],
        }
        data.update(overrides)
        return await self.service.register_trademark(data, "tester")

    async def test_status_declares_phase_two(self):
        status = self.service.status()
        self.assertEqual(status["phase"], 6)
        self.assertEqual(status["implemented_phases"], [1, 2, 3, 4, 5, 6])

    async def test_conflicting_registered_mark_is_critical(self):
        await self._mark()
        result = await self.service.check_trademark({
            "proposed": "Novatech", "jurisdiction": "ZA", "classes": ["9"],
            "use_context": "brand_use",
        })
        self.assertEqual(result["risk"], "CRITICAL")
        self.assertEqual(result["outcome"], "do_not_adopt_without_clearance")
        self.assertTrue(result["professional_review_required"])
        self.assertTrue(result["conflicts"])

    async def test_legitimate_reference_is_not_ownership_claim(self):
        await self._mark()
        result = await self.service.check_trademark({
            "proposed": "Novatech", "jurisdiction": "ZA", "classes": ["9"],
            "use_context": "legitimate_reference",
        })
        self.assertNotEqual(result["risk"], "CRITICAL")
        self.assertTrue(result["legitimate_reference"])

    async def test_pending_mark_is_unknown_not_clear(self):
        await self._mark(status="pending")
        result = await self.service.check_trademark({
            "proposed": "Novatech", "jurisdiction": "ZA", "classes": ["9"],
        })
        self.assertEqual(result["risk"], "UNKNOWN")
        self.assertTrue(result["professional_review_required"])

    async def test_no_conflict_is_not_a_clearance_opinion(self):
        await self._mark(classes=["25"])
        result = await self.service.check_trademark({
            "proposed": "Novatech", "jurisdiction": "ZA", "classes": ["9"],
        })
        self.assertEqual(result["outcome"], "no_recorded_conflict")
        self.assertIn("not a legal clearance", result["reasons"][0])

    async def test_studying_a_patent_is_not_infringement(self):
        await self.service.register_patent({
            "publication_number": "ZA202600001",
            "title": "Robotic arm torque control",
            "status": "granted",
            "jurisdiction": ["ZA"],
            "claims": ["neural network control of robotic arm with torque feedback"],
        })
        result = await self.service.check_patent({
            "activity": "study",
            "implementation": "neural network control of robotic arm with torque feedback",
            "jurisdiction": "ZA",
        })
        self.assertEqual(result["risk"], "LOW")
        self.assertEqual(result["outcome"], "study_permitted")
        self.assertFalse(result["professional_review_required"])

    async def test_implementing_overlapping_claims_is_critical(self):
        await self.service.register_patent({
            "publication_number": "ZA202600002",
            "title": "Robotic arm torque control",
            "status": "granted",
            "jurisdiction": ["ZA"],
            "claims": ["neural network control of robotic arm with torque feedback"],
        })
        result = await self.service.check_patent({
            "activity": "implement",
            "implementation": "neural network control of robotic arm with torque feedback",
            "jurisdiction": "ZA",
        })
        self.assertEqual(result["risk"], "CRITICAL")
        self.assertTrue(result["professional_review_required"])

    async def test_expired_patent_is_not_an_enforceable_claim(self):
        await self.service.register_patent({
            "publication_number": "ZA199900001",
            "title": "Old mechanism",
            "status": "expired",
            "jurisdiction": ["ZA"],
            "claims": ["neural network control of robotic arm with torque feedback"],
        })
        result = await self.service.check_patent({
            "activity": "make",
            "implementation": "neural network control of robotic arm with torque feedback",
            "jurisdiction": "ZA",
        })
        self.assertEqual(result["outcome"], "no_claim_overlap_detected")

    async def test_pending_patent_keeps_unknown_risk(self):
        await self.service.register_patent({
            "publication_number": "ZA202600003",
            "title": "Pending mechanism",
            "status": "pending",
            "jurisdiction": ["ZA"],
            "claims": ["adaptive torque feedback for a manipulator"],
        })
        result = await self.service.check_patent({
            "activity": "sell",
            "implementation": "adaptive torque feedback for a manipulator",
            "jurisdiction": "ZA",
        })
        self.assertEqual(result["risk"], "UNKNOWN")

    async def test_domain_name_conflict_is_critical(self):
        await self.service.register_design({
            "subject": "example.com", "right_type": "domain_name",
            "owner": "Registrant", "status": "registered",
        })
        result = await self.service.check_design({
            "subject": "example.com", "right_type": "domain_name",
        })
        self.assertEqual(result["risk"], "CRITICAL")

    async def test_permissive_dependency_is_compatible(self):
        result = await self.service.check_dependency({
            "licence_id": "MIT", "distribution": "commercial_product",
        })
        self.assertEqual(result["compatibility"], "COMPATIBLE")
        self.assertEqual(result["risk"], "LOW")
        self.assertTrue(result["conditions"])

    async def test_strong_copyleft_blocks_different_project_licence(self):
        result = await self.service.check_dependency({
            "licence_id": "GPL-3.0", "distribution": "commercial_product",
            "project_licence": "MIT",
        })
        self.assertEqual(result["compatibility"], "INCOMPATIBLE")
        self.assertEqual(result["risk"], "CRITICAL")

    async def test_agpl_blocks_network_service(self):
        result = await self.service.check_dependency({
            "licence_id": "AGPL-3.0", "distribution": "saas", "network_service": True,
        })
        self.assertEqual(result["risk"], "CRITICAL")

    async def test_non_commercial_licence_blocks_commercial_use(self):
        result = await self.service.check_dependency({
            "licence_id": "CC-BY-NC-4.0", "distribution": "commercial_product",
        })
        self.assertEqual(result["risk"], "CRITICAL")

    async def test_unknown_licence_never_becomes_approved(self):
        result = await self.service.check_dependency({
            "licence_id": None, "distribution": "internal",
        })
        self.assertEqual(result["compatibility"], "UNKNOWN")
        self.assertEqual(result["risk"], "UNKNOWN")

    async def test_vulnerability_status_does_not_change_licence_decision(self):
        clean = await self.service.check_dependency({"licence_id": "MIT", "distribution": "internal"})
        vulnerable = await self.service.check_dependency({
            "licence_id": "MIT", "distribution": "internal", "vulnerability_status": "critical",
        })
        self.assertEqual(clean["compatibility"], vulnerable["compatibility"])
        self.assertEqual(clean["risk"], vulnerable["risk"])
        self.assertTrue(vulnerable["vulnerability_tracked_separately"])

    async def test_unclear_source_origin_requires_review(self):
        unclear = await self.service.check_source_origin({"origin": "unclear"})
        original = await self.service.check_source_origin({"origin": "original"})
        self.assertTrue(unclear["review_required"])
        self.assertFalse(original["review_required"])

    async def test_sbom_separates_licence_and_vulnerability_views(self):
        sbom = await self.service.record_sbom({
            "project_id": "iam-core",
            "components": [
                {"name": "a", "licence_id": "MIT"},
                {"name": "b", "licence_id": "GPL-3.0", "vulnerability_status": "high"},
                {"name": "c", "licence_id": None},
            ],
        })
        report = await self.service.sbom_report(sbom["id"])
        self.assertEqual(report["component_count"], 3)
        self.assertEqual(report["unresolved_licences"], ["c"])
        self.assertEqual(report["copyleft_components"], ["b"])
        self.assertEqual(report["high_vulnerability_components"], ["b"])
        self.assertTrue(report["licence_compliance_separate_from_vulnerabilities"])

    async def test_risk_decisions_are_persisted_and_auditable(self):
        result = await self.service.check_trademark({
            "proposed": "NovaTech", "jurisdiction": "ZA", "classes": ["9"],
        })
        decision = await self.service.risk_decision(result["id"])
        self.assertIsNotNone(decision)
        self.assertEqual(decision["domain"], "trademark")
        audit = await self.service.audit()
        self.assertTrue(audit["chain_valid"])

    async def test_normalisation_and_licence_rules(self):
        self.assertEqual(ip_rights.normalise("Nova-Tech 2"), "nova tech 2")
        self.assertEqual(software.normalise_licence("Apache 2.0"), "apache-2.0")
        self.assertEqual(software.normalise_licence("MIT OR Apache-2.0"), "compound")


if __name__ == "__main__":
    unittest.main()
