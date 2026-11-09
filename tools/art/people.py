"""Kid and adult characters: styles and expression poses."""

from dataclasses import dataclass, field

from . import kit
from .face import Face
from .human import HumanDrawer, HumanPose, HumanStyle


@dataclass
class Expr:
    """One expression: one or more drawings plus how the app animates it."""

    name: str
    frames: list  # poses (or drawing callables) -> one PNG each
    motion: str
    keywords: list
    description: str
    hold: int | None = None  # video frames per drawing for cycles
    extra: dict = field(default_factory=dict)


KID = HumanStyle(
    head_r=118, neck=18, torso_h=185, torso_w_top=150, torso_w_bottom=165, hip_w=125,
    upper_arm=100, forearm=92, arm_w=42, thigh=118, shin=112, leg_w=50, foot_len=72, hand_r=27,
    skin=kit.rgb("#f6c9a4"), hair=kit.rgb("#7a4a2a"), shirt=kit.rgb("#ffcc33"), pants=kit.rgb("#4a7bd6"),
    shoes=kit.rgb("#e84d4d"), iris=kit.rgb("#5a8f3c"), socks=kit.rgb("#ffffff"), hair_style="pigtails", ow=9,
)

ADULT = HumanStyle(
    head_r=74, neck=20, torso_h=212, torso_w_top=160, torso_w_bottom=138, hip_w=118,
    upper_arm=122, forearm=108, arm_w=39, thigh=145, shin=138, leg_w=48, foot_len=75, hand_r=23,
    skin=kit.rgb("#e0a77f"), hair=kit.rgb("#3b2a24"), shirt=kit.rgb("#8cc3ef"), pants=kit.rgb("#3d4a78"),
    shoes=kit.rgb("#6d4c41"), iris=kit.rgb("#5b3a29"), hair_style="short", long_sleeves=True, long_pants=True,
    tie=kit.rgb("#d64545"), glasses=True, ow=7,
)


def P(**kw) -> HumanPose:
    return HumanPose(**kw)


def F(**kw) -> Face:
    return Face(**kw)


def points(style: HumanStyle):
    """Handy canvas points on the default standing skeleton (pre-grounding)."""
    j = HumanDrawer(style).skeleton(HumanPose(), (512.0, 560.0))
    r = style.head_r
    hx, hy = j["head"]
    return {
        "chin": (hx + r * 0.35, hy + r * 0.95),
        "mouth": (hx + r * 0.75, hy + r * 0.45),
        "ear": (hx + r * 0.05, hy + r * 0.1),
        "eyes": (hx + r * 0.45, hy - r * 0.05),
        "chest": (j["neck"][0] + style.torso_w_top * 0.55, j["neck"][1] + style.torso_h * 0.3),
        "belly": (j["hip"][0] + style.torso_w_bottom * 0.45, j["hip"][1] - style.torso_h * 0.3),
        "hip_front": (j["hip"][0] + style.hip_w * 0.5, j["hip"][1] - style.torso_h * 0.05),
        "hip_back": (j["hip"][0] - style.hip_w * 0.55, j["hip"][1] - style.torso_h * 0.05),
        "forehead": (hx + r * 0.5, hy - r * 0.45),
    }


def walk_cycle(face, lean=2.0, arms=1.0, **extra):
    a = arms
    return [
        P(face=face, lean=lean, leg_front=(24, 20), leg_back=(-24, -34), arm_front=(-28 * a, -16 * a), arm_back=(28 * a, 40 * a), **extra),
        P(face=face, lean=lean, leg_front=(2, 0), leg_back=(16, -28), arm_front=(-4, 4), arm_back=(4, 10), **extra),
        P(face=face, lean=lean, leg_front=(-24, -34), leg_back=(24, 20), arm_front=(28 * a, 40 * a), arm_back=(-28 * a, -16 * a), **extra),
        P(face=face, lean=lean, leg_front=(16, -28), leg_back=(2, 0), arm_front=(4, 10), arm_back=(-4, 4), **extra),
    ]


def run_cycle(face):
    fx = ["speed"]
    return [
        P(face=face, lean=14, leg_front=(38, 16), leg_back=(-42, -80), arm_front=(-50, 40), arm_back=(50, 135), effects_extra=fx),
        P(face=face, lean=14, leg_front=(62, -8), leg_back=(-18, -95), arm_front=(-12, 80), arm_back=(12, 100), effects_extra=fx),
        P(face=face, lean=14, leg_front=(-42, -80), leg_back=(38, 16), arm_front=(50, 135), arm_back=(-50, 40), effects_extra=fx),
        P(face=face, lean=14, leg_front=(-18, -95), leg_back=(62, -8), arm_front=(12, 100), arm_back=(-12, 80), effects_extra=fx),
    ]


def person_expressions(style: HumanStyle, adult: bool) -> list[Expr]:
    pt = points(style)
    up = dict(arm_back=(-140, -160), arm_front=(135, 160))
    hips = dict(hand_targets=(pt["hip_back"], pt["hip_front"]))
    happy = F(eyes="happy", mouth="big_smile", blush=True)
    X = []
    add = lambda *a, **k: X.append(Expr(*a, **k))

    # Feelings ----------------------------------------------------------------
    add("idle", [P()], "idle", ["stand", "standing", "wait", "waiting", "stay"], "Standing, relaxed smile.")
    add("happy", [P(face=happy, arm_back=(-25, -15), arm_front=(30, 20))], "sway",
        ["happy", "glad", "smile", "smiling", "cheerful", "joy"], "Big smile with rosy cheeks.")
    add("excited", [P(face=F(eyes="star", mouth="laugh", effects=["sparkles"]), arm_back=(-135, -155), arm_front=(130, 150), air=40)],
        "bounce", ["excited", "thrilled", "yay", "hooray"], "Star eyes, bouncing with arms up.")
    add("sad", [P(face=F(eyes="sad", brows="sad", mouth="frown"), head_tilt=12, lean=4, arm_back=(-4, -2), arm_front=(2, 4))],
        "slow", ["sad", "unhappy", "upset", "lonely", "sorry"], "Droopy eyes and a frown.")
    add("cry", [P(face=F(eyes="closed", brows="sad", mouth="sob", effects=["tears"]), head_tilt=8,
                  hand_targets=(pt["eyes"], (pt["eyes"][0] + 25, pt["eyes"][1] + 10)))],
        "sob", ["cry", "crying", "cried", "tears", "weep", "sob"], "Crying with hands at the eyes.")
    add("angry", [P(face=F(eyes="angry", brows="angry", mouth="teeth", effects=["anger"]), lean=6,
                    arm_back=(-35, -10), arm_front=(35, 10), hands=("fist", "fist"))],
        "tremble", ["angry", "mad", "furious", "cross", "grumpy"], "Clenched fists and teeth.")
    add("surprised", [P(face=F(eyes="wide", brows="raised", mouth="open", effects=["exclaim"]), lean=-6,
                        arm_back=(-60, -100), arm_front=(60, 120), hands=("open", "open"))],
        "surprised", ["surprised", "shocked", "amazed", "wow", "astonished"], "Wide eyes, open mouth.")
    add("scared", [P(face=F(eyes="wide", brows="worried", mouth="wavy", effects=["sweat"]), lean=-10,
                     hand_targets=((pt["chest"][0] + 40, pt["chest"][1] - 40), (pt["chest"][0] + 80, pt["chest"][1] - 70)),
                     hands=("open", "open"))],
        "scared", ["scared", "afraid", "frightened", "fear", "terrified"], "Leaning away, hands up, sweating.")
    add("laugh", [P(face=F(eyes="happy", mouth="laugh", blush=True), lean=-8, head_tilt=-8,
                    hand_targets=(pt["belly"], (pt["belly"][0] + 30, pt["belly"][1] + 10)))],
        "giggle", ["laugh", "laughing", "laughed", "giggle", "funny", "haha"], "Laughing, holding the tummy.")
    add("think", [P(face=F(eyes="up", brows="raised", mouth="flat", effects=["question"]),
                    hand_targets=(pt["hip_back"], pt["chin"]), hands=("mitt", "point"))],
        "idle", ["think", "thinking", "thought", "wonder", "hmm"], "Hand on chin, thinking.")
    if not adult:
        add("idea", [P(face=F(eyes="open", brows="raised", mouth="big_smile", effects=["bulb"]), arm_front=(120, 175), hands=("mitt", "point"))],
            "surprised", ["idea", "realize", "realized", "remember", "aha"], "Finger up with a light bulb.")
    add("confused", [P(face=F(eyes="side", brows="worried", mouth="wavy", effects=["question"]), head_tilt=-12,
                       arm_back=(-70, -150), arm_front=(70, 150), hands=("open", "open"))],
        "sway", ["confused", "puzzled", "unsure", "lost", "shrug"], "Shrugging, head tilted.")
    add("shy", [P(face=F(eyes="side", brows="sad", mouth="smile", blush=True), head_tilt=10,
                  arm_back=(25, 50), arm_front=(-20, -40))],
        "sway", ["shy", "embarrassed", "blush", "blushed", "timid"], "Blushing, looking away.")
    add("love", [P(face=F(eyes="heart", mouth="big_smile", blush=True, effects=["hearts"]),
                   hand_targets=(pt["chest"], (pt["chest"][0] + 20, pt["chest"][1] - 5)))],
        "sway", ["love", "loves", "loved", "adore", "hug", "heart"], "Heart eyes, hands on heart.")
    add("worried", [P(face=F(eyes="open", brows="worried", mouth="wavy", effects=["sweat"]),
                      hand_targets=(pt["chest"], (pt["chest"][0] + 10, pt["chest"][1] + 15)))],
        "tremble", ["worried", "nervous", "anxious", "worry"], "Nervous frown, hands together.")
    add("tired", [P(face=F(eyes="half", brows="sad", mouth="open", effects=["sweat"]), lean=14, head_tilt=10,
                    arm_back=(-2, 0), arm_front=(2, 0))],
        "slow", ["tired", "exhausted", "weary", "sleepy"], "Slumped and out of breath.")
    add("yawn", [P(face=F(eyes="closed", mouth="yawn"), lean=-6, arm_back=(-145, -175), arm_front=(140, 170))],
        "slow", ["yawn", "yawning", "yawned", "stretch", "stretching"], "Stretching with a big yawn.")
    add("sleep", [P(face=F(eyes="closed", mouth="small_o", effects=["zzz"]), body_angle=-90,
                    arm_back=(4, 4), arm_front=(6, 6), leg_back=(0, 0), leg_front=(2, 2))],
        "sleep", ["fell asleep", "falls asleep", "fall asleep", "sleep", "sleeping", "asleep", "slept", "nap", "bed"], "Lying down asleep.")
    add("wink", [P(face=F(eyes="wink", mouth="smirk"), arm_front=(120, 170), hands=("mitt", "thumb"))],
        "idle", ["wink", "winked", "thumbs", "okay", "great", "cool"], "Wink and thumbs up.")
    if not adult:
        add("silly", [P(face=F(eyes="wink", mouth="tongue", blush=True), head_tilt=-10, arm_back=(-100, -150), arm_front=(100, 150),
                        hands=("open", "open"))],
            "bounce", ["silly", "funny face", "tease", "teasing", "joke"], "Tongue out, pulling a funny face.")
    add("proud", [P(face=F(eyes="happy", brows="raised", mouth="smirk", effects=["sparkles"]), lean=-6, head_tilt=-8, **hips)],
        "idle", ["proud", "brave", "strong", "win", "won"], "Hands on hips, chin up.")

    # Talking -----------------------------------------------------------------
    add("talk", [P(face=F(mouth="talk"), arm_front=(60, 110), hands=("mitt", "open")),
                 P(face=F(mouth="smile"), arm_front=(50, 95), hands=("mitt", "open"))],
        "talk", ["talk", "talking", "say", "said", "says", "tell", "told", "speak", "ask", "asked"], "Talking with a hand gesture.", hold=3)
    add("shout", [P(face=F(eyes="closed", brows="angry", mouth="shout"), lean=10,
                    hand_targets=((pt["mouth"][0] - 10, pt["mouth"][1] + 30), (pt["mouth"][0] + 30, pt["mouth"][1] + 10)),
                    hands=("open", "open"), effects_extra=["shout"])],
        "pulse", ["shout", "shouting", "shouted", "yell", "yelled", "call", "called", "scream"], "Shouting with hands cupped.")
    add("sing", [P(face=F(eyes="happy", mouth="open", effects=["notes"]), arm_back=(-60, -40), arm_front=(70, 60), hands=("open", "open")),
                 P(face=F(eyes="happy", mouth="small_o", effects=["notes"]), arm_back=(-70, -55), arm_front=(80, 75), hands=("open", "open"))],
        "talk", ["sing", "singing", "sang", "song", "music"], "Singing with arms open.", hold=4)
    add("wave", [P(face=F(mouth="big_smile"), arm_front=(118, 190), hands=("mitt", "open"), effects_extra=["wave"]),
                 P(face=F(mouth="big_smile"), arm_front=(118, 145), hands=("mitt", "open"), effects_extra=["wave"])],
        "wave", ["wave", "waving", "waved", "hello", "hi", "goodbye", "bye"], "Waving hello.", hold=3)

    # Moving --------------------------------------------------------------------
    add("walk", walk_cycle(F()), "walk", ["walk", "walking", "walked", "stroll", "go", "went", "goes"], "Walking (4 frames).", hold=3)
    add("run", run_cycle(F(mouth="open", brows="focused")), "run",
        ["run", "running", "ran", "hurry", "race", "raced", "rush", "chase", "sprint"], "Running (4 frames).", hold=2)
    add("jump", [P(face=F(eyes="happy", mouth="laugh"), arm_back=(-135, -155), arm_front=(130, 150),
                   leg_back=(20, -40), leg_front=(45, -20), air=110)],
        "jump", ["jump", "jumping", "jumped", "leap", "leapt", "hop"], "Jumping with arms up.")
    add("dance", [P(face=happy, lean=-4, arm_back=(-60, -20), arm_front=(125, 165), leg_front=(40, 25), leg_back=(-3, -3)),
                  P(face=happy, lean=4, arm_back=(-135, -160), arm_front=(60, 95), leg_front=(3, 3), leg_back=(-40, -60))],
        "dance", ["dance", "dancing", "danced", "party", "boogie"], "Dancing (2 frames).", hold=6)
    add("clap", [P(face=happy, hand_targets=((pt["chest"][0] + 5, pt["chest"][1] + 10), (pt["chest"][0] + 75, pt["chest"][1] - 25)), hands=("open", "open")),
                 P(face=happy, hand_targets=((pt["chest"][0] + 35, pt["chest"][1] - 5), (pt["chest"][0] + 45, pt["chest"][1] - 10)),
                   hands=("open", "open"), effects_extra=["clap"])],
        "clap", ["clap", "clapping", "clapped", "applause", "applaud"], "Clapping (2 frames).", hold=2)
    add("cheer", [P(face=F(eyes="happy", mouth="laugh", effects=["sparkles"]), hands=("fist", "fist"), **up),
                  P(face=F(eyes="happy", mouth="big_smile", effects=["sparkles"]), arm_back=(-125, -150), arm_front=(120, 145), hands=("fist", "fist"))],
        "bounce", ["cheer", "cheering", "cheered", "celebrate", "celebrated", "victory"], "Cheering with fists up.", hold=4)
    add("point", [P(face=F(eyes="open", brows="raised", mouth="open"), arm_front=(100, 95), hands=("mitt", "point"))],
        "idle", ["point", "pointing", "pointed", "show", "showed", "look", "looked", "see", "saw"], "Pointing ahead.")
    add("bow", [P(face=F(eyes="closed", mouth="smile"), lean=38, head_tilt=12, arm_back=(10, 15), arm_front=(15, 20))],
        "idle", ["bow", "bowing", "bowed", "thank", "thanks", "greet", "greeted"], "Polite bow.")
    add("fall", [P(face=F(eyes="wide", brows="worried", mouth="shout", effects=["sweat"]), arm_back=(-140, -110), arm_front=(130, 100),
                   leg_back=(-30, -60), leg_front=(40, 70), hands=("open", "open"), air=120)],
        "fall", ["fall", "falling", "fell", "trip", "tripped", "slip", "slipped"], "Falling, arms flailing.")

    # Activities ---------------------------------------------------------------
    if adult:
        add("sit", [P(prop="chair", leg_back=(85, 0), leg_front=(88, 2), arm_back=(20, 70), arm_front=(25, 75))],
            "idle", ["sit", "sitting", "sat", "seat", "chair", "rest", "rested"], "Sitting on a chair.")
        add("doze", [P(prop="chair", face=F(eyes="closed", mouth="small_o", effects=["zzz"]), head_tilt=22,
                       leg_back=(85, 0), leg_front=(88, 2), arm_back=(20, 60), arm_front=(25, 65))],
            "sleep", ["doze", "dozed", "snooze", "nod off"], "Asleep in a chair.")
        add("read", [P(face=F(eyes="open", brows="focused", mouth="flat"), prop="book", head_tilt=14,
                       hand_targets=((pt["chest"][0] + 30, pt["chest"][1] + 10), (pt["chest"][0] + 80, pt["chest"][1] - 5)))],
            "idle", ["read", "reading", "book", "newspaper", "study"], "Reading a book.")
        add("phone", [P(face=F(mouth="talk"), prop="phone", hand_targets=(pt["hip_back"], (pt["ear"][0] + 10, pt["ear"][1] + 30))),
                      P(face=F(mouth="smile"), prop="phone", hand_targets=(pt["hip_back"], (pt["ear"][0] + 10, pt["ear"][1] + 30)))],
            "talk", ["phone", "call", "calls", "called", "telephone", "text"], "Talking on the phone.", hold=4)
        add("coffee", [P(face=F(eyes="happy", mouth="smile"), prop="cup", hand_targets=(pt["hip_back"], (pt["chest"][0] + 40, pt["chest"][1] - 20)))],
            "idle", ["coffee", "tea", "drink", "drinking", "drank", "cup"], "Holding a hot drink.")
        add("carry", [P(face=F(brows="focused", mouth="flat", effects=["sweat"]), prop="box", lean=-4,
                        hand_targets=((pt["chest"][0] - 10, pt["chest"][1] + 40), (pt["chest"][0] + 120, pt["chest"][1] + 30)))],
            "idle", ["carry", "carrying", "carried", "box", "lift", "lifted", "move", "moving"], "Carrying a box.")
        add("work", [P(face=F(brows="focused", mouth="smile"), prop="briefcase", arm_front=(6, 6))], "idle", ["work", "working", "office", "job", "briefcase", "leave", "left"], "Off to work with a briefcase.")
        add("facepalm", [P(face=F(eyes="closed", brows="sad", mouth="frown"), head_tilt=10,
                           hand_targets=(pt["hip_back"], (pt["forehead"][0] + 20, pt["forehead"][1] + 25)), hands=("mitt", "open"))],
            "slow", ["facepalm", "oops", "oh no", "mistake", "forgot"], "Hand on forehead, oh no!")
    else:
        add("sit", [P(face=F(), arm_back=(20, 60), arm_front=(25, 60), leg_back=(85, 88), leg_front=(90, 92))],
            "idle", ["sit", "sitting", "sat", "seat", "rest", "rested"], "Sitting on the ground.")
        add("read", [P(face=F(eyes="open", brows="focused", mouth="smile"), prop="book", head_tilt=12,
                       hand_targets=((pt["chest"][0] + 20, pt["chest"][1] + 20), (pt["chest"][0] + 70, pt["chest"][1] + 10)))],
            "idle", ["read", "reading", "book", "story", "study", "school"], "Reading a book.")
        add("eat", [P(face=F(eyes="happy", mouth="tongue", blush=True), prop="ice_cream",
                      hand_targets=(pt["hip_back"], (pt["chest"][0] + 45, pt["chest"][1] - 40)))],
            "sway", ["eat", "eating", "ate", "ice cream", "snack", "treat", "lunch", "hungry"], "Enjoying an ice cream.")
        add("balloon", [P(face=happy, prop="balloon", arm_front=(70, 125))],
            "sway", ["balloon", "birthday", "fair", "gift", "present"], "Holding a red balloon.")
        add("play", [P(face=F(eyes="happy", mouth="big_smile"), prop="ball", hand_targets=((pt["chest"][0] + 20, pt["chest"][1] - 30),
                                                                                          (pt["chest"][0] + 90, pt["chest"][1] - 40)))],
            "bounce", ["play", "playing", "played", "ball", "game", "toy", "fun"], "Playing with a ball.")
        add("flower", [P(face=F(eyes="happy", mouth="smile", blush=True), prop="flower",
                         hand_targets=(pt["hip_back"], (pt["chest"][0] + 50, pt["chest"][1] - 20)))],
            "sway", ["flower", "flowers", "pick", "picked", "smell", "garden"], "Holding a flower.")
    return X
