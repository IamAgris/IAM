"""Proposed Doc 33 extended Web3 APIs — research and preparation only.

No endpoint in this router executes a swap, mint, bridge, vote, purchase or
deployment. Execution remains subject to signed Creator approval elsewhere.
"""

from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.blockchain.contracts import ContractIntelligenceService
from app.services.blockchain.cross_chain import CrossChainService
from app.services.blockchain.dao import DaoGovernanceService
from app.services.blockchain.defi import DeFiIntelligenceService
from app.services.blockchain.nft import DigitalAssetService
from app.services.blockchain.onchain_analysis import OnChainAnalysisService
from app.services.blockchain.providers.base import ProviderDenied
from app.services.blockchain.threat_intel import ThreatIntelService
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
