# Stimuli to source

*2026-11-21. What the image and audio families need. Every stimulus gets a row in the stimulus table: id, kind, file, title, creator, year, source URL, license, credit line.*

## Rules for every image

- Public domain or a license that allows reuse in a public app. Record the license.
- Landscape orientation, at least 1600 px wide.
- No readable text in the image (diagrams may carry part numbers).
- Nothing violent, sexual or distressing.

## 1. Single scenes: 30 (yields 90 prompts)

Wanted: several people doing different things at once, at least two actions in progress, ideally one thing going wrong.

Where: open-access collections of the Metropolitan Museum, Rijksmuseum, National Gallery of Art and Art Institute of Chicago. Check each image's own license statement before use.

Candidates to look up (all by artists dead more than a century; confirm the specific image file is open):

- Pieter Bruegel the Elder: Children's Games; Netherlandish Proverbs; The Peasant Wedding; The Hunters in the Snow; The Fight Between Carnival and Lent
- Hendrick Avercamp: Winter Landscape with Ice Skaters
- Jan Steen: The Merry Family; The Feast of Saint Nicholas
- William Hogarth: single plates such as Beer Street
- William Powell Frith: The Railway Station; The Derby Day
- Georges Seurat: A Sunday on La Grande Jatte
- Pierre-Auguste Renoir: Luncheon of the Boating Party; Bal du moulin de la Galette
- Gustave Caillebotte: Paris Street; Rainy Day; The Floor Scrapers
- Edgar Degas: A Cotton Office in New Orleans
- Edouard Manet: A Bar at the Folies-Bergere
- Winslow Homer: Snap the Whip; Breezing Up
- George Caleb Bingham: The Jolly Flatboatmen
- Carl Larsson: household scenes
- Utagawa Hiroshige and Katsushika Hokusai: street and travel prints

That list covers about 25. The rest can be own photographs of busy places (a market, a kitchen mid-meal, a playground), which also adds present-day scenes.

## 2. Pairs: 10 pairs, 20 images (yields 10 prompts)

Two things of the same kind, unbranded, photographed alike. Own photos are simplest.

Two breakfasts; two beaches; two apartments or living rooms; two chairs; two bicycles; two city streets; two desks; two picnic spots; two coats; two front doors.

## 3. Diagrams: 12 (yields 12 to 24 prompts)

Line drawings of everyday mechanisms or assemblies. Drawings from expired patents are the easiest open source; search a patent database by object name. Avoid any drawing that shows a brand name.

Zipper; paper clip; safety pin; can opener; corkscrew; umbrella; stapler; mousetrap; pencil sharpener; bicycle; toaster; folding chair.

Retail assembly instructions (for example flat-pack furniture) are copyrighted and should not be used.

## 4. Picture sequences: 8 (yields 8 prompts)

Four to six frames, one causal chain, no words. This is the hardest to find ready-made and open. Options: draw or generate them, or stage and photograph them (spilled drink, missed bus, burnt toast). Suggest leaving this family for a later build if time is short.

## 5. Soundscapes: 12 clips of 20 seconds (yields 12 prompts)

Own phone recordings are free and owned. Commercial music and film audio cannot be used.

Cooking a meal; washing dishes; yard work with a mower or rake; a train platform; a cafe; a playground; a street market; rain on a window with traffic; a workshop with hand tools; a sports game from the sidelines; packing a suitcase; a kitchen at breakfast.

## 6. Voiced audio: 25 clips

Scripts are in `2026-11-21-audio-stimuli-draft.csv`: 15 stories (each recorded twice, full and cut) and 10 claims. At a normal reading pace the stories run about 22 to 30 seconds. Vary the voices; one voice for everything makes the audio prompts blur together.

## Totals if everything is sourced

| Source | Stimuli | Prompts |
|---|---|---|
| Text | none | 215 |
| Single scenes | 30 | 90 |
| Pairs | 20 | 10 |
| Diagrams | 12 | 12 to 24 |
| Sequences | 8 | 8 |
| Soundscapes | 12 | 12 |
| Stories | 15 | 30 |
| Claims | 10 | 10 |
| **Total** | **107** | **about 390** |
