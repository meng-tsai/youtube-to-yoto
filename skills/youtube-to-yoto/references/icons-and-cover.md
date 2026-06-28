# Icons & cover

Two visual artifacts go into a Yoto MYO playlist:

- **Per-chapter `display.icon16x16`** — a 16×16 pixel-art sprite shown on the Player's LED matrix while the track plays. One per unique subject across the playlist. **High visual significance**: this is what the kid looks at to recognize an episode.
- **Playlist `metadata.cover.imageL`** — a single larger image shown in the Yoto app's library tile for the playlist. **Low priority**: the LED matrix never shows it, only the app does, and the user can change it from the app post-upload.

## Cover image — use the default URL

Don't author a custom cover unless the user explicitly asks for one. Use Yoto's stock URL:

```
https://cdn.yoto.io/myo-cover/star_grapefruit.gif
```

That's a free public asset hosted on Yoto's CDN; no upload, no auth, just point at it from `metadata.cover.imageL`. If the user wants a custom cover later, they can change it from the Yoto app on their phone — Settings → tap the playlist → tap the cover → choose from gallery or upload.

If a custom-uploaded cover ever becomes a requirement, Yoto's cover-upload endpoint behaviour wasn't characterised by this skill — research it then.

## 16×16 sprite design

The Yoto Player has a 16×16 RGB LED matrix. Sprites must be RGBA PNG sized exactly 16×16. Compose them by code (one character per pixel mapped through a palette) rather than by downscaling a larger image — at 16×16, every pixel matters and AI-downscaled output muddles the silhouette.

### Always load the `pixel-art` skill first

Without it, sprite quality drops noticeably: flat color steps instead of hue-shifted ramps, no selective outlining, weak silhouettes that all collapse to "blob" at toddler glance.

```bash
npx skills add omer-metin/skills-for-antigravity@pixel-art -g -y
```

Each sprite-generation SubAgent must load `pixel-art` (read its SKILL.md + references) before authoring anything. The skill provides saint11 / Pedro Medeiros techniques.

### Design rules (apply per sprite)

- **Subject fills 70-85% of the 16×16 frame.** Don't center with huge margins.
- **Hue-shifted color ramps**, not flat tone-steps. Red highlight shifts toward warm yellow-pink, red shadow shifts toward cool purple-magenta. Result looks alive instead of plastic.
- **Selective outlining (selout).** The outline is part of the shading, not a sticker. Light-facing edges (top-left in a top-left-light setup) use a mid-warm tone. Shadow-facing edges use the darkest tone.
- **Darkest tone is `#181818`, not pure `#000000`.** The Yoto LED matrix doesn't render pure black cleanly. `#181818` is visually identical and renders correctly.
- **Top-left light source**, consistent across all sprites in a card.
- **2-pixel minimum for any visible feature.** 1px protrusions read as noise; simplify or remove.
- **3/4 isometric view** for low-wide subjects (shoes, beds, cars, sofas). Side profile collapses them all to the same blob silhouette.
- **Silhouette test.** Imagine the sprite filled with one color — would the toddler still recognize it? If not, simplify the pose or change the angle.
- **Background = full transparency.** Save as RGBA. No checkerboard, no near-white pixels — Yoto auto-keys near-white to transparent on upload and can wash out highlights if you're not careful.

### 5-pointed stars don't quite work

A regular 5-point star has 72° angles that don't snap cleanly to a 16×16 grid; you'll always have minor asymmetry. Accept it, switch to a 4-point cross+diagonal, or use a "shooting star" / sparkle alternative.

### Dedupe subjects before generating

Most playlists have far fewer unique subjects than episodes (268 episodes → 187 unique subjects is typical). Slug each subject (`"rhinoceros beetle"` → `"rhinoceros-beetle"`) and generate one sprite per unique slug. Map each chapter's icon by looking up its subject's slug.

## SubAgent prompt template — Phase 4 sprite generation

Dispatch ~20 Opus SubAgents in parallel, each handling ~9 unique subjects. Each agent reads:

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

After all SubAgents finish, build a PIL grid (e.g. 20×N at 64× scale = 320 px per cell) so you can eyeball all sprites at once. Iterate on weak ones.

### Toddler-aesthetics checklist before upload

- Bright saturated colors over muted/realistic palettes
- Subjects readable at arm's length (a kid won't lean in to study)
- No text in sprites (16×16 can't legibly render Chinese characters or English words; the chapter title shows on the Player's display anyway)
- Recurring subjects (food, animals, weather) stay visually consistent if a series repeats them
