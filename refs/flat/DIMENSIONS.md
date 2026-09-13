# AP1 face dimensions (flat / orthographic)

Canonical lock for the **AP1** face style. Copied from the OEM flat elevation
(`ap1_cluster_flat`) and remeasured against the Car Spy photo
(`refs/oem/lit/lit_ap1_carspy_cluster.jpg`, CC BY 2.0). Percentages are of
the **module bounding box**, origin top-left. The **AP2** style is a
separate layout family (arched side gauges); do not copy those percentages
here.

Physical envelope (OEM face): **170 mm × 72.3 mm** → aspect **2.35:1**.

## Evidence

- Flat elevation: `refs/flat/ap1_cluster_flat.svg` / `.png`
- OEM photo: `refs/oem/lit/lit_ap1_carspy_cluster.jpg` (1600×1200)
- Calliper plate: `refs/oem/plates/oem_ap1_measurements_plate.png`
- Calliper data: `refs/oem/plates/oem_ap1_measurements.json`

Remeasured against the Car Spy photo (module ≈ 480 px tall):

| Landmark | px | % of module |
| --- | --: | --: |
| Cluster cowl top | 240 | 0.0 |
| Hood peak (top of printed band arch) | 290 | 10.4 |
| Band right end (redline blocks, 9 mark) | 510 | 56.2 |
| Numeral 9 (visual centre) | 525 | 59.4 |
| Lamp / hardware strip top | 615 | 78.1 |
| Cluster bottom | 720 | 100.0 |

In-repo flat lock matches the OEM numbers for the band (~54 % at the
0-tick vs 56 % in OEM — within ±2 pp). The lamp strip sits a touch higher
in OEM (78 %) than in the lock (85 %), because the OEM lamp strip is the
top of the SEL/TRIP row, while the lock draws the full telltale band
thicker.

## Module on the 1920×1080 canvas

| Item | Value |
| --- | --- |
| x | 4.0 % of canvas |
| w | 92.0 % of canvas |
| aspect (w:h) | **2.35:1** |

## Silhouette (percent of module)

| Item | Value |
| --- | --- |
| Bottom | **flat** |
| Side notches | rectangular, **y = 58–72 %**, depth 4.4 % of width |
| Top arch | quadratic bezier, peak at module top, spring line ≈ 32 % (eyeballed — cowl spring is hard to pin through the wheel rim) |
| Arch peak | y ≈ **10 %** (printed band peaks here; the cowl above is a thin lip) |
| Arch spring | y ≈ **56 %** (where the band's printed curve straightens to the bezel verticals) |

## Face layout (percent of module)

| Item | Placement |
| --- | --- |
| Speed centre | **(50 %, 68 %)** — **3-digit 7-seg** (ghost `188`); units (`km/h`) to the **right** of the digits. Sits BELOW the printed band ends (band ends at ~56 % mh) — OEM Car Spy photo. |
| ODO / TRIP | directly under the speed (~74 % y): 6-digit odo + `TRIP A` `xxx.x` (ghost `888888` / `888.8`) |
| TEMP bar | **horizontal** C→H **left of the speedo** at **(8.0 %, 68.0 %)**, **w = 16 %**, **h = 1.2 %** — **6** thin coolant ticks. Bar sits at the speedo centre, not mid-arch. |
| FUEL bar | **horizontal** E→F **right of the speedo** at **(76.0 %, 68.0 %)**, same w / h — finer tick ladder |
| TEMP icon | thermometer above **C** |
| FUEL icon | pump above **F** |
| Lamp / hardware strip | y ≈ **78 %** (OEM Car Spy, top of SEL/TRIP row) — note: flat lock draws the lamp band at 85 % to give the bezel room |
| Printed tach band | peak ≈ **10 %**, ends (0 / 9) at **56 %** of module height; rise ≈ **46 %**; parabola passes through (peak, end_y) at u ∈ [−1, 1] |
| Tach numerals | inside the well, **~3 % below the band ends** for 0/9, **~28 % below the band peak** for the middle (4/5/6); drop varies with `1 − end²` so the middle numerals sink into the well |
| Redline | printed red zone **8–9** with five thick blocks |

Hardware strip, left → right:

- `−/+` rocker; brightness dial + **PUSH CANCEL** under the rocker
- OEM telltales (self-test order, after the signal pair):
  **←** (green), high beam (blue), **ABS** (amber), **BRAKE** (red),
  battery (red), oil (red), CEL (amber), immobilizer key (green),
  **MAINT REQ'D** (amber), **EPS** (amber), seatbelt (red), door (red),
  **SRS** (red), **→** (green)
- **SEL** oval + **TRIP** oval

AP1 style = these **horizontal bars flanking the speed/odo**. AP2 arched
TEMP/FUEL is a separate family — do not copy it here.

A vertical TEMP/FUEL stack was tried against a misread of the live photo
and is **erroneous**. Do not merge vertical side gauges into this lock.

Protocol JSON fields stay `rpm`, `speed_kmh`, `fuel_pct`, `ect_c`, `batt_v`,
`odo_km`, plus the existing `lamps` keys.

## What not to regress

- **Vertical** TEMP / FUEL side stacks (erroneous; OEM AP1 is horizontal flanking bars)
- AP2 arched corner gauges copied onto AP1
- 45° chamfer instead of the **rectangular** 58–72 % notches
- Semicircle / superellipse crown instead of a quadratic bezier
- Units stacked under the speed
- Lamps as large labelled chips on the LCD (use OEM telltale artwork)
- Neon cyan high beam or sweep (high beam is ISO blue)
- Fake 3D cabin ellipses
- Module aspect drifting off **2.35:1**
- Tach numerals sitting **outside** the printed band (OEM AP1 puts 0–9 in the well)
- The **printed band** ending at the **parabola's spring line** — the band parabola is
  steeper than the cowl arch and the band ends sit ~25 pp **below** the cowl spring

## Driver map (which constant moves what)

The face geometry is built in `src/gauge_ui.py::build_face_geom`. The
rendering path uses `g.lcd_peak_y` and `g.lcd_spring_y` for the printed
band parabola via `tach_arch_xy` — not the global `TACH_END_Y_PCT`. As of
this revision:

| Visual landmark | Driven by | Default value |
| --- | --- | --- |
| Printed band peak y | `LCD_TOP_PCT` + `TACH_ARCH_DROP` | `0.085 + 14 px` (band peak at 10.4 % mh, OEM match — iter 0007) |
| Printed band end y | `(LCD_TOP_PCT … ARCH_RISE_PCT) × 0.92` | `ARCH_RISE_PCT = 0.60` (lands band ends at ~56 % of mh — iter 0002 position PR) |
| Tach numerals 0 / 9 | vertical drop = `TACH_NUM_DROP_BASE` (15 px) + `TACH_NUM_DROP_PEAK × (1 − end²)`; horizontal inset `TACH_NUM_X_INSET` (50 px) along inward normal | OEM 0/9 just under band ends (~3 % drop), middle numerals deep in the well (~28 % drop) — iter 0007 |
| Tach numerals 5 | same formula, peak at end² = 0 → drop = base + peak = 208 px (38.1 % mh, OEM match) | iter 0007 |
| Band peak y | `LCD_TOP_PCT` + `TACH_ARCH_DROP` | `0.085 + 14 px` (band peak at 10.4 % mh, OEM match — iter 0007; was `0.055` which put the peak too high at 7.3 % mh) |
| Speed centre y | `SPEED_Y_PCT` | `0.68` (iter 0006 — OEM Car Spy puts the speed BELOW the band ends) |
| ODO row y | `ODO_Y_PCT` | `0.74` (iter 0006 — odo sits just under speed, just above the lamp strip top) |
| TEMP / FUEL bar y | `TEMP_Y_PCT` / `FUEL_Y_PCT` | `0.68` (iter 0006 — bars flank the speedo at the speed y, not mid-arch) |

### Iter note — lamp strip top

OEM Car Spy puts the SEL/TRIP top at **78 %**. The flat lock draws the
full lamp band at **85 %** to leave room for the bezel lip. Both are
correct for their purpose; the **face layout lock** quotes the OEM
78 %, and the SVG/PNG flat lock keeps the visual 85 % for the band.