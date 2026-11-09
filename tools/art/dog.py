"""Parametric cartoon dog (side view, facing right) and its expressions."""

from dataclasses import dataclass, field

from . import kit
from .face import Face, FaceDrawer, FaceLayout
from .human import place, two_bone_ik
from .kit import Layer
from .people import Expr

FUR = kit.rgb("#f1dcb8")
PATCH = kit.rgb("#9c6238")
EAR = kit.rgb("#7e4a2a")
COLLAR = kit.rgb("#e0453a")
NOSE = kit.rgb("#3a2c2f")
OW = 9.0

BODY_RX, BODY_RY = 165, 92
HEAD_R = 92
UPPER, LOWER = 70, 72
LEG_W = 42


@dataclass
class DogPose:
    face: Face = field(default_factory=lambda: Face(mouth="smile"))
    pitch: float = 0.0  # body rotation, + = nose down (clockwise)
    front_near: tuple = (2.0, 0.0)
    front_far: tuple = (-2.0, -2.0)
    hind_near: tuple = (-4.0, 8.0)
    hind_far: tuple = (4.0, 12.0)
    head: tuple = (0.0, 0.0)  # head offset from its usual place
    head_tilt: float = 0.0
    ear: float = 0.0  # ear swing: + = flaps back/up, - = droops forward
    tail: float = 40.0  # tail angle: 180 = straight up, 90 = straight back
    tail_curl: float = 25.0
    air: float = 0.0
    crouch: float = 0.0  # lowers the body towards the ground
    plant_front: bool = False  # IK the front legs down to the ground
    prop: str | None = None  # ball bowl dirt
    effects_extra: list = field(default_factory=list)  # sound, speed, hackles, dirt
    rotate: float = 0.0  # rotate the finished drawing (roll over)


def _leg(L: Layer, root, angles, colour, paw=True):
    knee = kit.along(root, angles[0], UPPER)
    foot = kit.along(knee, angles[1], LOWER)
    L.limb([root, knee, foot], LEG_W, colour)
    if paw:
        L.ellipse(foot[0] + 10, foot[1] + 4, 30, 18, colour)
    return foot


def draw_dog(pose: DogPose):
    body = Layer(OW)
    fx = Layer(OW)
    b = (512.0, 560.0 + pose.crouch)
    R = lambda u, v: kit.rot((b[0] + u, b[1] + v), pose.pitch, b)
    front_root = R(110, 30)
    hind_root = R(-115, 30)
    head = R(178 + pose.head[0], -88 + pose.head[1])
    far = lambda c: kit.shade(c, 0.82)

    legs = {"front_near": pose.front_near, "front_far": pose.front_far, "hind_near": pose.hind_near, "hind_far": pose.hind_far}
    if pose.plant_front:
        floor = max(kit.along(kit.along(hind_root, pose.hind_near[0], UPPER), pose.hind_near[1], LOWER)[1],
                    b[1] + BODY_RY * 0.9)
        for key, dx in (("front_near", 18), ("front_far", -10)):
            target = (front_root[0] + dx, floor - 6)
            legs[key] = two_bone_ik(front_root, target, UPPER, LOWER, bend=1)

    # tail (behind the body)
    base = R(-150, -35)
    mid = kit.along(base, pose.tail, 75)
    tip = kit.along(mid, pose.tail + pose.tail_curl, 70)
    body.limb([base, mid, tip], 30, FUR)
    body.circle(tip[0], tip[1], 16, PATCH, outline=False)

    # far legs
    fl = _leg(body, kit.lerp(front_root, R(110, 30), 1.0), legs["front_far"], far(FUR))
    hl = _leg(body, R(-105, 30), legs["hind_far"], far(FUR))

    # body
    body.ellipse(b[0], b[1], BODY_RX, BODY_RY, FUR, angle=pose.pitch)
    px, py = R(-40, -35)
    body.ellipse(px, py, 62, 44, PATCH, angle=pose.pitch - 10, ow=0)
    if "hackles" in pose.effects_extra:
        for i in range(5):
            p = R(-60 + i * 35, -BODY_RY + 8)
            body.poly([kit.rot((p[0] - 14, p[1] + 8), pose.pitch, p), kit.rot((p[0], p[1] - 26), pose.pitch, p),
                       kit.rot((p[0] + 14, p[1] + 8), pose.pitch, p)], FUR, ow=OW * 0.7)

    # near legs
    fn = _leg(body, front_root, legs["front_near"], FUR)
    hn = _leg(body, R(-120, 35), legs["hind_near"], FUR)
    body.ellipse(*R(-118, 20), 48, 58, FUR, angle=pose.pitch)  # haunch

    # neck + collar + head
    neck_a = R(128, -40)
    body.limb([neck_a, kit.lerp(neck_a, head, 0.7)], 88, FUR)
    collar = kit.lerp(neck_a, head, 0.45)
    body.ellipse(collar[0], collar[1], 16, 46, COLLAR, angle=pose.pitch - 20)
    body.circle(collar[0] + 4, collar[1] + 44, 13, kit.GOLD, ow=OW * 0.6)

    hx, hy = head
    tilt = pose.head_tilt + pose.pitch * 0.6
    P = lambda u, v: kit.rot((hx + u * HEAD_R, hy + v * HEAD_R), tilt, (hx, hy))
    body.circle(hx, hy, HEAD_R, FUR)
    sx, sy = P(0.78, 0.38)
    body.ellipse(sx, sy, 0.72 * HEAD_R, 0.48 * HEAD_R, FUR, angle=tilt)
    nx, ny = P(1.42, 0.22)
    body.ellipse(nx, ny, 0.2 * HEAD_R, 0.15 * HEAD_R, NOSE, angle=tilt)
    body.circle(nx + 0.05 * HEAD_R, ny - 0.06 * HEAD_R, 0.05 * HEAD_R, kit.WHITE, outline=False)
    # floppy ear (near side)
    ea = P(-0.62, -0.5)
    ear_angle = -8 - 0.9 * max(-30.0, min(70.0, pose.ear)) + tilt
    tipp = kit.along(ea, ear_angle, 112)
    body.limb([ea, kit.lerp(ea, tipp, 0.5), tipp], 58, EAR)

    layout = FaceLayout(eye_x=0.3, eye_dx=0.2, eye_y=-0.18, eye_rx=0.14, eye_ry=0.18, iris=kit.rgb("#5b3a29"),
                        mouth_x=0.95, mouth_y=0.72, mouth_w=0.34, brow_y=-0.48, skin=FUR, nose=False, far_eye_scale=0.85)
    face = FaceDrawer(body, hx, hy, HEAD_R, layout, tilt=tilt)
    f = pose.face
    face.eyes(f.eyes)
    face.brows(f.brows)
    if f.blush:
        face.blush()
    face.mouth(f.mouth)

    # props and effects
    if pose.prop == "ball":
        mx, my = P(1.05, 0.62)
        body.circle(mx, my, 40, kit.rgb("#ff7043"))
        body.arc(mx, my, 40, 16, 180, 360, OW * 0.8)
    if pose.prop == "bowl":
        bx, by = P(1.0, 1.1)
        body.poly(kit.trapezoid_points((bx, by - 30), (bx, by + 30), 170, 120, 14), kit.rgb("#4a90d9"))
        body.ellipse(bx, by - 30, 80, 14, kit.rgb("#b5793e"))
    for e in pose.effects_extra:
        if e == "sound":
            kit.sound_arcs(fx, *P(1.6, 0.4), 60, OW, count=3)
        elif e == "speed":
            kit.motion_lines(fx, b[0] - BODY_RX - 40, b[1] - 20, 110, 40, 3, OW * 1.1)
        elif e == "dirt":
            for dx, dy, r in ((150, 90, 26), (200, 60, 20), (240, 100, 16), (120, 40, 14)):
                fx.circle(b[0] + dx + 60, b[1] + dy + 120, r, kit.rgb("#8d6e4a"), ow=OW * 0.6)
        elif e == "wag":
            kit.sound_arcs(fx, tip[0] - 10, tip[1], 45, OW * 0.9, count=2, facing=-1)
    FaceDrawer(fx, hx, hy, HEAD_R, layout, tilt=0).effects(f.effects)

    if pose.rotate:
        for layer in (body, fx):
            layer.image = layer.image.rotate(-pose.rotate, center=(b[0] * kit.SS, b[1] * kit.SS), resample=kit.Image.Resampling.BICUBIC)
            layer.draw = kit.ImageDraw.Draw(layer.image)
    paws_x = (fn[0] + fl[0] + hn[0] + hl[0]) / 4 + 10
    image, _ = place(body, fx, pose.air, 190, None if pose.rotate else paws_x)
    return image


def D(**kw) -> DogPose:
    return DogPose(**kw)


def F(**kw) -> Face:
    return Face(**kw)


def walk_cycle():
    f = F(mouth="smile")
    return [
        D(face=f, front_near=(22, 12), front_far=(-18, -22), hind_near=(-26, -10), hind_far=(18, 26), tail=60),
        D(face=f, front_near=(2, 0), front_far=(12, -30), hind_near=(-4, 8), hind_far=(-4, 30), tail=50),
        D(face=f, front_near=(-18, -22), front_far=(22, 12), hind_near=(18, 26), hind_far=(-26, -10), tail=60),
        D(face=f, front_near=(12, -30), front_far=(2, 0), hind_near=(-4, 30), hind_far=(-4, 8), tail=50),
    ]


def run_cycle():
    f = F(mouth="tongue", brows="focused")
    s = ["speed"]
    return [
        D(face=f, pitch=-4, front_near=(70, 55), front_far=(55, 40), hind_near=(-60, -35), hind_far=(-45, -20), tail=95, effects_extra=s, ear=50),
        D(face=f, pitch=2, front_near=(20, -40), front_far=(5, -50), hind_near=(30, 70), hind_far=(45, 80), tail=85, effects_extra=s, ear=40),
        D(face=f, pitch=4, front_near=(-30, -10), front_far=(-15, -5), hind_near=(60, 45), hind_far=(40, 40), tail=75, effects_extra=s, ear=30),
        D(face=f, pitch=0, front_near=(45, -20), front_far=(30, -30), hind_near=(-20, 40), hind_far=(-5, 50), tail=90, effects_extra=s, ear=45),
    ]


SIT = dict(pitch=-32, hind_near=(88, -80), hind_far=(82, -75), plant_front=True, head=(-20, -10), tail=100)


def sit(**overrides) -> dict:
    """Sitting pose with some settings changed."""
    return {**SIT, **overrides}


def dog_expressions() -> list[Expr]:
    X = []
    add = lambda *a, **k: X.append(Expr(*a, **k))
    happy = F(eyes="happy", mouth="big_smile")
    add("idle", [D()], "idle", ["stand", "standing", "wait", "waiting", "stay"], "Standing, tail relaxed.")
    add("walk", walk_cycle(), "walk", ["walk", "walking", "walked", "trot", "trotted", "go", "went"], "Walking (4 frames).", hold=3)
    add("run", run_cycle(), "run", ["run", "running", "ran", "chase", "chased", "race", "raced", "dash", "rush", "hurry"], "Galloping (4 frames).", hold=2)
    add("jump", [D(face=happy, pitch=-12, front_near=(85, 70), front_far=(70, 60), hind_near=(-70, -40), hind_far=(-55, -30), tail=120, ear=70, air=120)],
        "jump", ["jump", "jumping", "jumped", "leap", "leapt", "hop", "pounce"], "Leaping through the air.")
    add("sit", [D(face=F(mouth="smile"), **sit())], "idle", ["sit", "sitting", "sat", "rest", "rested"], "Sitting nicely.")
    add("lie", [D(face=F(mouth="smile"), crouch=60, front_near=(88, 92), front_far=(84, 90), hind_near=(92, -85), hind_far=(85, -80), tail=80, head=(10, 35))],
        "idle", ["lie", "lying", "lay", "lay down", "relax", "relaxed"], "Lying down, relaxed.")
    add("sleep", [D(face=F(eyes="closed", mouth="flat", effects=["zzz"]), crouch=60, front_near=(88, 92), front_far=(84, 90),
                    hind_near=(92, -85), hind_far=(85, -80), tail=60, tail_curl=60, head=(20, 85), head_tilt=8, ear=-20)],
        "sleep", ["fell asleep", "falls asleep", "fall asleep", "sleep", "sleeping", "asleep", "slept", "nap", "napped"], "Curled up asleep.")
    add("sleepy", [D(face=F(eyes="half", mouth="yawn"), **sit(ear=-15))], "slow", ["sleepy", "yawn", "yawned", "tired"], "Yawning.")
    add("beg", [D(face=F(eyes="open", mouth="tongue", blush=True), pitch=-72, hind_near=(90, -88), hind_far=(86, -84),
                  front_near=(130, 40), front_far=(120, 30), head=(-45, 10), tail=120)],
        "bounce", ["beg", "begged", "please", "treat", "want", "wanted"], "Sitting up, begging.")
    add("play", [D(face=happy, pitch=22, front_near=(80, 92), front_far=(76, 90), hind_near=(-6, 6), hind_far=(6, 10), tail=150, ear=20, head=(-10, 25))],
        "bounce", ["play", "playing", "played", "game", "fun", "bow"], "Play bow, ready to play.")
    add("rollover", [D(face=F(eyes="happy", mouth="tongue"), front_near=(35, -25), front_far=(20, -35), hind_near=(-35, 40),
                       hind_far=(-20, 50), tail=20, rotate=180)],
        "sway", ["roll", "rolled", "rolling", "belly", "tickle", "tickled"], "Rolling on its back.")
    add("sniff", [D(face=F(eyes="half", mouth="flat"), pitch=8, head=(30, 110), head_tilt=20, tail=140, front_near=(10, 5))],
        "sway", ["sniff", "sniffed", "smell", "smelled", "search", "searched", "track"], "Nose to the ground, sniffing.")
    add("dig", [D(face=F(eyes="happy", mouth="tongue"), pitch=16, head=(10, 50), front_near=(40, 60), front_far=(-10, 10), tail=150, effects_extra=["dirt"]),
                D(face=F(eyes="happy", mouth="tongue"), pitch=16, head=(10, 50), front_near=(-10, 10), front_far=(40, 60), tail=140, effects_extra=["dirt"])],
        "cycle", ["dig", "digging", "dug", "bury", "buried", "bone", "hole"], "Digging (2 frames).", hold=2)
    add("bark", [D(face=F(eyes="open", brows="raised", mouth="open"), head=(5, -15), head_tilt=-10, ear=30, tail=130, effects_extra=["sound"]),
                 D(face=F(eyes="open", brows="raised", mouth="smile"), head=(0, -8), head_tilt=-4, ear=15, tail=120)],
        "talk", ["bark", "barking", "barked", "woof", "call", "called", "say", "said", "talk"], "Barking (2 frames).", hold=3)
    add("howl", [D(face=F(eyes="closed", mouth="small_o", effects=["notes"]), **sit(head=(-40, -40), head_tilt=-40, ear=60))],
        "slow", ["howl", "howling", "howled", "sing", "sang", "moon", "awoo"], "Howling at the sky.")
    add("wag", [D(face=happy, tail=160, tail_curl=10, effects_extra=["wag"]),
                D(face=happy, tail=120, tail_curl=40, effects_extra=["wag"]),
                D(face=happy, tail=140, tail_curl=25, effects_extra=["wag"])],
        "cycle", ["wag", "wagging", "wagged", "tail", "friend", "welcome"], "Wagging its tail (3 frames).", hold=2)
    add("scratch", [D(face=F(eyes="closed", mouth="tongue"), **sit(hind_near=(150, 110), head_tilt=15, ear=-10))],
        "tremble", ["scratch", "scratching", "scratched", "itch", "itchy", "flea"], "Scratching an itch.")
    add("paw", [D(face=F(eyes="open", mouth="big_smile"), **sit(plant_front=False, front_near=(110, 95), front_far=(4, 4)))],
        "idle", ["paw", "shake", "high five", "give", "gave", "offer"], "Offering a paw.")
    add("fetch", [D(face=F(eyes="happy", mouth="flat"), prop="ball", tail=150, ear=10)],
        "bounce", ["fetch", "fetched", "ball", "bring", "brought", "catch", "caught", "toy"], "Ball in its mouth.")
    add("eat", [D(face=F(eyes="happy", mouth="tongue"), pitch=10, head=(25, 95), head_tilt=18, prop="bowl", tail=140)],
        "idle", ["eat", "eating", "ate", "food", "dinner", "lunch", "breakfast", "hungry", "bowl"], "Eating from a bowl.")
    add("happy", [D(face=F(eyes="happy", mouth="tongue", blush=True), tail=150, ear=10)], "sway",
        ["happy", "glad", "joy", "cheerful", "smile", "smiled", "good"], "Happy, tongue out.")
    add("excited", [D(face=F(eyes="star", mouth="big_smile", effects=["sparkles"]), pitch=-25, front_near=(95, 60), front_far=(85, 50), tail=160, ear=60)],
        "bounce", ["excited", "thrilled", "yay", "hooray"], "Jumping up with excitement.")
    add("sad", [D(face=F(eyes="sad", brows="sad", mouth="frown"), head=(10, 40), head_tilt=12, ear=-35, tail=10)],
        "slow", ["sad", "unhappy", "upset", "lonely", "miss", "missed"], "Ears and tail down.")
    add("cry", [D(face=F(eyes="closed", brows="sad", mouth="sob", effects=["tears"]), **sit(ear=-35))],
        "sob", ["cry", "crying", "cried", "whimper", "whine", "whined", "tears"], "Whimpering.")
    add("angry", [D(face=F(eyes="angry", brows="angry", mouth="teeth", effects=["anger"]), pitch=6, head=(20, 25), ear=-10, tail=150,
                    effects_extra=["hackles"])],
        "tremble", ["angry", "mad", "growl", "growled", "grr", "snarl"], "Growling, hackles up.")
    add("scared", [D(face=F(eyes="wide", brows="worried", mouth="wavy", effects=["sweat"]), crouch=30, pitch=-4, ear=-30, tail=-20,
                     front_near=(20, -10), hind_near=(20, 40), hind_far=(25, 45), head=(-20, 20))],
        "scared", ["scared", "afraid", "frightened", "fear", "hide", "hid", "thunder"], "Cowering, tail tucked.")
    add("surprised", [D(face=F(eyes="wide", brows="raised", mouth="open", effects=["exclaim"]), ear=60, tail=170, head=(-10, -20))],
        "surprised", ["surprised", "shocked", "amazed", "startled", "wow"], "Ears up, startled.")
    add("confused", [D(face=F(eyes="open", brows="worried", mouth="flat", effects=["question"]), **sit(head_tilt=-22, ear=30))],
        "sway", ["confused", "puzzled", "curious", "wonder", "wondered", "huh"], "Head tilted, puzzled.")
    add("love", [D(face=F(eyes="heart", mouth="big_smile", blush=True, effects=["hearts"]), **sit(tail=150))],
        "sway", ["love", "loves", "loved", "hug", "hugged", "cuddle", "kiss", "lick", "licked"], "In love.")
    add("guilty", [D(face=F(eyes="side", brows="sad", mouth="wavy"), head=(10, 35), ear=-35, tail=5, crouch=15)],
        "slow", ["guilty", "naughty", "sorry", "oops", "mess", "broke", "chewed"], "Looking guilty.")
    add("laugh", [D(face=F(eyes="happy", mouth="laugh"), **sit(head_tilt=-10))],
        "giggle", ["laugh", "laughing", "laughed", "funny", "joke"], "Laughing.")
    add("dizzy", [D(face=F(eyes="spiral", mouth="wavy", effects=["stars"]), head_tilt=14, tail=60, pitch=3)],
        "sway", ["dizzy", "spin", "spun", "bump", "bumped", "wobbly"], "Dizzy, seeing stars.")
    add("proud", [D(face=F(eyes="happy", mouth="smile", effects=["sparkles"]), head=(0, -25), head_tilt=-15, tail=170, ear=10)],
        "idle", ["proud", "brave", "good boy", "good dog", "win", "won", "hero"], "Nose up, proud.")
    return X
