"""Builds generated.html: review page for the generated image candidates.

Shows the versions the owner is choosing between: argue pairs as line drawings;
invent and describe scenes as a landscape and a square photograph side by side.

Run from the repo root:  python3 design/stimuli/make_generated_page.py
Reads generated.csv; images load from candidates/generated/ (local only, not
committed). Style: browser-app style (app.css).
"""

import csv
import html
import os
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).parent
e = html.escape
FAMILY_NOTE = {
    "argue": "Argue: two simple line drawings side by side, square so both fit on a phone.",
    "invent": "Invent: an action between at least two parties, each person with a specific expression. Landscape "
              "next to a square version, which shows larger on a phone. The square one is a new picture, not a crop.",
    "describe": "Describe: many separate things to name. Landscape next to a square version, as above.",
}
# Round 2 (owner, 2026-11-22): Sunburst throughout. The MAI versions and the photographic argue
# pairs stay in generated.csv and on disk but are left off this page.
# Round 3: the first invent scenes (blank smiles) are hidden too; the versions with expressions replace them.
SHOWN = {"argue": ["sunburst-line"], "invent": ["sunburst-expr", "sunburst-expr-square"],
         "describe": ["sunburst", "sunburst-square"]}
LABEL = {"sunburst-line": "line drawing", "sunburst": "landscape", "sunburst-square": "square",
         "sunburst-expr": "landscape", "sunburst-expr-square": "square"}


def version(r: dict) -> str:
    """Which version a file is, from its name: img-inv-01__sunburst-square.jpg -> sunburst-square."""
    return r["file"].rsplit(".", 1)[0].split("__")[1]


def picture(r: dict, caption: str) -> str:
    return (f'<figure><img src="candidates/generated/{e(r["file"])}" alt="{e(r["item"])}" loading="lazy">'
            f'<figcaption class="small">{e(caption)}</figcaption></figure>')


def main():
    logged = list(csv.DictReader((HERE / "generated.csv").open()))
    spent = sum(float(r["billed_usd"]) for r in logged)
    rows = [r for r in logged if version(r) in SHOWN[r["family"]]]
    stimuli = {}
    for r in rows:
        stimuli.setdefault(r["stimulus_id"], []).append(r)
    out = [
        '<!doctype html><html lang="en"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        "<title>SoundSmarter generated images</title><style>", (HERE / "app.css").read_text(),
        "figure{margin:0;flex:1;min-width:0}img{width:100%;border:1px solid #000;display:block}"
        ".versions{display:flex;gap:10px;margin:.4em 0 1em;align-items:flex-start}details{margin:.2em 0 .6em}"
        "</style></head><body>",
        f'<div class="strip"><b>{datetime.now():%a %-d %b, %H:%M}</b><b>Items {len(stimuli)}</b>'
        f"<b>Shown {len(rows)} of {len(logged)} images</b><b>Spent ${spent:.2f} of $10.00</b></div>",
        '<p class="small">All by OpenAI GPT Image 2.5 Sunburst. Tell pi in chat what to keep, for example '
        '"argue: all except img-arg-05; invent: square for all; img-des-04 landscape; img-des-02 neither". '
        "Check each for legible text, logos and anything odd (hands, faces).</p>",
    ]
    for family in ("argue", "invent", "describe"):
        out.append(f'<section class="box"><h2>{e(family)}</h2><p class="small">{e(FAMILY_NOTE[family])}</p>')
        for sid, group in sorted(stimuli.items()):
            if group[0]["family"] != family:
                continue
            group.sort(key=lambda r: (SHOWN[family].index(version(r)), r["file"]))
            names = " / ".join(dict.fromkeys(r["item"] for r in group))
            out.append(f'<h3>{e(names)} <span class="mk">{e(sid)}</span></h3><div class="versions">'
                       + "".join(picture(r, r["item"] if family == "argue" else LABEL[version(r)]) for r in group)
                       + "</div>")
            prompts = dict.fromkeys(r["generation_prompt"] for r in group)
            out.append("<details><summary class=\"small\">Generation prompt</summary>"
                       + "".join(f'<p class="small">{e(p)}</p>' for p in prompts) + "</details>")
        out.append("</section>")
    out.append(f'<p class="small">{len(rows)} images · logged in generated.csv by generate_images.py · '
               "rebuilt when pi re-runs make_generated_page.py</p></body></html>")
    tmp = HERE / "generated.html.tmp"
    tmp.write_text("\n".join(out))
    os.replace(tmp, HERE / "generated.html")


if __name__ == "__main__":
    main()
