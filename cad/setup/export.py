#!/usr/bin/env python3
"""Export the digital bench setup: prototype STLs + assembled/exploded GLBs.
Run: uv run --extra cad python cad/setup/export.py
SCAD is the source of solid geometry. GLB uses metres, +Y up, +Z to driver.
"""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile

import numpy as np
from PIL import Image
import trimesh

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
WEB = ROOT / 'apps/harness/public/models'
PRINT = ('bezel', 'enclosure', 'rear_cover', 'carrier')
LAYERS = {
    'bezel': (1.3, '#28282c'), 'enclosure': (0, '#46464c'),
    'rear_cover': (-1.8, '#888780'), 'carrier': (-1.2, '#c68a32'),
    'oled': (.65, '#262631'), 'screen': (.65, '#ffffff'),
    'pi_board': (-.65, '#287c51'), 'ports': (-.65, '#b7bec3'),
    'gpio': (-.65, '#242424'), 'cooler': (-.65, '#8d9b9f'),
    'driver_board': (-.65, '#27526a'),
}


def body_count(mesh):
    # Vertex connectivity without optional scipy/networkx dependencies.
    parents = list(range(len(mesh.vertices)))
    def root(i):
        while parents[i] != i:
            parents[i] = parents[parents[i]]
            i = parents[i]
        return i
    for a, b, c in mesh.faces:
        parents[root(b)] = root(a)
        parents[root(c)] = root(a)
    return len({root(i) for i in range(len(parents))})


def run():
    if not shutil.which('openscad'):
        raise SystemExit('OpenSCAD is required')
    WEB.mkdir(parents=True, exist_ok=True)
    (HERE / 'print').mkdir(exist_ok=True)
    meshes = {}
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        def render(name):
            path = tmp / f'{name}.stl'
            subprocess.run(['openscad', '--export-format=binstl', '-o', str(path),
                            '-D', f'part="{name}"', str(HERE / 'setup.scad')],
                           check=True, capture_output=True)
            mesh = trimesh.load_mesh(path)
            if not mesh.is_watertight or mesh.volume <= 0:
                raise ValueError(f'{name}: invalid solid')
            if name in PRINT and body_count(mesh) != 1:
                raise ValueError(f'{name}: disconnected printable')
            return name, mesh
        with ThreadPoolExecutor(max_workers=4) as pool:
            meshes = dict(pool.map(render, LAYERS))
        subprocess.run([sys.executable, str(ROOT / 'src/gauge_ui.py'), '--smoke',
                        '--car', '--size', '1280x720', '--screenshot', str(tmp / 'face')],
                       check=True, capture_output=True,
                       env={**os.environ, 'SDL_VIDEODRIVER': 'dummy', 'SDL_AUDIODRIVER': 'dummy'})
        texture = Image.open(tmp / 'face/05_cruise.png').convert('RGB')
        reports = []
        for name in PRINT:
            mesh = meshes[name].copy()
            bounds = mesh.bounds.copy()
            mesh.apply_translation([0, 0, -bounds[0, 2]])
            mesh.export(HERE / 'print' / f'{name}.stl')
            reports.append({'part': name, 'extent_mm': np.round(mesh.extents, 2).tolist(),
                            'watertight': bool(mesh.is_watertight), 'bodies': 1})
        for mode, spacing in [('assembled', 0), ('exploded', 40), ('electronics', 0)]:
            scene = trimesh.Scene()
            for name, (factor, colour) in LAYERS.items():
                if mode == "electronics" and name in ("bezel", "enclosure", "rear_cover", "oled", "screen"):
                    continue
                mesh = meshes[name].copy()
                if name == 'screen':
                    # Only the front plane receives the instrument texture.
                    x0, y0, _ = mesh.bounds[0]
                    x1, y1, z = mesh.bounds[1]
                    mesh = trimesh.Trimesh(vertices=[[x0,y0,z],[x1,y0,z],[x1,y1,z],[x0,y1,z]],
                                           faces=[[0,1,2],[0,2,3]], process=False)
                    material = trimesh.visual.material.PBRMaterial(
                        baseColorTexture=texture, emissiveTexture=texture,
                        emissiveFactor=[.65,.65,.65], metallicFactor=0, roughnessFactor=1)
                    mesh.visual = trimesh.visual.texture.TextureVisuals(
                        uv=[[0,0],[1,0],[1,1],[0,1]], material=material)
                else:
                    rgba = [int(colour[i:i+2],16) for i in (1,3,5)] + [255]
                    mesh.visual = trimesh.visual.ColorVisuals(mesh, vertex_colors=np.tile(rgba,(len(mesh.vertices),1)))
                mesh.apply_translation([0,0,spacing*factor])
                mesh.apply_scale(.001)
                scene.add_geometry(mesh, node_name=name, geom_name=name)
            scene.export(WEB / f'setup-{mode}.glb')
        (HERE / 'manifest.json').write_text(json.dumps({'units':'mm','prototype':True,'parts':reports},indent=2)+'\n')
        with zipfile.ZipFile(WEB / 'setup-prototype.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
            for path in [HERE / 'setup.scad', HERE / 'README.md', HERE / 'manifest.json', *(HERE / 'print').glob('*.stl')]:
                archive.write(path, path.relative_to(HERE))
    print(json.dumps(reports, indent=2))


if __name__ == '__main__':
    run()
