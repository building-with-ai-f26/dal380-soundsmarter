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


def transcription(text: str, seconds: float, language: str = "en") -> dict:
    """A speech-service response for `text`, its words spread evenly over `seconds` (starting at 1 s)."""
    words = text.split()
    step = seconds / len(words)
    return {"language": language, "verbatim": {"text": text, "words": [
        {"word": (" " if i else "") + w, "start": round(1 + i * step, 2), "end": round(1 + (i + 0.8) * step, 2)}
        for i, w in enumerate(words)]}}


# One filler and 16 other words over 8 seconds: a usable recording
NYRA = transcription("[UM] the kitchen in the house I grew up in was small and yellow and always warm", 8)


class FakeSupabase:
    """Answers the handful of Supabase calls the server makes, and records them."""

    def __init__(self, sent_today=0):
        self.calls, self.inserted = [], []
        self.sent_today = sent_today
        self.consented = True
        self.key_works = True
        self.database_down = False
        self.prompts = [PROMPT]
        self.files_in_bucket = set()
        self.recordings = []

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
        if request.method == "POST" and self.database_down:
            if isinstance(self.database_down, tuple):  # (status, body): an odd but well-formed answer
                return httpx.Response(self.database_down[0], json=self.database_down[1])
            return httpx.Response(500, text="upstream connect error")
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
        if table == "recordings" and "metrics" in q.get("select", ""):
            return httpx.Response(200, json=self.recordings)
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
    assert (row["metrics_version"], row["word_list_version"]) == (3, 2)
    assert row["metrics"]["speaking_rate_wpm"] and row["metrics"]["word_forms"]["tier1"]["um"] == 1
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


def test_a_database_outage_stops_before_transcription(fake, monkeypatch):
    fake.database_down = True  # the key is fine, but the database can't answer properly

    async def must_not_run(audio, content_type):
        raise AssertionError("transcription ran although nothing could be saved")
    monkeypatch.setattr(server, "send_to_nyra", must_not_run)
    assert post_recording(TestClient(server.app)).status_code == 503
    # Well-formed answers that are not the healthy one also stop it: a list, "no permission", an unexpected success
    for status, body in [(400, ["not", "an", "object"]), (400, {"code": "42501"}), (200, {})]:
        fake.database_down = (status, body)
        assert post_recording(TestClient(server.app)).status_code == 503


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
    # Not yet counted as seen: the page reports "served" once the pictures have loaded
    assert r.json()["confirm_served"] and fake.inserted == []
    ok = TestClient(server.app).post("/api/prompt-event", headers={"Authorization": "Bearer user-token"},
                                     json={"prompt_id": "arg-i-01", "event": "served"})
    assert ok.status_code == 200 and fake.inserted == [("prompt_events", {"user_id": "u1", "prompt_id": "arg-i-01", "event": "served"})]
    bad = TestClient(server.app).post("/api/prompt-event", headers={"Authorization": "Bearer user-token"},
                                      json={"prompt_id": "arg-i-01", "event": "sent"})
    assert bad.status_code == 400  # the page can never claim a recording was sent


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


def rejected(fake, monkeypatch, response):
    """Send a recording whose transcription comes back as `response`; return the server's answer."""
    async def fake_nyra(audio, content_type):
        return response
    monkeypatch.setattr(server, "send_to_nyra", fake_nyra)
    r = post_recording(TestClient(server.app))
    assert r.status_code == 200
    return r.json()


def test_unusable_recordings_store_no_row_and_count_toward_the_cap(fake, monkeypatch):
    cases = {
        "too_few_words": transcription("[UM] a kitchen I think", 3),
        "not_english": transcription(NYRA["verbatim"]["text"], 8, language="de"),
        "implausible_rate": transcription(NYRA["verbatim"]["text"], 1),    # 17 words in one second
    }
    for reason, response in cases.items():
        fake.inserted.clear()
        body = rejected(fake, monkeypatch, response)
        assert body["rejected"] and body["reason"] == reason and body["message"]
        assert "total" not in body and "fillers_per_100" not in body          # no numbers
        assert [(t, row["event"]) for t, row in fake.inserted] == [("prompt_events", "rejected")]  # no recordings row
        assert "rejected" in server.records.COUNTS_TOWARD_CAP


def test_a_slow_but_real_recording_is_not_rejected(fake, monkeypatch):
    body = rejected(fake, monkeypatch, transcription(NYRA["verbatim"]["text"], 20))  # 17 words in 20 s = 0.85 a second
    assert body.get("saved") and not body.get("rejected")


def test_transcription_is_not_forced_to_english():
    assert "language" not in server.NYRA_FIELDS


def eleven_recordings():
    old = [{"family": "describe", "mode": "text", "metrics": {"fillers_per_100": 4.0, "prep_s": 2.0}}] * 10
    return old + [{"family": "describe", "mode": "text", "metrics": {"fillers_per_100": 1.0, "prep_s": 1.0}}]


def test_from_the_eleventh_recording_results_carry_the_users_baseline(fake):
    fake.recordings = eleven_recordings()[:10]  # this one is the 10th: still baseline, no comparison
    assert post_recording(TestClient(server.app)).json()["baseline"] is None
    fake.recordings = eleven_recordings()
    body = post_recording(TestClient(server.app)).json()
    assert (body["baseline"]["fillers_per_100"], body["baseline"]["prep_s"]) == (4.0, 2.0)


def test_baseline_table_endpoint(fake):
    c, auth = TestClient(server.app), {"Authorization": "Bearer user-token"}
    fake.recordings = eleven_recordings()[:9]
    assert c.get("/api/baseline", headers=auth).json() == {"rows": []}
    fake.recordings = eleven_recordings()
    rows = c.get("/api/baseline", headers=auth).json()["rows"]
    assert [(r["family"], r["mode"]) for r in rows] == [("describe", "text")]
    assert rows[0]["cells"]["fillers_per_100"] == {"baseline": 4.0, "since": 1.0, "n": 1}
    assert c.get("/api/baseline").status_code == 401
