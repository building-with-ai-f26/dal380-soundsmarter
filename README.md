# SoundSmarter

> **One-line pitch:** For young professionals who speak under pressure: answer a short prompt out loud and see how many filler words you used, so you can measure how you speak and improve take after take.

- **Builder:** Duncan Lindsay (`@duncanlindsay`)
- **Pod:** 10
- **Product Page & Living PRD:** https://building-with-ai-f26.github.io/dal380-soundsmarter/
- **App:** runs locally through Week 4; cloud URL in Build 5.

## What it does (Build 1)
Prompt → record (30–60 s in the browser) → transcribe with Deepgram → count "um" and "uh".

## Run it locally
Needs Python and [uv](https://docs.astral.sh/uv/), plus a Deepgram API key.

1. Copy `.env.example` to `.env` and add your `DEEPGRAM_API_KEY`.
2. `cd prototype && uv sync`
3. `uv run uvicorn server:app --reload`, then open http://localhost:8000
4. Tests: `uv run pytest`

## Repository map
| File / folder | Purpose |
| --- | --- |
| [`docs/index.html`](./docs/index.html) | Product Page: PRD and weekly build log |
| [`HANDOFF.md`](./HANDOFF.md) | Product source of truth (decisions, roadmap) |
| [`AGENTS.md`](./AGENTS.md) | Rules and commands for coding agents |
| [`prototype/`](./prototype/) | Build 1 throwaway prototype |
| [`Plan.md`](./Plan.md), [`SPONSOR_MEMO.md`](./SPONSOR_MEMO.md) | Class templates for Build 2 and the final memo |
| [`tests/`](./tests/) | Verification guidance (Build 4) |

Keys live in `.env`, which git ignores. Never commit them.
