import {
  MODULE_H,
  RPM_MAX,
  VIEW_W,
  anchorPx,
  arcPath,
  faceGeom,
  hatchSpans,
  hoodPath,
  lcdPath,
  radialTickPath,
  rectPx,
  sideArchSector,
  cellWindow,
  divAt,
  scaleCells,
  tachAngleDeg,
  tachNumXY,
  tempSegmentsLit,
  tickRpms,
  visorLipPoly,
  wpx,
  hpx,
  type FaceGeom,
  type LampSpot,
  type Rect,
  type Tone,
} from "@/lib/geometry";
import type { CSSProperties } from "react";
import { SevenSeg } from "./SevenSeg";
import { PICTOGRAMS } from "./LampIcons";
import { DEFAULT_FACE_STYLE, type FaceStyle } from "@/lib/faceStyle";
import { type IntroPhase, revealRpm, smoothstep } from "@/lib/intro";
import { BATT_LOW_V, ECT_HOT_C, FUEL_LOW_PCT } from "@/lib/protocol";
import type { DisplayState } from "@/lib/mockDrive";
import { ectFrac, fuelFrac } from "@/lib/mockDrive";

// --- palette (matches src/gauge_ui.py) -----------------------------------------------
const COWL = "#1e1e20";
const COWL_EDGE = "#3e3e40";
const FACE_BLACK = "#070708";
const PANEL = "#181a1c";
const PANEL_EDGE = "#282a2c";
const STRIP = "#121214";
const STRIP_HI = "#2c2c30";
const LCD = "#42090b";
const LCD_OFF = "#160607";
const AMBER = "#f49420";
const AMBER_HOT = "#ffb03c";
const BAND_UNLIT_END = "#ac5c18";
const BAND_UNLIT_MID = "#6c380e";
const HATCH_AMBER = "#d0761e";
const HATCH_RED = "#9c2018";
const HATCH_RED_LIT = "#ff3c28";
const RED = "#e42820";
const RED_LCD = "#ff4228";
const RED_LCD_GHOST = "#4a0c0e";
const LABEL_OFF = "#3c0f0f";
const SEG_YELLOW = "#ffb22e";
const SEG_RED = "#ee2c22";
const SEG_GHOST = "#2a1408";
const GAUGE_WINDOW = "#380a0a";
const WHITE = "#f6f4ee";
const DIM = "#767064";
const BTN = "#969694";
const BTN_HI = "#c4c4c0";
const BTN_RING = "#3a3a3a";
const BTN_TEXT = "#282828";
const LAMP_GHOST = "#1c1a18";
const TONE: Record<Tone, string> = { red: "#e22820", amber: "#ec941c", green: "#22b84c", blue: "#1c54d8" };

function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

function lerpHex(a: string, b: string, t: number): string {
  const parse = (hex: string) => [parseInt(hex.slice(1, 3), 16), parseInt(hex.slice(3, 5), 16), parseInt(hex.slice(5, 7), 16)];
  const [ar, ag, ab] = parse(a);
  const [br, bg, bb] = parse(b);
  return `rgb(${Math.round(lerp(ar, br, t))},${Math.round(lerp(ag, bg, t))},${Math.round(lerp(ab, bb, t))})`;
}

// --- housing -------------------------------------------------------------------------
function Housing({ g }: { g: FaceGeom }) {
  const m = g.module;
  const bezel = { x: m.x, y: g.springY, w: m.w, h: m.y + m.h - g.springY };
  return (
    <g aria-hidden>
      <path d={hoodPath(g)} fill={COWL} stroke={COWL_EDGE} strokeWidth={1} strokeLinejoin="round" />
      <rect x={bezel.x} y={bezel.y} width={bezel.w} height={bezel.h} rx={wpx(g, 0.008)} fill={PANEL} stroke={PANEL_EDGE} strokeWidth={0.8} />
      <path d={lcdPath(g)} fill={FACE_BLACK} />
      <path d={lcdPath(g)} fill="url(#well-vignette)" />
      <polyline points={visorLipPoly(g)} fill="none" stroke="#403c38" strokeWidth={0.9} />
    </g>
  );
}

// --- printed tach (static) ---------------------------------------------------------------
function TachPrint({ g, dim }: { g: FaceGeom; dim?: boolean }) {
  const t = g.spec.tach;
  const mid = (t.a0_deg + t.a9_deg) / 2;
  const half = Math.max(1e-6, (t.a9_deg - t.a0_deg) / 2);
  const band = scaleCells(t).map(({ rpm0, d0, d1 }) => {
    const u = Math.abs(((d0 + d1) / 2 - mid) / half);
    const fill = rpm0 >= t.redline_rpm ? HATCH_RED : lerpHex(BAND_UNLIT_MID, BAND_UNLIT_END, Math.min(1, u) ** 1.6);
    return <path key={`b${rpm0}`} d={arcPath(g, t.r_out, t.r_in, d0, d1, 2)} fill={fill} />;
  });
  const hatch = (["left", "right"] as const).flatMap((side) =>
    hatchSpans(t, side).map(([d0, d1]) => (
      <path
        key={`${side}${d0.toFixed(2)}`}
        d={arcPath(g, t.r_out, t.r_in - t.hatch_inner_over, d0, d1, 1)}
        fill={side === "left" ? HATCH_AMBER : HATCH_RED}
      />
    )),
  );
  const ticks = tickRpms(t).map(({ rpm, major }) => {
    const [w, len] = major ? t.tick_major : t.tick_minor;
    return <path key={`t${rpm}`} d={radialTickPath(g, t.r_line + t.line_w / 2, len, w, tachAngleDeg(rpm, g))} fill={dim ? DIM : WHITE} />;
  });
  const zero = tachNumXY(0, g);
  const numSize = wpx(g, t.num_size);
  return (
    <g aria-hidden className="tach-print">
      {band}
      {hatch}
      <path d={arcPath(g, t.r_line + t.line_w / 2, t.r_line - t.line_w / 2, t.a0_deg, t.a9_deg)} fill={dim ? DIM : WHITE} />
      {ticks}
      {Array.from({ length: 10 }, (_, i) => {
        const p = tachNumXY(i / 9, g);
        return (
          <text key={i} className="tach-num" x={p.x} y={p.y + numSize * 0.36} fontSize={numSize} fill={dim ? DIM : WHITE} textAnchor="middle">
            {i}
          </text>
        );
      })}
      <text className="unit-label" x={zero.x + wpx(g, g.spec.rpm_dx)} y={zero.y + wpx(g, g.spec.rpm_dy + 0.003)} fontSize={wpx(g, 0.009)} fill={dim ? DIM : WHITE} textAnchor="middle">
        x1000r/min
      </text>
    </g>
  );
}

// --- lit bar graph -------------------------------------------------------------------------
function TachFill({ g, rpm }: { g: FaceGeom; rpm: number }) {
  const t = g.spec.tach;
  const step = t.cell_rpm;
  const r = Math.max(0, Math.min(RPM_MAX * 1.06, rpm));
  if (r < step * 0.5) return null;
  const aLit = t.a0_deg + divAt(t, r) * t.deg_per_div;
  const cells = [];
  for (let i = 0; i <= Math.floor(Math.min(r, RPM_MAX) / step); i += 1) {
    const r0 = i * step;
    const r1 = Math.min(r, r0 + step);
    if (r1 - r0 < 1) continue;
    const [d0, d1] = cellWindow(t, r0, r1, r1 >= r0 + step);
    if (d1 <= d0) continue;
    cells.push(<path key={r0} d={arcPath(g, t.r_out, t.r_in, d0, d1, 2)} fill={r0 >= t.redline_rpm ? HATCH_RED_LIT : AMBER} />);
  }
  const over =
    r > RPM_MAX
      ? hatchSpans(t, "right")
          .filter(([d0, d1]) => (d0 + d1) / 2 <= aLit)
          .map(([d0, d1]) => <path key={`h${d0.toFixed(2)}`} d={arcPath(g, t.r_out, t.r_in - t.hatch_inner_over, d0, d1, 1)} fill={HATCH_RED_LIT} />)
      : null;
  return (
    <g aria-hidden className="tach-fill">
      {cells}
      {over}
    </g>
  );
}

// --- LCD windows -------------------------------------------------------------------------
function LcdWindow({ r, on, rx }: { r: Rect; on: boolean; rx: number }) {
  return (
    <g className="lcd-window">
      <rect x={r.x} y={r.y} width={r.w} height={r.h} rx={rx} fill={on ? LCD : LCD_OFF} stroke="#240909" strokeWidth={0.6} />
      <rect x={r.x} y={r.y} width={r.w} height={r.h * 0.45} rx={rx} fill="url(#lcd-glass)" />
    </g>
  );
}

function SpeedWindow({ g, speed, on, bulbCheck }: { g: FaceGeom; speed: number; on: boolean; bulbCheck: boolean }) {
  const s = g.spec;
  const win = g.speedWin;
  const rx = wpx(g, 0.004);
  const text = bulbCheck ? "188" : String(speed).padStart(3, " ");
  return (
    <g>
      <LcdWindow r={win} on={on} rx={rx} />
      {on ? (
        <>
          <SevenSeg text={text} ghost="888" digitH={hpx(g, s.speed_digit_h)} color={RED_LCD} ghostColor={RED_LCD_GHOST} x={wpx(g, s.speed_right)} y={g.speed.y} align="right" />
          <text className="lcd-label" x={wpx(g, s.unit_x)} y={hpx(g, s.unit_y_top) + wpx(g, 0.006)} fontSize={wpx(g, 0.017)} fill={LABEL_OFF}>
            mph
          </text>
          <text className="lcd-label" x={wpx(g, s.unit_x)} y={hpx(g, s.unit_y_bot) + wpx(g, 0.006)} fontSize={wpx(g, 0.017)} fill={RED_LCD}>
            km/h
          </text>
        </>
      ) : null}
    </g>
  );
}

function OdoWindow({ g, face, on, battWarn, clock }: { g: FaceGeom; face: DisplayState; on: boolean; battWarn: boolean; clock: string }) {
  const s = g.spec;
  const win = g.odoWin;
  const rx = wpx(g, 0.004);
  const odo = String(Math.round(face.odo_km) % 1_000_000).padStart(6, "0");
  const trip = Math.max(0, Math.min(999.9, face.trip_km)).toFixed(1).padStart(5, "0");
  const tripLabel = anchorPx(g, s.trip_label);
  return (
    <g>
      <LcdWindow r={win} on={on} rx={rx} />
      {on ? (
        <g>
          <SevenSeg text={odo} ghost="888888" digitH={hpx(g, s.odo_digit_h)} color={RED_LCD} ghostColor={RED_LCD_GHOST} x={wpx(g, s.odo_left)} y={hpx(g, s.odo_cy)} align="left" />
          <text className="lcd-label" x={tripLabel.x} y={tripLabel.y + wpx(g, 0.004)} fontSize={wpx(g, 0.0105)} fill={RED_LCD} textAnchor="middle">
            TRIP A
          </text>
          <SevenSeg text={trip} ghost="888.8" digitH={hpx(g, s.trip_digit_h)} color={RED_LCD} ghostColor={RED_LCD_GHOST} x={wpx(g, s.trip_right)} y={hpx(g, s.trip_cy)} align="right" />
          {s.clock ? <SevenSeg text={clock} ghost="88:88" digitH={hpx(g, s.trip_digit_h)} color={RED_LCD} ghostColor={RED_LCD_GHOST} x={g.clock.x} y={g.clock.y} align="left" /> : null}
          {battWarn ? (
            <text x={win.x + win.w + wpx(g, 0.012)} y={win.y + wpx(g, 0.012)} fontSize={wpx(g, 0.01)} fontWeight={700} fill={RED} className="lcd-label">
              {`${face.batt_v.toFixed(1)}V`}
            </text>
          ) : null}
        </g>
      ) : null}
    </g>
  );
}

// --- side gauges ------------------------------------------------------------------------------
function CoolantIcon({ x, y, h, fill }: { x: number; y: number; h: number; fill: string }) {
  const s = h / 30;
  return (
    <g transform={`translate(${x} ${y}) scale(${s})`} fill={fill} stroke={fill} aria-hidden>
      <rect x="-1.45" y="-15.2" width="2.9" height="16.4" rx="1.45" stroke="none" />
      <circle cx="0" cy="4.7" r="4.35" stroke="none" />
      <circle cx="0" cy="4.7" r="1.45" fill={FACE_BLACK} stroke="none" />
      <path d="M2.2 -11.6h5.1M2.2 -7.1h5.1M2.2 -2.6h5.1" strokeWidth="1.35" fill="none" strokeLinecap="round" />
      <path d="M-8.1 11.4c2.15-2.35 4.3-2.35 6.45 0s4.3 2.35 6.45 0 4.3-2.35 6.45 0" fill="none" strokeWidth="1.4" strokeLinecap="round" />
      <path d="M-7 14.9c1.95-2.05 3.9-2.05 5.85 0s3.9 2.05 5.85 0 3.9-2.05 5.85 0" fill="none" strokeWidth="1.3" strokeLinecap="round" />
    </g>
  );
}

function PumpIcon({ x, y, h, fill }: { x: number; y: number; h: number; fill: string }) {
  const s = h / 22;
  return (
    <g transform={`translate(${x} ${y}) scale(${s})`} fill={fill} stroke={fill} aria-hidden>
      <rect x="-7.4" y="-8.4" width="11.4" height="15.8" rx="1.05" stroke="none" />
      <rect x="-5.6" y="-13.8" width="7.8" height="5.6" rx="0.7" stroke="none" />
      <rect x="-4.6" y="-4.8" width="5.6" height="3.3" fill={FACE_BLACK} stroke="none" />
      <path d="M3.6 -3.9c6.6-5.6 12.4-0.4 11.8 7.4" fill="none" strokeWidth="1.7" strokeLinecap="round" />
      <rect x="12.6" y="-1.2" width="3.05" height="8.2" rx="0.7" stroke="none" />
      <rect x="-7.4" y="7.2" width="11.4" height="1.7" rx="0.35" stroke="none" />
    </g>
  );
}

/** AP1 horizontal block gauge inside a red-backlit window. */
function SegBar({ r, segs, lit, colour, on }: { r: Rect; segs: number; lit: number; colour: (i: number) => string; on: boolean }) {
  const pad = r.h * 0.16;
  const gap = Math.max(0.6, r.w * 0.012);
  const bw = (r.w - 2 * pad - gap * (segs - 1)) / segs;
  return (
    <g>
      <rect x={r.x} y={r.y} width={r.w} height={r.h} rx={r.h * 0.12} fill={on ? GAUGE_WINDOW : LCD_OFF} stroke="#1e0808" strokeWidth={0.5} />
      {on
        ? Array.from({ length: segs }, (_, i) => (
            <rect
              key={i}
              className={i < lit ? "seg-lit" : "seg-ghost"}
              x={r.x + pad + i * (bw + gap)}
              y={r.y + pad}
              width={bw}
              height={r.h - 2 * pad}
              fill={i < lit ? colour(i) : SEG_GHOST}
            />
          ))
        : null}
    </g>
  );
}

/** AP2 interpretive half-ring gauge. */
function ArchedGauge({ box, segs, lit, colour, on }: { box: Rect; segs: number; lit: number; colour: (i: number) => string; on: boolean }) {
  return (
    <g>
      <path d={sideArchSector(box, 0, 1, 1, 0.7, 36)} fill={on ? GAUGE_WINDOW : LCD_OFF} />
      {on
        ? Array.from({ length: segs }, (_, i) => (
            <path key={i} className={i < lit ? "seg-lit" : "seg-ghost"} d={sideArchSector(box, (i + 0.1) / segs, (i + 0.9) / segs, 0.95, 0.75, 3)} fill={i < lit ? colour(i) : SEG_GHOST} />
          ))
        : null}
    </g>
  );
}

function SideGauges({ g, face, on, bulbCheck }: { g: FaceGeom; face: DisplayState; on: boolean; bulbCheck: boolean }) {
  const s = g.spec;
  const hot = face.ect_c >= ECT_HOT_C;
  const low = face.fuel_pct < FUEL_LOW_PCT;
  const tempLit = bulbCheck ? s.temp_segs : hot ? s.temp_segs : tempSegmentsLit(ectFrac(face.ect_c), s.temp_segs);
  const fuelLit = bulbCheck ? s.fuel_segs : Math.round(fuelFrac(face.fuel_pct) * s.fuel_segs);
  const tempColour = (i: number) => (hot && i >= s.temp_segs - 2 ? SEG_RED : SEG_YELLOW);
  const fuelColour = (i: number) => (i === 0 ? SEG_RED : SEG_YELLOW);
  const tIcon = anchorPx(g, s.temp_icon);
  const fIcon = anchorPx(g, s.fuel_icon);
  const label = (a: { x: number; y: number }, text: string, fill: string) => {
    const p = anchorPx(g, a);
    return (
      <text className="unit-label" x={p.x} y={p.y + wpx(g, 0.006)} fontSize={wpx(g, 0.017)} fill={fill} textAnchor="middle">
        {text}
      </text>
    );
  };
  const litW = on ? WHITE : DIM;
  return (
    <g aria-hidden>
      <CoolantIcon x={tIcon.x} y={tIcon.y} h={wpx(g, s.temp_icon_h)} fill={hot && on ? RED : litW} />
      {label(s.temp_c, "C", litW)}
      {label(s.temp_h, "H", hot && on ? RED : litW)}
      <PumpIcon x={fIcon.x} y={fIcon.y} h={wpx(g, s.fuel_icon_h)} fill={low && on ? AMBER_HOT : litW} />
      {label(s.fuel_e, "E", low && on ? RED : litW)}
      {label(s.fuel_f, "F", litW)}
      {s.side_gauges_arched ? (
        <>
          <ArchedGauge box={g.temp} segs={s.temp_segs} lit={tempLit} colour={tempColour} on={on} />
          <ArchedGauge box={g.fuel} segs={s.fuel_segs} lit={fuelLit} colour={fuelColour} on={on} />
        </>
      ) : (
        <>
          <SegBar r={g.temp} segs={s.temp_segs} lit={tempLit} colour={tempColour} on={on} />
          <line x1={g.temp.x} x2={g.temp.x + g.temp.w} y1={hpx(g, s.temp_underline_y)} y2={hpx(g, s.temp_underline_y)} stroke={litW} strokeWidth={0.9} />
          <SegBar r={g.fuel} segs={s.fuel_segs} lit={fuelLit} colour={fuelColour} on={on} />
          <line x1={g.fuel.x} x2={g.fuel.x + g.fuel.w} y1={hpx(g, s.fuel_underline_y)} y2={hpx(g, s.fuel_underline_y)} stroke={litW} strokeWidth={0.9} />
          {on ? <rect x={g.fuel.x + g.fuel.w * 0.42} y={hpx(g, s.fuel_underline_y) - 3} width={0.9} height={3} fill={litW} /> : null}
        </>
      )}
    </g>
  );
}

// --- telltales ----------------------------------------------------------------------------------
function BrakeGlyph({ x, y, h, fill }: { x: number; y: number; h: number; fill: string }) {
  const r = h / 2;
  return (
    <g fill="none" stroke={fill} strokeWidth={h * 0.09} aria-hidden>
      <path d={`M ${x - r * 1.15} ${y - r * 0.7} A ${r * 1.35} ${r * 1.35} 0 0 0 ${x - r * 1.15} ${y + r * 0.7}`} />
      <path d={`M ${x + r * 1.15} ${y - r * 0.7} A ${r * 1.35} ${r * 1.35} 0 0 1 ${x + r * 1.15} ${y + r * 0.7}`} />
      <circle cx={x} cy={y} r={r * 0.78} />
      <line x1={x} x2={x} y1={y - r * 0.42} y2={y + r * 0.1} strokeLinecap="round" strokeWidth={h * 0.13} />
      <circle cx={x} cy={y + r * 0.38} r={h * 0.07} fill={fill} stroke="none" />
    </g>
  );
}

function Lamp({ g, spot, lit, index }: { g: FaceGeom; spot: LampSpot; lit: boolean; index: number }) {
  const p = anchorPx(g, spot);
  const colour = lit ? TONE[spot.tone] : LAMP_GHOST;
  const h = wpx(g, spot.size);
  const icon = spot.kind || spot.key;
  const cls = `telltale telltale-${spot.tone}${lit ? " telltale-on" : ""}`;
  const style = { ["--i" as string]: index, ["--lamp" as string]: colour } as CSSProperties;
  if (spot.word) {
    const lines = spot.word.split(" ");
    const two = lines.length > 1 && spot.word.length > 6;
    const size = wpx(g, two ? 0.0095 : 0.0125);
    return (
      <g className={cls} style={style} aria-label={spot.word}>
        {two ? (
          <>
            <text className="lamp-word" x={p.x} y={p.y - size * 0.15} fontSize={size} fill={colour} textAnchor="middle">
              {lines[0]}
            </text>
            <text className="lamp-word" x={p.x} y={p.y + size * 0.95} fontSize={size} fill={colour} textAnchor="middle">
              {lines.slice(1).join(" ")}
            </text>
          </>
        ) : (
          <text className="lamp-word" x={p.x} y={p.y + size * 0.36} fontSize={size} fill={colour} textAnchor="middle">
            {spot.word}
          </text>
        )}
      </g>
    );
  }
  if (icon === "brake") {
    return (
      <g className={cls} style={style} aria-label="Brake">
        <BrakeGlyph x={p.x} y={p.y} h={h} fill={colour} />
      </g>
    );
  }
  const Pictogram = icon in PICTOGRAMS ? PICTOGRAMS[icon as keyof typeof PICTOGRAMS] : null;
  if (!Pictogram) return null;
  return (
    <g className={cls} style={style} aria-label={spot.key}>
      <Pictogram x={p.x} y={p.y} width={h / 0.75} fill={colour} />
    </g>
  );
}

function ArcLamps({ g, lamps, bulbCheck }: { g: FaceGeom; lamps: Record<string, boolean | undefined>; bulbCheck: boolean }) {
  const r = wpx(g, g.spec.arc_lamp_r);
  return (
    <g aria-hidden>
      {g.spec.arc_lamps.map((spot, i) => {
        const p = anchorPx(g, spot);
        const lit = bulbCheck || Boolean(lamps[spot.key]);
        return (
          <g key={spot.key}>
            <circle cx={p.x} cy={p.y} r={r} fill="#101012" stroke="#2a2a2e" strokeWidth={0.7} />
            <Lamp g={g} spot={spot} lit={lit} index={i} />
          </g>
        );
      })}
    </g>
  );
}

function RoundButton({ g, c, label }: { g: FaceGeom; c: { x: number; y: number }; label: "−" | "+" }) {
  const p = anchorPx(g, c);
  const d = wpx(g, g.spec.btn_d);
  return (
    <g aria-hidden>
      <circle cx={p.x} cy={p.y} r={d / 2} fill={BTN_RING} />
      <circle cx={p.x} cy={p.y - d * 0.02} r={d * 0.44} fill="url(#btn-dome)" />
      <text x={p.x} y={p.y + d * 0.16} fontSize={d * 0.5} fontWeight={700} fill={BTN_TEXT} textAnchor="middle" className="unit-label">
        {label}
      </text>
    </g>
  );
}

function OvalButton({ g, c, label }: { g: FaceGeom; c: { x: number; y: number }; label: string }) {
  const p = anchorPx(g, c);
  const w = wpx(g, g.spec.oval_w);
  const h = hpx(g, g.spec.oval_h);
  return (
    <g aria-hidden>
      <rect x={p.x - w / 2} y={p.y - h / 2} width={w} height={h} rx={h / 2} fill={BTN_RING} />
      <rect x={p.x - w / 2 + 1} y={p.y - h / 2 + 1} width={w - 2} height={h - 2} rx={h / 2} fill="url(#btn-dome)" />
      <text x={p.x} y={p.y + h * 0.16} fontSize={Math.min(h * 0.42, (w / Math.max(3, label.length)) * 1.5)} fontWeight={700} fill={BTN_TEXT} textAnchor="middle" className="unit-label">
        {label}
      </text>
    </g>
  );
}

function CancelMark({ g }: { g: FaceGeom }) {
  const s = g.spec;
  const icon = anchorPx(g, s.cancel_icon);
  const text = anchorPx(g, s.cancel_text);
  const r = wpx(g, 0.006);
  return (
    <g aria-hidden>
      <circle cx={icon.x} cy={icon.y} r={r} fill="none" stroke={WHITE} strokeWidth={r * 0.28} />
      <circle cx={icon.x} cy={icon.y} r={r * 0.2} fill={WHITE} />
      <line x1={icon.x} y1={icon.y} x2={icon.x + r * 0.7} y2={icon.y - r * 0.7} stroke={WHITE} strokeWidth={r * 0.25} strokeLinecap="round" />
      <text className="unit-label" x={text.x} y={text.y + wpx(g, 0.0045)} fontSize={wpx(g, 0.0125)} fill={WHITE}>
        PUSH CANCEL
      </text>
    </g>
  );
}

function Hardware({ g, lamps, bulbCheck }: { g: FaceGeom; lamps: Record<string, boolean | undefined>; bulbCheck: boolean }) {
  const s = g.spec;
  const strip = g.strip;
  const units = anchorPx(g, s.units_label);
  const panel = (r: Rect | null) =>
    r ? <rect x={rectPx(g, r).x} y={rectPx(g, r).y} width={rectPx(g, r).w} height={rectPx(g, r).h} rx={wpx(g, 0.004)} fill={STRIP} stroke={STRIP_HI} strokeWidth={0.6} /> : null;
  return (
    <g>
      <rect x={strip.x} y={strip.y} width={strip.w} height={strip.h} rx={strip.h * 0.18} fill={STRIP} stroke={STRIP_HI} strokeWidth={0.8} />
      {panel(s.panel_left)}
      {panel(s.panel_right)}
      <g className="lamp-strip" role="group" aria-label="OEM telltales">
        {s.strip_lamps.map((spot, i) => (
          <Lamp key={spot.key} g={g} spot={spot} lit={bulbCheck || Boolean(lamps[spot.key])} index={i} />
        ))}
        {s.panel_lamps.map((spot, i) => (
          <Lamp key={spot.key} g={g} spot={spot} lit={bulbCheck || Boolean(lamps[spot.key])} index={s.strip_lamps.length + i} />
        ))}
      </g>
      <RoundButton g={g} c={s.btn_minus} label="−" />
      <RoundButton g={g} c={s.btn_plus} label="+" />
      <OvalButton g={g} c={s.btn_sel} label={s.sel_label} />
      <OvalButton g={g} c={s.btn_trip} label="TRIP" />
      <CancelMark g={g} />
      <BrandLockup
        g={g}
        x={g.module.w / 2}
        y={hpx(g, g.spec.cancel_text.y)}
        hSize={wpx(g, 0.022)}
        badgeH={wpx(g, 0.012)}
      />
      <text className="unit-label" x={units.x} y={units.y + wpx(g, 0.004)} fontSize={wpx(g, 0.0105)} fill={WHITE} textAnchor="middle">
        mph·km/h
      </text>
    </g>
  );
}

// --- boot card --------------------------------------------------------------------------------------
const S2000_BADGE_ASPECT = 2731.535 / 245.88;

function BrandLockup({
  g,
  x,
  y,
  hSize,
  badgeH,
}: {
  g: FaceGeom;
  x: number;
  y: number;
  hSize: number;
  badgeH: number;
}) {
  const badgeW = badgeH * S2000_BADGE_ASPECT;
  const gap = wpx(g, 0.008);
  const total = hSize + gap + badgeW;
  const x0 = x - total / 2;
  return (
    <g aria-hidden className="brand-lockup">
      <image href="/docs/assets/honda-h-mark.svg" x={x0} y={y - hSize / 2} width={hSize} height={hSize} />
      <image
        href="/docs/assets/s2000-badge-on-dark.svg"
        x={x0 + hSize + gap}
        y={y - badgeH / 2}
        width={badgeW}
        height={badgeH}
      />
    </g>
  );
}

function ReadyBrand({ g }: { g: FaceGeom }) {
  const mid = g.module.w / 2;
  const hSize = wpx(g, 0.058);
  const badgeH = wpx(g, 0.018);
  const badgeW = badgeH * S2000_BADGE_ASPECT;
  return (
    <g aria-hidden className="ready-brand">
      <image
        href="/docs/assets/honda-h-mark.svg"
        x={mid - hSize / 2}
        y={hpx(g, 0.298) - hSize / 2}
        width={hSize}
        height={hSize}
      />
      <image
        href="/docs/assets/s2000-badge-on-dark.svg"
        x={mid - badgeW / 2}
        y={hpx(g, 0.388) - badgeH / 2}
        width={badgeW}
        height={badgeH}
      />
    </g>
  );
}

function ReadyCard({ g, face }: { g: FaceGeom; face: DisplayState }) {
  const sw = g.speedWin;
  const cx = sw.x + sw.w / 2;
  const chips: Array<[string, string]> = [
    ["BATT", `${face.batt_v.toFixed(1)}V`],
    ["FUEL", `${face.fuel_pct.toFixed(0)}%`],
    ["TEMP", `${face.ect_c.toFixed(0)}°C`],
    ["ODO", `${Math.round(face.odo_km).toLocaleString("en-AU")}km`],
  ];
  return (
    <g className="ready-card">
      <ReadyBrand g={g} />
      <text x={cx} y={sw.y + sw.h * 0.78} textAnchor="middle" fontSize={wpx(g, 0.046)} fontWeight={700} fill={AMBER_HOT} className="ready-word" letterSpacing="0.06em">
        READY
      </text>
      {chips.map(([name, val], i) => {
        const x = g.module.w * (0.30 + 0.13 * i);
        return (
          <g key={name}>
            <text className="unit-label" x={x} y={hpx(g, 0.555)} textAnchor="middle" fontSize={wpx(g, 0.0085)} fill={DIM}>
              {name}
            </text>
            <text className="unit-label" x={x} y={hpx(g, 0.593)} textAnchor="middle" fontSize={wpx(g, 0.0135)} fill={AMBER}>
              {val}
            </text>
          </g>
        );
      })}
    </g>
  );
}

// --- face -----------------------------------------------------------------------------------------------
const FACE_CLOCK = "11:03";

export function ClusterFace({
  face,
  style = DEFAULT_FACE_STYLE,
  phase = "live",
  phaseT = 1,
}: {
  face: DisplayState;
  style?: FaceStyle;
  phase?: IntroPhase;
  phaseT?: number;
}) {
  const g = faceGeom(style);
  const selfTest = phase === "sweep";
  const liveLike = phase === "live" || phase === "reveal";
  const rpm = selfTest ? RPM_MAX * smoothstep(phaseT) : phase === "reveal" ? revealRpm(phaseT, face.rpm) : liveLike ? face.rpm : 0;
  const bulbCheck = selfTest || (phase === "reveal" && phaseT < 0.55);
  const battWarn = liveLike && (face.batt_v < BATT_LOW_V || Boolean(face.lamps.batt_warn));
  const speed = Math.round(Math.max(0, Math.min(399, face.speed_kmh)));
  const lamps = liveLike ? face.lamps : {};
  const odoFace = bulbCheck ? { ...face, odo_km: 888888, trip_km: 888.8 } : face;
  const styleName = style === "ap2" ? "AP2" : "AP1";
  const rx = wpx(g, 0.012);
  // The cowl lip rises just past the module top (crown is concentric with the
  // band); give the viewBox that headroom so the rim is not clipped.
  const pad = wpx(g, g.spec.crown_lip);

  return (
    <figure className={`cluster cluster-${style} cluster-${phase}`}>
      <div className="cluster-stage">
        <svg viewBox={`0 ${-pad} ${VIEW_W} ${MODULE_H + pad}`} role="img" aria-label={`${styleName} cluster, ${speed} kilometres per hour, ${Math.round(rpm)} rpm`}>
          <defs>
            <radialGradient id="well-vignette" cx="50%" cy="30%" r="70%">
              <stop offset="0%" stopColor="#141012" stopOpacity="0.35" />
              <stop offset="100%" stopColor="#000" stopOpacity="0" />
            </radialGradient>
            <linearGradient id="lcd-glass" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#ffffff" stopOpacity="0.07" />
              <stop offset="100%" stopColor="#ffffff" stopOpacity="0" />
            </linearGradient>
            <radialGradient id="btn-dome" cx="40%" cy="32%" r="70%">
              <stop offset="0%" stopColor={BTN_HI} />
              <stop offset="100%" stopColor={BTN} />
            </radialGradient>
            <clipPath id={`face-clip-${style}`}>
              <rect x={g.module.x} y={g.module.y - pad} width={g.module.w} height={g.module.h + pad} rx={rx} />
            </clipPath>
          </defs>

          <g clipPath={`url(#face-clip-${style})`}>
            <Housing g={g} />
            <TachPrint g={g} dim={phase === "ready"} />
            {selfTest || liveLike ? <TachFill g={g} rpm={rpm} /> : null}
            <SideGauges g={g} face={face} on={selfTest || liveLike} bulbCheck={bulbCheck} />
            <SpeedWindow g={g} speed={speed} on={selfTest || liveLike} bulbCheck={bulbCheck} />
            <OdoWindow g={g} face={odoFace} on={selfTest || liveLike} battWarn={battWarn} clock={FACE_CLOCK} />
            {phase === "ready" ? <ReadyCard g={g} face={face} /> : null}
            <ArcLamps g={g} lamps={lamps} bulbCheck={bulbCheck} />
            <Hardware g={g} lamps={lamps} bulbCheck={bulbCheck} />
          </g>
        </svg>
      </div>
      <figcaption className="cluster-caption">{styleName}</figcaption>
    </figure>
  );
}
