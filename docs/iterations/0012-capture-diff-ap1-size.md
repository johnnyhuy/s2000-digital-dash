# Iteration 0012 — size track, scale up the tach numerals to OEM

## Carryover

iter 0008 thinned the tach numerals from 42 → 38 px to soften their
pixel weight after the SemiBoldItalic's natural chunkiness pushed
them past the OEM plate's thin/regular feel. But the **size** of the
glyph dropped at the same time — and the Car Spy lit photo's
numerals sit visibly taller than 38 px in the cluster.

Pixel measurement on the lit AP1 photo
(`refs/oem/lit/lit_ap1_carspy_cluster.jpg`, cluster is 480 px mh):

| Source | Glyph height | % module height |
| ------ | ------------ | --------------- |
| OEM lit AP1 photo (numeral `5`) | ~30 – 35 px | ~7 % mh |
| OEM glyph plate (`oem_dash_glyphs_plate.png`) | ~95 px of 1024 mh | ~9 % mh |
| UI before (Barlow SemiBoldItalic 38) | ~30 px (glyph height, *not* font size) | ~4 % mh (on 752 UI mh) |
| UI after (Barlow SemiBoldItalic 50) | ~40 px glyph height | ~5.3 % mh (closer to OEM 7 % mh) |

The 38 px SemiBoldItalic also remains the heaviest concrete delta
relative to the OEM plate (would need a Regular/Light font to fix
font-track side) — out of scope here.

## Capture

- UI live shot rebaked: `docs/assets/compare/compare_ap1_lit_live.png`
- OEM lit photo: `refs/oem/lit/lit_ap1_carspy_cluster.jpg`
- Reference plate: `refs/oem/plates/oem_dash_glyphs_plate.png`

## Diff (size track only)

| Element | OEM | UI before | UI after | Verdict |
| ------- | --- | --------- | -------- | ------- |
| Tach numeral glyph height (on 480 mh module) | 30 – 35 px (~7 % mh) | ~30 px (font 38) | ~40 px (font **50**) | closer |
| Tach numeral stroke weight | thin / regular | SemiBoldItalic | SemiBoldItalic | unchanged (font track — separate PR) |
| Tach numeral italic slant | slight (~8°) | SemiBoldItalic skew | unchanged | match |
| LCD speed / odo / trip | 7-seg | lcd_digits.py | lcd_digits.py | unchanged |
| "x1000 r/min" / "km/h" / "TRIP A" | sans-serif bold small | Barlow | Barlow | unchanged |
| All other 5 tracks | OEM | unchanged | unchanged | match |

## Empirically picked knob

```python
# before
"tick": _font(pygame, 38, italic=True)
# → glyph height ~30 px ≈ 4 % mh on the UI 752 mh module

# after
"tick": _font(pygame, 50, italic=True)
# → glyph height ~40 px ≈ 5.3 % mh, closer to OEM 7 % mh
# Tests that lock glyph height (test_band_peak_locks_to_oem, etc.) stay
# locked because they check layout positions, not font pixel size.
```

A bump from 38 → 50 lifts the numerals from ~4 % mh (visibly small,
sinking below the band ends into the well) to ~5.3 % mh — closer to
the OEM Car Spy photo's 7 % mh without crowding the well.

## Scope (single track, single intent)

- One-character bump in `build_fonts`: `"tick"` size `38` → `50`
- Rebake `tests/harness/goldens.json`
- Rebake `docs/assets/compare/*.png` and `shots/*.png`

## Not in scope (deferred)

- **Tach numerals stroke weight** — SemiBoldItalic is still heavier
  than the OEM plate's thin/regular; closing the gap exactly would
  require bundling `BarlowCondensed-Regular.ttf` /
  `BarlowCondensed-Light.ttf`. fonts-track housekeeping PR,
  **explicitly out of scope**.
- Speed digit `h` (size track — separate iteration)
- Boot motion timings (motion track)
- Tach numeral drop formula / position
- LCD cluster window proportions

## Acceptance

- `uv run pytest tests/` → 107 passed
- `SDL_VIDEODRIVER=dummy uv run python src/gauge_ui.py --smoke` → exits 0
- `uv run python scripts/compare_oem.py` → all five PNGs rebaked
- `compare_ap1_lit_live.png`: tach numerals sit visibly taller
  (~5 % mh instead of ~4 % mh), read closer to the OEM Car Spy
  photo's `0` – `9` row.
- Module aspect 2.35:1, side notches 58–72 %, band peak 10.4 %, band
  ends 56 %, LCD cluster at 68 %/74 %, numerals drop formula at 22 px
  base + 193 px peak — all `DIMENSIONS.md` locks hold within ±0.5 %

## Verify (objective)

- [ ] `git diff src/gauge_ui.py` is exactly one font-size constant bump
      (no other face logic touched)
- [ ] no graphics / colour / position / motion / font weight touches
- [ ] no docs / CAD / icon asset edits beyond `goldens.json` +
      `docs/assets/compare/*.png` + `shots/*.png` re-bakes
- [ ] pytest 107 passed
- [ ] smoke exits 0
- [ ] composite eyeball: numerals 0–9 visibly taller, closer to
      the OEM lit photo
- [ ] ahash goldens within tolerance after rebake
