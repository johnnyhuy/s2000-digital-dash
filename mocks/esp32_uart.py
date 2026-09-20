#!/usr/bin/env python3
"""Mock ESP32 UART emitter — Phase 2 newline JSON at ~20 Hz, no firmware.

Speaks the same frozen fields as ``src/mock_telemetry.py`` / ``src/protocol.py``.
Does not claim to be flashed ESP32 firmware; it is a bench stand-in so the
Pi UI and serial reader can be exercised without hardware.

  python -m mocks.esp32_uart
  python -m mocks.esp32_uart --count 40 --immediate
  python -m mocks.esp32_uart --scenario warn --count 5 --immediate
  python -m mocks.esp32_uart --pty --count 20 --immediate
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import IO, Optional, TextIO

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from mock_telemetry import driving_loop  # noqa: E402
from protocol import MOCK_HZ, REQUIRED_FIELDS, Telemetry  # noqa: E402

# Optional OEM telltales already drawn on main; names pass through as bools.
OEM_EXTRA_LAMPS = (
    "brake",
    "immobilizer",
    "maint",
    "eps",
    "seatbelt",
    "door",
    "trunk",
    "srs",
)

SCENARIOS = ("drive", "warn", "idle")


def _extras_off() -> dict[str, bool]:
    return {key: False for key in OEM_EXTRA_LAMPS}


def warn_frame(odo: float = 142_857.3) -> Telemetry:
    """Hot / low-fuel / lamp-on frame used by headless colour + e2e tests."""
    lamps = {
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
        **{key: True for key in OEM_EXTRA_LAMPS},
    }
    return Telemetry(
        rpm=8200,
        speed_kmh=12.0,
        fuel_pct=8.0,
        ect_c=108.0,
        batt_v=11.8,
        odo_km=round(odo, 1),
        lamps=lamps,
    )


def idle_frame(odo: float = 142_857.3) -> Telemetry:
    return Telemetry(
        rpm=850,
        speed_kmh=0.0,
        fuel_pct=62.0,
        ect_c=82.0,
        batt_v=12.6,
        odo_km=round(odo, 1),
        lamps={
            "oil": False,
            "cel": False,
            "abs": False,
            "turn_l": False,
            "turn_r": False,
            "high_beam": False,
            "fog": False,
            "fuel_low": False,
            "batt_warn": False,
            "ect_hot": False,
            **_extras_off(),
        },
    )


def frame_at(t: float, odo: float, scenario: str = "drive") -> Telemetry:
    """One protocol-valid frame. Field names stay frozen."""
    if scenario == "warn":
        return warn_frame(odo)
    if scenario == "idle":
        return idle_frame(odo)
    if scenario != "drive":
        raise ValueError(f"unknown scenario: {scenario}")
    telem = driving_loop(t, odo)
    telem.lamps = {**_extras_off(), **telem.lamps}
    return telem


def iter_frames(
    count: int,
    *,
    scenario: str = "drive",
    hz: float = MOCK_HZ,
    odo: float = 142_857.3,
) -> Iterator[Telemetry]:
    if count < 0:
        raise ValueError("count must be >= 0")
    dt = 1.0 / hz if hz > 0 else 0.05
    t = 0.0
    for _ in range(count):
        telem = frame_at(t, odo, scenario)
        yield telem
        odo += max(0.0, telem.speed_kmh) / 3600.0 * dt
        t += dt


def emit_frames(
    frames: Iterable[Telemetry],
    sink: IO[str] | TextIO,
) -> int:
    n = 0
    for telem in frames:
        sink.write(telem.to_line())
        n += 1
    if hasattr(sink, "flush"):
        sink.flush()
    return n


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Mock ESP32 UART: newline JSON at ~20 Hz (no firmware)",
    )
    p.add_argument(
        "--hz",
        type=float,
        default=MOCK_HZ,
        help=f"Emit rate (default {MOCK_HZ}, Phase 2 UART cadence)",
    )
    p.add_argument(
        "--count",
        type=int,
        default=None,
        help="Frame count then exit (default: run until SIGINT / broken pipe)",
    )
    p.add_argument(
        "--immediate",
        action="store_true",
        help="Do not sleep between frames (tests / CI)",
    )
    p.add_argument(
        "--scenario",
        choices=SCENARIOS,
        default="drive",
        help="drive = mock cruise loop; warn = all lamps; idle = parked",
    )
    p.add_argument(
        "--pty",
        action="store_true",
        help="Open a local PTY and print PTY=/dev/pts/N for --serial",
    )
    return p.parse_args(argv)


def _pace(hz: float, started: float) -> None:
    if hz <= 0:
        return
    dt = 1.0 / hz
    sleep_for = dt - (time.monotonic() - started)
    if sleep_for > 0:
        time.sleep(sleep_for)


def _write_forever(
    sink_write,
    *,
    hz: float,
    scenario: str,
    immediate: bool,
) -> None:
    dt = 1.0 / hz if hz > 0 else 0.05
    t0 = time.monotonic()
    odo = 142_857.3
    while True:
        now = time.monotonic()
        t = now - t0
        telem = frame_at(t, odo, scenario)
        odo += max(0.0, telem.speed_kmh) / 3600.0 * dt
        telem.odo_km = round(odo, 1)
        sink_write(telem.to_line())
        if not immediate:
            _pace(hz, now)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.hz <= 0:
        print("hz must be > 0", file=sys.stderr)
        return 2

    master_fd: Optional[int] = None
    slave_fd: Optional[int] = None

    def write_stdout(line: str) -> None:
        sys.stdout.write(line)
        sys.stdout.flush()

    def write_master(line: str) -> None:
        assert master_fd is not None
        os.write(master_fd, line.encode("utf-8"))

    sink_write = write_stdout
    if args.pty:
        import pty

        master_fd, slave_fd = pty.openpty()
        print(f"PTY={os.ttyname(slave_fd)}", flush=True)
        sink_write = write_master

    try:
        if args.count is None:
            _write_forever(
                sink_write,
                hz=args.hz,
                scenario=args.scenario,
                immediate=args.immediate,
            )
            return 0
        frames = iter_frames(args.count, scenario=args.scenario, hz=args.hz)
        for telem in frames:
            now = time.monotonic()
            sink_write(telem.to_line())
            if not args.immediate:
                _pace(args.hz, now)
        return 0
    except BrokenPipeError:
        return 0
    except KeyboardInterrupt:
        return 0
    finally:
        if master_fd is not None:
            os.close(master_fd)
        if slave_fd is not None:
            os.close(slave_fd)


if __name__ == "__main__":
    # Required field names stay frozen — imported so a typo fails import time.
    assert REQUIRED_FIELDS == (
        "rpm",
        "speed_kmh",
        "fuel_pct",
        "ect_c",
        "batt_v",
        "odo_km",
    )
    raise SystemExit(main())
