# SubAgent prompt templates

Verbatim prompts to dispatch in parallel during Phase 3 (subject extraction) and Phase 4 (sprite generation). Tested at ~20 SubAgents in parallel each. Each SubAgent gets a batch file produced by splitting the work.

## Phase 3 — subject + clean title extraction (Sonnet)

Goal: per episode, extract TWO things — (a) ONE concrete English noun for the sprite, (b) a CLEAN target-language story title to show on the Yoto Player.

The raw YouTube title is almost always noisy — channel/season prefix (「卡通【可愛巧虎島】」, `Season 12:`), trailing hashtags (`#幼兒 #卡通 #動畫`), bracketed metadata, occasional translation cruft. The Yoto Player has limited screen real estate and a parent/child will see this title in the app. Showing raw YouTube titles is the bug fixed in 1.0.1 — **always run this extraction step before upload**.

```
## Task
For each cartoon episode in your batch, extract TWO things:
  1. subject  — ONE English noun naming a drawable physical object for the 16×16 sprite icon
  2. title    — the CLEAN story-title in the episode's native language, ready to show on the Yoto Player

## Context
We're publishing episodes to a Yoto Player (toddler audio device). The user will scroll through a list of episode titles in the Yoto app. The title must read as a real story name — short, complete, in the original language — NOT the YouTube SEO blob.

## Your batch
Read /path/to/batches/batch_NN.json — JSON array of {vid, title, original, transcript_file}.
- `title` may already be partially cleaned by the splitter; `original` is the raw YouTube title.
- Always work from `original` to clean the title, and use the transcript when the title is too abstract to identify the subject.

For each entry: read transcript_file, combine with original title, output BOTH fields.

## Title-cleaning rules
- Strip channel/season prefix patterns: 「卡通【XXX】」, 「第N季【XXX】」, 「Season N:」, 「XXX |」, 「【XXX】」 → keep only the actual story name
- Strip trailing hashtags entirely: `#幼兒 #卡通 #動畫 #親子 #育兒` → drop
- Strip emoji decoration if it's not part of the story (📺, 🎵, etc.)
- Strip noisy bracketed metadata at the end ((Full Episode), (HD), [中文版]) — but keep brackets that ARE part of the story (「夏天爬山大冒險（下）」 — the （下） denotes Part 2)
- DO NOT translate. Preserve the original language (Chinese stays Chinese, English stays English).
- DO NOT rewrite the story name. Keep what the uploader chose; only remove the noise around it.
- Examples:
  * 「第12季【可愛巧虎島】神祕的祕密寶盒 #幼兒 #卡通 #動畫」 → `神祕的祕密寶盒`
  * 「卡通【可愛巧虎島】夏天爬山大冒險（下） #育兒」 → `夏天爬山大冒險（下）`
  * 「Season 13 of "Cute Shimajiro Island": The Rules of Dorothy's House #Toddler」 → `The Rules of Dorothy's House`
  * 「Bluey S03E08 "The Decider" 720p [official]」 → `The Decider`
- If the cleaned title is empty or you can't isolate the real story name, use the transcript's first descriptive sentence (truncate to ≤30 chars).

## Subject-selection rules
- Concrete physical object, drawable as a 16×16 sprite
- Good: snail, birthday cake, rhinoceros beetle, octopus, cherry blossom, school bus, umbrella, apple
- BAD: verbs, abstract concepts, character names, places, emotions, relationships
- If the title is concrete (「奇怪的生日」 → birthday cake), title alone may suffice
- If the title is abstract (「爸爸的朋友」), use the transcript to find the actual subject (the friend may turn out to be a rhinoceros beetle → output "rhinoceros beetle")
- Transcripts may contain Whisper transcription errors (獨角仙 → 獨角蟹, 蛤蜊 → 隔離, etc.). Use context to deduce the real word.
- If multiple plausible subjects, pick the most central + visually distinct
- Fallback when nothing concrete fits: "star"

## Output
Save to /path/to/output/batch_NN.json as JSON `{vid: {"subject": "<english noun>", "title": "<clean story title>"}}`. Lowercase English nouns 1-3 words. Title in native language, ≤60 chars, no leading/trailing punctuation. Do not skip any vid.
```

Dispatch each agent with its batch number injected. Merge outputs into `subjects.json` (which now contains both fields per vid). The new format is `{vid: {subject, title}}`; `yoto_upload.py` accepts this and falls back to the legacy `{vid: "subject"}` format for older runs.

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
