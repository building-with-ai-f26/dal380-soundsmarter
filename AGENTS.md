# AGENTS.md — Coding Agent Operating Manual

> Give this file to your coding agent and check that it is using these instructions. Keep the stack, commands, and ground rules current.

## 1. Project Overview
- **What this repo builds:** SoundSmarter records 30–60 seconds of extemporaneous speech and returns measured metrics (filler count, fillers per 100 words, prep time, pauses) so speakers become aware of their filler and pause habits.
- **Who it's for:** Speakers who want to develop awareness of their extemporaneous speech patterns through metric analysis (PRD, 2026-11-16). Improvement-seeking users come later, once recommendations or tracking across recordings exist. Not for language learners.
- **The one job:** give a speaker measured feedback on *how* they speak, response after response.
- **Primary user & core workflow:** prompt → record → transcribe → metrics. Full PRD in `docs/index.html`.
- **Copy rule:** never call a recording a "take" (owner, 2026-11-16). Say recording, response, or attempt. Applies to the app, the Product Page and docs. Code identifiers (`takes_left`, `TAKES_PER_CODE`) can stay.
- **Tech stack:** Build 1: throwaway local prototype using Deepgram speech-to-text (filler words on, word timestamps). From Build 2: speech-to-text is CrisperWhisper 2 via Nyra's hosted API (decided 2026-11-15 after test C). Current lean, not set in stone: web client (browser MediaRecorder), Python backend (FastAPI), SQLite. Details in HANDOFF.md → Technical choices.

- **Product source of truth:** [`HANDOFF.md`](./HANDOFF.md). Read it before building. Product decisions are made in design review and by the owner; the agent merges approved changes, builds, and never changes a product decision on its own. Put anything that needs deciding under "Questions for design" at the end of HANDOFF.md.

## 2. Commands
All commands run from the `prototype/` folder (`cd prototype`). Needs `NYRA_API_KEY` in the repo-root `.env` (CrisperWhisper via Nyra's API, from Build 2; Build 1 used Deepgram). Sign-in and stored records also need `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY` and `SUPABASE_SECRET_KEY` (see `.env.example`); the secret key is server-only.
- **Install dependencies:** `uv sync`
- **Run locally:** `uv run uvicorn server:app --reload --port 8001`, then open http://localhost:8001 (port 8000 is the logbook board)
- **Run deterministic tests:** `uv run pytest`
- **Run model evals:** none yet (Build 4)

## 3. Project Structure
- `prototype/`: the app. Run everything from here.
  - `server.py`: web server; receives a recording, calls Nyra, returns results
  - `index.html`: the whole front end (all screens, PostHog setup)
  - `fillers.py`: counts "um"/"uh" in the transcript
  - `metrics.py`: every number computed from a transcription (shown: word count, fillers per 100 words, prep time, pauses; stored: rates, repairs, filled share and more)
  - `wordlist.py`: the words and phrases counted by form in every recording
  - `access.py`: invite codes and daily cap for the shared demo
  - `supa.py`: talks to Supabase (sign-in, reading and saving records, stimulus files)
  - `records.py`: rules for signed-in users (which prompt next, sessions, daily cap)
  - `db/`: database migrations, the seed built from the prompt CSVs (`make_seed.py`), and `check_direct_write.py`
  - `analytics_proxy.py`: relays PostHog events so ad blockers don't drop them
  - `tests/`: unit tests for `access`, `analytics_proxy`, `fillers`, `metrics`, `records` and the signed-in flow (`uv run pytest`)
- `docs/index.html`: Product Page (PRD + build log), served by GitHub Pages
- `HANDOFF.md`: product source of truth. Read before building
- `README.md`: front page of the GitHub repo, for human visitors
- `tests/` (repo root): verification guidance for Build 4, not test code
- `design/`: design briefs, mockups, logo; the prompt and stimulus CSVs (source of truth for prompts); `design/stimuli/` generates and reviews images
- `experiments/stt-compare/`: speech-to-text comparison (test C); reference, not app code
- `journal/`: optional weekly build notes
- `Intent.md`, `Plan.md`: class kit files; their content lives on the Product Page (pointers only)
- `SPONSOR_MEMO.md`: class template; the final memo is written here (due Dec 14)
- `.env.example`: required environment variables (real keys go in `.env`, never committed)
- Deploy: Render serves `prototype/` from `main`. Auto-deploy doesn't fire; run Manual Deploy after each merge.

## 4. Non-Negotiable Engineering Rules
1. **Plan before coding:** Before touching multiple files, propose a brief plan and wait for approval.
2. **Small batches:** Make small, focused changes that can be reviewed and explained by a human in a single Pull Request.
3. **Explainability:** Avoid unnecessary abstractions or dependencies. Help the human builder understand the main components, what changed, why it matters, what could break, and how it was checked.
4. **Verify changes:** Run relevant checks. For a reproducible logic bug, use a failing test to demonstrate the fix when practical. Record manual checks and known limitations; follow the selected Build 4 evaluation track. Before saying "done," run the app and tell the owner exactly how you verified it.
5. **Zero secrets in code:** Never hardcode API keys, tokens, or credentials. Always read from environment variables (`.env`) and update `.env.example` when new variables are needed.
6. **Stop when looping:** If a fix fails twice in a row, stop, summarize what failed, and ask the human before trying a third approach.
7. **Review before every commit:** Before any commit, show the owner what will be committed and ask for approval, even when the owner says "commit it." For text the owner wrote or specifically directed, show the exact text diff. For generated or bulk files, a file list plus a summary is enough; flag any changes to existing files, secrets, or public-facing text. The owner can ask for the full diff at any time. **Cadence:** don't propose a commit after every change. Iterate in the working tree (UI, copy and product changes especially); show the whole batch and commit once the owner says "looks right" or "checkpoint," or a working slice is finished. Product calls the owner makes here are fine; record them in HANDOFF.md's dated change notes.
8. **Commits and branches:** Use Conventional Commits (`type: short summary`; types: feat, fix, docs, chore, refactor, test). One logical change per commit. Do build work on a branch named for the build (e.g. `build-1-prototype`) and merge to main through a pull request when it works. Tag the submitted version of each build (`build-1`, `build-2`, ...).
9. **Shrink the ask:** If a task gets big or confusing, stop and propose a smaller working slice before continuing.
10. **Keep the Product Page current:** Keep `docs/index.html` (PRD + build log) up to date. Each weekly build (due Monday noon) gets a build-log entry: what shipped, what broke, what it cost (tokens/API/hosting, hours), and what's next.
