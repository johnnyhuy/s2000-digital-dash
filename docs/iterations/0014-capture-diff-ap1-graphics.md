# Iteration 0014 - graphics track, add OEM "mph·km/h" bezel label

## Carryover

iter 0013 (graphics) closed the chevron needle refinement. The OEM Car
Spy lit photo (`refs/oem/lit/lit_ap1_carspy_cluster.jpg`) has a small
**`mph·km/h`** label printed in the lower-right bezel, just to the left
of the SEL button - a unit toggle hint, not a clickable control. The
UI bezel did not draw it.

## Capture

- UI live shot rebaked: `docs/assets/compare/compare_ap1_lit_live.png`
- OEM lit photo: `refs/oem/lit/lit_ap1_carspy_cluster.jpg` (crop below)

```
[ OEM bottom-right bezel crop ]
...   9   E ▮▮▮ F
                       SEL   TRIP
                  mph·km/h
```

## Diff (graphics track only)

| Element | OEM | UI before | UI after | Verdict |
| ------- | --- | --------- | -------- | ------- |
| `mph·km/h` bezel label | printed white text, lower-right, just left of SEL | absent | **added** (`fonts["micro"]`, DIM, mid-right of SEL button) | closer |
| All other bezel marks (–/+ rocker, PUSH CANCEL, telltale strip, SEL/TRIP ovals) | OEM | unchanged | unchanged | match |
| All ticks, band, numerals, hood, cowl | OEM | unchanged | unchanged | match |
| All other 5 tracks (colour / position / size / motion / font) | OEM | unchanged | unchanged | match |

## Empirically picked knob

The label is anchored to `g.trip_blank` (the SEL button rect) - its
right edge minus 8 px, bottom-aligned 2 px above the button's bottom
edge. Uses `fonts["micro"]` (13 px Barlow Condensed Bold) and `DIM`
(122, 114, 100) so it reads as printed bezel text, not LCD red.

Skipped on AP2 - AP2 replaces the SEL with a CLOCK button and the
bezel layout is interpretive.

## Scope (single track, single intent)

- 15-line addition to `draw_hardware_strip` in `src/gauge_ui.py`
- Rebake `tests/harness/goldens.json`
- Rebake `docs/assets/compare/*.png` + `shots/*.png` + `shots/harness/*.png`

## Not in scope (deferred)

- Tach numerals stroke weight - fonts-track housekeeping
- Speed digit height - size track
- Boot motion timings - motion track
- Telltale glyph art
- Tach numerals position

## Acceptance

- `uv run pytest tests/` → 107 passed
- `SDL_VIDEODRIVER=dummy uv run python src/gauge_ui.py --smoke` → exits 0
- `uv run python scripts/ui_harness.py --check` → ahash OK
- `uv run python scripts/compare_oem.py` → all five PNGs rebaked
- `compare_ap1_lit_live.png`: `mph·km/h` visible in the lower-right
  bezel, sitting just to the left of the SEL button (mid-right anchor,
  DIM colour)
- Module aspect 2.35:1, side notches 58–72 %, band peak 10.4 %, band
  ends 56 %, LCD cluster at 68 %/74 %, numerals drop 22 px base +
  193 px peak - all `DIMENSIONS.md` locks hold within ±0.5 %

## Verify (objective)

- [ ] `git diff src/gauge_ui.py` is exactly one new `blit_text` block
      in `draw_hardware_strip` (no other face code touched)
- [ ] no colour / position / size / motion / font touches
- [ ] no docs / CAD / icon asset edits beyond `goldens.json` +
      `docs/assets/compare/*.png` + `shots/*.png` + `shots/harness/*.png`
      re-bakes
- [ ] pytest 107 passed
- [ ] smoke exits 0
- [ ] composite eyeball: `mph·km/h` reads as printed bezel text, not
      LCD, sits in the OEM-typical spot
- [ ] ahash goldens within tolerance after rebake
