from pathlib import Path

from PIL import Image


class AssetManager:
    def __init__(self, root_dir: Path):
        self.root_dir = root_dir
        self.character_dir = root_dir / "assets" / "characters" / "cat"
        self.backgrounds_dir = root_dir / "assets" / "backgrounds"

        self.character_images: dict[str, Image.Image] = {}
        self.backgrounds: dict[str, Image.Image] = {}

        self.load_character_images()
        self.load_backgrounds()

    def load_character_images(self) -> None:
        for image_path in self.character_dir.glob("*.png"):
            action_name = image_path.stem.lower()
            image = Image.open(image_path).convert("RGBA")
            image.thumbnail((140, 140), Image.Resampling.LANCZOS)
            self.character_images[action_name] = image

    def load_backgrounds(self) -> None:
        for setting in ["garden", "forest", "night"]:
            with Image.open(self.backgrounds_dir / f"{setting}.jpeg") as image:
                self.backgrounds[setting] = image.convert("RGB").resize(
                    (640, 360),
                    Image.Resampling.LANCZOS,
                )

    def get_character_image(self, action: str) -> Image.Image:
        return self.character_images.get(action, self.character_images["idle"])
