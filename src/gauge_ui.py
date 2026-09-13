#!/usr/bin/env python3
"""S2000 digital cluster — red 7-seg LCD in a hooded amber tach cowl.

Reads Telemetry JSON lines from stdin (or --serial in Phase 2).

  python mock_telemetry.py | python gauge_ui.py
  python gauge_ui.py --style ap2 --windowed
  python -m mocks.esp32_uart --count 40 --immediate | python gauge_ui.py --smoke
  python gauge_ui.py --smoke --screenshot shots

Esc or Q quits. Space skips the boot intro. 1 / 2 switches AP1 / AP2 faces.

AP1 proportions are locked in `refs/flat/DIMENSIONS.md`. AP2 is an
interpretive side-gauge layout (see refs/oem/ap2/). Protocol JSON field
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
from face_style import DEFAULT_FACE_STYLE, FaceStyle, parse_face_style
from lcd_digits import blit_digits, lcd_window
from oem_icons import (
    LAMP_GAP,
    LAMP_GHOST,
    blit_glow,
    icon_surface,
    lamp_states,
    lamp_strip_inner_width,
)
from protocol import (
    BATT_LOW_V,
    ECT_HOT_C,
    FUEL_LOW_PCT,
    RPM_REDLINE,
    SERIAL_BAUD,
    Telemetry,
    try_parse_line,
)

W, H = 1920, 1080

# Cabin around the module — flat orthographic, no fake 3D skew
CABIN = (5, 5, 6)
COWL = (16, 14, 13)
COWL_HIGH = (122, 112, 98)
COWL_EDGE = (52, 48, 44)
WELL = (5, 3, 2)
LCD = (5, 1, 1)
AMBER = (244, 148, 32)
AMBER_HOT = (255, 137, 77)         # OEM bloom + READY: orange-amber, not yellow
AMBER_DIM = (110, 58, 14)
AMBER_GHOST = (28, 18, 8)
AMBER_WASH = (80, 42, 10)
AMBER_BAND = (176, 88, 20)
AMBER_BAND_LO = (242, 170, 50)
AMBER_BAND_HI = (176, 60, 18)
RED = (228, 40, 32)
RED_DIM = (86, 18, 16)
RED_GHOST = (44, 14, 12)
RED_LCD = (255, 58, 34)
RED_LCD_GHOST = (42, 10, 8)
WHITE = (246, 240, 228)
DIM = (122, 114, 100)
MUTED = (48, 44, 38)
ORANGE = (244, 120, 32)
TICK_MAJOR_DIM = (248, 242, 228)
TICK_MINOR_DIM = (196, 124, 40)
REDLINE_PRINT = (196, 40, 28)
BEZEL_BTN = (148, 148, 144)
BEZEL_BAND = (10, 11, 12)
BEZEL_BAND_EDGE = (36, 38, 40)
# Printed band depth along the inward normal; ticks stay inside it.
# OEM band fills ~10-12% of module height (~50-60 px on a 752 mh).
TACH_BAND_OUTER = 56.0
# Numerals sit in the dark well, below the printed band (OEM photo).
# Vertical drop varies with `1 − end²` — numerals 0/9 just clear the band
# ends (~3% mh drop), middle numerals drop deep into the well (~25% mh drop).
# Horizontal inset (along inward normal) is a separate constant.
TACH_NUM_X_INSET = 50.0
TACH_NUM_DROP_BASE = 15.0
TACH_NUM_DROP_PEAK = 193.0
TACH_TICK_MAJOR = (2.4, 22.0)
TACH_TICK_MINOR = (1.4, 13.0)
TACH_NEEDLE_TIP = -3.4
TACH_NEEDLE_TAIL = 16.5

# --- locked % layout (see refs/flat/DIMENSIONS.md) ---------------------------
# Module as % of the 1920×1080 canvas; height from OEM 2.35:1 elevation
MODULE_X_PCT = 0.040
MODULE_W_PCT = 0.920
MODULE_ASPECT = 2.35
# Within the module (0,0 = module top-left) — locked from the flat OEM drawing
STEP_W_PCT = 0.044          # rectangular side-notch depth
NOTCH_TOP_PCT = 0.58        # notch y-range (OEM lock)
NOTCH_BOT_PCT = 0.72
ARCH_RISE_PCT = 0.60        # OEM band ends ~56% of mh; rise = (spring - peak) * 0.92
LAMP_Y_PCT = 0.805          # hardware strip centre-line
BEZEL_H_PCT = 0.175
LCD_INSET_X_PCT = 0.010
LCD_TOP_PCT = 0.085         # OEM band peak ~10.4% mh (Car Spy, was 0.055 — too high)
LCD_BOTTOM_PCT = 0.76       # LCD fills to the lamp strip
ARCH_N = 2.0                # parabola (u²)
# AP1: thin horizontal bars flanking the speed/odo (not vertical stacks, not AP2 arches).
# OEM puts the speed/odo LCD cluster *under* the printed band — the band ends at
# ~56% mh and the speed/odo sit at ~68% / ~74%. Earlier values (0.40 / 0.50 /
# 0.505) were an early guess that left the LCD cluster floating mid-arch.
TEMP_X_PCT, TEMP_Y_PCT, TEMP_W_PCT = 0.080, 0.680, 0.160
FUEL_X_PCT, FUEL_Y_PCT, FUEL_W_PCT = 0.760, 0.680, 0.160
BAR_H_PCT = 0.018           # OEM AP1 ticks are thin horizontal dashes
SPEED_X_PCT, SPEED_Y_PCT = 0.50, 0.680
ODO_Y_PCT = 0.74            # directly under the speed, just above the lamp strip
# AP2 interpretive side-gauges (not a measured plate)
AP2_SPEED_X_PCT = 0.36
AP2_ODO_Y_PCT = 0.52
AP2_TEMP_X_PCT = 0.68
AP2_TEMP_Y_PCT = 0.26
AP2_FUEL_Y_PCT = 0.46
AP2_SIDE_W_PCT = 0.27
AP2_SIDE_H_PCT = 0.17
AP2_TEMP_SEGS = 12
AP2_FUEL_SEGS = 14

# OEM AP1: 6 coolant bars, a finer fuel ladder (photos ~10–16 visible)
TEMP_SEGS = 6
FUEL_SEGS = 16
REDLINE_BLOCKS = 5
TACH_MAJORS = 10  # 0..9
TACH_MINORS_PER = 4  # 200 r/min ticks between majors (OEM)

# ID.4-inspired boot: sweep → READY summary → gauge reveal → live
PHASE_SWEEP_S = 1.35
PHASE_READY_S = 1.75
PHASE_REVEAL_S = 1.55


@dataclass(frozen=True)
class FaceGeom:
    """Pixel geometry derived from the locked OEM percentages."""

    style: str
    module: tuple[int, int, int, int]
    lcd: tuple[int, int, int, int]
    bezel: tuple[int, int, int, int]
    step: int
    spring_y: int
    hood_peak_y: int
    lcd_peak_y: int
    lcd_spring_y: int
    notch_top_y: int
    notch_bot_y: int
    temp: tuple[int, int, int, int]
    fuel: tuple[int, int, int, int]
    speed_c: tuple[int, int]
    odo_c: tuple[int, int]
    clock_c: tuple[int, int]
    arch_n: float
    rocker: tuple[int, int, int, int]
    minus_btn: tuple[int, int, int, int]
    plus_btn: tuple[int, int, int, int]
    lamp_band: tuple[int, int, int, int]
    trip: tuple[int, int, int, int]
    trip_blank: tuple[int, int, int, int]


def _pct(v: float) -> int:
    return int(round(v))


def build_face_geom(
    w: int = W,
    h: int = H,
    style: FaceStyle | str = DEFAULT_FACE_STYLE,
) -> FaceGeom:
    """Build a face. AP1 percentages match refs/flat/DIMENSIONS.md."""
    parsed = parse_face_style(style)
    ap2 = parsed is FaceStyle.AP2
    mx = _pct(w * MODULE_X_PCT)
    mw = _pct(w * MODULE_W_PCT)
    mh = _pct(mw / MODULE_ASPECT)
    my = _pct((h - mh) * 0.42)  # sit slightly high so the caption clears
    step = _pct(mw * STEP_W_PCT)
    bezel_h = _pct(mh * BEZEL_H_PCT)
    bezel_y = my + _pct(mh * LAMP_Y_PCT)
    notch_top_y = my + _pct(mh * NOTCH_TOP_PCT)
    notch_bot_y = my + _pct(mh * NOTCH_BOT_PCT)
    inset = _pct(mw * LCD_INSET_X_PCT)
    lcd_x = mx + step + inset
    lcd_w = mw - 2 * step - 2 * inset
    lcd_bottom = my + _pct(mh * LCD_BOTTOM_PCT)
    lcd_peak = my + _pct(mh * LCD_TOP_PCT)
    spring = my + _pct(mh * ARCH_RISE_PCT)
    lcd_y = lcd_peak
    lcd_h = lcd_bottom - lcd_peak
    lcd_spring = spring - _pct(mh * 0.02)

    bar_h = max(6, _pct(mh * BAR_H_PCT))
    if ap2:
        temp = (
            mx + _pct(mw * AP2_TEMP_X_PCT),
            my + _pct(mh * AP2_TEMP_Y_PCT),
            _pct(mw * AP2_SIDE_W_PCT),
            max(bar_h, _pct(mh * AP2_SIDE_H_PCT)),
        )
        fuel = (
            mx + _pct(mw * AP2_TEMP_X_PCT),
            my + _pct(mh * AP2_FUEL_Y_PCT),
            _pct(mw * AP2_SIDE_W_PCT),
            max(bar_h, _pct(mh * AP2_SIDE_H_PCT)),
        )
        speed_x_pct = AP2_SPEED_X_PCT
        odo_y_pct = AP2_ODO_Y_PCT
    else:
        temp = (
            mx + _pct(mw * TEMP_X_PCT),
            my + _pct(mh * TEMP_Y_PCT),
            _pct(mw * TEMP_W_PCT),
            bar_h,
        )
        fuel = (
            mx + _pct(mw * FUEL_X_PCT),
            my + _pct(mh * FUEL_Y_PCT),
            _pct(mw * FUEL_W_PCT),
            bar_h,
        )
        speed_x_pct = SPEED_X_PCT
        odo_y_pct = ODO_Y_PCT

    cx = mx + _pct(mw * speed_x_pct)

    pad = _pct(mw * 0.018)
    btn_d = max(28, _pct(bezel_h * 0.42))
    btn_y = bezel_y + (bezel_h - btn_d) // 2
    btn_gap = 12
    minus_btn = (mx + pad, btn_y, btn_d, btn_d)
    plus_btn = (mx + pad + btn_d + btn_gap, btn_y, btn_d, btn_d)
    rocker = (minus_btn[0], btn_y, plus_btn[0] + btn_d - minus_btn[0], btn_d)
    trip_w = _pct(mw * 0.062)
    trip = (mx + mw - pad - trip_w, btn_y, trip_w, btn_d)
    trip_blank = (trip[0] - trip_w - 14, btn_y, trip_w, btn_d)
    band_h = _pct(bezel_h * 0.58)
    band_y = bezel_y + (bezel_h - band_h) // 2
    pack_w = lamp_strip_inner_width() + 28
    gap_l = rocker[0] + rocker[2] + _pct(mw * 0.08)
    gap_r = trip_blank[0] - 16
    mid = (gap_l + gap_r) // 2
    lamp_band = (mid - pack_w // 2, band_y, pack_w, band_h)
    speed_y = my + _pct(mh * SPEED_Y_PCT)
    odo_c = (cx, speed_y + 72 if ap2 else my + _pct(mh * odo_y_pct))
    clock_c = (cx, speed_y + 36 if ap2 else odo_c[1])

    return FaceGeom(
        style=parsed.value,
        module=(mx, my, mw, mh),
        lcd=(lcd_x, lcd_y, lcd_w, lcd_h),
        bezel=(mx, bezel_y, mw, bezel_h),
        step=step,
        spring_y=spring,
        hood_peak_y=my,
        lcd_peak_y=lcd_peak,
        lcd_spring_y=lcd_spring,
        notch_top_y=notch_top_y,
        notch_bot_y=notch_bot_y,
        temp=temp,
        fuel=fuel,
        speed_c=(cx, speed_y),
        odo_c=odo_c,
        clock_c=clock_c,
        arch_n=ARCH_N,
        rocker=rocker,
        minus_btn=minus_btn,
        plus_btn=plus_btn,
        lamp_band=lamp_band,
        trip=trip,
        trip_blank=trip_blank,
    )


FACE = build_face_geom()


def apply_face_style(style: FaceStyle | str) -> FaceGeom:
    """Rebuild the active face. Defaults bind at call time, not import time."""
    global FACE
    FACE = build_face_geom(style=style)
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
        help="Face layout: ap1 (horizontal TEMP/FUEL flanking the speedo, default) or ap2 (arched side gauges)",
    )
    args = p.parse_args(argv)
    if args.intro is None:
        args.intro = not args.smoke
    return args


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


TACH_ARCH_DROP = 14.0
VISOR_LIP_OFFSET = -2.8
VISOR_LIP_PAD = 24.0


def tach_arch_xy(frac: float, g: FaceGeom | None = None) -> tuple[float, float]:
    """Place a tach tick on the OEM parabola (not a circular wedge).

    frac 0 → 0×1000 at the lower left; frac 1 → 9×1000 at the lower right.
    """
    g = _geom(g)
    lx, _, lw, _ = g.lcd
    inset = lw * 0.055
    x0 = lx + inset
    x1 = lx + lw - inset
    x = x0 + (x1 - x0) * clamp(frac, 0.0, 1.0)
    u = 2.0 * clamp(frac, 0.0, 1.0) - 1.0
    rise = (g.lcd_spring_y - g.lcd_peak_y) * 0.92
    y = g.lcd_peak_y + TACH_ARCH_DROP + rise * (u * u)
    return x, y


def visor_lip_points(
    g: FaceGeom | None = None,
    offset: float = VISOR_LIP_OFFSET,
    pad: float = VISOR_LIP_PAD,
    steps: int = 48,
) -> list[tuple[int, int]]:
    """Inner visor lip — same parabola as the printed tach, just above it."""
    g = _geom(g)
    lx, _, lw, _ = g.lcd
    inset = lw * 0.055
    x0t = lx + inset
    x1t = lx + lw - inset
    span = x1t - x0t
    x0 = x0t - pad
    x1 = x1t + pad
    rise = (g.lcd_spring_y - g.lcd_peak_y) * 0.92
    pts: list[tuple[int, int]] = []
    for i in range(steps + 1):
        t = i / steps
        x = x0 + (x1 - x0) * t
        tu = (x - x0t) / span
        u = 2.0 * tu - 1.0
        y = g.lcd_peak_y + TACH_ARCH_DROP + rise * (u * u)
        dx, dy = span, 4.0 * rise * u
        n = math.hypot(dx, dy) or 1.0
        nx, ny = dy / n, -dx / n
        if ny < 0:
            nx, ny = -nx, -ny
        pts.append((int(round(x + nx * offset)), int(round(y + ny * offset))))
    return pts


def tach_arch_tangent(frac: float, g: FaceGeom | None = None) -> tuple[float, float]:
    """Unit tangent along the parabola, left → right."""
    g = _geom(g)
    lx, _, lw, _ = g.lcd
    inset = lw * 0.055
    span_x = (lx + lw - inset) - (lx + inset)
    rise = (g.lcd_spring_y - g.lcd_peak_y) * 0.92
    u = 2.0 * clamp(frac, 0.0, 1.0) - 1.0
    dx, dy = span_x, 4.0 * rise * u
    n = math.hypot(dx, dy) or 1.0
    return dx / n, dy / n


def tach_arch_normal(frac: float, g: FaceGeom | None = None) -> tuple[float, float]:
    """Unit normal pointing into the LCD (generally downward)."""
    tx, ty = tach_arch_tangent(frac, g)
    nx, ny = ty, -tx
    if ny < 0:
        nx, ny = -nx, -ny
    return nx, ny


def tach_num_xy(frac: float, g: FaceGeom | None = None) -> tuple[float, float]:
    """Tach numeral centre — inside the well, not on the printed band.

    OEM Car Spy photo: numerals 0/9 sit just under the band ends
    (~3% drop), middle numerals sit deep in the well (~25% drop). The
    parabola's vertical drop therefore varies with `1 − end²` rather
    than with the constant normal inset the previous formula used.
    Horizontal inset is a separate constant (along the inward normal)
    so numerals sit slightly inside the band's x range at the corners.
    """
    x, y = tach_arch_xy(frac, g)
    nx, _ny = tach_arch_normal(frac, g)
    end = abs(2.0 * clamp(frac, 0.0, 1.0) - 1.0)
    drop_v = TACH_NUM_DROP_BASE + TACH_NUM_DROP_PEAK * (1.0 - end * end)
    return x + nx * TACH_NUM_X_INSET, y + drop_v


def tach_tick_poly(
    frac: float,
    width: float,
    length: float,
    g: FaceGeom | None = None,
    inset: float = 2.0,
) -> list[tuple[int, int]]:
    """Thin rectangle whose long axis is the arch normal (OEM slant)."""
    x, y = tach_arch_xy(frac, g)
    nx, ny = tach_arch_normal(frac, g)
    tx, ty = -ny, nx
    hw = width * 0.5
    x0 = x + nx * inset
    y0 = y + ny * inset
    return [
        (int(round(x0 - tx * hw)), int(round(y0 - ty * hw))),
        (int(round(x0 + tx * hw)), int(round(y0 + ty * hw))),
        (int(round(x0 + tx * hw + nx * length)), int(round(y0 + ty * hw + ny * length))),
        (int(round(x0 - tx * hw + nx * length)), int(round(y0 - ty * hw + ny * length))),
    ]


def tach_band_poly(
    frac0: float,
    frac1: float,
    inner: float,
    outer: float,
    g: FaceGeom | None = None,
    steps: int = 48,
) -> list[tuple[int, int]]:
    """Closed polygon for a printed tach band along the parabola."""
    g = _geom(g)
    t0 = clamp(frac0, 0.0, 1.0)
    t1 = clamp(frac1, 0.0, 1.0)
    if t1 <= t0 + 1e-4:
        return []
    n = max(8, int(round(steps * (t1 - t0))))
    outer_pts: list[tuple[int, int]] = []
    inner_pts: list[tuple[int, int]] = []
    for i in range(n + 1):
        f = t0 + (t1 - t0) * (i / n)
        x, y = tach_arch_xy(f, g)
        nx, ny = tach_arch_normal(f, g)
        outer_pts.append((int(round(x + nx * inner)), int(round(y + ny * inner))))
        inner_pts.append((int(round(x + nx * outer)), int(round(y + ny * outer))))
    inner_pts.reverse()
    return outer_pts + inner_pts


def smoothstep(t: float) -> float:
    t = clamp(t, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def ect_frac(ect_c: float) -> float:
    """0 at cold (C), 1 at hot (H). OEM-ish 40–105 °C window."""
    return clamp((ect_c - 40.0) / 65.0, 0.0, 1.0)


def fuel_frac(fuel_pct: float) -> float:
    return clamp(fuel_pct / 100.0, 0.0, 1.0)


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
    """Hide drive lamps until reveal; bulb-check only in the first half of reveal."""
    if phase in ("sweep", "ready"):
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


@dataclass
class DisplayState:
    """Smoothed face values. Lamps snap; needles lerp."""

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


_FONTS = Path(__file__).resolve().parents[1] / "assets" / "fonts"


def _font(
    pygame,
    size: int,
    bold: bool = False,
    mono: bool = False,
    italic: bool = False,
):
    bundled = None
    if mono:
        bundled = _FONTS / "ShareTechMono-Regular.ttf"
    elif italic:
        bundled = _FONTS / "BarlowCondensed-SemiBoldItalic.ttf"
    else:
        bundled = _FONTS / "BarlowCondensed-Bold.ttf"
    if bundled is not None and bundled.is_file():
        try:
            return pygame.font.Font(str(bundled), size)
        except (OSError, pygame.error):
            pass
    names = (
        ("DejaVu Sans Mono", "FreeMono", "monospace")
        if mono
        else ("DejaVu Sans", "FreeSans", "sans-serif")
    )
    return pygame.font.SysFont(list(names), size, bold=bold)


def blit_text(surf, font, text: str, color, pos, anchor: str = "topleft") -> None:
    img = font.render(text, True, color)
    rect = img.get_rect()
    setattr(rect, anchor, pos)
    surf.blit(img, rect)


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
    t.lamps = {**t.lamps, "turn_l": False, "high_beam": False}
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
    }
    return t


def arch_points(
    x0: float,
    x1: float,
    y_peak: float,
    y_spring: float,
    n: float = ARCH_N,
    steps: int = 56,
) -> list[tuple[int, int]]:
    """OEM lock: y = y_peak + rise * u²  (n is kept for call-site compatibility)."""
    del n
    rise = y_spring - y_peak
    pts: list[tuple[int, int]] = []
    for i in range(steps + 1):
        t = i / steps
        u = 2.0 * t - 1.0
        x = x0 + (x1 - x0) * t
        y = y_peak + rise * u * u
        pts.append((int(round(x)), int(round(y))))
    return pts


def hood_outer_points(g: FaceGeom | None = None) -> list[tuple[int, int]]:
    """Flat bottom, rectangular side notches (58–72%), parabolic crown (28% rise)."""
    g = _geom(g)
    mx, my, mw, mh = g.module
    step = g.step
    lx = mx + step
    rx = mx + mw - step
    pts: list[tuple[int, int]] = [
        (mx, my + mh),
        (mx + mw, my + mh),
        (mx + mw, g.notch_bot_y),
        (rx, g.notch_bot_y),
        (rx, g.notch_top_y),
        (rx, g.spring_y),
    ]
    pts.extend(arch_points(rx, lx, g.hood_peak_y, g.spring_y, n=g.arch_n))
    pts.extend(
        [
            (lx, g.spring_y),
            (lx, g.notch_top_y),
            (lx, g.notch_bot_y),
            (mx, g.notch_bot_y),
        ]
    )
    return pts


def lcd_aperture_points(g: FaceGeom | None = None) -> list[tuple[int, int]]:
    g = _geom(g)
    lx, ly, lw, lh = g.lcd
    rx = lx + lw
    bot = ly + lh
    pts: list[tuple[int, int]] = [(lx, bot), (rx, bot), (rx, g.lcd_spring_y)]
    pts.extend(arch_points(rx, lx, g.lcd_peak_y, g.lcd_spring_y, n=g.arch_n))
    pts.append((lx, g.lcd_spring_y))
    return pts


def hood_bottom_corners(g: FaceGeom | None = None) -> tuple[tuple[int, int], tuple[int, int]]:
    g = _geom(g)
    mx, my, mw, mh = g.module
    return (mx, my + mh), (mx + mw, my + mh)


def draw_cabin(pygame, surf) -> None:
    surf.fill(CABIN)


def draw_cowl(pygame, surf, sweep_t: float | None = None, g: FaceGeom | None = None) -> None:
    g = _geom(g)
    outer = hood_outer_points(g)
    pygame.draw.polygon(surf, COWL, outer)
    pygame.draw.polygon(surf, COWL_EDGE, outer, width=2)

    aperture = lcd_aperture_points(g)
    pygame.draw.polygon(surf, WELL, aperture)
    pygame.draw.polygon(surf, LCD, aperture)
    # Quiet night wash — OEM well is charcoal, not a brown overlay
    wash = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    pygame.draw.polygon(wash, (36, 18, 6, 20), aperture)
    surf.blit(wash, (0, 0))
    inner = visor_lip_points(g)
    if len(inner) > 1:
        pygame.draw.lines(surf, (239, 230, 214), False, inner, 2)
    pygame.draw.polygon(surf, (22, 18, 14), aperture, width=2)

    if sweep_t is not None:
        band = arch_points(
            g.module[0] + g.step + 20,
            g.module[0] + g.module[2] - g.step - 20,
            g.hood_peak_y + 10,
            g.spring_y - 2,
            n=g.arch_n,
            steps=48,
        )
        t = smoothstep(clamp(sweep_t, 0.0, 1.0))
        i = int(t * max(0, len(band) - 10))
        chunk = band[i : i + 10]
        if len(chunk) > 1:
            pygame.draw.lines(surf, lerp_colour(COWL_HIGH, AMBER, 0.45 * t), False, chunk, 2)


def _expand_poly(pts: list[tuple[int, int]], px: float) -> list[tuple[int, int]]:
    cx = sum(p[0] for p in pts) / len(pts)
    cy = sum(p[1] for p in pts) / len(pts)
    out: list[tuple[int, int]] = []
    for x, y in pts:
        dx, dy = x - cx, y - cy
        n = math.hypot(dx, dy) or 1.0
        out.append((int(x + dx / n * px), int(y + dy / n * px)))
    return out


def _blit_seg_bloom(pygame, surf, bloom, pts, color) -> None:
    glow = (
        min(255, color[0] + 28),
        min(255, color[1] + 20),
        min(255, color[2] + 8),
        78,
    )
    pygame.draw.polygon(bloom, glow, _expand_poly(pts, 5))
    pygame.draw.polygon(surf, color, pts)


def draw_tach_segments(
    pygame,
    surf,
    lit_frac: float,
    ghost: bool = True,
    g: FaceGeom | None = None,
) -> None:
    """Printed OEM amber/red scale, ticks always on, cream needle at lit_frac."""
    g = _geom(g)
    red_from = 8.0 / 9.0
    bloom = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    n_minor = 9 * TACH_MINORS_PER  # 36 × 200 r/min steps across 0–9
    del ghost

    slices = 48
    for i in range(slices):
        t0 = red_from * (i / slices)
        t1 = red_from * ((i + 1) / slices)
        slab = tach_band_poly(t0, t1, 0.4, TACH_BAND_OUTER, g, steps=8)
        if slab:
            col = lerp_colour(AMBER_BAND_LO, AMBER_BAND_HI, i / max(1, slices - 1))
            pygame.draw.polygon(surf, col, slab)
    red_band = tach_band_poly(red_from, 1.0, 0.4, TACH_BAND_OUTER + 2.0, g)
    if red_band:
        pygame.draw.polygon(surf, (148, 32, 24), red_band)
        pygame.draw.polygon(bloom, (*RED, 56), red_band)

    wash_to = clamp(lit_frac, 0.0, 1.0)
    if wash_to > 0.012:
        lit = tach_band_poly(0.0, min(wash_to, red_from), 0.4, TACH_BAND_OUTER, g)
        if lit:
            pygame.draw.polygon(bloom, (*AMBER_HOT, 56), lit)
        if wash_to > red_from:
            lit_red = tach_band_poly(red_from, wash_to, 0.4, TACH_BAND_OUTER + 2.0, g)
            if lit_red:
                pygame.draw.polygon(bloom, (255, 56, 36, 72), lit_red)

    for i in range(n_minor + 1):
        frac = i / n_minor
        major = i % TACH_MINORS_PER == 0
        if frac >= red_from - 1e-6:
            continue
        w, length = TACH_TICK_MAJOR if major else TACH_TICK_MINOR
        pts = tach_tick_poly(frac, w, length, g, inset=2.0)
        reached = frac <= lit_frac + 1e-6
        col = WHITE if major else lerp_colour(AMBER, AMBER_HOT, frac)
        if reached:
            _blit_seg_bloom(pygame, surf, bloom, pts, col)
        else:
            pygame.draw.polygon(surf, col if major else TICK_MINOR_DIM, pts)

    for i in range(REDLINE_BLOCKS):
        t0 = red_from + (1.0 - red_from) * (i / REDLINE_BLOCKS)
        t1 = red_from + (1.0 - red_from) * ((i + 1) / REDLINE_BLOCKS)
        mid = (t0 + t1) * 0.5
        reached = mid <= lit_frac + 1e-6
        pts = tach_tick_poly(mid, 7.2, TACH_BAND_OUTER - 2.0, g, inset=1.0)
        if reached:
            _blit_seg_bloom(pygame, surf, bloom, pts, RED)
        else:
            pygame.draw.polygon(surf, REDLINE_PRINT, pts)

    small = pygame.transform.smoothscale(bloom, (surf.get_width() // 3, surf.get_height() // 3))
    surf.blit(pygame.transform.smoothscale(small, surf.get_size()), (0, 0))

    if lit_frac > 0.002:
        _draw_tach_pointer(pygame, surf, clamp(lit_frac, 0.0, 1.0), g)


def _draw_tach_pointer(pygame, surf, frac: float, g: FaceGeom) -> None:
    """OEM cream chevron on the printed band — short, no well hub."""
    red_from = 8.0 / 9.0
    tx, ty = tach_arch_xy(frac, g)
    nx, ny = tach_arch_normal(frac, g)
    px, py = -ny, nx
    tip = (tx + nx * TACH_NEEDLE_TIP, ty + ny * TACH_NEEDLE_TIP)
    base = (tx + nx * TACH_NEEDLE_TAIL, ty + ny * TACH_NEEDLE_TAIL)
    col = WHITE if frac < red_from else RED
    glow = AMBER_HOT if frac < red_from else RED

    def chevron(half: float) -> list[tuple[int, int]]:
        return [
            (int(tip[0]), int(tip[1])),
            (int(base[0] + px * half), int(base[1] + py * half)),
            (int(base[0] - px * half), int(base[1] - py * half)),
        ]

    pygame.draw.polygon(surf, (28, 20, 12), chevron(5.4))
    pygame.draw.polygon(surf, glow, chevron(4.2))
    pygame.draw.polygon(surf, col, chevron(2.8))


def draw_welcome_sweep(pygame, surf, sweep_t: float, g: FaceGeom | None = None) -> None:
    """ID.4-style comet along the printed tach arch."""
    g = _geom(g)
    t = smoothstep(clamp(sweep_t, 0.0, 1.0))
    bloom = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    trail = tach_band_poly(max(0.0, t - 0.11), max(t, 0.012), 0.4, TACH_BAND_OUTER, g, steps=28)
    if trail:
        pygame.draw.polygon(bloom, (255, 208, 96, 78), trail)
    n = 36
    for i in range(n + 1):
        frac = i / n
        dist = t - frac
        if dist < 0 or dist > 0.09:
            continue
        strength = 1.0 - dist / 0.09
        col = lerp_colour(AMBER, WHITE, strength)
        w, length = TACH_TICK_MAJOR if i % TACH_MINORS_PER == 0 else TACH_TICK_MINOR
        pts = tach_tick_poly(frac, w, length, g, inset=2.0)
        pygame.draw.polygon(bloom, (*col, int(24 + 90 * strength)), _expand_poly(pts, 1.5))
        pygame.draw.polygon(surf, col, pts)
    x, y = tach_arch_xy(t, g)
    pygame.draw.circle(bloom, (255, 224, 150, 80), (int(x), int(y)), 7)
    pygame.draw.circle(surf, (255, 232, 170), (int(x), int(y)), 3)
    pygame.draw.circle(surf, WHITE, (int(x), int(y)), 1)
    small = pygame.transform.smoothscale(bloom, (surf.get_width() // 3, surf.get_height() // 3))
    surf.blit(pygame.transform.smoothscale(small, surf.get_size()), (0, 0))
    _draw_tach_pointer(pygame, surf, t, g)


def draw_tach_numbers(pygame, fonts, surf, dim: bool = False, g: FaceGeom | None = None) -> None:
    """Numerals sit in the dark well, just inside the printed amber band."""
    g = _geom(g)
    for i in range(10):
        col = WHITE if not dim else DIM
        frac = i / 9.0
        x, y = tach_num_xy(frac, g)
        img = fonts["tick"].render(str(i), True, col)
        surf.blit(img, img.get_rect(center=(int(x), int(y))))
    zx, zy = tach_num_xy(0.0, g)
    blit_text(
        surf,
        fonts["micro"],
        "x1000 r/min",
        WHITE if not dim else DIM,
        (int(zx + 46), int(zy + 20)),
        "center",
    )


def _seg_bar(
    pygame,
    surf,
    rect: tuple[int, int, int, int],
    frac: float,
    segs: int,
    warn_low: bool,
    hot_end: bool,
) -> None:
    """Thin horizontal amber ticks — OEM AP1, not fat LCD blocks."""
    x, y, w, h = rect
    tick_h = max(5, min(10, h))
    gap = max(3, int(w * 0.028))
    tick_w = max(10, int((w - gap * (segs - 1)) / segs * 0.9))
    stride = (w - tick_w) / max(1, segs - 1)
    lit = int(round(frac * segs))
    baseline = y + tick_h + 3
    pygame.draw.line(surf, AMBER_DIM, (x, baseline), (x + w, baseline), 1)
    for i in range(segs):
        sx = x + i * stride
        on = i < lit
        last = i >= segs - 1
        if on and ((warn_low and i == 0) or (hot_end and last and frac > 0.92)):
            col = RED
        elif on:
            col = AMBER
        elif warn_low and i == 0:
            col = RED_DIM
        else:
            col = AMBER_GHOST
        pygame.draw.rect(surf, col, pygame.Rect(int(sx), y, tick_w, tick_h), border_radius=1)


def _thermometer_icon(pygame, surf, cx: int, cy: int, col) -> None:
    """AP1 TEMP pictogram: stem, bulb, three right-hand ticks, two waves."""
    pygame.draw.rect(surf, col, pygame.Rect(cx - 2, cy - 18, 4, 18), border_radius=2)
    pygame.draw.circle(surf, col, (cx, cy + 4), 6)
    pygame.draw.circle(surf, WELL, (cx, cy + 4), 2)
    for dy in (-12, -7, -2):
        pygame.draw.line(surf, col, (cx + 4, cy + dy), (cx + 11, cy + dy), 2)
    for y in (cy + 13, cy + 18):
        pts = [(cx - 8 + x, y + (2 if (x // 4) % 2 else -2)) for x in range(0, 20, 4)]
        if len(pts) >= 2:
            pygame.draw.lines(surf, col, False, pts, 2)


def _pump_icon(pygame, surf, cx: int, cy: int, col) -> None:
    """AP1 FUEL pictogram: pump body, window, hose loop, nozzle, foot."""
    pygame.draw.rect(surf, col, pygame.Rect(cx - 8, cy - 6, 12, 17), border_radius=2)
    pygame.draw.rect(surf, col, pygame.Rect(cx - 6, cy - 12, 8, 6), border_radius=1)
    pygame.draw.rect(surf, WELL, pygame.Rect(cx - 5, cy - 2, 6, 4))
    pygame.draw.arc(surf, col, pygame.Rect(cx, cy - 6, 16, 16), -0.35, 1.7, 2)
    pygame.draw.rect(surf, col, pygame.Rect(cx + 12, cy + 2, 4, 10), border_radius=1)
    pygame.draw.rect(surf, col, pygame.Rect(cx - 8, cy + 11, 12, 2), border_radius=1)


def _side_arch_point(rect: tuple[int, int, int, int], frac: float) -> tuple[float, float]:
    x, y, w, h = rect
    t = clamp(frac, 0.0, 1.0)
    u = 2.0 * t - 1.0
    return x + w * t, y + h * 0.22 + h * 0.72 * u * u


def _side_band_poly(
    rect: tuple[int, int, int, int],
    frac0: float,
    frac1: float,
    depth: float = 16.0,
    steps: int = 20,
) -> list[tuple[int, int]]:
    t0 = clamp(frac0, 0.0, 1.0)
    t1 = clamp(frac1, 0.0, 1.0)
    if t1 <= t0 + 1e-4:
        return []
    n = max(6, steps)
    outer: list[tuple[int, int]] = []
    inner: list[tuple[int, int]] = []
    for i in range(n + 1):
        f = t0 + (t1 - t0) * (i / n)
        f2 = min(1.0, f + 1.0 / n)
        ax, ay = _side_arch_point(rect, f)
        bx, by = _side_arch_point(rect, f2)
        tx, ty = bx - ax, by - ay
        length = math.hypot(tx, ty) or 1.0
        nx, ny = (ty / length) * depth, (-tx / length) * depth
        outer.append((int(ax), int(ay)))
        inner.append((int(ax + nx), int(ay + ny)))
    inner.reverse()
    return outer + inner


def draw_arched_side_gauge(
    pygame,
    fonts,
    surf,
    rect: tuple[int, int, int, int],
    frac: float,
    segs: int,
    left: str,
    right: str,
    warn_low: bool,
    hot_end: bool,
    left_col,
    right_col,
) -> None:
    """Interpretive AP2 rainbow — printed ghost arc plus lit fill."""
    ghost = _side_band_poly(rect, 0.0, 1.0)
    if ghost:
        pygame.draw.polygon(surf, AMBER_GHOST, ghost)
    fill_to = clamp(frac, 0.0, 1.0)
    lit_band = _side_band_poly(rect, 0.0, max(fill_to, 0.02) if fill_to > 0.01 else 0.0)
    if lit_band:
        hot = warn_low or (hot_end and fill_to > 0.92)
        pygame.draw.polygon(surf, RED if hot and fill_to > 0.92 else AMBER, lit_band)
    lit = int(round(frac * segs))
    for i in range(segs):
        t0 = (i + 0.18) / segs
        t1 = (i + 0.82) / segs
        ax, ay = _side_arch_point(rect, t0)
        bx, by = _side_arch_point(rect, t1)
        on = i < lit
        last = i >= segs - 1
        if on and ((warn_low and i == 0) or (hot_end and last and frac > 0.92)):
            col = RED
        elif on:
            col = lerp_colour(AMBER, AMBER_HOT, i / max(1, segs - 1))
        elif warn_low and i == 0:
            col = RED_DIM
        else:
            col = (38, 24, 10)
        nx, ny = (by - ay) * 0.16, (ax - bx) * 0.16
        pts = [
            (int(ax), int(ay)),
            (int(bx), int(by)),
            (int(bx + nx), int(by + ny)),
            (int(ax + nx), int(ay + ny)),
        ]
        pygame.draw.polygon(surf, col, pts)
    lx, ly = _side_arch_point(rect, 0.0)
    rx, ry = _side_arch_point(rect, 1.0)
    blit_text(surf, fonts["tiny"], left, left_col, (int(lx - 12), int(ly)), "center")
    blit_text(surf, fonts["tiny"], right, right_col, (int(rx + 12), int(ry)), "center")


def draw_temp_bar(pygame, fonts, surf, frac: float, hot: bool, g: FaceGeom | None = None) -> None:
    """AP1: thin C–H ticks. AP2: arched side gauge on the right."""
    g = _geom(g)
    x, y, w, h = g.temp
    if g.style == FaceStyle.AP2.value:
        _thermometer_icon(pygame, surf, x + 16, y + 8, AMBER if not hot else RED)
        draw_arched_side_gauge(
            pygame, fonts, surf, g.temp, frac, AP2_TEMP_SEGS, "C", "H",
            False, hot, AMBER, RED if hot else AMBER,
        )
        return
    blit_text(surf, fonts["unit"], "C", AMBER, (x - 16, y + h // 2), "center")
    blit_text(surf, fonts["unit"], "H", RED if hot else AMBER, (x + w + 16, y + h // 2), "center")
    _thermometer_icon(pygame, surf, x + 8, y - 20, AMBER if not hot else RED)
    _seg_bar(pygame, surf, g.temp, frac, TEMP_SEGS, warn_low=False, hot_end=hot)


def draw_fuel_bar(pygame, fonts, surf, frac: float, low: bool, g: FaceGeom | None = None) -> None:
    """AP1: thin E–F ticks. AP2: arched side gauge under TEMP."""
    g = _geom(g)
    x, y, w, h = g.fuel
    if g.style == FaceStyle.AP2.value:
        _pump_icon(pygame, surf, x + w - 16, y + 10, AMBER if not low else ORANGE)
        draw_arched_side_gauge(
            pygame, fonts, surf, g.fuel, frac, AP2_FUEL_SEGS, "E", "F",
            low, False, RED if low else AMBER, AMBER,
        )
        return
    blit_text(surf, fonts["unit"], "E", RED if low else AMBER, (x - 16, y + h // 2), "center")
    blit_text(surf, fonts["unit"], "F", AMBER, (x + w + 16, y + h // 2), "center")
    _pump_icon(pygame, surf, x + w - 6, y - 18, AMBER if not low else ORANGE)
    _seg_bar(pygame, surf, g.fuel, frac, FUEL_SEGS, warn_low=low, hot_end=False)


def draw_speed(pygame, fonts, surf, speed: float, g: FaceGeom | None = None) -> None:
    """3-digit 7-seg speed. Single unit label — OEM centre is not km/h+mph stacked."""
    g = _geom(g)
    value = int(round(clamp(speed, 0.0, 399.0)))
    digits = f"{value:d}".rjust(3)
    cx, cy = g.speed_c
    win = (cx - 128, cy - 52, 236, 100)
    lcd_window(pygame, surf, win, (10, 3, 2), (58, 16, 14), door=(255, 42, 28, 16))
    box = blit_digits(
        pygame,
        surf,
        digits,
        (cx - 8, cy),
        digit_h=96,
        color=RED_LCD,
        ghost=RED_LCD_GHOST,
        ghost_text="188",
        bloom=True,
        italic=0.08,
    )
    unit_x = box[0] + box[2] + 14
    blit_text(surf, fonts["label"], "km/h", RED_LCD, (unit_x, cy + 4), "midleft")


def _clock_text() -> str:
    from datetime import datetime

    return os.environ.get("DASH_CLOCK") or datetime.now().strftime("%H:%M")


def draw_odo_row(
    pygame,
    fonts,
    surf,
    face: DisplayState,
    batt_warn: bool,
    g: FaceGeom | None = None,
) -> None:
    """ODO + TRIP A under the speed. Battery stays a quiet secondary."""
    g = _geom(g)
    cx, y = g.odo_c
    odo = int(round(face.odo_km)) % 1_000_000
    trip = clamp(face.trip_km, 0.0, 999.9)
    if g.style == FaceStyle.AP2.value:
        blit_text(surf, fonts["readout"], _clock_text(), DIM, g.clock_c, "center")
    win = (cx - 196, y - 26, 392, 52)
    lcd_window(pygame, surf, win, (10, 3, 2), (52, 14, 12), door=(255, 42, 28, 14))
    blit_digits(
        pygame,
        surf,
        f"{odo:06d}",
        (cx - 78, y + 4),
        digit_h=26,
        color=RED_LCD,
        ghost=RED_LCD_GHOST,
        ghost_text="888888",
        bloom=True,
        italic=0.04,
    )
    blit_text(surf, fonts["micro"], "TRIP A", RED_LCD, (cx + 118, y - 16), "center")
    blit_digits(
        pygame,
        surf,
        f"{trip:05.1f}",
        (cx + 118, y + 10),
        digit_h=22,
        color=RED_LCD,
        ghost=RED_LCD_GHOST,
        ghost_text="888.8",
        bloom=True,
        italic=0.04,
    )
    if batt_warn:
        blit_text(surf, fonts["micro"], f"{face.batt_v:.1f}V", RED, (cx + 210, y - 18), "midleft")


def _round_btn(pygame, fonts, surf, rect, label: str, label_col=WHITE) -> None:
    """One circular OEM bezel button — never a merged −/+ pill."""
    x, y, w, h = rect
    pygame.draw.ellipse(surf, (22, 22, 22), pygame.Rect(x, y + 2, w, h))
    pygame.draw.ellipse(surf, BEZEL_BTN, pygame.Rect(x, y, w, h))
    pygame.draw.ellipse(surf, (188, 188, 182), pygame.Rect(x + 3, y + 2, max(6, w - 8), max(4, h // 3)), width=1)
    pygame.draw.ellipse(surf, (72, 72, 70), pygame.Rect(x, y, w, h), width=1)
    blit_text(surf, fonts["lamp"], label, label_col, (x + w // 2, y + h // 2), "center")


def _cruise_cancel_icon(pygame, surf, cx: int, cy: int, col) -> None:
    """OEM PUSH CANCEL: speedo dial, needle to 2 o'clock, cancel X."""
    pygame.draw.circle(surf, col, (cx, cy), 8, 2)
    pygame.draw.circle(surf, col, (cx, cy), 2)
    pygame.draw.line(surf, col, (cx, cy), (cx + 5, cy - 5), 2)
    for ang in (3.6, 2.8, 2.2, 1.55):
        x0 = cx + int(5.2 * math.cos(ang))
        y0 = cy - int(5.2 * math.sin(ang))
        x1 = cx + int(7.6 * math.cos(ang))
        y1 = cy - int(7.6 * math.sin(ang))
        pygame.draw.line(surf, col, (x0, y0), (x1, y1), 2)
    pygame.draw.line(surf, col, (cx + 8, cy + 2), (cx + 14, cy + 8), 2)
    pygame.draw.line(surf, col, (cx + 14, cy + 2), (cx + 8, cy + 8), 2)


def draw_hardware_strip(
    pygame,
    fonts,
    surf,
    face: DisplayState,
    bulb_check: bool = False,
    lamps: dict[str, bool] | None = None,
    g: FaceGeom | None = None,
) -> None:
    """Lower bezel: separate round − and +, telltales, SEL/CLOCK + TRIP."""
    g = _geom(g)
    _round_btn(pygame, fonts, surf, g.minus_btn, "−", RED)
    _round_btn(pygame, fonts, surf, g.plus_btn, "+", WHITE)

    rx, ry, rw, rh = g.minus_btn
    dial_x = rx + 10
    dial_y = ry + rh + 16
    _cruise_cancel_icon(pygame, surf, dial_x, dial_y, WHITE)
    blit_text(surf, fonts["lamp"], "PUSH CANCEL", WHITE, (dial_x + 78, dial_y), "center")

    bx, by, bw, bh = g.lamp_band
    flags = face.lamps if lamps is None else lamps
    lamps_on = lamp_states(
        flags,
        bulb_check=bulb_check,
        batt_low=False if lamps is not None else face.batt_v < BATT_LOW_V,
    )
    total = sum(item.width for item in lamps_on) + LAMP_GAP * max(0, len(lamps_on) - 1)
    x = bx + max(8, (bw - total) // 2)
    cy = by + bh // 2
    icon_h = max(16, min(28, bh - 10))
    for item in lamps_on:
        cx = x + item.width // 2
        col = item.color if item.lit else LAMP_GHOST
        sprite = icon_surface(pygame, item.kind, col, icon_h, max_width=item.width - 2)
        if item.lit:
            blit_glow(pygame, surf, sprite, (cx, cy), strength=0.68, scale=1.18)
        else:
            surf.blit(sprite, sprite.get_rect(center=(cx, cy)))
        x += item.width + LAMP_GAP

    _round_btn(pygame, fonts, surf, g.trip_blank, "CLOCK" if g.style == FaceStyle.AP2.value else "SEL")
    _round_btn(pygame, fonts, surf, g.trip, "TRIP")


def draw_ready_card(fonts, surf, face: DisplayState, g: FaceGeom | None = None) -> None:
    """ID.4-like pre-drive summary sitting in the LCD well."""
    g = _geom(g)
    cx = g.speed_c[0]
    ly = g.lcd[1]
    blit_text(surf, fonts["micro"], "S2000  DIGITAL  DASH", DIM, (cx, ly + 70), "center")
    blit_text(surf, fonts["ready"], "READY", AMBER_HOT, g.speed_c, "center")
    blit_text(surf, fonts["tiny"], "IGNITION ON   SYSTEMS OK", DIM, (cx, g.speed_c[1] + 58), "center")
    chips = [
        ("BATT", f"{face.batt_v:.1f} V"),
        ("FUEL", f"{face.fuel_pct:.0f} %"),
        ("TEMP", f"{face.ect_c:.0f} °C"),
        ("ODO", f"{face.odo_km:,.0f} km"),
    ]
    y = g.odo_c[1] + 36
    x0 = cx - 270
    for i, (name, val) in enumerate(chips):
        x = x0 + i * 180
        blit_text(surf, fonts["micro"], name, DIM, (x, y), "center")
        blit_text(surf, fonts["readout"], val, AMBER, (x, y + 26), "center")


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
    draw_tach_segments(pygame, layer, clamp(rpm / float(RPM_REDLINE), 0.0, 1.0), g=g)
    draw_tach_numbers(pygame, fonts, layer, g=g)
    draw_temp_bar(pygame, fonts, layer, ect_frac(face.ect_c), face.ect_c >= ECT_HOT_C, g=g)
    draw_fuel_bar(pygame, fonts, layer, fuel_frac(face.fuel_pct), face.fuel_pct < FUEL_LOW_PCT, g=g)
    draw_speed(pygame, fonts, layer, face.speed_kmh, g=g)
    draw_odo_row(
        pygame,
        fonts,
        layer,
        face,
        face.batt_v < BATT_LOW_V or face.lamps.get("batt_warn", False),
        g=g,
    )
    draw_hardware_strip(pygame, fonts, layer, face, bulb_check=bulb_check, g=g)
    if fade < 0.999:
        layer.set_alpha(int(255 * clamp(fade, 0.0, 1.0)))
        surf.blit(layer, (0, 0))


def draw_caption(fonts, surf, g: FaceGeom | None = None) -> None:
    g = _geom(g)
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
    draw_cabin(pygame, surf)
    draw_cowl(pygame, surf, sweep_t=phase_t if phase == "sweep" else None, g=g)
    lamps, bulb_check = boot_strip_mode(phase, phase_t)
    if phase == "sweep":
        draw_tach_segments(pygame, surf, 0.0, ghost=True, g=g)
        draw_welcome_sweep(pygame, surf, phase_t, g=g)
        draw_tach_numbers(pygame, fonts, surf, dim=True, g=g)
        draw_temp_bar(pygame, fonts, surf, 0.0, False, g=g)
        draw_fuel_bar(pygame, fonts, surf, 0.0, False, g=g)
        draw_hardware_strip(pygame, fonts, surf, face, bulb_check=False, lamps=lamps, g=g)
    elif phase == "ready":
        card = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        draw_ready_card(fonts, card, face, g=g)
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


def build_fonts(pygame) -> dict:
    return {
        "speed": _font(pygame, 132, bold=True, mono=True),
        "ready": _font(pygame, 92, bold=True),
        # OEM Car Spy: tach numerals sit at ~38 px tall with a thin stroke;
        # the SemiBoldItalic at 42 was rendering noticeably heavier than the
        # OEM glyph plate. Sizing down + the natural pixel-thinness at this
        # scale brings the stroke weight into OEM territory.
        "tick": _font(pygame, 38, italic=True),
        "label": _font(pygame, 20, bold=True),
        "readout": _font(pygame, 26, bold=True, mono=True),
        "tiny": _font(pygame, 15, italic=True),
        "unit": _font(pygame, 18, bold=True),
        "micro": _font(pygame, 13, bold=True),
        "lamp": _font(pygame, 16, bold=True),
    }


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

    apply_face_style(args.style)
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
                if event.key == pygame.K_2:
                    apply_face_style(FaceStyle.AP2)

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


if __name__ == "__main__":
    main()
