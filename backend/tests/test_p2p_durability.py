"""P2P store-and-forward and replay state survive a transport restart."""

import tempfile
import unittest
from pathlib import Path

from app.services.p2p_transport import P2PTransport, make_envelope


class P2PDurabilityTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = str(Path(self.directory.name) / "p2p-state.json")

    def tearDown(self):
        self.directory.cleanup()

    def test_outbox_survives_restart(self):
        first = P2PTransport()
        first.configure("node-a", "shared-secret", state_path=self.path)
        envelope = make_envelope("node-a", "research", {"note": "offline"}, 1, "shared-secret")
        first.queue_for("node-b", envelope)

        restarted = P2PTransport()
        restarted.configure("node-a", "shared-secret", state_path=self.path)
        self.assertEqual(restarted.drain("node-b"), [envelope])
        self.assertEqual(restarted.drain("node-b"), [])

    def test_replay_state_survives_restart(self):
        first = P2PTransport()
        first.configure("node-a", "shared-secret", state_path=self.path)
        envelope = make_envelope("peer", "research", {"note": "once"}, 7, "shared-secret")
        self.assertTrue(first.accept(envelope, "shared-secret")["accepted"])

        restarted = P2PTransport()
        restarted.configure("node-a", "shared-secret", state_path=self.path)
        result = restarted.accept(envelope, "shared-secret")
        self.assertFalse(result["accepted"])
        self.assertEqual(result["reason"], "duplicate")

    def test_transport_is_explicitly_not_ed25519(self):
        doc = P2PTransport.__module__ and __import__(
            "app.services.p2p_transport", fromlist=["make_envelope"]
        ).__doc__
        self.assertIn("HMAC", doc)
        self.assertIn("not implemented", doc)


if __name__ == "__main__":
    unittest.main()
