"""Results-page numbers, computed in code from CrisperWhisper's word timestamps.

Everything here is deterministic: same transcript in, same numbers out. No AI.
Definitions (owner, 2026-11-15):
  - word count: every spoken word, fillers included
  - fillers per 100 words: fillers / non-filler words x 100
  - prep time: prompt reveal -> first sound (a filler counts as the first sound);
    recording starts at prompt reveal, so it's the first word's start time
  - silent pause: a gap of PAUSE_S or more between two words. Deliberately low,
    so each speaker's own pause pattern shows up as a baseline.
"""

from fillers import COUNTED_FILLERS, normalize, words_from_response

PAUSE_S = 0.45


def is_sound(word: str) -> bool:
    """Bracketed non-word events like [LAUGHTER] aren't words; [UM]/[UH] are."""
    w = word.strip()
    return w.startswith("[") and normalize(w) not in COUNTED_FILLERS


def compute(response: dict) -> dict:
    words = [w for w in words_from_response(response) if not is_sound(w.get("word", ""))]

    tokens, prev_end = [], None
    for w in words:
        start, end = w.get("start"), w.get("end")
        if prev_end is not None and start is not None and start - prev_end >= PAUSE_S:
            tokens.append({"pause": round(start - prev_end, 1)})
        filler = normalize(w.get("word", "")) in COUNTED_FILLERS
        text = normalize(w["word"]) if filler else w.get("word", "").strip()
        tokens.append({"text": text, "filler": filler})
        prev_end = end if end is not None else prev_end

    word_count = len(words)
    fillers = sum(1 for t in tokens if t.get("filler"))
    real_words = word_count - fillers
    return {
        "word_count": word_count,
        "fillers_per_100": round(fillers / real_words * 100, 1) if real_words else 0.0,
        "prep_s": round(words[0]["start"], 1) if words and words[0].get("start") is not None else None,
        "tokens": tokens,
    }
