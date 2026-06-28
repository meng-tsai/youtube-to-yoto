#!/usr/bin/env python3
"""
Yoto OAuth Device Flow bootstrap.

Usage:
    export YOTO_CLIENT_ID=your-client-id-from-dashboard.yoto.dev
    python3 yoto_auth.py [--with-offline]

Without --with-offline, requests scopes that work out of the box on a fresh
dashboard app. Add --with-offline once you've enabled offline_access in the
dashboard's app settings (gives you refresh tokens — no re-auth every few hours).

Tokens are saved to ~/.yoto-tokens.json (chmod 600). Re-runs auto-refresh.
"""

import argparse, json, os, sys, time
from pathlib import Path
import requests

LOGIN_BASE = "https://login.yotoplay.com"
API_BASE   = "https://api.yotoplay.com"
AUDIENCE   = "https://api.yotoplay.com"
TOKEN_PATH = Path.home() / ".yoto-tokens.json"

def _save_tokens(tokens: dict) -> None:
    """Always write tokens with mode 600 so refresh-path writes don't widen perms."""
    import os
    fd = os.open(str(TOKEN_PATH), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(json.dumps(tokens, indent=2))

def device_login(client_id: str, scopes: str) -> dict:
    print("→ Requesting device code...", flush=True)
    r = requests.post(
        f"{LOGIN_BASE}/oauth/device/code",
        data={"client_id": client_id, "scope": scopes, "audience": AUDIENCE},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=15,
    )
    r.raise_for_status()
    info = r.json()
    print(flush=True)
    print("┌──────────────────────────────────────────────────────────", flush=True)
    print(f"│  1. Open this URL in your browser:", flush=True)
    print(f"│     {info['verification_uri']}", flush=True)
    print(f"│", flush=True)
    print(f"│  2. Enter this code:  {info['user_code']}", flush=True)
    print(f"│", flush=True)
    print(f"│  3. Or open the direct URL:", flush=True)
    print(f"│     {info.get('verification_uri_complete', info['verification_uri'])}", flush=True)
    print("└──────────────────────────────────────────────────────────", flush=True)
    print(flush=True)
    print(f"Polling every {info['interval']}s, expires in {info['expires_in']}s...", flush=True)

    deadline = time.time() + info["expires_in"]
    while time.time() < deadline:
        time.sleep(info["interval"])
        tr = requests.post(
            f"{LOGIN_BASE}/oauth/token",
            data={
                "grant_type":  "urn:ietf:params:oauth:grant-type:device_code",
                "device_code": info["device_code"],
                "client_id":   client_id,
                "audience":    AUDIENCE,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=15,
        )
        body = tr.json()
        err = body.get("error")
        if err == "authorization_pending":
            print("  ...waiting for you to approve in browser", flush=True)
            continue
        if err == "slow_down":
            time.sleep(2)
            continue
        if err:
            sys.exit(f"OAuth error: {err} — {body.get('error_description','')}")
        body["_obtained_at"] = int(time.time())
        return body
    sys.exit("Device code expired before you approved. Re-run.")

def refresh(client_id: str, refresh_token: str) -> dict:
    r = requests.post(
        f"{LOGIN_BASE}/oauth/token",
        data={"grant_type": "refresh_token", "client_id": client_id,
              "refresh_token": refresh_token},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=15,
    )
    r.raise_for_status()
    body = r.json()
    body["_obtained_at"] = int(time.time())
    if "refresh_token" not in body:
        body["refresh_token"] = refresh_token
    return body

def get_tokens(scopes: str) -> dict:
    client_id = os.environ.get("YOTO_CLIENT_ID")
    if not client_id:
        sys.exit("ERROR: set YOTO_CLIENT_ID env var (get from dashboard.yoto.dev)")

    if TOKEN_PATH.exists():
        tokens = json.loads(TOKEN_PATH.read_text())
        age = time.time() - tokens.get("_obtained_at", 0)
        if age < tokens.get("expires_in", 0) - 60:
            print(f"✓ Using cached token (expires in {int(tokens['expires_in'] - age)}s)", flush=True)
            return tokens
        if "refresh_token" in tokens:
            print("→ Refreshing token...", flush=True)
            try:
                tokens = refresh(client_id, tokens["refresh_token"])
                _save_tokens(tokens)
                print("✓ Refreshed", flush=True)
                return tokens
            except Exception as e:
                print(f"⚠ Refresh failed ({e}), starting device flow", flush=True)

    tokens = device_login(client_id, scopes)
    _save_tokens(tokens)
    print(f"✓ Saved tokens to {TOKEN_PATH}", flush=True)
    return tokens

def test_call(access_token: str) -> None:
    print("\n→ Testing API: GET /content/mine", flush=True)
    r = requests.get(
        f"{API_BASE}/content/mine",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=15,
    )
    if r.status_code != 200:
        print(f"  ✗ {r.status_code}: {r.text[:300]}", flush=True)
        return
    cards = r.json().get("cards", [])
    print(f"  ✓ Got {len(cards)} MYO card(s)", flush=True)
    for c in cards[:5]:
        print(f"    - {c.get('title','(no title)')}  [{c.get('cardId')}]", flush=True)

if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description="Yoto OAuth Device Flow. If you change scopes, delete "
                    "~/.yoto-tokens.json first — cached tokens keep their old scope set.")
    ap.add_argument("--with-offline", action="store_true",
                    help="Request offline_access (refresh tokens; must be enabled in dashboard).")
    ap.add_argument("--with-mqtt", action="store_true",
                    help="Request family:devices:view + family:library:view scopes for MQTT diagnostics.")
    args = ap.parse_args()
    scopes = "user:content:manage"
    if args.with_mqtt:
        scopes += " family:devices:view family:library:view"
    if args.with_offline:
        scopes += " offline_access"
    tokens = get_tokens(scopes)
    test_call(tokens["access_token"])
