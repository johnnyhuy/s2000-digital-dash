"""Face style enum — layout only; protocol fields stay frozen."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from face_style import (  # noqa: E402
    DEFAULT_FACE_STYLE,
    FACE_STYLE_LABELS,
    FaceStyle,
    FaceStyleError,
    parse_face_style,
)
from gauge_ui import FACE, apply_face_style, build_face_geom, parse_args, tach_tick_poly  # noqa: E402
from protocol import REQUIRED_FIELDS  # noqa: E402


class ParseTests(unittest.TestCase):
    def test_default_is_ap1(self) -> None:
        self.assertEqual(DEFAULT_FACE_STYLE, FaceStyle.AP1)
        self.assertEqual(parse_face_style(None), FaceStyle.AP1)
        self.assertEqual(parse_face_style(""), FaceStyle.AP1)
        self.assertEqual(parse_face_style("AP2"), FaceStyle.AP2)

    def test_unknown_raises(self) -> None:
        with self.assertRaises(FaceStyleError):
            parse_face_style("ap3")

    def test_cli_style_flag(self) -> None:
        self.assertEqual(parse_args([]).style, "ap1")
        self.assertEqual(parse_args(["--style", "ap2"]).style, "ap2")


class GeomTests(unittest.TestCase):
    def tearDown(self) -> None:
        apply_face_style(FaceStyle.AP1)

    def test_default_face_is_ap1_lock(self) -> None:
        self.assertEqual(FACE.style, "ap1")
        # AP1: TEMP bar left of the speedo, FUEL bar right, both horizontal
        self.assertLess(FACE.temp[0], FACE.speed_c[0])
        self.assertLess(FACE.speed_c[0], FACE.fuel[0])
        self.assertGreater(FACE.temp[2], FACE.temp[3])
        self.assertGreater(FACE.fuel[2], FACE.fuel[3])
        self.assertLess(FACE.minus_btn[0] + FACE.minus_btn[2], FACE.plus_btn[0])

    def test_ap2_stacks_side_gauges_on_the_right(self) -> None:
        g = build_face_geom(style=FaceStyle.AP2)
        self.assertEqual(g.style, "ap2")
        self.assertLess(g.temp[1], g.fuel[1])
        self.assertGreater(g.temp[0], g.speed_c[0])
        self.assertGreater(g.fuel[0], g.speed_c[0])
        self.assertGreater(g.clock_c[1], g.speed_c[1])
        self.assertGreater(g.odo_c[1], g.clock_c[1])
        self.assertNotEqual(g.temp[1], FACE.temp[1])

    def test_tach_ticks_are_arc_normal_not_upright(self) -> None:
        end = tach_tick_poly(0.05, 4, 30)
        xs = [p[0] for p in end]
        # A slanted tick's top and bottom x should differ (not a vertical brick).
        self.assertGreater(max(xs) - min(xs), 6)

    def test_protocol_fields_unchanged(self) -> None:
        self.assertEqual(
            REQUIRED_FIELDS,
            ("rpm", "speed_kmh", "fuel_pct", "ect_c", "batt_v", "odo_km"),
        )
        self.assertIn(FaceStyle.AP1, FACE_STYLE_LABELS)
        self.assertIn(FaceStyle.AP2, FACE_STYLE_LABELS)


if __name__ == "__main__":
    unittest.main()
