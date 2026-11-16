"""Deterministic tests for the results-page numbers (no network, no API key)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from metrics import compute  # noqa: E402


def response(*words):
    """words: (text, start, end) tuples, CrisperWhisper-shaped (leading spaces)."""
    return {"verbatim": {"words": [{"word": " " + t, "start": s, "end": e} for t, s, e in words]}}


SAMPLE = response(
    ("[UM]", 1.4, 1.7),          # first sound: prep time 1.4 s
    ("So", 1.8, 2.0),
    ("I", 2.1, 2.2),
    ("went", 2.2, 2.5),
    ("home.", 2.5, 2.9),
    ("[LAUGHTER]", 3.0, 3.3),    # not a word
    ("[UH]", 3.5, 3.7),          # 0.6 s after "home." -> pause
    ("Then", 3.8, 4.0),
)


def test_counts_include_fillers_rate_divides_by_real_words():
    m = compute(SAMPLE)
    assert m["word_count"] == 7            # 5 real words + 2 fillers
    assert m["fillers_per_100"] == 40.0    # 2 / 5 x 100


def test_prep_time_is_first_sound_even_a_filler():
    assert compute(SAMPLE)["prep_s"] == 1.4


def test_pauses_of_450ms_or_more_are_marked_between_words():
    tokens = compute(SAMPLE)["tokens"]
    assert {"pause": 0.6} in tokens
    i = tokens.index({"pause": 0.6})
    assert tokens[i - 1]["text"] == "home." and tokens[i + 1] == {"text": "uh", "filler": True}
    # 0.1 s gaps don't count; the laughter's own gap is ignored (it's dropped)
    assert sum(1 for t in tokens if "pause" in t) == 1


def test_just_under_threshold_is_not_a_pause():
    m = compute(response(("a", 0.0, 1.0), ("b", 1.44, 1.6)))
    assert not any("pause" in t for t in m["tokens"])


def test_no_speech():
    m = compute({"verbatim": {"words": []}})
    assert m == {"word_count": 0, "fillers_per_100": 0.0, "prep_s": None, "tokens": []}
