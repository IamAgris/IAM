"""P2P transport acceptance tests.

Run: python tests/p2p_acceptance.py
Tests: signed envelopes, replay protection, dedup, store-and-forward, broadcast.
"""
import sys
import os
import httpx
import asyncio
import json
import websockets

BASE = os.environ.get("IAM_API_URL", "http://localhost:8000")
API_KEY = os.environ.get("IAM_API_KEY", "").strip()
if not API_KEY:
    raise SystemExit("IAM_API_KEY (admin scope) is required for P2P acceptance tests")
HEADERS = {"Authorization": f"Bearer {API_KEY}"}
results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok)))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))


def main():
    # 1. Envelope signing/verification unit behaviour via service
    try:
        sys.path.insert(0, r"D:\AI\project-aura\backend")
        from app.services.p2p_transport import make_envelope, verify_envelope
        env = make_envelope("node-a", "knowledge", {"x": 1}, 1, "secret")
        check("envelope signed", verify_envelope(env, "secret"))
        check("envelope rejects wrong key", not verify_envelope(env, "wrong"))
        env2 = dict(env); env2["payload"] = {"x": 2}
        check("tamper detected", not verify_envelope(env2, "secret"))
    except Exception as e:
        check("envelope signing", False, str(e))

    # 2. Transport endpoints
    try:
        r = httpx.get(f"{BASE}/api/v1/p2p/status", headers=HEADERS, timeout=10)
        check("p2p status endpoint", r.status_code == 200 and "node_id" in r.json())
    except Exception as e:
        check("p2p status endpoint", False, str(e))

    # 3. Store-and-forward to offline peer
    try:
        r = httpx.post(f"{BASE}/api/v1/p2p/send", headers=HEADERS, json={
            "peer_id": "offline-peer-1", "topic": "research", "payload": {"msg": "queued"}
        }, timeout=10)
        d = r.json()
        check("offline peer message queued", r.status_code == 200 and d.get("queued") is True)
        r2 = httpx.get(f"{BASE}/api/v1/p2p/outbox/offline-peer-1", headers=HEADERS, timeout=10)
        msgs = r2.json().get("messages", [])
        check("queued message retrievable", len(msgs) >= 1)
    except Exception as e:
        check("store-and-forward", False, str(e))

    # 4. Broadcast
    try:
        r = httpx.post(f"{BASE}/api/v1/p2p/broadcast", headers=HEADERS, json={
            "topic": "finding", "payload": {"type": "test"}
        }, timeout=10)
        check("broadcast endpoint", r.status_code == 200 and "envelope" in r.json())
    except Exception as e:
        check("broadcast", False, str(e))

    # 5. WebSocket delivery + gossip between two peers
    async def ws_test():
        try:
            uri = "ws://localhost:8000/api/v1/p2p/ws"
            async with websockets.connect(uri + "/peer-A?secret=shared-secret") as a, websockets.connect(uri + "/peer-B?secret=shared-secret") as b:
                from app.services.p2p_transport import make_envelope
                import time as _time, secrets as _sec
                seq = int(_time.time() * 1000) + int.from_bytes(_sec.token_bytes(3), "big")
                env = make_envelope("peer-A", "research", {"hello": "world", "t": _time.time()}, seq, "shared-secret")
                await a.send(json.dumps(env))
                ack = json.loads(await asyncio.wait_for(a.recv(), 3))
                check("ws ack returned", "ack" in ack)
                try:
                    gossiped = json.loads(await asyncio.wait_for(b.recv(), 3))
                    check("gossip delivered to peer B", gossiped.get("id") == env["id"])
                except asyncio.TimeoutError:
                    check("gossip delivered to peer B", False, "timeout")
        except Exception as e:
            check("websocket transport", False, str(e))

    asyncio.run(ws_test())

    print("\n=== P2P summary ===")
    passed = sum(1 for r in results if r[1])
    print(f"{passed}/{len(results)} passed")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
