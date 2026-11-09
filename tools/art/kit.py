"""Small vector-drawing kit for flat cartoon artwork.

Everything is drawn at ``SS`` x resolution and downsampled for smooth edges.
Coordinates passed to the kit are in final canvas pixels (1024 x 1024).
All body colours are opaque; only the ground shadow is translucent (pure
black, low alpha) so the app can separate it from the character.
"""

import math
from dataclasses import dataclass, field

from PIL import Image, ImageDraw

CANVAS = 1024
SS = 2
GROUND = 900  # y of the ground line in the canvas

OUTLINE = (42, 34, 48, 255)
WHITE = (255, 255, 255, 255)
EYE_DARK = (40, 32, 44, 255)
BLUSH = (255, 160, 170, 255)
TEAR = (120, 190, 255, 255)
HEART = (240, 70, 100, 255)
GOLD = (255, 205, 60, 255)
MARK = (110, 120, 150, 255)  # motion / sound marks
ZZZ = (90, 110, 240, 255)
SHADOW_ALPHA = 42

Point = tuple[float, float]


def rgb(hex_colour: str) -> tuple[int, int, int, int]:
    h = hex_colour.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 255


def shade(colour, factor: float):
    r, g, b, a = colour
    return (round(r * factor), round(g * factor), round(b * factor), a)


def rot(p: Point, angle_deg: float, origin: Point = (0.0, 0.0)) -> Point:
    """Rotate ``p`` around ``origin``; positive = clockwise on screen."""
    a = math.radians(angle_deg)
    x, y = p[0] - origin[0], p[1] - origin[1]
    return origin[0] + x * math.cos(a) - y * math.sin(a), origin[1] + x * math.sin(a) + y * math.cos(a)


def direction(angle_deg: float) -> Point:
    """Unit vector: 0 = straight down, +90 = forward (+x), 180 = up."""
    a = math.radians(angle_deg)
    return math.sin(a), math.cos(a)


def along(p: Point, angle_deg: float, length: float) -> Point:
    dx, dy = direction(angle_deg)
    return p[0] + dx * length, p[1] + dy * length


def lerp(a: Point, b: Point, t: float) -> Point:
    return a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t


def bezier(points: list[Point], steps: int = 24) -> list[Point]:
    """Quadratic/cubic Bezier through control points."""
    out = []
    for i in range(steps + 1):
        t = i / steps
        pts = list(points)
        while len(pts) > 1:
            pts = [lerp(pts[j], pts[j + 1], t) for j in range(len(pts) - 1)]
        out.append(pts[0])
    return out


def ellipse_points(cx, cy, rx, ry, angle=0.0, start=0.0, end=360.0, steps=72) -> list[Point]:
    pts = []
    for i in range(steps + 1):
        a = math.radians(start + (end - start) * i / steps)
        p = (cx + rx * math.cos(a), cy + ry * math.sin(a))
        pts.append(rot(p, angle, (cx, cy)) if angle else p)
    return pts


def rounded_rect_points(cx, cy, w, h, r, angle=0.0, origin: Point | None = None) -> list[Point]:
    r = min(r, w / 2, h / 2)
    pts = []
    corners = [
        (cx + w / 2 - r, cy - h / 2 + r, -90, 0),
        (cx + w / 2 - r, cy + h / 2 - r, 0, 90),
        (cx - w / 2 + r, cy + h / 2 - r, 90, 180),
        (cx - w / 2 + r, cy - h / 2 + r, 180, 270),
    ]
    for ccx, ccy, a0, a1 in corners:
        for i in range(9):
            a = math.radians(a0 + (a1 - a0) * i / 8)
            pts.append((ccx + r * math.cos(a), ccy + r * math.sin(a)))
    o = origin or (cx, cy)
    return [rot(p, angle, o) for p in pts] if angle else pts


def trapezoid_points(top: Point, bottom: Point, w_top: float, w_bottom: float, r: float = 0.0) -> list[Point]:
    """Quad from a centre line (top -> bottom) with widths at each end."""
    dx, dy = bottom[0] - top[0], bottom[1] - top[1]
    length = math.hypot(dx, dy) or 1.0
    nx, ny = -dy / length, dx / length
    pts = [
        (top[0] + nx * w_top / 2, top[1] + ny * w_top / 2),
        (bottom[0] + nx * w_bottom / 2, bottom[1] + ny * w_bottom / 2),
        (bottom[0] - nx * w_bottom / 2, bottom[1] - ny * w_bottom / 2),
        (top[0] - nx * w_top / 2, top[1] - ny * w_top / 2),
    ]
    return rounded_polygon(pts, r) if r else pts


def rounded_polygon(pts: list[Point], r: float, steps: int = 6) -> list[Point]:
    """Round the corners of a convex-ish polygon."""
    out = []
    n = len(pts)
    for i in range(n):
        p0, p1, p2 = pts[i - 1], pts[i], pts[(i + 1) % n]
        d0 = math.hypot(p1[0] - p0[0], p1[1] - p0[1]) or 1
        d2 = math.hypot(p2[0] - p1[0], p2[1] - p1[1]) or 1
        rr = min(r, d0 / 2, d2 / 2)
        a = (p1[0] + (p0[0] - p1[0]) * rr / d0, p1[1] + (p0[1] - p1[1]) * rr / d0)
        b = (p1[0] + (p2[0] - p1[0]) * rr / d2, p1[1] + (p2[1] - p1[1]) * rr / d2)
        out.extend(bezier([a, p1, b], steps))
    return out


@dataclass
class Layer:
    """One drawing surface at supersampled resolution."""

    ow: float  # outline width in canvas px
    image: Image.Image = field(init=False)
    draw: ImageDraw.ImageDraw = field(init=False)

    def __post_init__(self):
        self.image = Image.new("RGBA", (CANVAS * SS, CANVAS * SS), (0, 0, 0, 0))
        self.draw = ImageDraw.Draw(self.image)

    # -- low level -----------------------------------------------------------

    @staticmethod
    def _s(pts):
        return [(x * SS, y * SS) for x, y in pts]

    def _dot(self, p: Point, r: float, fill):
        x, y = p[0] * SS, p[1] * SS
        r *= SS
        self.draw.ellipse((x - r, y - r, x + r, y + r), fill=fill)

    def _stroke(self, pts: list[Point], width: float, fill):
        if len(pts) == 1:
            self._dot(pts[0], width / 2, fill)
            return
        self.draw.line(self._s(pts), fill=fill, width=max(1, round(width * SS)), joint="curve")
        self._dot(pts[0], width / 2, fill)
        self._dot(pts[-1], width / 2, fill)

    # -- shapes ----------------------------------------------------------------

    def poly(self, pts: list[Point], fill, outline=True, ow: float | None = None):
        ow = self.ow if ow is None else ow
        if outline and ow > 0:
            self._stroke(list(pts) + [pts[0]], ow * 2, OUTLINE)
            for p in pts[:: max(1, len(pts) // 24)]:
                self._dot(p, ow, OUTLINE)
        self.draw.polygon(self._s(pts), fill=fill)

    def ellipse(self, cx, cy, rx, ry, fill, angle=0.0, outline=True, ow=None):
        self.poly(ellipse_points(cx, cy, rx, ry, angle), fill, outline, ow)

    def circle(self, cx, cy, r, fill, outline=True, ow=None):
        self.ellipse(cx, cy, r, r, fill, 0.0, outline, ow)

    def limb(self, pts: list[Point], width: float, fill, outline=True):
        """Thick stroke with round joints and caps (arms, legs, tails)."""
        if outline:
            self._stroke(pts, width + 2 * self.ow, OUTLINE)
        self._stroke(pts, width, fill)

    def limbs(self, chains: list[tuple[list[Point], float, tuple]]):
        """Several limbs sharing one outline pass (seamless joins)."""
        for pts, width, _ in chains:
            self._stroke(pts, width + 2 * self.ow, OUTLINE)
        for pts, width, fill in chains:
            self._stroke(pts, width, fill)

    def line(self, pts: list[Point], width: float, fill=OUTLINE):
        self._stroke(pts, width, fill)

    def curve(self, ctrl: list[Point], width: float, fill=OUTLINE, steps=24):
        self._stroke(bezier(ctrl, steps), width, fill)

    def arc(self, cx, cy, rx, ry, start, end, width, fill=OUTLINE, angle=0.0):
        self._stroke(ellipse_points(cx, cy, rx, ry, angle, start, end, 24), width, fill)

    def shadow(self, cx: float, rx: float, ry: float = None, cy: float = GROUND):
        ry = ry if ry is not None else rx * 0.16
        x, y = cx * SS, cy * SS
        self.draw.ellipse((x - rx * SS, y - ry * SS, x + rx * SS, y + ry * SS), fill=(0, 0, 0, SHADOW_ALPHA))

    # -- output ----------------------------------------------------------------

    def bbox(self):
        box = self.image.getchannel("A").point(lambda v: 255 if v > 128 else 0).getbbox()
        return None if box is None else tuple(v / SS for v in box)

    def offset(self, dx: float, dy: float):
        moved = Image.new("RGBA", self.image.size, (0, 0, 0, 0))
        moved.paste(self.image, (round(dx * SS), round(dy * SS)))
        self.image = moved
        self.draw = ImageDraw.Draw(self.image)


def compose(*layers: Layer) -> Image.Image:
    out = Image.new("RGBA", layers[0].image.size, (0, 0, 0, 0))
    for layer in layers:
        out.alpha_composite(layer.image)
    return out.convert("RGBa").resize((CANVAS, CANVAS), Image.Resampling.LANCZOS).convert("RGBA")


# -- symbols (drawn as shapes so no fonts are needed) ---------------------------


def heart(layer: Layer, cx, cy, size, fill=HEART):
    r = size * 0.3
    pts = ellipse_points(cx - r * 0.95, cy - r * 0.4, r, r, 0, 140, 330, 24)
    pts += ellipse_points(cx + r * 0.95, cy - r * 0.4, r, r, 0, 210, 400, 24)
    pts += [(cx, cy + size * 0.55)]
    layer.poly(pts, fill, ow=layer.ow * 0.6)


def star(layer: Layer, cx, cy, r, fill=GOLD, points=5, angle=-90.0):
    pts = []
    for i in range(points * 2):
        rr = r if i % 2 == 0 else r * 0.45
        a = math.radians(angle + i * 180 / points)
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    layer.poly(pts, fill, ow=layer.ow * 0.6)


def sparkle(layer: Layer, cx, cy, r, fill=GOLD):
    star(layer, cx, cy, r, fill, points=4, angle=0)


def letter_z(layer: Layer, x, y, size, fill=ZZZ):
    w = size * 0.12
    layer.line([(x, y), (x + size, y), (x, y + size), (x + size, y + size)], w, fill)


def zzz(layer: Layer, x, y, size=60):
    letter_z(layer, x, y, size * 0.55)
    letter_z(layer, x + size * 0.55, y - size * 0.55, size * 0.75)
    letter_z(layer, x + size * 1.25, y - size * 1.35, size)


def question(layer: Layer, x, y, size, fill=MARK):
    w = size * 0.16
    layer.curve([(x - size * 0.3, y - size * 0.2), (x - size * 0.3, y - size * 0.6), (x + size * 0.3, y - size * 0.6),
                 (x + size * 0.3, y - size * 0.15), (x, y), (x, y + size * 0.2)], w, fill)
    layer.line([(x, y + size * 0.45)], w * 1.2, fill)


def exclaim(layer: Layer, x, y, size, fill=(230, 60, 60, 255)):
    w = size * 0.18
    layer.line([(x, y - size * 0.6), (x, y + size * 0.15)], w, fill)
    layer.line([(x, y + size * 0.45)], w * 1.2, fill)


def note(layer: Layer, x, y, size, fill=(80, 90, 200, 255)):
    w = size * 0.1
    layer.ellipse(x, y, size * 0.22, size * 0.16, fill, angle=-20, outline=False)
    layer.line([(x + size * 0.19, y - size * 0.05), (x + size * 0.19, y - size * 0.8)], w, fill)
    layer.line([(x + size * 0.19, y - size * 0.8), (x + size * 0.45, y - size * 0.55)], w, fill)


def drop(layer: Layer, x, y, size, fill=TEAR):
    pts = ellipse_points(x, y, size * 0.35, size * 0.35, 0, -20, 200, 24) + [(x, y - size * 0.8)]
    layer.poly(pts, fill, ow=layer.ow * 0.5)


def anger_mark(layer: Layer, x, y, size, fill=(230, 50, 60, 255)):
    w = size * 0.14
    for a in (45, 135, 225, 315):
        p0 = rot((x + size * 0.15, y), a, (x, y))
        p1 = rot((x + size * 0.5, y), a, (x, y))
        c = rot((x + size * 0.35, y - size * 0.2), a, (x, y))
        layer.curve([p0, c, p1], w, fill)


def spiral(layer: Layer, cx, cy, r, width, fill=OUTLINE, turns=2.2):
    pts = []
    for i in range(60):
        t = i / 59
        a = t * turns * 2 * math.pi
        pts.append((cx + r * t * math.cos(a), cy + r * t * math.sin(a)))
    layer.line(pts, width, fill)


def motion_lines(layer: Layer, x, y, length, gap, count=3, width=8, fill=MARK):
    for i in range(count):
        yy = y + (i - (count - 1) / 2) * gap
        xx = x - (i % 2) * length * 0.25
        layer.line([(xx - length, yy), (xx, yy)], width, fill)


def sound_arcs(layer: Layer, x, y, size, width=8, fill=MARK, count=2, facing=1):
    for i in range(count):
        r = size * (0.5 + 0.45 * i)
        start, end = (-40, 40) if facing > 0 else (140, 220)
        layer.arc(x, y, r, r, start, end, width, fill)


def puff(layer: Layer, cx, cy, r, fill=(230, 230, 235, 255)):
    pts = []
    for i in range(8):
        a = i * 45
        pts += ellipse_points(cx + r * 0.6 * math.cos(math.radians(a)), cy + r * 0.45 * math.sin(math.radians(a)),
                              r * 0.45, r * 0.45, 0, a - 70, a + 70, 8)
    layer.poly(pts, fill, ow=layer.ow * 0.6)
