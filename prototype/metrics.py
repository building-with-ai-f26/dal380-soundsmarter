"""Numbers computed in code from CrisperWhisper's word timestamps and labels.

Everything here is deterministic: same transcript in, same numbers out. No AI.

Shown on the results page (owner, 2026-11-15):
  - word count: every spoken word, fillers included
  - fillers per 100 words: fillers / non-filler words x 100
  - prep time: prompt reveal -> first sound (a filler counts as the first sound);
    recording starts at prompt reveal, so it's the first word's start time
  - silent pause: a gap of PAUSE_S or more between two words. Deliberately low,
    so each speaker's own pause pattern shows up as a baseline.

Stored with every signed-in recording (HANDOFF decisions 23, 25 and 26):
  - pauses split by position: a sentence-end pause follows the end of a
    sentence; any other pause is mid-sentence. A sentence ends at a word that
    ends in . ? or ! in what was said, or in the service's tidied version of
    it (the service often drops the full stop from the spoken words when a
    filler follows). Fillers sitting at the boundary don't hide it: the pause
    after "chimneys. [UM]" is a sentence-end pause.
  - speaking rate: non-filler words per minute, first word start to last word end
  - articulation rate: the same, with silent pauses taken out of the time
  - repetitions, cut-offs and "disfluent" words: the labels the speech service
    puts on each word. A repair is one unbroken run of such words.
  - corrections: how many the service made. Stored, never shown.
  - filled share: of all hesitations, the share that were filled with a sound.
    A filled hesitation is one filler, together with any pause touching it
    ("uh um" is two). A silent hesitation is any pause that touches no filler,
    mid-sentence or at a sentence end. Stored by count and by time.
  - word-list counts by form (wordlist.py)
"""

import difflib

import wordlist
from fillers import COUNTED_FILLERS, normalize, words_from_response

PAUSE_S = 0.45
REPAIR_LABELS = ("cutoff", "disfluent", "repetition")


def is_sound(word: str) -> bool:
    """Bracketed non-word events like [LAUGHTER] aren't words; [UM]/[UH] are."""
    w = word.strip()
    return w.startswith("[") and normalize(w) not in COUNTED_FILLERS


def entries_for(response: dict, words: list[dict]) -> list[int | None]:
    """Which entry of the service's `alignment` list belongs to each word (None if it can't be told).

    Each entry holds the word as said (`verbatim`), the tidied word (`intended`)
    and a label (`type`: match, filler, repetition, cutoff, disfluent, correction).
    Usually each word says which entry is its own (`alignment_index`). Sometimes
    that is missing; then the words and the entries are lined up by their text.
    """
    alignment = response.get("alignment") or []
    if words and all(w.get("alignment_index") is not None for w in words):
        return [w["alignment_index"] if w["alignment_index"] < len(alignment) else None for w in words]
    spoken = [k for k, a in enumerate(alignment) if a.get("verbatim") is not None]
    key = lambda s: s.strip().lower()  # noqa: E731
    matcher = difflib.SequenceMatcher(None, [key(w.get("word", "")) for w in words],
                                      [key(alignment[k]["verbatim"]) for k in spoken], autojunk=False)
    entries: list[int | None] = [None] * len(words)
    for block in matcher.get_matching_blocks():
        for k in range(block.size):
            entries[block.a + k] = spoken[block.b + k]
    return entries


def closes_sentence(text: str | None) -> bool:
    return (text or "").strip().endswith((".", "?", "!"))


def share(part: float, rest: float) -> float | None:
    return round(part / (part + rest), 3) if part + rest > 0 else None


def compute(response: dict) -> dict:
    words = [w for w in words_from_response(response) if not is_sound(w.get("word", ""))]
    alignment = response.get("alignment") or []
    entries = entries_for(response, words)
    labels = [alignment[k]["type"] if k is not None else "match" for k in entries]  # unplaced = an ordinary word
    is_filler = [normalize(w.get("word", "")) in COUNTED_FILLERS for w in words]

    # Transcript tokens for the results page, and every pause with what sits on each side of it
    tokens, pauses, prev_end, prev_i = [], [], None, None
    for i, w in enumerate(words):
        start, end = w.get("start"), w.get("end")
        if prev_end is not None and start is not None and start - prev_end >= PAUSE_S:
            tokens.append({"pause": round(start - prev_end, 1)})
            pauses.append({"s": start - prev_end, "before": prev_i, "after": i})
        text = normalize(w["word"]) if is_filler[i] else w.get("word", "").strip()
        tokens.append({"text": text, "filler": is_filler[i]})
        if end is not None:
            prev_end, prev_i = end, i

    word_count = len(words)
    fillers = sum(is_filler)
    real_words = word_count - fillers

    def per_100(n: float) -> float:
        return round(n / real_words * 100, 1) if real_words else 0.0

    # Pauses by position
    def word_ends_sentence(i: int) -> bool:
        """Full stop on the word as said, on its tidied version, or added by the service right after it."""
        if closes_sentence(words[i].get("word")):
            return True
        k = entries[i]
        if k is None:
            return False
        if closes_sentence(alignment[k].get("intended")):
            return True
        nxt = alignment[k + 1] if k + 1 < len(alignment) else None
        return bool(nxt and nxt.get("verbatim") is None and closes_sentence(nxt.get("intended")))

    def ends_sentence(i: int) -> bool:
        """Is the pause after word i at a sentence end? Looks back past fillers sitting at the boundary."""
        while i >= 0:
            if word_ends_sentence(i):
                return True
            if not is_filler[i]:
                return False
            i -= 1
        return False

    end_pauses = [p for p in pauses if ends_sentence(p["before"])]
    mid_pauses = [p for p in pauses if not ends_sentence(p["before"])]

    # Rates
    first = words[0].get("start") if words else None
    last = words[-1].get("end") if words else None
    span = last - first if first is not None and last is not None and last > first else None
    voiced = span - sum(p["s"] for p in pauses) if span else None
    speaking_rate = round(real_words / span * 60, 1) if span else None
    articulation_rate = round(real_words / voiced * 60, 1) if voiced and voiced > 0 else None

    # Repairs: unbroken runs of cut-off, disfluent and repeated words
    repairs, in_run = 0, False
    for label, filler in zip(labels, is_filler):
        hit = label in REPAIR_LABELS and not filler
        repairs += hit and not in_run
        in_run = hit

    # Filled share: fillers (with any pause touching them) against every pause that touches no filler
    touches_filler = [is_filler[p["before"]] or is_filler[p["after"]] for p in pauses]
    filled_time = sum(w["end"] - w["start"] for w, f in zip(words, is_filler)
                      if f and w.get("start") is not None and w.get("end") is not None)
    filled_time += sum(p["s"] for p, t in zip(pauses, touches_filler) if t)
    silent = [p for p, t in zip(pauses, touches_filler) if not t]

    return {
        "word_count": word_count,
        "fillers_per_100": per_100(fillers),
        "prep_s": round(words[0]["start"], 1) if words and words[0].get("start") is not None else None,
        "tokens": tokens,
        # stored, not shown on the results page
        "mid_pauses": len(mid_pauses),
        "mid_pause_s": round(sum(p["s"] for p in mid_pauses), 2),
        "mid_pauses_per_100": per_100(len(mid_pauses)),
        "end_pauses": len(end_pauses),
        "end_pause_s": round(sum(p["s"] for p in end_pauses), 2),
        "speaking_rate_wpm": speaking_rate,
        "articulation_rate_wpm": articulation_rate,
        "repetitions": sum(lab == "repetition" and not f for lab, f in zip(labels, is_filler)),
        "cutoffs": sum(lab == "cutoff" and not f for lab, f in zip(labels, is_filler)),
        "disfluent": sum(lab == "disfluent" and not f for lab, f in zip(labels, is_filler)),
        "repairs": int(repairs),
        "corrections": sum(a.get("type") == "correction" for a in alignment),
        "filled_hesitations": fillers,
        "silent_hesitations": len(silent),
        "filled_share_count": share(fillers, len(silent)),
        "filled_share_time": share(filled_time, sum(p["s"] for p in silent)),
        "word_forms": wordlist.count_forms([w.get("word", "") for w in words]),
    }
