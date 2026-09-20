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

Provisional design envelope (not a measured OEM face): **170 mm × 72.3 mm** → **2.35:1**.

## Evidence

- OEM lit photo: `refs/oem/lit/lit_ap1_carspy_cluster.jpg` (Car Spy, CC BY 2.0)
- Historic illustrative plates and estimated measurement JSON: `refs/oem/plates/`
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
| Hood crown | circle **concentric with the tach** `(50 %, 148.7 % H)`, r = band `r_out` + **1.4 % W** well = **60.4 % W**; cowl lip **1.8 % W** outside it |
| Crown top | y ≈ **2.6 %** (lip) then a dark well; band apex at **10 % H** |
| Spring line | y = **58 %** - crown meets the flat lower bezel; springs land at x ≈ 5 % / 95 % |
| Lower bezel | full width below the spring; strip and buttons live here |

## Tach arc

| Item | AP1 | AP2 |
| --- | --- | --- |
| Centre | `(50 %, 148.7 % H)` | same (shared housing, concentric crown) |
| Band outer / inner radius | 59.0 % / 55.7 % W | same |
| Baseline (white line) radius | 55.3 % W | same |
| Numeral radius | 51.9 % W | same |
| 0 → 9 sweep (screen angles) | **−127.8° → −52.2°** (75.6°) | −132° → −74° (58°) |
| 0 tick / 9 tick | (17 %, 47 %) / (83 %, 47 %) | (13 %, 53 %) / (65 %, 25 %) |
| Band apex | y ≈ **10 %** | same |
| Numeral 0 / 5 | (18 %, 53 %) / (50 %, 28 %) | (15 %, 58 %) / (41 %, 30 %) |
| First division | 0 → 1 is **60 %** of a division (OEM squeezes the idle band) | same |
| Hatches | amber overrun below 0 and red above 9, **5.5°** each, 5 blocks | 6.5° |

The tach is a **bar graph**: amber cells light from 0 up to the current
rpm in 200 rpm steps with a 0.16° gap between cells; the red hatch lights
past 9. There is no needle.

## Face layout - AP1

| Item | Placement |
| --- | --- |
| Speed window | **(39 %, 35 %) 21 × 21.8 %**; digit height **19.4 % H**, right edge 59 % W |
| ODO / TRIP window | **(39 %, 58.2 %) 21 × 11.8 %**; digit heights 5.2 % / 4.8 % H, centres y 66.1 % |
| TEMP | horizontal 8-block bar **(13.5 %, 58.6 %) 12.5 × 3 %**, C/H clear of both ends |
| FUEL | horizontal 16-block bar **(74.7 %, 58.6 %) 12.5 × 3 %**, E/F clear of both ends |
| Side symbols | shared coolant / fuel SVG masters; silhouette height **2.2 % W** |
| Arc telltales | left (33.5 %, 45.5 %), right (67.5 %, 45.5 %), high beam (72 %, 53.5 %) |
| Warning pockets | ABS left; low fuel, belt and SRS right, centred y 68.2 % |
| Lower strip | brake, battery, oil, CEL, immobilizer, maintenance, cruise, EPS, trunk, door |
| Hardware | retained −/+, SEL/TRIP and bezel marks; custom Honda/S2000 lockup is not factory face printing |

These are photo-derived design proportions, **not a pixel-perfect OEM measurement**. Lamp locations were checked against Honda's 2003 manual p.45 and 2005 manual p.39; those are North American diagrams, so market-specific legends still need checking against the actual 2001 Australian car. The brake (!) symbol is retained from this project's reference variant.

Temp blocks idle at 3–4 of 8 across the whole normal range and climb
quickly toward H (`temp_segments_lit`, knee at 85 % of the window).

## Face layout - AP2 (interpretive)

Same housing and crown. Differences: shorter tach sweep ending at 2
o'clock, **stacked arched TEMP / FUEL** on the right - TEMP (69 %, 31 %)
15 × 17 %, FUEL (75.5 %, 54 %) 15 × 17 %, 10 blocks each - a **clock**
row at (39.2 %, 61 %), SRS in the well beside the left arrow, a wider
telltale strip (22 % → 84.5 %) and SEL/TRIP pushed to the corners.
`refs/oem/ap2/` is reference, not a plate.

## Digits

`src/lcd_digits.py` / `SevenSeg.tsx`: digit w = 0.58 h, gap 0.20 h,
stroke 0.155 h, hairline segment gap 0.016 h, chamfered outer corners
0.045 h, mitred 45° joints. Unlit `8` ghost behind every glyph, colons
and points as squares. Speed/odo/trip use red segments without software bloom or synthetic pixel-grid lines.

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

## Replacement display fit

`--car` contains the 2.35:1 face in the available pygame canvas on both axes. `/display` does the same for the SVG (including its cowl padding). Unused pixels stay black. A 7-inch diagonal alone does not determine resolution, active width, orientation or mounting alignment.

At the **provisional** 154 mm active width, the AP1 speed digit is about 12.7 mm tall, odo digits about 3.4 mm, and a 2.2 % W symbol about 3.4 mm. These are design estimates, not measurements of the user's OLED. Geometry and digit bounds are exercised at 800×480, 1280×720 and 1920×1080; containment also covers 1920×720 and 1280×400.
