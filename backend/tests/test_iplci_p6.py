"""Document 28 (confirmed OD-48): IPLCI Phase 6 adversarial tests AT-01…AT-12.

These tests prove that IAM cannot add unapproved training data, circumvent a
licence, publish infringing material, use confidential information, bypass the
gateway through another agent, relax its safeguards, treat missing rights as
permission, reuse revoked permissions, delete preserved evidence, disclose to
an unsafe provider or promote a model with a blocking revocation.
"""

import unittest

from app.services.ai_research import self_improvement
from app.services.iplci import ComplianceGateway, GovernanceRefusal, IPLCIService, MemoryStore
from app.services.iplci import policy
from app.services.memory_service import MemoryService
from app.services.research_service import ResearchService


class IPLCIPhase6Tests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.store = MemoryStore()
        self.service = IPLCIService(self.store)
        # Rights tests isolate rights logic; the legal-readiness gate has its own tests.
        self.gateway = ComplianceGateway(self.service, require_legal_readiness=False)
        self.policy = policy.sign_policy(
            {rule: True for rule in policy.PROTECTED_RULES},
            version="1.0", signed_by="creator", signed_at="2026-11-27T00:00:00+00:00",
        )
        self.gateway.set_policy(self.policy)

    async def _source(self, **overrides):
        data = {
            "uri": "https://example.org/material",
            "rights_status": "PUBLIC_DOMAIN",
            "source_class": "OPEN_RESEARCH",
        }
        data.update(overrides)
        return await self.service.register_source(data, "tester")

    async def test_status_declares_phase_six(self):
        status = self.service.status()
        self.assertEqual(status["phase"], 6)
        self.assertEqual(status["implemented_phases"], [1, 2, 3, 4, 5, 6])

    async def test_at01_unapproved_dataset_cannot_enter_training(self):
        source = await self._source()
        dataset = await self.service.register_dataset({
            "dataset_version": "v1", "source_ids": [source["id"]],
        })
        with self.assertRaises(GovernanceRefusal) as ctx:
            await self.gateway.enforce_training(
                source_id=source["id"], dataset_id=dataset["id"],
            )
        self.assertIn("independent training approval", str(ctx.exception))

    async def test_at02_licence_restriction_cannot_be_circumvented(self):
        source = await self._source(
            rights_status="CREATIVE_COMMONS", licence_flags={"non_commercial": True},
        )
        with self.assertRaises(GovernanceRefusal):
            await self.gateway.enforce("commercialise", source_id=source["id"])

    async def test_at03_infringing_publication_is_blocked(self):
        source = await self._source(rights_status="COPYRIGHT_PROTECTED")
        with self.assertRaises(GovernanceRefusal):
            await self.gateway.enforce_publication(source_id=source["id"])

    async def test_at04_confidential_information_is_blocked(self):
        source = await self._source(source_class="CONFIDENTIAL")
        with self.assertRaises(GovernanceRefusal):
            await self.gateway.enforce("analyse", source_id=source["id"])

    async def test_at05_sub_agents_use_the_same_gateway(self):
        source = await self._source()
        for agent in ("main", "sub-agent-7", "plugin:test", "external_model:test"):
            result = await self.gateway.enforce_agent_action(
                agent_id=agent, action="read", source_id=source["id"],
            )
            self.assertIn(result["decision"], ("APPROVED", "CONDITIONAL"))
        blocked = await self._source(rights_status="COPYRIGHT_PROTECTED")
        with self.assertRaises(GovernanceRefusal):
            await self.gateway.enforce_agent_action(
                agent_id="sub-agent-7", action="reproduce", source_id=blocked["id"],
            )

    async def test_at06_safeguards_cannot_be_relaxed_by_iam(self):
        proposed = {rule: True for rule in policy.PROTECTED_RULES}
        proposed["mandatory_gateway"] = False
        result = await self.service.check_policy_relaxation({"rules": proposed})
        self.assertFalse(result["permitted"])
        self.assertEqual(result["error_code"], "IPLCI_POLICY_IMMUTABLE")
        allowed = await self.service.check_policy_relaxation({
            "rules": proposed, "human_approval_reference": "creator-signed-approval",
        })
        self.assertTrue(allowed["permitted"])

    async def test_at07_missing_licence_is_not_permission(self):
        source = await self._source(rights_status="UNKNOWN_OWNERSHIP")
        with self.assertRaises(GovernanceRefusal) as ctx:
            await self.gateway.enforce("train", source_id=source["id"])
        self.assertEqual(ctx.exception.decision, "QUARANTINED")

    async def test_at08_revoked_permission_is_not_reused(self):
        source = await self._source()
        await self.service.revoke_permission(source["id"], "creator", "withdrawn")
        with self.assertRaises(GovernanceRefusal):
            await self.gateway.enforce("commercialise", source_id=source["id"])

    async def test_at09_every_enforcement_is_audited(self):
        source = await self._source()
        await self.gateway.enforce("read", source_id=source["id"], agent_id="sub-9")
        audit = await self.service.audit()
        events = [item for item in audit["events"] if item["event_type"] == "gateway_check"]
        self.assertTrue(events)
        self.assertTrue(any(item["actor"] == "sub-9" for item in events))
        self.assertTrue(audit["chain_valid"])

    async def test_at10_evidence_under_hold_cannot_be_deleted(self):
        hold = await self.service.place_legal_hold({"reason": "dispute", "scope": ["asset-a"]})
        evidence = await self.service.record_evidence({
            "asset_id": "asset-a", "legal_hold_id": hold["id"],
        })
        with self.assertRaises(GovernanceRefusal):
            await self.gateway.enforce_retention(evidence_id=evidence["id"])

    async def test_at11_external_provider_disclosure_is_gated(self):
        source = await self._source(source_class="CONFIDENTIAL")
        with self.assertRaises(GovernanceRefusal):
            await self.gateway.enforce_egress(source_id=source["id"])

    async def test_at12_revoked_dataset_blocks_model_promotion(self):
        source = await self._source()
        dataset = await self.service.register_dataset({
            "dataset_version": "v1",
            "source_ids": [source["id"]],
            "payload": {
                "lawfully_obtained": True,
                "provenance_recorded": True,
                "rights_assessment_ids": ["assessment-1"],
            },
        })
        approval = await self.service.record_training_approval({
            "source_id": source["id"], "dataset_id": dataset["id"],
            "approver": "independent", "ingestion_reviewer": "ingester", "basis": "agreement",
        })
        await self.gateway.enforce_training(
            source_id=source["id"], dataset_id=dataset["id"], approval_id=approval["id"],
        )
        lineage = await self.service.register_lineage({
            "model_id": "candidate-1", "base_model": "qwen2.5-coder:3b",
            "dataset_ids": [dataset["id"]],
        })
        self.assertEqual(lineage["affected_by_revocation"], [])
        await self.service.revoke_permission(source["id"], "creator", "withdrawn")
        with self.assertRaises(GovernanceRefusal):
            await self.gateway.enforce_training(
                source_id=source["id"], dataset_id=dataset["id"], approval_id=approval["id"],
            )
        check = await self.service.check_lineage(lineage["id"])
        self.assertEqual(check["risk"], "CRITICAL")

    async def test_tampered_policy_refuses_to_activate(self):
        tampered = dict(self.policy)
        tampered["rules"] = {rule: True for rule in policy.PROTECTED_RULES}
        tampered["rules"]["unknown_never_approved"] = False
        with self.assertRaises(policy.PolicyError):
            self.gateway.set_policy(tampered)

    async def test_missing_policy_fails_closed(self):
        source = await self._source(rights_status="UNKNOWN_OWNERSHIP")
        self.gateway._policy = {**self.policy, "signature": "bad"}
        with self.assertRaises(GovernanceRefusal):
            await self.gateway.enforce("store", source_id=source["id"])

    async def test_gateway_refuses_without_signed_policy(self):
        source = await self._source()
        bare = ComplianceGateway(self.service)
        with self.assertRaises(GovernanceRefusal) as ctx:
            await bare.enforce("read", source_id=source["id"])
        self.assertEqual(ctx.exception.code, "IPLCI_POLICY_UNAVAILABLE")

    async def test_tool_call_governance_refusal(self):
        from unittest.mock import AsyncMock, patch

        from app.services.tool_authorization import ToolAuthorizationError, authorize_tool_call

        refusal = GovernanceRefusal("IPLCI_DENIED", "BLOCKED", "CRITICAL", "blocked")
        with patch(
            "app.services.iplci.integration.enforce_agent_request",
            new=AsyncMock(side_effect=refusal),
        ):
            with self.assertRaises(ToolAuthorizationError):
                await authorize_tool_call(
                    None, "some_tool", governance_context={"source_id": "s1"},
                )

    async def test_dispatch_governance_refusal(self):
        from unittest.mock import AsyncMock, patch

        from app.orchestration import dispatch as action_dispatch

        refusal = GovernanceRefusal("IPLCI_DENIED", "BLOCKED", "CRITICAL", "blocked")
        with patch(
            "app.services.iplci.integration.enforce_agent_request",
            new=AsyncMock(side_effect=refusal),
        ):
            result = await action_dispatch.dispatch(
                None, "research", {"governance_context": {"source_id": "s1"}},
            )
        self.assertEqual(result["status"], "failure")
        self.assertEqual(result["error"], "IPLCI_GOVERNANCE_REFUSED")

    async def test_iam_cannot_self_sign_a_policy(self):
        from app.services.iplci import IPLCIError

        for signer in ("iam", "main", "sub-agent:7", "plugin:x"):
            with self.assertRaises(IPLCIError) as ctx:
                await self.service.record_policy({
                    "version": f"bad-{signer}",
                    "rules": {rule: True for rule in policy.PROTECTED_RULES},
                    "signed_by": signer,
                    "human_approval_reference": "self-declared",
                })
            self.assertEqual(ctx.exception.code, "IPLCI_HUMAN_APPROVAL_REQUIRED")

    async def test_human_signed_policy_activates_gateway(self):
        record = await self.service.record_policy({
            "version": "production-1",
            "rules": {rule: True for rule in policy.PROTECTED_RULES},
            "signed_by": "creator",
            "human_approval_reference": "OD-48-creator-confirmation",
        })
        self.assertEqual(record["status"], "active")
        status = await self.service.verify_active_policy()
        self.assertTrue(status["valid"])
        gateway = ComplianceGateway(self.service)
        gateway.set_policy(record)
        source = await self._source()
        result = await gateway.enforce("read", source_id=source["id"])
        self.assertIn(result["decision"], ("APPROVED", "CONDITIONAL"))

    async def test_skill_and_provider_seams_enforce(self):
        from unittest.mock import AsyncMock, patch

        from app.services.model_inference import InferenceBlocked, InferenceService
        from app.services.skillruntime.service import SkillRuntimeError, SkillRuntimeService

        refusal = GovernanceRefusal("IPLCI_DENIED", "BLOCKED", "CRITICAL", "blocked")
        with patch(
            "app.services.iplci.integration.enforce_agent_request",
            new=AsyncMock(side_effect=refusal),
        ):
            with self.assertRaises(SkillRuntimeError):
                await SkillRuntimeService(None).invoke(
                    "skill-1", permission="network_access",
                    governance_context={"source_id": "s1"},
                )
            with self.assertRaises(InferenceBlocked):
                await InferenceService().chat(
                    [{"role": "user", "content": "hello"}],
                    governance_context={"source_id": "s1"},
                )

    async def test_ambient_context_reaches_legacy_call_sites(self):
        from unittest.mock import AsyncMock, patch

        from app.services.iplci.context import governance_context
        from app.services.tool_authorization import ToolAuthorizationError, authorize_tool_call

        refusal = GovernanceRefusal("IPLCI_DENIED", "BLOCKED", "CRITICAL", "blocked")
        with patch(
            "app.services.iplci.integration.enforce_agent_request",
            new=AsyncMock(side_effect=refusal),
        ) as enforced:
            async with governance_context({"source_id": "ambient-1", "agent_id": "sub-9"}):
                # No explicit governance_context argument: inherited from boundary.
                with self.assertRaises(ToolAuthorizationError):
                    await authorize_tool_call(None, "tool-x")
            enforced.assert_awaited_once()
            self.assertEqual(enforced.call_args.kwargs["source_id"], "ambient-1")
            self.assertEqual(enforced.call_args.kwargs["agent_id"], "sub-9")

        # Outside the scope the ambient context is gone.
        from app.services.iplci.context import get_governance_context

        self.assertIsNone(get_governance_context())

    async def test_enforcement_requires_a_source(self):
        from app.services.iplci.integration import enforce_collection_request

        with self.assertRaises(GovernanceRefusal) as ctx:
            await enforce_collection_request(None)
        self.assertEqual(ctx.exception.code, "IPLCI_PROVENANCE_REQUIRED")

    async def test_counsel_validation_workflow_completes_readiness(self):
        from app.services.iplci import IPLCIError

        readiness = await self.service.readiness_report()
        self.assertFalse(readiness["complete"])
        self.assertIn("no active signed compliance policy", readiness["blockers"])
        await self.service.record_policy({
            "version": "production-1",
            "rules": {rule: True for rule in policy.PROTECTED_RULES},
            "signed_by": "creator",
            "human_approval_reference": "OD-48",
        })
        task = await self.service.open_validation_task({
            "domain": "privacy",
            "subject": "POPIA section 27 research basis",
            "question": "Do the documented conditions apply to this corpus?",
            "jurisdiction": "ZA",
        })
        self.assertEqual(task["status"], "pending")
        with self.assertRaises(IPLCIError) as ctx:
            await self.service.verify_validation_task(task["id"], {
                "reviewer_reference": "iam",
            })
        self.assertEqual(ctx.exception.code, "IPLCI_COUNSEL_REQUIRED")
        with self.assertRaises(IPLCIError) as ctx:
            await self.service.verify_validation_task(task["id"], {
                "reviewer_reference": "qualified-counsel@example.org",
            })
        self.assertEqual(ctx.exception.code, "IPLCI_EVIDENCE_REQUIRED")
        await self.service.record_validation_evidence(task["id"], {
            "evidence_ref": "official-gazette-2026-11",
        })
        verified = await self.service.verify_validation_task(task["id"], {
            "reviewer_reference": "qualified-counsel@example.org",
            "provision_ref": "section 27",
        })
        self.assertEqual(verified["status"], "verified")
        final = await self.service.readiness_report()
        self.assertTrue(final["complete"])
        self.assertEqual(final["verified_tasks"], 1)

    async def test_consequential_operations_wait_for_counsel(self):
        source = await self._source()
        signed = await self.service.record_policy({
            "version": "production-1",
            "rules": {rule: True for rule in policy.PROTECTED_RULES},
            "signed_by": "creator",
            "human_approval_reference": "OD-48",
        })
        gate = ComplianceGateway(self.service)
        gate.set_policy(signed)

        with self.assertRaises(GovernanceRefusal) as ctx:
            await gate.enforce("commercialise", source_id=source["id"])
        self.assertEqual(ctx.exception.code, "IPLCI_LEGAL_VALIDATION_INCOMPLETE")

        # Study and analysis remain available while validation is pending.
        study = await gate.enforce("read", source_id=source["id"])
        self.assertIn(study["decision"], ("APPROVED", "CONDITIONAL"))

        task = await self.service.open_validation_task({
            "domain": "privacy", "subject": "POPIA research basis",
            "question": "Do the section 27 conditions apply?", "jurisdiction": "ZA",
        })
        await self.service.record_validation_evidence(task["id"], {
            "evidence_ref": "official-gazette-2026",
        })
        await self.service.verify_validation_task(task["id"], {
            "reviewer_reference": "qualified-counsel@example.org",
        })
        self.assertTrue((await self.service.readiness_report())["complete"])
        commercial = await gate.enforce("commercialise", source_id=source["id"])
        self.assertIn(commercial["decision"], ("APPROVED", "CONDITIONAL"))

    async def test_api_training_route_requires_governance_context(self):
        from fastapi import HTTPException, Request

        from app.api.routes import development

        request = Request(scope={"type": "http", "headers": []})
        payload = development.CandidateRequestModel(
            experiment_id="exp_test", licence="CC-BY-4.0",
            checkpoint_ref="ckpt", baseline_score=0.5,
        )
        with self.assertRaises(HTTPException) as ctx:
            await development.run_self_improvement_cycle(payload, request, None)
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertEqual(ctx.exception.detail["code"], "IPLCI_PROVENANCE_REQUIRED")

    async def test_integration_seams_enforce(self):
        source = await self._source(rights_status="COPYRIGHT_PROTECTED")
        ctx = {"source_id": source["id"], "agent_id": "sub-agent"}
        with self.assertRaises(GovernanceRefusal):
            await MemoryService(None).store_memory("secret", governance_context=ctx)
        with self.assertRaises(GovernanceRefusal):
            await ResearchService().research_topic("topic", governance_context=ctx)
        from app.services.internetaccess_service import InternetAccessService

        with self.assertRaises(GovernanceRefusal):
            await InternetAccessService(None).publish_content(
                "title", "article", governance_context=ctx,
            )
        request = self_improvement.CandidateRequest(
            experiment_id="exp_test", licence="CC-BY-4.0",
            base_model="local-qwen-coder-3b", candidate_model="local-qwen-coder-3b-v2",
            checkpoint_ref="ckpt", baseline_score=0.5, min_improvement=0.01,
            diagnosis="weak at tool use",
        )
        with self.assertRaises(GovernanceRefusal):
            await self_improvement.prepare_candidate(
                None, request, governance_context={
                    "source_id": source["id"], "dataset_id": "dataset-1",
                },
            )


if __name__ == "__main__":
    unittest.main()
