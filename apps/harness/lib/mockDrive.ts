/**
 * Client-side mock drive — same frozen fields as src/mock_telemetry.py
 * and mocks/esp32_uart.py. Scenarios: idle / cruise / vtec / warn.
 */

import {
  BATT_LOW_V,
  ECT_HOT_C,
  FUEL_LOW_PCT,
  emptyLamps,
  type Telemetry,
} from "./protocol.ts";
import smoothTau from "./motionSpec.json" with { type: "json" };

export const START_ODO_KM = 142_857.3;

export const SCENARIOS = ["idle", "cruise", "vtec", "warn"] as const;
export type Scenario = (typeof SCENARIOS)[number];

export const SCENARIO_LABELS: Record<Scenario, string> = {
  idle: "Idle",
  cruise: "Cruise",
  vtec: "VTEC",
  warn: "Warn",
};

export type DisplayState = Telemetry & {
  trip_km: number;
};

function clamp(v: number, lo: number, hi: number): number {
  return v < lo ? lo : v > hi ? hi : v;
}

export function expSmooth(current: number, target: number, dt: number, tau: number): number {
  if (dt <= 0) return current;
  if (tau <= 0) return target;
  const k = 1 - Math.exp(-dt / tau);
  return current + (target - current) * k;
}

export function ectFrac(ectC: number): number {
  return clamp((ectC - 40) / 65, 0, 1);
}

export function fuelFrac(fuelPct: number): number {
  return clamp(fuelPct / 100, 0, 1);
}

function blink(t: number, hz = 1.35): boolean {
  return Math.floor(t * hz * 2) % 2 === 0;
}

function extrasOff(): Record<string, boolean> {
  return {
    brake: false,
    immobilizer: false,
    maint: false,
    eps: false,
    seatbelt: false,
    door: false,
    srs: false,
  };
}

/** Python mock_telemetry.driving_loop — idle → cruise → VTEC blip → coast. */
export function drivingLoop(t: number, odo: number): Telemetry {
  const pull = 0.5 + 0.5 * Math.sin(t * 0.25);
  let rpm = Math.trunc(1800 + 4200 * pull + 1800 * Math.max(0, Math.sin(t * 0.55)) ** 2);
  rpm = Math.max(850, Math.min(9200, rpm));

  const speed = Math.max(0, 35 + 95 * pull + 25 * Math.sin(t * 0.18));
  const fuel = Math.max(8, 62 - ((t * 0.02) % 40));
  const ect = 82 + 12 * (1 - Math.exp(-t / 45)) + 3 * Math.sin(t * 0.08);
  const batt = 14.1 - 0.4 * (rpm < 1000 ? 1 : 0) + 0.15 * Math.sin(t * 0.3);

  const blinkPhase = t % 16 < 3.2;
  const blinkOn = blinkPhase && Math.trunc(t * 2.4) % 2 === 0;

  return {
    rpm,
    speed_kmh: Math.round(speed * 10) / 10,
    fuel_pct: Math.round(fuel * 10) / 10,
    ect_c: Math.round(ect * 10) / 10,
    batt_v: Math.round(batt * 100) / 100,
    odo_km: Math.round(odo * 10) / 10,
    lamps: {
      ...emptyLamps(),
      ...extrasOff(),
      oil: rpm < 700,
      cel: false,
      abs: false,
      turn_l: blinkOn,
      turn_r: false,
      high_beam: Math.trunc(t / 20) % 5 === 0,
      fog: false,
      fuel_low: fuel < FUEL_LOW_PCT,
      batt_warn: batt < BATT_LOW_V,
      ect_hot: ect > ECT_HOT_C,
    },
  };
}

export function idleFrame(t: number, odo: number): Telemetry {
  const hunt = 850 + 40 * Math.sin(t * 3.1);
  return {
    rpm: Math.trunc(hunt),
    speed_kmh: 0,
    fuel_pct: 62,
    ect_c: 82 + 0.6 * Math.sin(t * 0.2),
    batt_v: 12.6 + 0.04 * Math.sin(t * 0.4),
    odo_km: Math.round(odo * 10) / 10,
    lamps: { ...emptyLamps(), ...extrasOff() },
  };
}

export function cruiseFrame(t: number, odo: number): Telemetry {
  const rpm = 3000 + 80 * Math.sin(t * 0.35);
  const speed = 80 + 2.4 * Math.sin(t * 0.22);
  return {
    rpm: Math.trunc(rpm),
    speed_kmh: Math.round(speed * 10) / 10,
    fuel_pct: 48,
    ect_c: 88 + 1.2 * Math.sin(t * 0.08),
    batt_v: 14.05 + 0.06 * Math.sin(t * 0.3),
    odo_km: Math.round(odo * 10) / 10,
    lamps: { ...emptyLamps(), ...extrasOff(), high_beam: true },
  };
}

export function vtecFrame(t: number, odo: number): Telemetry {
  const pull = 0.55 + 0.45 * Math.sin(t * 0.55);
  const rpm = Math.trunc(5200 + 3600 * pull);
  const speed = 118 + 42 * pull;
  return {
    rpm: Math.max(4800, Math.min(9100, rpm)),
    speed_kmh: Math.round(speed * 10) / 10,
    fuel_pct: 36,
    ect_c: 94 + 3 * pull,
    batt_v: 13.9,
    odo_km: Math.round(odo * 10) / 10,
    lamps: {
      ...emptyLamps(),
      ...extrasOff(),
      high_beam: false,
      fuel_low: false,
    },
  };
}

export function warnFrame(t: number, odo: number): Telemetry {
  const lamps = emptyLamps();
  for (const key of Object.keys(lamps)) lamps[key] = true;
  lamps.turn_l = blink(t);
  lamps.turn_r = blink(t);
  lamps.high_beam = true;
  return {
    rpm: 8200,
    speed_kmh: 12,
    fuel_pct: 8,
    ect_c: 108,
    batt_v: 11.8,
    odo_km: Math.round(odo * 10) / 10,
    lamps,
  };
}

export function frameAt(t: number, odo: number, scenario: Scenario): Telemetry {
  switch (scenario) {
    case "idle":
      return idleFrame(t, odo);
    case "cruise":
      return cruiseFrame(t, odo);
    case "vtec":
      return vtecFrame(t, odo);
    case "warn":
      return warnFrame(t, odo);
    default: {
      const _exhaustive: never = scenario;
      return _exhaustive;
    }
  }
}

export function followDisplay(
  current: DisplayState,
  target: Telemetry,
  dt: number,
  tripOrigin: number,
): DisplayState {
  return {
    rpm: expSmooth(current.rpm, target.rpm, dt, smoothTau.rpm),
    speed_kmh: expSmooth(current.speed_kmh, target.speed_kmh, dt, smoothTau.speed_kmh),
    fuel_pct: expSmooth(current.fuel_pct, target.fuel_pct, dt, smoothTau.fuel_pct),
    ect_c: expSmooth(current.ect_c, target.ect_c, dt, smoothTau.ect_c),
    batt_v: expSmooth(current.batt_v, target.batt_v, dt, smoothTau.batt_v),
    odo_km: target.odo_km,
    lamps: { ...target.lamps },
    trip_km: Math.max(0, target.odo_km - tripOrigin),
  };
}

export function snapDisplay(target: Telemetry, tripOrigin: number): DisplayState {
  return {
    ...target,
    trip_km: Math.max(0, target.odo_km - tripOrigin),
  };
}

export function integrateOdo(odo: number, speedKmh: number, dt: number): number {
  return odo + Math.max(0, speedKmh) / 3600 * dt;
}
