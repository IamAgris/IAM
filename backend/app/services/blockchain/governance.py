"""Creator approval and permission gating for Web3 operations (proposed Doc 33 §6).

This module does not create a second approval engine. It delegates every decision
to the existing ``CreatorApprovalService`` (ED25519 signature over a one-time
challenge) and the OD-04 spend path in ``financial_policy.authorize_transaction``.
No method here can approve its own request.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.services.blockchain.providers.base import ProviderDenied, require_flag
from app.services.creatorapproval_service import CreatorApprovalService
from app.services.financial_policy import SpendDenied, authorize_transaction

# Levels map to the existing LEVEL_ORDER (1..4). There is no level 5.
ACTION_LEVELS: Dict[str, str] = {
    "web3.transaction.prepare": "1",
    "web3.x402.purchase": "3",
    "web3.defi.swap": "3",
    "web3.defi.stake": "3",
    "web3.nft.mint": "3",
    "web3.nft.list": "3",
    "web3.bridge.execute": "3",
    "web3.dao.vote": "3",
    "web3.contract.deploy_testnet": "2",
    "web3.invoice.create": "2",
    "web3.transaction.broadcast": "3",
    "web3.payment.pay_invoice": "3",
    "web3.swap.execute": "3",
    "web3.wallet.key_rotate": "4",
    "web3.treasury.withdraw": "4",
    "web3.contract.deploy_production": "4",
    "web3.governance.change": "4",
}

# Actions that move value: OD-04 caps apply in addition to signed authority.
SPEND_ACTIONS = frozenset(
    {
        "web3.transaction.broadcast",
        "web3.payment.pay_invoice",
        "web3.swap.execute",
        "web3.defi.swap",
        "web3.defi.stake",
        "web3.x402.purchase",
        "web3.nft.mint",
        "web3.nft.list",
        "web3.bridge.execute",
        "web3.treasury.withdraw",
    }
)

PROTECTED_ACTIONS = frozenset(
    {
        "web3.wallet.key_rotate",
        "web3.treasury.withdraw",
        "web3.contract.deploy_production",
        "web3.governance.change",
    }
)

ACTION_CONSEQUENCES: Dict[str, tuple] = {
    "web3.transaction.broadcast": (
        "Broadcasts a prepared on-chain transaction; fees and the transferred value are irreversible.",
    ),
    "web3.payment.pay_invoice": (
        "Pays a Lightning invoice from the configured node; the payment is final in most cases.",
    ),
    "web3.wallet.key_rotate": (
        "Changes protected signing authority for a wallet; existing authorizations may need renewal.",
    ),
    "web3.treasury.withdraw": (
        "Moves protected treasury funds out of the treasury domain.",
    ),
}


@dataclass(frozen=True)
class ExecutionAuthorization:
    """Proof issued only after the existing signed-approval checks pass."""

    action: str
    approval_id: str
    authorization_id: str
    level: str
    amount_usd: Optional[float]
    expires_at: Optional[str]
    signer_id: Optional[str] = None
    verified: bool = True

    def summary(self) -> Dict[str, Any]:
        """Safe to log or send to an external signer; contains no secret material."""
        return {
            "action": self.action,
            "approval_id": self.approval_id,
            "authorization_id": self.authorization_id,
            "level": self.level,
            "amount_usd": self.amount_usd,
            "expires_at": self.expires_at,
            "verified": self.verified,
        }


class Web3ApprovalService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def policy(self) -> Dict[str, Any]:
        return {
            "engine": "existing CreatorApprovalService",
            "levels": sorted(set(ACTION_LEVELS.values())),
            "level_5": False,
            "zero_standing_budget": True,
            "actions": sorted(ACTION_LEVELS),
            "spend_actions": sorted(SPEND_ACTIONS),
            "protected_actions": sorted(PROTECTED_ACTIONS),
            "iam_can_self_approve": False,
        }

    async def create_request(
        self,
        *,
        action: str,
        target_ref: str,
        summary: str,
        reason: Optional[str] = None,
        channel: str = "creator_cli",
        requester: str = "iam",
    ) -> Dict[str, Any]:
        """Create a PENDING Creator request. This grants no authority."""
        if action not in ACTION_LEVELS:
            raise ProviderDenied(f"unknown Web3 action '{action}'")
        if not target_ref:
            raise ProviderDenied("target_ref is required")
        return await CreatorApprovalService(self.db).create_request(
            action_type=action,
            target_ref=target_ref,
            risk_level=ACTION_LEVELS[action],
            summary=summary,
            consequences=list(ACTION_CONSEQUENCES.get(action, ())),
            reason=reason,
            requester=requester,
            channel=channel,
        )

    async def authorize(
        self,
        *,
        action: str,
        approval_id: str,
        amount_usd: Optional[float] = None,
        target_ref: Optional[str] = None,
    ) -> ExecutionAuthorization:
        """Verify signed authority at the moment of execution. Fail closed."""
        if action not in ACTION_LEVELS:
            raise ProviderDenied(f"unknown Web3 action '{action}'")
        if not approval_id:
            raise ProviderDenied("a signed Creator approval_id is required")

        level = ACTION_LEVELS[action]
        authority = await CreatorApprovalService(self.db).check_authorization(
            action, requested_level=level, target_ref=str(approval_id)
        )
        if not authority.get("authorized"):
            raise ProviderDenied(
                "no active signed Creator authorization covers this action and approval_id"
            )

        if action in SPEND_ACTIONS:
            if amount_usd is None:
                raise ProviderDenied(
                    "a USD valuation is required for signed spend (OD-04 caps)"
                )
            try:
                value = float(amount_usd)
            except (TypeError, ValueError) as exc:
                raise ProviderDenied("amount_usd must be numeric") from exc
            if value <= 0:
                raise ProviderDenied("amount_usd must be positive")
            try:
                await authorize_transaction(
                    self.db,
                    amount=value,
                    transaction_type="transfer",
                    approval_id=str(approval_id),
                )
            except SpendDenied as exc:
                raise ProviderDenied(f"OD-04 spend policy denied the action: {exc}") from exc

        return ExecutionAuthorization(
            action=action,
            approval_id=str(approval_id),
            authorization_id=str(authority["authorization_id"]),
            level=level,
            amount_usd=amount_usd,
            expires_at=authority.get("expires_at"),
            signer_id=authority.get("signer_id"),
        )

    @staticmethod
    def require_authorization(
        authorization: Optional[ExecutionAuthorization], action: str
    ) -> None:
        if not isinstance(authorization, ExecutionAuthorization):
            raise ProviderDenied("a verified ExecutionAuthorization is required")
        if not authorization.verified or authorization.action != action:
            raise ProviderDenied("authorization is invalid or for a different action")

    @staticmethod
    def require_protected(authorization: ExecutionAuthorization) -> None:
        require_flag(
            authorization.level == "4",
            "protected operation requires level 4 signed Creator authority",
        )
