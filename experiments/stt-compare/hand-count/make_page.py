"""Builds index.html: the 15 recordings needed for the accuracy test, with boxes for the hand counts.

Reads recordings-needed.csv and writes index.html next to this file.
Run from the repo root:  python3 experiments/stt-compare/hand-count/make_page.py
Style: Duncan's browser-app style (app.css, copied). The counts typed into the page are kept
in this browser only, until "Download hand counts" saves them as hand_counts.csv.
"""

import csv
import html
import json
import os
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).parent
e = html.escape
# What gets counted by hand for each recording: (column in the CSV, label on the page)
COUNTS = [
    ("um", "um"), ("uh", "uh"), ("er_erm_ah", "er / erm / ah"),
    ("mid_pauses", "pauses mid-sentence"), ("end_pauses", "pauses after a sentence"),
    ("repeats", "repeated words"), ("cutoffs", "cut-off words"),
    ("first_sound_s", "seconds before first sound"),
]


def row(r: dict) -> str:
    boxes = " ".join(
        f'<label>{e(label)} <input size="3" inputmode="decimal" data-rec="{e(r["id"])}" data-col="{col}"></label>'
        for col, label in COUNTS)
    app = ' <span class="mk hi">ALSO IN THE APP</span>' if r["also_in_app"] else ""
    return (f'<li><b>rec-{e(r["id"])}.m4a</b> — <span class="why">{e(r["tests"])}</span>{app}'
            f'<div class="nxt">{e(r["what_to_do"])}</div>'
            f'<div class="nxt">Prompt: {e(r["prompt"])}</div>'
            f'<div class="nxt">{boxes} <label>notes <input size="30" data-rec="{e(r["id"])}" data-col="notes"></label></div></li>')


def build(rows: list[dict]) -> str:
    now = datetime.now().strftime("%a %-d %b, %H:%M")
    box = lambda title, kind: (  # noqa: E731
        f'<section class="box"><h2>{title}</h2><ul class="rows">'
        + "".join(row(r) for r in rows if r["kind"] == kind) + "</ul></section>")
    cols = json.dumps([c for c, _ in COUNTS] + ["notes"])
    ids = json.dumps([r["id"] for r in rows])
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SoundSmarter: recordings to hand-count</title>
<link rel="stylesheet" href="app.css">
</head>
<body class="narrow">
<div class="strip"><b>{now}</b><b>Recordings {len(rows)}</b><b>Counted <span id="n">0</span></b>
  <button id="dl">Download hand counts</button></div>

<section class="box"><h2>How</h2><ul class="rows">
  <li>Record each one on the phone's voice recorder, 30 to 60 seconds, in a quiet room.</li>
  <li>Name the files rec-01.m4a to rec-15.m4a and put them in experiments/stt-compare/recordings/.</li>
  <li><span class="mk hi">ALSO IN THE APP</span> means: start the same answer in the app at the same moment, signed in on the local copy, and press Send. That compares the browser's recording with the phone's.</li>
  <li>Count from the playback. A pause counts if it is a silence you would notice, about half a second or more.</li>
  <li>For the planted ones, count what you actually said, not what was asked for.</li>
  <li>When done, press Download hand counts and save the file as experiments/stt-compare/hand-count/hand_counts.csv.</li>
</ul></section>

{box("Natural: answer normally, count afterwards", "natural")}
{box("Planted: put these in on purpose", "planted")}

<p class="small">{len(rows)} recordings · from recordings-needed.csv · counts are kept in this browser until downloaded · re-run make_page.py after changing the CSV</p>
<script>
const COLS = {cols}, IDS = {ids}, KEY = "ss_hand_counts";
const saved = JSON.parse(localStorage.getItem(KEY) || "{{}}");
const boxes = [...document.querySelectorAll("input[data-rec]")];
const counted = () => IDS.filter((id) => COLS.slice(0, -1).every((c) => (saved[id + "." + c] || "") !== "")).length;
boxes.forEach((b) => {{
  b.value = saved[b.dataset.rec + "." + b.dataset.col] || "";
  b.oninput = () => {{ saved[b.dataset.rec + "." + b.dataset.col] = b.value; localStorage.setItem(KEY, JSON.stringify(saved));
    document.getElementById("n").textContent = counted(); }};
}});
document.getElementById("n").textContent = counted();
document.getElementById("dl").onclick = () => {{
  const q = (v) => '"' + String(v || "").replace(/"/g, '""') + '"';
  const lines = [["file", ...COLS].join(",")].concat(IDS.map((id) => ["rec-" + id + ".m4a", ...COLS.map((c) => q(saved[id + "." + c]))].join(",")));
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([lines.join("\\n") + "\\n"], {{ type: "text/csv" }}));
  a.download = "hand_counts.csv";
  a.click();
}};
</script>
</body></html>
"""


def main():
    rows = list(csv.DictReader((HERE / "recordings-needed.csv").open()))
    tmp = HERE / "index.html.tmp"
    tmp.write_text(build(rows))
    os.replace(tmp, HERE / "index.html")  # all or nothing
    print(f"wrote {HERE / 'index.html'}: {len(rows)} recordings")


if __name__ == "__main__":
    main()
