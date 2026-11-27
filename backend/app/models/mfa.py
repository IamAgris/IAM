"""WebAuthn passkey and TOTP enrollment records (Phase 9)."""

from sqlalchemy import Column, Text, JSON, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class WebAuthnChallenge(Base):
    __tablename__ = "webauthn_challenges"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    website_credential_id = Column(
        UUID(as_uuid=True), ForeignKey("website_credentials.id", ondelete="CASCADE"), nullable=False
    )
    purpose = Column(Text, nullable=False)  # register | authenticate
    challenge = Column(Text, nullable=False)
    rp_id = Column(Text, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    consumed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class PasskeyCredential(Base):
    __tablename__ = "passkey_credentials"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    website_credential_id = Column(
        UUID(as_uuid=True), ForeignKey("website_credentials.id", ondelete="CASCADE"), nullable=False
    )
    credential_id = Column(Text, nullable=False, unique=True)
    public_key_pem = Column(Text, nullable=False)
    rp_id = Column(Text, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_used_at = Column(DateTime(timezone=True), nullable=True)


class TotpEnrollment(Base):
    __tablename__ = "totp_enrollments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    website_credential_id = Column(
        UUID(as_uuid=True), ForeignKey("website_credentials.id", ondelete="CASCADE"), nullable=False
    )
    secret_ciphertext = Column(Text, nullable=False)
    issuer = Column(Text, nullable=True)
    account = Column(Text, nullable=True)
    recovery_hashes = Column(JSON, nullable=False, default=list)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
