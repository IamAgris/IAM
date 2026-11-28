"""Node attestation, integrity and signed sync smoke test.

Requires two scoped credentials:
    IAM_ADMIN_KEY    - admin scope (approve known-good manifest, revoke)
    IAM_OPERATOR_KEY - operator scope (register/attest/publish)
"""

import base64
import json
import os
import uuid
from datetime import datetime, timezone

import httpx
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from auth_headers import install_auth_headers

install_auth_headers()

BASE = "http://localhost:8000"
results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok)))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))


def canonical(payload):
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sign_payload(payload):
    key = Ed25519PrivateKey.generate()
    public = base64.b64encode(
        key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
    ).decode()
    signature = base64.b64encode(key.sign(canonical(payload))).decode()
    return public, signature, key


def main():
    admin = os.environ.get("IAM_ADMIN_KEY", "")
    operator = os.environ.get("IAM_OPERATOR_KEY", "")
    if not admin or not operator:
        print("SKIP: set IAM_ADMIN_KEY and IAM_OPERATOR_KEY")
        return
    admin_h = {"Authorization": f"Bearer {admin}"}
    op_h = {"Authorization": f"Bearer {operator}"}

    s = httpx.get(f"{BASE}/api/v1/integrity/status", headers=op_h, timeout=20)
    check(
        "integrity status available",
        s.status_code == 200 and s.json().get("claim") == "best_effort_not_certainty",
        str(s.status_code),
    )

    forbidden = httpx.post(
        f"{BASE}/api/v1/integrity/manifest",
        headers=op_h,
        json={"confirm": True},
        timeout=20,
    )
    if operator != admin:
        check("manifest approval requires admin", forbidden.status_code == 403, str(forbidden.status_code))

    m = httpx.post(
        f"{BASE}/api/v1/integrity/manifest",
        headers=admin_h,
        json={"confirm": True},
        timeout=20,
    )
    root_hash = m.json().get("root_hash")
    check("known-good manifest approved", m.status_code == 200 and bool(root_hash), str(m.status_code))

    s = httpx.get(f"{BASE}/api/v1/integrity/status", headers=op_h, timeout=20)
    check("local measurement matches", s.status_code == 200 and s.json().get("matches") is True, str(s.json().get("matches")))

    # Honest attestation: matching core hash -> trusted.
    r = httpx.post(
        f"{BASE}/api/v1/nodes/register",
        headers=op_h,
        json={
            "name": f"attest-ok-{uuid.uuid4().hex[:8]}",
            "architecture": "arm64",
            "resources": {"permitted_contribution_percent": 1.0},
        },
        timeout=20,
    )
    node_id = r.json().get("id")
    check("candidate node registered", r.status_code == 200 and r.json().get("trust_level") == "candidate", str(r.status_code))

    payload = {
        "node_id": node_id,
        "core_hash": root_hash,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "nonce": uuid.uuid4().hex,
    }
    public, signature, private_key = sign_payload(payload)
    payload["public_key"] = public
    # Re-sign now that public_key is part of the signed payload.
    signature = base64.b64encode(private_key.sign(canonical(payload))).decode()

    a = httpx.post(
        f"{BASE}/api/v1/nodes/{node_id}/attestation",
        headers=op_h,
        json={"payload": payload, "signature": signature},
        timeout=20,
    )
    check("attestation promotes to trusted", a.status_code == 200 and a.json().get("trust_level") == "trusted", str(a.status_code) + " " + str(a.json().get("detail", "")))

    replay = httpx.post(
        f"{BASE}/api/v1/nodes/{node_id}/attestation",
        headers=op_h,
        json={"payload": payload, "signature": signature},
        timeout=20,
    )
    check("attestation replay rejected", replay.status_code == 400, str(replay.status_code))

    obj_payload = {"kind": "research", "summary": "approved note", "sources": []}
    signed_meta = canonical(
        {
            "publisher_node_id": node_id,
            "object_type": "research",
            "content_hash": __import__("hashlib").sha256(canonical(obj_payload)).hexdigest(),
        }
    )
    obj_sig = base64.b64encode(private_key.sign(signed_meta)).decode()
    p = httpx.post(
        f"{BASE}/api/v1/sync/objects",
        headers=op_h,
        json={
            "publisher_node_id": node_id,
            "object_type": "research",
            "payload": obj_payload,
            "signature": obj_sig,
        },
        timeout=20,
    )
    check("signed sync object accepted", p.status_code == 200 and p.json().get("verified") is True, str(p.status_code) + " " + str(p.json().get("detail", "")))

    st = httpx.get(f"{BASE}/api/v1/sync/status", headers=op_h, timeout=20)
    check("sync status available", st.status_code == 200 and st.json().get("objects", 0) >= 1, str(st.status_code))

    # Modified deployment: mismatched core hash -> restricted.
    r2 = httpx.post(
        f"{BASE}/api/v1/nodes/register",
        headers=op_h,
        json={
            "name": f"attest-limited-{uuid.uuid4().hex[:8]}",
            "architecture": "x86-64",
            "resources": {"permitted_contribution_percent": 1.0},
        },
        timeout=20,
    )
    node2 = r2.json().get("id")
    payload2 = {
        "node_id": node2,
        "core_hash": "0" * 64,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "nonce": uuid.uuid4().hex,
    }
    key2 = Ed25519PrivateKey.generate()
    pub2 = base64.b64encode(
        key2.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
    ).decode()
    payload2["public_key"] = pub2
    sig2 = base64.b64encode(key2.sign(canonical(payload2))).decode()
    a2 = httpx.post(
        f"{BASE}/api/v1/nodes/{node2}/attestation",
        headers=op_h,
        json={"payload": payload2, "signature": sig2},
        timeout=20,
    )
    check("modified node downgraded to restricted", a2.status_code == 200 and a2.json().get("trust_level") == "restricted", str(a2.status_code) + " " + str(a2.json().get("detail", "")))

    rep = httpx.post(
        f"{BASE}/api/v1/nodes/{node2}/restricted-report",
        headers=op_h,
        json={"reason": "local core modified"},
        timeout=20,
    )
    check("restricted reporting path", rep.status_code == 200 and rep.json().get("privileges") == "reporting_only", str(rep.status_code))

    rv = httpx.post(f"{BASE}/api/v1/nodes/{node2}/revoke", headers=admin_h, timeout=20)
    check("creator revocation", rv.status_code == 200 and rv.json().get("trust_level") == "revoked", str(rv.status_code))

    passed = sum(1 for _, ok in results if ok)
    print(f"\n=== Attestation smoke summary ===\n{passed}/{len(results)} passed")
    raise SystemExit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
