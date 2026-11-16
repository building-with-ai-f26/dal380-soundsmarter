"""SoundSmarter Build 1 prototype server.

Serves the page, receives a recording from the browser, sends it to
CrisperWhisper (Nyra's hosted API), and returns the filler count. The API key
stays here, never in the browser.
When shared online, access.py limits who can use it and how often.

Run from prototype/:  uv run uvicorn server:app --reload
"""

import os
from pathlib import Path

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse

from access import AccessDenied, Gate
from analytics_proxy import router as analytics_router
from fillers import count_fillers
from metrics import compute

HERE = Path(__file__).parent
load_dotenv(HERE.parent / ".env")  # repo-root .env (local only; online, the host sets these)

# CrisperWhisper 2 keeps fillers, repeats and cut-offs (test C: caught 18/18
# hand-counted fillers vs. Deepgram Nova-2's 13). $0.90 per audio hour.
NYRA_URL = "https://api.nyra-labs.com/v1/audio/transcriptions"
NYRA_FIELDS = {"model": "crisperwhisper-v2", "language": "en"}
MAX_AUDIO_BYTES = 2_000_000  # a 60 s take is ~1 MB; refuse anything much bigger

app = FastAPI()
app.include_router(analytics_router)  # /ingest/... -> PostHog (gets past ad blockers)
gate = Gate.from_env()


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


@app.post("/transcribe")
async def transcribe(request: Request):
    key = os.getenv("NYRA_API_KEY")
    if not key:
        raise HTTPException(500, "NYRA_API_KEY is not set in .env")

    audio = await read_capped(request)
    if not audio:
        raise HTTPException(400, "No audio received")

    try:
        token = gate.reserve(request.headers.get("x-access-code"))
    except AccessDenied as e:
        raise HTTPException(e.status, e.message)

    try:
        # Sent as a file upload (multipart). Nyra reads the format from the bytes,
        # so Chrome's webm and Safari's mp4 both work without converting.
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                NYRA_URL,
                headers={"Authorization": f"Bearer {key}"},
                data=NYRA_FIELDS,
                files={"file": ("take", audio, request.headers.get("content-type", "audio/webm"))},
            )
    except httpx.HTTPError:
        gate.refund(token)
        raise HTTPException(502, "Could not reach the speech service")
    if resp.status_code != 200:
        gate.refund(token)
        raise HTTPException(502, f"Speech service error {resp.status_code}: {resp.text[:300]}")

    data = resp.json()
    return {
        **count_fillers(data),
        **compute(data),  # word count, fillers per 100 words, prep time, pauses
        "transcript": (data.get("verbatim") or {}).get("text", ""),
    }
