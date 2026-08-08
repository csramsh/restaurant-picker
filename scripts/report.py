#!/usr/bin/env python3
"""A one-screen health check on the restaurant list and history.

    python scripts/report.py

Read-only. Answers the questions that keep coming up: how many places are in
each area, which days are thin, what's still missing, and where the group has
and hasn't been. Use it before adding restaurants (to see where the gaps are)
and after a batch of edits (to see what moved).

For "is the data valid" use scripts/validate.py — that's the CI gate. This is
for "what does the data say".
"""

import csv
import io
import json
import sys
from collections import Counter
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402

ROOT = paths.ROOT
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# Phrases we use in notes to mean "somebody still needs to look at this".
OPEN_QUESTION = ["unconfirmed", "somebody check", "worth a menu check",
                 "needs looking up", "check the prices", "worth ringing ahead",
                 "second look"]


def month_index(m):
    y, mo = m.split("-")
    return int(y) * 12 + int(mo) - 1


def bar(n, scale=1):
    return "#" * int(n * scale)


def main():
    cfg = json.loads(paths.config_path().read_text(encoding="utf-8"))
    doc = yaml.safe_load(io.open(paths.restaurants_path(), encoding="utf-8"))
    places = doc["restaurants"]
    rows = list(csv.reader(
        io.open(paths.history_path(), encoding="utf-8").read().splitlines()))[1:]
    history = [r for r in rows if r and r[0].strip()]

    live = [r for r in places if r.get("active") is not False]
    normal = [r for r in live if r.get("category") != "special"]
    special = [r for r in live if r.get("category") == "special"]
    retired = [r for r in places if r.get("active") is False]
    by_id = {r["id"]: r for r in places}

    print()
    print("%d entries: %d in normal rotation, %d special occasion, %d retired"
          % (len(places), len(normal), len(special), len(retired)))

    # ---------------------------------------------------------------- areas
    n_by_area = Counter(r["area"] for r in normal)
    s_by_area = Counter(r["area"] for r in special)
    visits = Counter()
    last_visit = {}
    for month, rid, _notes in ((r + ["", "", ""])[:3] for r in history):
        place = by_id.get(rid.strip())
        if not place:
            continue
        area = place["area"]
        visits[area] += 1
        if area not in last_visit or month.strip() > last_visit[area]:
            last_visit[area] = month.strip()

    print()
    print("AREAS")
    print("  %-15s %6s %8s %7s  %s" % ("", "normal", "special", "visits", "last visit"))
    for area in cfg["areas"]:
        print("  %-15s %6d %8s %7d  %s" % (
            area,
            n_by_area[area],
            s_by_area[area] or "-",
            visits[area],
            last_visit.get(area, "never"),
        ))
    thin = [a for a in cfg["areas"] if 0 < n_by_area[a] <= 2]
    empty = [a for a in cfg["areas"] if n_by_area[a] == 0]
    if thin:
        print("  thin (2 or fewer): " + ", ".join(thin))
    if empty:
        print("  no normal options: " + ", ".join(empty))

    # ------------------------------------------------------------ day cover
    print()
    print("OPEN AT %s, BY DAY  (normal rotation only)" % paths.start_label().upper())
    per_day = Counter()
    for r in normal:
        for d in (r.get("open_days") or " ".join(DAYS)).split():
            per_day[d] += 1
    worst = min(per_day[d] for d in DAYS) if per_day else 0
    for d in DAYS:
        flag = "  <- thinnest" if per_day[d] == worst and worst else ""
        print("  %-4s %3d  %s%s" % (d, per_day[d], bar(per_day[d]), flag))

    # ----------------------------------------------------------------- gaps
    no_addr = [r for r in live if not r.get("address")]
    no_days = [r for r in live if not r.get("open_days")]
    questions = [r for r in live
                 if any(p in (r.get("notes") or "").lower() for p in OPEN_QUESTION)]

    print()
    print("GAPS")
    print("  no address:    %d%s" % (
        len(no_addr), "  " + ", ".join(r["name"] for r in no_addr) if no_addr else ""))
    print("  no open_days:  %d%s" % (
        len(no_days), "  " + ", ".join(r["name"] for r in no_days) if no_days else ""))
    print("  open questions in notes: %d" % len(questions))
    for r in questions:
        print("     %s (%s)" % (r["name"], r["area"]))

    # -------------------------------------------------------------- history
    print()
    if history:
        months = sorted(r[0].strip() for r in history)
        span = month_index(months[-1]) - month_index(months[0]) + 1
        print("HISTORY  %d meetups, %s to %s (%d months, %d with no record)"
              % (len(history), months[0], months[-1], span, span - len(history)))
    else:
        print("HISTORY  nothing recorded yet")

    never = [r for r in normal
             if r["id"] not in {h[1].strip() for h in history}]
    print("  never visited: %d of %d in normal rotation" % (len(never), len(normal)))
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
