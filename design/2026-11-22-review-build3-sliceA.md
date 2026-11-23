I reviewed `main...build-3` (commit ec3c5b5, 29 files) against HANDOFF decisions 12–26 and the PR body. I didn't edit anything, and the 28 tests pass. No secrets were committed: `.env.example` has placeholders only and no `.env` is tracked.

The biggest problems are that any signed-in user can write fake recordings straight to the database, and that merging to `main` puts this half-built slice on the live site.

## High

1. **Users can write their own records directly** (`prototype/db/migrations/001_init.sql:156` and `:161`). The insert rules only check that a row belongs to the user. The publishable key is public, so a signed-in user can skip our server and write to Supabase directly. They can add recordings with made-up metrics, transcriptions, dates and session numbers, for any prompt, without ever calling Nyra. This technically meets decision 12, but stored records stop being measurements. That undermines decision 14 and the baseline and trends built on it. Severity: high (research data integrity).

2. **Merging deploys an unfinished slice to production** (whole branch). Render serves `prototype/` from `main`, so a merge puts this live. Prod would:
   - show "Sign in · Create account" to every visitor (`index.html:200`);
   - store recordings with no unusable-audio checks (decision 21);
   - still force English;
   - store only the old metrics.

   The PR doesn't say whether `001_init.sql` has run on `soundsmarter-prod` or whether Render has `SUPABASE_*` set. If they're not set, every sign-in attempt returns "Accounts are not set up on this server." Severity: high until confirmed.

## Medium

3. **Unusable audio is still saved** (`server.py:250-283`). A silent or 3-word recording gets a row, uses up one of the 10 baseline slots, and counts toward the cap. Decision 21 says "nothing stored." The PR lists the checks as Slice B, but the Goal line ("each sent recording's metrics… stored") ships the opposite behaviour. Also, nothing ever writes a `rejected` event, although `COUNTS_TOWARD_CAP` (`records.py:20`) expects one.

4. **The daily cap can be exceeded with simultaneous sends** (`server.py:258` vs `:274`). The server checks the count, then calls Nyra (seconds later), then writes `sent`. The background "Next prompt while this one is analysed" link (`index.html:596`) makes parallel sends normal, so a user can go past 20. It's a cost risk, though small at 20 a day.

5. **The server doesn't check that a prompt was served or already sent** (`server.py:254`). Any approved prompt id works, repeatedly. "Never the same prompt twice" (decision 22) is enforced only by the page.

6. **Supabase sign-in limits are shared by everyone** (`supa.py`). All sign-ups and sign-ins reach Supabase from Render's single address, so Supabase's per-address limits apply to all users together. A few failed attempts or a code-guessing run could block sign-in for everyone. Our server has no rate limit of its own on `/api/signup` or `/api/signin`.

7. **A Supabase hiccup signs the user out and loses the recording** (`supa.py:99-106` with `index.html:409`). If Supabase's "who is this user?" check returns any non-200 (including a server error or rate limit), our server reports 401. The page then signs the user out mid-Send and the recording is gone.

8. **Each prompt request spends a prompt** (`server.py:211-220`). `GET /api/prompt` records a `served` event every time. Reloading, leaving via "Account" (`index.html:776`) or a failed microphone start each use up a prompt permanently. Prod will have few approved prompts, so families can run out fast. Abandoned prompts also never appear in `skipped_before`.

9. **Signed-in users skip the English-only notice before recording** (`index.html:777`). "Record A Response" goes straight to recording, bypassing the start screen with the English-only line and the 30-second instruction. Decision 18 requires the notice "before the first recording." Signing in (rather than signing up) never shows it.

10. **The Gaps line is incomplete.** These aren't built and aren't listed:
    - baseline map and trends pages (decisions 19, 24);
    - results "against the user's baseline" from the 11th recording on (decision 19);
    - family × mode comparisons (decision 25).

    Decision 25 allows deferring them, but the PR body should say so.

## Low

11. **The stored `language` is meaningless** (`server.py:38`, `:283`). The service is still told the audio is English, so the stored language is just what we told it.
12. **Version numbers claim more than is stored** (`server.py:43-44`). `metrics_version=1` and `word_list_version=1` are saved, but none of the decision 23 metrics or word-list counts exist yet. When Slice B lands, bump to 2 so v1 rows can be told apart.
13. **Any Supabase 500 at sign-up reads as a bad code** (`supa.py:83`). A Supabase outage shows "That sign-up code isn't valid." The "at least 8 characters" rule is only enforced in the browser (Supabase's default minimum is 6).
14. **Re-running the seed undoes dev approvals** (`make_seed.py:38`, seed file: 215 prompts, 0 approved). Its update also resets `status` from the CSV, so the hand-approved dev prompts go back to draft. Prompts removed from the CSV are never retired in the database.
15. **The sign-up check blocks dashboard-created users** (`001_init.sql:57`). The trigger runs on every new user, so the owner can't create or invite a user from the Supabase dashboard without code metadata. Worth noting in HANDOFF.
16. **Baseline numbers are only hidden on the page.**
    - The server returns full metrics during baseline, and RLS lets users read their own `recordings.metrics` directly. This is a UX rule, not a protection, which is acceptable but worth stating.
    - With background sends, `baselineLeft` can be stale (`index.html:592`), so the 11th recording may be shown without numbers.
17. **Leaving for the account page mid-analysis gives no feedback** (`index.html:776`). The analysis still finishes and saves, but the user never sees the "Previous response saved" message.
18. **Two simultaneous sends can share a session position** (`server.py:268-272`), because both read the same last recording.
19. **Supabase caps reads at 1,000 rows** (`server.py:215`). The "seen prompts" list has no limit; past 1,000 events the list is cut off and prompts could repeat. Not near-term.
20. **Login tokens are kept in the browser's local storage** (`index.html`, `ss_session`). A script injected into the page could read them. The page currently writes text safely (`textContent`), so the risk is low.
21. **Check PostHog network capture.** Session replay is on with defaults. If "capture network requests/headers" is ever enabled in PostHog, `/api/signin` passwords and Bearer tokens would be recorded. Confirm it's off.
22. **Untested paths:**
    - `/api/prompt`, `/api/prompt-event`, `/api/recordings` (baseline hiding), `/api/signin`, `/api/refresh`;
    - Supabase error mapping (409, weak password);
    - failure when Supabase is down;
    - the two-account RLS test (already noted in Gaps).
23. **Docs not updated.** AGENTS.md's project structure doesn't list `records.py`, `supa.py` or `db/`. The Product Page (`docs/index.html`) has no Build 3 log entry (AGENTS rule 10).

**Summary: 23 findings (2 high, 8 medium, 13 low), none fixed.**
