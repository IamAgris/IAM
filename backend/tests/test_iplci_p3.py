"""Document 28 (proposed OD-48): IPLCI Phase 3 tests.

Collection legality, privacy/data protection and AI-training governance.
No network, no database, no model calls.
"""

import unittest

from app.services.iplci import IPLCIError, IPLCIService, MemoryStore


class IPLCIPhase3Tests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.service = IPLCIService(MemoryStore())

    async def _source(self):
        return await self.service.register_source({
            "uri": "https://example.org/dataset",
            "rights_status": "PUBLIC_DOMAIN",
            "source_class": "OPEN_RESEARCH",
        }, "tester")

    async def _dataset(self, source_id, **extra):
        payload = {
            "lawfully_obtained": True,
            "provenance_recorded": True,
            "rights_assessment_ids": ["assessment-1"],
            **extra,
        }
        return await self.service.register_dataset({
            "dataset_version": "v1",
            "source_ids": [source_id],
            "payload": payload,
        }, "tester")

    async def test_status_declares_phase_three(self):
        status = self.service.status()
        self.assertEqual(status["phase"], 6)
        self.assertEqual(status["implemented_phases"], [1, 2, 3, 4, 5, 6])

    async def test_paywall_bypass_is_prohibited(self):
        result = await self.service.assess_collection({
            "source_uri": "https://example.org/paywalled",
            "bypassed_paywall": True,
        })
        self.assertEqual(result["risk"], "CRITICAL")
        self.assertTrue(result["blocked"])
        self.assertEqual(result["outcome"], "prohibited_collection")

    async def test_robots_disallow_is_a_signal_not_permission(self):
        result = await self.service.assess_collection({
            "source_uri": "https://example.org/page",
            "robots_txt": "Disallow",
        })
        self.assertEqual(result["risk"], "MODERATE")
        self.assertFalse(result["blocked"])
        self.assertTrue(any("robots.txt" in item for item in result["conditions"]))

    async def test_restrictive_terms_require_approval(self):
        result = await self.service.assess_collection({
            "source_uri": "https://example.org/api",
            "api_terms_restrict_use": True,
            "scraping_restricted": True,
        })
        self.assertEqual(result["risk"], "HIGH")
        self.assertEqual(result["outcome"], "additional_approval_required")

    async def test_clean_collection_is_not_a_reuse_grant(self):
        result = await self.service.assess_collection({
            "source_uri": "https://example.org/open",
        })
        self.assertEqual(result["risk"], "LOW")
        self.assertTrue(any("not legal permission" in item for item in result["reasons"]))

    async def test_non_personal_data_is_out_of_privacy_scope(self):
        result = await self.service.assess_privacy({
            "jurisdiction": "ZA", "personal_data_present": False,
        })
        self.assertEqual(result["outcome"], "not_personal_data")

    async def test_missing_lawful_basis_is_quarantined(self):
        result = await self.service.assess_privacy({
            "jurisdiction": "EU", "personal_data_present": True,
        })
        self.assertEqual(result["risk"], "UNKNOWN")
        self.assertEqual(result["outcome"], "quarantined")
        self.assertEqual(result["legal_context_status"], "requires_verification")

    async def test_sensitive_data_requires_consent_and_dpia(self):
        result = await self.service.assess_privacy({
            "jurisdiction": "ZA", "personal_data_present": True,
            "lawful_basis": "consent", "data_categories": ["biometric", "voice"],
        })
        self.assertEqual(result["risk"], "CRITICAL")
        self.assertIn("complete a data protection impact assessment", result["requirements"])

    async def test_lawful_processing_with_safeguards(self):
        result = await self.service.assess_privacy({
            "jurisdiction": "ZA", "personal_data_present": True,
            "lawful_basis": "consent", "minimisation_applied": True,
            "retention_period": "12 months", "deletion_supported": True,
        })
        self.assertEqual(result["risk"], "LOW")
        self.assertEqual(result["outcome"], "permitted_with_safeguards")

    async def test_transfer_and_deletion_obligations(self):
        transfer = await self.service.assess_privacy({
            "jurisdiction": "EU", "personal_data_present": True,
            "lawful_basis": "consent", "international_transfer": True,
        })
        deletion = await self.service.assess_privacy({
            "jurisdiction": "UK", "personal_data_present": True,
            "lawful_basis": "consent", "deletion_requested": True,
        })
        self.assertEqual(transfer["risk"], "HIGH")
        self.assertEqual(deletion["risk"], "HIGH")

    async def test_training_approval_must_be_independent(self):
        with self.assertRaises(IPLCIError) as ctx:
            await self.service.record_training_approval({
                "approver": "same-person", "ingestion_reviewer": "same-person",
                "basis": "reviewed",
            })
        self.assertEqual(ctx.exception.code, "IPLCI_INDEPENDENT_APPROVAL_REQUIRED")

    async def test_training_gate_blocks_without_independent_approval(self):
        source = await self._source()
        dataset = await self._dataset(source["id"])
        result = await self.service.training_gate({
            "source_id": source["id"], "dataset_id": dataset["id"],
        })
        self.assertEqual(result["outcome"], "blocked")
        self.assertFalse(result["eligible"])
        self.assertIn("independent training approval", result["missing"])

    async def test_training_gate_passes_with_independent_approval(self):
        source = await self._source()
        dataset = await self._dataset(source["id"])
        approval = await self.service.record_training_approval({
            "source_id": source["id"], "dataset_id": dataset["id"],
            "approver": "independent-reviewer", "ingestion_reviewer": "ingester",
            "basis": "written research agreement",
        })
        result = await self.service.training_gate({
            "source_id": source["id"], "dataset_id": dataset["id"],
            "approval_id": approval["id"],
        })
        self.assertTrue(result["eligible"])
        self.assertEqual(result["outcome"], "approved_for_training")

    async def test_foundation_model_licence_is_checked(self):
        result = await self.service.assess_foundation_model({
            "model_id": "unknown-model", "licence_id": None, "commercial": True,
        })
        self.assertEqual(result["risk"], "UNKNOWN")
        self.assertEqual(result["outcome"], "model_licence_review_required")

    async def test_provider_terms_gate(self):
        result = await self.service.assess_provider({
            "provider": "external-api", "uses_submissions_for_training": True,
        })
        self.assertEqual(result["risk"], "CRITICAL")
        self.assertEqual(result["outcome"], "blocked")

    async def test_lineage_tracks_revoked_datasets(self):
        source = await self._source()
        dataset = await self._dataset(source["id"])
        lineage = await self.service.register_lineage({
            "model_id": "candidate-1", "base_model": "qwen2.5-coder:3b",
            "dataset_ids": [dataset["id"]],
        })
        self.assertEqual(lineage["affected_by_revocation"], [])
        await self.service.revoke_permission(source["id"], "creator", "licence withdrawn")
        check = await self.service.check_lineage(lineage["id"])
        self.assertEqual(check["risk"], "CRITICAL")
        self.assertEqual(check["affected_dataset_ids"], [dataset["id"]])
        self.assertTrue(check["deletion_is_not_untraining"])

    async def test_privacy_record_is_persisted_with_verification_status(self):
        result = await self.service.record_privacy({
            "source_id": None, "jurisdiction": "ZA",
            "personal_data_present": True, "lawful_basis": "consent",
        }, "tester")
        record = await self.service.privacy_record(result["privacy_id"])
        self.assertEqual(record["verification_status"], "requires_verification")
        audit = await self.service.audit()
        self.assertTrue(audit["chain_valid"])


if __name__ == "__main__":
    unittest.main()
