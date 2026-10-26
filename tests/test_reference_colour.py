import re
from pathlib import Path

import pygame

import gauge_ui
from scripts import reference_colour

ROOT = Path(__file__).resolve().parents[1]


def test_reference_palette_and_web_parity():
    # Compare actual source pixels, not expected RGB constants copied from UI.
    image = pygame.Surface((1920, 1080))
    g = gauge_ui.build_face_geom()
    gauge_ui._draw_band_unlit(pygame, image, g)
    mx, my, mw, mh = g.module
    for key, rgb, roi in [
        ("lcd_red", gauge_ui.RED_LCD, (.39, .35, .60, .568)),
        ("side_amber", gauge_ui.SEG_YELLOW, (.135, .586, .26, .616)),
    ]:
        x0,y0,x1,y1 = roi
        pygame.draw.rect(image, rgb, (round(mx+mw*x0), round(my+mh*y0), round(mw*(x1-x0)), round(mh*(y1-y0))))
    checks = reference_colour.measure(image, {"ui_module": g.module})
    assert all(c["pass"] for c in checks), checks
    web = (ROOT / "apps/harness/components/ClusterFace.tsx").read_text()
    for name in ("AMBER", "BAND_UNLIT_END", "BAND_UNLIT_MID", "HATCH_AMBER", "HATCH_RED", "HATCH_RED_LIT", "RED_LCD", "SEG_YELLOW"):
        value = re.search(rf'const {name} = "#([0-9a-f]{{6}})"', web)[1]
        assert tuple(bytes.fromhex(value)) == getattr(gauge_ui, name)


def test_old_saturated_red_is_rejected():
    image = pygame.Surface((1000, 426))
    pygame.draw.rect(image, (255, 66, 40), (390, 149, 210, 93))
    checks = reference_colour.measure(image, {"ui_module": [0, 0, 1000, 426]})
    assert not next(c for c in checks if c["sample"] == "lcd_red")["pass"]
