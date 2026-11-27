"""Run an OD-06 disaster-recovery drill against a real Postgres database.

Usage:
    IAM_RESTORE_DSN=postgresql://user:pass@host:5432/iam_restore \
        python scripts/backup_restore_drill.py

The restore target MUST be a separate database. The script refuses to run
without an explicit target and never restores over production.
"""

import asyncio
import os
import sys

from app.core.database import AsyncSessionLocal
from app.services.backup_service import BackupService, BackupError


async def main() -> int:
    target = os.environ.get("IAM_RESTORE_DSN")
    if not target:
        print("IAM_RESTORE_DSN is required (an isolated database, not production)", file=sys.stderr)
        return 2
    async with AsyncSessionLocal() as db:
        service = BackupService(db)
        try:
            backup = await service.create_backup("drill")
            verified = await service.verify_backup(backup["backup_id"])
            result = await service.restore_isolated(backup["backup_id"], target)
        except BackupError as exc:
            print(f"DR drill FAILED: {exc}", file=sys.stderr)
            return 1
        print("DR drill PASSED")
        print("backup:", backup["backup_id"], backup["sha256"])
        print("verified objects:", verified["object_entries"])
        print("restored tables:", result["restored_tables"], "/", result["source_tables"])
        print("RPO hours:", result["rpo_hours"], "target", result["rpo_target_hours"])
        print("RTO hours:", result["rto_hours"], "target", result["rto_target_hours"])
        return 0 if result["rpo_met"] and result["rto_met"] else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
