"""Parametric cartoon person (3/4 view, facing right).

Angles are absolute, in degrees: 0 = pointing straight down, +90 = forward
(+x, the way the character faces), 180 = straight up, -90 = backwards.
"""

import math
from dataclasses import dataclass, field, replace

from . import kit
from .face import Face, FaceDrawer, FaceLayout
from .kit import GROUND, OUTLINE, Layer


@dataclass
class HumanStyle:
    head_r: float
    neck: float
    torso_h: float
    torso_w_top: float
    torso_w_bottom: float
    hip_w: float
    upper_arm: float
    forearm: float
    arm_w: float
    thigh: float
    shin: float
    leg_w: float
    foot_len: float
    hand_r: float
    skin: tuple
    hair: tuple
    shirt: tuple
    pants: tuple
    shoes: tuple
    iris: tuple
    hair_style: str = "pigtails"  # pigtails | short | helmet
    long_sleeves: bool = False
    long_pants: bool = False
    socks: tuple | None = None
    tie: tuple | None = None
    glasses: bool = False
    helmet: tuple | None = None
    ow: float = 9.0


@dataclass
class HumanPose:
    face: Face = field(default_factory=Face)
    lean: float = 0.0  # torso lean, + = forward
    head_tilt: float = 0.0  # + = nod forward
    arm_back: tuple = (-10.0, -6.0)
    arm_front: tuple = (8.0, 16.0)
    leg_back: tuple = (-3.0, -3.0)
    leg_front: tuple = (3.0, 3.0)
    body_angle: float = 0.0  # rotate the whole figure (lying down)
    air: float = 0.0  # draw this far above the ground (jump poses)
    hands: tuple = ("mitt", "mitt")  # back, front: mitt | fist | point | thumb | open
    prop: str | None = None  # book phone cup ball ice_cream flower box chair balloon briefcase
    effects_extra: list = field(default_factory=list)  # body-level effects: speed lines, sweat
    ground_offset: float = 0.0  # extra vertical offset after grounding
    hip_override: tuple | None = None  # place the hip at this canvas point (bicycle)
    foot_targets: tuple | None = None  # (back, front) ankle targets -> leg IK (bicycle)
    hand_targets: tuple | None = None  # (back, front) wrist targets -> arm IK (bicycle)
    skip_ground: bool = False  # do not move the figure to the ground (bicycle)


def two_bone_ik(root, target, l1, l2, bend=1):
    """Angles (absolute, this module's convention) reaching ``target``.

    ``bend`` = +1 puts the middle joint forward (knees), -1 backwards (elbows
    pointing back)."""
    dx, dy = target[0] - root[0], target[1] - root[1]
    d = min(math.hypot(dx, dy), l1 + l2 - 1e-3)
    d = max(d, abs(l1 - l2) + 1e-3)
    base = math.degrees(math.atan2(dx, dy))  # angle of root->target in our convention
    cos_a = (l1 * l1 + d * d - l2 * l2) / (2 * l1 * d)
    a = math.degrees(math.acos(max(-1, min(1, cos_a))))
    upper = base + bend * a
    joint = kit.along(root, upper, l1)
    lower = math.degrees(math.atan2(target[0] - joint[0], target[1] - joint[1]))
    return upper, lower


class HumanDrawer:
    def __init__(self, style: HumanStyle):
        self.s = style

    # ------------------------------------------------------------- skeleton

    def skeleton(self, pose: HumanPose, hip=(512.0, 600.0)):
        s = self.s
        lean = pose.lean
        axis = kit.direction(180 - lean)
        perp = (-axis[1], axis[0])
        neck = (hip[0] + axis[0] * s.torso_h, hip[1] + axis[1] * s.torso_h)

        def off(p, along_axis, across):
            return (p[0] + axis[0] * along_axis + perp[0] * across, p[1] + axis[1] * along_axis + perp[1] * across)

        j = {"hip": hip, "neck": neck}
        j["sh_back"] = off(neck, -s.torso_h * 0.12, -s.torso_w_top * 0.32)
        j["sh_front"] = off(neck, -s.torso_h * 0.12, s.torso_w_top * 0.16)
        j["hip_back"] = off(hip, 0, -s.hip_w * 0.22)
        j["hip_front"] = off(hip, 0, s.hip_w * 0.22)
        head_dir = 180 - (lean + pose.head_tilt)
        j["head"] = kit.along(neck, head_dir, s.neck + s.head_r * 0.88)

        legs = {"back": pose.leg_back, "front": pose.leg_front}
        arms = {"back": pose.arm_back, "front": pose.arm_front}
        if pose.foot_targets:
            for side, target in zip(("back", "front"), pose.foot_targets):
                legs[side] = two_bone_ik(j[f"hip_{side}"], target, s.thigh, s.shin, bend=1)
        if pose.hand_targets:
            for side, target in zip(("back", "front"), pose.hand_targets):
                arms[side] = two_bone_ik(j[f"sh_{side}"], target, s.upper_arm, s.forearm, bend=-1)
        for side in ("back", "front"):
            t, sh = legs[side]
            j[f"knee_{side}"] = kit.along(j[f"hip_{side}"], t, s.thigh)
            j[f"ankle_{side}"] = kit.along(j[f"knee_{side}"], sh, s.shin)
            j[f"shin_{side}"] = sh
            u, lo = arms[side]
            j[f"elbow_{side}"] = kit.along(j[f"sh_{side}"], u, s.upper_arm)
            j[f"wrist_{side}"] = kit.along(j[f"elbow_{side}"], lo, s.forearm)
            j[f"fore_{side}"] = lo
        return j

    # ---------------------------------------------------------------- parts

    def _leg(self, L: Layer, j, side, dark):
        s = self.s
        f = (lambda c: kit.shade(c, 0.86)) if dark else (lambda c: c)
        hip, knee, ankle = j[f"hip_{side}"], j[f"knee_{side}"], j[f"ankle_{side}"]
        if s.long_pants:
            L.limb([hip, knee, ankle], s.leg_w, f(s.pants))
        else:
            L.limbs([([hip, knee, ankle], s.leg_w * 0.78, f(s.skin))])
            mid = kit.lerp(hip, knee, 0.75)
            L.limb([hip, mid], s.leg_w * 1.12, f(s.pants))
            if s.socks:
                L.limb([kit.lerp(knee, ankle, 0.7), ankle], s.leg_w * 0.82, f(s.socks))
        shin = j[f"shin_{side}"]
        foot_angle = -shin  # screen angle of the foot's long axis
        centre = kit.along(ankle, shin, s.leg_w * 0.25)
        centre = (centre[0] + math.cos(math.radians(foot_angle)) * s.foot_len * 0.32,
                  centre[1] + math.sin(math.radians(foot_angle)) * s.foot_len * 0.32)
        L.ellipse(centre[0], centre[1], s.foot_len * 0.62, s.leg_w * 0.42, f(s.shoes), angle=foot_angle)

    def _hand(self, L: Layer, j, side, kind, dark):
        s = self.s
        skin = kit.shade(s.skin, 0.9) if dark else s.skin
        w = j[f"wrist_{side}"]
        fore = j[f"fore_{side}"]
        c = kit.along(w, fore, s.hand_r * 0.4)
        if kind == "point":
            tip = kit.along(c, fore, s.hand_r * 1.9)
            L.limb([c, tip], s.hand_r * 0.55, skin)
        elif kind == "thumb":
            tip = (c[0], c[1] - s.hand_r * 1.6)
            L.limb([c, tip], s.hand_r * 0.55, skin)
        L.circle(c[0], c[1], s.hand_r * (0.9 if kind == "fist" else 1.0), skin)
        if kind == "open":
            for a in (-40, 0, 40):
                tip = kit.along(c, fore + a, s.hand_r * 1.35)
                L.limb([c, tip], s.hand_r * 0.45, skin)
            L.circle(c[0], c[1], s.hand_r * 0.9, skin, outline=False)

    def _arm(self, L: Layer, j, side, dark, hand):
        s = self.s
        f = (lambda c: kit.shade(c, 0.86)) if dark else (lambda c: c)
        sh, el, wr = j[f"sh_{side}"], j[f"elbow_{side}"], j[f"wrist_{side}"]
        if s.long_sleeves:
            L.limb([sh, el, wr], s.arm_w, f(s.shirt))
        else:
            L.limb([sh, el, wr], s.arm_w * 0.8, f(s.skin))
            L.limb([sh, kit.lerp(sh, el, 0.55)], s.arm_w * 1.08, f(s.shirt))
        self._hand(L, j, side, hand, dark)

    def _torso(self, L: Layer, j, pose):
        s = self.s
        axis = kit.direction(180 - pose.lean)
        bottom = (j["hip"][0] - axis[0] * s.leg_w * 0.35, j["hip"][1] - axis[1] * s.leg_w * 0.35)
        top = (j["neck"][0] - axis[0] * s.torso_h * 0.02, j["neck"][1] - axis[1] * s.torso_h * 0.02)
        if s.long_pants:
            hips = kit.trapezoid_points(kit.lerp(j["hip"], j["neck"], 0.22), bottom, s.hip_w * 1.02, s.hip_w * 1.02, s.hip_w * 0.3)
            L.poly(hips, s.pants)
        L.poly(kit.trapezoid_points(top, kit.lerp(bottom, top, 0.06), s.torso_w_top, s.torso_w_bottom, s.torso_w_top * 0.32), s.shirt)
        if s.tie:
            a = kit.lerp(top, bottom, 0.1)
            b = kit.lerp(top, bottom, 0.62)
            L.poly(kit.trapezoid_points(a, b, s.torso_w_top * 0.1, s.torso_w_top * 0.2, 6), s.tie)
        if not s.long_pants:
            L.poly(kit.trapezoid_points(kit.lerp(bottom, top, 0.2), kit.lerp(bottom, top, -0.05),
                                        s.torso_w_bottom * 1.02, s.hip_w * 1.05, 14), s.pants)

    def _head(self, L: Layer, FX: Layer, j, pose):
        s = self.s
        hx, hy = j["head"]
        r = s.head_r
        tilt = pose.lean + pose.head_tilt  # body_angle is applied to the finished layers
        P = lambda u, v: kit.rot((hx + u * r, hy + v * r), tilt, (hx, hy))
        # neck
        L.limb([kit.lerp(j["neck"], j["head"], 0.05), kit.lerp(j["neck"], j["head"], 0.45)], s.arm_w * 0.8, s.skin)
        # hair behind the head
        if s.hair_style == "pigtails":
            for (u, v, rx, ry, a) in ((-0.95, -0.05, 0.32, 0.45, 25), (0.55, -0.85, 0.28, 0.4, -35)):
                x, y = P(u, v)
                L.ellipse(x, y, rx * r, ry * r, s.hair, angle=a + tilt)
                bx, by = P(u * 0.78, v * 0.82)
                L.circle(bx, by, 0.1 * r, (235, 70, 90, 255))
        L.circle(hx, hy, r, s.skin)
        # ear
        ex, ey = P(-0.62, 0.1)
        L.circle(ex, ey, 0.17 * r, s.skin)
        L.arc(ex, ey, 0.07 * r, 0.07 * r, 100, 260, L.ow * 0.6)
        # hair on top
        if s.hair_style in ("pigtails", "short", "helmet"):
            cap = [P(1.05 * math.cos(math.radians(a)), 1.05 * math.sin(math.radians(a))) for a in range(165, 346, 6)]
            if s.hair_style == "pigtails":
                fringe = kit.bezier([P(0.98, -0.36), P(0.6, -0.6), P(0.3, -0.44), P(0.0, -0.64), P(-0.4, -0.5), P(-0.95, 0.2)], 24)
            else:
                fringe = kit.bezier([P(0.96, -0.38), P(0.45, -0.62), P(-0.1, -0.52), P(-0.55, -0.4), P(-0.98, 0.2)], 24)
            L.poly(cap + fringe, s.hair)
        if s.helmet:
            dome = [P(1.12 * math.cos(math.radians(a)), 0.92 * math.sin(math.radians(a)) - 0.36) for a in range(172, 369, 6)]
            L.poly(dome, s.helmet)
            for a in (215, 250, 285, 320):
                p0 = P(0.5 * math.cos(math.radians(a)), 0.45 * math.sin(math.radians(a)) - 0.4)
                p1 = P(0.92 * math.cos(math.radians(a)), 0.8 * math.sin(math.radians(a)) - 0.4)
                L.line([p0, p1], L.ow * 1.1, kit.shade(s.helmet, 0.7))
            L.line([P(-0.75, -0.3), P(-0.5, 0.55), P(0.1, 0.95)], L.ow * 0.8, OUTLINE)
        layout = FaceLayout(skin=s.skin, iris=s.iris)
        face = FaceDrawer(L, hx, hy, r, layout, tilt=tilt)
        f = pose.face
        face.eyes(f.eyes)
        if s.glasses:
            for u, v, sc in face._eye_centres():
                x, y = P(u, v)
                L.arc(x, y, 0.25 * r * sc, 0.24 * r * sc, 0, 360, L.ow * 0.8)
            a = P(face._eye_centres()[0][0] + 0.22, layout.eye_y)
            b = P(face._eye_centres()[1][0] - 0.24, layout.eye_y)
            L.line([a, b], L.ow * 0.8)
        face.brows(f.brows)
        face.nose()
        if f.blush:
            face.blush()
        face.mouth(f.mouth)
        return layout, tilt

    # ---------------------------------------------------------------- props

    def _prop(self, L: Layer, j, pose, stage):
        s = self.s
        p = pose.prop
        if not p:
            return
        wf = j["wrist_front"]
        hand = kit.along(wf, j["fore_front"], s.hand_r * 0.4)
        if stage == "back" and p == "chair":
            seat_y = j["hip"][1] + s.leg_w * 0.55
            floor = max(j["ankle_back"][1], j["ankle_front"][1]) + s.leg_w * 0.6
            x0 = j["hip"][0] - s.hip_w * 0.9
            x1 = j["hip"][0] + s.hip_w * 0.7
            wood = kit.rgb("#b07a4a")
            L.limb([(x0 + 10, seat_y), (x0 + 10, floor)], 22, kit.shade(wood, 0.85))
            L.limb([(x1 - 10, seat_y), (x1 - 10, floor)], 22, kit.shade(wood, 0.85))
            L.limb([(x0 + 10, seat_y), (x0 + 4, seat_y - s.torso_h * 1.0)], 24, wood)
            L.poly(kit.rounded_rect_points((x0 + x1) / 2, seat_y + 12, x1 - x0 + 20, 26, 8), wood)
        if stage != "front":
            return
        if p == "book":
            c = (hand[0] + 20, hand[1] - 25)
            L.poly(kit.rounded_rect_points(c[0] - 38, c[1], 80, 105, 8, angle=-8), kit.rgb("#e84d4d"))
            L.poly(kit.rounded_rect_points(c[0] + 38, c[1], 80, 105, 8, angle=8), kit.rgb("#e84d4d"))
            L.poly(kit.rounded_rect_points(c[0] - 34, c[1] - 2, 68, 92, 5, angle=-8), kit.rgb("#fff8e6"), outline=False)
            L.poly(kit.rounded_rect_points(c[0] + 34, c[1] - 2, 68, 92, 5, angle=8), kit.rgb("#fff8e6"), outline=False)
            L.line([(c[0], c[1] - 50), (c[0], c[1] + 52)], L.ow * 0.7)
        elif p == "phone":
            L.poly(kit.rounded_rect_points(hand[0] + 10, hand[1] - 30, 34, 70, 8, angle=15), kit.rgb("#3b3f58"))
        elif p == "cup":
            c = (hand[0] + 22, hand[1] - 25)
            L.poly(kit.rounded_rect_points(c[0], c[1], 52, 62, 10), kit.rgb("#ffffff"))
            L.arc(c[0] + 30, c[1], 16, 16, -90, 90, L.ow * 1.2)
            for dx in (-10, 8):
                L.curve([(c[0] + dx, c[1] - 45), (c[0] + dx + 12, c[1] - 62), (c[0] + dx, c[1] - 80)], L.ow * 0.7, kit.MARK)
        elif p == "ice_cream":
            c = (hand[0] + 5, hand[1] - 30)
            L.poly([(c[0] - 24, c[1]), (c[0] + 24, c[1]), (c[0], c[1] + 62)], kit.rgb("#e8b06a"))
            L.circle(c[0], c[1] - 18, 30, kit.rgb("#ff9ec4"))
            L.circle(c[0] + 8, c[1] - 44, 22, kit.rgb("#fff2c2"))
        elif p == "flower":
            top = (hand[0] + 15, hand[1] - 95)
            L.line([hand, top], L.ow * 1.2, kit.rgb("#4caf50"))
            for a in range(0, 360, 60):
                x = top[0] + 20 * math.cos(math.radians(a))
                y = top[1] + 20 * math.sin(math.radians(a))
                L.circle(x, y, 15, kit.rgb("#ff6fa8"), ow=L.ow * 0.6)
            L.circle(top[0], top[1], 12, kit.GOLD, ow=L.ow * 0.6)
        elif p == "balloon":
            top = (hand[0] + 40, hand[1] - 260)
            L.curve([hand, (hand[0] + 40, hand[1] - 120), (top[0] - 10, top[1] + 90)], L.ow * 0.6)
            L.ellipse(top[0], top[1], 62, 75, kit.rgb("#ff5a5a"))
            L.ellipse(top[0] - 20, top[1] - 25, 12, 20, kit.rgb("#ffb0b0"), outline=False)
        elif p == "ball":
            c = (hand[0] + 10, hand[1] - 40)
            L.circle(c[0], c[1], 46, kit.rgb("#ff7043"))
            L.arc(c[0], c[1], 46, 20, 180, 360, L.ow * 0.8)
            L.arc(c[0], c[1], 20, 46, 270, 450, L.ow * 0.8)
        elif p == "box":
            wb = j["wrist_back"]
            c = ((hand[0] + wb[0]) / 2 + 20, (hand[1] + wb[1]) / 2 - 30)
            L.poly(kit.rounded_rect_points(c[0], c[1], 170, 130, 10), kit.rgb("#c99a60"))
            L.line([(c[0] - 85, c[1] - 20), (c[0] + 85, c[1] - 20)], L.ow * 0.7)
            L.poly(kit.rounded_rect_points(c[0], c[1] - 20, 34, 14, 3), kit.rgb("#e8d9b0"), outline=False)
        elif p == "briefcase":
            c = (hand[0] + 5, hand[1] + 55)
            L.arc(c[0], c[1] - 48, 22, 16, 180, 360, L.ow * 1.3)
            L.poly(kit.rounded_rect_points(c[0], c[1], 120, 85, 10), kit.rgb("#6d4c41"))

    # ---------------------------------------------------------------- draw

    def draw(self, pose: HumanPose, shadow_scale=1.0):
        s = self.s
        hip = pose.hip_override or (512.0, 560.0)
        j = self.skeleton(pose, hip)
        body = Layer(s.ow)
        fx = Layer(s.ow)
        self._prop(body, j, pose, "back")
        self._arm(body, j, "back", True, pose.hands[0])
        self._leg(body, j, "back", True)
        self._leg(body, j, "front", False)
        self._torso(body, j, pose)
        layout, tilt = self._head(body, fx, j, pose)
        self._arm(body, j, "front", False, pose.hands[1])
        self._prop(body, j, pose, "front")
        for e in pose.effects_extra:
            draw_body_effect(fx, e, j, s)
        if pose.body_angle:
            body.image = body.image.rotate(-pose.body_angle, center=(hip[0] * kit.SS, hip[1] * kit.SS),
                                           resample=kit.Image.Resampling.BICUBIC)
            fx.image = fx.image.rotate(-pose.body_angle, center=(hip[0] * kit.SS, hip[1] * kit.SS),
                                       resample=kit.Image.Resampling.BICUBIC)
            body.draw = kit.ImageDraw.Draw(body.image)
            fx.draw = kit.ImageDraw.Draw(fx.image)
        # Face effects (tears, Zzz, hearts...) stay upright even when lying.
        head = kit.rot(j["head"], pose.body_angle, hip) if pose.body_angle else j["head"]
        FaceDrawer(fx, head[0], head[1], s.head_r, layout, tilt=0 if pose.body_angle else tilt).effects(pose.face.effects)
        return body, fx, j


def draw_body_effect(L: Layer, name, j, s: HumanStyle):
    hx, hy = j["head"]
    if name == "speed":
        kit.motion_lines(L, j["hip"][0] - s.hip_w * 1.1, j["hip"][1] - s.torso_h * 0.5, 110, 45, 3, L.ow * 1.1)
    elif name == "action":
        kit.motion_lines(L, j["hip"][0] - s.hip_w * 0.9, j["hip"][1] + s.thigh * 0.4, 70, 35, 2, L.ow)
    elif name == "clap":
        c = kit.lerp(j["wrist_back"], j["wrist_front"], 0.5)
        for a in (-60, -20, 20):
            p0 = kit.along(c, 180 + a, s.hand_r * 1.6)
            p1 = kit.along(c, 180 + a, s.hand_r * 2.6)
            L.line([p0, p1], L.ow, kit.MARK)
    elif name == "wave":
        w = j["wrist_front"]
        kit.sound_arcs(L, w[0] + s.hand_r, w[1] - s.hand_r, s.hand_r * 1.8, L.ow, count=2)
    elif name == "shout":
        kit.sound_arcs(L, hx + s.head_r * 1.2, hy + s.head_r * 0.4, s.head_r * 0.7, L.ow * 1.1, count=3)


def place(body: Layer, fx: Layer, air: float, shadow_rx: float, centre_x: float | None = None, ground_offset=0.0):
    """Move the figure so its lowest point is on the ground (or ``air``
    above it) and add the ground shadow. Returns the final image."""
    box = body.bbox()
    target_bottom = GROUND - air + ground_offset
    cx = (box[0] + box[2]) / 2 if centre_x is None else centre_x
    dx, dy = 512 - cx, target_bottom - box[3]
    body.offset(dx, dy)
    fx.offset(dx, dy)
    shadow = Layer(body.ow)
    shadow.shadow(512, shadow_rx)
    return kit.compose(shadow, body, fx), (dx, dy)


def draw_person(style: HumanStyle, pose: HumanPose) -> tuple:
    drawer = HumanDrawer(style)
    body, fx, j = drawer.draw(pose)
    # Centre on the support point: between the feet when standing.
    feet_x = (j["ankle_back"][0] + j["ankle_front"][0]) / 2 + style.foot_len * 0.3
    centre = feet_x if not pose.body_angle else None
    image, (dx, dy) = place(body, fx, pose.air, style.hip_w * 0.95, centre, pose.ground_offset)
    moved = {k: (v[0] + dx, v[1] + dy) for k, v in j.items() if isinstance(v, tuple)}
    return image, moved


def variant(pose: HumanPose, **changes) -> HumanPose:
    return replace(pose, **changes)
