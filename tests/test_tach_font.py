"""Reject a substitute font by comparing its ink to the committed OEM plate."""
import hashlib
import json
from pathlib import Path

import pygame
import pytest

from scripts.export_tach_font import generate
from tach_font import glyph

ROOT = Path(__file__).resolve().parents[1]
FONT = ROOT / "assets/fonts/oem-tach"


@pytest.mark.parametrize("key", [str(i) for i in range(10)] + ["rpm"])
def test_glyph_silhouette_matches_reference_plate(key):
    source = json.loads((FONT / "source.json").read_text())
    plate = ROOT / source["reference"]
    assert hashlib.sha256(plate.read_bytes()).hexdigest() == source["reference_sha256"]
    image = pygame.image.load(str(plate))
    x0, y0, w, h = source["crops"][key]
    expected = pygame.mask.Mask((w, h))
    for y in range(h):
        for x in range(w):
            if min(image.get_at((x0 + x, y0 + y))[:3]) > source["threshold"]:
                expected.set_at((x, y))
    actual = pygame.mask.from_surface(glyph(pygame, key, h, (255, 255, 255)), 128)
    intersection = expected.overlap_area(actual, (0, 0))
    iou = intersection / (expected.count() + actual.count() - intersection)
    assert iou >= .90, (key, iou)


def test_web_alphabet_uses_identical_svg_masters():
    assert (ROOT / "apps/harness/components/TachGlyphs.tsx").read_text() == generate()
