import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { RPM_REDLINE } from "./protocol.ts";
import {
  PHASE_READY_S,
  PHASE_SWEEP_S,
  introDurationS,
  introPhaseAt,
  revealRpm,
  smoothstep,
} from "./intro.ts";

describe("boot intro", () => {
  it("walks sweep → ready → reveal → live", () => {
    assert.equal(introPhaseAt(0).phase, "sweep");
    assert.equal(introPhaseAt(PHASE_SWEEP_S + 0.01).phase, "ready");
    assert.equal(introPhaseAt(PHASE_SWEEP_S + PHASE_READY_S + 0.01).phase, "reveal");
    assert.equal(introPhaseAt(introDurationS() + 0.2).phase, "live");
  });

  it("sweeps rpm to redline then settles", () => {
    assert.equal(revealRpm(0, 2000), 0);
    assert.ok(revealRpm(0.3, 2000) > 3000);
    assert.ok(revealRpm(0.55, 2000) > RPM_REDLINE);
    assert.ok(Math.abs(revealRpm(1, 2000) - 2000) < 1e-6);
  });

  it("eases sweep with smoothstep", () => {
    assert.equal(smoothstep(0), 0);
    assert.equal(smoothstep(1), 1);
    assert.ok(smoothstep(0.25) < 0.25);
    assert.ok(smoothstep(0.75) > 0.75);
  });
});
