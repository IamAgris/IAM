"""Unit tests for Doc 19 / OD-35 free node usefulness gate (no DB required)."""

import unittest

from app.services.free_node_lifecycle import FreeNodeError, FreeNodeLifecycleService

service = FreeNodeLifecycleService(None)

GOOD = {
    "provider": "google_cloud",
    "architecture": "amd64",
    "cpu_cores": 2,
    "ram_mb": 1024,
    "run_compatible": True,
    "operational_overhead": "low",
    "security_exposure": "low",
    "net_benefit": True,
}


class UsefulnessGateTests(unittest.TestCase):
    def test_free_alone_is_declined(self):
        result = service.assess({"provider": "anywhere", "architecture": "amd64"})
        self.assertEqual(result["decision"], "decline")
        self.assertTrue(result["creator_authorisation_required"])
        self.assertTrue(result["reasons"])

    def test_all_checks_pass(self):
        result = service.assess(GOOD)
        self.assertEqual(result["decision"], "deploy")
        self.assertTrue(result["useful"])
        self.assertEqual(result["reasons"], [])

    def test_unknown_architecture_fails_compatibility(self):
        payload = dict(GOOD, architecture="mips")
        result = service.assess(payload)
        self.assertFalse(result["run_compatible"])
        self.assertEqual(result["decision"], "decline")

    def test_high_overhead_fails(self):
        result = service.assess(dict(GOOD, operational_overhead="high"))
        self.assertEqual(result["decision"], "decline")

    def test_no_net_benefit_fails(self):
        result = service.assess(dict(GOOD, net_benefit=False))
        self.assertEqual(result["decision"], "decline")


class TimestampTests(unittest.TestCase):
    def test_iso_string_parsed(self):
        parsed = service._parse_dt("2027-05-31T00:00:00+00:00")
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.year, 2027)

    def test_invalid_timestamp_rejected(self):
        with self.assertRaises(FreeNodeError):
            service._parse_dt("not-a-date")


class InputTests(unittest.IsolatedAsyncioTestCase):
    async def test_provider_required(self):
        with self.assertRaises(FreeNodeError):
            await service.record_candidate({"architecture": "amd64"})

    async def test_invalid_architecture(self):
        with self.assertRaises(FreeNodeError):
            await service.record_candidate({"provider": "x", "architecture": "sparc"})


if __name__ == "__main__":
    unittest.main()
