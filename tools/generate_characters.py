"""Draw the built-in characters and write their manifests.

    python -m tools.generate_characters            # all characters
    python -m tools.generate_characters kid car    # only some

For every character this writes ``assets/characters/<id>/``:

* one PNG per drawing (``walk_01.png`` ... for multi-frame expressions),
* ``character.json`` linking each expression to its drawings, the motion the
  app uses to animate it, story keywords and (for travelling motions) the
  speed that matches the stride or wheel rotation,

and a contact sheet ``docs/characters/<id>.png`` for browsing expressions.
Hand-made art can replace any PNG; keep the same framing (feet on the
canvas's ground line, same scale) or adjust ``size`` in ``character.json``.
"""

import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from PIL import Image, ImageDraw, ImageFont

from app.config import FPS, WORLD_SCALE
from tools.art import bicycle, car, dog, people
from tools.art.human import draw_person
from tools.art.kit import CANVAS

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets" / "characters"
DOCS = ROOT / "docs" / "characters"


@dataclass
class CharacterDef:
    id: str
    name: str
    kind: str
    description: str
    keywords: list
    target: tuple  # ("height" | "width", output pixels) for the idle drawing
    expressions: Callable[[], list]
    draw: Callable
    speed: Callable  # (expr, images_meta) -> output px/s or None


def _scale(size: float) -> float:
    """Canvas px -> output px."""
    return size / CANVAS


# Travel speeds ------------------------------------------------------------------
# A drawing cycle of ``hold`` video frames per drawing; speeds in canvas px/s.


def person_speed(expr, meta):
    if expr.motion not in ("walk", "run"):
        return None
    j = meta[0]
    separation = abs(j["ankle_front"][0] - j["ankle_back"][0])
    steps_per_second = FPS / (2 * (expr.hold or 3))
    flight = 1.35 if expr.motion == "run" else 1.0
    return separation * steps_per_second * flight


def dog_speed(expr, meta):
    if expr.motion not in ("walk", "run"):
        return None
    pose = expr.frames[0]
    foot = lambda a: dog.UPPER * math.sin(math.radians(a[0])) + dog.LOWER * math.sin(math.radians(a[1]))
    separation = abs(foot(pose.front_near) - foot(pose.front_far))
    flight = 1.6 if expr.motion == "run" else 1.0
    return separation * FPS / (2 * (expr.hold or 3)) * flight


def wheel_speed(radius, step_deg, hold):
    return radius * math.radians(step_deg) * FPS / hold


def car_speed(expr, meta):
    if expr.motion in ("drive", "reverse"):
        return wheel_speed(car.WHEEL_R, car.DRIVE_STEP, expr.hold or 1)
    if expr.motion == "drive_fast":
        return wheel_speed(car.WHEEL_R, car.DRIVE_STEP, 1) * 1.8
    return None


def bike_speed(expr, meta):
    if expr.motion not in ("ride", "drive", "drive_fast"):
        return None
    poses = expr.frames
    if expr.motion == "drive_fast" and poses[0].blur:
        return wheel_speed(bicycle.WHEEL_R, bicycle.SPOKE_STEP, 1) * 1.6
    step = (poses[1].spoke - poses[0].spoke) if len(poses) > 1 else bicycle.SPOKE_STEP
    return wheel_speed(bicycle.WHEEL_R, abs(step), expr.hold or 1)


def _draw_person(style):
    def draw(pose):
        return draw_person(style, pose)
    return draw


def _no_meta(fn):
    def draw(pose):
        return fn(pose), None
    return draw


CHARACTERS = {
    "kid": CharacterDef(
        "kid", "Kid", "person", "A cheerful girl with pigtails, yellow T-shirt and blue shorts.",
        ["kid", "child", "children", "girl", "boy", "daughter", "son", "little one", "lily", "kiddo", "student"],
        ("height", 130), lambda: people.person_expressions(people.KID, adult=False), _draw_person(people.KID), person_speed,
    ),
    "adult": CharacterDef(
        "adult", "Adult", "person", "A friendly grown-up with glasses, shirt and tie.",
        ["adult", "man", "woman", "dad", "father", "mum", "mom", "mother", "teacher", "grandpa", "grandma", "uncle", "aunt",
         "parent", "grown-up", "mr", "mrs"],
        ("height", 185), lambda: people.person_expressions(people.ADULT, adult=True), _draw_person(people.ADULT), person_speed,
    ),
    "dog": CharacterDef(
        "dog", "Dog", "animal", "A floppy-eared puppy with a red collar.",
        ["dog", "puppy", "pup", "doggy", "doggie", "hound", "animal", "pet", "rex", "buddy"],
        ("height", 88), dog.dog_expressions, _no_meta(dog.draw_dog), dog_speed,
    ),
    "car": CharacterDef(
        "car", "Car", "vehicle", "A little red car with a face (four wheels).",
        ["car", "cars", "vehicle", "auto", "automobile", "taxi", "jeep", "truck", "van", "four-wheel", "4x4", "beep"],
        ("width", 255), car.car_expressions, _no_meta(car.draw_car), car_speed,
    ),
    "bicycle": CharacterDef(
        "bicycle", "Bicycle", "vehicle", "A blue bicycle ridden by the kid in a green helmet.",
        ["bicycle", "bike", "bikes", "cycle", "cycling", "cyclist", "ride a bike", "rode a bike", "pedal", "pedalled", "pedaled"],
        ("height", None), bicycle.bicycle_expressions, _no_meta(bicycle.draw_bike), bike_speed,
    ),
}


def _solid_box(image: Image.Image):
    return image.getchannel("A").point(lambda v: 255 if v > 128 else 0).getbbox()


def generate(cid: str) -> dict:
    spec = CHARACTERS[cid]
    exprs = spec.expressions()
    out_dir = ASSETS / cid
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("*.png"):
        old.unlink()

    # Size: output pixels for the whole canvas, from the idle drawing.
    idle_img, _ = spec.draw(exprs[0].frames[0])
    box = _solid_box(idle_img)
    if spec.id == "bicycle":
        size = generate.kid_size  # same scale as the kid so the rider matches
    elif spec.target[0] == "height":
        size = spec.target[1] / (box[3] - box[1]) * CANVAS
    else:
        size = spec.target[1] / (box[2] - box[0]) * CANVAS
    if spec.id == "kid":
        generate.kid_size = size
    # Save at the smallest canvas that still has >= 1 px per world pixel.
    save_px = min(CANVAS, math.ceil(size * WORLD_SCALE / 64) * 64)

    manifest = {
        "id": spec.id,
        "name": spec.name,
        "kind": spec.kind,
        "description": spec.description,
        "size": round(size, 1),
        "bend": False,
        "keywords": spec.keywords,
        **({"rider": True} if spec.id == "bicycle" else {}),
        "default": exprs[0].name,
        "expressions": {},
    }
    thumbs = []
    for expr in exprs:
        files, meta = [], []
        for i, frame in enumerate(expr.frames):
            image, m = spec.draw(frame)
            meta.append(m)
            name = f"{expr.name}.png" if len(expr.frames) == 1 else f"{expr.name}_{i + 1:02d}.png"
            small = image.convert("RGBa").resize((save_px, save_px), Image.Resampling.LANCZOS).convert("RGBA")
            # Flat cartoon colours fit a 256-colour palette (with alpha): ~5x smaller files.
            small = small.quantize(colors=256, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE)
            small.save(out_dir / name, optimize=True)
            files.append(name)
            if i == 0:
                thumbs.append((expr.name, len(expr.frames), image))
        entry = {"frames": files, "motion": expr.motion, "keywords": expr.keywords, "description": expr.description}
        if len(files) > 1:
            entry["hold"] = expr.hold or 3
        speed = spec.speed(expr, meta)
        if speed:
            entry["speed"] = round(speed * _scale(size), 1)
        manifest["expressions"][expr.name] = entry

    (out_dir / "character.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    contact_sheet(spec, thumbs)
    print(f"{cid:8s} {len(exprs)} expressions, {sum(len(e['frames']) for e in manifest['expressions'].values())} drawings,"
          f" size {size:.0f}, saved at {save_px}px")
    return manifest


generate.kid_size = None


def contact_sheet(spec: CharacterDef, thumbs, cols=8, cell=200):
    DOCS.mkdir(parents=True, exist_ok=True)
    rows = math.ceil(len(thumbs) / cols)
    sheet = Image.new("RGB", (cols * cell, rows * (cell + 22) + 40), (236, 244, 236))
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 14)
        title = ImageFont.truetype("DejaVuSans-Bold.ttf", 20)
    except OSError:
        font = title = ImageFont.load_default()
    draw.text((10, 8), f"{spec.name} ({spec.id}): {len(thumbs)} expressions", fill=(40, 34, 48), font=title)
    for i, (name, frames, image) in enumerate(thumbs):
        x, y = (i % cols) * cell, 40 + (i // cols) * (cell + 22)
        thumb = image.resize((cell, cell), Image.Resampling.LANCZOS)
        sheet.paste(thumb, (x, y), thumb)
        label = name if frames == 1 else f"{name} ({frames} frames)"
        draw.text((x + 6, y + cell), label, fill=(40, 34, 48), font=font)
    sheet.save(DOCS / f"{spec.id}.png", optimize=True)


def main(argv):
    wanted = argv or list(CHARACTERS)
    unknown = set(wanted) - set(CHARACTERS)
    if unknown:
        raise SystemExit(f"Unknown character(s): {', '.join(sorted(unknown))}. Choose from {', '.join(CHARACTERS)}.")
    if "bicycle" in wanted and "kid" not in wanted:
        # The bicycle is drawn at the kid's scale so the rider matches.
        kid_manifest = ASSETS / "kid" / "character.json"
        if kid_manifest.exists():
            generate.kid_size = json.loads(kid_manifest.read_text(encoding="utf-8"))["size"]
        else:
            wanted = ["kid"] + wanted
    for cid in sorted(wanted, key=list(CHARACTERS).index):
        generate(cid)


if __name__ == "__main__":
    main(sys.argv[1:])
