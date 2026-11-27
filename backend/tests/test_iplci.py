"""Document 28 (proposed OD-48): IPLCI Phase 1 tests.

No network, no database, no model calls. Tests verify the permanent IP
governing rules: access is not permission, the ten rights are separate,
unknown fails closed, and every decision is auditable.
"""

import unittest

from app.services.iplci import IPLCIError, IPLCIService, MemoryStore
from app.services.iplci import core


class BrokenStore(MemoryStore):
    async def get_source(self, record_id):
        raise RuntimeError("governance store unavailable")


class IPLCIPhase1Tests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.store = MemoryStore()
        self.service = IPLCIService(self.store)

    async def _source(self, **overrides):
        data = {
            "uri": "https://example.org/research/paper",
            "rights_status": "PUBLIC_DOMAIN",
            "source_class": "OPEN_RESEARCH",
        }
        data.update(overrides)
        return await self.service.register_source(data, "tester")

    async def test_status_declares_phase_and_scope(self):
        status = self.service.status()
        self.assertEqual(status["phase"], 6)
        self.assertEqual(status["capability_areas"], 20)
        self.assertEqual(status["engines"], 7)
        self.assertEqual(status["default_posture"], "fail_closed")
        self.assertEqual(len(status["rights"]), 10)

    async def test_public_domain_is_permitted_with_conditions(self):
        source = await self._source()
        result = await self.service.assess({
            "source_id": source["id"], "operation": "train",
        })
        self.assertEqual(result["decision"], "CONDITIONAL")
        self.assertEqual(result["decision_class"], "MODERATE")
        self.assertEqual(result["right"], "train")

    async def test_copyright_protected_reproduction_is_blocked(self):
        source = await self._source(rights_status="COPYRIGHT_PROTECTED")
        result = await self.service.assess({
            "source_id": source["id"], "operation": "reproduce",
        })
        self.assertEqual(result["decision"], "BLOCKED")
        self.assertEqual(result["decision_class"], "CRITICAL")

    async def test_study_right_is_separate_from_copying(self):
        source = await self._source(rights_status="COPYRIGHT_PROTECTED")
        read = await self.service.assess({"source_id": source["id"], "operation": "read"})
        train = await self.service.assess({"source_id": source["id"], "operation": "train"})
        self.assertNotIn(read["decision"], ("BLOCKED", "QUARANTINED"))
        self.assertEqual(train["decision"], "BLOCKED")
        self.assertEqual(train["rights_evaluated"]["read"], "PERMITTED")
        self.assertEqual(train["rights_evaluated"]["train"], "PROHIBITED")

    async def test_unknown_ownership_is_quarantined(self):
        source = await self._source(rights_status="UNKNOWN_OWNERSHIP")
        result = await self.service.gate_check({
            "source_id": source["id"], "operation": "train", "agent_id": "main",
        })
        self.assertEqual(result["decision"], "QUARANTINED")
        self.assertEqual(result["decision_class"], "UNKNOWN")
        self.assertIsNotNone(result["audit_event_id"])

    async def test_missing_source_never_becomes_approved(self):
        result = await self.service.gate_check({
            "source_id": "does-not-exist", "operation": "store",
        })
        self.assertEqual(result["decision"], "QUARANTINED")
        self.assertEqual(result["decision_class"], "UNKNOWN")

    async def test_explicit_permission_can_override_default(self):
        source = await self._source(rights_status="COPYRIGHT_PROTECTED")
        await self.service.set_permission({
            "source_id": source["id"], "right": "train", "state": "PERMITTED",
            "basis": "written research agreement", "evidence_ref": "agreement-42",
        }, "reviewer")
        result = await self.service.assess({"source_id": source["id"], "operation": "train"})
        self.assertIn(result["decision"], ("APPROVED", "CONDITIONAL"))

    async def test_expired_permission_blocks(self):
        source = await self._source(expiry_date="2020-01-01T00:00:00+00:00")
        result = await self.service.assess({"source_id": source["id"], "operation": "train"})
        self.assertEqual(result["decision"], "EXPIRED")
        self.assertIn("expiry_check", result["rules_applied"])

    async def test_revoked_permission_blocks(self):
        source = await self._source()
        await self.service.revoke_permission(source["id"], "creator", "licence withdrawn")
        result = await self.service.gate_check({
            "source_id": source["id"], "operation": "commercialise",
        })
        self.assertEqual(result["decision"], "REVOKED")
        self.assertEqual(result["decision_class"], "CRITICAL")

    async def test_non_commercial_licence_blocks_commercial_use(self):
        source = await self._source(
            rights_status="CREATIVE_COMMONS",
            licence_flags={"non_commercial": True},
        )
        result = await self.service.assess({
            "source_id": source["id"], "operation": "commercialise",
        })
        self.assertEqual(result["decision"], "BLOCKED")

    async def test_territory_restriction_is_enforced(self):
        source = await self._source(territory=["ZA"])
        result = await self.service.assess({
            "source_id": source["id"], "operation": "train", "jurisdiction": "US",
        })
        self.assertEqual(result["decision"], "BLOCKED")
        self.assertIn("territory_check", result["rules_applied"])

    async def test_personal_data_without_lawful_basis_is_quarantined(self):
        source = await self._source(personal_data_present=True)
        result = await self.service.assess({"source_id": source["id"], "operation": "store"})
        self.assertEqual(result["decision"], "QUARANTINED")
        self.assertIn("privacy_check", result["rules_applied"])

    async def test_reference_only_and_confidential_sources(self):
        reference = await self._source(source_class="REFERENCE_ONLY")
        confidential = await self._source(source_class="CONFIDENTIAL")
        self.assertEqual(
            (await self.service.assess({
                "source_id": reference["id"], "operation": "store",
            }))["decision"],
            "BLOCKED",
        )
        self.assertEqual(
            (await self.service.assess({
                "source_id": confidential["id"], "operation": "analyse",
            }))["decision"],
            "BLOCKED",
        )

    async def test_unknown_operation_fails_closed(self):
        result = await self.service.gate_check({"operation": "do_anything"})
        self.assertEqual(result["decision"], "BLOCKED")
        self.assertEqual(result["decision_class"], "UNKNOWN")
        self.assertEqual(result["error_code"], "IPLCI_UNKNOWN_OPERATION")

    async def test_gateway_store_failure_fails_closed(self):
        service = IPLCIService(BrokenStore())
        result = await service.gate_check({"source_id": "any", "operation": "train"})
        self.assertEqual(result["decision"], "BLOCKED")
        self.assertEqual(result["error_code"], "IPLCI_POLICY_UNAVAILABLE")

    async def test_asset_requires_legal_owner(self):
        with self.assertRaises(IPLCIError) as ctx:
            await self.service.register_asset({"title": "New tool"})
        self.assertEqual(ctx.exception.code, "IPLCI_INVALID_INPUT")

    async def test_dataset_provenance_and_lineage(self):
        source = await self._source()
        assessment = await self.service.assess({
            "source_id": source["id"], "operation": "analyse",
        })
        dataset = await self.service.register_dataset({
            "dataset_version": "v1",
            "source_ids": [source["id"]],
            "assessment_ids": [assessment["id"]],
            "permitted_purposes": ["research"],
        })
        self.assertEqual(dataset["approval_status"], "pending")
        lineage = await self.service.lineage(dataset["id"])
        self.assertEqual(len(lineage["sources"]), 1)
        self.assertEqual(len(lineage["assessments"]), 1)

    async def test_audit_chain_is_tamper_evident(self):
        await self._source()
        await self.service.gate_check({
            "source_id": "missing", "operation": "train",
        })
        audit = await self.service.audit()
        self.assertTrue(audit["chain_valid"])
        self.store._audit[0]["details"]["rights_status"] = "PUBLIC_DOMAIN_TAMPERED"
        broken = await self.service.audit()
        self.assertFalse(broken["chain_valid"])
        self.assertTrue(broken["broken_event_ids"])

    async def test_defaults_are_conservative(self):
        self.assertEqual(core.default_permissions({"rights_status": "UNKNOWN_OWNERSHIP"})["train"], "UNKNOWN")
        self.assertEqual(
            core.default_permissions({
                "rights_status": "COPYRIGHT_PROTECTED",
                "source_class": "OPEN_RESEARCH",
            })["train"],
            "PROHIBITED",
        )
        # An unverified source dominates its rights status: quarantine wins.
        self.assertEqual(
            core.default_permissions({"rights_status": "COPYRIGHT_PROTECTED"})["train"],
            "UNKNOWN",
        )
        self.assertEqual(len(core.RIGHTS), 10)


if __name__ == "__main__":
    unittest.main()
