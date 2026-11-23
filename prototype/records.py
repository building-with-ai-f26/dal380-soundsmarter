"""Rules for signed-in users, kept free of network code so they can be tested.

  - which prompt to serve next (never one the user has seen)
  - session number and position within the session
  - which prompts were skipped or discarded just before a recording
  - the daily cap window (midnight to midnight, New York time)

  - whether a transcribed recording is usable at all

Rules come from HANDOFF.md decisions 19-25.
"""

import random
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from fillers import words_from_response
from metrics import is_sound

NY = ZoneInfo("America/New_York")
SESSION_GAP = timedelta(minutes=30)  # a new session starts after 30 min with no recording
DAILY_CAP = 20                       # recordings a day per signed-in account
BASELINE_SIZE = 10                   # first 10 recordings: no numbers shown
FAMILIES = ("describe", "narrate", "argue", "invent", "explain")
COUNTS_TOWARD_CAP = ("sent", "rejected")  # each one cost a transcription
SKIP_EVENTS = ("skipped", "discarded")

# Unusable audio, checked after transcription (decisions 21 and 25)
MIN_WORDS = 15                           # fewer spoken words than this can't be measured
MIN_WORDS_PER_S, MAX_WORDS_PER_S = 0.8, 5.0  # outside this, the transcript is implausible
UNUSABLE_MESSAGES = {
    "not_english": "SoundSmarter works in English only, so that recording wasn't analysed. Please record again in English.",
    "too_few_words": "That recording had too few words to analyse. Please record again and keep talking for at least 30 seconds.",
    "implausible_rate": "That recording couldn't be analysed reliably. Please record again.",
}


def unusable_reason(response: dict) -> str | None:
    """Why a transcribed recording can't be used, or None if it can.

    A rejected recording stores no row and shows no numbers. It still cost a
    transcription, so it counts toward the daily cap (a 'rejected' event).
    """
    language = (response.get("language") or "").lower()
    if language and not language.startswith("en"):  # the service detects the language itself
        return "not_english"
    words = [w for w in words_from_response(response) if not is_sound(w.get("word", ""))]
    if len(words) < MIN_WORDS:
        return "too_few_words"
    start, end = words[0].get("start"), words[-1].get("end")
    if start is None or end is None or end <= start:
        return "implausible_rate"
    if not MIN_WORDS_PER_S <= len(words) / (end - start) <= MAX_WORDS_PER_S:
        return "implausible_rate"
    return None


def parse_time(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def day_start_utc(now: datetime | None = None) -> str:
    """Midnight New York time today, as a UTC timestamp string for the database."""
    now = (now or datetime.now(timezone.utc)).astimezone(NY)
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return midnight.astimezone(timezone.utc).isoformat()


def choose_prompt(prompts: list[dict], events: list[dict], recordings: list[dict],
                  family: str | None = None, rng: random.Random | None = None) -> dict | None:
    """Pick the next prompt, or None if every approved prompt has been seen.

    prompts:    approved prompts (what RLS lets the user read)
    events:     the user's prompt events; any event means "seen" (never served twice)
    recordings: the user's recordings, oldest first (for keeping families even)
    family:     after a skip or discard, stay in this family if it has prompts left

    Baseline (the first BASELINE_SIZE recordings, 2 per family): where a family
    has an image prompt, its two recordings are one text and one image, in
    either order. Otherwise both are text.
    """
    rng = rng or random.Random()
    seen = {e["prompt_id"] for e in events}
    unseen = [p for p in prompts if p["id"] not in seen]
    if not unseen:
        return None

    def pick(fam: str) -> dict:
        pool = [p for p in unseen if p["family"] == fam]
        if len(recordings) < BASELINE_SIZE:
            done = {r.get("mode", "text") for r in recordings if r["family"] == fam}
            has_image = any(p.get("mode", "text") == "image" for p in pool)
            wanted = [m for m in (("text", "image") if has_image else ("text",)) if m not in done]
            narrowed = [p for p in pool if p.get("mode", "text") in wanted]
            pool = narrowed or pool  # nothing left in the wanted mode: any prompt in the family will do
        return rng.choice(pool)

    if family:
        if any(p["family"] == family for p in unseen):
            return pick(family)
        # that family has run out for this user: fall through to the normal rotation

    # Rotate families so counts stay even: the family with the fewest recordings
    # goes next; never the same family twice in a row if another is tied.
    open_families = {p["family"] for p in unseen}  # a family with nothing left stops being served
    done = {f: 0 for f in open_families}
    for r in recordings:
        if r["family"] in done:
            done[r["family"]] += 1
    fewest = min(done.values())
    tied = sorted(f for f, n in done.items() if n == fewest)
    last = recordings[-1]["family"] if recordings else None
    if len(tied) > 1 and last in tied:
        tied.remove(last)
    return pick(rng.choice(tied))


def session_slot(last_recording: dict | None, now: datetime) -> tuple[int, int]:
    """(session_no, position_in_session) for a recording made now."""
    if not last_recording:
        return 1, 1
    if now - parse_time(last_recording["created_at"]) < SESSION_GAP:
        return last_recording["session_no"], last_recording["position_in_session"] + 1
    return last_recording["session_no"] + 1, 1


def skipped_before(events: list[dict]) -> list[str]:
    """Prompt ids skipped or discarded since the user's last sent/rejected recording."""
    out = []
    for e in sorted(events, key=lambda e: e["created_at"]):
        if e["event"] in COUNTS_TOWARD_CAP:
            out = []
        elif e["event"] in SKIP_EVENTS:
            out.append(e["prompt_id"])
    return out
