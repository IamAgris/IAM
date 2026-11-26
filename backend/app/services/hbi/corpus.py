"""Document 26 (OD-45): licensed local corpus ingestion.

A source is ingested only after the fail-closed corpus gate approves it.
Public accessibility is never treated as permission.
"""

import json
from pathlib import Path
from typing import Any, Dict, List

from app.services.hbi.schemas import CorpusSourceManifest, ResearchDocumentInput


def load_manifest(path: str) -> List[Dict[str, Any]]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("manifest_must_be_a_list")
    return payload


async def ingest_corpus(service: Any, manifest_path: str, root: str = "") -> Dict[str, Any]:
    """Review every manifest entry, then ingest only approved sources."""
    results = []
    for entry in load_manifest(manifest_path):
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
        if not manifest.path:
            results.append({"source_id": manifest.source_id, "status": "path_missing"})
            continue

        file_path = Path(manifest.path)
        if not file_path.is_absolute() and root:
            file_path = Path(root) / file_path
        if not file_path.is_file():
            results.append({"source_id": manifest.source_id, "status": "file_missing"})
            continue

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
        "records_accepted": sum(len(item.get("accepted", [])) for item in results),
        "results": results,
        "corpus_state": service.corpus_governance.state()["state"],
        "note": "Unapproved sources are excluded from the approved research corpus.",
    }
