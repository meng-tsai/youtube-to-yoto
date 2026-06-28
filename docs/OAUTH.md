# Yoto OAuth Setup — Detailed Walkthrough

The youtube-to-yoto skill normally walks you through this conversationally.
This document is the same content in long form — useful if you want to do
it ahead of time or if the conversational flow breaks.

## What you'll end up with

- A Yoto **Client ID** (a long alphanumeric string, public-ish).
- A token saved at `~/.yoto-tokens.json` (private; treat like a password).

The Client ID alone can't access your account — it just identifies your
app. The token (obtained via Device Flow) is what authenticates API
calls. Both expire / can be rotated.

## Step 1 — Create a Yoto developer account

1. Go to https://dashboard.yoto.dev/
2. Click "Sign in" (top right).
3. Use the **same email** you sign in to the Yoto app with — your
   developer account is linked to your consumer account, so the Client
   ID you create here will have access to your MYO cards.

## Step 2 — Create an OAuth app

1. On the dashboard, look for "Apps" in the left navigation or a
   "Create new app" button.
2. Click "Create new app".
3. Name it anything memorable, e.g. `my-myo-uploader`.
4. App type: "Public" / "Device flow" (whatever the dashboard's
   default is — we don't use a client secret).
5. Save.

## Step 3 — Enable scopes

After creating the app, you'll see its settings page. Look for the
**Scopes** (or "Permissions") section.

Required:

- **`user:content:manage`** — lets the skill create/edit MYO playlists.

Optional (only if you want MQTT diagnostics):

- **`family:devices:view`** — lets `mqtt_log.py` subscribe to your
  Player's MQTT topics to debug playback issues.
- **`family:library:view`** — lets the skill enumerate your other Yoto
  content (not currently used; future-proofing).

If you want refresh tokens (so you don't re-auth every 24h):

- **`offline_access`** — must be enabled in the dashboard's app
  settings (sometimes under an "Advanced" or "Token" tab).

Save the scope changes.

## Step 4 — Copy your Client ID

Still on the app settings page, find the **Client ID** field (often
labeled "App ID" or shown near the top). Copy it — it's a 30-ish
character string of letters/digits.

## Step 5 — Set the env var and run the auth script

In a terminal, in the same Claude Code session or any shell:

```bash
export YOTO_CLIENT_ID=<paste your Client ID here>
python3 ~/.claude/skills/youtube-to-yoto/scripts/yoto_auth.py
```

(Adjust the path if you installed the skill globally vs per-project.)

The script will print something like:

```
┌──────────────────────────────────────────────────────────
│  1. Open this URL in your browser:
│     https://login.yotoplay.com/activate
│
│  2. Enter this code:  ABCD-1234
│
│  3. Or open the direct URL:
│     https://login.yotoplay.com/activate?user_code=ABCD-1234
└──────────────────────────────────────────────────────────
```

Open the URL, sign in if prompted, click Approve. The terminal detects
approval within a few seconds and saves the token to
`~/.yoto-tokens.json`.

## Step 6 — Verify

```bash
python3 -c "import json; print(list(json.load(open('$HOME/.yoto-tokens.json')).keys()))"
```

Expected output:

```
['access_token', 'expires_in', 'token_type', 'scope', '_obtained_at']
```

(Plus `refresh_token` if you enabled `offline_access`.)

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `OAuth error: unauthorized_client` when running yoto_auth.py | Scope not enabled | Step 3 — check `user:content:manage` |
| `OAuth error: device code expired` | Took too long to approve in browser | Re-run `yoto_auth.py`, approve faster |
| `401 Unauthorized` from later API calls | Token expired (24h, no refresh) | Re-run `yoto_auth.py`, or enable `offline_access` |
| `403 Forbidden` from `mqtt_log.py` | Missing `family:devices:view` scope | Re-enable in dashboard → delete `~/.yoto-tokens.json` → re-run `yoto_auth.py` |
| Multiple Yoto accounts on one email — wrong account picked | Browser auto-pick | Sign out of all Yoto sessions, re-run, pick the right account at sign-in |

## Rotating your Client ID

If you suspect your Client ID is leaked: delete the app in
dashboard.yoto.dev → create a new one → update `$YOTO_CLIENT_ID` →
delete `~/.yoto-tokens.json` → re-run `yoto_auth.py`. The old
client_id is immediately invalid for the deleted app.
