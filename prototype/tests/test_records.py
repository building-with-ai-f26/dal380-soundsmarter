"""Deterministic tests for the signed-in rules in records.py (no network)."""

import random
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import records  # noqa: E402

PROMPTS = [{"id": f"{f[:3]}-{n}", "family": f} for f in records.FAMILIES for n in range(3)]


def test_never_serves_a_seen_prompt():
    seen = [{"prompt_id": p["id"]} for p in PROMPTS if p["id"] != "arg-2"]
    assert records.choose_prompt(PROMPTS, seen, [])["id"] == "arg-2"
    assert records.choose_prompt(PROMPTS, seen + [{"prompt_id": "arg-2"}], []) is None


def test_families_stay_even_and_never_repeat_back_to_back():
    rng = random.Random(1)
    events, recs = [], []
    for _ in range(10):  # the baseline: 2 per family
        p = records.choose_prompt(PROMPTS, events, recs, rng=rng)
        if recs:
            assert p["family"] != recs[-1]["family"]
        events.append({"prompt_id": p["id"]})
        recs.append({"family": p["family"]})
    counts = {f: sum(r["family"] == f for r in recs) for f in records.FAMILIES}
    assert set(counts.values()) == {2}


def test_baseline_is_one_text_and_one_image_where_a_family_has_images():
    prompts = [{"id": f"{f[:3]}-t{n}", "family": f, "mode": "text"} for f in records.FAMILIES for n in range(4)]
    prompts += [{"id": f"{f[:3]}-i{n}", "family": f, "mode": "image"} for f in ("describe", "argue") for n in range(4)]
    for seed in range(20):  # the order within a family is random, so try many runs
        rng = random.Random(seed)
        events, recs = [], []
        for _ in range(records.BASELINE_SIZE):
            p = records.choose_prompt(prompts, events, recs, rng=rng)
            events.append({"prompt_id": p["id"]})
            recs.append({"family": p["family"], "mode": p["mode"]})
        modes = {f: sorted(r["mode"] for r in recs if r["family"] == f) for f in records.FAMILIES}
        assert modes["describe"] == modes["argue"] == ["image", "text"]
        assert modes["narrate"] == modes["invent"] == modes["explain"] == ["text", "text"]


def test_a_skip_during_baseline_keeps_the_mode_still_owed():
    prompts = [{"id": f"des-t{n}", "family": "describe", "mode": "text"} for n in range(3)]
    prompts += [{"id": f"des-i{n}", "family": "describe", "mode": "image"} for n in range(3)]
    recs = [{"family": "describe", "mode": "text"}]  # text is done, so image is owed
    events = [{"prompt_id": "des-t0"}, {"prompt_id": "des-i0"}]  # des-i0 was skipped
    for seed in range(10):
        p = records.choose_prompt(prompts, events, recs, family="describe", rng=random.Random(seed))
        assert p["mode"] == "image" and p["id"] != "des-i0"


def test_skip_stays_in_family_until_it_runs_out():
    events = [{"prompt_id": "des-0"}, {"prompt_id": "des-1"}]
    assert records.choose_prompt(PROMPTS, events, [], family="describe")["id"] == "des-2"
    events.append({"prompt_id": "des-2"})
    p = records.choose_prompt(PROMPTS, events, [], family="describe")
    assert p["family"] != "describe"  # describe has run out: stop serving it


def test_session_slot():
    now = datetime(2026, 11, 22, 12, 0, tzinfo=timezone.utc)
    assert records.session_slot(None, now) == (1, 1)
    recent = {"created_at": "2026-11-22T11:40:00+00:00", "session_no": 3, "position_in_session": 4}
    assert records.session_slot(recent, now) == (3, 5)
    old = {**recent, "created_at": "2026-11-22T11:29:00Z"}
    assert records.session_slot(old, now) == (4, 1)


def test_skipped_before_resets_at_each_recording():
    events = [
        {"prompt_id": "a", "event": "skipped", "created_at": "2026-11-22T10:00:00Z"},
        {"prompt_id": "b", "event": "sent", "created_at": "2026-11-22T10:01:00Z"},
        {"prompt_id": "c", "event": "served", "created_at": "2026-11-22T10:02:00Z"},
        {"prompt_id": "c", "event": "discarded", "created_at": "2026-11-22T10:03:00Z"},
        {"prompt_id": "d", "event": "skipped", "created_at": "2026-11-22T10:04:00Z"},
    ]
    assert records.skipped_before(list(reversed(events))) == ["c", "d"]


def test_day_starts_at_new_york_midnight():
    late = datetime(2026, 11, 22, 3, 0, tzinfo=timezone.utc)  # 10pm on the 21st in New York
    assert records.day_start_utc(late) == "2026-11-21T05:00:00+00:00"


def test_real_recordings_from_test_c_are_usable():
    import json
    folder = Path(__file__).parent.parent.parent / "experiments" / "stt-compare" / "results" / "crisper"
    files = sorted(folder.glob("*.json"))
    if not files:  # the owner's own recordings; kept out of git, so absent on a fresh copy
        import pytest
        pytest.skip("no local test C results")
    for f in files:
        assert records.unusable_reason(json.loads(f.read_text())) is None, f.name


def rec(family, mode, **metrics):
    return {"family": family, "mode": mode, "metrics": metrics}


def ten_baseline_recordings():
    """2 per family; describe and argue get one text and one image."""
    recs = []
    for f in records.FAMILIES:
        second = "image" if f in ("describe", "argue") else "text"
        recs += [rec(f, "text", fillers_per_100=4.0, prep_s=1.0, speaking_rate_wpm=120.0),
                 rec(f, second, fillers_per_100=6.0, prep_s=2.0, speaking_rate_wpm=140.0)]
    return recs


def test_no_table_until_the_baseline_is_complete():
    assert records.baseline_table(ten_baseline_recordings()[:9]) == []
    assert records.baseline_for(ten_baseline_recordings(), "describe", "text") is None  # the 10th shows no numbers


def test_table_rows_are_family_and_mode_with_baseline_then_average_since():
    recs = ten_baseline_recordings() + [
        rec("describe", "text", fillers_per_100=2.0, prep_s=0.5, speaking_rate_wpm=130.0),
        rec("describe", "text", fillers_per_100=3.0, prep_s=1.5, speaking_rate_wpm=150.0),
        rec("narrate", "text", fillers_per_100=1.0, prep_s=1.0),  # stored before metrics v2: no speaking rate
    ]
    rows = {(r["family"], r["mode"]): r["cells"] for r in records.baseline_table(recs)}
    assert list(rows)[:3] == [("describe", "text"), ("describe", "image"), ("narrate", "text")]
    assert rows[("describe", "text")]["fillers_per_100"] == {"baseline": 4.0, "since": 2.5, "n": 2}
    assert rows[("describe", "image")]["fillers_per_100"] == {"baseline": 6.0, "since": None, "n": 0}
    assert rows[("narrate", "text")]["fillers_per_100"] == {"baseline": 5.0, "since": 1.0, "n": 1}  # two text baselines averaged
    assert rows[("narrate", "text")]["speaking_rate_wpm"] == {"baseline": 130.0, "since": None, "n": 0}
    assert rows[("describe", "text")]["filled_share_count"] == {"baseline": None, "since": None, "n": 0}  # never stored


def test_results_baseline_is_for_the_same_family_and_mode():
    recs = ten_baseline_recordings() + [rec("argue", "image", fillers_per_100=9.0, prep_s=3.0)]
    base = records.baseline_for(recs, "argue", "image")
    assert (base["fillers_per_100"], base["prep_s"]) == (6.0, 2.0)
    assert records.baseline_for(recs, "argue", "audio")["fillers_per_100"] is None  # no baseline for that mode
