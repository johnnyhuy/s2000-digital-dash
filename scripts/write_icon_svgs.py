#!/usr/bin/env python3
"""Write AP1 telltale SVGs traced from OEM lamp-strip / self-test plates.

Source of truth is the OEM silhouettes (ISO 2575 wording + Honda AP1
pictograms), not crude boxes. Rasterise with ``scripts/rasterize_icons.py``.

Plates live in ``refs/oem/plates/`` (atlas + pictogram close-ups generated
from the Car Spy AP1 frame and the self-test lamp-strip descriptions).
"""

from __future__ import annotations

import shutil
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "assets" / "icons"
HARNESS = ROOT / "apps" / "harness" / "public" / "icons"

HEADER = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {vb_w} {vb_h}" width="{vb_w}" height="{vb_h}" role="img" aria-label="{label}">
  <title>{label}</title>
  <!-- Traced / redrawn from OEM AP1 lamp-strip plates in refs/oem/plates/.
       White on transparent; tinted at draw time. Not Honda Motor Co. artwork. -->
'''
FOOT = "</svg>\n"


def wrap(name: str, body: str, vb_w: int = 64, vb_h: int = 48, label: str | None = None) -> str:
    return HEADER.format(vb_w=vb_w, vb_h=vb_h, label=label or name) + body + FOOT


# Word lamps: condensed bold gothic, matching the OEM printed legends.
WORD = (
    '  <text x="{x}" y="{y}" text-anchor="middle" fill="#fff" '
    'font-family="Barlow Condensed, DejaVu Sans, Liberation Sans, Arial Narrow, sans-serif" '
    'font-size="{size}" font-weight="700" letter-spacing="{track}">{label}</text>\n'
)


# CHECK letter holes for the CEL block (single outlines so evenodd punches).
CHECK_HOLES = (
    "M16.2 22.2h5.1v2.05h-3.05v4.5h3.05v2.05h-5.1z"
    "M22.2 22.2h2.05v3.35h1.7V22.2h2.05v8.6h-2.05v-3.2h-1.7v3.2H22.2z"
    "M29.1 22.2h5.05v2.05h-3v1.55h2.45v1.9H31.15v1.05h3v2.05h-5.05z"
    "M35.3 22.2h5.1v2.05h-3.05v4.5h3.05v2.05h-5.1z"
    "M41.5 22.2h2.1v3.15l2.55-3.15h2.35L45.3 26.4l3.35 4.4h-2.45l-2.05-2.7v2.7h-2.1z"
)

SVGS: dict[str, str] = {
    "turn_l": wrap(
        "turn_l",
        '  <path fill="#fff" d="M42.6 8.4 8.2 24l34.4 15.6v-8.2H56V16.6H42.6z"/>\n',
        label="Left turn telltale",
    ),
    "turn_r": wrap(
        "turn_r",
        '  <path fill="#fff" d="M21.4 8.4v8.2H8v15.2h13.4v8.2L55.8 24z"/>\n',
        label="Right turn telltale",
    ),
    "high_beam": wrap(
        "high_beam",
        """  <g fill="#fff">
    <rect x="3.4" y="12.4" width="22.8" height="3.5" rx="0.35"/>
    <rect x="3.4" y="22.25" width="22.8" height="3.5" rx="0.35"/>
    <rect x="3.4" y="32.1" width="22.8" height="3.5" rx="0.35"/>
    <path fill-rule="evenodd" d="M32.6 7.6h6.2C54.4 7.6 61.2 14.6 61.2 24S54.4 40.4 38.8 40.4h-6.2V7.6z M36.8 12.2v23.6h2.8c11.6 0 16.4-5.5 16.4-11.8S51.2 12.2 39.6 12.2h-2.8z"/>
  </g>
""",
        label="High beam telltale",
    ),
    "abs": wrap(
        "abs",
        WORD.format(x=32, y=31.2, size=18, track="0.9", label="ABS"),
        label="ABS telltale",
    ),
    "brake": wrap(
        "brake",
        WORD.format(x=48, y=31.2, size=17.2, track="1.15", label="BRAKE"),
        vb_w=96,
        label="BRAKE telltale",
    ),
    "battery": wrap(
        "battery",
        """  <g fill="#fff">
    <rect x="18.2" y="4.6" width="9.6" height="7" rx="0.7"/>
    <rect x="36.2" y="4.6" width="9.6" height="7" rx="0.7"/>
    <path fill-rule="evenodd" d="M9.2 12.2h45.6v31.2H9.2z M14.4 17.4h35.2v20.8H14.4z"/>
    <rect x="18.8" y="25.4" width="10.8" height="3.1"/>
    <rect x="22.65" y="21.55" width="3.1" height="10.8"/>
    <rect x="34.6" y="25.4" width="10.8" height="3.1"/>
  </g>
""",
        label="Battery telltale",
    ),
    "oil": wrap(
        "oil",
        '<g fill="none" stroke="#fff" stroke-width="3" stroke-linejoin="round">\n<path d="M17 19h23l13-7 3 4-14 17H18L10 21H4v-6h10z"/>\n<path d="M24 19v-6m-6 0h13"/>\n</g><path fill="#fff" d="M58 24c-2 4-4 6-4 9a4 4 0 0 0 8 0c0-3-2-5-4-9z"/>',
        label="Oil pressure telltale",
    ),
    "trunk": wrap("trunk", '<g fill="#fff"><path d="M5 27h8l10-10h20l10 10h6v10H5z"/><circle cx="17" cy="38" r="5"/><circle cx="48" cy="38" r="5"/><path d="m7 23-4-11 3-1 6 12z"/></g>', label="Trunk open"),
    "airbag": wrap("airbag", '<g fill="#fff"><circle cx="21" cy="8" r="5"/><circle cx="43" cy="22" r="9"/>\n<path d="M17 15h8l5 13-5 4-6-10-3 11h15l6 12h-7l-5-7H10z"/></g>', label="Supplemental restraint system"),
    "coolant": wrap("coolant", '<g fill="none" stroke="#fff" stroke-width="2.6" stroke-linecap="round"><path d="M27 27V5h6v22a6 6 0 1 1-6 0zM34 9h7m-7 7h7m-7 7h7M13 38q4-4 8 0t8 0 8 0 8 0M13 44q4-4 8 0t8 0 8 0 8 0"/></g>', label="Coolant temperature"),
    "fuel": wrap("fuel", '<g fill="none" stroke="#fff" stroke-width="3" stroke-linejoin="round"><path d="M14 41V7h22v34M9 41h32M36 19h5v15q0 7 6 7t6-7V17L43 7M45 9v10h8"/><path d="M19 12h12v10H19z"/></g>', label="Fuel pump"),
    "cel": wrap(
        "cel",
        f"""  <g fill="#fff">
    <path fill-rule="evenodd" d="M16.4 8.8h19.2c1.7 0 3.15 1.05 3.7 2.6l1.85 5.2h8.4l4.4-4.7h4.8v6.4h3.1v12.4h-3.1v6.6H8.2v-6.6H2.6V25.8h5.2v-4h6.8L15 11.4c.5-1.55 1.95-2.6 3.4-2.6z {CHECK_HOLES}"/>
  </g>
""",
        label="Check engine telltale",
    ),
    "immobilizer": wrap(
        "immobilizer",
        """  <g fill="#fff">
    <path fill-rule="evenodd" d="M17.6 5.2a16.6 16.6 0 1 0 .02 0zm0 7.2a9.4 9.4 0 1 0 .02 0z"/>
    <rect x="30.6" y="19.4" width="30.2" height="7.8" rx="1.4"/>
    <rect x="45.6" y="27" width="4.8" height="7.4" rx="0.7"/>
    <rect x="52.2" y="27" width="4.8" height="10.2" rx="0.7"/>
    <rect x="58.8" y="27" width="4.8" height="13.2" rx="0.7"/>
  </g>
""",
        label="Immobilizer key telltale",
    ),
    "maint": wrap(
        "maint",
        WORD.format(x=32, y="20.5", size=13, track="0.35", label="MAINT")
        + WORD.format(x=32, y="36.5", size=13, track="0.15", label="REQ'D"),
        label="MAINT REQ'D telltale",
    ),
    "eps": wrap(
        "eps",
        WORD.format(x=32, y=31, size=17, track="0.8", label="EPS"),
        label="EPS telltale",
    ),
    "seatbelt": wrap(
        "seatbelt",
        """  <g fill="#fff">
    <circle cx="32" cy="7.8" r="6.2"/>
    <path d="M29.4 13.4h5.2v3.2h-5.2z"/>
    <path fill-rule="evenodd" d="M18.2 18.2 25.8 16.4 29.2 19.4h5.6l3.4-3 7.6 1.8-2.4 26.6H20.6z M21.6 15.4 47.4 45h-8.8L20.2 22.2z"/>
  </g>
""",
        label="Seatbelt telltale",
    ),
    "door": wrap(
        "door",
        """  <g fill="#fff">
    <path fill-rule="evenodd" d="M24.8 2.4h14.4c2.05 0 3.9 1.15 4.8 3L48 11.8v25.8c0 1.75-1.05 3.35-2.7 4.35L38.4 46H25.6l-6.9-4.05c-1.65-1-2.7-2.6-2.7-4.35V11.8L20 5.4c.9-1.85 2.75-3 4.8-3z M27.4 8.4h9.2v8.8h-9.2z"/>
    <path d="M18.2 20.6 2.8 28.6l3.4 5.8 13.4-7.1z"/>
    <path d="M45.8 20.6 61.2 28.6l-3.4 5.8-13.4-7.1z"/>
  </g>
""",
        label="Door-open telltale",
    ),
    "srs": wrap(
        "srs",
        WORD.format(x=32, y=31, size=17, track="0.8", label="SRS"),
        label="SRS telltale",
    ),
}

def atlas_svg() -> str:
    """Review sheet of the actual masters, not another hand-maintained copy."""
    width = len(SVGS) * 72
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} 72" width="{width}" height="72">',
           f'<rect width="{width}" height="72" fill="#0a0a0a"/>']
    for i, (name, svg) in enumerate(SVGS.items()):
        view_box = re.search(r'viewBox="([^"]+)"', svg)[1]
        body = svg[svg.index('>', svg.index('<svg')) + 1:svg.rindex('</svg>')]
        colour = "#22b84c" if name in ("turn_l", "turn_r", "immobilizer") else "#1c54d8" if name == "high_beam" else "#ec941c" if name in ("cel", "abs", "eps", "maint", "fuel") else "#e22820"
        body = body.replace('"#fff"', f'"{colour}"')
        out.append(f'<svg x="{i * 72 + 4}" y="12" width="64" height="48" viewBox="{view_box}">{body}</svg>')
    return "\n".join(out) + "</svg>\n"


def main() -> None:
    DEST.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for name, svg in SVGS.items():
        path = DEST / f"{name}.svg"
        path.write_text(svg, encoding="utf-8")
        written.append(path)
        print(path.relative_to(ROOT))
    atlas = DEST / "atlas.svg"
    atlas.write_text(atlas_svg(), encoding="utf-8")
    written.append(atlas)
    print(atlas.relative_to(ROOT))
    if HARNESS.is_dir():
        for path in written:
            dest = HARNESS / path.name
            shutil.copy2(path, dest)
            print(dest.relative_to(ROOT))


if __name__ == "__main__":
    main()
