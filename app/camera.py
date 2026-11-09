"""Camera framing.

The camera looks at the *world* (background with the character already drawn
in), so zooms and pans move the character and the ground together. It stays
level with the ground, keeps the character in shot and follows it when it
travels.
"""

import math

from .config import HEIGHT, WIDTH, WORLD_SCALE

# Keyed by motion name (see app/characters.py MOTIONS).
# zoom: (start, end) over the scene; ease: "out" for a quick punch-in;
# shake: amplitude in output pixels.
CAMERA_MOVES = {
    "idle": dict(zoom=(1.00, 1.10)),
    "sit": dict(zoom=(1.05, 1.16)),
    "nod": dict(zoom=(1.00, 1.10)),
    "clap": dict(zoom=(1.00, 1.12)),
    "sleep": dict(zoom=(1.00, 1.20)),
    "wake": dict(zoom=(1.20, 1.00)),
    "bow": dict(zoom=(1.12, 1.00)),
    "sad": dict(zoom=(1.20, 1.02)),
    "wave": dict(zoom=(1.08, 1.16)),
    "laugh": dict(zoom=(1.08, 1.18)),
    "happy": dict(zoom=(1.06, 1.14)),
    "look": dict(zoom=(1.12, 1.12)),
    "turn": dict(zoom=(1.12, 1.12)),
    "peek": dict(zoom=(1.15, 1.15)),
    "dance": dict(zoom=(1.08, 1.16)),
    "spin": dict(zoom=(1.00, 1.20)),
    "surprised": dict(zoom=(1.00, 1.25), ease="out"),
    "scared": dict(zoom=(1.08, 1.18), shake=3),
    "shake": dict(zoom=(1.06, 1.06), shake=2),
    # Travelling and airborne actions keep a wide shot so there is headroom.
    "walk": dict(zoom=(1.04, 1.04)),
    "run": dict(zoom=(1.04, 1.04)),
    "slide": dict(zoom=(1.04, 1.04)),
    "hop": dict(zoom=(1.06, 1.06)),
    "jump": dict(zoom=(1.03, 1.03)),
    "fly": dict(zoom=(1.02, 1.02)),
    "fall": dict(zoom=(1.02, 1.08)),
    # Generic motions (characters with a drawing per expression).
    "still": dict(zoom=(1.00, 1.06)),
    "cycle": dict(zoom=(1.04, 1.10)),
    "sway": dict(zoom=(1.04, 1.12)),
    "slow": dict(zoom=(1.12, 1.02)),
    "talk": dict(zoom=(1.06, 1.14)),
    "sob": dict(zoom=(1.10, 1.20)),
    "tremble": dict(zoom=(1.08, 1.14)),
    "giggle": dict(zoom=(1.06, 1.14)),
    "pulse": dict(zoom=(1.00, 1.12), ease="out"),
    "bounce": dict(zoom=(1.04, 1.10)),
    # Vehicles: wide shots.
    "engine": dict(zoom=(1.00, 1.06)),
    "drive": dict(zoom=(1.03, 1.03)),
    "ride": dict(zoom=(1.03, 1.03)),
    "drive_fast": dict(zoom=(1.02, 1.02)),
    "reverse": dict(zoom=(1.03, 1.03)),
    "brake": dict(zoom=(1.03, 1.08), shake=1),
    "wheelie": dict(zoom=(1.04, 1.10)),
}

# World-space size of the frame at zoom 1.
VIEW_W = WIDTH * WORLD_SCALE
VIEW_H = HEIGHT * WORLD_SCALE


def smoothstep(p: float) -> float:
    return p * p * (3 - 2 * p)


def ease_out(p: float) -> float:
    return 1 - (1 - p) ** 3


def lerp(a: float, b: float, e: float) -> float:
    return a + (b - a) * e


class Camera:
    def __init__(self, asset_manager=None):
        self.asset_manager = asset_manager

    @staticmethod
    def max_zoom(action: str) -> float:
        return max(CAMERA_MOVES.get(action, {}).get("zoom", (1.0, 1.0)))

    def zoom(self, action: str, t: float, duration: float) -> float:
        move = CAMERA_MOVES.get(action, {})
        p = min(max(t / duration, 0.0), 1.0)
        e = ease_out(p) if move.get("ease") == "out" else smoothstep(p)
        z0, z1 = move.get("zoom", (1.0, 1.0))
        return lerp(z0, z1, e)

    def view_box(
        self,
        action: str,
        t: float,
        duration: float,
        center_x: float,
        focus_y: float,
        world_width: float,
    ) -> tuple[float, float, float, float]:
        """World rectangle to show: (left, top, right, bottom)."""
        zoom = self.zoom(action, t, duration)
        w, h = VIEW_W / zoom, VIEW_H / zoom

        cx = center_x
        # Keep the ground where it is at zoom 1 as far as possible: push in
        # toward the character but never show past the bottom of the world.
        cy = min(max(focus_y, h / 2), VIEW_H - h / 2)

        shake = CAMERA_MOVES.get(action, {}).get("shake", 0) * WORLD_SCALE
        if shake:
            cx += shake * (math.sin(t * 23) + 0.5 * math.sin(t * 37))
            cy += shake * (math.sin(t * 29) + 0.5 * math.sin(t * 41))

        cx = min(max(cx, w / 2), world_width - w / 2)
        cy = min(max(cy, h / 2), VIEW_H - h / 2)
        return cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2
