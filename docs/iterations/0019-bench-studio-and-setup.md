# Bench studio layout and complete 3D setup

The web layout now separates the instrument canvas, grouped controls and live
readouts. Raw JSON is collapsed, startup can be replayed explicitly, and changing
face respects reduced-motion preferences. Light/dark theme controls and the dash
button styling are retained. The OLED-only route remains free of web controls.

## Hardware studio

`/setup` loads a locally bundled `@google/model-viewer` on demand. It supports
assembled, exploded and electronics-only scenes, pointer orbit/zoom, front/rear
camera presets, fullscreen, and downloads. `cad/setup/setup.scad` is the source
for four single-body prototype parts: front frame, vented enclosure, removable
Pi carrier and rear cover. Exported GLBs use metres and embed an AP1 screen image;
STLs use millimetres, with their lowest Z moved onto the build plate.

The 85 × 56 mm Pi outline and 58 × 49 mm mounting centres follow the
[Raspberry Pi 5 drawing](https://datasheets.raspberrypi.com/rpi5/raspberry-pi-5-mechanical-drawing.pdf).
Panel outline/active area, enclosure dimensions, connector geometry, cooler,
controller allowance and fasteners remain provisional. No vehicle mounting or
thermal qualification is claimed. This is a full digital-screen option alongside
the existing arched mask; it does not silently change that mask's geometry.

## Verification

- 139 Python tests and 24 web tests pass; lint and production build pass.
- Exporter rejects open/disconnected printable solids. All four prints pass.
- CI tests validate STL closure/build-plane placement, metre-scale self-contained
  GLBs, electronics inspection content, embedded textures and ZIP/source parity.
- Production-browser checks: AP1/AP2 and presets, JSON expand, replay/skip startup;
  all three 3D modes and matching download links; rear/reset camera, pointer orbit,
  fullscreen enter/exit; light/dark, 390px layout, no page errors.
- Refreshed desktop and 3D screenshots under `docs/assets/`.

Regeneration and remaining hardware questions are in `cad/setup/README.md`.
