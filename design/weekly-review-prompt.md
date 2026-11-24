# Weekly codebase review: the prompt

Run in a fresh pi with no memory of the build, from the repo folder, once a week:

```
pi -p "$(sed -n '/^---$/,$p' design/weekly-review-prompt.md | tail -n +2)"
```

Save the reply as `design/YYYY-MM-DD-weekly-review.md`. First written 2026-11-23, from that day's review.

---
Review this whole repository as it stands on the current branch. Change nothing.

Read: HANDOFF.md (product source of truth), AGENTS.md, README.md, SECURITY.md, docs/index.html (the Product Page and PRD), NOTES.md, every file under prototype/ (code, migrations, tests), the newest files in design/ (briefs and earlier reviews, the last weekly review included), experiments/stt-compare/RESULTS.md, the git log since the last weekly review, and the session logs in ~/Desktop/projects/logbook/ that mention SoundSmarter since then. Run `uv run pytest` in prototype/ and report the count.

Report, in plain language for an owner who is not a programmer, under these headings:

1. Scope against execution: where what the product says it is (landing page, PRD, HANDOFF Scope) differs from what the app does.
2. Plan against execution: what HANDOFF, the roadmap, the task list or AGENTS.md's rules said would happen and did not. Include process rules that slipped.
3. Advice not taken: advice from a design brief, an earlier review or the owner's own earlier notes that was not followed. Say who gave it, what was done instead, and what it costs.
4. Where the agent was inaccurate or vague: wrong code, numbers that cannot be reproduced, claims stronger than the evidence, stale statements in files an agent reads first, and findings from earlier reviews that were neither fixed nor recorded.
5. Security: anything new since SECURITY.md was last updated.
6. What held up: published numbers and claims you checked and found correct.

Rules:
- Give every finding an ID (S1, P1, A1, G1, C1...). If the last weekly review used an ID for the same finding, reuse it and say what changed.
- For each finding give the file and line or the dated source, and say whether you confirmed it yourself or are repeating an earlier report.
- Check the last weekly review's findings one by one: fixed (which commit), decided, or still open.
- Say what you did not check (the production database, Render, the live site).
- Never print the contents of .env or any key.
- End with the decisions the owner has to make, as a short list.
