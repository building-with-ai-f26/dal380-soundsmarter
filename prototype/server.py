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

import os
from datetime import datetime, timezone
from pathlib import Path

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
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

CONSENT_VERSION = "2026-11-21"  # bump when the consent wording on the sign-up page changes
METRICS_VERSION = 2             # bump when a metric definition changes. 1 = fillers, rate and prep time only
WORD_LIST_VERSION = wordlist.VERSION  # bump (in wordlist.py) when the counted word list changes

app = FastAPI()
app.include_router(analytics_router)  # /ingest/... -> PostHog (gets past ad blockers)
gate = Gate.from_env()
supa = Supa.from_env()


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
        raise HTTPException(502, f"Speech service error {resp.status_code}: {resp.text[:300]}")
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
    event: str  # "skipped" or "discarded"


@app.post("/api/signup")
async def signup(body: SignUp):
    if not body.consent:  # no consent, no account (the database checks this too)
        raise HTTPException(400, "Consent is required to create an account.")
    if not body.signup_code.strip():
        raise HTTPException(400, "A sign-up code is required.")
    return await supa_call(supa.sign_up(body.email.strip(), body.password, body.signup_code.strip(), CONSENT_VERSION))


@app.post("/api/signin")
async def signin(body: SignIn):
    return await supa_call(supa.sign_in(body.email.strip(), body.password))


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
    events = await supa_call(supa.select(token, "prompt_events", {"select": "prompt_id"}))
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
    await supa_call(supa.insert_as_server("prompt_events", {
        "user_id": user["id"], "prompt_id": prompt["id"], "event": "served"}))
    return prompt


@app.post("/api/prompt-event")
async def prompt_event(request: Request, body: PromptEvent):
    """Record a skip (during recording) or a discard (after stopping)."""
    if body.event not in records.SKIP_EVENTS:
        raise HTTPException(400, "Unknown event")
    user = await supa_call(supa.user(bearer(request)))
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
