"""OEM-style 7-segment LCD digits — mitred segments, red backlit windows.

The S2000 speed / odo digits are classic LCD sevens: straight segments that
meet at 45° mitres with hairline gaps, upright (no italic), a wide 0.58:1
digit box and a stroke ~15 % of the digit height. Unlit segments are all
but invisible on the OEM glass, so the ghost tint stays a whisper above
the window colour. Display only — protocol field names are unchanged.
"""
from __future__ import annotations

from typing import Iterable

# Standard 7-seg names: A top, B UR, C LR, D bot, E LL, F UL, G mid
SEGMENTS = "abcdefg"

DIGIT_SEGS: dict[str, str] = {
    "0": "abcdef",
    "1": "bc",
    "2": "abged",
    "3": "abcdg",
    "4": "bcfg",
    "5": "acdfg",
    "6": "acdefg",
    "7": "abc",
    "8": "abcdefg",
    "9": "abcdfg",
    "-": "g",
    " ": "",
    ".": "",
}

DIGIT_W_RATIO = 0.58     # OEM digit box width / height
DIGIT_GAP_RATIO = 0.20   # gap between digit boxes / height
STROKE_RATIO = 0.155     # segment thickness / height
SEG_GAP_RATIO = 0.016    # hairline between segments / height
CORNER_RATIO = 0.045     # outer-corner chamfer / height (reads as rounded)


def segs_for(ch: str) -> str:
    return DIGIT_SEGS.get(ch, "")


def ghost_pattern(width: int, fill: str = "8") -> str:
    """Unlit 7-seg silhouette (OEM self-test is 188 / 888888 / 888.8)."""
    return fill * max(0, width)


def segment_polys(x: int, y: int, w: int, h: int) -> dict[str, list[tuple[int, int]]]:
    """Pixel polygons for one digit. Origin is top-left of the digit box.

    Horizontal segments are trapezoids, verticals are pentagons whose
    inner ends taper to a point at the middle bar, and the middle bar is a
    hexagon — all mitred at 45° with a hairline gap like the OEM glass.
    """
    t = max(2.0, h * STROKE_RATIO)
    g = max(0.8, h * SEG_GAP_RATIO)
    c = max(0.0, h * CORNER_RATIO)
    ym = y + h / 2.0
    xr = x + w
    yb = y + h
    raw: dict[str, list[tuple[float, float]]] = {
        "a": [(x + g + c, y), (xr - g - c, y), (xr - t - g, y + t), (x + t + g, y + t)],
        "d": [(x + t + g, yb - t), (xr - t - g, yb - t), (xr - g - c, yb), (x + g + c, yb)],
        "f": [
            (x, y + g + c),
            (x + t, y + t + g),
            (x + t, ym - t / 2.0 - g),
            (x + t / 2.0, ym - g),
            (x, ym - t / 2.0 - g),
        ],
        "b": [
            (xr, y + g + c),
            (xr, ym - t / 2.0 - g),
            (xr - t / 2.0, ym - g),
            (xr - t, ym - t / 2.0 - g),
            (xr - t, y + t + g),
        ],
        "e": [
            (x, ym + t / 2.0 + g),
            (x + t / 2.0, ym + g),
            (x + t, ym + t / 2.0 + g),
            (x + t, yb - t - g),
            (x, yb - g - c),
        ],
        "c": [
            (xr - t / 2.0, ym + g),
            (xr, ym + t / 2.0 + g),
            (xr, yb - g - c),
            (xr - t, yb - t - g),
            (xr - t, ym + t / 2.0 + g),
        ],
        "g": [
            (x + t / 2.0 + g, ym),
            (x + t + g, ym - t / 2.0),
            (xr - t - g, ym - t / 2.0),
            (xr - t / 2.0 - g, ym),
            (xr - t - g, ym + t / 2.0),
            (x + t + g, ym + t / 2.0),
        ],
    }
    return {
        name: [(int(round(px)), int(round(py))) for px, py in pts]
        for name, pts in raw.items()
    }


def _expand(pts: list[tuple[int, int]], px: float) -> list[tuple[int, int]]:
    cx = sum(p[0] for p in pts) / len(pts)
    cy = sum(p[1] for p in pts) / len(pts)
    out: list[tuple[int, int]] = []
    for x, y in pts:
        dx, dy = x - cx, y - cy
        n = (dx * dx + dy * dy) ** 0.5 or 1.0
        out.append((int(x + dx / n * px), int(y + dy / n * px)))
    return out


def draw_digit(
    pygame,
    dest,
    ch: str,
    box: tuple[int, int, int, int],
    color: tuple[int, int, int],
    ghost: tuple[int, int, int] | None,
    bloom=None,
) -> None:
    x, y, w, h = box
    polys = segment_polys(x, y, w, h)
    lit = set(segs_for(ch))
    if ghost is not None:
        for pts in polys.values():
            pygame.draw.polygon(dest, ghost, pts)
    for name, pts in polys.items():
        if name not in lit:
            continue
        if bloom is not None:
            glow = (
                min(255, color[0] + 20),
                min(255, color[1] + 24),
                min(255, color[2] + 10),
                44,
            )
            pygame.draw.polygon(bloom, glow, _expand(pts, max(2, h * 0.04)))
        pygame.draw.polygon(dest, color, pts)


def digit_metrics(digit_h: int) -> tuple[int, int, int]:
    """(digit width, gap, decimal-point gutter) for a digit height."""
    dw = max(6, int(round(digit_h * DIGIT_W_RATIO)))
    gap = max(2, int(round(digit_h * DIGIT_GAP_RATIO)))
    dot = max(4, int(round(digit_h * 0.22)))
    return dw, gap, dot


def measure_text(text: str, digit_h: int, gap: int | None = None) -> tuple[int, int]:
    """Width × height of a digit string including a decimal point gutter."""
    dw, default_gap, dot = digit_metrics(digit_h)
    gap = default_gap if gap is None else gap
    width = 0
    for ch in text:
        if ch in ".:":
            width += dot
        else:
            width += dw + gap
    if text and not text.endswith((".", ":")):
        width -= gap
    return width, digit_h


def blit_digits(
    pygame,
    dest,
    text: str,
    center: tuple[int, int],
    digit_h: int,
    color: tuple[int, int, int],
    ghost: tuple[int, int, int] | None = None,
    ghost_text: str | None = None,
    bloom: bool = False,
    italic: float = 0.0,
    align: str = "center",
    bloom_layer=None,
) -> tuple[int, int, int, int]:
    """Draw ``text`` (digits / space / minus / one '.') at ``center``.

    ``align`` is ``center`` (default), ``left`` or ``right`` and applies to
    the x of ``center``; y is always the vertical centre. Returns the
    bounding rect (x, y, w, h). ``ghost_text`` defaults to eights so unused
    digits keep the OEM 188 / 888888 / 888.8 silhouette.

    Pass ``bloom_layer`` to batch a glow layer. Off by default: the cluster
    is an LCD, so software bloom just smears the digits.
    """
    dw, gap, dot = digit_metrics(digit_h)
    total_w, _ = measure_text(text, digit_h, gap)
    cx, cy = center
    if align == "left":
        x0 = cx
    elif align == "right":
        x0 = cx - total_w
    else:
        x0 = cx - total_w // 2
    y0 = cy - digit_h // 2
    own_layer = None
    layer = bloom_layer
    if layer is None and bloom:
        own_layer = pygame.Surface(dest.get_size(), pygame.SRCALPHA)
        layer = own_layer

    gtext = ghost_text if ghost_text is not None else "".join(
        ch if ch in ".:" else "8" for ch in text
    )
    if len(gtext) < len(text):
        gtext = gtext.ljust(len(text))
    elif len(gtext) > len(text):
        gtext = gtext[: len(text)]

    x = x0
    shear = int((0.5 * digit_h) * italic)
    for i, ch in enumerate(text):
        if ch in ".:":
            side = max(2, int(digit_h * STROKE_RATIO * 0.9))
            px = x + (dot - side) // 2
            if ch == ".":
                tops = (y0 + digit_h - side,)
            else:  # colon: two squares straddling the digit's middle bar
                tops = (y0 + int(digit_h * 0.28) - side // 2, y0 + int(digit_h * 0.72) - side // 2)
            for py in tops:
                rect = pygame.Rect(px, py, side, side)
                if ghost is not None:
                    pygame.draw.rect(dest, ghost, rect)
                pygame.draw.rect(dest, color, rect)
                if layer is not None:
                    pygame.draw.rect(layer, (*color, 44), rect.inflate(side, side))
            x += dot
            continue
        box = (x + shear, y0, dw, digit_h)
        if ghost is not None:
            draw_digit(pygame, dest, gtext[i], box, ghost, ghost=None, bloom=None)
        draw_digit(pygame, dest, ch, box, color, ghost=None, bloom=layer)
        x += dw + gap

    if own_layer is not None:
        composite_bloom(pygame, dest, own_layer)

    return (x0, y0, total_w, digit_h)


def composite_bloom(pygame, dest, layer, shrink: int = 2) -> None:
    """Cheap blur: downscale the glow layer and stretch it back over ``dest``."""
    if layer is None:
        return
    w, h = dest.get_size()
    small = pygame.transform.smoothscale(layer, (max(1, w // shrink), max(1, h // shrink)))
    dest.blit(pygame.transform.smoothscale(small, (w, h)), (0, 0))


def lcd_window(
    pygame,
    dest,
    rect: tuple[int, int, int, int],
    wash,
    edge,
    door: tuple[int, int, int, int] = (255, 48, 32, 12),
    radius: int = 6,
) -> None:
    """Recessed red-backlit LCD window: dark rim, maroon glass, soft top fade."""
    x, y, w, h = rect
    pygame.draw.rect(dest, (14, 4, 4), pygame.Rect(x - 2, y - 2, w + 4, h + 4), border_radius=radius + 2)
    pygame.draw.rect(dest, wash, pygame.Rect(x, y, w, h), border_radius=radius)
    glass = pygame.Surface((w, h), pygame.SRCALPHA)
    # Backlight is brightest low-centre on the OEM glass; fade the top.
    steps = max(4, h // 6)
    for i in range(steps):
        t = i / max(1, steps - 1)
        alpha = int(70 * (1.0 - t) ** 1.6)
        band_h = max(1, h // steps + 1)
        pygame.draw.rect(glass, (0, 0, 0, alpha), pygame.Rect(0, int(t * (h - band_h)), w, band_h))
    for i in range(0, w, 3):
        pygame.draw.line(glass, door, (i, 0), (i, h))
    mask = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(mask, (255, 255, 255, 255), pygame.Rect(0, 0, w, h), border_radius=radius)
    glass.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    dest.blit(glass, (x, y))
    pygame.draw.rect(dest, edge, pygame.Rect(x, y, w, h), width=1, border_radius=radius)


def iter_lit_cells(text: str) -> Iterable[str]:
    for ch in text:
        yield segs_for(ch)
