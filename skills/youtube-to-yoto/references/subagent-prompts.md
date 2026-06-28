# SubAgent prompt templates

Verbatim prompts to dispatch in parallel during Phase 3 (subject extraction) and Phase 4 (sprite generation). Tested at ~20 SubAgents in parallel each. Each SubAgent gets a batch file produced by splitting the work.

## Phase 3 — subject extraction (Sonnet)

Goal: reduce each episode to ONE concrete English noun naming a drawable physical object.

```
## Task
Extract a single English pixel-art subject for each cartoon episode in your batch.

## Context
We have N episodes of a children's cartoon. Each will be uploaded to a Yoto Player as a track. Each track gets a 16×16 pixel-art icon shown on the device's LED matrix. A 2-year-old toddler will look at these icons to recognize/pick the episode.

So: your output (one English noun per episode) becomes the subject drawn as a 16×16 pixel art icon. It must be a single, concrete, physical object that a 2-year-old can recognize.

## Your batch
Read /path/to/batches/batch_NN.json — JSON array of {vid, title, transcript_file}.

For each entry: read transcript_file, combine with title, output ONE English noun naming a concrete physical object.

## Selection rules
- Concrete physical object, drawable as a 16×16 sprite
- Good: snail, birthday cake, rhinoceros beetle, octopus, cherry blossom, school bus, umbrella, apple
- BAD: verbs, abstract concepts, character names, places, emotions, relationships
- If the title is concrete (「奇怪的生日」 → birthday cake), title alone may suffice
- If the title is abstract (「爸爸的朋友」), use the transcript to find the actual subject (the friend may turn out to be a rhinoceros beetle → output "rhinoceros beetle")
- Transcripts may contain Whisper transcription errors (獨角仙 → 獨角蟹, 蛤蜊 → 隔離, etc.). Use context to deduce the real word.
- If multiple plausible subjects, pick the most central + visually distinct
- Fallback when nothing concrete fits: "star"

## Output
Save to /path/to/output/batch_NN.json as flat JSON {vid: "subject"}. Lowercase English nouns, 1-3 words. Do not skip any vid.
```

Dispatch each agent with its batch number injected. Merge outputs into `subjects.json`, then `unique_subjects.json` (dedupe).

## Phase 4 — sprite generation (Opus)

Goal: one 16×16 RGBA PNG per unique subject, following pixel-art mastery rules.

```
## Task
Design one 16×16 pixel-art sprite per subject in your batch.

## Your batch
Read /path/to/sprite_batches/batch_NN.json — a JSON array of subject strings.

## Hard requirements per sprite
- Exactly 16×16, RGBA PNG, alpha channel
- Save as /path/to/pixel_subjects/{slug}.png where slug = subject.lower().replace(' ', '-')
- Darkest tone is #181818, never #000000 (Yoto LED matrix limitation)
- Background fully transparent (alpha 0); no checkerboard, no near-white background
- Subject fills 70-85% of the frame

## Design quality
Load the `pixel-art` skill (Skill tool → "pixel-art") and read its SKILL.md + references first. Apply:
- Hue-shifted color ramps (warm highlight, cool shadow)
- Selective outlining (selout) using the darkest tone
- Top-left light source, consistent across the batch
- 2-pixel minimum for any visible feature
- 3/4 isometric view for low-wide subjects (cars, beds, shoes, etc.)
- Silhouette test: fill the sprite with one color in your head — is the subject still identifiable?

## Process
1. Plan the subject: what's the iconic angle/pose? What's the silhouette?
2. Author with the char-grid DSL: one character per pixel → palette → render to PNG with PIL
3. After saving, re-read the PNG with PIL and visually verify it's correct (silhouette, palette, transparency)
4. If a sprite turns out ambiguous, iterate before moving on

## Subjects in your batch
(listed in batch_NN.json)
```

After all SubAgents finish, build a PIL grid of all sprites at 64× scale so you can eyeball the full set at once. Iterate on weak ones (re-dispatch a small batch with stronger guidance) before uploading.
