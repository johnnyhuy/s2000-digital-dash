"""OEM cluster helpers — flags, lerp, intro phases, smoke path."""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "src"))
sys.path.insert(0, str(_ROOT / "tests"))

from gauge_ui import (  # noqa: E402
    ARCH_RISE_PCT,
    BAR_H_PCT,
    FACE,
    MODULE_ASPECT,
    NOTCH_BOT_PCT,
    NOTCH_TOP_PCT,
    REDLINE_BLOCKS,
    TACH_BAND_OUTER,
    TACH_NEEDLE_TAIL,
TACH_NUM_X_INSET,
    TACH_NUM_DROP_BASE,
    TACH_NUM_DROP_PEAK,
    TACH_TICK_MAJOR,
    TEMP_SEGS,
    TEMP_W_PCT,
    tach_arch_normal,
    tach_arch_xy,
    tach_band_poly,
    tach_num_xy,
    visor_lip_points,
    DisplayState,
    PHASE_READY_S,
    PHASE_REVEAL_S,
    PHASE_SWEEP_S,
    RPM_REDLINE,
    SMOKE_PHASES,
    SerialSource,
    StdinSource,
    boot_strip_mode,
    draw_frame,
    ect_frac,
    exp_smooth,
    fuel_frac,
    hood_bottom_corners,
    intro_duration_s,
    intro_phase_at,
    lerp,
    parse_args,
    smoothstep,
    reveal_rpm,
    sample_telem,
)
from protocol import REQUIRED_FIELDS, parse_line  # noqa: E402


class FlagTests(unittest.TestCase):
    def test_smoke_defaults_skip_intro(self) -> None:
        args = parse_args(["--smoke"])
        self.assertTrue(args.smoke)
        self.assertFalse(args.intro)

    def test_intro_and_no_intro(self) -> None:
        self.assertTrue(parse_args(["--intro"]).intro)
        self.assertFalse(parse_args(["--no-intro"]).intro)

    def test_screenshot_and_windowed_and_serial(self) -> None:
        args = parse_args(["--windowed", "--screenshot", "shots", "--serial"])
        self.assertTrue(args.windowed)
        self.assertEqual(args.screenshot, "shots")
        self.assertEqual(args.serial, "/dev/ttyUSB0")

    def test_style_defaults_to_ap1(self) -> None:
        self.assertEqual(parse_args([]).style, "ap1")
        self.assertEqual(parse_args(["--style", "ap2"]).style, "ap2")


class IntroTests(unittest.TestCase):
    def test_phase_order(self) -> None:
        self.assertEqual(intro_phase_at(0.0)[0], "sweep")
        self.assertEqual(intro_phase_at(PHASE_SWEEP_S + 0.01)[0], "ready")
        self.assertEqual(
            intro_phase_at(PHASE_SWEEP_S + PHASE_READY_S + 0.01)[0], "reveal"
        )
        self.assertEqual(intro_phase_at(intro_duration_s() + 0.2)[0], "live")

    def test_reveal_rpm_hits_redline_then_settles(self) -> None:
        self.assertAlmostEqual(reveal_rpm(0.0, 2000), 0.0)
        self.assertGreater(reveal_rpm(0.3, 2000), 3000)
        self.assertGreater(reveal_rpm(0.55, 2000), float(RPM_REDLINE))
        self.assertAlmostEqual(reveal_rpm(1.0, 2000), 2000.0)

    def test_boot_hides_lamps_until_reveal(self) -> None:
        lamps, bulb = boot_strip_mode("sweep", 0.5)
        self.assertEqual(lamps, {})
        self.assertFalse(bulb)
        lamps, bulb = boot_strip_mode("ready", 0.5)
        self.assertEqual(lamps, {})
        self.assertFalse(bulb)
        lamps, bulb = boot_strip_mode("reveal", 0.4)
        self.assertIsNone(lamps)
        self.assertTrue(bulb)
        lamps, bulb = boot_strip_mode("live", 1.0)
        self.assertIsNone(lamps)
        self.assertFalse(bulb)


class LerpTests(unittest.TestCase):
    def test_exp_smooth_approaches_target(self) -> None:
        v = 0.0
        for _ in range(40):
            v = exp_smooth(v, 100.0, 0.016, 0.08)
        self.assertGreater(v, 95.0)

    def test_lerp_midpoint(self) -> None:
        self.assertAlmostEqual(lerp(0.0, 10.0, 0.5), 5.0)

    def test_smoothstep_ends(self) -> None:
        self.assertAlmostEqual(smoothstep(0.0), 0.0)
        self.assertAlmostEqual(smoothstep(1.0), 1.0)
        self.assertGreater(smoothstep(0.5), 0.49)
        self.assertLess(smoothstep(0.25), 0.25)

    def test_fracs(self) -> None:
        self.assertEqual(ect_frac(40.0), 0.0)
        self.assertEqual(ect_frac(105.0), 1.0)
        self.assertEqual(fuel_frac(50.0), 0.5)
        self.assertEqual(fuel_frac(140.0), 1.0)


class DisplayStateTests(unittest.TestCase):
    def test_sample_keeps_protocol_fields(self) -> None:
        telem = sample_telem()
        parsed = parse_line(telem.to_line())
        for key in REQUIRED_FIELDS:
            self.assertIn(key, parsed.to_dict())

    def test_follow_snaps_lamps_and_tracks_trip(self) -> None:
        face = DisplayState()
        telem = sample_telem()
        face.snap(telem)
        face.trip_origin = telem.odo_km - 12.5
        face.follow(telem, 0.016)
        self.assertTrue(face.lamps["turn_l"])
        self.assertAlmostEqual(face.trip_km, 12.5, places=1)


class SmokeTests(unittest.TestCase):
    def test_smoke_writes_named_shots(self) -> None:
        from gauge_ui import main

        with tempfile.TemporaryDirectory() as tmp:
            main(["--smoke", "--screenshot", tmp])
            self.assertEqual(
                sorted(os.listdir(tmp)),
                [
                    "01_sweep.png",
                    "02_ready.png",
                    "03_reveal.png",
                    "04_live.png",
                    "05_cruise.png",
                ],
            )

    def test_smoke_walks_intro_phases(self) -> None:
        self.assertEqual(
            [name for name, _ in SMOKE_PHASES],
            ["sweep", "ready", "reveal", "live"],
        )


class FaceGeomTests(unittest.TestCase):
    def test_temp_and_fuel_are_horizontal_flanking_bars(self) -> None:
        tx, ty, tw, th = FACE.temp
        fx, fy, fw, fh = FACE.fuel
        self.assertEqual(ty, fy)
        self.assertEqual(th, fh)
        self.assertGreater(tw, th * 6)
        self.assertGreater(fw, fh * 6)
        self.assertLess(tx + tw, FACE.speed_c[0])
        self.assertGreater(fx, FACE.speed_c[0])
        # Flank the speedo at speed-y (OEM puts the bars level with the speed digits).
        self.assertLess(abs(ty - FACE.speed_c[1]), 4)
        self.assertLess(th, 16)

    def test_tach_numerals_sit_inside_the_well(self) -> None:
        nx, ny = tach_arch_normal(0.5)
        self.assertGreater(ny, 0.5)
        ax, ay = tach_arch_xy(0.5)
        px, py = tach_num_xy(0.5)
        self.assertGreater(py, ay)
        # Horizontal inset is a constant along the inward normal — numerals
        # sit slightly inside the band's x range at the corners.
        self.assertLess(abs(px - ax), TACH_NUM_X_INSET + 4)
        # Numerals sit at TACH_NUM_DROP_BASE + end² × (peak − base) below the band.
        self.assertAlmostEqual(TACH_NUM_DROP_BASE, 15.0, delta=1.0)
        self.assertGreater(TACH_NUM_DROP_BASE + TACH_NUM_DROP_PEAK, TACH_BAND_OUTER)
        self.assertGreater(TACH_NUM_X_INSET, TACH_TICK_MAJOR[1] + 16)
        # Chevron sits on the printed band, not a dart hanging into the well
        self.assertLess(TACH_NEEDLE_TAIL, TACH_BAND_OUTER)
        left = tach_num_xy(0.0)
        left_arch = tach_arch_xy(0.0)
        self.assertGreater(left[1], left_arch[1])
        self.assertGreater(tach_num_xy(1.0)[1], tach_arch_xy(1.0)[1])

    def test_tach_numeral_drop_matches_oem(self) -> None:
        """OEM Car Spy: numerals 0/9 just clear the band ends, middle numerals
        drop deep into the well. Vertical drop varies with `1 − end²`.
        """
        my, mh = FACE.module[1], FACE.module[3]
        _, y_end = tach_arch_xy(0.0)
        _, y_peak = tach_arch_xy(0.5)
        # 0/9 drop ~15 px (UI scale, OEM ~3% mh)
        drop_end = tach_num_xy(0.0)[1] - y_end
        self.assertAlmostEqual(drop_end, TACH_NUM_DROP_BASE, delta=2.0)
        drop_end_pct = drop_end / mh
        self.assertLess(drop_end_pct, 0.04)
        # Middle numerals drop ~200 px (UI scale, OEM ~28% mh)
        drop_mid = tach_num_xy(0.5)[1] - y_peak
        self.assertAlmostEqual(drop_mid, TACH_NUM_DROP_BASE + TACH_NUM_DROP_PEAK, delta=4.0)
        drop_mid_pct = drop_mid / mh
        self.assertGreater(drop_mid_pct, 0.20)
        self.assertLess(drop_mid_pct, 0.32)
        # And 0/9 always drop LESS than the middle numerals (formula inverted
        # from the previous `end² × extra` shape).
        self.assertLess(drop_end, drop_mid)

    def test_band_peak_locks_to_oem(self) -> None:
        """OEM Car Spy photo: band peak (printed amber arch top) at ~10.4% mh."""
        my, mh = FACE.module[1], FACE.module[3]
        _, y_peak = tach_arch_xy(0.5)
        peak_pct = (y_peak - my) / mh
        self.assertAlmostEqual(peak_pct, 0.104, delta=0.015)

    def test_visor_lip_hugs_the_printed_tach(self) -> None:
        ax, ay = tach_arch_xy(0.5)
        pts = visor_lip_points()
        self.assertGreater(len(pts), 20)
        mid = pts[len(pts) // 2]
        self.assertLess(mid[1], ay)
        self.assertLess(abs(mid[0] - ax), 24)
        self.assertLess(ay - mid[1], 10)

    def test_module_is_flat_bottom_and_stepped(self) -> None:
        bl, br = hood_bottom_corners(FACE)
        self.assertEqual(bl[1], br[1])
        self.assertGreater(FACE.step, 0)
        self.assertGreater(FACE.lcd[0], FACE.module[0])
        self.assertLess(FACE.lcd[0] + FACE.lcd[2], FACE.module[0] + FACE.module[2])

    def test_bezel_sits_below_lcd(self) -> None:
        lcd_bottom = FACE.lcd[1] + FACE.lcd[3]
        self.assertGreaterEqual(FACE.bezel[1], lcd_bottom)

    def test_module_aspect_is_locked(self) -> None:
        self.assertAlmostEqual(MODULE_ASPECT, 2.35, places=2)
        mw, mh = FACE.module[2], FACE.module[3]
        self.assertAlmostEqual(mw / mh, 2.35, delta=0.05)

    def test_lcd_is_wide_and_short(self) -> None:
        aspect = FACE.lcd[2] / FACE.lcd[3]
        self.assertGreater(aspect, 2.8)
        self.assertLess(aspect, 4.2)

    def test_locked_flanking_gauges_and_speed_percentages(self) -> None:
        mx, my, mw, mh = FACE.module
        self.assertAlmostEqual((FACE.temp[0] - mx) / mw, 0.080, delta=0.015)
        # OEM puts the speed/odo LCD cluster *under* the printed band, so the
        # TEMP / FUEL bars sit at the same y as the speedo centre (~68% mh).
        self.assertAlmostEqual((FACE.temp[1] - my) / mh, 0.680, delta=0.02)
        self.assertAlmostEqual(FACE.temp[3] / mh, BAR_H_PCT, delta=0.01)
        self.assertAlmostEqual(FACE.temp[2] / mw, TEMP_W_PCT, delta=0.015)
        self.assertAlmostEqual((FACE.fuel[0] - mx) / mw, 0.760, delta=0.015)
        self.assertAlmostEqual((FACE.fuel[1] - my) / mh, 0.680, delta=0.02)
        self.assertAlmostEqual((FACE.speed_c[0] - mx) / mw, 0.50, delta=0.01)
        self.assertAlmostEqual((FACE.speed_c[1] - my) / mh, 0.680, delta=0.02)
        # ODO row sits just under the speedo, just above the lamp strip top.
        self.assertAlmostEqual((FACE.odo_c[1] - my) / mh, 0.74, delta=0.02)
        self.assertAlmostEqual((FACE.bezel[1] - my) / mh, 0.805, delta=0.02)

    def test_five_redline_blocks(self) -> None:
        self.assertEqual(REDLINE_BLOCKS, 5)

    def test_six_oem_temp_bars(self) -> None:
        self.assertEqual(TEMP_SEGS, 6)

    def test_tach_band_is_a_closed_polygon(self) -> None:
        pts = tach_band_poly(0.0, 0.5, 1.0, 16)
        self.assertGreater(len(pts), 16)
        xs = [p[0] for p in pts]
        self.assertLess(min(xs), max(xs))

    def test_tach_arch_is_parabola_not_a_drop(self) -> None:
        x0, y0 = tach_arch_xy(0.0)
        x1, y1 = tach_arch_xy(0.5)
        x2, y2 = tach_arch_xy(1.0)
        self.assertLess(x0, x1)
        self.assertLess(x1, x2)
        self.assertLess(y1, y0)
        self.assertLess(y1, y2)

    def test_notch_and_arch_lock(self) -> None:
        mx, my, mw, mh = FACE.module
        self.assertAlmostEqual(NOTCH_TOP_PCT, 0.58)
        self.assertAlmostEqual(NOTCH_BOT_PCT, 0.72)
        self.assertAlmostEqual(ARCH_RISE_PCT, 0.60, delta=0.005)
        self.assertAlmostEqual((FACE.notch_top_y - my) / mh, 0.58, delta=0.015)
        self.assertAlmostEqual((FACE.notch_bot_y - my) / mh, 0.72, delta=0.015)
        self.assertAlmostEqual((FACE.spring_y - my) / mh, 0.60, delta=0.02)
        self.assertEqual(FACE.hood_peak_y, my)

    def test_band_rise_lands_on_oem(self) -> None:
        """OEM band ends sit at ~56% of module height (DIMENSIONS.md lock)."""
        my, mh = FACE.module[1], FACE.module[3]
        x0, y0 = tach_arch_xy(0.0)
        x1, y1 = tach_arch_xy(1.0)
        ends_pct = (y0 - my) / mh
        self.assertAlmostEqual(ends_pct, 0.56, delta=0.02)

    def test_numeral_sits_below_band_end(self) -> None:
        """Numerals 0/9 drop below the band ends into the well (OEM lock)."""
        my, mh = FACE.module[1], FACE.module[3]
        _, y_band = tach_arch_xy(0.0)
        _, y_num = tach_num_xy(0.0)
        # Numerals always sit below the band (inset along inward normal plus extra end² drop).
        self.assertGreater(y_num, y_band)
        # And the drop stays bounded — well clear of the speedo centre at 68%.
        drop_pct = (y_num - my) / mh
        self.assertLess(drop_pct, 0.70)

    def test_lcd_cluster_locks_to_oem_below_band(self) -> None:
        """OEM Car Spy photo: speed/odo sit BELOW the band ends (~56% mh).

        The speed centre should be ~68% of mh, the odo row just under it at
        ~74%, and the TEMP/FUEL bars at the same y as the speedo centre.
        """
        my, mh = FACE.module[1], FACE.module[3]
        self.assertAlmostEqual((FACE.speed_c[1] - my) / mh, 0.68, delta=0.02)
        self.assertAlmostEqual((FACE.odo_c[1] - my) / mh, 0.74, delta=0.02)
        self.assertAlmostEqual((FACE.temp[1] - my) / mh, 0.68, delta=0.02)
        self.assertAlmostEqual((FACE.fuel[1] - my) / mh, 0.68, delta=0.02)
        # Odo row sits BELOW the speedo (no overlap with the speed window).
        self.assertGreater(FACE.odo_c[1], FACE.speed_c[1])
        # Speedo sits BELOW the band ends (OEM puts speed under the printed band).
        x_end, y_end = tach_arch_xy(0.0)
        self.assertGreater(FACE.speed_c[1], y_end)

    def test_speed_sits_below_tach_numerals(self) -> None:
        """OEM photo: speed/odo sit below the 0/9 numerals, not above them."""
        my, mh = FACE.module[1], FACE.module[3]
        _, y_num = tach_num_xy(0.0)
        # Numeral 0 sits at ~59% mh in OEM; speed sits at ~68% mh — clearly below.
        self.assertGreater(FACE.speed_c[1], y_num)


class HeadlessDrawTests(unittest.TestCase):
    """Dummy SDL: boot intro → reveal → live, plus OEM lamp colours."""

    @classmethod
    def setUpClass(cls) -> None:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
        from _headless import count_warm, init_cluster, sample_near

        cls.pygame, cls.screen, cls.fonts = init_cluster()
        cls.sample_near = staticmethod(sample_near)
        cls.count_warm = staticmethod(count_warm)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.pygame.quit()

    def _draw(self, face: DisplayState, phase: str, local_t: float):
        self.screen.fill((0, 0, 0))
        draw_frame(self.pygame, self.fonts, self.screen, face, phase, local_t)
        return self.screen.copy()

    def test_intro_phases_paint_the_lcd(self) -> None:
        from gauge_ui import AMBER

        face = DisplayState()
        face.snap(sample_telem())
        blobs = []
        for phase, local_t in SMOKE_PHASES:
            frame = self._draw(face, phase, local_t)
            warm = self.count_warm(frame, step=12)
            self.assertGreater(warm, 20, f"{phase} should show amber LCD (got {warm})")
            if phase in ("ready", "live"):
                self.assertGreater(
                    self.sample_near(frame, AMBER, step=12, tol=48),
                    8,
                    f"{phase} should hit bright amber",
                )
            blobs.append(self.pygame.image.tobytes(frame, "RGB"))
        self.assertNotEqual(blobs[0], blobs[1], "sweep and ready must differ")
        self.assertNotEqual(blobs[1], blobs[3], "ready and live must differ")

    def test_lamp_strip_uses_oem_colours_not_cyan(self) -> None:
        from oem_icons import LAMP_AMBER, LAMP_BLUE, LAMP_GREEN, LAMP_RED, NEON_CYAN
        from _headless import region

        from mocks.esp32_uart import warn_frame

        face = DisplayState()
        face.snap(warn_frame())
        frame = self._draw(face, "live", 1.0)
        strip = region(frame, FACE.lamp_band)
        self.assertGreater(self.sample_near(strip, LAMP_RED, step=2, tol=40), 0)
        self.assertGreater(self.sample_near(strip, LAMP_AMBER, step=2, tol=40), 0)
        self.assertGreater(self.sample_near(strip, LAMP_GREEN, step=2, tol=40), 0)
        self.assertGreater(self.sample_near(strip, LAMP_BLUE, step=2, tol=40), 0)
        self.assertEqual(self.sample_near(strip, NEON_CYAN, step=2, tol=20), 0)

    def test_reveal_bulb_check_lights_the_strip(self) -> None:
        from gauge_ui import draw_hardware_strip
        from oem_icons import LAMP_RED

        face = DisplayState()
        face.snap(sample_telem())
        self.assertFalse(face.lamps.get("oil"))
        canvas = self.pygame.Surface(self.screen.get_size())
        canvas.fill((8, 8, 9))
        draw_hardware_strip(self.pygame, self.fonts, canvas, face, bulb_check=True)
        strip = canvas.subsurface(FACE.lamp_band)
        self.assertGreater(self.sample_near(strip, LAMP_RED, step=2, tol=40), 0)
        reveal = self._draw(face, "reveal", 0.40)
        self.assertGreater(self.count_warm(reveal, step=12), 20)

    def test_sweep_does_not_show_live_high_beam(self) -> None:
        from oem_icons import LAMP_BLUE
        from _headless import region

        face = DisplayState()
        face.snap(sample_telem())
        self.assertTrue(face.lamps.get("high_beam"))
        sweep = self._draw(face, "sweep", 0.55)
        strip = region(sweep, FACE.lamp_band)
        self.assertEqual(self.sample_near(strip, LAMP_BLUE, step=2, tol=40), 0)

    def test_live_speedo_is_red_lcd(self) -> None:
        from gauge_ui import RED_LCD
        from _headless import region

        face = DisplayState()
        face.snap(sample_telem())
        frame = self._draw(face, "live", 1.0)
        cx, cy = FACE.speed_c
        well = region(frame, (cx - 140, cy - 70, 280, 140))
        self.assertGreater(self.sample_near(well, RED_LCD, step=3, tol=48), 8)
        self.assertEqual(self.sample_near(well, (236, 152, 32), step=3, tol=28), 0)

    def test_bundled_cluster_fonts_render(self) -> None:
        from gauge_ui import _FONTS

        self.assertTrue((_FONTS / "Oxanium-Bold.ttf").is_file())
        self.assertTrue((_FONTS / "BarlowCondensed-SemiBoldItalic.ttf").is_file())
        img = self.fonts["ready"].render("READY", True, (232, 148, 28))
        self.assertGreater(img.get_width(), 80)


class SourceTests(unittest.TestCase):
    def test_stdin_pipe_keeps_latest_frame(self) -> None:
        r, w = os.pipe()
        first = sample_telem()
        first.rpm = 2000
        second = sample_telem()
        second.rpm = 7100
        os.write(w, first.to_line().encode("utf-8"))
        os.write(w, second.to_line().encode("utf-8"))
        os.close(w)
        prev = sys.stdin
        sys.stdin = os.fdopen(r, "r")
        try:
            got = StdinSource().poll()
        finally:
            sys.stdin.close()
            sys.stdin = prev
        self.assertIsNotNone(got)
        self.assertEqual(got.rpm, 7100)

    def test_serial_source_reads_fake_uart(self) -> None:
        from mocks.esp32_uart import warn_frame
        from mocks.fake_serial import FakeSerial

        telem = warn_frame()
        ser = FakeSerial([telem.to_line(), "not-json\n"])
        got = SerialSource(ser).poll()
        self.assertIsNotNone(got)
        self.assertEqual(got.rpm, telem.rpm)
        self.assertTrue(got.lamp("brake"))
        self.assertTrue(got.lamp("srs"))


if __name__ == "__main__":
    unittest.main()

