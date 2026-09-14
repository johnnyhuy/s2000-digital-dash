"""Sanity checks for the replace-face printables and their lock (no pygame)."""

from __future__ import annotations

import re
import struct
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from face_spec import spec_for, spec_to_scad  # noqa: E402

REPLACE = ROOT / "cad" / "replace_face"
PRINT_STL = REPLACE / "print" / "stl"
PRINT_STEP = REPLACE / "print" / "step"
PRINT_OBJ = REPLACE / "print" / "obj"
PREVIEW = REPLACE / "preview" / "assembly.glb"
SCRIPT = REPLACE / "mesh_export.py"
LOCK_SCAD = REPLACE / "face_lock.scad"
DIMS_SCAD = REPLACE / "dims.scad"
OUTLINE_SCAD = REPLACE / "outline.scad"
README = REPLACE / "README.md"

PARTS = ("backlight", "backlight_web", "acrylic_face", "button_rocker", "button_sel", "button_trip")

# Expected bbox of the cleaned printables — pins the meshes to the SCAD lock.
# (min), (max), tolerance mm
BBOX = {
    "acrylic_face": ((0.0, 0.0, 0.0), (170.0, 73.33, 2.0), 0.05),
    "backlight": ((-2.0, -16.13, 0.0), (172.0, 88.47, 12.0), 0.08),
    "backlight_web": ((2.49, 2.49, 0.0), (167.51, 53.77, 0.9), 0.08),
    "button_rocker": ((-1.6, -1.6, 0.0), (19.96, 10.1, 3.6), 0.08),
    "button_sel": ((-1.0, -1.0, 0.0), (7.8, 5.34, 3.6), 0.08),
    "button_trip": ((-1.0, -1.0, 0.0), (7.8, 5.34, 3.6), 0.08),
}


def _read_binary_stl(path: Path):
    data = path.read_bytes()
    count = struct.unpack_from("<I", data, 80)[0]
    if 84 + count * 50 != len(data):
        raise ValueError(f"{path.name}: not a binary STL")
    mn = [1e9, 1e9, 1e9]
    mx = [-1e9, -1e9, -1e9]
    for i in range(count):
        vals = struct.unpack_from("<12f", data, 84 + i * 50)
        for v in (vals[3:6], vals[6:9], vals[9:12]):
            for a in range(3):
                mn[a] = min(mn[a], v[a])
                mx[a] = max(mx[a], v[a])
    return count, tuple(mn), tuple(mx)


def _scad_numbers(path: Path) -> dict[str, float]:
    text = path.read_text(encoding="utf-8")
    pat = r"^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)\s*;"
    return {m.group(1): float(m.group(2)) for m in re.finditer(pat, text, flags=re.MULTILINE)}


class ReplaceFaceLockTest(unittest.TestCase):
    def test_face_lock_scad_is_in_sync_with_face_spec(self):
        # Arrange: the committed lock must be exactly what the spec exports today.
        expected = spec_to_scad(spec_for("ap1"))
        # Act / Assert
        self.assertEqual(LOCK_SCAD.read_text(encoding="utf-8"), expected, "run `uv run python src/face_spec.py`")

    def test_lock_carries_the_arc_geometry_not_a_parabola(self):
        lock = _scad_numbers(LOCK_SCAD)
        for name in ("tach_cx", "tach_cy_h", "tach_r_out", "tach_r_in", "tach_a0", "tach_a9", "crown_cy_h", "crown_r", "spring_y_h"):
            self.assertIn(name, lock, name)
        self.assertLess(lock["tach_a0"], lock["tach_a9"])
        self.assertGreater(lock["tach_r_out"], lock["tach_r_in"])
        self.assertAlmostEqual(lock["module_aspect"], 2.35, places=3)
        text = (DIMS_SCAD.read_text(encoding="utf-8") + OUTLINE_SCAD.read_text(encoding="utf-8")).lower()
        self.assertNotIn("parabola", text)
        self.assertNotIn("28 u", text)

    def test_dims_derive_mm_from_the_lock(self):
        text = DIMS_SCAD.read_text(encoding="utf-8")
        self.assertIn("include <face_lock.scad>", text)
        dims = _scad_numbers(DIMS_SCAD)
        self.assertAlmostEqual(dims["face_w"], 170.0)
        # Panel pocket is parametric, not the face box.
        for name in ("panel_w", "panel_h", "panel_t", "panel_active_w", "panel_active_h"):
            self.assertIn(name, dims, name)
        self.assertGreater(dims["panel_active_h"], dims["face_w"] / 2.35)
        self.assertLess(dims["panel_active_w"], dims["face_w"])

    def test_outline_cuts_display_windows_from_the_lock(self):
        text = OUTLINE_SCAD.read_text(encoding="utf-8")
        for mod in ("tach_window_2d", "speed_window_2d", "odo_window_2d", "temp_window_2d", "fuel_window_2d", "arc_lamp_holes_2d", "strip_window_2d", "panel_pocket_2d"):
            self.assertIn(f"module {mod}(", text, mod)
        self.assertIn("min_rim", text)


class ReplaceFacePrintablesTest(unittest.TestCase):
    def test_mesh_export_help_runs_without_trimesh(self):
        proc = subprocess.run([sys.executable, str(SCRIPT), "--help"], check=False, capture_output=True, text=True)
        # numpy / trimesh may be missing in a bare venv — only the import may fail.
        if proc.returncode != 0:
            self.assertIn("ModuleNotFoundError", proc.stderr)
            return
        self.assertIn("--explode", proc.stdout)

    def test_cleaned_stls_exist_and_keep_lock_bbox(self):
        for part in PARTS:
            path = PRINT_STL / f"{part}.stl"
            self.assertTrue(path.is_file(), f"missing {path}")
            count, mn, mx = _read_binary_stl(path)
            self.assertGreater(count, 10, part)
            exp_min, exp_max, tol = BBOX[part]
            for i, axis in enumerate("xyz"):
                self.assertAlmostEqual(mn[i], exp_min[i], delta=tol, msg=f"{part} min {axis}")
                self.assertAlmostEqual(mx[i], exp_max[i], delta=tol, msg=f"{part} max {axis}")

    def test_faceted_step_and_obj(self):
        for part in PARTS:
            step = PRINT_STEP / f"{part}.step"
            obj = PRINT_OBJ / f"{part}.obj"
            self.assertTrue(step.is_file(), step)
            text = step.read_text(encoding="ascii", errors="replace")
            self.assertTrue(text.startswith("ISO-10303-21;"), part)
            self.assertIn("END-ISO-10303-21;", text)
            self.assertIn("SI_UNIT(.MILLI.,.METRE.)", text)
            self.assertIn("PLACEHOLDER", text)
            self.assertTrue(obj.is_file(), obj)
            self.assertIn("v ", obj.read_text(encoding="ascii", errors="replace")[:4000])

    def test_assembly_glb_is_binary_gltf(self):
        data = PREVIEW.read_bytes()
        self.assertGreater(len(data), 200)
        self.assertEqual(data[:4], b"glTF")

    def test_readme_points_at_the_shared_lock(self):
        readme = README.read_text(encoding="utf-8")
        self.assertIn("face_spec.py", readme)
        self.assertIn("face_lock.scad", readme)
        self.assertIn("not a verified ap1 drop-in", readme.lower())
        self.assertNotIn("blender --background", readme.lower())
        self.assertIn("mesh_export.py", readme)


if __name__ == "__main__":
    unittest.main()
