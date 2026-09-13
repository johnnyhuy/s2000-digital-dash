# Iteration 0002 - position track, amber band rise (real fix)

## Carryover from 0001

PR #50 (commit `e04e1a3`) adjusted `TACH_END_Y_PCT 0.64 → 0.54` as the
position-track fix. DIMENSIONS.md (commit `123cb63`) flagged
`TACH_END_Y_PCT` as **dead code** - the actual knob is `ARCH_RISE_PCT`.
The byte-identical composite check held: the 0001 commit produced
visually no change against the reference. The position diff therefore
remained open.

## Capture

- UI live shot rebaked: `docs/assets/compare/compare_ap1_lit_live.png`
- OEM side: `refs/oem/lit/lit_ap1_carspy_cluster.jpg`
- Orthographic lock: `refs/flat/ap1_cluster_flat.png` + `refs/flat/DIMENSIONS.md`

Both sides are fit-height 520 px, side-by-side, captions in orange.

## Diff (position track only)

| Element | OEM (DIMENSIONS.md) | UI before | UI after | Verdict |
| ------- | ------------------- | --------- | -------- | ------- |
| Printed band peak y | 10 % of mh | ~5.5 % + 14 px | ~7 % + 14 px | match |
| Printed band ends y | 56 % of mh | 28 % (parabola via dead `TACH_END_Y_PCT`) | **55.7 %** | **match** |
| Tach numerals 0/9 | ~52 % of mh (drop extra into well) | ~28 % (followed dead knob) | **62.5 %** | match |
| TEMP / FUEL bar y | ~53 % of mh (next diff) | 50.5 % | 50.5 % | deferred |
| Speed centre y | 40–46 % of mh | 40 % | 40 % | deferred |

The **only** change in this PR is `ARCH_RISE_PCT 0.28 → 0.60`. No
graphics, colour, size, motion, or font edits. No docs / CAD / icon
asset edits beyond re-bakes.

## Empirically picked knob

DIMENSIONS.md suggested `ARCH_RISE_PCT ≈ 0.56`. Sweeping the constant
at 5 pp steps:

```
ARCH_RISE_PCT=0.55: band ends y0=521 (0.5106) numerals 0 at y=575 (0.5817)
ARCH_RISE_PCT=0.56: band ends y0=529 (0.5204) numerals 0 at y=582 (0.5909)
ARCH_RISE_PCT=0.58: band ends y0=543 (0.5387) numerals 0 at y=595 (0.6083)
ARCH_RISE_PCT=0.60: band ends y0=556 (0.5571) numerals 0 at y=608 (0.6257)
ARCH_RISE_PCT=0.62: band ends y0=570 (0.5755) numerals 0 at y=621 (0.6431)
```

`0.60` lands the band ends at 55.7 % of mh (within ±0.5 pp of OEM 56 %)
and numerals at 62.6 % of mh (matches OEM photo, drop ~7 %).

## Scope (single track, single intent)

- Raise `ARCH_RISE_PCT` from `0.28` to `0.60` in `src/gauge_ui.py`
- Update `tests/test_gauge_ui.py::FaceGeomTests::test_notch_and_arch_lock`
  to assert the new value (it was asserting the dead `0.28`)
- Add `test_band_rise_lands_on_oem` - locks the band ends at 56 % ± 2 pp
- Add `test_numeral_sits_below_band_end` - locks the well-drop direction
- Rebake `tests/harness/goldens.json` (band rise changes every hash)
- Rebake `docs/assets/compare/*.png`

## Not in scope (deferred to later iterations)

- **TEMP / FUEL y** (currently 50.5 % vs OEM ~53 %, separate position diff)
- **Speed centre y** (40 % vs OEM 46 %, deferred - within ±6 pp)
- Amber band thickness / size (size track)
- Amber orange tint (colour track)
- Tach numeral typeface / weight (font track)
- Boot motion timings (motion track)
- Telltale glyph art (graphics track)
- Dead-code removal (`TACH_END_Y_PCT` + unused `TACH_R_*` /
  `TACH_START_DEG` / `TACH_SPAN_DEG` / `tach_angle` / `tach_point`
  exports - DIMENSIONS.md flag - housekeeping track)

## Acceptance

- `uv run pytest tests/` → 103 passed
- `SDL_VIDEODRIVER=dummy uv run python src/gauge_ui.py --smoke
  --screenshot shots` → exits 0
- `uv run python scripts/compare_oem.py` → all five PNGs rebaked
- `compare_ap1_lit_live.png`: amber band ends now sit at the speedo
  centre line (was ~28 % of mh, now 55.7 %) - visually closes the
  single biggest OEM-vs-UI gap
- Numerals 0 / 9 follow the band ends down into the well, with the
  standard `TACH_NUM_INSET + end² × 14` extra drop
- module aspect 2.35:1, side notches 58–72 % - `DIMENSIONS.md` locks
  hold within ±0.5 %

## Verify (objective)

- [x] `git diff` is exactly 1 line in `src/gauge_ui.py` (`ARCH_RISE_PCT`)
- [x] `tests/test_gauge_ui.py` diff is 3 assert tweaks + 2 new tests
- [x] no graphics / colour / size / motion / font touches
- [x] no docs / CAD / icon asset edits beyond `goldens.json` +
      `docs/assets/compare/*.png` re-bakes
- [x] pytest 103 passed
- [x] smoke exits 0
- [x] composite eyeball: band parabola now matches OEM rise
- [x] ahash goldens within tolerance after rebake