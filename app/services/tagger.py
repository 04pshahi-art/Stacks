"""Suggest genres and moods from text with a keyword lexicon.

Runs entirely on the server with no model and no network, so uploads still get
useful tags when the local AI is switched off.
"""
import re
from collections import Counter

from .catalog import GENRES, MOODS

_TOKEN_RE = re.compile(r"[a-z']+")

# Each entry is a word stem: "murder" also matches "murdered" and "murderer".
GENRE_STEMS = {
    "Fantasy": ("dragon", "wizard", "magic", "kingdom", "sword", "elf", "elves", "spell", "quest", "realm", "witch", "sorcer"),
    "Science Fiction": ("starship", "galax", "planet", "robot", "android", "alien", "quantum", "orbit", "spacecraft", "laser", "cyber", "colony"),
    "Mystery": ("detective", "clue", "murder", "suspect", "alibi", "inspector", "evidence", "whodunit", "investigat"),
    "Romance": ("kiss", "love", "heart", "romance", "darling", "wedding", "passion", "beloved", "lover"),
    "Thriller": ("chase", "assassin", "agent", "conspiracy", "hostage", "escape", "bomb", "spy", "ambush"),
    "Horror": ("ghost", "haunt", "scream", "blood", "demon", "corpse", "nightmare", "monster", "terror"),
    "Historical": ("empire", "emperor", "revolution", "castle", "century", "queen", "battlefield", "victorian", "medieval"),
    "Literary": ("memory", "grief", "silence", "marriage", "mother", "father", "childhood", "inherit"),
    "Adventure": ("expedition", "voyage", "treasure", "jungle", "mountain", "journey", "explor", "island", "ship"),
    "Poetry": ("verse", "stanza", "sonnet", "poem", "rhyme", "lyric"),
    "Non-fiction": ("research", "history of", "study", "essay", "theory", "evidence shows", "according to"),
    "Self-help": ("habit", "mindset", "productiv", "confidence", "goal", "routine", "motivat", "improve your"),
}

MOOD_STEMS = {
    "Cozy": ("cozy", "tea", "fireplace", "blanket", "bakery", "cottage", "warm", "cosy", "kitchen"),
    "Dark": ("dark", "grim", "shadow", "cruel", "dread", "blood", "bleak", "sinister"),
    "Adventurous": ("adventure", "quest", "expedition", "voyage", "daring", "explor", "journey"),
    "Romantic": ("romance", "kiss", "love", "heart", "tender", "longing", "beloved"),
    "Thoughtful": ("wonder", "reflect", "meaning", "philosoph", "ponder", "memory", "consider"),
    "Funny": ("laugh", "joke", "ridiculous", "grin", "funny", "absurd", "giggle", "hilarious"),
    "Suspenseful": ("tense", "suspense", "trembl", "hunt", "danger", "deadline", "panic", "chase"),
    "Inspiring": ("hope", "courage", "dream", "believe", "triumph", "inspir", "overcome", "resilien"),
    "Melancholic": ("sorrow", "grief", "lonely", "loss", "mourn", "regret", "tears", "farewell"),
    "Mysterious": ("secret", "mystery", "hidden", "strange", "unknown", "riddle", "vanish", "whisper"),
}

MIN_HITS = 2


def _score(tokens: Counter, lexicon: dict[str, tuple[str, ...]]) -> Counter:
    scores: Counter = Counter()
    for label, stems in lexicon.items():
        for stem in stems:
            for token, count in tokens.items():
                if token.startswith(stem):
                    scores[label] += count
    return scores


def _top(scores: Counter, limit: int) -> list[str]:
    return [label for label, hits in scores.most_common(limit) if hits >= MIN_HITS]


def suggest_tags(text: str, limit: int = 2) -> tuple[list[str], list[str]]:
    """Return (genres, moods) that best match the text, strongest first."""
    tokens = Counter(_TOKEN_RE.findall(text.lower()))
    return (
        _top(_score(tokens, GENRE_STEMS), limit),
        _top(_score(tokens, MOOD_STEMS), limit),
    )


def mentioned_tags(message: str) -> tuple[list[str], list[str]]:
    """Genres and moods literally named in a message, e.g. 'something cozy'."""
    lowered = message.lower()
    return (
        [genre for genre in GENRES if genre.lower() in lowered],
        [mood for mood in MOODS if mood.lower() in lowered],
    )
