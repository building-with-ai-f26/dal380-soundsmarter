"""Accuracy test with the app's own settings: hand counts against what the app would report.

Sends each recording to the speech service with the server's own address and settings
(read from server.py, so they can never drift from the app's) and runs the app's own
counting and metrics code on the reply. One difference from the app: each phone recording (.m4a) is first converted to WAV
with ffmpeg, as test C did, because the speech service can't decode a phone's .m4a as sent. Costs about 1 cent per recording ($0.90 per audio hour).

Run from prototype/ (it needs the app's packages and the repo-root .env):
  uv run python ../experiments/stt-compare/app_settings_test.py                       the 4 test C recordings
  uv run python ../experiments/stt-compare/app_settings_test.py hand-count/hand_counts.csv   the 15-recording set

Recordings are read from experiments/stt-compare/recordings/. Raw replies are saved in
results/app-settings/ (not committed: personal voice data). If results/crisper/ holds
test C's replies (language forced to English), their counts are shown beside the new ones.
"""

import csv
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent.parent / "prototype"))
import httpx  # noqa: E402

import server  # noqa: E402
from fillers import count_fillers  # noqa: E402
from metrics import compute  # noqa: E402

RECORDINGS, OUT, OLD = HERE / "recordings", HERE / "results" / "app-settings", HERE / "results" / "crisper"
# hand-count column -> the app's number for the same thing
COMPARE = [("um", lambda c, m: c["breakdown"]["um"]), ("uh", lambda c, m: c["breakdown"]["uh"]),
           ("mid_pauses", lambda c, m: m["mid_pauses"]), ("end_pauses", lambda c, m: m["end_pauses"]),
           ("repeats", lambda c, m: m["repetitions"]), ("cutoffs", lambda c, m: m["cutoffs"]),
           ("first_sound_s", lambda c, m: m["prep_s"])]


def to_wav(src: Path) -> Path:
    """Convert to 16 kHz mono WAV with ffmpeg, exactly as test C did (compare.py).

    The speech service can't decode a phone's .m4a as sent: the file keeps its index
    at the end. The browser's recordings don't have that problem.
    """
    out = Path(tempfile.gettempdir()) / f"sttc_{src.stem}.wav"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-ar", "16000", "-ac", "1", str(out)], check=True)
    return out


def send(f: Path) -> dict:
    wav = to_wav(f)
    resp = httpx.post(server.NYRA_URL, headers={"Authorization": f"Bearer {os.environ['NYRA_API_KEY']}"},
                      data=server.NYRA_FIELDS, files={"file": (wav.name, wav.read_bytes(), "audio/wav")}, timeout=180)
    if resp.status_code != 200:
        sys.exit(f"The speech service refused {f.name}: HTTP {resp.status_code} {resp.text[:300]}")
    return resp.json()


def number_in(name: str) -> str:
    found = re.findall(r"\d+", Path(name).stem)
    return str(int(found[-1])) if found else name


def main():
    hand_csv = HERE / (sys.argv[1] if len(sys.argv) > 1 else "hand_counts.csv")
    hand = {number_in(r["file"]): r for r in csv.DictReader(hand_csv.open(), skipinitialspace=True)}
    files = sorted(f for f in RECORDINGS.glob("*.m4a") if number_in(f.name) in hand)
    if len(sys.argv) > 1:  # a named set: only files called rec-NN
        files = [f for f in files if f.name.startswith("rec-")]
    else:
        files = [f for f in files if not f.name.startswith("rec-")]
    OUT.mkdir(parents=True, exist_ok=True)
    print(f"{len(files)} recordings, settings sent to the speech service: {server.NYRA_FIELDS}\n")
    totals = {"hand": 0, "app": 0, "old": 0}
    for f in files:
        reply = send(f)
        (OUT / (f.stem + ".json")).write_text(json.dumps(reply))
        counts, m, h = count_fillers(reply), compute(reply), hand[number_in(f.name)]
        old = OLD / (f.stem + ".json")
        old_total = count_fillers(json.loads(old.read_text()))["total"] if old.exists() else None
        print(f"{f.name}  (language heard: {reply.get('language')})")
        for col, app_value in COMPARE:
            if (h.get(col) or "").strip() == "":
                continue
            print(f"  {col:14} hand {h[col].strip():>5}   app {app_value(counts, m)}")
        hand_total = sum(int(h[c]) for c in ("um", "uh") if (h.get(c) or "").strip().isdigit())
        totals["hand"] += hand_total
        totals["app"] += counts["total"]
        totals["old"] += old_total or 0
        print(f"  um + uh        hand {hand_total:>5}   app {counts['total']}"
              + (f"   test C, English forced: {old_total}" if old_total is not None else "") + "\n")
    print(f"All recordings, um + uh: hand {totals['hand']}, app {totals['app']}"
          + (f", test C with English forced {totals['old']}" if totals["old"] else ""))


if __name__ == "__main__":
    main()
