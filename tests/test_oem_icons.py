"""OEM telltale colours, strip order, and committed icon assets."""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from oem_icons import (  # noqa: E402
    ASSETS,
    ICON_KINDS,
    LAMP_AMBER,
    LAMP_BLUE,
    LAMP_GHOST,
    LAMP_GREEN,
    LAMP_RED,
    LAMPS,
    is_neon_cyan,
    lamp_color_for,
    lamp_states,
    lamp_strip_inner_width,
)
from protocol import LAMP_KEYS, REQUIRED_FIELDS  # noqa: E402


class ColourTests(unittest.TestCase):
    def test_oem_colour_map(self) -> None:
        red = {
            "brake",
            "battery",
            "oil",
            "door",
            "seatbelt",
            "srs",
        }
        amber = {"abs", "cel", "maint", "eps"}
        green = {"immobilizer", "turn_l", "turn_r"}
        for kind in red:
            self.assertEqual(lamp_color_for(kind), LAMP_RED)
        for kind in amber:
            self.assertEqual(lamp_color_for(kind), LAMP_AMBER)
        for kind in green:
            self.assertEqual(lamp_color_for(kind), LAMP_GREEN)
        self.assertEqual(lamp_color_for("high_beam"), LAMP_BLUE)

    def test_ghost_lamps_are_near_black(self) -> None:
        self.assertLess(max(LAMP_GHOST), 50)
        self.assertGreater(min(LAMP_GHOST), 20)

    def test_high_beam_is_blue_not_cyan(self) -> None:
        r, g, b = LAMP_BLUE
        self.assertGreater(b, r)
        self.assertGreater(b, g)
        self.assertFalse(is_neon_cyan(LAMP_BLUE))
        self.assertTrue(is_neon_cyan((72, 210, 230)))

    def test_no_neon_cyan_on_the_strip(self) -> None:
        for lamp in LAMPS:
            self.assertFalse(is_neon_cyan(lamp.color), lamp.kind)


class StripTests(unittest.TestCase):
    def test_self_test_order(self) -> None:
        self.assertEqual(
            [lamp.kind for lamp in LAMPS],
            [
                "turn_l",
                "high_beam",
                "abs",
                "brake",
                "battery",
                "oil",
                "cel",
                "immobilizer",
                "maint",
                "eps",
                "seatbelt",
                "door",
                "srs",
                "turn_r",
            ],
        )

    def test_bulb_check_lights_every_telltale(self) -> None:
        states = lamp_states({}, bulb_check=True)
        self.assertTrue(all(item.lit for item in states))
        self.assertEqual(len(states), 14)

    def test_battery_derives_from_low_voltage(self) -> None:
        states = {item.kind: item.lit for item in lamp_states({}, batt_low=True)}
        self.assertTrue(states["battery"])
        self.assertFalse(states["oil"])

    def test_oem_extra_keys_light_their_slots(self) -> None:
        flags = {
            "brake": True,
            "door": True,
            "srs": True,
            "maint": True,
            "eps": True,
            "seatbelt": True,
            "immobilizer": True,
        }
        states = {item.kind: item.lit for item in lamp_states(flags)}
        for kind in flags:
            self.assertTrue(states[kind], kind)
        self.assertFalse(states["oil"])
        self.assertFalse(states["high_beam"])

    def test_strip_is_dense(self) -> None:
        self.assertGreater(lamp_strip_inner_width(), 500)
        self.assertLess(lamp_strip_inner_width(), 800)


class AssetTests(unittest.TestCase):
    def test_svg_and_png_exist(self) -> None:
        missing = []
        for kind in ICON_KINDS:
            for ext in (".svg", ".png"):
                path = ASSETS / f"{kind}{ext}"
                if not path.is_file() or path.stat().st_size < 40:
                    missing.append(str(path))
        self.assertEqual(missing, [])
        self.assertTrue((ASSETS / "atlas.svg").is_file())

    def test_pictograms_keep_iso_cutouts(self) -> None:
        battery = (ASSETS / "battery.svg").read_text(encoding="utf-8")
        oil = (ASSETS / "oil.svg").read_text(encoding="utf-8")
        beam = (ASSETS / "high_beam.svg").read_text(encoding="utf-8")
        belt = (ASSETS / "seatbelt.svg").read_text(encoding="utf-8")
        cel = (ASSETS / "cel.svg").read_text(encoding="utf-8")
        self.assertIn("evenodd", battery)
        self.assertIn('fill="none"', oil)  # outlined oil can has a transparent interior
        self.assertIn("evenodd", beam)
        self.assertIn("evenodd", belt)
        self.assertIn("evenodd", cel)
        self.assertIn('stroke="#fff"', oil)
        self.assertEqual(beam.count("<rect"), 3)
        self.assertIn("16.2 22.2", cel)
        self.assertIn("<circle", belt)
        self.assertIn("21.6 15.4", belt)
        self.assertIn("h-8.8", belt)
        key = (ASSETS / "immobilizer.svg").read_text(encoding="utf-8")
        door = (ASSETS / "door.svg").read_text(encoding="utf-8")
        self.assertIn("evenodd", key)
        self.assertIn("16.6", key)
        self.assertIn("2.8 28.6", door)

    def test_protocol_field_names_unchanged(self) -> None:
        self.assertEqual(
            REQUIRED_FIELDS,
            ("rpm", "speed_kmh", "fuel_pct", "ect_c", "batt_v", "odo_km"),
        )
        self.assertEqual(
            LAMP_KEYS,
            (
                "oil",
                "cel",
                "abs",
                "turn_l",
                "turn_r",
                "high_beam",
                "fog",
                "fuel_low",
                "batt_warn",
                "ect_hot",
            ),
        )


class RenderTests(unittest.TestCase):
    def test_icon_surfaces_are_tinted(self) -> None:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
        import pygame

        from oem_icons import icon_surface

        pygame.init()
        pygame.display.set_mode((64, 64))
        red = icon_surface(pygame, "oil", LAMP_RED, 32)
        blue = icon_surface(pygame, "high_beam", LAMP_BLUE, 32)
        self.assertGreater(red.get_width(), 8)
        self.assertGreater(blue.get_width(), 8)
        # Sample a non-transparent pixel — oil should lean red, high beam blue
        def peak_channel(surf) -> tuple[int, int, int]:
            best = (0, 0, 0, 0)
            w, h = surf.get_size()
            for x in range(0, w, 2):
                for y in range(0, h, 2):
                    px = surf.get_at((x, y))
                    if px.a > best[3]:
                        best = (px.r, px.g, px.b, px.a)
            return best[:3]

        rr, rg, rb = peak_channel(red)
        br, bg, bb = peak_channel(blue)
        self.assertGreater(rr, rb)
        self.assertGreater(bb, br)
        pygame.quit()


if __name__ == "__main__":
    unittest.main()
