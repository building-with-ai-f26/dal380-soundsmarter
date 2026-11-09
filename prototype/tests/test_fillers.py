"""Deterministic test for the filler counter (no network, no API key)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fillers import count_fillers  # noqa: E402


def deepgram_response(words):
    """Build a minimal Deepgram-shaped response from a list of words."""
    return {"results": {"channels": [{"alternatives": [{
        "transcript": " ".join(words),
        "words": [{"word": w} for w in words],
    }]}]}}


def test_counts_um_and_uh():
    words = "um so i think uh the best um costume was uh".split()
    assert count_fillers(deepgram_response(words)) == {
        "total": 4, "breakdown": {"um": 2, "uh": 2}}


def test_ignores_yes_no_sounds_and_lexical_fillers():
    words = "mhmm uh-huh like you know er um".split()
    assert count_fillers(deepgram_response(words)) == {
        "total": 1, "breakdown": {"um": 1, "uh": 0}}


def test_no_speech():
    assert count_fillers({"results": {"channels": [{"alternatives": [{"words": []}]}]}}) == {
        "total": 0, "breakdown": {"um": 0, "uh": 0}}
    assert count_fillers({}) == {"total": 0, "breakdown": {"um": 0, "uh": 0}}
