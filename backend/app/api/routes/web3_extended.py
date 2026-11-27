"""Proposed Doc 33 extended Web3 APIs — research and preparation only.

No endpoint in this router executes a swap, mint, bridge, vote, purchase or
deployment. Execution remains subject to signed Creator approval elsewhere.
"""

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.services.blockchain.accounting import Web3AccountingService
from app.services.blockchain.business import Web3BusinessService
from app.services.blockchain.contracts import ContractIntelligenceService
from app.services.blockchain.cross_chain import CrossChainService
from app.services.blockchain.dao import DaoGovernanceService
from app.services.blockchain.defi import DeFiIntelligenceService
from app.services.blockchain.emergency import Web3EmergencyService
from app.services.blockchain.fiat import FiatRampResearch
from app.services.blockchain.nft import DigitalAssetService
from app.services.blockchain.non_evm import NonEvmRegistry
from app.services.blockchain.registries import (
    ContractRegistryService,
    ProviderHealthRegistry,
    TokenRegistryService,
)
from app.services.blockchain.onchain_analysis import OnChainAnalysisService
from app.services.blockchain.providers.base import ProviderDenied
from app.services.blockchain.threat_intel import ThreatIntelService
from app.services.blockchain.transaction_ops import (
    GasManager,
    NonceManager,
    StuckTransactionRecovery,
    TransactionQueue,
    TransactionSimulator,
)
from app.services.blockchain.wallet_ecosystem import WalletEcosystemService
from app.services.blockchain.web3_learning import Web3LearningService
from app.services.blockchain.x402 import X402Service

router = APIRouter(prefix="/api/v1/web3-extended", tags=["web3-extended"])


class Payload(BaseModel):
    data: Dict[str, Any] = {}


class Signals(BaseModel):
    target: str
    signals: List[Dict[str, Any]] = []


class Quotes(BaseModel):
    quotes: List[Dict[str, Any]] = []


class TemplateRequest(BaseModel):
    standard: str


def _denied(exc: ProviderDenied) -> HTTPException:
    return HTTPException(403, str(exc))


# --- DeFi ---------------------------------------------------------------------

@router.get("/defi/policy")
async def defi_policy():
    return DeFiIntelligenceService().policy()


@router.post("/defi/swaps/compare")
async def defi_compare(payload: Quotes):
    try:
        return DeFiIntelligenceService().compare_swaps(payload.quotes)
    except ProviderDenied as exc:
        raise _denied(exc) from exc


@router.post("/defi/prepare")
async def defi_prepare(payload: Payload):
    try:
        return DeFiIntelligenceService().prepare_action(
            str(payload.data.get("action", "")), payload.data
        )
    except ProviderDenied as exc:
        raise _denied(exc) from exc


@router.get("/defi/impermanent-loss")
async def defi_impermanent_loss(ratio: float):
    try:
        return DeFiIntelligenceService.impermanent_loss(ratio)
    except ProviderDenied as exc:
        raise _denied(exc) from exc


@router.post("/defi/liquidation")
async def defi_liquidation(payload: Payload):
    try:
        return DeFiIntelligenceService.liquidation_risk(**payload.data)
    except (ProviderDenied, TypeError) as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/defi/staking")
async def defi_staking(payload: Payload):
    try:
        return DeFiIntelligenceService.staking_estimate(**payload.data)
    except (ProviderDenied, TypeError) as exc:
        raise HTTPException(400, str(exc)) from exc


# --- x402 ---------------------------------------------------------------------

@router.get("/x402/policy")
async def x402_policy():
    return X402Service().policy()


@router.post("/x402/discover")
async def x402_discover(payload: Payload):
    try:
        return await X402Service().discover(str(payload.data.get("service_url", "")))
    except ProviderDenied as exc:
        raise _denied(exc) from exc


@router.post("/x402/evaluate")
async def x402_evaluate(payload: Payload):
    try:
        return X402Service().evaluate(**payload.data)
    except (ProviderDenied, TypeError) as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/x402/prepare")
async def x402_prepare(payload: Payload):
    try:
        return X402Service().prepare_purchase(**payload.data)
    except (ProviderDenied, TypeError) as exc:
        raise HTTPException(400, str(exc)) from exc


# --- Contracts ----------------------------------------------------------------

@router.get("/contracts/policy")
async def contracts_policy():
    return ContractIntelligenceService().policy()


@router.post("/contracts/analyze")
async def contracts_analyze(payload: Payload):
    try:
        return ContractIntelligenceService().analyze(**payload.data)
    except (ProviderDenied, TypeError) as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/contracts/template")
async def contracts_template(payload: TemplateRequest):
    try:
        return {"source": ContractIntelligenceService.template(payload.standard)}
    except ProviderDenied as exc:
        raise _denied(exc) from exc


@router.post("/contracts/deploy/prepare")
async def contracts_prepare_deploy(payload: Payload):
    try:
        return ContractIntelligenceService().prepare_deployment(**payload.data)
    except (ProviderDenied, TypeError) as exc:
        raise HTTPException(400, str(exc)) from exc


# --- NFTs ---------------------------------------------------------------------

@router.get("/nft/policy")
async def nft_policy():
    return DigitalAssetService().policy()


@router.post("/nft/mint/prepare")
async def nft_prepare_mint(payload: Payload):
    try:
        return DigitalAssetService().prepare_mint(**payload.data)
    except (ProviderDenied, TypeError) as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/nft/list/prepare")
async def nft_prepare_list(payload: Payload):
    try:
        return DigitalAssetService().prepare_listing(**payload.data)
    except (ProviderDenied, TypeError) as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/nft/ownership")
async def nft_ownership(payload: Payload):
    try:
        return DigitalAssetService().verify_ownership(**payload.data)
    except (ProviderDenied, TypeError) as exc:
        raise HTTPException(400, str(exc)) from exc


# --- DAO ----------------------------------------------------------------------

@router.get("/dao/policy")
async def dao_policy():
    return DaoGovernanceService().policy()


@router.post("/dao/analyze")
async def dao_analyze(payload: Payload):
    try:
        return DaoGovernanceService().analyze_proposal(**payload.data)
    except (ProviderDenied, TypeError) as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/dao/recommendation")
async def dao_recommendation(payload: Payload):
    try:
        return DaoGovernanceService().recommendation(payload.data)
    except (ProviderDenied, TypeError) as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/dao/vote/prepare")
async def dao_prepare_vote(payload: Payload):
    try:
        return DaoGovernanceService().prepare_vote(**payload.data)
    except (ProviderDenied, TypeError) as exc:
        raise HTTPException(400, str(exc)) from exc


# --- Cross-chain --------------------------------------------------------------

@router.get("/cross-chain/policy")
async def cross_chain_policy():
    return CrossChainService().policy()


@router.post("/cross-chain/routes/compare")
async def cross_chain_compare(payload: Quotes):
    try:
        return CrossChainService().compare_routes(payload.quotes)
    except ProviderDenied as exc:
        raise _denied(exc) from exc


@router.post("/cross-chain/prepare")
async def cross_chain_prepare(payload: Payload):
    try:
        return CrossChainService().prepare_bridge(**payload.data)
    except (ProviderDenied, TypeError) as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/cross-chain/settlement")
async def cross_chain_settlement(payload: Payload):
    try:
        return CrossChainService().settlement_check(**payload.data)
    except (ProviderDenied, TypeError) as exc:
        raise HTTPException(400, str(exc)) from exc


# --- Threat and on-chain analysis ---------------------------------------------

@router.get("/threat/policy")
async def threat_policy():
    return ThreatIntelService().policy()


@router.post("/threat/assess")
async def threat_assess(payload: Signals):
    try:
        return ThreatIntelService().assess(target=payload.target, signals=payload.signals)
    except ProviderDenied as exc:
        raise _denied(exc) from exc


@router.get("/onchain/policy")
async def onchain_policy():
    return OnChainAnalysisService().policy()


@router.post("/onchain/concentration")
async def onchain_concentration(payload: Payload):
    try:
        return OnChainAnalysisService().holder_concentration(**payload.data)
    except (ProviderDenied, TypeError) as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/onchain/anomalies")
async def onchain_anomalies(payload: Payload):
    try:
        return OnChainAnalysisService().anomaly_scores(**payload.data)
    except (ProviderDenied, TypeError) as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/onchain/fee")
async def onchain_fee(base_fee: float, priority_fee: float):
    try:
        return OnChainAnalysisService.eip1559_fee(base_fee, priority_fee)
    except ProviderDenied as exc:
        raise _denied(exc) from exc


@router.post("/onchain/whales")
async def onchain_whales(payload: Payload):
    try:
        return OnChainAnalysisService().whale_activity(**payload.data)
    except (ProviderDenied, TypeError) as exc:
        raise HTTPException(400, str(exc)) from exc


# --- Wallet ecosystem ---------------------------------------------------------

@router.get("/wallets/policy")
async def wallets_policy():
    return WalletEcosystemService().policy()


@router.post("/wallets/siwe/verify")
async def wallets_siwe_verify(payload: Payload):
    try:
        return WalletEcosystemService().verify_siwe(**payload.data)
    except (ProviderDenied, TypeError) as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/wallets/session-keys/prepare")
async def wallets_session_key(payload: Payload):
    try:
        return WalletEcosystemService().session_key(**payload.data)
    except (ProviderDenied, TypeError) as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/wallets/multisig/prepare")
async def wallets_multisig(payload: Payload):
    try:
        return WalletEcosystemService().multisig(**payload.data)
    except (ProviderDenied, TypeError) as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/wallets/transfers/prepare")
async def wallets_transfer(payload: Payload):
    try:
        return WalletEcosystemService().prepare_transfer(**payload.data)
    except (ProviderDenied, TypeError) as exc:
        raise HTTPException(400, str(exc)) from exc


# --- Transaction operations ---------------------------------------------------

@router.post("/transactions/nonce")
async def transactions_nonce(payload: Payload):
    try:
        return {"nonce": NonceManager().next_nonce(**payload.data)}
    except (ProviderDenied, TypeError) as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/transactions/gas")
async def transactions_gas(payload: Payload):
    try:
        return GasManager.estimate(**payload.data)
    except (ProviderDenied, TypeError) as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/transactions/simulate")
async def transactions_simulate(payload: Payload):
    try:
        return TransactionSimulator().simulate(**payload.data)
    except (ProviderDenied, TypeError) as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/transactions/stuck")
async def transactions_stuck(payload: Payload):
    try:
        return StuckTransactionRecovery.assess(**payload.data)
    except (ProviderDenied, TypeError) as exc:
        raise HTTPException(400, str(exc)) from exc


# --- Registries, emergency, accounting ----------------------------------------

@router.get("/contracts/registry")
async def contracts_registry(
    chain_id: str | None = None, db: AsyncSession = Depends(get_db_session)
):
    try:
        return {"contracts": await ContractRegistryService(db).list(chain_id)}
    except ProviderDenied as exc:
        raise _denied(exc) from exc


@router.get("/tokens/registry")
async def tokens_registry(
    chain_id: str | None = None, db: AsyncSession = Depends(get_db_session)
):
    try:
        return {"tokens": await TokenRegistryService(db).list(chain_id)}
    except ProviderDenied as exc:
        raise _denied(exc) from exc


@router.get("/providers/health")
async def provider_health(db: AsyncSession = Depends(get_db_session)):
    try:
        return {"providers": await ProviderHealthRegistry(db).list()}
    except ProviderDenied as exc:
        raise _denied(exc) from exc


@router.get("/emergency/policy")
async def emergency_policy(db: AsyncSession = Depends(get_db_session)):
    return Web3EmergencyService(db).policy()


@router.post("/emergency/suspend")
async def emergency_suspend(payload: Payload, db: AsyncSession = Depends(get_db_session)):
    try:
        return await Web3EmergencyService(db).suspend(**payload.data)
    except (ProviderDenied, TypeError) as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/accounting/fifo")
async def accounting_fifo(payload: Payload):
    try:
        return Web3AccountingService.fifo_basis(**payload.data)
    except (ProviderDenied, TypeError, ValueError) as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/accounting/unrealised")
async def accounting_unrealised(payload: Payload):
    try:
        return Web3AccountingService.unrealised_pnl(**payload.data)
    except (ProviderDenied, TypeError) as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/accounting/exposure")
async def accounting_exposure(payload: Payload):
    try:
        return Web3AccountingService.portfolio_exposure(payload.data.get("holdings", []))
    except (ProviderDenied, TypeError) as exc:
        raise HTTPException(400, str(exc)) from exc


# --- Learning, business, non-EVM, fiat ----------------------------------------

@router.get("/learning/policy")
async def learning_policy():
    return Web3LearningService().policy()


@router.post("/learning/research")
async def learning_research(payload: Payload):
    try:
        return Web3LearningService().research_record(**payload.data)
    except (ProviderDenied, TypeError) as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/learning/benchmark")
async def learning_benchmark(payload: Payload):
    try:
        return Web3LearningService().benchmark(**payload.data)
    except (ProviderDenied, TypeError) as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/business/evaluate")
async def business_evaluate(payload: Payload):
    try:
        return Web3BusinessService().evaluate(**payload.data)
    except (ProviderDenied, TypeError) as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/networks/non-evm")
async def non_evm_networks(family: str | None = None):
    try:
        return {"networks": NonEvmRegistry().list(family)}
    except ProviderDenied as exc:
        raise _denied(exc) from exc


@router.get("/fiat/candidates")
async def fiat_candidates(route: str | None = None):
    try:
        return {"candidates": FiatRampResearch().candidates(route)}
    except ProviderDenied as exc:
        raise _denied(exc) from exc


@router.post("/fiat/evaluate")
async def fiat_evaluate(payload: Payload):
    try:
        return FiatRampResearch().evaluate(**payload.data)
    except (ProviderDenied, TypeError) as exc:
        raise HTTPException(400, str(exc)) from exc
