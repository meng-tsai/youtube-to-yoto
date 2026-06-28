# Troubleshooting

Common failure modes and fixes. Add an issue at
https://github.com/meng-tsai/youtube-to-yoto/issues if you hit something not listed here.

## Player issues

### Card inserts → cloud icon → skips all tracks in ~0.5s each

Almost always a payload-format bug. Subscribe to the Player's events
to confirm:

```bash
python3 ~/.claude/skills/youtube-to-yoto/scripts/mqtt_log.py
```

Insert the card. If the events show `"trackLength": 4` while audio
should be 9 minutes, your `track.format` is wrong. The fix is in
`scripts/yoto_upload.py` — `format` must be `"opus"`, never `"mp3"`
(Yoto re-encodes everything to Opus regardless of what you upload).

If `trackLength` matches duration but tracks still skip, check:
- `track.overlayLabel` set at TRACK level (not just chapter)
- `track.channels` set to `"stereo"` or `"mono"`
- `metadata.media.duration` is sum of all track durations in seconds

See `skills/youtube-to-yoto/references/pitfalls.md` for the full list.

### Card never appears in the Yoto app

Make sure the Yoto app is open and you tapped your MYO card on the
Player while the app is in the foreground. The NFC bind step requires
the app — there's no API for it.

If still not appearing after retry, sign out + back in to the Yoto
app and try again.

### Audio plays but the icon is wrong / blank

Two possible causes:

1. Wrong subject extracted in Phase 3 — re-run Phase 3 + 4 + 5 with
   the corrected `subjects.json`. The icon upload is cached, so only
   the wrong subject's sprite regenerates.
2. `display.icon16x16` references a `mediaId` that doesn't exist on
   your account — check `upload_cache.json` and re-run icon upload.

## Install / dependency issues

### `brew: command not found`

Homebrew not installed. Install:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Then re-run `scripts/bootstrap.sh`.

### `whisper-cli: command not found`

```bash
brew install whisper-cpp
```

Or re-run `scripts/bootstrap.sh`.

### `Model not found: ~/.local/share/whisper-models/ggml-large-v3-turbo.bin`

```bash
mkdir -p ~/.local/share/whisper-models
curl -L -o ~/.local/share/whisper-models/ggml-large-v3-turbo.bin \
  https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo.bin
```

Or re-run `scripts/bootstrap.sh`.

### `npx: command not found`

Node not installed.

```bash
brew install node
```

### `ModuleNotFoundError: No module named 'PIL'` / `requests` / etc.

```bash
python3 -m pip install --user Pillow requests aiomqtt
```

Or re-run `scripts/bootstrap.sh`.

### `python3.11: command not found` from `mqtt_log.py`

This was a bug in older versions. Update to the latest:

```bash
cd ~/.claude/plugins/.../youtube-to-yoto && git pull
```

The current shebang is `#!/usr/bin/env python3` and works on any
python3 ≥ 3.10.

## OAuth issues

See `docs/OAUTH.md` § Troubleshooting for OAuth-specific failures.

## YouTube download issues

### `ERROR: ... HTTP Error 429: Too Many Requests`

YouTube rate-limited you. yt-dlp needs a JS runtime; bootstrap.sh
installs Node for this. If you still hit 429:

- Wait 10-30 minutes
- Try with `--parallel 1` to slow down (default is 4)
- Try a VPN if you're on a shared IP

### Titles come back in the wrong language

Pass `--lang <BCP-47>` to `download_playlist.sh`:

```bash
scripts/download_playlist.sh <URL> <out_dir> --lang en
scripts/download_playlist.sh <URL> <out_dir> --lang zh-TW
```

Or set `YOTO_LANG` env var before running the skill.

## Upload issues

### `POST /content` returns 400 `track count is limited to 100`

Yoto hard limit. Either:

- Pick the most important 100 episodes
- Split into multiple MYO cards (one card per ~90 episodes is safe)

### Upload hangs at `Phase B — audio` for a long time

Each upload is `POST → PUT → poll until transcode finishes`.
Transcoding can take 30-60 seconds per file the first time. If it
hangs for > 5 minutes on one file: kill the script, re-run — the
`upload_cache.json` will resume from where you left off.

## Cost / quota issues

### "Quota exceeded" mid-run on Pro/Max

You hit the 5-hour rolling window. Wait for it to roll over, then
re-run the same command. `upload_cache.json` makes the run resumable.

### Sprite generation is too expensive on pay-per-token API

For v1, the only option is to use Pro/Max (much cheaper for bulk
sprite work). A Sonnet fallback may come in a future version.
