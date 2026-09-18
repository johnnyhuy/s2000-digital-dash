# Iteration 0017 - position: shallower tach cap from the bench OEM

## Capture

- OEM: `refs/oem/bench/oem_ap1_bench.png` (straight-on) vs Car Spy (downward)
- UI: `docs/assets/compare/compare_ap1_lit_cruise.png`

## Diff (position only)

| Landmark | OEM bench | Before (0016) | After |
| --- | --- | --- | --- |
| Band apex | ~10–12 % H (visor above) | 2.4 % H (band glued to the lip) | **10 % H** |
| Circle | r ≈ 59 % W, centre deep | r 54.3 % W, cy 130 % H | **r 59.0 % W, cy 148.7 % H** |
| 0 / 9 ticks | low, near C/H and E/F | (19 %, 36 %) | **(17 %, 47 %)** |
| Numeral 0 / 5 | 0 beside the temp bar | 43 % / 19 % H | **53 % / 28 % H** |

The Car Spy downward angle made the cap look taller than it is. The bench plate is a shallower slice of a larger circle. Aspect stays 2.35:1 this pass.

## Fix plan

Position. `ArcSpec.cy` / `r_out` only (crown stays concentric). No size, font, colour or CAD mesh rebuild.

## Acceptance

`test_band_peak_and_ends_land_on_oem` locks apex 10 % H and 0/9 at y ≈ 47 % H. Same-room: the arch is a shallow cap, 0 and 9 sit down by the side gauges.

## Verify

pytest + harness geometry tests. Rebake stills and the OEM composite.

## Hand-off

Continues #64. Not in scope: module aspect 2.69, digit size, thick physical visor, CAD STL rebuild.
