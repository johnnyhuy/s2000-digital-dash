/**
 * Frozen Phase 1 JSON telemetry — same field names as src/protocol.py.
 * Wire format on the Pi is one JSON object per newline. The harness speaks
 * the same object in memory.
 */

export const PROTOCOL_VERSION = 1;
export const MOCK_HZ = 20;

export const REQUIRED_FIELDS = [
  "rpm",
  "speed_kmh",
  "fuel_pct",
  "ect_c",
  "batt_v",
  "odo_km",
] as const;

export const LAMP_KEYS = [
  "oil",
  "cel",
  "abs",
  "turn_l",
  "turn_r",
  "high_beam",
  "fog",
  "fuel_low",
  "batt_warn",
  "ect_hot",
] as const;

export const OEM_EXTRA_LAMPS = [
  "brake",
  "immobilizer",
  "maint",
  "eps",
  "seatbelt",
  "door",
  "trunk",
  "srs",
] as const;

export const RPM_REDLINE = 9000;
export const RPM_VTEC = 6000;
export const SPEED_MAX_KMH = 280;
export const FUEL_LOW_PCT = 15;
export const ECT_HOT_C = 105;
export const BATT_LOW_V = 12.2;

export type LampMap = Record<string, boolean>;

export type Telemetry = {
  rpm: number;
  speed_kmh: number;
  fuel_pct: number;
  ect_c: number;
  batt_v: number;
  odo_km: number;
  lamps: LampMap;
};

export class ProtocolError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ProtocolError";
  }
}

export function emptyLamps(): LampMap {
  const lamps: LampMap = {};
  for (const key of LAMP_KEYS) lamps[key] = false;
  for (const key of OEM_EXTRA_LAMPS) lamps[key] = false;
  return lamps;
}

function asNumber(value: unknown, field: string): number {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string" && value.trim() !== "" && Number.isFinite(Number(value))) {
    return Number(value);
  }
  throw new ProtocolError(`bad numeric field: ${field}`);
}

export function validate(data: unknown): Telemetry {
  if (data === null || typeof data !== "object" || Array.isArray(data)) {
    throw new ProtocolError("payload must be a JSON object");
  }
  const raw = data as Record<string, unknown>;
  const missing = REQUIRED_FIELDS.filter((key) => !(key in raw));
  if (missing.length > 0) {
    throw new ProtocolError(`missing required fields: ${missing.join(", ")}`);
  }

  let fuel = asNumber(raw.fuel_pct, "fuel_pct");
  if (fuel < 0 || fuel > 100) fuel = Math.max(0, Math.min(100, fuel));

  const lamps: LampMap = {};
  if (raw.lamps !== undefined) {
    if (raw.lamps === null || typeof raw.lamps !== "object" || Array.isArray(raw.lamps)) {
      throw new ProtocolError("lamps must be an object of booleans");
    }
    for (const [key, value] of Object.entries(raw.lamps as Record<string, unknown>)) {
      lamps[String(key)] = Boolean(value);
    }
  }

  return {
    rpm: Math.trunc(asNumber(raw.rpm, "rpm")),
    speed_kmh: asNumber(raw.speed_kmh, "speed_kmh"),
    fuel_pct: fuel,
    ect_c: asNumber(raw.ect_c, "ect_c"),
    batt_v: asNumber(raw.batt_v, "batt_v"),
    odo_km: asNumber(raw.odo_km, "odo_km"),
    lamps,
  };
}

export function telemetryToDict(telem: Telemetry): Record<string, unknown> {
  const d: Record<string, unknown> = {
    rpm: Math.trunc(telem.rpm),
    speed_kmh: telem.speed_kmh,
    fuel_pct: telem.fuel_pct,
    ect_c: telem.ect_c,
    batt_v: telem.batt_v,
    odo_km: telem.odo_km,
  };
  if (Object.keys(telem.lamps).length > 0) {
    d.lamps = { ...telem.lamps };
  }
  return d;
}

export function telemetryToLine(telem: Telemetry): string {
  return `${JSON.stringify(telemetryToDict(telem))}\n`;
}

export function tryParseObject(data: unknown): Telemetry | null {
  try {
    return validate(data);
  } catch {
    return null;
  }
}
