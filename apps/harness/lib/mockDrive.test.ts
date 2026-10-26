import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { REQUIRED_FIELDS } from "./protocol.ts";
import { SCENARIOS, frameAt, expSmooth, followDisplay, snapDisplay } from "./mockDrive.ts";

describe("mock drive", () => {
  it("holds response when time does not advance", () => {
    assert.equal(expSmooth(100, 9000, 0, .18), 100);
    assert.equal(expSmooth(100, 9000, -.01, .18), 100);
  });

  it("uses the same 180ms RPM response at 30, 60 and 120 fps", () => {
    const target = { ...frameAt(0, 0, "idle"), rpm: 9000 };
    for (const fps of [30, 60, 120]) {
      let current = snapDisplay({ ...target, rpm: 0 }, 0);
      for (let i = 0; i < fps; i++) current = followDisplay(current, target, 1 / fps, 0);
      assert.ok(Math.abs(current.rpm - expSmooth(0, 9000, 1, .18)) < 1e-8);
    }
  });
  for (const scenario of SCENARIOS) {
    it(`emits frozen fields for ${scenario}`, () => {
      const frame = frameAt(1.25, 142_857.3, scenario);
      for (const key of REQUIRED_FIELDS) {
        assert.equal(typeof frame[key], "number");
      }
      assert.equal(typeof frame.lamps, "object");
    });
  }

  it("warn lights the OEM extras", () => {
    const frame = frameAt(0, 0, "warn");
    assert.equal(frame.fuel_pct, 8);
    assert.equal(frame.ect_c, 108);
    assert.equal(frame.lamps.cel, true);
    assert.equal(frame.lamps.brake, true);
  });

  it("cruise keeps a night high-beam lamp", () => {
    const frame = frameAt(0, 0, "cruise");
    assert.equal(frame.lamps.high_beam, true);
    assert.equal(frame.lamps.turn_l, false);
  });
});
