"""Full acceptance must reject altered ink even with fresh capture hashes."""
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys

import pygame
import pytest

from scripts import accept_oem, measure_oem_ui


@pytest.fixture(scope="module")
def composite(tmp_path_factory):
    dest = tmp_path_factory.mktemp("acceptance")
    subprocess.run([sys.executable, "-c",
                    "import sys; from pathlib import Path; from scripts import compare_oem; "
                    "compare_oem.DEST = Path(sys.argv[1]); raise SystemExit(compare_oem.main())",
                    str(dest)], check=True, capture_output=True)
    return dest / "compare_ap1_lit_live.png"


def test_all_reference_tracks_pass(composite):
    report = accept_oem.evaluate(composite)
    assert report["acceptance_pass"]
    assert set(report["tracks"]) == {"graphics", "colour", "position", "size", "motion", "font"}


def test_erasing_one_tach_glyph_fails_the_complete_gate(composite, tmp_path):
    image, metadata = measure_oem_ui.load_capture(composite)
    mx, my, mw, mh = metadata["ui_module"]
    # Numeral five at the literal lock position, leaving the band/LCD intact.
    a = math.radians(-127.8 + 4.6 * 75.6 / 8.6)
    cx = mx + mw * (.5 + .519 * math.cos(a))
    cy = my + mh * 1.487 + mw * .519 * math.sin(a)
    image.fill((0, 0, 0), pygame.Rect(round(cx - mw*.02), round(cy - mw*.015), round(mw*.04), round(mw*.03)))
    changed = tmp_path / "changed.png"
    pygame.image.save(image, str(changed))
    metadata["image_sha256"] = hashlib.sha256(changed.read_bytes()).hexdigest()
    changed.with_suffix(".json").write_text(json.dumps(metadata))
    report = accept_oem.evaluate(changed)
    assert not report["tracks"]["font"]["pass"]
    assert not report["acceptance_pass"]
    assert accept_oem.main(["--composite", str(changed), "--check"]) == 1


def test_previous_lcd_colour_fails_captured_pixels(composite):
    image, metadata = measure_oem_ui.load_capture(composite)
    mx, my, mw, mh = metadata["ui_module"]
    for y in range(round(my + .35*mh), round(my + .568*mh)):
        for x in range(round(mx + .39*mw), round(mx + .60*mw)):
            p = image.get_at((x, y))
            if p.r > 200 and p.g > 50 and p.b < 130:
                image.set_at((x, y), (255, 66, 40))
    assert not accept_oem.capture_tracks(image, metadata)["colour"]["pass"]


def test_solid_hatch_region_fails_captured_pixels(composite):
    image, metadata = measure_oem_ui.load_capture(composite)
    mx, my, mw, mh = metadata["ui_module"]
    points = []
    for radius, angles in [(.590, range(21)), (.557, range(20, -1, -1))]:
        for i in angles:
            a = math.radians(-133.3 + 5.5 * i / 20)
            points.append((round(mx + mw*(.5 + radius*math.cos(a))), round(my + mh*1.487 + mw*radius*math.sin(a))))
    pygame.draw.polygon(image, (255, 191, 79), points)
    assert not accept_oem.capture_tracks(image, metadata)["graphics"]["pass"]
