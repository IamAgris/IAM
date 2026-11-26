"""WH-01/WH-02 enforcement tests (signed target authority + capability deny)."""

import asyncio
import unittest
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from app.services.aegis import AegisEngine
from app.services.cybersecurity.security_guard import (
    SecurityGuard,
    SecurityGuardDenied,
)
from app.services.security_policy import (
    AUTHORIZATION_ACTION,
    AuthorisedTargetDenied,
    AuthorisedTargetPolicy,
    forbidden_capability,
    is_broad_target,
    target_matches,
)


def auth_row(**overrides):
    values = dict(
        id=uuid.uuid4(),
        action_type=AUTHORIZATION_ACTION,
        is_active=True,
        revoked_at=None,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        target_ref="lab.example.internal",
        signer_id="creator-signer",
        scope={
            "targets": ["lab.example.internal", "10.0.0.0/24"],
            "target_type": "lab_url",
            "allowed_operations": ["read", "scan"],
            "allow_write": False,
        },
    )
    values.update(overrides)
    return type("Authorization", (), values)()


class FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def scalars(self):
        return self

    def all(self):
        return self.rows


class FakeDB:
    def __init__(self, rows):
        self.rows = rows

    async def execute(self, _statement):
        return FakeResult(self.rows)


def approvals_for(row):
    class Approvals:
        def __init__(self, _db):
            pass

        async def check_authorization(self, _action, target_ref=None):
            return {
                "authorized": True,
                "authorization_id": str(row.id),
                "expires_at": row.expires_at.isoformat(),
            }

    return Approvals


class PurePolicyTests(unittest.TestCase):
    def test_forbidden_capability_taxonomy(self):
        for text in (
            "exploitation",
            "reverse-shell",
            "credential theft",
            "command_and_control",
            "mass_scan",
        ):
            self.assertIsNotNone(forbidden_capability(text), text)
        self.assertIsNone(forbidden_capability("read findings"))

    def test_broad_targets_denied(self):
        for target in ("*", "0.0.0.0/0", "internet", "10.0.0.0/8"):
            self.assertTrue(is_broad_target(target), target)

    def test_exact_and_cidr_only(self):
        self.assertTrue(target_matches("lab.example.internal", "lab.example.internal"))
        self.assertTrue(target_matches("10.0.0.5", "10.0.0.0/24"))
        self.assertFalse(target_matches("evil-lab.example.internal", "lab.example.internal"))
        self.assertFalse(target_matches("192.168.1.2", "10.0.0.0/24"))

    def test_security_guard_denies_full_taxonomy(self):
        for operation in ("credential_theft", "reverse_shell", "persistence"):
            with self.assertRaises(SecurityGuardDenied, msg=operation):
                SecurityGuard.validate_operation(operation)

    def test_aegis_rejects_prefix_and_offensive_action(self):
        engine = AegisEngine()
        denied = engine.verify_scope(
            "evil-lab.example.internal", ["lab.example.internal"]
        )
        self.assertFalse(denied["permitted"])
        offensive = engine.verify_scope(
            "lab.example.internal", ["lab.example.internal"], action="exploit_target"
        )
        self.assertFalse(offensive["permitted"])
        allowed = engine.verify_scope(
            "lab.example.internal", ["lab.example.internal"], action="read"
        )
        self.assertTrue(allowed["permitted"])


class AuthorisedTargetPolicyTests(unittest.IsolatedAsyncioTestCase):
    async def test_signed_scope_allows_in_scope_operation(self):
        row = auth_row()
        with patch("app.services.security_policy.CreatorApprovalService", approvals_for(row)):
            result = await AuthorisedTargetPolicy(FakeDB([row])).verify(
                "lab.example.internal", "scan"
            )
        self.assertTrue(result["authorized"])
        self.assertEqual(result["authorization_id"], str(row.id))

    async def test_cidr_scope_allows_member(self):
        row = auth_row()
        with patch("app.services.security_policy.CreatorApprovalService", approvals_for(row)):
            result = await AuthorisedTargetPolicy(FakeDB([row])).verify("10.0.0.9", "read")
        self.assertTrue(result["authorized"])

    async def test_unlisted_and_prefix_targets_denied(self):
        row = auth_row()
        with patch("app.services.security_policy.CreatorApprovalService", approvals_for(row)):
            policy = AuthorisedTargetPolicy(FakeDB([row]))
            for target in ("evil-lab.example.internal", "192.168.1.5"):
                with self.assertRaises(AuthorisedTargetDenied):
                    await policy.verify(target, "read")

    async def test_expired_revoked_and_write_denied(self):
        for row in (
            auth_row(expires_at=datetime.now(timezone.utc) - timedelta(minutes=1)),
            auth_row(revoked_at=datetime.now(timezone.utc)),
            auth_row(),
        ):
            with patch("app.services.security_policy.CreatorApprovalService", approvals_for(row)):
                policy = AuthorisedTargetPolicy(FakeDB([row]))
                if row.revoked_at or row.expires_at < datetime.now(timezone.utc):
                    with self.assertRaises(AuthorisedTargetDenied):
                        await policy.verify("lab.example.internal", "read")
                else:
                    with self.assertRaises(AuthorisedTargetDenied):
                        await policy.verify(
                            "lab.example.internal", "read", require_write=True
                        )

    async def test_forbidden_operation_denied_before_authority_check(self):
        with patch("app.services.security_policy.CreatorApprovalService", approvals_for(auth_row())):
            with self.assertRaises(AuthorisedTargetDenied):
                await AuthorisedTargetPolicy(FakeDB([auth_row()])).verify(
                    "lab.example.internal", "credential theft"
                )


if __name__ == "__main__":
    unittest.main()
