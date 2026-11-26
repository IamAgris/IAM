"""Phase 9 tests: HAIS, computer use, mobile agent, encrypted credentials, tabs."""

import base64
import hashlib
import json
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, patch

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

from app.core.config import settings
from app.models.digital_access import AssistanceRequest, WebsiteCredential
from app.models.mfa import PasskeyCredential, TotpEnrollment
from app.models.security import AuditEvent
from app.services.browser_service import BrowserService
from app.services.computer_use import ComputerUseError, ComputerUseService
from app.services.human_assistance import AssistanceError, HumanAssistanceService
from app.services.mobile_agent import MobileAgentError, MobileAgentService
from app.services.mfa import MFAService, MFAError, totp_code
from app.services.website_credentials import (
    CredentialError,
    WebsiteCredentialService,
    generate_password,
)


class FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def scalars(self):
        return self

    def all(self):
        return self.rows

    def scalar_one_or_none(self):
        return self.rows[0] if self.rows else None


class FakeDB:
    def __init__(self, rows=None):
        self.rows = list(rows or [])

    def add(self, obj):
        if obj not in self.rows:
            if getattr(obj, "id", None) is None:
                obj.id = uuid.uuid4()
            self.rows.append(obj)

    async def flush(self):
        return None

    async def commit(self):
        return None

    async def execute(self, statement):
        entity = statement.column_descriptions[0]["entity"]
        return FakeResult([row for row in self.rows if isinstance(row, entity)])


def approvals(authorized=True):
    class Approvals:
        def __init__(self, _db):
            pass

        async def check_authorization(self, _action, requested_level="3", target_ref=None):
            if not authorized:
                return {"authorized": False}
            return {"authorized": True, "authorization_id": str(uuid.uuid4()), "signer_id": "signer"}

    return Approvals


class AssistTests(unittest.IsolatedAsyncioTestCase):
    async def test_levels_resolve_escalate(self):
        service = HumanAssistanceService(FakeDB())
        row = await service.request(
            level="2", reason="CAPTCHA", context={"url": "https://example.com"}, actor="iam"
        )
        self.assertEqual(row["human_action"], "assist")
        resolved = await service.resolve(row["id"], "creator", "iam")
        self.assertEqual(resolved["status"], "resolved")
        with self.assertRaises(AssistanceError):
            await service.resolve(row["id"], "creator", "iam")
        other = await service.request(level="5", reason="blocked", actor="iam")
        escalated = await service.escalate(other["id"], "iam", "unavailable")
        self.assertEqual(escalated["status"], "escalated")


class ComputerUseTests(unittest.IsolatedAsyncioTestCase):
    def test_coordinates_and_permission(self):
        service = ComputerUseService(FakeDB())
        self.assertEqual(service._coords(10, 20), (10, 20))
        with self.assertRaises(ComputerUseError):
            service._coords(99999, 0)

    async def test_disabled_by_default(self):
        service = ComputerUseService(FakeDB())
        with patch.object(settings, "uwai_computer_use_enabled", False):
            with self.assertRaises(ComputerUseError):
                await service.screenshot("session", "iam")


class MobileAgentTests(unittest.IsolatedAsyncioTestCase):
    async def test_device_allowlist_and_disabled(self):
        with patch.object(settings, "mobile_allowed_devices", "device-1,device-2"), patch.object(
            settings, "mobile_agent_enabled", False
        ):
            service = MobileAgentService(FakeDB())
            self.assertEqual(service._device("device-1"), "device-1")
            with self.assertRaises(MobileAgentError):
                service._device("unknown")
            with self.assertRaises(MobileAgentError):
                await service.tap("device-1", 10, 10, "iam")


class CredentialTests(unittest.IsolatedAsyncioTestCase):
    async def test_generate_register_reveal_rotate(self):
        db = FakeDB()
        service = WebsiteCredentialService(db)
        password = generate_password()
        self.assertGreaterEqual(len(password), 16)
        with patch("app.services.website_credentials.CreatorApprovalService", approvals()):
            row = await service.register(
                site="example", url="https://example.com", username="iam",
                owner_entity="Aura Holdings", password=password,
                secret_env_var=None, actor="iam",
            )
            revealed = await service.reveal(row["id"], "iam")
            rotated = await service.rotate(row["id"], "iam")
        self.assertTrue(row["has_stored_secret"])
        self.assertEqual(revealed["password"], password)
        self.assertNotEqual(rotated["password"], password)
        stored = next(item for item in db.rows if isinstance(item, WebsiteCredential))
        self.assertNotIn(rotated["password"], stored.secret_ciphertext)
        self.assertTrue(any(item.event_type == "website_credential_revealed" for item in db.rows if isinstance(item, AuditEvent)))

    async def test_env_reference_without_password(self):
        service = WebsiteCredentialService(FakeDB())
        row = await service.register(
            site="example", url="https://example.com", username="iam",
            owner_entity="Aura Holdings", password=None,
            secret_env_var="EXAMPLE_PASSWORD", actor="iam",
        )
        self.assertEqual(row["secret_env_var"], "EXAMPLE_PASSWORD")
        self.assertFalse(row["has_stored_secret"])
        with self.assertRaises(CredentialError):
            await service.register(
                site="x", url="https://x.example", username="u",
                owner_entity="Aura Holdings", password=None, secret_env_var=None, actor="iam",
            )


class TabTests(unittest.IsolatedAsyncioTestCase):
    async def test_multi_tab_lifecycle(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(
            settings, "uwai_upload_root", tmp
        ):
            browser = BrowserService()
            browser._browser = object()
            browser._context = type(
                "Context", (), {"new_page": AsyncMock(return_value=type(
                    "Page", (), {"is_closed": lambda self: False, "close": AsyncMock()}
                )())}
            )()
            tab_id = await browser.new_tab("session")
            self.assertIn(tab_id, await browser.list_tabs("session"))
            self.assertTrue(await browser.close_tab("session", tab_id))
            self.assertEqual(await browser.list_tabs("session"), [])


class MFATests(unittest.IsolatedAsyncioTestCase):
    async def test_passkey_registration_and_assertion(self):
        credential = WebsiteCredential(
            id=uuid.uuid4(), site="example", url="https://example.com",
            username="iam", secret_ciphertext="", owner_entity="Aura Holdings",
        )
        db = FakeDB([credential])
        service = MFAService(db)
        private_key = ec.generate_private_key(ec.SECP256R1())
        public_pem = private_key.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode("utf-8")
        with patch("app.services.mfa.CreatorApprovalService", approvals()):
            began = await service.begin_registration(str(credential.id), "example.com", "iam")
            registered = await service.complete_registration(
                began["challenge_id"], "cred-1", public_pem, "iam"
            )
            auth = await service.begin_authentication(registered["id"], "iam")
            client_data = json.dumps(
                {"type": "webauthn.get", "challenge": auth["challenge"], "origin": "https://example.com"},
                separators=(",", ":"),
            )
            auth_data = b"authenticator-data"
            signature = private_key.sign(
                auth_data + hashlib.sha256(client_data.encode("utf-8")).digest(),
                ec.ECDSA(hashes.SHA256()),
            )
            verified = await service.verify_assertion(
                auth["challenge_id"], "cred-1",
                base64.b64encode(auth_data).decode("ascii"),
                client_data,
                base64.b64encode(signature).decode("ascii"),
                "iam",
            )
        self.assertTrue(verified["verified"])
        self.assertTrue(any(isinstance(row, PasskeyCredential) for row in db.rows))

    async def test_totp_enrollment_and_verification(self):
        credential = WebsiteCredential(
            id=uuid.uuid4(), site="example", url="https://example.com",
            username="iam", secret_ciphertext="", owner_entity="Aura Holdings",
        )
        db = FakeDB([credential])
        service = MFAService(db)
        with patch("app.services.mfa.CreatorApprovalService", approvals()):
            enrolled = await service.enroll_totp(
                str(credential.id), "Example", "iam@example.com", "iam"
            )
            secret = enrolled["otpauth_uri"].split("secret=")[1].split("&")[0]
            verified = await service.verify_totp(
                str(credential.id), totp_code(secret), "iam"
            )
        self.assertTrue(verified["verified"])
        with self.assertRaises(MFAError):
            await service.verify_totp(str(credential.id), "000000", "iam")
        self.assertTrue(any(isinstance(row, TotpEnrollment) for row in db.rows))


if __name__ == "__main__":
    unittest.main()
