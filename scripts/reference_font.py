"""Compare captured tach ink with the independent reference-plate alphabet."""
import hashlib
import json
import math
from pathlib import Path

import pygame

ROOT = Path(__file__).resolve().parents[1]


def white_mask(image):
    mask = pygame.mask.Mask(image.get_size())
    for y in range(image.get_height()):
        for x in range(image.get_width()):
            p = image.get_at((x, y))
            if min(p[:3]) > 140 and max(p[:3]) - min(p[:3]) < 35:
                mask.set_at((x, y))
    return mask


def measure(image, metadata):
    source = json.loads((ROOT / "assets/fonts/oem-tach/source.json").read_text())
    reference = ROOT / source["reference"]
    if hashlib.sha256(reference.read_bytes()).hexdigest() != source["reference_sha256"]:
        raise ValueError("tach reference plate changed after the alphabet was traced")
    plate = pygame.image.load(str(reference))
    mx, my, mw, mh = metadata["ui_module"]
    checks = []
    for i in range(10):
        # Literal circle, nominal size and division compression from the lock.
        angle = math.radians(-127.8 + (0 if i == 0 else i - .4) * 75.6 / 8.6)
        cx = mx + mw * (.5 + .519 * math.cos(angle))
        cy = my + mh * 1.487 + mw * .519 * math.sin(angle)
        crop = pygame.Rect(source["crops"][str(i)])
        h = max(1, round(mw * .034 * .72))
        w = max(1, round(h * crop.w / crop.h))
        target = pygame.transform.smoothscale(plate.subsurface(crop), (w, h))
        expected = white_mask(target)
        # One capture pixel of centre rounding in each direction is allowed.
        roi = pygame.Rect(round(cx - w / 2) - 2, round(cy - h / 2) - 2, w + 4, h + 4)
        actual = white_mask(image.subsurface(roi))
        scores = []
        for dy in (1, 2, 3):
            for dx in (1, 2, 3):
                intersection = actual.overlap_area(expected, (dx, dy))
                union = actual.count() + expected.count() - intersection
                scores.append(intersection / union if union else 0)
        iou = max(scores)
        checks.append({"glyph": str(i), "ink_iou": iou, "minimum": .70, "pass": iou >= .70})
    return checks
