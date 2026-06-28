#!/usr/bin/env bash
# Translate README.md into 6 community languages by dispatching Sonnet SubAgents.
#
# Usage:
#   bash scripts/translate-readme.sh             # print dispatch protocol
#   bash scripts/translate-readme.sh --check     # verify all 6 outputs exist
#   bash scripts/translate-readme.sh --stale     # warn if translations lag README
#
# This script DOES NOT call any AI directly. It prints the protocol for the
# driving Claude Code session to fan out 6 parallel SubAgents via the Task tool.
# Must run from a top-level Claude Code session (nested subagents typically
# cannot dispatch further subagents).
#
# Output files (written by the SubAgents, not by this script):
#   README.zh-TW.md  README.zh-CN.md  README.ja.md
#   README.ko.md     README.es.md     README.fr.md

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
README="$REPO_ROOT/README.md"
LANGS="zh-TW zh-CN ja ko es fr"

if [ ! -f "$README" ]; then
  echo "ERROR: $README not found." >&2
  exit 1
fi

SHA=$(cd "$REPO_ROOT" && git rev-parse --short HEAD 2>/dev/null || echo "unknown")

# --- mode: --check ---
if [ "${1:-}" = "--check" ]; then
  echo "Verifying all 6 translations exist:"
  any_bad=0
  for L in $LANGS; do
    f="$REPO_ROOT/README.$L.md"
    if [ -f "$f" ]; then
      if head -1 "$f" | grep -q "Translated from README.md"; then
        echo "  ok  $L  ($(wc -l <"$f" | tr -d ' ') lines)"
      else
        echo "  !!  $L  exists but missing translation header"
        any_bad=1
      fi
    else
      echo "  !!  $L  missing"
      any_bad=1
    fi
  done
  [ "$any_bad" = "0" ] && { echo "All translations present."; exit 0; } || { echo "Some translations missing or malformed."; exit 1; }
fi

# --- mode: --stale (W10) ---
if [ "${1:-}" = "--stale" ]; then
  echo "Checking translation staleness against README.md @ $SHA:"
  for L in $LANGS; do
    f="$REPO_ROOT/README.$L.md"
    [ -f "$f" ] || { echo "  !!  $L missing"; continue; }
    header_sha=$(head -1 "$f" | grep -oE '@ [0-9a-f]+' | awk '{print $2}' || true)
    if [ -z "$header_sha" ]; then
      echo "  !!  $L  no SHA in header"
    elif [ "$header_sha" = "$SHA" ]; then
      echo "  ok  $L  up to date ($header_sha)"
    else
      echo "  --  $L  stale (header=$header_sha, current=$SHA) — re-run translate-readme.sh"
    fi
  done
  exit 0
fi

# --- default mode: emit the dispatch protocol ---
# Static rules first (single-quoted heredoc — no variable expansion needed here).
cat <<'STATIC'

===================================================================
TRANSLATE README — INSTRUCTIONS FOR CLAUDE
===================================================================

Dispatch SIX SubAgents IN PARALLEL using the Task tool. One per target
language. Each SubAgent receives the full text of the source README, the
per-language style guide, and the HTML-comment header to prepend.

CRITICAL RULES (give these to every SubAgent verbatim):
  - DO NOT translate code blocks, file paths, command names, URLs,
    JSON keys, or environment variable names. They stay verbatim.
  - DO translate prose, table headers, table cells, and link text.
  - DO rewrite the FIRST LINE language switcher so the current language
    is bold and unlinked, and the OTHER languages are linked.
    Example for ja: **日本語** | [English](README.md) | ...
  - Keep all Markdown structure identical (heading levels, list bullets,
    table column count, code-block fences).
  - Prepend this HTML comment as the VERY FIRST line of output, BEFORE
    the language switcher (replace SHA with the value below):
      <!-- Translated from README.md @ SHA. Translations may lag behind
           English. PRs welcome. -->

PER-LANGUAGE STYLE GUIDES
===================================================================

zh-TW (繁體中文 - Traditional Chinese, Taiwan):
  - Use 繁體 (traditional) characters throughout.
  - Tone: friendly but precise. Address reader as 「你」.
  - Technical loanwords (API, OAuth, MQTT, etc.) stay in English.
  - Numerals stay Arabic.
  - Output: README.zh-TW.md

zh-CN (简体中文 - Simplified Chinese, Mainland):
  - Use 简体 (simplified) characters.
  - Tone: friendly but precise. Address reader as "你".
  - Technical loanwords stay in English.
  - Output: README.zh-CN.md

ja (日本語):
  - Use です／ます polite form throughout.
  - Technical terms in katakana where conventional (e.g. インストール);
    proper nouns and CLI names stay in Roman letters.
  - No emojis.
  - Output: README.ja.md

ko (한국어):
  - Use formal -습니다 / -습니까 register (격식체) for instructions.
  - Technical terms in Hangul where conventional, otherwise Roman.
  - Output: README.ko.md

es (Español, neutral Latin American):
  - Use "ustedes" rather than "vosotros".
  - Avoid regional slang. Aim for tone usable across MX/AR/CL/ES.
  - Output: README.es.md

fr (Français):
  - Use the formal "vous" form throughout.
  - Standard European French spelling.
  - Output: README.fr.md

SUBAGENT DISPATCH PATTERN
===================================================================

Dispatch all 6 SubAgents in a single message (parallel). Each prompt:
  "Translate the README at <PATH> into <LANG> per these rules: <style>
   Source SHA for header: <SHA>
   Write the result to <REPO_ROOT>/README.<LANG>.md."

STATIC

# Dynamic context (separate echoes, so variables actually expand).
echo "Source SHA for translation header: $SHA"
echo "Source README:           $README"
echo "Repo root:               $REPO_ROOT"
echo "Expected output files:"
for L in $LANGS; do
  echo "  $REPO_ROOT/README.$L.md"
done
echo
echo "After SubAgents finish, verify with:"
echo "  bash $0 --check"
echo
