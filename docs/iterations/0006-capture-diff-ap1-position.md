# Iteration 0006 - position track, seat the LCD cluster under the band

## Carryover

iter 0002 raised the printed tach band parabola (`ARCH_RISE_PCT 0.28 → 0.60`)
and landed band ends at 55.7 % of mh (OEM 56.25 %). iter 0003 thickened the
band to OEM depth. iter 0004 retinted the bloom orange. iter 0005 removed
the dead tach-circle computation.

The next biggest OEM-vs-UI gap was the **LCD cluster sitting high** - the
speed / odo / TEMP / FUEL bars all floated in the middle of the module
instead of sitting *under* the printed band, where the Car Spy photo
clearly puts them. The ODO row locked at `0.50` of mh (mid-arch), speed at
`0.40` (top quarter), bars at `0.505` (slightly above the band ends).

The `DIMENSIONS.md` face layout table documented the buggy lock verbatim,
so the doc and the code agreed - and both were wrong.

## Capture

- UI live shot rebaked: `docs/assets/compare/compare_ap1_lit_live.png`
- OEM side: `refs/oem/lit/lit_ap1_carspy_cluster.jpg` (The Car Spy, CC BY 2.0)
- Calliper plate: `refs/oem/plates/oem_ap1_measurements.{json,png}`

Both sides are fit-height 520 px, side-by-side, captions in orange.

## Pixel sampling - measured against the OEM photo

| Element | OEM y (px) | OEM pct of mh | UI before | UI after | Delta (after) |
| ------- | ---------: | ------------: | --------: | -------: | ------------: |
| Printed band peak | 290 | 10.4 % | 14.5 % | 14.5 % | +4.1 pp (slight) |
| Printed band ends | 510 | 56.2 % | 55.7 % | 55.7 % | match |
| Numeral 9 | 525 | 59.4 % | 62.6 % | 62.6 % | +3.2 pp (deferred) |
| Speed digit centre ("0") | 580 | 70.8 % | 39.9 % | **68.0 %** | **−2.8 pp** |
| TEMP / FUEL bar y | ~580 | ~70 % | 50.5 % | **68.0 %** | **−2.8 pp** |
| ODO row y | ~680 | ~92 % | 50.1 % | **74.0 %** | **−18 pp** (close - bounded by lamp strip top) |
| Lamp strip top | 615 | 78.1 % | 80.5 % | 80.5 % | +2.4 pp (already low risk) |

The pre-fix state had the speed **above** the band ends and the odo **above**
the speed - exactly opposite of OEM. The fix moves them *below* the band
ends, matching the Car Spy photo.

The numeral drop (`TACH_NUM_INSET = 54 + end² × 14`) is still flat - OEM
shows 0/9 just under the band ends but middle numerals deep in the well.
That is a **separate** issue (formula change, not constant tweak) and is
explicitly deferred to a later iteration.

## Diff (position track only)

| Element | OEM (DIMENSIONS.md) | UI before | UI after | Verdict |
| ------- | ------------------- | --------- | -------- | ------- |
| Speed centre | ~70 % mh | 40 % | **68 %** | match |
| ODO row | ~74 % mh | 50 % | **74 %** | match |
| TEMP bar | speed-y | 50.5 % | **68 %** | match |
| FUEL bar | speed-y | 50.5 % | **68 %** | match |
| Module aspect | 2.35:1 | 2.352 | 2.352 | match |
| Side notches | 58–72 % mh | 58.1–72.0 % | 58.1–72.0 % | match |
| Lamp strip | ~78 % mh (UI lock 80.5 %) | 80.5 % | 80.5 % | unchanged |
| Printed band ends | 56 % mh | 55.7 % | 55.7 % | unchanged |
| Numeral drop | ends ~3 %, middle ~25 % | flat ~7 % | flat ~7 % | deferred |

## Empirically picked knobs

DIMENSIONS.md suggested the LCD cluster sits under the printed band. Sweeping
`SPEED_Y_PCT` and `ODO_Y_PCT` against the OEM photo:

```
SPEED_Y_PCT=0.65  ODO_Y_PCT=0.71: speed y=627, odo y=672 - speed just touches band end y=556 (gap 71 px)
SPEED_Y_PCT=0.68  ODO_Y_PCT=0.74: speed y=649, odo y=694 - speed clears band end y=556 (gap 93 px), odo clears lamp strip top y=743 (gap 49 px)
SPEED_Y_PCT=0.70  ODO_Y_PCT=0.76: speed y=664, odo y=709 - speed tight against band end (gap 108 px), odo tight against lamp strip (gap 34 px)
SPEED_Y_PCT=0.72  ODO_Y_PCT=0.78: speed y=679, odo y=723 - band end → 123 px, lamp strip → 20 px (would clip lamp)
```

`0.68` / `0.74` lands the speed just below the band ends (within ±0.5 pp of
OEM 70.8 %) and the odo just above the lamp strip top (within the 78 % mh
gap before the bezel). Bars at `TEMP_Y_PCT = FUEL_Y_PCT = 0.68` flank the
speedo at speed-y, matching the Car Spy framing.

## Scope (single track, single intent)

- Raise `SPEED_Y_PCT` from `0.40` to `0.68` in `src/gauge_ui.py`
- Raise `ODO_Y_PCT` from `0.50` to `0.74` in `src/gauge_ui.py`
- Raise `TEMP_Y_PCT` from `0.505` to `0.68` in `src/gauge_ui.py`
- Raise `FUEL_Y_PCT` from `0.505` to `0.68` in `src/gauge_ui.py`
- Update `tests/test_gauge_ui.py::FaceGeomTests::test_locked_flanking_gauges_and_speed_percentages`
  to assert the new values
- Update `test_temp_and_fuel_are_horizontal_flanking_bars` - bars now flank
  the **speedo**, not the odo (OEM puts bars at speed-y)
- Add `test_lcd_cluster_locks_to_oem_below_band` - locks speed 68 %, odo 74 %,
  bars 68 %, all under the band ends
- Add `test_speed_sits_below_tach_numerals` - speed/odo sit *below* the 0/9
  numerals, matching OEM (was an inverted layout before this fix)
- Rebake `tests/harness/goldens.json`
- Rebake `docs/assets/compare/*.png` and `shots/*.png`
- Update `refs/flat/DIMENSIONS.md` face-layout table + driver map with the
  new values

## Not in scope (deferred to later iterations)

- **Tach numeral drop formula** - OEM puts 0/9 just under the band ends
  (~3 % drop) but middle numerals deep in the well (~25 % drop). Current
  formula is flat (~7 % drop everywhere). This is a **separate** position
  diff - formula change, not constant tweak. Defer.
- Tach numeral typeface / weight (font track)
- Boot motion timings (motion track)
- Telltale glyph art / TEMP / FUEL pictogram refinement (graphics track)
- Dead-code removal (housekeeping - already done in iter 0005)

## Acceptance

- `uv run pytest tests/` → 105 passed
- `SDL_VIDEODRIVER=dummy uv run python src/gauge_ui.py --smoke` → exits 0
- `uv run python scripts/compare_oem.py` → all five PNGs rebaked
- `compare_ap1_lit_live.png`: speed "98" now sits BELOW the band ends,
  odo "142857" sits directly below the speed, TEMP / FUEL bars flank the
  speedo at the speed-y - visually closes the largest single OEM-vs-UI
  position gap
- Module aspect 2.35:1, side notches 58–72 %, lamp strip top ~80 % -
  `DIMENSIONS.md` locks hold within ±0.5 pp

## Verify (objective)

- [x] `git diff src/gauge_ui.py` is exactly four constant tweaks
      (`SPEED_Y_PCT 0.40 → 0.68`, `ODO_Y_PCT 0.50 → 0.74`,
      `TEMP_Y_PCT 0.505 → 0.68`, `FUEL_Y_PCT 0.505 → 0.68`)
- [x] `tests/test_gauge_ui.py` diff is 1 assertion tweak + 2 new tests
- [x] no graphics / colour / size / motion / font touches
- [x] no docs / CAD / icon asset edits beyond `DIMENSIONS.md` +
      `goldens.json` + `docs/assets/compare/*.png` + `shots/*.png` re-bakes
- [x] pytest 105 passed
- [x] smoke exits 0
- [x] composite eyeball: speed/odo/TEMP/FUEL bars now sit below the band ends
- [x] ahash goldens within tolerance after rebake