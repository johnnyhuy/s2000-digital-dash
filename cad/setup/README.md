# Digital-screen bench setup

A complete **layout prototype** for a 7-inch OLED and Raspberry Pi, alongside
(not a replacement for) the arched mask option in `../replace_face/`.
The rectangular screen carries the entire digital face, without a physical mask
covering pixels. The front frame, electronics shell, removable carrier and
vented rear cover are separate solids. The web `/setup` viewer uses these meshes.

## Geometry and limits

- **OLED:** 164 × 100 × 2.6 mm module, 154 × 87 mm active area. PLACEHOLDERS;
  confirm the actual panel drawing. The 174 × 110 × 49.6 mm assembled housing
  follows those assumptions; it is not a measured S2000 bay adapter.
- **Pi 5 reference:** 85 × 56 mm PCB, mounting centres 58 × 49 mm with first
  centre 3.5 mm from the PCB edges. Source: [Raspberry Pi mechanical drawing](https://datasheets.raspberrypi.com/rpi5/raspberry-pi-5-mechanical-drawing.pdf).
  The drawing itself is approximate. PCB thickness, connector blocks, GPIO,
  cooler envelope and all other component heights here are clearance proxies.
- **Carrier:** 144 × 90 × 3 mm plate, four Pi standoffs, cable-tie slots and
  ventilation. Pi faces forward inside a 40 mm deep enclosure. An 18 × 38 mm
  display-driver board is an allowance only, not a selected controller.
- **Service access:** broad right-side port opening, bottom cable exit, top and
  rear vents. Cable bend radii, power interface, cooling, fasteners, switch
  locations and mounting to the car remain unverified. No vehicle clips or
  invented OEM mounting holes are supplied.
- **Fastening concept:** pilot holes at cover/carrier/frame positions. Screw
  lengths, thread inserts and tolerances must be designed after physical checks.
  No electrical connection or thermal performance is implied by this layout.

## Exports

```sh
uv run --extra cad python cad/setup/export.py
openscad -o output/setup.png --imgsize=1600,1000 --viewall --autocenter -D explode=24 cad/setup/setup.scad
```

`print/*.stl` are millimetre prototype parts with their bases on Z=0. The exporter
rejects open or disconnected printable solids. `manifest.json` records bounds.
`apps/harness/public/models/setup-{assembled,exploded,electronics}.glb` are coloured,
metre-scale scenes with named components, port and cooler proxies and an embedded
AP1 screen texture. They are for inspection, not printing as one body.
`setup-prototype.zip` bundles the SCAD, four STLs, manifest and this note.

The browser offers orbit/zoom, front/rear views, assembled/exploded/electronics mode and an
expanded view. The static screen texture is illustrative, not live telemetry.
