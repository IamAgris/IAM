"""Vision output must expose real objects/OCR instead of hard-coded empties."""

import unittest

from app.services.vision_service import VisionService


class VisionStructuredTests(unittest.TestCase):
    def test_json_response_yields_objects_and_ocr(self):
        description, objects, text, structured = VisionService._structured(
            '{"description":"a red sign","objects":["sign","wall"],"text_ocr":"EXIT"}'
        )
        self.assertEqual(description, "a red sign")
        self.assertEqual(objects, ["sign", "wall"])
        self.assertEqual(text, "EXIT")
        self.assertTrue(structured)

    def test_fenced_json_is_accepted(self):
        _d, objects, text, structured = VisionService._structured(
            '```json\n{"description":"desk","objects":["laptop"],"text_ocr":null}\n```'
        )
        self.assertEqual(objects, ["laptop"])
        self.assertIsNone(text)
        self.assertTrue(structured)

    def test_plain_description_falls_back_honestly(self):
        description, objects, text, structured = VisionService._structured(
            "A desk with a laptop"
        )
        self.assertEqual(description, "A desk with a laptop")
        self.assertEqual(objects, [])
        self.assertIsNone(text)
        self.assertFalse(structured)


if __name__ == "__main__":
    unittest.main()
