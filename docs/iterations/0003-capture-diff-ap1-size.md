# Iteration 0003 - size track, amber band thickness

## Carryover

iter 0002 (PR #51) raised the band parabola via `ARCH_RISE_PCT 0.28 → 0.60`
and landed band ends at 55.7 % of module height (OEM 56 %). Numerals 0/9
followed into the well. The band shape now matches, but its **radial
depth** was still half of OEM.

## Capture

- UI live shot rebaked: `docs/assets/compare/compare_ap1_lit_live.png`
- OEM side: `refs/oem/lit/lit_ap1_carspy_cluster.jpg`
- Reference callipers: `refs/oem/plates/oem_ap1_measurements.{json,png}`

## Diff (size track only)

| Element | OEM | UI before | UI after | Verdict |
| ------- | --- | --------- | -------- | ------- |
| Band radial depth (along inward normal) | ~10–12 % of mh (~50–60 px on 752 mh) | 4.3 % of mh (`TACH_BAND_OUTER = 32`) | **7.4 % of mh (`TACH_BAND_OUTER = 56`)** | match |
| Redline blocks (8–9) | thick, fill the band depth | thin (30 px) | 54 px, fill band depth | match |
| Major ticks (1–7) | ~22 px vertical bars normal to curve | 22 px (fixed) | 22 px (unchanged) | match |
| Minor ticks (between majors) | ~13 px vertical bars normal to curve | 13 px (fixed) | 13 px (unchanged) | match |

The **only** knob touched is `TACH_BAND_OUTER`. Ticks are sized
independently via `TACH_TICK_MAJOR` / `TACH_TICK_MINOR` (no change).
Chevron needle (`TACH_NEEDLE_TIP` / `TACH_NEEDLE_TAIL`) is independent
(no change).

## Why 56 px

Visual calliper on the OEM photo: the band's outer edge lands just above
the 0 / 9 numerals, ~50–60 px below the curve. `TACH_NUM_INSET + 14`
(54 + 14 = 68 px) is the numeral drop - the band outer edge must sit
inside that. Picking 56 leaves a 12 px gap from band edge to numeral,
mirroring the OEM photo.

## Scope (single track, single intent)

- Raise `TACH_BAND_OUTER` from `32.0` to `56.0` in `src/gauge_ui.py`
- Update `tests/test_gauge_ui.py::FaceGeomTests::test_tach_numerals_sit_inside_the_well`
  - assert numerals + extra end² drop clear the band edge (was asserting
  raw `TACH_NUM_INSET > TACH_BAND_OUTER`)
- Rebake `tests/harness/goldens.json`
- Rebake `docs/assets/compare/*.png` and `shots/*.png`

## Not in scope (deferred)

- Amber orange tint - colour track
- TEMP / FUEL y position (50.5 % vs OEM ~53 %) - position track
- Speed centre y (40 % vs OEM 46 %) - position track (deferred)
- Tach numeral typeface / weight - font track
- Boot motion timings - motion track
- Telltale glyph art - graphics track
- Dead-code removal (`TACH_END_Y_PCT`, `TACH_R_*`, `TACH_START_DEG`,
  `TACH_SPAN_DEG`, `tach_angle`, `tach_point` exports) - housekeeping

## Acceptance

- `uv run pytest tests/` → 103 passed
- `SDL_VIDEODRIVER=dummy uv run python src/gauge_ui.py --smoke
  --screenshot shots` → exits 0
- `uv run python scripts/compare_oem.py` → all five PNGs rebaked
- `compare_ap1_lit_live.png`: amber band now fills ~10 % of module
  height (was ~4 %), redline blocks now fill the band depth - visually
  matches OEM
- Numerals 0 / 9 still sit 12 px below the band outer edge in the well
- `DIMENSIONS.md` module lock (aspect 2.35:1, side notches 58–72 %)
  holds within ±0.5 %

## Verify (objective)

- [x] `git diff src/gauge_ui.py` is exactly one constant tweak
- [x] `tests/test_gauge_ui.py` diff is one assertion update
- [x] no graphics / colour / position / motion / font touches
- [x] no docs / CAD / icon asset edits beyond `goldens.json` +
      `docs/assets/compare/*.png` + `shots/*.png` re-bakes
- [x] pytest 103 passed
- [x] smoke exits 0
- [x] composite eyeball: band depth matches OEM
- [x] ahash goldens within tolerance after rebake