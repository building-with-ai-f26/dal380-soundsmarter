"""Count fillers in a CrisperWhisper (Nyra API) transcription response.

Counts only "um" and "uh" (HANDOFF.md). CrisperWhisper's verbatim transcript
writes fillers in brackets, e.g. "[UM]" or "[UH]"; we strip the brackets and
match exactly, so "um" said as a word in plural ("the [UM]s") doesn't count.
"""

import re

COUNTED_FILLERS = ("um", "uh")


def words_from_response(response: dict) -> list[dict]:
    """Pull the verbatim word list out of the response (empty list if no speech)."""
    try:
        return response["verbatim"]["words"] or []
    except (KeyError, TypeError):
        return []


def normalize(word: str) -> str:
    """' [UM]' -> 'um'; ' [UM]s' -> 'ums'; ' Hello,' -> 'hello'."""
    return re.sub(r"[^a-z]", "", word.lower())


def count_fillers(response: dict) -> dict:
    """Return {"total": int, "breakdown": {"um": int, "uh": int}}."""
    breakdown = {filler: 0 for filler in COUNTED_FILLERS}
    for word in words_from_response(response):
        text = normalize(word.get("word", ""))
        if text in breakdown:
            breakdown[text] += 1
    return {"total": sum(breakdown.values()), "breakdown": breakdown}
