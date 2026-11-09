"""SoundSmarter Build 1 prototype server.

Serves the page, receives a recording from the browser, sends it to Deepgram,
and returns the filler count. The Deepgram key stays here, never in the browser.

Run from prototype/:  uv run uvicorn server:app --reload
"""

import os
from pathlib import Path

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse

from fillers import count_fillers

HERE = Path(__file__).parent
load_dotenv(HERE.parent / ".env")  # repo-root .env

DEEPGRAM_URL = "https://api.deepgram.com/v1/listen"
DEEPGRAM_PARAMS = {"model": "nova-2", "language": "en", "filler_words": "true"}

app = FastAPI()


@app.get("/")
def index():
    return FileResponse(HERE / "index.html")


@app.post("/transcribe")
async def transcribe(request: Request):
    key = os.getenv("DEEPGRAM_API_KEY")
    if not key:
        raise HTTPException(500, "DEEPGRAM_API_KEY is not set in .env")

    audio = await request.body()
    if not audio:
        raise HTTPException(400, "No audio received")

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
    if resp.status_code != 200:
        raise HTTPException(502, f"Deepgram error {resp.status_code}: {resp.text[:300]}")

    data = resp.json()
    alt = data["results"]["channels"][0]["alternatives"][0]
    return {**count_fillers(data), "transcript": alt.get("transcript", "")}
