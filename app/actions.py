import re

ACTION_KEYWORDS = {
    "run": ["run", "running", "ran", "sprint"],
    "walk": ["walk", "walking", "stroll"],
    "jump": ["jump", "jumping", "leap", "leapt"],
    "hop": ["hop", "hopping", "hopped"],
    "dance": ["dance", "dancing"],
    "wave": ["wave", "waving"],
    "sleep": ["sleep", "sleeping", "asleep", "slept"],
    "wake": ["wake", "waking", "woke up", "woke"],
    "sit": ["sit", "sitting", "sat down", "sat"],
    "spin": ["spin", "spinning", "spun", "twirl"],
    "turn": ["turn", "turning"],
    "shake": ["shake", "shaking", "shook", "shiver"],
    "fall": ["fall", "falling", "fell"],
    "fly": ["fly", "flying", "flies", "flew"],
    "slide": ["slide", "sliding", "slid"],
    "clap": ["clap", "clapping", "clapped"],
    "nod": ["nod", "nodding", "nodded"],
    "bow": ["bow", "bowing"],
    "look": ["look", "looking"],
    "peek": ["peek", "peeking"],
    "happy": ["happy", "excited", "cheerful"],
    "sad": ["sad", "crying", "unhappy"],
    "scared": ["scared", "afraid", "frightened"],
    "surprised": ["surprised", "shocked", "amazed"],
    "laugh": ["laugh", "laughing", "giggle"],
    "idle": ["wait", "waiting", "stand", "standing", "stood"],
}


# Regular verb endings, so "walks", "jumped" and "waved" match "walk",
# "jump" and "wave". Irregular forms are listed explicitly above.
_SUFFIXES = r"(?:s|es|ed|d|ing)?"


def detect_action(sentence: str) -> str:
    lower = sentence.lower()

    for action, keywords in ACTION_KEYWORDS.items():
        for keyword in keywords:
            if re.search(r"\b" + re.escape(keyword) + _SUFFIXES + r"\b", lower):
                return action

    return "idle"
