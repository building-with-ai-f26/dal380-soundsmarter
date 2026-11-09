"""Count fillers in a Deepgram transcription response.

Build 1 counts only "uh" and "um" (HANDOFF.md, Build 1 detail). Deepgram also
flags yes/no sounds (mhmm, uh-huh, ...) when filler_words=true; we ignore them.
Deepgram always spells fillers exactly "uh" / "um", so an exact match is enough.
"""

COUNTED_FILLERS = ("um", "uh")


def words_from_response(response: dict) -> list[dict]:
    """Pull the word list out of Deepgram's nested JSON (empty list if no speech)."""
    try:
        return response["results"]["channels"][0]["alternatives"][0]["words"]
    except (KeyError, IndexError):
        return []


def count_fillers(response: dict) -> dict:
    """Return {"total": int, "breakdown": {"um": int, "uh": int}}."""
    breakdown = {filler: 0 for filler in COUNTED_FILLERS}
    for word in words_from_response(response):
        text = word.get("word", "").lower()
        if text in breakdown:
            breakdown[text] += 1
    return {"total": sum(breakdown.values()), "breakdown": breakdown}
