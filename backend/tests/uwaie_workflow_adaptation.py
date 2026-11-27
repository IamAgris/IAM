"""Verify approved workflow reuse adapts selectors by accessible label.

Run inside the backend container: python tests/uwaie_workflow_adaptation.py
"""

import asyncio
import uuid

from app.core.database import get_session_factory
from app.models.uwaie import WebsiteWorkflow
from app.services.uwaie_service import UWAIEService


async def main() -> None:
    name = f"adaptive-{uuid.uuid4().hex[:8]}"
    url = "https://en.wikipedia.org/wiki/Main_Page"

    async with get_session_factory()() as db:
        workflow = WebsiteWorkflow(
            name=name,
            url_pattern="wikipedia.org",
            steps=[
                {"action": "navigate", "target": url},
                {"action": "type", "target": "[name=old_field]", "value": "<redacted>", "semantic": "Search Wikipedia"},
                {"action": "text", "target": "body"},
            ],
            verification={"expected_text": "Wikipedia"},
            source_actor="test",
            is_approved=True,
        )
        db.add(workflow)
        await db.commit()

        service = UWAIEService(db)
        session = await service.create_session("workflow adaptation test")
        result = await service.reuse_workflow(
            str(workflow.id), url, session["session_token"], "test"
        )
        print("verified:", result.get("verified"))
        print("adapted_steps:", result.get("adapted_steps"))
        print("reason:", result.get("verification_reason"))
        print("steps:", result.get("steps"))
        assert result.get("verified") is True
        assert result.get("adapted_steps", 0) >= 1
        print("PASS: workflow adapted to changed layout")


if __name__ == "__main__":
    asyncio.run(main())
