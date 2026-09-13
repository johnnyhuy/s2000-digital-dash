# Iteration 0001 - capture + diff + first PR

## Capture

- UI live shot rebaked: `docs/assets/compare/compare_ap1_lit_live.png`
- OEM side: `refs/oem/lit/lit_ap1_carspy_cluster.jpg` (The Car Spy, CC BY 2.0)
- Orthographic lock: `refs/flat/ap1_cluster_flat.png` + `refs/flat/DIMENSIONS.md`

Both sides are fit-height 520 px, side-by-side, captions in orange.

## Diff (six tracks)

Numbers below are eyeballed from the 520 px composite, then mapped back to
the 1920×1080 UI canvas where it helps. Module is 2.35:1 inside a 4–96 %
horizontal band, vertically centred at 0.42.

### 1. graphics

| Element | OEM | UI | Verdict |
| ------- | --- | -- | ------- |
| Chevron needle | white chevron tip + tail, cream fill | white chevron tip + tail, cream fill | match |
| Tach ticks | vertical bars normal to arch | vertical bars normal to arch | match |
| TEMP thermometer icon | glyph above the C bar | glyph above the C bar | match |
| FUEL pump icon | glyph above the F bar | glyph above the F bar | match |
| PUSH CANCEL | speedo dial + needle to 2 o'clock + X | speedo dial + needle to 2 o'clock + X | match |
| Hardware buttons | round −/+ rocker + oval SEL + oval TRIP | round −/+ rocker + oval SEL + oval TRIP | match |
| Telltales | self-test order: ← / hi / ABS / BRAKE / batt / oil / CEL / key / MAINT / EPS / belt / door / SRS / → | same order, ISO pictograms | match (recent polish) |

No graphics diff worth a PR this iteration.

### 2. colour

| Element | OEM | UI | Verdict |
| ------- | --- | -- | ------- |
| Amber band | warm orange-amber with bloom | warm yellow-amber with bloom | close - UI leans yellow vs OEM orange |
| Redline (8–9) | orange-red blocks | orange-red blocks | match |
| LCD red | deep red with soft bloom | deep red with soft bloom | match |
| Off-segment ghost | dim red ghost of `188` / `888888` | dim red ghost of `188` / `888888` | match |
| Tach tick (major / minor) | warm white on amber | warm white on amber | match |

Amber bias is a candidate but smaller than the position diff below. Defer.

### 3. position

| Element | OEM (flat lock %) | UI code (%) | Delta | Verdict |
| ------- | ----------------- | ----------- | ----- | ------- |
| Tach band peak y | ~12 % | 12 % | 0 | locked |
| Tach band ends y | ~50 % | 64 % | **+14 pp** | **overshoots** |
| Amber band rise (ends − peak) | ~38 % | **52 %** | **+14 pp** | **overshoots** |
| Numerals 0/9 y | ~55 % (just below band ends) | derived from band ends → ~67 % | +12 pp | **pulled down with band** |
| Speed centre y | ~46 % | 40 % | −6 pp | close enough |
| TEMP/FUEL bars y | ~65 % | 50.5 % | **−14.5 pp** | **too high** |
| Hardware strip y | ~80 % | 80.5 % | +0.5 pp | locked |

The **biggest single position diff is the amber band rise**. The flat lock
puts the printed band at peak 12 %, ends 50 % - a rise of ~38 % of module
height. The UI overshoots to 52 %. The numerals 0 and 9 ride the band
ends, so they drop too. The TEMP/FUEL bars also sit too high (50.5 % vs
~65 % in the flat lock), but that's a separate position diff for a later
iteration.

### 4. size

| Element | OEM | UI | Verdict |
| ------- | --- | -- | ------- |
| Speed digit height | ~28 % module height | ~26 % (96 px on 751 mh) | close - UI slightly smaller |
| Tach numerals | compact, narrower | Barlow SemiBold Italic | wider than OEM - defer to font track |
| Amber band depth | thick (~9 % mh) | TACH_BAND_OUTER = 32 px ≈ 4.3 % mh | **UI band too thin** - size track |
| Odo digit height | small | 26 px ≈ 3.5 % mh | close |
| Trip digit height | smaller than odo | 22 px ≈ 2.9 % mh | match |
| TEMP/FUEL bar height | thin dashes | 0.018 × mh ≈ 13 px | close |

UI band is half as thick as the OEM. That's a real size diff but secondary
to position. Defer.

### 5. motion

Stills only - cannot diff motion from the composite. Boot phases are:
sweep (1.35 s) → READY (1.75 s) → reveal (1.55 s) → live. Visual timing
match against the lit reference will need a side-by-side video, not a
still. Skip until a video diff lands.

### 6. font

| Element | OEM | UI | Verdict |
| ------- | --- | -- | ------- |
| Tach numerals | narrow compact sans, italic slant | Barlow Condensed SemiBold Italic | UI slightly wider / heavier - defer |
| Speed / odo / trip | 7-seg LCD with rounded corners | rounded 7-seg in `lcd_digits.py` | match |
| "x1000 r/min" label | tucked next to 0, smaller | tucked next to 0, smaller | match |
| "TRIP A" label | small caps next to trip digits | small caps next to trip digits | match |
| `km/h` / `mph` label | right of digits, same line | right of digits, same line | match (UI uses km/h per protocol) |

Font diff is real but small. Defer.

## First PR - position track, single fix

**Branch**: `iter/0001-position-band-rise`

**Title**: `fix(cluster): seat the printed tach band on the OEM rise`

**Scope** (single track, single intent):

- Reduce `TACH_END_Y_PCT` from `0.64` to `0.54` in `src/gauge_ui.py`
- Verify the band rise drops from 52 % → 42 % of module height
- Verify the numerals 0 / 9 follow the band ends down (no manual fix)
- Verify TEMP / FUEL bars at `0.505` still clear the band ends (>4 % gap)
- Rebake `docs/assets/compare/compare_ap1_lit_live.png`
- Update `tests/harness/goldens.json` (geometry-only change)

**Not in scope** (deferred to later iterations):

- TEMP / FUEL y position (separate position diff)
- Amber band thickness / size (size track)
- Amber orange tint (colour track)
- Tach numeral typeface / weight (font track)
- Boot motion timings (motion track)
- Telltale glyph art (graphics track)
- Docs cleanup, dead code, CAD callipers, icon atlas (housekeeping)

## Acceptance

- pytest green
- `SDL_VIDEODRIVER=dummy uv run python src/gauge_ui.py --smoke --screenshot shots` exits 0
- `uv run python scripts/compare_oem.py` regenerates the composite
- `compare_ap1_lit_live.png`: the printed band ends sit visibly closer to
  the speedo centre (band rise 42 % of module height vs prior 52 %)
- numerals 0 / 9 still sit just below the band in the well
- TEMP / FUEL bars still flank the speedo with no overlap with band ends
- module aspect 2.35:1, hood arch 28 % rise, side notches 58–72 % - all
  `refs/flat/DIMENSIONS.md` locks hold within ±0.5 %

## Verify (hand-off checklist for human approval)

- [ ] git diff against `main` is ≤ 30 lines in `src/gauge_ui.py` and
      ≤ 10 lines in `tests/`
- [ ] no graphics / colour / motion / font touches
- [ ] no docs / CAD / icon asset edits (re-bakes only)
- [ ] composite eyeball test: amber band ends noticeably closer to OEM
- [ ] pytest + smoke + ahash goldens all green

## Hand-off

Awaiting user approval before `git switch -c`, commit, push, PR.
