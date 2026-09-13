# Iteration 0008 — font track, thin the tach numerals

## Carryover

iter 0006 and 0007 closed the position track — band shape, band peak,
band ends, LCD cluster, and the 0/9-vs-middle numeral drop formula now
all match the Car Spy photo within ±1.5 pp. The remaining OEM-vs-UI
diff that jumps out at the eyeball is the tach numeral stroke weight:

| Source | Numeral height | Stroke feel |
| ------ | -------------- | ----------- |
| OEM Car Spy photo | ~38 px | thin / regular |
| OEM AP1 glyph plate | ~52 px | thin / regular, slight italic |
| UI before (Barlow SemiBoldItalic 42) | ~32 px | heavy, wider spacing |
| UI after (Barlow SemiBoldItalic 38) | ~30 px | closer, slightly tighter |

No regular/light Barlow weight is bundled — the available tick fonts are
`BarlowCondensed-Bold.ttf`, `BarlowCondensed-SemiBoldItalic.ttf`, and
`Oxanium-Bold.ttf`. `Oxanium` is rounder/more geometric and reads as a
different typeface, not the OEM numerals. The pragmatic move is to use the
SemiBoldItalic at a smaller pixel size — at 38 the natural AA-thinning
plus the smaller silhouette bring the visual weight into OEM territory
without introducing a new font file.

## Capture

- UI live shot rebaked: `docs/assets/compare/compare_ap1_lit_live.png`
- OEM side: `refs/oem/lit/lit_ap1_carspy_cluster.jpg`
- Reference plate: `refs/oem/plates/oem_dash_glyphs_plate.png`

## Diff (font track only)

| Element | OEM | UI before | UI after | Verdict |
| ------- | --- | --------- | -------- | ------- |
| Tach numeral stroke weight | thin | SemiBold 42 px | SemiBold **38 px** | closer |
| Tach numeral italic slant | slight (~8°) | ~12° (file skew) | ~12° (unchanged) | unchanged |
| Tach numeral height | ~38 px | ~32 px | ~30 px | slightly tighter (still > 80 % of OEM) |
| LCD speed / odo / trip | 7-seg | lcd_digits.py | lcd_digits.py | unchanged |
| "km/h" / "TRIP A" / "x1000 r/min" / "C/H/E/F" | sans-serif bold small | Barlow Bold | Barlow Bold | unchanged |

The italic slant is unchanged — the SemiBoldItalic file's built-in skew is
the closest available match; `font.set_italic(True)` on Bold renders with
~16° skew (too steep, tested offline).

## Scope (single track, single intent)

- Lower `"tick"` font size from `42` to `38` in `build_fonts`
- Rebake `tests/harness/goldens.json`
- Rebake `docs/assets/compare/*.png` and `shots/*.png`

## Not in scope (deferred to later iterations)

- **Tach numerals stroke weight** is now in the same neighbourhood as
  OEM but still slightly heavier. Approximating the OEM weight exactly
  would require a new bundled font (Barlow Condensed Regular/Light) — a
  fonts-track housekeeping PR that is **explicitly out of scope** here.
- "x1000 r/min" label weight / family (font track)
- Boot motion timings (motion track)
- Telltale glyph art / TEMP / FUEL pictogram refinement (graphics track)
- Speed centre y (UI 68 % vs OEM 76 %) — bounded by odo row + lamp strip
  top, needs a cabin-photo re-measure (position track)

## Acceptance

- `uv run pytest tests/` → 107 passed
- `SDL_VIDEODRIVER=dummy uv run python src/gauge_ui.py --smoke` → exits 0
- `uv run python scripts/compare_oem.py` → all five PNGs rebaked
- `compare_ap1_lit_live.png`: tach numerals sit slightly closer to the
  OEM stroke weight — visibly less chunky, no other change
- Module aspect 2.35:1, side notches 58–72 %, band peak 10.4 %, band
  ends 56 %, LCD cluster at 68 %/74 %, numerals drop formula at 15 px /
  208 px — all `DIMENSIONS.md` locks hold within ±0.5 %

## Verify (objective)

- [x] `git diff src/gauge_ui.py` is exactly one font size constant tweak
- [x] no graphics / colour / position / size / motion touches
- [x] no docs / CAD / icon asset edits beyond `goldens.json` +
      `docs/assets/compare/*.png` + `shots/*.png` re-bakes
- [x] pytest 107 passed
- [x] smoke exits 0
- [x] composite eyeball: numerals less chunky, all other elements
      unchanged
- [x] ahash goldens within tolerance after rebake