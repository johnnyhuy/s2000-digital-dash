#!/usr/bin/env python3
"""Side-by-side OEM photo | UI screenshot composites.

Writes PNGs into docs/assets/compare/. Protocol field names are unchanged.

  python scripts/compare_oem.py
  uv run python scripts/compare_oem.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
OEM = ROOT / "refs" / "oem"
DEST = ROOT / "docs" / "assets" / "compare"

sys.path.insert(0, str(SRC))
sys.path.insert(0, str(ROOT))

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")


def _init():
    from face_style import FaceStyle
    from gauge_ui import (
        DisplayState,
        apply_face_style,
        build_fonts,
        cruise_telem,
        draw_frame,
        init_pygame,
        sample_telem,
        selftest_telem,
    )

    pygame, _screen = init_pygame(windowed=True, headless=True)
    fonts = build_fonts(pygame)
    return (
        pygame,
        fonts,
        DisplayState,
        draw_frame,
        sample_telem,
        cruise_telem,
        selftest_telem,
        apply_face_style,
        FaceStyle,
    )


def _render(pygame, fonts, draw_frame, DisplayState, telem, phase: str, local_t: float):
    from gauge_ui import W, H

    face = DisplayState()
    face.snap(telem)
    face.trip_origin = telem.odo_km - 128.4
    face.trip_km = 128.4
    canvas = pygame.Surface((W, H))
    draw_frame(pygame, fonts, canvas, face, phase, local_t)
    return canvas


def _fit_height(pygame, surf, height: int):
    w, h = surf.get_size()
    if h == height:
        return surf
    nw = max(2, int(w * (height / h)))
    return pygame.transform.smoothscale(surf, (nw, height))


def _caption(pygame, surf, text: str) -> None:
    font = pygame.font.SysFont(["DejaVu Sans", "FreeSans", "sans-serif"], 22, bold=True)
    img = font.render(text, True, (236, 152, 32))
    pad = pygame.Surface((surf.get_width(), 36))
    pad.fill((8, 8, 9))
    pad.blit(img, (12, 6))
    surf.blit(pad, (0, 0))


def compose(pygame, left, right, label_l: str, label_r: str, height: int = 520):
    a = _fit_height(pygame, left, height)
    b = _fit_height(pygame, right, height)
    gap = 10
    out = pygame.Surface((a.get_width() + b.get_width() + gap, height + 36))
    out.fill((8, 8, 9))
    out.blit(a, (0, 36))
    out.blit(b, (a.get_width() + gap, 36))
    _caption(pygame, out.subsurface(pygame.Rect(0, 0, a.get_width(), 36)), label_l)
    cap_r = out.subsurface(pygame.Rect(a.get_width() + gap, 0, b.get_width(), 36))
    _caption(pygame, cap_r, label_r)
    pygame.draw.line(
        out,
        (58, 52, 40),
        (a.get_width() + gap // 2, 0),
        (a.get_width() + gap // 2, out.get_height()),
        2,
    )
    return out


def load_optional(pygame, path: Path):
    if not path.is_file():
        return None
    return pygame.image.load(str(path)).convert()


def main() -> int:
    (
        pygame,
        fonts,
        DisplayState,
        draw_frame,
        sample_telem,
        cruise_telem,
        selftest_telem,
        apply_face_style,
        FaceStyle,
    ) = _init()
    DEST.mkdir(parents=True, exist_ok=True)

    apply_face_style(FaceStyle.AP1)
    live = _render(pygame, fonts, draw_frame, DisplayState, sample_telem(), "live", 1.0)
    cruise = _render(pygame, fonts, draw_frame, DisplayState, cruise_telem(), "live", 1.0)
    selftest = _render(pygame, fonts, draw_frame, DisplayState, selftest_telem(), "live", 1.0)
    sweep = _render(pygame, fonts, draw_frame, DisplayState, sample_telem(), "sweep", 0.55)
    apply_face_style(FaceStyle.AP2)
    live_ap2 = _render(pygame, fonts, draw_frame, DisplayState, sample_telem(), "live", 1.0)
    sweep_ap2 = _render(pygame, fonts, draw_frame, DisplayState, sample_telem(), "sweep", 0.55)
    apply_face_style(FaceStyle.AP1)

    pairs = [
        (
            "compare_ap1_lit_live.png",
            OEM / "lit" / "lit_ap1_carspy_cluster.jpg",
            live,
            "OEM AP1 (The Car Spy, CC BY 2.0)",
            "UI live ~6500 r/min",
        ),
        (
            "compare_ap1_lit_cruise.png",
            OEM / "lit" / "lit_ap1_carspy_cluster.jpg",
            cruise,
            "OEM AP1 (The Car Spy, CC BY 2.0)",
            "UI cruise 80 km/h",
        ),
        (
            "compare_ap1_selftest.png",
            OEM / "lit" / "lit_ap1_carspy_cluster.jpg",
            selftest,
            "OEM AP1 (The Car Spy, CC BY 2.0)",
            "UI self-test 188 / all lamps",
        ),
        (
            "compare_ap1_flat_sweep.png",
            ROOT / "refs" / "flat" / "ap1_cluster_flat.png",
            sweep,
            "OEM flat lock (in-repo)",
            "UI sweep / ghost ticks",
        ),
        (
            "compare_ap2_caution.png",
            OEM / "ap2" / "ap2_s2ki_arched_gauges.jpg",
            live_ap2,
            "AP2 OEM (arched TEMP/FUEL) — reference, not a plate",
            "UI AP2 style (interpretive side gauges)",
        ),
        (
            "compare_ap2_sweep.png",
            OEM / "ap2" / "ap2_s2ki_arched_gauges.jpg",
            sweep_ap2,
            "AP2 OEM (arched TEMP/FUEL) — reference, not a plate",
            "UI AP2 ignition sweep / bulb check",
        ),
    ]

    written = 0
    for name, oem_path, ui, lab_l, lab_r in pairs:
        oem = load_optional(pygame, oem_path)
        if oem is None:
            print(f"skip {name}: missing {oem_path}", file=sys.stderr)
            continue
        frame = compose(pygame, oem, ui, lab_l, lab_r)
        dest = DEST / name
        pygame.image.save(frame, str(dest))
        print(dest)
        written += 1

    pygame.quit()
    return 0 if written else 1


if __name__ == "__main__":
    raise SystemExit(main())
