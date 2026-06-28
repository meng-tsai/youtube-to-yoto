#!/usr/bin/env python3
"""
Yoto upload pipeline:
  Phase A: upload unique sprite icons → mediaId map
  Phase B: upload all audio (parallel) → transcoded info map
  Phase C: POST /content with chapters mapping each vid to its (audio + icon)

Usage:
    python3 yoto_upload.py [--card-id ci8iF] [--title "巧虎全集"] [--limit N] [--go]

Without --go: dry run (uploads + cache, but doesn't POST the playlist).
With --go: actually create or update the playlist.

Required input files (paths configurable via --csv, --subjects, --sprites, --mp3):
  manifest.csv         — columns: video_id, title (with optional 故事名稱)
  subjects.json        — {video_id: subject_string}
  pixel_subjects/      — {subject_slug}.png 16×16 RGBA sprites
  mp3/                 — {video_id}.mp3 audio files

Resume support: upload_cache.json caches all icon mediaIds + audio transcoded info.
Safe to interrupt and rerun.
"""

import argparse, csv, hashlib, json, re, sys, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import requests

DEFAULT_COVER_URL = "https://cdn.yoto.io/myo-cover/star_grapefruit.gif"

API   = "https://api.yotoplay.com"
TOKEN = json.load(open(str(Path.home() / ".yoto-tokens.json")))["access_token"]
HDR   = {"Authorization": f"Bearer {TOKEN}"}

def slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9-]+", "-", s.lower().strip()).strip("-")

# ─── API helpers ────────────────────────────────────
def upload_icon(png: Path) -> str:
    """Upload PNG bytes (NOT multipart form-data) → mediaId."""
    r = requests.post(
        f"{API}/media/displayIcons/user/me/upload",
        params={"autoConvert": "true", "filename": png.name},
        headers={**HDR, "Content-Type": "image/png"},
        data=png.read_bytes(),
        timeout=60,
    )
    r.raise_for_status()
    return r.json()["displayIcon"]["mediaId"]

def get_upload_url(mp3: Path) -> dict:
    """Returns {uploadId, uploadUrl}. uploadUrl is null if file already on Yoto (SHA dedup)."""
    sha = hashlib.sha256(mp3.read_bytes()).hexdigest()
    r = requests.get(
        f"{API}/media/transcode/audio/uploadUrl",
        params={"sha256": sha, "filename": mp3.name},
        headers=HDR, timeout=30,
    )
    r.raise_for_status()
    return r.json()["upload"]

def put_audio(mp3: Path, url: str):
    with open(mp3, "rb") as f:
        r = requests.put(url, data=f,
                         headers={"Content-Type": "audio/mpeg"}, timeout=600)
    r.raise_for_status()

def poll_transcoded(upload_id: str, max_wait_s: int = 300) -> dict:
    """Returns {transcodedSha256, duration_seconds, fileSize, channels}."""
    deadline = time.time() + max_wait_s
    while time.time() < deadline:
        r = requests.get(
            f"{API}/media/upload/{upload_id}/transcoded",
            params={"loudnorm": "false"}, headers=HDR, timeout=30,
        )
        r.raise_for_status()
        info = r.json().get("transcode", r.json())
        if info.get("transcodedSha256"):
            ti = info.get("transcodedInfo", {})
            return {
                "transcodedSha256": info["transcodedSha256"],
                "duration": ti.get("duration", 0),
                "fileSize": ti.get("fileSize", 0),
                "channels": ti.get("channels", "stereo"),
            }
        time.sleep(3)
    raise TimeoutError(f"Transcode {upload_id} took >{max_wait_s}s")

def upload_one_episode(mp3: Path) -> dict:
    up = get_upload_url(mp3)
    if up.get("uploadUrl"):
        put_audio(mp3, up["uploadUrl"])
    return poll_transcoded(up["uploadId"])

# ─── Driver ─────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv",          default=None, help="Manifest CSV (video_id, title). Optional — if omitted, reads _playlist.json from --mp3 dir.")
    ap.add_argument("--playlist-json", default=None, help="yt-dlp _playlist.json (alternative to --csv).")
    ap.add_argument("--subjects", required=True, help="subjects.json {vid: subject}")
    ap.add_argument("--sprites",  required=True, help="Dir of {slug}.png sprites")
    ap.add_argument("--mp3",      required=True, help="Dir of {vid}.mp3 audio")
    ap.add_argument("--cache",    default="upload_cache.json")
    ap.add_argument("--card-id",  default=None, help="Existing card to UPDATE (omit to CREATE new)")
    ap.add_argument("--title",    required=True, help="Playlist title")
    ap.add_argument("--limit",    type=int, default=None, help="Stop after N vids (testing)")
    ap.add_argument("--icon-parallel",  type=int, default=8)
    ap.add_argument("--audio-parallel", type=int, default=4)
    ap.add_argument("--go", action="store_true", help="Actually POST the playlist update")
    args = ap.parse_args()

    subjects_path = Path(args.subjects)
    sprites_dir   = Path(args.sprites)
    mp3_dir       = Path(args.mp3)
    cache_path    = Path(args.cache)

    # Load subjects.json. Two supported shapes:
    #   1) legacy flat:   {vid: "subject"}            — title falls back to CSV/playlist-json
    #   2) since 1.0.1:   {vid: {subject, title}}     — per-episode clean title overrides everything
    # The new shape is produced by the Phase 3 SubAgent (see references/subagent-prompts.md).
    raw_subjects   = json.loads(subjects_path.read_text())
    subjects       = {}   # vid -> subject string (English noun for sprite)
    subj_titles    = {}   # vid -> clean story title (from new dual-extraction format)
    for vid, val in raw_subjects.items():
        if isinstance(val, dict):
            subjects[vid] = val.get("subject", "")
            if val.get("title"):
                subj_titles[vid] = val["title"]
        else:
            subjects[vid] = val
    titles, vids = {}, []

    csv_path = Path(args.csv) if args.csv else None
    pj_path  = Path(args.playlist_json) if args.playlist_json else (mp3_dir / "_playlist.json")

    if csv_path and csv_path.exists():
        with open(csv_path, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            has_included = "included" in (reader.fieldnames or [])
            for row in reader:
                vid = (row.get("video_id") or row.get("vid")
                       or Path(row.get("封面檔名", "")).stem or "").strip()
                if not vid: continue
                if has_included and (row.get("included") or "").strip() != "1":
                    continue
                titles[vid] = (row.get("故事名稱") or row.get("title")
                               or row.get("原始名稱", "")[:50]).strip()
                vids.append(vid)
        print(f"Loaded {len(vids)} vids from CSV {csv_path}")
    elif pj_path.exists():
        data = json.loads(pj_path.read_text())
        for entry in data.get("entries", []):
            vid = entry.get("id", "").strip()
            if not vid: continue
            titles[vid] = (entry.get("title") or vid)[:80]
            vids.append(vid)
        print(f"Loaded {len(vids)} vids from playlist JSON {pj_path}")
    else:
        sys.exit(f"ERROR: no manifest. Pass --csv or --playlist-json, or place _playlist.json in {mp3_dir}")

    # Per-episode clean titles from subjects.json (Phase 3 dual-extraction) override
    # whatever the manifest gave us — manifests carry raw YouTube titles with
    # channel/season prefix + hashtag noise that should NOT reach the Yoto Player.
    overridden = 0
    for vid in vids:
        if vid in subj_titles:
            titles[vid] = subj_titles[vid][:80]
            overridden += 1
    if overridden:
        print(f"Overrode {overridden}/{len(vids)} chapter titles with cleaned story names from subjects.json")
    elif vids and not any(vid in subj_titles for vid in vids):
        print("WARNING: subjects.json has no per-episode `title` field — chapter titles will be raw YouTube titles.")
        print("         Re-run Phase 3 SubAgents with the updated prompt in references/subagent-prompts.md")
        print("         to extract clean story titles (introduced in 1.0.1).")

    if args.limit:
        vids = vids[:args.limit]
    print(f"Processing {len(vids)} vids")

    # Cache for resume
    cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}
    cache.setdefault("icons", {})
    cache.setdefault("audio", {})
    print(f"Cache: {len(cache['icons'])} icons, {len(cache['audio'])} audio")

    # Phase A: upload unique icons
    needed_slugs = sorted({slugify(subjects[v]) for v in vids if v in subjects})
    todo_icons = [s for s in needed_slugs if s not in cache["icons"]]
    print(f"\nPhase A: {len(todo_icons)} unique icons to upload "
          f"({len(needed_slugs)-len(todo_icons)} cached)")
    with ThreadPoolExecutor(max_workers=args.icon_parallel) as ex:
        futs = {ex.submit(upload_icon, sprites_dir / f"{s}.png"): s for s in todo_icons}
        for i, fut in enumerate(as_completed(futs), 1):
            slug = futs[fut]
            try:
                cache["icons"][slug] = fut.result()
                if i % 20 == 0 or i == len(futs):
                    print(f"  icons {i}/{len(futs)}", flush=True)
                    cache_path.write_text(json.dumps(cache, ensure_ascii=False))
            except Exception as e:
                print(f"  ✗ icon {slug}: {e}", flush=True)
    cache_path.write_text(json.dumps(cache, ensure_ascii=False))

    # Phase B: upload audio
    todo_audio = [v for v in vids if v not in cache["audio"]]
    print(f"\nPhase B: {len(todo_audio)} audio to upload "
          f"({len(vids)-len(todo_audio)} cached)")
    def upload_audio(vid):
        return vid, upload_one_episode(mp3_dir / f"{vid}.mp3")
    with ThreadPoolExecutor(max_workers=args.audio_parallel) as ex:
        futs = [ex.submit(upload_audio, v) for v in todo_audio]
        for i, fut in enumerate(as_completed(futs), 1):
            try:
                vid, info = fut.result()
                cache["audio"][vid] = info
                if i % 5 == 0 or i == len(futs):
                    print(f"  audio {i}/{len(futs)} (last: {vid} dur={info['duration']}s)", flush=True)
                    cache_path.write_text(json.dumps(cache, ensure_ascii=False))
            except Exception as e:
                print(f"  ✗ audio: {e}", flush=True)
    cache_path.write_text(json.dumps(cache, ensure_ascii=False))

    # Phase C: build chapters[]. Field rules (see references/pitfalls.md):
    #   format: "opus"   — Yoto transcodes everything to Opus regardless of input
    #   duration: int    — seconds (NOT ms)
    #   overlayLabel     — REQUIRED on track, not just chapter
    #   channels         — "stereo" or "mono", detect from transcode result
    chapters, skipped = [], []
    for i, vid in enumerate(vids, 1):
        if vid not in cache["audio"] or vid not in subjects:
            skipped.append(vid); continue
        slug = slugify(subjects[vid])
        icon_id = cache["icons"].get(slug)
        if not icon_id:
            skipped.append(vid); continue
        a = cache["audio"][vid]
        key = f"{i:03d}"
        label = str(i)
        track = {
            "key": key,
            "title": titles[vid][:80],
            "overlayLabel": label,
            "trackUrl": f"yoto:#{a['transcodedSha256']}",
            "duration": int(a["duration"]),
            "fileSize": a["fileSize"],
            "channels": a.get("channels", "stereo"),
            "type": "audio",
            "format": "opus",
            "display": {"icon16x16": f"yoto:#{icon_id}"},
        }
        chapters.append({
            "key": key,
            "title": titles[vid][:80],
            "overlayLabel": label,
            "tracks": [track],
            "display": {"icon16x16": f"yoto:#{icon_id}"},
        })
    print(f"\nBuilt {len(chapters)} chapters; skipped {len(skipped)}")

    if len(chapters) > 100:
        sys.exit(f"ERROR: Yoto hard cap is 100 chapters per playlist; you have {len(chapters)}. "
                 "Use --limit or split into multiple cards.")

    if not args.go:
        print("\nDry run — pass --go to actually POST the update.")
        return

    total_duration = sum(t["tracks"][0]["duration"] for t in chapters)
    total_fileSize = sum(t["tracks"][0]["fileSize"] for t in chapters)
    payload = {
        "title": args.title,
        "metadata": {
            "description": f"{len(chapters)} episodes, auto-uploaded",
            "media": {
                "duration": total_duration,
                "fileSize": total_fileSize,
                "readableFileSize": round(total_fileSize / 1024 / 1024 * 10) / 10,
            },
            "cover": {"imageL": DEFAULT_COVER_URL},
        },
        "content": {
            "activity": "yoto_Player",
            "version": "1",
            "chapters": chapters,
            "config": {"onlineOnly": False},
        },
    }
    if args.card_id:
        payload["cardId"] = args.card_id
    print(f"\nPOSTing /content (cardId={args.card_id or '(new)'}, {len(chapters)} chapters)...")
    r = requests.post(f"{API}/content",
                      headers={**HDR, "Content-Type": "application/json"},
                      json=payload, timeout=120)
    print(f"Status: {r.status_code}")
    if r.status_code >= 400:
        print(r.text[:1000]); sys.exit(1)
    cid = r.json().get("card", r.json()).get("cardId")
    print(f"✓ Card {cid}: 「{args.title}」 — refresh Yoto app → Library")
    print(f"  Then scan a blank MYO card on the player and assign this playlist.")

if __name__ == "__main__":
    main()
