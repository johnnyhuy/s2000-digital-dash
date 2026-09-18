#!/usr/bin/env python3
"""Python UI test harness — smoke frames, average-hash, OEM compare.

  uv run python scripts/ui_harness.py
  uv run python scripts/ui_harness.py --check
  UPDATE_GOLDENS=1 uv run python scripts/ui_harness.py --check

Does not change protocol JSON fields. Headless dummy SDL only.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
HARNESS_DIR = ROOT / "shots" / "harness"
GOLDEN = ROOT / "tests" / "harness" / "goldens.json"

sys.path.insert(0, str(SRC))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

# Hamming distance allowed on a 16×16 average hash (font/AA drift)
AHASH_TOLERANCE = 18
AHASH_SIZE = 16

# name, telem, phase, local_t, style
SCENES: tuple[tuple[str, str, str, float, str], ...] = (
    ("harness_sweep", "sample", "sweep", 0.55, "ap1"),
    ("harness_ready", "sample", "ready", 0.55, "ap1"),
    ("harness_reveal", "sample", "reveal", 0.40, "ap1"),
    ("harness_live", "sample", "live", 1.0, "ap1"),
    ("harness_cruise", "cruise", "live", 1.0, "ap1"),
    ("harness_selftest", "selftest", "live", 1.0, "ap1"),
    ("harness_ap2_sweep", "sample", "sweep", 0.55, "ap2"),
    ("harness_ap2_ready", "sample", "ready", 0.55, "ap2"),
    ("harness_ap2_live", "sample", "live", 1.0, "ap2"),
)


def ahash(pygame, surf, size: int = AHASH_SIZE) -> str:
    """64–256 bit average hash as a hex string. No extra deps."""
    small = pygame.transform.smoothscale(surf, (size, size))
    pixels = []
    for y in range(size):
        for x in range(size):
            px = small.get_at((x, y))
            pixels.append((px.r * 3 + px.g * 6 + px.b) // 10)
    mean = sum(pixels) / len(pixels)
    bits = "".join("1" if v >= mean else "0" for v in pixels)
    return f"{int(bits, 2):0{(size * size) // 4}x}"


def hamming(a: str, b: str) -> int:
    if len(a) != len(b):
        return 10**9
    xa, xb = int(a, 16), int(b, 16)
    return (xa ^ xb).bit_count()


def _telem(kind: str):
    from gauge_ui import cruise_telem, sample_telem, selftest_telem

    if kind == "cruise":
        return cruise_telem()
    if kind == "selftest":
        return selftest_telem()
    return sample_telem()


def render_scenes(pygame, fonts, dest: Path) -> dict[str, str]:
    from face_style import FaceStyle
    from gauge_ui import W, H, DisplayState, apply_face_style, draw_frame

    dest.mkdir(parents=True, exist_ok=True)
    hashes: dict[str, str] = {}
    canvas = pygame.Surface((W, H))
    for name, telem_kind, phase, local_t, style in SCENES:
        apply_face_style(FaceStyle.AP2 if style == "ap2" else FaceStyle.AP1)
        face = DisplayState()
        telem = _telem(telem_kind)
        face.snap(telem)
        face.trip_origin = telem.odo_km - 128.4
        face.trip_km = 128.4
        draw_frame(pygame, fonts, canvas, face, phase, local_t)
        path = dest / f"{name}.png"
        pygame.image.save(canvas, str(path))
        hashes[name] = ahash(pygame, canvas)
    apply_face_style(FaceStyle.AP1)
    return hashes


def load_goldens() -> dict[str, str]:
    if not GOLDEN.is_file():
        return {}
    return json.loads(GOLDEN.read_text(encoding="utf-8"))


def write_goldens(hashes: dict[str, str]) -> None:
    GOLDEN.parent.mkdir(parents=True, exist_ok=True)
    GOLDEN.write_text(json.dumps(hashes, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def check_hashes(got: dict[str, str], expected: dict[str, str]) -> list[str]:
    errors: list[str] = []
    if not expected:
        errors.append("no goldens.json — run with UPDATE_GOLDENS=1")
        return errors
    for name, digest in got.items():
        want = expected.get(name)
        if want is None:
            errors.append(f"{name}: missing golden")
            continue
        dist = hamming(digest, want)
        if dist > AHASH_TOLERANCE:
            errors.append(f"{name}: ahash hamming {dist} > {AHASH_TOLERANCE}")
    return errors


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="S2000 digital dash UI harness")
    p.add_argument("--check", action="store_true", help="Compare ahash against goldens")
    p.add_argument("--compare", action="store_true", help="Also write OEM side-by-sides")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    from gauge_ui import build_fonts, init_pygame

    pygame, _screen = init_pygame(windowed=True, headless=True)
    fonts = build_fonts(pygame)
    hashes = render_scenes(pygame, fonts, HARNESS_DIR)
    for name, digest in hashes.items():
        print(f"{name} {digest}")

    if os.environ.get("UPDATE_GOLDENS") == "1":
        write_goldens(hashes)
        print(f"wrote {GOLDEN}")

    rc = 0
    if args.check:
        errors = check_hashes(hashes, load_goldens())
        for err in errors:
            print(err, file=sys.stderr)
            rc = 1
        if not errors:
            print("harness ahash OK")

    if args.compare:
        from compare_oem import main as compare_main

        rc = rc or compare_main()

    pygame.quit()
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
