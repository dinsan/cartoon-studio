from pathlib import Path

WIDTH = 640
HEIGHT = 360
FPS = 12

# Most scenes a story (and therefore a video) can have.
MAX_SCENES = 10

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ASSETS_DIR = PROJECT_ROOT / "assets"
CHARACTERS_DIR = ASSETS_DIR / "characters"
CHARACTER_DIR = CHARACTERS_DIR / "cat"
# Character used when a story doesn't name one.
DEFAULT_CHARACTER = "cat"
BACKGROUNDS_DIR = ASSETS_DIR / "backgrounds"

# Frames are composed at WORLD_SCALE x the output resolution and then
# downsampled. This gives sub-pixel smooth motion and sharp camera zooms.
WORLD_SCALE = 2
WORLD_HEIGHT = HEIGHT * WORLD_SCALE

# Where the character's feet touch the ground (output pixels at zoom 1).
GROUND_Y = 320

# Default size of a character canvas in output pixels (the cat's 1024x1024
# PNGs are shown 140 px wide). Each character.json can set its own "size".
CHARACTER_BOX = 140
