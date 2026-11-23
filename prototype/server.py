"""SoundSmarter server.

Serves the page, receives a recording from the browser, sends it to
CrisperWhisper (Nyra's hosted API), and returns the metrics. The API key
stays here, never in the browser.

Two kinds of visitor:
  - demo-code visitors: instant results, nothing saved; access.py limits them
  - signed-in users (Build 3): accounts and stored records on Supabase
    (supa.py); prompt and session rules in records.py

Run from prototype/:  uv run uvicorn server:app --reload
"""

import asyncio
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

import records
import wordlist
from access import AccessDenied, Gate
from analytics_proxy import router as analytics_router
from fillers import count_fillers
from metrics import compute
from supa import Supa, SupaError

HERE = Path(__file__).parent
load_dotenv(HERE.parent / ".env")  # repo-root .env (local only; online, the host sets these)

# CrisperWhisper 2 keeps fillers, repeats and cut-offs (test C: caught 18/18
# hand-counted fillers vs. Deepgram Nova-2's 13). $0.90 per audio hour.
NYRA_URL = "https://api.nyra-labs.com/v1/audio/transcriptions"
# No "language" field: the service detects the language itself, and a recording
# it hears as non-English is rejected for signed-in users (decision 25).
NYRA_FIELDS = {"model": "crisperwhisper-v2"}
STT_MODEL = NYRA_FIELDS["model"]
MAX_AUDIO_BYTES = 2_000_000  # a 60 s recording is ~1 MB; refuse anything much bigger
MAX_BODY_BYTES = 5_000_000   # no request to any route needs more (same limit as the analytics relay)
log = logging.getLogger("uvicorn.error")

CONSENT_VERSION = "2026-11-21"  # bump when the consent wording on the sign-up page changes
# Bump when a metric definition changes. 1 = fillers, rate and prep time only. 2 = the full set.
# 3 = sentence ends read from the tidied text too; filled share counts every silent pause.
METRICS_VERSION = 3
WORD_LIST_VERSION = wordlist.VERSION  # bump (in wordlist.py) when the counted word list changes

# No auto-generated API pages (/docs, /redoc, /openapi.json): they list every route to anyone.
app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
app.include_router(analytics_router)  # /ingest/... -> PostHog (gets past ad blockers)
gate = Gate.from_env()
supa = Supa.from_env()
# One transcription at a time per account: a second recording sent meanwhile waits its
# turn, so a burst of simultaneous sends can't all pass the daily-cap check before any
# is counted. Kept in memory, which is enough while there is one server process.
user_locks: dict[str, asyncio.Lock] = {}

# Per-visitor limit on failed attempts to create an account or sign in, so one visitor
# can't guess passwords or sign-up codes at speed. Only failures count, and the number
# is generous, because a classroom of testers can share one network address.
AUTH_LIMIT, AUTH_WINDOW_S = 30, 600  # failed attempts per visitor address, per 10 minutes
auth_attempts: dict[str, list[float]] = {}
MAX_EVENTS_PER_DAY = 500  # prompt events per account; ordinary use is a few dozen


def visitor_address(request: Request) -> str:
    """The visitor's network address, as the host reports it.

    Not confirmed on Render: if the host does not set or overwrite these headers,
    a visitor can fake them and get round the limit (SECURITY.md, Remaining issues).
    """
    forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    return (request.headers.get("cf-connecting-ip") or forwarded
            or (request.client.host if request.client else "unknown"))


async def limited_auth(request: Request, coro):
    """Run a sign-up or sign-in, unless this visitor has failed AUTH_LIMIT times in AUTH_WINDOW_S."""
    who, now = visitor_address(request), time.monotonic()
    recent = [t for t in auth_attempts.get(who, []) if now - t < AUTH_WINDOW_S]
    if len(recent) >= AUTH_LIMIT:
        coro.close()
        raise HTTPException(429, "Too many failed sign-in attempts from this network. Try again in a few minutes.")
    try:
        return await supa_call(coro)
    except HTTPException:
        if len(auth_attempts) > 10_000:  # never let the list of addresses grow without end
            auth_attempts.clear()
        auth_attempts[who] = recent + [now]
        raise


@app.middleware("http")
async def refuse_huge_bodies(request: Request, call_next):
    """Turn away a request that says it is bigger than anything this app accepts, before reading it."""
    try:
        too_big = int(request.headers.get("content-length") or 0) > MAX_BODY_BYTES
    except ValueError:
        too_big = True
    if too_big:
        return JSONResponse({"detail": "Request too large"}, status_code=413)
    return await call_next(request)


@app.get("/")
def index():
    # no-cache: browsers re-check for a new version instead of showing an old copy
    return FileResponse(HERE / "index.html", headers={"Cache-Control": "no-cache"})


@app.get("/access")
def access(request: Request):
    """Lets the page check the invite code before the user records anything."""
    try:
        return {"takes_left": gate.takes_left(request.headers.get("x-access-code"))}
    except AccessDenied as e:
        raise HTTPException(e.status, e.message)


async def read_capped(request: Request) -> bytes:
    if int(request.headers.get("content-length") or 0) > MAX_AUDIO_BYTES:
        raise HTTPException(413, "Recording too large")
    body = b""
    async for chunk in request.stream():
        body += chunk
        if len(body) > MAX_AUDIO_BYTES:
            raise HTTPException(413, "Recording too large")
    return body


async def send_to_nyra(audio: bytes, content_type: str) -> dict:
    """Transcribe one recording. Raises HTTPException(502) if the service fails."""
    key = os.getenv("NYRA_API_KEY")
    if not key:
        raise HTTPException(500, "NYRA_API_KEY is not set in .env")
    try:
        # Sent as a file upload (multipart). Nyra reads the format from the bytes,
        # so Chrome's webm and Safari's mp4 both work without converting.
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                NYRA_URL,
                headers={"Authorization": f"Bearer {key}"},
                data=NYRA_FIELDS,
                files={"file": ("recording", audio, content_type)},
            )
    except httpx.HTTPError:
        raise HTTPException(502, "Could not reach the speech service")
    if resp.status_code != 200:
        # The service's own words stay in the server log; they could name the account or its balance.
        log.warning("Speech service error %s: %s", resp.status_code, resp.text[:300])
        raise HTTPException(502, "The speech service could not analyse that recording.")
    return resp.json()


def results(data: dict) -> dict:
    """What the results page shows: filler counts, rate, prep time, transcript tokens."""
    return {
        **count_fillers(data),
        **compute(data),  # word count, fillers per 100 words, prep time, pauses
        "transcript": (data.get("verbatim") or {}).get("text", ""),
    }


@app.post("/transcribe")
async def transcribe(request: Request):
    if request.headers.get("authorization"):
        return await transcribe_signed_in(request)

    # Demo-code visitors: instant results, nothing saved.
    try:
        gate.takes_left(request.headers.get("x-access-code"))  # no valid code, no upload
    except AccessDenied as e:
        raise HTTPException(e.status, e.message)
    audio = await read_capped(request)
    if not audio:
        raise HTTPException(400, "No audio received")
    try:
        token = gate.reserve(request.headers.get("x-access-code"))
    except AccessDenied as e:
        raise HTTPException(e.status, e.message)
    try:
        data = await send_to_nyra(audio, request.headers.get("content-type", "audio/webm"))
    except HTTPException:
        gate.refund(token)
        raise
    return results(data)


# ======================= signed-in users (Build 3) =======================

def bearer(request: Request) -> str:
    auth = request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        raise HTTPException(401, "Signed out. Please sign in again.")
    return auth[7:]


async def supa_call(coro):
    """Turn account-service errors into HTTP errors the page can show."""
    try:
        return await coro
    except SupaError as e:
        raise HTTPException(e.status, e.message)


class SignUp(BaseModel):
    email: str
    password: str
    signup_code: str
    consent: bool


class SignIn(BaseModel):
    email: str
    password: str


class Refresh(BaseModel):
    refresh_token: str


class PromptEvent(BaseModel):
    prompt_id: str
    event: str  # "skipped", "discarded", or "served" (the page confirming an image prompt's pictures loaded)


@app.post("/api/signup")
async def signup(request: Request, body: SignUp):
    if not body.consent:  # no consent, no account (the database checks this too)
        raise HTTPException(400, "Consent is required to create an account.")
    if not body.signup_code.strip():
        raise HTTPException(400, "A sign-up code is required.")
    return await limited_auth(request, supa.sign_up(
        body.email.strip(), body.password, body.signup_code.strip(), CONSENT_VERSION))


@app.post("/api/signin")
async def signin(request: Request, body: SignIn):
    return await limited_auth(request, supa.sign_in(body.email.strip(), body.password))


@app.post("/api/refresh")
async def refresh(body: Refresh):
    return await supa_call(supa.refresh(body.refresh_token))


async def today_count(token: str) -> int:
    rows = await supa.select(token, "prompt_events", {
        "select": "id", "event": f"in.({','.join(records.COUNTS_TOWARD_CAP)})",
        "created_at": f"gte.{records.day_start_utc()}",
    })
    return len(rows)


@app.get("/api/me")
async def me(request: Request):
    token = bearer(request)
    user = await supa_call(supa.user(token))
    recs = await supa_call(supa.select(token, "recordings", {"select": "id"}))
    used = await supa_call(today_count(token))
    return {
        "email": user.get("email", ""),
        "recordings": len(recs),
        "baseline_size": records.BASELINE_SIZE,
        "today": used,
        "daily_cap": records.DAILY_CAP,
    }


async def stimulus_for(token: str, prompt: dict) -> dict | None:
    """The images an image prompt shows, or None if any file is missing from the bucket.

    A pair's title holds the two item names ("Cat | Dog"), shown under the images.
    """
    found = await supa.select(token, "stimuli", {"select": "id,kind,files,title,credit", "id": f"eq.{prompt['stimulus_id']}"})
    if not found or not found[0]["files"]:
        return None
    stim = found[0]
    for path in stim["files"]:
        if not await supa.file_exists(path):
            return None
    labels = [s.strip() for s in (stim.get("title") or "").split("|")] if stim["kind"] == "pair" else []
    return {
        "images": [{"url": supa.file_url(path), "label": labels[i] if i < len(labels) else ""}
                   for i, path in enumerate(stim["files"])],
        "credit": stim.get("credit") or "",
    }


@app.get("/api/prompt")
async def next_prompt(request: Request, family: str | None = None):
    """Serve the next prompt and record that it was seen."""
    token = bearer(request)
    user = await supa_call(supa.user(token))
    prompts = await supa_call(supa.select(token, "prompts", {"select": "id,family,mode,variant,text,stimulus_id"}))
    events = await supa_call(supa.select(token, "prompt_events", {"select": "prompt_id,event"}))
    recs = await supa_call(supa.select(token, "recordings", {"select": "family,mode", "order": "created_at.asc"}))
    # A prompt whose stimulus file is missing is never served (decision 22): drop it and choose again.
    while True:
        prompt = records.choose_prompt(prompts, events, recs, family=family)
        if prompt is None or not prompt.get("stimulus_id"):
            break
        stimulus = await supa_call(stimulus_for(token, prompt))
        if stimulus:
            prompt = {**prompt, **stimulus}
            break
        prompts = [p for p in prompts if p["id"] != prompt["id"]]
    if prompt is None:
        raise HTTPException(404, "No new prompts left. More are coming.")
    if prompt.get("images"):
        # An image prompt counts as seen only once its pictures have loaded in the browser;
        # the page then reports "served". If a picture fails to load, the prompt is not used up.
        return {**prompt, "confirm_served": True}
    await supa_call(supa.insert_as_server("prompt_events", {
        "user_id": user["id"], "prompt_id": prompt["id"], "event": "served"}))
    return prompt


@app.post("/api/prompt-event")
async def prompt_event(request: Request, body: PromptEvent):
    """Record a skip (during recording), a discard (after stopping), or an image prompt's pictures having loaded."""
    if body.event not in records.SKIP_EVENTS + ("served",):
        raise HTTPException(400, "Unknown event")
    token = bearer(request)
    user = await supa_call(supa.user(token))
    # Only for an approved prompt, and not without end: a script can't fill the table.
    if not await supa_call(supa.select(token, "prompts", {"select": "id", "id": f"eq.{body.prompt_id}"})):
        raise HTTPException(400, "Unknown prompt")
    today = await supa_call(supa.select(token, "prompt_events", {
        "select": "id", "created_at": f"gte.{records.day_start_utc()}"}))
    if len(today) >= MAX_EVENTS_PER_DAY:
        raise HTTPException(429, "That's enough prompts for today. More tomorrow.")
    await supa_call(supa.insert_as_server("prompt_events", {
        "user_id": user["id"], "prompt_id": body.prompt_id, "event": body.event}))
    return {"ok": True}


@app.get("/api/recordings")
async def my_recordings(request: Request):
    """The account page's list. Metrics are left out until baseline is complete."""
    token = bearer(request)
    recs = await supa_call(supa.select(token, "recordings", {
        "select": "id,created_at,prompt_id,family,mode,metrics", "order": "created_at.desc"}))
    prompts = await supa_call(supa.select(token, "prompts", {"select": "id,text,stimulus_id"}))
    stimuli = await supa_call(supa.select(token, "stimuli", {"select": "id,title"}))
    title = {s["id"]: s["title"] for s in stimuli}
    # An image prompt has no text of its own: list it by its picture's title instead.
    text = {p["id"]: p["text"] or f"Image: {title.get(p.get('stimulus_id')) or 'picture'}" for p in prompts}
    show_numbers = len(recs) >= records.BASELINE_SIZE
    return [{
        "created_at": r["created_at"], "family": r["family"], "mode": r["mode"],
        "prompt": text.get(r["prompt_id"], ""),
        "metrics": r["metrics"] if show_numbers else None,
    } for r in recs]


@app.get("/api/baseline")
async def my_baseline(request: Request):
    """The Account page table: baseline and average since, by family and mode. Empty until the 10th recording."""
    token = bearer(request)
    recs = await supa_call(supa.select(token, "recordings", {
        "select": "family,mode,metrics", "order": "created_at.asc"}))
    return {"rows": records.baseline_table(recs)}


async def transcribe_signed_in(request: Request):
    token = bearer(request)
    user = await supa_call(supa.user(token))  # rejects a bad or expired token before any cost
    async with user_locks.setdefault(user["id"], asyncio.Lock()):
        return await transcribe_and_store(request, token, user)


async def transcribe_and_store(request: Request, token: str, user: dict):
    await supa_call(supa.check_can_write())  # a missing or broken key stops here, before Nyra is paid
    # Nothing is stored without consent (decision 14). Sign-up always writes a
    # consent row; this check replaces the database rule removed in migration 002.
    if not await supa_call(supa.select(token, "consents", {"select": "id", "limit": "1"})):
        raise HTTPException(403, "Consent is required before a recording can be saved.")
    prompt_id = request.headers.get("x-prompt-id", "")
    found = await supa_call(supa.select(token, "prompts", {"select": "*", "id": f"eq.{prompt_id}"}))
    if not found:
        raise HTTPException(400, "Unknown prompt")
    prompt = found[0]
    if await supa_call(today_count(token)) >= records.DAILY_CAP:
        raise HTTPException(429, f"That's today's {records.DAILY_CAP} recordings. More tomorrow.")

    audio = await read_capped(request)
    if not audio:
        raise HTTPException(400, "No audio received")
    data = await send_to_nyra(audio, request.headers.get("content-type", "audio/webm"))

    # Unusable audio (decision 21): no row, no numbers, a re-record message. It
    # cost a transcription, so the 'rejected' event counts toward the daily cap.
    reason = records.unusable_reason(data)
    if reason:
        await supa_call(supa.insert_as_server("prompt_events", {
            "user_id": user["id"], "prompt_id": prompt["id"], "event": "rejected"}))
        return {"rejected": True, "reason": reason, "message": records.UNUSABLE_MESSAGES[reason]}
    shown = results(data)

    now = datetime.now(timezone.utc)
    last = await supa_call(supa.select(token, "recordings", {
        "select": "created_at,session_no,position_in_session", "order": "created_at.desc", "limit": "1"}))
    events = await supa_call(supa.select(token, "prompt_events", {
        "select": "prompt_id,event,created_at", "order": "created_at.desc", "limit": "100"}))
    session_no, position = records.session_slot(last[0] if last else None, now)

    # Written by the server, never by the browser, so every stored row is one we measured.
    await supa_call(supa.insert_as_server("prompt_events", {
        "user_id": user["id"], "prompt_id": prompt["id"], "event": "sent"}))
    await supa_call(supa.insert_as_server("recordings", {
        "user_id": user["id"], "prompt_id": prompt["id"], "family": prompt["family"], "mode": prompt["mode"],
        "variant": prompt["variant"], "stimulus_id": prompt.get("stimulus_id"),
        "session_no": session_no, "position_in_session": position,
        "skipped_before": records.skipped_before(events),
        "prep_from": "clip_end" if prompt["mode"] == "audio" else "reveal",
        "metrics": {k: v for k, v in shown.items() if k not in ("tokens", "transcript")},
        "metrics_version": METRICS_VERSION, "word_list_version": WORD_LIST_VERSION,
        "transcription": data, "stt_model": STT_MODEL, "language": data.get("language"),
    }))
    recs = await supa_call(supa.select(token, "recordings", {
        "select": "family,mode,metrics", "order": "created_at.asc"}))
    return {**shown, "saved": True, "recordings": len(recs), "baseline_size": records.BASELINE_SIZE,
            # from the 11th recording on: the user's own baseline for this family and mode
            "baseline": records.baseline_for(recs, prompt["family"], prompt["mode"])}
