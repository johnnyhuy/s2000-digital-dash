"""Validate shipped 3D payloads without requiring OpenSCAD in CI."""
from collections import Counter
import json
from pathlib import Path
import struct
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[1]
CAD = ROOT / 'cad/setup'
WEB = ROOT / 'apps/harness/public/models'


def glb(mode):
    data = (WEB / f'setup-{mode}.glb').read_bytes()
    magic, version, size = struct.unpack_from('<4sII', data)
    assert magic == b'glTF' and version == 2 and size == len(data)
    count, kind = struct.unpack_from('<I4s', data, 12)
    assert kind == b'JSON'
    return json.loads(data[20:20+count])


@pytest.mark.parametrize('mode', ['assembled', 'exploded', 'electronics'])
def test_web_models_are_self_contained_metre_scale_scenes(mode):
    scene = glb(mode)
    names = {n.get('name') for n in scene['nodes']}
    assert {'carrier', 'pi_board', 'ports', 'gpio', 'cooler', 'driver_board'} <= names
    if mode != 'electronics':
        assert {'screen', 'oled', 'bezel', 'rear_cover', 'enclosure'} <= names
        assert scene['images'] and all('bufferView' in image for image in scene['images'])
    else:
        assert 'enclosure' not in names  # inspection mode actually exposes components
    assert all('uri' not in buffer for buffer in scene['buffers'])
    for mesh in scene['meshes']:
        a = scene['accessors'][mesh['primitives'][0]['attributes']['POSITION']]
        assert all(abs(v) < .5 for v in a['min'] + a['max']), 'Expected metre-scale model'


@pytest.mark.parametrize('part', ['bezel', 'enclosure', 'rear_cover', 'carrier'])
def test_prototype_printables_are_closed_and_rest_on_build_plate(part):
    data = (CAD / 'print' / f'{part}.stl').read_bytes()
    count = struct.unpack_from('<I', data, 80)[0]
    assert len(data) == 84 + count * 50
    edges = Counter()
    heights = []
    for i in range(count):
        f = struct.unpack_from('<12f', data, 84 + i * 50)
        triangle = [tuple(f[k:k+3]) for k in (3, 6, 9)]
        heights += [p[2] for p in triangle]
        for j in range(3):
            edges[tuple(sorted((triangle[j], triangle[(j+1)%3])))] += 1
    assert min(heights) == pytest.approx(0, abs=1e-5)
    assert all(n == 2 for n in edges.values()), 'Non-manifold or open STL edge'


def test_download_bundle_matches_sources():
    with zipfile.ZipFile(WEB / 'setup-prototype.zip') as archive:
        for path in [CAD / 'README.md', CAD / 'setup.scad', CAD / 'manifest.json', *(CAD / 'print').glob('*.stl')]:
            assert archive.read(str(path.relative_to(CAD))) == path.read_bytes()
