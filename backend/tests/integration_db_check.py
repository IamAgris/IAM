"""Postgres integration check for Skill Forge, Creator approval and ARTEX.

Runs against a throwaway database, never the live ``aura_db``.

Usage (from backend/):
    $env:DATABASE_URL = "postgresql+asyncpg://aura:<pw>@127.0.0.1:5434/aura_integration_test"
    python tests/integration_db_check.py
"""

import asyncio
import base64
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import asyncpg
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[1]  # backend/
MIGRATIONS = ROOT / "app" / "db" / "migrations"
TEST_DB = "aura_integration_test"
HOST = os.environ.get("POSTGRES_HOST", "127.0.0.1")
PORT = int(os.environ.get("POSTGRES_PORT", "5434"))
USER = os.environ.get("POSTGRES_USER", "aura")
PASSWORD = os.environ.get("POSTGRES_PASSWORD", "change-me-securely")

INSTRUCTIONS = (
    "# Integration helper\n\n"
    "Use this skill to summarise authorized lab notes into short bullet points.\n"
    "Keep the original meaning and cite the source section for each point.\n"
    "Do not access the network or modify files outside the provided input.\n"
)


def _dsn(database: str) -> str:
    return f"postgresql://{USER}:{PASSWORD}@{HOST}:{PORT}/{database}"


async def apply_migrations() -> None:
    admin = await asyncpg.connect(_dsn("postgres"))
    exists = await admin.fetchval(
        "SELECT 1 FROM pg_database WHERE datname = $1", TEST_DB
    )
    if exists:
        await admin.execute(f'DROP DATABASE IF EXISTS "{TEST_DB}"')
    await admin.execute(f'CREATE DATABASE "{TEST_DB}"')
    await admin.close()

    from app.core.config import settings

    settings.app_debug = False

    # 0001 is generated from ORM metadata in dependency order, so Alembic is
    # now the authoritative path. 002-005 are raw SQL and are idempotent.
    result = await asyncio.to_thread(
        subprocess.run,
        [sys.executable, "-m", "alembic", "-c", str(ROOT / "alembic.ini"), "upgrade", "head"],
        cwd=ROOT.parent,
        env=os.environ.copy(),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr, file=sys.stderr)
        raise RuntimeError("alembic upgrade failed")
    print("  applied alembic 0001_initial")

    conn = await asyncpg.connect(_dsn(TEST_DB))
    for name in (
        "002_skillforge.sql",
        "003_security_engines.sql",
        "004_creator_email_approval.sql",
        "005_retire_legacy_owner_authorizations.sql",
        "006_creator_email_outbox.sql",
        "007_api_credentials.sql",
        "008_retire_legacy_approval_requests.sql",
        "009_skill_runtime.sql",
        "010_creator_email_dead_letter.sql",
        "011_skill_runtime_logs.sql",
    ):
        sql = (MIGRATIONS / name).read_text(encoding="utf-8")
        await conn.execute(sql)
        print(f"  applied {name}")
    tables = await conn.fetchval(
        "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public'"
    )
    print(f"  {tables} tables present")
    await conn.close()


async def run_checks() -> None:
    from app.core.config import settings
    from app.core.database import get_session_factory

    settings.app_debug = False  # keep the check output readable
    settings.skillforge_root = tempfile.mkdtemp(prefix="aura-skillforge-int-")
    private_key = Ed25519PrivateKey.generate()
    settings.creator_public_key = base64.b64encode(
        private_key.public_key().public_bytes_raw()
    ).decode()
    settings.creator_email = "creator@iam.example"
    settings.creator_signer_id = "integration-signer"
    settings.creator_email_transport = "log"
    settings.creator_gateway_secret = "integration-gateway-secret"
    settings.skill_runtime_enabled = True
    settings.skill_runtime_adapter = "stub"
    settings.creator_challenge_ttl_seconds = 3600
    settings.creator_authorization_ttl_seconds = 3600

    from app.services.creatorapproval_service import CreatorApprovalService
    from app.services.cybersecurity.service import SecurityEngineService
    from app.services.governance_service import GovernanceService
    from app.services.skillforge.engine import SkillBuildRequest
    from app.services.skillforge.service import SkillForgeService

    def sign(digest: str, decision: str = "approved") -> str:
        return base64.b64encode(
            private_key.sign(f"{digest}|{decision}".encode("utf-8"))
        ).decode()

    async def authorize(action: str, level: str, target: str | None, summary: str) -> None:
        service = CreatorApprovalService(db)
        request = await service.create_request(
            action_type=action,
            summary=summary,
            consequences=["Integration test approval"],
            risk_level=level,
            target_ref=target,
        )
        result = await service.decide(
            request["request_id"],
            decision="approved",
            signature=sign(request["challenge_hash"]),
            signer_id=settings.creator_signer_id,
        )
        assert result["signature_verified"] is True

    session_factory = get_session_factory()
    async with session_factory() as db:
        # --- Skill Forge: ordinary lifecycle + version rollback ----------------
        forge = SkillForgeService(db)
        sid = "iam.native.testing.integration_personal"
        await forge.create(
            SkillBuildRequest(
                skill_id=sid,
                name="Integration personal",
                instructions=INSTRUCTIONS,
                permissions=["knowledge", "task_workflow"],
            )
        )
        assert (await forge.validate(sid))["valid"]
        assert all(r["passed"] for r in (await forge.test(sid))["results"])
        assert (await forge.publish(sid))["status"] == "published"
        assert (await forge.activate(sid))["status"] == "active"
        await forge.create(
            SkillBuildRequest(
                skill_id=sid,
                name="Integration personal",
                version="1.1.0",
                instructions=INSTRUCTIONS + "\nAdditional guidance.\n",
                permissions=["knowledge", "task_workflow"],
            )
        )
        assert (await forge.rollback(sid, "1.0.0"))["version"] == "1.0.0"
        await forge.activate(sid)
        print("  PASS skillforge personal lifecycle + rollback")

        # --- Skill Runtime: gated execution ----------------------------------
        from app.services.skillruntime.service import (
            SkillRuntimeError,
            SkillRuntimeService,
        )

        runtime = SkillRuntimeService(db)
        invocation = await runtime.invoke(
            sid, permission="knowledge", arguments={"input": "integration"}
        )
        assert invocation["execution"]["status"] == "completed"
        assert invocation["execution"]["dry_run"] is True
        try:
            await runtime.invoke(sid, permission="security_analysis")
        except SkillRuntimeError:
            pass
        else:
            raise AssertionError("ungranted permission should be denied")
        executions = await runtime.executions(sid)
        assert any(e["status"] == "denied" for e in executions)
        print("  PASS skill runtime gated invocation + denial audit")

        # --- Skill Forge: sensitive skill requires signed email approval -------
        sensitive_id = "iam.native.security.integration_defensive"
        await forge.create(
            SkillBuildRequest(
                skill_id=sensitive_id,
                name="Integration defensive",
                classification="sensitive",
                permissions=["security_analysis", "remediation_guidance"],
                requires_creator_approval=True,
                instructions=INSTRUCTIONS,
            )
        )
        await forge.validate(sensitive_id)
        assert all(r["passed"] for r in (await forge.test(sensitive_id))["results"])
        request = await forge.request_approval(sensitive_id, reason="integration")
        creator_service = CreatorApprovalService(db)
        outbox = await creator_service.outbox()
        assert outbox and outbox[0]["status"] == "sent"
        assert outbox[0]["transport"] == "log"
        challenge = await creator_service.challenge_for_signer(request["request_id"])
        assert challenge["challenge_hash"] == request["challenge_hash"]

        # Worker retries failed deliveries without changing approval authority.
        from app.models.creatorapproval import CreatorEmailOutbox
        from app.workers.creator_email_worker import CreatorEmailWorker

        row = (
            await db.execute(
                select(CreatorEmailOutbox).where(
                    CreatorEmailOutbox.request_id == request["request_id"]
                )
            )
        ).scalar_one()
        row.status = "failed"
        await db.commit()
        await CreatorEmailWorker(interval=999)._cycle()
        db.expire_all()  # the worker committed through a separate session
        retried = await creator_service.outbox()
        assert any(
            r["request_id"] == request["request_id"] and r["status"] == "sent"
            for r in retried
        )
        print("  PASS creator email outbox + signer challenge + retry worker")
        await CreatorApprovalService(db).decide(
            request["request_id"],
            decision="approved",
            signature=sign(request["challenge_hash"]),
            signer_id=settings.creator_signer_id,
        )
        assert (await forge.publish(sensitive_id))["status"] == "published"
        print("  PASS skillforge sensitive signed-approval publish")

        # --- ARTEX / external security engine ---------------------------------
        await authorize(
            "cybersecurity.engine_register", "4", "integration-artex", "Register engine"
        )
        engines = SecurityEngineService(db)
        engine = await engines.register_engine(
            name="integration-artex",
            base_url="http://127.0.0.1:8787",
            enabled=True,
            dry_run=True,
        )
        await authorize(
            "cybersecurity.scope_register", "3", "lab.integration.local", "Register scope"
        )
        await engines.add_scope(
            engine["id"], target="lab.integration.local", target_type="host"
        )
        await authorize("security_testing", "3", None, "Security testing")
        task = await engines.create_task(
            engine["id"],
            target="lab.integration.local",
            description="Integration read-only check",
            operation="list_task_findings",
        )
        await authorize("cybersecurity.task_approve", "3", task["id"], "Approve task")
        assert (await engines.approve_task(task["id"]))["status"] == "authorized"
        dispatched = await engines.dispatch_task(task["id"])
        assert dispatched["transport_result"]["dry_run"] is True
        await engines.sync_task(task["id"])
        print("  PASS ARTEX dry-run task lifecycle")

        # --- Findings → remediation → Skill Forge handoff ---------------------
        await engines.ingest_findings(
            task["id"],
            [
                {
                    "id": "finding-1",
                    "title": "Missing security header",
                    "severity": "high",
                    "description": "Header absent on the lab endpoint",
                }
            ],
        )
        findings = await engines.findings_for_task(task["id"])
        assert len(findings) == 1
        await engines.remediate(findings[0]["id"], "Add the missing security header.")
        handoff = await engines.create_defensive_skill(task["id"])
        assert handoff["requires_creator_approval"] is True
        print("  PASS finding normalisation + defensive skill handoff")

        # --- Governance now uses signed Creator authority ---------------------
        from app.models.governance import AuthorityBoundary

        db.add(
            AuthorityBoundary(
                action_type="integration.high_impact",
                authority_level="4",
                description="Integration test boundary",
                requires_human_approval=True,
            )
        )
        await db.commit()
        governance = GovernanceService(db)
        await authorize("integration.high_impact", "4", None, "Governance check")
        result = await governance.check_authority("integration.high_impact", "1")
        assert result["permitted"] is True
        assert result["source"] == "signed_creator_authorization"
        print("  PASS governance signed-authorization check")

        # --- API authentication + rate limiting -------------------------------
        from httpx import ASGITransport, AsyncClient
        from app.main import app

        os.environ["IAM_BOOTSTRAP_API_KEY"] = "integration-bootstrap"
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            bootstrap = await client.post(
                "/api/v1/auth/bootstrap",
                json={"name": "integration-admin", "scope": "admin"},
                headers={"X-Bootstrap-Key": "integration-bootstrap"},
            )
            assert bootstrap.status_code == 201, bootstrap.text
            admin_headers = {"Authorization": f"Bearer {bootstrap.json()['key']}"}

            assert (await client.get("/api/v1/skill-forge/skills")).status_code == 401
            assert (await client.get("/health")).status_code == 200
            assert (
                await client.get("/api/v1/auth/me", headers=admin_headers)
            ).status_code == 200
            admin_skills = await client.get(
                "/api/v1/skill-forge/skills", headers=admin_headers
            )
            assert admin_skills.status_code == 200, (
                admin_skills.status_code,
                admin_skills.text[:500],
            )

            user = await client.post(
                "/api/v1/auth/credentials",
                json={"name": "integration-user", "scope": "user"},
                headers=admin_headers,
            )
            assert user.status_code == 201, user.text
            user_headers = {"Authorization": f"Bearer {user.json()['key']}"}
            assert (
                await client.get("/api/v1/skill-forge/skills", headers=user_headers)
            ).status_code == 403

            # External-presence approval now uses the signed Creator email flow.
            integration = await client.post(
                "/api/v1/external-presence/integrations",
                json={
                    "name": "integration-lab",
                    "provider": "lab",
                    "integration_type": "business",
                    "requires_human_approval": True,
                },
                headers=admin_headers,
            )
            assert integration.status_code == 200, integration.text
            integ = integration.json()
            assert integ["creator_request_id"] and integ["is_active"] is False
            activation_url = (
                f"/api/v1/external-presence/integrations/{integ['id']}/activate"
            )
            assert (
                await client.patch(activation_url, headers=admin_headers)
            ).status_code == 403

            challenge = await CreatorApprovalService(db).challenge_for_signer(
                integ["creator_request_id"]
            )
            await CreatorApprovalService(db).decide(
                integ["creator_request_id"],
                decision="approved",
                signature=sign(challenge["challenge_hash"]),
                signer_id=settings.creator_signer_id,
            )
            assert (
                await client.patch(activation_url, headers=admin_headers)
            ).status_code == 200

            # Visitor data rights + encryption at rest (OD-05/07/09).
            from app.models.globalaccess import VisitorMessage

            created_visitor = await client.post(
                "/api/v1/access/visitors", json={"visitor_token": "integration-visitor"}
            )
            assert created_visitor.status_code == 200, created_visitor.text
            # The service issues an unpredictable token; use the one it returned.
            visitor_token = created_visitor.json()["visitor_token"]
            session = await client.post(
                "/api/v1/access/sessions",
                json={"visitor_token": visitor_token, "mode": "focus"},
            )
            assert session.status_code == 200, session.text
            session_token = session.json()["session_token"]
            await client.post(
                "/api/v1/access/messages",
                json={
                    "session_token": session_token,
                    "role": "user",
                    "content": "private integration note",
                },
            )
            stored = (await db.execute(select(VisitorMessage))).scalars().first()
            assert stored is not None and stored.content.startswith("enc:v1:")
            inspected = await client.get(
                f"/api/v1/access/visitors/{visitor_token}/data"
            )
            assert inspected.status_code == 200, inspected.text
            assert any(
                m["content"] == "private integration note"
                for m in inspected.json()["messages"]
            )
            corrected = await client.patch(
                f"/api/v1/access/visitors/{visitor_token}/data",
                json={
                    "preferences": {"theme": "dark"},
                    "memory_permissions": {"allow_shared_knowledge": False},
                },
            )
            assert corrected.status_code == 200, corrected.text
            assert (
                await client.delete(f"/api/v1/access/visitors/{visitor_token}")
            ).status_code == 200
        print("  PASS auth + approval + visitor data rights + encryption at rest")

        # Redis limiter is optional; exercised when REDIS_URL is provided.
        redis_url = os.environ.get("REDIS_URL")
        if redis_url:
            from app.core.rate_limit import RedisRateLimiter

            limiter = RedisRateLimiter(redis_url, default_limit=2)
            key = f"integration:{os.getpid()}"
            assert (await limiter.check(key))[0]
            assert (await limiter.check(key))[0]
            allowed, retry = await limiter.check(key)
            assert not allowed and retry >= 1
            print("  PASS redis rate limiter")


async def main() -> None:
    print("Applying migrations to throwaway database ...")
    await apply_migrations()
    print("Running service checks ...")
    await run_checks()
    print("ALL DATABASE INTEGRATION CHECKS PASSED")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as exc:
        print(f"FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise
