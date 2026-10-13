import math

from PIL import Image

from .assets import AssetManager

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


class Camera:
    def __init__(self, asset_manager: AssetManager):
        self.asset_manager = asset_manager

    def view(self, setting: str, action: str, t: float, duration: int) -> Image.Image:
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
