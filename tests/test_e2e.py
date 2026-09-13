"""E2E: mock ESP32 → protocol parse → dummy-SDL cluster frames.

Structural invariants only (dimensions, red speed LCD, amber tach, phase
diffs, lamp colours). No brittle pixel hashes — font/AA can drift across hosts.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "src"))
sys.path.insert(0, str(_ROOT / "tests"))

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from gauge_ui import (  # noqa: E402
    AMBER,
    FACE,
    RED_LCD,
    SMOKE_PHASES,
    W,
    H,
    DisplayState,
    SerialSource,
    draw_frame,
    write_screenshots,
)
from mocks.esp32_uart import iter_frames, warn_frame  # noqa: E402
from mocks.fake_serial import FakeSerial  # noqa: E402
from oem_icons import LAMP_BLUE, NEON_CYAN  # noqa: E402
from protocol import REQUIRED_FIELDS, parse_line  # noqa: E402
from serial_reader import SerialLineReader  # noqa: E402
from _headless import count_warm, init_cluster, sample_near  # noqa: E402


SHOT_NAMES = [
    "01_sweep.png",
    "02_ready.png",
    "03_reveal.png",
    "04_live.png",
    "05_cruise.png",
]


class E2EPipelineTests(unittest.TestCase):
    def test_mock_esp32_to_parse_to_smoke_frames(self) -> None:
        lines = [telem.to_line() for telem in iter_frames(20, scenario="drive")]
        self.assertEqual(len(lines), 20)
        parsed = [parse_line(line) for line in lines]
        for telem in parsed:
            for key in REQUIRED_FIELDS:
                self.assertIn(key, telem.to_dict())

        pygame, screen, fonts = init_cluster()
        try:
            face = DisplayState()
            face.snap(parsed[-1])
            blobs = []
            for phase, local_t in SMOKE_PHASES:
                draw_frame(pygame, fonts, screen, face, phase, local_t)
                self.assertEqual(screen.get_size(), (W, H))
                self.assertGreater(count_warm(screen, step=12), 20, phase)
                if phase in ("ready", "live"):
                    self.assertGreater(sample_near(screen, AMBER, step=12, tol=48), 8, phase)
                blobs.append(pygame.image.tobytes(screen, "RGB"))
            self.assertNotEqual(blobs[0], blobs[3])
        finally:
            pygame.quit()

    def test_fake_serial_loopback_into_ui_source(self) -> None:
        frames = list(iter_frames(4, scenario="warn"))
        ser = FakeSerial(telem.to_line() for telem in frames)
        reader = SerialLineReader(ser)
        got = reader.poll()
        self.assertIsNotNone(got)
        self.assertEqual(got.rpm, frames[-1].rpm)
        self.assertTrue(got.lamp("door"))

        ui_got = SerialSource(FakeSerial([warn_frame().to_line()])).poll()
        self.assertIsNotNone(ui_got)
        self.assertTrue(ui_got.lamp("srs"))
        self.assertTrue(ui_got.lamp("high_beam"))

    def test_subprocess_pipe_smoke_screenshots(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            emit = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "mocks.esp32_uart",
                    "--count",
                    "25",
                    "--immediate",
                    "--scenario",
                    "drive",
                ],
                cwd=_ROOT,
                stdout=subprocess.PIPE,
            )
            ui = subprocess.run(
                [
                    sys.executable,
                    str(_ROOT / "src" / "gauge_ui.py"),
                    "--smoke",
                    "--screenshot",
                    str(dest),
                ],
                cwd=_ROOT,
                stdin=emit.stdout,
                capture_output=True,
                text=True,
                env={
                    **os.environ,
                    "SDL_VIDEODRIVER": "dummy",
                    "SDL_AUDIODRIVER": "dummy",
                },
            )
            self.assertIsNotNone(emit.stdout)
            emit.stdout.close()
            emit.wait(timeout=15)
            self.assertEqual(ui.returncode, 0, ui.stderr)
            self.assertEqual(sorted(os.listdir(dest)), SHOT_NAMES)
            import pygame

            pygame.init()
            try:
                live = pygame.image.load(str(dest / "04_live.png"))
                sweep = pygame.image.load(str(dest / "01_sweep.png"))
                self.assertEqual(live.get_size(), (W, H))
                self.assertEqual(sweep.get_size(), (W, H))
                self.assertNotEqual(
                    pygame.image.tobytes(live, "RGB"),
                    pygame.image.tobytes(sweep, "RGB"),
                )
                self.assertGreater(sample_near(live, AMBER, step=12, tol=48), 8)
                cx, cy = FACE.speed_c
                well = live.subsurface((cx - 140, cy - 70, 280, 140))
                self.assertGreater(sample_near(well, RED_LCD, step=3, tol=48), 8)
            finally:
                pygame.quit()

    def test_screenshot_helper_matches_named_scenes(self) -> None:
        pygame, _screen, fonts = init_cluster()
        try:
            face = DisplayState()
            face.snap(warn_frame())
            with tempfile.TemporaryDirectory() as tmp:
                written = write_screenshots(pygame, fonts, face, Path(tmp))
                self.assertEqual([p.name for p in written], SHOT_NAMES)
                live = pygame.image.load(str(Path(tmp) / "04_live.png"))
                # high beam is one of the round windows inside the tach arc
                self.assertGreater(sample_near(live.subsurface(FACE.lcd), LAMP_BLUE, step=2, tol=40), 0)
                self.assertEqual(sample_near(live, NEON_CYAN, step=10, tol=18), 0)
        finally:
            pygame.quit()


class E2EPtyTests(unittest.TestCase):
    def test_pty_loopback_optional_pyserial(self) -> None:
        try:
            import serial  # type: ignore
        except ImportError:
            self.skipTest("pyserial not installed")

        from mocks.fake_serial import close_pty, open_pty_pair, write_pty
        from protocol import SERIAL_BAUD

        telem = warn_frame()
        slave_name, master_fd, slave_fd = open_pty_pair()
        try:
            # Open the reader first — opening a PTY slave often flushes queued bytes.
            ser = serial.Serial(slave_name, SERIAL_BAUD, timeout=0.2)
            try:
                write_pty(master_fd, telem.to_line())
                got = SerialLineReader(ser).poll()
                if got is None:
                    raw = ser.readline()
                    from protocol import try_parse_line

                    got = try_parse_line(raw.decode("utf-8", errors="ignore"))
            finally:
                ser.close()
        finally:
            close_pty(master_fd, slave_fd)
        self.assertIsNotNone(got)
        self.assertEqual(got.rpm, telem.rpm)
        self.assertTrue(got.lamp("brake"))
        for key in REQUIRED_FIELDS:
            self.assertIn(key, got.to_dict())


if __name__ == "__main__":
    unittest.main()
