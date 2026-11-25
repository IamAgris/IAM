"""Core-authorised object storage metadata (OD-29).

Binary content lives in S3-compatible storage. Only metadata and references
are kept in Postgres; no file bytes are stored in the database.
"""

import uuid

from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.core.database import Base


class StoredObject(Base):
    __tablename__ = "stored_objects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False)
    s3_key = Column(Text, nullable=False, unique=True)
    bucket = Column(Text, nullable=False)
    content_type = Column(Text, nullable=False)
    size_bytes = Column(Integer, nullable=False)
    sha256 = Column(Text, nullable=False)
    owner = Column(Text, nullable=False)
    is_approved_for_sharing = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("size_bytes >= 0", name="ck_stored_object_size"),
    )
