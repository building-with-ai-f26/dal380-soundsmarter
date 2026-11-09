"""SoundSmarter Build 1 prototype server.

Serves the page, receives a recording from the browser, sends it to Deepgram,
and returns the filler count. The Deepgram key stays here, never in the browser.
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
from fillers import count_fillers

HERE = Path(__file__).parent
load_dotenv(HERE.parent / ".env")  # repo-root .env (local only; online, the host sets these)

DEEPGRAM_URL = "https://api.deepgram.com/v1/listen"
DEEPGRAM_PARAMS = {"model": "nova-2", "language": "en", "filler_words": "true"}
MAX_AUDIO_BYTES = 2_000_000  # a 60 s take is ~1 MB; refuse anything much bigger

app = FastAPI()
gate = Gate.from_env()


@app.get("/")
def index():
    return FileResponse(HERE / "index.html")


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
    key = os.getenv("DEEPGRAM_API_KEY")
    if not key:
        raise HTTPException(500, "DEEPGRAM_API_KEY is not set in .env")

    audio = await read_capped(request)
    if not audio:
        raise HTTPException(400, "No audio received")

    try:
        token = gate.reserve(request.headers.get("x-access-code"))
    except AccessDenied as e:
        raise HTTPException(e.status, e.message)

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                DEEPGRAM_URL,
                params=DEEPGRAM_PARAMS,
                headers={
                    "Authorization": f"Token {key}",
                    "Content-Type": request.headers.get("content-type", "audio/webm"),
                },
                content=audio,
            )
    except httpx.HTTPError:
        gate.refund(token)
        raise HTTPException(502, "Could not reach the speech service")
    if resp.status_code != 200:
        gate.refund(token)
        raise HTTPException(502, f"Deepgram error {resp.status_code}: {resp.text[:300]}")

    data = resp.json()
    alt = data["results"]["channels"][0]["alternatives"][0]
    return {**count_fillers(data), "transcript": alt.get("transcript", "")}
