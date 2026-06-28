# Pitfalls

Things that **pass server-side validation but break the Player at runtime**, plus a few things that fail loudly in surprising ways. Skip this file and you'll spend hours debugging an upload that "succeeded" (HTTP 200) but doesn't actually play.

## Yoto API — silent failures

### `track.format` must be `"opus"`, never `"mp3"`

Yoto's transcode pipeline takes whatever you upload (MP3, M4A, WAV) and re-encodes to **Opus in Ogg container** at ~96 kbps. Verify by GETting `/media/upload/{uploadId}/transcoded`:

```json
"transcodedInfo": { "codec": "opus", "format": "opus", ... }
```

If you declare `format: "mp3"` in chapter tracks, the Player's firmware picks its MP3 decoder, fails to parse the Opus file, and reports `trackLength: 4` via MQTT. Each track plays for ~0.5s, then advances. **Always set `format: "opus"`.**

Detection: subscribe to `device/{deviceId}/data/events`; check that `trackLength` matches your `duration` in seconds. If it's a small constant like `4`, format is wrong.

The Yoto app on iPhone (NFC tap) plays the file fine because the in-app player uses a generic browser decoder that auto-detects. Only the embedded Player firmware is strict. "Plays on phone via NFC" is NOT a useful signal that the playlist is right — you must test on the physical Player.

### `track.duration` is in seconds, not milliseconds

Schema is explicit: "The duration of the track in seconds." Pass the value from `transcodedInfo.duration` through as an integer. **Do not multiply by 1000.** If you do, the Player's metadata bookkeeping breaks and skip behaviour appears.

### `track.overlayLabel` is required at the track level

The Yoto Zod schema marks `overlayLabel` required on track, not just on chapter. Setting it only on chapter passes server validation (returns 200) but breaks the Player at runtime. Typical value: the chapter number as a string (`"1"`, `"2"`, …).

### `track.channels` should be set

`"stereo"` or `"mono"`. Detect from source MP3:

```bash
ffprobe -v error -select_streams a:0 -show_entries stream=channels \
  -of default=noprint_wrappers=1:nokey=1 input.mp3
```

YouTube audio is typically `2` channels → `"stereo"`. Omitting `channels` is in the same class of subtle failure: server accepts, Player misbehaves.

### `metadata.media` (playlist totals) is required

The Player uses these for whole-playlist scrubbing:

```json
{
  "metadata": {
    "media": {
      "duration": 25028,        // SUM over all chapters, seconds
      "fileSize": 265299898,    // SUM over all chapters, bytes
      "readableFileSize": 253.0 // optional MB; server keeps or strips harmlessly
    }
  }
}
```

POST returns 200 without it; Player behaves erratically. The official Yoto tutorial and the `bperkinspdx/yoto-mcp-server` reference both include it.

### Hard cap: 100 chapters per playlist

`POST /content` returns `400 "track count is limited to 100"` above that. Not documented anywhere obvious. Plan splits in advance.

## Yoto API — loud failures with misleading messages

### Icon upload wants raw bytes, NOT multipart form-data

`POST /media/displayIcons/user/me/upload` with multipart returns:

```json
{"error": {"code": "bad-request", "message": "A binary image file is required"}}
```

Trying every form field name (`file`, `image`, `icon`, `data`, `binary`) all fail with the same message. The actual fix: send the raw PNG bytes in the body with `Content-Type: image/png`. Use `?autoConvert=true&filename=X.png` as query params.

### Audio upload returns `null` uploadUrl on dedup

Yoto dedupes audio by SHA256. Uploading the same MP3 twice gives `{"upload": {"uploadId": "...", "uploadUrl": null}}`. **Skip the PUT** and go straight to polling `/media/upload/{uploadId}/transcoded` — the transcoded info is already available.

### Many endpoints require a scope you don't have yet

`user:content:manage` covers the upload pipeline but NOT:
- `GET /content/{cardId}` — needs `user:content:view` or `family:library:view`
- `GET /device-v2/devices/mine` — needs `family:devices:view`
- MQTT topic subscribe — also needs `family:devices:view`

If you hit `403 forbidden`, re-auth with broader scopes via the device flow. Enable the scope first at https://dashboard.yoto.dev/ for your client.

### Cached tokens won't pick up new scopes

After enabling a new scope in the dashboard, the existing access token in `~/.yoto-tokens.json` still has the old scope set. The auth script's "use cached token if not expired" check will keep using the stale one. Delete the token file first:

```bash
rm ~/.yoto-tokens.json && python3 scripts/yoto_auth.py
```

## Audio source — YouTube

### Use a JS runtime with yt-dlp

```bash
yt-dlp --js-runtimes node ...
```

Without it: `429 Too Many Requests` and missing format info on most modern YouTube extracts. Install Node separately (`brew install node`) or via nvm.

### Force a language at extraction time

YouTube auto-translates titles in the playlist response based on viewer locale. Without an explicit lang setting you get a mix of languages depending on which videos the uploader has translated:

```bash
yt-dlp --js-runtimes node \
  --extractor-args "youtubetab:lang=zh-TW;youtube:lang=zh-TW" \
  ...
```

### Don't parallel-curl-scrape YouTube

`curl https://youtube.com/watch?v=...` works once. Above ~16 parallel requests you get a `reCAPTCHA` "unusual traffic" challenge HTML back (with HTTP 200, so it's silent). Use yt-dlp for all metadata reads.

### Publish dates need a per-video extract

`yt-dlp --flat-playlist -J` returns `timestamp: None` and `release_timestamp: None`. For publish dates, per-video extract:

```bash
yt-dlp --js-runtimes node --skip-download \
  --print "%(id)s|%(upload_date)s" "https://youtu.be/$VID"
```

Run parallel-4. Higher parallelism trips rate-limit.

### Excel/Numbers corrupts YouTube video IDs starting with `-`

`-pQV_U5Cspo` gets auto-interpreted as a formula and saved back as `#NAME?` on CSV export. Workarounds: edit CSVs in a text editor (VS Code), or set the column type to Text before pasting in Numbers/Excel. Validate after every spreadsheet roundtrip.

### Thumbnails are URL-predictable

`https://i.ytimg.com/vi/{video_id}/hqdefault.jpg` always exists for public videos. Don't scrape; just construct the URL.

## Whisper

### Use whisper-cpp on Apple Silicon

`brew install whisper-cpp` gives `whisper-cli` with Metal acceleration out of the box. ~15× realtime with the turbo model.

### Convert to 16 kHz mono WAV first

```bash
ffmpeg -y -i input.mp3 -t 180 -ar 16000 -ac 1 -c:a pcm_s16le output.wav
```

`-t 180` truncates to first 3 minutes (enough to identify the episode subject for kids' content where the title is stated up front).

### `-of out` requires `-otxt` to write a file

```bash
whisper-cli -m model.bin -l zh -otxt -nt -f input.wav -of output_prefix
# writes output_prefix.txt
```

Without `-otxt`, output goes to stdout only.

### Whisper Chinese typos are systematic

Common substitutions to expect:
- 獨角仙 → 獨角蟹 (rhinoceros beetle)
- 耶誕樹 → 椰蛋樹 (Christmas tree)
- 撿栗子 → 簡粒子 (pick chestnuts)
- 蛤蜊 → 隔離 (clam)

Instruct the subject-extraction LLM: "Transcripts may contain Whisper transcription errors; use context to deduce the real word." Surrounding context disambiguates ~100% of the time.

## Subject extraction

### Title alone isn't enough for abstract titles

「爸爸的朋友」 (Dad's Friend) → must read the transcript to learn the friend is a rhinoceros beetle. Without transcript context, the LLM picks "two tea cups" (generic friendship symbol) — wrong subject, wrong icon, kid doesn't recognize the episode. **Always pass title + transcript together** in the prompt.

### Use Sonnet (or smarter), not Haiku

Haiku is too literal — picks the first concrete noun it sees, often a side prop (snack, table). Sonnet weighs central importance + visual distinctiveness. Cost difference is negligible for short transcripts (~$2 vs $0.30 for 268 episodes).

### Force a single concrete English noun

Output must be ONE physical object expressible as a 1-3 word English noun. Not verbs, not abstractions, not character names. The Phase 3 prompt template in `subagent-prompts.md` enforces this with worked examples.

## Image generation (if you ever use it)

### Verbs in prompts get drawn

Prompt: "draw an icon for 「章魚買到哪裡去了」" (where did the octopus go to buy?). The model interprets "買" (buy) and draws a SHOPPING BAG instead of an octopus. **Extract the subject first**, then prompt the image API with just the subject noun.

### "Pixel art at 1024×1024" is a lie

Even with strict prompts, models like gpt-image-2 don't snap to a true 16×16 grid — they render at effective 32×32 or 48×48 styled as chunky blocks. Downscaling muddies detail. Use AI for inspiration only; author the final 16×16 by code.

### Transparent background returns an opaque checkerboard

Asking for `background="transparent"` gets you an opaque PNG with the standard transparency-checkerboard baked in (the model "imagined" what transparent looks like). Specify `background = pure white #FFFFFF` AND tell the model "the subject must NOT contain pure white pixels", then post-process near-white → alpha 0.

## Verification

After upload, before declaring success:

1. The MYO card appears in the Yoto app's library — basic acknowledgement that POST worked
2. Tap the card in the app → playlist plays via phone — confirms the audio files are decodable by SOME decoder, not that the Player will accept them
3. **Insert the bound physical card into the Player** — this is the only real test. If audio doesn't play, run `scripts/mqtt_log.py` and check `trackLength` vs your `duration`
4. Long-press power 10s on the Player to force a metadata re-fetch if you suspect it's caching a stale chapter list
