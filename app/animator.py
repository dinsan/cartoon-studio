"""Character motion.

Each expression in a character's ``character.json`` names a *motion*. A
motion is a function of time that returns a :class:`Pose`: which drawing to
show and how the character sits in the world. Motions follow a few rules
that make them read as physical rather than "sliding stickers":

* Feet stay planted: the pose is anchored where the feet touch the ground and
  rotations pivot around a foot, never around the middle of the image.
* Things in the air follow a parabola (gravity), with anticipation before a
  jump and a squash on landing. The shadow stays on the ground and shrinks
  with height.
* Squash and stretch preserve volume.
* Drawing changes are locked to whole video frames (no uneven 2-1-2 holds)
  and oscillations stay well below the 6 Hz limit of 12 fps video.
* Travel speed matches the stride or wheel rotation so feet and tyres don't
  skate (the speed is stored per expression in ``character.json``).

Distances are in world pixels (``WORLD_SCALE`` x output pixels).
"""

import math
from dataclasses import dataclass

from PIL import Image

from .assets import AssetManager, CharacterAssets, Sprite
from .characters import MOTIONS, ExpressionSpec
from .config import FPS, WORLD_SCALE

S = WORLD_SCALE

# Default locomotion tuning (world px) for expressions without a speed. One
# walk drawing is held for WALK_HOLD frames; two drawings make one step.
WALK_HOLD = 3
WALK_STEP = 29 * S
WALK_SPEED = WALK_STEP * FPS / (2 * WALK_HOLD)  # ~58 output px/s
RUN_HOLD = 2
RUN_STEP = 45 * S
RUN_SPEED = RUN_STEP * FPS / (2 * RUN_HOLD)  # ~135 output px/s
DRIVE_SPEED = 120 * S


@dataclass
class Pose:
    sprite: Sprite
    x: float = 0.0  # horizontal travel from the scene start (world px)
    lift: float = 0.0  # height of the feet above the ground (world px)
    angle: float = 0.0  # degrees, counter-clockwise, around ``pivot``
    pivot: str = "feet"  # "feet", "front", "back" or "auto" (the lower foot)
    sx: float = 1.0  # horizontal scale; negative means facing left
    sy: float = 1.0  # vertical scale
    arm: float = 0.0  # rigged limb rotation in degrees (wave pose)
    bend: float = 0.0  # lower the front (>0) or back (<0) by bending the legs


@dataclass
class Ctx:
    """What a motion needs to know about the expression it animates."""

    assets: CharacterAssets
    spec: ExpressionSpec
    frames: list[Sprite]

    @property
    def base(self) -> Sprite:
        return self.frames[0]

    @property
    def hold(self) -> int:
        return self.spec.hold or 3

    def speed(self, default: float) -> float:
        """Travel speed in world px/s."""
        return self.spec.speed * S if self.spec.speed else default

    def cycle(self, t: float, hold: int | None = None) -> Sprite:
        return self.frames[(frame_index(t) // (hold or self.hold)) % len(self.frames)]

    def ref(self, expression: str) -> Sprite:
        """First drawing of another expression of the same character."""
        return self.assets.sprite(expression) if self.assets.has(expression) else self.base


# Easing helpers -------------------------------------------------------------


def clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return min(max(v, lo), hi)


def smooth(p: float) -> float:
    p = clamp(p)
    return p * p * (3 - 2 * p)


def ease_out(p: float) -> float:
    return 1 - (1 - clamp(p)) ** 3


def window(t: float, start: float, end: float) -> float:
    """0 before ``start``, eases to 1 at ``end``."""
    return smooth((t - start) / (end - start)) if end > start else float(t >= start)


def squash(amount: float) -> tuple[float, float]:
    """Volume-preserving squash (amount > 0) or stretch (amount < 0)."""
    sy = 1 - amount
    return 1 / math.sqrt(sy), sy


def breathe(t: float, depth: float = 0.012, period: float = 3.0) -> tuple[float, float]:
    return squash(depth * 0.5 * (1 - math.cos(2 * math.pi * t / period)))


def frame_index(t: float) -> int:
    return int(round(t * FPS))


def jitter(t: float, amount: float) -> float:
    """Per-frame alternating offset: a shiver at the frame rate."""
    n = frame_index(t)
    return amount * (1 if n % 2 else -1) * (0.6 + 0.4 * math.sin(n * 1.7) ** 2)


def hop_arc(p: float, height: float) -> float:
    """Parabolic height for a hop at progress p in [0, 1]."""
    return 4 * height * p * (1 - p) if 0 <= p <= 1 else 0.0


def _facing(value: float) -> float:
    """Horizontal scale for turning: narrows through zero and flips."""
    if abs(value) < 0.06:
        value = math.copysign(0.06, value)
    return value


class CharacterAnimator:
    def __init__(self, assets: AssetManager | CharacterAssets):
        self.assets = assets.character() if isinstance(assets, AssetManager) else assets

    def get_animated_sprite(self, action: str, t: float) -> Image.Image:
        """Image of the pose shown at time ``t`` (kept for compatibility)."""
        return self.pose(action, t, 5).sprite.body

    def pose(self, expression: str, t: float, duration: float) -> Pose:
        spec = self.assets.spec.expression(expression)
        ctx = Ctx(self.assets, spec, self.assets.frames(spec.name))
        return getattr(self, f"_{spec.motion}")(t, duration, ctx)

    # Standing -----------------------------------------------------------------

    def _idle(self, t, d, c):
        sx, sy = breathe(t)
        return Pose(c.cycle(t), sx=sx, sy=sy)

    def _still(self, t, d, c):
        return Pose(c.cycle(t))

    def _cycle(self, t, d, c):
        sx, sy = breathe(t)
        return Pose(c.cycle(t), sx=sx, sy=sy)

    def _sway(self, t, d, c):
        sx, sy = breathe(t)
        return Pose(c.cycle(t), angle=2.0 * math.sin(2 * math.pi * 0.45 * t), pivot="auto", sx=sx, sy=sy)

    def _slow(self, t, d, c):
        sx, sy = breathe(t, depth=0.02, period=4.5)
        return Pose(c.cycle(t), sx=sx, sy=sy)

    def _talk(self, t, d, c):
        _, sy = breathe(t)
        return Pose(c.cycle(t), angle=1.2 * math.sin(2 * math.pi * 0.6 * t), pivot="auto", sy=sy)

    def _sob(self, t, d, c):
        sx, sy = squash(0.025 * abs(math.sin(2 * math.pi * 1.3 * t)))
        return Pose(c.cycle(t), x=jitter(t, 0.4 * S), sx=sx, sy=sy)

    def _tremble(self, t, d, c):
        sx, sy = breathe(t)
        return Pose(c.cycle(t), x=jitter(t, 0.7 * S), sx=sx, sy=sy)

    def _giggle(self, t, d, c):
        sx, sy = squash(0.04 * abs(math.sin(2 * math.pi * 2.2 * t)))
        return Pose(c.cycle(t), angle=2.5 * math.sin(2 * math.pi * 0.9 * t), pivot="auto", sx=sx, sy=sy)

    def _pulse(self, t, d, c):
        sx, sy = squash(-0.05 * max(0.0, math.sin(2 * math.pi * 1.4 * t)))
        return Pose(c.cycle(t), sx=sx, sy=sy)

    def _bounce(self, t, d, c):
        return self._hops(t, c, period=0.6, height=16 * S, travel=0)

    def _sit(self, t, d, c):
        # No sitting drawing exists: lower the hindquarters and stay there.
        settle = window(t, 0.1, 0.8)
        sx, sy = breathe(t)
        return Pose(c.base, sx=sx, sy=sy, bend=-0.7 * settle)

    def _sleep(self, t, d, c):
        sx, sy = breathe(t, depth=0.03, period=3.4)
        return Pose(c.cycle(t, max(c.hold, 12)), sx=sx, sy=sy)

    def _wake(self, t, d, c):
        wake_at = min(1.6, d * 0.35)
        if t < wake_at:
            return self._sleep(t, d, c)
        # Pop up from lying down with a stretch that overshoots, then settle.
        p = (t - wake_at) / 0.7
        amount = 0.25 * (1 - ease_out(p)) - 0.06 * math.sin(math.pi * clamp(p)) if p < 1 else 0.0
        sx, sy = squash(amount)
        bsx, bsy = breathe(t)
        return Pose(c.ref("idle"), sx=sx * bsx, sy=sy * bsy)

    def _nod(self, t, d, c):
        dip = max(0.0, math.sin(2 * math.pi * 1.1 * t)) ** 2
        return Pose(c.base, bend=0.22 * dip)

    def _bow(self, t, d, c):
        down = window(t, 0.2 * d, 0.2 * d + 0.6) - window(t, 0.65 * d, 0.65 * d + 0.6)
        return Pose(c.base, bend=0.55 * down)

    def _look(self, t, d, c):
        # Turn to look behind, pause, then turn back.
        facing = math.cos(math.pi * (window(t, 0.3 * d, 0.3 * d + 0.3) - window(t, 0.7 * d, 0.7 * d + 0.3)))
        _, sy = breathe(t)
        return Pose(c.base, sx=_facing(facing), sy=sy)

    _turn = _look

    def _peek(self, t, d, c):
        # Lean forward to peek, hold, lean back; twice.
        cycle = (t % 2.2) / 2.2
        lean = window(cycle, 0.1, 0.35) - window(cycle, 0.65, 0.9)
        return Pose(c.base, x=12 * S * lean, bend=0.3 * lean)

    def _sad(self, t, d, c):
        droop = window(t, 0.0, 1.0)
        sx, sy = breathe(t, depth=0.015, period=4.0)
        return Pose(c.base, sx=sx, sy=sy, bend=0.3 * droop)

    def _scared(self, t, d, c):
        # Recoil backwards into a low crouch and tremble.
        recoil = ease_out(t / 0.35)
        sx, sy = squash(0.05 * recoil)
        return Pose(
            c.cycle(t),
            x=-30 * S * recoil + jitter(t, 1.2 * S) * recoil,
            sx=sx,
            sy=sy,
            bend=-0.45 * recoil,
        )

    def _surprised(self, t, d, c):
        # A startled hop straight up, then stay a little stretched.
        start, air = 0.25, 0.36
        p = (t - start) / air
        if 0 <= p <= 1:
            sx, sy = squash(-0.08)
            return Pose(c.base, lift=hop_arc(p, 28 * S), sx=sx, sy=sy)
        if t < start:
            sx, sy = squash(0.1 * window(t, 0.05, start))
        else:
            land = clamp((t - start - air) / 0.2)
            sx, sy = squash(0.12 * (1 - land) - 0.03 * land)
        return Pose(c.base, sx=sx, sy=sy, bend=-0.2 * (t > start))

    def _laugh(self, t, d, c):
        # Belly laugh: quick bounces while rocking back on the hind legs.
        shake = abs(math.sin(2 * math.pi * 2.2 * t))
        sx, sy = squash(0.05 * shake)
        rock = 0.5 + 0.5 * math.sin(2 * math.pi * 0.9 * t)
        return Pose(c.base, sx=sx, sy=sy, bend=-0.15 - 0.25 * rock)

    def _shake(self, t, d, c):
        return Pose(c.cycle(t), x=jitter(t, 3 * S), angle=jitter(t, 1.0))

    # Gestures -----------------------------------------------------------------

    def _wave(self, t, d, c):
        sprite = c.cycle(t) if len(c.frames) > 1 else c.base
        # Paw swings from the shoulder (rigged drawings); body sways gently.
        swing = 0.5 - 0.5 * math.cos(2 * math.pi * 1.6 * t)
        _, sy = breathe(t)
        return Pose(sprite, angle=1.5 * math.sin(2 * math.pi * 0.8 * t), pivot="auto", sy=sy, arm=14 * swing)

    def _clap(self, t, d, c):
        if len(c.frames) > 1:
            _, sy = breathe(t)
            return Pose(c.cycle(t), sy=sy)
        beat = abs(math.sin(2 * math.pi * 1.25 * t))
        return Pose(c.base, lift=6 * S * beat**4, arm=10 * beat)

    def _happy(self, t, d, c):
        return self._hops(t, c, period=0.6, height=22 * S, travel=0)

    def _dance(self, t, d, c):
        # 120 bpm: hop on every beat, change drawing every beat, face the
        # other way every two beats, and sway around the feet.
        beat = 0.5
        n = int(t / beat)
        p = (t % beat) / beat
        sprite = c.frames[n % len(c.frames)]
        # Quick turn (0.2 s) to face the other way every two beats.
        turn = t / (2 * beat)
        k = int(turn)
        facing = (1 if k % 2 == 0 else -1) * _facing(-math.cos(math.pi * clamp((turn - k) / 0.2))) if k > 0 else 1.0
        air = 0.55
        if p < air:
            lift = hop_arc(p / air, 14 * S)
            sx, sy = squash(-0.05)
        else:
            lift = 0.0
            sx, sy = squash(0.1 * math.sin(math.pi * (p - air) / (1 - air)))
        return Pose(sprite, lift=lift, angle=5 * math.sin(math.pi * t / beat), pivot="auto", sx=sx * facing, sy=sy, arm=12 * p)

    def _spin(self, t, d, c):
        # Turn around on the spot: the drawing narrows and flips as it turns.
        turns = 1.1 * t - 0.25 * math.sin(2 * math.pi * 1.1 * t) / math.pi
        facing = math.cos(2 * math.pi * turns)
        lift = 8 * S * abs(math.sin(2 * math.pi * turns))
        return Pose(c.base, lift=lift, sx=_facing(facing))

    # Locomotion ---------------------------------------------------------------

    def _walk(self, t, d, c):
        hold = c.spec.hold or WALK_HOLD
        sprite = c.cycle(t, hold)
        phase = (frame_index(t) % (2 * hold)) / (2 * hold)
        lift = 2.5 * S * 0.5 * (1 - math.cos(2 * math.pi * phase))
        return Pose(sprite, x=c.speed(WALK_SPEED) * t, lift=lift)

    def _run(self, t, d, c):
        hold = c.spec.hold or RUN_HOLD
        sprite = c.cycle(t, hold)
        phase = (frame_index(t) % (2 * hold)) / (2 * hold)
        lift = 9 * S * math.sin(math.pi * phase)
        sx, sy = squash(-0.04 * math.sin(math.pi * phase))
        lean = c.spec.lean or 0.0
        return Pose(sprite, x=c.speed(RUN_SPEED) * t, lift=lift, angle=lean, pivot="front", sx=sx, sy=sy)

    def _slide(self, t, d, c):
        # Pushed off, then friction slows it down: v = v0 * exp(-k t).
        v0, k = 330 * S / 2, 1.1
        speed = math.exp(-k * t)
        return Pose(c.base, x=v0 / k * (1 - speed), bend=-0.35 * speed)

    def _hop(self, t, d, c):
        return self._hops(t, c, period=0.55, height=20 * S, travel=28 * S)

    def _hops(self, t, c, period, height, travel):
        n, p = divmod(t, period)
        sprite = c.frames[int(n) % len(c.frames)]
        contact = 0.2  # fraction of each cycle spent on the ground
        if p / period < contact:
            q = p / period / contact
            sx, sy = squash(0.12 * math.sin(math.pi * q))
            return Pose(sprite, x=travel * n, sx=sx, sy=sy, arm=6)
        q = (p / period - contact) / (1 - contact)
        sx, sy = squash(-0.06 * (1 - abs(2 * q - 1)))
        return Pose(sprite, x=travel * (n + q), lift=hop_arc(q, height), sx=sx, sy=sy, arm=6 + 8 * q)

    def _jump(self, t, d, c):
        # Rest -> crouch (anticipation) -> leap along a parabola -> land with a
        # squash -> recover.
        cycle = 1.6
        rest, crouch, air, land = 0.3, 0.22, 0.62, 0.2
        n, p = divmod(t, cycle)
        forward = 60 * S
        x0 = forward * n
        ground = c.ref("idle")
        if p < rest:
            sx, sy = breathe(t)
            return Pose(ground, x=x0, sx=sx, sy=sy)
        p -= rest
        if p < crouch:
            sx, sy = squash(0.16 * smooth(p / crouch))
            return Pose(ground, x=x0, sx=sx, sy=sy)
        p -= crouch
        if p < air:
            q = p / air
            sx, sy = squash(-0.07 * (1 - q))
            return Pose(c.base, x=x0 + forward * q, lift=hop_arc(q, 75 * S), angle=10 - 20 * q, sx=sx, sy=sy)
        p -= air
        q = clamp(p / land)
        sx, sy = squash(0.18 * (1 - ease_out(q)))
        return Pose(ground, x=x0 + forward, sx=sx, sy=sy)

    def _fly(self, t, d, c):
        rise = ease_out(t / 1.8)
        bob = math.sin(2 * math.pi * t / 1.6)
        return Pose(c.base, x=14 * S * t, lift=(22 + 62 * rise) * S + 7 * S * bob, angle=4 * bob)

    def _fall(self, t, d, c):
        # Drop in from above under gravity, land hard, bounce once, wobble.
        height = 130 * S
        fall_time = 0.65
        ground = c.ref("idle")
        if t < fall_time:
            g = 2 * height / fall_time**2
            return Pose(c.base, lift=height - 0.5 * g * t**2, angle=-12 * t / fall_time)
        p = t - fall_time
        if p < 0.14:
            sx, sy = squash(0.28 * math.sin(math.pi * p / 0.14 / 2))
            return Pose(ground, sx=sx, sy=sy)
        p -= 0.14
        if p < 0.32:
            sx, sy = squash(-0.04 * math.sin(math.pi * p / 0.32))
            return Pose(ground, lift=hop_arc(p / 0.32, 10 * S), sx=sx, sy=sy)
        p -= 0.32
        wobble = 6 * math.sin(2 * math.pi * 1.4 * p) * math.exp(-1.3 * p)
        sx, sy = breathe(t)
        return Pose(ground, angle=wobble, pivot="auto", sx=sx, sy=sy)

    # Vehicles -----------------------------------------------------------------

    def _engine(self, t, d, c):
        # Idling engine: a tiny vibration at the frame rate.
        n = frame_index(t)
        return Pose(c.cycle(t), sy=1 + 0.005 * (1 if n % 2 else -1))

    def _drive(self, t, d, c):
        n = frame_index(t)
        return Pose(c.cycle(t), x=c.speed(DRIVE_SPEED) * t, sy=1 + 0.004 * math.sin(n * 2.1))

    _ride = _drive

    def _drive_fast(self, t, d, c):
        n = frame_index(t)
        return Pose(c.cycle(t), x=c.speed(2 * DRIVE_SPEED) * t, lift=0.6 * S * (n % 2), sy=1 + 0.006 * math.sin(n * 2.7))

    def _reverse(self, t, d, c):
        return Pose(c.cycle(t), x=-c.speed(DRIVE_SPEED * 0.6) * t)

    def _brake(self, t, d, c):
        # Arrive at speed, brake hard (nose dives, then rocks back), stop.
        v0, k = 170 * S, 2.2
        travel = v0 / k * (1 - math.exp(-k * t))
        dive = math.exp(-k * t)
        settle = math.sin(2 * math.pi * 1.2 * t) * math.exp(-2.5 * t) * 1.2
        return Pose(c.base, x=travel, angle=-3.5 * dive + settle, pivot="front" if dive > 0.1 else "auto")

    def _wheelie(self, t, d, c):
        up = window(t, 0.3, 0.9) - window(t, d - 0.8, d - 0.2)
        wobble = 2.5 * math.sin(2 * math.pi * 0.7 * t) * up
        return Pose(c.base, angle=16 * up + wobble, pivot="back")


# Every motion named in a character.json must exist here.
_missing = {m for m in MOTIONS if not hasattr(CharacterAnimator, f"_{m}")}
assert not _missing, f"Motions without an implementation: {_missing}"
