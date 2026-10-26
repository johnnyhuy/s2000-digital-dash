"""Photo-derived hatch ink coverage, independent of the rendered face spec."""
import math
from pathlib import Path

import pygame

from face_spec import AP1
from gauge_ui import _draw_band_unlit, build_face_geom

ROOT = Path(__file__).resolve().parents[1]


def reference_coverage():
    photo = pygame.image.load(str(ROOT / "refs/oem/lit/lit_ap1_carspy_cluster.jpg"))
    # Cross the five left hatches perpendicular to their long edges.
    samples = [photo.get_at((round(405 + 42 * i / 100), round(498 - 29 * i / 100))) for i in range(101)]
    return sum(p.r > 210 and p.g > 140 and p.b < 150 for p in samples) / len(samples)


def capture_coverage(image, module):
    mx, my, mw, mh = module
    samples = []
    for i in range(301):
        # Independent DIMENSIONS.md circle and overrun; mid-band radius.
        a = math.radians(-133.3 + 5.5 * i / 300)
        x = round(mx + mw * (.5 + .5735 * math.cos(a)))
        y = round(my + mh * 1.487 + mw * .5735 * math.sin(a))
        p = image.get_at((x, y))
        samples.append(p.r > 140 and p.r > p.g * 1.2 and p.g > p.b * 1.4)
    coverage = sum(samples) / len(samples)
    runs = sum(on and (i == 0 or not samples[i - 1]) for i, on in enumerate(samples))
    return coverage, runs


def test_rendered_hatches_match_photo_ink_coverage():
    g = build_face_geom()
    image = pygame.Surface((1920, 1080))
    _draw_band_unlit(pygame, image, g)
    coverage, runs = capture_coverage(image, g.module)
    assert runs == 5
    assert abs(coverage - reference_coverage()) <= .10, coverage


def test_filled_overrun_is_rejected():
    # Previous geometry covered ~80% of the hatch region instead of ~33%.
    coverage = sum(b - a for a, b in AP1.tach.hatch_spans("left")) / 5.5
    assert abs(coverage - reference_coverage()) <= .10
    assert abs(.80 - reference_coverage()) > .10
