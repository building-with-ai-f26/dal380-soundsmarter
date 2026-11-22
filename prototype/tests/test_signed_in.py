"""Signed-in flow through the server, with Supabase and the speech service faked.

Checks what gets stored for a recording, the daily cap, consent, and that every
database call carries the user's own token (so RLS applies). No network.
"""

import json
import sys
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))

import server  # noqa: E402
from supa import Supa  # noqa: E402

PROMPT = {"id": "des-t-01", "family": "describe", "mode": "text", "variant": "place",
          "stimulus_id": None, "text": "Describe a kitchen."}
NYRA = {"language": "en", "verbatim": {"text": "um a kitchen", "words": [
    {"word": "[UM]", "start": 1.0, "end": 1.3}, {"word": " a", "start": 1.4, "end": 1.5},
    {"word": " kitchen.", "start": 1.5, "end": 2.0}]}}


class FakeSupabase:
    """Answers the handful of Supabase calls the server makes, and records them."""

    def __init__(self, sent_today=0):
        self.calls, self.inserted = [], []
        self.sent_today = sent_today

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.calls.append(request)
        path, q = request.url.path, dict(request.url.params)
        if path == "/auth/v1/user":
            ok = request.headers.get("authorization") == "Bearer user-token"
            return httpx.Response(200 if ok else 401, json={"id": "u1", "email": "a@b.c"})
        if path == "/auth/v1/signup":
            body = json.loads(request.content)
            if body["data"]["signup_code"] != "GOOD":
                return httpx.Response(500, json={"msg": "Database error saving new user"})
            return httpx.Response(200, json={"access_token": "t", "refresh_token": "r", "user": {"email": body["email"]}})
        table = path.rsplit("/", 1)[-1]
        if request.method == "POST":
            self.inserted.append((table, json.loads(request.content)))
            return httpx.Response(201, json=[json.loads(request.content)])
        if table == "prompts":
            return httpx.Response(200, json=[PROMPT])
        if table == "prompt_events" and "event" in q:  # the daily-cap count
            return httpx.Response(200, json=[{"id": i} for i in range(self.sent_today)])
        return httpx.Response(200, json=[])


@pytest.fixture
def fake(monkeypatch):
    f = FakeSupabase()
    monkeypatch.setattr(server, "supa", Supa("https://x.supabase.co", "sb_publishable_test", httpx.MockTransport(f)))

    async def fake_nyra(audio, content_type):
        return NYRA
    monkeypatch.setattr(server, "send_to_nyra", fake_nyra)
    return f


def post_recording(client):
    return client.post("/transcribe", content=b"audio", headers={
        "Authorization": "Bearer user-token", "X-Prompt-Id": "des-t-01", "Content-Type": "audio/webm"})


def test_recording_is_stored_with_metrics_and_transcription_but_no_audio(fake):
    r = post_recording(TestClient(server.app))
    assert r.status_code == 200 and r.json()["saved"]
    tables = [t for t, _ in fake.inserted]
    assert tables == ["prompt_events", "recordings"]
    assert fake.inserted[0][1]["event"] == "sent"
    row = fake.inserted[1][1]
    assert row["transcription"] == NYRA
    assert row["metrics"]["total"] == 1 and "tokens" not in row["metrics"]
    assert (row["session_no"], row["position_in_session"], row["prep_from"]) == (1, 1, "reveal")
    assert not any(isinstance(v, (bytes, bytearray)) for v in row.values())


def test_every_database_call_uses_the_users_token(fake):
    post_recording(TestClient(server.app))
    for req in fake.calls:
        assert req.headers["apikey"] == "sb_publishable_test"
        assert req.headers["authorization"] == "Bearer user-token"


def test_daily_cap_blocks_before_any_transcription(fake):
    fake.sent_today = 20
    r = post_recording(TestClient(server.app))
    assert r.status_code == 429
    assert fake.inserted == []


def test_bad_token_is_refused(fake):
    r = TestClient(server.app).post("/transcribe", content=b"a", headers={"Authorization": "Bearer nope", "X-Prompt-Id": "x"})
    assert r.status_code == 401


def test_signup_needs_consent_and_a_valid_code(fake):
    c = TestClient(server.app)
    base = {"email": "a@b.c", "password": "longenough", "signup_code": "GOOD"}
    assert c.post("/api/signup", json={**base, "consent": False}).status_code == 400
    assert c.post("/api/signup", json={**base, "signup_code": "BAD", "consent": True}).status_code == 403
    ok = c.post("/api/signup", json={**base, "consent": True})
    assert ok.status_code == 200 and ok.json()["access_token"] == "t"
