# SoundSmarter: design context for Claude Cowork (2026-11-15)

Read alongside `HANDOFF.md` (product source of truth) and `design/2026-11-15-build2-brief.md` (open questions). This file covers look, feel and the practical constraints a design has to fit.

## How to hand work back

- **Propose, don't decide.** Product decisions are Duncan's. Return a list of changes to HANDOFF.md with a reason for each, not a rewritten file.
- **Mockups:** static HTML + CSS files are welcome (they can sit in `design/mockups/`). The coding agent (pi) integrates them into the app. Don't edit `prototype/` directly.
- Mark anything uncertain as a question for Duncan.

## What this is (for scale)

- An MBA class project ("Building with AI", NYU Stern), five weekly builds, Nov 9 → Dec 7, 2026. Build 2 is due Mon Nov 16, noon ET. Builds 3-5 are where design lands; the UI may become the focus of the later builds.
- One builder (Duncan), using a coding agent. Simple beats clever: every part has to be explainable by Duncan.
- Audience: young professionals, fluent English speakers, who get nervous speaking under pressure (interviews, presentations, talking to executives). Not language learners.
- Where people will see it:
  - **Live demo:** https://soundsmarter-demo.onrender.com/ (Render free tier; invite codes; ~30 s cold start on first load; must work on phone browsers).
  - **Product Page / PRD:** https://building-with-ai-f26.github.io/dal380-soundsmarter/ (`docs/index.html`, GitHub Pages; class-required template, so keep restyling light there).
  - **Duncan's site:** https://duncanlindsay.com will link to it from its "projects" row. The app should feel like it belongs next to that site.
- Repo is **public**: no private material in mockups.

## Design direction (Duncan's calls)

1. **Numbers, not AI text.** The user sees measured numbers. No generated paragraphs of feedback. AI is used behind the scenes only to *classify* (e.g. "like" as a filler vs. a verb), never to write coaching prose. The numbers are the heavy design element.
2. **No AI-slop look.** Avoid:
   - bento-box grids of cards
   - purple/blue gradients, glassmorphism, glowing borders
   - sparkle ✨ icons, robot/brain imagery, "AI coach" chat bubbles
   - emoji bullet lists, confetti, gamified badges
   - generic SaaS font stacks (Inter everywhere), pill-shaped everything
   - vague encouragement copy ("Great job! You're on your way!")
3. **Colour: yellow and lime green** as the accents (Duncan's starting idea; propose exact values). Watch contrast: yellow or lime *text* on a light background fails accessibility. Use them as fills, highlights, bars or markers, with dark text on top.
4. **Font: the same as duncanlindsay.com.** Archivo Narrow, weight 700 (Google Fonts), fallback "Helvetica Neue", Arial, sans-serif. Duncan chose it after the condensed bold type on the back cover of the *Randy Newman Live* LP.
5. **Reference: duncanlindsay.com's look.** Barely off-white background `#fdfcfa`, near-black text `#222`, thin 1px rules, a near-invisible grey row divider `#f0efec`, plain underlined links, a faint text-shadow for analog softness (`0 0 0.6px rgba(0,0,0,0.5)`). Spare, typographic, a printed-record-sleeve feel more than an app dashboard.
6. **Tone of copy:** brutally minimal, plain, specific. Duncan writes or approves all user-facing words. The intro screen text in HANDOFF is his, verbatim.

## The screens (current app, Build 1)

One page, three states:
1. **Intro:** "SoundSmarter listens to you talk!" + 4 numbered steps + Start. Must not say that fillers are counted.
2. **Prompt + recording:** prompt text shown large; recording starts at reveal; Stop greyed out until 30 s; hard stop at 60 s; Skip any time. HANDOFF prefers a soft fill bar, **no numeric countdown** (numbers on screen while speaking cause rushing).
3. **Result:** filler total ("um" + "uh") with a breakdown, plus the transcript. "N takes left" for invite-code users.

Coming (see HANDOFF Metrics spec + roadmap): prep time (framed neutrally, never a penalty), speaking rate, pauses, filler-to-pause ratio (headline metric), hitches (repeats, false starts, cut-offs), later pitch and loudness tied to specific words, trends across takes.

## The design problem worth the most thought

How does a numbers-first app convince a nervous speaker, in something small and digestible, that they can sound more confident and impressive? Public speaking is one of the most common fears. Starting material (brief Q6): speakers overestimate how visible their nerves are (illusion of transparency); a visible win within ~3 minutes (fillers falling across three short takes); low stakes (30 s, no audience); one thing at a time; hearing your own before/after. Key question: what does the results screen look like (which numbers, in what order, compared to what), and how does it carry encouragement **without** generated prose?

## Technical constraints that shape the design

- **Front end:** one plain HTML file with vanilla JavaScript, no framework, no build step. Served by a small Python (FastAPI) server. Keep designs buildable in plain HTML/CSS: no component libraries, no heavy animation libraries.
- **Mobile matters:** testers use phone browsers. Design mobile-first; the mic-permission prompt is the first hurdle.
- **Recording:** browser MediaRecorder. Browser noise suppression is deliberately off (it erased soft "um"s), so recordings can be noisy.
- **Waiting:** after Stop, audio goes to speech-to-text (CrisperWhisper 2 via Nyra's API) and back. Expect a few seconds; speed not yet measured. Design a waiting state; the finished loop's "Listen" step (play the take back before showing numbers) could fill that gap.
- **What the data can support:** every word comes with start/end timestamps and a label (filler, repetition, false start, cut-off, correction, sound). So the UI can highlight fillers *in the transcript* or on a timeline, mark pauses by length, and point at specific words. Pitch/loudness (Praat, Build 3) will add per-phrase values aligned to words.
- **Hosting:** Render free tier; it sleeps when idle, so the first visit has a ~30 s cold start. A friendly "waking up" state helps.
- **Analytics:** PostHog (Build 2) will track funnel events (start, record, finish, skip). Design shouldn't depend on it.
- **No accounts yet:** invite codes, 3 takes per code. Trends across sessions need persistence (Build 2-3); multi-user accounts are an open question.
