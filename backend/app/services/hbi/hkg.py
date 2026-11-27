"""Document 26 (OD-45): E1 Historical Knowledge Graph.

Connects events, people, institutions, ideas and outcomes across time.
Edges are typed and evidence-graded; conflicting accounts remain distinct.
"""

import uuid
from collections import deque
from typing import Any, Dict, List, Optional

from app.services.hbi.chronology import date_bounds


class HistoricalKnowledgeGraph:
    def __init__(self, db_session: Optional[Any] = None):
        self.db = db_session
        self.nodes: Dict[str, Dict[str, Any]] = {}
        self.edges: Dict[str, Dict[str, Any]] = {}

    async def add_node(self, *, node_ref: Optional[str] = None, node_type: str,
                       label: str, period: Optional[str] = None,
                       region: Optional[str] = None,
                       date_value: Optional[Any] = None,
                       properties: Optional[Dict[str, Any]] = None,
                       evidence_class: str = "unverified") -> Dict[str, Any]:
        bounds = date_bounds(date_value) if date_value is not None else None
        node = {
            "node_ref": node_ref or "hgn_" + uuid.uuid4().hex,
            "node_type": node_type,
            "label": label,
            "period": period,
            "region": region,
            "date_low": bounds[0] if bounds else None,
            "date_high": bounds[1] if bounds else None,
            "properties": properties or {},
            "evidence_class": evidence_class,
        }
        self.nodes[node["node_ref"]] = node
        if self.db is not None:
            from app.models.hbi import HBIGraphNode
            self.db.add(HBIGraphNode(**node))
            await self.db.flush()
        return node

    async def add_edge(self, *, from_ref: str, to_ref: str, relation: str,
                       confidence: float = 0.0, evidence_class: str = "unverified",
                       properties: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if from_ref not in self.nodes or to_ref not in self.nodes:
            raise ValueError("unknown_node_reference")
        edge = {
            "edge_ref": "hge_" + uuid.uuid4().hex,
            "from_ref": from_ref,
            "to_ref": to_ref,
            "relation": relation,
            "confidence": confidence,
            "evidence_class": evidence_class,
            "properties": properties or {},
        }
        self.edges[edge["edge_ref"]] = edge
        if self.db is not None:
            from app.models.hbi import HBIGraphEdge
            self.db.add(HBIGraphEdge(**edge))
            await self.db.flush()
        return edge

    def query(self, *, node_type: Optional[str] = None, period: Optional[str] = None,
              region: Optional[str] = None, relation: Optional[str] = None,
              keyword: Optional[str] = None, limit: int = 50) -> Dict[str, Any]:
        if relation:
            matches = [e for e in self.edges.values() if e["relation"] == relation]
            return {"count": len(matches[:limit]), "edges": matches[:limit]}
        matches = []
        for node in self.nodes.values():
            if node_type and node["node_type"] != node_type:
                continue
            if period and node["period"] != period:
                continue
            if region and node["region"] != region:
                continue
            if keyword and keyword.lower() not in node["label"].lower():
                continue
            matches.append(node)
        return {"count": len(matches[:limit]), "nodes": matches[:limit]}

    def expand(self, node_ref: str, depth: int = 1) -> Dict[str, Any]:
        if node_ref not in self.nodes:
            raise ValueError("unknown_node_reference")
        visited = {node_ref}
        frontier = deque([(node_ref, 0)])
        found_edges = []
        while frontier:
            current, level = frontier.popleft()
            if level >= depth:
                continue
            for edge in self.edges.values():
                if edge["from_ref"] == current or edge["to_ref"] == current:
                    found_edges.append(edge)
                    other = edge["to_ref"] if edge["from_ref"] == current else edge["from_ref"]
                    if other not in visited:
                        visited.add(other)
                        frontier.append((other, level + 1))
        return {
            "root": node_ref,
            "depth": depth,
            "nodes": [self.nodes[ref] for ref in visited],
            "edges": found_edges,
            "conflicting_accounts_preserved": True,
        }

    async def ingest_timeline(self, timeline_result: Dict[str, Any]) -> Dict[str, Any]:
        """Materialise E13 chronology output as graph nodes and temporal edges."""
        refs = {}
        for event in timeline_result.get("ordered_events", []):
            node = await self.add_node(
                node_ref="evt_" + str(event["event_id"]),
                node_type="historical_event",
                label=str(event.get("name") or event["event_id"]),
                period=event.get("calendar"),
                date_value=event.get("bounds"),
                properties={
                    "precision": event.get("precision"),
                    "date_confidence": event.get("date_confidence"),
                    "undated": event.get("undated"),
                },
                evidence_class="unverified",
            )
            refs[str(event["event_id"])] = node["node_ref"]
        for relation in timeline_result.get("relations", []):
            source = refs.get(str(relation["event_a"]))
            target = refs.get(str(relation["event_b"]))
            if source and target:
                await self.add_edge(
                    from_ref=source, to_ref=target,
                    relation=relation["relation"],
                    confidence=relation.get("relation_confidence") or 0.0,
                )
        for account in timeline_result.get("conflicting_accounts", []):
            await self.add_node(
                node_type="contested_account",
                label=str(account.get("account_a")),
                properties=account,
                evidence_class="contested",
            )
        return {
            "nodes_added": len(refs),
            "edges_added": len(timeline_result.get("relations", [])),
            "conflicting_accounts": len(timeline_result.get("conflicting_accounts", [])),
        }
