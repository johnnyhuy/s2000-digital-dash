# Iteration 0004 - colour track, amber tint

## Carryover

iter 0003 (PR #52) thickened the band to OEM depth. iter 0002 raised
the parabola. iter 0001 (no-op) was the dead-knob PR.

The remaining colour diff: UI amber leans **yellow** (R:G ≈ 1.31 for the
bloom) while OEM leans **orange-amber** (R:G ≈ 1.86 in the bright
pixels of `refs/oem/lit/lit_ap1_carspy_cluster.jpg`).

## Capture

- UI live shot rebaked: `docs/assets/compare/compare_ap1_lit_live.png`
- OEM side: `refs/oem/lit/lit_ap1_carspy_cluster.jpg`
- Reference callipers: `refs/oem/plates/oem_ap1_measurements.{json,png}`

## Pixel sampling

Bright amber pixels in the OEM photo (cluster band area):

```
(255, 157, 76), (255, 137, 77), (189, 110, 71), (181, 103, 18)
```

`AMBER_HOT` was `(255, 194, 74)` - too yellow (`R:G = 1.31`). OEM
brightest amber sits at `R:G ≈ 1.86`, e.g. `(255, 137, 77)`.

## Diff (colour track only)

| Element | OEM | UI before | UI after | Verdict |
| ------- | --- | --------- | -------- | ------- |
| Lit band bloom | orange-amber `(255, 137, 77)` | yellow `(255, 194, 74)` | `(255, 137, 77)` | match |
| Tach pointer glow | orange-amber | yellow `(255, 194, 74)` | `(255, 137, 77)` | match |
| Minor tick colour | orange-amber | yellow lerp | orange lerp | match |
| TEMP/FUEL gradient hot | orange-amber | yellow lerp | orange lerp | match |
| READY text | orange-amber | yellow | orange-amber | match |

`AMBER_BAND_LO` / `AMBER_BAND_HI` (band base gradient) are unchanged -
they already sit in the right orange space (R:G 1.42 → 2.93). The
yellow tint came from the bloom / hot layer using `AMBER_HOT`.

## Scope (single track, single intent)

- Change `AMBER_HOT` from `(255, 194, 74)` to `(255, 137, 77)` in
  `src/gauge_ui.py`
- Rebake `tests/harness/goldens.json` (small hash change on bloom-tinted
  cells)
- Rebake `docs/assets/compare/*.png` and `shots/*.png`

## Not in scope (deferred)

- TEMP / FUEL y position (50.5 % vs OEM ~53 %) - position track
- Speed centre y (40 % vs OEM 46 %) - position track (deferred)
- Tach numeral typeface / weight - font track
- Boot motion timings - motion track
- Telltale glyph art - graphics track
- Dead-code removal - housekeeping track
- LCD / cowl / bezel palette (already match OEM) - colour track (done)

## Acceptance

- `uv run pytest tests/` → 103 passed
- `SDL_VIDEODRIVER=dummy uv run python src/gauge_ui.py --smoke
  --screenshot shots` → exits 0
- `uv run python scripts/compare_oem.py` → all five PNGs rebaked
- `compare_ap1_lit_live.png`: lit amber bloom now leans orange, not
  yellow - matches OEM
- `compare_ap1_selftest.png`: minor ticks and pointer glow now lean
  orange, not yellow
- TEMP / FUEL hot gradient end now leans orange (warm end of the
  OEM heat range), not lemon yellow

## Verify (objective)

- [x] `git diff src/gauge_ui.py` is exactly one constant tweak
- [x] no graphics / position / size / motion / font touches
- [x] no docs / CAD / icon asset edits beyond `goldens.json` +
      `docs/assets/compare/*.png` + `shots/*.png` re-bakes
- [x] pytest 103 passed
- [x] smoke exits 0
- [x] composite eyeball: amber now leans orange, not yellow
- [x] ahash goldens within tolerance after rebake