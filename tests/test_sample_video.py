"""Renders the sample video in ``tests/sample_video`` and checks it.

The video is built only from the files in that folder (assets + story.json)
and is kept in ``tests/sample_video/output/sample.mp4`` so it can be watched
after the test run.
"""

import json
import shutil
import subprocess
import time
import unittest
from pathlib import Path

from PIL import Image, ImageChops

from app.animator import CharacterAnimator
from app.assets import AssetManager
from app.characters import CharacterLibrary
from app.config import FPS, HEIGHT, MAX_SCENES, WIDTH
from app.models import Prompt, Story
from app.scene_renderer import SceneRenderer
from app.storyboard import storyboard
from app.video import VideoRenderer

SAMPLE_DIR = Path(__file__).resolve().parent / "sample_video"
OUTPUT_DIR = SAMPLE_DIR / "output"
SAMPLE_VIDEO = OUTPUT_DIR / "sample.mp4"


def ffprobe(path: Path) -> dict:
    return json.loads(
        subprocess.check_output(
            [
                "ffprobe", "-v", "error", "-count_frames",
                "-show_streams", "-show_format", "-of", "json", str(path),
            ]
        )
    )


class SampleVideoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        for tool in ("ffmpeg", "ffprobe"):
            if shutil.which(tool) is None:
                raise RuntimeError(f"{tool} is required to generate the sample video; install FFmpeg.")

        cls.story = Story.model_validate_json((SAMPLE_DIR / "story.json").read_text(encoding="utf-8"))

        # Build the pipeline from this folder's assets, not the app's.
        cls.assets = AssetManager(SAMPLE_DIR)
        renderer = VideoRenderer(SceneRenderer(cls.assets, CharacterAnimator(cls.assets)))

        shutil.rmtree(OUTPUT_DIR, ignore_errors=True)
        cls.progress = []
        started = time.perf_counter()
        video = renderer.render(cls.story, OUTPUT_DIR, cls.progress.append)
        cls.render_seconds = time.perf_counter() - started
        video.replace(SAMPLE_VIDEO)
        cls.probe = ffprobe(SAMPLE_VIDEO)
        print(f"\nSample video: {SAMPLE_VIDEO} (rendered in {cls.render_seconds:.1f}s)")

    # Inputs -------------------------------------------------------------------

    def test_folder_contains_everything_needed(self):
        # Every character's manifest and every image it links to, plus backgrounds.
        characters = CharacterLibrary(SAMPLE_DIR / "assets/characters")  # validates files exist
        self.assertEqual(set(characters.ids()), {"cat", "kid", "adult", "dog", "car", "bicycle"})
        for name in ("garden", "forest", "night"):
            self.assertTrue((SAMPLE_DIR / f"assets/backgrounds/{name}.jpeg").is_file(), name)
        self.assertEqual(self.assets.characters_dir, SAMPLE_DIR / "assets/characters")

    def test_sample_story_covers_every_character_background_and_the_scene_limit(self):
        self.assertEqual(len(self.story.scenes), MAX_SCENES)
        self.assertEqual({s.setting for s in self.story.scenes}, {"garden", "forest", "night"})
        self.assertEqual({s.character for s in self.story.scenes}, {"cat", "kid", "adult", "dog", "car", "bicycle"})

    def test_demo_storyboard_from_prompt_matches_expected(self):
        prompt = (SAMPLE_DIR / "prompt.txt").read_text(encoding="utf-8").strip()
        expected = Story.model_validate_json((SAMPLE_DIR / "expected_storyboard.json").read_text(encoding="utf-8"))
        self.assertEqual(storyboard(Prompt(prompt=prompt)), expected)

    # Output -------------------------------------------------------------------

    def test_video_format(self):
        stream = self.probe["streams"][0]
        self.assertEqual(stream["codec_name"], "h264")
        self.assertEqual((stream["width"], stream["height"]), (WIDTH, HEIGHT))
        self.assertEqual(stream["pix_fmt"], "yuv420p")
        self.assertEqual(stream["avg_frame_rate"], f"{FPS}/1")
        self.assertEqual(len(self.probe["streams"]), 1)  # silent: video only

    def test_video_length_matches_storyboard(self):
        seconds = sum(scene.duration for scene in self.story.scenes)
        self.assertEqual(int(self.probe["streams"][0]["nb_read_frames"]), seconds * FPS)
        self.assertAlmostEqual(float(self.probe["format"]["duration"]), seconds, places=1)

    def test_video_decodes_without_errors(self):
        result = subprocess.run(
            ["ffmpeg", "-v", "error", "-i", str(SAMPLE_VIDEO), "-f", "null", "-"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr.strip(), "")

    def test_each_scene_has_a_distinct_thumbnail(self):
        thumbs = [OUTPUT_DIR / f"scene-{n}.png" for n in range(1, len(self.story.scenes) + 1)]
        for path in thumbs:
            self.assertTrue(path.is_file(), path.name)
        images = [Image.open(p).convert("RGB") for p in thumbs]
        for a, b in zip(images, images[1:]):
            self.assertIsNotNone(ImageChops.difference(a, b).getbbox())

    def test_character_moves_within_a_scene(self):
        # Frames 1 s apart in the bicycle scene must differ.
        index = next(i for i, s in enumerate(self.story.scenes) if s.character == "bicycle")
        start = sum(s.duration for s in self.story.scenes[:index])
        frames = []
        for t in (start + 0.5, start + 1.5):
            raw = subprocess.check_output(
                ["ffmpeg", "-v", "error", "-ss", str(t), "-i", str(SAMPLE_VIDEO),
                 "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
            )
            frames.append(Image.frombytes("RGB", (WIDTH, HEIGHT), raw))
        self.assertIsNotNone(ImageChops.difference(*frames).getbbox())

    def test_storyboard_and_progress_are_saved(self):
        saved = Story.model_validate_json((OUTPUT_DIR / "story.json").read_text(encoding="utf-8"))
        self.assertEqual(saved, self.story)
        self.assertEqual(self.progress[-1], 100)
        self.assertEqual(self.progress, sorted(self.progress))
        self.assertEqual((OUTPUT_DIR / "render.log").read_text().strip(), "")


if __name__ == "__main__":
    unittest.main()
