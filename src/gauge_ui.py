#!/usr/bin/env python3
"""S2000 digital cluster — OEM AP1 face simulated on a 1920×1080 panel.

Reads Telemetry JSON lines from stdin (or --serial in Phase 2).

  python mock_telemetry.py | python gauge_ui.py
  python gauge_ui.py --style ap2 --windowed
  python gauge_ui.py --car            # module fills the panel width (in-car)
  python -m mocks.esp32_uart --count 40 --immediate | python gauge_ui.py --smoke
  python gauge_ui.py --smoke --screenshot shots

Esc or Q quits. Space skips the boot intro. 1 / 2 switches AP1 / AP2 faces.

All face geometry comes from ``face_spec.py`` (fractions of the 2.35:1
module measured off the OEM photos). This file turns the spec into pixels,
pre-renders the printed face once, and draws the live LCD elements on top:
bar-graph tach, mitred 7-seg speed / odo, TEMP / FUEL blocks, in-arc turn
and high-beam windows, and the lower telltale strip. Protocol JSON field
names are unchanged.
"""
from __future__ import annotations

import argparse
import math
import os
import select
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from face_spec import (  # noqa: E402
    MODULE_ASPECT,
    RPM_MAX,
    Anchor,
    FaceSpec,
    LampSpot,
    Rect,
    crown_point,
    crown_spring_x,
    h_to_w,
    spec_for,
)
from face_style import DEFAULT_FACE_STYLE, FaceStyle, parse_face_style  # noqa: E402
from lcd_digits import blit_digits, composite_bloom, lcd_window  # noqa: E402
from oem_icons import (  # noqa: E402
    LAMP_AMBER,
    LAMP_BLUE,
    LAMP_GHOST,
    LAMP_GREEN,
    LAMP_RED,
    icon_surface,
)
from protocol import (  # noqa: E402
    BATT_LOW_V,
    ECT_HOT_C,
    FUEL_LOW_PCT,
    RPM_REDLINE,
    SERIAL_BAUD,
    Telemetry,
    try_parse_line,
)

W, H = 1920, 1080

# --- palette (OEM lit photo, refs/oem/lit/) ----------------------------------
CABIN = (4, 4, 5)
COWL = (30, 30, 32)
COWL_EDGE = (62, 62, 64)
FACE_BLACK = (7, 7, 8)
WELL = FACE_BLACK
LCD = (66, 9, 11)              # red-backlit window glass
LCD_EDGE = (36, 9, 9)
LCD_OFF = (22, 6, 7)           # window with the backlight off (boot)
AMBER = (244, 148, 32)         # lit bar-graph segment
AMBER_HOT = (255, 176, 60)
AMBER_DIM = (110, 58, 14)
AMBER_GHOST = (28, 18, 8)
BAND_UNLIT_END = (172, 92, 24)  # unlit amber film — brighter toward the ends
BAND_UNLIT_MID = (108, 56, 14)
BAND_SEG_LINE = (92, 46, 12)
HATCH_AMBER = (208, 118, 30)
HATCH_AMBER_LIT = (255, 180, 44)
HATCH_RED = (156, 32, 24)
HATCH_RED_LIT = (255, 60, 40)
RED = (228, 40, 32)
RED_DIM = (110, 22, 20)
RED_LCD = (255, 66, 40)
RED_LCD_GHOST = (74, 12, 14)
LABEL_LIT = RED_LCD
LABEL_OFF = (60, 15, 15)
SEG_YELLOW = (255, 178, 46)    # TEMP / FUEL blocks
SEG_RED = (238, 44, 34)
GAUGE_WINDOW = (56, 10, 10)
GAUGE_EDGE = (30, 8, 8)
WHITE = (246, 244, 238)
DIM = (118, 112, 100)
MUTED = (52, 50, 46)
ORANGE = (244, 120, 32)
BTN = (150, 150, 148)
BTN_RING = (58, 58, 58)
BTN_HI = (196, 196, 192)
BTN_TEXT = (40, 40, 40)
PANEL = (24, 24, 26)
PANEL_EDGE = (40, 40, 42)
STRIP = (18, 18, 20)
STRIP_HI = (44, 44, 48)
LAMP_TONE = {"red": LAMP_RED, "amber": LAMP_AMBER, "green": LAMP_GREEN, "blue": LAMP_BLUE}

# Module as % of the 1920×1080 canvas (demo framing). ``--car`` fills the width.
MODULE_X_PCT = 0.040
MODULE_W_PCT = 0.920

# Boot (OEM ignition self-test, then a branded READY card):
#   sweep  — bar fills 0→9, all lamps + 188 (the car's bulb check)
#   ready  — Honda H + S2000 badge + READY
#   reveal — settle onto live values
#   live
PHASE_SWEEP_S = 1.35
PHASE_READY_S = 1.75
PHASE_REVEAL_S = 1.55

# Bar-graph resolution lives on ArcSpec; aliases keep older call sites compiling.
TACH_CELL_RPM = 200
TACH_CELL_GAP_DEG = 0.16


@dataclass(frozen=True)
class FaceGeom:
    """Pixel geometry for one face style on one canvas."""

    style: str
    spec: FaceSpec
    module: tuple[int, int, int, int]
    car: bool
    lcd: tuple[int, int, int, int]
    bezel: tuple[int, int, int, int]
    step: int
    spring_y: int
    hood_peak_y: int
    temp: tuple[int, int, int, int]
    fuel: tuple[int, int, int, int]
    speed_win: tuple[int, int, int, int]
    odo_win: tuple[int, int, int, int]
    speed_c: tuple[int, int]
    odo_c: tuple[int, int]
    clock_c: tuple[int, int]
    minus_btn: tuple[int, int, int, int]
    plus_btn: tuple[int, int, int, int]
    rocker: tuple[int, int, int, int]
    lamp_band: tuple[int, int, int, int]
    trip: tuple[int, int, int, int]
    trip_blank: tuple[int, int, int, int]

    # --- spec → pixel helpers -------------------------------------------------
    def px(self, xw: float, yw: float) -> tuple[float, float]:
        """Module-width units (both axes) → canvas pixels."""
        mx, my, mw, _ = self.module
        return mx + xw * mw, my + yw * mw

    def w(self, frac: float) -> float:
        return frac * self.module[2]

    def hh(self, frac: float) -> float:
        return frac * self.module[3]

    def rect_px(self, r: Rect) -> tuple[int, int, int, int]:
        mx, my, mw, mh = self.module
        return (
            int(round(mx + r.x * mw)),
            int(round(my + r.y * mh)),
            int(round(r.w * mw)),
            int(round(r.h * mh)),
        )

    def anchor_px(self, a: Anchor) -> tuple[int, int]:
        mx, my, mw, mh = self.module
        return int(round(mx + a.x * mw)), int(round(my + a.y * mh))

    def arc_px(self, r_w: float, deg: float) -> tuple[float, float]:
        return self.px(*self.spec.tach.point(r_w, deg))

    def crown_px(self, r_w: float, deg: float) -> tuple[float, float]:
        return self.px(*crown_point(self.spec, r_w, deg))


def _pct(v: float) -> int:
    return int(round(v))


def build_face_geom(
    w: int = W,
    h: int = H,
    style: FaceStyle | str = DEFAULT_FACE_STYLE,
    car: bool = False,
) -> FaceGeom:
    """Turn the face spec into canvas pixels.

    ``car`` fills the panel width (no drawn cowl) for the in-dash install;
    the default framing leaves a cowl margin for screenshots and the demo.
    """
    parsed = parse_face_style(style)
    spec = spec_for(parsed.value)
    if car:
        mx, mw = 0, w
    else:
        mx = _pct(w * MODULE_X_PCT)
        mw = _pct(w * MODULE_W_PCT)
    mh = _pct(mw / MODULE_ASPECT)
    my = _pct((h - mh) * (0.5 if car else 0.42))
    module = (mx, my, mw, mh)
    tmp = FaceGeom(  # partial, only for the helpers
        style=parsed.value, spec=spec, module=module, car=car, lcd=(0, 0, 0, 0),
        bezel=(0, 0, 0, 0), step=0, spring_y=0, hood_peak_y=0, temp=(0, 0, 0, 0),
        fuel=(0, 0, 0, 0), speed_win=(0, 0, 0, 0), odo_win=(0, 0, 0, 0), speed_c=(0, 0),
        odo_c=(0, 0), clock_c=(0, 0), minus_btn=(0, 0, 0, 0), plus_btn=(0, 0, 0, 0),
        rocker=(0, 0, 0, 0), lamp_band=(0, 0, 0, 0), trip=(0, 0, 0, 0), trip_blank=(0, 0, 0, 0),
    )
    spring_y = my + _pct(mh * spec.spring_y)
    step = _pct(mw * (0.5 - crown_spring_x(spec, spec.crown_r + spec.crown_lip, spec.spring_y)))
    hood_peak_y = _pct(tmp.crown_px(spec.crown_r + spec.crown_lip, -90.0)[1])
    lip = _pct(mw * spec.crown_lip)
    lcd = (mx + lip, _pct(tmp.crown_px(spec.crown_r, -90.0)[1]), mw - 2 * lip, my + mh - lip - _pct(tmp.crown_px(spec.crown_r, -90.0)[1]))
    bezel = (mx, spring_y, mw, my + mh - spring_y)

    speed_win = tmp.rect_px(spec.speed)
    odo_win = tmp.rect_px(spec.odo)
    speed_c = (_pct(mx + mw * (spec.speed.x + spec.speed.w * 0.5)), _pct(my + mh * spec.speed.cy))
    odo_c = (_pct(mx + mw * spec.odo.cx), _pct(my + mh * spec.odo_cy))
    clock_c = tmp.anchor_px(spec.clock) if spec.clock else odo_c

    d = _pct(mw * spec.btn_d)
    mnx, mny = tmp.anchor_px(spec.btn_minus)
    plx, ply = tmp.anchor_px(spec.btn_plus)
    minus_btn = (mnx - d // 2, mny - d // 2, d, d)
    plus_btn = (plx - d // 2, ply - d // 2, d, d)
    rocker = (minus_btn[0], minus_btn[1], plus_btn[0] + d - minus_btn[0], d)
    ow, oh = _pct(mw * spec.oval_w), _pct(mh * spec.oval_h)
    sx, sy = tmp.anchor_px(spec.btn_sel)
    tx, ty = tmp.anchor_px(spec.btn_trip)
    trip_blank = (sx - ow // 2, sy - oh // 2, ow, oh)
    trip = (tx - ow // 2, ty - oh // 2, ow, oh)

    return FaceGeom(
        style=parsed.value,
        spec=spec,
        module=module,
        car=car,
        lcd=lcd,
        bezel=bezel,
        step=step,
        spring_y=spring_y,
        hood_peak_y=hood_peak_y,
        temp=tmp.rect_px(spec.temp),
        fuel=tmp.rect_px(spec.fuel),
        speed_win=speed_win,
        odo_win=odo_win,
        speed_c=speed_c,
        odo_c=odo_c,
        clock_c=clock_c,
        minus_btn=minus_btn,
        plus_btn=plus_btn,
        rocker=rocker,
        lamp_band=tmp.rect_px(spec.strip),
        trip=trip,
        trip_blank=trip_blank,
    )


FACE = build_face_geom()
_CAR_MODE = False


def apply_face_style(style: FaceStyle | str, car: bool | None = None) -> FaceGeom:
    """Rebuild the active face. Defaults bind at call time, not import time."""
    global FACE, _CAR_MODE
    if car is not None:
        _CAR_MODE = car
    FACE = build_face_geom(style=style, car=_CAR_MODE)
    return FACE


def _geom(g: FaceGeom | None) -> FaceGeom:
    return FACE if g is None else g


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="S2000 digital cluster (AP1 / AP2 face styles)")
    p.add_argument("--windowed", action="store_true", help="1920×1080 window instead of fullscreen")
    p.add_argument(
        "--smoke",
        action="store_true",
        help="Dummy SDL, draw a few frames, optional screenshots, then exit",
    )
    intro = p.add_mutually_exclusive_group()
    intro.add_argument(
        "--intro",
        dest="intro",
        action="store_true",
        help="Play the ID.4-style boot (default when not --smoke)",
    )
    intro.add_argument(
        "--no-intro",
        dest="intro",
        action="store_false",
        help="Skip boot and go straight to live gauges",
    )
    p.set_defaults(intro=None)
    p.add_argument(
        "--screenshot",
        metavar="DIR",
        default=None,
        help="Write PNG frames (sweep/ready/reveal/live/cruise) into DIR",
    )
    p.add_argument(
        "--serial",
        metavar="PORT",
        nargs="?",
        const="/dev/ttyUSB0",
        default=None,
        help="Phase 2: read JSON from UART (default port /dev/ttyUSB0)",
    )
    p.add_argument(
        "--style",
        choices=("ap1", "ap2"),
        default=DEFAULT_FACE_STYLE.value,
        help="Face layout: ap1 (default, measured OEM lock) or ap2 (arched side gauges)",
    )
    p.add_argument(
        "--car",
        action="store_true",
        help="In-car framing: module fills the panel width, no drawn cowl or caption",
    )
    args = p.parse_args(argv)
    if args.intro is None:
        args.intro = not args.smoke
    return args


# --- small maths --------------------------------------------------------------
def clamp(v: float, lo: float, hi: float) -> float:
    return lo if v < lo else hi if v > hi else v


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def lerp_colour(
    a: tuple[int, int, int], b: tuple[int, int, int], t: float
) -> tuple[int, int, int]:
    t = clamp(t, 0.0, 1.0)
    return (
        int(a[0] + (b[0] - a[0]) * t),
        int(a[1] + (b[1] - a[1]) * t),
        int(a[2] + (b[2] - a[2]) * t),
    )


def exp_smooth(current: float, target: float, dt: float, tau: float) -> float:
    """Frame-rate independent approach toward target (tau ≈ seconds to settle)."""
    if tau <= 0 or dt <= 0:
        return target
    k = 1.0 - math.exp(-dt / tau)
    return current + (target - current) * k


def smoothstep(t: float) -> float:
    t = clamp(t, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def ect_frac(ect_c: float) -> float:
    """0 at cold (C), 1 at hot (H). OEM-ish 40–105 °C window."""
    return clamp((ect_c - 40.0) / 65.0, 0.0, 1.0)


def temp_segments_lit(frac: float, segs: int) -> int:
    """Blocks lit for an ``ect_frac``. The OEM cluster idles at 3–4 of 8 blocks
    through the whole normal range, then climbs quickly toward H — so the
    lower ~85 % of the window maps onto the first half of the blocks."""
    f = clamp(frac, 0.0, 1.0)
    knee = 0.85
    half = segs / 2.0
    if f <= knee:
        return int(round(f / knee * half))
    return int(round(half + (f - knee) / (1.0 - knee) * (segs - half)))


def fuel_frac(fuel_pct: float) -> float:
    return clamp(fuel_pct / 100.0, 0.0, 1.0)


# --- tach arc helpers (pixels) -------------------------------------------------
def tach_angle(frac: float, g: FaceGeom | None = None) -> float:
    """Screen angle (degrees) for a 0–1 fraction of the 0–9 000 scale."""
    return _geom(g).spec.tach.angle_for_frac(frac)


def tach_arch_xy(frac: float, g: FaceGeom | None = None) -> tuple[float, float]:
    """Point on the white baseline arc under the band (0 → left, 1 → right)."""
    g = _geom(g)
    return g.arc_px(g.spec.tach.r_line, tach_angle(frac, g))


def tach_arch_normal(frac: float, g: FaceGeom | None = None) -> tuple[float, float]:
    """Unit normal pointing into the well (toward the arc centre)."""
    g = _geom(g)
    return g.spec.tach.normal(tach_angle(frac, g))


def tach_num_xy(frac: float, g: FaceGeom | None = None) -> tuple[float, float]:
    """Tach numeral centre — inside the ticks, on the numeral radius."""
    g = _geom(g)
    return g.arc_px(g.spec.tach.r_num, tach_angle(frac, g))


def arc_poly(
    g: FaceGeom,
    r_outer: float,
    r_inner: float,
    deg0: float,
    deg1: float,
    steps: int | None = None,
) -> list[tuple[int, int]]:
    """Closed annular-sector polygon between two radii (module-width units)."""
    if deg1 < deg0:
        deg0, deg1 = deg1, deg0
    if deg1 - deg0 < 1e-4:
        return []
    n = steps if steps is not None else max(3, int((deg1 - deg0) / 1.2) + 2)
    outer: list[tuple[int, int]] = []
    inner: list[tuple[int, int]] = []
    for i in range(n + 1):
        a = deg0 + (deg1 - deg0) * i / n
        ox, oy = g.arc_px(r_outer, a)
        ix, iy = g.arc_px(r_inner, a)
        outer.append((int(round(ox)), int(round(oy))))
        inner.append((int(round(ix)), int(round(iy))))
    inner.reverse()
    return outer + inner


def tach_band_poly(
    frac0: float,
    frac1: float,
    inner: float = 0.0,
    outer: float | None = None,
    g: FaceGeom | None = None,
    steps: int | None = None,
) -> list[tuple[int, int]]:
    """Band sector between two scale fractions.

    ``inner`` / ``outer`` are pixel offsets inward from the band's outer
    edge (``outer`` defaults to the band thickness).
    """
    g = _geom(g)
    t = g.spec.tach
    mw = g.module[2]
    r_hi = t.r_out - inner / mw
    r_lo = t.r_out - (t.band * mw if outer is None else outer) / mw
    return arc_poly(g, r_hi, r_lo, tach_angle(frac0, g), tach_angle(frac1, g), steps)


def radial_tick_poly(
    g: FaceGeom,
    r_start: float,
    length: float,
    width: float,
    deg: float,
) -> list[tuple[int, int]]:
    """Thin rectangle along the radius from ``r_start`` inward (W units)."""
    a = math.radians(deg)
    nx, ny = -math.cos(a), -math.sin(a)
    tx, ty = -ny, nx
    sx, sy = g.arc_px(r_start, deg)
    hw = width * g.module[2] * 0.5
    ln = length * g.module[2]
    pts = [
        (sx - tx * hw, sy - ty * hw),
        (sx + tx * hw, sy + ty * hw),
        (sx + tx * hw + nx * ln, sy + ty * hw + ny * ln),
        (sx - tx * hw + nx * ln, sy - ty * hw + ny * ln),
    ]
    return [(int(round(x)), int(round(y))) for x, y in pts]


def tach_tick_poly(frac: float, width_px: int, length_px: int, g: FaceGeom | None = None) -> list[tuple[int, int]]:
    """Tick at scale fraction ``frac`` hanging inward from the baseline arc
    (legacy pixel-sized signature)."""
    g = _geom(g)
    mw = g.module[2]
    return radial_tick_poly(g, g.spec.tach.r_line, length_px / mw, width_px / mw, tach_angle(frac, g))


def visor_lip_points(g: FaceGeom | None = None, steps: int = 64) -> list[tuple[int, int]]:
    """Hood inner edge (crown circle) from spring to spring."""
    g = _geom(g)
    s = g.spec
    half = crown_spring_x(s, s.crown_r, s.spring_y)
    a0 = math.degrees(math.atan2(-(h_to_w(s.crown_cy) - h_to_w(s.spring_y)), -half))
    a1 = math.degrees(math.atan2(-(h_to_w(s.crown_cy) - h_to_w(s.spring_y)), half))
    pts: list[tuple[int, int]] = []
    for i in range(steps + 1):
        a = a0 + (a1 - a0) * i / steps
        x, y = g.crown_px(s.crown_r, a)
        pts.append((int(round(x)), int(round(y))))
    return pts


# --- intro clock ----------------------------------------------------------------
def intro_phase_at(t: float) -> tuple[str, float]:
    """Return (phase_name, local 0–1) for the boot clock."""
    if t < 0:
        t = 0.0
    if t < PHASE_SWEEP_S:
        return "sweep", t / PHASE_SWEEP_S
    t -= PHASE_SWEEP_S
    if t < PHASE_READY_S:
        return "ready", t / PHASE_READY_S
    t -= PHASE_READY_S
    if t < PHASE_REVEAL_S:
        return "reveal", t / PHASE_REVEAL_S
    return "live", 1.0


def intro_duration_s() -> float:
    return PHASE_SWEEP_S + PHASE_READY_S + PHASE_REVEAL_S


def boot_strip_mode(phase: str, phase_t: float) -> tuple[dict[str, bool] | None, bool]:
    """OEM ignition lights every telltale. Sweep is that bulb check; reveal
    repeats it briefly, then live lamps take over."""
    if phase == "sweep":
        return None, True
    if phase == "ready":
        return {}, False
    if phase == "reveal" and phase_t < 0.55:
        return None, True
    return None, False


def reveal_rpm(local_t: float, live_rpm: float) -> float:
    """Self-test: 0 → slight redline overshoot, then settle onto live RPM."""
    t = clamp(local_t, 0.0, 1.0)
    peak = float(RPM_REDLINE) * 1.03
    if t < 0.52:
        return peak * smoothstep(t / 0.52)
    if t < 0.62:
        return peak
    return lerp(peak, live_rpm, smoothstep((t - 0.62) / 0.38))


# --- state + sources -----------------------------------------------------------
@dataclass
class DisplayState:
    """Smoothed face values. Lamps snap; bars lerp."""

    rpm: float = 0.0
    speed_kmh: float = 0.0
    fuel_pct: float = 50.0
    ect_c: float = 20.0
    batt_v: float = 12.4
    odo_km: float = 0.0
    trip_km: float = 0.0
    lamps: dict[str, bool] = field(default_factory=dict)
    trip_origin: float | None = None

    def snap(self, telem: Telemetry) -> None:
        self.rpm = float(telem.rpm)
        self.speed_kmh = float(telem.speed_kmh)
        self.fuel_pct = float(telem.fuel_pct)
        self.ect_c = float(telem.ect_c)
        self.batt_v = float(telem.batt_v)
        self.odo_km = float(telem.odo_km)
        self.lamps = dict(telem.lamps)
        if self.trip_origin is None:
            self.trip_origin = self.odo_km
        self.trip_km = max(0.0, self.odo_km - self.trip_origin)

    def follow(self, telem: Telemetry, dt: float) -> None:
        self.rpm = exp_smooth(self.rpm, float(telem.rpm), dt, 0.18)
        self.speed_kmh = exp_smooth(self.speed_kmh, float(telem.speed_kmh), dt, 0.12)
        self.fuel_pct = exp_smooth(self.fuel_pct, float(telem.fuel_pct), dt, 0.32)
        self.ect_c = exp_smooth(self.ect_c, float(telem.ect_c), dt, 0.38)
        self.batt_v = exp_smooth(self.batt_v, float(telem.batt_v), dt, 0.20)
        self.odo_km = float(telem.odo_km)
        self.lamps = dict(telem.lamps)
        if self.trip_origin is None:
            self.trip_origin = self.odo_km
        self.trip_km = max(0.0, self.odo_km - self.trip_origin)


class StdinSource:
    """Non-blocking JSON lines from stdin."""

    def poll(self) -> Telemetry | None:
        latest = None
        try:
            fileno = sys.stdin.fileno()
        except (AttributeError, OSError, ValueError):
            return None
        while True:
            ready, _, _ = select.select([fileno], [], [], 0)
            if not ready:
                break
            line = sys.stdin.readline()
            if not line:
                break
            parsed = try_parse_line(line)
            if parsed is not None:
                latest = parsed
        return latest


class SerialSource:
    """Non-blocking JSON lines from UART or a serial-like mock."""

    def __init__(self, port: str | object) -> None:
        from serial_reader import SerialLineReader, SerialUnavailable, open_serial

        if hasattr(port, "read"):
            ser = port
        else:
            try:
                ser = open_serial(str(port), baud=SERIAL_BAUD, timeout=0)
            except SerialUnavailable as e:
                print(f"serial: {e}", file=sys.stderr)
                raise SystemExit(2) from e
        self._reader = SerialLineReader(ser)

    def poll(self) -> Telemetry | None:
        return self._reader.poll()


# --- fonts ------------------------------------------------------------------------
_FONTS = Path(__file__).resolve().parents[1] / "assets" / "fonts"
_FONT_FILES = {
    "round": "MPLUSRounded1c-Bold.ttf",       # OEM rounded numerals / labels
    "round_x": "MPLUSRounded1c-ExtraBold.ttf",
    "mono": "ShareTechMono-Regular.ttf",
    "ready": "Oxanium-Bold.ttf",
}
_FONT_CACHE: dict[tuple[str, int], object] = {}


def _font(pygame, size: int, bold: bool = False, mono: bool = False, kind: str | None = None):
    if kind is None:
        kind = "mono" if mono else "round_x" if bold else "round"
    key = (kind, int(size))
    cached = _FONT_CACHE.get(key)
    if cached is not None:
        return cached
    bundled = _FONTS / _FONT_FILES.get(kind, _FONT_FILES["round"])
    font = None
    if bundled.is_file():
        try:
            font = pygame.font.Font(str(bundled), int(size))
        except (OSError, pygame.error):
            font = None
    if font is None:
        names = (
            ("DejaVu Sans Mono", "FreeMono", "monospace")
            if kind == "mono"
            else ("DejaVu Sans", "FreeSans", "sans-serif")
        )
        font = pygame.font.SysFont(list(names), int(size), bold=bold)
    _FONT_CACHE[key] = font
    return font


def blit_text(surf, font, text: str, color, pos, anchor: str = "topleft") -> None:
    img = font.render(text, True, color)
    rect = img.get_rect()
    setattr(rect, anchor, pos)
    surf.blit(img, rect)


_BRAND_DIR = Path(__file__).resolve().parents[1] / "assets" / "brand"
_BRAND_CACHE: dict[str, object] = {}
_S2000_BADGE_ASPECT = 2731.535 / 245.88


def _brand_png(pygame, name: str):
    cached = _BRAND_CACHE.get(name)
    if cached is not None:
        return cached
    path = _BRAND_DIR / name
    if not path.is_file():
        raise FileNotFoundError(f"brand mark missing: {path}")
    surf = pygame.image.load(str(path)).convert_alpha()
    _BRAND_CACHE[name] = surf
    return surf


def _blit_brand(pygame, dest, name: str, cx: int, cy: int, max_w: int, max_h: int) -> None:
    src = _brand_png(pygame, name)
    sw, sh = src.get_size()
    scale = min(max_w / sw, max_h / sh)
    img = pygame.transform.smoothscale(src, (max(1, int(sw * scale)), max(1, int(sh * scale))))
    dest.blit(img, img.get_rect(center=(cx, cy)))


def _draw_bezel_brand(pygame, dest, g: FaceGeom) -> None:
    """Honda H + S2000 wordmark on the lower bezel, live and boot."""
    mx, my, mw, mh = g.module
    cx = mx + mw // 2
    cy = my + int(mh * g.spec.cancel_text.y)
    h_size = max(16, int(mw * 0.022))
    badge_h = max(8, int(mw * 0.012))
    badge_w = max(40, int(badge_h * _S2000_BADGE_ASPECT))
    gap = max(4, int(mw * 0.008))
    total = h_size + gap + badge_w
    left = cx - total // 2
    _blit_brand(pygame, dest, "honda-h-mark.png", left + h_size // 2, cy, h_size, h_size)
    _blit_brand(
        pygame,
        dest,
        "s2000-badge.png",
        left + h_size + gap + badge_w // 2,
        cy,
        badge_w,
        badge_h,
    )


def reset_render_caches() -> None:
    """Drop cached fonts / surfaces. Call after ``pygame.quit()`` — SDL_ttf
    handles do not survive a re-init and dereferencing them segfaults."""
    _FONT_CACHE.clear()
    _STATIC_CACHE.clear()
    _ICON_CACHE.clear()
    _BRAND_CACHE.clear()


def build_fonts(pygame) -> dict:
    """Named fonts for the default canvas (face text sizes come from the spec).

    Marks the start of a render session: any font or surface cached under a
    previous ``pygame.init()`` is discarded first.
    """
    reset_render_caches()
    mw = FACE.module[2]
    return {
        "speed": _font(pygame, 132, kind="mono"),
        "ready": _font(pygame, int(mw * 0.05), kind="ready"),
        "tick": _font(pygame, int(mw * FACE.spec.tach.num_size), kind="round"),
        "label": _font(pygame, int(mw * 0.0155), kind="round"),
        "readout": _font(pygame, int(mw * 0.016), kind="round"),
        "tiny": _font(pygame, int(mw * 0.011), kind="round"),
        "unit": _font(pygame, int(mw * 0.020), kind="round_x"),
        "micro": _font(pygame, int(mw * 0.0095), kind="round_x"),
        "lamp": _font(pygame, int(mw * 0.012), kind="round_x"),
    }


# --- sample telemetry ----------------------------------------------------------------
def sample_telem() -> Telemetry:
    return Telemetry(
        rpm=6420,
        speed_kmh=98.0,
        fuel_pct=41.0,
        ect_c=89.0,
        batt_v=14.05,
        odo_km=142_857.3,
        lamps={
            "oil": False,
            "cel": False,
            "abs": False,
            "turn_l": True,
            "turn_r": False,
            "high_beam": True,
            "fog": False,
            "fuel_low": False,
            "batt_warn": False,
            "ect_hot": False,
        },
    )


def cruise_telem() -> Telemetry:
    """Steady 80 km/h / 3000 r/min cruise used for the 05_cruise still."""
    t = sample_telem()
    t.rpm = 3000
    t.speed_kmh = 80.0
    t.fuel_pct = 48.0
    t.lamps = {**t.lamps, "turn_l": False, "high_beam": False, "cruise_main": True}
    return t


def selftest_telem() -> Telemetry:
    """OEM bulb + LCD segment check — 188 / full bars / every telltale."""
    t = sample_telem()
    t.rpm = RPM_REDLINE
    t.speed_kmh = 188.0
    t.fuel_pct = 100.0
    t.ect_c = 105.0
    t.batt_v = 11.8
    t.lamps = {
        "oil": True,
        "cel": True,
        "abs": True,
        "turn_l": True,
        "turn_r": True,
        "high_beam": True,
        "fog": True,
        "fuel_low": True,
        "batt_warn": True,
        "ect_hot": True,
        "brake": True,
        "door": True,
        "srs": True,
        "seatbelt": True,
        "immobilizer": True,
        "maint": True,
        "eps": True,
        "cruise_main": True,
        "cruise_on": True,
    }
    return t


# --- silhouette -----------------------------------------------------------------------
def hood_outer_points(g: FaceGeom | None = None, steps: int = 72) -> list[tuple[int, int]]:
    """Cowl silhouette: flat bottom, straight lower bezel, circular crown."""
    g = _geom(g)
    mx, my, mw, mh = g.module
    s = g.spec
    r = s.crown_r + s.crown_lip
    half = crown_spring_x(s, r, s.spring_y)
    cy_w = h_to_w(s.crown_cy) - h_to_w(s.spring_y)
    a0 = math.degrees(math.atan2(-cy_w, half))
    a1 = math.degrees(math.atan2(-cy_w, -half))
    pts: list[tuple[int, int]] = [(mx, my + mh), (mx + mw, my + mh), (mx + mw, g.spring_y)]
    for i in range(steps + 1):
        a = a0 + (a1 - a0) * i / steps
        x, y = g.crown_px(r, a)
        pts.append((int(round(x)), int(round(y))))
    pts.append((mx, g.spring_y))
    return pts


def lcd_aperture_points(g: FaceGeom | None = None, steps: int = 72) -> list[tuple[int, int]]:
    """Visible face inside the cowl lip (crown arc + straight sides)."""
    g = _geom(g)
    mx, my, mw, mh = g.module
    s = g.spec
    lip = mw * s.crown_lip
    r = s.crown_r
    x_side = lip
    half = 0.5 - x_side / mw
    cy_w = h_to_w(s.crown_cy)
    dy = math.sqrt(max(0.0, r * r - half * half))
    a0 = math.degrees(math.atan2(-dy, half))
    a1 = math.degrees(math.atan2(-dy, -half))
    bottom = my + mh - int(lip * 0.6)
    pts: list[tuple[int, int]] = [(mx + int(x_side), bottom), (mx + mw - int(x_side), bottom)]
    for i in range(steps + 1):
        a = a0 + (a1 - a0) * i / steps
        x, y = g.crown_px(r, a)
        pts.append((int(round(x)), int(round(y))))
    del cy_w
    return pts


def hood_bottom_corners(g: FaceGeom | None = None) -> tuple[tuple[int, int], tuple[int, int]]:
    g = _geom(g)
    mx, my, mw, mh = g.module
    return (mx, my + mh), (mx + mw, my + mh)


# --- printed face (static layer) -----------------------------------------------------
_STATIC_CACHE: dict[tuple, object] = {}


def _static_key(g: FaceGeom) -> tuple:
    return (g.style, g.module, g.car)


def _draw_cowl(pygame, surf, g: FaceGeom) -> None:
    if not g.car:
        outer = hood_outer_points(g)
        pygame.draw.polygon(surf, COWL, outer)
        pygame.draw.polygon(surf, COWL_EDGE, outer, width=2)
    aperture = lcd_aperture_points(g)
    pygame.draw.polygon(surf, FACE_BLACK, aperture)
    if not g.car:
        pygame.draw.polygon(surf, (18, 18, 19), aperture, width=2)


def _draw_band_unlit(pygame, surf, g: FaceGeom) -> None:
    """Printed bar graph: discrete cells with the black well showing in the gaps."""
    t = g.spec.tach
    mid = (t.a0_deg + t.a9_deg) / 2.0
    half = max(1e-6, (t.a9_deg - t.a0_deg) / 2.0)
    for rpm0, _rpm1, d0, d1 in t.iter_scale_cells():
        if rpm0 >= t.redline_rpm:
            col = HATCH_RED
        else:
            u = abs(((d0 + d1) / 2.0 - mid) / half)
            col = lerp_colour(BAND_UNLIT_MID, BAND_UNLIT_END, min(1.0, u) ** 1.6)
        poly = arc_poly(g, t.r_out, t.r_in, d0, d1, steps=2)
        if poly:
            pygame.draw.polygon(surf, col, poly)
    for side, col in (("left", HATCH_AMBER), ("right", HATCH_RED)):
        for d0, d1 in t.hatch_spans(side):
            poly = arc_poly(g, t.r_out, t.r_in - t.hatch_inner_over, d0, d1, steps=1)
            if poly:
                pygame.draw.polygon(surf, col, poly)
    # white baseline arc + ticks
    base = arc_poly(g, t.r_line + t.line_w / 2, t.r_line - t.line_w / 2, t.a0_deg - 0.3, t.a9_deg + 0.3)
    pygame.draw.polygon(surf, WHITE, base)
    for rpm, major in t.tick_rpms():
        w_, ln = t.tick_major if major else t.tick_minor
        poly = radial_tick_poly(g, t.r_line - t.line_w / 2, ln, w_, t.angle_deg(rpm))
        pygame.draw.polygon(surf, WHITE, poly)


def _draw_numerals(pygame, surf, g: FaceGeom, col=WHITE) -> None:
    t = g.spec.tach
    font = _font(pygame, int(g.w(t.num_size)), kind="round")
    for i in range(10):
        x, y = g.arc_px(t.r_num, t.angle_deg(i * 1000))
        img = font.render(str(i), True, col)
        surf.blit(img, img.get_rect(center=(int(round(x)), int(round(y)))))
    zx, zy = g.arc_px(t.r_num, t.angle_deg(0))
    blit_text(
        surf,
        _font(pygame, int(g.w(0.0095)), kind="round"),
        "x1000r/min",
        col,
        (int(zx + g.w(g.spec.rpm_dx)), int(zy + g.w(g.spec.rpm_dy))),
        "center",
    )


def _draw_windows_off(pygame, surf, g: FaceGeom, on: bool) -> None:
    glass = LCD if on else LCD_OFF
    rad = max(4, int(g.w(0.007)))
    lcd_window(pygame, surf, g.speed_win, glass, LCD_EDGE, door=(255, 42, 28, 10 if on else 0), radius=rad)
    lcd_window(pygame, surf, g.odo_win, glass, LCD_EDGE, door=(255, 42, 28, 10 if on else 0), radius=rad)


def _thermometer_icon(pygame, surf, cx: int, cy: int, hgt: int, col) -> None:
    """OEM coolant pictogram: stem + bulb, three ticks right, two waves below."""
    s = hgt / 30.0
    stem_w = max(2, int(3 * s))
    pygame.draw.rect(surf, col, pygame.Rect(cx - stem_w // 2, cy - int(15 * s), stem_w, int(15 * s)), border_radius=stem_w // 2)
    pygame.draw.circle(surf, col, (cx, cy + int(2 * s)), max(3, int(4.5 * s)))
    for dy in (-12, -8, -4):
        y = cy + int(dy * s)
        pygame.draw.line(surf, col, (cx + int(3 * s), y), (cx + int(8 * s), y), max(1, int(2 * s)))
    for base in (9, 14):
        pts = []
        for i in range(0, 19):
            x = cx - int(9 * s) + int(i * s)
            pts.append((x, cy + int(base * s) + int(round(math.sin(i * math.pi / 4.5) * 1.6 * s))))
        pygame.draw.lines(surf, col, False, pts, max(1, int(2 * s)))


def _pump_icon(pygame, surf, cx: int, cy: int, hgt: int, col) -> None:
    """OEM fuel pictogram: pump body with window, hose to the right, base."""
    s = hgt / 30.0
    body = pygame.Rect(cx - int(9 * s), cy - int(14 * s), int(13 * s), int(24 * s))
    pygame.draw.rect(surf, col, body, border_radius=max(1, int(2 * s)))
    pygame.draw.rect(surf, FACE_BLACK, pygame.Rect(body.x + int(2.5 * s), body.y + int(3 * s), int(8 * s), int(6 * s)))
    pygame.draw.rect(surf, col, pygame.Rect(cx - int(11 * s), cy + int(10 * s), int(17 * s), int(3 * s)))
    hose_w = max(1, int(2.2 * s))
    pygame.draw.line(surf, col, (body.right, cy - int(6 * s)), (body.right + int(4 * s), cy - int(6 * s)), hose_w)
    pygame.draw.arc(surf, col, pygame.Rect(body.right + int(1 * s), cy - int(6 * s), int(7 * s), int(12 * s)), -math.pi / 2, math.pi / 2, hose_w)
    pygame.draw.line(surf, col, (body.right + int(7 * s), cy), (body.right + int(7 * s), cy + int(8 * s)), hose_w)
    pygame.draw.rect(surf, col, pygame.Rect(body.right + int(5 * s), cy + int(7 * s), int(4 * s), int(3 * s)))


def _gauge_window(pygame, surf, g: FaceGeom, rect: tuple[int, int, int, int]) -> None:
    lcd_window(pygame, surf, rect, GAUGE_WINDOW, GAUGE_EDGE, door=(0, 0, 0, 0), radius=max(2, int(g.w(0.003))))


def _draw_side_gauge_print(pygame, surf, g: FaceGeom) -> None:
    """TEMP / FUEL windows, letters, icons and underlines (printed parts)."""
    s = g.spec
    letter = _font(pygame, int(g.w(0.020)), kind="round_x")
    if s.side_gauges_arched:
        for rect, icon, left, right, lt, rt in (
            (s.temp, "temp", s.temp_c, s.temp_h, "C", "H"),
            (s.fuel, "fuel", s.fuel_e, s.fuel_f, "E", "F"),
        ):
            _draw_arched_gauge(pygame, surf, g, rect, 0.0, s.temp_segs if icon == "temp" else s.fuel_segs, print_only=True)
            blit_text(surf, letter, lt, WHITE, g.anchor_px(left), "center")
            blit_text(surf, letter, rt, WHITE, g.anchor_px(right), "center")
        tx, ty = g.anchor_px(s.temp_icon)
        _thermometer_icon(pygame, surf, tx, ty, int(g.w(s.temp_icon_h)), WHITE)
        fx, fy = g.anchor_px(s.fuel_icon)
        _pump_icon(pygame, surf, fx, fy, int(g.w(s.fuel_icon_h)), WHITE)
        return
    _gauge_window(pygame, surf, g, g.temp)
    _gauge_window(pygame, surf, g, g.fuel)
    blit_text(surf, letter, "C", WHITE, g.anchor_px(s.temp_c), "center")
    blit_text(surf, letter, "H", WHITE, g.anchor_px(s.temp_h), "center")
    blit_text(surf, letter, "E", WHITE, g.anchor_px(s.fuel_e), "center")
    blit_text(surf, letter, "F", WHITE, g.anchor_px(s.fuel_f), "center")
    tx, ty = g.anchor_px(s.temp_icon)
    _thermometer_icon(pygame, surf, tx, ty, int(g.w(s.temp_icon_h)), WHITE)
    fx, fy = g.anchor_px(s.fuel_icon)
    _pump_icon(pygame, surf, fx, fy, int(g.w(s.fuel_icon_h)), WHITE)
    lw = max(2, int(g.w(0.0022)))
    mx, my, mw, mh = g.module
    tx, _, tw, _ = g.temp
    ty_ = int(my + mh * s.temp_underline_y)
    pygame.draw.line(surf, WHITE, (tx, ty_), (tx + tw, ty_), lw)  # OEM: rule is exactly bar-wide
    fx, _, fw, _ = g.fuel
    fy_ = int(my + mh * s.fuel_underline_y)
    pygame.draw.line(surf, WHITE, (fx, fy_), (fx + fw, fy_), lw)
    half_x = int(mx + mw * (s.fuel.x + s.fuel.w * 0.5))
    pygame.draw.rect(surf, WHITE, pygame.Rect(half_x - lw // 2, fy_ - int(g.w(0.007)), lw, int(g.w(0.007))))


def _round_btn(pygame, surf, rect, label: str, font, label_col=BTN_TEXT) -> None:
    x, y, w, h = rect
    pygame.draw.ellipse(surf, (10, 10, 10), pygame.Rect(x - 2, y - 1, w + 4, h + 5))
    pygame.draw.ellipse(surf, BTN_RING, pygame.Rect(x - 1, y - 1, w + 2, h + 2))
    pygame.draw.ellipse(surf, BTN, pygame.Rect(x, y, w, h))
    pygame.draw.ellipse(surf, BTN_HI, pygame.Rect(x + w // 6, y + h // 10, w - w // 3, max(3, h // 4)))
    blit_text(surf, font, label, label_col, (x + w // 2, y + h // 2), "center")


def _cruise_cancel_icon(pygame, surf, cx: int, cy: int, hgt: int, col) -> None:
    r = max(4, hgt // 2)
    pygame.draw.circle(surf, col, (cx, cy), r, max(1, r // 4))
    pygame.draw.circle(surf, col, (cx, cy), max(1, r // 4))
    pygame.draw.line(surf, col, (cx, cy), (cx + int(r * 0.7), cy - int(r * 0.7)), max(1, r // 4))
    for ang in (2.3, 2.8, 3.3):
        x0 = cx + int(r * 1.05 * math.cos(ang))
        y0 = cy - int(r * 1.05 * math.sin(ang))
        x1 = cx + int(r * 1.5 * math.cos(ang))
        y1 = cy - int(r * 1.5 * math.sin(ang))
        pygame.draw.line(surf, col, (x0, y0), (x1, y1), max(1, r // 4))


def _draw_hardware_print(pygame, surf, g: FaceGeom) -> None:
    """Lower bezel: recessed panels, telltale strip glass, buttons, labels."""
    s = g.spec
    rad = max(4, int(g.w(0.006)))
    for panel in (s.panel_left, s.panel_right):
        if panel is None:
            continue
        r = pygame.Rect(g.rect_px(panel))
        pygame.draw.rect(surf, PANEL, r, border_radius=rad)
        pygame.draw.rect(surf, PANEL_EDGE, r, width=1, border_radius=rad)
    strip = pygame.Rect(g.lamp_band)
    srad = strip.height // 2
    pygame.draw.rect(surf, (10, 10, 11), strip.inflate(6, 6), border_radius=srad + 3)
    pygame.draw.rect(surf, STRIP, strip, border_radius=srad)
    gloss = pygame.Surface(strip.size, pygame.SRCALPHA)
    pygame.draw.rect(gloss, (255, 255, 255, 14), pygame.Rect(0, 0, strip.width, strip.height // 3), border_radius=srad)
    surf.blit(gloss, strip.topleft)
    pygame.draw.rect(surf, STRIP_HI, strip, width=1, border_radius=srad)

    btn_font = _font(pygame, int(g.w(0.020)), kind="round_x")
    _round_btn(pygame, surf, g.minus_btn, "−", btn_font)
    _round_btn(pygame, surf, g.plus_btn, "+", btn_font)
    oval_font = _font(pygame, int(g.w(0.0095)), kind="round_x")
    _round_btn(pygame, surf, g.trip_blank, s.sel_label, oval_font)
    _round_btn(pygame, surf, g.trip, "TRIP", oval_font)

    ix, iy = g.anchor_px(s.cancel_icon)
    _cruise_cancel_icon(pygame, surf, ix, iy, int(g.w(0.012)), WHITE)
    blit_text(surf, _font(pygame, int(g.w(0.0135)), kind="round_x"), "PUSH CANCEL", WHITE, g.anchor_px(s.cancel_text), "midleft")
    blit_text(surf, _font(pygame, int(g.w(0.0105)), kind="round_x"), "mph\u00b7km/h", WHITE, g.anchor_px(s.units_label), "midright")
    _draw_bezel_brand(pygame, surf, g)

    # in-arc round windows (turn / high beam) — dark glass, lit later
    for spot in s.arc_lamps:
        cx, cy = g.anchor_px(Anchor(spot.x, spot.y))
        r = int(g.w(s.arc_lamp_r))
        pygame.draw.circle(surf, (12, 12, 12), (cx, cy), r + 2)
        pygame.draw.circle(surf, (22, 24, 22), (cx, cy), r)
        pygame.draw.circle(surf, (30, 32, 30), (cx, cy), r, 1)


def static_face(pygame, g: FaceGeom | None = None):
    """Cached printed face (everything that never changes frame to frame)."""
    g = _geom(g)
    key = _static_key(g)
    cached = _STATIC_CACHE.get(key)
    if cached is not None:
        return cached
    surf = pygame.Surface((W, H))
    surf.fill(CABIN)
    _draw_cowl(pygame, surf, g)
    _draw_band_unlit(pygame, surf, g)
    _draw_numerals(pygame, surf, g)
    _draw_side_gauge_print(pygame, surf, g)
    _draw_hardware_print(pygame, surf, g)
    _STATIC_CACHE[key] = surf
    return surf


# --- live elements --------------------------------------------------------------------
def _bloom_layer(pygame, surf):
    """Software bloom is off: the cluster is an LCD, so the pixels already emit."""
    del pygame, surf
    return None


def draw_tach_fill(pygame, surf, rpm: float, bloom, g: FaceGeom | None = None) -> None:
    """Light the bar graph from 0 up to ``rpm`` (same cell windows as the print)."""
    g = _geom(g)
    t = g.spec.tach
    step = t.cell_rpm
    rpm = clamp(rpm, 0.0, RPM_MAX * 1.06)
    if rpm < step * 0.5:
        return
    a_lit = t.angle_deg(rpm)
    cells = int(min(rpm, RPM_MAX) // step)
    for i in range(cells + 1):
        r0 = i * step
        r1 = min(rpm, r0 + step)
        if r1 - r0 < 1.0:
            continue
        closed = r1 >= r0 + step
        d0, d1 = t.cell_window(r0, r1, closed=closed)
        if d1 <= d0:
            continue
        col = HATCH_RED_LIT if r0 >= t.redline_rpm else AMBER
        poly = arc_poly(g, t.r_out, t.r_in, d0, d1, steps=2)
        if poly:
            pygame.draw.polygon(surf, col, poly)
    if bloom is not None:
        glow = arc_poly(g, t.r_out + 0.004, t.r_in - 0.004, t.a0_deg, min(a_lit, t.a9_deg))
        if glow:
            pygame.draw.polygon(bloom, (*AMBER_HOT, 30), glow)
    if rpm > RPM_MAX:
        for d0, d1 in t.hatch_spans("right"):
            if (d0 + d1) / 2.0 <= a_lit:
                poly = arc_poly(g, t.r_out, t.r_in - t.hatch_inner_over, d0, d1, steps=1)
                if poly:
                    pygame.draw.polygon(surf, HATCH_RED_LIT, poly)


def draw_tach_segments(pygame, surf, lit_frac: float, ghost: bool = True, g: FaceGeom | None = None) -> None:
    """Compatibility wrapper: printed band comes from the static layer."""
    del ghost
    g = _geom(g)
    bloom = _bloom_layer(pygame, surf)
    draw_tach_fill(pygame, surf, lit_frac * RPM_MAX, bloom, g)
    composite_bloom(pygame, surf, bloom)


def draw_tach_numbers(pygame, fonts, surf, dim: bool = False, g: FaceGeom | None = None) -> None:
    del fonts
    _draw_numerals(pygame, surf, _geom(g), DIM if dim else WHITE)


def draw_welcome_sweep(pygame, surf, sweep_t: float, bloom, g: FaceGeom | None = None) -> None:
    """Car self-test: the bar graph fills 0 → 9 the way a needle would sweep."""
    draw_tach_fill(pygame, surf, RPM_MAX * smoothstep(clamp(sweep_t, 0.0, 1.0)), bloom, g)


def _seg_blocks(
    pygame,
    surf,
    rect: tuple[int, int, int, int],
    segs: int,
    lit: int,
    colours,
    first_scale: float = 1.0,
) -> None:
    """Fill ``lit`` blocks left → right inside a gauge window."""
    x, y, w, h = rect
    pad = max(2, int(h * 0.16))
    gap = max(1, int(w * 0.006))
    inner_w = w - 2 * pad
    units = (segs - 1) + first_scale
    unit_w = (inner_w - gap * (segs - 1)) / units
    cx = x + pad
    for i in range(segs):
        bw = unit_w * (first_scale if i == 0 else 1.0)
        if i < lit:
            pygame.draw.rect(surf, colours(i), pygame.Rect(int(cx), y + pad, max(1, int(bw)), h - 2 * pad))
        cx += bw + gap


def draw_temp_bar(pygame, fonts, surf, frac: float, hot: bool, g: FaceGeom | None = None) -> None:
    """Coolant blocks C → H; the printed window is on the static layer."""
    del fonts
    g = _geom(g)
    s = g.spec
    if s.side_gauges_arched:
        _draw_arched_gauge(pygame, surf, g, s.temp, frac, s.temp_segs, hot_end=hot)
        return
    segs = s.temp_segs
    lit = temp_segments_lit(frac, segs)
    if hot:
        lit = segs

    def colour(i: int):
        return SEG_RED if (hot and i >= segs - 2) else SEG_YELLOW

    _seg_blocks(pygame, surf, g.temp, segs, lit, colour)
    x, y, w, h = g.temp
    pad = max(2, int(h * 0.16))
    mark = pygame.Rect(x + w - pad - max(2, int(g.w(0.0025))), y + pad, max(2, int(g.w(0.0025))), h - 2 * pad)
    pygame.draw.rect(surf, SEG_RED if hot else RED_DIM, mark)


def draw_fuel_bar(pygame, fonts, surf, frac: float, low: bool, g: FaceGeom | None = None) -> None:
    """Fuel blocks E → F; block 0 is the narrow red reserve segment."""
    del fonts
    g = _geom(g)
    s = g.spec
    if s.side_gauges_arched:
        _draw_arched_gauge(pygame, surf, g, s.fuel, frac, s.fuel_segs, warn_low=low)
        return
    segs = s.fuel_segs
    frac = clamp(frac, 0.0, 1.0)
    lit = 1 + int(round(frac * (segs - 1))) if frac > 0.01 else 0

    def colour(i: int):
        return SEG_RED if i == 0 else SEG_YELLOW

    _seg_blocks(pygame, surf, g.fuel, segs, lit, colour, first_scale=0.6)
    del low


def _arched_gauge_geom(g: FaceGeom, rect: Rect) -> tuple[float, float, float]:
    """(cx_px, cy_px, r_px) for an AP2 half-ring drawn inside ``rect``."""
    x, y, w, h = g.rect_px(rect)
    r = min(w / 2.0, h * 0.95)
    return x + w / 2.0, y + h, r


def _draw_arched_gauge(
    pygame,
    surf,
    g: FaceGeom,
    rect: Rect,
    frac: float,
    segs: int,
    warn_low: bool = False,
    hot_end: bool = False,
    print_only: bool = False,
) -> None:
    """AP2 interpretive half-ring: printed dim band, lit blocks clockwise from the left."""
    cx, cy, r = _arched_gauge_geom(g, rect)
    band = r * 0.30

    def sector(a0: float, a1: float, ro: float, ri: float) -> list[tuple[int, int]]:
        n = max(2, int((a1 - a0) / 3) + 1)
        outer = []
        inner = []
        for i in range(n + 1):
            a = math.radians(a0 + (a1 - a0) * i / n)
            outer.append((int(cx + ro * math.cos(a)), int(cy + ro * math.sin(a))))
            inner.append((int(cx + ri * math.cos(a)), int(cy + ri * math.sin(a))))
        inner.reverse()
        return outer + inner

    if print_only:
        pygame.draw.polygon(surf, GAUGE_WINDOW, sector(-180, 0, r, r - band))
        pygame.draw.polygon(surf, GAUGE_EDGE, sector(-180, 0, r, r - band), width=1)
        return
    lit = int(round(clamp(frac, 0.0, 1.0) * segs))
    span = 180.0 / segs
    for i in range(lit):
        a0 = -180 + span * i + 0.8
        a1 = -180 + span * (i + 1) - 0.8
        col = SEG_YELLOW
        if warn_low and i == 0:
            col = SEG_RED
        if hot_end and i >= segs - 2:
            col = SEG_RED
        pygame.draw.polygon(surf, col, sector(a0, a1, r - 2, r - band + 2))


def draw_speed(pygame, fonts, surf, speed: float, bloom=None, g: FaceGeom | None = None) -> None:
    """3-digit mitred 7-seg speed, right-aligned in the red window; km/h lit."""
    g = _geom(g)
    s = g.spec
    value = int(round(clamp(speed, 0.0, 399.0)))
    digits = f"{value:d}".rjust(3)
    mx, my, mw, mh = g.module
    right = int(mx + mw * s.speed_right)
    cy = int(my + mh * s.speed.cy)
    blit_digits(
        pygame,
        surf,
        digits,
        (right, cy),
        digit_h=int(mh * s.speed_digit_h),
        color=RED_LCD,
        ghost=RED_LCD_GHOST,
        ghost_text="888",
        bloom=False,
        italic=0.0,
        align="right",
        bloom_layer=None,
    )
    ux = int(mx + mw * s.unit_x)
    unit_font = fonts.get("label") if fonts else None
    unit_font = unit_font or _font(pygame, int(g.w(0.0155)), kind="round")
    blit_text(surf, unit_font, "mph", LABEL_OFF, (ux, int(my + mh * s.unit_y_top)), "midleft")
    blit_text(surf, unit_font, "km/h", LABEL_LIT, (ux, int(my + mh * s.unit_y_bot)), "midleft")


def _clock_text() -> str:
    from datetime import datetime

    return os.environ.get("DASH_CLOCK") or datetime.now().strftime("%H:%M")


def draw_odo_row(
    pygame,
    fonts,
    surf,
    face: DisplayState,
    batt_warn: bool,
    bloom=None,
    g: FaceGeom | None = None,
) -> None:
    """ODO + TRIP A in the lower red window (AP2 adds the clock)."""
    del fonts
    g = _geom(g)
    s = g.spec
    mx, my, mw, mh = g.module
    odo = int(round(face.odo_km)) % 1_000_000
    trip = clamp(face.trip_km, 0.0, 999.9)
    del bloom
    blit_digits(
        pygame, surf, f"{odo:06d}", (int(mx + mw * s.odo_left), int(my + mh * s.odo_cy)),
        digit_h=int(mh * s.odo_digit_h), color=RED_LCD, ghost=RED_LCD_GHOST, ghost_text="888888",
        italic=0.0, align="left", bloom=False, bloom_layer=None,
    )
    blit_text(surf, _font(pygame, int(g.w(0.011)), kind="round"), "TRIP A", RED_LCD, g.anchor_px(s.trip_label), "center")
    blit_digits(
        pygame, surf, f"{trip:05.1f}", (int(mx + mw * s.trip_right), int(my + mh * s.trip_cy)),
        digit_h=int(mh * s.trip_digit_h), color=RED_LCD, ghost=RED_LCD_GHOST, ghost_text="888.8",
        italic=0.0, align="right", bloom=False, bloom_layer=None,
    )
    if s.clock is not None:
        blit_digits(
            pygame, surf, _clock_text(), g.clock_c,
            digit_h=int(mh * s.trip_digit_h), color=RED_LCD, ghost=RED_LCD_GHOST, ghost_text="88:88",
            italic=0.0, align="left", bloom=False, bloom_layer=None,
        )
    if batt_warn:
        blit_text(
            surf, _font(pygame, int(g.w(0.010)), kind="round"), f"{face.batt_v:.1f}V", RED,
            (g.odo_win[0] + g.odo_win[2] + int(g.w(0.012)), g.odo_win[1] + int(g.w(0.006))), "midleft",
        )


_ICON_CACHE: dict[tuple, object] = {}


def _icon(pygame, kind: str, colour, height: int, max_w: int | None = None):
    key = (kind, colour, height, max_w)
    cached = _ICON_CACHE.get(key)
    if cached is None:
        cached = icon_surface(pygame, kind, colour, height, max_width=max_w)
        _ICON_CACHE[key] = cached
    return cached


def _draw_brake_glyph(pygame, surf, cx: int, cy: int, hgt: int, col) -> None:
    """OEM brake lamp: (!) — circle with exclamation between two brackets."""
    r = max(4, int(hgt * 0.36))
    lw = max(2, int(hgt * 0.10))
    pygame.draw.circle(surf, col, (cx, cy), r, lw)
    pygame.draw.rect(surf, col, pygame.Rect(cx - lw // 2, cy - int(r * 0.6), lw, int(r * 0.75)))
    pygame.draw.circle(surf, col, (cx, cy + int(r * 0.5)), max(1, lw // 2 + 1))
    for sgn in (-1, 1):
        bx = cx + sgn * int(r * 1.55)
        pygame.draw.arc(
            surf, col,
            pygame.Rect(bx - int(r * 0.9), cy - int(r * 1.15), int(r * 1.8), int(r * 2.3)),
            (math.pi * 0.62) if sgn < 0 else (-math.pi * 0.38),
            (math.pi * 1.38) if sgn < 0 else (math.pi * 0.38),
            lw,
        )


def _draw_lamp(pygame, surf, bloom, g: FaceGeom, spot: LampSpot, lit: bool, bulb_check: bool) -> None:
    on = lit or bulb_check
    col = LAMP_TONE.get(spot.tone, LAMP_RED) if on else LAMP_GHOST
    cx, cy = g.anchor_px(Anchor(spot.x, spot.y))
    hgt = max(8, int(g.w(spot.size)))
    if spot.word:
        font = _font(pygame, int(hgt * 0.62), kind="round_x")
        lines = spot.word.split(" ") if spot.word.startswith("MAINT") or spot.word.startswith("CRUISE") else [spot.word]
        total = len(lines) * font.get_height()
        y = cy - total // 2
        for line in lines:
            blit_text(surf, font, line, col, (cx, y + font.get_height() // 2), "center")
            if on and bloom is not None:
                img = font.render(line, True, (*col, 90))
                bloom.blit(pygame.transform.smoothscale(img, (int(img.get_width() * 1.15) + 4, int(img.get_height() * 1.3) + 4)), img.get_rect(center=(cx, y + font.get_height() // 2)).inflate(6, 6).topleft)
            y += font.get_height()
        return
    if spot.icon == "brake":
        _draw_brake_glyph(pygame, surf, cx, cy, hgt, col)
        if on and bloom is not None:
            pygame.draw.circle(bloom, (*col, 70), (cx, cy), int(hgt * 0.8))
        return
    sprite = _icon(pygame, spot.icon, col, hgt, max_w=int(hgt * 1.7))
    surf.blit(sprite, sprite.get_rect(center=(cx, cy)))
    if on and bloom is not None:
        big = pygame.transform.smoothscale(sprite, (int(sprite.get_width() * 1.4) + 4, int(sprite.get_height() * 1.4) + 4))
        big.set_alpha(110)
        bloom.blit(big, big.get_rect(center=(cx, cy)))


def draw_hardware_strip(
    pygame,
    fonts,
    surf,
    face: DisplayState,
    bulb_check: bool = False,
    lamps: dict[str, bool] | None = None,
    g: FaceGeom | None = None,
    bloom=None,
) -> None:
    """Lower bezel + every telltale (strip, side panels and in-arc windows).

    Draws the printed bezel too so it works on a blank canvas (tests); in
    the frame loop the printed parts also live on the static layer.
    """
    del fonts
    g = _geom(g)
    s = g.spec
    _draw_hardware_print(pygame, surf, g)
    flags = face.lamps if lamps is None else lamps
    batt_low = False if lamps is not None else face.batt_v < BATT_LOW_V
    del bloom
    for spot in s.strip_lamps + s.panel_lamps + s.arc_lamps:
        lit = bool(flags.get(spot.key, False))
        if spot.key == "batt_warn" and batt_low:
            lit = True
        _draw_lamp(pygame, surf, None, g, spot, lit, bulb_check)


def draw_ready_card(fonts, surf, face: DisplayState, g: FaceGeom | None = None, pygame=None) -> None:
    """Honda H + S2000 wordmark in the well, READY in the speed window."""
    g = _geom(g)
    mx, my, mw, mh = g.module
    sx, sy, sw, sh = g.speed_win
    cx = mx + mw // 2
    h_size = max(28, int(mw * 0.058))
    _blit_brand(pygame, surf, "honda-h-mark.png", cx, my + int(mh * 0.298), h_size, h_size)
    _blit_brand(
        pygame,
        surf,
        "s2000-badge.png",
        cx,
        my + int(mh * 0.388),
        max(48, int(mw * 0.22)),
        max(10, int(mw * 0.018)),
    )
    blit_text(surf, fonts["ready"], "READY", AMBER_HOT, (cx, sy + int(sh * 0.72)), "center")
    # widths are proportional so the odometer chip gets the room it needs
    chips = [
        ("BATT", f"{face.batt_v:.1f}V", 0.20),
        ("FUEL", f"{face.fuel_pct:.0f}%", 0.18),
        ("TEMP", f"{face.ect_c:.0f}°C", 0.20),
        ("ODO", f"{face.odo_km:,.0f}km", 0.42),
    ]
    row_y = my + int(mh * 0.555)
    for i, (name, val, _share) in enumerate(chips):
        x = mx + int(mw * (0.30 + 0.13 * i))
        blit_text(surf, fonts["micro"], name, DIM, (x, row_y), "center")
        blit_text(surf, fonts["label"], val, AMBER, (x, row_y + int(mh * 0.038)), "center")


def draw_live_face(
    pygame,
    fonts,
    surf,
    face: DisplayState,
    rpm_override: float | None = None,
    bulb_check: bool = False,
    fade: float = 1.0,
    g: FaceGeom | None = None,
) -> None:
    g = _geom(g)
    rpm = face.rpm if rpm_override is None else rpm_override
    layer = surf
    if fade < 0.999:
        layer = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    bloom = None
    _draw_windows_off(pygame, layer, g, on=True)
    draw_tach_fill(pygame, layer, rpm, bloom, g)
    if bulb_check:
        draw_temp_bar(pygame, fonts, layer, 1.0, False, g=g)
        draw_fuel_bar(pygame, fonts, layer, 1.0, False, g=g)
        draw_speed(pygame, fonts, layer, 188.0, bloom=bloom, g=g)
        check = DisplayState()
        check.odo_km = 888888.0
        check.trip_km = 888.8
        check.trip_origin = 0.0
        draw_odo_row(pygame, fonts, layer, check, False, bloom=bloom, g=g)
    else:
        draw_temp_bar(pygame, fonts, layer, ect_frac(face.ect_c), face.ect_c >= ECT_HOT_C, g=g)
        draw_fuel_bar(pygame, fonts, layer, fuel_frac(face.fuel_pct), face.fuel_pct < FUEL_LOW_PCT, g=g)
        draw_speed(pygame, fonts, layer, face.speed_kmh, bloom=bloom, g=g)
        draw_odo_row(
            pygame,
            fonts,
            layer,
            face,
            face.batt_v < BATT_LOW_V or face.lamps.get("batt_warn", False),
            bloom=bloom,
            g=g,
        )
    draw_hardware_strip(pygame, fonts, layer, face, bulb_check=bulb_check, g=g, bloom=bloom)
    composite_bloom(pygame, layer, bloom)
    if fade < 0.999:
        layer.set_alpha(int(255 * clamp(fade, 0.0, 1.0)))
        surf.blit(layer, (0, 0))


def draw_caption(fonts, surf, g: FaceGeom | None = None) -> None:
    g = _geom(g)
    if g.car:
        return
    mx, my, mw, mh = g.module
    label = "AP2" if g.style == FaceStyle.AP2.value else "AP1"
    blit_text(
        surf,
        fonts["micro"],
        f"{label} face  ·  OEM cluster remains powered for legal odometer  ·  Esc quit",
        MUTED,
        (W // 2, my + mh + 28),
        "center",
    )


def draw_frame(
    pygame,
    fonts,
    surf,
    face: DisplayState,
    phase: str,
    phase_t: float,
    g: FaceGeom | None = None,
) -> None:
    g = _geom(g)
    surf.blit(static_face(pygame, g), (0, 0))
    lamps, bulb_check = boot_strip_mode(phase, phase_t)
    if phase == "sweep":
        draw_live_face(
            pygame,
            fonts,
            surf,
            face,
            rpm_override=RPM_MAX * smoothstep(phase_t),
            bulb_check=True,
            g=g,
        )
    elif phase == "ready":
        _draw_windows_off(pygame, surf, g, on=False)
        card = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        draw_ready_card(fonts, card, face, g=g, pygame=pygame)
        card.set_alpha(int(255 * clamp(phase_t * 3.2, 0.0, 1.0)))
        surf.blit(card, (0, 0))
        draw_hardware_strip(pygame, fonts, surf, face, bulb_check=False, lamps=lamps, g=g)
    elif phase == "reveal":
        draw_live_face(
            pygame,
            fonts,
            surf,
            face,
            rpm_override=reveal_rpm(phase_t, face.rpm),
            bulb_check=bulb_check,
            fade=clamp(phase_t * 1.4, 0.0, 1.0),
            g=g,
        )
    else:
        draw_live_face(pygame, fonts, surf, face, g=g)
    draw_caption(fonts, surf, g=g)


# Headless smoke walks the boot clock so CI covers sweep → ready → reveal → live
SMOKE_PHASES: tuple[tuple[str, float], ...] = (
    ("sweep", 0.55),
    ("ready", 0.55),
    ("reveal", 0.40),
    ("live", 1.0),
)

SCREENSHOT_SCENES: tuple[tuple[str, str, float], ...] = (
    ("01_sweep", "sweep", 0.55),
    ("02_ready", "ready", 0.55),
    ("03_reveal", "reveal", 0.40),
    ("04_live", "live", 1.0),
    ("05_cruise", "live", 1.0),
)


def write_screenshots(pygame, fonts, face: DisplayState, dest: Path) -> list[Path]:
    dest.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    canvas = pygame.Surface((W, H))
    cruise = DisplayState()
    cruise.snap(cruise_telem())
    cruise.trip_origin = cruise.odo_km - 128.4
    cruise.trip_km = 128.4
    for name, phase, local_t in SCREENSHOT_SCENES:
        draw_frame(pygame, fonts, canvas, cruise if name.endswith("cruise") else face, phase, local_t)
        path = dest / f"{name}.png"
        pygame.image.save(canvas, str(path))
        written.append(path)
    return written


def init_pygame(windowed: bool, headless: bool):
    import pygame

    pygame.init()
    pygame.display.set_caption("S2000 Digital Dash")
    flags = 0 if (windowed or headless) else pygame.FULLSCREEN
    try:
        screen = pygame.display.set_mode((W, H), flags)
    except pygame.error:
        screen = pygame.display.set_mode((W, H))
    return pygame, screen


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    if args.smoke:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

    try:
        import pygame as _pygame_probe  # noqa: F401
    except ImportError:
        print("pygame is required: uv sync   (or pip install -r requirements.txt)", file=sys.stderr)
        raise SystemExit(1)

    apply_face_style(args.style, car=args.car)
    if args.smoke:
        os.environ.setdefault("DASH_CLOCK", "11:03")
    pygame, screen = init_pygame(args.windowed, headless=args.smoke)
    fonts = build_fonts(pygame)
    clock = pygame.time.Clock()

    if args.serial:
        source: StdinSource | SerialSource = SerialSource(args.serial)
    else:
        source = StdinSource()

    telem = sample_telem() if args.smoke else Telemetry()
    incoming = source.poll()
    if incoming is not None:
        telem = incoming

    face = DisplayState()
    face.snap(telem)
    if args.smoke:
        face.trip_origin = telem.odo_km - 128.4
        face.trip_km = 128.4

    if args.screenshot:
        paths = write_screenshots(pygame, fonts, face, Path(args.screenshot))
        for path in paths:
            print(path)

    if args.smoke:
        for phase, local_t in SMOKE_PHASES:
            draw_frame(pygame, fonts, screen, face, phase, local_t)
            pygame.display.flip()
        pygame.quit()
        reset_render_caches()
        return

    boot_t = 0.0
    running = True
    while running:
        dt = clock.tick(60) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_q):
                    running = False
                if event.key in (pygame.K_SPACE, pygame.K_RETURN):
                    args.intro = False
                if event.key == pygame.K_1:
                    apply_face_style(FaceStyle.AP1)
                    args.intro = True
                    boot_t = 0.0
                if event.key == pygame.K_2:
                    apply_face_style(FaceStyle.AP2)
                    args.intro = True
                    boot_t = 0.0

        incoming = source.poll()
        if incoming is not None:
            telem = incoming

        face.follow(telem, dt)

        if args.intro:
            boot_t += dt
            phase, phase_t = intro_phase_at(boot_t)
            if phase == "live":
                args.intro = False
        else:
            phase, phase_t = "live", 1.0

        draw_frame(pygame, fonts, screen, face, phase, phase_t)
        pygame.display.flip()

    pygame.quit()
    reset_render_caches()


if __name__ == "__main__":
    main()
