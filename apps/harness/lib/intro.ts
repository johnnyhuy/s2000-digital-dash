/** OEM-style boot clock — same phase lengths as src/gauge_ui.py.
 *  sweep = bar 0→9 + bulb check; ready = Honda H + S2000 badge; reveal settles. */

import { RPM_REDLINE } from "./protocol.ts";

export const PHASE_SWEEP_S = 1.35;
export const PHASE_READY_S = 1.75;
export const PHASE_REVEAL_S = 1.55;

export const INTRO_PHASES = ["sweep", "ready", "reveal", "live"] as const;
export type IntroPhase = (typeof INTRO_PHASES)[number];

export function introDurationS(): number {
  return PHASE_SWEEP_S + PHASE_READY_S + PHASE_REVEAL_S;
}

export function introPhaseAt(t: number): { phase: IntroPhase; local: number } {
  let clock = t < 0 ? 0 : t;
  if (clock < PHASE_SWEEP_S) return { phase: "sweep", local: clock / PHASE_SWEEP_S };
  clock -= PHASE_SWEEP_S;
  if (clock < PHASE_READY_S) return { phase: "ready", local: clock / PHASE_READY_S };
  clock -= PHASE_READY_S;
  if (clock < PHASE_REVEAL_S) return { phase: "reveal", local: clock / PHASE_REVEAL_S };
  return { phase: "live", local: 1 };
}

export function smoothstep(t: number): number {
  const x = t < 0 ? 0 : t > 1 ? 1 : t;
  return x * x * (3 - 2 * x);
}

/** Self-test: 0 → slight redline overshoot, then settle onto live RPM. */
export function revealRpm(localT: number, liveRpm: number): number {
  const t = localT < 0 ? 0 : localT > 1 ? 1 : localT;
  const peak = RPM_REDLINE * 1.03;
  if (t < 0.52) return peak * smoothstep(t / 0.52);
  if (t < 0.62) return peak;
  return peak + (liveRpm - peak) * smoothstep((t - 0.62) / 0.38);
}
