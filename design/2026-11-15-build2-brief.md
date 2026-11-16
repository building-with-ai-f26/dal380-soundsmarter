# Design brief: Build 2 (2026-11-15)

**For:** Claude design session. **Attach:** `HANDOFF.md` (source of truth) and `soundsmarter-research-basis.md` (already in the claude.ai "Building With AI" project; kept private, not in the public repo).
**Deadline:** Plan.md + Build 2 log due Mon Nov 16, 12:00 noon ET. Today is Sun Nov 15.

## How to answer

Return a **list of changes to HANDOFF.md, each with a reason**. Don't rewrite the file. Mark anything you're unsure of as a question for Duncan. Product decisions are Duncan's; propose, don't decide.

## Where things stand

- Build 1 shipped: prompt → record (browser) → Deepgram Nova-2 (`filler_words=true`) → count of "um" + "uh". Live demo on Render.
- Accuracy so far: Nova-3 caught 0 of 5–8 fillers. Nova-2 with the browser's noise suppression turned off catches about 4 of 5–6. **It still undercounts.**
- Leading filler: the "uhh"/"umm" at the very start of every take is missing from both the count and the transcript. Cause unknown (browser clipping, speech before recording is live, or Deepgram dropping an opening disfluency).
- Filler detection accuracy is the riskiest assumption (PRD). Build 2 is meant to test it.

## Question 1: how do we get an accurate um/uh count?

**Update 2026-11-15, decided by Duncan:** speech-to-text moves to **CrisperWhisper 2.0** (verbatim mode). He tried the online demo and it caught everything. Test C still runs (Deepgram Nova-2, CrisperWhisper 2.0, ElevenLabs Scribe v3) for evidence and the build log, but it doesn't decide the choice. What design now needs to answer is in **Question 1b** below. The background on the other options follows.

Options:
- **A. Stay on Deepgram Nova-2** and accept the undercount for now.
- **B. Deepgram + an LLM post-pass on the transcript.** The coding agent's view: this can't recover a filler that the speech-to-text step left out of the transcript, because the text model never hears the audio. It does help with *lexical* fillers ("like", "you know"), which is a separate problem. Challenge this if you disagree.
- **C. A different speech-to-text service that keeps disfluencies:** AssemblyAI (`disfluencies`), CrisperWhisper (open source, verbatim, self-hosted), others you know of (e.g. Rev.ai verbatim, Speechmatics, ElevenLabs Scribe; check what's current).
- **D. An audio-native model that listens to the clip** (HANDOFF currently ranks this as a side experiment: not reproducible, no per-word anchor).
- **E. Train or fine-tune our own** (e.g. on Switchboard). Likely out of scope for the class timeline.

Evidence found 2026-11-15 (the vendor's own benchmark, so biased): CrisperWhisper 2.0's model card reports **disfluency F1** (how reliably fillers get written down without inventing extras) on the Nyra Verbatim Speech Benchmark: CrisperWhisper 2.0 Pro 93.5, CrisperWhisper 2.0 87.8, ElevenLabs Scribe v2 79.2, Microsoft MAI-Transcribe-1.5 77.5, Deepgram Nova-3 37.8, AssemblyAI Universal-3 Pro 30.5. Nova-2 isn't listed. CrisperWhisper's license is **non-commercial research only**: fine for the class, a blocker for a paid product unless licensed. ElevenLabs Scribe v2 is the best-ranked commercial API.

Proposed way to decide: **test C** from the HANDOFF protocol. Run the same 5 hand-counted recordings through Deepgram Nova-2 (current baseline), CrisperWhisper 2.0 (local, free) and ElevenLabs Scribe v2 (commercial API); AssemblyAI is optional given its ranking. Compare each against Duncan's hand count (fillers caught, fillers missed, false fillers, leading filler caught yes/no). The coding agent is preparing this now.

Asks:
1. Is the option list missing anything that's current and worth testing?
2. Is 5 recordings × 3 services enough for Build 2? What should the recordings contain (e.g. one that opens with a long "uhh", one with soft ums, one with "um" used as a real word)?
3. What counts as "good enough" to pick a service (e.g. ≥90% of hand-counted fillers, zero false fillers)?

## Question 1b: what moving to CrisperWhisper means

- **How we call it: Nyra's hosted API** (decided 2026-11-15), not self-hosted. `POST https://api.nyra-labs.com/v1/audio/transcriptions`, model `crisperwhisper-v2`. Same shape of integration as Deepgram today (send the file, get JSON back), so the Render demo keeps working with no GPU. Prepaid wallet, minimum $5 top-up; **$0.90 per audio hour**, so a 60 s take costs ~$0.015.
- **What comes back:** a `verbatim` transcript (keeps fillers, repeats, cut-offs), an `intended` transcript (the fluent version), word timestamps for both, and an `alignment` list that labels every verbatim token as `match`, `filler`, `repetition`, `disfluent` (false start), `cutoff`, `correction` or `sound`. The app can count fillers from these labels instead of matching spellings.
- **License.** The open-weight models are non-commercial research only. The terms for the paid API still need checking: does a paying API customer get commercial use? Fine for the class either way.
- **Speed.** Unknown until test C. If a take takes more than a few seconds, does that change the UI (e.g. play the take back while it's analyzed, which the loop already has as step 3, Listen)?
- **Bonus.** The `alignment` labels (repetition, disfluent, cutoff, correction) cover the **Hitches** metric (restarts, repeats, false starts) without an LLM. Should hitches move earlier in the roadmap?
- **Deepgram's role.** Drop it, or keep it as a fallback?

## Question 2: the leading filler

Test C will show whether any service catches the opening "uhh" in a saved file. If all of them miss it, suspect the browser recording. If some catch it, suspect the Deepgram model. Is there a better way to isolate the cause? Does Build 2 prep time need a fallback (e.g. take the first sound from the audio energy rather than the first transcribed word)?

## Question 3: research basis → HANDOFF

`soundsmarter-research-basis.md` (drafted Nov 9 in design review) proposes 7 HANDOFF changes that were never merged. Recommend which to accept now. Note the gap: the doc supports "listeners rate a filled pause as less confident than a silent one" (Brennan & Williams 1995, secondary). It does **not** directly support "fillers make you sound less smart." Christenfeld (1995), "Does it hurt to say um?", is the direct test and is unread. How should the PRD state the premise until that paper is read?

## Question 4: Build 2 scope, given the deadline

The roadmap lists for Build 2: real stack (web + Python + SQLite), saved session records, speaking rate + prep time, pauses + filler-to-pause ratio, LLM classification of lexical fillers, PostHog, start hand-labeling 10–15 takes. That's a lot for one day. Propose a cut: what must ship by Monday noon (Plan.md + the smallest real local version + PostHog), and what moves to Build 3?

## Question 6: numbers, not AI text; and the fear of public speaking

**Decided by Duncan 2026-11-15:** minimize AI-generated text feedback. Give the user numbers. A numbers-first look is a core design element, deliberately away from the "AI slop" look. Context: Duncan tried Yoodli (the nearest competitor). It drops fillers rather than counting them, and its feedback reads as generic AI text.

**Conflict to resolve:** HANDOFF's finished loop, step 6 (Recommendation), has an LLM write vocabulary suggestions, delivery notes and one recommendation per take; Proposed decision 10 says "narration comes from the LLM." What survives? For example: does the LLM still classify lexical fillers ("like" as filler vs. verb) but write no prose? Is the one recommendation per take a fixed, templated line driven by the numbers (e.g. the metric that moved most) rather than generated text? Propose changes to the loop, the Ideas-considered table and the Decisions list.

**The persuasion question (chewier, later builds):** public speaking is one of the most common fears. How does a numbers-first app convince someone, in a small digestible way, that they can sound more confident and impressive? Starting material, not decisions:
- Ease the fear first: Savitsky & Gilovich (2003) found speakers overestimate how visible their nervousness is ("illusion of transparency"), and telling them so improved their speeches and lowered anxiety. Verify before using publicly.
- A visible win within ~3 minutes: three short takes, filler count falling from take 1 to take 3.
- Small and safe: 30 s, no audience, low-stakes prompts, daily reps.
- One thing at a time.
- Hearing your own before/after.

Ask: what does a numbers-first results screen look like (which numbers, in what order, compared to what), and how does it carry encouragement without generated prose? Build 4's user-test track is where this gets tested with real people.

## Question 5: Plan.md answers

Draft short answers for Plan.md sections 1 (riskiest part + how Build 2 tests it) and 2 (architecture), based on your answers above. Duncan will edit.
