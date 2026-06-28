#!/usr/bin/env bash
# Batch-transcribe MP3s with whisper.cpp (Apple Silicon Metal acceleration).
# First N seconds only (default 180 = 3 min). Usually enough for subject extraction.
#
# Usage:
#   transcribe_all.sh <mp3_dir> <transcript_dir> [seconds=180] [model_path]
#
# Requires: whisper-cli (brew install whisper-cpp), ffmpeg, large-v3-turbo model.

set -euo pipefail

MP3_DIR="${1:-}"
OUT_DIR="${2:-}"
SECONDS_LIMIT="${3:-180}"
MODEL="${4:-$HOME/.local/share/whisper-models/ggml-large-v3-turbo.bin}"

if [ -z "$MP3_DIR" ] || [ -z "$OUT_DIR" ]; then
  echo "Usage: $0 <mp3_dir> <transcript_dir> [seconds=180] [model_path]"
  exit 1
fi
if [ ! -f "$MODEL" ]; then
  echo "Model not found: $MODEL"
  echo "Download: curl -L -o '$MODEL' 'https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo.bin'"
  exit 1
fi

mkdir -p "$OUT_DIR"
WAV_DIR=$(mktemp -d)
trap "rm -rf $WAV_DIR" EXIT

total=$(ls "$MP3_DIR"/*.mp3 2>/dev/null | wc -l | tr -d ' ')
i=0
for mp3 in "$MP3_DIR"/*.mp3; do
  i=$((i+1))
  vid=$(basename "$mp3" .mp3)
  txt="$OUT_DIR/$vid.txt"
  if [ -f "$txt" ]; then
    echo "[$i/$total] $vid skip (exists)"
    continue
  fi
  wav="$WAV_DIR/$vid.wav"
  ffmpeg -y -loglevel error -i "$mp3" -t "$SECONDS_LIMIT" -ar 16000 -ac 1 -c:a pcm_s16le "$wav"
  whisper-cli -m "$MODEL" -l auto -otxt -nt -f "$wav" -of "$OUT_DIR/$vid" >/dev/null 2>&1
  if [ -f "$txt" ]; then
    chars=$(wc -c < "$txt" | tr -d ' ')
    echo "[$i/$total] $vid done ($chars chars)"
  else
    echo "[$i/$total] $vid FAILED"
  fi
  rm -f "$wav"
done

DONE=$(ls "$OUT_DIR"/*.txt 2>/dev/null | wc -l | tr -d ' ')
echo "✓ $DONE/$total transcripts in $OUT_DIR"
