"""Phase 9 tests: owner-owned digital asset registry, licences and domains."""

import unittest
import uuid

from app.models.digitalassets import DomainRegistration
from app.models.security import AuditEvent
from app.services.digitalassets_service import (
    DigitalAssetError,
    DigitalAssetsService,
    validate_owner_entity,
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
    def __init__(self):
        self.rows = []

    def add(self, obj):
        if obj not in self.rows:
            if getattr(obj, "id", None) is None:
                obj.id = uuid.uuid4()
            self.rows.append(obj)

    async def delete(self, obj):
        if obj in self.rows:
            self.rows.remove(obj)

    async def flush(self):
        return None

    async def commit(self):
        return None

    async def execute(self, statement):
        entity = statement.column_descriptions[0]["entity"]
        return FakeResult([row for row in self.rows if isinstance(row, entity)])


def fake_request():
    state = type("State", (), {"credential": {"name": "iam"}})()
    return type("Request", (), {"state": state})()


class OwnershipTests(unittest.TestCase):
    def test_iam_cannot_own_assets(self):
        self.assertEqual(validate_owner_entity("Aura Holdings"), "Aura Holdings")
        for value in ("IAM", "self", "none", "aura", ""):
            with self.assertRaises(DigitalAssetError):
                validate_owner_entity(value)


class RegistryTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = FakeDB()
        self.service = DigitalAssetsService(self.db)

    async def test_asset_licence_ip_lifecycle(self):
        asset = await self.service.create(
            name="SDK feature",
            asset_type="software",
            owner_entity="Aura Holdings",
            source_code_location="git://internal/sdk.git",
            licence_type="MIT",
            actor="iam",
        )
        self.assertEqual(asset["owner_entity"], "Aura Holdings")
        licence = await self.service.add_licence(
            asset["id"], licence_text="MIT", licence_url="https://opensource.org/license/mit",
            granted_to="public", actor="iam",
        )
        self.assertEqual(licence["asset_id"], asset["id"])
        self.assertEqual(len(await self.service.licences(asset["id"])), 1)

        ip = await self.service.add_ip(
            asset["id"], ip_type="copyright", registration_number="CR-1",
            owner_entity="Aura Holdings", actor="iam",
        )
        self.assertEqual(ip["ip_type"], "copyright")
        self.assertEqual(len(await self.service.ip_records(asset["id"])), 1)

        updated = await self.service.update(asset["id"], {"description": "v2"}, "iam")
        self.assertEqual(updated["description"], "v2")
        deleted = await self.service.delete(asset["id"], "iam")
        self.assertEqual(deleted["status"], "deleted")
        self.assertTrue(any(row.event_type == "digital_asset_registered" for row in self.db.rows if isinstance(row, AuditEvent)))

    async def test_secrets_and_wrong_types_denied(self):
        with self.assertRaises(DigitalAssetError):
            await self.service.create(
                name="x", asset_type="unknown", owner_entity="Aura Holdings", actor="iam"
            )
        with self.assertRaises(DigitalAssetError):
            await self.service.create(
                name="x", asset_type="software", owner_entity="Aura Holdings",
                source_code_location="https://user:password@example.com/repo",
                actor="iam",
            )

    async def test_domain_registration_is_metadata_only(self):
        record = await self.service.register_domain(
            domain_name="Example.COM", registrar="Example Registrar",
            owner_entity="Aura Holdings", actor="iam",
        )
        self.assertEqual(record["domain_name"], "example.com")
        self.assertFalse(record["live_registration"])
        with self.assertRaises(DigitalAssetError):
            await self.service.register_domain(
                domain_name="not a domain", owner_entity="Aura Holdings", actor="iam"
            )
        self.assertTrue(any(isinstance(row, DomainRegistration) for row in self.db.rows))


if __name__ == "__main__":
    unittest.main()
