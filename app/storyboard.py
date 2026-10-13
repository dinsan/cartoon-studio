import json
import os
import re
import textwrap
import urllib.request

from .actions import detect_action
from .models import Prompt, Scene, Story


def _ollama_storyboard(request: Prompt) -> Story:
    instructions = (
        "Write a short children's cartoon storyboard. "
        "Return only JSON matching this schema: "
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

    return Story.model_validate_json(result["message"]["content"])


def _demo_storyboard(request: Prompt) -> Story:
    sentences = [
        s.strip()
        for s in re.split(r"(?<=[.!?])\s+|\n+", request.prompt)
        if s.strip()
    ]

    scenes: list[Scene] = []

    for sentence in sentences:
        lower = sentence.lower()
        setting = next((s for s in ["forest", "night"] if s in lower), "garden")
        action = detect_action(sentence)

        for chunk in textwrap.wrap(sentence, 250):
            scenes.append(
                Scene(
                    narration=chunk,
                    setting=setting,
                    action=action,
                    duration=5,
                )
            )

            if len(scenes) >= 8:
                break

        if len(scenes) >= 8:
            break

    if not scenes:
        scenes = [Scene(narration="Our little adventure begins!", action="idle")]

    return Story(title="A little adventure", scenes=scenes)


def storyboard(request: Prompt) -> Story:
    if request.provider == "ollama":
        return _ollama_storyboard(request)
    return _demo_storyboard(request)
