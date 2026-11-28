"""Persistent state for the repository-wide emergency stop.

The halt is an operator/creator control, never an IAM self-action. A signed
Creator authorization is required to engage and to lift it; both transitions
are written to the audit stream. State is stored so a process restart cannot
silently clear an emergency.
"""

from sqlalchemy import JSON, Boolean, Column, DateTime, Text

from app.core.database import Base


class EmergencyShutdownState(Base):  # type: ignore[misc]
    __tablename__ = "emergency_shutdown_state"

    scope = Column(Text, primary_key=True)
    halted = Column(Boolean, nullable=False, default=False)
    reason = Column(Text, nullable=True)
    actor = Column(Text, nullable=True)
    authorization_id = Column(Text, nullable=True)
    engaged_at = Column(DateTime(timezone=True), nullable=True)
    details = Column(JSON, nullable=False, default=dict)
