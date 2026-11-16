"""Test C: send the same saved recordings to each speech-to-text service and
compare their um/uh counts against Duncan's hand count.

No microphone, no browser: this isolates the model (HANDOFF, A/B/C protocol).

Setup (from this folder):
  1. Put recordings in recordings/  (any format ffmpeg reads: .m4a, .wav, ...)
  2. Fill in hand_counts.csv: one row per file with your own um/uh count
  3. uv run python compare.py            # all services
     uv run python compare.py crisper    # just one (deepgram | crisper | elevenlabs)

Keys come from the repo-root .env (DEEPGRAM_API_KEY, NYRA_API_KEY, ELEVENLABS_API_KEY).
A service whose key is missing is skipped. Raw responses are saved to
results/<service>/<file>.json so counts can be rechecked without paying again.
"""

import csv
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import httpx
from dotenv import load_dotenv

HERE = Path(__file__).parent
REPO = HERE.parent.parent
load_dotenv(REPO / ".env")

RECORDINGS = HERE / "recordings"
RESULTS = HERE / "results"
HAND_COUNTS = HERE / "hand_counts.csv"
AUDIO_TYPES = {".m4a", ".wav", ".mp3", ".webm", ".ogg", ".flac", ".aac", ".mp4"}

# um/uh and their stretched spellings (umm, uhhh), with or without [brackets].
UM = re.compile(r"^u+m+$")
UH = re.compile(r"^u+h+$")


def to_wav(src: Path) -> Path:
    """Convert to 16 kHz mono WAV, the format speech models expect."""
    out = Path(tempfile.gettempdir()) / f"sttc_{src.stem}.wav"
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-ar", "16000", "-ac", "1", str(out)],
        check=True,
    )
    return out


def classify(token: str) -> str | None:
    t = re.sub(r"[^a-z]", "", token.lower())
    if UM.match(t):
        return "um"
    if UH.match(t):
        return "uh"
    return None


# --- one function per service: audio file in, list of (word, start_seconds) out ---

def run_deepgram(wav: Path) -> tuple[list, dict]:
    key = os.environ["DEEPGRAM_API_KEY"]
    resp = httpx.post(
        "https://api.deepgram.com/v1/listen",
        params={"model": "nova-2", "language": "en", "filler_words": "true"},
        headers={"Authorization": f"Token {key}", "Content-Type": "audio/wav"},
        content=wav.read_bytes(),
        timeout=120,
    )
    resp.raise_for_status()
    raw = resp.json()
    words = raw["results"]["channels"][0]["alternatives"][0]["words"]
    return [(w["word"], w["start"]) for w in words], raw


def run_elevenlabs(wav: Path) -> tuple[list, dict]:
    key = os.environ["ELEVENLABS_API_KEY"]
    with wav.open("rb") as f:
        resp = httpx.post(
            "https://api.elevenlabs.io/v1/speech-to-text",
            headers={"xi-api-key": key},
            data={
                "model_id": "scribe_v3",
                "language_code": "en",
                "no_verbatim": "false",  # keep fillers and false starts
                "tag_audio_events": "true",
                "timestamps_granularity": "word",
            },
            files={"file": (wav.name, f, "audio/wav")},
            timeout=180,
        )
    resp.raise_for_status()
    raw = resp.json()
    words = [w for w in raw.get("words", []) if w.get("type") == "word"]
    return [(w["text"], w.get("start", 0.0)) for w in words], raw


def run_crisper(wav: Path) -> tuple[list, dict]:
    """CrisperWhisper 2 via Nyra's hosted API ($0.90 per audio hour).
    Returns the verbatim track, which keeps fillers, repeats and cut-offs."""
    key = os.environ["NYRA_API_KEY"]
    with wav.open("rb") as f:
        resp = httpx.post(
            "https://api.nyra-labs.com/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {key}"},
            data={"model": "crisperwhisper-v2", "language": "en"},
            files={"file": (wav.name, f, "audio/wav")},
            timeout=180,
        )
    resp.raise_for_status()
    if resp.headers.get("x-nyra-test-mode") == "true":
        print("  crisper: WARNING test key, dummy transcript (use an nl_live_ key)")
    raw = resp.json()
    words = raw["verbatim"]["words"]
    return [(w["word"], w["start"]) for w in words], raw


SERVICES = {
    "deepgram": ("DEEPGRAM_API_KEY", run_deepgram),
    "crisper": ("NYRA_API_KEY", run_crisper),
    "elevenlabs": ("ELEVENLABS_API_KEY", run_elevenlabs),
}


def test_number(name: str) -> str | None:
    """'Test 3' and '11.15.26 ss test 3.m4a' both -> '3', so rows match files."""
    m = re.search(r"test\s*(\d+)", name, re.I)
    return m.group(1) if m else None


def load_hand_counts() -> dict:
    """Keyed by test number. Tolerant of free-text columns: a row 'starts with
    filler' anywhere in its text counts as opening with a filler."""
    if not HAND_COUNTS.exists():
        return {}
    out = {}
    with HAND_COUNTS.open() as f:
        next(f)  # header
        for line in f:
            cells = [c.strip() for c in line.split(",")]
            if len(cells) < 3 or not test_number(cells[0]):
                continue
            out[test_number(cells[0])] = {
                "um": cells[1], "uh": cells[2],
                "starts_with_filler": "yes" if "starts with filler" in line.lower() else "no",
                "notes": ", ".join(cells[3:]),
            }
    return out


def main():
    wanted = sys.argv[1:] or list(SERVICES)
    files = sorted(p for p in RECORDINGS.glob("*") if p.suffix.lower() in AUDIO_TYPES)
    if not files:
        sys.exit(f"No recordings in {RECORDINGS}")
    hand = load_hand_counts()

    rows = []
    for src in files:
        print(f"{src.name}")
        wav = to_wav(src)
        for name in wanted:
            env_key, fn = SERVICES[name]
            if env_key and not os.getenv(env_key):
                print(f"  {name}: skipped ({env_key} not set)")
                continue
            words, raw = fn(wav)
            out = RESULTS / name / f"{src.stem}.json"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(raw, indent=2))

            kinds = [classify(w) for w, _ in words]
            um, uh = kinds.count("um"), kinds.count("uh")
            leading = bool(kinds) and kinds[0] is not None
            first_word_s = words[0][1] if words else None
            # CrisperWhisper also labels each token; count what it calls a filler
            labelled = None
            if name == "crisper" and raw.get("alignment"):
                labelled = sum(1 for a in raw["alignment"] if a["type"] == "filler")
            rows.append((src.name, name, um, uh, leading, first_word_s, labelled))
            extra = f", labelled filler: {labelled}" if labelled is not None else ""
            print(f"  {name}: um {um}, uh {uh}, opens with filler: {leading}{extra}")

    # Summary table (markdown, so it can be pasted into the build log)
    print("\n| File | Service | um | uh | Total | Hand total | Opens with filler (hand) | First word (s) |")
    print("|---|---|---|---|---|---|---|---|")
    for fname, svc, um, uh, leading, first, _ in rows:
        h = hand.get(test_number(fname), {})
        hand_total = (int(h["um"]) + int(h["uh"])) if h.get("um") else "?"
        hand_lead = h.get("starts_with_filler", "?")
        first_s = f"{first:.2f}" if first is not None else "-"
        print(f"| {fname} | {svc} | {um} | {uh} | {um + uh} | {hand_total} | {'yes' if leading else 'no'} ({hand_lead}) | {first_s} |")


if __name__ == "__main__":
    main()
