# The loop

OEM-vs-UI face polish runs in **six discrete tracks**. Each iteration
captures, diffs, fixes **one** track, verifies, pushes, merges. Stop only
when the OEM | UI composite in `docs/assets/compare/` passes a same-room
eyeball test.

## Tracks (one per PR, never bundled)

| # | Track | Touches | Acceptance |
| - | ----- | ------- | ---------- |
| 1 | **graphics** | icon art, tick glyphs, bezel marks, bar-graph cell / hatch shape | OEM pictogram proportions + tick direction match the lit reference |
| 2 | **colour** | amber band, redline, LCD red, bloom | Palette and bloom match the lit AP1 reference |
| 3 | **position** | element anchors, arc centre / radii, crown geometry — edited in `src/face_spec.py` only | `refs/flat/DIMENSIONS.md` locks hold within ±0.5% in pygame, SVG and CAD |
| 4 | **size** | digit height, band thickness, numeral weight | OEM proportions hold at the 1920×1080 canvas |
| 5 | **motion** | bar-graph fill lag, lamp pulse, boot phases | Smoothing constants match the lit reference timing |
| 6 | **font** | tach numerals, LCD digits, labels | Same family/weight/style as the OEM reference; weight + spacing match |

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

1. **Capture** — what was rendered (`docs/assets/compare/...`) and the OEM side-by-side
2. **Diff** — table of deltas per track with the OEM reference cited
3. **Fix plan** — which track this iteration fixes, which it leaves for later
4. **Acceptance** — how to verify this single-track fix
5. **Verify** — pytest + smoke + screenshot + composite diff notes
6. **Hand-off** — PR title, branch, scope, what is **not** in scope

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

## Eyeball test

The loop stops when `docs/assets/compare/compare_ap1_lit_live.png` passes a
same-room eyeball check against `refs/oem/lit/lit_ap1_carspy_cluster.jpg`
on the AP1 face (left = OEM, right = UI). Each iteration must move the
match closer — never further.
