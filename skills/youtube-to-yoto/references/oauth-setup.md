# OAuth Setup — Conversational Walkthrough

This file is the script Claude follows when the user has not yet
configured a Yoto OAuth Client ID. The goal: get from "no OAuth app"
to "client_id in env + tokens on disk" in under 3 minutes, entirely
within the chat — no expectation that the user reads any doc.

## Detection

Trigger this walkthrough when EITHER:

- `$YOTO_CLIENT_ID` is unset, OR
- `~/.yoto-tokens.json` does not exist, OR
- `~/.yoto-tokens.json` exists but `expires_at` has lapsed and refresh
  fails

## The conversation

### 1. Announce

> "Before we can upload to your Yoto card, we need a Yoto OAuth Client ID.
> I'll open the dashboard for you and walk you through it — takes about 3 minutes."

### 2. Open the dashboard (Mac)

```bash
open https://dashboard.yoto.dev/
```

If `open` fails (e.g. non-Mac, no GUI), print the URL and ask the user to open it manually.

### 3. Guide step-by-step

Ask the user one short instruction at a time. Wait for them to confirm "done" / "ok" before moving on. Don't dump all steps at once.

1. **Sign in.** "Sign in with the same email you use for your Yoto app. Tell me when you're on the dashboard."
2. **Create an app.** "Look for a 'Create new app' button (usually top right). Click it. Name the app anything you like — `my-myo-uploader` works. Tell me when done."
3. **Enable scopes.** "On the app's settings page, find the Scopes / Permissions section. Check **`user:content:manage`** (required). Optionally also check **`family:devices:view`** (only needed if you want MQTT playback diagnostics later). Save. Tell me when done."
4. **Copy the Client ID.** "Find the Client ID (it's a long alphanumeric string). Copy it and paste it here."

### 4. Capture and run Device Flow

When the user pastes the Client ID:

```bash
export YOTO_CLIENT_ID="<the value the user pasted>"
python3 scripts/yoto_auth.py
```

This prints a verification URL and a short code. Tell the user:

> "Open this URL in your browser: `<verification_uri_complete>`
> Then click Approve. The terminal will detect it automatically."

### 5. Confirm

After `yoto_auth.py` exits 0:

> "OAuth done. Token saved to `~/.yoto-tokens.json` (expires in 24 hours; the script auto-refreshes after that if you enabled `offline_access`)."

## Fallback: pure text walkthrough

If the user prefers to do it themselves: point them at `docs/OAUTH.md` (same content, in document form).

## Notes for Claude

- The Client ID is short-lived and rotatable. When the user pastes it into the chat, treat it as visible to the conversation transcript (it's needed for `export YOTO_CLIENT_ID=...`). The OAuth Device Flow tokens are higher-value secrets — they live only on the user's local disk at `~/.yoto-tokens.json` (mode 600) and never transit the chat.
- If the user prefers to keep even the Client ID off the transcript: tell them to set it themselves in their own terminal (`export YOTO_CLIENT_ID=...` then `python3 scripts/yoto_auth.py`) rather than pasting into the chat.
- If the user says they already have a Client ID, skip steps 1-4 and jump straight to running `yoto_auth.py`.
- If `yoto_auth.py` fails with "OAuth error: unauthorized_client", the user likely forgot to enable the scope. Send them back to step 3.
- The `family:devices:view` scope is only needed for `mqtt_log.py`. Don't insist on it.
