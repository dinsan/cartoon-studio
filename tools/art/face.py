"""Cartoon faces: eyes, brows, mouths and emotion effects.

A face is drawn in a local frame centred on (cx, cy) with unit ``r`` (head
radius) and rotated by ``tilt``. ``FaceLayout`` places the features, so the
same expressions work on a child, an adult, a dog or a car.
"""

import math
from dataclasses import dataclass, field

from . import kit
from .kit import EYE_DARK, WHITE, Layer

MOUTH = (150, 45, 70, 255)
TONGUE = (250, 120, 140, 255)


@dataclass
class Face:
    eyes: str = "open"  # open wide half happy closed sleep angry sad wink heart spiral x star side up tearful
    brows: str = "normal"  # none normal raised angry sad worried
    mouth: str = "smile"  # smile big_smile grin open small_o frown flat wavy laugh shout talk yawn tongue teeth smirk sob whistle
    blush: bool = False
    effects: list = field(default_factory=list)  # tears sweat anger hearts zzz question exclaim notes sparkles stars bulb steam


@dataclass
class FaceLayout:
    eye_dx: float = 0.27  # half distance between eyes (units of r)
    eye_x: float = 0.3  # face centre offset toward facing side
    eye_y: float = -0.05
    eye_rx: float = 0.14
    eye_ry: float = 0.19
    iris: tuple = (90, 60, 40, 255)
    mouth_x: float = 0.3
    mouth_y: float = 0.45
    mouth_w: float = 0.32
    brow_y: float = -0.32
    skin: tuple = (250, 210, 175, 255)
    nose: bool = True
    far_eye_scale: float = 0.9  # 3/4 view: the far eye is a little smaller


class FaceDrawer:
    def __init__(self, layer: Layer, cx, cy, r, layout: FaceLayout, tilt=0.0, line=None):
        self.l, self.cx, self.cy, self.r, self.k, self.tilt = layer, cx, cy, r, layout, tilt
        self.w = line if line is not None else layer.ow * 0.9

    def p(self, u, v):
        return kit.rot((self.cx + u * self.r, self.cy + v * self.r), self.tilt, (self.cx, self.cy))

    # ------------------------------------------------------------------ eyes

    def _eye_centres(self):
        k = self.k
        return [
            (k.eye_x - k.eye_dx, k.eye_y, k.far_eye_scale),
            (k.eye_x + k.eye_dx, k.eye_y, 1.0),
        ]

    def _open_eye(self, u, v, s, pupil=(0.0, 0.0), size=1.0, iris_scale=1.0, highlight=True):
        k, r = self.k, self.r
        cx, cy = self.p(u, v)
        rx, ry = k.eye_rx * r * s * size, k.eye_ry * r * s * size
        self.l.ellipse(cx, cy, rx, ry, WHITE, angle=self.tilt, ow=self.w * 0.7)
        px, py = self.p(u + pupil[0] * k.eye_rx * s, v + pupil[1] * k.eye_ry * s)
        ir = min(rx, ry) * 0.82 * iris_scale
        self.l.circle(px, py, ir, k.iris, outline=False)
        self.l.circle(px, py, ir * 0.55, EYE_DARK, outline=False)
        if highlight:
            hx, hy = self.p(u + pupil[0] * k.eye_rx * s + 0.05 * s, v + pupil[1] * k.eye_ry * s - 0.07 * s)
            self.l.circle(hx, hy, ir * 0.3, WHITE, outline=False)

    def _lid(self, u, v, s, left_drop, right_drop):
        """Skin-coloured lid covering the top of an eye, slanted."""
        k = self.k
        rx, ry = k.eye_rx * s * 1.25, k.eye_ry * s * 1.3
        a = (u - rx, v - ry * 1.2)
        b = (u + rx, v - ry * 1.2)
        c = (u + rx, v - ry + right_drop * ry * 2)
        d = (u - rx, v - ry + left_drop * ry * 2)
        pts = [self.p(*q) for q in (a, b, c, d)]
        self.l.poly(pts, k.skin, outline=False)
        self.l.line([self.p(*d), self.p(*c)], self.w * 1.1)

    def _arc_eye(self, u, v, s, up=True):
        k = self.k
        rx, ry = k.eye_rx * s, k.eye_ry * s * 0.7
        start, end = (200, 340) if up else (20, 160)
        pts = [self.p(u + rx * math.cos(math.radians(a)), v + ry * math.sin(math.radians(a)) + (0.05 if up else -0.05))
               for a in range(int(start), int(end) + 1, 10)]
        self.l.line(pts, self.w * 1.3)

    def eyes(self, kind: str):
        for i, (u, v, s) in enumerate(self._eye_centres()):
            near = i == 1
            if kind in ("open", "tearful"):
                self._open_eye(u, v, s, pupil=(0.15, 0.0), iris_scale=1.1 if kind == "tearful" else 1.0)
                if kind == "tearful":
                    x, y = self.p(u - 0.04, v + 0.02)
                    self.l.circle(x, y, self.k.eye_rx * self.r * s * 0.18, WHITE, outline=False)
            elif kind == "wide":
                self._open_eye(u, v, s, pupil=(0.0, 0.0), size=1.2, iris_scale=0.55)
            elif kind == "side":
                self._open_eye(u, v, s, pupil=(-0.45, 0.1))
                self._lid(u, v, s, 0.35, 0.35)
            elif kind == "up":
                self._open_eye(u, v, s, pupil=(0.25, -0.45))
            elif kind == "half":
                self._open_eye(u, v, s, pupil=(0.1, 0.25))
                self._lid(u, v, s, 0.5, 0.5)
            elif kind == "angry":
                self._open_eye(u, v, s, pupil=(0.1, 0.1))
                self._lid(u, v, s, 0.15, 0.5) if near else self._lid(u, v, s, 0.5, 0.15)
            elif kind == "sad":
                self._open_eye(u, v, s, pupil=(0.05, 0.2), iris_scale=1.1)
                self._lid(u, v, s, 0.4, 0.05) if near else self._lid(u, v, s, 0.05, 0.4)
            elif kind == "happy":
                self._arc_eye(u, v, s, up=True)
            elif kind in ("closed", "sleep"):
                self._arc_eye(u, v, s, up=False)
            elif kind == "wink":
                if near:
                    self._arc_eye(u, v, s, up=True)
                else:
                    self._open_eye(u, v, s, pupil=(0.15, 0.0))
            elif kind == "heart":
                x, y = self.p(u, v)
                kit.heart(self.l, x, y + self.r * 0.03, self.k.eye_ry * self.r * 2.1 * s)
            elif kind == "star":
                x, y = self.p(u, v)
                kit.star(self.l, x, y, self.k.eye_ry * self.r * 1.2 * s)
            elif kind == "spiral":
                x, y = self.p(u, v)
                self.l.circle(x, y, self.k.eye_ry * self.r * s, WHITE, ow=self.w)
                kit.spiral(self.l, x, y, self.k.eye_ry * self.r * s * 0.85, self.w * 0.9)
            elif kind == "x":
                x, y = self.p(u, v)
                d = self.k.eye_ry * self.r * s * 0.7
                self.l.line([(x - d, y - d), (x + d, y + d)], self.w * 1.3)
                self.l.line([(x - d, y + d), (x + d, y - d)], self.w * 1.3)

    # ----------------------------------------------------------------- brows

    def brows(self, kind: str):
        if kind == "none":
            return
        k = self.k
        for i, (u, _, s) in enumerate(self._eye_centres()):
            near = i == 1
            inner = -1 if near else 1  # towards the other eye
            half = k.eye_rx * 1.1 * s
            y = k.brow_y
            lift_in, lift_out = {
                "normal": (0.0, 0.0),
                "raised": (-0.08, -0.08),
                "angry": (0.1, -0.06),
                "sad": (-0.1, 0.05),
                "worried": (-0.1, 0.04) if near else (-0.02, -0.02),
                "focused": (0.05, 0.0),
            }.get(kind, (0.0, 0.0))
            a = (u + inner * half, y + lift_in)
            b = (u - inner * half, y + lift_out)
            mid = ((a[0] + b[0]) / 2, min(a[1], b[1]) - 0.04)
            self.l.curve([self.p(*a), self.p(*mid), self.p(*b)], self.w * 1.4)

    # ---------------------------------------------------------------- mouth

    def _mouth_shape(self, top, bottom, fill=MOUTH, tongue=True, teeth=False):
        pts = [self.p(*q) for q in top + bottom[::-1]]
        self.l.poly(pts, fill, ow=self.w)
        k = self.k
        if teeth:
            x0, y0 = top[0]
            x1, y1 = top[-1]
            band = [self.p(x0 + 0.03, y0 + 0.01), self.p(x1 - 0.03, y1 + 0.01),
                    self.p(x1 - 0.05, y1 + 0.09), self.p(x0 + 0.05, y0 + 0.09)]
            self.l.poly(band, WHITE, outline=False)
        if tongue:
            bx = sum(q[0] for q in bottom) / len(bottom)
            by = max(q[1] for q in bottom)
            depth = by - max(q[1] for q in top)
            if depth > 0.08:
                tx, ty = self.p(bx, by - depth * 0.28)
                self.l.ellipse(tx, ty, k.mouth_w * self.r * 0.42, depth * self.r * 0.3, TONGUE, angle=self.tilt, outline=False)
        # crisp outline on top of inner details
        self.l.line(pts + [pts[0]], self.w)

    def mouth(self, kind: str):
        k = self.k
        x, y, w = k.mouth_x, k.mouth_y, k.mouth_w
        line = lambda ctrl, width=1.2: self.l.curve([self.p(*c) for c in ctrl], self.w * width)
        if kind == "smile":
            line([(x - w * 0.6, y - 0.03), (x, y + 0.12), (x + w * 0.6, y - 0.05)])
        elif kind == "smirk":
            line([(x - w * 0.5, y + 0.02), (x + w * 0.1, y + 0.06), (x + w * 0.6, y - 0.07)])
        elif kind == "flat":
            line([(x - w * 0.45, y + 0.02), (x, y + 0.03), (x + w * 0.45, y + 0.01)])
        elif kind == "frown":
            line([(x - w * 0.5, y + 0.1), (x, y - 0.02), (x + w * 0.5, y + 0.08)])
        elif kind == "wavy":
            line([(x - w * 0.55, y + 0.04), (x - w * 0.2, y - 0.04), (x + w * 0.15, y + 0.08), (x + w * 0.55, y - 0.01)])
        elif kind == "big_smile":
            top = [(x - w * 0.65, y - 0.04), (x, y - 0.01), (x + w * 0.65, y - 0.06)]
            bottom = kit.bezier([(x - w * 0.65, y - 0.04), (x, y + 0.32), (x + w * 0.65, y - 0.06)], 12)
            self._mouth_shape(top, bottom)
        elif kind == "grin":
            top = [(x - w * 0.7, y - 0.03), (x, y), (x + w * 0.7, y - 0.05)]
            bottom = kit.bezier([(x - w * 0.7, y - 0.03), (x, y + 0.24), (x + w * 0.7, y - 0.05)], 12)
            self._mouth_shape(top, bottom, tongue=False, teeth=True)
        elif kind == "laugh":
            top = [(x - w * 0.75, y - 0.08), (x, y - 0.04), (x + w * 0.75, y - 0.1)]
            bottom = kit.bezier([(x - w * 0.75, y - 0.08), (x, y + 0.45), (x + w * 0.75, y - 0.1)], 14)
            self._mouth_shape(top, bottom, teeth=True)
        elif kind in ("open", "shout", "yawn", "small_o", "whistle", "talk", "sob"):
            rx, ry, dy = {
                "open": (0.13, 0.15, 0.06),
                "shout": (0.2, 0.22, 0.1),
                "yawn": (0.12, 0.26, 0.1),
                "small_o": (0.07, 0.08, 0.04),
                "whistle": (0.05, 0.05, 0.03),
                "talk": (0.12, 0.08, 0.04),
                "sob": (0.17, 0.12, 0.06),
            }[kind]
            pts = kit.ellipse_points(x, y + dy, rx * (w / 0.32), ry, 0, 180, 540, 20)
            top = pts[:11]
            bottom = pts[10:][::-1]
            if kind == "sob":
                top = kit.bezier([(x - rx * 1.2, y + 0.16), (x, y - 0.04), (x + rx * 1.2, y + 0.14)], 10)
                bottom = kit.bezier([(x - rx * 1.2, y + 0.16), (x, y + 0.2), (x + rx * 1.2, y + 0.14)], 10)
            self._mouth_shape(top, bottom, tongue=kind in ("shout", "yawn", "sob", "open"))
        elif kind == "tongue":
            line([(x - w * 0.6, y - 0.03), (x, y + 0.1), (x + w * 0.6, y - 0.05)])
            tx, ty = self.p(x + 0.05, y + 0.14)
            self.l.ellipse(tx, ty, 0.09 * self.r, 0.1 * self.r, TONGUE, angle=self.tilt, ow=self.w)
            self.l.line([self.p(x + 0.05, y + 0.1), self.p(x + 0.05, y + 0.18)], self.w * 0.6, (200, 80, 100, 255))
        elif kind == "teeth":
            top = [(x - w * 0.6, y), (x + w * 0.6, y - 0.02)]
            bottom = [(x - w * 0.55, y + 0.11), (x + w * 0.55, y + 0.09)]
            pts = [self.p(*q) for q in top + bottom[::-1]]
            self.l.poly(pts, WHITE, ow=self.w)
            self.l.line([self.p(x - w * 0.55, y + 0.055), self.p(x + w * 0.55, y + 0.035)], self.w * 0.6)
            for f in (-0.25, 0.1, 0.4):
                self.l.line([self.p(x + w * f, y), self.p(x + w * f, y + 0.1)], self.w * 0.5)

    def nose(self):
        if not self.k.nose:
            return
        x, y = self.k.eye_x + 0.12, self.k.eye_y + 0.26
        self.l.curve([self.p(x - 0.02, y - 0.06), self.p(x + 0.08, y + 0.02), self.p(x - 0.02, y + 0.06)], self.w)

    def blush(self):
        for u, v, s in self._eye_centres():
            x, y = self.p(u - 0.02, v + self.k.eye_ry + 0.14)
            self.l.ellipse(x, y, 0.12 * self.r * s, 0.06 * self.r * s, kit.BLUSH, angle=self.tilt, outline=False)

    # --------------------------------------------------------------- effects

    def effects(self, names):
        r = self.r
        top = self.p(0, -1.25)
        for name in names:
            if name == "tears":
                for u, v, s in self._eye_centres():
                    x, y = self.p(u, v + self.k.eye_ry * 0.9)
                    self.l.limb([(x, y), (x - r * 0.03, y + r * 0.28), (x + r * 0.01, y + r * 0.5)], r * 0.07, kit.TEAR)
            elif name == "tear":
                u, v, s = self._eye_centres()[1]
                x, y = self.p(u + 0.05, v + self.k.eye_ry + 0.12)
                kit.drop(self.l, x, y, r * 0.22)
            elif name == "sweat":
                x, y = self.p(1.0, -0.55)
                kit.drop(self.l, x, y, r * 0.3)
            elif name == "anger":
                x, y = self.p(0.75, -0.85)
                kit.anger_mark(self.l, x, y, r * 0.45)
            elif name == "hearts":
                kit.heart(self.l, top[0] + r * 0.6, top[1] - r * 0.1, r * 0.45)
                kit.heart(self.l, top[0] + r * 1.15, top[1] - r * 0.55, r * 0.3)
            elif name == "zzz":
                kit.zzz(self.l, top[0] + r * 0.7, top[1] + r * 0.1, r * 0.5)
            elif name == "question":
                kit.question(self.l, top[0] + r * 0.95, top[1] + r * 0.1, r * 0.7)
            elif name == "exclaim":
                kit.exclaim(self.l, top[0] + r * 0.95, top[1] + r * 0.1, r * 0.7)
            elif name == "notes":
                kit.note(self.l, top[0] + r * 1.2, top[1] + r * 0.5, r * 0.55)
                kit.note(self.l, top[0] + r * 1.7, top[1] + r * 0.05, r * 0.45)
            elif name == "sparkles":
                kit.sparkle(self.l, top[0] - r * 0.9, top[1] + r * 0.3, r * 0.22)
                kit.sparkle(self.l, top[0] + r * 1.1, top[1] + r * 0.15, r * 0.28)
            elif name == "stars":
                for i in range(4):
                    a = math.radians(-160 + i * 50)
                    kit.star(self.l, top[0] + r * 0.9 * math.cos(a), top[1] + r * 0.45 + r * 0.3 * math.sin(a), r * 0.15)
            elif name == "bulb":
                x, y = top[0] + r * 0.9, top[1] - r * 0.05
                self.l.circle(x, y, r * 0.28, kit.GOLD, ow=self.w)
                self.l.poly(kit.rounded_rect_points(x, y + r * 0.33, r * 0.22, r * 0.14, r * 0.04), (170, 170, 180, 255), ow=self.w)
                for a in (-150, -90, -30, 10, 190):
                    p0 = (x + r * 0.38 * math.cos(math.radians(a)), y + r * 0.38 * math.sin(math.radians(a)))
                    p1 = (x + r * 0.52 * math.cos(math.radians(a)), y + r * 0.52 * math.sin(math.radians(a)))
                    self.l.line([p0, p1], self.w, kit.GOLD)
            elif name == "steam":
                kit.puff(self.l, top[0] - r * 0.8, top[1] + r * 0.3, r * 0.3)
                kit.puff(self.l, top[0] + r * 0.9, top[1] + r * 0.25, r * 0.3)
            elif name == "ring":
                kit.sound_arcs(self.l, top[0] + r * 1.1, top[1] + r * 0.9, r * 0.5, self.w)

    def draw(self, face: Face):
        self.eyes(face.eyes)
        self.brows(face.brows)
        self.nose()
        if face.blush:
            self.blush()
        self.mouth(face.mouth)
        self.effects(face.effects)
