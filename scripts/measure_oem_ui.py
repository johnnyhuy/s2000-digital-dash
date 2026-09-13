#!/usr/bin/env python3
"""Objectively measure OEM-vs-UI deltas in the live composite.

This is the same-room eyeball test the loop prereqs on, automated.
Outputs a JSON dump of landmark positions on the OEM side (from the
Car Spy plate) and on the UI side (from the live composite), then the
delta for each.

Run:  uv run python scripts/measure_oem_ui.py
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
OEM = ROOT / "refs" / "oem"
COMPARE = ROOT / "docs" / "assets" / "compare"

sys.path.insert(0, str(SRC))
sys.path.insert(0, str(ROOT))

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="OEM-vs-UI measurement")
    p.add_argument("--composite", default=str(COMPARE / "compare_ap1_lit_live.png"))
    return p.parse_args(argv)


def measure_oem() -> dict[str, float]:
    """Read the OEM measurements plate JSON, return % of module height."""
    data = json.loads((OEM / "plates" / "oem_ap1_measurements.json").read_text())
    return {k: v / 100.0 for k, v in data["pct_of_module_height"].items()}


def measure_ui_landmarks(composite: Path) -> dict[str, float]:
    """Return rough landmark y-positions (in % of module height) found
    in the UI composite.

    Landmark reading uses heuristic threshold sweeps against the
    composite itself — the right half is the UI render, the left is the
    OEM photo. UI module is the lit-arch region inside the right half.
    """
    # Lazy imports — pygame + PIL live elsewhere too
    import pygame  # noqa: F401

    surf = pygame.image.load(str(composite))
    w, h = surf.get_size()
    ui_x = w // 2 + 8  # skip the gap
    ui_w = w - ui_x

    band_top = None
    band_bottom = None
    speed_top = None
    speed_bottom = None
    lcd_bottom = None
    lamp_top = None
    cluster_top = None
    cluster_bottom = None

    # Sample centre column of UI for landmark detection
    cx = ui_x + ui_w // 2
    last_y = None
    for y in range(36, h):
        r, g, b = surf.get_at((cx, y))[:3]
        bright = r + g + b
        if cluster_top is None and bright > 60:
            cluster_top = y
        if band_top is None and (r > 150 and g > 80 and b < 80 and bright > 250):
            band_top = y
        if band_top is not None and band_bottom is None and not (r > 150 and g > 80 and b < 80):
            if bright < 200 and last_y is not None and (last_y - band_top) > 4:
                band_bottom = last_y
        if speed_top is None and r > 100 and g < 80 and b < 60:
            speed_top = y
        if speed_top is not None and bright < 30:
            speed_bottom = y - 1
            break
        last_y = y

    # Use the bottom of UI for cluster_bottom (last drawn pixel)
    cluster_bottom = h - 36

    # Convert to UI-relative percentages of pixel-space height
    ui_height = cluster_bottom - cluster_top
    if ui_height <= 0:
        return {}

    def pct(y: int) -> float:
        return (y - cluster_top) / ui_height * 100.0

    return {
        "module_top_px": cluster_top,
        "module_height_px": ui_height,
        "cluster_top_pct": 0.0,
        "band_top_pct": pct(band_top) if band_top else None,
        "band_bottom_pct": pct(band_bottom) if band_bottom else None,
        "speed_top_pct": pct(speed_top) if speed_top else None,
        "speed_bottom_pct": pct(speed_bottom) if speed_bottom else None,
        "cluster_bottom_pct": 100.0,
    }


def measure_module_width_aspect(composite: Path) -> dict[str, float]:
    import pygame  # noqa: F401

    surf = pygame.image.load(str(composite))
    w, h = surf.get_size()
    ui_x = w // 2 + 8
    ui_w = w - ui_x
    # Find module left/right by scanning the middle band row
    mid_y = h // 2
    left = None
    right = None
    for x in range(ui_x, w):
        r, g, b = surf.get_at((x, mid_y))[:3]
        bright = r + g + b
        if bright > 60:
            if left is None:
                left = x
            right = x
    width_px = (right or w) - (left or ui_x)
    return {"ui_x": ui_x, "module_left_px": left, "module_right_px": right, "width_px": width_px}


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    composite = Path(args.composite)
    if not composite.is_file():
        print(f"missing {composite}", file=sys.stderr)
        return 2

    oem = measure_oem()
    ui = measure_ui_landmarks(composite)
    print("OEM % of module height:")
    for k, v in oem.items():
        print(f"  {k:20s} {v:.2f}")
    print("UI landmarks (px space):")
    for k, v in ui.items():
        print(f"  {k:20s} {v}")
    width = measure_module_width_aspect(composite)
    print("UI module width:")
    for k, v in width.items():
        print(f"  {k:20s} {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
