"""Creator hardware signer acceptance tests."""
import sys
import httpx

sys.path.insert(0, r"D:\AI\project-aura\backend")
from app.services.creator_keys import generate_keypair, sign_challenge, verify_signature

BASE = "http://localhost:8000"
H = {"Authorization": "Bearer iam_GJaBEtX-1Uyt13V4m7hwxZ0oNNOkErOP5rrwyktyKa8"}
results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok)))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))


def main():
    # 1. Keypair generation (offline ceremony)
    try:
        kp = generate_keypair()
        check("keypair generated", "private_key_pem" in kp and "public_key_pem" in kp)
        check("private key warning present", "Never give it to IAM" in kp["warning"])
    except Exception as e:
        check("keypair generation", False, str(e))

    # 2. Sign/verify round trip
    try:
        kp = generate_keypair()
        h = "abc123hash"
        sig = sign_challenge(kp["private_key_pem"], h, "approved")
        check("challenge signed", len(sig) > 20)
        check("valid signature verifies", verify_signature(kp["public_key_pem"], h, "approved", sig))
        check("wrong decision rejected", not verify_signature(kp["public_key_pem"], h, "rejected", sig))
        check("tampered hash rejected", not verify_signature(kp["public_key_pem"], "other", "approved", sig))
    except Exception as e:
        check("sign/verify", False, str(e))

    # 3. Ceremony documentation
    try:
        c = httpx.get(f"{BASE}/api/v1/creator/keys/ceremony", headers=H, timeout=10).json()
        check("ceremony documented", len(c.get("steps", [])) >= 6)
        check("no private key in runtime rule", "never" in c.get("rule", "").lower())
    except Exception as e:
        check("ceremony endpoint", False, str(e))

    # 4. Backend signer identity enforced (approval requires configured signer id + key)
    try:
        r = httpx.post(f"{BASE}/api/v1/creator/gateway/decision", json={}, timeout=10)
        check("unsigned gateway decision rejected", r.status_code in (400, 401, 403, 503))
    except Exception as e:
        check("gateway protection", False, str(e))

    print("\n=== Signer summary ===")
    passed = sum(1 for r in results if r[1])
    print(f"{passed}/{len(results)} passed")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
