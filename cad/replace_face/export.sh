#!/usr/bin/env bash
# Regenerate the replace-face stack from the shared face lock:
#   1. src/face_spec.py  → face_lock.scad (+ apps/harness/lib/faceSpec.json)
#   2. OpenSCAD          → stl/*.stl        (one SCAD → one solid)
#   3. mesh_export.py    → print/{stl,obj,step}/*, preview/assembly.glb
# Requires OpenSCAD (xvfb-run on headless boxes) and uv.
set -euo pipefail
cd "$(dirname "$0")"
ROOT=$(cd ../.. && pwd)
mkdir -p stl

echo "lock: src/face_spec.py"
(cd "$ROOT" && uv run python src/face_spec.py >/dev/null)

run_scad() {
    local src=$1
    local dst=$2
    echo "export $src -> stl/$dst"
    if command -v xvfb-run >/dev/null 2>&1; then
        xvfb-run -a openscad --export-format=binstl -o "stl/$dst" "$src"
    else
        openscad --export-format=binstl -o "stl/$dst" "$src"
    fi
}

run_scad backlight.scad backlight.stl
run_scad backlight_web.scad backlight_web.stl
run_scad acrylic_face.scad acrylic_face.stl
run_scad button_rocker.scad button_rocker.stl
run_scad button_sel.scad button_sel.stl
run_scad button_trip.scad button_trip.stl

(cd "$ROOT" && uv run --extra cad python cad/replace_face/mesh_export.py "$@")
echo "done"
