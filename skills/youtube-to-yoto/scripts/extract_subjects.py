#!/usr/bin/env python3
"""
Split a manifest CSV into N batches for parallel SubAgent subject extraction.

Each batch is a JSON array of {vid, title, transcript_file} entries — feed
each batch to one Sonnet SubAgent with the prompt template in
references/workflow.md "Subject extraction".

Usage:
    python3 extract_subjects.py <manifest.csv> <transcript_dir> <out_dir> [N=20]

Outputs <out_dir>/batch_NN.json files.
After agents complete, merge their outputs:
    python3 -c "
import json, glob
m = {}
for f in sorted(glob.glob('<output_dir>/batch_*.json')):
    m.update(json.load(open(f)))
json.dump(m, open('subjects.json','w'), ensure_ascii=False, indent=2)
"
"""

import csv, json, sys
from pathlib import Path

if len(sys.argv) < 4:
    sys.exit("Usage: extract_subjects.py <manifest.csv> <transcript_dir> <out_dir> [N=20]")

CSV_PATH, TR_DIR, OUT_DIR = sys.argv[1:4]
N = int(sys.argv[4]) if len(sys.argv) > 4 else 20

Path(OUT_DIR).mkdir(parents=True, exist_ok=True)

rows = []
with open(CSV_PATH, encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
        vid = r.get("video_id") or r.get("vid")
        if not vid: continue
        if not (Path(TR_DIR) / f"{vid}.txt").exists():
            continue   # skip vids without transcripts
        rows.append({
            "vid":       vid,
            "title":     (r.get("story_name") or r.get("title") or "")[:80],
            "original":  (r.get("title") or "")[:120],
            "transcript_file": str(Path(TR_DIR) / f"{vid}.txt"),
        })

batches = [rows[i::N] for i in range(N)]
for i, batch in enumerate(batches):
    Path(f"{OUT_DIR}/batch_{i:02d}.json").write_text(
        json.dumps(batch, ensure_ascii=False, indent=2)
    )
print(f"{len(rows)} vids → {N} batches of {len(batches[0])}-{len(batches[-1])} each")
print(f"Batches in {OUT_DIR}")
print(f"\nNext: dispatch {N} Sonnet SubAgents, each reading batch_NN.json")
print(f"      See references/workflow.md 'Phase 3' for the prompt template")
