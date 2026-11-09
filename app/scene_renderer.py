"""Composes one video frame: background, ground shadow, character, camera."""

import math
from dataclasses import dataclass
from functools import lru_cache

from PIL import Image, ImageDraw

from .animator import CharacterAnimator, Pose
from .assets import AssetManager, CharacterAssets, Sprite
from .camera import VIEW_W, Camera
from .config import FPS, GROUND_Y, HEIGHT, WIDTH, WORLD_SCALE
from .fonts import font
from .models import Scene

GROUND = GROUND_Y * WORLD_SCALE
# Fraction of the frame the character may drift across while the camera
# follows it; the rest of the travel is a camera pan.
SCREEN_TRAVEL = 0.55
# Camera smoothing window (seconds) so stop-start motion (hops, jumps) gives
# a steady pan.
CAMERA_SMOOTHING = 0.6
# The artwork's shadows are very faint (~15% black); strengthen them a little
# so the character reads as standing on the ground.
SHADOW_STRENGTH = 1.5
# Share of the character's height taken by the legs (used when bending).
LEG_SHARE = 0.3
BEND_STRIPS = 24


@dataclass
class ScenePlan:
    start_x: float  # world x of the character at t = 0
    camera_x: list[float]  # smoothed camera centre per video frame
    world_width: float


@dataclass
class Placement:
    image: Image.Image
    left: int
    top: int
    anchor_x: float  # where the feet centre ended up (world x)


def _affine_place(
    image: Image.Image,
    anchor: tuple[float, float],
    pivot: tuple[float, float],
    sx: float,
    sy: float,
    angle: float,
    dest: tuple[float, float],
) -> Placement:
    """Scale around ``anchor`` and rotate around ``pivot`` (both in image
    coordinates), then move ``anchor`` to ``dest``. One resampling pass."""
    a = math.radians(angle)
    c, s = math.cos(a), math.sin(a)
    # Forward map W = M p + b with M = R * S (screen y points down, so a
    # counter-clockwise rotation is [[c, s], [-s, c]]).
    m00, m01, m10, m11 = c * sx, s * sy, -s * sx, c * sy
    ax, ay = anchor
    px, py = (pivot[0] - ax) * sx, (pivot[1] - ay) * sy  # scaled pivot offset
    rpx, rpy = c * px + s * py, -s * px + c * py
    bx = dest[0] + px - rpx - (m00 * ax + m01 * ay)
    by = dest[1] + py - rpy - (m10 * ax + m11 * ay)

    corners = [(0, 0), (image.width, 0), (0, image.height), (image.width, image.height)]
    xs = [m00 * x + m01 * y + bx for x, y in corners]
    ys = [m10 * x + m11 * y + by for x, y in corners]
    left, top = math.floor(min(xs)), math.floor(min(ys))
    size = (max(1, math.ceil(max(xs)) - left), max(1, math.ceil(max(ys)) - top))

    det = m00 * m11 - m01 * m10
    i00, i01, i10, i11 = m11 / det, -m01 / det, -m10 / det, m00 / det
    ox, oy = left - bx, top - by
    data = (i00, i01, i00 * ox + i01 * oy, i10, i11, i10 * ox + i11 * oy)
    out = image.transform(size, Image.Transform.AFFINE, data, resample=Image.Resampling.BICUBIC)
    return Placement(out, left, top, m00 * ax + m01 * ay + bx)


def _bend(image: Image.Image, sprite: Sprite, bend: float) -> Image.Image:
    """Lower the front (bend > 0) or the back (bend < 0) of the character by
    shortening its legs, keeping every foot on the ground.

    The torso is shifted down by an amount that grows linearly from the
    planted foot to the other foot (the head or tail beyond it moves as one
    piece), while the legs compress. Used for bowing, nodding, drooping and sitting.
    """
    if abs(bend) < 1e-3:
        return image
    ground = sprite.anchor[1]
    leg = LEG_SHARE * sprite.height
    hip = ground - leg
    span = max(1.0, sprite.front_x - sprite.back_x)

    def drop(x: float) -> float:
        w = (x - sprite.back_x) / span if bend > 0 else (sprite.front_x - x) / span
        # Beyond the feet (head, tail) the drop stays constant so the face
        # moves down without being skewed.
        return min(0.85 * leg, abs(bend) * leg * min(1.0, max(0.0, w)))

    width, height = image.size
    mesh = []
    for i in range(BEND_STRIPS):
        x0 = round(i * width / BEND_STRIPS)
        x1 = round((i + 1) * width / BEND_STRIPS)
        if x1 <= x0:
            continue
        d0, d1, dm = drop(x0), drop(x1), drop((x0 + x1) / 2)
        edge = hip + dm  # output y where the shifted torso meets the legs
        # Torso/head: shifted down.
        mesh.append(((x0, 0, x1, round(edge)), (x0, -d0, x0, edge - d0, x1, edge - d1, x1, -d1)))
        # Legs: compressed between the hip and the ground.
        mesh.append(((x0, round(edge), x1, round(ground)), (x0, edge - d0, x0, ground, x1, ground, x1, edge - d1)))
        # Below the ground line: unchanged.
        mesh.append(((x0, round(ground), x1, height), (x0, ground, x0, height, x1, height, x1, ground)))
    return image.transform(image.size, Image.Transform.MESH, mesh, resample=Image.Resampling.BICUBIC)


@lru_cache(maxsize=64)
def _with_arm(sprite: Sprite, arm_angle: float) -> Image.Image:
    """Body with the rigged limb rotated around its shoulder, premultiplied."""
    body = sprite.body.copy()
    arm = sprite.arm.rotate(arm_angle, resample=Image.Resampling.BICUBIC, center=sprite.arm_pivot)
    body.alpha_composite(arm)
    return body.convert("RGBa")


@lru_cache(maxsize=32)
def _premultiplied(sprite: Sprite) -> Image.Image:
    return sprite.body.convert("RGBa")


class SceneRenderer:
    def __init__(
        self,
        asset_manager: AssetManager,
        animator: CharacterAnimator,
        camera: Camera | None = None,
    ):
        self.asset_manager = asset_manager
        self.animator = animator
        self.camera = camera or Camera(asset_manager)
        self._plans: dict[tuple, ScenePlan] = {}
        self._animators: dict[str, CharacterAnimator] = {animator.assets.spec.id: animator}

    # Characters ---------------------------------------------------------------

    def character(self, scene: Scene) -> CharacterAssets:
        return self.asset_manager.character(getattr(scene, "character", None))

    def animator_for(self, scene: Scene) -> CharacterAnimator:
        assets = self.character(scene)
        cid = assets.spec.id
        if cid not in self._animators:
            self._animators[cid] = CharacterAnimator(assets)
        return self._animators[cid]

    def pose(self, scene: Scene, t: float) -> Pose:
        pose = self.animator_for(scene).pose(scene.action, t, scene.duration)
        if not self.character(scene).spec.bend:
            pose.bend = 0.0  # drawings of this character must not be deformed
        return pose

    def motion(self, scene: Scene) -> str:
        """Motion name, which also selects the camera move."""
        return self.character(scene).spec.expression(scene.action).motion

    # Planning -----------------------------------------------------------------

    def plan(self, scene: Scene) -> ScenePlan:
        key = (self.character(scene).spec.id, scene.action, scene.setting, scene.duration)
        if key in self._plans:
            return self._plans[key]

        frames = int(scene.duration * FPS) + 1
        xs = [self.pose(scene, i / FPS).x for i in range(frames)]
        lo, hi = min(xs), max(xs)
        span = hi - lo
        view_w = VIEW_W / self.camera.max_zoom(self.motion(scene))
        budget = SCREEN_TRAVEL * view_w
        follow = 0.0 if span <= budget else 1 - budget / span

        radius = int(CAMERA_SMOOTHING * FPS / 2)
        padded = [xs[0]] * radius + xs + [xs[-1]] * radius
        smoothed = [sum(padded[i : i + 2 * radius + 1]) / (2 * radius + 1) for i in range(frames)]

        background = self.asset_manager.backgrounds[scene.setting]
        # The world extends to the right, so a character travelling left
        # (reversing) starts further right to give the camera room to follow.
        home = max(background.width / 2, VIEW_W / 2 - follow * min(smoothed) + 8)
        # Centre the on-screen part of the path in the frame.
        start_x = home - (1 - follow) * (lo + hi) / 2
        camera_x = [home + follow * x for x in smoothed]

        world_width = max(background.width, max(camera_x) + VIEW_W / 2 + 8)
        self.asset_manager.world_strip(scene.setting, world_width)
        plan = ScenePlan(start_x, camera_x, world_width)
        self._plans[key] = plan
        return plan

    # Drawing ------------------------------------------------------------------

    def _pivot(self, sprite: Sprite, pose: Pose) -> tuple[float, float]:
        pivot = pose.pivot
        if pivot == "auto":
            # A rigid body rocks on whichever foot stays on the ground.
            pivot = "back" if pose.angle > 0 else "front"
        x = {"front": sprite.front_x, "back": sprite.back_x}.get(pivot, sprite.anchor[0])
        return x, sprite.anchor[1]

    def place_character(self, pose: Pose, x: float, ground: float = GROUND) -> Placement:
        """Character image for ``pose`` with its feet centre at ``x`` and
        ``lift`` above ``ground`` (premultiplied RGBa)."""
        sprite = pose.sprite
        image = _with_arm(sprite, round(pose.arm * 2) / 2) if sprite.arm is not None else _premultiplied(sprite)
        image = _bend(image, sprite, pose.bend)
        return _affine_place(
            image,
            sprite.anchor,
            self._pivot(sprite, pose),
            pose.sx,
            pose.sy,
            pose.angle,
            (x, ground - pose.lift),
        )

    def _draw_character(
        self, canvas: Image.Image, origin: tuple[int, int], pose: Pose, x: float, character: CharacterAssets
    ) -> None:
        sprite = pose.sprite
        ground = GROUND - origin[1]
        placed = self.place_character(pose, x - origin[0], ground)

        # Contact shadow stays on the ground and fades/shrinks with height.
        base_shadow = character.contact_shadow(sprite)
        if base_shadow is not None:
            k = 1 / (1 + max(pose.lift, 0.0) / (110 * WORLD_SCALE))
            width = max(1, round(base_shadow.width * k * max(abs(pose.sx), 0.75)))
            height = max(1, round(base_shadow.height * k))
            shadow = base_shadow.resize((width, height), Image.Resampling.BILINEAR)
            strength = SHADOW_STRENGTH * k
            shadow.putalpha(shadow.getchannel("A").point(lambda v: min(255, round(v * strength))))
            center_y = ground + character.shadow_drop
            canvas.paste(
                (0, 0, 0),
                (
                    round(placed.anchor_x - width / 2),
                    round(center_y - height / 2),
                    round(placed.anchor_x - width / 2) + width,
                    round(center_y - height / 2) + height,
                ),
                shadow.getchannel("A"),
            )

        image = placed.image.convert("RGBA")
        canvas.paste(image, (placed.left, placed.top), image)

    def camera_view(self, setting: str, action: str, t: float, duration: int) -> Image.Image:
        """Background only, framed as the camera would frame it."""
        scene = Scene(narration="-", setting=setting, action=action, duration=duration)
        return self._compose(scene, t, draw_character=False)

    def render_frame(self, scene: Scene, t: float) -> Image.Image:
        return self._compose(scene, t)

    def _compose(self, scene: Scene, t: float, draw_character: bool = True) -> Image.Image:
        plan = self.plan(scene)
        pose = self.pose(scene, t)
        character = self.character(scene)
        x = plan.start_x + pose.x
        index = min(max(int(round(t * FPS)), 0), len(plan.camera_x) - 1)

        idle_height = character.idle.height
        left, top, right, bottom = self.camera.view_box(
            self.motion(scene),
            t,
            scene.duration,
            center_x=plan.camera_x[index],
            focus_y=GROUND - 0.5 * idle_height,
            world_width=plan.world_width,
        )

        strip = self.asset_manager.world_strip(scene.setting, plan.world_width)
        box = (math.floor(left), math.floor(top), math.ceil(right), math.ceil(bottom))
        canvas = strip.crop(box)
        if draw_character:
            self._draw_character(canvas, box[:2], pose, x, character)

        frame = canvas.resize(
            (WIDTH, HEIGHT),
            Image.Resampling.BICUBIC,
            box=(left - box[0], top - box[1], right - box[0], bottom - box[1]),
        )

        if draw_character:
            is_night = scene.setting == "night"
            ImageDraw.Draw(frame).text(
                (18, 40),
                f"{character.spec.name}: {scene.action}",
                font=font(12),
                fill=("white" if is_night else "#263d50"),
            )
        return frame
