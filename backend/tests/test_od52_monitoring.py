"""OD-52 Phases D/E: availability classification and capability assignment."""

import unittest
import uuid
from unittest.mock import patch

from app.models.modelrouter import DiscoveredModel
from app.services.capability_evaluator import CapabilityEvaluator
from app.services.endpoint_availability import (
    AvailabilityResult,
    EndpointAvailabilityMonitor,
    classify,
)


class FakeResult:
    def __init__(self, rows):
        self.rows = list(rows)

    def scalars(self):
        return self

    def all(self):
        return self.rows

    def scalar_one_or_none(self):
        return self.rows[0] if self.rows else None


class FakeDB:
    def __init__(self, rows=None):
        self.rows = list(rows or [])

    async def execute(self, statement):
        name = ""
        try:
            froms = list(statement.froms)
            name = getattr(froms[0], "name", "") if froms else ""
        except Exception:
            name = str(statement)
        return FakeResult(
            [r for r in self.rows if getattr(r.__class__, "__tablename__", "") in name]
        )

    def add(self, obj):
        self.rows.append(obj)

    async def flush(self):
        return None

    async def commit(self):
        return None


class FakeResponse:
    def __init__(self, status_code):
        self.status_code = status_code


class FakeClient:
    calls = []

    def __init__(self, codes):
        self.codes = list(codes)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def post(self, url, headers=None, json=None):
        FakeClient.calls.append({"url": url, "json": json})
        return FakeResponse(self.codes.pop(0))


def _row(alias, model_id, capabilities=None, access="free", status="available"):
    return DiscoveredModel(
        id=uuid.uuid4(),
        provider_id=uuid.uuid4(),
        model_id=model_id,
        display_name=model_id,
        alias=alias,
        capabilities=capabilities or [],
        access_type=access,
        endpoint_status=status,
    )


class AvailabilityTests(unittest.IsolatedAsyncioTestCase):
    def test_classification(self):
        self.assertEqual(classify(200).status, "available")
        self.assertEqual(classify(401).status, "auth")
        self.assertEqual(classify(429).status, "rate_limit")
        self.assertEqual(classify(410).status, "model_outage")
        self.assertEqual(classify(503).status, "model_outage")

    async def test_disabled_monitor_makes_no_call(self):
        with patch("app.services.endpoint_availability.httpx.AsyncClient") as client:
            result = await EndpointAvailabilityMonitor(FakeDB()).monitor_all()
        self.assertEqual(result, [])
        client.assert_not_called()

    async def test_probe_marks_status_and_never_probes_paid(self):
        FakeClient.calls = []
        db = FakeDB([
            _row("nv-free", "nvidia/free"),
            _row(None, "nvidia/paid", access="paid"),
        ])
        with patch("app.services.endpoint_availability.settings.endpoint_availability_enabled", True), \
             patch("app.services.endpoint_availability.httpx.AsyncClient",
                   side_effect=lambda *a, **k: FakeClient([429])):
            outcomes = await EndpointAvailabilityMonitor(db).monitor_all()
        self.assertEqual(len(outcomes), 1)
        self.assertEqual(outcomes[0]["status"], "rate_limit")
        self.assertEqual(db.rows[0].endpoint_status, "unavailable")
        self.assertEqual(db.rows[0].test_result["status"], "rate_limit")
        self.assertEqual(len(FakeClient.calls), 1)

    async def test_success_updates_last_known_good(self):
        db = FakeDB([_row("nv-free", "nvidia/free")])
        with patch("app.services.endpoint_availability.settings.endpoint_availability_enabled", True), \
             patch("app.services.endpoint_availability.httpx.AsyncClient",
                   side_effect=lambda *a, **k: FakeClient([200])):
            await EndpointAvailabilityMonitor(db).monitor_all()
        self.assertEqual(db.rows[0].endpoint_status, "available")
        self.assertEqual(db.rows[0].last_known_good["alias"], "nv-free")


class CapabilityAssignmentTests(unittest.IsolatedAsyncioTestCase):
    async def test_assigns_by_capability_and_excludes_unavailable(self):
        db = FakeDB([
            _row("nv-code", "nvidia/code", capabilities=["coding"], status="available"),
            _row("nv-reason", "nvidia/reason", capabilities=["reasoning"], status="available"),
            _row("nv-offline", "nvidia/offline", capabilities=["coding"], status="unavailable"),
            _row("nv-paid", "nvidia/paid", capabilities=["coding"], access="paid"),
        ])
        row = _row("nv-tool", "nvidia/tool", capabilities=["coding"])
        row.tool_calling = True
        db.rows.append(row)
        selected = await CapabilityEvaluator(db).select_for_role("coding")
        self.assertEqual(selected, "nv-tool")

    async def test_no_eligible_model_fails_closed(self):
        db = FakeDB([_row("nv-offline", "nvidia/offline", status="unavailable")])
        self.assertIsNone(await CapabilityEvaluator(db).select_for_role("research"))


if __name__ == "__main__":
    unittest.main()
