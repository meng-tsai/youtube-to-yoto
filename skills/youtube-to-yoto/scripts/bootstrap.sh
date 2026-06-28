#!/usr/bin/env bash
# Bootstrap dependencies for youtube-to-yoto. Idempotent.
#
# Usage: bash scripts/bootstrap.sh
#
# Detects what's missing and installs it. Safe to re-run.
# Requires macOS. Bash 3.2 compatible (no bash-4-isms).

set -euo pipefail

STEPS=9
step=0
ok()   { echo "  ok  $*"; }
todo() { echo "  --> $*"; }
fail() { echo "  !!  $*" >&2; }

bump() { step=$((step+1)); echo; echo "[$step/$STEPS] $*"; }

# --- 0. Platform gate (U2) ---
bump "Checking platform"
if [ "$(uname)" != "Darwin" ]; then
  fail "Mac (Darwin) only for v1."
  echo "  uname returned: $(uname)"
  echo "  Linux/Windows support is on the roadmap but not in this release."
  exit 1
fi
ok "macOS $(sw_vers -productVersion 2>/dev/null || echo '?')"

# --- 1. Homebrew ---
bump "Checking Homebrew"
if ! command -v brew >/dev/null 2>&1; then
  fail "Homebrew not installed."
  echo
  echo "  Install it with the official one-liner from https://brew.sh :"
  echo "    /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
  echo
  echo "  Then re-run: bash scripts/bootstrap.sh"
  exit 1
fi
ok "Homebrew $(brew --version | head -1)"

# --- 2. Homebrew packages ---
bump "Checking brew packages (yt-dlp, ffmpeg, whisper-cpp, node)"
NEEDED=""
for pkg in yt-dlp ffmpeg whisper-cpp node; do
  if brew list --formula | grep -qx "$pkg"; then
    ok "$pkg already installed"
  else
    NEEDED="$NEEDED $pkg"
    todo "$pkg will be installed"
  fi
done
if [ -n "$NEEDED" ]; then
  # shellcheck disable=SC2086
  brew install $NEEDED
fi

# --- 3. python3 present ---
bump "Checking python3"
if command -v python3 >/dev/null 2>&1; then
  ok "$(python3 --version)"
else
  fail "python3 not on PATH"
  echo "  Install with: brew install python@3.12"
  exit 1
fi

# --- 4. python3 >= 3.10 (CR6 — aiomqtt + walrus operator readiness) ---
bump "Checking python3 >= 3.10"
if python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)'; then
  ok "$(python3 --version) >= 3.10"
else
  fail "python3 >= 3.10 required. Install:  brew install python@3.12"
  exit 1
fi

# --- 5. pip packages (required) ---
# CR1/CR2: explicit pip_name => import_name mapping. NO bash-4 `${var,,}`,
# AND Pillow imports as PIL, not 'pillow'.
bump "Checking pip packages (Pillow, requests)"
MISSING_REQ=""
check_pkg() {
  pip_name="$1"; import_name="$2"
  if python3 -c "import $import_name" >/dev/null 2>&1; then
    ok "$pip_name installed"
  else
    MISSING_REQ="$MISSING_REQ $pip_name"
    todo "$pip_name will be installed"
  fi
}
check_pkg Pillow   PIL
check_pkg requests requests
if [ -n "$MISSING_REQ" ]; then
  # shellcheck disable=SC2086
  python3 -m pip install --user $MISSING_REQ
fi

# --- 6. pip packages (optional MQTT diagnostics) ---
bump "Checking optional pip packages (aiomqtt - only for mqtt_log.py)"
if python3 -c "import aiomqtt" >/dev/null 2>&1; then
  ok "aiomqtt installed"
else
  todo "aiomqtt not installed (optional). Install later with: pip install --user aiomqtt"
fi

# --- 7. Whisper model (W6 — SHA256 verify) ---
bump "Checking Whisper large-v3-turbo model (~1.5 GB, one-time)"
MODEL_DIR="$HOME/.local/share/whisper-models"
MODEL="$MODEL_DIR/ggml-large-v3-turbo.bin"
# SHA256 of ggml-large-v3-turbo.bin from official whisper.cpp HuggingFace repo.
# IMPLEMENTOR: before committing, fetch the actual digest and paste here, e.g.:
#   curl -sL https://huggingface.co/ggerganov/whisper.cpp/raw/main/ggml-large-v3-turbo.bin \
#     | shasum -a 256
# If left blank, the script downloads but cannot verify integrity (warns).
EXPECTED_SHA=""

verify_model() {
  if [ ! -f "$MODEL" ]; then
    return 2
  fi
  if [ -z "$EXPECTED_SHA" ]; then
    ok "Model present ($(du -h "$MODEL" | cut -f1)) (SHA256 verification skipped - no expected digest)"
    return 0
  fi
  actual="$(shasum -a 256 "$MODEL" | awk '{print $1}')"
  if [ "$actual" = "$EXPECTED_SHA" ]; then
    ok "Model present and SHA256 matches ($(du -h "$MODEL" | cut -f1))"
    return 0
  fi
  fail "Model SHA256 mismatch - expected $EXPECTED_SHA got $actual"
  return 1
}

if verify_model; then
  :
else
  rc=$?
  if [ "$rc" = "1" ]; then
    echo "  Re-downloading..."
    rm -f "$MODEL"
  fi
  mkdir -p "$MODEL_DIR"
  todo "Downloading Whisper turbo model - 5-15 min depending on your connection..."
  curl -L --progress-bar \
    -o "$MODEL" \
    "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo.bin"
  if ! verify_model; then
    fail "Downloaded model failed SHA256 check. Aborting; please retry."
    exit 1
  fi
fi

# --- 8. pixel-art skill (W7 — supply-chain note + version) ---
bump "Checking pixel-art skill (third-party, recommended)"
PIXEL_SKILL_DIR="$HOME/.claude/skills/pixel-art"
if [ -d "$PIXEL_SKILL_DIR" ]; then
  ok "pixel-art skill present at $PIXEL_SKILL_DIR"
else
  echo
  echo "  HEADS UP: this installs a third-party skill (omer-metin/skills-for-antigravity)"
  echo "  via npx -- it runs arbitrary JavaScript with your user permissions."
  echo "  We recommend the skill (the sprite quality drops noticeably without it)"
  echo "  but it is not maintained by this project."
  echo "  Source: https://github.com/omer-metin/skills-for-antigravity"
  echo
  echo "  Installing..."
  npx -y skills add omer-metin/skills-for-antigravity@pixel-art -g -y
fi

# --- 9. Done ---
bump "All set"
echo
echo "  Next: get a Yoto OAuth Client ID from https://dashboard.yoto.dev/"
echo "  The skill walks you through it the first time you run it."
echo
echo "  Then trigger the skill in Claude Code by saying:"
echo '    "I want to put this YouTube playlist on my Yoto card: <URL>"'
