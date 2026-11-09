"""Bicycle with a rider (the kid in a helmet), side view facing right."""

import math
from dataclasses import dataclass, field, replace

from . import kit
from .face import Face
from .human import HumanDrawer, HumanPose
from .kit import GROUND, Layer
from .people import KID, Expr

RIDER = replace(KID, helmet=kit.rgb("#36b37e"))
FRAME = kit.rgb("#3f7ee8")
TYRE = kit.rgb("#35323d")
METAL = kit.rgb("#a7adbf")
OW = 9.0

WHEEL_R = 118
REAR = (330.0, GROUND - WHEEL_R)
FRONT = (700.0, GROUND - WHEEL_R)
BB = (505.0, GROUND - 100)  # bottom bracket (crank centre)
CRANK = 50
SEAT = (452.0, 652.0)
HEAD_TOP = (648.0, 642.0)
HEAD_BOT = (664.0, 700.0)
GRIP = (690.0, 590.0)
SPOKES = 8
RIDE_FRAMES = 8
SPOKE_STEP = 3 * (360 / SPOKES) / RIDE_FRAMES  # 16.875 deg per drawing, reads as forward motion


@dataclass
class BikePose:
    face: Face = field(default_factory=lambda: Face(mouth="smile"))
    crank: float = 0.0  # crank angle, degrees clockwise from pointing forward
    spoke: float = 0.0
    rider: str = "pedal"  # pedal | foot_down | standing | feet_out | none | flying
    arms: str = "bars"  # bars | wave1 | wave2 | up | bell
    lean: float = 30.0
    blur: bool = False
    flat: bool = False
    air: float = 0.0
    tilt: float = 0.0  # rotate everything (crash), + = clockwise
    basket: bool = False
    number: bool = False
    effects_extra: list = field(default_factory=list)


def _pedal(angle):
    a = math.radians(angle)
    return BB[0] + CRANK * math.cos(a), BB[1] + CRANK * math.sin(a)


def _wheel(L: Layer, c, spoke, blur=False, flat=False):
    x, y = c
    if flat:
        L.ellipse(x, y + 18, WHEEL_R * 1.08, WHEEL_R * 0.86, TYRE)
        L.ellipse(x, y + 18, WHEEL_R * 0.88, WHEEL_R * 0.7, kit.rgb("#e9edf5"), outline=False)
    else:
        L.circle(x, y, WHEEL_R, TYRE)
        L.circle(x, y, WHEEL_R * 0.84, kit.rgb("#e9edf5"), ow=OW * 0.6)
    if blur:
        for rr in (0.7, 0.5, 0.3):
            L.arc(x, y + (18 if flat else 0), WHEEL_R * rr, WHEEL_R * rr, 0, 360, OW * 0.6, METAL)
    else:
        for i in range(SPOKES):
            a = spoke + i * 360 / SPOKES
            p = (x + WHEEL_R * 0.82 * math.cos(math.radians(a)), y + WHEEL_R * 0.82 * math.sin(math.radians(a)))
            L.line([(x, y), p], OW * 0.45, METAL)
    L.circle(x, y, 14, METAL, ow=OW * 0.6)


def _bike(L: Layer, pose: BikePose):
    _wheel(L, REAR, pose.spoke, pose.blur)
    _wheel(L, FRONT, pose.spoke, pose.blur, pose.flat)
    far = _pedal(pose.crank + 180)
    L.limb([BB, far], 14, kit.shade(METAL, 0.8))
    L.poly(kit.rounded_rect_points(far[0], far[1], 46, 16, 5), kit.shade(METAL, 0.7))
    # chain
    L.line([(BB[0], BB[1] - 34), (REAR[0], REAR[1] - 16), (REAR[0], REAR[1] + 16), (BB[0], BB[1] + 34)], OW * 0.7, kit.rgb("#5b5f70"))
    tubes = [
        [REAR, SEAT], [REAR, BB], [BB, SEAT], [BB, HEAD_BOT], [SEAT, HEAD_TOP], [HEAD_TOP, HEAD_BOT], [HEAD_BOT, FRONT],
    ]
    L.limbs([(t, 20, FRAME) for t in tubes])
    L.circle(BB[0], BB[1], 36, METAL, ow=OW * 0.7)
    L.circle(BB[0], BB[1], 12, kit.shade(METAL, 0.7), ow=OW * 0.5)
    # seat post, saddle, stem, handlebar, bell, light
    L.limb([SEAT, (SEAT[0] - 6, SEAT[1] - 22)], 14, METAL)
    L.ellipse(SEAT[0] - 12, SEAT[1] - 28, 46, 14, kit.rgb("#3b2a24"))
    L.limb([HEAD_TOP, (HEAD_TOP[0] - 4, GRIP[1])], 16, METAL)
    L.limb([(HEAD_TOP[0] - 4, GRIP[1]), GRIP], 14, METAL)
    L.limb([GRIP, (GRIP[0] + 18, GRIP[1])], 20, kit.rgb("#3b2a24"))
    L.circle(HEAD_TOP[0] + 14, GRIP[1] - 14, 13, kit.GOLD, ow=OW * 0.6)
    L.ellipse(HEAD_TOP[0] + 42, HEAD_TOP[1] + 8, 18, 14, kit.rgb("#fff2a8"), ow=OW * 0.6)
    if pose.basket:
        bx, by = FRONT[0] + 5, HEAD_TOP[1] - 10
        L.poly(kit.trapezoid_points((bx, by - 40), (bx, by + 40), 120, 96, 10), kit.rgb("#c99a60"))
        for dx in (-35, 0, 35):
            L.line([(bx + dx, by - 38), (bx + dx * 0.8, by + 38)], OW * 0.5)
        for dx, col in ((-30, "#ff6fa8"), (0, "#ffd54f"), (30, "#ff7043")):
            L.circle(bx + dx, by - 55, 20, kit.rgb(col), ow=OW * 0.6)
    if pose.number:
        L.circle(HEAD_TOP[0] + 48, GRIP[1] + 30, 34, kit.WHITE, ow=OW * 0.8)
        nx, ny = HEAD_TOP[0] + 48, GRIP[1] + 30
        L.line([(nx - 6, ny - 18), (nx + 4, ny - 24), (nx + 4, ny + 22)], OW * 1.1)
    near = _pedal(pose.crank)
    return near


def _rider(pose: BikePose, near_pedal):
    hip = (SEAT[0] - 8, SEAT[1] - 40)
    lean = pose.lean
    far_pedal = _pedal(pose.crank + 180)
    feet = ((far_pedal[0] - 8, far_pedal[1] - 16), (near_pedal[0] - 8, near_pedal[1] - 16))
    hands = ((GRIP[0] - 14, GRIP[1] + 2), (GRIP[0] + 6, GRIP[1] + 2))
    arm_front = None
    extra = []
    if pose.rider == "foot_down":
        feet = ((far_pedal[0] - 8, far_pedal[1] - 16), (BB[0] + 70, GROUND - 22))
        lean = 18
    elif pose.rider == "standing":
        hip = (SEAT[0] + 40, SEAT[1] - 95)
        lean = 40
    elif pose.rider == "feet_out":
        feet = ((BB[0] - 175, BB[1] + 10), (BB[0] + 175, BB[1] + 10))
    elif pose.rider == "flying":
        hip = (SEAT[0] + 40, SEAT[1] - 150)
        lean = 50
        feet = ((hip[0] - 170, hip[1] + 40), (hip[0] - 70, hip[1] + 180))
    hand_targets = hands
    if pose.arms in ("wave1", "wave2"):
        arm_front = (118, 190 if pose.arms == "wave1" else 145)
        hand_targets = None
        extra.append("wave")
    elif pose.arms == "up":
        hand_targets = None
        arm_front = (130, 150)
    elif pose.arms == "bell":
        hands = (hands[0], (HEAD_TOP[0] + 16, GRIP[1] - 18))
        hand_targets = hands
        extra.append("ring")
    # Riders lean the body but keep their head up to see the road.
    hp = HumanPose(face=pose.face, lean=lean, head_tilt=-0.7 * lean, hip_override=hip, foot_targets=feet,
                   hand_targets=hand_targets, effects_extra=extra)
    if hand_targets is None:
        hp.hand_targets = None
        hp.arm_front = arm_front or (70, 90)
        hp.arm_back = (-130, -150) if pose.arms == "up" else (40, 80)
        if pose.arms != "up":
            hp.hand_targets = (hands[0], None)
    return hp


class _BikeRiderDrawer(HumanDrawer):
    def skeleton(self, pose, hip=(512.0, 560.0)):
        targets = pose.hand_targets
        if targets and targets[1] is None:
            pose = replace(pose, hand_targets=None)
            j = super().skeleton(pose, hip)
            from .human import two_bone_ik
            up, lo = two_bone_ik(j["sh_back"], targets[0], self.s.upper_arm, self.s.forearm, bend=-1)
            j["elbow_back"] = kit.along(j["sh_back"], up, self.s.upper_arm)
            j["wrist_back"] = kit.along(j["elbow_back"], lo, self.s.forearm)
            j["fore_back"] = lo
            return j
        return super().skeleton(pose, hip)


def draw_bike(pose: BikePose):
    bike = Layer(OW)
    near = _bike(bike, pose)
    layers = [bike]
    if pose.rider != "none":
        hp = _rider(pose, near)
        body, fx, _ = _BikeRiderDrawer(RIDER).draw(hp)
        layers += [body, fx]
    fx2 = Layer(OW)
    for e in pose.effects_extra:
        if e == "speed":
            kit.motion_lines(fx2, REAR[0] - WHEEL_R - 15, REAR[1] - 60, 110, 45, 3, OW * 1.1)
        elif e == "dust":
            for dx, r in ((-60, 30), (-110, 24), (-150, 18)):
                kit.puff(fx2, REAR[0] + dx, GROUND - r * 0.8, r, (215, 190, 150, 255))
        elif e == "beam":
            hx, hy = HEAD_TOP[0] + 60, HEAD_TOP[1] + 8
            for a in (-10, 0, 10, 20):
                fx2.line([(hx + 10, hy + a * 0.6), (hx + 110, hy + a * 3.5)], OW, kit.rgb("#fff2a8"))
        elif e == "sweat":
            kit.drop(fx2, 760, 330, 36)
    layers.append(fx2)
    if pose.tilt:
        pivot = (FRONT[0], GROUND) if pose.tilt > 0 else (REAR[0], GROUND)
        for layer in layers:
            layer.image = layer.image.rotate(-pose.tilt, center=(pivot[0] * kit.SS, pivot[1] * kit.SS),
                                             resample=kit.Image.Resampling.BICUBIC)
            layer.draw = kit.ImageDraw.Draw(layer.image)
    if pose.air:
        for layer in layers:
            layer.offset(0, -pose.air)
    # centre the bike in the canvas and draw the ground shadow
    dx = 512 - (REAR[0] + FRONT[0]) / 2
    for layer in layers:
        layer.offset(dx, 0)
    shadow = Layer(OW)
    shadow.shadow(512, (FRONT[0] - REAR[0]) / 2 + WHEEL_R * 0.9)
    return kit.compose(shadow, *layers)


def B(**kw) -> BikePose:
    return BikePose(**kw)


def F(**kw) -> Face:
    return Face(**kw)


def ride_cycle(face, frames=RIDE_FRAMES, **kw):
    return [B(face=face, crank=i * 360 / frames, spoke=i * SPOKE_STEP * RIDE_FRAMES / frames, **kw) for i in range(frames)]


def bicycle_expressions() -> list[Expr]:
    X = []
    add = lambda *a, **k: X.append(Expr(*a, **k))
    stop = dict(rider="foot_down", crank=200)
    add("idle", [B(face=F(), **stop)], "idle", ["stop", "stopped", "wait", "waiting", "stand"], "Stopped with one foot down.")
    add("ride", ride_cycle(F(mouth="big_smile")), "ride", ["ride", "riding", "rode", "cycle", "cycling", "bike", "bicycle", "pedal", "go", "went"],
        "Pedalling along (8 frames).", hold=1)
    add("fast", [B(face=F(brows="focused", mouth="grin"), crank=i * 90, blur=True, lean=42, effects_extra=["speed"]) for i in range(4)],
        "drive_fast", ["fast", "speed", "race", "raced", "hurry", "rush", "zoom", "zoomed"], "Pedalling hard (4 frames).", hold=1)
    add("coast", [B(face=F(eyes="happy", mouth="smile"), crank=0, spoke=i * SPOKE_STEP) for i in range(3)], "drive",
        ["coast", "coasted", "roll", "rolled", "glide", "glided", "cruise"], "Coasting, feet still.", hold=1)
    add("uphill", [B(face=F(eyes="closed", brows="angry", mouth="teeth", effects=["sweat"]), rider="standing", crank=i * 90, spoke=i * 8) for i in range(4)],
        "ride", ["uphill", "hill", "climb", "climbed", "push", "pushed", "hard"], "Standing on the pedals up a hill (4 frames).", hold=3)
    add("downhill", [B(face=F(eyes="happy", mouth="laugh"), rider="feet_out", crank=0, spoke=i * SPOKE_STEP, effects_extra=["speed"]) for i in range(3)],
        "drive_fast", ["downhill", "down the hill", "wheee", "whee", "swoosh"], "Feet out, zooming downhill.", hold=1)
    add("wheelie", [B(face=F(eyes="wink", mouth="big_smile"), crank=0, lean=20)], "wheelie",
        ["wheelie", "trick", "tricks", "show off", "showed off"], "Pulling a wheelie.")
    add("jump", [B(face=F(eyes="wide", mouth="laugh"), crank=0, rider="standing", air=110)], "jump",
        ["jump", "jumped", "hop", "hopped", "bump", "ramp", "leap"], "Bunny-hop jump.")
    add("brake", [B(face=F(eyes="wide", brows="worried", mouth="teeth"), crank=0, lean=12, effects_extra=["dust"])], "brake",
        ["brake", "braked", "skid", "skidded", "screech", "halt", "stop suddenly"], "Skidding to a stop.")
    add("bell", [B(face=F(eyes="happy", mouth="open"), arms="bell", **stop), B(face=F(eyes="happy", mouth="smile"), arms="bell", **stop)],
        "talk", ["bell", "ring", "rang", "ding", "ting", "say", "said", "call", "called"], "Ringing the bell (2 frames).", hold=3)
    add("wave", [B(face=F(mouth="big_smile"), arms="wave1", **stop), B(face=F(mouth="big_smile"), arms="wave2", **stop)],
        "wave", ["wave", "waved", "waving", "hello", "hi", "bye", "goodbye"], "Waving from the bike (2 frames).", hold=3)
    add("happy", [B(face=F(eyes="happy", mouth="big_smile", blush=True), **stop)], "sway", ["happy", "glad", "joy", "smile", "cheerful"], "Happy.")
    add("sad", [B(face=F(eyes="sad", brows="sad", mouth="frown"), **stop)], "slow", ["sad", "unhappy", "upset", "lonely"], "Sad.")
    add("scared", [B(face=F(eyes="wide", brows="worried", mouth="wavy", effects=["sweat"]), **stop)], "scared",
        ["scared", "afraid", "frightened", "wobbly", "nervous"], "Scared.")
    add("surprised", [B(face=F(eyes="wide", brows="raised", mouth="open", effects=["exclaim"]), **stop)], "surprised",
        ["surprised", "shocked", "wow", "amazed"], "Surprised.")
    add("laugh", [B(face=F(eyes="happy", mouth="laugh"), **stop)], "giggle", ["laugh", "laughed", "laughing", "funny", "giggle"], "Laughing.")
    add("angry", [B(face=F(eyes="angry", brows="angry", mouth="teeth", effects=["anger"]), **stop)], "tremble",
        ["angry", "mad", "cross", "grumpy"], "Angry.")
    add("love", [B(face=F(eyes="heart", mouth="big_smile", blush=True, effects=["hearts"]), **stop)], "sway",
        ["love", "loves", "loved", "favourite", "favorite"], "Loves the bike.")
    add("tired", [B(face=F(eyes="half", brows="sad", mouth="open", effects=["sweat"]), **stop, lean=38)], "slow",
        ["tired", "exhausted", "puff", "puffed", "breath"], "Out of breath.")
    add("sing", [B(face=F(eyes="happy", mouth="open", effects=["notes"]), crank=i * 90, spoke=i * SPOKE_STEP * 2) for i in range(4)],
        "ride", ["sing", "sang", "singing", "song", "whistle", "whistled"], "Singing while riding (4 frames).", hold=2)
    add("nohands", [B(face=F(eyes="star", mouth="laugh", effects=["sparkles"]), arms="up", crank=0, spoke=i * SPOKE_STEP) for i in range(3)],
        "drive", ["no hands", "look no hands", "show", "cheer", "cheered", "yay"], "Look, no hands!", hold=1)
    add("race", [B(face=F(brows="angry", mouth="grin"), number=True, lean=42, crank=i * 45, spoke=i * SPOKE_STEP, effects_extra=["speed"]) for i in range(8)],
        "ride", ["racing", "competition", "winner", "finish", "first"], "Racing with a number plate (8 frames).", hold=1)
    add("fall", [B(face=F(eyes="wide", brows="worried", mouth="shout", effects=["sweat"]), rider="flying", arms="up", tilt=12)], "shake",
        ["fall", "fell", "crash", "crashed", "tumble", "tumbled", "over the handlebars"], "Tumbling over the handlebars.")
    add("night", ride_cycle(F(mouth="smile"), effects_extra=["beam"]), "ride", ["night", "dark", "light", "lamp", "evening"],
        "Riding at night with the lamp on (8 frames).", hold=1)
    add("flat", [B(face=F(eyes="sad", brows="sad", mouth="open"), flat=True, **stop)], "slow",
        ["flat", "flat tire", "puncture", "punctured", "tyre", "tire"], "Flat tyre.")
    add("basket", ride_cycle(F(eyes="happy", mouth="smile", blush=True), basket=True), "ride",
        ["basket", "flowers", "deliver", "delivered", "shopping", "market", "carry", "carried"], "Riding with a basket of flowers (8 frames).", hold=1)
    add("parked", [B(rider="none", crank=200)], "still", ["parked", "park", "leave", "left", "alone", "empty"], "Bicycle parked on its own.")
    add("dizzy", [B(face=F(eyes="spiral", mouth="wavy", effects=["stars"]), **stop)], "sway", ["dizzy", "wobble", "wobbled", "bumpy"], "Dizzy.")
    return X
