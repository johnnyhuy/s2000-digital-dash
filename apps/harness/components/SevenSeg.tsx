/**
 * OEM-style 7-seg glass: mitred 45° segments with a hairline gap, chamfered
 * outer corners, unlit "8" ghost behind every digit. Same proportions as
 * `src/lcd_digits.py`. Display only.
 */

const DIGITS: Record<string, string> = {
  "0": "abcdef",
  "1": "bc",
  "2": "abged",
  "3": "abcdg",
  "4": "bcfg",
  "5": "acdfg",
  "6": "acdefg",
  "7": "abc",
  "8": "abcdefg",
  "9": "abcdfg",
  " ": "",
  "-": "g",
};

export const DIGIT_W_RATIO = 0.58;
export const DIGIT_GAP_RATIO = 0.2;
export const STROKE_RATIO = 0.155;
export const SEG_GAP_RATIO = 0.016;
export const CORNER_RATIO = 0.045;

type Poly = Array<[number, number]>;

export function segmentPolys(x: number, y: number, w: number, h: number): Record<string, Poly> {
  const t = Math.max(1, h * STROKE_RATIO);
  const g = Math.max(0.3, h * SEG_GAP_RATIO);
  const c = h * CORNER_RATIO;
  const ym = y + h / 2;
  const xr = x + w;
  const yb = y + h;
  return {
    a: [
      [x + g + c, y],
      [xr - g - c, y],
      [xr - t - g, y + t],
      [x + t + g, y + t],
    ],
    d: [
      [x + t + g, yb - t],
      [xr - t - g, yb - t],
      [xr - g - c, yb],
      [x + g + c, yb],
    ],
    f: [
      [x, y + g + c],
      [x + t, y + t + g],
      [x + t, ym - t / 2 - g],
      [x + t / 2, ym - g],
      [x, ym - t / 2 - g],
    ],
    b: [
      [xr, y + g + c],
      [xr, ym - t / 2 - g],
      [xr - t / 2, ym - g],
      [xr - t, ym - t / 2 - g],
      [xr - t, y + t + g],
    ],
    e: [
      [x, ym + t / 2 + g],
      [x + t / 2, ym + g],
      [x + t, ym + t / 2 + g],
      [x + t, yb - t - g],
      [x, yb - g - c],
    ],
    c: [
      [xr - t / 2, ym + g],
      [xr, ym + t / 2 + g],
      [xr, yb - g - c],
      [xr - t, yb - t - g],
      [xr - t, ym + t / 2 + g],
    ],
    g: [
      [x + t / 2 + g, ym],
      [x + t + g, ym - t / 2],
      [xr - t - g, ym - t / 2],
      [xr - t / 2 - g, ym],
      [xr - t - g, ym + t / 2],
      [x + t + g, ym + t / 2],
    ],
  };
}

const polyPath = (pts: Poly) => `M ${pts.map(([px, py]) => `${px.toFixed(2)} ${py.toFixed(2)}`).join(" L ")} Z`;

export function digitMetrics(digitH: number): { dw: number; gap: number; dot: number } {
  return { dw: digitH * DIGIT_W_RATIO, gap: digitH * DIGIT_GAP_RATIO, dot: digitH * 0.22 };
}

export function measureText(text: string, digitH: number): number {
  const { dw, gap, dot } = digitMetrics(digitH);
  let width = 0;
  for (const ch of text) width += ch === "." || ch === ":" ? dot : dw + gap;
  if (text && !text.endsWith(".") && !text.endsWith(":")) width -= gap;
  return width;
}

export function SevenSeg({
  text,
  ghost,
  digitH = 42,
  color = "#ff4228",
  ghostColor = "#4a0c0e",
  x = 0,
  y = 0,
  align = "left",
  className,
}: {
  text: string;
  /** Unlit silhouette (defaults to eights, dots / colons kept). */
  ghost?: string;
  digitH?: number;
  color?: string;
  ghostColor?: string;
  /** `x` is the left / centre / right edge per `align`; `y` is the vertical centre. */
  x?: number;
  y?: number;
  align?: "left" | "center" | "right";
  className?: string;
}) {
  const { dw, gap, dot } = digitMetrics(digitH);
  const total = measureText(text, digitH);
  const x0 = align === "left" ? x : align === "right" ? x - total : x - total / 2;
  const y0 = y - digitH / 2;
  const chars = text.split("");
  const gtext = (ghost ?? chars.map((ch) => (ch === "." || ch === ":" ? ch : "8")).join("")).padEnd(chars.length, " ").slice(0, chars.length);

  // left edge of every glyph cell
  const xs = chars.reduce<number[]>((acc, _ch, i) => {
    if (i === 0) return [x0];
    const prev = chars[i - 1];
    return [...acc, acc[i - 1] + (prev === "." || prev === ":" ? dot : dw + gap)];
  }, []);
  const nodes = chars.map((ch, i) => {
    const cx = xs[i];
    if (ch === "." || ch === ":") {
      const side = digitH * STROKE_RATIO * 0.9;
      const px = cx + (dot - side) / 2;
      const tops = ch === "." ? [y0 + digitH - side] : [y0 + digitH * 0.28 - side / 2, y0 + digitH * 0.72 - side / 2];
      return (
        <g key={`p${i}`}>
          {tops.map((py) => (
            <g key={py}>
              <rect x={px} y={py} width={side} height={side} fill={ghostColor} />
              <rect x={px} y={py} width={side} height={side} fill={color} className="seg-lit seg-red" />
            </g>
          ))}
        </g>
      );
    }
    const polys = segmentPolys(cx, y0, dw, digitH);
    const lit = new Set((DIGITS[ch] ?? "").split(""));
    const ghostLit = new Set((DIGITS[gtext[i]] ?? "abcdefg").split(""));
    return (
      <g key={`d${i}`}>
        {Object.entries(polys).map(([name, pts]) =>
          ghostLit.has(name) ? <path key={`g${name}`} d={polyPath(pts)} fill={ghostColor} /> : null,
        )}
        {Object.entries(polys).map(([name, pts]) =>
          lit.has(name) ? <path key={`l${name}`} d={polyPath(pts)} fill={color} className="seg-lit seg-red" /> : null,
        )}
      </g>
    );
  });

  return (
    <g className={className ? `seven-seg ${className}` : "seven-seg"} aria-hidden>
      {nodes}
    </g>
  );
}
