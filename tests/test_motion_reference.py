"""Discrete-cell and frame-rate invariants supported by the face lock."""
from pathlib import Path

import pygame
import pytest

from gauge_ui import build_face_geom, draw_tach_fill, exp_smooth
from motion_spec import export_json


def tach_pixels(rpm):
    image = pygame.Surface((1000, 600))
    draw_tach_fill(pygame, image, rpm, None, build_face_geom(1000, 600))
    return pygame.image.tobytes(image, "RGB")


@pytest.mark.parametrize("low,high,next_step", [(0, 199.9, 200), (3200, 3399.9, 3400), (8000, 8199.9, 8200)])
def test_tach_changes_only_at_whole_200_rpm_cells(low, high, next_step):
    assert tach_pixels(low) == tach_pixels(high)
    assert tach_pixels(high) != tach_pixels(next_step)


def test_smoothing_export_and_no_time_advance():
    path = Path(__file__).resolve().parents[1] / "apps/harness/lib/motionSpec.json"
    assert path.read_text() == export_json()
    assert exp_smooth(100, 9000, 0, .18) == 100
    assert exp_smooth(100, 9000, -.01, .18) == 100
    assert exp_smooth(100, 9000, .01, 0) == 9000


@pytest.mark.parametrize("fps", [30, 60, 120])
def test_frame_rate_independent_response(fps):
    rpm = 0
    for _ in range(fps):
        rpm = exp_smooth(rpm, 9000, 1 / fps, .18)
    assert rpm == pytest.approx(exp_smooth(0, 9000, 1, .18), abs=1e-8)
