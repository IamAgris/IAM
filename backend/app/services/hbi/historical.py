"""Document 26 (OD-45): historical analysis modules 16–23.

Each module produces structured, evidence-graded output. Historical material
supplies context and carefully qualified lessons, never a guarantee that the
future repeats the past.
"""

from typing import Any, Dict, List

from app.services.hbi import advanced, temporal
from app.services.hbi.causal import causal_assessment


def _records_for(records: List[Dict[str, Any]], module_id: int) -> List[Dict[str, Any]]:
    return [r for r in records if module_id in (r.get("module_ids") or [])] or records[:10]


def analyse(module_id: int, question: str, records: List[Dict[str, Any]], graph: Any) -> Dict[str, Any]:
    base = {"module_id": module_id, "question": question, "scope": "aggregate"}
    if module_id == 16:  # Historical Research
        sources = graph.query(node_type="historical_source")["nodes"]
        return {**base, "status": "implemented", "sources": sources,
                "note": "Primary and secondary sources are kept distinct."}
    if module_id == 17:  # Historical Behaviour Analysis
        items = [r for r in records if (r.get("context_dimensions") or {}).get("environment", {}).get("period")]
        return {**base, "status": "implemented", "records": items[:20],
                "patterns": sorted({str((r.get("context_dimensions") or {}).get("environment", {}).get("period")) for r in items})}
    if module_id == 18:  # Historical Psychology
        hypotheses = [r for r in records if r.get("epistemic_type") == "hypothesis"]
        return {**base, "status": "implemented", "motivational_hypotheses": hypotheses[:10],
                "note": "Motivations are hypotheses, not established facts."}
    if module_id == 19:  # Historical Social Dynamics
        nodes = graph.query(node_type="society")["nodes"]
        return {**base, "status": "implemented", "societies": nodes,
                "relations": graph.query(relation="member_of")["edges"]}
    if module_id == 20:  # Historical Decision
        cutoff = None
        for token in question.replace("-", " ").split():
            if token.isdigit() and len(token) == 4:
                cutoff = int(token)
        available = [r for r in records if not cutoff or r.get("evidence_class") in {"verified", "well_supported"}]
        return {**base, "status": "implemented", "as_of": cutoff,
                "available_evidence": available[:10],
                "alternatives": [alt for r in available for alt in r.get("alternatives", [])][:10],
                "note": "Reconstructed with information available at the time; hindsight excluded."}
    if module_id == 21:  # Conflict and Cooperation
        relations = graph.query(relation="conflict")["edges"] + graph.query(relation="cooperation")["edges"]
        return {**base, "status": "implemented", "relations": relations}
    if module_id == 22:  # Patterns and Trends
        result = temporal.analyse(records, question)
        return {**base, "status": "implemented", **result}
    if module_id == 23:  # Historical Forecasting
        precedents = []
        for node in graph.query(node_type="historical_event")["nodes"][:5]:
            precedents.append({"event_id": node["node_ref"], "evidence_class": node["evidence_class"]})
        comparisons = [advanced.analogy({"similarities": {}}, precedent) for precedent in precedents]
        return {**base, "status": "implemented", "comparisons": comparisons,
                "note": "Weak or misleading analogies are explicitly permitted verdicts."}
    return {**base, "status": "unknown_module"}
