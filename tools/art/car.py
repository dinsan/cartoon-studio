"""Cartoon car with a face (side view, facing right) and its expressions."""

import math
from dataclasses import dataclass, field

from . import kit
from .face import Face, FaceDrawer, FaceLayout
from .human import place
from .kit import GROUND, Layer
from .people import Expr

PAINT = kit.rgb("#e8473b")
GLASS = kit.rgb("#bfe6fb")
TYRE = kit.rgb("#35323d")
HUB = kit.rgb("#d9dbe3")
TRIM = kit.rgb("#9ea3b5")
OW = 8.0

WHEEL_R = 92
WHEELS = (250.0, 770.0)  # x of rear and front wheel
AXLE_Y = 808.0
SPOKES = 5
DRIVE_STEP = 24.0  # degrees of hub rotation per drawing (period 72 / 3 frames)


@dataclass
class CarPose:
    face: Face = field(default_factory=lambda: Face(mouth="smile"))
    spoke: float = 0.0  # hub rotation (degrees, clockwise)
    tilt: float = 0.0  # body pitch, + = nose down
    bounce: float = 0.0  # body offset on its suspension (+ = down)
    blur: bool = False  # fast wheels
    flat: bool = False  # flat front tyre
    air: float = 0.0
    effects_extra: list = field(default_factory=list)
    paint: tuple = PAINT


def _wheel(L: Layer, x, spoke, blur=False, flat=False):
    y = AXLE_Y
    if flat:
        L.ellipse(x, y + 22, WHEEL_R * 1.12, WHEEL_R * 0.72, TYRE)
        L.circle(x, y + 10, WHEEL_R * 0.5, HUB)
        return
    L.circle(x, y, WHEEL_R, TYRE)
    L.circle(x, y, WHEEL_R * 0.56, HUB)
    if blur:
        for rr in (0.42, 0.3):
            L.arc(x, y, WHEEL_R * rr, WHEEL_R * rr, 0, 360, OW * 0.8, TRIM)
    else:
        for i in range(SPOKES):
            a = spoke + i * 360 / SPOKES
            p = (x + WHEEL_R * 0.44 * math.cos(math.radians(a)), y + WHEEL_R * 0.44 * math.sin(math.radians(a)))
            L.line([(x, y), p], OW * 1.4, TRIM)
    L.circle(x, y, WHEEL_R * 0.14, TRIM, ow=OW * 0.7)


def draw_car(pose: CarPose):
    body = Layer(OW)
    fx = Layer(OW)
    pivot = (512.0, 760.0)
    T = lambda x, y: kit.rot((x, y + pose.bounce), pose.tilt, pivot)
    paint = pose.paint

    # wheel arches (behind wheels) and wheels
    for wx in WHEELS:
        body.ellipse(*T(wx, AXLE_Y - 10), WHEEL_R * 1.2, WHEEL_R * 1.1, kit.shade(TYRE, 0.8), angle=pose.tilt)
    # body
    lower = [(95, 790), (95, 660), (150, 615), (330, 600), (720, 600), (870, 622), (930, 665), (935, 790)]
    cabin = [(300, 610), (375, 445), (600, 432), (660, 440), (760, 608)]
    body.poly(kit.rounded_polygon([T(*p) for p in cabin], 40), paint)
    body.poly(kit.rounded_polygon([T(*p) for p in lower], 45), paint)
    # windows
    rear_win = [(340, 598), (392, 470), (470, 462), (470, 598)]
    front_win = [(492, 598), (492, 458), (600, 450), (652, 458), (738, 598)]
    body.poly(kit.rounded_polygon([T(*p) for p in rear_win], 20), GLASS, ow=OW * 0.8)
    body.poly(kit.rounded_polygon([T(*p) for p in front_win], 24), GLASS, ow=OW * 0.8)
    # doors, handle, lights, bumpers
    body.line([T(480, 610), T(482, 770)], OW * 0.8)
    body.poly(kit.rounded_rect_points(*T(430, 640), 46, 14, 6, angle=pose.tilt), TRIM, ow=OW * 0.6)
    body.ellipse(*T(905, 672), 26, 22, kit.GOLD, angle=pose.tilt)
    body.ellipse(*T(108, 672), 14, 24, kit.rgb("#ff8a65"), angle=pose.tilt)
    body.poly(kit.rounded_rect_points(*T(935, 765), 46, 34, 14, angle=pose.tilt), TRIM)
    body.poly(kit.rounded_rect_points(*T(92, 765), 40, 34, 14, angle=pose.tilt), TRIM)
    if "number" in pose.effects_extra:
        cx, cy = T(340, 700)
        body.circle(cx, cy, 52, kit.WHITE)
        body.line([(cx - 8, cy - 28), (cx + 6, cy - 36), (cx + 6, cy + 34)], OW * 1.6)
    if "mud" in pose.effects_extra:
        for mx, my, r in ((200, 720, 30), (330, 760, 22), (560, 700, 26), (650, 760, 18), (820, 710, 24), (150, 650, 16)):
            body.ellipse(*T(mx, my), r * 1.3, r, kit.rgb("#8d6e4a"), angle=20, ow=OW * 0.5)

    # face: eyes in the front window, mouth on the front wing
    layout = FaceLayout(eye_x=0.0, eye_dx=0.36, eye_y=0.05, eye_rx=0.29, eye_ry=0.38, iris=kit.rgb("#3d5a80"),
                        mouth_x=2.5, mouth_y=2.0, mouth_w=1.1, brow_y=-0.42, skin=paint, nose=False, far_eye_scale=0.92)
    fcx, fcy = T(598, 522)
    face = FaceDrawer(body, fcx, fcy, 100, layout, tilt=pose.tilt, line=OW * 1.15)
    f = pose.face
    face.eyes(f.eyes)
    face.brows(f.brows)
    if f.blush:
        face.blush()
    face.mouth(f.mouth)

    for wx in WHEELS:
        _wheel(body, wx, pose.spoke, pose.blur, pose.flat and wx == WHEELS[1])

    # effects
    for e in pose.effects_extra:
        if e == "speed":
            kit.motion_lines(fx, 78, 700, 70, 42, 3, OW * 1.3)
        elif e == "smoke":
            for i, (dx, dy, r) in enumerate(((40, -60, 40), (90, -120, 52), (30, -170, 36))):
                kit.puff(fx, *T(820 + dx, 560 + dy), r, (120, 120, 130, 255) if i == 1 else (170, 170, 180, 255))
        elif e == "exhaust":
            kit.puff(fx, 45, 770, 30, (200, 200, 210, 255))
            kit.puff(fx, 10, 735, 22, (220, 220, 228, 255))
        elif e == "dust":
            for dx, r in ((-120, 34), (-70, 26), (-170, 22)):
                kit.puff(fx, WHEELS[1] + dx, GROUND - r * 0.8, r, (215, 190, 150, 255))
                kit.puff(fx, WHEELS[0] + dx, GROUND - r * 0.8, r * 0.8, (215, 190, 150, 255))
        elif e == "honk":
            kit.sound_arcs(fx, *T(960, 690), 70, OW * 1.3, count=3)
        elif e == "beam":
            hx, hy = T(930, 672)
            for a in (-14, -4, 6, 16):
                fx.line([(hx + 20, hy + a * 0.8), (hx + 120, hy + a * 4.5)], OW * 1.2, kit.rgb("#fff2a8"))
        elif e == "bubbles":
            for bx, by, r in ((200, 520, 30), (280, 440, 22), (700, 420, 34), (860, 560, 24), (120, 600, 20), (450, 400, 26)):
                fx.circle(bx, by, r, kit.rgb("#e3f6ff"), ow=OW * 0.6)
                fx.circle(bx - r * 0.3, by - r * 0.3, r * 0.25, kit.WHITE, outline=False)
        elif e == "steam":
            for dx in (0, 60):
                kit.puff(fx, *T(840 + dx, 540 - dx * 0.6), 34, (235, 235, 240, 255))
        elif e == "stars":
            for i in range(4):
                kit.star(fx, 470 + i * 90, 370 - 30 * math.sin(i * 1.3), 26)
        elif e == "bump":
            kit.motion_lines(fx, 300, GROUND - 30, 60, 26, 2, OW)
    FaceDrawer(fx, fcx, fcy - 40, 100, layout, tilt=0).effects(f.effects)
    image, _ = place(body, fx, pose.air, 420, 510)
    return image


def C(**kw) -> CarPose:
    return CarPose(**kw)


def F(**kw) -> Face:
    return Face(**kw)


def car_expressions() -> list[Expr]:
    X = []
    add = lambda *a, **k: X.append(Expr(*a, **k))
    drive = lambda face, **kw: [C(face=face, spoke=i * DRIVE_STEP, **kw) for i in range(3)]
    add("idle", [C(face=F(mouth="smile"), effects_extra=["exhaust"])], "engine",
        ["park", "parked", "wait", "waiting", "stop", "stopped", "engine"], "Parked with the engine running.")
    add("drive", drive(F(mouth="big_smile")), "drive", ["drive", "driving", "drove", "go", "went", "ride", "road", "trip", "travel"],
        "Driving along (wheels turn, 3 frames).", hold=1)
    add("fast", [C(face=F(eyes="open", brows="focused", mouth="grin"), blur=True, tilt=-2, effects_extra=["speed"]),
                 C(face=F(eyes="open", brows="focused", mouth="grin"), blur=True, tilt=-2, bounce=3, effects_extra=["speed"])],
        "drive_fast", ["fast", "speed", "speeding", "zoom", "zoomed", "race", "raced", "hurry", "rush"], "Zooming at top speed.", hold=2)
    add("reverse", [C(face=F(eyes="side", mouth="wavy"), spoke=-i * DRIVE_STEP) for i in range(3)], "reverse",
        ["reverse", "reversed", "back up", "backed", "backwards"], "Reversing carefully (3 frames).", hold=1)
    add("brake", [C(face=F(eyes="wide", brows="worried", mouth="teeth"), tilt=4, effects_extra=["dust"])], "brake",
        ["brake", "braked", "stop suddenly", "screech", "skid", "skidded", "halt"], "Slamming on the brakes.")
    add("honk", [C(face=F(eyes="happy", mouth="shout"), effects_extra=["honk"]), C(face=F(eyes="happy", mouth="smile"))],
        "talk", ["honk", "honked", "beep", "toot", "horn", "say", "said", "call", "called"], "Honking the horn (2 frames).", hold=3)
    add("lights", [C(face=F(eyes="open", mouth="smile"), effects_extra=["beam"])], "engine",
        ["lights", "headlights", "dark", "night", "tunnel", "shine"], "Headlights on.")
    add("jump", [C(face=F(eyes="wide", mouth="laugh"), tilt=-6, air=110, effects_extra=["bump"])], "jump",
        ["jump", "jumped", "fly", "flew", "ramp", "bump", "bumped"], "Flying off a bump.")
    add("bounce", [C(face=F(eyes="happy", mouth="big_smile"), bounce=-10)], "bounce",
        ["bounce", "bounced", "bouncy", "dance", "danced", "music", "excited"], "Bouncing on its springs.")
    add("happy", [C(face=F(eyes="happy", mouth="big_smile", blush=True))], "sway", ["happy", "glad", "smile", "joy", "cheerful"], "Happy.")
    add("sad", [C(face=F(eyes="sad", brows="sad", mouth="frown"), bounce=8)], "slow", ["sad", "unhappy", "upset", "lonely"], "Sad.")
    add("cry", [C(face=F(eyes="closed", brows="sad", mouth="sob", effects=["tears"]), bounce=8)], "sob",
        ["cry", "crying", "cried", "tears", "sob"], "Crying.")
    add("angry", [C(face=F(eyes="angry", brows="angry", mouth="teeth"), effects_extra=["steam"])], "tremble",
        ["angry", "mad", "furious", "grumpy", "cross"], "Angry, steaming.")
    add("surprised", [C(face=F(eyes="wide", brows="raised", mouth="open", effects=["exclaim"]))], "surprised",
        ["surprised", "shocked", "amazed", "wow", "startled"], "Surprised.")
    add("scared", [C(face=F(eyes="wide", brows="worried", mouth="wavy", effects=["sweat"]), tilt=-3)], "scared",
        ["scared", "afraid", "frightened", "fear", "nervous"], "Scared.")
    add("laugh", [C(face=F(eyes="happy", mouth="laugh"))], "giggle", ["laugh", "laughing", "laughed", "funny", "joke", "giggle"], "Laughing.")
    add("sleep", [C(face=F(eyes="closed", mouth="small_o", effects=["zzz"]), bounce=6)], "sleep",
        ["fell asleep", "falls asleep", "fall asleep", "sleep", "sleeping", "asleep", "slept", "nap", "garage", "rest", "rested"], "Asleep in the garage.")
    add("sleepy", [C(face=F(eyes="half", mouth="yawn"), bounce=4)], "slow", ["sleepy", "tired", "yawn", "yawned"], "Sleepy.")
    add("wink", [C(face=F(eyes="wink", mouth="smirk"))], "idle", ["wink", "winked", "cool", "okay", "great"], "Winking.")
    add("love", [C(face=F(eyes="heart", mouth="big_smile", blush=True, effects=["hearts"]))], "sway",
        ["love", "loves", "loved", "friend", "friends"], "In love.")
    add("dizzy", [C(face=F(eyes="spiral", mouth="wavy"), tilt=2, effects_extra=["stars"])], "sway",
        ["dizzy", "spin", "spun", "wobbly", "round and round"], "Dizzy.")
    add("confused", [C(face=F(eyes="side", brows="worried", mouth="flat", effects=["question"]))], "sway",
        ["confused", "lost", "puzzled", "which way", "map"], "Lost and confused.")
    add("proud", [C(face=F(eyes="happy", mouth="smirk", effects=["sparkles"]), bounce=-4)], "idle",
        ["proud", "shiny", "new", "clean", "win", "won"], "Proud and shiny.")
    add("worried", [C(face=F(eyes="open", brows="worried", mouth="wavy", effects=["sweat"]))], "tremble",
        ["worried", "anxious", "late", "traffic"], "Worried.")
    add("breakdown", [C(face=F(eyes="x", mouth="frown"), bounce=10, effects_extra=["smoke"])], "tremble",
        ["break", "broke", "broken", "breakdown", "smoke", "smoking", "engine trouble"], "Broken down, smoke from the engine.")
    add("flat", [C(face=F(eyes="wide", brows="worried", mouth="open"), flat=True, tilt=3)], "slow",
        ["flat", "flat tire", "puncture", "punctured", "tyre", "tire"], "Flat tyre!")
    add("wash", [C(face=F(eyes="happy", mouth="big_smile"), paint=kit.shade(PAINT, 1.05), effects_extra=["bubbles"])], "sway",
        ["wash", "washed", "washing", "bubbles", "soap", "clean"], "Getting a bubbly wash.")
    add("muddy", [C(face=F(eyes="wink", mouth="tongue"), effects_extra=["mud"])], "bounce",
        ["mud", "muddy", "dirty", "puddle", "splash", "splashed"], "Covered in mud.")
    add("crash", [C(face=F(eyes="spiral", brows="worried", mouth="sob"), tilt=5, bounce=6, effects_extra=["stars", "smoke"])], "shake",
        ["crash", "crashed", "hit", "bang", "accident"], "Bump! A little crash.")
    add("race", [C(face=F(eyes="open", brows="angry", mouth="grin"), spoke=i * DRIVE_STEP, effects_extra=["number", "speed"]) for i in range(3)],
        "drive_fast", ["racing", "race car", "competition", "finish", "winner"], "Racing with a number on the door.", hold=1)
    return X
