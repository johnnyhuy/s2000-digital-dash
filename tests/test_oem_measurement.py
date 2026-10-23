"""The acceptance tool must reject missing, stale, and visibly wrong pixels."""
import json
import subprocess
import sys

import pytest
import pygame

from scripts import measure_oem_ui


@pytest.fixture(scope="module")
def capture(tmp_path_factory):
    dest = tmp_path_factory.mktemp("oem-composites")
    # Rendering owns pygame.init/quit. Keep it out of the test process so
    # cached font objects in other render tests cannot outlive SDL teardown.
    subprocess.run([
        sys.executable, "-c",
        "import sys; from pathlib import Path; from scripts import compare_oem; "
        "compare_oem.DEST = Path(sys.argv[1]); raise SystemExit(compare_oem.main())",
        str(dest),
    ], check=True, capture_output=True, text=True)
    return dest / "compare_ap1_lit_live.png"


def test_measures_actual_unequal_panels(capture):
    image, metadata = measure_oem_ui.load_capture(capture)
    assert metadata["ui_panel"][0] != image.get_width() // 2
    report = measure_oem_ui.measure(image, metadata)
    assert report["geometry_pass"]
    assert measure_oem_ui.measure_oem()["hood_peak"] == 10.42
    assert measure_oem_ui.main(["--composite", str(capture), "--check"]) == 0


def test_missing_pixels_fail_instead_of_becoming_zero(capture):
    image, metadata = measure_oem_ui.load_capture(capture)
    image.fill((0, 0, 0))
    report = measure_oem_ui.measure(image, metadata)
    assert not report["geometry_pass"]
    assert report["checks"][0]["measured_pct"] is None


def test_displaced_speed_pixels_fail(capture):
    image, metadata = measure_oem_ui.load_capture(capture)
    mx, my, mw, mh = metadata["ui_module"]
    box = (round(mx + .39 * mw), round(my + .35 * mh),
           round(mx + .60 * mw), round(my + .568 * mh))
    rect = pygame.Rect(box[0], box[1], box[2] - box[0], box[3] - box[1])
    digits = image.subsurface(rect).copy()
    image.fill((0, 0, 0), rect)
    image.blit(digits, (box[0] - round(.04 * mw), box[1]))
    report = measure_oem_ui.measure(image, metadata)
    right = next(c for c in report["checks"] if c["landmark"] == "speed_right_pct")
    assert not right["pass"]


def test_stale_composite_is_rejected(capture, tmp_path):
    other = tmp_path / "changed.png"
    image, metadata = measure_oem_ui.load_capture(capture)
    image.set_at((0, 0), (255, 0, 0))
    pygame.image.save(image, str(other))
    other.with_suffix(".json").write_text(json.dumps(metadata))
    with pytest.raises(ValueError, match="composite changed"):
        measure_oem_ui.load_capture(other)
    with pytest.raises(SystemExit) as failure:
        measure_oem_ui.main(["--composite", str(other), "--check"])
    assert failure.value.code == 2
