**English** · [繁體中文](README.zh-TW.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Español](README.es.md) · [Français](README.fr.md)

# youtube-to-yoto

Turn any YouTube playlist into a [Yoto](https://yotoplay.com/) MYO ("Make Your Own") card playlist with per-episode 16×16 pixel-art icons on the Player's LED matrix.

Built as a [Claude Code](https://claude.ai/code) skill / plugin. Mac-only for v1.

## What this does

You give it a YouTube playlist URL. It:

1. Downloads each video's audio as MP3.
2. Transcribes the first 3 minutes of each (local Whisper, free, no API call).
3. Picks one drawable concrete noun per episode (e.g. `rhinoceros beetle`, `birthday cake`) via Claude SubAgents.
4. Designs a 16×16 pixel-art sprite per unique noun via Claude SubAgents.
5. Uploads everything (audio + sprites + playlist metadata) to your Yoto account.
6. Tells you to tap a blank MYO card on the Player to bind it.

Total wall-clock for ~100 episodes: ~1.5 hours.

## Cost

> Read this **before** you install.

This skill uses Claude SubAgents to design pixel-art icons. Cost depends on **how you're billed for Claude**:

| Billing | What it costs you |
|---|---|
| **Claude Pro / Max subscription** *(recommended)* | $0 extra. SubAgent runs draw from your existing plan quota. A 100-episode playlist typically fits within a Max session. |
| **Pay-as-you-go API key** | ~$0.10–0.15 per unique sprite (Opus). A 100-episode playlist with ~70 unique subjects ≈ **$7–$10**. |
| **Free Claude tier** | Not enough quota — upgrade to Pro before running. |

The skill **always announces estimated cost up front** and asks you to confirm before fanning out SubAgents. Partial progress is cached and resumable.

Details: [docs/COSTS.md](docs/COSTS.md).

## Hardware requirements

| Component | Minimum | Recommended |
|---|---|---|
| macOS | 12 Monterey | 14 Sonoma+ |
| CPU | Intel Mac (3–5× slower) | **Apple Silicon (M1+)** — whisper.cpp uses Metal GPU acceleration; turbo runs ~15× realtime on M1 |
| RAM | 8 GB | 16 GB (Whisper uses 2–3 GB at peak) |
| Free disk | 4 GB | 10 GB |
| Network | Stable broadband | Downloads ~800 MB for 100 episodes; uploads ~800 MB to Yoto |
| Wall-clock time | — | ~1.5 hours for a 100-episode first run |

**Windows and Linux are not supported in v1.**

## Disk space

| Item | Size | When |
|---|---|---|
| Whisper `large-v3-turbo` model | **1.5 GB** | One-time, shared across all playlists |
| brew packages (yt-dlp, ffmpeg, whisper-cpp, node) | ~400 MB | One-time |
| pip packages (Pillow, requests, aiomqtt) | ~60 MB | One-time |
| `pixel-art` skill | ~2 MB | One-time |
| MP3 audio per playlist | ~8 MB / episode | Per playlist. Can delete after upload. 100 episodes ≈ 800 MB. |
| Transcripts, sprites, cache | < 5 MB total | Negligible |

**First-run total: ~2.5 GB one-time + ~1 GB per playlist.**

## Dependencies (and why)

Every external tool we need, and what it's for:

| Dependency | Why we need it | Optional? |
|---|---|---|
| **yt-dlp** | Pulls audio from YouTube. No official YouTube audio download API exists. | Required |
| **ffmpeg** | yt-dlp uses it internally to extract MP3 from YouTube's streams. Also slices 3-min WAVs for Whisper. | Required |
| **whisper-cpp** + `ggml-large-v3-turbo` model | Transcribes the first 3 min of each episode so Claude knows what concrete noun to draw as an icon. YouTube titles like "Episode 5: Friends" don't tell us. | Optional — the skill skips Phase 2 when YouTube titles are already concrete enough to identify the subject |
| **node** | (1) yt-dlp uses Node as a JS runtime to solve YouTube's anti-bot challenge. (2) `npx skills` installs the `pixel-art` skill. | Required |
| **Pillow** (pip) | Reads/writes 16×16 PNG sprites | Required |
| **requests** (pip) | HTTP client for the Yoto REST API | Required |
| **aiomqtt** (pip) | Async MQTT client for `mqtt_log.py` diagnostics | Optional — only if you run the playback debugger |
| **pixel-art skill** | Design knowledge for 16×16 sprites: hue-shifted ramps, selective outlining, palette discipline. Without it, sprite quality drops noticeably. | Strongly recommended |

`scripts/bootstrap.sh` installs everything except Homebrew itself. Run it once.

## Install

### If you're new to Claude Code

Read [docs/SETUP.md](docs/SETUP.md) — it walks you through installing Claude Code, then this skill, in 30 minutes.

### If you already have Claude Code

Inside Claude Code:

```
/plugin marketplace add meng-tsai/youtube-to-yoto
/plugin install youtube-to-yoto
```

Restart Claude Code. Then have it run the bootstrap to install pipeline deps:

```
> please run scripts/bootstrap.sh for the youtube-to-yoto skill
```

### If you use Cursor / Codex / OpenCode / another skill-compatible agent

```bash
npx skills add meng-tsai/youtube-to-yoto
```

Then run the bootstrap as above.

## First run (recommended: demo mode)

Inside Claude Code, with your playlist URL ready:

```
> I want to put this YouTube playlist on my Yoto card:
> https://www.youtube.com/playlist?list=XXXXXXXXX
```

The skill detects it's your first run and **recommends doing the first 3 episodes only**. Say yes. If anything's wrong (OAuth, card binding, audio format), you'll catch it in 5 minutes instead of 1.5 hours.

After you confirm the 3 episodes play correctly on the Player, it'll ask whether to continue with the rest.

## Full pipeline reference

For users who want to drive the scripts directly without going through Claude:

```bash
SKILL=~/.claude/skills/youtube-to-yoto

# Phase 1 — Download
bash $SKILL/scripts/download_playlist.sh \
  https://www.youtube.com/playlist?list=XXX  \
  /tmp/myplaylist                            \
  --first 3 --lang en

# Phase 2 — Transcribe
bash $SKILL/scripts/transcribe_all.sh \
  /tmp/myplaylist /tmp/myplaylist/transcripts

# Phase 3 — Subject extraction (via SubAgents in your Claude session)
# (Done conversationally — the skill walks you through it.)

# Phase 4 — Sprite generation (via SubAgents in your Claude session)
# (Cost confirm gate fires here.)

# Phase 5 — Upload
export YOTO_CLIENT_ID=<your client id>
python3 $SKILL/scripts/yoto_auth.py
python3 $SKILL/scripts/yoto_upload.py \
  --subjects /tmp/myplaylist/subjects.json \
  --sprites  /tmp/myplaylist/pixel_subjects \
  --mp3      /tmp/myplaylist \
  --title    "My playlist" \
  --go
```

See [skills/youtube-to-yoto/SKILL.md](skills/youtube-to-yoto/SKILL.md) for the full skill spec, [references/yoto-api.md](skills/youtube-to-yoto/references/yoto-api.md) for the Yoto API reference, [references/pitfalls.md](skills/youtube-to-yoto/references/pitfalls.md) for the list of bugs that pass server validation but break the Player.

## OAuth

You need a Yoto OAuth Client ID from https://dashboard.yoto.dev/. The skill walks you through getting one the first time. Manual reference: [docs/OAUTH.md](docs/OAUTH.md).

## Troubleshooting

[docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) covers the common failure modes — player skipping tracks, OAuth errors, yt-dlp 429s, quota issues.

## Hard limits

- **100 tracks per playlist** (Yoto API limit). For larger collections, split across cards.
- **Mac only** (v1). Apple Silicon strongly recommended for Whisper Metal acceleration.
- **No NFC binding API** — you must physically tap a blank MYO card on the Player while the Yoto app is open.

## Contributing

PRs welcome, especially for:

- Translations of `docs/SETUP.md`, `docs/OAUTH.md`, etc. (only `README.md` is currently translated)
- Screenshots for `docs/OAUTH.md`
- Sample sprite library extensions

## License

[MIT](LICENSE)

## Acknowledgements

- The Yoto API mapping was reverse-engineered from these prior projects: `cjlm/yoto-playlist-creator`, `bperkinspdx/yoto-mcp-server`, `cdnninja/yoto_api`.
- Pixel-art design guidance via [omer-metin/skills-for-antigravity@pixel-art](https://github.com/omer-metin/skills-for-antigravity).
- Built with [Claude Code](https://claude.ai/code).
