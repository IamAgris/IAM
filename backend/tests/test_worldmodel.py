"""Phase 10 tests: world model entities, relationships, cause-effect, traversal, projection."""

import unittest
import uuid
from unittest.mock import patch

from app.models.worldmodel import (
    WorldEntity,
    EntityRelationship,
    CauseEffectChain,
    WorldEvent,
)
from app.services.worldmodel_service import WorldModelService


class FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def scalars(self):
        return self

    def all(self):
        return self.rows

    def scalar_one_or_none(self):
        return self.rows[0] if self.rows else None


class FakeDB:
    def __init__(self):
        self.rows = []

    def add(self, obj):
        if obj not in self.rows:
            if getattr(obj, "id", None) is None:
                obj.id = uuid.uuid4()
            self.rows.append(obj)

    async def flush(self):
        return None

    async def commit(self):
        return None

    async def refresh(self, obj):
        return None

    async def execute(self, statement):
        entity = statement.column_descriptions[0]["entity"]
        rows = [row for row in self.rows if isinstance(row, entity)]
        # Handle simple id == "uuid" WHERE clause filters (UUID string compare)
        wc = getattr(statement, "whereclause", None)
        if wc is not None and entity is WorldEntity:
            try:
                from sqlalchemy.sql.elements import BinaryExpression
                if isinstance(wc, BinaryExpression):
                    left = str(wc.left)
                    right = wc.right
                    if hasattr(right, "value"):
                        right = right.value
                    right = str(right)
                    if "id" in left and len(right) == 36 and "-" in right:
                        target = str(right)
                        rows = [row for row in rows if str(row.id) == target]
            except Exception:
                pass
        return FakeResult(rows)


class WorldModelTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = FakeDB()
        self.service = WorldModelService(self.db)

    async def test_entity_create_and_get(self):
        entity = await self.service.create_entity(
            name="Example Corp",
            entity_type="organisation",
            description="A test organisation",
            confidence=0.8,
        )
        self.assertEqual(entity["name"], "Example Corp")
        self.assertEqual(entity["entity_type"], "organisation")

        fetched = await self.service.get_entity(str(entity["id"]))
        self.assertEqual(fetched["name"], "Example Corp")
        self.assertEqual(fetched["entity_type"], "organisation")

    async def test_entity_get_invalid_id(self):
        with self.assertRaises(ValueError):
            await self.service.get_entity("not-a-uuid")

    async def test_relationship_and_traversal(self):
        a = await self.service.create_entity(
            name="Company A", entity_type="organisation", confidence=0.9
        )
        b = await self.service.create_entity(
            name="Company B", entity_type="organisation", confidence=0.9
        )
        c = await self.service.create_entity(
            name="Company C", entity_type="organisation", confidence=0.9
        )

        await self.service.create_relationship(
            str(a["id"]), str(b["id"]), "founded", 0.9
        )
        await self.service.create_relationship(
            str(b["id"]), str(c["id"]), "acquired", 0.8
        )

        rels = await self.service.list_relationships(str(a["id"]))
        self.assertEqual(len(rels), 2)
        types = {r["relationship_type"] for r in rels}
        self.assertIn("founded", types)
        self.assertIn("acquired", types)

        traversal = await self.service.traverse(str(a["id"]), depth=2)
        self.assertEqual(traversal["root_entity_id"], str(a["id"]))
        entity_ids = {e["id"] for e in traversal["entities"]}
        self.assertIn(str(b["id"]), entity_ids)
        self.assertIn(str(c["id"]), entity_ids)
        self.assertEqual(len(traversal["relationships"]), 2)

    async def test_cause_effect_and_projection(self):
        entity = await self.service.create_entity(
            name="Central Bank", entity_type="organisation", confidence=0.9
        )
        await self.service.record_cause_effect(
            "Interest rates rise", "Borrowing costs increase", 0.8
        )
        await self.service.record_cause_effect(
            "Borrowing costs increase", "Startup formation slows", 0.7
        )
        await self.service.record_cause_effect(
            "Startup formation slows", "Job creation falls", 0.6
        )

        chains = await self.service.list_cause_effects()
        self.assertEqual(len(chains), 3)

        proj = await self.service.project_scenario(
            str(entity["id"]), "Interest rates rise", depth=3
        )
        self.assertEqual(proj["trigger_description"], "Interest rates rise")
        self.assertGreaterEqual(len(proj["projections"]), 1)
        self.assertEqual(proj["projections"][0]["effect"], "Borrowing costs increase")
        self.assertAlmostEqual(
            proj["projections"][0]["projected_confidence"], 0.8
        )
        # Second hop: 0.8 * 0.7 = 0.56
        second = [p for p in proj["projections"] if p["effect"] == "Startup formation slows"]
        self.assertEqual(len(second), 1)
        self.assertAlmostEqual(second[0]["projected_confidence"], 0.56)

    async def test_world_events(self):
        event = await self.service.record_world_event(
            "regulation", "New AI safety law passed", relevance_to_iam=0.9
        )
        self.assertEqual(event["event_type"], "regulation")

        events = await self.service.list_world_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["event_type"], "regulation")

    async def test_traverse_invalid_entity(self):
        with self.assertRaises(ValueError):
            await self.service.traverse(str(uuid.uuid4()), depth=2)

    async def test_project_invalid_entity(self):
        with self.assertRaises(ValueError):
            await self.service.project_scenario(str(uuid.uuid4()), "trigger", depth=3)


if __name__ == "__main__":
    unittest.main()
