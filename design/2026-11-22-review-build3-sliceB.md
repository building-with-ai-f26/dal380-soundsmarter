I reviewed the 8 commits from `43734ee` to `e02939d` and ran the tests (52 pass). I also ran `metrics.py` on the four real CrisperWhisper results from test C, which are only on your machine. No files were edited.

**Fixed as claimed:** a broken secret key now stops a recording before transcription is paid for, and the three Slice A findings this work targeted are resolved (unusable audio no longer saved, stored language now meaningful, version numbers now match what's stored). The approvals in decision 29 match the CSVs exactly: 206 approved, and every denied or held-back id is not approved. All 42 uploaded images are square.

The checks against the CSVs and image files aren't proof that `prompts.sql` was pasted into dev, or that the images were uploaded to the bucket.

## High: arithmetic in `prototype/metrics.py`

1. **Sentence ends are missed wherever a filler sits at the boundary.** The code decides "end of sentence" by looking for `.` `?` `!` on the spoken words. The speech service often drops the full stop exactly when a filler follows. In test C it gives "chimneys [UM] I" and "sound [UM] A" with no full stop, while its tidied text has "chimneys." and "sound.". Sometimes the full stop comes back as a separate "correction" entry. Three of the four test C recordings show 0 sentence-end pauses. Effect:
   - mid-sentence pauses, and the Account column "mid-sentence pauses per 100 words", are overcounted;
   - sentence-end pauses are undercounted.

   The code follows decision 25's wording, but not its purpose.

2. **The "corrections" count mostly measures punctuation.** In test C, the correction entries are full stops the service inserted, not anything the speaker corrected. It matches decision 23 literally, but the stored number means little.

## Medium: arithmetic needing your decision

3. **Back-to-back fillers count as separate hesitations.** "[UH] [UM]" counts as 2 filled hesitations. Decision 26 says a filler plus its adjacent pause is *one* hesitation, but is silent on clusters. Test 1 has several such pairs and a filled share of 0.40; counting each cluster once would lower it.
4. **Filled share leans toward fillers.**
   - Fillers count wherever they occur, including between sentences.
   - Silent pauses count only mid-sentence.
   - The by-time version also adds sentence-end pauses that touch a filler to the filled time.

   Combined with finding 1, filled share comes out higher than the substitution it is meant to measure.
5. **Articulation rate mixes two bases.** It takes filler words out of the word count but leaves filler *time* in the speaking time. So more "um"s lower the articulation rate, which muddies the "pausing versus dragging syllables" reading in the Metrics spec. This follows the definition literally.
6. **Speaking rate counts cut-off fragments ("st-") and repeated words as words.** Also literal to "non-filler words", but worth a deliberate decision.
7. **The too-fast/too-slow check uses a different count from "speaking rate".** It counts all words, fillers included; decision 25 defines speaking rate as non-filler words. Under that definition your own test 1 recording (about 0.75 words a second) would be rejected; under the code's count it passes at about 0.9. The code's choice looks safer, but HANDOFF doesn't record it. Test 1 also sits close to the 0.8 limit.

## Medium: other code

8. **A rejected attempt wipes the record of earlier skips.** A `rejected` event resets the list in `records.skipped_before`. When the user re-records and sends, the saved row loses the skips made before the rejected attempt. The reset rule was already there; this branch is the first to write `rejected` events, so it now takes effect.
9. **A rejection that arrives after the user has moved on loses the prompt.** It is already marked seen and is never offered again. Decision 21 says the user records the same prompt again.
10. **Turning off "force English" affects demo visitors too.** They get no language check. Test C was run with English forced, so nobody has checked whether auto-detect changes CrisperWhisper's filler output or misreads accented English. Your Gaps line covers only the non-English case.
11. **More prompts can be wasted on a failed serve** (this worsens Slice A finding 8). The prompt is recorded as served before the browser loads its pictures. If a picture fails to load, the prompt is lost, and there is no timeout while waiting.
    - Every image prompt also costs up to 3 extra requests to check its files.
    - If prod's bucket is empty when the seed is pasted, one prompt request can cycle through many image prompts before landing on a text one.
12. **The key check only catches 401 and 403.** A 404, a server error or a timeout from Supabase lets the request through, so the transcription is paid for and then the save fails. It also adds one extra database round trip per recording. The test's fake database assumes a working key returns 400; real Supabase was never tried with a broken key.

## Low

13. **Spend cap in `generate_images.py`.** Real spend so far is $1.77, so the cap was not at risk, but the tracking can drift:
    - Regenerating a deleted image removes the old cost from `generated.csv`, so later runs undercount.
    - A request that times out or fails after OpenRouter billed it is never counted.
    - The "no cost reported" stop saves the image but doesn't log it, so a re-run pays for it again.
    - The cap only lives in that CSV. A credit limit on the OpenRouter key would be the real safeguard.
    - Describe items 7–12 also make a landscape version that's never used, and the docstring still says "two models".
14. **Missing timestamps can distort filled time.** `(end or 0) - (start or 0)` adds a whole timestamp, or a negative, if either is missing.
15. **The word list counts cut-offs as words.** Stripping the hyphen turns "like-" into "like" in the word-form counts.
16. **Baseline cells look the same whatever they're based on.** In families with images, each baseline cell is one recording; elsewhere it's an average of two. Nothing on the table says which.
17. **The too-few-words message says "keep talking for at least 30 seconds".** The user already had to, because Stop is disabled until 30 s.
18. **A re-recorded attempt's prep time isn't comparable.** The user has already seen the prompt, and nothing on the saved row marks it as a second try.
19. **Testing prod creates a real account there.** `check_direct_write.py --prod` can create a test account in prod with a consent row, which then stays. It also loads the dev `.env` (indirectly) even in `--prod` mode.
20. **HANDOFF loose ends:**
    - "Rule 1" is still an open question, though decision 29 settled it.
    - The text argue prompts still show no header on the Send/Discard screen (the earlier review's finding 9; only image prompts were fixed).
    - `HANDOFF.md` has uncommitted edits (owner notes after testing Slice B) that this review didn't cover.

## Untested paths, beyond your Gaps line
- What the speech service returns for language when it isn't told English (a missing value passes the check).
- The sentence-end and filled-share arithmetic against real transcripts; the tests use clean, hand-built ones.
- A broken key against real Supabase.
- A picture failing to load in the browser.
- The sound-level check on Safari; if the browser can't read the audio back, the check is silently skipped.
- `check_direct_write.py --prod` hasn't been run.

**Summary: 20 findings (2 high, 10 medium, 8 low), none fixed.** The high ones and findings 3–7 are judgement calls on definitions; findings 3–7 belong under "Questions for design" rather than as fixes.
