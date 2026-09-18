# Iteration 0016 - position: unstack the hood / band / tick radii

## Capture

- OEM: bench AP1 (`refs/oem/bench/oem_ap1_bench.png`) + Car Spy lit
- UI: `docs/assets/compare/compare_ap1_lit_cruise.png`, harness stills

## Diff (position only)

| Stack (outside → in) | OEM | Before | After |
| --- | --- | --- | --- |
| Cowl lip → band | visible dark well | `CROWN_GAP` 0.4 % W (lip painted on the band) | **1.4 % W** well, lip **1.8 % W** |
| Hatch → baseline | hatches stay in the band | `hatch_inner_over` 1.0 % W crossed the white line | **0** — hatches clip at `r_in` |
| Band → ticks | dark gap, then ticks | `line_gap` 0.3 % W (baseline sat on the band) | **0.8 % W** |
| Ticks → numerals | tick tips clear the digits | major 1.4 % W reached the glyph | major **1.2 % W**, `num_inset` **3.4 % W** |

## Fix plan

Position track. Edit `src/face_spec.py` only (plus lock export + tests). No colour, font, motion or icon work.

## Acceptance

`test_arc_stack_radii_do_not_overlap` holds in pygame and the harness: crown, band, hatch, baseline and numerals each own a radius.

## Verify

pytest + harness geometry tests green. Same-room: the grey lip, amber band and white ticks read as three concentric curves, not one stroke.

## Hand-off

PR title: `fix(cluster): unstack overlapping hood, band and tick curves`

Not in scope: module aspect / circle refit from the bench photo (size + position follow-up), CAD mesh rebuild, glow.
