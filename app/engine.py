import json
import math
import os
import re
import subprocess
import textwrap
import urllib.request
from pathlib import Path
from typing import Literal

from PIL import Image, ImageDraw, ImageFont
from pydantic import BaseModel, Field


# ============================================================
# CONFIGURATION
# ============================================================

WIDTH = 640
HEIGHT = 360
FPS = 12

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ASSETS_DIR = PROJECT_ROOT / "assets"
CHARACTER_DIR = ASSETS_DIR / "characters" / "cat"
BACKGROUNDS_DIR = ASSETS_DIR / "backgrounds"


Action = Literal[
    "idle",
    "walk",
    "run",
    "jump",
    "hop",
    "slide",
    "fly",
    "dance",
    "spin",
    "turn",
    "shake",
    "fall",
    "sit",
    "sleep",
    "wake",
    "wave",
    "nod",
    "bow",
    "look",
    "peek",
    "clap",
    "happy",
    "sad",
    "scared",
    "surprised",
    "laugh",
]


# ============================================================
# DATA MODELS
# ============================================================

class Scene(BaseModel):
    narration: str = Field(min_length=1, max_length=260)
    setting: Literal["garden", "forest", "night"] = "garden"
    action: Action = "idle"
    duration: int = Field(default=5, ge=3, le=12)


class Story(BaseModel):
    title: str = Field(default="A little adventure", max_length=80)
    scenes: list[Scene] = Field(min_length=1, max_length=8)


class Prompt(BaseModel):
    prompt: str = Field(min_length=3, max_length=2000)
    provider: Literal["demo", "ollama"] = "demo"


# ============================================================
# ASSET MANAGER
# ============================================================

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


# ============================================================
# ACTION DETECTION
# ============================================================

ACTION_KEYWORDS = {
    "run": ["run", "running", "ran", "sprint"],
    "walk": ["walk", "walking", "stroll"],
    "jump": ["jump", "jumping", "leap"],
    "hop": ["hop", "hopping"],
    "dance": ["dance", "dancing"],
    "wave": ["wave", "waving"],
    "sleep": ["sleep", "sleeping", "asleep"],
    "wake": ["wake", "waking", "woke up"],
    "sit": ["sit", "sitting", "sat down"],
    "spin": ["spin", "spinning", "twirl"],
    "turn": ["turn", "turning"],
    "shake": ["shake", "shaking", "shiver"],
    "fall": ["fall", "falling", "fell"],
    "fly": ["fly", "flying"],
    "slide": ["slide", "sliding"],
    "clap": ["clap", "clapping"],
    "nod": ["nod", "nodding"],
    "bow": ["bow", "bowing"],
    "look": ["look", "looking"],
    "peek": ["peek", "peeking"],
    "happy": ["happy", "excited", "cheerful"],
    "sad": ["sad", "crying", "unhappy"],
    "scared": ["scared", "afraid", "frightened"],
    "surprised": ["surprised", "shocked", "amazed"],
    "laugh": ["laugh", "laughing", "giggle"],
    "idle": ["wait", "waiting", "stand", "standing"],
}


def detect_action(sentence: str) -> str:
    lower = sentence.lower()

    for action, keywords in ACTION_KEYWORDS.items():
        for keyword in keywords:
            if re.search(r"\b" + re.escape(keyword) + r"\b", lower):
                return action

    return "idle"


# ============================================================
# STORYBOARD GENERATION
# ============================================================

def storyboard(request: Prompt):
    if request.provider == "ollama":
        instructions = (
            "Write a short children's cartoon storyboard. "
            "Return only JSON matching this schema: "
            + json.dumps(Story.model_json_schema())
        )

        body = json.dumps(
            {
                "model": os.getenv("OLLAMA_MODEL", "llama3.2"),
                "stream": False,
                "format": "json",
                "messages": [
                    {"role": "system", "content": instructions},
                    {"role": "user", "content": request.prompt},
                ],
            }
        ).encode()

        url = (
            os.getenv("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
            + "/api/chat"
        )

        req = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
        )

        with urllib.request.urlopen(req, timeout=120) as response:
            result = json.loads(response.read())

        return Story.model_validate_json(result["message"]["content"])

    sentences = [
        s.strip()
        for s in re.split(r"(?<=[.!?])\s+|\n+", request.prompt)
        if s.strip()
    ]

    scenes: list[Scene] = []

    for sentence in sentences:
        lower = sentence.lower()
        setting = next((s for s in ["forest", "night"] if s in lower), "garden")
        action = detect_action(sentence)

        for chunk in textwrap.wrap(sentence, 250):
            scenes.append(
                Scene(
                    narration=chunk,
                    setting=setting,
                    action=action,
                    duration=5,
                )
            )

            if len(scenes) >= 8:
                break

        if len(scenes) >= 8:
            break

    if not scenes:
        scenes = [Scene(narration="Our little adventure begins!", action="idle")]

    return Story(title="A little adventure", scenes=scenes)


# ============================================================
# FONT SUPPORT
# ============================================================

def font(size: int) -> ImageFont.FreeTypeFont:
    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
    ]

    for path in paths:
        if Path(path).exists():
            return ImageFont.truetype(path, size)

    return ImageFont.load_default()


# ============================================================
# CHARACTER ANIMATOR
# ============================================================

class CharacterAnimator:
    def __init__(self, asset_manager: AssetManager):
        self.asset_manager = asset_manager

    def get_animated_sprite(self, action: str, t: float) -> Image.Image:
        frames = sorted(
            key for key in self.asset_manager.character_images
            if key.startswith(f"{action}_")
        )

        if frames:
            animation_fps = 8 if action == "walk" else 12
            index = int(t * animation_fps) % len(frames)
            return self.asset_manager.character_images[frames[index]]

        return self.asset_manager.get_character_image(action)

    def animate_character(self, sprite: Image.Image, action: str, t: float):
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


# ============================================================
# CAMERA MOVES
# ============================================================

CAMERA_MOVES = {
    "idle": dict(zoom=(1.00, 1.12)),
    "sit": dict(zoom=(1.05, 1.18)),
    "nod": dict(zoom=(1.00, 1.10)),
    "clap": dict(zoom=(1.00, 1.15)),
    "sleep": dict(zoom=(1.00, 1.22), y=(0.5, 0.8)),
    "wake": dict(zoom=(1.22, 1.00)),
    "bow": dict(zoom=(1.15, 1.00)),
    "sad": dict(zoom=(1.20, 1.00), y=(0.2, 0.8)),
    "wave": dict(zoom=(1.15, 1.15), x=(0.0, 1.0), y=(0.0, 1.0)),
    "laugh": dict(zoom=(1.10, 1.18), x=(0.2, 0.8), y=(0.2, 0.6)),
    "happy": dict(zoom=(1.10, 1.20), x=(0.2, 0.8), y=(0.7, 0.3)),
    "look": dict(zoom=(1.15, 1.15), x=(0.1, 0.9)),
    "turn": dict(zoom=(1.15, 1.15), x=(0.0, 1.0)),
    "slide": dict(zoom=(1.15, 1.15), x=(0.0, 1.0)),
    "peek": dict(zoom=(1.15, 1.15), x=(0.9, 0.1)),
    "jump": dict(zoom=(1.15, 1.15), y=(1.0, 0.0)),
    "hop": dict(zoom=(1.12, 1.12), y=(0.9, 0.3)),
    "fly": dict(zoom=(1.18, 1.18), x=(0.3, 0.7), y=(1.0, 0.0)),
    "fall": dict(zoom=(1.15, 1.15), y=(0.0, 1.0)),
    "dance": dict(zoom=(1.18, 1.18), orbit=True),
    "spin": dict(zoom=(1.00, 1.25)),
    "surprised": dict(zoom=(1.00, 1.28), ease="out"),
    "scared": dict(zoom=(1.10, 1.22), shake=3),
    "shake": dict(zoom=(1.08, 1.08), shake=6),
}


def smoothstep(p: float) -> float:
    return p * p * (3 - 2 * p)


def ease_out(p: float) -> float:
    return 1 - (1 - p) ** 3


def lerp(a: float, b: float, e: float) -> float:
    return a + (b - a) * e


# ============================================================
# SCENE RENDERER
# ============================================================

class SceneRenderer:
    def __init__(self, asset_manager: AssetManager, animator: CharacterAnimator):
        self.asset_manager = asset_manager
        self.animator = animator

    def camera_view(self, setting: str, action: str, t: float, duration: int) -> Image.Image:
        background = self.asset_manager.backgrounds[setting]
        move = CAMERA_MOVES.get(action)

        if move is None:
            return background.copy()

        w, h = background.size

        p = min(max(t / duration, 0.0), 1.0)
        e = ease_out(p) if move.get("ease") == "out" else smoothstep(p)

        z0, z1 = move.get("zoom", (1.0, 1.0))
        zoom = lerp(z0, z1, e)

        if move.get("orbit"):
            angle = 2 * math.pi * p
            px = 0.5 + 0.4 * math.sin(angle)
            py = 0.5 - 0.4 * math.cos(angle)
        else:
            x0, x1 = move.get("x", (0.5, 0.5))
            y0, y1 = move.get("y", (0.5, 0.5))
            px = lerp(x0, x1, e)
            py = lerp(y0, y1, e)

        crop_w = w / zoom
        crop_h = h / zoom

        left = px * (w - crop_w)
        top = py * (h - crop_h)

        shake = move.get("shake", 0)
        if shake:
            left += shake * math.sin(t * 23) + shake * 0.5 * math.sin(t * 37)
            top += shake * math.sin(t * 29) + shake * 0.5 * math.sin(t * 41)

        left = min(max(left, 0), w - crop_w)
        top = min(max(top, 0), h - crop_h)

        return background.resize(
            (w, h),
            Image.Resampling.BICUBIC,
            box=(left, top, left + crop_w, top + crop_h),
        )

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


# ============================================================
# VIDEO RENDERER
# ============================================================

class VideoRenderer:
    def __init__(self, scene_renderer: SceneRenderer):
        self.scene_renderer = scene_renderer

    def render(self, story: Story, output: str | Path, progress):
        output = Path(output)
        output.mkdir(parents=True, exist_ok=True)

        total = sum(scene.duration * FPS for scene in story.scenes)
        count = 0
        video_path = output / "video.mp4"

        command = [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "-s",
            f"{WIDTH}x{HEIGHT}",
            "-r",
            str(FPS),
            "-i",
            "-",
            "-an",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(video_path),
        ]

        log_path = output / "render.log"

        with log_path.open("w") as log:
            process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stderr=log,
            )

            try:
                for n, scene in enumerate(story.scenes, 1):
                    for f in range(scene.duration * FPS):
                        t = f / FPS
                        image = self.scene_renderer.render_frame(scene, t)

                        if f == 0:
                            image.save(output / f"scene-{n}.png")

                        process.stdin.write(image.tobytes())
                        count += 1

                        if count % FPS == 0:
                            progress(round(count / total * 95))

                process.stdin.close()

                return_code = process.wait(timeout=90)
                if return_code != 0:
                    raise RuntimeError(
                        "Video encoder failed. Check FFmpeg installation and "
                        f"{log_path}"
                    )

            except BaseException:
                process.kill()
                process.wait()
                raise

        (output / "story.json").write_text(
            story.model_dump_json(indent=2),
            encoding="utf-8",
        )

        progress(100)
        return video_path


# ============================================================
# TEST STORY
# ============================================================

def create_test_story() -> Story:
    return Story(
        title="Milo the Happy Cat",
        scenes=[
            Scene(
                narration="Milo wakes up in the beautiful garden.",
                setting="garden",
                action="wake",
                duration=4,
            ),
            Scene(
                narration="Milo starts walking around the garden.",
                setting="garden",
                action="walk",
                duration=4,
            ),
            Scene(
                narration="Suddenly, Milo sees a butterfly and jumps!",
                setting="forest",
                action="jump",
                duration=4,
            ),
            Scene(
                narration="Milo dances happily with his new friend.",
                setting="forest",
                action="dance",
                duration=4,
            ),
            Scene(
                narration="After a wonderful day, Milo falls asleep.",
                setting="night",
                action="sleep",
                duration=5,
            ),
        ],
    )


# ============================================================
# GLOBAL INSTANTIATIONS
# ============================================================

ASSET_MANAGER = AssetManager(PROJECT_ROOT)
CHARACTER_ANIMATOR = CharacterAnimator(ASSET_MANAGER)
SCENE_RENDERER = SceneRenderer(ASSET_MANAGER, CHARACTER_ANIMATOR)
VIDEO_RENDERER = VideoRenderer(SCENE_RENDERER)


# ============================================================
# COMPATIBILITY WRAPPERS
# ============================================================

def frame(scene: Scene, t: float, number: int, total: int) -> Image.Image:
    return SCENE_RENDERER.render_frame(scene, t)


def render(story: Story, output: str | Path, progress) -> Path:
    return VIDEO_RENDERER.render(story, output, progress)


# ============================================================
# RUN DIRECTLY
# ============================================================

if __name__ == "__main__":
    story = create_test_story()
    output_directory = Path("output")

    def show_progress(value: int):
        print(f"Rendering: {value}%")

    video = render(story, output_directory, show_progress)
    print(f"\nVideo created successfully: {video}")