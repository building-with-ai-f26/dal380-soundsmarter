I reviewed the three commits from `ec3c5b5` to `43734ee` (prompt rewrite, argue header, server-only writes) against HANDOFF.md. I didn't edit anything. All 32 tests pass. No secrets were committed: the only `sb_secret_` values are the placeholder in `.env.example` and the fake one in the tests, and `.env` isn't tracked.

**Finding 1 (users writing their own records):** fixed as claimed. Users can no longer add rows, the server stamps each row with the user it checked, and sign-in, consent and the missing-key case are each checked before Nyra is called. The problems below are smaller ones left around it.

## Medium

1. **Prod's database lock is untested, though it could be tested now.** `db/check_direct_write.py` always loads the repo-root `.env`, which points at dev. Migrations 002 and 003 have run on prod, and testing that doesn't need a merge. The script would just need to point at prod's address and public key.
2. **A missing or wrong secret key still costs a transcription.** `supa.can_write` (`supa.py`) only checks that `SUPABASE_SECRET_KEY` is set, not that it works. If Render has a wrong or revoked key, or migration 003 didn't run, Nyra is called and paid. The save then fails, and the user gets an error and loses their results. Nothing tests this failure path. The PR doesn't say whether `SUPABASE_SECRET_KEY` is set on Render yet.
3. **Many new prompts break writing rule 1 ("one task per prompt").** Decision 27 overrides rules 2 and 10 only, but many prompts now ask two things. For example, `des-t-01` asks what the kitchen looked like and then what you loved or disliked about it. Rule 1 names exactly that (a description, then an opinion) as two tasks. Some argue prompts ask for several answers: `arg` "How early should you show up to a dinner, a flight, and a job interview?" sits awkwardly under "Give at least two reasons." This needs a design call before anything is approved.

## Low

4. **Consent is now checked only by the server.** Migration 002 removed the database's consent rule for recordings, so the database no longer enforces it. The code comment says so, but HANDOFF decision 12 and 14 don't.
5. **`/api/prompt-event` saves whatever prompt id the browser sends.** That includes draft or retired prompts the user can't see. It can't fake a measurement, and it was already possible before, but "only the server writes" doesn't mean the server checked the prompt.
6. **HANDOFF decision 12 names migration 002 but not 003.** Without 003 the server can't save anything.
7. **Migration 003's claim about the server key is checked only on dev.** It says the key "only adds rows, cannot read." That holds only if prod's default permissions match dev's.
8. **The check script leaves junk rows if the lock is broken.** Its fake rows would then be saved and never removed. They'd count toward that test account's 10 starter recordings and its seen prompts.
9. **The argue header isn't shown on the review screen.** That screen (`index.html:590`) shows the prompt without the header. The header text is also kept in two places (`make_page.py` and `index.html`), held in sync only by a code comment.
10. **The `beats` column (how many parts a prompt asks for) is now inaccurate and still goes into the database.** Every whatif prompt is marked 2, but `inv-t-65` and `inv-t-74` ask three questions. Decision 27 dropped fixed beats, but the column wasn't updated.
11. **Argue's `variant` is still called `statement`,** but the prompts are now questions.
12. **Two voice points for design.**
    - Narrate: 28 of 50 prompts open with "Tell me about…", which is close to the fixed wording decision 27 rules out.
    - Some prompts speak as "I" ("If I opened your refrigerator…"). Decision 27 covers "you" but says nothing about "I".
13. **A HANDOFF note says image prompt wording "comes with the next commit".** No later commit added it, so the note is out of date.
14. **Untested paths:**
    - the argue header in a browser (already listed in Gaps);
    - the database refusing a save;
    - the lock check on prod;
    - the server actually being unable to read with its key.

**Summary: 14 findings (0 high, 3 medium, 11 low), none fixed.**
