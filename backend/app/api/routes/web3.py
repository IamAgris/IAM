"""Proposed Doc 30 APIs — read-only Web3/node intelligence and prepare-only transactions.

There is no endpoint for broadcast, payment, swap, bridge, invoice payment or channel
change. Those require signed Creator approval and are a separate later work item.
All prefixes are admin-scoped in ``app.core.auth_policy`` and all features are
default-off through configuration flags.

Route handlers are intentionally untyped pending the full response-model pass;
their contracts are verified by the OpenAPI drift gate.
"""
# mypy: disable-error-code=no-untyped-def

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.services.blockchain.activation import check_web3_activation
from app.services.blockchain.audit import BlockchainAuditService
from app.services.blockchain.governance import Web3ApprovalService
from app.services.blockchain.monitoring import Web3MonitoringService
from app.services.blockchain.network_registry import NetworkRegistry
from app.services.blockchain.node_service import NodeService
from app.services.blockchain.providers.base import ProviderDenied
from app.services.blockchain.providers.cln_adapter import ClnAdapter
from app.services.blockchain.providers.lnd_adapter import LndAdapter
from app.services.blockchain.providers.thirdweb_adapter import ThirdwebReadAdapter
from app.services.blockchain.reconciliation import ReconciliationService
from app.services.blockchain.transaction_manager import TransactionManager
from app.services.blockchain.wallet_registry import WalletRegistry

web3_router = APIRouter(prefix="/api/v1/web3", tags=["web3"])
nodes_router = APIRouter(prefix="/api/v1/nodes", tags=["nodes"])


class WalletCreate(BaseModel):
    domain: str
    provider: str
    address: str
    network_id: Optional[str] = None
    verification_method: Optional[str] = None
    verification_evidence_ref: Optional[str] = None
    policy_ref: Optional[str] = None


class WalletTransition(BaseModel):
    target: str
    verification_method: Optional[str] = None
    verification_evidence_ref: Optional[str] = None


class ApprovalConfirm(BaseModel):
    approval_id: str
    amount_usd: float


class BroadcastRequest(BaseModel):
    amount_usd: float


class InvoiceCreate(BaseModel):
    amount_sats: Optional[int] = None
    amount_msat: Optional[int] = None
    memo: Optional[str] = None
    label: Optional[str] = None
    approval_id: str


class PayInvoice(BaseModel):
    payment_request: Optional[str] = None
    bolt11: Optional[str] = None
    approval_id: str
    amount_usd: float


class TransactionPrepare(BaseModel):
    chain_id: str
    to_address: str
    amount: float
    from_address: Optional[str] = None
    token: Optional[str] = None
    tx_type: str = "transfer"
    wallet_id: Optional[str] = None
    nonce: Optional[str] = None
    approval_id: Optional[str] = None
    gas_estimate: Optional[float] = None


def _actor(request: Request) -> str:
    credential = getattr(request.state, "credential", None)
    return credential.get("name", "iam") if credential else "iam"


def _denied(exc: ProviderDenied) -> HTTPException:
    return HTTPException(403, str(exc))


# --- Web3 ---------------------------------------------------------------------

@web3_router.get("/policy")
async def web3_policy(db: AsyncSession = Depends(get_db_session)):
    return {
        "wallets": WalletRegistry(db).policy(),
        "transactions": TransactionManager(db).policy(),
        "thirdweb": ThirdwebReadAdapter().policy(),
        "execution_enabled": False,
        "creator_approval_integration": "deferred",
    }


@web3_router.get("/networks")
async def web3_networks(testnet_only: bool = False):
    return {"networks": NetworkRegistry().list_networks(testnet_only=testnet_only)}


@web3_router.get("/audit/verify")
async def web3_audit_verify(db: AsyncSession = Depends(get_db_session)):
    return await BlockchainAuditService(db).verify()


@web3_router.get("/reconcile")
async def web3_reconcile(db: AsyncSession = Depends(get_db_session)):
    try:
        return await ReconciliationService(db).reconcile()
    except ProviderDenied as exc:
        raise _denied(exc) from exc


@web3_router.get("/wallets")
async def web3_wallets(domain: Optional[str] = None, db: AsyncSession = Depends(get_db_session)):
    return {"wallets": await WalletRegistry(db).list_wallets(domain)}


@web3_router.post("/wallets")
async def web3_register_wallet(
    payload: WalletCreate, request: Request, db: AsyncSession = Depends(get_db_session)
):
    try:
        return await WalletRegistry(db).register(
            domain=payload.domain,
            provider=payload.provider,
            address=payload.address,
            network_id=payload.network_id,
            verification_method=payload.verification_method,
            verification_evidence_ref=payload.verification_evidence_ref,
            policy_ref=payload.policy_ref,
            actor=_actor(request),
        )
    except ProviderDenied as exc:
        raise _denied(exc) from exc


@web3_router.post("/wallets/{wallet_id}/transition")
async def web3_wallet_transition(
    wallet_id: str,
    payload: WalletTransition,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        return await WalletRegistry(db).transition(
            wallet_id=wallet_id,
            target=payload.target,
            actor=_actor(request),
            verification_method=payload.verification_method,
            verification_evidence_ref=payload.verification_evidence_ref,
        )
    except ProviderDenied as exc:
        raise _denied(exc) from exc
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc


@web3_router.get("/transactions")
async def web3_transactions(
    status: Optional[str] = None, db: AsyncSession = Depends(get_db_session)
):
    return {"transactions": await TransactionManager(db).list_transactions(status)}


@web3_router.post("/transactions/prepare")
async def web3_prepare_transaction(
    payload: TransactionPrepare, request: Request, db: AsyncSession = Depends(get_db_session)
):
    try:
        return await TransactionManager(db).prepare(payload.model_dump(), _actor(request))
    except ProviderDenied as exc:
        raise _denied(exc) from exc


@web3_router.get("/governance/policy")
async def web3_governance_policy(db: AsyncSession = Depends(get_db_session)):
    return Web3ApprovalService(db).policy()


@web3_router.get("/activation")
async def web3_activation():
    return check_web3_activation()


@web3_router.post("/monitoring/run")
async def web3_monitoring_run(db: AsyncSession = Depends(get_db_session)):
    try:
        return await Web3MonitoringService(db).run_checks()
    except ProviderDenied as exc:
        raise _denied(exc) from exc


@web3_router.post("/transactions/{transaction_id}/approval-request")
async def web3_request_approval(
    transaction_id: str, request: Request, db: AsyncSession = Depends(get_db_session)
):
    try:
        return await TransactionManager(db).request_approval(transaction_id, actor=_actor(request))
    except ProviderDenied as exc:
        raise _denied(exc) from exc
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc


@web3_router.post("/transactions/{transaction_id}/approve")
async def web3_confirm_approval(
    transaction_id: str,
    payload: ApprovalConfirm,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        return await TransactionManager(db).confirm_approval(
            transaction_id, payload.approval_id, payload.amount_usd
        )
    except ProviderDenied as exc:
        raise _denied(exc) from exc
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc


@web3_router.post("/transactions/{transaction_id}/broadcast")
async def web3_broadcast(
    transaction_id: str,
    payload: BroadcastRequest,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        return await TransactionManager(db).broadcast(transaction_id, payload.amount_usd)
    except ProviderDenied as exc:
        raise _denied(exc) from exc
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc


# --- Nodes --------------------------------------------------------------------

@nodes_router.get("/policy")
async def nodes_policy():
    return NodeService().policy()


@nodes_router.get("/bitcoin")
async def nodes_bitcoin():
    return await NodeService().bitcoin_report()


@nodes_router.get("/lightning")
async def nodes_lightning():
    return await NodeService().lightning_report()


@nodes_router.get("/compare")
async def nodes_compare():
    return await NodeService().compare()


@nodes_router.get("/health")
async def nodes_health():
    return await NodeService().health()


@nodes_router.post("/lnd/invoices")
async def lnd_create_invoice(
    payload: InvoiceCreate, db: AsyncSession = Depends(get_db_session)
):
    try:
        authorization = await Web3ApprovalService(db).authorize(
            action="web3.invoice.create", approval_id=payload.approval_id,
            target_ref="lnd",
        )
        result = await LndAdapter().create_invoice(payload.model_dump(), authorization)
        return result.as_dict()
    except ProviderDenied as exc:
        raise _denied(exc) from exc


@nodes_router.post("/lnd/payments")
async def lnd_pay_invoice(payload: PayInvoice, db: AsyncSession = Depends(get_db_session)):
    try:
        authorization = await Web3ApprovalService(db).authorize(
            action="web3.payment.pay_invoice", approval_id=payload.approval_id,
            amount_usd=payload.amount_usd, target_ref="lnd",
        )
        result = await LndAdapter().pay_invoice(payload.model_dump(), authorization)
        return result.as_dict()
    except ProviderDenied as exc:
        raise _denied(exc) from exc


@nodes_router.post("/cln/invoices")
async def cln_create_invoice(
    payload: InvoiceCreate, db: AsyncSession = Depends(get_db_session)
) -> Any:
    try:
        authorization = await Web3ApprovalService(db).authorize(
            action="web3.invoice.create", approval_id=payload.approval_id,
            target_ref="cln",
        )
        result = await ClnAdapter().create_invoice(payload.model_dump(), authorization)
        return result.as_dict()
    except ProviderDenied as exc:
        raise _denied(exc) from exc


@nodes_router.post("/cln/payments")
async def cln_pay_invoice(
    payload: PayInvoice, db: AsyncSession = Depends(get_db_session)
) -> Any:
    try:
        authorization = await Web3ApprovalService(db).authorize(
            action="web3.payment.pay_invoice", approval_id=payload.approval_id,
            amount_usd=payload.amount_usd, target_ref="cln",
        )
        result = await ClnAdapter().pay_invoice(payload.model_dump(), authorization)
        return result.as_dict()
    except ProviderDenied as exc:
        raise _denied(exc) from exc
