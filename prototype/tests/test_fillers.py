"""Deterministic test for the filler counter (no network, no API key)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fillers import count_fillers  # noqa: E402


def crisper_response(words):
    """Build a minimal CrisperWhisper-shaped response from a list of words.
    Like the real API, each word keeps its leading space."""
    return {"verbatim": {
        "text": " ".join(words),
        "words": [{"word": " " + w, "start": 0.0, "end": 0.1} for w in words],
    }}


def test_counts_um_and_uh():
    words = "[UM] so I think [UH] the best [UM] costume was [UH]".split()
    assert count_fillers(crisper_response(words)) == {
        "total": 4, "breakdown": {"um": 2, "uh": 2}}


def test_ignores_other_sounds_and_lexical_fillers():
    words = "[ER] like you know [LAUGHTER] mhmm [UM]".split()
    assert count_fillers(crisper_response(words)) == {
        "total": 1, "breakdown": {"um": 1, "uh": 0}}


def test_plural_um_is_talk_about_fillers_not_a_filler():
    # From test C, take 3: "describe the [UM]s as opposed to the [UH]s"
    words = "describe the [UM]s as opposed to the [UH]s".split()
    assert count_fillers(crisper_response(words))["total"] == 0


def test_no_speech():
    assert count_fillers({"verbatim": {"text": "", "words": []}}) == {
        "total": 0, "breakdown": {"um": 0, "uh": 0}}
    assert count_fillers({}) == {"total": 0, "breakdown": {"um": 0, "uh": 0}}
