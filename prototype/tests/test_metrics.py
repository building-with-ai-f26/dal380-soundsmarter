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
    assert (m["word_count"], m["fillers_per_100"], m["prep_s"], m["tokens"]) == (0, 0.0, None, [])
    assert m["speaking_rate_wpm"] is None and m["filled_share_count"] is None and m["repairs"] == 0


# ---------- stored metrics (decisions 23, 25, 26) ----------

def labelled(words, extra_alignment=(), indexed=True):
    """words: (text, start, end, label). Builds a response with the service's `alignment` labels."""
    alignment = [{"verbatim": t, "intended": t, "type": lab} for t, _, _, lab in words] + list(extra_alignment)
    return {"alignment": alignment, "verbatim": {"words": [
        {"word": " " + t, "start": s, "end": e, "alignment_index": i if indexed else None}
        for i, (t, s, e, _) in enumerate(words)]}}


STORY = [
    ("So", 0.0, 0.2, "match"), ("I", 0.2, 0.4, "match"), ("went", 0.4, 0.6, "match"), ("home.", 0.6, 1.0, "match"),
    # 1.0 s pause after a full stop: sentence-end
    ("Then", 2.0, 2.2, "match"), ("I", 2.2, 2.4, "match"),
    ("I", 2.4, 2.6, "repetition"), ("st-", 2.6, 2.8, "cutoff"),      # one repair: two words in a row
    ("started", 2.8, 3.0, "match"),
    # 0.5 s pause, a filler, 0.6 s pause: one filled hesitation lasting 0.5 + 0.4 + 0.6 = 1.5 s
    ("[UM]", 3.5, 3.9, "filler"),
    ("cooking", 4.5, 5.0, "match"),
    # 1.0 s pause mid-sentence, touching no filler: one silent hesitation
    ("you", 6.0, 6.2, "match"), ("know", 6.2, 6.4, "match"), ("like", 6.4, 6.6, "match"),
    ("a-", 6.6, 6.8, "cutoff"),                                      # a second repair
    ("pasta.", 6.8, 7.0, "match"),
]
CORRECTION = [{"verbatim": None, "intended": ".", "type": "correction"}]


def test_pauses_are_split_by_position():
    m = compute(labelled(STORY))
    assert (m["end_pauses"], m["end_pause_s"]) == (1, 1.0)
    assert (m["mid_pauses"], m["mid_pause_s"]) == (3, 2.1)
    assert m["mid_pauses_per_100"] == 20.0  # 3 pauses / 15 non-filler words


def test_speaking_rate_and_articulation_rate():
    m = compute(labelled(STORY))
    assert m["speaking_rate_wpm"] == 128.6      # 15 non-filler words in 7.0 s
    assert m["articulation_rate_wpm"] == 230.8  # the same words in 7.0 - 3.1 s of pauses


def test_repairs_are_unbroken_runs_of_labelled_words():
    m = compute(labelled(STORY, CORRECTION))
    assert (m["repetitions"], m["cutoffs"], m["disfluent"]) == (1, 2, 0)
    assert m["repairs"] == 2
    assert m["corrections"] == 1  # stored, never shown


def test_filled_share_by_count_and_by_time():
    m = compute(labelled(STORY))
    # Silent hesitations are all pauses touching no filler: the 1.0 s at the sentence end and the 1.0 s mid-sentence
    assert (m["filled_hesitations"], m["silent_hesitations"]) == (1, 2)
    assert m["filled_share_count"] == 0.333
    assert m["filled_share_time"] == 0.429  # 1.5 s filled against 2.0 s silent


def test_word_forms_are_raw_counts():
    forms = compute(labelled(STORY))["word_forms"]
    assert forms["tier1"]["um"] == 1 and forms["tier1"]["uh"] == 0
    assert forms["tier2"]["you know"] == 1 and forms["tier2"]["like"] == 1 and forms["tier2"]["i mean"] == 0
    feel = compute(response(("I", 0, 0.1), ("feel", 0.1, 0.2), ("like", 0.2, 0.3), ("I", 0.3, 0.4), ("like", 0.4, 0.5), ("it", 0.5, 0.6)))
    assert feel["word_forms"]["tier2"]["i feel like"] == 1
    assert feel["word_forms"]["tier2"]["like"] == 2  # raw: every "like", whatever its use


def test_labels_are_found_even_when_words_do_not_point_at_them():
    # Some responses leave out alignment_index, and split "[UM]s" (the word, said in the plural) in two.
    words = STORY[:9] + [("[UM]s", 3.1, 3.3, "match")] + STORY[9:]
    resp = labelled(words, indexed=False)
    i = next(k for k, a in enumerate(resp["alignment"]) if a["verbatim"] == "[UM]s")
    resp["alignment"][i:i + 1] = [{"verbatim": "[UM]", "intended": "[UM]", "type": "filler"},
                                  {"verbatim": "s", "intended": "s", "type": "match"}]
    m = compute(resp)
    assert (m["repetitions"], m["cutoffs"], m["repairs"]) == (1, 2, 2)
    assert m["filled_hesitations"] == 1  # "[UM]s" is a word about fillers, not a filler


def test_back_to_back_fillers_are_two_hesitations():
    m = compute(response(("So", 0, 0.2), ("[UH]", 0.3, 0.5), ("[UM]", 0.6, 0.8), ("yes", 0.9, 1.0)))
    assert m["filled_hesitations"] == 2


def test_sentence_ends_come_from_the_tidied_text_too():
    # The service drops the full stop from the spoken word when a filler follows,
    # but keeps it in its tidied version: "chimneys [UM] I" / "chimneys."
    words = [("the", 0.0, 0.2, "match"), ("chimneys", 0.2, 0.6, "match"), ("[UM]", 0.7, 1.0, "filler"),
             ("I", 2.0, 2.2, "match"), ("saw", 2.2, 2.4, "match"), ("smoke", 3.0, 3.2, "match")]
    resp = labelled(words)
    assert compute(resp)["end_pauses"] == 0                      # nothing marks the sentence end yet
    resp["alignment"][1]["intended"] = "chimneys."
    m = compute(resp)
    assert (m["end_pauses"], m["mid_pauses"]) == (1, 1)          # the pause after "[UM]" is at the boundary; "saw ... smoke" is not
    # Same when the service adds the full stop as its own entry after the word
    resp = labelled(words)
    resp["alignment"].insert(2, {"verbatim": None, "intended": ".", "type": "correction"})
    for w in resp["verbatim"]["words"][2:]:
        w["alignment_index"] += 1
    assert compute(resp)["end_pauses"] == 1
