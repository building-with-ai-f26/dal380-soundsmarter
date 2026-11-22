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
