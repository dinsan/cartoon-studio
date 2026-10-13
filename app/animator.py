import math

from PIL import Image

from .assets import AssetManager


class CharacterAnimator:
    def __init__(self, asset_manager: AssetManager):
        self.asset_manager = asset_manager

    def get_animated_sprite(self, action: str, t: float) -> Image.Image:
        frames = sorted(
            key
            for key in self.asset_manager.character_images
            if key.startswith(f"{action}_")
        )

        if frames:
            animation_fps = 8 if action == "walk" else 12
            index = int(t * animation_fps) % len(frames)
            return self.asset_manager.character_images[frames[index]]

        return self.asset_manager.get_character_image(action)

    def animate_character(
        self, sprite: Image.Image, action: str, t: float
    ) -> tuple[Image.Image, int, int]:
        sprite = sprite.copy()

        x_offset = 0
        y_offset = 0
        angle = 0
        scale_x = 1.0
        scale_y = 1.0

        if action == "idle":
            scale_y = 1 + 0.015 * math.sin(t * 2)

        elif action == "walk":
            speed = 45
            x_offset = int(t * speed)
            y_offset = -int(abs(math.sin(t * 9)) * 3)
            angle = 1.5 * math.sin(t * 9)

        elif action == "run":
            speed = 90
            x_offset = int(t * speed)
            y_offset = -int(abs(math.sin(t * 15)) * 7)
            angle = -4 + 2 * math.sin(t * 12)

        elif action == "jump":
            y_offset = -int(abs(math.sin(t * 3)) * 65)

        elif action == "hop":
            y_offset = -int(abs(math.sin(t * 7)) * 28)

        elif action == "slide":
            x_offset = int(85 * math.sin(t))
            angle = -12

        elif action == "fly":
            y_offset = -65 - int(15 * math.sin(t * 3))
            angle = 7 * math.sin(t * 2)

        elif action == "dance":
            x_offset = int(15 * math.sin(t * 6))
            y_offset = -int(abs(math.sin(t * 8)) * 18)
            angle = 15 * math.sin(t * 6)

        elif action == "spin":
            scale_x = max(0.08, abs(math.cos(t * 4)))

        elif action == "turn":
            scale_x = max(0.08, abs(math.cos(t * 2)))

        elif action == "shake":
            x_offset = int(7 * math.sin(t * 25))

        elif action == "fall":
            angle = min(t * 75, 85)
            y_offset = min(int(t * 25), 20)

        elif action == "sit":
            scale_y = 1.0
            scale_x = 1.12

        elif action == "sleep":
            scale_y = 1 + 0.01 * math.sin(t * 2)
            scale_x = 1.10

        elif action == "wake":
            scale_y = min(1.0, 0.65 + t * 0.3)

        elif action == "wave":
            angle = 3 * math.sin(t * 5)

        elif action == "nod":
            scale_y = 1 - 0.06 * abs(math.sin(t * 5))

        elif action == "bow":
            angle = 12 * abs(math.sin(t * 2))
            scale_y = 0.9

        elif action == "look":
            angle = 8 * math.sin(t * 2)

        elif action == "peek":
            x_offset = int(22 * math.sin(t * 2))
            angle = 12 * math.sin(t * 2)

        elif action == "clap":
            scale_x = 1 + 0.02 * math.sin(t * 8)
            y_offset = -int(abs(math.sin(t * 12)) * 5)

        elif action == "happy":
            y_offset = -int(abs(math.sin(t * 5)) * 18)
            angle = 5 * math.sin(t * 5)

        elif action == "sad":
            scale_y = 0.88
            angle = -2

        elif action == "scared":
            x_offset = int(5 * math.sin(t * 22))
            scale_y = 1.05

        elif action == "surprised":
            scale_x = 1.0
            scale_y = 1.0

        elif action == "laugh":
            scale_y = 1 + 0.05 * math.sin(t * 9)
            angle = 5 * math.sin(t * 7)

        new_width = max(1, int(sprite.width * scale_x))
        new_height = max(1, int(sprite.height * scale_y))

        sprite = sprite.resize((new_width, new_height), Image.Resampling.BICUBIC)

        if angle != 0:
            sprite = sprite.rotate(
                angle,
                resample=Image.Resampling.BICUBIC,
                expand=True,
            )

        return sprite, x_offset, y_offset
