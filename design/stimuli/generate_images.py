"""Generates candidate images for Build 3 image prompts (HANDOFF decision 28).

Each item is made once by each of two models from different makers, in one
style (natural-light photograph), through OpenRouter's Image API. The owner
keeps the better version of each item, or neither.

Run from prototype/ (it has the libraries and reads OPENROUTER_API_KEY from the
repo-root .env):
  uv run python ../design/stimuli/generate_images.py --probe   one image per model, to see what it costs
  uv run python ../design/stimuli/generate_images.py           everything not made yet

Images go to design/stimuli/candidates/generated/ (not committed). Every image
made is logged in design/stimuli/generated.csv with its model, the exact
generation prompt and the cost OpenRouter billed. It never starts a request
that could take the total over SPEND_CAP, and it skips images that already
exist, so it is safe to re-run.
"""

import base64
import csv
import os
import sys
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv

HERE = Path(__file__).parent
OUT = HERE / "candidates" / "generated"
LOG = HERE / "generated.csv"
load_dotenv(HERE.parent.parent / ".env")

API = "https://openrouter.ai/api/v1/images"
SPEND_CAP = 10.00  # US dollars, for the whole set (owner, 2026-11-22)
SUNBURST = ("openai/gpt-image-2.5-sunburst", {"quality": "medium", "output_format": "jpeg"})
MODELS = {  # version name used in file names -> (OpenRouter model, extra request settings)
    # Round 1: every item as a landscape photograph, by two models.
    "sunburst": (SUNBURST[0], {**SUNBURST[1], "aspect_ratio": "3:2"}),
    "mai": ("microsoft/mai-image-2.7", {"aspect_ratio": "3:2"}),
    # Round 2 (owner, 2026-11-22: Sunburst preferred throughout; no photorealism for argue pairs;
    # wide photographs are hard to see on a phone). Argue pairs as simple line drawings, square so
    # two fit side by side on a phone; invent and describe scenes again as square photographs.
    "sunburst-line": (SUNBURST[0], {**SUNBURST[1], "aspect_ratio": "1:1"}),
    "sunburst-square": (SUNBURST[0], {**SUNBURST[1], "aspect_ratio": "1:1"}),
    # Round 3 (owner, 2026-11-22): invent scenes again with a specific expression for each person,
    # because everyone had the same blank smile and eyes lock on faces.
    "sunburst-expr": (SUNBURST[0], {**SUNBURST[1], "aspect_ratio": "3:2"}),
    "sunburst-expr-square": (SUNBURST[0], {**SUNBURST[1], "aspect_ratio": "1:1"}),
}
ROUND_1 = ["sunburst", "mai"]  # only the first six items of each family were made as two-model photographs


def versions(family: str, number: int) -> list[str]:
    """Which versions an item gets. Items 7-12 were added in round 3, after the styles were settled."""
    first = ROUND_1 if number <= 6 else []
    if family == "argue":
        return first + ["sunburst-line"]
    if family == "invent":
        return first + ["sunburst-square", "sunburst-expr", "sunburst-expr-square"]
    return (first or ["sunburst"]) + ["sunburst-square"]
COLUMNS = ["file", "stimulus_id", "family", "item", "model", "billed_usd", "media_type", "generation_prompt"]

LINE = ("A very simple hand-drawn line drawing of this subject: {item}. Clean black outlines of even weight, "
        "filled with two or three flat basic colors, on a plain white background. Centered, with generous white "
        "space around it. No shading, no gradients, no texture, no shadows, no 3D, nothing photographic or realistic. "
        "Nothing else in the picture. No text, lettering, numbers, labels or logos.")

STYLE = ("Natural-light photograph, landscape orientation, realistic and unposed. "
         "No legible text, lettering, numbers, signs, labels, brand logos or watermarks anywhere in the image. "
         "No recognizable real people, no famous landmarks; an ordinary, unnamed place. Nothing distressing.")

# Argue pairs: one item per image. The two images of a pair share a template so
# framing, lighting and scale match.
PLAIN = ("One {item}, alone and centered, filling about half the height of the frame, seen at eye level, "
         "on a plain, seamless, light neutral background with soft, even daylight from the left. Nothing else in the picture.")
OUTDOOR = ("{item}, seen straight on from a middle distance and centered, under a soft overcast midday sky, "
           "horizon one third of the way up the frame. No people. Nothing else of interest in the picture.")
PAIRS = [  # (stimulus id, template, item a, description a, item b, description b)
    ("img-arg-01", PLAIN, "Cat", "short-haired tabby cat, sitting upright and facing the camera",
     "Dog", "medium-sized short-haired mixed-breed dog, sitting upright and facing the camera"),
    ("img-arg-02", OUTDOOR, "Swings", "A playground swing set with two empty swings, standing on plain grass",
     "Slide", "A playground slide, empty, standing on plain grass"),
    ("img-arg-03", PLAIN, "Peanut butter", "open, unlabelled clear glass jar of peanut butter with a spoon standing in it",
     "Jelly", "open, unlabelled clear glass jar of dark red fruit jelly with a spoon standing in it"),
    ("img-arg-04", PLAIN, "Coffee", "plain white cup of black coffee on a white saucer",
     "Tea", "plain white cup of tea on a white saucer, with a tea bag steeping in it and its string over the rim"),
    ("img-arg-05", OUTDOOR, "Beach", "A wide, empty sandy beach with gentle waves",
     "Mountains", "A wide view of a mountain range with a meadow in front"),
    ("img-arg-06", PLAIN, "Pancakes", "stack of three plain pancakes on a plain white plate",
     "Waffles", "stack of three plain waffles on a plain white plate"),
    ("img-arg-07", PLAIN, "Pizza", "whole round pizza with simple toppings",
     "Burger", "hamburger in a bun"),
    ("img-arg-08", PLAIN, "Bicycle", "bicycle seen from the side",
     "Car", "small car seen from the side"),
    ("img-arg-09", PLAIN, "Book", "open book lying flat",
     "Television", "flat-screen television on a stand, switched off"),
    ("img-arg-10", PLAIN, "Train", "passenger train seen from the side",
     "Airplane", "passenger airplane seen from the side"),
    ("img-arg-11", PLAIN, "Ice cream", "ice cream cone with two scoops",
     "Cake", "slice of layer cake on a small plate"),
    ("img-arg-12", PLAIN, "Bath", "bathtub full of water with bubbles",
     "Shower", "shower head with water coming out, above a shower tray"),
]

INVENT = ("A candid moment caught mid-action. {scene} Everyone's face, hands and body language are clearly readable, "
          "and the people involved are the centre of the picture.")
EXPRESSIONS = ("The expressions are specific, strong and easy to read, as described. "
               "Nobody is smiling blankly, and nobody is looking at the camera.")
SCENES_INVENT = [  # (stimulus id, name, the scene, the same scene with each person's expression)
    ("img-inv-01", "Cat over the fence",
     "Two neighbors are passing a cat over a garden fence; one of them is standing on a ladder. A watering can lies tipped over on the ground.",
     "Two neighbors are passing a cat over a garden fence. The one on a ladder, handing the cat over, looks embarrassed and apologetic, wincing. "
     "The one receiving it is frowning, plainly annoyed. The cat is wide-eyed. A watering can lies on its side on the ground, its water spilled."),
    ("img-inv-02", "The plate",
     "In a restaurant, a waiter and a seated diner are each holding one side of the same plate of food. A full plate of food is already on the table in front of the diner.",
     "In a restaurant, a waiter and a seated diner are each holding one side of the same plate of food. A full plate of food is already on the table "
     "in front of the diner. The diner is surprised and taken aback: leaning away, eyebrows raised, mouth open. The waiter is insistent and confused, brow furrowed."),
    ("img-inv-03", "Oranges in the crosswalk",
     "A man in a suit and a cyclist in a helmet are both crouched over oranges rolling across a street crosswalk. Several people wait at the curb, watching.",
     "A woman cyclist in a helmet has dropped a bag of oranges, which are rolling across a street crosswalk. She is crouched, scrambling to gather them, "
     "stressed and flustered, grimacing. A man in a suit crouches beside her to help, calm and concerned. At the curb, one person is laughing "
     "and another is impatient, checking a watch."),
    ("img-inv-04", "The sofa",
     "Two movers have a sofa wedged in the doorway of a house, one of them inside and one outside. A third person stands nearby holding a tape measure.",
     "Two movers are forcing a sofa through the doorway of a house, one of them inside and one outside, and it is only just fitting. Both movers are "
     "straining, teeth gritted, faces red with effort. A third person stands nearby holding a tape measure, visibly relieved: eyes closed, breathing out, a hand on their chest."),
    ("img-inv-05", "The guitar",
     "On a city sidewalk, a street musician is handing his guitar to a passer-by dressed in office clothes. A few people stand watching.",
     "On a city sidewalk, a street musician is holding his guitar out to a passer-by dressed in office clothes. The musician is grinning, daring them "
     "to take it. The passer-by is nervous and reluctant: wide-eyed, leaning back, hands half raised. Among a few people watching, one is curious and one is skeptical, arms crossed."),
    ("img-inv-06", "The last umbrella",
     "By a doorway, two people are reaching at the same moment for the last umbrella in an umbrella stand, as rain starts to fall outside.",
     "By a doorway, two people each have a hand on the last umbrella in an umbrella stand, as rain starts to fall outside. One is determined, jaw set, "
     "staring the other down. The other is startled and indignant, mouth open in protest."),
]

DESCRIBE = ("A wide, busy, detailed view of {scene}. Many separate, clearly visible things to name: objects, activities, "
            "colors and small details in every part of the frame. Any people are small, at a distance, and not the subject.")
SCENES_DESCRIBE = [
    ("img-des-01", "Farmers market", "an outdoor farmers market with many stalls"),
    ("img-des-02", "Kitchen mid-meal", "a lived-in home kitchen in the middle of a meal being cooked"),
    ("img-des-03", "Playground", "a neighborhood playground on a weekend afternoon"),
    ("img-des-04", "Train platform", "a train station platform with a train standing at it"),
    ("img-des-05", "Bike repair workshop", "the inside of a small bicycle repair workshop"),
    ("img-des-06", "Campsite at dusk", "a campsite at dusk with tents, a campfire and gear laid out"),
    ("img-des-07", "Harbor", "a small working harbor with fishing boats, nets, crates and gulls"),
    ("img-des-08", "Classroom", "an elementary school classroom between lessons, with desks, supplies and children's artwork"),
    ("img-des-09", "Laundromat", "the inside of a neighborhood laundromat with machines running and baskets of clothes"),
    ("img-des-10", "Busy beach", "a busy public beach on a summer day, with umbrellas, towels, toys and games"),
    ("img-des-11", "Garden center", "a garden center greenhouse full of plants, pots, tools and carts"),
    ("img-des-12", "Cafe terrace", "a street corner cafe terrace with tables, chairs, plants, bicycles and a passing street"),
]


def items() -> list[dict]:
    """Every picture to make: stimulus id, file stem, family, item name, versions, generation prompts."""
    out = []
    for sid, template, a, desc_a, b, desc_b in PAIRS:
        for letter, name, desc in (("a", a, desc_a), ("b", b, desc_b)):
            out.append({"stimulus_id": sid, "stem": f"{sid}-{letter}", "family": "argue", "item": name,
                        "prompt": template.format(item=desc) + " " + STYLE,
                        "prompt_line": LINE.format(item=desc[0].lower() + desc[1:])})
    for sid, name, scene, with_expressions in SCENES_INVENT:
        out.append({"stimulus_id": sid, "stem": sid, "family": "invent", "item": name,
                    "prompt": INVENT.format(scene=scene) + " " + STYLE,
                    "prompt_expr": INVENT.format(scene=with_expressions) + " " + EXPRESSIONS + " " + STYLE})
    for sid, name, scene in SCENES_DESCRIBE:
        out.append({"stimulus_id": sid, "stem": sid, "family": "describe", "item": name,
                    "prompt": DESCRIBE.format(scene=scene) + " " + STYLE})
    for it in out:
        it["versions"] = versions(it["family"], int(it["stimulus_id"][-2:]))
    return out


def prompt_for(it: dict, version: str) -> str:
    """The exact generation prompt for one version of an item."""
    prompt = {"sunburst-line": it.get("prompt_line"), "sunburst-expr": it.get("prompt_expr"),
              "sunburst-expr-square": it.get("prompt_expr")}.get(version) or it["prompt"]
    return prompt.replace("landscape orientation", "square format") if version.endswith("square") else prompt


def read_log() -> list[dict]:
    return list(csv.DictReader(LOG.open())) if LOG.exists() else []


def write_log(rows: list[dict]):
    with LOG.open("w", newline="") as f:
        w = csv.DictWriter(f, COLUMNS)
        w.writeheader()
        w.writerows(sorted(rows, key=lambda r: r["file"]))


def generate(client: httpx.Client, model: str, extra: dict, prompt: str) -> tuple[bytes, str, float]:
    r = client.post(API, json={"model": model, "prompt": prompt, "n": 1, **extra})
    if r.status_code != 200:
        raise RuntimeError(f"{model}: HTTP {r.status_code} {r.text[:300]}")
    body = r.json()
    image = body["data"][0]
    cost = float((body.get("usage") or {}).get("cost") or 0)
    return base64.b64decode(image["b64_json"]), image.get("media_type", "image/png"), cost


def main():
    probe = "--probe" in sys.argv
    key = os.environ.get("OPENROUTER_API_KEY", "")
    if not key:
        sys.exit("OPENROUTER_API_KEY is not set in .env")
    OUT.mkdir(parents=True, exist_ok=True)
    rows = read_log()
    done = {r["file"].rsplit(".", 1)[0] for r in rows if (OUT / r["file"]).exists()}
    spent = sum(float(r["billed_usd"]) for r in rows)
    dearest = {short: max([float(r["billed_usd"]) for r in rows if r["model"] == m] or [0.0])
               for short, (m, _) in MODELS.items()}  # dearest image seen so far from each version's model

    todo = [(it, short) for it in items() for short in it["versions"] if f"{it['stem']}__{short}" not in done]
    if probe:  # the first missing item, once per model
        todo = [next(t for t in todo if t[1] == short) for short in MODELS if any(t[1] == short for t in todo)]  # one per version
    print(f"{len(todo)} to make; ${spent:.2f} spent so far of ${SPEND_CAP:.2f}")

    with httpx.Client(timeout=300, headers={"Authorization": f"Bearer {key}"}) as client:
        for it, short in todo:
            model, extra = MODELS[short]
            prompt = prompt_for(it, short)
            # Never start a request that could cross the cap: allow for the dearest image seen so far
            # from this model, with a margin; before any is seen, assume 50 cents.
            allowance = dearest[short] * 1.5 if dearest[short] else 0.50
            if spent + allowance > SPEND_CAP:
                print(f"STOPPED before {it['stem']} ({short}): ${spent:.2f} spent, next could cost ${allowance:.2f}, cap ${SPEND_CAP:.2f}")
                break
            started = time.time()
            try:
                data, media_type, cost = generate(client, model, extra, prompt)
            except Exception as err:  # one failure should not lose the rest
                print(f"FAILED  {it['stem']} ({short}): {str(err)[:200]}")
                continue
            ext = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}.get(media_type, "png")
            name = f"{it['stem']}__{short}.{ext}"
            (OUT / name).write_bytes(data)
            if cost <= 0:  # without a billed cost the spend cap can't be enforced
                print(f"STOPPED: {name} was saved but OpenRouter reported no cost, so spend can't be tracked.")
                break
            spent += cost
            dearest[short] = max(dearest[short], cost)
            rows = [r for r in rows if r["file"] != name] + [{
                "file": name, "stimulus_id": it["stimulus_id"], "family": it["family"], "item": it["item"],
                "model": model, "billed_usd": f"{cost:.4f}", "media_type": media_type, "generation_prompt": prompt}]
            write_log(rows)  # after every image, so a crash loses nothing
            print(f"ok  {name}  ${cost:.4f}  {len(data) // 1024} KB  {time.time() - started:.0f}s  (total ${spent:.2f})")
    print(f"Done. ${spent:.2f} spent in total. {len(read_log())} images logged.")


if __name__ == "__main__":
    main()
