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

from face_spec import AP1, AP2, RPM_MAX  # noqa: E402
from gauge_ui import (  # noqa: E402
    FACE,
    MODULE_ASPECT,
    build_face_geom,
    tach_arch_normal,
    tach_arch_xy,
    tach_band_poly,
    tach_num_xy,
    temp_segments_lit,
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
    """Lock the face to the OEM AP1 plate (refs/oem/lit/lit_ap1_carspy_cluster.jpg).

    All numbers are fractions of the module box (x/W, y/H). The photo is
    squashed by the camera, but a uniform squash keeps y-fractions, so the
    measurements below are read straight off the plate.
    """

    def _pct(self, x: float, y: float) -> tuple[float, float]:
        mx, my, mw, mh = FACE.module
        return (x - mx) / mw, (y - my) / mh

    def _assert_pct(self, px: tuple[float, float], want: tuple[float, float], delta: float = 0.02) -> None:
        got = self._pct(*px)
        self.assertAlmostEqual(got[0], want[0], delta=delta)
        self.assertAlmostEqual(got[1], want[1], delta=delta)

    def test_module_aspect_is_locked(self) -> None:
        self.assertAlmostEqual(MODULE_ASPECT, 2.35, places=2)
        mw, mh = FACE.module[2], FACE.module[3]
        self.assertAlmostEqual(mw / mh, 2.35, delta=0.05)

    def test_tach_is_a_true_circular_arc(self) -> None:
        t = AP1.tach
        cx, cy = FACE.px(t.cx, t.cy / MODULE_ASPECT)
        for frac in (0.0, 0.25, 0.5, 0.75, 1.0):
            x, y = tach_arch_xy(frac)
            r = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
            self.assertAlmostEqual(r / FACE.module[2], t.r_line, delta=0.002)

    def test_band_peak_and_ends_land_on_oem(self) -> None:
        """Band outer edge peaks at ~2.3 % H; 0 / 9 ticks at x ≈ 0.19 / 0.81, y ≈ 0.36 H."""
        t = AP1.tach
        _, peak_y = FACE.arc_px(t.r_out, -90.0)
        self.assertAlmostEqual(self._pct(0, peak_y)[1], 0.023, delta=0.01)
        x0, y0 = self._pct(*tach_arch_xy(0.0))
        x9, y9 = self._pct(*tach_arch_xy(1.0))
        self.assertAlmostEqual(x0, 0.19, delta=0.02)
        self.assertAlmostEqual(x9, 0.81, delta=0.02)
        self.assertAlmostEqual(y0, 0.36, delta=0.03)
        self.assertAlmostEqual(y0, y9, delta=0.002)

    def test_zero_to_one_is_squeezed(self) -> None:
        t = AP1.tach
        first = t.angle_deg(1000) - t.angle_deg(0)
        rest = (t.angle_deg(9000) - t.angle_deg(1000)) / 8.0
        self.assertAlmostEqual(first / rest, 0.60, delta=0.02)
        self.assertAlmostEqual(t.angle_deg(9000) - t.angle_deg(0), 75.6, delta=0.5)
        self.assertEqual(t.angle_deg(RPM_MAX), t.a9_deg)

    def test_numerals_sit_just_inside_the_baseline(self) -> None:
        for frac in (0.0, 0.5, 1.0):
            ax, ay = tach_arch_xy(frac)
            nx, ny = tach_arch_normal(frac)
            px, py = tach_num_xy(frac)
            inset = ((px - ax) ** 2 + (py - ay) ** 2) ** 0.5 / FACE.module[2]
            self.assertAlmostEqual(inset, AP1.tach.num_inset, delta=0.001)
            # numerals are displaced along the inward normal, i.e. below the arc
            self.assertGreater((px - ax) * nx + (py - ay) * ny, 0)
            self.assertGreater(py, ay)
        # "5" sits at ~19 % H on the plate, "0" at ~43 % H
        self.assertAlmostEqual(self._pct(*tach_num_xy(5 / 9))[1], 0.19, delta=0.03)
        self.assertAlmostEqual(self._pct(*tach_num_xy(0.0))[1], 0.43, delta=0.03)

    def test_visor_lip_clears_the_band(self) -> None:
        _, peak_y = FACE.arc_px(AP1.tach.r_out, -90.0)
        pts = visor_lip_points()
        self.assertGreater(len(pts), 20)
        mid = pts[len(pts) // 2]
        self.assertLess(mid[1], peak_y)
        self.assertLess(peak_y - mid[1], FACE.module[2] * 0.012)
        # springs meet the bezel at ~8 % / 92 % W
        self.assertAlmostEqual(self._pct(*pts[0])[0], 0.08, delta=0.02)
        self.assertAlmostEqual(self._pct(*pts[-1])[0], 0.92, delta=0.02)

    def test_band_runs_under_the_hood_lip_not_past_it(self) -> None:
        """OEM: the band ends tuck under the hood edge. The printed band may
        run a hair under the lip but never out past the cowl, and the apex
        clears the crown with a visible gap."""
        t = AP1.tach
        lip_px = AP1.crown_lip * FACE.module[2]

        def crown_y_at(bx: float) -> float:
            dx = (bx - FACE.px(AP1.tach.cx, 0)[0]) / FACE.module[2]
            dy = (AP1.crown_r ** 2 - dx ** 2) ** 0.5
            return FACE.px(0, AP1.crown_cy / MODULE_ASPECT - dy)[1]

        _, apex_y = FACE.arc_px(t.r_out, -90.0)
        self.assertGreater(apex_y - crown_y_at(FACE.px(0.5, 0)[0]), lip_px * 0.25)
        for deg in (t.band_start_deg(), -110.0, -70.0, t.band_end_deg()):
            bx, by = FACE.arc_px(t.r_out, deg)
            self.assertGreater(by, crown_y_at(bx) - lip_px, f"band escapes the cowl at {deg}°")

    def test_temp_and_fuel_are_horizontal_flanking_bars(self) -> None:
        tx, ty, tw, th = FACE.temp
        fx, fy, fw, fh = FACE.fuel
        self.assertGreater(tw, th * 2.5)
        self.assertGreater(fw, fh * 2.2)
        self.assertLess(tx + tw, FACE.speed_win[0])
        self.assertGreater(fx, FACE.speed_win[0] + FACE.speed_win[2])
        # OEM plate: TEMP window x 0.13–0.29 at 52–57.5 % H; FUEL 0.815–0.925 at 46.5–51 % H
        self._assert_pct((tx, ty), (0.13, 0.52))
        self._assert_pct((fx, fy), (0.815, 0.465))
        self.assertEqual(AP1.temp_segs, 8)
        self.assertEqual(AP1.fuel_segs, 16)

    def test_temp_blocks_idle_low(self) -> None:
        # 89 °C → 3–4 of 8 blocks like the real cluster; H → all 8
        from gauge_ui import ect_frac

        self.assertIn(temp_segments_lit(ect_frac(89.0), 8), (3, 4))
        self.assertEqual(temp_segments_lit(0.0, 8), 0)
        self.assertEqual(temp_segments_lit(1.0, 8), 8)

    def test_lcd_windows_lock_to_oem(self) -> None:
        sx, sy, sw, sh = FACE.speed_win
        ox, oy, ow, oh = FACE.odo_win
        self._assert_pct((sx, sy), (0.39, 0.30))
        self.assertAlmostEqual(sw / FACE.module[2], 0.22, delta=0.02)
        self._assert_pct((ox, oy), (0.39, 0.57))
        self.assertGreater(oy, sy + sh)
        self.assertAlmostEqual(self._pct(*FACE.speed_c)[0], 0.50, delta=0.01)
        self.assertAlmostEqual(sh / FACE.module[3], 0.24, delta=0.03)

    def test_strip_and_hardware_lock(self) -> None:
        lx, ly, lw, lh = FACE.lamp_band
        self._assert_pct((lx, ly), (0.155, 0.745))
        self.assertGreater(ly, FACE.spring_y)
        self.assertLess(FACE.minus_btn[0] + FACE.minus_btn[2], FACE.plus_btn[0])
        self.assertLess(FACE.plus_btn[0] + FACE.plus_btn[2], lx)
        self.assertGreater(FACE.trip[0], lx + lw)
        self.assertGreaterEqual(FACE.bezel[1], FACE.spring_y)

    def test_module_is_flat_bottom_and_stepped(self) -> None:
        bl, br = hood_bottom_corners(FACE)
        self.assertEqual(bl[1], br[1])
        self.assertGreater(FACE.step, 0)
        self.assertGreater(FACE.lcd[0], FACE.module[0])
        self.assertLess(FACE.lcd[0] + FACE.lcd[2], FACE.module[0] + FACE.module[2])
        self.assertLessEqual(FACE.hood_peak_y, FACE.module[1] + 2)

    def test_car_mode_fills_the_panel(self) -> None:
        g = build_face_geom(1280, 720, car=True)
        self.assertEqual(g.module[0], 0)
        self.assertEqual(g.module[2], 1280)
        self.assertTrue(g.car)

    def test_ap2_is_the_same_housing(self) -> None:
        g = build_face_geom(style="ap2")
        self.assertEqual(g.lcd, FACE.lcd)
        self.assertEqual(AP2.crown_r, AP1.crown_r)
        self.assertTrue(AP2.side_gauges_arched)
        self.assertLess(AP2.tach.a9_deg, -60.0)  # 9 sits near the apex, not the right spring

    def test_tach_band_is_a_closed_polygon(self) -> None:
        pts = tach_band_poly(0.0, 0.5, 1.0, 16)
        self.assertGreater(len(pts), 16)
        xs = [p[0] for p in pts]
        self.assertLess(min(xs), max(xs))


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
        self.assertEqual(self.sample_near(strip, NEON_CYAN, step=2, tol=20), 0)
        # turn arrows / high beam live inside the tach arc on the OEM plate
        well = region(frame, FACE.lcd)
        self.assertGreater(self.sample_near(well, LAMP_GREEN, step=2, tol=40), 0)
        self.assertGreater(self.sample_near(well, LAMP_BLUE, step=2, tol=40), 0)
        self.assertEqual(self.sample_near(well, NEON_CYAN, step=2, tol=20), 0)

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
        self.assertTrue((_FONTS / "MPLUSRounded1c-Bold.ttf").is_file())
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

