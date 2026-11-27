"""Document 28 (confirmed OD-48): IPLCI Phase 5 tests.

Disputes, incident response, legal holds, deadlines, evidence and continuity.
No network, no database, no model calls.
"""

import unittest

from app.services.iplci import IPLCIService, MemoryStore


class IPLCIPhase5Tests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.service = IPLCIService(MemoryStore())

    async def test_status_declares_phase_five(self):
        status = self.service.status()
        self.assertEqual(status["phase"], 6)
        self.assertEqual(status["implemented_phases"], [1, 2, 3, 4, 5, 6])

    async def test_unverified_complainant_is_not_accepted(self):
        result = await self.service.register_dispute({
            "case_type": "copyright", "complainant": "Anonymous",
        }, "tester")
        self.assertEqual(result["risk"], "UNKNOWN")
        self.assertFalse(result["accepted_allegation"])
        self.assertEqual(result["case"]["status"], "verifying")
        self.assertTrue(any("do not accept" in item for item in result["required_actions"]))

    async def test_verified_complainant_still_requires_investigation(self):
        result = await self.service.register_dispute({
            "case_type": "trademark", "complainant": "Owner Inc",
            "identity_ref": "id-1", "authority_evidence": "register-extract",
            "asserted_right": "registered mark", "register_match": True,
        }, "tester")
        self.assertTrue(result["case"]["authority_verified"])
        self.assertEqual(result["case"]["status"], "investigating")
        self.assertFalse(result["accepted_allegation"])

    async def test_patent_dispute_requires_professional_review(self):
        result = await self.service.register_dispute({
            "case_type": "patent", "complainant": "Patent Owner",
            "identity_ref": "id-2", "authority_evidence": "register",
            "asserted_right": "patent", "register_match": True,
        })
        self.assertTrue(result["professional_review_required"])

    async def test_dispute_status_history(self):
        created = await self.service.register_dispute({
            "case_type": "takedown", "complainant": "Owner",
            "identity_ref": "id-3", "authority_evidence": "doc",
            "asserted_right": "copyright", "owner_match": True,
        })
        updated = await self.service.update_dispute_status(
            created["dispute_id"], "restricted", "tester", "temporary restriction"
        )
        self.assertEqual(updated["status"], "restricted")
        self.assertEqual(updated["case_history"][-1]["note"], "temporary restriction")

    async def test_incident_remediation_has_ten_steps(self):
        result = await self.service.open_incident({
            "incident_type": "improper_licence", "affected_models": ["model-1"],
        }, "tester")
        self.assertEqual(len(result["remediation_steps"]), 10)
        self.assertEqual(result["remediation_steps"][-1], "update the compliance rules to prevent recurrence")

    async def test_disclosure_incident_adds_notification_step(self):
        result = await self.service.open_incident({
            "incident_type": "unauthorised_disclosure",
            "disclosure_type": "trade_secret",
        })
        self.assertEqual(len(result["remediation_steps"]), 11)

    async def test_legal_hold_blocks_scoped_evidence_deletion(self):
        hold = await self.service.place_legal_hold({
            "reason": "active dispute", "scope": ["asset-1"],
        }, "tester")
        evidence = await self.service.record_evidence({
            "asset_id": "asset-1", "legal_hold_id": hold["id"],
        })
        guard = await self.service.evidence_guard(hold["id"])
        self.assertFalse(guard["can_delete"])
        self.assertIn(evidence["id"], guard["blocked_evidence_ids"])

    async def test_released_hold_allows_deletion(self):
        hold = await self.service.place_legal_hold({"reason": "review", "scope": ["asset-2"]})
        await self.service.record_evidence({"asset_id": "asset-2", "legal_hold_id": hold["id"]})
        await self.service.release_legal_hold(hold["id"], "creator")
        guard = await self.service.evidence_guard(hold["id"])
        self.assertTrue(guard["can_delete"])

    async def test_retention_respects_legal_hold(self):
        hold = await self.service.place_legal_hold({"reason": "litigation", "scope": ["asset-3"]})
        evidence = await self.service.record_evidence({
            "asset_id": "asset-3", "legal_hold_id": hold["id"],
            "retention_until": "2020-01-01T00:00:00+00:00",
        })
        decision = await self.service.retention_decision(evidence["id"], "2026-01-01T00:00:00+00:00")
        self.assertEqual(decision["action"], "retain")

    async def test_retention_without_period_is_review(self):
        evidence = await self.service.record_evidence({"asset_id": "asset-4"})
        decision = await self.service.retention_decision(evidence["id"], "2026-01-01T00:00:00+00:00")
        self.assertEqual(decision["action"], "review")

    async def test_expired_retention_allows_lawful_deletion(self):
        evidence = await self.service.record_evidence({
            "asset_id": "asset-5", "retention_until": "2020-01-01T00:00:00+00:00",
        })
        decision = await self.service.retention_decision(evidence["id"], "2026-01-01T00:00:00+00:00")
        self.assertEqual(decision["action"], "delete_if_lawful")

    async def test_rights_contact_recorded(self):
        contact = await self.service.record_rights_contact({
            "request_type": "training_permission", "requested_rights": ["train", "store"],
        })
        self.assertEqual(contact["status"], "requested")
        self.assertEqual(len(await self.service.rights_contacts()), 1)

    async def test_compliance_calendar_alerts(self):
        await self.service.record_deadline({
            "deadline_type": "renewal", "due_at": "2026-01-01T00:00:00+00:00",
        })
        await self.service.record_deadline({
            "deadline_type": "filing", "due_at": "2027-12-01T00:00:00+00:00",
        })
        calendar = await self.service.compliance_calendar("2026-11-27T00:00:00+00:00")
        self.assertEqual(len(calendar["alerts"]), 1)
        self.assertEqual(calendar["overdue"][0]["deadline_type"], "renewal")

    async def test_permission_changes_detected(self):
        source = await self.service.register_source({
            "uri": "https://example.org/x", "rights_status": "PUBLIC_DOMAIN",
            "expiry_date": "2020-01-01T00:00:00+00:00",
        })
        result = await self.service.permission_changes("2026-01-01T00:00:00+00:00")
        self.assertTrue(result["reassessment_required"])
        self.assertTrue(any(item["change"] == "expired" for item in result["changes"]))

    async def test_reassessment_trigger(self):
        result = await self.service.check_reassessment({"licence_changed": True, "law_changed": True})
        self.assertTrue(result["required"])
        self.assertEqual(len(result["triggers"]), 2)

    async def test_continuity_check_recovers_from_broken_chain(self):
        result = await self.service.continuity_check({
            "signed_policy_version": "1.0", "evidence_complete": True,
        })
        self.assertEqual(result["outcome"], "governance_intact")
        record = await self.service.continuity_record(result["continuity_id"])
        self.assertEqual(record["risk"], "LOW")
        self.service.store._audit[0]["details"]["rights_status"] = "TAMPERED"
        broken = await self.service.continuity_check({})
        self.assertEqual(broken["outcome"], "recovery_required")
        self.assertTrue(broken["recovery_actions"])

    async def test_audit_chain_valid_after_operations(self):
        await self.service.register_dispute({"case_type": "copyright"})
        await self.service.place_legal_hold({"reason": "preserve"})
        self.assertTrue((await self.service.audit())["chain_valid"])


if __name__ == "__main__":
    unittest.main()
