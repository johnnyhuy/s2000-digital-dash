# S2000 Digital Dash - web cluster harness

Shareable Next.js App Router demo of the OEM face - red mitred 7-seg speed/odo, amber **bar-graph tach on a circular arc**, flanking TEMP / FUEL block bars, telltale strip and buttons - rendered as a single SVG. Same frozen JSON fields as the Pi bench (`rpm`, `speed_kmh`, `fuel_pct`, `ect_c`, `batt_v`, `odo_km`, optional `lamps`). Client-side mock drive - no Raspberry Pi, no ESP32.

Geometry is **not** hand-placed here: `lib/geometry.ts` reads `lib/faceSpec.json`, exported from `src/face_spec.py`, so the SVG and pygame share every anchor (`uv run python src/face_spec.py` to refresh). Tach cells light in 100 rpm steps with the red hatch past 9; numerals sit in the well in bundled M PLUS Rounded 1c. Off telltales stay just above black so the strip still reads; cruise lights the ISO high beam; green turn lamps pulse at about 85 flashes/min. Inline ISO pictograms (`components/LampIcons.tsx`) keep the strip sharp. TEMP uses the OEM coolant-wave thermometer; FUEL is a pump with hose.

**Face styles:** **AP1** (default - horizontal TEMP / FUEL flanking the speedo) and **AP2** (interpretive stacked arched side gauges + clock). Toggle on the desk or open `/?style=ap2`. AP2 is **not** a measured plate.

**Unofficial DIY.** Not affiliated with Honda Motor Co., Ltd. Title mark is an original geometric H, not Honda trademark artwork.

## Local

```bash
cd apps/harness
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) (also `/harness`).

```bash
npm run build
npm test
```

Play / pause, **AP1 / AP2** face presets, and drive presets: **Idle**, **Cruise**, **VTEC**, **Warn**. Space skips the ID.4-style boot (sweep → READY → reveal). Telltale pictograms live in `components/LampIcons.tsx`; SVG plates in `public/icons/` still match `assets/icons/`. Current web stills: [`docs/assets/web-ap1-cruise.png`](../../docs/assets/web-ap1-cruise.png), [`web-ap1-warn.png`](../../docs/assets/web-ap1-warn.png), [`web-ap2-warn.png`](../../docs/assets/web-ap2-warn.png).

## Vercel

Create a project rooted at **`apps/harness`**.

1. [vercel.com/new](https://vercel.com/new) → import `johnnyhuy/s2000-digital-dash`
2. **Root Directory**: `apps/harness`
3. Framework preset: Next.js (auto)
4. Deploy

The Vercel project itself can be renamed to **s2000-digital-dash** for consistency; Root Directory stays `apps/harness`.

CLI from this folder:

```bash
npx vercel --yes
```

`vercel.json` in this directory sets `framework: nextjs`.
