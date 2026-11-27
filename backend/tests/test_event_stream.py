"""Public activity cursors must fail soft, not return HTTP 500."""

import unittest
from datetime import datetime, timezone

from app.services.event_stream import parse_since


class ParseSinceTests(unittest.TestCase):
    def test_empty_cursor(self):
        self.assertIsNone(parse_since(None))
        self.assertIsNone(parse_since(""))

    def test_utc_and_naive_cursors(self):
        parsed = parse_since("2026-11-27T10:00:00Z")
        self.assertEqual(parsed.tzinfo, timezone.utc)
        parsed = parse_since("2026-11-27T10:00:00")
        self.assertEqual(parsed.tzinfo, timezone.utc)

    def test_malformed_cursor_does_not_raise(self):
        for value in ("not-a-date", "2026-13-99", 12345, {"bad": True}):
            with self.subTest(value=value):
                self.assertIsNone(parse_since(value))


if __name__ == "__main__":
    unittest.main()
