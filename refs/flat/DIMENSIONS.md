# Face dimensions - the arc lock

Canonical geometry for the **AP1** (default) and **AP2** face styles. The
numbers live in **`src/face_spec.py`** - this page explains them; if the
two disagree, the Python wins. The spec exports the same lock to the web
harness (`apps/harness/lib/faceSpec.json`) and the replace-face CAD
(`cad/replace_face/face_lock.scad`), so pygame, SVG and the printed mask
cannot drift apart.

Percentages are of the **module bounding box**, origin top-left. `x`,
`w` and every radius are fractions of module **width**; `y` and `h` are
fractions of module **height**. Arc centres are given in both.

Physical envelope (OEM face, estimated): **170 mm × 72.3 mm** → **2.35:1**.

## Evidence

- OEM lit photo: `refs/oem/lit/lit_ap1_carspy_cluster.jpg` (Car Spy, CC BY 2.0)
- OEM plates and calliper JSON: `refs/oem/plates/`
- AP2 reference (interpretive): `refs/oem/ap2/`
- Flat elevation (historic, parabola era): `refs/flat/ap1_cluster_flat.svg`
- Measurement script: `scripts/measure_oem_ui.py` (perspective-corrected
  landmarks from the Car Spy photo; circle fit through the 0/5/9 ticks)

## What changed from the parabola lock

The previous lock drew the tach as a quadratic bezier and placed elements
by eyeballed `%` constants spread across `gauge_ui.py`. Fitting a circle
through the OEM tick marks shows the real cluster is a **true circular
arc** whose centre sits well **below** the module - the band is a shallow
cap, not a parabola - and the hood crown is **concentric** with it: the
band hugs the cowl with a constant hairline gap all the way round.
Everything below is derived from that one circle.

## Silhouette

| Item | AP1 / AP2 |
| --- | --- |
| Module aspect | **2.35:1** |
| Bottom | flat |
| Hood crown | circle **concentric with the tach** `(50 %, 130 % H)`, r = band `r_out` + **1.4 % W** well = **55.7 % W**; cowl lip **1.8 % W** outside it |
| Crown top | y ≈ **0.5 %** (constant gap over the band apex; the lip rises just past the module top) |
| Spring line | y = **58 %** - crown meets the flat lower bezel; springs land at x ≈ 5 % / 95 % |
| Lower bezel | full width below the spring; strip and buttons live here |

## Tach arc

| Item | AP1 | AP2 |
| --- | --- | --- |
| Centre | `(50 %, 130.0 % H)` | same (shared housing, concentric crown) |
| Band outer / inner radius | 54.3 % / 51.0 % W | same |
| Baseline (white line) radius | 50.6 % W | same |
| Numeral radius | 47.6 % W | same |
| 0 → 9 sweep (screen angles) | **−127.8° → −52.2°** (75.6°) | −132° → −74° (58°) |
| 0 tick / 9 tick | (19 %, 36 %) / (81 %, 36 %) | (16 %, 42 %) / (64 %, 16 %) |
| Band apex | y ≈ **2.4 %** | same |
| Numeral 0 / 5 | (21 %, 42 %) / (52 %, 18 %) | (18 %, 47 %) / (41 %, 20 %) |
| First division | 0 → 1 is **60 %** of a division (OEM squeezes the idle band) | same |
| Hatches | amber overrun below 0 and red above 9, **5.5°** each, 5 blocks | 6.5° |

The tach is a **bar graph**: amber cells light from 0 up to the current
rpm in 100 rpm steps with a 0.22° gap between cells; the red hatch lights
past 9. There is no needle.

## Face layout - AP1

| Item | Placement |
| --- | --- |
| Speed window | rect **(39 %, 30 %) 22 × 24 %**, 3-digit 7-seg (ghost `188`), digit h = 20 % H, right edge 59.6 %; `mph` (unlit) over `km/h` to the right |
| ODO / TRIP window | rect **(39 %, 57 %) 22 × 13 %**; 6-digit odo (h 5.6 %) at y 64.8 %; `TRIP A` + `xxx.x` (h 5.0 %) at y 65.5 % |
| TEMP | **horizontal 8-block bar** at **(13 %, 52 %) 16 × 5.5 %**, left of the speedo; thermometer icon above, `C` / `H` hugging the bar ends, white underline exactly bar-wide touching the block bottoms |
| FUEL | **horizontal 16-block bar** at **(81.5 %, 46.5 %) 11 × 4.5 %**, right of the speedo; pump icon above, `E` / `F` hugging the bar ends, underline exactly bar-wide touching the block bottoms |
| Arc telltales | round wells in the well: **←** (35 %, 34 %), **→** (65 %, 34 %), high beam (71 %, 42 %) |
| Telltale strip | rect **(15.5 %, 74.5 %) 75 × 14 %**: BRAKE 19 %, battery 26 %, oil 32 %, CEL 39 %, ABS 46 %, MAINT 55 %, EPS 64 %, SRS 72 %, seatbelt 80 % |
| Lower panels | left (6 %, 61.5 %) 18.5 × 9 %; right (79 %, 59 %) 14.5 × 9 % |
| Buttons | −/+ at (6 %, 81.5 %) / (11.8 %, 81.5 %), d 5 % W; **SEL** (93.5 %, 74.5 %), **TRIP** (97.8 %, 74.5 %), ovals 4 × 6 % |
| Printed legends | `PUSH CANCEL` at (15.7 %, 93.5 %); `mph·km/h` at (90 %, 86 %); `x1000r/min` under the 0 numeral |

Temp blocks idle at 3–4 of 8 across the whole normal range and climb
quickly toward H (`temp_segments_lit`, knee at 85 % of the window).

## Face layout - AP2 (interpretive)

Same housing and crown. Differences: shorter tach sweep ending at 2
o'clock, **stacked arched TEMP / FUEL** on the right - TEMP (69 %, 31 %)
15 × 17 %, FUEL (75.5 %, 54 %) 15 × 17 %, 10 blocks each - a **clock**
row at (39 %, 59 %), SRS in the well beside the left arrow, a wider
telltale strip (22 % → 84.5 %) and SEL/TRIP pushed to the corners.
`refs/oem/ap2/` is reference, not a plate.

## Digits

`src/lcd_digits.py` / `SevenSeg.tsx`: digit w = 0.58 h, gap 0.20 h,
stroke 0.155 h, hairline segment gap 0.016 h, chamfered outer corners
0.045 h, mitred 45° joints. Unlit `8` ghost behind every glyph, colons
and points as squares. Speed/odo/trip glow through a red LCD bloom.

## Fonts

Tach numerals and legends: **M PLUS Rounded 1c** Bold / ExtraBold (OFL,
`assets/fonts/`). READY card: Oxanium. Both bundled for pygame and the
harness.

## What not to regress

- A **parabolic** or bezier tach - the OEM arc is circular
- A needle - the OEM tach is a segmented bar graph
- Vertical TEMP / FUEL stacks on AP1 (they flank the speedo horizontally)
- AP2 arched gauges copied onto AP1
- Neon cyan high beam (ISO blue) or a cyan sweep
- Fake 3D cabin ellipses; module aspect drifting off 2.35:1
- Numerals outside the band (they sit **inside**, along the inward normal)
- Typing geometry into `gauge_ui.py`, `ClusterFace.tsx` or a `.scad` by
  hand - change `face_spec.py` and re-export

## Driver map

| Visual landmark | Driven by (`face_spec.py`) |
| --- | --- |
| Band shape / apex / ends | `ArcSpec.cx cy r_out r_in a0_deg a9_deg` |
| Tick + numeral placement | `r_line r_num num_inset tick_major tick_minor` |
| Hood crown | `crown_cy crown_r crown_lip spring_y` |
| Windows and bars | `speed odo temp fuel` rects + `*_digit_h *_cy` |
| Telltales | `arc_lamps strip_lamps panel_lamps` (`LampSpot`) |
| Buttons / legends | `btn_* oval_* cancel_* units_label` |

Regenerate everything downstream with `uv run python src/face_spec.py`
(JSON + SCAD) and `bash cad/replace_face/export.sh` (meshes).
