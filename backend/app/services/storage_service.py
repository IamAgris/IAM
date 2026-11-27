"""Core-authorised S3-compatible file storage (OD-29).

Files never go into the database and are never exposed without a scoped
credential. Metadata, checksums and ownership are recorded in Postgres.
"""

import base64
import hashlib
import re
import uuid
from typing import Any, Dict, List

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.security import AuditEvent
from app.models.storage import StoredObject

MAX_OBJECT_BYTES = 5 * 1024 * 1024
ALLOWED_CONTENT_TYPES = {
    "text/plain",
    "text/markdown",
    "text/csv",
    "application/json",
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/webp",
}


class StorageError(ValueError):
    pass


class StorageService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.bucket = settings.s3_bucket
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            region_name=settings.s3_region,
            config=Config(signature_version="s3v4", retries={"max_attempts": 2}),
        )

    def _ensure_bucket(self) -> None:
        try:
            self._client.head_bucket(Bucket=self.bucket)
        except ClientError:
            self._client.create_bucket(Bucket=self.bucket)

    async def upload(
        self,
        name: str,
        content: str,
        content_type: str = "text/plain",
        owner: str = "sdk",
        approved_for_sharing: bool = False,
    ) -> Dict[str, Any]:
        safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", name).strip("._") or "object"
        data = content.encode("utf-8") if isinstance(content, str) else content
        if len(data) > MAX_OBJECT_BYTES:
            raise StorageError(f"object exceeds {MAX_OBJECT_BYTES} byte limit")
        if content_type not in ALLOWED_CONTENT_TYPES:
            raise StorageError(f"content type not allowed: {content_type}")

        s3_key = f"iam/{uuid.uuid4().hex}/{safe_name}"
        digest = hashlib.sha256(data).hexdigest()
        self._ensure_bucket()
        self._client.put_object(
            Bucket=self.bucket,
            Key=s3_key,
            Body=data,
            ContentType=content_type,
            Metadata={"sha256": digest, "owner": owner},
        )

        record = StoredObject(
            name=safe_name,
            s3_key=s3_key,
            bucket=self.bucket,
            content_type=content_type,
            size_bytes=len(data),
            sha256=digest,
            owner=owner,
            is_approved_for_sharing=approved_for_sharing,
        )
        self.db.add(record)
        self.db.add(
            AuditEvent(
                event_type="storage_object_uploaded",
                actor=owner,
                target=safe_name,
                details={"sha256": digest, "size_bytes": len(data), "s3_key": s3_key},
            )
        )
        await self.db.commit()
        await self.db.refresh(record)
        return self.to_dict(record)

    async def get(self, object_id: str, owner: str = "sdk") -> Dict[str, Any]:
        record = await self._get(object_id)
        result = self._client.get_object(Bucket=record.bucket, Key=record.s3_key)
        data = result["Body"].read()
        if hashlib.sha256(data).hexdigest() != record.sha256:
            raise StorageError("stored object failed checksum verification")
        self.db.add(
            AuditEvent(
                event_type="storage_object_retrieved",
                actor=owner,
                target=record.name,
                details={"s3_key": record.s3_key},
            )
        )
        await self.db.commit()
        return {
            **self.to_dict(record),
            "content_base64": base64.b64encode(data).decode("ascii"),
        }

    async def list(self, owner: str | None = None) -> List[Dict[str, Any]]:
        query = select(StoredObject)
        if owner:
            query = query.where(StoredObject.owner == owner)
        result = await self.db.execute(query.order_by(StoredObject.created_at.desc()))
        return [self.to_dict(record) for record in result.scalars().all()]

    async def _get(self, object_id: str) -> StoredObject:
        result = await self.db.execute(
            select(StoredObject).where(StoredObject.id == object_id)
        )
        record = result.scalar_one_or_none()
        if not record:
            raise StorageError("object not found")
        return record

    @staticmethod
    def to_dict(record: StoredObject) -> Dict[str, Any]:
        return {
            "id": str(record.id),
            "name": record.name,
            "s3_key": record.s3_key,
            "bucket": record.bucket,
            "content_type": record.content_type,
            "size_bytes": record.size_bytes,
            "sha256": record.sha256,
            "owner": record.owner,
            "is_approved_for_sharing": record.is_approved_for_sharing,
            "created_at": record.created_at.isoformat() if record.created_at else None,
        }
