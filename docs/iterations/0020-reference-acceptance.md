# AP1 reference acceptance

The capture/diff/fix/verify/push/merge loop completed in separate PRs:

| PR | Track | Result |
| --- | --- | --- |
| [72](https://github.com/johnnyhuy/s2000-digital-dash/pull/72) | Position | Coolant over the cold end; SEL/TRIP on the lower hardware row |
| [73](https://github.com/johnnyhuy/s2000-digital-dash/pull/73) | Font | Plate-derived SVG tach alphabet shared by pygame and React |
| [74](https://github.com/johnnyhuy/s2000-digital-dash/pull/74) | Graphics | Five thin hatch strokes, matching source-photo ink coverage |
| [75](https://github.com/johnnyhuy/s2000-digital-dash/pull/75) | Colour | LCD, amber and hatches measured against lit-photo regions |
| [76](https://github.com/johnnyhuy/s2000-digital-dash/pull/76) | Motion | Whole 200 rpm cells and shared display response |
| [77](https://github.com/johnnyhuy/s2000-digital-dash/pull/77) | Verification only | Six-track composite gate and reproducible React SVG capture |

Size passed the dimension lock without a face change. This documentation
cleanup is separate from those face PRs. No calliper measurements, CAD
redesign, cabin prints, symbol/icon revision or dead-code removal occurred.

## Evidence and decisions

- [Lit AP1 composite](../assets/compare/compare_ap1_lit_live.png)
- [Pixel acceptance report](../../shots/oem-acceptance.json)
- [Actual React SVG raster](../../shots/web/ap1-live.png)
- Sources: `refs/oem/lit/`, `refs/oem/plates/`, `refs/flat/DIMENSIONS.md`

The lit photograph wins over the historic illustrative plate's cabin-inclusive
top boundary. The dimension lock supplies module proportions. The supplied
high-resolution glyph plate supplies the traced tach alphabet; it is a
reconstruction, not a newly identified OEM font. Photo hatch/side-bar amber
provides the available proxy for lit tach amber because the reference is at
idle. Existing demo smoothing remains the timing contract, shared across
renderers; no factory timing is inferred from a still image.

## Measured result

All six native tracks and all five static SVG tracks pass. Maximum position
error is 0.128 percentage points. Captured numeral ink IoU is at least 0.784
in pygame and 0.798 in SVG, above the 0.70 capture threshold. Master numeral
silhouettes overlap the plate by 93.8–97.8%, above the 90% master threshold.
Maximum peak-normalized colour-channel delta is 0.0569 against a 0.08 limit.
The photo hatch scan has 32.7% ink coverage; native and SVG captures have
36.5% and 29.9%, within the 10 percentage-point raster allowance. Both retain
five separated strokes.

175 Python tests, 26 web tests, React render checks, ESLint, the production
build and capture hashes pass. Regression tests reject missing glyphs,
the former LCD palette, filled hatch regions and the former hardware
anchors. CI enforces native composite acceptance and React render checks.

The available-reference gate is automated and requires no human approval.
It does not establish calibrated OLED brightness, physical vehicle fit or
OEM ignition timing. The React capture rasterizes the actual instrument SVG
without browser CSS or interaction testing. AP2 remains interpretive.
