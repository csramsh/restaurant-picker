#!/usr/bin/env python3
"""Check that the data files are well formed before they reach the site.

Run automatically on every pull request and push. You can also run it locally:

    python scripts/validate.py

It exits non-zero and prints plain-English problems if something is wrong.
"""

import csv
import json
import re
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402

ROOT = paths.ROOT
ALLOWED_KEYS = {"id", "name", "area", "address", "cuisine", "open_days",
                "category", "notes", "active", "unavailable_until"}
REQUIRED_KEYS = {"id", "name", "area"}
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
MONTH_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
CATEGORIES = {"normal", "special"}

errors: list[str] = []
warnings: list[str] = []


def load_config():
    path = paths.config_path()
    try:
        cfg = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"config.json is not valid JSON: {exc}")
        return None
    if not isinstance(cfg.get("areas"), list) or not cfg["areas"]:
        errors.append("config.json needs a non-empty \"areas\" list.")
        return None
    for key in ("candidatesPerMonth", "areaCooldownMonths", "restaurantCooldownMonths"):
        if not isinstance(cfg.get(key), int):
            errors.append(f'config.json is missing the whole number "{key}".')

    # A misspelled area here does nothing at all rather than failing loudly,
    # so the map links for that area would quietly use the wrong state.
    overrides = cfg.get("areaRegions")
    if overrides is not None:
        if not isinstance(overrides, dict):
            errors.append('config.json "areaRegions" must be a set of '
                          '"Area": "Region" pairs.')
        else:
            for area in overrides:
                if area not in cfg["areas"]:
                    errors.append(
                        f'config.json "areaRegions" mentions "{area}", which is '
                        "not in the areas list. Allowed: " + ", ".join(cfg["areas"])
                    )
    return cfg


def load_restaurants(areas):
    path = paths.restaurants_path()
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        errors.append(
            "data/restaurants.yaml could not be read. This is almost always an "
            f"indentation problem. Details:\n{exc}"
        )
        return {}

    if not isinstance(doc, dict) or not isinstance(doc.get("restaurants"), list):
        errors.append(
            'data/restaurants.yaml must have a top-level "restaurants:" key '
            "with a list underneath it."
        )
        return {}

    by_id = {}
    for index, entry in enumerate(doc["restaurants"], start=1):
        where = f"restaurant #{index}"
        if not isinstance(entry, dict):
            errors.append(f"{where} is not a set of field: value lines.")
            continue

        rid = entry.get("id")
        if isinstance(rid, str) and rid:
            where = f'restaurant "{rid}"'

        missing = REQUIRED_KEYS - {k for k, v in entry.items() if v not in (None, "")}
        for key in sorted(missing):
            errors.append(f"{where} is missing {key}.")

        for key in sorted(set(entry) - ALLOWED_KEYS):
            errors.append(
                f'{where} has an unexpected field "{key}". Allowed fields: '
                + ", ".join(sorted(ALLOWED_KEYS))
            )

        if isinstance(rid, str) and rid:
            if not ID_RE.match(rid):
                errors.append(
                    f'{where}: id must be lowercase letters, numbers and dashes only.'
                )
            if rid in by_id:
                errors.append(f'Two restaurants share the id "{rid}". Ids must be unique.')
            by_id[rid] = entry

        area = entry.get("area")
        if area is not None and area not in areas:
            errors.append(
                f'{where} has area "{area}", which is not in the areas list in '
                "config.json. Allowed: " + ", ".join(areas)
            )

        active = entry.get("active")
        if active is not None and not isinstance(active, bool):
            errors.append(
                f'{where}: active must be yes or no (got "{active}"). Quoting it '
                "turns it into text, so leave the quotes off."
            )

        category = entry.get("category")
        if category is not None and category not in CATEGORIES:
            errors.append(
                f'{where}: category must be normal or special (got "{category}").'
            )

        open_days = entry.get("open_days")
        if open_days is not None:
            if not isinstance(open_days, str):
                errors.append(
                    f"{where}: open_days must be days separated by spaces, like "
                    "Mon Tue Wed. Don't use a YAML list."
                )
            else:
                seen_days = []
                for token in open_days.split():
                    if token not in DAYS:
                        errors.append(
                            f'{where}: open_days has "{token}", which is not a day. '
                            "Use " + " ".join(DAYS) + "."
                        )
                    elif token in seen_days:
                        errors.append(f'{where}: open_days lists {token} twice.')
                    else:
                        seen_days.append(token)
                if not seen_days and not errors:
                    warnings.append(
                        f"{where}: open_days is empty. Leave the field out "
                        "entirely if you don't know the hours."
                    )

        # A pause with no stated reason is indistinguishable from a mistake by
        # the time anyone reads it, and an expired one is invisible without
        # report.py, so both get flagged here rather than sitting silently.
        until = entry.get("unavailable_until")
        if until is not None:
            if not isinstance(until, str) or not MONTH_RE.match(until):
                errors.append(
                    f'{where}: unavailable_until must be a month like 2026-10 '
                    f'(got "{until}"). It means "back in that month".'
                )
            elif not entry.get("notes"):
                warnings.append(
                    f"{where} is paused with unavailable_until but has no notes "
                    "saying why. In a month nobody will remember."
                )
            if entry.get("active") is False:
                warnings.append(
                    f"{where} is both retired and paused. active: no already "
                    "keeps it out of the draw, so unavailable_until does "
                    "nothing here - drop one of them."
                )

        if not entry.get("address"):
            warnings.append(f"{where} has no address yet.")

    # Names are just names. Where a place is lives in area and address, so two
    # branches of the same chain are told apart by those.
    for rid, entry in by_id.items():
        name, area = entry.get("name"), entry.get("area")
        if isinstance(name, str) and isinstance(area, str) and area:
            if area.lower() in name.lower():
                warnings.append(
                    f'restaurant "{rid}": name "{name}" repeats the area. Take '
                    "the location out of the name — the site adds the area for "
                    "you, so this would read as \"... — " + area + '".'
                )

    # ...but two live places with the same name in the same area really are
    # indistinguishable on a poll.
    pairs = {}
    for rid, entry in by_id.items():
        if entry.get("active") is False:
            continue
        key = (str(entry.get("name", "")).lower(), str(entry.get("area", "")))
        pairs.setdefault(key, []).append(rid)
    for (name, area), ids in pairs.items():
        if len(ids) > 1:
            errors.append(
                f'{len(ids)} active restaurants are called "{name}" in {area} '
                f"({', '.join(sorted(ids))}). Nobody could tell them apart on a "
                "poll — give them distinguishing names or check for a duplicate."
            )

    if not by_id:
        errors.append("No usable restaurants found.")
    return by_id


def load_history(by_id):
    path = paths.history_path()
    rows = list(csv.reader(path.read_text(encoding="utf-8").splitlines()))
    if not rows:
        errors.append("data/history.csv is completely empty; it needs a header row.")
        return

    header = [c.strip() for c in rows[0]]
    if header[:3] != ["month", "restaurant_id", "notes"]:
        errors.append(
            "data/history.csv's first line must be exactly: month,restaurant_id,notes"
        )
        return

    seen_months = {}
    for line_no, row in enumerate(rows[1:], start=2):
        if not row or not any(c.strip() for c in row):
            continue
        if len(row) != 3:
            errors.append(
                f"data/history.csv line {line_no} has {len(row)} values but needs "
                "exactly 3 (month,restaurant_id,notes). If a note contains a comma, "
                'wrap the note in "double quotes".'
            )
            continue

        month, rid, _notes = (c.strip() for c in row)
        if not MONTH_RE.match(month):
            errors.append(
                f'data/history.csv line {line_no}: "{month}" is not a valid month. '
                "Use the form 2026-08."
            )
        if rid not in by_id:
            errors.append(
                f'data/history.csv line {line_no} points at "{rid}", which is not '
                "an id in data/restaurants.yaml. Check for a typo, and remember "
                "that retiring a place means setting active: no rather than "
                "deleting it."
            )
        if month in seen_months:
            warnings.append(
                f"data/history.csv has more than one entry for {month} "
                f"(lines {seen_months[month]} and {line_no}). That's allowed, but "
                "double-check it's intentional."
            )
        else:
            seen_months[month] = line_no


def main():
    cfg = load_config()
    if cfg is None:
        report()
    by_id = load_restaurants(cfg["areas"])
    load_history(by_id)
    report()


def report():
    for w in warnings:
        print(f"note: {w}")
    if errors:
        print()
        print(f"{len(errors)} problem(s) found:")
        for e in errors:
            print(f"  - {e}")
        print()
        print("Fix these and push again. If you're stuck, see RUNBOOK.md.")
        sys.exit(1)
    print()
    print("Data looks good.")
    sys.exit(0)


if __name__ == "__main__":
    main()
