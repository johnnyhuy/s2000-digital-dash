"""OEM S2000 face lock — one source of numbers for pygame, the web harness
and the replace-face CAD.

Everything is expressed as a fraction of the **module** bounding box
(2.35:1, 170 × 72.3 mm). ``x`` / ``w`` / radii are fractions of the module
**width**; ``y`` / ``h`` are fractions of the module **height**. Angles are
screen-space degrees (0° = +x, positive = clockwise, so the tach arc runs
from about −140° at 0 r/min to −40° at 9 000 r/min).

AP1 numbers were measured off ``refs/oem/lit/lit_ap1_carspy_cluster.jpg``
(horizontal spans are reliable; vertical spans were corrected for the
camera's downward angle). AP2 is read off ``refs/oem/ap2/`` and stays
interpretive. See ``refs/flat/DIMENSIONS.md`` for the measurement notes.

No pygame here — this module is pure maths so tests and the JSON export
stay cheap.
"""
from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path

MODULE_ASPECT = 2.35
RPM_MAX = 9000


def h_to_w(y_h: float) -> float:
    """Convert a module-height fraction into module-width units."""
    return y_h / MODULE_ASPECT


def w_to_h(y_w: float) -> float:
    return y_w * MODULE_ASPECT


@dataclass(frozen=True)
class Rect:
    """x / w in width units, y / h in height units."""

    x: float
    y: float
    w: float
    h: float

    @property
    def cx(self) -> float:
        return self.x + self.w / 2.0

    @property
    def cy(self) -> float:
        return self.y + self.h / 2.0


@dataclass(frozen=True)
class Anchor:
    x: float
    y: float


@dataclass(frozen=True)
class ArcSpec:
    """Bar-graph tachometer on a true circular arc."""

    cx: float = 0.50            # W
    cy: float = 1.300           # H — centre sits well below the module
    r_out: float = 0.543        # W — band outer edge (peak lands at ~2.3 % H)
    band: float = 0.033         # W — band thickness (r_in = r_out − band)
    a0_deg: float = -127.8      # 0 r/min   (ticks at x = 0.19 / 0.81, y = 0.36 H)
    a9_deg: float = -52.2       # 9 000 r/min  (75.6° sweep, measured)
    first_div: float = 0.60     # OEM squeezes 0→1 to ~60 % of a division
    hatch_deg: float = 5.5      # band overrun past 0 and 9 (5 stripes each)
    hatch_n: int = 5
    hatch_w_deg: float = 0.62
    hatch_inner_over: float = 0.0    # W — hatches stay inside the band (do not cross the ticks)
    minors_per: int = 4
    line_w: float = 0.0020      # W — white baseline arc under the band
    line_gap: float = 0.008     # W — dark gap so the baseline is not painted on the band
    tick_major: tuple[float, float] = (0.0024, 0.012)  # (w, len) in W
    tick_minor: tuple[float, float] = (0.0014, 0.007)
    num_inset: float = 0.034    # W — baseline → numeral centre (clears tick tips)
    num_size: float = 0.034     # W — font size (M PLUS Rounded 1c Bold)

    @property
    def r_in(self) -> float:
        return self.r_out - self.band

    @property
    def r_line(self) -> float:
        return self.r_in - self.line_gap - self.line_w / 2.0

    @property
    def r_num(self) -> float:
        return self.r_line - self.num_inset

    @property
    def divisions(self) -> float:
        return self.first_div + (RPM_MAX / 1000.0 - 1.0)

    @property
    def deg_per_div(self) -> float:
        return (self.a9_deg - self.a0_deg) / self.divisions

    def div_at(self, rpm: float) -> float:
        k = rpm / 1000.0
        if k <= 1.0:
            return self.first_div * max(0.0, k)
        return self.first_div + (k - 1.0)

    def angle_deg(self, rpm: float) -> float:
        return self.a0_deg + self.div_at(rpm) * self.deg_per_div

    def angle_for_frac(self, frac: float) -> float:
        """Legacy 0–1 fraction of the 0–9 000 scale."""
        return self.angle_deg(RPM_MAX * min(1.0, max(0.0, frac)))

    def point(self, r: float, deg: float) -> tuple[float, float]:
        """Point on the arc in **module-width units** (y is also in W)."""
        a = math.radians(deg)
        return self.cx + r * math.cos(a), h_to_w(self.cy) + r * math.sin(a)

    def normal(self, deg: float) -> tuple[float, float]:
        """Unit vector pointing from the arc toward the centre (inward)."""
        a = math.radians(deg)
        return -math.cos(a), -math.sin(a)

    def band_start_deg(self) -> float:
        return self.a0_deg - self.hatch_deg

    def band_end_deg(self) -> float:
        return self.a9_deg + self.hatch_deg

    def hatch_angles(self, side: str) -> list[float]:
        """Centre angles of the five printed stripes past 0 (left) or 9 (right)."""
        step = (self.hatch_deg - 1.0) / self.hatch_n
        out: list[float] = []
        for i in range(self.hatch_n):
            off = 1.4 + step * i
            out.append(self.a0_deg - off if side == "left" else self.a9_deg + off)
        return out

    def tick_rpms(self) -> list[tuple[int, bool]]:
        """(rpm, is_major) for every printed tick, 0 → 9 000."""
        out: list[tuple[int, bool]] = []
        step = 1000 // (self.minors_per + 1)
        for rpm in range(0, RPM_MAX + 1, step):
            out.append((rpm, rpm % 1000 == 0))
        return out


@dataclass(frozen=True)
class LampSpot:
    key: str
    x: float
    y: float
    kind: str = ""          # icon kind (defaults to key)
    tone: str = "red"
    size: float = 0.026     # W — icon height
    word: str = ""          # text lamp instead of pictogram

    @property
    def icon(self) -> str:
        return self.kind or self.key


@dataclass(frozen=True)
class FaceSpec:
    style: str
    tach: ArcSpec
    # crown circle (hood inner edge) — centre y in H, radius in W
    crown_cy: float
    crown_r: float
    crown_lip: float            # W — cowl lip thickness outside the aperture
    spring_y: float             # H — lower bezel top / crown spring line
    speed: Rect
    speed_digit_h: float        # H
    speed_right: float          # W — right edge of the digit run
    unit_x: float               # W — "km/h" / "mph" left edge
    unit_y_top: float           # H — first unit label centre (mph)
    unit_y_bot: float           # H — second unit label centre (km/h)
    odo: Rect
    odo_digit_h: float          # H
    odo_left: float             # W
    odo_cy: float               # H
    trip_label: Anchor
    trip_digit_h: float
    trip_right: float
    trip_cy: float
    temp: Rect
    temp_segs: int
    temp_icon: Anchor
    temp_c: Anchor
    temp_h: Anchor
    temp_underline_y: float     # H
    fuel: Rect
    fuel_segs: int
    fuel_icon: Anchor
    fuel_e: Anchor
    fuel_f: Anchor
    fuel_underline_y: float
    arc_lamps: tuple[LampSpot, ...]
    arc_lamp_r: float           # W — round window radius
    strip: Rect
    strip_lamps: tuple[LampSpot, ...]
    panel_left: Rect | None
    panel_right: Rect | None
    panel_lamps: tuple[LampSpot, ...]
    btn_minus: Anchor
    btn_plus: Anchor
    btn_d: float                # W
    cancel_icon: Anchor
    cancel_text: Anchor
    btn_sel: Anchor
    btn_trip: Anchor
    oval_w: float               # W
    oval_h: float               # H
    units_label: Anchor         # "mph·km/h"
    sel_label: str = "SEL"
    clock: Anchor | None = None
    side_gauges_arched: bool = False
    extras: dict[str, float] = field(default_factory=dict)


# The hood crown is CONCENTRIC with the tach. OEM leaves a visible dark
# well between the cowl lip and the band — a hairline gap makes the lip,
# the band and the tick baseline paint as one stroke.
CROWN_GAP = 0.014   # W — dark well between band outer edge and cowl
CROWN_LIP = 0.018   # W

_AP1_TACH = ArcSpec()
AP1 = FaceSpec(
    style="ap1",
    tach=_AP1_TACH,
    crown_cy=_AP1_TACH.cy,
    crown_r=_AP1_TACH.r_out + CROWN_GAP,
    crown_lip=CROWN_LIP,
    spring_y=0.58,
    speed=Rect(0.39, 0.30, 0.22, 0.24),
    speed_digit_h=0.20,
    speed_right=0.596,
    unit_x=0.622,
    unit_y_top=0.455,
    unit_y_bot=0.515,
    odo=Rect(0.39, 0.57, 0.22, 0.13),
    odo_digit_h=0.056,
    odo_left=0.408,
    odo_cy=0.648,
    trip_label=Anchor(0.572, 0.598),
    trip_digit_h=0.050,
    trip_right=0.598,
    trip_cy=0.655,
    temp=Rect(0.130, 0.520, 0.160, 0.055),
    temp_segs=8,
    temp_icon=Anchor(0.150, 0.478),
    temp_c=Anchor(0.121, 0.548),  # C hugs the bar: bar.x − half-letter − hair
    temp_h=Anchor(0.299, 0.548),  # H hugs the bar: bar right + half-letter + hair
    temp_underline_y=0.569,  # rule touches the block bottoms (no floating gap)
    fuel=Rect(0.815, 0.465, 0.110, 0.045),
    fuel_segs=16,
    fuel_icon=Anchor(0.905, 0.425),
    fuel_e=Anchor(0.806, 0.490),
    fuel_f=Anchor(0.934, 0.490),
    fuel_underline_y=0.506,  # rule touches the block bottoms (no floating gap)
    arc_lamps=(
        LampSpot("turn_l", 0.350, 0.340, tone="green", size=0.022),
        LampSpot("turn_r", 0.650, 0.340, tone="green", size=0.022),
        LampSpot("high_beam", 0.712, 0.420, tone="blue", size=0.020),
    ),
    arc_lamp_r=0.0185,
    strip=Rect(0.155, 0.745, 0.750, 0.140),
    strip_lamps=(
        LampSpot("brake", 0.190, 0.815, tone="red", size=0.030),
        LampSpot("batt_warn", 0.262, 0.815, kind="battery", tone="red", size=0.022),
        LampSpot("oil", 0.322, 0.815, tone="red", size=0.024),
        LampSpot("cel", 0.388, 0.815, tone="amber", size=0.024),
        LampSpot("abs", 0.462, 0.815, tone="amber", size=0.020, word="ABS"),
        LampSpot("maint", 0.545, 0.815, tone="amber", size=0.020, word="MAINT REQ'D"),
        LampSpot("eps", 0.635, 0.815, tone="amber", size=0.020, word="EPS"),
        LampSpot("srs", 0.715, 0.815, tone="red", size=0.020, word="SRS"),
        LampSpot("seatbelt", 0.800, 0.815, tone="red", size=0.030),
    ),
    panel_left=Rect(0.060, 0.615, 0.185, 0.090),
    panel_right=Rect(0.790, 0.590, 0.145, 0.090),
    panel_lamps=(
        LampSpot("cruise_main", 0.105, 0.660, tone="green", size=0.016, word="CRUISE MAIN"),
        LampSpot("cruise_on", 0.195, 0.660, tone="green", size=0.016, word="CRUISE CONTROL"),
        LampSpot("immobilizer", 0.830, 0.635, tone="green", size=0.022),
        LampSpot("door", 0.895, 0.635, tone="red", size=0.024),
    ),
    btn_minus=Anchor(0.060, 0.815),
    btn_plus=Anchor(0.118, 0.815),
    btn_d=0.050,
    cancel_icon=Anchor(0.157, 0.935),
    cancel_text=Anchor(0.172, 0.935),
    btn_sel=Anchor(0.935, 0.745),
    btn_trip=Anchor(0.978, 0.745),
    oval_w=0.040,
    oval_h=0.060,
    units_label=Anchor(0.900, 0.862),
)

# AP2 (2004–07): the same bar-graph engine, arc rotated so 9 lands near the
# top right, arched TEMP / FUEL on the right, clock row under the speed.
_AP2_TACH = ArcSpec(a0_deg=-132.0, a9_deg=-74.0, hatch_deg=6.5)
AP2 = FaceSpec(
    style="ap2",
    # Same housing and arc as AP1 - only the sweep differs (ends at 2 o'clock).
    tach=_AP2_TACH,
    crown_cy=_AP2_TACH.cy,
    crown_r=_AP2_TACH.r_out + CROWN_GAP,
    crown_lip=CROWN_LIP,
    spring_y=0.58,
    speed=Rect(0.394, 0.32, 0.19, 0.22),
    speed_digit_h=0.185,
    speed_right=0.572,
    unit_x=0.596,
    unit_y_top=0.455,
    unit_y_bot=0.515,
    odo=Rect(0.370, 0.55, 0.240, 0.17),
    odo_digit_h=0.056,
    odo_left=0.385,
    odo_cy=0.665,
    trip_label=Anchor(0.540, 0.600),
    trip_digit_h=0.050,
    trip_right=0.598,
    trip_cy=0.672,
    temp=Rect(0.690, 0.310, 0.150, 0.170),   # arched: rect is the arc box
    temp_segs=10,
    temp_icon=Anchor(0.765, 0.435),
    temp_c=Anchor(0.705, 0.490),
    temp_h=Anchor(0.825, 0.490),
    temp_underline_y=0.0,
    fuel=Rect(0.755, 0.540, 0.150, 0.170),
    fuel_segs=10,
    fuel_icon=Anchor(0.830, 0.665),
    fuel_e=Anchor(0.756, 0.735),
    fuel_f=Anchor(0.894, 0.735),
    fuel_underline_y=0.0,
    arc_lamps=(
        LampSpot("turn_l", 0.270, 0.680, tone="green", size=0.022),
        LampSpot("srs", 0.330, 0.680, tone="red", size=0.024, kind="seatbelt"),
        LampSpot("turn_r", 0.640, 0.680, tone="green", size=0.022),
        LampSpot("high_beam", 0.700, 0.680, tone="blue", size=0.020),
    ),
    arc_lamp_r=0.0185,
    strip=Rect(0.180, 0.760, 0.710, 0.130),
    strip_lamps=(
        LampSpot("brake", 0.220, 0.825, tone="red", size=0.030),
        LampSpot("abs", 0.282, 0.825, tone="amber", size=0.020, word="ABS"),
        LampSpot("batt_warn", 0.342, 0.825, kind="battery", tone="red", size=0.022),
        LampSpot("oil", 0.400, 0.825, tone="red", size=0.024),
        LampSpot("cel", 0.462, 0.825, tone="amber", size=0.024),
        LampSpot("maint", 0.545, 0.825, tone="amber", size=0.020, word="MAINT REQ'D"),
        LampSpot("eps", 0.635, 0.825, tone="amber", size=0.020, word="EPS"),
        LampSpot("immobilizer", 0.710, 0.825, tone="green", size=0.022),
        LampSpot("door", 0.775, 0.825, tone="red", size=0.024),
        LampSpot("seatbelt", 0.845, 0.825, tone="red", size=0.030),
    ),
    panel_left=None,
    panel_right=None,
    panel_lamps=(),
    btn_minus=Anchor(0.094, 0.825),
    btn_plus=Anchor(0.146, 0.825),
    btn_d=0.046,
    cancel_icon=Anchor(0.178, 0.930),
    cancel_text=Anchor(0.193, 0.930),
    btn_sel=Anchor(0.040, 0.825),
    btn_trip=Anchor(0.960, 0.825),
    oval_w=0.052,
    oval_h=0.060,
    units_label=Anchor(0.905, 0.930),
    sel_label="CLOCK",
    clock=Anchor(0.392, 0.592),
    side_gauges_arched=True,
)

SPECS: dict[str, FaceSpec] = {"ap1": AP1, "ap2": AP2}


def spec_for(style: str) -> FaceSpec:
    return SPECS[str(style).lower()]


def crown_point(spec: FaceSpec, r: float, deg: float) -> tuple[float, float]:
    """Point on the hood crown circle, module-width units."""
    a = math.radians(deg)
    return spec.tach.cx + r * math.cos(a), h_to_w(spec.crown_cy) + r * math.sin(a)


def crown_spring_x(spec: FaceSpec, r: float, y_h: float) -> float:
    """Half-chord where a crown circle of radius ``r`` crosses ``y_h``."""
    dy = h_to_w(spec.crown_cy) - h_to_w(y_h)
    return math.sqrt(max(0.0, r * r - dy * dy))


def spec_to_dict(spec: FaceSpec) -> dict:
    d = asdict(spec)
    d["tach"]["r_in"] = spec.tach.r_in
    d["tach"]["r_line"] = spec.tach.r_line
    d["tach"]["r_num"] = spec.tach.r_num
    d["tach"]["deg_per_div"] = spec.tach.deg_per_div
    d["module_aspect"] = MODULE_ASPECT
    return d


def export_json(dest: Path) -> Path:
    """Write the lock for the web harness (``apps/harness/lib/faceSpec.json``)."""
    payload = {style: spec_to_dict(spec) for style, spec in SPECS.items()}
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return dest


def _scad_value(v) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return repr(float(v)) if isinstance(v, float) else str(v)
    if isinstance(v, str):
        return '"' + v.replace('"', '\\"') + '"'
    if isinstance(v, Rect):
        return f"[{v.x!r}, {v.y!r}, {v.w!r}, {v.h!r}]"
    if isinstance(v, Anchor):
        return f"[{v.x!r}, {v.y!r}]"
    if isinstance(v, (list, tuple)):
        return "[" + ", ".join(_scad_value(i) for i in v) + "]"
    if v is None:
        return "[]"
    raise TypeError(type(v))


def spec_to_scad(spec: FaceSpec, prefix: str = "") -> str:
    """OpenSCAD assignments for the face lock (fractions, not mm).

    ``x``/``w``/radii are fractions of module width, ``y``/``h`` fractions of
    module height measured from the **top** (the CAD flips to y-up). Lamp
    spots are ``[x, y, size]``; rects ``[x, y, w, h]``; anchors ``[x, y]``.
    """
    t = spec.tach
    lines = [
        f"// {spec.style.upper()} face lock — generated by src/face_spec.py. Do not edit; edit the spec.",
        f'{prefix}style = "{spec.style}";',
        f"{prefix}module_aspect = {MODULE_ASPECT!r};",
        f"{prefix}tach_cx = {t.cx!r};",
        f"{prefix}tach_cy_h = {t.cy!r};",
        f"{prefix}tach_r_out = {t.r_out!r};",
        f"{prefix}tach_r_in = {t.r_in!r};",
        f"{prefix}tach_r_line = {t.r_line!r};",
        f"{prefix}tach_r_num = {t.r_num!r};",
        f"{prefix}tach_num_size = {t.num_size!r};",
        f"{prefix}tach_a0 = {t.a0_deg!r};",
        f"{prefix}tach_a9 = {t.a9_deg!r};",
        f"{prefix}tach_hatch_deg = {t.hatch_deg!r};",
        f"{prefix}crown_cy_h = {spec.crown_cy!r};",
        f"{prefix}crown_r = {spec.crown_r!r};",
        f"{prefix}crown_lip = {spec.crown_lip!r};",
        f"{prefix}spring_y_h = {spec.spring_y!r};",
        f"{prefix}speed_win = {_scad_value(spec.speed)};",
        f"{prefix}odo_win = {_scad_value(spec.odo)};",
        f"{prefix}temp_win = {_scad_value(spec.temp)};",
        f"{prefix}temp_icon = {_scad_value(spec.temp_icon)};",
        f"{prefix}temp_c = {_scad_value(spec.temp_c)};",
        f"{prefix}temp_h = {_scad_value(spec.temp_h)};",
        f"{prefix}temp_underline_y = {spec.temp_underline_y!r};",
        f"{prefix}fuel_win = {_scad_value(spec.fuel)};",
        f"{prefix}fuel_icon = {_scad_value(spec.fuel_icon)};",
        f"{prefix}fuel_e = {_scad_value(spec.fuel_e)};",
        f"{prefix}fuel_f = {_scad_value(spec.fuel_f)};",
        f"{prefix}fuel_underline_y = {spec.fuel_underline_y!r};",
        f"{prefix}side_gauges_arched = {_scad_value(spec.side_gauges_arched)};",
        f"{prefix}arc_lamps = {_scad_value([[l.x, l.y, l.size] for l in spec.arc_lamps])};",
        f"{prefix}arc_lamp_r = {spec.arc_lamp_r!r};",
        f"{prefix}strip = {_scad_value(spec.strip)};",
        f"{prefix}strip_lamps = {_scad_value([[l.x, l.y, l.size] for l in spec.strip_lamps])};",
        f"{prefix}panel_left = {_scad_value(spec.panel_left)};",
        f"{prefix}panel_right = {_scad_value(spec.panel_right)};",
        f"{prefix}btn_minus = {_scad_value(spec.btn_minus)};",
        f"{prefix}btn_plus = {_scad_value(spec.btn_plus)};",
        f"{prefix}btn_d = {spec.btn_d!r};",
        f"{prefix}btn_sel = {_scad_value(spec.btn_sel)};",
        f"{prefix}btn_trip = {_scad_value(spec.btn_trip)};",
        f"{prefix}oval_w = {spec.oval_w!r};",
        f"{prefix}oval_h = {spec.oval_h!r};",
        f"{prefix}cancel_icon = {_scad_value(spec.cancel_icon)};",
        f"{prefix}cancel_text = {_scad_value(spec.cancel_text)};",
        f"{prefix}units_label = {_scad_value(spec.units_label)};",
    ]
    return "\n".join(lines) + "\n"


def export_scad(dest: Path, style: str = "ap1") -> Path:
    """Write the lock for the replace-face CAD (``cad/replace_face/face_lock.scad``)."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(spec_to_scad(spec_for(style)), encoding="utf-8")
    return dest


if __name__ == "__main__":
    import sys

    root = Path(__file__).resolve().parents[1]
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else root / "apps" / "harness" / "lib" / "faceSpec.json"
    print(export_json(out))
    if len(sys.argv) <= 1:
        print(export_scad(root / "cad" / "replace_face" / "face_lock.scad"))
