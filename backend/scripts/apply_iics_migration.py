#!/usr/bin/env python3
"""Apply the IICS foundation migration (057) to a deployment database.

The numbered SQL migrations are idempotent (CREATE TABLE IF NOT EXISTS), so
re-running this script is safe. Usage:

    python backend/scripts/apply_iics_migration.py

DATABASE_URL is read from the environment / backend .env. The script prints
APPLIED or SKIPPED and never prints credentials.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import asyncpg

BACKEND = Path(__file__).resolve().parents[1]
MIGRATION = BACKEND / "app" / "db" / "migrations" / "057_iics_foundation.sql"
ENV_FILE = BACKEND / ".env"


def load_env() -> None:
    if not ENV_FILE.is_file():
        return
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        if not line or line.lstrip().startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


async def apply(dsn: str) -> int:
    connection = await asyncpg.connect(dsn)
    try:
        await connection.execute(MIGRATION.read_text(encoding="utf-8"))
        count = await connection.fetchval(
            "SELECT count(*) FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name LIKE 'iics_%'"
        )
    finally:
        await connection.close()
    return int(count)


def main() -> int:
    load_env()
    dsn = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_DSN")
    if not dsn:
        print("SKIPPED: DATABASE_URL is not configured")
        return 0
    if dsn.startswith("sqlite"):
        print("SKIPPED: SQLite uses create_all in development; no SQL migration needed")
        return 0
    try:
        import asyncio

        tables = asyncio.run(apply(dsn))
    except Exception as exc:
        print(f"FAILED: {type(exc).__name__}")
        return 1
    print(f"APPLIED: {MIGRATION.name} ({tables} iics_* tables present)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
