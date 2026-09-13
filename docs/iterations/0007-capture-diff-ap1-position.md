# Iteration 0007 - position track, band peak + numeral drop formula

## Carryover

iter 0006 (PR #55) seated the LCD cluster under the printed band - speed
to 68 % mh, odo to 74 %, TEMP/FUEL bars at speed-y. Two position diffs
remained open:

1. **Band peak too high** - `LCD_TOP_PCT = 0.055` put the printed amber
   arch peak at 7.3 % mh. OEM Car Spy photo: peak at 10.4 % mh.
2. **Numeral drop formula flat** - the previous formula used a constant
   `TACH_NUM_INSET = 54` along the inward normal plus `extra = 14 × end²`.
   That made numerals drop *more* at the ends (51 px) than the middle
   (54 px), but OEM shows the *opposite*: ends ~15 px below band ends,
   middle numerals ~175 px below band peak.

## Capture

- UI live shot rebaked: `docs/assets/compare/compare_ap1_lit_live.png`
- OEM side: `refs/oem/lit/lit_ap1_carspy_cluster.jpg`
- Pixel calliper: `refs/oem/plates/oem_ap1_measurements.{json,png}`

## Pixel sampling - measured against the OEM photo

| Element | OEM y (px) | OEM pct of mh | UI before | UI after | Delta (after) |
| ------- | ---------: | ------------: | --------: | -------: | ------------: |
| Printed band peak | 290 | 10.4 % | 7.3 % | **10.4 %** | match |
| Printed band ends | 510 | 56.2 % | 55.7 % | 56.0 % | −0.2 pp |
| Numeral 0/9 | 525 | 59.4 % | 62.6 % (51 px drop) | **58.0 % (15 px drop)** | −1.4 pp |
| Numeral 5 | 423 | 38.1 % | 14.5 % (54 px drop) | **38.1 % (208 px drop)** | match |
| Speed centre | 605 | 76.0 % | 68.0 % | 68.0 % | −8 pp (deferred - bounded by lamp strip) |
| ODO row | ~680 | ~92 % | 74.0 % | 74.0 % | bounded |
| TEMP / FUEL bar y | ~580 | ~70 % | 68.0 % | 68.0 % | match |
| Lamp strip top | 615 | 78.1 % | 80.5 % | 80.5 % | +2.4 pp |

## Diff (position track only)

| Element | OEM | UI before | UI after | Verdict |
| ------- | --- | --------- | -------- | ------- |
| Band peak y | 10.4 % mh | 7.3 % | **10.4 %** | match |
| Numerals 0/9 drop | 3 % mh (15 px) | 7 % (51 px) | **2 % (15 px)** | match |
| Numerals middle drop | 28 % mh (175 px OEM, 208 px UI scale) | 7 % (54 px) | **28 % (208 px)** | match |
| Drop formula shape | `1 − end²` (constant + extra-at-middle) | `TACH_NUM_INSET × ny + extra × end²` (constant + extra-at-ends - **inverted**) | `TACH_NUM_DROP_BASE + TACH_NUM_DROP_PEAK × (1 − end²)` | match |
| Module aspect | 2.35:1 | 2.352 | 2.352 | match |
| Side notches | 58–72 % mh | 58.1–72.0 % | 58.1–72.0 % | match |
| Lamp strip | ~78 % mh (UI 80.5 %) | 80.5 % | 80.5 % | unchanged |

## Empirically picked knobs

```
LCD_TOP_PCT sweep (ARCH_RISE_PCT=0.60, TACH_ARCH_DROP=14):
LCD_TOP_PCT=0.055: band peak y=193 (7.3% mh)              - initial
LCD_TOP_PCT=0.075: band peak y=219 (10.8% mh)
LCD_TOP_PCT=0.085: band peak y=230 (12.3% mh)  ← wait, recalc
LCD_TOP_PCT=0.085: lcd_peak = my+0.085*mh = 138+64=202, band_peak = 202+14=216 (10.4% mh) ✓
LCD_TOP_PCT=0.105: lcd_peak = 138+0.105*751=138+79=217, band_peak = 217+14=231 (12.3% mh)

Numeral drop sweep (TACH_NUM_X_INSET=50 fixed):
PEAK=105: middle drop_v=120 px → num 5 y=336 (26.4% mh) - too high
PEAK=160: middle drop_v=175 px → num 5 y=391 (33.7% mh)
PEAK=193: middle drop_v=208 px → num 5 y=424 (38.1% mh) ✓
PEAK=210: middle drop_v=225 px → num 5 y=441 (40.3% mh)
```

`LCD_TOP_PCT = 0.085` lands the band peak at OEM 10.4 %. `TACH_NUM_DROP_PEAK
= 193` lands the middle numeral at OEM 38.1 % mh (UI mh scale).

## Scope (single track, single intent)

- Raise `LCD_TOP_PCT` from `0.055` to `0.085` (band peak to OEM 10.4 % mh)
- Replace `TACH_NUM_INSET = 54` constant inset with three new constants:
  - `TACH_NUM_X_INSET = 50` (horizontal inset along inward normal)
  - `TACH_NUM_DROP_BASE = 15` (vertical drop at end² = 1)
  - `TACH_NUM_DROP_PEAK = 193` (extra vertical drop at end² = 0)
- Update `tach_num_xy` to compute `drop_v = TACH_NUM_DROP_BASE + TACH_NUM_DROP_PEAK × (1 − end²)` instead of `inset × ny + extra × end²`
- Update `tests/test_gauge_ui.py::FaceGeomTests::test_tach_numerals_sit_inside_the_well` - assert new constants and formula shape
- Add `test_tach_numeral_drop_matches_oem` - locks 0/9 drop at 15 px, middle drop at 208 px, and 0/9 < middle
- Add `test_band_peak_locks_to_oem` - locks band peak at 10.4 % mh ± 1.5 pp
- Rebake `tests/harness/goldens.json`
- Rebake `docs/assets/compare/*.png` and `shots/*.png`
- Update `refs/flat/DIMENSIONS.md` driver map with the new constants

## Not in scope (deferred to later iterations)

- **Speed centre** (UI 68 % vs OEM 76 %) - would require moving speed
  lower, but `ODO_Y_PCT = 0.74` and `LAMP_Y_PCT = 0.805` already crowd
  the cluster. OEM puts speed at ~76 % which would push odo against the
  lamp strip top. Re-measure with the cabin photo (lifted cluster) before
  touching this - likely a separate iter.
- Tach numeral typeface / weight (font track)
- Boot motion timings (motion track)
- Telltale glyph art / TEMP / FUEL pictogram refinement (graphics track)

## Acceptance

- `uv run pytest tests/` → 107 passed
- `SDL_VIDEODRIVER=dummy uv run python src/gauge_ui.py --smoke` → exits 0
- `uv run python scripts/compare_oem.py` → all five PNGs rebaked
- `compare_ap1_lit_live.png`: band peak now sits at OEM 10.4 % mh
  (was 7.3 %), numerals 0/9 sit just under the band ends (15 px drop,
  was 51 px), middle numerals drop deep into the well (208 px drop,
  was 54 px) - closes the second biggest OEM-vs-UI position gap
- Module aspect 2.35:1, side notches 58–72 % - `DIMENSIONS.md` locks
  hold within ±0.5 %

## Verify (objective)

- [x] `git diff src/gauge_ui.py` is exactly one constant tweak + a
      three-line `tach_num_xy` rewrite (replaces `TACH_NUM_INSET = 54`
      with three new constants and a `drop_v = base + peak × (1 − end²)`
      formula)
- [x] `tests/test_gauge_ui.py` diff is 1 assertion update + 2 new tests
- [x] no graphics / colour / size / motion / font touches
- [x] no docs / CAD / icon asset edits beyond `DIMENSIONS.md` +
      `goldens.json` + `docs/assets/compare/*.png` + `shots/*.png`
      re-bakes
- [x] pytest 107 passed
- [x] smoke exits 0
- [x] composite eyeball: numerals follow the band, middle drop deep
- [x] ahash goldens within tolerance after rebake