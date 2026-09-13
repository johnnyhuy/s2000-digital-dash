# Iteration 0010 — graphics track, refine FUEL pump icon

## Carryover

iter 0009 (PR #N) finished the TEMP thermometer refinement. Its carryover
note flagged the FUEL pump icon for this iteration: the OEM glyph plate
(`refs/oem/plates/oem_dash_glyphs_plate.png`) shows a clear
pump-body + display-window + hose-curve + nozzle + base silhouette,
whereas the current UI stitches those together from rect/arc
primitives but the proportions and the nozzle landing do not match.

## Capture

- UI live shot rebaked: `docs/assets/compare/compare_ap1_lit_live.png`
- OEM side: `refs/oem/lit/lit_ap1_carspy_cluster.jpg`
- OEM glyph plate (FUEL crop): `refs/oem/plates/oem_dash_glyphs_plate.png`,
  upper-right quadrant

## Diff (graphics track only)

| Element | OEM | UI before | UI after | Verdict |
| ------- | --- | --------- | -------- | ------- |
| Body shape | rounded rectangle, taller-than-wide | 12×17 body rect (`border_radius=2`) | 14×18 body rect (`border_radius=3`) | closer |
| Display window | square readout in upper third of the body | 6×4 inset at `cy - 2` | 9×6 inset at `cy − 8` (upper third) | closer |
| Hose curve | thick rounded handle that loops from the right-top of the body, over and down to a nozzle on the right side | single `pygame.draw.arc` from `(cx, cy-6)` | composed: `lines()` from body right + `arc()` to loop + `circle` cap + `lines()` for the nozzle | closer |
| Nozzle | small grip with a clear nozzle head hanging at the right of the pump | 4×10 vertical rect on the right of the arc | short rounded rect anchored at the arc's end, plus a tip tick | closer |
| Base | flat platform under the body, slightly wider than the body | 12×2 rect (matches body width) | 18×3 rect (slightly wider) | closer |
| TEMP / FUEL / chevron / ticks / numerals / band / arch / bezel | OEM | unchanged | unchanged | match |

## Empirically picked knob

```python
# before
body     = Rect(cx - 8,  cy - 6,  12, 17)   # 12×17
cap      = Rect(cx - 6,  cy - 12, 8,  6)    # tiny head
window   = Rect(cx - 5,  cy - 2,  6,  4)    # display
hose_arc = Rect(cx,      cy - 6,  16, 16)   # single 180° arc
nozzle   = Rect(cx + 12, cy + 2,  4, 10)    # vertical bar
base     = Rect(cx - 8,  cy + 11, 12,  2)

# after
body     = Rect(cx - 7,  cy - 7,  14, 18)   # 14×18, slightly wider
window   = Rect(cx - 6,  cy - 6,  9,  6)    # larger square in upper third
hose_path = composed (right-of-body) → arc → nozzle head → tip tick
nozzle   = Rect(cx + 12, cy + 4,  4,  8)    # shorter, anchored at the arc
base     = Rect(cx - 10, cy + 11, 20,  3)   # wider platform
```

The new body is ~17 % wider than before; the window is now a clearly
square readout in the upper third (matches the OEM glyph plate's
screen placement), and the hose routes **off the right shoulder of
the body** then arcs down and to the right to a short nozzle — the
OEM silhouette.

## Scope (single track, single intent)

- Rewrite `_pump_icon` in `src/gauge_ui.py`:
  - wider body (14 wide × 18 tall, was 12 × 17)
  - larger, square-ish window at upper third of the body
  - composed hose curve from the right shoulder of the body to the
    nozzle, with a tip tick
  - wider, flatter base
- Rebake `tests/harness/goldens.json`
- Rebake `docs/assets/compare/*.png` and `shots/*.png`

## Not in scope (deferred)

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
- `compare_ap1_lit_live.png`: FUEL pump icon now reads as
  body → display window → hose-curve → nozzle with a clear tip,
  closer to the OEM glyph plate
- Module aspect 2.35:1, side notches 58–72 %, band peak 10.4 %, band
  ends 56 %, LCD cluster at 68 %/74 %, numerals drop formula at 15 px /
  208 px — all `DIMENSIONS.md` locks hold within ±0.5 %

## Verify (objective)

- [ ] `git diff src/gauge_ui.py` is exactly one icon function rewrite
      (no other face logic touched)
- [ ] no colour / position / size / motion / font touches
- [ ] no docs / CAD / icon asset edits beyond `goldens.json` +
      `docs/assets/compare/*.png` + `shots/*.png` re-bakes
- [ ] pytest 107 passed
- [ ] smoke exits 0
- [ ] composite eyeball: pump body / display window / hose / nozzle
      closer to the OEM glyph plate
- [ ] ahash goldens within tolerance after rebake
