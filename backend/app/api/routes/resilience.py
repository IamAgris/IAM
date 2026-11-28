"""Resilience engine routes - health monitoring, recovery, backups, disaster recovery"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from app.core.database import get_db_session
from app.services.resilience_service import ResilienceService

router = APIRouter(prefix="/api/v1/resilience", tags=["resilience"])


class HealthCheckRequest(BaseModel):
    service_name: str
    status: str  # healthy, degraded, down
    response_time_ms: Optional[int] = None
    details: Optional[Dict[str, Any]] = None


class RecoveryRequest(BaseModel):
    service_name: str
    action: str
    success: bool
    details: Optional[Dict[str, Any]] = None


class BackupVerificationRequest(BaseModel):
    backup_id: str
    verification_type: str  # full, partial, integrity
    success: bool
    restored_items: Optional[int] = None


class IncidentRequest(BaseModel):
    incident_type: str  # security, failure, outage, suspicious_activity
    severity: str  # low, medium, high, critical
    title: str
    description: Optional[str] = None


class CredentialRotationRequest(BaseModel):
    secret_name: str
    integration_id: Optional[str] = None
    next_rotation_due: Optional[str] = None


@router.post("/health")
async def record_health_check(request: HealthCheckRequest, db: AsyncSession = Depends(get_db_session)):  # type: ignore[no-untyped-def]
    """Record a service health check."""
    service = ResilienceService(db)
    try:
        return await service.record_health_check(
            request.service_name, request.status,
            request.response_time_ms, request.details,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/health")
async def get_health(  # type: ignore[no-untyped-def]
    service_name: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session),
):
    """Get latest health checks."""
    service = ResilienceService(db)
    return await service.get_latest_health(service_name)


@router.post("/recovery")
async def record_recovery(request: RecoveryRequest, db: AsyncSession = Depends(get_db_session)):  # type: ignore[no-untyped-def]
    """Record an automatic recovery action."""
    service = ResilienceService(db)
    return await service.record_recovery(
        request.service_name, request.action, request.success, request.details,
    )


@router.post("/backup-verify")
async def verify_backup(request: BackupVerificationRequest, db: AsyncSession = Depends(get_db_session)):  # type: ignore[no-untyped-def]
    """Verify a backup can be restored."""
    service = ResilienceService(db)
    return await service.record_backup_verification(
        request.backup_id, request.verification_type, request.success, request.restored_items,
    )


@router.post("/incidents")
async def record_incident(request: IncidentRequest, db: AsyncSession = Depends(get_db_session)):  # type: ignore[no-untyped-def]
    """Record a security or failure incident."""
    service = ResilienceService(db)
    try:
        return await service.record_incident(
            request.incident_type, request.severity, request.title, request.description,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/credential-rotate")
async def rotate_credential(request: CredentialRotationRequest, db: AsyncSession = Depends(get_db_session)):  # type: ignore[no-untyped-def]
    """Record credential rotation."""
    service = ResilienceService(db)
    return await service.record_credential_rotation(
        request.secret_name, request.integration_id, request.next_rotation_due,
    )
