"""Character library: manifests, artwork, detection, rendering and linking."""

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image, ImageChops

from app.animator import CharacterAnimator
from app.api.main import app
from app.assets import AssetManager
from app.characters import MOTIONS, TRAVEL_MOTIONS, CharacterLibrary, library
from app.config import CHARACTERS_DIR, FPS, PROJECT_ROOT
from app.container import SCENE_RENDERER
from app.models import Prompt, Scene, Story
from app.scene_renderer import GROUND, SceneRenderer
from app.storyboard import storyboard
from tools.link_image import link

NEW_CHARACTERS = ("kid", "adult", "dog", "car", "bicycle")
FOOT_TOLERANCE = 6  # world px


def feet_y(placement):
    alpha = placement.image.convert("RGBA").getchannel("A").point(lambda v: 255 if v > 128 else 0)
    return placement.top + alpha.getbbox()[3]


class ManifestTests(unittest.TestCase):
    def test_five_new_characters_with_20_to_40_expressions(self):
        lib = library()
        for cid in NEW_CHARACTERS:
            with self.subTest(character=cid):
                self.assertIn(cid, lib.characters)
                self.assertGreaterEqual(len(lib.get(cid).expressions), 20)
                self.assertLessEqual(len(lib.get(cid).expressions), 40)
        kinds = {lib.get(c).kind for c in NEW_CHARACTERS}
        self.assertEqual(kinds, {"person", "animal", "vehicle"})

    def test_every_expression_links_to_existing_images_and_known_motions(self):
        for spec in library().characters.values():
            for e in spec.expressions.values():
                with self.subTest(character=spec.id, expression=e.name):
                    self.assertIn(e.motion, MOTIONS)
                    for f in e.frames:
                        self.assertTrue((spec.directory / f).is_file(), f)
                    if len(e.frames) > 1:
                        self.assertGreaterEqual(e.hold or 3, 1)
                    if e.motion in TRAVEL_MOTIONS and spec.id in NEW_CHARACTERS:
                        self.assertGreater(e.speed or 0, 0, "travelling expressions need a matched speed")

    def test_each_character_has_a_default_and_an_idle_drawing_on_the_ground(self):
        assets = SCENE_RENDERER.asset_manager
        for cid in library().ids():
            with self.subTest(character=cid):
                c = assets.character(cid)
                self.assertIn(c.spec.default, c.spec.expressions)
                self.assertIsNotNone(c.idle.shadow, "idle drawing needs a ground shadow")


class RenderTests(unittest.TestCase):
    def test_every_expression_renders_with_feet_on_the_ground(self):
        for spec in library().characters.values():
            for name, e in spec.expressions.items():
                scene = Scene(narration="x", character=spec.id, action=name, duration=4)
                for t in (0.0, 1.25, 3.0):
                    pose = SCENE_RENDERER.pose(scene, t)
                    if pose.lift > 0.5 or e.motion in ("fall", "jump"):
                        continue
                    placed = SCENE_RENDERER.place_character(pose, 600)
                    with self.subTest(character=spec.id, expression=name, t=t):
                        self.assertLessEqual(abs(feet_y(placed) - GROUND), FOOT_TOLERANCE)

    def test_frames_show_the_character(self):
        plain = SCENE_RENDERER.render_frame(Scene(narration="x", character="car", action="idle"), 1.0)
        for cid, action in (("kid", "wave"), ("dog", "bark"), ("bicycle", "ride"), ("adult", "talk")):
            frame = SCENE_RENDERER.render_frame(Scene(narration="x", character=cid, action=action), 1.0)
            self.assertEqual(frame.size, plain.size)
            self.assertIsNotNone(ImageChops.difference(frame, plain).getbbox())

    def test_cycles_change_drawing_on_an_even_beat(self):
        for cid, action in (("kid", "walk"), ("adult", "run"), ("dog", "walk"), ("car", "drive"), ("bicycle", "ride")):
            e = library().get(cid).expressions[action]
            animator = SCENE_RENDERER.animator_for(Scene(narration="x", character=cid, action=action))
            names = [animator.pose(action, f / FPS, 6).sprite.name for f in range(6 * FPS)]
            runs, count = [], 1
            for a, b in zip(names, names[1:]):
                if a == b:
                    count += 1
                else:
                    runs.append(count)
                    count = 1
            with self.subTest(character=cid, expression=action):
                self.assertEqual(set(runs), {e.hold})
                self.assertEqual(len(set(names)), len(e.frames))

    def test_travel_speed_comes_from_the_manifest(self):
        e = library().get("car").expressions["drive"]
        animator = SCENE_RENDERER.animator_for(Scene(narration="x", character="car", action="drive"))
        moved = animator.pose("drive", 1.0, 6).x - animator.pose("drive", 0.0, 6).x
        self.assertAlmostEqual(moved, e.speed * 2, delta=1)  # world px = 2 x output px

    def test_drawings_are_not_deformed_unless_allowed(self):
        # The cat may bend its legs (bow); generated drawings must not be squeezed.
        self.assertTrue(library().get("cat").bend)
        for cid in NEW_CHARACTERS:
            self.assertFalse(library().get(cid).bend)
        pose = SCENE_RENDERER.pose(Scene(narration="x", character="kid", action="scared"), 1.0)
        self.assertEqual(pose.bend, 0.0)


class StoryTests(unittest.TestCase):
    def test_demo_storyboard_picks_characters_and_expressions(self):
        story = (
            "Lily wakes up and yawns. The girl waved at her dad. Dad was drinking coffee. "
            "The puppy barked happily. Lily rode her bike to the park. A red car honked. "
            "The car zoomed away. She laughed. Milo the cat fell asleep."
        )
        got = [(s.character, s.action) for s in storyboard(Prompt(prompt=story)).scenes]
        self.assertEqual(got, [
            ("kid", "yawn"), ("kid", "wave"), ("adult", "coffee"), ("dog", "bark"), ("bicycle", "ride"),
            ("car", "honk"), ("car", "fast"), ("bicycle", "laugh"), ("cat", "sleep"),
        ])

    def test_stories_without_characters_still_use_the_cat(self):
        scenes = storyboard(Prompt(prompt="Pig walks in the garden. Rabbit jump in the forest.")).scenes
        self.assertEqual([s.character for s in scenes], ["cat", "cat"])

    def test_invalid_character_or_expression_is_rejected(self):
        with TestClient(app) as client:
            bad = client.post("/api/jobs", json={"scenes": [{"narration": "x", "character": "car", "action": "dance"}]})
            self.assertEqual(bad.status_code, 422)
            self.assertIn("no expression 'dance'", bad.text)
            self.assertEqual(client.post("/api/jobs", json={"scenes": [{"narration": "x", "character": "robot"}]}).status_code, 422)

    def test_old_storyboards_without_character_default_to_the_cat(self):
        story = Story.model_validate({"scenes": [{"narration": "x", "action": "wave"}]})
        self.assertEqual(story.scenes[0].character, "cat")


class ApiTests(unittest.TestCase):
    def test_characters_endpoint_lists_expressions_and_images(self):
        with TestClient(app) as client:
            data = {c["id"]: c for c in client.get("/api/characters").json()}
            self.assertTrue(set(NEW_CHARACTERS) <= set(data))
            ride = data["bicycle"]["expressions"]["ride"]
            self.assertEqual(len(ride["images"]), len(ride["frames"]))
            image = client.get(ride["images"][0])
            self.assertEqual(image.status_code, 200)
            self.assertEqual(image.headers["content-type"], "image/png")
            self.assertEqual(client.get("/api/characters/kid/character.json").status_code, 404)


class LinkImageTests(unittest.TestCase):
    def test_linking_a_different_image_changes_the_scene(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copytree(PROJECT_ROOT / "assets" / "backgrounds", root / "assets" / "backgrounds")
            shutil.copytree(CHARACTERS_DIR / "kid", root / "assets" / "characters" / "kid")
            kid_dir = root / "assets" / "characters" / "kid"

            def frame():
                assets = AssetManager(root, default_character="kid")
                renderer = SceneRenderer(assets, CharacterAnimator(assets))
                return renderer.render_frame(Scene(narration="x", character="kid", action="happy"), 1.0)

            before = frame()
            # Link "happy" to a different image (a recoloured copy of the drawing).
            with Image.open(kid_dir / "happy.png") as im:
                r, g, b, a = im.convert("RGBA").split()
                Image.merge("RGBA", (b, g, r, a)).save(root / "blue_happy.png")
            result = link(kid_dir, "happy", [root / "blue_happy.png"])
            self.assertEqual(result["frames"], ["happy.png"])
            after = frame()
            self.assertIsNotNone(ImageChops.difference(before, after).getbbox())

            # A brand-new expression becomes available to scenes and stories.
            link(kid_dir, "juggle", [kid_dir / "cheer_01.png", kid_dir / "cheer_02.png"], motion="bounce",
                 keywords=["juggle", "juggling"], hold=4)
            lib = CharacterLibrary(root / "assets" / "characters")
            self.assertEqual(lib.get("kid").expressions["juggle"].frames, ("juggle_01.png", "juggle_02.png"))
            self.assertEqual(lib.detect_expression("The girl is juggling.", "kid"), "juggle")
            manifest = json.loads((kid_dir / "character.json").read_text())
            self.assertEqual(manifest["expressions"]["juggle"]["hold"], 4)


if __name__ == "__main__":
    unittest.main()
