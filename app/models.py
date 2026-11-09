from typing import Literal

from pydantic import BaseModel, Field, model_validator

from .characters import CharacterError, library
from .config import DEFAULT_CHARACTER, MAX_SCENES

# The cat's original actions. Other characters define their own expressions
# in assets/characters/<id>/character.json (see GET /api/characters).
Action = Literal[
    "idle",
    "walk",
    "run",
    "jump",
    "hop",
    "slide",
    "fly",
    "dance",
    "spin",
    "turn",
    "shake",
    "fall",
    "sit",
    "sleep",
    "wake",
    "wave",
    "nod",
    "bow",
    "look",
    "peek",
    "clap",
    "happy",
    "sad",
    "scared",
    "surprised",
    "laugh",
]


class Scene(BaseModel):
    narration: str = Field(min_length=1, max_length=260)
    setting: Literal["garden", "forest", "night"] = "garden"
    character: str = Field(default=DEFAULT_CHARACTER, description="Character id, e.g. cat, kid, adult, dog, car, bicycle")
    action: str = Field(default="idle", description="One of the character's expressions, e.g. walk, happy, drive")
    duration: int = Field(default=5, ge=3, le=12)

    @model_validator(mode="after")
    def _known_character_and_expression(self):
        try:
            library().validate(self.character, self.action)
        except CharacterError as error:
            raise ValueError(str(error)) from None
        return self


class Story(BaseModel):
    title: str = Field(default="A little adventure", max_length=80)
    scenes: list[Scene] = Field(min_length=1, max_length=MAX_SCENES)


class Prompt(BaseModel):
    prompt: str = Field(min_length=3, max_length=2000)
    provider: Literal["demo", "ollama"] = "demo"
