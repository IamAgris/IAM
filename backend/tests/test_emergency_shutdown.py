"""Repository-wide emergency stop: signed authority, durable state, enforcement."""

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.services.emergency_shutdown import (
    EmergencyShutdownService,
    emergency,
)
from app.services.model_inference import InferenceBlocked, inference_service


AUTH_ID = "22222222-2222-4222-8222-222222222222"
AUTHORIZED = {"authorized": True, "authorization_id": AUTH_ID}


class FakeResult:
    def __init__(self, value=None):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class FakeDB:
    def __init__(self, row=None):
        self.row = row
        self.added = []
        self.commits = 0

    async def execute(self, statement):
        return FakeResult(value=self.row)

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        self.commits += 1


def row():
    return SimpleNamespace(
        scope="global",
        halted=False,
        reason=None,
        actor=None,
        authorization_id=None,
        engaged_at=None,
        details={},
    )


class EmergencyShutdownTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        emergency.apply(halted=False, reason="", actor="", authorization_id="")

    def tearDown(self):
        emergency.apply(halted=False, reason="", actor="", authorization_id="")

    async def test_stop_requires_signed_creator_authorization(self):
        db = FakeDB(row())
        with patch(
            "app.services.creatorapproval_service.CreatorApprovalService.check_authorization",
            new_callable=AsyncMock,
            return_value={"authorized": False, "reason": "no active authorization"},
        ) as check:
            with self.assertRaisesRegex(PermissionError, "signed Creator authorization"):
                await EmergencyShutdownService(db).engage(reason="incident")
        check.assert_awaited_once()
        self.assertFalse(emergency.is_halted())

    async def test_rejects_unauthorized_supplied_proof_without_db_check(self):
        db = FakeDB(row())
        with patch(
            "app.services.creatorapproval_service.CreatorApprovalService.check_authorization",
            new_callable=AsyncMock,
        ) as check:
            with self.assertRaises(PermissionError):
                await EmergencyShutdownService(db).engage(
                    reason="incident",
                    authorization={"authorized": False},
                )
        check.assert_not_awaited()

    async def test_engage_halts_all_subsystems_and_audits(self):
        db = FakeDB(row())
        result = await EmergencyShutdownService(db).engage(
            reason="credential leak", actor="operator-1", authorization=AUTHORIZED
        )
        self.assertTrue(result["halted"])
        self.assertTrue(all(result["subsystems"].values()))
        self.assertEqual(result["authorization_id"], AUTH_ID)
        for subsystem in ("inference", "autonomy", "browser", "trading"):
            self.assertTrue(emergency.is_halted(subsystem))
        self.assertEqual(db.commits, 1)
        self.assertTrue(any(getattr(a, "event_type", "") == "emergency_stop_engaged" for a in db.added))

    async def test_resume_requires_separate_signed_authorization_and_clears_state(self):
        db = FakeDB(row())
        service = EmergencyShutdownService(db)
        await service.engage(reason="incident", authorization=AUTHORIZED)
        with patch(
            "app.services.creatorapproval_service.CreatorApprovalService.check_authorization",
            new_callable=AsyncMock,
            return_value={"authorized": False},
        ):
            with self.assertRaises(PermissionError):
                await service.resume(reason="resolved")
        self.assertTrue(emergency.is_halted())
        result = await service.resume(
            reason="resolved", actor="operator-2", authorization=AUTHORIZED
        )
        self.assertFalse(result["halted"])
        self.assertFalse(emergency.is_halted())
        self.assertTrue(any(getattr(a, "event_type", "") == "emergency_stop_resumed" for a in db.added))

    async def test_reason_is_required(self):
        db = FakeDB(row())
        with self.assertRaises(ValueError):
            await EmergencyShutdownService(db).engage(reason="  ", authorization=AUTHORIZED)

    async def test_chat_is_blocked_before_routing(self):
        emergency.apply(halted=True, reason="incident", actor="op", authorization_id=AUTH_ID)
        route = AsyncMock()
        with patch.object(inference_service, "_route", route):
            with self.assertRaisesRegex(InferenceBlocked, "emergency stop"):
                await inference_service.chat(
                    [{"role": "user", "content": "hello"}]
                )
        route.assert_not_awaited()

    async def test_stream_emits_emergency_halted_without_routing(self):
        emergency.apply(halted=True, reason="incident", actor="op", authorization_id=AUTH_ID)
        route = AsyncMock()
        with patch.object(inference_service, "_route", route):
            events = [
                event
                async for event in inference_service.stream(
                    [{"role": "user", "content": "hello"}]
                )
            ]
        self.assertEqual(events[0]["event"], "error")
        self.assertEqual(events[0]["data"]["code"], "emergency_halted")
        route.assert_not_awaited()

    async def test_browser_and_trading_guards_fail_closed(self):
        from app.services.browser_service import BrowserService
        from app.services.trading.paper import PaperTradingService, TradingDenied

        emergency.apply(halted=True, reason="incident", actor="op", authorization_id=AUTH_ID)

        browser = object.__new__(BrowserService)
        result = await browser.interact("click", "https://example.test")
        self.assertFalse(result["success"])
        self.assertIn("emergency stop", result["error"])

        with patch("app.services.trading.paper.settings.trading_simulation_enabled", True):
            with self.assertRaisesRegex(TradingDenied, "emergency stop"):
                await PaperTradingService(FakeDB()).place_order(
                    "portfolio-1", symbol="ABC", side="buy", quantity=1, price=1, actor="op"
                )


if __name__ == "__main__":
    unittest.main()
