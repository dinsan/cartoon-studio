"""Link a character expression to your own image(s).

    # replace the kid's "happy" drawing
    python -m tools.link_image kid happy ~/Pictures/happy_girl.png

    # a two-drawing cycle for the dog's "wag"
    python -m tools.link_image dog wag wag_a.png wag_b.png --hold 2

    # add a brand-new expression to the adult
    python -m tools.link_image adult juggle juggle.png --motion sway --keywords juggle juggling juggled

The images are copied into ``assets/characters/<character>/`` and the
expression's ``frames`` in ``character.json`` point at them. Scenes using that
expression show the new image(s) the next time the app starts.

Image guidelines (see README "Characters"): transparent background (PNG),
the character standing on the same ground line and at the same scale as the
existing drawings of that character, facing right. An optional soft shadow
(pure black, low opacity) under the feet is kept on the ground by the app.
"""

import argparse
import json
import shutil
import sys
from pathlib import Path

from PIL import Image

from app.characters import MOTIONS, TRAVEL_MOTIONS, CharacterError, load_character
from app.config import CHARACTERS_DIR


def link(character_dir: Path, expression: str, images: list[Path], motion=None, keywords=None, hold=None,
         speed=None, description=None) -> dict:
    manifest_path = character_dir / "character.json"
    if not manifest_path.is_file():
        raise CharacterError(f"No character.json in {character_dir}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expressions = manifest.setdefault("expressions", {})
    entry = expressions.get(expression)
    if entry is None:
        entry = {"frames": [], "motion": motion or "idle", "keywords": keywords or [expression],
                 "description": description or f"{expression} (custom image)"}
        expressions[expression] = entry
    if motion:
        if motion not in MOTIONS:
            raise CharacterError(f"Unknown motion '{motion}'. Choose from: {', '.join(sorted(MOTIONS))}")
        entry["motion"] = motion
    if keywords:
        entry["keywords"] = keywords
    if description:
        entry["description"] = description

    warnings = []
    files = []
    for i, src in enumerate(images):
        src = Path(src).expanduser()
        with Image.open(src) as im:
            im.load()
            has_alpha = im.mode in ("RGBA", "LA", "PA") or (im.mode == "P" and "transparency" in im.info)
            if not has_alpha or im.convert("RGBA").getchannel("A").getextrema()[0] == 255:
                warnings.append(f"{src.name}: no transparent background, the whole rectangle will be drawn")
            name = f"{expression}.png" if len(images) == 1 else f"{expression}_{i + 1:02d}.png"
            dest = character_dir / name
            if src.suffix.lower() == ".png":
                if src.resolve() != dest.resolve():
                    shutil.copyfile(src, dest)
            else:
                im.convert("RGBA").save(dest)
        files.append(name)
    entry["frames"] = files
    if len(files) > 1:
        entry["hold"] = hold or entry.get("hold", 3)
    elif hold:
        entry["hold"] = hold
    if speed:
        entry["speed"] = speed
    if entry["motion"] in TRAVEL_MOTIONS and not entry.get("speed"):
        warnings.append(f"motion '{entry['motion']}' moves the character: set --speed (output px/s) to match the stride")

    original = manifest_path.read_text(encoding="utf-8")
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    try:
        load_character(character_dir)  # validate the result
    except CharacterError:
        manifest_path.write_text(original, encoding="utf-8")
        raise
    return {"expression": expression, "frames": files, "motion": entry["motion"], "warnings": warnings}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("character", help="character id, e.g. kid, adult, dog, car, bicycle, cat")
    parser.add_argument("expression", help="expression name (existing to replace, new to add)")
    parser.add_argument("images", nargs="+", type=Path, help="one image, or several for an animated cycle")
    parser.add_argument("--motion", help="how the app animates it, e.g. idle, sway, walk, drive")
    parser.add_argument("--keywords", nargs="+", help="story words that select this expression")
    parser.add_argument("--hold", type=int, help="video frames per drawing when cycling several images")
    parser.add_argument("--speed", type=float, help="travel speed in output px/s for walk/run/drive/ride motions")
    parser.add_argument("--description")
    parser.add_argument("--characters-dir", type=Path, default=CHARACTERS_DIR)
    args = parser.parse_args(argv)
    try:
        result = link(args.characters_dir / args.character, args.expression, args.images, args.motion,
                      args.keywords, args.hold, args.speed, args.description)
    except (CharacterError, OSError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    print(f"Linked {args.character}.{result['expression']} -> {', '.join(result['frames'])} (motion: {result['motion']})")
    for w in result["warnings"]:
        print(f"Warning: {w}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
