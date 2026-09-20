"""Render-scale regressions: panel clipping, LCD gutters and shared artwork."""
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pygame
import pytest

from face_spec import AP1, AP2, MODULE_ASPECT
from gauge_ui import build_face_geom, _font
from lcd_digits import measure_text

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("style", ["ap1", "ap2"])
@pytest.mark.parametrize("size", [(1920, 1080), (1280, 720), (800, 480), (1920, 720), (1280, 400)])
def test_face_contained_without_stretch(style, size):
    g = build_face_geom(*size, style=style, car=True)
    x, y, w, h = g.module
    assert x >= 0 and y >= 0
    assert x + w <= size[0] and y + h <= size[1]
    assert abs(w / h - MODULE_ASPECT) < .01


@pytest.mark.parametrize("style", ["ap1", "ap2"])
@pytest.mark.parametrize("size", [(1920, 1080), (1280, 720), (800, 480)])
def test_actual_digit_runs_fit_their_windows(style, size):
    g = build_face_geom(*size, style=style, car=True)
    s = g.spec
    mx, my, mw, mh = g.module
    runs = []
    for name, text, height, x, y, align, window in (
        ("speed", "188", s.speed_digit_h, s.speed_right, s.speed.cy, "right", g.speed_win),
        ("odo", "888888", s.odo_digit_h, s.odo_left, s.odo_cy, "left", g.odo_win),
        ("trip", "888.8", s.trip_digit_h, s.trip_right, s.trip_cy, "right", g.odo_win),
    ):
        w, h = measure_text(text, int(mh * height))
        box = pygame.Rect(int(mx + mw * x) - (w if align == "right" else 0), int(my + mh * y) - h // 2, w, h)
        assert pygame.Rect(window).contains(box), (style, size, name, box, window)
        runs.append(box)
    assert runs[1].right + 2 <= runs[2].left, (style, size, "odo/trip gutter")
    if s.clock:
        cw, ch = measure_text("88:88", int(mh * s.trip_digit_h))
        cx, cy = g.anchor_px(s.clock)
        clock = pygame.Rect(cx, cy - ch // 2, cw, ch)
        assert pygame.Rect(g.odo_win).contains(clock)
        assert clock.bottom + 2 <= runs[1].top



@pytest.mark.parametrize("style", ["ap1", "ap2"])
def test_numeral_ink_clears_central_windows(style):
    pygame.font.init()
    g = build_face_geom(style=style)
    font = _font(pygame, int(g.w(g.spec.tach.num_size)), kind="round")
    for i in range(10):
        glyph = font.render(str(i), True, "white")
        cx, cy = g.arc_px(g.spec.tach.r_num, g.spec.tach.angle_deg(i * 1000))
        box = glyph.get_bounding_rect().move(glyph.get_rect(center=(round(cx), round(cy))).topleft)
        for window in (g.speed_win, g.odo_win):
            assert not box.colliderect(window), (style, i, window)


def test_web_pictograms_match_committed_masters():
    spec = importlib.util.spec_from_file_location("export_web_icons", ROOT / "scripts/export_web_icons.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert (ROOT / "apps/harness/components/LampIcons.tsx").read_text() == module.generate()


def test_airbag_is_distinct_from_belt_and_low_fuel_is_available():
    assert next(s for s in AP2.arc_lamps if s.key == "srs").icon == "airbag"
    for face in (AP1, AP2):
        assert any(s.key == "fuel_low" and s.icon == "fuel" for s in face.strip_lamps + face.panel_lamps)
        assert len(face.tach.tick_rpms()) == 19  # integers plus half-thousands, photo/manual


def test_oil_can_cutout_and_droplet_survive_rasterization():
    image = pygame.image.load(str(ROOT / "assets/icons/oil.png"))
    def alpha(x, y):
        return image.get_at((int(x * image.get_width() / 64), int(y * image.get_height() / 48))).a
    assert alpha(31, 26) == 0  # transparent can interior
    assert alpha(58, 32) > 200  # separate droplet inside the plate


def test_panel_resolution_reaches_real_render_entrypoint(tmp_path):
    subprocess.run([sys.executable, str(ROOT / "src/gauge_ui.py"), "--smoke", "--car",
                    "--size", "800x480", "--style", "ap2", "--screenshot", str(tmp_path)],
                   check=True, capture_output=True,
                   env={**os.environ, "SDL_VIDEODRIVER": "dummy", "SDL_AUDIODRIVER": "dummy"})
    for path in tmp_path.glob("*.png"):
        assert pygame.image.load(str(path)).get_size() == (800, 480)
    assert len(list(tmp_path.glob("*.png"))) == 5
