# Iteration 0013 - graphics track, sharpen the chevron needle

## Carryover

iter 0009 (graphics) closed the TEMP thermometer refinement; iter 0010
closed the FUEL pump icon. The remaining graphics-track deltas are
small ad-hoc refinements: chevron needle, hood lip details, label
kernels. The most visually obvious is the **chevron needle** - in
the OEM Car Spy lit photo it reads as a tiny cream mark on the printed
band (no visible tail behind the band's spring), whereas the UI's
chevron has a TAIL = 16.5 px which doubles the visible footprint.

## Capture

- UI live shot rebaked: `docs/assets/compare/compare_ap1_lit_live.png`
- OEM lit photo: `refs/oem/lit/lit_ap1_carspy_cluster.jpg`
- OEM glyph plate (chevron not present - needle is small at idle)

## Diff (graphics track only)

| Element | OEM | UI before | UI after | Verdict |
| ------- | --- | --------- | -------- | ------- |
| Needle TIP (px above band) | small (just visible above band) | -3.4 | unchanged (-3.4) | match |
| Needle TAIL (px below band) | barely visible (OEM needle reads as a tip-only chevron) | 16.5 | **9.0** | closer |
| Chevron half-widths (shadow / glow / main) | small stroke | 5.4 / 4.2 / 2.8 | unchanged | match |
| All ticks, band, numerals, hood, cowl, bezel | OEM | unchanged | unchanged | match |
| All other 5 tracks (colour / position / size / motion / font) | OEM | unchanged | unchanged | match |

## Empirically picked knob

```python
# before
TACH_NEEDLE_TIP = -3.4
TACH_NEEDLE_TAIL = 16.5   # 2.2 % mh on the UI 752 mh module
# → chevron reads as a long arrowhead behind the band spring

# after
TACH_NEEDLE_TIP = -3.4   # unchanged
TACH_NEEDLE_TAIL = 9.0    # 1.2 % mh on the UI 752 mh module
# → chevron reads as a small, OEM-like tip-only mark
```

The shadow + glow + main chevron layers are drawn from `chevron(5.4)` /
`chevron(4.2)` / `chevron(2.8)`. With a shorter tail, the three
triangles stay cohesive (no separation), and the visible footprint
shrinks by ~40 %.

## Scope (single track, single intent)

- One-knob tweak of `TACH_NEEDLE_TAIL` from `16.5` to `9.0` in
  `src/gauge_ui.py`
- Rebake `tests/harness/goldens.json`
- Rebake `docs/assets/compare/*.png` and `shots/*.png`

## Not in scope (deferred)

- **Tach numerals stroke weight** - SemiBoldItalic is still heavier
  than the OEM plate's thin/regular; closing the gap exactly would
  require bundling `BarlowCondensed-Regular.ttf` /
  `BarlowCondensed-Light.ttf`. fonts-track housekeeping PR,
  explicitly out of scope.
- **Speed digit `h`** - size track, separate iteration
- **Boot motion timings** - motion track, no OEM video reference
- Telltale glyph art
- Tach numerals / position

## Acceptance

- `uv run pytest tests/` → 107 passed
- `SDL_VIDEODRIVER=dummy uv run python src/gauge_ui.py --smoke` → exits 0
- `uv run python scripts/compare_oem.py` → all five PNGs rebaked
- `compare_ap1_lit_live.png`: at ~6500 r/min the chevron reads as a
  tighter cream mark on the band, less of a long dart hanging into
  the well
- Module aspect 2.35:1, side notches 58–72 %, band peak 10.4 %, band
  ends 56 %, LCD cluster at 68 %/74 %, numerals drop 22 px base +
  193 px peak - all `DIMENSIONS.md` locks hold within ±0.5 %

## Verify (objective)

- [ ] `git diff src/gauge_ui.py` is exactly one constant tweak
      (16.5 → 9.0 on `TACH_NEEDLE_TAIL`)
- [ ] no colour / position / size / motion / font touches
- [ ] no docs / CAD / icon asset edits beyond `goldens.json` +
      `docs/assets/compare/*.png` + `shots/*.png` re-bakes
- [ ] pytest 107 passed
- [ ] smoke exits 0
- [ ] composite eyeball: needle a small cream tip-only chevron,
      no visible tail behind the band's spring
- [ ] ahash goldens within tolerance after rebake
