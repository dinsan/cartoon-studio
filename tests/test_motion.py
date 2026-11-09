"""Checks that character motion stays physically plausible."""

import unittest
from typing import get_args

from app.actions import detect_action
from app.animator import RUN_HOLD, WALK_HOLD
from app.camera import VIEW_W
from app.config import FPS, WIDTH
from app.container import CHARACTER_ANIMATOR, SCENE_RENDERER
from app.models import Action, Scene
from app.scene_renderer import GROUND

ALL_ACTIONS = get_args(Action)
# World pixels; the world is rendered at 2x the output resolution.
FOOT_TOLERANCE = 6


def times(duration):
    return [f / FPS for f in range(duration * FPS)]


def feet_y(placement):
    """Lowest solid pixel row of a placed character, in world coordinates."""
    alpha = placement.image.convert("RGBA").getchannel("A").point(lambda v: 255 if v > 128 else 0)
    return placement.top + alpha.getbbox()[3]


class MotionTests(unittest.TestCase):
    def test_grounded_poses_keep_feet_on_the_ground(self):
        # Rotations, bends and squashes must not make feet float or sink.
        for action in ALL_ACTIONS:
            for t in times(6)[::3]:
                pose = CHARACTER_ANIMATOR.pose(action, t, 6)
                if pose.lift > 0.5 or pose.sprite.name == "jump":
                    continue
                placed = SCENE_RENDERER.place_character(pose, 600)
                with self.subTest(action=action, t=t):
                    self.assertLessEqual(abs(feet_y(placed) - GROUND), FOOT_TOLERANCE)

    def test_airborne_height_follows_lift(self):
        pose = CHARACTER_ANIMATOR.pose("jump", 0.84, 6)  # top of the first leap
        self.assertGreater(pose.lift, 100)
        placed = SCENE_RENDERER.place_character(pose, 600)
        self.assertLess(feet_y(placed), GROUND - 100)

    def test_character_stays_in_frame(self):
        for action in ALL_ACTIONS:
            scene = Scene(narration="x", action=action, duration=12)
            plan = SCENE_RENDERER.plan(scene)
            for i, t in enumerate(times(12)):
                pose = CHARACTER_ANIMATOR.pose(action, t, 12)
                x = plan.start_x + pose.x
                left, _, right, _ = SCENE_RENDERER.camera.view_box(
                    action, t, 12, plan.camera_x[i], GROUND - 100, plan.world_width
                )
                screen_x = (x - left) / (right - left) * WIDTH
                with self.subTest(action=action, t=t):
                    self.assertGreater(screen_x, 0.1 * WIDTH)
                    self.assertLess(screen_x, 0.9 * WIDTH)

    def test_camera_never_leaves_the_background(self):
        scene = Scene(narration="x", action="run", duration=12)
        plan = SCENE_RENDERER.plan(scene)
        for i, t in enumerate(times(12)):
            left, top, right, bottom = SCENE_RENDERER.camera.view_box(
                "run", t, 12, plan.camera_x[i], GROUND - 100, plan.world_width
            )
            self.assertGreaterEqual(left, 0)
            self.assertLessEqual(right, plan.world_width)
            self.assertLessEqual(right - left, VIEW_W)

    def test_walk_and_run_poses_change_on_an_even_beat(self):
        for action, hold in (("walk", WALK_HOLD), ("run", RUN_HOLD)):
            names = [CHARACTER_ANIMATOR.pose(action, t, 6).sprite.name for t in times(6)]
            runs, count = [], 1
            for a, b in zip(names, names[1:]):
                if a == b:
                    count += 1
                else:
                    runs.append(count)
                    count = 1
            with self.subTest(action=action):
                self.assertGreater(len(runs), 4)
                self.assertEqual(set(runs), {hold})

    def test_no_single_frame_pose_flicker(self):
        for action in ALL_ACTIONS:
            names = [CHARACTER_ANIMATOR.pose(action, t, 6).sprite.name for t in times(6)]
            changes = [i for i in range(1, len(names)) if names[i] != names[i - 1]]
            holds = [b - a for a, b in zip(changes, changes[1:])]
            with self.subTest(action=action):
                self.assertTrue(all(h >= 2 for h in holds))

    def test_travel_speed_matches_stepping(self):
        # Walking distance per step equals the stride so feet don't skate.
        first = CHARACTER_ANIMATOR.pose("walk", 0, 6).x
        after_step = CHARACTER_ANIMATOR.pose("walk", 2 * WALK_HOLD / FPS, 6).x
        self.assertAlmostEqual(after_step - first, 29 * 2, delta=1)

    def test_wave_moves_the_paw(self):
        arms = {round(CHARACTER_ANIMATOR.pose("wave", t, 6).arm) for t in times(2)}
        self.assertGreater(max(arms) - min(arms), 10)

    def test_detects_inflected_verbs(self):
        cases = {
            "The cat walks home.": "walk",
            "Milo jumped over the log.": "jump",
            "She waved goodbye.": "wave",
            "He runs fast.": "run",
            "It slept all day.": "sleep",
            "Milo fell asleep.": "sleep",
            "Milo fell off the wall.": "fall",
            "A bowl of milk.": "idle",
        }
        for sentence, action in cases.items():
            with self.subTest(sentence=sentence):
                self.assertEqual(detect_action(sentence), action)


if __name__ == "__main__":
    unittest.main()
