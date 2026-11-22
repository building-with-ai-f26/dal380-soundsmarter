# Prompts in conflict with rule 1 (one task per prompt)

*2026-11-22. For the owner's prompt review. Nothing here is decided.*

Rule 1 (guidelines §B3): "One task per prompt. A prompt that asks for a description and then an opinion is two tasks and cannot be compared with either." HANDOFF decision 27 overrides rules 2 and 10, not rule 1.

This list is the coding agent's reading of the 215 live drafts in `2026-11-21-prompts-text-draft.csv`, taking rule 1 strictly. The five tasks are the five families: describe, narrate (recount), argue (opinion with reasons), invent, explain (procedure).

## Clear conflicts (13): the second part is a different task

| ID | Family | What it also asks for |
|---|---|---|
| `des-t-01` | describe | an opinion (what you loved or disliked). The owner's own wording. |
| `des-t-13` | describe | an opinion (the one thing that needs fixing) |
| `des-t-14` | describe | an invention (swap one thing in the view) |
| `des-t-15` | describe | an opinion (an honest review) |
| `des-t-25` | describe | an explanation (what it takes to get there) |
| `des-t-30` | describe | an opinion (what makes it better than the others) |
| `des-t-38` | describe | a recount (where it came from) |
| `des-t-39` | describe | a recount or invention (what was happening outside the frame) |
| `des-t-41` | describe | an opinion (which app earned its spot, which should go) |
| `des-t-46` | describe | a reason (why it got the spot) |
| `nar-t-36` | narrate | a description (the boss) before the recount (one shift) |
| `inv-t-52` | invent | an explanation (how you'd make the dish). The owner's own wording. |
| `inv-t-64` | invent | a description of a real route |

## Borderline (23): a judgment call

**Choose, then describe (6).** The first part is a choice with no reasons asked for; the describing is still the main job.
`des-t-04`, `des-t-08`, `des-t-10`, `des-t-23`, `des-t-24`, `des-t-43`

**Describe, with a pull toward something else (11).**

| ID | The pull |
|---|---|
| `des-t-07` | inference (what a stranger would figure out about you) |
| `des-t-09` | advice (what to tell a first-timer) |
| `des-t-19` | memory and judgment more than description (fought over, dangerous) |
| `des-t-20` | a spending choice |
| `des-t-22` | a choice (the one thing you'd rescue) |
| `des-t-28` | an explanation (which item needs explaining) |
| `des-t-29` | evaluation (an honest sale listing) |
| `des-t-33` | a hypothetical choice of instrument |
| `des-t-34` | what you do with it |
| `des-t-42` | explaining a game to someone who's never played |
| `des-t-47` | evaluation (where it still lets the cold in) |

**Recount, ending on a verdict or a description (5).**

| ID | The pull |
|---|---|
| `nar-t-17` | description (the room) |
| `nar-t-28` | opinion (what made it better than the rest) |
| `nar-t-30` | judgment (whose fault it was) |
| `nar-t-46` | verdict (was it worth it) |
| `nar-t-47` | description (what you looked like) |

**Invent, with a pull toward procedure (1).** `inv-t-59` (how you'd rehearse the act)

## Argue: several answers under one "Give at least two reasons." (7)

Not a mix of tasks, but each asks for more than one position, so "two reasons" is unclear.

| ID | Asks for |
|---|---|
| `arg-t-03` | how much to tip, and when to leave nothing |
| `arg-t-09` | a ranking of four seasons |
| `arg-t-11` | days in the week, and hours in the day |
| `arg-t-14` | three arrival times (dinner, flight, interview) |
| `arg-t-26` | two lists (theater movies, home movies) |
| `arg-t-29` | an age, and which chores |
| `arg-t-49` | the best seat, and what it is worth |

## No conflict found

- Explain (15): one task each.
- Invent story snippets (`inv-t-01` to `inv-t-25`): one task each, and already set aside for reshaping.
- The other hypotheticals (`inv-t-51`, `inv-t-53` to `inv-t-75` except the two above): describing an imagined thing is still inventing.
- The remaining describe and narrate prompts.

## A related note

The `beats` column in the CSV is no longer accurate (for example `inv-t-65` and `inv-t-74` ask three questions but are marked 2). It should be recounted, or dropped, once rule 1 is settled.
