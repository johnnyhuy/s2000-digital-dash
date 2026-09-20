# OEM face and replacement-display audit

This pass covers the requested combined symbol, proportion and web-theme revision.
The target is a 7-inch OLED driven by a Raspberry Pi. The user's Obsidian
installed-parts inventory identifies the car as a 2001 AP1; no exact OLED model,
resolution or active dimensions were found in that vault. Existing 154×87 mm
active-area and CAD measurements remain placeholders.

## Evidence

- [Honda 2003 S2000 manual](https://techinfo.honda.com/rjanisis/pubs/OM/AH/AS20303OM/enu/S20303OM.pdf), printed p.45: AP1 warning locations and identities.
- [Honda 2005 S2000 manual](https://techinfo.honda.com/rjanisis/pubs/OM/AH/AS20505OM/enu/S20505OM.pdf), printed pp.39, 44: AP2 instruments and warnings.
- Existing Car Spy lit AP1 and S2KI AP2 photos under `refs/oem/`.
- User's local `refs/oem/bench/oem_ap1_bench.png`: inspect only the upper OEM
  cluster; the lower half is an aftermarket display, not an OEM AP2 reference.
  This pre-existing untracked file is not redistributed by this change.

The manuals show North American configurations. They establish symbol identity
and relative layout, not all Australian-market legends or physical dimensions.
The current circular arc and font remain approximations; no claim of pixel-perfect
geometry, exact startup timing or verified hardware fit is made.

## Corrections

- AP1 speed and odometer windows were undersized. Speed digit height goes from
  11.2% to 19.4% of the face height, with a separate lower odometer/trip window.
- Side bars move outward, with readable symbols and gutters around numerals.
- One half-thousand minor tick between major marks, as visible in the references,
  replaces four minors. The existing 200 rpm bar cells are retained.
- ABS moves to AP1's left pocket. Fuel-low, seat-belt and SRS occupy the right
  pocket. Immobilizer, cruise, trunk and door are in the lower strip.
- AP2 gets an actual airbag symbol, distinct from the belt reminder; ABS/EPS/belt
  move into the left well, with turns beside the speed display. C/H and E/F sit
  inside their half-ring gauges instead of colliding with their endpoints.
- Oil-can silhouette and droplet fit inside their master artwork. Coolant and
  pump art is shared across renderers, as are all pictogram plates. React code is
  generated from the SVG/PNG masters with the same alpha-crop sizing as pygame.
- Synthetic pixel-grid lines are removed. Steady green indicators no longer
  pulse just because they are green; state comes from telemetry.
- The custom READY screen puts the real marks and READY inside the central
  windows. Removed crowded diagnostic chips. This remains a custom boot sequence.
- Web controls, text, logos, focus states and JSON support System/Light/Dark.
  Rounded charcoal switches, cluster typography and amber selected indicators
  match the instrument in both page themes, including the appearance selector.
  The instrument retains its black field and warning colours in every theme.
- `/display?style=ap1` or `ap2` provides a control-free, aspect-preserving OLED
  preview. It still uses mock data. Pygame `--car` now fits height as well as width; `--size WIDTHxHEIGHT` reaches the actual render loop and screenshot path.

## Reproduce

```sh
uv run python src/face_spec.py
uv run python scripts/write_icon_svgs.py
uv run python scripts/rasterize_icons.py
uv run python scripts/export_web_icons.py
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy uv run pytest
SDL_VIDEODRIVER=dummy uv run python scripts/ui_harness.py --check
cd apps/harness
npm test
npm run lint
npm run build
```

Visual acceptance includes AP1/AP2 bulb-check, live, warning and READY frames;
light/dark and mobile screenshots; unchanged instrument colours under either
theme; and no clipping/stretching in the OLED preview. Regression tests measure
actual digit runs, numeral ink bounds, icon-generation parity and panel fit.
Generated CAD follows the updated lock, but is still a provisional design.

## Verification result

- 131 Python tests; 24 web tests; ESLint and production build pass.
- Headless smoke with/without intro, UI hashes and mock UART pipe pass.
- Browser: both styles in light/dark, persisted override, system changes, 390 px mobile, five OLED viewport sizes; no page errors.
- CAD export completes with watertight solids. Prior committed meshes were stale relative to the shallower arc; regenerated mask bounds are 170 × 70.51 mm and remain provisional.
- AP1/AP2 self-test frames, comparison images, boot recording and theme screenshots refreshed.
