"""Find candidate single-scene images (public-domain paintings) on Wikimedia Commons.

The Met's own image host blocks scripted downloads, so the files come from
Commons, which mirrors the museums' open-access photographs. For each work in
WORKS: search Commons, keep the first landscape public-domain file at least
1600 px wide, download a 1600 px copy into candidates/ (not committed; files go
to Supabase Storage once approved) and write candidates.csv with credit and license.

Run:  cd prototype && uv run python ../design/stimuli/fetch_candidates.py
"""

import csv
import html
import re
import time
from pathlib import Path

import httpx

HERE = Path(__file__).parent
OUT = HERE / "candidates"
COMMONS = "https://commons.wikimedia.org/w/api.php"
WIDTH = 1600
OK_LICENSES = {"public domain", "cc0"}

# (artist, title as searched). From 2026-11-21-stimuli-to-source.md plus extra busy scenes.
WORKS = [
    ("Pieter Bruegel the Elder", "Hunters in the Snow"),
    ("Pieter Bruegel the Elder", "Children's Games"),
    ("Pieter Bruegel the Elder", "The Peasant Wedding"),
    ("Pieter Bruegel the Elder", "The Fight Between Carnival and Lent"),
    ("Pieter Bruegel the Elder", "The Harvesters"),
    ("Pieter Bruegel the Elder", "The Peasant Dance"),
    ("Pieter Bruegel the Elder", "The Census at Bethlehem"),
    ("Hendrick Avercamp", "Winter Landscape with Ice Skaters"),
    ("Hendrick Avercamp", "A Scene on the Ice"),
    ("Jan Steen", "The Merry Family"),
    ("Jan Steen", "The Feast of Saint Nicholas"),
    ("David Teniers the Younger", "Kermis"),
    ("William Powell Frith", "The Railway Station"),
    ("William Powell Frith", "The Derby Day"),
    ("William Powell Frith", "Ramsgate Sands"),
    ("Georges Seurat", "A Sunday on La Grande Jatte"),
    ("Pierre-Auguste Renoir", "Luncheon of the Boating Party"),
    ("Pierre-Auguste Renoir", "Bal du moulin de la Galette"),
    ("Gustave Caillebotte", "Paris Street; Rainy Day"),
    ("Gustave Caillebotte", "The Floor Scrapers"),
    ("Edgar Degas", "A Cotton Office in New Orleans"),
    ("Edouard Manet", "Music in the Tuileries"),
    ("Winslow Homer", "Snap the Whip"),
    ("Winslow Homer", "Breezing Up"),
    ("Winslow Homer", "The Country School"),
    ("George Caleb Bingham", "The Jolly Flatboatmen"),
    ("Eastman Johnson", "Corn Husking Bee"),
    ("Carl Larsson", "Breakfast under the Big Birch"),
    ("Carl Larsson", "Crayfishing"),
    ("Peder Severin Krøyer", "Hip, Hip, Hurrah!"),
    ("Eugène Boudin", "Beach at Trouville"),
    ("Joaquín Sorolla", "Children on the Beach"),
    ("Max Liebermann", "Women Mending Nets"),
    ("Isaac van Ostade", "Frozen River"),
    ("Claude Monet", "Boulevard des Capucines"),
    ("Frederick Childe Hassam", "Rainy Day, Columbus Avenue"),
    ("Jean Béraud", "Boulevard des Capucines"),
    ("Albert Edelfelt", "Children Playing on the Shore"),
]

client = httpx.Client(headers={"User-Agent": "SoundSmarterResearch/0.1 (class project; contact via GitHub duncanlindsay)"}, timeout=60)


def plain(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s or "")).strip()


def get(url, **kw):
    """Commons rate-limits bursts; back off and retry instead of failing the run."""
    for wait in (5, 20, 60, 120):
        r = client.get(url, **kw)
        if r.status_code == 200 and r.content:
            return r
        time.sleep(wait)
    return None


def matches(title, file_title):
    """At least half the title's main words appear in the file name (stops wrong-painting hits)."""
    words = [w for w in re.findall(r"[a-zà-ÿ]+", title.lower()) if len(w) > 3 and w not in {"the", "with", "under"}]
    return sum(w in file_title.lower() for w in words) * 2 >= len(words)


def search(artist, title, taken):
    params = dict(action="query", format="json", generator="search", gsrnamespace=6,
                  gsrsearch=f"{artist} {title}", gsrlimit=8, prop="imageinfo",
                  iiprop="url|size|extmetadata", iiurlwidth=WIDTH)
    r = get(COMMONS, params=params)
    pages = (r.json() if r else {}).get("query", {}).get("pages", {})
    for p in sorted(pages.values(), key=lambda p: p.get("index", 99)):
        ii = p["imageinfo"][0]
        meta = ii.get("extmetadata", {})
        lic = plain(meta.get("LicenseShortName", {}).get("value")).lower()
        if lic in OK_LICENSES and ii["width"] > ii["height"] and ii["width"] >= WIDTH and p["title"].lower().endswith((".jpg", ".jpeg", ".png")) \
                and matches(title, p["title"]) and p["title"] not in taken:
            return p, ii, meta
    return None


def main():
    OUT.mkdir(exist_ok=True)
    rows, taken = [], set()
    for n, (artist, title) in enumerate(WORKS, 1):
        time.sleep(3)
        hit = search(artist, title, taken)
        if not hit:
            print("none:", artist, title)
            continue
        page, ii, meta = hit
        cid = f"cand-{n:02d}"
        img = get(ii["thumburl"])
        if not img or not img.content.startswith(b"\xff\xd8"):  # not a JPEG
            print("download failed:", artist, title)
            continue
        taken.add(page["title"])
        (OUT / f"{cid}.jpg").write_bytes(img.content)
        date = plain(meta.get("DateTimeOriginal", {}).get("value"))[:40]
        rows.append({
            "candidate_id": cid, "artist": artist, "title": title, "date": date,
            "commons_file": page["title"], "source_url": ii["descriptionurl"],
            "full_width": ii["width"], "full_height": ii["height"],
            "license": "Public domain", "credit": f"{artist}, {title}. Public domain, via Wikimedia Commons.",
            "file": f"{cid}.jpg", "status": "candidate",
        })
        print(cid, artist, "|", title, "|", page["title"][:60])
    with (HERE / "candidates.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    main()
