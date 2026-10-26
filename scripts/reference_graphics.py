"""Measure separated hatch strokes in a captured module and the OEM photo."""
import math
from pathlib import Path

import pygame

ROOT = Path(__file__).resolve().parents[1]


def reference_coverage():
    photo = pygame.image.load(str(ROOT / "refs/oem/lit/lit_ap1_carspy_cluster.jpg"))
    samples = [photo.get_at((round(405 + 42*i/100), round(498 - 29*i/100))) for i in range(101)]
    return sum(p.r > 210 and p.g > 140 and p.b < 150 for p in samples) / len(samples)


def capture_coverage(image, module):
    mx, my, mw, mh = module
    samples = []
    for i in range(301):
        a = math.radians(-133.3 + 5.5*i/300)
        x = round(mx + mw*(.5 + .5735*math.cos(a)))
        y = round(my + mh*1.487 + mw*.5735*math.sin(a))
        p = image.get_at((x, y))
        samples.append(p.r > 140 and p.r > p.g*1.2 and p.g > p.b*1.4)
    coverage = sum(samples) / len(samples)
    runs = sum(on and (i == 0 or not samples[i-1]) for i, on in enumerate(samples))
    return coverage, runs


def measure(image, metadata):
    coverage, runs = capture_coverage(image, metadata["ui_module"])
    expected = reference_coverage()
    return [{"sample": "left_hatches", "reference_ink_fraction": expected,
             "ui_ink_fraction": coverage, "runs": runs, "expected_runs": 5,
             "coverage_tolerance": .10, "pass": runs == 5 and abs(coverage - expected) <= .10}]
