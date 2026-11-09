import json
import os
import re
import textwrap
import urllib.request

from .characters import library
from .config import MAX_SCENES
from .models import Prompt, Scene, Story


def _ollama_storyboard(request: Prompt) -> Story:
    instructions = (
        "Write a children's cartoon storyboard for the user's story. "
        "Create one scene for each event in the story, in order, and do not "
        f"merge events: use up to {MAX_SCENES} scenes, and aim for "
        f"{MAX_SCENES} when the story has that many events. "
        "Each scene's narration is one or two short sentences. "
        "For each scene choose the character who acts in it and one of that "
        "character's expressions from this list (character: expressions):\n"
        + library().prompt_catalogue()
        + "\nReturn only JSON matching this schema: "
        + json.dumps(Story.model_json_schema())
    )

    body = json.dumps(
        {
            "model": os.getenv("OLLAMA_MODEL", "llama3.2"),
            "stream": False,
            "format": "json",
            "messages": [
                {"role": "system", "content": instructions},
                {"role": "user", "content": request.prompt},
            ],
        }
    ).encode()

    url = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/") + "/api/chat"

    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
    )

    with urllib.request.urlopen(req, timeout=120) as response:
        result = json.loads(response.read())

    data = json.loads(result["message"]["content"])
    # Models sometimes return more scenes than asked; keep the first ones
    # rather than rejecting the whole storyboard.
    if isinstance(data, dict) and isinstance(data.get("scenes"), list):
        data["scenes"] = [_repair_scene(s) for s in data["scenes"][:MAX_SCENES]]
    return Story.model_validate(data)


def _repair_scene(scene):
    """Map an unknown character/expression from the model to a valid one
    instead of rejecting the whole storyboard."""
    if not isinstance(scene, dict):
        return scene
    lib = library()
    narration = str(scene.get("narration", ""))
    cid = scene.get("character")
    if cid not in lib.characters:
        cid = lib.detect_character(narration) or lib.default
    scene["character"] = cid
    if scene.get("action") not in lib.get(cid).expressions:
        scene["action"] = lib.detect_expression(narration, cid)
    return scene


def _demo_storyboard(request: Prompt) -> Story:
    sentences = [
        s.strip()
        for s in re.split(r"(?<=[.!?])\s+|\n+", request.prompt)
        if s.strip()
    ]

    scenes: list[Scene] = []
    lib = library()
    # Sentences that don't name anyone ("He jumps.") keep the last character;
    # before the first name, use the first character the story mentions.
    character = next((c for c in map(lib.detect_character, sentences) if c), lib.default)
    last_person = None

    for sentence in sentences:
        lower = sentence.lower()
        setting = next((s for s in ["forest", "night"] if s in lower), "garden")
        character = lib.detect_character(sentence, previous=character, last_person=last_person)
        if lib.get(character).is_person:
            last_person = character
        action = lib.detect_expression(sentence, character)

        for chunk in textwrap.wrap(sentence, 250):
            scenes.append(
                Scene(
                    narration=chunk,
                    setting=setting,
                    character=character,
                    action=action,
                    duration=5,
                )
            )

            if len(scenes) >= MAX_SCENES:
                break

        if len(scenes) >= MAX_SCENES:
            break

    if not scenes:
        scenes = [Scene(narration="Our little adventure begins!", action="idle")]

    return Story(title="A little adventure", scenes=scenes)


def storyboard(request: Prompt) -> Story:
    if request.provider == "ollama":
        return _ollama_storyboard(request)
    return _demo_storyboard(request)
