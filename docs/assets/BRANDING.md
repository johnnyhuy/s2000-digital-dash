# Unofficial DIY branding

The title mark in `honda-unofficial-mark.svg` is an **original geometric H**
drawn for this repository.

- **Not** Honda Motor Co., Ltd. trademark artwork
- **Not** the Honda wing logo
- **Not** the official Honda H-mark / grille badge

If someone asks for a “Honda logo SVG”, ship this file and the README
disclaimer. Do **not** scrape, download, or embed official Honda brand
assets.

Same mark is copied to `apps/harness/public/docs/assets/` for the web demo.

Product name in docs and chrome is **S2000 Digital Dash** (AP1 + AP2 faces).
The live GitHub repo is `johnnyhuy/s2000-digital-dash`. See the root README.

Cluster type is **M PLUS Rounded 1c** Bold / ExtraBold (tach numerals,
C/H, E/F, bezel and LCD legends) - the closest OFL match to the OEM plate's
rounded gothic. **Oxanium** sets the READY card and masthead; **Share Tech
Mono** is the harness JSON / protocol face. Speed and odo are **red 7-seg**
with mitred 45° joints, matching the AP1 photo. Faces live under
`assets/fonts/` (SIL OFL); the web harness self-hosts the same files from
`apps/harness/app/fonts/`. DejaVu remains the pygame fallback when those
files are absent.

The tach is the OEM **bar graph on a true circular arc**: an unlit band
grading `#6c380e` → `#ac5c18` toward both ends with hairline cell lines,
amber `#f49420` cells lighting in 100 rpm steps, amber hatch below 0 and
red hatch above 9 (`#ff3c28` when lit). There is no needle in either
renderer. The hood crown is a second circle with a thin off-white lip just
outside the band. LCD red is `#ff4228` with a faint `#4a0c0e` 188 / 888888
ghost and a soft bloom. The LCD well is near-black with a quiet vignette,
not a brown overlay. TEMP uses the OEM coolant pictogram
(stem, bulb, ticks, two waves); FUEL is a pump with window, hose, and
nozzle. Telltales: red `#e22820`, amber `#ec941c`, green `#22b84c`, ISO
high-beam blue `#1c54d8` (never neon cyan). Off lamps sit just above black
(`#1a1816` on the web strip, `#1a1816` in pygame) so the row still reads
without competing with lit bulbs. Icons are white-on-transparent ISO
silhouettes (hollow battery with +/−, oil-can with drop, 3-ray outlined
high-beam D, CEL with CHECK punched through the block, filled key bow,
person with sash and arm nubs, top-down car with both doors ajar) under
`assets/icons/`, tinted at draw time. The web strip draws the same
pictograms inline (`LampIcons.tsx`) so CSS masks cannot collapse them.
Word lamps set in M PLUS Rounded 1c. Tach numerals sit **inside** the
well along the inward normal of the arc, ticks hang from the white
baseline. Analog lag on RPM; green turn lamps pulse at about 85
flashes/min after the strike; the red hatch lights past 9. Boot motion is
sweep comet along the band → READY glow → reveal settle with a bulb check.
Preset buttons on the web harness snap the face so Idle / Cruise / VTEC /
Warn are readable immediately. PUSH CANCEL is a small dial mark beside its
legend under the −/+ rocker, matching the OEM bezel.
