"""Shared display response, a demo contract rather than measured OEM timing."""
import json
from pathlib import Path

SMOOTH_TAU_S = {
    "rpm": .18, "speed_kmh": .12, "fuel_pct": .32, "ect_c": .38, "batt_v": .20,
}


def export_json():
    return json.dumps(SMOOTH_TAU_S, indent=2) + "\n"


if __name__ == "__main__":
    target = Path(__file__).resolve().parents[1] / "apps/harness/lib/motionSpec.json"
    target.write_text(export_json())
