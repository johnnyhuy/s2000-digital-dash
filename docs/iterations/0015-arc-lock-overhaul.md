# Iteration 0015 - arc lock: one measured geometry for pygame, web and CAD

## Why this breaks the one-track rule

Iterations 0001–0014 each moved one knob against a **parabolic** band and
a scatter of `%` constants in `gauge_ui.py`. Side-by-side with the Car Spy
photo the face still did not read as an S2000 cluster: the band was the
wrong curve, numerals floated, the tach was a needle over a printed scale
(the OEM is a segmented bar graph), the digits were rounded not mitred,
and the web harness and the CAD each carried their own copy of the
geometry. No single track could fix that - the *lock itself* was wrong.
This iteration replaces the lock and re-derives every renderer from it.
After it, the six-track loop resumes on top of `face_spec.py`.

## Capture

- OEM: `refs/oem/lit/lit_ap1_carspy_cluster.jpg`, perspective-corrected
  with `scripts/measure_oem_ui.py`; circle fit through the 0 / 5 / 9 ticks
- UI: `docs/assets/compare/compare_ap1_*.png`, `shots/*.png`,
  `shots/harness/*.png`, web `docs/assets/web-*.png`
- CAD: `cad/replace_face/preview/acrylic_face.png`, `assembly.png`

## Diff (all tracks - this is a relock, not a polish)

| Element | OEM | Before | After |
| --- | --- | --- | --- |
| Tach curve | circular arc, centre ≈ 130 % H below top, r ≈ 54 % W | quadratic bezier `y = 28 u²` | `ArcSpec` circle; 0/9 ticks at (19 %, 36 %) / (81 %, 36 %), apex 2.4 % |
| Tach readout | amber **bar graph** cells + red hatch past 9 | white chevron needle on a printed band | 100 rpm cells, 0.22° gaps, hatch lights over 9; no needle |
| 0 → 1 division | squeezed (~60 %) | uniform | `first_div = 0.6` |
| Hood crown | concentric with the band, constant gap | parabola with rectangular side notches | circle concentric with the tach, r = r_out + 0.4 % W, 1.2 % lip, springs at 58 % H |
| Digits | mitred 45° 7-seg, hairline gaps, chamfered corners | rounded strokes | `lcd_digits.py` / `SevenSeg.tsx` rewritten, ghost `#4a0c0e` |
| Numerals | rounded gothic, inside the well | Barlow Condensed italic | M PLUS Rounded 1c Bold, on `r_num` along the inward normal |
| TEMP / FUEL | 8 / 16 block bars with icon + letters | 6 thin ticks | `SegBar`, idle knee at 3–4 blocks (`temp_segments_lit`) |
| Telltales | ←/→/high beam in the well; strip of nine | all in the strip | `arc_lamps` wells + `strip_lamps` |
| Web harness | - | HTML bezel + CSS masks | one SVG from `faceSpec.json` |
| CAD mask | windows over the panel | parabola + ten tach slots | sector + LCD + bar + lamp windows from `face_lock.scad`, `min_rim` clip |
| CAD tray | - | LCD guess | parametric 7" AMOLED pocket, switch wells skipped where they collide |

## Fix

- `src/face_spec.py` - `ArcSpec` / `FaceSpec` for AP1 and AP2; `export_json`,
  `export_scad`, `spec_to_scad`
- `src/gauge_ui.py`, `src/lcd_digits.py` - redrawn on the lock; static-layer
  cache; `reset_render_caches()` after `pygame.quit()`
- `apps/harness/lib/geometry.ts`, `components/ClusterFace.tsx`,
  `SevenSeg.tsx`, `LampIcons.tsx` - SVG face from the JSON lock;
  `Telltales.tsx` removed
- `cad/replace_face/*.scad`, `mesh_export.py` (trimesh replaces Blender),
  `export.sh`
- fonts: M PLUS Rounded 1c OFL subset bundled twice
- docs: `refs/flat/DIMENSIONS.md` rewritten around the arc; READMEs;
  BRANDING

## Acceptance

- `uv run pytest -q` → 105 passed
- `cd apps/harness && npm test && npm run lint && npx tsc --noEmit` → 22 pass, clean
- `bash cad/replace_face/export.sh` → six watertight solids, GLB preview
- `tests/test_replace_face_printables.py` pins `face_lock.scad` to the
  spec export, so the CAD cannot silently diverge
- Composite eyeball: band curve, 0/9 positions, numeral seats, digit
  shapes and bar layout match the Car Spy photo within the ±2 pp the
  measurement script reports

## Deferred (back onto the six tracks)

- colour: amber cell grade vs. lit photo under the same exposure
- size: speed digit height on AP2; strip lamp glyph heights
- motion: bar-graph cell fill lag vs. the OEM LCD refresh
- position: SEL / TRIP outboard once the bay is measured
- CAD: panel drawing, switch locations, callipers - see the measure list
