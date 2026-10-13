from typing import Literal

from pydantic import BaseModel, Field

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
    action: Action = "idle"
    duration: int = Field(default=5, ge=3, le=12)


class Story(BaseModel):
    title: str = Field(default="A little adventure", max_length=80)
    scenes: list[Scene] = Field(min_length=1, max_length=8)


class Prompt(BaseModel):
    prompt: str = Field(min_length=3, max_length=2000)
    provider: Literal["demo", "ollama"] = "demo"
