"""Chat history persistence invariants.

A chat request may carry a resent client-side transcript for context, but only
the new turn belongs in stored history. Streamed deltas use the ``text`` key
emitted by inference_service; collecting any other key silently discards the
assistant reply.
"""

import unittest

from app.api.routes import models


def request_with(*messages):
    return models.ChatRequest(
        messages=[models.ChatMessage(role=role, content=content) for role, content in messages]
    )


class ChatPersistenceTests(unittest.TestCase):
    def test_only_the_last_user_turn_is_stored(self):
        request = request_with(
            ("system", "prompt"),
            ("user", "old question"),
            ("assistant", "old answer"),
            ("user", "new question"),
        )
        stored = models._new_turn_message(request)
        self.assertIsNotNone(stored)
        self.assertEqual(stored.role, "user")
        self.assertEqual(stored.content, "new question")

    def test_no_user_turn_returns_none(self):
        request = request_with(("system", "prompt"), ("assistant", "answer"))
        self.assertIsNone(models._new_turn_message(request))

    def test_streamed_delta_text_is_accumulated(self):
        accumulated = ""
        for payload in ({"text": "Hello "}, {"text": "IAM"}, {"request_id": "x"}):
            accumulated = models._append_delta(accumulated, payload)
        self.assertEqual(accumulated, "Hello IAM")


if __name__ == "__main__":
    unittest.main()
