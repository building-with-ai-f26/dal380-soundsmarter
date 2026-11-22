"""Builds index.html: a read-only review page for the draft prompt bank.

Reads the two CSVs in design/ and writes index.html next to this file.
Run from the repo root:  python3 design/prompt-review/make_page.py
Re-run after any CSV change. Style: Duncan's browser-app style (app.css, copied).
"""

import csv
import html
import os
from collections import Counter
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).parent
DESIGN = HERE.parent
TEXT_CSV = DESIGN / "2026-11-21-prompts-text-draft.csv"
AUDIO_CSV = DESIGN / "2026-11-21-audio-stimuli-draft.csv"
FAMILIES = ["describe", "narrate", "argue", "invent", "explain"]
HEADERS = {"argue": "Give at least two reasons."}  # shown above the prompt in the app; keep in step with FAMILY_HEADERS in prototype/index.html
e = html.escape


def status_mark(s):
    return '<span class="mk hi">APPROVED</span>' if s == "approved" else f'<span class="mk">{e(s.upper())}</span>'


def main():
    all_rows = list(csv.DictReader(TEXT_CSV.open()))
    rows = [r for r in all_rows if r["status"] != "retired"]  # retired rows stay in the CSV, off the page
    retired = len(all_rows) - len(rows)
    audio = list(csv.DictReader(AUDIO_CSV.open()))
    status = Counter(r["status"] for r in rows)
    long = [r for r in rows if int(r["words_on_screen"] or 0) > 30]

    out = [
        '<!doctype html><html lang="en"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        "<title>SoundSmarter prompt review</title><style>", (HERE / "app.css").read_text(),
        "</style></head><body class=\"narrow\">",
        f'<div class="strip"><b>{datetime.now():%a %-d %b, %H:%M}</b><b>Text prompts {len(rows)}</b>'
        f'<b>Approved {status.get("approved", 0)}</b><b>Draft {status.get("draft", 0)}</b>'
        f'<b>Retired (hidden) {retired}</b><b>Audio scripts {len(audio)}</b>'
        + (f'<div class="c-bad">Over 30 words on screen: {", ".join(e(r["id"]) for r in long)}</div>' if long else "")
        + "</div>",
        '<p class="small">To approve or cut, tell pi in chat: for example "approve all describe except des-t-18, des-t-36" '
        "or \"cut arg-t-45\". Pi changes the CSV and rebuilds this page. Nothing is served until it is approved.</p>",
    ]

    for fam in FAMILIES:
        fam_rows = [r for r in rows if r["family"] == fam]
        for variant in dict.fromkeys(r["variant"] for r in fam_rows):
            vr = [r for r in fam_rows if r["variant"] == variant]
            first = vr[0]
            out.append(
                f'<section class="box"><h2>{e(fam)} / text / {e(variant)}</h2>'
                f'<p class="small">{len(vr)} prompts — {e(first["openness"])}'
                + (f' — header in the app: <b>{e(HEADERS[fam])}</b>' if fam in HEADERS else "")
                + '</p><ul class="rows">'
            )
            for r in vr:
                out.append(
                    f'<li>{e(r["text"])} — <span class="why">{e(r["words_on_screen"])} words</span> '
                    f'<span class="mk">{e(r["id"])}</span>{status_mark(r["status"])}</li>'
                )
            out.append("</ul></section>")

    out.append('<section class="box"><h2>Audio scripts (later build)</h2><ul class="rows">')
    for a in audio:
        cut = (f'<div class="nxt"><span class="why">Cut version ({e(a["words_cut"])} words, ~{e(a["est_seconds_cut"])} s):</span> '
               f'{e(a["script_cut"])}</div>') if a.get("script_cut") else ""
        out.append(
            f'<li>{e(a["script_full"])} — <span class="why">{e(a["kind"])}, {e(a["words_full"])} words, '
            f'~{e(a["est_seconds_full"])} s</span> <span class="mk">{e(a["stimulus_id"])}</span>'
            f'{status_mark(a["status"])}{cut}</li>'
        )
    out.append("</ul></section>")

    out.append(f'<p class="small">{len(rows)} text prompts, {len(audio)} audio scripts · from {TEXT_CSV.name} and '
               f"{AUDIO_CSV.name} · rebuilt when pi re-runs make_page.py</p></body></html>")

    tmp = HERE / "index.html.tmp"
    tmp.write_text("\n".join(out))
    os.replace(tmp, HERE / "index.html")


if __name__ == "__main__":
    main()
