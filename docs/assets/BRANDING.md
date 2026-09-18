# DIY cluster marks

`honda-h-mark.svg` and `s2000-badge.svg` are **retraces** of generated
reference plates in `docs/assets/brand/`. They are original vector
drawings for this unofficial DIY cluster — **not** Honda Motor Co., Ltd.
trademark artwork, and this project is not affiliated with or endorsed
by Honda.

- Honda H-mark: squircle ring + pill-ended H, taken off
  `brand/honda-h-mark-ref.png` (S2000-era steering-wheel plate)
- S2000 badge: italic five-glyph wordmark, taken off
  `brand/s2000-badge-ref.png`

The older geometric H (`honda-unofficial-mark.svg`) stays in the tree
as history. The live GitHub repo is `johnnyhuy/s2000-digital-dash`.

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
silhouettes under `assets/icons/`, tinted at draw time. The web strip
draws the same pictograms inline (`LampIcons.tsx`).

Boot motion is the car's ignition self-test (bar 0→9, all lamps, `188`)
then a READY card with the retraced H and S2000 badge, then reveal.
Preset buttons on the web harness snap the face so Idle / Cruise / VTEC /
Warn are readable immediately. Switching AP1 / AP2 replays the boot.
PUSH CANCEL is a small dial mark beside its legend under the −/+ rocker.
