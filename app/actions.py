import re

ACTION_KEYWORDS = {
    "run": ["run", "running", "ran", "sprint"],
    "walk": ["walk", "walking", "stroll"],
    "jump": ["jump", "jumping", "leap"],
    "hop": ["hop", "hopping"],
    "dance": ["dance", "dancing"],
    "wave": ["wave", "waving"],
    "sleep": ["sleep", "sleeping", "asleep"],
    "wake": ["wake", "waking", "woke up"],
    "sit": ["sit", "sitting", "sat down"],
    "spin": ["spin", "spinning", "twirl"],
    "turn": ["turn", "turning"],
    "shake": ["shake", "shaking", "shiver"],
    "fall": ["fall", "falling", "fell"],
    "fly": ["fly", "flying"],
    "slide": ["slide", "sliding"],
    "clap": ["clap", "clapping"],
    "nod": ["nod", "nodding"],
    "bow": ["bow", "bowing"],
    "look": ["look", "looking"],
    "peek": ["peek", "peeking"],
    "happy": ["happy", "excited", "cheerful"],
    "sad": ["sad", "crying", "unhappy"],
    "scared": ["scared", "afraid", "frightened"],
    "surprised": ["surprised", "shocked", "amazed"],
    "laugh": ["laugh", "laughing", "giggle"],
    "idle": ["wait", "waiting", "stand", "standing"],
}


def detect_action(sentence: str) -> str:
    lower = sentence.lower()

    for action, keywords in ACTION_KEYWORDS.items():
        for keyword in keywords:
            if re.search(r"\b" + re.escape(keyword) + r"\b", lower):
                return action

    return "idle"
