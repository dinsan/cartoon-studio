from PIL import Image, ImageDraw

from .animator import CharacterAnimator
from .assets import AssetManager
from .camera import Camera
from .config import WIDTH
from .fonts import font
from .models import Scene


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

    def camera_view(
        self, setting: str, action: str, t: float, duration: int
    ) -> Image.Image:
        return self.camera.view(setting, action, t, duration)

    def render_frame(self, scene: Scene, t: float) -> Image.Image:
        is_night = scene.setting == "night"
        background = self.asset_manager.backgrounds[scene.setting]
        width, height = background.size

        if scene.action == "walk":
            speed = 35
            offset = int(t * speed) % width
            im = Image.new("RGB", (width, height))
            im.paste(background, (-offset, 0))
            im.paste(background, (width - offset, 0))
        elif scene.action == "run":
            im = background.copy()
        else:
            im = self.camera_view(scene.setting, scene.action, t, scene.duration)

        d = ImageDraw.Draw(im)

        sprite = self.animator.get_animated_sprite(scene.action, t)
        character, offset_x, offset_y = self.animator.animate_character(
            sprite,
            scene.action,
            t,
        )

        ground_y = 320

        if scene.action in ("walk", "run", "slide"):
            x = 40 + offset_x
        else:
            x = (WIDTH - character.width) // 2 + offset_x

        y = ground_y - character.height + offset_y

        im.paste(character, (x, y), character)

        if scene.action == "sleep":
            d.text(
                (x + character.width, y - 25),
                "Zzz...",
                font=font(20),
                fill=("#ffffff" if is_night else "#34495e"),
            )

        d.text(
            (18, 40),
            f"Action: {scene.action}",
            font=font(12),
            fill=("white" if is_night else "#263d50"),
        )

        return im
