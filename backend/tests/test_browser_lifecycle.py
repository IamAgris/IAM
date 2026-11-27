"""Doc 29 P8 tests: versioning, backups, approvals and lifecycle evidence."""

import json
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, patch

from app.api.routes import browser_lifecycle as lifecycle_routes
from app.core.config import settings
from app.models.web_knowledge import BrowserLifecycleRecord
from app.services.browser_lifecycle import (
    BrowserLifecycleError,
    BrowserLifecycleService,
    installed_version,
)


class FakeResult:
    def __init__(self, rows, scalar=None):
        self.rows = rows
        self.scalar_value = scalar

    def scalars(self):
        return self

    def all(self):
        return self.rows

    def scalar_one(self):
        return self.scalar_value or 0

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

    async def flush(self):
        return None

    async def commit(self):
        return None

    async def execute(self, statement):
        return FakeResult([], scalar=2)


class SnapshotTests(unittest.TestCase):
    def test_snapshot_has_version_and_digest(self):
        service = BrowserLifecycleService(object())
        snapshot = service.snapshot()
        self.assertEqual(len(snapshot["sha256"]), 64)
        self.assertIn("playwright", snapshot["packages"])
        self.assertIn("not proof", snapshot["note"])

    def test_vulnerability_scan_flags_outdated_component(self):
        service = BrowserLifecycleService(object())
        with patch(
            "app.services.browser_lifecycle.installed_version",
            side_effect=lambda name: "1.0.0" if name == "playwright" else "9.9.9",
        ):
            result = service.vulnerability_scan()
        self.assertEqual(result["components"]["playwright"]["status"], "outdated")
        self.assertFalse(result["cve_scan_claimed"])
        self.assertNotEqual(installed_version("definitely-not-installed"), "9.9.9")


class LifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.settings_patch = patch.object(
            settings, "browser_evidence_dir", self.tempdir.name
        )
        self.settings_patch.start()
        self.db = FakeDB()
        self.service = BrowserLifecycleService(self.db)

    async def asyncTearDown(self):
        self.settings_patch.stop()
        self.tempdir.cleanup()

    async def test_health_never_claims_operational(self):
        with patch("app.services.browser_lifecycle.Path") as path_cls:
            path_cls.return_value.is_dir.return_value = True
            path_cls.return_value.is_file.return_value = True
            path_cls.return_value.resolve.return_value = Path(self.tempdir.name)
            result = await self.service.health()
        self.assertFalse(result["claimed_operational"])
        self.assertIn("ocr", result["checks"])

    async def test_backup_and_integrity_verification(self):
        record = await self.service.backup("iam")
        self.assertEqual(record["event_type"], "backup")
        self.assertTrue(Path(record["backup_ref"]).is_file())
        verified = await self.service.verify_backup(record["backup_ref"], "iam")
        self.assertEqual(verified["status"], "verified")
        self.assertFalse(verified["restore_applied"])

    async def test_backup_outside_root_is_denied(self):
        with self.assertRaises(BrowserLifecycleError):
            await self.service.verify_backup(
                str(Path(self.tempdir.name).parent / "outside.json"), "iam"
            )

    async def test_update_requires_signed_approval(self):
        with patch(
            "app.services.browser_lifecycle.CreatorApprovalService"
        ) as approval_cls:
            approval_cls.return_value.check_authorization = AsyncMock(
                return_value={"authorized": False}
            )
            with self.assertRaises(BrowserLifecycleError):
                await self.service.apply_update("chromium", "new", "iam")
            approval_cls.return_value.check_authorization = AsyncMock(
                return_value={"authorized": True, "authorization_id": "a1"}
            )
            result = await self.service.apply_update("chromium", "new", "creator")
        self.assertFalse(result["installation_performed"])
        rows = [r for r in self.db.rows if isinstance(r, BrowserLifecycleRecord)]
        self.assertEqual(rows[0].status, "applied")

    async def test_retire_tor_disables_flags(self):
        with patch(
            "app.services.browser_lifecycle.CreatorApprovalService"
        ) as approval_cls, patch.object(settings, "tor_enabled", True), patch.object(
            settings, "tor_onion_access_enabled", True
        ):
            approval_cls.return_value.check_authorization = AsyncMock(
                return_value={"authorized": True}
            )
            result = await self.service.retire("tor", "outdated", "creator")
        self.assertEqual(result["status"], "retired")
        self.assertFalse(settings.tor_enabled)
        self.assertFalse(settings.tor_onion_access_enabled)

    async def test_audit_report_and_performance_budget(self):
        report = await self.service.audit_report()
        self.assertFalse(report["secret_values_logged"])
        budget = self.service.performance_budget()
        self.assertFalse(budget["measured"])
        self.assertIn("IRWM", budget["model_ram_governed_by"])


class RouteTests(unittest.IsolatedAsyncioTestCase):
    async def test_snapshot_route(self):
        result = await lifecycle_routes.snapshot()
        self.assertIn("sha256", result)

    async def test_health_route_delegates(self):
        with patch.object(lifecycle_routes, "BrowserLifecycleService") as service_cls:
            service_cls.return_value.health = AsyncMock(return_value={"healthy": False})
            result = await lifecycle_routes.health(object())
        self.assertFalse(result["healthy"])


if __name__ == "__main__":
    unittest.main()
