# Iteration 0005 - housekeeping, dead tach circle removal

## Carryover

DIMENSIONS.md (commit `123cb63`) flagged an entire chain of dead code
that PR #50 (commit `e04e1a3`) had tried to "fix" by tweaking the dead
constant. The whole chain produced a byte-identical composite - proof
nothing downstream consumed it.

## Capture

- UI live shot rebaked: `docs/assets/compare/compare_ap1_lit_live.png`
- ahash goldens: byte-identical to iter 0004 (proves the dead chain
  never reached the renderer)

## Diff (housekeeping track)

| Knob | Status before | Status after |
| ---- | ------------- | ------------ |
| `TACH_END_Y_PCT` | constant defined, read only to derive the unused circle | **deleted** |
| `TACH_PEAK_Y_PCT` | same | **deleted** |
| `TACH_INSET_X_PCT` | same | **deleted** |
| `tach_cx`, `tach_cy`, `tach_r_outer`, `tach_r_inner`, `tach_r_num`, `tach_start_deg`, `tach_span_deg` | dataclass fields, set but never read by any drawing function | **deleted from `FaceGeom`** |
| Local `end_y / peak_y / end_inset / x0 / x1 / half / drop / tach_r / tach_cy / start_deg / end_deg / span` in `build_face_geom` | computed only to populate the dead fields | **deleted** |
| `TACH_CX, TACH_CY, TACH_R_NUM, TACH_R_OUTER, TACH_R_INNER, TACH_START_DEG, TACH_SPAN_DEG` globals | bound at import + re-bound in `apply_face_style` | **deleted** |
| `apply_face_style` globals list | listed 6 dead globals | **now only `FACE`** |
| `tach_angle(frac)` | defined, never called | **deleted** |
| `tach_point(r, frac)` | defined, never called | **deleted** |
| DIMENSIONS.md "Iter note - `TACH_END_Y_PCT` is dead code" | documented artefact waiting for housekeeping | **deleted (note obsolete)** |
| DIMENSIONS.md driver map | referenced dead `ARCH_RISE_PCT = 0.28` | updated to `0.60` (iter 0002 actual value) |

The actual tach rendering path (`tach_arch_xy`, `tach_arch_normal`,
`tach_band_poly`, `tach_tick_poly`, `tach_num_xy`, `_draw_tach_pointer`)
was untouched and still uses `lcd_peak_y` / `lcd_spring_y` /
`ARCH_RISE_PCT`. Those are the live knobs.

## Scope (housekeeping track, single intent)

- Delete the dead tach-circle constants, fields, locals, globals, and
  functions from `src/gauge_ui.py`
- Delete the obsolete iter note from `refs/flat/DIMENSIONS.md`
- Update the driver map to the actual `ARCH_RISE_PCT = 0.60` value
  (was still showing the pre-iter-0002 `0.28`)
- Rebake `tests/harness/goldens.json` - verified byte-identical
  (proves no behavioural change)

## Not in scope

- Any graphics / colour / position / size / motion / font edit
- Any docs / CAD / icon asset edit beyond the dead-code note
- bench / telemetry / serial changes

## Acceptance

- `uv run pytest tests/` → 103 passed
- `SDL_VIDEODRIVER=dummy uv run python src/gauge_ui.py --smoke
  --screenshot shots` → exits 0
- `uv run python scripts/compare_oem.py` → all five PNGs rebaked
- `compare_ap1_lit_live.png` byte-identical to iter 0004
  (the dead chain had no visual effect - this is the entire point of
  the housekeeping PR)
- `git diff src/gauge_ui.py` removes 62 lines, adds 2

## Verify (objective)

- [x] only `src/gauge_ui.py` and `refs/flat/DIMENSIONS.md` touched
- [x] no graphics / colour / position / size / motion / font touches
- [x] no assets / composite / goldens changes
- [x] pytest 103 passed
- [x] smoke exits 0
- [x] composite pixel-identical to iter 0004 (dead code had no effect)
- [x] ahash goldens identical to iter 0004 (re-baked - proves no
      behavioural change)