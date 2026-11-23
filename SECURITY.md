# SECURITY.md — Build 3 security audit

*Audited 2026-11-23. Lane: Beginner. Live app: https://soundsmarter-demo.onrender.com/*

## What kind of app this is

**An app with sign-in.** Signed-in users have accounts on Supabase (email and password, a personal sign-up code, a consent notice). For each recording they send, the app stores the transcript, word timings and metrics in Supabase Postgres. Audio is never stored. The app calls one paid service, Nyra Labs CrisperWhisper 2 (speech-to-text, $0.90 per audio hour).

Demo-code visitors can also use the app without an account. Nothing is saved for them.

## Summary

| # | Check | Result |
| --- | --- | --- |
| 1 | Access controls: Account B tries to read Account A's data | Pass. Every read blocked, on production |
| 2 | Secret keys stay on the server | Pass. Nothing found in the repo, its history or the live site |
| 3 | File storage is private | One public bucket, on purpose: prompt images only, no user files |
| 4 | Production is protected from the agent | "Ask Me First" list added; manual backup made |
| 5 | Spending caps and rate limits | Caps in place. Limits on the paid route, sign-up, sign-in and prompt events; the sign-in limit is unproven on the live host |
| 6 | Dependency audit | Pass. `pip-audit`: no known vulnerabilities |
| 7 | Agent security review | 10 findings and 2 of our own. 9 fixed, 3 open |

## 1. Access controls

**The test for an app with sign-in:** log in as Account B and try to read Account A's data.

**How it was run.** `prototype/db/check_cross_account.py --prod` signs in as two real accounts on the production database. Account A has a recording. As Account B, it asks Supabase directly, the way an attacker would, with the public key and B's own sign-in:
- for every row of `recordings`, `prompt_events` and `consents` that belongs to A;
- for one of A's recordings by its id;
- for every row of each table, to confirm B gets only its own;
- for the sign-up codes table.

It then asks for the same tables with no sign-in at all. The script only reads stored data; it never changes or deletes a row.

**Result.** Run by the owner on the production project, 2026-11-23:

```
What Account A can see of its own data:
  recordings: 1 rows
  prompt_events: 3 rows
  consents: 1 rows

Account B asks Supabase for Account A's data:
  BLOCKED  recordings where user is A: HTTP 200, 0 rows
  BLOCKED  prompt_events where user is A: HTTP 200, 0 rows
  BLOCKED  consents where user is A: HTTP 200, 0 rows
  BLOCKED  one of A's recordings, by its id: HTTP 200, 0 rows
  BLOCKED  every row of recordings (B should get only its own): HTTP 200, 0 rows
  BLOCKED  every row of prompt_events (B should get only its own): HTTP 200, 0 rows
  BLOCKED  every row of consents (B should get only its own): HTTP 200, 0 rows
  BLOCKED  the sign-up codes table: HTTP 403, 0 rows

A visitor who is not signed in (public key only):
  BLOCKED  recordings: HTTP 401, 0 rows
  BLOCKED  prompt_events: HTTP 401, 0 rows
  BLOCKED  consents: HTTP 401, 0 rows
  BLOCKED  signup_codes: HTTP 401, 0 rows

PASS: on prod, Account B and signed-out visitors cannot read Account A's data.
```

"HTTP 200, 0 rows" is how the database blocks a read: it answers, but row-level security leaves out every row that is not the asker's own.

**Also checked:**
- Signed-out requests to the live server: `/api/me`, `/api/recordings`, `/api/baseline` and `/api/prompt` each return 401. The demo route returns 403 without a valid code.
- Signed-out requests to the dev database with the public key: all five tables return 401.
- Direct writes: `prototype/db/check_direct_write.py` confirmed on the dev project on 2026-11-22 that a signed-in user cannot add rows to `recordings` or `prompt_events` with the public key. Only the server can write them (migrations 002 and 003).

**Why it holds.** Row-level security is on for every table. Each user can read only rows carrying their own user id. Users have no permission to insert, change or delete rows. The server's secret key was given permission only to insert into two tables (migration 003); the server does all its reading with the user's own sign-in.

## 2. Secret keys

**Searched for:** `sb_secret_`, `service_role`, `sk-or-`, `sk-ant-`, `sk-proj-`, `sk_live_`, and the actual value of all seven keys in the local `.env` (Nyra, Supabase URL, publishable and secret keys, OpenRouter, Deepgram, ElevenLabs).

**Where:** every tracked file, the full git history of every branch, and the page the live site serves. The live page loads no other script of ours.

**Found:** no real key anywhere.
- `.env.example` has placeholders (`sb_secret_replace-with-your-key`, `sk-or-v1-replace-with-your-key`).
- The tests use a made-up key, `sb_secret_test`.
- Migration 003 and one review file use the word `service_role` as the name of a database role, not a key.
- `.env` is in `.gitignore` and has never been committed.
- The `phc_` PostHog key in the page is the public, send-only key.

**Limit of this check:** the production keys live only on Render and are not on this machine, so their exact values could not be searched for. The pattern search (`sb_secret_`) covers the Supabase one. The live page does not contain any Supabase key: the browser signs in and reads records only through our server. The one thing it loads straight from Supabase is the prompt images, from the public bucket in section 3.

Nothing needed rotating.

## 3. File storage

The app stores no user files. Audio goes from the browser to our server to the speech service and is not saved anywhere.

There is one storage bucket, `stimuli`, and it is **public on purpose**. It holds only the generated images used as prompts. They contain no personal data and are shown to every signed-in user anyway. A private bucket with expiring links would add a signing step for no gain. If user files are ever stored, they go in a separate private bucket.

## 4. Protecting production from the agent

- **"Ask Me First" list** added to `AGENTS.md` (section 6): deleting or changing data, keys and permissions, anything that costs money, going live, destructive commands.
- **The agent has no production access.** The local `.env` points at the development project, `soundsmarter-dev`. Production's keys are only on Render. Migrations on production are run by the owner, by hand, after they have run on dev (`AGENTS.md` section 5, Shipping).
- **Manual backup:** on 2026-11-23 the owner exported `recordings`, `prompt_events`, `consents` and `signup_codes` from the production project as CSV files and saved them outside the repo. Prompts and stimuli can be rebuilt from the seed files in git.

## 5. Spending caps and rate limits

**Spending caps**
- **Nyra (the only paid service the live app calls):** a prepaid wallet with automatic top-up off. $10 was paid in and $0.51 is used (owner, from Nyra's dashboard, 2026-11-23). When the wallet is empty the service stops; it cannot bill more. This is the hard cap.
- **OpenRouter (image generation, not called by the live app):** pay as you go, automatic top-up off, no credit limit set on the key (owner, 2026-11-23). The generating script stops itself at $10.
- **Supabase and Render:** free plans with no card on file.
- **PostHog:** free plan.

**Rate limits on the paid route (`/transcribe`)**
- Signed-in: 20 recordings a day per account, counted in the database; the 21st gets a 429. One transcription at a time per account (new today, see section 7).
- Demo: needs a valid code; a daily limit across all codes, then a 429. The limit is 30 unless Render's `DAILY_CAP` setting says otherwise (not checked today).
- Every upload is capped at 2 MB.

**Rate limits on routes that write to the database**
- Sign-up needs an unused personal code, checked inside the database. Each code makes one account.
- Sign-up and sign-in: 30 failed attempts per visitor address per 10 minutes, then a 429 (new today). Only failures count, and the number is generous, because a classroom of testers can share one address.
- Recordings and prompt events can be written only for a signed-in user, by the server.
- Prompt events: only for an approved prompt, and refused once the account has about 500 events that day (new today).

## 6. Dependencies

`uv run --with pip-audit pip-audit`, run from `prototype/` on 2026-11-23, against the app's installed packages: **no known vulnerabilities found.**

## 7. Agent security review

A fresh coding agent with no memory of the build was asked to act as an attacker against the code: read another user's data, write fake data, run up the speech bill, get round the sign-up code, consent or caps, misuse the analytics relay, inject script, leak keys, or crash the server. It read the code and git history only. It found 10 problems. We found two more ourselves on the live site.

Earlier in Build 3, four other fresh-agent reviews had already led to security fixes: users could write their own records directly (fixed by server-only writes), and a wrong server key would have let a recording be paid for before the save failed (fixed by checking first).

**Fixed today** (9 new tests in `prototype/tests/test_hardening.py`; `uv run pytest` passes 66)

| Finding | Fix |
| --- | --- |
| **High.** The 20-a-day cap could be beaten by sending many recordings at the same moment: each passed the cap check before any was counted. | One transcription at a time per account; a second one sent meanwhile waits its turn, so each is counted before the next is checked. |
| Low. The speech service's own error text was shown to the user and could name the account or its balance. | The user sees a general message; the detail goes to the server log. |
| Low. The demo route accepted a 2 MB upload before checking the code. | The code is checked first. |
| Low (ours). The live site served auto-generated pages listing every route (`/docs`, `/openapi.json`). | Turned off. |
| Medium. A very large request body was read into memory before its size was checked. | Any request declaring more than 5 MB is refused before it is read; the analytics relay stops reading at 5 MB. |
| Low. The analytics relay passed any address on to PostHog. | It passes only the PostHog addresses the page was seen to use in a real session (events, session replay, flags and PostHog's own scripts), and tells browsers not to guess file types. |
| Medium. No limit of our own on sign-up and sign-in: one script could use up the allowance all users share at Supabase, or guess sign-up codes. | 30 failed attempts per visitor address per 10 minutes. |
| Medium (ours, found by the owner on the live site). After signing out, the sign-in form still held the email and password that had been typed, so the next person at that computer could sign straight back in. | Both forms are emptied on sign-in, on account creation and on sign-out. A browser's own password manager may still offer a saved password; that is the browser's setting, not the app's. No automated test; checked by hand. |
| Low to medium. A signed-in user could add unlimited prompt-event rows with a script. | The prompt must be an approved one; refused once the account has about 500 events that day. A burst of simultaneous requests can pass a little over. |

**Checked by the review and found sound:** reading other users' data; writing fake data; database query injection; the sign-up code and consent checks; the order of checks before the paid call; the demo gate; script injection (everything from prompts, transcripts and emails is put on the page as plain text); session replay leaves out the forms, the email, the list of recordings and the transcript; keys.

## Remaining issues

1. **The new sign-in limit has not been proven on the live host.** It reads the visitor's address from headers the hosting service is expected to set. If the host does not set or overwrite them, a visitor can fake them and get round the limit; if it sends none, all visitors share one count. Tested in code only. Successful sign-ins are not limited by us, so the allowance all users share at Supabase can still be used up by one person with a working account. The one-at-a-time rule also assumes the app runs as a single server process, which is Render's default and has not been confirmed.
2. **A recording's length is not checked before it is paid for.** The 2 MB limit caps file size, not minutes. Someone with a code or an account could send a long, low-quality file straight to the server, not through the page, and it would be billed by its length. The daily caps and the $10 wallet limit the damage. Fix: trim or refuse audio over 65 seconds on the server.
3. **The demo's daily count is kept in the server's memory**, so it restarts at zero whenever the server restarts or wakes from sleep. The same is true of the new sign-in limit. Fix: keep the counts in the database, which needs a migration.
4. **The analytics relay's list of addresses is fixed.** If PostHog starts using a new address (surveys, for example), those calls are refused until the list is updated.
5. **Smaller items** (the review's tenth finding, and what is left of two others):
   - sign-up reveals whether an email already has an account;
   - email addresses are not confirmed, so an account can be made with someone else's address;
   - the consent check accepts any consent version;
   - the demo code sits in the page address, so it reaches browser history and PostHog;
   - the forwarded visitor address in the analytics relay can be faked by the visitor;
   - a request with no declared size can still be read whole on the routes that take a small form (sign-up, sign-in, refresh, prompt event);
   - sign-in tokens are kept in the browser's local storage and there is no Content Security Policy.
6. **Known gaps carried from the Build 3 reviews** (HANDOFF.md, "Questions for design"): the server does not check that a prompt was served before accepting a recording for it; account deletion and password reset are not built.

Of the review's ten findings, three are open: 2 above (its finding 2), 3 above (its finding 5) and the smaller items in 5 (its finding 10).

## Deployed

The fixes in PR #12 were deployed to Render by the owner on 2026-11-23. Re-checked on the live site the same morning:
- `/docs` and `/openapi.json` return 404;
- an address outside the analytics relay's list returns 404, and PostHog's script still loads through it;
- a demo upload with no code returns 403;
- a wrong sign-in still gets its normal 401;
- the owner signed in, sent a recording and skipped a prompt, and confirmed the events and a session replay arrived in PostHog.

Not re-checked live: the 5 MB refusal (the host turned the test request away before it reached the app) and the sign-in limit (it would need 30 failed sign-ins).

The sign-out fix (PR #13) was deployed by the owner later the same morning. The live page was confirmed to carry it, and the owner checked by hand, on a local run, that the sign-in fields are empty after signing out.
