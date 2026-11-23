"""Tests for the fixes from the Build 3 security review (SECURITY.md). No network."""

import asyncio
import sys
from pathlib import Path

import httpx
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))

import server  # noqa: E402
from access import Gate  # noqa: E402
from analytics_proxy import allowed  # noqa: E402
from test_signed_in import PROMPT, fake, post_recording, transcription  # noqa: E402,F401  (fake is a pytest fixture)

GOOD = transcription("I walked to the shop and bought some bread and milk for the week ahead of us.", 8.0)


def test_the_auto_generated_api_pages_are_off():
    c = TestClient(server.app)
    for path in ("/docs", "/redoc", "/openapi.json"):
        assert c.get(path).status_code == 404


def test_a_request_that_says_it_is_huge_is_refused_before_it_is_read():
    c = TestClient(server.app)
    r = c.post("/api/signin", content=b"{}", headers={"Content-Length": "50000000", "Content-Type": "application/json"})
    assert r.status_code == 413


def test_one_transcription_at_a_time_per_account(fake, monkeypatch):  # noqa: F811
    """Two recordings sent at the same moment are handled one after the other, and neither is lost."""
    running, most = 0, 0

    async def slow_nyra(audio, content_type):
        nonlocal running, most
        running += 1
        most = max(most, running)
        await asyncio.sleep(0.05)
        running -= 1
        return GOOD
    monkeypatch.setattr(server, "send_to_nyra", slow_nyra)
    monkeypatch.setattr(server, "user_locks", {})

    async def two_at_once():
        headers = {"Authorization": "Bearer user-token", "X-Prompt-Id": "des-t-01", "Content-Type": "audio/webm"}
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app), base_url="http://test") as c:
            return await asyncio.gather(*(c.post("/transcribe", content=b"audio", headers=headers) for _ in range(2)))
    replies = asyncio.run(two_at_once())
    assert [r.status_code for r in replies] == [200, 200]
    assert most == 1


def test_a_failed_recording_does_not_block_the_next_one(fake, monkeypatch):  # noqa: F811
    monkeypatch.setattr(server, "user_locks", {})
    fake.consented = False
    assert post_recording(TestClient(server.app)).status_code == 403
    fake.consented = True
    assert post_recording(TestClient(server.app)).status_code == 200


def test_sign_in_attempts_are_limited_per_visitor(fake, monkeypatch):  # noqa: F811
    monkeypatch.setattr(server, "auth_attempts", {})
    monkeypatch.setattr(server, "AUTH_LIMIT", 3)
    c = TestClient(server.app)
    body = {"email": "a@b.c", "password": "password1"}
    one = {"cf-connecting-ip": "203.0.113.1"}
    assert [c.post("/api/signin", json=body, headers=one).status_code for _ in range(4)][-1] == 429
    assert c.post("/api/signup", json={**body, "signup_code": "GOOD", "consent": True}, headers=one).status_code == 429
    assert c.post("/api/signin", json=body, headers={"cf-connecting-ip": "203.0.113.2"}).status_code != 429


def test_prompt_events_need_a_real_prompt_and_have_a_daily_limit(fake, monkeypatch):  # noqa: F811
    c = TestClient(server.app)
    event = {"headers": {"Authorization": "Bearer user-token"}, "json": {"prompt_id": "des-t-01", "event": "skipped"}}
    assert c.post("/api/prompt-event", **event).status_code == 200
    assert len(fake.inserted) == 1
    fake.prompts = []  # a prompt id this user cannot be served
    assert c.post("/api/prompt-event", **event).status_code == 400
    fake.prompts = [PROMPT]
    monkeypatch.setattr(server, "MAX_EVENTS_PER_DAY", 0)
    assert c.post("/api/prompt-event", **event).status_code == 429
    assert len(fake.inserted) == 1


def test_demo_upload_without_a_valid_code_is_refused(monkeypatch):
    monkeypatch.setattr(server, "gate", Gate(codes={"DEMO"}, on_server=True))

    async def must_not_run(audio, content_type):
        raise AssertionError("the speech service was called")
    monkeypatch.setattr(server, "send_to_nyra", must_not_run)
    r = TestClient(server.app).post("/transcribe", content=b"audio", headers={"X-Access-Code": "WRONG"})
    assert r.status_code == 403


def test_the_speech_services_own_error_text_is_not_shown_to_the_user(monkeypatch):
    monkeypatch.setenv("NYRA_API_KEY", "test-key")
    real = httpx.AsyncClient
    transport = httpx.MockTransport(lambda request: httpx.Response(402, text="account 123 has no balance"))
    monkeypatch.setattr(server.httpx, "AsyncClient", lambda **kw: real(transport=transport))
    try:
        asyncio.run(server.send_to_nyra(b"audio", "audio/webm"))
        raise AssertionError("expected an error")
    except server.HTTPException as e:
        assert e.status_code == 502
        assert "balance" not in e.detail and "123" not in e.detail


def test_the_analytics_relay_only_passes_posthog_addresses_the_page_uses():
    for path in ("e/", "i/v0/e/", "s/", "flags/", "static/array.js", "array/phc_x/config.js", "decide"):
        assert allowed(path)
    for path in ("", "api/projects/", "api/event", "login", "../e/", "e/../api/projects/", "static/./../api"):
        assert not allowed(path)
    assert TestClient(server.app).get("/ingest/api/projects/").status_code == 404
