"""Builds index.html: review page for candidate single-scene images.

Run from the repo root:  python3 design/stimuli/make_page.py
Images load from candidates/ (local only, not committed). Style: browser-app style.
"""

import csv
import html
import os
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).parent
e = html.escape

# pi's notes from looking at each image (2026-11-21). Duncan decides.
NOTES = {
    "cand-08": "Round painting; would show with white corners.",
    "cand-13": "A later colourised engraving after Frith, not the painting. Station signs may carry text.",
    "cand-14": "Very wide; small figures on a phone.",
    "cand-21": "Wrong work: Degas's sketchier 'Cotton Merchants', not 'A Cotton Office'. Few actions.",
    "cand-24": "Only four people; one action.",
    "cand-26": "Few actions; mostly men sitting.",
    "cand-31": "Few people; quiet scene.",
    "cand-32": "Includes a nude child. Likely cut.",
    "cand-34": "Few people; quiet scene.",
    "cand-35": "Cropped detail; figures are blurred dabs.",
    "cand-37": "Signature visible bottom left; small text on posters.",
    "cand-20": "Two men shirtless at work.",
}


def main():
    rows = list(csv.DictReader((HERE / "candidates.csv").open()))
    flagged = sum(r["candidate_id"] in NOTES for r in rows)
    out = [
        '<!doctype html><html lang="en"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        "<title>SoundSmarter image candidates</title><style>", (HERE / "app.css").read_text(),
        "img{max-width:100%;border:1px solid #000;display:block;margin:.3em 0}</style></head><body class=\"narrow\">",
        f'<div class="strip"><b>{datetime.now():%a %-d %b, %H:%M}</b><b>Candidates {len(rows)}</b>'
        f"<b>Flagged {flagged}</b><b>Needed 30</b></div>",
        '<p class="small">Single scenes. Each approved image serves three prompts: Describe, Invent before, Invent after. '
        'Tell pi in chat which to keep, e.g. "keep all except cand-21, cand-32".</p>',
        '<section class="box"><h2>Candidates</h2><ul class="rows">',
    ]
    for r in rows:
        note = NOTES.get(r["candidate_id"])
        out.append(
            f'<li><a href="{e(r["source_url"])}" target="_blank" rel="noopener noreferrer">{e(r["title"])}</a> — '
            f'{e(r["artist"])} — <span class="why">{e(r["date"] or "date unknown")}</span> '
            f'<span class="mk">{e(r["candidate_id"])}</span>'
            + (f'<span class="mk bad">CHECK</span>' if note else "")
            + f'<img src="candidates/{e(r["file"])}" alt="{e(r["title"])}" loading="lazy">'
            + (f'<div class="nxt c-bad">{e(note)}</div>' if note else "")
            + f'<div class="nxt small">Credit: {e(r["credit"])} Full size {e(r["full_width"])}×{e(r["full_height"])} px.</div></li>'
        )
    out.append(f'</ul></section><p class="small">{len(rows)} candidates · from Wikimedia Commons (public domain) via '
               "fetch_candidates.py · rebuilt when pi re-runs make_page.py</p></body></html>")
    tmp = HERE / "index.html.tmp"
    tmp.write_text("\n".join(out))
    os.replace(tmp, HERE / "index.html")


if __name__ == "__main__":
    main()
