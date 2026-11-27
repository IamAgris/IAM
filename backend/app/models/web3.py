"""Proposed Doc 30 / OD-50 — Web3 and self-hosted node records.

Metadata only. No table in this module stores a private key, seed phrase, macaroon,
rune or RPC password. Execution authority is not created here: all transaction
records are prepared/validated/simulated until a signed Creator approval is wired
in a later work item.
"""

import uuid

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.core.database import Base


class Web3Network(Base):  # type: ignore[misc]
    __tablename__ = "web3_networks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chain_id = Column(Text, nullable=False, unique=True, index=True)
    name = Column(Text, nullable=False)
    native_currency = Column(Text, nullable=False)
    provider = Column(Text, nullable=False, default="thirdweb")
    rpc_reference = Column(Text, nullable=True)
    confirmation_blocks = Column(Integer, nullable=False, default=12)
    free_tier_verified = Column(Boolean, nullable=False, default=False)
    capabilities = Column(JSON, nullable=False, default=dict)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Web3Wallet(Base):  # type: ignore[misc]
    __tablename__ = "web3_wallets"
    __table_args__ = (
        UniqueConstraint("provider", "network_id", "address", name="uq_web3_wallet_address"),
        Index("ix_web3_wallets_domain", "domain"),
        Index("ix_web3_wallets_state", "state"),
        CheckConstraint(
            "domain IN ('operational','treasury','project','development','user')",
            name="ck_web3_wallet_domain",
        ),
        CheckConstraint(
            "state IN ('proposed','verified','active','suspended','retired')",
            name="ck_web3_wallet_state",
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    wallet_id = Column(Text, nullable=False, unique=True)
    domain = Column(Text, nullable=False)
    provider = Column(Text, nullable=False)
    network_id = Column(UUID(as_uuid=True), ForeignKey("web3_networks.id", ondelete="SET NULL"), nullable=True)
    address = Column(Text, nullable=False)
    state = Column(Text, nullable=False, default="proposed")
    verification_method = Column(Text, nullable=True)
    verification_evidence_ref = Column(Text, nullable=True)
    policy_ref = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class Web3Transaction(Base):  # type: ignore[misc]
    __tablename__ = "web3_transactions"
    __table_args__ = (
        Index("ix_web3_transactions_status", "status"),
        Index("ix_web3_transactions_chain", "chain_id"),
        CheckConstraint(
            "status IN ('draft','validated','simulated','awaiting_approval','approved',"
            "'broadcast','confirming','confirmed','reconciled','rejected','expired',"
            "'failed','replaced','cancelled')",
            name="ck_web3_transaction_status",
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    approval_id = Column(Text, nullable=True)
    wallet_id = Column(Text, nullable=True)
    chain_id = Column(Text, nullable=False)
    tx_type = Column(Text, nullable=False)
    from_address = Column(Text, nullable=True)
    to_address = Column(Text, nullable=False)
    token = Column(Text, nullable=True)
    amount = Column(Numeric(36, 18), nullable=True)
    gas_estimate = Column(Numeric(36, 18), nullable=True)
    status = Column(Text, nullable=False, default="draft")
    idempotency_key = Column(Text, nullable=False, unique=True)
    tx_hash = Column(Text, nullable=True)
    simulation = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class Web3Asset(Base):  # type: ignore[misc]
    __tablename__ = "web3_assets"
    __table_args__ = (
        UniqueConstraint("chain_id", "contract_address", "symbol", name="uq_web3_asset"),
        CheckConstraint(
            "asset_type IN ('native','fungible','nft','multi_token','vault_share')",
            name="ck_web3_asset_type",
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chain_id = Column(Text, nullable=False)
    contract_address = Column(Text, nullable=True)
    symbol = Column(Text, nullable=False)
    name = Column(Text, nullable=True)
    decimals = Column(Integer, nullable=True)
    asset_type = Column(Text, nullable=False, default="fungible")
    source_url = Column(Text, nullable=True)
    risk_flags = Column(JSON, nullable=False, default=list)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Web3Contract(Base):  # type: ignore[misc]
    __tablename__ = "web3_contracts"
    __table_args__ = (
        UniqueConstraint("chain_id", "address", name="uq_web3_contract"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chain_id = Column(Text, nullable=False)
    address = Column(Text, nullable=False)
    standard = Column(Text, nullable=True)
    name = Column(Text, nullable=True)
    source_verified = Column(Boolean, nullable=False, default=False)
    proxy_detected = Column(Boolean, nullable=False, default=False)
    owner_analysis = Column(JSON, nullable=False, default=dict)
    risk_flags = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class NodeConnection(Base):  # type: ignore[misc]
    __tablename__ = "node_connections"
    __table_args__ = (
        UniqueConstraint("provider", "node_id", name="uq_node_connection"),
        CheckConstraint(
            "provider IN ('bitcoin_core','lnd','cln')", name="ck_node_provider"
        ),
        CheckConstraint(
            "health_state IN ('unknown','healthy','degraded','offline','suspended')",
            name="ck_node_health",
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider = Column(Text, nullable=False)
    node_id = Column(Text, nullable=False)
    endpoint_reference = Column(Text, nullable=True)
    transport = Column(Text, nullable=False, default="tailscale")
    tls_verified = Column(Boolean, nullable=False, default=False)
    credential_reference = Column(Text, nullable=True)
    health_state = Column(Text, nullable=False, default="unknown")
    last_check_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class NodeWalletBalance(Base):  # type: ignore[misc]
    __tablename__ = "node_wallet_balances"
    __table_args__ = (Index("ix_node_balances_connection", "connection_id"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    connection_id = Column(UUID(as_uuid=True), ForeignKey("node_connections.id", ondelete="CASCADE"), nullable=False)
    asset = Column(Text, nullable=False)
    confirmed = Column(Numeric(36, 8), nullable=False, default=0)
    unconfirmed = Column(Numeric(36, 8), nullable=False, default=0)
    observed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class BitcoinUtxo(Base):  # type: ignore[misc]
    __tablename__ = "bitcoin_utxos"
    __table_args__ = (
        UniqueConstraint("connection_id", "txid", "vout", name="uq_bitcoin_utxo"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    connection_id = Column(UUID(as_uuid=True), ForeignKey("node_connections.id", ondelete="CASCADE"), nullable=False)
    txid = Column(Text, nullable=False)
    vout = Column(Integer, nullable=False)
    address = Column(Text, nullable=True)
    amount_sats = Column(BigInteger, nullable=False, default=0)
    confirmations = Column(Integer, nullable=False, default=0)
    observed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class LightningChannel(Base):  # type: ignore[misc]
    __tablename__ = "lightning_channels"
    __table_args__ = (
        UniqueConstraint("connection_id", "channel_id", name="uq_lightning_channel"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    connection_id = Column(UUID(as_uuid=True), ForeignKey("node_connections.id", ondelete="CASCADE"), nullable=False)
    channel_id = Column(Text, nullable=False)
    peer_id = Column(Text, nullable=True)
    state = Column(Text, nullable=False, default="unknown")
    capacity_sats = Column(BigInteger, nullable=False, default=0)
    local_balance_sats = Column(BigInteger, nullable=False, default=0)
    remote_balance_sats = Column(BigInteger, nullable=False, default=0)
    observed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class LightningPeer(Base):  # type: ignore[misc]
    __tablename__ = "lightning_peers"
    __table_args__ = (
        UniqueConstraint("connection_id", "peer_id", name="uq_lightning_peer"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    connection_id = Column(UUID(as_uuid=True), ForeignKey("node_connections.id", ondelete="CASCADE"), nullable=False)
    peer_id = Column(Text, nullable=False)
    alias = Column(Text, nullable=True)
    connected = Column(Boolean, nullable=False, default=False)
    observed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class LightningInvoice(Base):  # type: ignore[misc]
    __tablename__ = "lightning_invoices"
    __table_args__ = (
        UniqueConstraint("connection_id", "payment_hash", name="uq_lightning_invoice"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    connection_id = Column(UUID(as_uuid=True), ForeignKey("node_connections.id", ondelete="CASCADE"), nullable=False)
    payment_hash = Column(Text, nullable=False)
    bolt11 = Column(Text, nullable=True)
    amount_sats = Column(BigInteger, nullable=True)
    state = Column(Text, nullable=False, default="unknown")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class LightningPayment(Base):  # type: ignore[misc]
    __tablename__ = "lightning_payments"
    __table_args__ = (
        UniqueConstraint("connection_id", "payment_hash", name="uq_lightning_payment"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    connection_id = Column(UUID(as_uuid=True), ForeignKey("node_connections.id", ondelete="CASCADE"), nullable=False)
    payment_hash = Column(Text, nullable=False)
    amount_sats = Column(BigInteger, nullable=True)
    fee_sats = Column(BigInteger, nullable=True)
    state = Column(Text, nullable=False, default="unknown")
    approval_id = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class LightningEvent(Base):  # type: ignore[misc]
    __tablename__ = "lightning_events"
    __table_args__ = (
        Index("ix_lightning_events_connection", "connection_id", "observed_at"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    connection_id = Column(UUID(as_uuid=True), ForeignKey("node_connections.id", ondelete="CASCADE"), nullable=False)
    event_type = Column(Text, nullable=False)
    payload = Column(JSON, nullable=False, default=dict)
    reconciled = Column(Boolean, nullable=False, default=False)
    observed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Web3ProviderHealth(Base):  # type: ignore[misc]
    __tablename__ = "web3_provider_health"
    __table_args__ = (
        UniqueConstraint("provider", "network", name="uq_web3_provider_health"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider = Column(Text, nullable=False)
    network = Column(Text, nullable=True)
    available = Column(Boolean, nullable=False, default=False)
    latency_ms = Column(Integer, nullable=True)
    last_check_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class BlockchainAuditLog(Base):  # type: ignore[misc]
    __tablename__ = "blockchain_audit_log"

    seq = Column(Integer, primary_key=True, autoincrement=True)
    prev_hash = Column(Text, nullable=False)
    entry_hash = Column(Text, nullable=False, unique=True)
    event_type = Column(Text, nullable=False)
    actor = Column(Text, nullable=False)
    target = Column(Text, nullable=True)
    approval_id = Column(Text, nullable=True)
    details = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

