import os

import httpx

key = os.environ.get("IAM_API_KEY", "")
h = {"Authorization": f"Bearer {key}"}
base = "http://localhost:8000/api/v1/free-nodes"

good = {
    "provider": "google_cloud",
    "instance_class": "e2-micro",
    "architecture": "amd64",
    "region": "us-central1",
    "cpu_cores": 2,
    "ram_mb": 1024,
    "run_compatible": True,
    "operational_overhead": "low",
    "security_exposure": "low",
    "net_benefit": True,
    "expires_at": "2027-05-31T00:00:00+00:00",
}
r = httpx.post(base + "/", headers=h, json=good, timeout=15)
print("record_good", r.status_code, r.json().get("status"))
tid = r.json().get("id")

r2 = httpx.patch(base + f"/{tid}/status", headers=h, json={"status": "deployed"}, timeout=15)
print("deploy_without_verified_terms", r2.status_code)

r3 = httpx.post(
    base + f"/{tid}/verify-terms",
    headers=h,
    json={"source_url": "https://cloud.google.com/free", "evidence": "official free-tier page checked"},
    timeout=15,
)
print("verify_terms", r3.status_code, r3.json().get("eligibility_verified"))

r4 = httpx.patch(base + f"/{tid}/status", headers=h, json={"status": "deployed"}, timeout=15)
print("deploy_after_verification", r4.status_code)

r5 = httpx.post(
    base + f"/{tid}/migration-plan", headers=h, json={"days_before_expiry": 7}, timeout=15
)
print("migration_plan", r5.status_code, r5.json().get("status"))

r6 = httpx.get(base, headers=h, timeout=15)
print("list", r6.status_code, len(r6.json()))
