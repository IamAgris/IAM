"""Digital asset registry, licences and domains (Phase 9).

All assets are owned by a designated legal person or entity (OD-02) — never by
IAM itself. No registrar credentials or browser access are involved: domain
records are owner-provided metadata, not live registrations.
"""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.digitalassets import AssetLicence, DigitalAsset, DomainRegistration, IPRecord
from app.models.security import AuditEvent

ASSET_TYPES = ("software", "document", "media", "research", "product")
IP_TYPES = ("copyright", "trademark", "patent", "trade_secret")
DOMAIN_PATTERN = re.compile(r"^(?=.{1,253}$)(?!-)[a-z0-9-]{1,63}(?<!-)(\.[a-z0-9-]{1,63}(?<!-))+$")
_SECRET_PATTERN = re.compile(r"(?i)(password|secret|token|api[_-]?key|private[_-]?key)")


class DigitalAssetError(PermissionError):
    """Raised when registry data breaks ownership or provenance rules."""


def validate_owner_entity(value: Optional[str]) -> str:
    if not value or not value.strip():
        raise DigitalAssetError("owner_entity must name a legal person or entity")
    owner = value.strip()
    if owner.lower() in {"iam", "self", "none", "system", "aura"}:
        raise DigitalAssetError("IAM cannot own digital assets; name the designated legal entity")
    return owner


def _reject_secrets(fields: Dict[str, Any]) -> None:
    for name, value in fields.items():
        if isinstance(value, str) and _SECRET_PATTERN.search(value):
            raise DigitalAssetError(f"{name} must not contain credentials or secret values")


class DigitalAssetsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _asset(self, asset_id: str) -> DigitalAsset:
        try:
            identifier = UUID(str(asset_id))
        except (ValueError, TypeError) as exc:
            raise LookupError("digital asset not found") from exc
        result = await self.db.execute(
            select(DigitalAsset).where(DigitalAsset.id == identifier)
        )
        asset = result.scalar_one_or_none()
        if not asset:
            raise LookupError("digital asset not found")
        return asset

    async def create(
        self,
        *,
        name: str,
        asset_type: str,
        owner_entity: str,
        description: Optional[str] = None,
        source_code_location: Optional[str] = None,
        licence_type: Optional[str] = None,
        actor: str,
    ) -> Dict[str, Any]:
        if not name or asset_type not in ASSET_TYPES:
            raise DigitalAssetError("name and a supported asset_type are required")
        owner = validate_owner_entity(owner_entity)
        _reject_secrets(
            {
                "source_code_location": source_code_location or "",
                "licence_type": licence_type or "",
                "description": description or "",
            }
        )
        asset = DigitalAsset(
            name=name.strip(),
            asset_type=asset_type,
            description=description,
            source_code_location=source_code_location,
            licence_type=licence_type,
            owner_entity=owner,
        )
        self.db.add(asset)
        await self.db.flush()
        await self._audit("digital_asset_registered", asset.id, actor, {"name": name, "owner_entity": owner})
        await self.db.commit()
        return self._asset_dict(asset)

    async def list(self) -> List[Dict[str, Any]]:
        result = await self.db.execute(
            select(DigitalAsset).order_by(DigitalAsset.created_at.desc())
        )
        return [self._asset_dict(row) for row in result.scalars().all()]

    async def get(self, asset_id: str) -> Dict[str, Any]:
        return self._asset_dict(await self._asset(asset_id))

    async def update(
        self, asset_id: str, changes: Dict[str, Any], actor: str
    ) -> Dict[str, Any]:
        asset = await self._asset(asset_id)
        allowed = ("name", "description", "source_code_location", "licence_type")
        updates = {key: value for key, value in changes.items() if key in allowed}
        if not updates:
            raise DigitalAssetError("no updatable fields supplied")
        _reject_secrets(updates)
        for key, value in updates.items():
            setattr(asset, key, value)
        await self._audit("digital_asset_updated", asset.id, actor, {"fields": sorted(updates)})
        await self.db.commit()
        return self._asset_dict(asset)

    async def delete(self, asset_id: str, actor: str) -> Dict[str, Any]:
        asset = await self._asset(asset_id)
        await self._audit("digital_asset_deleted", asset.id, actor, {"name": asset.name})
        await self.db.delete(asset)
        await self.db.commit()
        return {"id": str(asset.id), "status": "deleted"}

    async def add_licence(
        self,
        asset_id: str,
        *,
        licence_text: Optional[str],
        licence_url: Optional[str],
        granted_to: Optional[str],
        actor: str,
    ) -> Dict[str, Any]:
        asset = await self._asset(asset_id)
        _reject_secrets(
            {
                "licence_text": licence_text or "",
                "licence_url": licence_url or "",
                "granted_to": granted_to or "",
            }
        )
        licence = AssetLicence(
            asset_id=asset.id,
            licence_text=licence_text,
            licence_url=licence_url,
            granted_to=granted_to,
        )
        self.db.add(licence)
        await self.db.flush()
        await self._audit(
            "asset_licence_recorded", asset.id, actor,
            {"licence_id": str(licence.id), "granted_to": granted_to},
        )
        await self.db.commit()
        return {
            "id": str(licence.id),
            "asset_id": str(asset.id),
            "granted_to": granted_to,
            "licence_url": licence_url,
        }

    async def licences(self, asset_id: str) -> List[Dict[str, Any]]:
        asset = await self._asset(asset_id)
        result = await self.db.execute(
            select(AssetLicence).where(AssetLicence.asset_id == asset.id)
        )
        return [
            {
                "id": str(row.id),
                "asset_id": str(row.asset_id),
                "licence_text": row.licence_text,
                "licence_url": row.licence_url,
                "granted_to": row.granted_to,
            }
            for row in result.scalars().all()
        ]

    async def add_ip(
        self,
        asset_id: str,
        *,
        ip_type: str,
        registration_number: Optional[str],
        owner_entity: str,
        actor: str,
    ) -> Dict[str, Any]:
        asset = await self._asset(asset_id)
        if ip_type not in IP_TYPES:
            raise DigitalAssetError(f"ip_type must be one of {IP_TYPES}")
        owner = validate_owner_entity(owner_entity)
        record = IPRecord(
            asset_id=asset.id,
            ip_type=ip_type,
            registration_number=registration_number,
            owner_entity=owner,
        )
        self.db.add(record)
        await self.db.flush()
        await self._audit(
            "ip_record_added", asset.id, actor,
            {"ip_id": str(record.id), "ip_type": ip_type, "owner_entity": owner},
        )
        await self.db.commit()
        return {
            "id": str(record.id),
            "asset_id": str(asset.id),
            "ip_type": ip_type,
            "owner_entity": owner,
        }

    async def ip_records(self, asset_id: str) -> List[Dict[str, Any]]:
        asset = await self._asset(asset_id)
        result = await self.db.execute(
            select(IPRecord).where(IPRecord.asset_id == asset.id)
        )
        return [
            {
                "id": str(row.id),
                "asset_id": str(row.asset_id),
                "ip_type": row.ip_type,
                "registration_number": row.registration_number,
                "owner_entity": row.owner_entity,
            }
            for row in result.scalars().all()
        ]

    async def register_domain(
        self,
        *,
        domain_name: str,
        owner_entity: str,
        registrar: Optional[str] = None,
        expires_at: Optional[str] = None,
        actor: str,
    ) -> Dict[str, Any]:
        domain = domain_name.strip().lower()
        if not DOMAIN_PATTERN.fullmatch(domain):
            raise DigitalAssetError("domain_name must be a valid DNS name")
        owner = validate_owner_entity(owner_entity)
        _reject_secrets({"registrar": registrar or ""})
        expiry = datetime.fromisoformat(expires_at.replace("Z", "+00:00")) if expires_at else None
        record = DomainRegistration(
            domain_name=domain,
            registrar=registrar,
            expires_at=expiry,
            owner_entity=owner,
        )
        self.db.add(record)
        await self.db.flush()
        await self._audit(
            "domain_registration_recorded", record.id, actor,
            {"domain": domain, "owner_entity": owner},
        )
        await self.db.commit()
        return {
            "id": str(record.id),
            "domain_name": domain,
            "registrar": registrar,
            "owner_entity": owner,
            "live_registration": False,
        }

    async def domains(self) -> List[Dict[str, Any]]:
        result = await self.db.execute(select(DomainRegistration))
        return [
            {
                "id": str(row.id),
                "domain_name": row.domain_name,
                "registrar": row.registrar,
                "expires_at": row.expires_at.isoformat() if row.expires_at else None,
                "owner_entity": row.owner_entity,
            }
            for row in result.scalars().all()
        ]

    async def _audit(self, event: str, target: Any, actor: str, details: Dict[str, Any]) -> None:
        self.db.add(
            AuditEvent(
                event_type=event,
                actor=actor,
                target=str(target),
                details=details,
            )
        )

    @staticmethod
    def _asset_dict(asset: DigitalAsset) -> Dict[str, Any]:
        return {
            "id": str(asset.id),
            "name": asset.name,
            "asset_type": asset.asset_type,
            "description": asset.description,
            "source_code_location": asset.source_code_location,
            "licence_type": asset.licence_type,
            "owner_entity": asset.owner_entity,
            "revenue_generated": float(asset.revenue_generated or 0),
        }
