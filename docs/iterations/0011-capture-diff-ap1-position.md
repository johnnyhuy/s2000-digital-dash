# Iteration 0011 — position track, drop 0/9 below the band to OEM 3 % mh

## Carryover

iter 0009 closed the graphics track on the TEMP/thermometer
refinement. The OEM measurements plate
(`refs/oem/plates/oem_ap1_measurements.json`) has objective evidence
on the 0/9 numeral drop that the UI has been off by:

| Landmark | OEM px | OEM % mh |
| -------- | ------ | -------- |
| `band_end` | 510 | 56.25 |
| `numeral_9` | 525 | 59.38 |
| **drop at ends** | **15 px** | **3.13 pp** |

The UI module on the 1920×1080 canvas is **752 px** tall (`0.92 ×
1920 / 2.35`). The OEM drop of 3.13 pp on that scale is **23.5 px**,
but `TACH_NUM_DROP_BASE` has been **15.0** — visibly too tight against
the band's spring. This PR brings it into the OEM window.

## Capture

- UI live shot rebaked: `docs/assets/compare/compare_ap1_lit_live.png`
- OEM side: `refs/oem/lit/lit_ap1_carspy_cluster.jpg`
- OEM measurements plate: `refs/oem/plates/oem_ap1_measurements.json`
  (the objective ground truth for this fix)

## Diff (position track only)

| Element | OEM | UI before | UI after | Verdict |
| ------- | --- | --------- | -------- | ------- |
| Tach band spring (band_end) | y = 56.25 % mh | y = ~56 % mh (iter 0002 lock) | unchanged | match |
| Numeral 0 / 9 vertical drop below band spring | 15 px in photo ⇒ 3.13 pp on UI scale ≈ **22 px** | **15 px** | **22 px** | closer |
| Numeral middle drop (4 / 5 / 6) | deep in the well (~28 % mh, no picked landmark — empirical) | 208 px = base + peak (15 + 193) | 215 px = base + peak (22 + 193) | deeper in the well by ~3 px (still in the 0.20 – 0.32 window — iter 0007 test holds) |
| Numerals 0 / 9 horizontal inset | along inward normal | same | same | match |
| Band peak / band ends / LCD cluster / column bars | per `DIMENSIONS.md` | unchanged | unchanged | match |
| All other 5 tracks (graphics / colour / size / motion / font) | OEM | unchanged | unchanged | match |

## Empirically picked knob

```python
# before
TACH_NUM_DROP_BASE = 15.0
# → 0/9 numerals drop 15 px below band ends on a 752 mh module = 2.0 % mh

# after
TACH_NUM_DROP_BASE = 22.0
# → 0/9 numerals drop 22 px below band ends = 2.93 % mh
# OEM Car Spy plate: 3.13 % mh → well within ±0.3 pp (~2 px) tolerance
```

The middle numerals now drop **base + peak = 22 + 193 = 215 px**
(was 208 px), shifting deeper by ~3 px in the well. The
`test_tach_numeral_drop_matches_oem` upper bound is `0.32 mh`; 215 / 752
= 0.286 mh — still inside the window.

## Scope (single track, single intent)

- Bump `TACH_NUM_DROP_BASE` from `15.0` to `22.0` in `src/gauge_ui.py`
- Update `tests/test_gauge_ui.py` lock-assertion in
  `test_tach_numerals_sit_inside_the_well` from `15.0 ± 1.0` to
  `22.0 ± 1.0` (still asserts the constant against the locked value
  — single-document numerical update)
- Rebake `tests/harness/goldens.json`
- Rebake `docs/assets/compare/*.png` and `shots/*.png`

## Not in scope (deferred)

- **Tach numerals stroke weight** — at 38 px the SemiBoldItalic still
  reads slightly heavier than the OEM plate's thin/regular glyphs.
  Approximating the OEM weight exactly would require a new bundled
  font (Barlow Condensed Regular/Light) — fonts-track housekeeping PR,
  explicitly out of scope
- **Boot motion timings** (motion track)
- **Speed digit `h` (UI 96 px, OEM ~14 % mh)** — size track, deferred
  pending a cabin-photo re-measure of digit height vs module height
- **Hardware strip item widths** — would shift positions in the same
  draw function as drop change, bundled correctly only with lamp-strip
  rework

## Acceptance

- `uv run pytest tests/` → 107 passed (with updated lock assertion)
- `SDL_VIDEODRIVER=dummy uv run python src/gauge_ui.py --smoke` → exits 0
- `uv run python scripts/compare_oem.py` → all five PNGs rebaked
- `compare_ap1_lit_live.png`: numerals 0 and 9 sit visibly lower
  under the band's spring line (≈ 22 px = 2.9 % mh), closer to OEM's
  3.1 % mh plate landmark
- Module aspect 2.35:1, side notches 58–72 %, band peak 10.4 %, band
  ends 56 %, LCD cluster at 68 %/74 %, numerals middle drop formula at
  215 px (was 208) px → 28.6 % mh (still in 0.20–0.32 mh bracket) — all
  `DIMENSIONS.md` locks hold within ±0.5 %

## Verify (objective)

- [ ] `git diff src/gauge_ui.py` is exactly one constant bump (15.0 → 22.0)
- [ ] `git diff tests/` is exactly one numeric update in one test method
- [ ] no colour / size / motion / font / graphics touches
- [ ] no docs / CAD / icon asset edits beyond `goldens.json` +
      `docs/assets/compare/*.png` + `shots/*.png` re-bakes
- [ ] pytest 107 passed
- [ ] smoke exits 0
- [ ] composite eyeball: numerals 0 / 9 drop more visibly below the
      band's spring, closer to the OEM plate
- [ ] ahash goldens within tolerance after rebake
