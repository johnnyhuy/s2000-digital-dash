# The loop

OEM-vs-UI face polish runs in **six discrete tracks**. Each iteration
captures, diffs, fixes **one** track, verifies, pushes, merges. Stop when
the OEM | UI composite in `docs/assets/compare/` passes the automated
reference acceptance gate. Commit, push and merge passing PRs without a
human review prompt; failed checks return to capture and iteration.

## Tracks (one per PR, never bundled)

| # | Track | Touches | Acceptance |
| - | ----- | ------- | ---------- |
| 1 | **graphics** | tick glyphs, bezel marks, bar-graph cell / hatch shape | Five separated overrun strokes; ink coverage within 0.10 of the lit photo scan |
| 2 | **colour** | amber band, redline, LCD red, bloom | Peak-normalized RGB channel deltas ≤0.08 against named lit-photo regions; no synthetic bloom |
| 3 | **position** | element anchors, arc centre / radii, crown geometry - edited in `src/face_spec.py` only | `refs/flat/DIMENSIONS.md` locks hold within ±0.5% in pygame, SVG and CAD |
| 4 | **size** | digit height, band thickness, numeral weight | Digit / band / symbol dimensions match the lock within ±0.5 percentage points plus one raster pixel |
| 5 | **motion** | bar-graph fill lag, lamp pulse, boot phases | Whole 200 rpm cells, steady telemetry-driven lamps and shared response at 30/60/120 fps; stills establish no OEM timing |
| 6 | **font** | tach numerals, LCD digits, labels | Traced alphabet ≥0.90 ink IoU with the plate; captured numerals ≥0.70; bundled legends and LCD geometry retain the lock |

A PR that touches more than one track is **rejected**. Split it.

## Reference table (locked)

| Use | File |
| --- | ---- |
| AP1 lit photos | `refs/oem/lit/` |
| Telltale / pictogram plates | `refs/oem/plates/` |
| AP1 face percent-lock | `refs/flat/DIMENSIONS.md` |
| AP1 flat elevation | `refs/flat/ap1_cluster_flat.svg` / `.png` |
| AP2 reference (interpretive only) | `refs/oem/ap2/` |
| Source licences | `refs/oem/SOURCES.md` |

AP2 photos are **not** an AP1 plate. Do not regress AP2 arches onto AP1.

## Iteration format

`docs/iterations/<NNNN>-<short>.md`. Each iteration captures:

1. **Capture** - what was rendered (`docs/assets/compare/...`) and the OEM side-by-side
2. **Diff** - table of deltas per track with the OEM reference cited
3. **Fix plan** - which single track this iteration fixes
4. **Acceptance** - how to verify this single-track fix
5. **Verify** - pytest + smoke + screenshot + measured composite report
6. **Hand-off** - PR title, branch, scope, what is **not** in scope

## Housekeeping (separate PRs, never bundled with face polish)

| Track | Where |
| ----- | ----- |
| docs cleanup | `docs/`, `README.md` |
| dead code | `src/`, `scripts/`, `mocks/` |
| CAD revision (calliper-driven, no cabin prints) | `cad/`, `cad/replace_face/` |
| symbols / icons (OEM atlas tints, SVG source of truth) | `assets/icons/`, `scripts/write_icon_svgs.py`, `scripts/rasterize_icons.py` |

Housekeeping PRs never touch face code. Face PRs never touch docs / CAD /
icons unless the diff is purely a re-bake of generated artefacts (stills,
compare PNGs, intro GIF) caused by a code change.

## Automated acceptance

The former same-room eyeball check is an automated measurement. No human
eyes or approval step are required. Use the locked references to decide;
when references disagree, choose the closer OEM evidence, record the call
in the PR body, and continue. The lit photo takes precedence over the old
illustrative measurement plate whose top boundary includes cabin trim.
The dimension lock supplies the perspective-corrected module proportions.

```sh
uv run python scripts/compare_oem.py
node apps/harness/scripts/capture-face.cjs shots/web
uv run python scripts/accept_oem.py --check --web-dir shots/web --output shots/oem-acceptance.json
```

The gate measures actual PNG pixels, reference glyph ink and hatch coverage;
records pixel/percentage/channel deltas; verifies reference/capture SHA-256
values and exported SVG/CAD locks; and exits nonzero on failure. It also
checks discrete-cell motion and frame-rate response. Negative tests must
continue rejecting missing glyphs, old colours, filled hatches and shifted
hardware. Never relax a threshold or refresh a hash to conceal a failing
reference comparison.

`shots/oem-acceptance.json` is the evidence report. A passing result means
the documented photo/plate/lock criteria pass, including the captured React
SVG when supplied. The SVG capture does not include browser CSS or interaction
testing. Daylight exposure is not calibrated OLED brightness; the glyph
plate is reconstructed; stills cannot verify OEM ignition timing. The
custom demo boot remains explicitly labelled as such. AP2 remains interpretive.

Historical iteration notes retain their original verification language;
this page defines the current loop.
