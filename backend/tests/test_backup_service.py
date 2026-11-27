"""OD-06: backups are real archives and restore drills verify an isolated target."""

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.core.config import settings
from app.services.backup_service import BackupError, BackupService, _dsn


class FakeDB:
    def __init__(self, table_count=3):
        self.table_count = table_count
        self.added = []
        self.commits = 0

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        self.commits += 1

    async def execute(self, statement):
        return SimpleNamespace(scalar_one=lambda: self.table_count)


def fake_run(table_count="3"):
    async def run(*args):
        if args[0] == settings.backup_pg_dump_bin:
            target = next(a.split("=", 1)[1] for a in args if a.startswith("--file="))
            Path(target).write_bytes(b"pgdump-archive-content")
            return 0, "", ""
        if args[0] == settings.backup_pg_restore_bin and "--list" in args:
            return 0, "table public.goals\ntable public.tasks\ntable public.memory_items\n", ""
        if args[0] == settings.backup_pg_restore_bin:
            return 0, "", ""
        if args[0] == settings.backup_psql_bin:
            return 0, table_count + "\n", ""
        return 1, "", "unexpected command"

    return run


class BackupServiceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root_patch = patch.object(settings, "backup_directory", self.tmp.name)
        self.root_patch.start()
        self.addCleanup(self.root_patch.stop)

    async def test_create_backup_writes_real_archive_and_checksum(self):
        with patch("app.services.backup_service._run", new=fake_run()):
            result = await BackupService(FakeDB()).create_backup("nightly")
        archive = Path(result["archive"])
        self.assertTrue(archive.exists())
        self.assertGreater(archive.stat().st_size, 0)
        self.assertEqual(len(result["sha256"]), 64)
        self.assertTrue(Path(self.tmp.name, result["backup_id"] + ".json").exists())

    async def test_verify_backup_rejects_tampered_archive(self):
        with patch("app.services.backup_service._run", new=fake_run()):
            service = BackupService(FakeDB())
            result = await service.create_backup("nightly")
            archive = Path(result["archive"])
            archive.write_bytes(b"tampered")
            with self.assertRaisesRegex(BackupError, "checksum mismatch"):
                await service.verify_backup(result["backup_id"])

    async def test_restore_refuses_production_target(self):
        with patch("app.services.backup_service._run", new=fake_run()):
            service = BackupService(FakeDB())
            created = await service.create_backup("nightly")
            with self.assertRaisesRegex(BackupError, "isolated database"):
                await service.restore_isolated(created["backup_id"], _dsn())

    async def test_restore_isolated_measures_rpo_rto_and_verifies_tables(self):
        with patch("app.services.backup_service._run", new=fake_run()):
            service = BackupService(FakeDB(table_count=3))
            created = await service.create_backup("nightly")
            result = await service.restore_isolated(
                created["backup_id"], "postgresql://restore:secret@127.0.0.1:5433/aura_restore"
            )
        self.assertTrue(result["verified"])
        self.assertEqual(result["restored_tables"], 3)
        self.assertTrue(result["rpo_met"])
        self.assertTrue(result["rto_met"])
        self.assertNotIn("secret", str(result))
        self.assertTrue(
            any(getattr(item, "event_type", "") == "dr.restore_verified" for item in service.db.added)
        )

    async def test_restore_rejects_table_count_mismatch(self):
        with patch("app.services.backup_service._run", new=fake_run(table_count="1")):
            service = BackupService(FakeDB(table_count=3))
            created = await service.create_backup("nightly")
            with self.assertRaisesRegex(BackupError, "restore verification failed"):
                await service.restore_isolated(
                    created["backup_id"], "postgresql://restore@localhost:5433/aura_restore"
                )


if __name__ == "__main__":
    unittest.main()
