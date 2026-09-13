# OEM reference sources

Curated Honda S2000 cluster photographs used to lock the pygame face.
**AP1** (horizontal TEMP left / FUEL right flanking the speedo) is the default face lock.
**AP2** (arched side gauges, clock / outside-temp LCD) is filed under
`ap2/` as a **style reference** - the AP2 UI is interpretive, not a
pixel-perfect plate. Do not treat AP2 photos as AP1.

This is an unofficial DIY overlay. Photos stay in-repo for side-by-side
compare only. Honda marks remain theirs. See the root README disclaimer.

## AP1 - use these

| File | What | Source | Licence |
| --- | --- | --- | --- |
| `lit/lit_ap1_carspy_cluster.jpg` | Lit AP1 face, straight-on-ish through the wheel. Horizontal C–H / E–F, 7-seg speed, circular −/+ and SEL / TRIP, `mph · km/h` on the bezel. | [The Car Spy](https://www.flickr.com/photos/thecarspy/2644733191/) via [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Honda_S2000_-_Flickr_-_The_Car_Spy_(5).jpg) | [CC BY 2.0](https://creativecommons.org/licenses/by/2.0/) - The Car Spy |
| `lit/lit_ap1_carspy_cabin.jpg` | AP1 cabin context, RHD, same session. Straight TEMP left / FUEL right. | [The Car Spy](https://www.flickr.com/photos/thecarspy/2644732109/) via [Wikimedia](https://commons.wikimedia.org/wiki/File:Honda_S2000_-_Flickr_-_The_Car_Spy_(7).jpg) | [CC BY 2.0](https://creativecommons.org/licenses/by/2.0/) - The Car Spy |
| `../flat/ap1_cluster_flat.png` | Orthographic lock drawing (170×72.3 mm, 2.35:1). | In-repo (`refs/flat/`) | Original project artwork |
| `icons/icon_ap1_carspy_lampstrip.jpg` | Bottom bezel + lamp crop from the Car Spy AP1 frame. | Same as `lit_ap1_carspy_cluster.jpg` | CC BY 2.0 - The Car Spy |
| `../flat/DIMENSIONS.md` | Percent lock for the UI. | In-repo | - |

## AP2 - do not copy the gauges

| File | What | Source | Licence |
| --- | --- | --- | --- |
| `ap2/ap2_s2ki_arched_gauges.jpg` | **AP2** cluster: stacked *arched* TEMP / FUEL on the right, clock + outside temp in the LCD. Reference for the AP2 face style - not a measured plate. | [S2KI thread](https://www.digital-kaos.co.uk/forums/showthread.php/1111478-Honda-S2000-93C66-Enabling-MPH-on-a-KPH-cluster) image host `cimg6.ibsrv.net` (originally posted on S2KI) | Forum photograph; design-reference / fair-use thumbnail. Not AP1. |

## Attached refs (local drop)

The brief also named a curated drop at `/workspace/s2000-dash-phase1/refs/`:

- `lit/lit_ap1_04_selftest_all_lamps_flickr.jpg` - AP1 self-test, every segment + lamp (188)
- `lit/lit_ap1_07_night_idle_carsandbids.jpg` - night idle, first tach ticks lit
- `ap1_oem_cluster_3_jdmaster_face.jpg` - unlit 3/4 face (JDMaster)
- `icons/icon_ap1_selftest_lampstrip_tight.jpg` - lamp-strip crop
- `flat/ap1_cluster_flat.png` - already in `refs/flat/`

That folder was **not present on this agent box**. The Car Spy CC BY 2.0
pair + the in-repo flat lock are the committed stand-ins. Drop the Flickr /
Cars & Bids / JDMaster files into `refs/oem/lit/`, `unlit/`, and `icons/`
when available and add a row here (URL + licence). Do not treat AP2 interiors
(2004+ arched gauges, 2006+ self-diag LCD) as AP1.

## Generated plates (this repo)

High-res white-on-black plates used to trace / redraw `assets/icons/*.svg`.
They are **not** Honda artwork - cleaned reconstructions from the AP1
self-test lamp strip and the Car Spy frame.

| File | What |
| --- | --- |
| `plates/oem_telltale_atlas_plate.png` | 14-lamp atlas (signal pair + self-test strip) |
| `plates/oem_telltale_atlas_v2.png` | Refined atlas pass |
| `plates/oem_pictograms_closeup.png` | Battery, oil, CEL, key, seatbelt, door, high beam |
| `plates/oem_dash_glyphs_plate.png` | TEMP thermometer, FUEL pump, PUSH CANCEL dial, tach numerals |
| `plates/unofficial-geometric-h.png` | Unofficial geometric H (not Honda trademark) |

Pipeline: OEM refs → plates → SVG redraw under `assets/icons/` →
`scripts/rasterize_icons.py` (rsvg) → tint at draw time.

## How to attribute

Car Spy frames used in `docs/assets/compare/` must keep the “The Car Spy,
CC BY 2.0” caption. Do not strip credit from composites.

## Geometry notes pulled from the AP1 photos

- Tach ticks are **vertical** bars that follow the arch, not a filled circular wedge
- Redline is **five thick orange-red blocks from 8–9**
- Speed is a **3-digit 7-segment** LCD; unused digits ghost as 188
- Odo is **6 integer digits**; trip is **xxx.x**; label **TRIP A**
- TEMP is a **horizontal C–H bar left of the speedo** (6 ticks). FUEL is a **horizontal E–F bar right of the speedo**. Vertical side stacks are erroneous.
- Bezel buttons are **round** − / + and SEL / TRIP, plus `PUSH CANCEL` and `mph · km/h`
- Tach ticks and TEMP/FUEL are warm amber with bloom; speed/odo 7-seg is **red LCD**; unlit segments stay as dim ghosts
