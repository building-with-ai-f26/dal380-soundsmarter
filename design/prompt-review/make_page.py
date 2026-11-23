"""Builds index.html: a read-only review page for every Build 3 prompt, text and image.

Reads the CSVs in design/ and writes index.html next to this file. Pictures load
from design/stimuli/upload/ (local only, not committed).
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
IMAGE_CSV = DESIGN / "2026-11-22-prompts-image.csv"
STIMULI_CSV = DESIGN / "2026-11-22-stimuli-image.csv"
FAMILIES = ["describe", "narrate", "argue", "invent", "explain"]
e = html.escape

# Header lines shown above the prompt in the app; keep in step with HEADERS in prototype/index.html
HEADERS = {"argue": "Make your case. Be specific."}
IMAGE_HEADERS = {
    "argue": "Make your case for either. Be specific.",
    "invent": "What's going on here? What will happen next?",
    "describe": "What do you notice about this picture?",
}

# Why a prompt is not served (owner's review, 2026-11-22). The CSV only says 'draft'; the reason lives here.
DENIED = {
    "CONFIGURATION CONFLICT": set("des-t-13 des-t-14 des-t-15 des-t-30 des-t-38 des-t-39 des-t-46 "
                                  "nar-t-36 inv-t-52 inv-t-64".split()),  # asks for two tasks (rule 1)
    "BAD PROMPT": {"des-t-16", "des-t-48"},
    "NEXT BUILD": {f"inv-t-{n:02}" for n in range(1, 26)},  # story snippets, to be reshaped
}
HELD = {"des-t-03", "exp-t-03"}  # held back by the owner
# Reworded by the owner in the review (design/2026-11-22-prompt-review-comments.md).
EDITED = set("arg-t-08 arg-t-21 arg-t-23 des-t-01 des-t-08 des-t-09 des-t-10 des-t-12 des-t-16 des-t-19 des-t-20 "
             "des-t-25 des-t-30 des-t-41 des-t-42 des-t-47 des-t-49 inv-t-03 inv-t-06 inv-t-07 inv-t-08 inv-t-11 "
             "nar-t-01".split())
# Flags only, from design/2026-11-22-rule1-conflicts.md; these prompts are approved.
# (Prompts the owner has since reworded are no longer flagged.)
BORDERLINE = set("des-t-04 des-t-23 des-t-24 des-t-43 des-t-07 des-t-22 des-t-28 des-t-29 des-t-33 des-t-34 "
                 "nar-t-17 nar-t-28 nar-t-30 nar-t-46 nar-t-47 inv-t-59".split())
SEVERAL_ANSWERS = set("arg-t-03 arg-t-09 arg-t-11 arg-t-14 arg-t-26 arg-t-29 arg-t-49".split())


def status_mark(s, pid=""):
    reason = next((why for why, ids in DENIED.items() if pid in ids), None)
    if reason:
        mark = f'<span class="mk bad">DENIED: {reason}</span>'
    elif s == "approved":
        mark = '<span class="mk hi">APPROVED</span>'
    else:
        mark = '<span class="mk">HELD BACK</span>' if pid in HELD else f'<span class="mk">{e(s.upper())}</span>'
    if pid in EDITED:
        mark += '<span class="mk">REWORDED BY OWNER</span>'
    if pid in BORDERLINE:
        mark += '<span class="mk">BORDERLINE CONFLICT</span>'
    if pid in SEVERAL_ANSWERS:
        mark += '<span class="mk">SEVERAL ANSWERS</span>'
    return mark


def main():
    all_rows = list(csv.DictReader(TEXT_CSV.open()))
    rows = [r for r in all_rows if r["status"] != "retired"]  # retired rows stay in the CSV, off the page
    retired = len(all_rows) - len(rows)
    images = list(csv.DictReader(IMAGE_CSV.open()))
    stimuli = {r["id"]: r for r in csv.DictReader(STIMULI_CSV.open())}
    status = Counter(r["status"] for r in rows)
    long = [r for r in rows if int(r["words_on_screen"] or 0) > 30]

    out = [
        '<!doctype html><html lang="en"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        "<title>SoundSmarter prompt review</title><style>", (HERE / "app.css").read_text(),
        ".pics{display:flex;gap:10px;margin:.4em 0;max-width:560px}.pics figure{margin:0;flex:1;min-width:0}"
        ".pics img{width:100%;border:1px solid #000;display:block}.pics figcaption{text-align:center;font-weight:700}"
        "</style></head><body class=\"narrow\">",
        f'<div class="strip"><b>{datetime.now():%a %-d %b, %H:%M}</b><b>Text prompts {len(rows)}</b>'
        f'<b>Text approved {status.get("approved", 0)}</b><b>Denied {sum(len(v) for v in DENIED.values())}</b><b>Held back {len(HELD)}</b>'
        f'<b>Reworded by owner {len(EDITED)}</b>'
        f'<b>Image prompts {len(images)}, approved {sum(r["status"] == "approved" for r in images)}</b>'
        f'<b>Retired (hidden) {retired}</b>'
        + (f'<div class="c-bad">Over 30 words on screen: {", ".join(e(r["id"]) for r in long)}</div>' if long else "")
        + "</div>",
        '<p class="small">Every Build 3 prompt. Write comments in <b>design/2026-11-22-prompt-review-comments.md</b>, '
        "by prompt id. Only APPROVED prompts are served. DENIED: CONFIGURATION CONFLICT = asks for two different tasks "
        "(rule 1). DENIED: NEXT BUILD = story snippets, to be reshaped. BORDERLINE CONFLICT and SEVERAL ANSWERS are "
        "flags only; those prompts are still approved. "
        "Details: design/2026-11-22-rule1-conflicts.md.</p>",
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
                    f'<span class="mk">{e(r["id"])}</span>{status_mark(r["status"], r["id"])}</li>'
                )
            out.append("</ul></section>")
        fam_images = [r for r in images if r["family"] == fam]
        if fam_images:
            out.append(f'<section class="box"><h2>{e(fam)} / image / {e(fam_images[0]["variant"])}</h2>'
                       f'<p class="small">{len(fam_images)} prompts — no text of their own — header in the app: '
                       f'<b>{e(IMAGE_HEADERS[fam])}</b></p><ul class="rows">')
            for r in fam_images:
                stim = stimuli[r["stimulus_id"]]
                files = stim["files"].split("|")
                labels = [t.strip() for t in stim["title"].split("|")] if stim["kind"] == "pair" else [""] * len(files)
                out.append(
                    f'<li>{e(stim["title"])} <span class="mk">{e(r["id"])}</span>{status_mark(r["status"])}'
                    '<div class="pics">' + "".join(
                        f'<figure><img src="../stimuli/upload/{e(f)}" alt="{e(stim["title"])}" loading="lazy">'
                        + (f"<figcaption>{e(label)}</figcaption>" if label else "") + "</figure>"
                        for f, label in zip(files, labels)) + "</div></li>")
            out.append("</ul></section>")

    out.append(f'<p class="small">{len(rows)} text prompts, {len(images)} image prompts · from {TEXT_CSV.name} and '
               f"{IMAGE_CSV.name} · audio scripts are for a later build and not shown · rebuilt when pi re-runs "
               "make_page.py</p></body></html>")

    tmp = HERE / "index.html.tmp"
    tmp.write_text("\n".join(out))
    os.replace(tmp, HERE / "index.html")


if __name__ == "__main__":
    main()
