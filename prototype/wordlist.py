"""The word list: forms counted in every recording, stored but not shown.

From design/2026-11-21-word-list-and-prompt-guidelines.md, tiers 1 and 2
(HANDOFF.md decision 23). These are *raw counts by form*: every time the
form is said, with no judgement about whether that use was a filler. "like"
counts "I like dogs" as well as "it was, like, huge", and it also counts the
"like" inside "I feel like". Classifying uses comes later; no build is assigned.

Bump VERSION whenever a form is added, removed or changed, so stored counts
can be told apart.
"""

import re

VERSION = 2  # 1 = nothing was counted (rows stored before Slice B)

TIER_1 = ["um", "uh", "er", "erm", "ah"]  # filled pauses
TIER_2 = [
    "like", "you know", "i mean",                                # discourse markers
    "kind of", "sort of", "i think", "i guess", "i feel like",   # hedges
    "and stuff", "and things", "and everything", "or something", "or whatever", "or anything",
    "and so on", "and all that", "et cetera", "blah blah blah",  # general extenders
]


def plain(word: str) -> str:
    """' [UM]' -> 'um'; ' Know,' -> 'know'; " I'm" -> "i'm"."""
    return re.sub(r"[^a-z']", "", word.lower())


def count_forms(words: list[str]) -> dict:
    """{"tier1": {form: count}, "tier2": {form: count}} for the words of one recording, in order."""
    seq = [plain(w) for w in words]
    seq = [w for w in seq if w]

    def count(form: str) -> int:
        parts = form.split()
        return sum(seq[i:i + len(parts)] == parts for i in range(len(seq) - len(parts) + 1))

    return {"tier1": {f: count(f) for f in TIER_1}, "tier2": {f: count(f) for f in TIER_2}}
