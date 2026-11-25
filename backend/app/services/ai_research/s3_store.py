"""WP6 — S3-compatible artifact store for IAM-controlled research storage.

The client is injectable so tests can use a stub; production uses boto3 with
the existing MinIO/S3 settings. All artifacts carry integrity metadata.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .artifacts import ArtifactStore, ResearchArtifact
from .base import ResearchError


class S3ArtifactStore:
    def __init__(
        self,
        bucket: str,
        client: Optional[Any] = None,
        prefix: str = "",
    ) -> None:
        if not bucket:
            raise ResearchError("S3 bucket is required")
        self.bucket = bucket
        self.prefix = prefix.strip("/")
        if client is not None:
            self.client = client
        else:
            try:
                import boto3  # type: ignore
            except ImportError as exc:  # pragma: no cover - dependency present in backend
                raise ResearchError("boto3 is required for S3 research storage") from exc
            from app.core.config import settings

            self.client = boto3.client(
                "s3",
                endpoint_url=settings.s3_endpoint,
                aws_access_key_id=settings.s3_access_key,
                aws_secret_access_key=settings.s3_secret_key,
                region_name=settings.s3_region,
            )

    def _key(self, key: str) -> str:
        return f"{self.prefix}/{key}" if self.prefix else key

    def put(
        self, key: str, payload: bytes, metadata: Optional[Dict[str, str]] = None
    ) -> ResearchArtifact:
        from .artifacts import ArtifactKind, sha256_bytes

        parts = key.split("/")
        try:
            experiment_id = parts[1]
            kind = ArtifactKind(parts[2])
        except (IndexError, ValueError) as exc:
            raise ResearchError(f"invalid research artifact key: {key}") from exc

        meta = {
            "experiment_id": experiment_id,
            "kind": kind.value,
            "sha256": sha256_bytes(payload),
            "size_bytes": str(len(payload)),
            **(metadata or {}),
        }
        self.client.put_object(
            Bucket=self.bucket,
            Key=self._key(key),
            Body=payload,
            Metadata=meta,
        )
        from datetime import datetime, timezone

        return ResearchArtifact(
            experiment_id=experiment_id,
            kind=kind,
            relative_path=key,
            sha256=meta["sha256"],
            size_bytes=len(payload),
            created_at=datetime.now(timezone.utc).isoformat(),
            metadata=metadata or {},
        )

    def get(self, key: str) -> bytes:
        response = self.client.get_object(Bucket=self.bucket, Key=self._key(key))
        return response["Body"].read()

    def exists(self, key: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket, Key=self._key(key))
            return True
        except Exception:
            return False

    def list(self, experiment_id: str) -> List[ResearchArtifact]:
        from .artifacts import ArtifactKind

        prefix = self._key(f"experiments/{experiment_id}/")
        response = self.client.list_objects_v2(Bucket=self.bucket, Prefix=prefix)
        artifacts = []
        for item in response.get("Contents", []):
            key = item["Key"]
            if self.prefix and key.startswith(f"{self.prefix}/"):
                key = key[len(self.prefix) + 1 :]
            parts = key.split("/")
            try:
                kind = ArtifactKind(parts[2])
                metadata = item.get("Metadata") or {}
                artifacts.append(
                    ResearchArtifact(
                        experiment_id=parts[1],
                        kind=kind,
                        relative_path=key,
                        sha256=metadata.get("sha256", ""),
                        size_bytes=int(metadata.get("size_bytes", item.get("Size", 0))),
                        created_at=item.get("LastModified", ""),
                        metadata=metadata,
                    )
                )
            except (IndexError, ValueError, TypeError):
                continue
        return artifacts


# Ensure the protocol is explicit for type checkers.
_: ArtifactStore = S3ArtifactStore  # type: ignore[assignment]
