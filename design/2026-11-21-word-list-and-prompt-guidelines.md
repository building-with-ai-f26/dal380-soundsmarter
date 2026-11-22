# Word list and prompt guidelines

*Design review, 2026-11-21. Status: proposal. Nothing here is a product decision until the owner moves it into HANDOFF.md.*

Reading status of every source named here: **abstract or table of contents only**, unless marked *(part 1/2, read)*, which refers to the research-basis documents. Items marked *(from memory)* were not checked at all this round. Treat all of it as leads until the full texts are read.

---

## Part A. Words to detect

### A1. Categories

Organized by what the word is doing, because that is how the research divides them. "Detect" column: **F** = safe to count by form alone; **C** = same form has ordinary uses, needs classification; **A** = needs the audio, not the transcript.

| # | Category | What it does | Members (candidate list) | Detect | Research tradition | Listener evidence |
|---|---|---|---|---|---|---|
| 1 | Filled pauses | Signal a delay | um, uh, er, erm, ah, mm, hmm | F | Clark & Fox Tree 2002 *(part 1, read)* | Mixed; delay length matters more than the filler *(part 2)* |
| 2 | Non-word sounds | Delay without a word | tongue click, lip smack, audible inhale, sigh, throat clear | A | Counted as a target in Mancuso & Miltenberger 2016 | None found |
| 3 | Quotative | Introduces reported speech or thought | be like ("he was like"), be all, go/goes ("she goes"), be kind of like | C | D'Arcy 2017; Tagliamonte & D'Arcy 2004 *(part 2, secondary)* | Attitude studies exist (Dailey-O'Cain 2000; Hesson & Shellgren 2015), unread |
| 4 | Discourse *like* | Marks focus, looseness or a pause point | clause-initial "like, I went"; clause-medial "it was, like, huge"; clause-final "it was cold, like" | C | D'Arcy 2017 separates marker, particle and sentence adverb | Same as 3 |
| 5 | Approximator | Makes a quantity or category loose | like ("like five"), about, around, or so, -ish, roughly, something like | C | D'Arcy 2017 (approximative adverb *like*) | None found specific to these |
| 6 | Hedge | Lowers commitment to the claim | kind of / kinda, sort of / sorta, I think, I guess, I feel like, maybe, probably, pretty much, more or less, in a way, I would say, I suppose, a little bit, somewhat | C (kind of, sort of, I think) / F (kinda, sorta, I guess) | "Powerless language": Erickson et al. 1978; Hosman 1989; Hosman & Siltanen 2006 | **Strongest of any category.** Hedges rated lowest on speaker evaluation (Hosman & Siltanen 2006) |
| 7 | Disclaimer | Hedge as a whole phrase, usually up front | I'm not sure but, I could be wrong, I don't know / I dunno, this might be a dumb idea, if that makes sense, does that make sense | F | Powerless-language literature lists disclaimers | Grouped with hedges; not isolated in what was seen |
| 8 | Listener-directed marker | Invites the listener to fill in or agree | you know, you see, you know what I mean, right?, okay?, yeah?, tag questions (isn't it, don't you think) | C (you know, right) / F (you know what I mean) | Fox Tree & Schrock 2002 (*you know* invites inference); tag questions in powerless-language work | Tag questions tested with hedges (Blankenship & Holtgraves); *you know* in Hosman's "prototypically powerless" message |
| 9 | Repair marker | Announces a fix to what was just said | I mean, or rather, that is, sorry, no wait, let me rephrase, what I'm trying to say | C (I mean) / F (rest) | Fox Tree & Schrock 2002 (*I mean* forewarns adjustment); Levelt 1983 editing expressions *(from memory)* | None found |
| 10 | Opener | Starts a turn or a new point | so, well, okay, alright, now, look, listen, anyway, yeah so | C | Schiffrin 1987 *(from memory)*; Biber et al. 1999 name *well* among the commonest *(part 2, secondary)* | None found |
| 11 | General extender | Vague list-ender | and stuff (like that), and things, and everything, or something, or whatever, or anything, and so on, and all that, et cetera, blah blah blah | F | Overstreet 1999; Overstreet & Yule 2021; Biber et al. 1999 | None found |
| 12 | Placeholder | Stands in for a word not retrieved | thing, stuff, thingy, whatever it's called, what's the word, whatchamacallit | C (thing, stuff) / F (rest) | Word-finding literature *(from memory)* | None found |
| 13 | Intensifier | Turns the claim up | really, very, so, super, totally, absolutely, definitely, extremely, incredibly, literally | C (so, literally) / F (rest) | Powerless-language literature; Tagliamonte on intensifiers *(from memory)* | **Not penalized.** Rated most positively in Hosman & Siltanen 2006; a recent study found boosters did not raise perceived knowledge |
| 14 | Stance adverb and minimizer | Frames the claim as frank, simple or obvious | actually, basically, honestly, frankly, obviously, clearly, essentially, to be honest, just, simply | C (just, actually) / F (rest) | Biber et al. 1999 stance adverbials *(from memory)* | None found |
| 15 | Stalling phrase | Buys time with a full phrase | let me think, that's a good question, how do I put this, what else, at the end of the day, long story short | F | None found; closest is filled-pause work | None found |
| 16 | Chaining connective | Strings clauses without ending a sentence | and, and then, and so, but, so (mid-turn) | C | Schiffrin 1987 *(from memory)* | None found |

Already measured, not words: repetitions, cut-offs and corrections (CrisperWhisper labels).

Standard uses that are never counted: *like* as verb, preposition, conjunction, noun, adjective or suffix (D'Arcy lists seven "unremarkable" uses); *so* as degree word or "so that"; *well* as adverb; *right* as direction or "correct"; *just* meaning "a moment ago" or "fair"; *kind of* in "what kind of".

### A2. Three tests for including a category

1. **Cost.** Is there listener evidence that it lowers how the speaker is judged? (Yes: hedges, probably disclaimers and tag questions. Mixed: filled pauses. Attitudes documented but unread: *like*. No or positive: intensifiers. Unknown: everything else.)
2. **Countable.** F, C or A above. C categories cannot be shown as a number until classification accuracy has been checked against hand labels (build 4).
3. **Stable.** Does it occur often enough in 30–60 s to mean anything in one recording? Only filled pauses, *like*, and probably hedges do. The rest need totals across several recordings, like the crutch-word rule already in HANDOFF.

A fourth consideration: categories 8 and the quotative are dialogue and storytelling devices. In a monologue to a screen they depend heavily on prompt type (quotatives will appear in personal recounts and almost nowhere else), so their rates are only comparable within prompt type.

### A3. Proposed decision

- **Tier 1, counted for everyone, the "fillers" number:** category 1. Add er, erm, ah to um and uh.
- **Tier 2, tracked for everyone, shown as separate lines, never added into the filler number:** *like* in its non-standard uses (categories 3, 4 and approximator *like*, with quotative reported on its own line), *you know*, *I mean*, hedges (*kind of*, *sort of*, *I think*, *I guess*, *I feel like*), general extenders. Reason: these are the ones with either a published rate (*like*, *you know*, *I mean*: Laserna et al. 2014, part 2, secondary) or listener evidence (hedges).
- **Tier 3, off unless the user picks it at intake:** categories 9, 10, 13, 14, 15, plus *just*.
- **Custom word.** The user types any word or phrase. Counted by exact match, labelled "counts every use". Cheapest way to serve an objective the lists miss.
- **Not now:** 2 (needs audio), 12 and 16 (no evidence, hard to classify).
- Intensifiers stay in tier 3 with a note that the evidence does not show a cost.

### A4. Intake question

One optional screen. Proposed copy (app voice, no second person):

> **Words to watch (optional)**
> Um, uh and similar sounds are always counted.
> ☐ Like  ☐ You know / I mean  ☐ Hedges (kind of, sort of, I think, I guess)  ☐ Vague endings (and stuff, or something)  ☐ Openers (so, well, okay)  ☐ Intensifiers (really, very, literally)  ☐ Actually / basically / honestly / just
> Another word or phrase: ________

Checked items move to the top of the results page. Unchecked tier 2 items are still stored, so a profile can show them later.

---

## Part B. Prompt guidelines

### B1. Two axes: task and mode

**Task** is the kind of speaking asked for. **Mode** is what the user is given to respond to. Every prompt has exactly one of each.

| Task | What the speaker must do | Research precedent | Modes that fit |
|---|---|---|---|
| Personal recount | Tell a specific remembered event | AphasiaBank free-speech "important event"; Foster & Skehan 1996 personal-information task | text |
| Scene description | Say everything happening in one picture | Cookie Theft (BDAE); Berube et al. 2019 updated picture with content-unit norms | image |
| Sequence narration | Tell the story shown in a short picture sequence | AphasiaBank Broken Window, Refused Umbrella | image sequence |
| Retell | Retell a story just heard or read | AphasiaBank Cinderella; Pear film retellings (Chafe, via Clark & Fox Tree, part 1); retelling of orally presented stories (Doyle et al. 1998, unread) | audio, text |
| Procedure | Explain how to do something step by step | AphasiaBank sandwich task | text, image |
| Explanation | Explain how or why something works | Lectures in Schachter et al. 1991 *(part 1, secondary)* | text, image |
| Opinion | Take a position and give reasons | Christenfeld 1995's stimulus was an argued opinion *(part 2, read)*; argumentation vs. narration in task-type studies; Foster & Skehan decision-making task | text, audio |
| Interpretation | Say what a picture or clip means, or what happens next | Goldman-Eisler's description vs. interpretation of cartoons *(from memory, to verify)* | image, audio |
| Referential description | Describe one item so a listener could pick it out from similar ones | Tangram task in Bortfeld et al. 2001 *(part 1, read)*; Map Task | image, audio |
| Invention | Continue a story from a given opening, or make one up | No elicitation precedent found yet | text, image, audio |
| Estimation | Reason aloud to a number or a choice | No discourse precedent found; nearest is question-answering latency (Smith & Clark 1993, part 2, secondary) | text |

What the research says about task differences, so far: task type changed most linguistic measures in healthy adults as well as adults with aphasia (Stark 2019, 84 controls); planning time raised fluency and its effect depended on task (Foster & Skehan 1996, second-language speakers); fillers tracked the number of options open to the speaker more than difficulty (part 1 §3). None of these measured fillers or pauses by task in fluent adults speaking alone to a screen. That comparison is what the app's own data would add.

Audio as a mode has the thinnest precedent: heard-story retell is established; describing a sound is not something found in this literature.

### B2. Tags every prompt carries

- `task`, `mode` (above)
- `family`: the template it was written from (see B4). Trends compare within family.
- `openness`: closed (content is supplied: scene, sequence, retell), guided (a specific memory or procedure), open (opinion, invention). This is the variable the options hypothesis predicts on.
- `beats`: 1, 2 or 3 parts in the prompt text.
- `words_on_screen`: reading time is inside prep time, so prep time is only comparable between prompts of similar length.
- `topic`: e.g. food, work, childhood, travel, media, objects, places.
- `stimulus_id` for image or audio prompts.
- `status`: draft, approved, retired. Only the owner approves.

### B3. Writing rules

1. One task per prompt. A prompt that asks for a description and then an opinion is two tasks and cannot be compared with either.
2. 30 words or fewer on screen. Fixed opening verb per task ("Describe", "Explain how", "Retell", "Argue for or against") so the task is recognised at a glance.
3. Answerable by any fluent adult without special knowledge and without preparation. Specific beats general: "the last meal cooked for someone else" over "a favorite food". (Owner's Nov 9 lesson: "learn any skill overnight" was dropped as too hard to start.)
4. No yes/no questions; no prompt answerable in one sentence.
5. Nothing that pulls for health, money, politics, religion, trauma or other people's private lives.
6. No mention of fillers, pace or performance in the prompt.
7. Images: owned or public-domain only; one scene; no text in the image; 8–15 nameable things or actions, including at least two actions in progress and one thing going wrong. Each image is stored with its checklist of content units, so content scoring remains possible later.
8. Image sequences: 4–6 frames, one causal chain, same rules.
9. Audio: owned or public-domain only; 15–25 s; a short story or a spoken opinion for retell and opinion tasks. Stored with its transcript. The task line appears when the clip ends, and prep time runs from that moment.
10. Each family keeps a fixed number of beats. Mixing two- and three-beat prompts in one family makes rate and length drift for reasons unrelated to the speaker.

### B4. Families and counts

A family is one template with a slot. Example, personal recount, two beats: "Tell the story of the last time [EVENT]. Say what happened first and how it ended."

Proposed first bank, about 250 prompts:

| Family | Task / mode | Count | Role |
|---|---|---|---|
| Recount, 2 beats | personal recount / text | 40 | core |
| Opinion, 2 beats | opinion / text | 40 | core |
| Scene | scene description / image | 30 | core |
| Procedure | procedure / text | 25 | explore |
| Explanation | explanation / text | 25 | explore |
| Sequence | sequence narration / image sequence | 15 | explore |
| Interpretation | interpretation / image (reuses scene images) | 30 | explore |
| Story retell | retell / audio | 15 | explore |
| Opinion response | opinion / audio | 10 | explore |
| Invention | invention / text | 20 | explore |

**Core** families feed the baseline and the trend line, so they need enough prompts that a regular user does not see repeats. **Explore** families feed cross-task comparison only. Interpretation reuses the scene images on purpose: same picture, describe vs. interpret, is the cleanest contrast available. The 12 existing prompts get tagged and sorted into these families; several mix tasks and would need splitting.

The image and audio families depend on stimuli (about 45 images, 15 sequences, 25 clips), which is the slow part.

### B5. Storage

- Source of truth: a file in the repo (`prompts/prompts.csv`, plus `prompts/stimuli.csv`), reviewed and approved like any other owner-written copy.
- The app loads approved rows into a `prompts` table and a `stimuli` table in the same database as the session records. Each session record stores the `prompt_id`, so every tag is available to every analysis.
- Stimulus files live in storage, not in the public repo, unless their license allows redistribution. `stimuli.csv` records license and credit for each.

### B6. Questions the tags let the data answer

1. Do fillers and mid-sentence pause time rise from closed to guided to open prompts? (Options hypothesis.)
2. Same image, describe vs. interpret: which moves, fillers or pauses?
3. Do quotatives and *like* concentrate in personal recounts?
4. Does prep time scale with words on screen, and what is left after removing that?

---

## Sources to obtain or read in full

- D'Arcy, A. (2017). *Discourse-Pragmatic Variation in Context: Eight hundred years of LIKE*. Benjamins. Chapter 1 and the appendix.
- Hosman, L. A. (1989). The evaluative consequences of hedges, hesitations, and intensifiers. *Human Communication Research* 15(3).
- Hosman, L. A., & Siltanen, S. A. (2006). Powerful and powerless language forms. *Journal of Language and Social Psychology* 25(1).
- Erickson, B., Lind, E. A., Johnson, B. C., & O'Barr, W. M. (1978). Speech style and impression formation in a court setting. *Journal of Experimental Social Psychology* 14.
- Blankenship, K. L., & Holtgraves, T. (2005). The role of different markers of linguistic powerlessness in persuasion. *Journal of Language and Social Psychology* 24(1).
- Fox Tree, J. E., & Schrock, J. C. (2002). Basic meanings of *you know* and *I mean*. *Journal of Pragmatics* 34(6), 727–747. Open copy available.
- Overstreet, M., & Yule, G. (2021). *General Extenders*. Cambridge University Press. Chapter 1.
- Stark, B. C. (2019). A comparison of three discourse elicitation methods in aphasia and age-matched adults. *AJSLP* 28(3), 1067–1083. Open on PMC.
- Foster, P., & Skehan, P. (1996). The influence of planning and task type on second language performance. *Studies in Second Language Acquisition* 18(3), 299–323.
- AphasiaBank protocol description and instructions (talkbank.org), for the exact elicitation scripts.
- Goldman-Eisler, F. (1968). *Psycholinguistics: Experiments in Spontaneous Speech*. For the description vs. interpretation experiments.
