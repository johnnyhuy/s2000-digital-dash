import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  FACE,
  MODULE_ASPECT,
  MODULE_H,
  RPM_MAX,
  VIEW_W,
  arcPx,
  buildFaceGeom,
  crownSpringX,
  hoodPath,
  lcdPath,
  specFor,
  tachAngleDeg,
  tachArchNormal,
  tachArchXY,
  tachBandPath,
  tachNumXY,
  tachTickPath,
  tempSegmentsLit,
  visorLipPoly,
} from "./geometry.ts";

function near(got: number, want: number, delta: number) {
  assert.ok(Math.abs(got - want) <= delta, `${got} !≈ ${want} ±${delta}`);
}

const pctX = (x: number) => (x - FACE.module.x) / FACE.module.w;
const pctY = (y: number) => (y - FACE.module.y) / FACE.module.h;

describe("face geometry (shared faceSpec.json lock)", () => {
  it("locks the module aspect and reads both styles from the spec", () => {
    near(VIEW_W / MODULE_H, MODULE_ASPECT, 0.001);
    assert.equal(FACE.style, "ap1");
    assert.equal(specFor("ap1").style, "ap1");
    assert.equal(specFor("ap2").style, "ap2");
    assert.equal(specFor("ap2").side_gauges_arched, true);
  });

  it("puts the tach on a true circular arc through the OEM tick positions", () => {
    const t = FACE.spec.tach;
    const c = { x: t.cx * FACE.module.w, y: (t.cy / MODULE_ASPECT) * FACE.module.w };
    for (const f of [0, 0.25, 0.5, 0.75, 1]) {
      const p = tachArchXY(f);
      near(Math.hypot(p.x - c.x, p.y - c.y) / FACE.module.w, t.r_line, 0.001);
    }
    // 0 / 9 ticks at x ≈ 0.19 / 0.81, y ≈ 0.36 H; band apex ≈ 2.3 % H
    near(pctX(tachArchXY(0).x), 0.19, 0.02);
    near(pctX(tachArchXY(1).x), 0.81, 0.02);
    near(pctY(tachArchXY(0).y), 0.36, 0.03);
    near(pctY(arcPx(FACE, t.r_out, -90).y), 0.023, 0.01);
  });

  it("squeezes 0→1 to 60 % of a division over a 75.6° sweep", () => {
    const first = tachAngleDeg(1000) - tachAngleDeg(0);
    const rest = (tachAngleDeg(9000) - tachAngleDeg(1000)) / 8;
    near(first / rest, 0.6, 0.02);
    near(tachAngleDeg(RPM_MAX) - tachAngleDeg(0), 75.6, 0.5);
    assert.equal(tachAngleDeg(RPM_MAX + 5000), tachAngleDeg(RPM_MAX));
  });

  it("seats numerals just inside the baseline along the inward normal", () => {
    for (const f of [0, 0.5, 1]) {
      const a = tachArchXY(f);
      const n = tachArchNormal(f);
      const p = tachNumXY(f);
      near(Math.hypot(p.x - a.x, p.y - a.y) / FACE.module.w, FACE.spec.tach.num_inset, 0.001);
      assert.ok((p.x - a.x) * n.x + (p.y - a.y) * n.y > 0);
      assert.ok(p.y > a.y);
    }
    near(pctY(tachNumXY(5 / 9).y), 0.19, 0.03);
    near(pctY(tachNumXY(0).y), 0.43, 0.03);
  });

  it("keeps hood, band, hatch, ticks and numerals on separate radii", () => {
    const t = FACE.spec.tach;
    assert.ok(FACE.spec.crown_r - t.r_out >= 0.012);
    assert.ok(t.r_in - t.r_line >= t.line_gap);
    assert.ok(t.hatch_inner_over <= t.line_gap * 0.25);
    const tickTip = t.r_line - t.tick_major[1];
    const numeralOuter = t.r_num + t.num_size / 2;
    assert.ok(tickTip - numeralOuter > 0.002);
  });

  it("draws the hood crown concentric with the band, clearing its apex, springing at ~5 % W", () => {
    const pts = visorLipPoly().split(" ").map((p) => p.split(",").map(Number));
    assert.ok(pts.length > 20);
    const mid = pts[Math.floor(pts.length / 2)];
    const apex = arcPx(FACE, FACE.spec.tach.r_out, -90);
    assert.ok(mid[1] < apex.y);
    const well = apex.y - mid[1];
    assert.ok(well > FACE.module.w * 0.010);
    assert.ok(well < FACE.module.w * 0.020);
    const c = arcPx(FACE, 0, -90);
    const radii = pts.map(([x, y]) => Math.hypot(x - c.x, y - c.y) / FACE.module.w);
    near(Math.max(...radii) - Math.min(...radii), 0, 0.002);
    near(Math.min(...radii), FACE.spec.tach.r_out + 0.014, 0.002);
    const half = crownSpringX(FACE.spec, FACE.spec.crown_r, FACE.spec.spring_y);
    near(0.5 - half, 0.05, 0.02);
    assert.match(hoodPath(), /^M .* Z$/);
    assert.match(lcdPath(), /^M .* Z$/);
  });

  it("locks the AP1 windows and side bars to the plate", () => {
    near(pctX(FACE.speedWin.x), 0.39, 0.02);
    near(pctY(FACE.speedWin.y), 0.3, 0.02);
    near(pctX(FACE.odoWin.x), 0.39, 0.02);
    near(pctY(FACE.odoWin.y), 0.57, 0.02);
    assert.ok(FACE.odoWin.y > FACE.speedWin.y + FACE.speedWin.h);
    near(pctX(FACE.temp.x), 0.13, 0.02);
    near(pctY(FACE.temp.y), 0.52, 0.02);
    near(pctX(FACE.fuel.x), 0.815, 0.02);
    assert.ok(FACE.temp.w > FACE.temp.h * 2.5);
    assert.ok(FACE.temp.x + FACE.temp.w < FACE.speedWin.x);
    assert.ok(FACE.fuel.x > FACE.speedWin.x + FACE.speedWin.w);
    assert.equal(FACE.spec.temp_segs, 8);
    assert.equal(FACE.spec.fuel_segs, 16);
    near(pctY(FACE.strip.y), 0.745, 0.02);
    assert.ok(FACE.strip.y > FACE.springY);
  });

  it("keeps AP2 in the same housing with arched gauges on the right", () => {
    const ap2 = buildFaceGeom("ap2");
    assert.equal(ap2.spec.crown_r, FACE.spec.crown_r);
    assert.ok(ap2.temp.y < ap2.fuel.y);
    assert.ok(ap2.temp.x > ap2.speedWin.x + ap2.speedWin.w);
    assert.ok(ap2.clock.y < ap2.odo.y);
    assert.ok(ap2.spec.tach.a9_deg < -60);
  });

  it("idles the temp blocks low like the real cluster", () => {
    assert.ok([3, 4].includes(tempSegmentsLit((89 - 40) / 65, 8)));
    assert.equal(tempSegmentsLit(0, 8), 0);
    assert.equal(tempSegmentsLit(1, 8), 8);
  });

  it("emits closed SVG paths for ticks and band sectors", () => {
    const d = tachTickPath(0.05, 2, 16);
    assert.match(d, /^M .* Z$/);
    const band = tachBandPath(0, 0.5, 1, 16);
    assert.match(band, /^M .* Z$/);
    assert.equal(tachBandPath(0.5, 0.5), "");
  });
});
