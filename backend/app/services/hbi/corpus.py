"""Document 26 (OD-45): licensed local corpus ingestion.

A source is ingested only after the fail-closed corpus gate approves it.
Public accessibility is never treated as permission.
"""

import json
from pathlib import Path
from typing import Any, Dict, List

from app.services.hbi.schemas import CorpusSourceManifest, ResearchDocumentInput
from app.services.path_safety import UnsafePathError, contained_path


def load_manifest(path: str, root: str = "") -> List[Dict[str, Any]]:
    """Read a manifest, confined to *root* when one is supplied.

    Without an explicit root the manifest's own directory is the boundary.
    """
    base = root or str(Path(path).resolve().parent)
    # codeql[py/path-injection] contained_path resolves and enforces the corpus root.
    manifest_file = contained_path(base, path)
    # codeql[py/path-injection] manifest_file is resolved and contained above.
    payload = json.loads(manifest_file.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("manifest_must_be_a_list")
    return payload


async def ingest_corpus(service: Any, manifest_path: str, root: str = "") -> Dict[str, Any]:
    """Review every manifest entry, then ingest only approved sources."""
    results = []
    for entry in load_manifest(manifest_path, root):
        try:
            manifest = CorpusSourceManifest(**entry)
        except Exception as error:
            results.append({
                "source_id": entry.get("source_id"),
                "status": "invalid_manifest_entry",
                "reason": str(error)[:300],
            })
            continue

        review = service.corpus_governance.review(manifest, intended_purpose="research")
        if review["decision"] != "approved":
            results.append({
                "source_id": manifest.source_id,
                "status": review["decision"],
                "reasons": review["rejected_reasons"] + review["pending_reasons"],
            })
            continue
        service.permission_engine.register_manifest(manifest)
        if not manifest.path:
            results.append({"source_id": manifest.source_id, "status": "path_missing"})
            continue

        try:
            # codeql[py/path-injection] contained_path resolves and enforces the corpus root.
            file_path = contained_path(
                root or str(Path(manifest_path).resolve().parent), manifest.path
            )
        except (UnsafePathError, OSError, ValueError):
            results.append({"source_id": manifest.source_id, "status": "path_outside_root"})
            continue
        # codeql[py/path-injection] file_path is contained above.
        if not file_path.is_file():
            results.append({"source_id": manifest.source_id, "status": "file_missing"})
            continue

        # codeql[py/path-injection] file_path is contained above.
        text = file_path.read_text(encoding="utf-8", errors="ignore")[:20000]
        document = ResearchDocumentInput(
            source_id=manifest.source_id,
            title=manifest.source.title,
            text=text,
            source_type="peer_reviewed_journal",
            licence=manifest.licensing.licence_id or "documented_permission",
            permitted_purpose="research",
            collection_date=manifest.source.collection_date,
            period=None,
            region=None,
            population=None,
        )
        result = await service.ingest(document)
        result["status"] = "ingested"
        result["governance"] = {
            "approved_by": review["approved_by"],
            "reviewed_at": review["reviewed_at"],
            "rules_applied": review["rules_applied"],
        }
        results.append(result)

    return {
        "manifest": manifest_path,
        "documents": len(results),
        "records_accepted": sum(len(item.get("accepted", [])) for item in results),  # type: ignore[arg-type, misc]
        "results": results,
        "corpus_state": service.corpus_governance.state()["state"],
        "note": "Unapproved sources are excluded from the approved research corpus.",
    }
