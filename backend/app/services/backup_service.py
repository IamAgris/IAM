"""OD-06 disaster recovery: real backups, isolated restore and measured RPO/RTO.

This service never records a "backup verified" event it has not earned. A backup
is a real pg_dump archive with a computed SHA-256; verification re-hashes the
file and asks pg_restore to list the archive; a restore drill targets a separate
database and refuses to touch the production DSN. RPO and RTO are measured from
timestamps, not asserted.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlsplit, urlunsplit

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.security import AuditEvent


class BackupError(RuntimeError):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.isoformat()


def _redact(dsn: str) -> str:
    """Remove credentials from a DSN before it is logged or audited."""
    try:
        parts = urlsplit(dsn)
        host = parts.hostname or ""
        if parts.port:
            host = f"{host}:{parts.port}"
        netloc = f"{parts.username or ''}@{host}" if parts.username else host
        return urlunsplit((parts.scheme, netloc, parts.path, "", ""))
    except Exception:
        return "<redacted>"


def _container_mode() -> bool:
    return bool(settings.backup_container_service)


def _command(tool: str, *args: str) -> list[str]:
    """Build a command that runs a Postgres client either on the host or in a container."""
    if _container_mode():
        return [
            "docker", "compose", "exec", "-T", settings.backup_container_service, tool, *args
        ]
    return [tool, *args]


def _dsn() -> str:
    if _container_mode():
        if settings.backup_container_dsn:
            return settings.backup_container_dsn
        return (
            f"postgresql://{settings.postgres_user}:{settings.postgres_password}"
            f"@{settings.backup_container_service}:5432/{settings.postgres_db}"
        )
    if settings.database_url:
        return settings.database_url
    return (
        f"postgresql://{settings.postgres_user}:{settings.postgres_password}"
        f"@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
    )


async def _run(*args: str) -> Tuple[int, str, str]:
    process = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    return (
        process.returncode or 0,
        stdout.decode("utf-8", errors="replace"),
        stderr.decode("utf-8", errors="replace"),
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


async def _file_size(path: Path) -> Optional[int]:
    if _container_mode():
        code, out, _err = await _run(*_command("stat", "-c", "%s", str(path)))
        return int(out.strip()) if code == 0 and out.strip().isdigit() else None
    try:
        return path.stat().st_size
    except OSError:
        return None


async def _file_hash(path: Path) -> str:
    if _container_mode():
        code, out, _err = await _run(*_command("sha256sum", str(path)))
        token = out.strip().split()[0].lstrip("\\") if out.strip() else ""
        if code != 0 or len(token) != 64:
            raise BackupError("could not hash the backup archive in the container")
        return token
    return _sha256(path)


class BackupService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _root(self) -> Path:
        root = Path(settings.backup_directory)
        root.mkdir(parents=True, exist_ok=True)
        return root

    def _metadata_path(self, backup_id: str) -> Path:
        return self._root() / f"{backup_id}.json"

    def _load(self, backup_id: str) -> Dict[str, Any]:
        path = self._metadata_path(backup_id)
        if not path.exists():
            raise BackupError("backup metadata not found")
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise BackupError(f"unreadable backup metadata: {type(exc).__name__}") from exc

    async def _audit(self, event_type: str, details: Dict[str, Any]) -> None:
        self.db.add(
            AuditEvent(
                event_type=event_type,
                actor="backup-service",
                target=_redact(_dsn()),
                details={key: value for key, value in details.items() if "dsn" not in key},
            )
        )
        await self.db.commit()

    async def create_backup(self, label: str = "scheduled") -> Dict[str, Any]:
        """Create a real pg_dump custom-format archive and record its checksum."""
        safe_label = "".join(ch for ch in label if ch.isalnum() or ch in "-_")[:40] or "scheduled"
        backup_id = f"iam-{_now().strftime('%Y%m%dT%H%M%SZ')}-{safe_label}"
        if _container_mode():
            # Keep the path POSIX inside the container; Path() on Windows would
            # turn /tmp/x into \tmp\x and create a literal backslash filename.
            archive = Path(f"{settings.backup_directory.rstrip('/')}/{backup_id}.dump")
        else:
            archive = self._root() / f"{backup_id}.dump"
        started = _now()
        code, _out, err = await _run(
            *_command(
                settings.backup_pg_dump_bin,
                "--format=custom",
                "--no-owner",
                "--no-privileges",
                f"--file={archive}",
                _dsn(),
            )
        )
        size = await _file_size(archive)
        if code != 0 or not size:
            raise BackupError(f"pg_dump failed ({code}): {err[:300]}")
        finished = _now()
        checksum = await _file_hash(archive)
        metadata = {
            "backup_id": backup_id,
            "archive": str(archive),
            "sha256": checksum,
            "bytes": size,
            "started_at": _iso(started),
            "finished_at": _iso(finished),
            "source": _redact(_dsn()),
            "format": "custom",
        }
        self._metadata_path(backup_id).write_text(
            json.dumps(metadata, sort_keys=True), encoding="utf-8"
        )
        await self._audit(
            "backup.created",
            {"backup_id": backup_id, "sha256": checksum, "bytes": metadata["bytes"]},
        )
        await self._prune()
        return metadata

    async def _prune(self) -> None:
        backups = sorted(
            (p for p in self._root().glob("iam-*.json")),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        for old in backups[settings.backup_retention_count :]:
            try:
                archive = Path(json.loads(old.read_text(encoding="utf-8"))["archive"])
                if _container_mode():
                    await _run(*_command("rm", "-f", str(archive)))
                else:
                    archive.unlink(missing_ok=True)
                old.unlink(missing_ok=True)
            except (OSError, ValueError, KeyError):
                continue

    async def verify_backup(self, backup_id: str) -> Dict[str, Any]:
        """Re-hash the archive and confirm pg_restore can read its table of contents."""
        metadata = self._load(backup_id)
        archive = Path(metadata["archive"])
        if not await _file_size(archive):
            raise BackupError("backup archive is missing")
        actual = await _file_hash(archive)
        if actual != metadata.get("sha256"):
            raise BackupError("backup checksum mismatch")
        code, out, err = await _run(
            *_command(settings.backup_pg_restore_bin, "--list", str(archive))
        )
        if code != 0:
            raise BackupError(f"pg_restore could not read archive: {err[:300]}")
        result = {
            "backup_id": backup_id,
            "verified": True,
            "sha256": actual,
            "object_entries": len([line for line in out.splitlines() if line.strip()]),
            "verified_at": _iso(_now()),
        }
        await self._audit("backup.verified", result)
        return result

    async def restore_isolated(
        self, backup_id: str, target_dsn: str, actor: str = "operator"
    ) -> Dict[str, Any]:
        """Restore to a separate database, verify it, and measure RPO/RTO."""
        if not target_dsn or target_dsn == _dsn():
            raise BackupError("restore target must be an isolated database, not production")
        metadata = self._load(backup_id)
        verified = await self.verify_backup(backup_id)
        started = _now()
        code, _out, err = await _run(
            *_command(
                settings.backup_pg_restore_bin,
                "--clean",
                "--if-exists",
                "--no-owner",
                "--no-privileges",
                f"--dbname={target_dsn}",
                metadata["archive"],
            )
        )
        if code != 0:
            raise BackupError(f"isolated pg_restore failed ({code}): {err[:300]}")
        restored_at = _now()

        source_rows = (
            await self.db.execute(
                text("SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public'")
            )
        ).scalar_one()
        code, out, err = await _run(
            *_command(
                settings.backup_psql_bin,
                target_dsn,
                "-tAc",
                "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public'",
            )
        )
        if code != 0:
            raise BackupError(f"restored-database verification failed: {err[:300]}")
        restored_tables = int(out.strip() or 0)
        if restored_tables != int(source_rows):
            raise BackupError(
                f"restore verification failed: source={source_rows} restored={restored_tables}"
            )

        taken_at = datetime.fromisoformat(metadata["finished_at"])
        rpo_hours = (started - taken_at).total_seconds() / 3600
        rto_hours = (restored_at - started).total_seconds() / 3600
        result = {
            "backup_id": backup_id,
            "verified": verified["verified"],
            "target": _redact(target_dsn),
            "restored_tables": restored_tables,
            "source_tables": int(source_rows),
            "rpo_hours": round(rpo_hours, 4),
            "rto_hours": round(rto_hours, 4),
            "rpo_target_hours": settings.backup_rpo_hours,
            "rto_target_hours": settings.backup_rto_hours,
            "rpo_met": rpo_hours <= settings.backup_rpo_hours,
            "rto_met": rto_hours <= settings.backup_rto_hours,
            "actor": actor,
            "restored_at": _iso(restored_at),
        }
        await self._audit("dr.restore_verified", result)
        return result
