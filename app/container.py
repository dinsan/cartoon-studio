"""Wires the components together and exposes the compatibility wrappers.

Importing this module loads all image assets, so import it only when needed.
"""

from pathlib import Path

from PIL import Image

from .animator import CharacterAnimator
from .assets import AssetManager
from .config import PROJECT_ROOT
from .models import Scene, Story
from .scene_renderer import SceneRenderer
from .video import VideoRenderer

ASSET_MANAGER = AssetManager(PROJECT_ROOT)
CHARACTER_ANIMATOR = CharacterAnimator(ASSET_MANAGER)
SCENE_RENDERER = SceneRenderer(ASSET_MANAGER, CHARACTER_ANIMATOR)
VIDEO_RENDERER = VideoRenderer(SCENE_RENDERER)


def frame(scene: Scene, t: float, number: int, total: int) -> Image.Image:
    return SCENE_RENDERER.render_frame(scene, t)


def render(story: Story, output: str | Path, progress) -> Path:
    return VIDEO_RENDERER.render(story, output, progress)
