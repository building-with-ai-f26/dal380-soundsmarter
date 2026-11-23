I found 6 problems. None is serious, and 3 are small. I changed nothing. All 57 unit tests pass when I run them myself.

**1. A sign-out while an image prompt loads can drop the user on the wrong screen** (`index.html`, `fetchPrompt`)
- The new "served" message is sent from inside a block that hides every error, including the one raised when the user is signed out.
- If that request gets a 401 (not signed in), the page signs the user out and clears the current prompt. `fetchPrompt` then returns as if nothing happened, and `startSignedIn` carries on into `startTake()`.
- `startTake()` turns the microphone on and shows the record screen. Because the user is now signed out, it shows a demo prompt (`PROMPTS[index]`), not the sign-in page.
- This path is now more likely because each image prompt adds one more "who is this user?" call to Supabase. Finding 7 (a failed check signs the user out) still stands as a known gap. The new problem is the wrong screen afterwards.

**2. The baseline averages mix version 2 and version 3 numbers** (`records.py`)
- `_average`, `baseline_table` and `baseline_for` don't check `metrics_version`.
- Version 3 changes two of the five compared numbers: filled share (`filled_share_count`) and mid-sentence pauses per 100 words (`mid_pauses_per_100`). Silent hesitations now include sentence-end pauses, and some former mid-sentence pauses now count as sentence ends.
- So a user whose first 10 recordings span the version change gets a baseline averaged across two definitions. HANDOFF says version 2 rows "keep their numbers; no backfill" but doesn't say they can be averaged with version 3 rows. On dev this only affects the owner's test recordings, but the mixing is silent.

**3. "A filler at the boundary" only means um and uh** (`metrics.py`)
- The look-back that stops a filler hiding a sentence end uses `is_filler`, which covers um and uh only.
- After "chimneys. er", the pause still counts as mid-sentence. A pause next to er, erm or ah counts as a silent hesitation, so it lowers filled share.
- The speech service labels those words `filler`, but the code ignores that label here. This fits "the filler number shown is um and uh only", but the goal and HANDOFF decision 25 just say "a filler". A design call to confirm.

**4. Untested parts of the version 3 sentence-end logic** (`metrics.py`)
- There's no test for the backup route used when words don't say which alignment entry is theirs (the `entries_for` text-matching path) combined with the tidied-text check.
- A service-added full stop is only found if it is the very next entry. If the service adds a word and then the full stop, the sentence end is missed.
- A tidied word with a stop inside it, such as "Mr." or "U.S.", would wrongly mark a sentence end. The old check had the same weakness, but only on the spoken words.

**5. The save check can crash instead of refusing politely** (`supa.py`)
- `r.json().get("code")` only catches `ValueError`. If Supabase answered with valid JSON that isn't an object (a list, a string), `.get` fails with `AttributeError`.
- The user would see a generic 500 error instead of the 503 "nothing was sent" message. Nyra is still not paid, so it costs nothing. Unlikely to happen.

**6. Small mismatches and untested paths**
- The `signed_out_forced` event is sent anonymously, because the page never tells PostHog who the user is. HANDOFF says "repeats can be counted", but only per browser, not per user.
- Waiting for the "served" reply delays the image screen by one round trip after the pictures load. Prep time is unaffected because it starts when the screen appears; the cost is a slightly longer wait.
- `/api/prompt-event` accepts "served" for any prompt id, text prompts included. Users can only mark their own prompts, so this is not a security issue.
- None of the page changes is tested: the 15 second limit, the "served" post, or the forced sign-out event. You already listed this in Gaps.

**Checked and fine**
- A rejected prompt can be served again and is used up once it's sent, skipped or discarded. A rejected attempt no longer clears the earlier skips.
- The save check goes ahead only on HTTP 400 with code 23502; any other answer stops it. A missing grant (migration 003 not run) gives a different code, so it also stops.
- The metrics version is now 3, and the HANDOFF notes match the code.
- I found no secrets in the diff. The PostHog key in `index.html` is the public browser key and was already there.

To log: review: 6 findings, 0 fixed. Findings 1 and 2 are the ones worth fixing before merge; 3 needs a design call.
