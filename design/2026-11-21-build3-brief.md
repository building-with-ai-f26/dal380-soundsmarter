# Build 3 brief

*Design review, 2026-11-21. Owner's statement of Build 3, with the design that follows from it. Items marked **Decide** are the owner's to settle before the coding agent starts.*

## What Build 3 does (owner, 2026-11-21)

1. Establishes a **baseline disfluency map** for each user: what kind of disfluency the user produces under different prompt types.
2. Shows **trends** across repeated use.
3. Is built to ask: **does awareness of a personal speech tendency drive change, and if so, how?**

The prompt engine is the most important part. The app is not held to a clinical standard.

This replaces the Build 3 roadmap row (acoustic features, one recommendation per recording). Acoustic features move later. No recommendation line.

## What the uploaded studies add (all four read in full)

- **Beattie & Bradbury (1979)**, *J. Psycholinguistic Research* 8(3). 20 students, 5 per group, nine 2-minute story-continuation trials: 2 baseline, 5 with feedback, 2 after feedback stopped. Signalling "poor" at each silent pause of 600 ms or more cut pause count, but filled hesitation rose, mostly repetitions (+104%); fillers and phrases like "I mean" and "you know" fell. Story quality ratings did not change. The authors' reading: total hesitation is set by the task; the speaker changes its form. When feedback stopped, pausing returned to baseline within the first 2-minute trial. No subject worked out what the light was tied to. Control groups also drifted across trials (speech rate up 9.8%, filled hesitation down), so practice alone moves the numbers.
- **Lee & Papafragou (2027)**, *Cognition* 278. Four experiments, 120 listeners per rating; roughly 20-second clips of real spontaneous speech with four um/uh each, against the same clips with the fillers cut out. No effect on how competent, warm or trustworthy the speaker seemed as a person. Small effects within the conversation: less trustworthy, less ready, less certain, and listeners slightly less likely to ask that speaker again. Listeners did not rate the filler versions as less fluent. Only um/uh were tested; silent pauses, repetitions and words such as *like* were not.
- **Xu et al. (2026)**, *Folia Phoniatrica et Logopaedica*. Review of 69 studies: seven broad categories (repetition, prolongation, revision, pause, filler, incomplete production, non-verbal behavior), 155 subtypes, 368 definitions. Pause thresholds in use run from 150 ms to over 2 s. No agreed standard exists, so the app has to state its own definitions and keep them fixed.
- **Corley, MacGregor & Donaldson (2007)**, *Cognition* 105. 12 listeners. Words following "er" were processed differently and recognised slightly more often later (66% vs. 62%). Fillers do something for the listener; not a production finding.

Consequences for the design:

1. **Measure every category together.** If feedback on one kind of disfluency moves it into another, a single number will show a false improvement. The map and the trend both show the whole set.
2. **"How" has a specific first hypothesis:** substitution (form changes, total holds), not reduction.
3. **Baseline has to be feedback-free**, or awareness starts at the first recording and there is nothing to compare against.
4. **A trend is not proof of an awareness effect.** Practice moves the numbers too. Drift inside the baseline phase is the only available estimate of the practice effect.
5. **Does it last when the numbers are hidden?** In the 1979 study it did not.

## The map

Rows are the review's categories, limited to what the transcription already returns:

| Row | Source | Unit |
|---|---|---|
| Fillers (um, uh, er, erm, ah) | filler label | per 100 words; seconds |
| Repetitions | repetition label | per 100 words |
| Revisions | correction label | per 100 words |
| Cut-offs (incomplete) | cutoff label | per 100 words |
| Mid-sentence pauses, 450 ms or more | word timestamps + punctuation | count; seconds; share of answer |
| Sentence-end pauses, 450 ms or more | same | count; seconds |
| Total hesitation | fillers + mid-sentence pauses | share of answer |

Also stored per recording: speaking rate, articulation rate, prep time. Not in Build 3: prolongation and non-verbal sounds (need audio), and the word tiers from the 2026-11-21 word-list proposal (need classification; the stored transcript lets them be computed later).

Columns are prompt types. Each cell is the user's mean over the recordings of that type, with the lowest and highest value beside it.

Store the full transcription response for every recording. Every metric can then be recomputed when a definition changes.

## The prompt engine

**Bank.** `design/2026-11-21-prompts-draft.csv`: 60 text prompts, 15 in each of four families, all marked `draft`. Nothing ships until the owner marks it `approved`.

| Family | Task | Openness | Precedent |
|---|---|---|---|
| recount-2 | Tell the story of a specific event | guided | Standard clinical discourse protocol (personal narrative) |
| procedure-2 | Explain how to do something | guided | Same protocol (procedural discourse) |
| opinion-2 | Argue for or against a statement | open | Christenfeld 1995 stimulus; task-type studies |
| continue-1 | Continue a story from an opening line | open | Beattie & Bradbury 1979 used exactly this task |

Image and audio families follow in a later build; they need stimuli.

**Tags stored with every recording:** prompt id, family, task, mode, openness, beats, words on screen, position in the session, and any prompts skipped before it.

**Selection rules.**
1. Baseline: 8 recordings, 2 per family, families interleaved in random order, never two of the same family in a row.
2. After baseline: families rotate so counts stay even; prompt chosen at random within the family.
3. A user never sees the same prompt twice until the family is exhausted.
4. Skip gives another prompt from the same family and is recorded.
5. Trends compare within family only.

**Phases.**
1. *Baseline (recordings 1–8):* after each recording the user gets playback and transcript, no numbers.
2. *Map:* shown once, when baseline is complete.
3. *Tracking (recording 9 on):* each result shows the map rows for that recording beside the user's baseline for that family, and whether each value is inside or outside the baseline range.

## Needed underneath

- Stored session records and a way to know the same user came back. The demo host keeps no files between restarts, so this needs a hosted database; SQLite on the current host will not persist.
- A one-line consent notice that transcripts and timings are stored.

## Decide

1. Baseline with no numbers for 8 recordings: accept, shorten (4 recordings, 1 per family), or keep numbers on from the start and give up the before/after comparison?
2. The four families, and the 60 draft prompts: approve, cut or reword.
3. Demo-code visitors: keep the current instant-results page for them, with the baseline flow only for signed-in users?
4. Whether to add a later "numbers hidden" stretch to test whether a change lasts.
5. Audio: store it (needed later for acoustic features) or transcripts and timings only?
