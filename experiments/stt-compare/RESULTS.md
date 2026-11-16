# Test C results (2026-11-15)

Same 4 phone recordings (m4a, no browser involved) sent to three speech-to-text services; counts compared to Duncan's hand count. Run: `uv run python compare.py`. Total wall time ~25 s for all 12 calls.

- Deepgram Nova-2, `filler_words=true`
- CrisperWhisper 2.0 via Nyra API (`crisperwhisper-v2`, verbatim track)
- ElevenLabs Scribe v3, `no_verbatim=false`

| Take | What it tests | Hand (um+uh) | Deepgram | CrisperWhisper | Scribe v3 |
|---|---|---|---|---|---|
| 1 | Opens with a filler | 6 (4+2) | 2 | **6** | **6** |
| 2 | Soft, small ums | 9 | 8 | **9** | **9** |
| 4 | Normal answer (ideal day prompt) | 3 | **3** | **3** | **3** |
| **Total, takes 1, 2, 4** | | **18** | **13 (72%)** | **18 (100%)** | **18 (100%)** |
| 3 | 1 real filler + 5 "um"s said as a word ("the ums", "an um") | 1 | 3 | 5 (labels 8 as filler) | 4 |

## Findings

1. **Deepgram undercounts; CrisperWhisper and Scribe v3 matched the hand count exactly** on the three normal takes (n = 3 takes, 18 fillers: small sample).
2. **Leading filler: it's the Deepgram model, not the browser.** Take 1 was a phone recording, and Deepgram still dropped the opening "uh"s (both "uh"s missing). CrisperWhisper and Scribe caught them.
3. **Prep time error:** on take 1 Deepgram put the first word at 4.00 s; CrisperWhisper at 2.00 s, Scribe at 2.12 s. Measuring prep time with Deepgram would have overstated it by 2 s.
4. **No service tells a filler "um" from "um" used as a word** (take 3). CrisperWhisper labelled all 8 um/uh mentions as fillers, and turned "clear M sound" into "[UM] sound" (an invented filler). Scribe's text was closest to what was said. This is a classification job (AI for classification is approved); it's also a rare case in real speech.
5. **CrisperWhisper's extra labels work:** take 3 also came back with 1 repetition ("a a"), 2 cut-offs ("y- y-") and 1 correction. That's the Hitches metric with no extra step.

## Caveats

- One speaker, 4 takes, one phone. Test A/B (browser vs. phone) not run.
- Scribe v3 tied CrisperWhisper on counts. CrisperWhisper's advantages are the per-token labels (hitches) and the published timing accuracy; Scribe's are a commercial license and slightly better text on take 3.
- Raw responses are in `results/` (not committed: personal voice data).
