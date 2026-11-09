# AGENTS.md — Coding Agent Operating Manual

> Give this file to your coding agent and check that it is using these instructions. Keep the stack, commands, and ground rules current.

## 1. Project Overview
- **What this repo builds:** SoundSmarter records 30–60 seconds of extemporaneous speech and returns measured feedback (filler count, speaking rate, prep time) so speakers can track how they improve.
- **Who it's for:** Young professionals, native English speakers, who speak under pressure (executive conversations, interviews, presentations) and whose nerves show up as fillers and rushed starts. Not for language learners.
- **The one job:** give a speaker measured feedback on *how* they speak, take after take.
- **Primary user & core workflow:** prompt → record → transcribe → metrics. Full PRD in `docs/index.html`.
- **Tech stack:** Build 1: throwaway local prototype using Deepgram speech-to-text (filler words on, word timestamps). From Build 2 (current lean, not set in stone; open to discovering better tools): web client (browser MediaRecorder), Python backend (FastAPI), SQLite. Details in HANDOFF.md → Technical choices.

- **Product source of truth:** [`HANDOFF.md`](./HANDOFF.md). Read it before building. Product decisions are made in design review and by the owner; the agent merges approved changes, builds, and never changes a product decision on its own. Put anything that needs deciding under "Questions for design" at the end of HANDOFF.md.

## 2. Commands
All commands run from the `prototype/` folder (`cd prototype`). Needs `DEEPGRAM_API_KEY` in the repo-root `.env`.
- **Install dependencies:** `uv sync`
- **Run locally:** `uv run uvicorn server:app --reload`, then open http://localhost:8000
- **Run deterministic tests:** `uv run pytest`
- **Run model evals:** none yet (Build 4)

## 3. Non-Negotiable Engineering Rules
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
