"""Reference-plate tach alphabet shared with the SVG renderer."""
import io
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "assets/fonts/oem-tach"
_CACHE = {}


def glyph(pygame, key: str, height: int, color):
    cache_key = (key, height, tuple(color))
    if cache_key not in _CACHE:
        rgb = "#%02x%02x%02x" % tuple(color[:3])
        svg = (ROOT / f"{key}.svg").read_text().replace("currentColor", rgb)
        source = pygame.image.load(io.BytesIO(svg.encode()), "glyph.svg")
        width = max(1, round(height * source.get_width() / source.get_height()))
        _CACHE[cache_key] = pygame.transform.smoothscale(source, (width, max(1, height)))
    return _CACHE[cache_key]
