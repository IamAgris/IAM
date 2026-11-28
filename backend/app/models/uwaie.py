"""Universal Website and Application Interaction knowledge (OD-27).

Stored workflows contain no credentials, cookies or sessions. They are
unapproved local knowledge until explicitly reviewed and accepted.
"""

import uuid

from sqlalchemy import Boolean, Column, DateTime, JSON, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.core.database import Base


class WebsiteWorkflow(Base):  # type: ignore[misc]
    __tablename__ = "website_workflows"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False)
    url_pattern = Column(Text, nullable=False)
    steps = Column(JSON, nullable=False, default=list)
    verification = Column(JSON, nullable=False, default=dict)
    source_actor = Column(Text, nullable=False)
    is_approved = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
