# iam-sdk (Python)

Official Python client for the IAM Core. See [../PROTOCOL.md](../PROTOCOL.md) and [IAM_DEVELOPER_SDK_AND_CLI_SPEC.md](../../IAM_DEVELOPER_SDK_AND_CLI_SPEC.md).

**Proposed PyPI name — not published.** Python 3.11+.

```bash
pip install iam-sdk
```

```python
import asyncio
from iam_sdk import IAM

async def main():
    iam = IAM(endpoint="https://core.example.com", token="YOUR_IAM_TOKEN")
    await iam.connect()
    status = await iam.core.status()
    task = await iam.tasks.submit(
        type="research", instruction="Research efficient ARM64 AI models"
    )
    print(status, task["id"])
    await iam.disconnect()

asyncio.run(main())
```

Same protocol and conceptual surface as `@iam/sdk`: `core`, `tasks`, `events`, `nodes`, `resources`, `files`, `knowledge`, `sync`, `diagnostics`, `creator`, `integrity`, `uwaie`, `public_records`, `legal`, `geo`, `human_presence`, `assistant_lab`, `free_sandbox`. Scoped bearer tokens, version negotiation, controlled retries, offline task queue with `tasks.flush_queue()`. No database access and no protected-core modification.

## Creator CLI (no email dependency)

The `creator` section is for the human Creator's tooling, not for IAM. It reads
pending requests and challenges from the Core API and submits locally signed
decisions:

```bash
export IAM_CORE_URL=https://core.example.com
export IAM_TOKEN=<creator-scoped-token>
# Only if the Core is behind Cloudflare Access:
export IAM_CF_ACCESS_CLIENT_ID=<access-service-token-id>
export IAM_CF_ACCESS_CLIENT_SECRET=<access-service-token-secret>

python -m iam_sdk.creator_cli pending
python -m iam_sdk.creator_cli show cr_...
python -m iam_sdk.creator_cli sign cr_... --approve \
  --signer "python /secure/path/sign_with_hardware_key.py"
```

The signer command must print a base64 ED25519 signature for exactly
`<challenge_hash>|<approved|rejected>` (it receives that string as its last
argument, or on stdin with `--signer-input stdin`). Use `--dry-run` to inspect
the signing message without submitting. `decide` submits a signature obtained
from a separate signer.

Email is optional notification only. Authority comes from the verified
signature over the one-time challenge (OD-03/OD-19), never from the channel.
