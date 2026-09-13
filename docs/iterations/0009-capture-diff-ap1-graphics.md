# Iteration 0009 — graphics track, refine TEMP thermometer icon

## Carryover

iter 0008 (PR #58) thinned the tach numerals toward OEM weight by
lowering the tick font from 42 to 38. Position, colour, and font
tracks are essentially done. Two graphics-track refinements remained:

1. **TEMP thermometer waves** — the previous icon used a zigzag for
   the two ~≈ waves below the bulb. The OEM glyph plate
   (`refs/oem/plates/oem_dash_glyphs_plate.png`) shows smooth
   sine-like waves.
2. **TEMP thermometer proportions** — the previous stem was 18 px
   tall and the bulb only 6 px radius. The OEM plate has a clearly
   *larger* bulb relative to a *shorter* stem.

## Capture

- UI live shot rebaked: `docs/assets/compare/compare_ap1_lit_live.png`
- OEM side: `refs/oem/lit/lit_ap1_carspy_cluster.jpg`
- OEM glyph plate: `refs/oem/plates/oem_dash_glyphs_plate.png`

## Diff (graphics track only)

| Element | OEM | UI before | UI after | Verdict |
| ------- | --- | --------- | -------- | ------- |
| Stem height | ~12 px | 18 px | **12 px** | match |
| Bulb radius | ~8 px | 6 px | **7 px** | closer |
| Stem / bulb ratio | bulb larger | stem larger | bulb larger | match |
| Stem ticks | 3 short, evenly spaced | 3 short at dy = -12, -7, -2 | 3 short at dy = -12, -8, -4 | match |
| Wave shape below bulb | smooth (~≈) | zigzag | smooth sine | match |
| FUEL pump icon | pump body + window + handle + base | same | unchanged | match |
| Other graphics (chevron needle, ticks, bezel buttons) | OEM | unchanged | unchanged | match |

## Empirically picked knob

```python
# before
stem = pygame.Rect(cx - 2, cy - 18, 4, 18)   # 18 tall × 4 wide
bulb = circle(cx, cy + 4, 6)                   # 6 px radius (12 diameter)
ticks at dy = -12, -7, -2                      # 5-px spacing
wave = [(cx-8 + x, y + (zigzag ±2)) for ...]   # zigzag

# after
stem = pygame.Rect(cx - 2, cy - 16, 4, 12)   # 12 tall × 4 wide (closer to OEM plate)
bulb = circle(cx, cy + 4, 7)                   # 7 px radius (14 diameter — bulb larger than stem)
ticks at dy = -12, -8, -4                      # 4-px spacing
wave = [(cx-10 + x, baseline + round(sin(x*pi/5) * 2)) for x in 0..21]  # smooth ~≈
```

The new bulb (r=7) is ~17% bigger and the stem (12 px) is ~33%
shorter than before — net effect matches the OEM plate where the
bulb dominates and the stem is a small column.

## Scope (single track, single intent)

- Update `_thermometer_icon` in `src/gauge_ui.py`:
  - shorter stem (12 px tall, was 18 px)
  - bigger bulb (7 px radius, was 6)
  - smooth sine waves (was zigzag)
- Rebake `tests/harness/goldens.json`
- Rebake `docs/assets/compare/*.png` and `shots/*.png`

## Not in scope (deferred to later iterations)

- **FUEL pump icon refinements** — current pump body + window + handle
  + base already matches the OEM plate's structure; further tweaks would
  be pixel-level and probably require SVG redraw (graphics track or
  housekeeping-track icons PR)
- **Tach numerals stroke weight** — at 38 px the SemiBoldItalic still
  reads slightly heavier than the OEM plate's thin/regular glyphs.
  Approximating the OEM weight exactly would require a new bundled
  font (Barlow Condensed Regular/Light) — fonts-track housekeeping PR,
  explicitly out of scope here
- **Speed centre y** (UI 68 % vs OEM 65 %) — within ±3 pp, bounded by
  odo row + lamp strip top (position track, deferred — needs a
  cabin-photo re-measure)
- Boot motion timings (motion track)

## Acceptance

- `uv run pytest tests/` → 107 passed
- `SDL_VIDEODRIVER=dummy uv run python src/gauge_ui.py --smoke` → exits 0
- `uv run python scripts/compare_oem.py` → all five PNGs rebaked
- `compare_ap1_lit_live.png`: TEMP thermometer icon now has a clearly
  shorter stem, larger bulb, and smooth ~≈ waves — closer to the
  OEM glyph plate
- Module aspect 2.35:1, side notches 58–72 %, band peak 10.4 %, band
  ends 56 %, LCD cluster at 68 %/74 %, numerals drop formula at 15 px /
  208 px — all `DIMENSIONS.md` locks hold within ±0.5 %

## Verify (objective)

- [x] `git diff src/gauge_ui.py` is exactly one icon function rewrite
      (no other face logic touched)
- [x] no colour / position / size / motion / font touches
- [x] no docs / CAD / icon asset edits beyond `goldens.json` +
      `docs/assets/compare/*.png` + `shots/*.png` re-bakes
- [x] pytest 107 passed
- [x] smoke exits 0
- [x] composite eyeball: thermometer stem/bulb/waves closer to OEM
- [x] ahash goldens within tolerance after rebake