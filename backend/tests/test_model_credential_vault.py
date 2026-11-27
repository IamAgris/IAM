"""OD-51 §4.1/§4.2: encrypted provider keys, isolation and fail-closed failover."""

import unittest
import uuid
from unittest.mock import AsyncMock, patch

from app.models.model_provider_key import ModelProviderKey
from app.services.crypto_service import crypto
from app.services.model_credential_vault import (
    VaultError,
    ModelCredentialVault,
)


class FakeResult:
    def __init__(self, rows):
        self.rows = list(rows)

    def scalars(self):
        return self

    def all(self):
        return self.rows

    def scalar_one_or_none(self):
        return self.rows[0] if self.rows else None


class FakeDB:
    def __init__(self, rows=None):
        self.rows = list(rows or [])

    async def execute(self, statement):
        name = ""
        try:
            froms = list(statement.froms)
            name = getattr(froms[0], "name", "") if froms else ""
        except Exception:
            name = str(statement)
        rows = [r for r in self.rows if getattr(r.__class__, "__tablename__", "") in name]
        return FakeResult(rows)

    def add(self, obj):
        if getattr(obj, "id", None) is None:
            obj.id = uuid.uuid4()
        self.rows.append(obj)

    async def flush(self):
        return None

    async def commit(self):
        return None


def _key(alias, secret, scope="free", health="unknown", enabled=True, failure=0):
    return ModelProviderKey(
        provider="nvidia",
        key_alias=alias,
        key_fingerprint=ModelCredentialVault.fingerprint(secret),
        secret_ciphertext=crypto.encrypt(secret),
        scope=scope,
        is_enabled=enabled,
        health=health,
        failure_count=failure,
    )


class ModelCredentialVaultTests(unittest.IsolatedAsyncioTestCase):
    async def test_register_encrypts_and_never_returns_secret(self):
        db = FakeDB()
        with patch(
            "app.services.model_credential_vault.require_authorization",
            new=AsyncMock(return_value={"authorized": True}),
        ):
            result = await ModelCredentialVault(db).register(
                provider="nvidia", key_alias="primary", secret="nv-secret-1", scope="free"
            )
        row = db.rows[0]
        self.assertTrue(row.secret_ciphertext.startswith("enc:v1:"))
        self.assertNotEqual(row.secret_ciphertext, "nv-secret-1")
        self.assertNotIn("secret", result)
        self.assertNotIn("secret_ciphertext", result)
        self.assertEqual(row.key_fingerprint, ModelCredentialVault.fingerprint("nv-secret-1"))

    async def test_unhealthy_key_fails_over_only_to_another_authorised_key(self):
        db = FakeDB([_key("bad", "bad-secret", health="unhealthy"), _key("good", "good-secret")])
        vault = ModelCredentialVault(db)
        row, secret = await vault.resolve(provider="nvidia")
        self.assertEqual(row.key_alias, "good")
        self.assertEqual(secret, "good-secret")

    async def test_paid_work_requires_paid_scoped_key(self):
        db = FakeDB([_key("free-only", "free-secret", scope="free")])
        with self.assertRaises(VaultError):
            await ModelCredentialVault(db).resolve(provider="nvidia", is_paid=True)

    async def test_disabled_key_is_never_selected(self):
        db = FakeDB([_key("off", "off-secret", enabled=False)])
        with self.assertRaises(VaultError):
            await ModelCredentialVault(db).resolve(provider="nvidia")

    async def test_disable_requires_signed_authorization(self):
        key = _key("k", "s")
        key.id = uuid.uuid4()
        db = FakeDB([key])
        with patch(
            "app.services.model_credential_vault.require_authorization",
            new=AsyncMock(side_effect=VaultError("no signed authorization")),
        ):
            with self.assertRaises(VaultError):
                await ModelCredentialVault(db).disable(str(key.id))
        self.assertTrue(key.is_enabled)


if __name__ == "__main__":
    unittest.main()
