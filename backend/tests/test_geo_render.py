"""Tests for provider-neutral backend map rendering."""

import unittest

from app.services.geo_service import GeoService


class RenderTests(unittest.TestCase):
    def test_svg_contains_markers(self):
        svg = GeoService.render_svg(
            [
                {"name": "Cape Town", "latitude": -33.9, "longitude": 18.4},
                {"name": "London", "latitude": 51.5, "longitude": -0.1},
            ]
        )
        self.assertTrue(svg.startswith("<svg"))
        self.assertIn("<circle", svg)
        self.assertIn("Cape Town", svg)
        self.assertIn("</svg>", svg)

    def test_labels_are_xml_escaped(self):
        svg = GeoService.render_svg(
            [{"name": "<script>alert(1)</script>", "latitude": 0, "longitude": 0}]
        )
        self.assertNotIn("<script>", svg)
        self.assertIn("&lt;script&gt;", svg)


if __name__ == "__main__":
    unittest.main()
