"""Loads character sprites and backgrounds and prepares them for animation.

Each character drawing is a square canvas containing one pose with a soft
shadow drawn under it (see ``character.json`` in each character folder).
For believable motion the shadow has to stay on the ground while the body
moves, so every pose is split into a *body* layer and a
*shadow* layer, and the point where the feet touch the ground is measured so
poses can be anchored to the ground line.
"""

import math
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

from .characters import CharacterLibrary, CharacterSpec
from .config import CHARACTER_BOX, WORLD_HEIGHT, WORLD_SCALE

SETTINGS = ("garden", "forest", "night")

# Shadows in the artwork are pure black at low opacity; the darkest outline
# colour of the character is ~(32, 32, 48) and fully opaque.
_SHADOW_MAX_RGB = 12
_SHADOW_MAX_ALPHA = 120

_OUTLINE = (40, 33, 48, 255)


@dataclass(eq=False)  # identity-hashed so prepared images can be cached
class Sprite:
    """One character pose, prepared at world scale."""

    name: str
    body: Image.Image  # RGBA, cropped to the visible character
    anchor: tuple[float, float]  # feet centre on the ground line (body coords)
    back_x: float  # x of the rear-most foot contact (body coords)
    front_x: float  # x of the front-most foot contact (body coords)
    shadow: Image.Image | None  # RGBA shadow drawn by the artist
    shadow_center: tuple[float, float]  # shadow centre (shadow coords)
    shadow_drop: float  # shadow centre y minus feet y, in world pixels
    arm: Image.Image | None = None  # optional rigged limb (same coords as body)
    arm_pivot: tuple[float, float] | None = None

    @property
    def height(self) -> float:
        return self.anchor[1]


def _mask(channel: Image.Image, test) -> Image.Image:
    return channel.point(lambda v: 255 if test(v) else 0)


def _clean_shadow(shadow: Image.Image) -> Image.Image | None:
    """Redraw a shadow as a solid soft ellipse.

    The artwork's shadow has holes where paws overlapped it; they show as
    soon as the body moves relative to the shadow.
    """
    alpha = shadow.getchannel("A")
    box = alpha.getbbox()
    if box is None:
        return None
    hist = alpha.histogram()
    total = sum(hist[1:])
    # Typical opacity of the drawn shadow (90th percentile of its pixels).
    running, level = 0, 0
    for level in range(1, 256):
        running += hist[level]
        if running >= 0.9 * total:
            break
    width, height = box[2] - box[0], box[3] - box[1]
    pad = max(2, height // 3)
    mask = Image.new("L", (width + 2 * pad, height + 2 * pad), 0)
    ImageDraw.Draw(mask).ellipse((pad, pad, pad + width - 1, pad + height - 1), fill=level)
    mask = mask.filter(ImageFilter.GaussianBlur(pad / 2))
    out = Image.new("RGBA", mask.size, (0, 0, 0, 0))
    out.putalpha(mask)
    return out


def _split_shadow(image: Image.Image) -> tuple[Image.Image, Image.Image]:
    r, g, b, a = image.split()
    darkest = ImageChops.lighter(ImageChops.lighter(r, g), b)
    shadow_mask = ImageChops.multiply(
        _mask(darkest, lambda v: v < _SHADOW_MAX_RGB),
        _mask(a, lambda v: 0 < v < _SHADOW_MAX_ALPHA),
    )
    body = image.copy()
    body.putalpha(ImageChops.multiply(a, ImageChops.invert(shadow_mask)))
    shadow = Image.new("RGBA", image.size, (0, 0, 0, 0))
    shadow.paste(image, (0, 0), shadow_mask)
    return body, shadow


def _flood_region(image: Image.Image, seeds, grow: int) -> Image.Image:
    marked = image.copy()
    for seed in seeds:
        ImageDraw.floodfill(marked, seed, (255, 0, 255, 255), thresh=40)
    changed = ImageChops.difference(marked.convert("RGB"), image.convert("RGB"))
    region = _mask(changed.convert("L"), lambda v: v > 0)
    # Round dilation so the limb's outline is included.
    return _mask(region.filter(ImageFilter.GaussianBlur(grow / 2)), lambda v: v > 8)


def _fill_hole(image: Image.Image, hole: Image.Image, outline: int = 11) -> Image.Image:
    """Fill what was hidden behind a cut-out limb.

    Fill colours (body or transparent background) spread in from the edges of
    the hole; outline pixels are not spread, and a fresh outline is drawn
    where the filled body meets the background.
    """
    r, g, b, a = image.split()
    dark = ImageChops.multiply(
        _mask(ImageChops.lighter(ImageChops.lighter(r, g), b), lambda v: v < 100),
        _mask(a, lambda v: v > 128),
    )
    near_hole = hole.filter(ImageFilter.MaxFilter(2 * outline + 1))
    unknown = ImageChops.lighter(hole, ImageChops.multiply(dark, near_hole))
    known = ImageChops.invert(unknown)
    out = image.copy()
    for _ in range(4 * max(image.size)):
        if not ImageChops.invert(known).getbbox():
            break
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            take = ImageChops.multiply(ImageChops.offset(known, dx, dy), ImageChops.invert(known))
            out = Image.composite(ImageChops.offset(out, dx, dy), out, take)
            known = ImageChops.lighter(known, take)

    alpha = _mask(out.getchannel("A"), lambda v: v > 128)
    out.putalpha(Image.composite(alpha, image.getchannel("A"), unknown))
    near_edge = ImageChops.invert(out.getchannel("A")).filter(ImageFilter.MaxFilter(outline))
    ring = ImageChops.multiply(ImageChops.multiply(unknown, near_edge), out.getchannel("A"))
    out.paste(Image.new("RGBA", out.size, _OUTLINE), (0, 0), ring)
    return out


def _rig_limb(image: Image.Image, rig: dict) -> tuple[Image.Image, Image.Image] | None:
    """Split a limb off ``image``. Returns (body_without_limb, limb) or None.

    ``rig`` comes from ``character.json`` ("rigs": {"<file>.png": ...}):
    ``seeds`` are points inside the limb's fill colours and ``pivot`` is the
    centre of the limb's round shoulder end, in image pixels."""
    for seed in rig["seeds"]:
        r, g, b, a = image.getpixel(seed)
        if a < 250 or max(r, g, b) < 100:
            return None  # artwork changed; the rig no longer matches
    xs = [p[0] for p in rig["seeds"]] + [rig["pivot"][0]]
    ys = [p[1] for p in rig["seeds"]] + [rig["pivot"][1]]
    pad = 160
    box = (
        max(0, min(xs) - pad),
        max(0, min(ys) - pad),
        min(image.width, max(xs) + pad),
        min(image.height, max(ys) + pad),
    )
    crop = image.crop(box)
    seeds = [(x - box[0], y - box[1]) for x, y in rig["seeds"]]
    hole = _flood_region(crop, seeds, grow=14)
    area = hole.histogram()[255]
    if not 0.002 * image.width * image.height < area < 0.05 * image.width * image.height:
        return None

    limb_crop = Image.new("RGBA", crop.size, (0, 0, 0, 0))
    limb_crop.paste(crop, (0, 0), hole)
    base = image.copy()
    base.paste(_fill_hole(crop, hole), box[:2])
    limb = Image.new("RGBA", image.size, (0, 0, 0, 0))
    limb.paste(limb_crop, box[:2])
    return base, limb


def _prepare(name: str, canvas: Image.Image, rig: dict | None, box: float = CHARACTER_BOX) -> Sprite:
    """Prepare one drawing. ``box`` is the output size of the whole canvas."""
    body, shadow = _split_shadow(canvas)

    limb = None
    if rig is not None:
        rigged = _rig_limb(body, rig)
        if rigged is not None:
            body, limb = rigged

    size = max(8, round(box * WORLD_SCALE))  # world width of the canvas
    scale = size / canvas.width
    world_size = (size, max(8, round(canvas.height * scale)))  # keep the aspect ratio

    def to_world(img: Image.Image) -> Image.Image:
        # Premultiplied alpha avoids dark fringes when resampling.
        return img.convert("RGBa").resize(world_size, Image.Resampling.LANCZOS).convert("RGBA")

    body = to_world(body)
    shadow = to_world(shadow)
    if limb is not None:
        limb = to_world(limb)

    solid = _mask(body.getchannel("A"), lambda v: v > 128)
    if solid.getbbox() is None:
        raise ValueError(f"{name}: image has no visible character")
    left, top, right, bottom = body.getchannel("A").getbbox()
    feet_y = solid.getbbox()[3]
    # Feet that actually touch the ground: solid pixels in the bottom rows.
    strip = solid.crop((0, max(0, feet_y - 3 * WORLD_SCALE), world_size[0], feet_y)).getbbox()
    back_x, front_x = strip[0], strip[2]

    shadow_box = shadow.getchannel("A").getbbox()
    if shadow_box:
        anchor_x = (shadow_box[0] + shadow_box[2]) / 2
        shadow_crop = _clean_shadow(shadow)
        shadow_center = (shadow_crop.width / 2, shadow_crop.height / 2)
        shadow_drop = (shadow_box[1] + shadow_box[3]) / 2 - feet_y
    else:
        anchor_x = (back_x + front_x) / 2
        shadow_crop = None
        shadow_center = (0.0, 0.0)
        shadow_drop = 0.0

    crop_box = (left, top, right, max(bottom, feet_y))
    body = body.crop(crop_box)
    arm = limb.crop(crop_box) if limb is not None else None
    arm_pivot = None
    if arm is not None:
        arm_pivot = (rig["pivot"][0] * scale - left, rig["pivot"][1] * scale - top)

    return Sprite(
        name=name,
        body=body,
        anchor=(anchor_x - left, feet_y - top),
        back_x=back_x - left,
        front_x=front_x - left,
        shadow=shadow_crop,
        shadow_center=shadow_center,
        shadow_drop=shadow_drop,
        arm=arm,
        arm_pivot=arm_pivot,
    )


class CharacterAssets:
    """Drawings of one character, prepared on first use."""

    def __init__(self, spec: CharacterSpec):
        self.spec = spec
        self.character_dir = spec.directory
        self._sprites: dict[str, Sprite] = {}

    def _load(self, filename: str) -> Sprite:
        if filename not in self._sprites:
            with Image.open(self.character_dir / filename) as image:
                canvas = image.convert("RGBA")
            rig = self.spec.rigs.get(filename)
            self._sprites[filename] = _prepare(Path(filename).stem.lower(), canvas, rig, self.spec.size)
        return self._sprites[filename]

    def frames(self, expression: str) -> list[Sprite]:
        """Drawings linked to an expression (several for cycles like walk)."""
        e = self.spec.expressions.get(expression)
        return [self._load(f) for f in e.frames] if e else []

    def has(self, expression: str) -> bool:
        return expression in self.spec.expressions

    def sprite(self, expression: str) -> Sprite:
        frames = self.frames(expression)
        return frames[0] if frames else self.idle

    @property
    def idle(self) -> Sprite:
        return self.frames(self.spec.default)[0]

    @property
    def sprites(self) -> dict[str, Sprite]:
        """Every drawing used by the character, by file name stem."""
        for e in self.spec.expressions.values():
            for f in e.frames:
                self._load(f)
        return {s.name: s for s in self._sprites.values()}

    @property
    def shadow_drop(self) -> float:
        # Where a shadow sits relative to feet that touch the ground. (Poses
        # drawn in mid-air have their shadow far below the feet, so use idle's.)
        return self.idle.shadow_drop

    def contact_shadow(self, sprite: Sprite) -> Image.Image | None:
        """Shadow to draw on the ground under ``sprite``.

        Poses drawn in mid-air (their shadow sits well below the feet) use
        the standing pose's shadow, scaled by the renderer for height.
        """
        if sprite.shadow is None or sprite.shadow_drop > 0.1 * sprite.height:
            return self.idle.shadow
        return sprite.shadow

    def get_character_image(self, expression: str) -> Image.Image:
        return self.sprite(expression).body


class AssetManager:
    """Backgrounds plus every character under ``<root>/assets/characters``.

    The ``sprite``/``frames``/... helpers act on the default character (the
    cat) for backwards compatibility; use :meth:`character` for others.
    """

    def __init__(self, root_dir: Path, default_character: str | None = None):
        self.root_dir = Path(root_dir)
        self.characters_dir = self.root_dir / "assets" / "characters"
        self.backgrounds_dir = self.root_dir / "assets" / "backgrounds"
        self.library = CharacterLibrary(self.characters_dir)
        self.default_character = default_character or self.library.default
        self._characters: dict[str, CharacterAssets] = {}

        self.backgrounds: dict[str, Image.Image] = {}
        self._strips: dict[str, Image.Image] = {}
        self.load_backgrounds()

    # Characters -----------------------------------------------------------

    def character(self, cid: str | None = None) -> CharacterAssets:
        cid = cid or self.default_character
        if cid not in self._characters:
            self._characters[cid] = CharacterAssets(self.library.get(cid))
        return self._characters[cid]

    @property
    def character_dir(self) -> Path:
        return self.character().character_dir

    @property
    def sprites(self) -> dict[str, Sprite]:
        return self.character().sprites

    @property
    def shadow_drop(self) -> float:
        return self.character().shadow_drop

    def contact_shadow(self, sprite: Sprite) -> Image.Image | None:
        return self.character().contact_shadow(sprite)

    def frames(self, action: str) -> list[Sprite]:
        return self.character().frames(action)

    def sprite(self, action: str) -> Sprite:
        return self.character().sprite(action)

    def has(self, action: str) -> bool:
        return self.character().has(action)

    def get_character_image(self, action: str) -> Image.Image:
        return self.sprite(action).body

    # Backgrounds ----------------------------------------------------------

    def load_backgrounds(self) -> None:
        for setting in SETTINGS:
            with Image.open(self.backgrounds_dir / f"{setting}.jpeg") as image:
                width = round(image.width * WORLD_HEIGHT / image.height)
                self.backgrounds[setting] = image.convert("RGB").resize(
                    (width, WORLD_HEIGHT), Image.Resampling.LANCZOS
                )

    def world_strip(self, setting: str, min_width: float) -> Image.Image:
        """Background extended to the right by mirrored copies.

        Mirroring keeps the joins seamless, so the camera can follow a
        character that walks further than one background image.
        """
        strip = self._strips.get(setting) or self.backgrounds[setting]
        if strip.width >= min_width:
            return strip
        tile = self.backgrounds[setting]
        tiles = math.ceil(min_width / tile.width)
        strip = Image.new("RGB", (tile.width * tiles, tile.height))
        mirrored = tile.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        for i in range(tiles):
            strip.paste(mirrored if i % 2 else tile, (i * tile.width, 0))
        self._strips[setting] = strip
        return strip
