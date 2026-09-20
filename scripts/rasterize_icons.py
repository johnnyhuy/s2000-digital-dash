#!/usr/bin/env python3
"""Rasterise ``assets/icons/*.svg`` to white-on-transparent PNGs via rsvg.

Prefer this over pygame drawers so the committed PNG matches the SVG plate.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets" / "icons"

KINDS = (
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
    "atlas",
    "trunk",
    "airbag",
    "coolant",
    "fuel",
)


def rasterize(kind: str, height: int = 96) -> Path:
    svg = ASSETS / f"{kind}.svg"
    png = ASSETS / f"{kind}.png"
    if not svg.is_file():
        raise FileNotFoundError(svg)
    rsvg = shutil.which("rsvg-convert")
    magick = shutil.which("magick") or shutil.which("convert")
    if rsvg:
        subprocess.run(
            [rsvg, "-h", str(height), str(svg), "-o", str(png)],
            check=True,
        )
    elif magick:
        subprocess.run(
            [
                magick,
                "-background",
                "none",
                "-density",
                "192",
                f"SVG:{svg}",
                "-resize",
                f"x{height}",
                str(png),
            ],
            check=True,
        )
    else:
        raise FileNotFoundError("rsvg-convert or ImageMagick convert")
    return png


def main() -> None:
    for kind in KINDS:
        h = 72 if kind == "atlas" else 96
        path = rasterize(kind, height=h)
        print(f"{path.relative_to(ROOT)} {path.stat().st_size}")


if __name__ == "__main__":
    try:
        main()
    except FileNotFoundError as exc:
        sys.exit(f"rsvg-convert missing or SVG not written: {exc}")
