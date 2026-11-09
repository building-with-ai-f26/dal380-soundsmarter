"""Deterministic tests for the access gate (no network, no API key)."""

import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from access import AccessDenied, Gate  # noqa: E402


def make_gate(**kw):
    kw.setdefault("today", lambda: date(2026, 11, 9))
    return Gate(codes=["ABC", "DEF"], takes_per_code=3, daily_cap=30, **kw)


def denied_status(fn, *args):
    with pytest.raises(AccessDenied) as e:
        fn(*args)
    return e.value.status


def test_valid_code_gets_three_takes_then_stops():
    g = make_gate()
    for left in (3, 2, 1):
        assert g.takes_left("abc") == left  # case doesn't matter
        g.reserve("abc")
    assert denied_status(g.reserve, "ABC") == 429


def test_missing_or_wrong_code_is_refused():
    g = make_gate()
    assert denied_status(g.reserve, "") == 403
    assert denied_status(g.reserve, "NOPE") == 403


def test_daily_cap_across_codes_resets_next_day():
    day = [date(2026, 11, 9)]
    g = Gate(codes=[f"C{i}" for i in range(20)], takes_per_code=3, daily_cap=30, today=lambda: day[0])
    for i in range(10):
        for _ in range(3):
            g.reserve(f"C{i}")
    assert denied_status(g.reserve, "C10") == 429
    day[0] = date(2026, 11, 10)
    g.reserve("C10")


def test_refund_gives_the_take_back():
    g = make_gate()
    g.refund(g.reserve("ABC"))
    assert g.takes_left("ABC") == 3


def test_no_codes_is_open_locally_but_locked_on_server():
    assert Gate(codes=[""]).reserve("") is None
    assert denied_status(Gate(codes=[""], on_server=True).reserve, "") == 503
