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

Same protocol and conceptual surface as `@iam/sdk`: `core`, `tasks`, `nodes`, `resources`, `files`, `knowledge`, `sync`, `diagnostics`. Scoped bearer tokens, version negotiation, controlled retries, offline task queue with `tasks.flush_queue()`. No database access and no protected-core modification.
