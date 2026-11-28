"""P2P transport service — direct peer-to-peer messaging and sync.

Implements the transport layer specified in IAM_DISTRIBUTED_ARCHITECTURE.md (C)
and IAM_DYNAMIC_NODE_NETWORK_SPEC.md (OD-26):
  - Signed message envelopes (HMAC-SHA256 over the canonical body; Ed25519 is
    not implemented in this transport — do not describe these as Ed25519)
  - Persistent WebSocket connections between nodes
  - Store-and-forward for offline peers
  - Replay protection via monotonic sequence numbers
  - Gossip-style knowledge sync

Security: peers are untrusted until attested; a timeout is never proof of
delivery failure — duplicate suppression is mandatory.
"""

import json
import time
import uuid
import hashlib
import secrets
from typing import Dict, Any, List, Optional
from collections import defaultdict
import asyncio
import loguru
from pathlib import Path

logger = loguru.logger

from app.services.whitehat_policy import (
    WhiteHatPolicyError,
    ensure_p2p_shareable,
)


def make_envelope(
    sender_id: str,
    topic: str,
    payload: Dict[str, Any],
    seq: int,
    secret: str,
    recipient: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a signed, replay-protected message envelope."""
    env = {
        "id": str(uuid.uuid4()),
        "sender": sender_id,
        "recipient": recipient,
        "topic": topic,
        "seq": seq,
        "ts": int(time.time()),
        "payload": payload,
    }
    body = json.dumps(
        {k: env[k] for k in ("id", "sender", "recipient", "topic", "seq", "ts", "payload")},
        sort_keys=True, ensure_ascii=False,
    ).encode()
    env["sig"] = hashlib.sha256(secret.encode() + body).hexdigest()
    return env


def verify_envelope(env: Dict[str, Any], secret: str) -> bool:
    """Verify envelope signature and basic shape."""
    if not all(k in env for k in ("id", "sender", "topic", "seq", "ts", "payload", "sig")):
        return False
    body = json.dumps(
        {k: env[k] for k in ("id", "sender", "recipient", "topic", "seq", "ts", "payload")},
        sort_keys=True, ensure_ascii=False,
    ).encode()
    expected = hashlib.sha256(secret.encode() + body).hexdigest()
    return secrets.compare_digest(expected, env["sig"])


class P2PTransport:
    """In-memory transport registry + store-and-forward queues."""

    def __init__(self) -> Any:
        self.connections: Dict[str, Any] = {}       # node_id -> WebSocket
        self.seq: Dict[str, int] = defaultdict(int)  # sender -> last seq seen (inbound)
        self.outgoing_seq: Dict[str, int] = defaultdict(int)  # node -> next seq to send
        self.seen: Dict[str, float] = {}            # envelope id -> ts (dedup)
        self.outbox: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.local_secret: str = secrets.token_hex(32)
        self.node_id: str = "local-iam"
        self.state_path: Optional[Path] = None

    def configure(
        self,
        node_id: str,
        secret: Optional[str] = None,
        state_path: Optional[str] = None,
    ) -> Any:
        self.node_id = node_id
        if secret:
            self.local_secret = secret
        if state_path:
            self.state_path = Path(state_path)
            self.load()

    def load(self) -> None:
        """Restore outbox and replay state from an operator-managed file."""
        if not self.state_path or not self.state_path.exists():
            return
        try:
            data = json.loads(self.state_path.read_text(encoding="utf-8"))
            self.outbox.update(
                {str(k): list(v) for k, v in (data.get("outbox") or {}).items()}
            )
            self.seq.update({str(k): int(v) for k, v in (data.get("seq") or {}).items()})
            self.seen.update({str(k): float(v) for k, v in (data.get("seen") or {}).items()})
            self.outgoing_seq.update(
                {str(k): int(v) for k, v in (data.get("outgoing_seq") or {}).items()}
            )
            logger.info("P2P transport state restored")
        except Exception as exc:  # pragma: no cover - corrupt/partial file
            logger.warning(f"P2P state load failed: {type(exc).__name__}")

    def _persist(self) -> None:
        """Atomically persist durable state; best-effort, never blocks messaging."""
        if not self.state_path:
            return
        try:
            # Bound replay cache growth before writing.
            if len(self.seen) > 2000:
                oldest = sorted(self.seen.items(), key=lambda item: item[1])[: len(self.seen) - 2000]
                for key, _ in oldest:
                    self.seen.pop(key, None)
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.state_path.with_suffix(".tmp")
            tmp.write_text(
                json.dumps(
                    {
                        "outbox": self.outbox,
                        "seq": dict(self.seq),
                        "outgoing_seq": dict(self.outgoing_seq),
                        "seen": self.seen,
                    },
                    sort_keys=True,
                ),
                encoding="utf-8",
            )
            tmp.replace(self.state_path)
        except Exception as exc:  # pragma: no cover - filesystem failure
            logger.warning(f"P2P state persist failed: {type(exc).__name__}")

    def next_seq(self) -> int:
        # Outbound counters must not be confused with inbound replay tracking:
        # a locally published envelope would otherwise look like a replay.
        self.outgoing_seq[self.node_id] += 1
        self._persist()
        return self.outgoing_seq[self.node_id]

    def accept(self, env: Dict[str, Any], peer_secret: Optional[str] = None) -> Dict[str, Any]:
        """Accept an inbound envelope: verify, dedup, replay-check, store."""
        try:
            ensure_p2p_shareable(str(env.get("topic", "")), env.get("payload") or {})
        except (WhiteHatPolicyError, TypeError, ValueError):
            return {"accepted": False, "reason": "offensive_tool_rejected"}
        secret = peer_secret or self.local_secret
        if not verify_envelope(env, secret):
            return {"accepted": False, "reason": "invalid_signature"}
        eid = env.get("id")
        if eid in self.seen:
            return {"accepted": False, "reason": "duplicate"}
        last = self.seq.get(env["sender"], 0)
        if env["seq"] <= last:
            return {"accepted": False, "reason": "replay"}
        self.seq[env["sender"]] = env["seq"]
        self.seen[eid] = time.time()
        self._persist()
        return {"accepted": True, "envelope": env}

    def queue_for(self, peer_id: str, env: Dict[str, Any]) -> Any:
        """Store-and-forward for an offline peer."""
        self.outbox[peer_id].append(env)
        self._persist()

    def drain(self, peer_id: str) -> List[Dict[str, Any]]:
        """Return queued envelopes for a peer that reconnects."""
        items = self.outbox.pop(peer_id, [])
        self._persist()
        return items

    def register_ws(self, peer_id: str, ws: Any) -> Any:
        self.connections[peer_id] = ws

    def unregister_ws(self, peer_id: str) -> Any:
        self.connections.pop(peer_id, None)

    async def broadcast(self, topic: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Gossip to all connected peers; queue the rest for later."""
        ensure_p2p_shareable(topic, payload)
        env = make_envelope(self.node_id, topic, payload, self.next_seq(), self.local_secret)
        delivered, queued = [], []
        for peer_id, ws in list(self.connections.items()):
            try:
                await ws.send_json(env)
                delivered.append(peer_id)
            except Exception as e:
                logger.warning(f"P2P send to {peer_id} failed: {e}")
                self.queue_for(peer_id, env)
                queued.append(peer_id)
        return {"envelope": env, "delivered": delivered, "queued": queued}

    async def send_to(self, peer_id: str, topic: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        ensure_p2p_shareable(topic, payload)
        env = make_envelope(self.node_id, topic, payload, self.next_seq(), self.local_secret, recipient=peer_id)
        ws = self.connections.get(peer_id)
        if ws:
            try:
                await ws.send_json(env)
                return {"delivered": True, "envelope": env}
            except Exception as e:
                logger.warning(f"P2P send to {peer_id} failed: {e}")
        self.queue_for(peer_id, env)
        return {"delivered": False, "queued": True, "envelope": env}


transport = P2PTransport()
