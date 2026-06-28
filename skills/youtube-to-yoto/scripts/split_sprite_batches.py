#!/usr/bin/env python3
"""
Dedupe subjects → unique slugs → split into N batches for parallel sprite gen.

Usage:
    python3 split_sprite_batches.py <subjects.json> <out_dir> [N=20]

After this:
- Dispatch N Opus SubAgents, each reading <out_dir>/batch_NN.json
- See references/pixel-art-design.md for the prompt template
- Each agent saves sprites to pixel_subjects/{slug}.png
"""

import json, re, sys
from pathlib import Path

if len(sys.argv) < 3:
    sys.exit("Usage: split_sprite_batches.py <subjects.json> <out_dir> [N=20]")

SUBJECTS, OUT_DIR = sys.argv[1:3]
N = int(sys.argv[3]) if len(sys.argv) > 3 else 20

def slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9-]+", "-", s.lower().strip()).strip("-")

subjects = json.loads(Path(SUBJECTS).read_text())
unique = sorted({s for s in subjects.values()})
todo = [{"subject": s, "slug": slugify(s)} for s in unique]

Path(OUT_DIR).mkdir(parents=True, exist_ok=True)
batches = [todo[i::N] for i in range(N)]
for i, batch in enumerate(batches):
    Path(f"{OUT_DIR}/batch_{i:02d}.json").write_text(
        json.dumps(batch, ensure_ascii=False, indent=2)
    )

# Save dedup metadata for reference
Path(f"{OUT_DIR}/_unique_subjects.json").write_text(
    json.dumps(unique, ensure_ascii=False, indent=2)
)

print(f"{len(subjects)} vids → {len(unique)} unique subjects → {N} batches of {len(batches[0])}-{len(batches[-1])} each")
print(f"Batches in {OUT_DIR}")
print(f"\nNext: dispatch {N} Opus SubAgents — see references/pixel-art-design.md")
