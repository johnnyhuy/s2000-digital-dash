#!/usr/bin/env python3
"""Measure the captured AP1 pixels in their recorded module coordinate system.

Run compare_oem.py first, then measure_oem_ui.py --check --output report.json.
The geometry gate uses refs/flat/DIMENSIONS.md, not the historic illustrative
plate picks. Photo colour samples are reported without claiming calibrated
colour accuracy. A still reference cannot establish OEM motion equivalence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import pygame

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_COMPOSITE = ROOT / "docs/assets/compare/compare_ap1_lit_live.png"

# Independent acceptance intervals from DIMENSIONS.md. Approximate landmarks
# have the same 1.5 percentage-point allowance as FaceGeomTests; raster edges
# additionally allow one output pixel. Do not derive expectations from the UI.
LOCK = {
    "band_top_pct": (10.0, 1.5),
    "speed_height_pct": (19.4, 1.0),
    "speed_right_pct": (59.0, 1.0),
    "temp_left_pct": (13.5, 0.5),
    "temp_width_pct": (12.5, 0.5),
    "fuel_left_pct": (74.7, 0.5),
    "fuel_width_pct": (12.5, 0.5),
}


def measure_oem() -> dict[str, float]:
    """Historic plate percentages, preserved in their original units."""
    data = json.loads((ROOT / "refs/oem/plates/oem_ap1_measurements.json").read_text())
    return data["pct_of_module_height"]


def load_capture(composite: Path) -> tuple[pygame.Surface, dict]:
    metadata = json.loads(composite.with_suffix(".json").read_text())
    if metadata.get("schema") != 1 or metadata.get("style") != "ap1":
        raise ValueError("measurement requires a schema-1 AP1 capture")
    if hashlib.sha256(composite.read_bytes()).hexdigest() != metadata["image_sha256"]:
        raise ValueError("composite changed after its capture metadata was written")
    reference = ROOT / metadata["reference"]
    if hashlib.sha256(reference.read_bytes()).hexdigest() != metadata["reference_sha256"]:
        raise ValueError("OEM reference changed after capture")
    image = pygame.image.load(str(composite))
    for key in ("ui_panel", "ui_module"):
        x, y, w, h = metadata[key]
        if not all(math.isfinite(v) for v in (x, y, w, h)) or not (
            x >= 0 and y >= 0 and w > 0 and h > 0
            and x + w <= image.get_width() and y + h <= image.get_height()
        ):
            raise ValueError(f"invalid {key} bounds")
    return image, metadata


def pixel_bounds(image: pygame.Surface, module: list[float], roi: tuple, predicate) -> tuple | None:
    """Inclusive bounds of matching pixels in a normalized module ROI."""
    mx, my, mw, mh = module
    x0, y0, x1, y1 = roi
    points = [
        (x, y)
        for y in range(math.ceil(my + y0 * mh), math.floor(my + y1 * mh) + 1)
        for x in range(math.ceil(mx + x0 * mw), math.floor(mx + x1 * mw) + 1)
        if predicate(image.get_at((x, y)))
    ]
    if not points:
        return None
    xs, ys = zip(*points)
    return min(xs), min(ys), max(xs), max(ys)


def measure(image: pygame.Surface, metadata: dict) -> dict:
    module = metadata["ui_module"]
    mx, my, mw, mh = module
    amber = lambda p: p[0] > 150 and 70 < p[1] < 210 and p[2] < 90
    red = lambda p: p[0] > 180 and p[1] < 120 and p[2] < 100
    # Include both lit blocks and the unlit red glass when finding bar spans.
    glass = lambda p: p[0] > 40 and p[0] > p[1] * 2 and p[0] > p[2] * 2
    band = pixel_bounds(image, module, (.35, .05, .65, .22), amber)
    speed = pixel_bounds(image, module, (.39, .35, .60, .568), red)
    temp = pixel_bounds(image, module, (.12, .57, .27, .622), glass)
    fuel = pixel_bounds(image, module, (.74, .57, .88, .622), glass)
    values = {
        "band_top_pct": (band[1] - my) / mh * 100 if band else None,
        "speed_height_pct": (speed[3] - speed[1] + 1) / mh * 100 if speed else None,
        "speed_right_pct": (speed[2] + 1 - mx) / mw * 100 if speed else None,
        "temp_left_pct": (temp[0] - mx) / mw * 100 if temp else None,
        "temp_width_pct": (temp[2] - temp[0] + 1) / mw * 100 if temp else None,
        "fuel_left_pct": (fuel[0] - mx) / mw * 100 if fuel else None,
        "fuel_width_pct": (fuel[2] - fuel[0] + 1) / mw * 100 if fuel else None,
    }
    checks = []
    for key, (expected, tolerance) in LOCK.items():
        value = values[key]
        axis = mh if key in ("band_top_pct", "speed_height_pct") else mw
        delta = value - expected if value is not None else None
        checks.append({
            "landmark": key, "expected_pct": expected, "measured_pct": value,
            "delta_pct": delta, "delta_px": delta * axis / 100 if delta is not None else None,
            "tolerance_pct": tolerance + 100 / axis,
            "pass": delta is not None and abs(delta) <= tolerance + 100 / axis,
        })
    aspect_error = abs(mw / mh - 2.35)
    checks.append({"landmark": "module_aspect", "expected": 2.35,
                   "measured": mw / mh, "tolerance": .005, "pass": aspect_error <= .005})
    return {
        "geometry_pass": all(c["pass"] for c in checks),
        "checks": checks,
        "historic_plate_pct": measure_oem(),
        "limitations": [
            "Geometry-only gate against DIMENSIONS.md; not full OEM visual acceptance.",
            "Photo exposure and perspective are not calibrated colour or font evidence.",
            "Still references provide no OEM timing or motion evidence.",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--composite", type=Path, default=DEFAULT_COMPOSITE)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        image, metadata = load_capture(args.composite)
        report = measure(image, metadata)
        report["capture"] = metadata
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(2, f"invalid capture: {exc}\n")
    text = json.dumps(report, indent=2, allow_nan=False) + "\n"
    if args.output:
        args.output.write_text(text)
    print(text, end="")
    return int(args.check and not report["geometry_pass"])


if __name__ == "__main__":
    raise SystemExit(main())
