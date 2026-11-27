"""Unit tests for Doc 17 / OD-33 tone and influence analysis (no DB required)."""

import unittest

from app.services.tone_service import ToneService

service = ToneService()


class ToneAnalysisTests(unittest.TestCase):
    def test_benign_positive_text(self):
        result = service.analyse_text("This is a great and helpful result. Thank you!")
        self.assertEqual(result["tone"], "positive")
        self.assertGreater(result["sentiment"], 0)
        self.assertIn("not psychological diagnoses", result["caveat"])

    def test_aggressive_language_is_hostile_with_signal(self):
        result = service.analyse_text("You are an idiot and a liar. That is pathetic.")
        self.assertEqual(result["tone"], "hostile")
        self.assertEqual(result["register"], "confrontational")
        interpretations = result["interpretations"]
        self.assertIn("Hostile or confrontational tone", interpretations)

    def test_fear_based_messaging_is_flagged(self):
        result = service.analyse_text("There is a crisis and a threat of disaster. Act now.")
        self.assertEqual(result["tone"], "fearful")
        self.assertIn("fear_based_messaging", result["manipulation_indicators"])
        self.assertIn("urgency_pressure", result["manipulation_indicators"])
        self.assertIn("Possible fear-based persuasion", result["interpretations"])

    def test_certainty_pressure_is_flagged(self):
        result = service.analyse_text("Obviously everyone knows this is a fact. No doubt about it.")
        self.assertIn("certainty_pressure", result["manipulation_indicators"])
        self.assertIn("Potential overconfidence or rhetorical pressure", result["interpretations"])

    def test_sarcasm_is_possible_not_certain(self):
        result = service.analyse_text("Great job on that. /s")
        self.assertEqual(result["tone"], "sarcastic")
        self.assertIn("Humour, criticism or indirect disagreement", result["interpretations"])

    def test_no_private_state_claim(self):
        result = service.analyse_text("I am worried this might fail.")
        self.assertIn("No claim is made about any person's private psychological state", result["note"])
        self.assertNotIn("you are", result["note"].lower())

    def test_confidence_bounded(self):
        for text in ("hello", "idiot threat crisis obviously /s", "thanks!"):
            confidence = service.analyse_text(text)["confidence"]
            self.assertGreaterEqual(confidence, 0.0)
            self.assertLessEqual(confidence, 1.0)


class DiscussionTests(unittest.TestCase):
    def test_style_shift_is_reported_as_possibility(self):
        result = service.analyse_discussion([
            "Thank you, this is very helpful.",
            "You are an idiot and a liar.",
        ])
        self.assertTrue(result["style_shifts"])
        shift = result["style_shifts"][0]
        self.assertEqual(shift["interpretation"], "Possible change in context or tone")
        self.assertEqual(shift["from"], "positive")
        self.assertEqual(shift["to"], "hostile")

    def test_stable_discussion_has_no_shift(self):
        result = service.analyse_discussion(["Great work!", "Excellent result, thanks!"])
        self.assertEqual(result["style_shifts"], [])


class StorageGuardTests(unittest.IsolatedAsyncioTestCase):
    async def test_recording_requires_database_session(self):
        with self.assertRaises(RuntimeError):
            await service.record_analysis("text", "sample")


if __name__ == "__main__":
    unittest.main()
