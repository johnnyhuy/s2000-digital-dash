#!/usr/bin/env python3
"""Reference-driven AP1 composite acceptance for the six independent tracks.

Capture first with compare_oem.py. Optionally supply --web-dir from
apps/harness/scripts/capture-face.cjs to measure the real React SVG too.
This gate establishes the documented, measurable reference criteria; stills
cannot establish OEM timing, calibrated OLED brightness or vehicle fit.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame
from scripts import measure_oem_ui, reference_colour, reference_font, reference_graphics


def capture_tracks(image, metadata):
    geometry = measure_oem_ui.measure(image, metadata)["checks"]
    sizes = {"speed_height_pct", "temp_width_pct", "fuel_width_pct"}
    tracks = {
        "position": [c for c in geometry if c["landmark"] not in sizes],
        "size": [c for c in geometry if c["landmark"] in sizes],
        "graphics": reference_graphics.measure(image, metadata),
        "colour": reference_colour.measure(image, metadata),
        "font": reference_font.measure(image, metadata),
    }
    module = metadata["ui_module"]
    _, _, mw, mh = module
    red = lambda p: p[0] > 180 and p[1] < 140 and p[2] < 130
    white = lambda p: min(p[:3]) > 180
    amber = lambda p: p[0] > 150 and 70 < p[1] < 210 and p[2] < 120
    for name, roi, predicate, target, axis in [
        ("odo_digit_h", (.402, .625, .515, .70), red, 5.2, mh),
        ("trip_digit_h", (.53, .625, .60, .70), red, 4.8, mh),
        ("coolant_h", (.12, .48, .162, .57), white, 2.2, mw),
        ("band_thickness", (.48, .05, .52, .22), amber, 3.3, mw),
    ]:
        bounds = measure_oem_ui.pixel_bounds(image, module, roi, predicate)
        value = (bounds[3] - bounds[1] + 1) / axis * 100 if bounds else None
        tolerance = .5 + 100 / axis
        tracks["size"].append({"sample": name, "expected_pct": target, "measured_pct": value,
                               "tolerance_pct": tolerance,
                               "pass": value is not None and abs(value - target) <= tolerance})
    return {name: {"pass": all(c["pass"] for c in checks), "checks": checks}
            for name, checks in tracks.items()}


def motion_checks():
    from gauge_ui import build_face_geom, draw_tach_fill, DisplayState, sample_telem
    from motion_spec import export_json

    g = build_face_geom(1000, 600)
    def pixels(rpm):
        surface = pygame.Surface((1000, 600))
        draw_tach_fill(pygame, surface, rpm, None, g)
        return pygame.image.tobytes(surface, "RGB")
    checks = []
    for low, high, next_step in [(0, 199.9, 200), (3200, 3399.9, 3400), (8000, 8199.9, 8200)]:
        checks.append({"sample": f"cell_{low}_{next_step}",
                       "pass": pixels(low) == pixels(high) and pixels(high) != pixels(next_step)})
    target = sample_telem()
    target.rpm = 9000
    expected = 9000 * (1 - math.exp(-1 / .18))
    for fps in (30, 60, 120):
        state = DisplayState()
        for _ in range(fps):
            state.follow(target, 1 / fps)
        checks.append({"sample": f"response_{fps}fps", "rpm_after_1s": state.rpm,
                       "expected_rpm": expected, "pass": abs(state.rpm - expected) < 1e-8})
    state = DisplayState()
    state.follow(target, 0)
    checks.append({"sample": "paused_response", "pass": state.rpm == 0})
    checks.append({"sample": "web_response_export", "pass":
                   (ROOT / "apps/harness/lib/motionSpec.json").read_text() == export_json()})
    return {"pass": all(c["pass"] for c in checks), "checks": checks,
            "scope": "200 rpm steps and shared demo response; OEM timing is not established by stills"}


def export_checks():
    from face_spec import SPECS, AP1, spec_to_dict, spec_to_scad
    from scripts.export_tach_font import generate
    from scripts.export_web_icons import generate as icons

    expected = json.dumps({style: spec_to_dict(spec) for style, spec in SPECS.items()}, indent=2, sort_keys=True) + "\n"
    checks = [
        {"sample": "web_geometry_export", "pass": (ROOT / "apps/harness/lib/faceSpec.json").read_text() == expected},
        {"sample": "cad_geometry_export", "pass": (ROOT / "cad/replace_face/face_lock.scad").read_text() == spec_to_scad(AP1)},
        {"sample": "web_font_export", "pass": (ROOT / "apps/harness/components/TachGlyphs.tsx").read_text() == generate()},
        {"sample": "web_icon_export", "pass": (ROOT / "apps/harness/components/LampIcons.tsx").read_text() == icons()},
    ]
    return {"pass": all(c["pass"] for c in checks), "checks": checks}


def evaluate(composite, web_dir=None):
    image, metadata = measure_oem_ui.load_capture(composite)
    tracks = capture_tracks(image, metadata)
    tracks["motion"] = motion_checks()
    exports = export_checks()
    report = {
        "schema": 1, "capture": metadata, "tracks": tracks, "exports": exports,
        "references": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in [
            ROOT / "refs/flat/DIMENSIONS.md", ROOT / "refs/oem/lit/lit_ap1_carspy_cluster.jpg",
            ROOT / "refs/oem/plates/oem_dash_glyphs_plate.png",
        ]},
        "limitations": [
            "Photo/plate/lock acceptance, not a calibrated whole-photo pixel identity or physical fit claim.",
            "The photo is at idle: lit tach amber uses its lit hatch/side-bar colour as the available proxy.",
            "The glyph plate is a reconstruction; legends remain the bundled family specified by the lock.",
            "Motion checks enforce discrete steps and renderer parity; no OEM timing recording is available.",
        ],
    }
    passed = exports["pass"] and all(track["pass"] for track in tracks.values())
    if web_dir:
        web_meta = json.loads((web_dir / "ap1-live.json").read_text())
        for name, key in [("ap1-live.svg", "svg_sha256"), ("ap1-live.png", "image_sha256")]:
            if hashlib.sha256((web_dir / name).read_bytes()).hexdigest() != web_meta[key]:
                raise ValueError(f"stale web capture: {name}")
        web_image = pygame.image.load(str(web_dir / "ap1-live.png"))
        web_tracks = capture_tracks(web_image, web_meta)
        report["web"] = {"capture": web_meta, "tracks": web_tracks,
                         "pass": all(track["pass"] for track in web_tracks.values())}
        passed = passed and report["web"]["pass"]
    report["acceptance_pass"] = passed
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--composite", type=Path, default=measure_oem_ui.DEFAULT_COMPOSITE)
    parser.add_argument("--web-dir", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    try:
        report = evaluate(args.composite, args.web_dir)
    except (OSError, ValueError, KeyError, TypeError, IndexError) as exc:
        parser.exit(2, f"invalid acceptance input: {exc}\n")
    payload = json.dumps(report, indent=2, allow_nan=False) + "\n"
    if args.output:
        args.output.write_text(payload)
    print(json.dumps({"acceptance_pass": report["acceptance_pass"],
                      "tracks": {name: track["pass"] for name, track in report["tracks"].items()},
                      "web_pass": report.get("web", {}).get("pass")}, indent=2))
    return int(args.check and not report["acceptance_pass"])


if __name__ == "__main__":
    raise SystemExit(main())
