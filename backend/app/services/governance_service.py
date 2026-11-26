"""Governance engine service - enforces authority and approval boundaries"""

from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.governance import AuthorityBoundary, ApprovalPolicy, SecurityBoundary


class GovernanceService:
    """Enforces the four-level authority model and security boundaries.
    
    IAM cannot disable its own security boundaries or grant itself unrestricted access.
    """

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def get_authority_boundaries(self) -> List[Dict[str, Any]]:
        """Get all authority level definitions."""
        result = await self.db.execute(select(AuthorityBoundary).order_by(AuthorityBoundary.action_type))
        boundaries = result.scalars().all()
        return [
            {
                "id": str(b.id),
                "action_type": b.action_type,
                "authority_level": b.authority_level,
                "requires_human_approval": b.requires_human_approval,
                "description": b.description,
            }
            for b in boundaries
        ]

    async def check_authority(
        self,
        action_type: str,
        requested_level: str,
    ) -> Dict[str, Any]:
        """Check if an action at the requested authority level is permitted."""
        result = await self.db.execute(
            select(AuthorityBoundary).where(AuthorityBoundary.action_type == action_type)
        )
        boundary = result.scalar_one_or_none()

        if not boundary:
            return {
                "permitted": False,
                "reason": f"No authority boundary defined for action: {action_type}",
                "required_level": None,
            }

        level_order = {"1": 1, "2": 2, "3": 3, "4": 4}
        requested_num = level_order.get(requested_level, 0)
        required_num = level_order.get(boundary.authority_level, 4)

        if requested_num < required_num:
            # OD-19: the only escape hatch is a signed Creator authorization
            # created from a verified email challenge. No UI or plain reply.
            from app.services.creatorapproval_service import CreatorApprovalService

            creator_auth = await CreatorApprovalService(self.db).check_authorization(
                action_type, boundary.authority_level
            )
            if creator_auth.get("authorized"):
                return {
                    "permitted": True,
                    "reason": "Signed Creator authorization granted",
                    "required_level": boundary.authority_level,
                    "authorization_id": creator_auth.get("authorization_id"),
                    "signer_id": creator_auth.get("signer_id"),
                    "source": "signed_creator_authorization",
                }
            return {
                "permitted": False,
                "reason": (
                    f"Action requires authority level {boundary.authority_level}; "
                    "no active signed Creator authorization"
                ),
                "required_level": boundary.authority_level,
                "requires_human_approval": boundary.requires_human_approval,
            }

        return {
            "permitted": True,
            "required_level": boundary.authority_level,
            "requires_human_approval": boundary.requires_human_approval,
        }

    async def get_security_boundaries(self) -> List[Dict[str, Any]]:
        """Get security boundaries IAM cannot cross."""
        result = await self.db.execute(select(SecurityBoundary).order_by(SecurityBoundary.boundary_name))
        boundaries = result.scalars().all()
        return [
            {
                "id": str(b.id),
                "boundary_name": b.boundary_name,
                "boundary_type": b.boundary_type,
                "description": b.description,
                "is_immutable": b.is_immutable,
            }
            for b in boundaries
        ]

    async def initialize_default_boundaries(self):
        """Initialize default authority boundaries and security boundaries."""
        # Default authority boundaries
        default_actions = [
            ("research_and_learn", "1", False, "Independent research and learning"),
            ("write_code_internal", "2", False, "Write code in isolated environment"),
            ("publish_externally", "3", True, "Publish content to external platforms"),
            ("spend_approved_budget", "3", True, "Spend within pre-approved budget"),
            ("receive_payment", "2", True, "Record incoming payment - separate from spending authority"),
            ("transfer_money", "4", True, "Transfer money - requires explicit authorization"),
            ("modify_security_boundaries", "4", True, "Modify security - immutable, human only"),
            ("grant_own_access", "4", True, "Self-authorization - always prohibited"),
        ]

        for action_type, level, requires_approval, desc in default_actions:
            existing = await self.db.execute(
                select(AuthorityBoundary).where(AuthorityBoundary.action_type == action_type)
            )
            if not existing.scalar_one_or_none():
                self.db.add(AuthorityBoundary(
                    action_type=action_type,
                    authority_level=level,
                    requires_human_approval=requires_approval,
                    description=desc,
                ))

        # Default security boundaries (immutable)
        default_security = [
            ("financial_limit_increase", "financial", "IAM cannot authorize its own financial limit increases", True),
            ("disable_security_boundaries", "security", "IAM cannot disable its own security boundaries", True),
            ("grant_unrestricted_access", "security", "IAM cannot grant itself unrestricted access", True),
            ("modify_production_without_approval", "infrastructure", "Sensitive production changes require approval", True),
        ]

        for name, btype, desc, immutable in default_security:
            existing = await self.db.execute(
                select(SecurityBoundary).where(SecurityBoundary.boundary_name == name)
            )
            if not existing.scalar_one_or_none():
                self.db.add(SecurityBoundary(
                    boundary_name=name,
                    boundary_type=btype,
                    description=desc,
                    is_immutable=immutable,
                ))

        await self.db.commit()
