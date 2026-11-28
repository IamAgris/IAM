"""Document 28 (proposed OD-48): IPLCI Phase 4 tests.

Jurisdiction resolution, official-source verification, business compliance
and research ethics. No network, no database, no model calls.
"""

import unittest

from app.services.iplci import IPLCIService, MemoryStore
from app.services.iplci import jurisdiction as jurisdiction_module


class IPLCIPhase4Tests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.service = IPLCIService(MemoryStore())

    async def test_status_declares_phase_four(self):
        status = self.service.status()
        self.assertEqual(status["phase"], 6)
        self.assertEqual(status["implemented_phases"], [1, 2, 3, 4, 5, 6])

    async def test_multi_jurisdiction_escalates(self):
        result = await self.service.resolve_jurisdiction({
            "origin": "ZA", "processing_locations": ["EU"], "target_markets": ["US"],
        }, "tester")
        self.assertEqual(result["jurisdictions"], ["ZA", "EU", "US"])
        self.assertTrue(result["escalation_required"])
        self.assertEqual(result["risk"], "MODERATE")

    async def test_single_jurisdiction_resolves(self):
        result = await self.service.resolve_jurisdiction({"origin": "ZA"}, "tester")
        self.assertEqual(result["jurisdictions"], ["ZA"])
        self.assertFalse(result["escalation_required"])

    async def test_applicable_law_is_unverified_context(self):
        result = await self.service.applicable_laws(["ZA", "EU"], "privacy")
        provisions = result["provisions"]
        self.assertIn("POPIA", [item["provision"] for item in provisions])
        self.assertIn("GDPR", [item["provision"] for item in provisions])
        self.assertTrue(all(item["status"] == "requires_verification" for item in provisions))

    async def test_territory_check(self):
        permitted = jurisdiction_module.check_territory(["ZA", "EU"], ["ZA"])
        denied = jurisdiction_module.check_territory(["ZA"], ["US"])
        self.assertTrue(permitted["permitted"])
        self.assertFalse(denied["permitted"])

    async def test_official_source_without_provision_is_unverified(self):
        result = await self.service.verify_legal_source({
            "authority": "USPTO", "jurisdiction": "US", "url": "https://example.org",
        })
        self.assertEqual(result["status"], "unverified")
        self.assertIn("provision_ref", result["missing_fields"])

    async def test_verified_source_requires_reviewer_reference(self):
        result = await self.service.verify_legal_source({
            "authority": "WIPO", "jurisdiction": "EU", "url": "https://example.org",
            "provision_ref": "Art. 4", "document_type": "legislation",
            "verified_by": "qualified-counsel@example.org",
        })
        self.assertEqual(result["status"], "verified")
        record = await self.service.knowledge_verification(result["verification_id"])
        self.assertEqual(record["status"], "verified")

    async def test_unofficial_authority_is_flagged(self):
        result = await self.service.verify_legal_source({
            "authority": "random-blog", "jurisdiction": "ZA", "url": "https://example.org",
            "provision_ref": "section 1", "document_type": "legislation",
        })
        self.assertEqual(result["status"], "unverified")
        self.assertTrue(any("official-source" in item for item in result["problems"]))

    async def test_prediction_is_never_enacted_law(self):
        result = await self.service.assess_legal_change({
            "document_type": "legislation", "prediction": True,
        })
        self.assertFalse(result["binding"])
        self.assertEqual(result["label"], "prediction")

    async def test_enacted_legislation_is_binding(self):
        result = await self.service.assess_legal_change({"document_type": "regulation"})
        self.assertTrue(result["binding"])

    async def test_signing_contract_requires_human_authorisation(self):
        result = await self.service.assess_business({
            "domain": "contract", "action": "sign_contract",
        })
        self.assertEqual(result["risk"], "CRITICAL")
        self.assertTrue(result["human_approval_required"])
        self.assertFalse(result["can_iam_execute_independently"])

    async def test_sanctions_restricted_party_blocks(self):
        result = await self.service.assess_business({
            "domain": "sanctions", "restricted_party": True,
        })
        self.assertEqual(result["risk"], "CRITICAL")

    async def test_research_use_is_permitted_with_conditions(self):
        result = await self.service.assess_business({
            "domain": "contract", "action": "review",
        })
        self.assertNotEqual(result["outcome"], "blocked_pending_human_authorisation")

    async def test_business_review_is_persisted(self):
        result = await self.service.assess_business({
            "domain": "corporate", "action": "form_entity",
        }, "tester")
        review = await self.service.business_review(result["review_id"])
        self.assertTrue(review["human_approval_required"])
        self.assertEqual(review["business_domain"], "corporate")

    async def test_obligation_recording(self):
        obligation = await self.service.record_obligation({
            "obligation": "file annual return", "domain": "corporate",
            "jurisdiction": "ZA", "due_at": "2027-01-01T00:00:00+00:00",
        }, "tester")
        self.assertEqual(obligation["status"], "open")
        self.assertEqual(len(await self.service.obligations()), 1)

    async def test_research_ethics_requires_consent(self):
        result = await self.service.assess_research_ethics({
            "subject": "participant study", "ethics_review_required": True,
        })
        self.assertEqual(result["outcome"], "blocked")
        self.assertIn("obtain informed consent", result["requirements"])

    async def test_ethics_review_with_safeguards(self):
        result = await self.service.assess_research_ethics({
            "subject": "voluntary study", "informed_consent": True,
            "ethics_review_required": True, "ethics_review_completed": True,
            "withdrawal_process": True, "minimisation_applied": True,
        })
        self.assertEqual(result["outcome"], "permitted_with_safeguards")

    async def test_identity_impersonation_is_critical(self):
        result = await self.service.assess_identity_use({
            "subject": "creator identity", "impersonation": True,
        })
        self.assertEqual(result["risk"], "CRITICAL")
        self.assertEqual(result["outcome"], "blocked")

    async def test_cross_border_transfer_requires_mechanism(self):
        result = await self.service.assess_cross_border({
            "origin": "ZA", "destinations": ["US"],
        })
        self.assertEqual(result["risk"], "HIGH")
        self.assertEqual(result["legal_context_status"], "requires_verification")

    async def test_residency_obligation_blocks_transfer(self):
        result = await self.service.assess_cross_border({
            "origin": "ZA", "destinations": ["US"],
            "transfer_mechanism": "standard_contractual_clauses",
            "residency_required": True,
        })
        self.assertEqual(result["risk"], "CRITICAL")

    async def test_audit_chain_remains_valid(self):
        await self.service.resolve_jurisdiction({"origin": "ZA"}, "tester")
        await self.service.assess_business({"domain": "contract"}, "tester")
        self.assertTrue((await self.service.audit())["chain_valid"])


if __name__ == "__main__":
    unittest.main()
