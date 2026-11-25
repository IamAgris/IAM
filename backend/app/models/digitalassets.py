"""Digital asset and intellectual property SQLAlchemy models"""

from sqlalchemy import Column, String, Text, JSON, Boolean, Integer, DateTime, ForeignKey, CheckConstraint, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class DigitalAsset(Base):
    """Software, digital products, research and other created assets."""
    __tablename__ = "digital_assets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False)
    asset_type = Column(Text, nullable=False)  # software, document, media, research, product
    description = Column(Text, nullable=True)
    source_code_location = Column(Text, nullable=True)
    licence_type = Column(Text, nullable=True)
    owner_entity = Column(Text, nullable=False)  # Legal owner - person or entity, not IAM itself
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    revenue_generated = Column(Numeric(15, 4), nullable=False, default=0)

    __table_args__ = (
        CheckConstraint("revenue_generated >= 0", name="ck_digital_asset_revenue"),
    )

    licences = relationship("AssetLicence", back_populates="asset", cascade="all, delete-orphan")


class AssetLicence(Base):
    """Copyright and licensing records for assets."""
    __tablename__ = "asset_licences"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_id = Column(UUID(as_uuid=True), ForeignKey("digital_assets.id", ondelete="CASCADE"), nullable=False)
    licence_text = Column(Text, nullable=True)
    licence_url = Column(Text, nullable=True)
    granted_to = Column(Text, nullable=True)
    granted_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    asset = relationship("DigitalAsset", back_populates="licences")


class DomainRegistration(Base):
    """Domain registrations owned by IAM's projects."""
    __tablename__ = "domain_registrations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    domain_name = Column(Text, nullable=False, unique=True)
    registrar = Column(Text, nullable=True)
    registered_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    owner_entity = Column(Text, nullable=False)


class IPRecord(Base):
    """Intellectual property records."""
    __tablename__ = "ip_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_id = Column(UUID(as_uuid=True), ForeignKey("digital_assets.id", ondelete="CASCADE"), nullable=False)
    ip_type = Column(Text, nullable=False)  # copyright, trademark, patent, trade_secret
    registration_number = Column(Text, nullable=True)
    registered_at = Column(DateTime(timezone=True), nullable=True)
    owner_entity = Column(Text, nullable=False)

    __table_args__ = (
        CheckConstraint("ip_type IN ('copyright', 'trademark', 'patent', 'trade_secret')", name="ck_ip_type"),
    )
