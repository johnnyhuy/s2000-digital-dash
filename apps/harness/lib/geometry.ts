/**
 * Face geometry — read straight from the shared lock (`faceSpec.json`,
 * exported by `src/face_spec.py`). The viewBox is the module bounding box:
 * 1000 × 425.53 (2.35:1). Spec fractions are `x / w / radii` of module
 * width and `y / h` of module height; tach / crown points are circular
 * arcs in width units, so the same maths drives pygame, this SVG and the CAD.
 */

import specJson from "./faceSpec.json" with { type: "json" };
import { DEFAULT_FACE_STYLE, type FaceStyle } from "./faceStyle.ts";

export const MODULE_ASPECT = 2.35;
export const VIEW_W = 1000;
export const MODULE_H = VIEW_W / MODULE_ASPECT;
export const RPM_MAX = 9000;

export type Rect = { x: number; y: number; w: number; h: number };
export type Pt = { x: number; y: number };
export type Tone = "red" | "amber" | "green" | "blue";

export type LampSpot = {
  key: string;
  kind: string;
  tone: Tone;
  size: number;
  word: string;
  x: number;
  y: number;
};

export type ArcSpec = {
  cx: number;
  cy: number;
  r_out: number;
  r_in: number;
  r_line: number;
  r_num: number;
  band: number;
  a0_deg: number;
  a9_deg: number;
  first_div: number;
  deg_per_div: number;
  hatch_deg: number;
  hatch_n: number;
  hatch_w_deg: number;
  hatch_inner_over: number;
  minors_per: number;
  line_w: number;
  line_gap: number;
  tick_major: [number, number];
  tick_minor: [number, number];
  num_inset: number;
  num_size: number;
};

export type FaceSpec = {
  style: FaceStyle;
  tach: ArcSpec;
  crown_cy: number;
  crown_r: number;
  crown_lip: number;
  spring_y: number;
  speed: Rect;
  speed_digit_h: number;
  speed_right: number;
  unit_x: number;
  unit_y_top: number;
  unit_y_bot: number;
  odo: Rect;
  odo_digit_h: number;
  odo_left: number;
  odo_cy: number;
  trip_label: Pt;
  trip_digit_h: number;
  trip_right: number;
  trip_cy: number;
  temp: Rect;
  temp_segs: number;
  temp_icon: Pt;
  temp_c: Pt;
  temp_h: Pt;
  temp_underline_y: number;
  fuel: Rect;
  fuel_segs: number;
  fuel_icon: Pt;
  fuel_e: Pt;
  fuel_f: Pt;
  fuel_underline_y: number;
  arc_lamps: LampSpot[];
  arc_lamp_r: number;
  strip: Rect;
  strip_lamps: LampSpot[];
  panel_left: Rect | null;
  panel_right: Rect | null;
  panel_lamps: LampSpot[];
  btn_minus: Pt;
  btn_plus: Pt;
  btn_d: number;
  cancel_icon: Pt;
  cancel_text: Pt;
  btn_sel: Pt;
  btn_trip: Pt;
  oval_w: number;
  oval_h: number;
  units_label: Pt;
  sel_label: string;
  clock: Pt | null;
  side_gauges_arched: boolean;
};

export const SPECS = specJson as unknown as Record<FaceStyle, FaceSpec>;

export function specFor(style: FaceStyle = DEFAULT_FACE_STYLE): FaceSpec {
  return SPECS[style];
}

export type FaceGeom = {
  style: FaceStyle;
  spec: FaceSpec;
  module: Rect;
  springY: number;
  lip: number;
  temp: Rect;
  fuel: Rect;
  speedWin: Rect;
  odoWin: Rect;
  strip: Rect;
  speed: Pt;
  odo: Pt;
  clock: Pt;
};

// --- unit helpers ---------------------------------------------------------------
const hToW = (yH: number) => yH / MODULE_ASPECT;

/** Module-width units (both axes) → viewBox px. */
export function px(g: FaceGeom, xw: number, yw: number): Pt {
  return { x: g.module.x + xw * g.module.w, y: g.module.y + yw * g.module.w };
}

export function wpx(g: FaceGeom, frac: number): number {
  return frac * g.module.w;
}

export function hpx(g: FaceGeom, frac: number): number {
  return frac * g.module.h;
}

export function rectPx(g: FaceGeom, r: Rect): Rect {
  return { x: g.module.x + r.x * g.module.w, y: g.module.y + r.y * g.module.h, w: r.w * g.module.w, h: r.h * g.module.h };
}

export function anchorPx(g: FaceGeom, a: Pt): Pt {
  return { x: g.module.x + a.x * g.module.w, y: g.module.y + a.y * g.module.h };
}

export function arcPx(g: FaceGeom, rW: number, deg: number): Pt {
  const t = g.spec.tach;
  const a = (deg * Math.PI) / 180;
  return px(g, t.cx + rW * Math.cos(a), hToW(t.cy) + rW * Math.sin(a));
}

export function crownPx(g: FaceGeom, rW: number, deg: number): Pt {
  const a = (deg * Math.PI) / 180;
  return px(g, g.spec.tach.cx + rW * Math.cos(a), hToW(g.spec.crown_cy) + rW * Math.sin(a));
}

/** Half-chord (W units) where a crown circle of radius `r` crosses `yH`. */
export function crownSpringX(spec: FaceSpec, r: number, yH: number): number {
  const dy = hToW(spec.crown_cy) - hToW(yH);
  return Math.sqrt(Math.max(0, r * r - dy * dy));
}

export function buildFaceGeom(style: FaceStyle = DEFAULT_FACE_STYLE): FaceGeom {
  const spec = specFor(style);
  const box = { x: 0, y: 0, w: VIEW_W, h: MODULE_H };
  const g: FaceGeom = {
    style,
    spec,
    module: box,
    springY: box.y + box.h * spec.spring_y,
    lip: box.w * spec.crown_lip,
    temp: { x: 0, y: 0, w: 0, h: 0 },
    fuel: { x: 0, y: 0, w: 0, h: 0 },
    speedWin: { x: 0, y: 0, w: 0, h: 0 },
    odoWin: { x: 0, y: 0, w: 0, h: 0 },
    strip: { x: 0, y: 0, w: 0, h: 0 },
    speed: { x: 0, y: 0 },
    odo: { x: 0, y: 0 },
    clock: { x: 0, y: 0 },
  };
  g.temp = rectPx(g, spec.temp);
  g.fuel = rectPx(g, spec.fuel);
  g.speedWin = rectPx(g, spec.speed);
  g.odoWin = rectPx(g, spec.odo);
  g.strip = rectPx(g, spec.strip);
  g.speed = { x: g.speedWin.x + g.speedWin.w / 2, y: g.speedWin.y + g.speedWin.h / 2 };
  g.odo = { x: g.odoWin.x + g.odoWin.w / 2, y: box.y + box.h * spec.odo_cy };
  g.clock = spec.clock ? anchorPx(g, spec.clock) : g.odo;
  return g;
}

const GEOM: Record<FaceStyle, FaceGeom> = {
  ap1: buildFaceGeom("ap1"),
  ap2: buildFaceGeom("ap2"),
};

export function faceGeom(style: FaceStyle = DEFAULT_FACE_STYLE): FaceGeom {
  return GEOM[style];
}

/** Default AP1 lock — kept for existing call sites / tests. */
export const FACE = GEOM.ap1;

// --- tach scale ------------------------------------------------------------------
export function divAt(t: ArcSpec, rpm: number): number {
  const k = rpm / 1000;
  return k <= 1 ? t.first_div * Math.max(0, k) : t.first_div + (k - 1);
}

export function tachAngleDeg(rpm: number, g: FaceGeom = FACE): number {
  const t = g.spec.tach;
  return t.a0_deg + divAt(t, Math.max(0, Math.min(RPM_MAX, rpm))) * t.deg_per_div;
}

/** Radians for a legacy 0–1 fraction of the 0–9 000 scale. */
export function tachAngle(frac: number, g: FaceGeom = FACE): number {
  const f = frac < 0 ? 0 : frac > 1 ? 1 : frac;
  return (tachAngleDeg(RPM_MAX * f, g) * Math.PI) / 180;
}

/** Point on the white baseline arc under the band. */
export function tachArchXY(frac: number, g: FaceGeom = FACE): Pt {
  return arcPx(g, g.spec.tach.r_line, (tachAngle(frac, g) * 180) / Math.PI);
}

/** Unit normal from the arc toward the centre (into the well). */
export function tachArchNormal(frac: number, g: FaceGeom = FACE): Pt {
  const a = tachAngle(frac, g);
  return { x: -Math.cos(a), y: -Math.sin(a) };
}

export function tachNumXY(frac: number, g: FaceGeom = FACE): Pt {
  return arcPx(g, g.spec.tach.r_num, (tachAngle(frac, g) * 180) / Math.PI);
}

export function tickRpms(t: ArcSpec): Array<{ rpm: number; major: boolean }> {
  const step = Math.floor(1000 / (t.minors_per + 1));
  const out: Array<{ rpm: number; major: boolean }> = [];
  for (let rpm = 0; rpm <= RPM_MAX; rpm += step) out.push({ rpm, major: rpm % 1000 === 0 });
  return out;
}

export function hatchAngles(t: ArcSpec, side: "left" | "right"): number[] {
  const step = (t.hatch_deg - 1) / t.hatch_n;
  const out: number[] = [];
  for (let i = 0; i < t.hatch_n; i += 1) {
    const off = 1.4 + step * i;
    out.push(side === "left" ? t.a0_deg - off : t.a9_deg + off);
  }
  return out;
}

const f2 = (v: number) => v.toFixed(2);

/** Closed sector between two radii (W units) and two screen angles (degrees). */
export function arcPath(g: FaceGeom, rHi: number, rLo: number, deg0: number, deg1: number, steps?: number): string {
  const span = Math.abs(deg1 - deg0);
  const n = Math.max(2, steps ?? Math.ceil(span / 1.5));
  const outer: string[] = [];
  const inner: string[] = [];
  for (let i = 0; i <= n; i += 1) {
    const d = deg0 + ((deg1 - deg0) * i) / n;
    const o = arcPx(g, rHi, d);
    const q = arcPx(g, rLo, d);
    outer.push(`${f2(o.x)},${f2(o.y)}`);
    inner.push(`${f2(q.x)},${f2(q.y)}`);
  }
  inner.reverse();
  return `M ${outer.join(" L ")} L ${inner.join(" L ")} Z`;
}

/**
 * Band sector between two scale fractions. `inner` / `outer` are viewBox px
 * offsets inward from the band's outer edge (outer defaults to the band).
 */
export function tachBandPath(frac0: number, frac1: number, inner = 0, outer?: number, g: FaceGeom = FACE, steps?: number): string {
  const t = g.spec.tach;
  const t0 = Math.max(0, Math.min(1, frac0));
  const t1 = Math.max(0, Math.min(1, frac1));
  if (t1 <= t0 + 1e-5) return "";
  const rHi = t.r_out - inner / g.module.w;
  const rLo = t.r_out - (outer === undefined ? t.band : outer / g.module.w);
  return arcPath(g, rHi, rLo, (tachAngle(t0, g) * 180) / Math.PI, (tachAngle(t1, g) * 180) / Math.PI, steps);
}

/** Thin rectangle along the radius from `rStart` inward (W units). */
export function radialTickPath(g: FaceGeom, rStart: number, lengthW: number, widthW: number, deg: number): string {
  const a = (deg * Math.PI) / 180;
  const nx = -Math.cos(a);
  const ny = -Math.sin(a);
  const tx = -ny;
  const ty = nx;
  const s = arcPx(g, rStart, deg);
  const hw = widthW * g.module.w * 0.5;
  const ln = lengthW * g.module.w;
  const pts = [
    [s.x - tx * hw, s.y - ty * hw],
    [s.x + tx * hw, s.y + ty * hw],
    [s.x + tx * hw + nx * ln, s.y + ty * hw + ny * ln],
    [s.x - tx * hw + nx * ln, s.y - ty * hw + ny * ln],
  ];
  return `M ${pts.map(([x, y]) => `${f2(x)} ${f2(y)}`).join(" L ")} Z`;
}

/** Tick at scale fraction `frac` hanging inward from the baseline (legacy px signature). */
export function tachTickPath(frac: number, widthPx: number, lengthPx: number, g: FaceGeom = FACE): string {
  return radialTickPath(g, g.spec.tach.r_line, lengthPx / g.module.w, widthPx / g.module.w, (tachAngle(frac, g) * 180) / Math.PI);
}

// --- housing ----------------------------------------------------------------------
function crownArc(g: FaceGeom, r: number, steps = 72): Pt[] {
  const s = g.spec;
  const half = crownSpringX(s, r, s.spring_y);
  const dy = -(hToW(s.crown_cy) - hToW(s.spring_y));
  const a0 = (Math.atan2(dy, half) * 180) / Math.PI; // right spring
  const a1 = (Math.atan2(dy, -half) * 180) / Math.PI; // left spring
  const pts: Pt[] = [];
  for (let i = 0; i <= steps; i += 1) pts.push(crownPx(g, r, a0 + ((a1 - a0) * i) / steps));
  return pts;
}

/** Cowl outline: lower bezel block plus the hood crown (crown radius + lip). */
export function hoodPath(g: FaceGeom = FACE): string {
  const m = g.module;
  const bot = m.y + m.h;
  const arc = crownArc(g, g.spec.crown_r + g.spec.crown_lip);
  const rightSpring = arc[0];
  const leftSpring = arc[arc.length - 1];
  return [
    `M ${f2(m.x)},${f2(bot)}`,
    `L ${f2(m.x + m.w)},${f2(bot)}`,
    `L ${f2(m.x + m.w)},${f2(g.springY)}`,
    `L ${f2(rightSpring.x)},${f2(rightSpring.y)}`,
    `L ${arc.map((p) => `${f2(p.x)},${f2(p.y)}`).join(" L ")}`,
    `L ${f2(leftSpring.x)},${f2(g.springY)}`,
    `L ${f2(m.x)},${f2(g.springY)}`,
    "Z",
  ].join(" ");
}

/** Black face aperture: crown inner edge over the top, full width below the spring. */
export function lcdPath(g: FaceGeom = FACE): string {
  const m = g.module;
  const lip = g.lip;
  const arc = crownArc(g, g.spec.crown_r);
  const rightSpring = arc[0];
  const leftSpring = arc[arc.length - 1];
  return [
    `M ${f2(rightSpring.x)},${f2(rightSpring.y)}`,
    `L ${arc.map((p) => `${f2(p.x)},${f2(p.y)}`).join(" L ")}`,
    `L ${f2(leftSpring.x)},${f2(g.springY)}`,
    `L ${f2(m.x + lip)},${f2(g.springY)}`,
    `L ${f2(m.x + lip)},${f2(m.y + m.h - lip)}`,
    `L ${f2(m.x + m.w - lip)},${f2(m.y + m.h - lip)}`,
    `L ${f2(m.x + m.w - lip)},${f2(g.springY)}`,
    "Z",
  ].join(" ");
}

/** Hood inner edge (crown circle) from spring to spring, as a polyline points list. */
export function visorLipPoly(g: FaceGeom = FACE, steps = 72): string {
  return crownArc(g, g.spec.crown_r, steps)
    .map((p) => `${f2(p.x)},${f2(p.y)}`)
    .join(" ");
}

// --- AP2 side gauges ---------------------------------------------------------------
export function sideArchGeom(box: Rect): { cx: number; cy: number; r: number } {
  return { cx: box.x + box.w / 2, cy: box.y + box.h, r: Math.min(box.w / 2, box.h) };
}

/** Half-ring from C/E (left, 180°) over the top to H/F (right, 360°). */
export function sideArchPoint(box: Rect, frac: number, rScale = 1): Pt {
  const { cx, cy, r } = sideArchGeom(box);
  const t = frac < 0 ? 0 : frac > 1 ? 1 : frac;
  const a = Math.PI + Math.PI * t;
  return { x: cx + r * rScale * Math.cos(a), y: cy + r * rScale * Math.sin(a) };
}

export function sideArchSector(box: Rect, frac0: number, frac1: number, rOuter = 1, rInner = 0.7, steps = 6): string {
  const outer: string[] = [];
  const inner: string[] = [];
  for (let i = 0; i <= steps; i += 1) {
    const f = frac0 + ((frac1 - frac0) * i) / steps;
    const o = sideArchPoint(box, f, rOuter);
    const q = sideArchPoint(box, f, rInner);
    outer.push(`${f2(o.x)},${f2(o.y)}`);
    inner.push(`${f2(q.x)},${f2(q.y)}`);
  }
  inner.reverse();
  return `M ${outer.join(" L ")} L ${inner.join(" L ")} Z`;
}

/** Blocks lit for an `ectFrac` — the OEM idles at 3–4 of 8 blocks then climbs fast. */
export function tempSegmentsLit(frac: number, segs: number): number {
  const f = Math.max(0, Math.min(1, frac));
  const knee = 0.85;
  const half = segs / 2;
  if (f <= knee) return Math.round((f / knee) * half);
  return Math.round(half + ((f - knee) / (1 - knee)) * (segs - half));
}
