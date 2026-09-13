#!/usr/bin/env python3
"""Clean the one-body replace-face STLs and export printables — no Blender.

    uv run --extra cad python cad/replace_face/mesh_export.py [--explode MM]

Per part (tray and web are never merged):

- millimetre units, origin untouched (face parts: bottom-left of the face
  box; buttons: local SCAD origin)
- merge duplicate vertices, drop degenerate / duplicate faces, fix winding
- refuse to write a part that is not watertight
- ``print/stl``  binary STL      ``print/obj`` Wavefront OBJ
- ``print/step`` faceted STEP (honest tessellation, not a B-rep rebuild)
- ``preview/assembly.glb`` coloured, exploded stack, placed from the
  ``echo_placement()`` lines that ``assembly.scad`` prints

OpenSCAD (``face_lock.scad`` ← ``src/face_spec.py``) stays the source of
truth. Callipers are still PLACEHOLDER. Not a verified AP1 drop-in.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent
RAW_STL = HERE / "stl"
PRINT_STL = HERE / "print" / "stl"
PRINT_STEP = HERE / "print" / "step"
PRINT_OBJ = HERE / "print" / "obj"
PREVIEW = HERE / "preview"

FACE_PARTS = ("backlight", "backlight_web", "acrylic_face")
BUTTON_PARTS = ("button_rocker", "button_sel", "button_trip")
PARTS = FACE_PARTS + BUTTON_PARTS

COLOURS: dict[str, tuple[int, int, int, int]] = {
    "backlight": (56, 56, 61, 255),
    "panel": (30, 36, 46, 255),
    "backlight_web": (140, 133, 122, 255),
    "acrylic_face": (209, 204, 189, 140),
    "button_rocker": (30, 30, 30, 255),
    "button_sel": (30, 30, 30, 255),
    "button_trip": (30, 30, 30, 255),
}


class MeshExportError(RuntimeError):
    """A part failed cleaning or the OpenSCAD placement echo was unreadable."""


# --- cleaning ---------------------------------------------------------------------
def clean(mesh: trimesh.Trimesh, name: str) -> trimesh.Trimesh:
    before = (len(mesh.vertices), len(mesh.faces))
    mesh = mesh.copy()
    mesh.merge_vertices()
    mesh.update_faces(mesh.nondegenerate_faces())
    mesh.update_faces(mesh.unique_faces())
    mesh.remove_unreferenced_vertices()
    trimesh.repair.fix_normals(mesh)
    if not mesh.is_watertight:
        trimesh.repair.fill_holes(mesh)
    if not mesh.is_watertight:
        raise MeshExportError(f"{name}: not watertight after clean (v/f {before} → {len(mesh.vertices)}/{len(mesh.faces)})")
    if mesh.volume <= 0:
        raise MeshExportError(f"{name}: non-positive volume {mesh.volume:.3f}")
    print(f"  {name}: v/f {before[0]}/{before[1]} → {len(mesh.vertices)}/{len(mesh.faces)}, vol {mesh.volume:.0f} mm³, bbox {np.round(mesh.extents, 1).tolist()}")
    return mesh


# --- faceted STEP -----------------------------------------------------------------
def _real(value: float) -> str:
    text = f"{value:.6f}".rstrip("0").rstrip(".")
    if text in {"-0", ""}:
        return "0."
    return text if "." in text else text + "."


def write_faceted_step(path: Path, mesh: trimesh.Trimesh, part: str) -> None:
    """Millimetre FACETED_BREP STEP — the printable's triangles, nothing more."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [
        "ISO-10303-21;",
        "HEADER;",
        "FILE_DESCRIPTION(('replace-face cleaned mesh - faceted PLACEHOLDER, not parametric CAD, not a verified AP1 drop-in'),'2;1');",
        f"FILE_NAME('{path.name}','{now}',('s2000-ap1-digital-dash'),(''),'cad/replace_face/mesh_export.py','s2000-ap1-digital-dash','');",
        "FILE_SCHEMA(('CONFIG_CONTROL_DESIGN'));",
        "ENDSEC;",
        "DATA;",
        "#1=APPLICATION_CONTEXT('configuration controlled 3d designs of mechanical parts and assemblies');",
        "#2=APPLICATION_PROTOCOL_DEFINITION('international standard','config_control_design',1994,#1);",
        "#3=PRODUCT_CONTEXT('',#1,'mechanical');",
        f"#4=PRODUCT('{part}','{part}','PLACEHOLDER faceted mesh - OpenSCAD remains source of truth',(#3));",
        "#5=PRODUCT_DEFINITION_FORMATION('','',#4);",
        "#6=PRODUCT_DEFINITION_CONTEXT('part definition',#1,'design');",
        "#7=PRODUCT_DEFINITION('design','',#5,#6);",
        "#8=PRODUCT_RELATED_PRODUCT_CATEGORY('part',$,(#4));",
        "#9=PRODUCT_DEFINITION_SHAPE('','',#7);",
        "#10=(LENGTH_UNIT()NAMED_UNIT(*)SI_UNIT(.MILLI.,.METRE.));",
        "#11=(NAMED_UNIT(*)PLANE_ANGLE_UNIT()SI_UNIT($,.RADIAN.));",
        "#12=(NAMED_UNIT(*)SI_UNIT($,.STERADIAN.)SOLID_ANGLE_UNIT());",
        "#13=UNCERTAINTY_MEASURE_WITH_UNIT(LENGTH_MEASURE(1.E-6),#10,'distance_accuracy_value','confusion accuracy');",
        "#14=(GEOMETRIC_REPRESENTATION_CONTEXT(3)GLOBAL_UNCERTAINTY_ASSIGNED_CONTEXT((#13))GLOBAL_UNIT_ASSIGNED_CONTEXT((#10,#11,#12))REPRESENTATION_CONTEXT('Context #1','3D Context with UNIT and UNCERTAINTY'));",
    ]
    eid = 20
    verts = mesh.vertices
    point_ids: list[int] = []
    for x, y, z in verts:
        lines.append(f"#{eid}=CARTESIAN_POINT('',({_real(x)},{_real(y)},{_real(z)}));")
        point_ids.append(eid)
        eid += 1
    face_ids: list[int] = []
    for (a, b, c), n in zip(mesh.faces, mesh.face_normals):
        pa = verts[a]
        u = verts[b] - pa
        ulen = float(np.linalg.norm(u))
        if ulen < 1e-9:
            continue
        r = u / ulen
        ids = {}
        for key, text in (
            ("o", f"CARTESIAN_POINT('',({_real(pa[0])},{_real(pa[1])},{_real(pa[2])}))"),
            ("n", f"DIRECTION('',({_real(n[0])},{_real(n[1])},{_real(n[2])}))"),
            ("r", f"DIRECTION('',({_real(r[0])},{_real(r[1])},{_real(r[2])}))"),
        ):
            lines.append(f"#{eid}={text};")
            ids[key] = eid
            eid += 1
        lines.append(f"#{eid}=AXIS2_PLACEMENT_3D('',#{ids['o']},#{ids['n']},#{ids['r']});")
        axis = eid
        eid += 1
        lines.append(f"#{eid}=PLANE('',#{axis});")
        plane = eid
        eid += 1
        lines.append(f"#{eid}=POLY_LOOP('',(#{point_ids[a]},#{point_ids[b]},#{point_ids[c]}));")
        loop = eid
        eid += 1
        lines.append(f"#{eid}=FACE_OUTER_BOUND('',#{loop},.T.);")
        bound = eid
        eid += 1
        lines.append(f"#{eid}=FACE_SURFACE('',(#{bound}),#{plane},.T.);")
        face_ids.append(eid)
        eid += 1
    shell = eid
    lines.append(f"#{shell}=CLOSED_SHELL('',({','.join(f'#{i}' for i in face_ids)}));")
    eid += 1
    lines.append(f"#{eid}=FACETED_BREP('{part}',#{shell});")
    brep = eid
    eid += 1
    lines.append(f"#{eid}=ADVANCED_BREP_SHAPE_REPRESENTATION('',(#{brep}),#14);")
    rep = eid
    eid += 1
    lines.append(f"#{eid}=SHAPE_DEFINITION_REPRESENTATION(#9,#{rep});")
    lines += ["ENDSEC;", "END-ISO-10303-21;"]
    path.write_text("\n".join(lines) + "\n", encoding="ascii")


# --- placement from OpenSCAD -----------------------------------------------------
_PLACE = re.compile(r'ECHO: place = \["([a-z_]+)", ([-\d.e]+), ([-\d.e]+), ([-\d.e]+)\]')
_PANEL = re.compile(r"ECHO: panel_box = \[([-\d.e]+), ([-\d.e]+), ([-\d.e]+), ([-\d.e]+), ([-\d.e]+)\]")


def read_placement(explode: float) -> tuple[dict[str, np.ndarray], tuple[float, ...]]:
    scad = shutil.which("openscad")
    if scad is None:
        raise MeshExportError("openscad not on PATH")
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "placement.echo"
        proc = subprocess.run(
            [scad, "-o", str(out), "-D", "print_placement=true", "-D", f"explode={explode}", str(HERE / "assembly.scad")],
            capture_output=True,
            text=True,
            check=False,
        )
        text = (out.read_text(encoding="utf-8") if out.exists() else "") + proc.stdout + proc.stderr
    places = {m.group(1): np.array([float(m.group(2)), float(m.group(3)), float(m.group(4))]) for m in _PLACE.finditer(text)}
    panel = _PANEL.search(text)
    missing = [p for p in PARTS if p not in places]
    if missing or panel is None:
        raise MeshExportError(f"placement echo missing {missing or 'panel_box'}:\n{text[-800:]}")
    return places, tuple(float(v) for v in panel.groups())


def _paint(mesh: trimesh.Trimesh, rgba: tuple[int, int, int, int]) -> trimesh.visual.ColorVisuals:
    """Flat vertex colour (face colours would pull in scipy for the GLB writer)."""
    return trimesh.visual.ColorVisuals(mesh, vertex_colors=np.tile(np.array(rgba, dtype=np.uint8), (len(mesh.vertices), 1)))


def export_glb(meshes: dict[str, trimesh.Trimesh], explode: float) -> Path:
    places, panel = read_placement(explode)
    scene = trimesh.Scene()
    for name, mesh in meshes.items():
        m = mesh.copy()
        m.visual = _paint(m, COLOURS[name])
        m.apply_translation(places[name])
        scene.add_geometry(m, node_name=name, geom_name=name)
    px, py, pw, ph, pt = panel
    slab = trimesh.creation.box(extents=(pw, ph, pt))
    slab.apply_translation((px + pw / 2, py + ph / 2, pt / 2))
    slab.apply_translation(places["panel"])
    slab.visual = _paint(slab, COLOURS["panel"])
    scene.add_geometry(slab, node_name="panel_placeholder", geom_name="panel_placeholder")
    PREVIEW.mkdir(parents=True, exist_ok=True)
    out = PREVIEW / "assembly.glb"
    scene.export(out)
    return out


def run(explode: float) -> int:
    for d in (PRINT_STL, PRINT_STEP, PRINT_OBJ):
        d.mkdir(parents=True, exist_ok=True)
    meshes: dict[str, trimesh.Trimesh] = {}
    print("clean")
    for part in PARTS:
        src = RAW_STL / f"{part}.stl"
        if not src.exists():
            raise MeshExportError(f"missing {src} — run export.sh first")
        loaded = trimesh.load_mesh(src, force="mesh")
        if isinstance(loaded, trimesh.Scene):
            loaded = trimesh.util.concatenate(tuple(loaded.geometry.values()))
        mesh = clean(loaded, part)
        mesh.export(PRINT_STL / f"{part}.stl", file_type="stl")
        mesh.export(PRINT_OBJ / f"{part}.obj", file_type="obj", include_color=False, include_normals=False, include_texture=False)
        write_faceted_step(PRINT_STEP / f"{part}.step", mesh, part)
        meshes[part] = mesh
    out = export_glb(meshes, explode)
    print(f"preview {out.relative_to(HERE.parents[1])} (explode {explode:g} mm)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--explode", type=float, default=14.0, help="mm of air between layers in the GLB preview")
    args = ap.parse_args()
    try:
        return run(args.explode)
    except MeshExportError as exc:
        print(f"mesh_export: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
