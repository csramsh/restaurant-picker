#!/usr/bin/env python3
"""Set this fork up as your group's own picker.

    python scripts/setup.py
    python scripts/setup.py --name "Rambling Club" --blank-history

Copies the shipped examples to the paths the site prefers:

    config.example.json        ->  config.json
    data/example/restaurants.yaml  ->  data/restaurants.yaml
    data/example/history.csv       ->  data/history.csv

It **copies, never moves**. The originals stay exactly where they are, which
is what keeps "Sync fork" a one-click operation forever — upstream only ever
touches its own files, you only ever touch yours. Nothing here deletes
anything, and it refuses to overwrite files you've already made.

Afterwards, edit your new `config.json` and `data/restaurants.yaml`. The
example copies underneath keep working as a reference.
"""

import argparse
import io
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402

COPIES = [
    (paths.EXAMPLE_CONFIG, paths.REAL_CONFIG),
    (paths.EXAMPLE_RESTAURANTS, paths.REAL_RESTAURANTS),
    (paths.EXAMPLE_HISTORY, paths.REAL_HISTORY),
]


def rel(p):
    return p.relative_to(paths.ROOT).as_posix()


def main():
    ap = argparse.ArgumentParser(
        description="Copy the example data into place so this fork is yours.")
    ap.add_argument("--name", help='Your group\'s name, e.g. "Rambling Club"')
    ap.add_argument("--blank-history", action="store_true",
                    help="Start history.csv empty instead of copying the example rows")
    args = ap.parse_args()

    made, skipped = [], []
    for src, dst in COPIES:
        if dst.exists():
            skipped.append(dst)
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        made.append(dst)

    if args.blank_history and paths.REAL_HISTORY in made:
        io.open(paths.REAL_HISTORY, "w", encoding="utf-8", newline="\n").write(
            "month,restaurant_id,notes\n")

    # Tweak the fresh config if the caller told us anything about the group.
    if args.name and paths.REAL_CONFIG in made:
        cfg = json.loads(paths.REAL_CONFIG.read_text(encoding="utf-8"))
        if args.name:
            cfg["groupName"] = args.name
        io.open(paths.REAL_CONFIG, "w", encoding="utf-8", newline="\n").write(
            json.dumps(cfg, indent=2, ensure_ascii=False) + "\n")

    for p in made:
        print("created  %s" % rel(p))
    for p in skipped:
        print("kept     %s (already exists, left untouched)" % rel(p))

    if not made:
        print()
        print("Nothing to do - this fork is already set up.")
        return 0

    print()
    print("Now make it yours:")
    print("  1. Edit config.json - group name, areas, cooldowns.")
    print("  2. Replace the entries in data/restaurants.yaml with real places.")
    print("  3. Empty data/history.csv down to its header, unless you have")
    print("     past meetups to backfill.")
    print("  4. python scripts/validate.py")
    print()
    print("Leave config.example.json and data/example/ where they are. They")
    print("belong to upstream, they cost nothing, and deleting them will cause")
    print("merge conflicts the next time you sync.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
