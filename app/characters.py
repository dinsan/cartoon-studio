"""Character library: reads ``assets/characters/<id>/character.json``.

Each manifest links a character's expressions to image files and to the
motion the animator uses. Swap an image (or point ``frames`` at a different
file) and every scene using that expression picks it up.

Manifest fields (see README "Characters"):

    id, name, kind, description
    size      output pixels for the full width of one image canvas
    bend      whether leg-bending motions (bow, sit...) may deform drawings
    keywords  words in a story that mean this character
    default   expression used when nothing else matches
    rigs      optional per-image limb rigs (the cat's waving paw)
    expressions: {
      name: {frames: [png, ...], motion, keywords, description,
             hold (video frames per drawing), speed (output px/s),
             lean (degrees, for run)}
    }
"""

import json
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from .config import CHARACTERS_DIR, DEFAULT_CHARACTER

# Motions the animator implements (app/animator.py).
MOTIONS = frozenset(
    {
        # original actions (used by the cat)
        "idle", "walk", "run", "jump", "hop", "slide", "fly", "dance", "spin", "turn", "shake", "fall", "sit",
        "sleep", "wake", "wave", "nod", "bow", "look", "peek", "clap", "happy", "sad", "scared", "surprised", "laugh",
        # generic motions for characters with a drawing per expression
        "still", "sway", "slow", "bounce", "sob", "tremble", "giggle", "talk", "pulse", "cycle",
        # vehicles
        "engine", "drive", "drive_fast", "reverse", "brake", "ride", "wheelie",
    }
)

# Motions that move the character across the scene.
TRAVEL_MOTIONS = frozenset({"walk", "run", "drive", "drive_fast", "reverse", "ride"})

_SUFFIXES = r"(?:s|es|ed|d|ing)?"

# Very common verbs that only decide an expression when nothing more specific
# is in the sentence ("she went to sleep" -> sleep, not walk).
WEAK_KEYWORDS = frozenset(
    {"go", "went", "goes", "say", "said", "says", "tell", "told", "ask", "asked", "see", "saw", "look", "looked",
     "show", "showed", "call", "called", "move", "moving", "good", "new", "fun", "leave", "left", "get", "got",
     "give", "gave", "want", "wanted", "stand", "wait"}
)


class CharacterError(ValueError):
    pass


@dataclass(frozen=True)
class ExpressionSpec:
    name: str
    frames: tuple[str, ...]
    motion: str
    keywords: tuple[str, ...] = ()
    description: str = ""
    hold: int | None = None
    speed: float | None = None  # output px per second
    lean: float | None = None


@dataclass
class CharacterSpec:
    id: str
    name: str
    kind: str
    description: str
    size: float
    bend: bool
    keywords: tuple[str, ...]
    default: str
    expressions: dict[str, ExpressionSpec]
    directory: Path
    rigs: dict = field(default_factory=dict)
    rider: bool = False  # a vehicle with a person on it (he/she can refer to it)

    @property
    def is_person(self) -> bool:
        return self.kind == "person" or self.rider

    def expression(self, name: str) -> ExpressionSpec:
        return self.expressions.get(name) or self.expressions[self.default]

    def summary(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "kind": self.kind,
            "description": self.description,
            "keywords": list(self.keywords),
            "expressions": {
                e.name: {"description": e.description, "motion": e.motion, "frames": list(e.frames)}
                for e in self.expressions.values()
            },
        }


def load_character(directory: Path) -> CharacterSpec:
    path = directory / "character.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise CharacterError(f"{path}: {error}") from error

    cid = data.get("id", directory.name)
    expressions = {}
    for name, e in (data.get("expressions") or {}).items():
        frames = tuple(e.get("frames") or ())
        if not frames:
            raise CharacterError(f"{path}: expression '{name}' has no frames")
        for frame in frames:
            if not (directory / frame).is_file():
                raise CharacterError(f"{path}: expression '{name}' uses missing image '{frame}'")
        motion = e.get("motion", "idle")
        if motion not in MOTIONS:
            raise CharacterError(f"{path}: expression '{name}' has unknown motion '{motion}' (choose from {', '.join(sorted(MOTIONS))})")
        expressions[name] = ExpressionSpec(
            name=name,
            frames=frames,
            motion=motion,
            keywords=tuple(k.lower() for k in e.get("keywords", ())),
            description=e.get("description", ""),
            hold=e.get("hold"),
            speed=e.get("speed"),
            lean=e.get("lean"),
        )
    if not expressions:
        raise CharacterError(f"{path}: no expressions")
    default = data.get("default", "idle")
    if default not in expressions:
        default = next(iter(expressions))
    return CharacterSpec(
        id=cid,
        name=data.get("name", cid.title()),
        kind=data.get("kind", "character"),
        description=data.get("description", ""),
        size=float(data.get("size", 140)),
        bend=bool(data.get("bend", False)),
        keywords=tuple(k.lower() for k in data.get("keywords", ())),
        default=default,
        expressions=expressions,
        directory=directory,
        rigs=data.get("rigs", {}),
        rider=bool(data.get("rider", False)),
    )


class CharacterLibrary:
    """All characters found under a ``characters`` directory."""

    def __init__(self, directory: Path):
        self.directory = Path(directory)
        self.characters: dict[str, CharacterSpec] = {}
        for sub in sorted(p for p in self.directory.iterdir() if (p / "character.json").is_file()):
            spec = load_character(sub)
            self.characters[spec.id] = spec
        if not self.characters:
            raise CharacterError(f"No characters found in {self.directory}")

    @property
    def default(self) -> str:
        return DEFAULT_CHARACTER if DEFAULT_CHARACTER in self.characters else next(iter(self.characters))

    def ids(self) -> list[str]:
        return list(self.characters)

    def get(self, cid: str) -> CharacterSpec:
        try:
            return self.characters[cid]
        except KeyError:
            raise CharacterError(f"Unknown character '{cid}'. Available: {', '.join(self.characters)}") from None

    def validate(self, cid: str, expression: str) -> None:
        spec = self.get(cid)
        if expression not in spec.expressions:
            raise CharacterError(
                f"Character '{cid}' has no expression '{expression}'. Available: {', '.join(spec.expressions)}"
            )

    # Story text -> character / expression ------------------------------------

    @staticmethod
    def _first_match(text: str, keywords) -> int | None:
        best = None
        for keyword in keywords:
            m = re.search(r"\b" + re.escape(keyword) + _SUFFIXES + r"\b", text)
            if m and (best is None or m.start() < best):
                best = m.start()
        return best

    def detect_character(self, sentence: str, previous: str | None = None, last_person: str | None = None) -> str | None:
        """Character a sentence is about.

        A bicycle mention wins (the bicycle includes its rider: "she rode her
        bike"); otherwise the character named first in the sentence. With no
        name, he/she/they mean ``last_person`` and anything else ``previous``."""
        text = sentence.lower()
        found = {}
        for cid, spec in self.characters.items():
            pos = self._first_match(text, spec.keywords)
            if pos is not None:
                found[cid] = pos
        if not found:
            if last_person and re.search(r"\b(he|she|him|her|they|them)\b", text):
                return last_person
            return previous
        if "bicycle" in found:
            return "bicycle"
        return min(found, key=found.get)

    def detect_expression(self, sentence: str, cid: str) -> str:
        """Expression a sentence describes for character ``cid``.

        Multi-word phrases ("fell asleep") beat single words; specific words
        beat common verbs (go, say, look...); ties go to the word that comes
        first in the sentence."""
        from .actions import detect_action

        spec = self.get(cid)
        text = sentence.lower()
        best, best_rank = None, None
        for name, e in spec.expressions.items():
            for keyword in (name,) + e.keywords:
                pos = self._first_match(text, (keyword,))
                if pos is None:
                    continue
                tier = 0 if " " in keyword else (2 if keyword in WEAK_KEYWORDS else 1)
                rank = (tier, pos)
                if best_rank is None or rank < best_rank:
                    best, best_rank = name, rank
        if best:
            return best
        generic = detect_action(sentence)
        return generic if generic in spec.expressions else spec.default

    def prompt_catalogue(self) -> str:
        """Characters and expressions, for an LLM prompt."""
        lines = []
        for spec in self.characters.values():
            lines.append(f"- {spec.id} ({spec.description}): " + ", ".join(spec.expressions))
        return "\n".join(lines)


@lru_cache(maxsize=8)
def library(directory: str | None = None) -> CharacterLibrary:
    return CharacterLibrary(Path(directory) if directory else CHARACTERS_DIR)
