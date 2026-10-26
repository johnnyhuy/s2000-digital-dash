"""Reproducible photo/UI colour comparisons, without a panel-calibration claim."""
from collections import Counter
from pathlib import Path
import statistics

import pygame

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "refs/oem/lit/lit_ap1_carspy_cluster.jpg"

# Literal reference pixels and UI ROIs in the locked module coordinate space.
# The photo is at idle; its lit hatch/side-bar amber is the available proxy
# for lit tach amber. Normalize by the peak channel to separate exposure.
SAMPLES = {
    "lcd_red": ((888, 471, 954, 563), (.39, .35, .60, .568)),
    "side_amber": ((364, 562, 442, 580), (.135, .586, .26, .616)),
    "hatch_amber": ((385, 466, 465, 514), (.10, .34, .16, .50)),
    "hatch_red": ((1170, 442, 1258, 503), (.84, .34, .91, .50)),
}


def selected(key, p, photo=False):
    r, g, b = p[:3]
    if key == "lcd_red":
        return r > 200 and r > g * 2 and g > b * 1.2
    if key in ("side_amber", "hatch_amber"):
        return r > 180 and 90 < g < 225 and b < 150 and g > b * 1.5
    return r > 160 and r > g * 1.5 and g > b * 1.1


def pixels(image, box, key):
    x0, y0, x1, y1 = box
    return [tuple(image.get_at((x, y))[:3])
            for y in range(round(y0), round(y1)) for x in range(round(x0), round(x1))
            if selected(key, image.get_at((x, y)))]


def chroma(rgb):
    peak = max(rgb)
    return tuple(c / peak for c in rgb)


def measure(image, metadata):
    reference = pygame.image.load(str(REFERENCE))
    mx, my, mw, mh = metadata["ui_module"]
    checks = []
    for key, (ref_box, roi) in SAMPLES.items():
        ref_pixels = pixels(reference, ref_box, key)
        expected = tuple(statistics.median(p[c] for p in ref_pixels) for c in range(3))
        x0, y0, x1, y1 = roi
        ui_pixels = pixels(image, (mx + mw*x0, my + mh*y0, mx + mw*x1, my + mh*y1), key)
        actual = Counter(ui_pixels).most_common(1)[0][0] if ui_pixels else None
        delta = max(abs(a-b) for a,b in zip(chroma(actual), chroma(expected))) if actual else None
        checks.append({"sample": key, "reference_rgb": expected, "ui_rgb": actual,
                       "max_chroma_delta": delta, "tolerance": .08,
                       "pass": delta is not None and delta <= .08})
    return checks
