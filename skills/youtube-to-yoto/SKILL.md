---
name: youtube-to-yoto
description: End-to-end workflow for turning a YouTube playlist into a Yoto MYO (Make Your Own) playlist on a Yoto Player children's audio device, with per-track 16×16 pixel-art icons rendered on the Player's LED matrix. Use this skill whenever the user mentions Yoto, MYO cards, Yoto Player, a 16×16 LED audio player, or wants to put YouTube content (cartoons, audiobooks, podcasts, lectures) onto a children's audio device — even if they don't say "Yoto" by name. Also trigger for any pipeline that needs custom audio + tiny icons + a metadata server upload, or when the user asks how to automate Yoto card creation instead of clicking through the app.
---

# YouTube → Yoto MYO Playlist

Turn any YouTube playlist into a Yoto MYO playlist with custom per-episode 16×16 pixel-art icons. The Yoto Player ships with paywalled cards from the Yoto Store; MYO ("Make Your Own") cards are blank NFC cards you can program with your own audio. This skill automates the program-it-via-API path.

## What you produce

- One Yoto MYO card (≤ 100 chapters) populated with the user's chosen audio
- Each chapter has its own 16×16 pixel-art icon shown on the Player's LED matrix when the track plays
- Icons depict the most representative concrete object in each story so a non-reading toddler can recognize episodes

## First-run mode (MANDATORY)

When the user invokes this skill and there is NO existing `upload_cache.json` co-located with the MP3 download directory for this playlist, you MUST:

1. Detect this is the user's first run on THIS playlist. Check for `<mp3_dir>/upload_cache.json` where `<mp3_dir>` is whatever output directory the user specified for `download_playlist.sh` — NOT the current working directory. A cache from a different playlist must not suppress the demo prompt for a new one.
2. Tell the user, verbatim or close to it: "I recommend we run the first 3 episodes through the full pipeline first. You'll then put the card on the Player and verify it actually plays — if anything's wrong (OAuth, card binding, audio format), we'll catch it on 3 episodes instead of wasting an hour on the full set. Want to do this? (y/n)"
3. If user says yes: pass `--first 3` to `download_playlist.sh` and run all 5 phases on those 3 episodes.
4. After upload, ask: "Card uploaded. Insert it into your Player and tell me what happens. Did it play correctly?"
5. ONLY after explicit "yes it works" / "y" / equivalent: ask "Continue with the remaining N episodes?" and run the rest.
6. If user explicitly opts out ("no, do all of them"): honor that, but warn once: "Heads up — troubleshooting a 100-episode failure takes much longer than the 5-min demo."

## OAuth bootstrap (conversational)

When `YOTO_CLIENT_ID` is unset OR `~/.yoto-tokens.json` does not exist, follow `references/oauth-setup.md` and walk the user through it inside the conversation. Do not just dump the doc URL — open dashboard.yoto.dev for them (`open https://dashboard.yoto.dev/` on Mac) and step them through it.

## Cost confirm (MANDATORY before Phase 4)

Before dispatching sprite-generation SubAgents, count unique subjects (N) and tell the user:

> "About to dispatch N Opus SubAgents to design N pixel-art sprites.
> - On Claude Pro/Max: no extra charge, uses ~X% of your hourly quota.
> - On pay-per-token API: roughly $Y at current Opus pricing.
> Continue? (yes / no / show me 3 sample sprites first)"

Wait for explicit confirmation. Never silently run the full batch. If user picks "3 samples first": pick 3 representative subjects, dispatch only those 3 SubAgents, show the output, then re-prompt for the rest.

## Prerequisites

Run once to install everything the pipeline needs:

```bash
bash scripts/bootstrap.sh
```

This installs (idempotently): Homebrew packages (yt-dlp, ffmpeg, whisper-cpp, node), pip packages (Pillow, requests, optionally aiomqtt), the Whisper `large-v3-turbo` model (1.5 GB), and the `pixel-art` skill via `npx skills add`.

You also need a Yoto OAuth `client_id` from https://dashboard.yoto.dev/ — the skill walks you through getting one (see OAuth bootstrap above).

## The pipeline (5 phases)

Phases are independent. Each writes to disk so any step can be re-run without redoing the others.

### Phase 1 — Download

```bash
scripts/download_playlist.sh <YOUTUBE_PLAYLIST_URL> <out_dir> [--first N] [--lang LANG]
```

Produces `<out_dir>/{video_id}.mp3` plus `<out_dir>/_playlist.json` (metadata). On first run, pass `--first 3` per the first-run mode above.

### Phase 2 — Transcribe first 3 minutes (only if titles aren't enough)

Skip Phase 2-3 if YouTube titles already describe the episode concretely (e.g. "Chapter 5: The Talking Cat"). Run them when titles are abstract or in a language whose Whisper transcription is needed to identify what each episode is about.

```bash
scripts/transcribe_all.sh <mp3_dir> <transcript_dir>
```

Uses local `whisper-cli` with Metal acceleration on Apple Silicon. ~15× realtime for the turbo model. 3 minutes is enough — episodic kids' content states the subject up front. Language auto-detected.

### Phase 3 — Pick one drawable subject per episode

Each episode reduces to ONE concrete English noun naming a physical object a 2-year-old recognises. Examples: `rhinoceros beetle`, `birthday cake`, `school bus`. Not verbs, not abstractions, not character names.

Dispatch ~20 Sonnet SubAgents in parallel — each gets a batch of ~14 episodes and writes `{vid: subject}` JSON. See `references/subagent-prompts.md` for the exact prompt template. Merge outputs into `subjects.json`, then dedupe to `unique_subjects.json`.

### Phase 4 — Generate 16×16 pixel-art sprites

**Run the cost-confirm gate above FIRST.** Then for each unique subject, design one 16×16 RGBA PNG. **Always load the `pixel-art` skill first** — without it sprite quality drops noticeably.

Dispatch ~20 Opus SubAgents in parallel, each handling ~9 subjects. Each agent must:
1. Load the `pixel-art` skill (read its SKILL.md + references)
2. Author each sprite with the char-grid DSL (one char per pixel → palette → RGBA)
3. Save as `pixel_subjects/{subject-slug}.png`
4. Self-check via PIL silhouette read

See `references/icons-and-cover.md` for design rules, palette guidance, and the per-subject SubAgent prompt template.

### Phase 5 — Upload to Yoto

```bash
export YOTO_CLIENT_ID=your-client-id
python3 scripts/yoto_auth.py     # one-time OAuth Device Flow
python3 scripts/yoto_upload.py --subjects subjects.json --sprites pixel_subjects --mp3 <mp3_dir> --title "My Playlist" --go
```

`yoto_upload.py` does three sub-phases with `upload_cache.json` resume support:
- **A — icons** (parallel-8): POST each PNG to `/media/displayIcons/user/me/upload`, save returned `mediaId`
- **B — audio** (parallel-4): POST → PUT → poll `/transcoded`, save `(transcodedSha256, duration, fileSize)`
- **C — playlist**: assemble chapters, POST `/content` with `cardId` (update) or without (create new)

If neither `--csv` nor `--playlist-json` is given, the script reads `<mp3_dir>/_playlist.json` directly.

Exact endpoints, payload schemas, and the OAuth Device Flow are documented in `references/yoto-api.md`. **Read that file before modifying the upload script** — there are several fields that, if wrong, make `POST /content` return `200` but cause the Player to silently fail to play audio. See `references/pitfalls.md` for the short list.

Bind the playlist to a physical blank MYO card by scanning the card on the Player while the Yoto app is open. **The NFC bind step is necessarily manual** — there is no API for it.

## Cover image

Use Yoto's default cover URL in `metadata.cover.imageL`:

```
https://cdn.yoto.io/myo-cover/star_grapefruit.gif
```

The user can change the cover from the Yoto app after upload. The chapter `display.icon16x16` icons (Phase 4) are what shows on the Player's LED matrix during playback.

## Hard limit: 100 tracks per playlist

`POST /content` returns `400 "track count is limited to 100"` above that. If the user has > 100 episodes, either pick the top-N or split across multiple cards.

## Critical pitfalls

The Yoto API server validates payloads loosely (most malformed POSTs still return `200`), but the Player firmware is strict. These mistakes will not error at upload time — they only manifest when the user inserts the card and audio doesn't play.

| Pitfall | What to do |
|---|---|
| `track.format` must be `"opus"`, not `"mp3"` | Yoto re-encodes everything to Opus/Ogg. Declaring `mp3` makes the Player abort after ~0.5s per track. |
| `track.duration` is in **seconds**, not ms | Schema says seconds; if you multiply by 1000, the Player skips through tracks. |
| `track.overlayLabel` is required at TRACK level | Not just chapter level. Omitting it makes the Player advance through tracks without playing. |
| `track.channels` must be set | `"stereo"` or `"mono"` — detect from source MP3 via `ffprobe -show_entries stream=channels`. |
| `metadata.media` must total over all chapters | `{duration: sum_seconds, fileSize: sum_bytes}`. The Player uses this to scrub the whole playlist. |
| Icon upload sends raw bytes, NOT multipart | `Content-Type: image/png` with the raw PNG body. Multipart form-data is rejected. |
| Don't use `#000000` in icons | The Yoto LED matrix doesn't render pure black cleanly. Use `#181818` as the darkest tone. |
| Force YouTube language at extraction | yt-dlp `--extractor-args "youtubetab:lang=$LANG;youtube:lang=$LANG"` — otherwise titles come back partially auto-translated. |
| Modern YouTube needs a JS runtime for yt-dlp | `--js-runtimes node`. Without it: 429 errors, missing fields. |
| Always extract subjects from **title + transcript**, never title alone | Abstract titles say nothing about what to draw; transcripts reveal the concrete subject. |

`references/pitfalls.md` has the longer-form explanations with symptoms and detection commands.

## Diagnosing playback issues via MQTT

If the playlist uploads but the Player misbehaves (tracks skip, cloud icon stuck, audio doesn't start), subscribe to the Player's MQTT events:

```bash
python3 scripts/mqtt_log.py
```

Authenticates via existing token; needs `family:devices:view` scope. Subscribes to `device/{deviceId}/data/events` and prints every event live. The crucial field is `trackLength` — it should match your `duration` (in seconds). If `trackLength` is 4 with tracks advancing rapidly, your `track.format` is almost certainly wrong.

## Tips

- **Start with the first-run demo (3 episodes)** before bulk runs. Verify they play on a physical Player before scaling up.
- **Cache aggressively.** `upload_cache.json` makes a crashed run resumable without re-uploading anything.
- **Dedupe subjects before generating sprites.** N episodes often → far fewer unique subjects. Saves SubAgent time and quota.
- **Hand-craft 16×16, do not downscale AI-generated art.** Use AI for inspiration (composition/palette), then author the final 16×16 by code.

## Reference files

- `references/yoto-api.md` — every endpoint, OAuth flow, exact payload schema
- `references/icons-and-cover.md` — 16×16 design rules, palette, SubAgent prompt for sprite generation, cover image notes
- `references/subagent-prompts.md` — prompt templates for Phase 3 (subject extraction) and Phase 4 (sprite generation)
- `references/pitfalls.md` — the things that pass server validation but break the Player
- `references/oauth-setup.md` — conversational OAuth walkthrough for first-time setup
