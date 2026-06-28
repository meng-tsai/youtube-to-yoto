#!/usr/bin/env bash
# Download a YouTube playlist as MP3s with embedded thumbnails.
#
# Usage:
#   download_playlist.sh <YOUTUBE_PLAYLIST_URL> <output_dir> [--first N] [--parallel N] [--lang LANG]
#
# Outputs: {video_id}.mp3 in output_dir (stable IDs for downstream phases).
# Cache: skips already-downloaded vids (--no-overwrites).

set -euo pipefail

URL=""
OUT=""
FIRST=""
PAR="4"
LANG_TAG="${YOTO_LANG:-en}"

while [ $# -gt 0 ]; do
  case "$1" in
    --first)
      if [ -z "${2:-}" ]; then echo "ERROR: --first needs a value" >&2; exit 2; fi
      FIRST="$2"; shift 2 ;;
    --parallel)
      if [ -z "${2:-}" ]; then echo "ERROR: --parallel needs a value" >&2; exit 2; fi
      PAR="$2"; shift 2 ;;
    --lang)
      if [ -z "${2:-}" ]; then echo "ERROR: --lang needs a value" >&2; exit 2; fi
      LANG_TAG="$2"; shift 2 ;;
    -h|--help)
      echo "Usage: $0 <URL> <out_dir> [--first N] [--parallel N] [--lang LANG]"; exit 0 ;;
    *)
      if [ -z "$URL" ]; then URL="$1"
      elif [ -z "$OUT" ]; then OUT="$1"
      else echo "Unexpected arg: $1" >&2; exit 1
      fi
      shift ;;
  esac
done

if [ -z "$URL" ] || [ -z "$OUT" ]; then
  echo "Usage: $0 <YOUTUBE_PLAYLIST_URL> <output_dir> [--first N] [--parallel N] [--lang LANG]"
  exit 1
fi

# Validate user-supplied scalars before they reach subprocesses.
if [ -n "$FIRST" ] && ! echo "$FIRST" | grep -Eq '^[0-9]+$'; then
  echo "ERROR: --first must be a non-negative integer (got: $FIRST)" >&2; exit 2
fi
if ! echo "$PAR" | grep -Eq '^[0-9]+$'; then
  echo "ERROR: --parallel must be a non-negative integer (got: $PAR)" >&2; exit 2
fi
if ! echo "$LANG_TAG" | grep -Eq '^[a-zA-Z0-9_-]+$'; then
  echo "ERROR: --lang must match [a-zA-Z0-9_-]+ (got: $LANG_TAG)" >&2; exit 2
fi

mkdir -p "$OUT"
LOG="$OUT/_download_log.txt"
EXTRACTOR_ARGS="youtubetab:lang=${LANG_TAG};youtube:lang=${LANG_TAG}"

echo "→ Listing playlist (lang=$LANG_TAG)..."
yt-dlp --js-runtimes node \
    --extractor-args "$EXTRACTOR_ARGS" --flat-playlist -J "$URL" > "$OUT/_playlist.json"

# Pass paths via env vars, not via shell-string interpolation into -c "...".
N=$(OUT_DIR="$OUT" python3 -c '
import json, os
p = os.path.join(os.environ["OUT_DIR"], "_playlist.json")
print(len(json.load(open(p))["entries"]))
')
echo "  Found $N videos"

echo "→ Extracting video IDs..."
OUT_DIR="$OUT" FIRST="$FIRST" python3 -c '
import json, os, sys
p = os.path.join(os.environ["OUT_DIR"], "_playlist.json")
limit_raw = os.environ.get("FIRST", "")
limit = int(limit_raw) if limit_raw else None
entries = json.load(open(p))["entries"]
if limit:
    entries = entries[:limit]
for e in entries:
    print(e["id"])
' > "$OUT/_ids.txt"

ACTUAL=$(wc -l < "$OUT/_ids.txt" | tr -d ' ')
if [ -n "$FIRST" ]; then
  echo "  Downloading only the first $ACTUAL videos (--first $FIRST)"
fi

echo "→ Downloading MP3s ($PAR-parallel)..."
echo "  Log: $LOG"
# Reference $OUT, $EXTRACTOR_ARGS, $LOG via the inner shell's env, not via
# outer string interpolation, so weird chars in $OUT can't break out.
xargs -n 1 -P "$PAR" -I {} \
  env OUT_DIR="$OUT" EXTRACTOR_ARGS="$EXTRACTOR_ARGS" LOG="$LOG" \
  sh -c '
    yt-dlp --js-runtimes node \
      --extractor-args "$EXTRACTOR_ARGS" \
      -x --audio-format mp3 --audio-quality 0 \
      --embed-thumbnail --add-metadata \
      --no-overwrites \
      -o "$OUT_DIR/%(id)s.%(ext)s" \
      "https://youtu.be/$1" >> "$LOG" 2>&1
  ' _ {} < "$OUT/_ids.txt"

DONE=$(ls "$OUT"/*.mp3 2>/dev/null | wc -l | tr -d ' ')
echo "✓ Downloaded $DONE/$ACTUAL MP3s to $OUT"
