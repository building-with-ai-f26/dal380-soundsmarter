"""Signed-in flow through the server, with Supabase and the speech service faked.

Checks what gets stored for a recording, the daily cap, consent, and who writes:
reads carry the user's own token (so RLS applies); rows are added only by the
server, with its secret key and the user id it verified. No network.
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
IMAGE_PROMPT = {"id": "arg-i-01", "family": "argue", "mode": "image", "variant": "pair",
                "stimulus_id": "img-arg-01", "text": ""}
STIMULUS = {"id": "img-arg-01", "kind": "pair", "files": ["img-arg-01-a.jpg", "img-arg-01-b.jpg"],
            "title": "Cat | Dog", "credit": "Generated image"}
NYRA = {"language": "en", "verbatim": {"text": "um a kitchen", "words": [
    {"word": "[UM]", "start": 1.0, "end": 1.3}, {"word": " a", "start": 1.4, "end": 1.5},
    {"word": " kitchen.", "start": 1.5, "end": 2.0}]}}


class FakeSupabase:
    """Answers the handful of Supabase calls the server makes, and records them."""

    def __init__(self, sent_today=0):
        self.calls, self.inserted = [], []
        self.sent_today = sent_today
        self.consented = True
        self.key_works = True
        self.prompts = [PROMPT]
        self.files_in_bucket = set()

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
        if path.startswith("/storage/v1/object/public/stimuli/"):
            return httpx.Response(200 if path.rsplit("/", 1)[-1] in self.files_in_bucket else 400)
        table = path.rsplit("/", 1)[-1]
        if request.method == "POST" and not self.key_works:
            return httpx.Response(401, json={"message": "Invalid API key"})
        if request.method == "POST" and json.loads(request.content) == {}:  # the "does the key work?" check
            return httpx.Response(400, json={"code": "23502", "message": "null value in column"})
        if request.method == "POST":
            self.inserted.append((table, json.loads(request.content)))
            return httpx.Response(201, json=[json.loads(request.content)])
        if table == "consents":
            return httpx.Response(200, json=[{"id": 1}] if self.consented else [])
        if table == "prompts":
            return httpx.Response(200, json=self.prompts)
        if table == "stimuli":
            return httpx.Response(200, json=[STIMULUS])
        if table == "prompt_events" and "event" in q:  # the daily-cap count
            return httpx.Response(200, json=[{"id": i} for i in range(self.sent_today)])
        return httpx.Response(200, json=[])


@pytest.fixture
def fake(monkeypatch):
    f = FakeSupabase()
    monkeypatch.setattr(server, "supa", Supa("https://x.supabase.co", "sb_publishable_test", httpx.MockTransport(f),
                                               secret="sb_secret_test"))

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


def test_reads_use_the_users_token_and_writes_use_the_server_key(fake):
    post_recording(TestClient(server.app))
    reads = [r for r in fake.calls if r.method == "GET"]
    writes = [r for r in fake.calls if r.method == "POST"]
    assert reads and len(writes) == 3  # the key check, the 'sent' event, the recording
    for req in reads:
        assert req.headers["apikey"] == "sb_publishable_test"
        assert req.headers["authorization"] == "Bearer user-token"
    for req in writes:
        assert req.headers["apikey"] == "sb_secret_test"
        assert req.headers["authorization"] == "Bearer sb_secret_test"


def test_rows_are_stamped_with_the_verified_user_not_one_the_browser_names(fake):
    c = TestClient(server.app)
    auth = {"Authorization": "Bearer user-token"}
    post_recording(c)
    assert c.get("/api/prompt", headers=auth).status_code == 200
    r = c.post("/api/prompt-event", headers=auth, json={"prompt_id": "des-t-01", "event": "skipped", "user_id": "someone-else"})
    assert r.status_code == 200
    assert [row["user_id"] for _, row in fake.inserted] == ["u1"] * 4


def test_no_consent_means_nothing_is_transcribed_or_stored(fake, monkeypatch):
    fake.consented = False

    async def must_not_run(audio, content_type):
        raise AssertionError("transcription ran without consent")
    monkeypatch.setattr(server, "send_to_nyra", must_not_run)
    assert post_recording(TestClient(server.app)).status_code == 403
    assert fake.inserted == []


def test_without_the_secret_key_nothing_is_transcribed_or_stored(fake, monkeypatch):
    server.supa.secret = ""

    async def must_not_run(audio, content_type):
        raise AssertionError("transcription ran although nothing could be saved")
    monkeypatch.setattr(server, "send_to_nyra", must_not_run)
    assert post_recording(TestClient(server.app)).status_code == 503
    assert TestClient(server.app).get("/api/prompt", headers={"Authorization": "Bearer user-token"}).status_code == 503
    assert fake.inserted == []


def test_a_broken_secret_key_stops_before_transcription(fake, monkeypatch):
    fake.key_works = False  # set, but wrong or revoked

    async def must_not_run(audio, content_type):
        raise AssertionError("transcription ran although nothing could be saved")
    monkeypatch.setattr(server, "send_to_nyra", must_not_run)
    r = post_recording(TestClient(server.app))
    assert r.status_code == 503 and "Nothing was sent" in r.json()["detail"]
    assert fake.inserted == []


def test_signed_out_requests_cannot_add_prompt_events(fake):
    c = TestClient(server.app)
    r = c.post("/api/prompt-event", headers={"Authorization": "Bearer nope"}, json={"prompt_id": "des-t-01", "event": "skipped"})
    assert r.status_code == 401
    assert fake.inserted == []


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


def test_an_image_prompt_comes_with_its_pictures_and_item_names(fake):
    fake.prompts = [IMAGE_PROMPT]
    fake.files_in_bucket = {"img-arg-01-a.jpg", "img-arg-01-b.jpg"}
    r = TestClient(server.app).get("/api/prompt", headers={"Authorization": "Bearer user-token"})
    assert r.status_code == 200 and r.json()["id"] == "arg-i-01"
    assert r.json()["images"] == [
        {"url": "https://x.supabase.co/storage/v1/object/public/stimuli/img-arg-01-a.jpg", "label": "Cat"},
        {"url": "https://x.supabase.co/storage/v1/object/public/stimuli/img-arg-01-b.jpg", "label": "Dog"}]
    assert r.json()["credit"] == "Generated image"


def test_a_prompt_whose_file_is_missing_is_never_served(fake):
    fake.prompts = [IMAGE_PROMPT, PROMPT]
    fake.files_in_bucket = {"img-arg-01-a.jpg"}  # the second picture was never uploaded
    for _ in range(5):
        fake.inserted.clear()
        r = TestClient(server.app).get("/api/prompt", headers={"Authorization": "Bearer user-token"})
        assert r.status_code == 200 and r.json()["id"] == "des-t-01"
        assert [row["prompt_id"] for _, row in fake.inserted] == ["des-t-01"]  # the image prompt isn't marked as seen
    fake.prompts = [IMAGE_PROMPT]
    assert TestClient(server.app).get("/api/prompt", headers={"Authorization": "Bearer user-token"}).status_code == 404
