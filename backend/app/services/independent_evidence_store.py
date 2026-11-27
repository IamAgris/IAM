"""Append-only evidence store for independent evaluation.

Independent reports are authoritative artifacts held outside IAM's writable
knowledge database. Each report is written once under its run id and signed
with an operator-held key that is distinct from IAM's runtime credentials. A
report that is missing from this store, or whose signature does not verify, is
not admissible evidence — even if a matching belief exists in the database.

When no signing key is configured the store still provides append-only file
storage, but reports are only hash-verified. Production deployments should set
``independent_eval_signing_key`` and point the root at a mount IAM cannot
rewrite selectively.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

from app.core.config import settings


def canonical(payload: Dict[str, Any]) -> bytes:
    """Stable bytes for signing and verification."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


class IndependentEvidenceStore:
    def __init__(self, root: Optional[str] = None, signing_key: Optional[str] = None):
        self.root = Path(
            root
            or settings.independent_eval_artifact_root
            or str(Path(tempfile.gettempdir()) / "iam-independent-evaluation")
        )
        self.root.mkdir(parents=True, exist_ok=True)
        self.signing_key = (
            signing_key
            if signing_key is not None
            else settings.independent_eval_signing_key
        )

    def _paths(self, run_id: str) -> tuple[Path, Path]:
        safe = "".join(ch for ch in run_id if ch.isalnum() or ch in "-_")
        if not safe:
            raise ValueError("invalid run id")
        return self.root / f"{safe}.json", self.root / f"{safe}.sig"

    def _signature(self, payload: bytes) -> str:
        if self.signing_key:
            return hmac.new(
                self.signing_key.encode("utf-8"), payload, hashlib.sha256
            ).hexdigest()
        return hashlib.sha256(payload).hexdigest()

    def signature_for(self, payload: Dict[str, Any]) -> str:
        """Signature for a payload without writing it."""
        return self._signature(canonical(payload))

    def append(self, run_id: str, payload: Dict[str, Any]) -> str:
        """Write a report once; refuse to overwrite an existing artifact."""
        report_path, signature_path = self._paths(run_id)
        if report_path.exists():
            raise FileExistsError(f"independent report already stored: {run_id}")
        body = canonical(payload)
        signature = self._signature(body)
        report_path.write_bytes(body)
        signature_path.write_text(signature, encoding="ascii")
        return signature

    def verify(self, run_id: str, payload: Dict[str, Any], signature: str) -> bool:
        """Check both the stored artifact and its operator signature."""
        try:
            report_path, signature_path = self._paths(run_id)
            if not report_path.exists() or not signature_path.exists():
                return False
            stored = json.loads(report_path.read_bytes().decode("utf-8"))
            if stored != payload:
                return False
            expected = self._signature(canonical(stored))
            recorded = signature_path.read_text(encoding="ascii").strip()
            return hmac.compare_digest(expected, recorded) and hmac.compare_digest(
                expected, signature
            )
        except (OSError, ValueError, UnicodeDecodeError):
            return False


_default_store: Optional[IndependentEvidenceStore] = None


def default_store() -> IndependentEvidenceStore:
    global _default_store
    if _default_store is None:
        _default_store = IndependentEvidenceStore()
    return _default_store
