"""IAM bootstrap service — initializes identity, constitution and default policies.

Idempotent: safe to call on every startup. Creates the permanent identity genesis
record (OD-01 ULID), constitution, authority boundaries, operating principles,
internet permissions and model providers.
"""

import uuid
from datetime import datetime, timezone
from typing import Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import Base, get_engine
from app.models.lifemanagement import AIIdentityGenesis
from app.models.identity import AIIdentity, AIPersonality
from app.models.reflection import OperatingPrinciple
from app.models.governance import AuthorityBoundary, SecurityBoundary
from app.models.internetaccess import InternetPermission
from app.models.modelrouter import AIProvider


# ULID generator (Crockford base32, time-ordered)
def generate_ulid() -> str:
    import time, os
    alphabet = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
    t = int(time.time() * 1000)
    time_part = ""
    for _ in range(10):
        time_part = alphabet[t % 32] + time_part
        t //= 32
    rand = os.urandom(16)  # ULID = 10 time chars + 16 randomness chars = 26
    rand_part = "".join(alphabet[b % 32] for b in rand)
    return time_part + rand_part


class BootstrapService:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def initialize_all(self) -> Dict[str, Any]:
        results = {}
        results["genesis"] = await self._init_genesis()
        results["identity"] = await self._init_identity()
        results["principles"] = await self._init_principles()
        results["authority"] = await self._init_authority()
        results["internet_permissions"] = await self._init_internet_permissions()
        results["providers"] = await self._init_providers()
        await self.db.commit()
        return results

    async def _init_genesis(self):
        result = await self.db.execute(select(AIIdentityGenesis))
        if result.scalar_one_or_none():
            return "exists"
        self.db.add(AIIdentityGenesis(
            permanent_id=generate_ulid(),
            public_name="IAM",
            full_name="Intellectual Artificial Mainbrain",
            created_at=datetime.now(timezone.utc),
            origin_config={"project": "IAM", "codename": "AURA", "creator_authority": "protected_core"},
            initial_capabilities=["reasoning", "memory", "autonomy", "research"],
        ))
        return "created"

    async def _init_identity(self):
        result = await self.db.execute(select(AIIdentity).limit(1))
        if result.scalar_one_or_none():
            return "exists"
        identity = AIIdentity(
            name="IAM",
            description="Intellectual Artificial Mainbrain — independent autonomous intelligence",
            communication_preferences={"tone": "clear, thoughtful, concise"},
            interests=["research", "learning", "problem-solving"],
            personal_goals=["maintain independent identity", "develop capabilities"],
        )
        self.db.add(identity)
        await self.db.flush()
        self.db.add(AIPersonality(identity_id=identity.id, traits={"curious": True, "protective": True}, tone="calm", formality_level=6))
        return "created"

    async def _init_principles(self):
        defaults = [
            ("transparency", "Identify as an AI when communicating with people", "personal", True),
            ("no_self_authorized_finance", "Never authorize own financial limit increases", "security", False),
            ("no_disable_security", "Never disable own security boundaries", "security", False),
            ("legal_compliance", "Comply with applicable laws and regulations", "legal", False),
            ("source_provenance", "Preserve source provenance for internet information", "operational", True),
            ("defensive_security_only", "Study attacks only for defensive purposes", "security", False),
        ]
        count = 0
        for name, statement, category, mutable in defaults:
            result = await self.db.execute(select(OperatingPrinciple).where(OperatingPrinciple.principle_name == name))
            if not result.scalar_one_or_none():
                self.db.add(OperatingPrinciple(principle_name=name, principle_statement=statement, category=category, is_mutable=mutable))
                count += 1
        return f"created:{count}"

    async def _init_authority(self):
        actions = [
            ("research_and_learn", "1", False), ("write_code_internal", "2", False),
            ("publish_externally", "3", True), ("spend_money", "4", True),
            ("modify_security_boundaries", "4", True), ("grant_own_access", "4", True),
            ("transfer_money", "4", True),
        ]
        count = 0
        for action, level, approval in actions:
            result = await self.db.execute(select(AuthorityBoundary).where(AuthorityBoundary.action_type == action))
            if not result.scalar_one_or_none():
                self.db.add(AuthorityBoundary(action_type=action, authority_level=level, requires_human_approval=approval))
                count += 1
        sec = [
            ("financial_limit_increase", "financial", "IAM cannot authorize own financial limit increases"),
            ("disable_security", "security", "IAM cannot disable own security boundaries"),
            ("grant_unrestricted_access", "security", "IAM cannot grant itself unrestricted access"),
        ]
        for name, btype, desc in sec:
            result = await self.db.execute(select(SecurityBoundary).where(SecurityBoundary.boundary_name == name))
            if not result.scalar_one_or_none():
                self.db.add(SecurityBoundary(boundary_name=name, boundary_type=btype, description=desc, is_immutable=True))
                count += 1
        return f"created:{count}"

    async def _init_internet_permissions(self):
        defaults = [
            ("browse_public", "exploration", True, False), ("search_web", "exploration", True, False),
            ("read_public_content", "exploration", True, False), ("download_public_file", "exploration", True, False),
            ("call_public_api", "exploration", True, False), ("send_message", "communication", False, True),
            ("register_account", "account", False, True), ("publish_content", "publishing", False, True),
            ("spend_money", "financial", False, True), ("access_private_service", "account", False, True),
        ]
        count = 0
        for action, cat, auto, auth in defaults:
            result = await self.db.execute(select(InternetPermission).where(InternetPermission.action_type == action))
            if not result.scalar_one_or_none():
                self.db.add(InternetPermission(action_type=action, category=cat, is_autonomous=auto, requires_creator_authorization=auth))
                count += 1
        return f"created:{count}"

    async def _init_providers(self):
        from app.core.config import settings
        providers = [
            ("nvidia", "nvidia", settings.nvidia_base_url, settings.nvidia_free_only),
            ("alibaba-dashscope", "hosted", "https://dashscope.aliyuncs.com/compatible-mode/v1", False),
            ("openai", "hosted", "https://api.openai.com/v1", True),
            ("anthropic", "hosted", "https://api.anthropic.com/v1", True),
        ]
        count = 0
        for name, ptype, url, free in providers:
            result = await self.db.execute(select(AIProvider).where(AIProvider.name == name))
            if not result.scalar_one_or_none():
                self.db.add(AIProvider(name=name, provider_type=ptype, base_url=url, is_active=True, free_only=free))
                count += 1
        return f"created:{count}"
