"""Live search may publish only public fingerprints, never visitor content."""

import json
import unittest

from app.services.public_activity_signals import emit_public_search_activity


class FakeResult:
    def __init__(self, existing=False):
        self.existing = existing

    def scalar_one_or_none(self):
        return "existing-id" if self.existing else None


class FakeDB:
    def __init__(self, existing=False):
        self.events = []
        self.commits = 0
        self.existing = existing

    def add(self, event):
        self.events.append(event)

    async def execute(self, *_args, **_kwargs):
        return FakeResult(self.existing)

    async def commit(self):
        self.commits += 1


class PublicActivitySignalTests(unittest.IsolatedAsyncioTestCase):
    async def test_search_publishes_fingerprints_without_raw_urls(self):
        db = FakeDB()
        pasted = "https://www.sabcnews.com/sabcnews/story?visitor=secret-token"
        results = [
            {"url": pasted, "title": "Secret query title"},
            {"url": "https://en.wikipedia.org/wiki/Test", "title": "Test"},
        ]

        published = await emit_public_search_activity(db, results)

        self.assertTrue(published)
        types = [e.event_type for e in db.events]
        self.assertIn("research.search_completed", types)
        self.assertEqual(types.count("research.source_discovered"), 2)
        for event in db.events:
            if event.event_type != "research.source_discovered":
                continue
            source = event.details["source"]
            self.assertEqual(source["url"], "")
            self.assertEqual(source["node_id"], event.target)
            self.assertNotIn("visitor=secret-token", source["domain"])
            self.assertNotIn("Secret query title", source["title"])
        serialized = json.dumps(
            [{"target": e.target, "details": e.details} for e in db.events]
        )
        self.assertNotIn(pasted, serialized)
        self.assertNotIn("visitor=secret-token", serialized)
        self.assertEqual(db.commits, 1)

    async def test_duplicate_sources_are_not_republished(self):
        db = FakeDB(existing=True)
        published = await emit_public_search_activity(
            db, [{"url": "https://example.org/a", "title": "A"}]
        )
        self.assertFalse(published)
        self.assertEqual(
            [e.event_type for e in db.events], ["research.search_completed"]
        )

    async def test_empty_results_publish_nothing(self):
        db = FakeDB()
        published = await emit_public_search_activity(db, [])
        self.assertFalse(published)
        self.assertEqual(db.events, [])
        self.assertEqual(db.commits, 0)


if __name__ == "__main__":
    unittest.main()
