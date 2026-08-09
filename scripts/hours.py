#!/usr/bin/env python3
"""Fill in the open_days field on data/restaurants.yaml.

open_days lists the days a place is open AND still serving at our start time,
which is the distinction that's easy to get wrong by hand. This script does
that conversion for you.

    python scripts/hours.py todo
        List the restaurants still missing open_days, with a Google Maps link
        for each. Work down it, copy the hours off the listing, and use `set`.

    python scripts/hours.py set sconyers-bbq "Thu-Sat 10:00 am - 9:00 pm"
        Parse those hours, work out which days they're still serving at the
        group's start time, and write open_days into the YAML.
        Add --dry-run to see it first.

    python scripts/hours.py check "Mon-Fri 11am-8pm, Sat 11am-10pm, Sun closed"
        Parse without touching anything. Useful for sanity-checking a format.

    python scripts/hours.py fetch [--apply]
        Optional. Uses the Google Places API to look up everything still
        missing, if you have a key. See "Google Places" below.

If the hours are in a shape it can't read with confidence, it says so and
writes nothing rather than guessing. Re-run it as often as you like — it only
ever touches entries you name.

GOOGLE PLACES
  `fetch` needs an API key in the GOOGLE_MAPS_API_KEY environment variable.
  Getting one means a Google Cloud project with billing enabled; the lookups
  themselves sit inside the monthly free allowance at this volume, but a card
  has to be on file. That's why it's optional and nothing depends on it.

  NEVER commit a key. It goes in the environment, not in this repo.

  We do not scrape Google Maps. It's against their terms, and a scraper would
  rot silently and leave us trusting stale hours.
"""

import argparse
import io
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402

ROOT = paths.ROOT
YAML_PATH = paths.restaurants_path()

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
DAY_INDEX = {d.lower(): i for i, d in enumerate(DAYS)}
DAY_WORDS = {
    "monday": 0, "mon": 0, "mo": 0, "m": 0,
    "tuesday": 1, "tues": 1, "tue": 1, "tu": 1,
    "wednesday": 2, "weds": 2, "wed": 2, "we": 2,
    "thursday": 3, "thurs": 3, "thur": 3, "thu": 3, "th": 3,
    "friday": 4, "fri": 4, "fr": 4, "f": 4,
    "saturday": 5, "sat": 5, "sa": 5,
    "sunday": 6, "sun": 6, "su": 6,
}
# listings often pluralise: "closed Tuesdays", "open Saturdays"
for _word, _i in list(DAY_WORDS.items()):
    if len(_word) > 2:
        DAY_WORDS.setdefault(_word + "s", _i)
# "Open" means "still serving when we arrive", not merely open at some point.
# The time comes from "startTime" in config.json.
START_MINUTES = paths.start_minutes()
START_LABEL = paths.start_label()

DAY_ALT = "|".join(sorted(DAY_WORDS, key=len, reverse=True))
RANGE_SEP = r"(?:-|to|thru|through|until|til)"
# \b matters: without it the one-letter tokens ("m" for Monday) match inside
# words like "AM" and "PM".
DAY_SPEC = rf"\b(?:{DAY_ALT})\b(?:\s*(?:{RANGE_SEP}|,|&|and|\+)\s*\b(?:{DAY_ALT})\b)*"
TIME = r"\d{1,2}(?::\d{2})?\s*(?:a\.?m\.?|p\.?m\.?)?"
TIME_RANGE = rf"{TIME}\s*(?:-|to|until|til)\s*{TIME}"
SEGMENT = re.compile(
    rf"(?P<days>{DAY_SPEC}|daily|every\s*day|all\s*week|7\s*days)?"
    rf"\s*:?\s*"
    rf"(?P<times>{TIME_RANGE}|closed|open\s*24\s*hours)",
    re.I,
)


class Unreadable(Exception):
    """The hours string isn't in a shape we can trust."""


def normalise(text):
    text = text.replace("–", "-").replace("—", "-").replace("−", "-")
    text = text.replace(" ", " ")
    text = re.sub(r"\bnoon\b", "12:00 pm", text, flags=re.I)
    text = re.sub(r"\bmidnight\b", "12:00 am", text, flags=re.I)
    text = re.sub(r"\bopen\b(?!\s*24)", " ", text, flags=re.I)
    # "Closed Tuesdays" -> "Tuesdays closed", so it reads days-then-state like
    # everything else.
    #
    # Only when "closed" opens a clause. Google's own listings run the days
    # together as "Sunday Closed Monday Closed Tuesday 11AM-9PM", where each
    # "Closed" belongs to the day BEFORE it — rewriting those would silently
    # shift every day by one.
    text = re.sub(rf"(^|[;,.]\s*)closed\s+(?:on\s+)?(?P<days>{DAY_SPEC})",
                  lambda m: m.group(1) + m.group("days") + " closed",
                  text, flags=re.I)
    return re.sub(r"\s+", " ", text).strip()


def parse_day_spec(spec):
    """'Mon-Thu' or 'Fri, Sat' or 'daily' -> set of day indexes."""
    spec = spec.strip().lower()
    if re.fullmatch(r"daily|every\s*day|all\s*week|7\s*days", spec):
        return set(range(7))

    days = set()
    for chunk in re.split(r"\s*(?:,|&|and|\+)\s*", spec):
        chunk = chunk.strip()
        if not chunk:
            continue
        bounds = re.split(rf"\s*(?:{RANGE_SEP})\s*", chunk)
        bounds = [b.strip(" .") for b in bounds if b.strip(" .")]
        if len(bounds) == 1:
            if bounds[0] not in DAY_WORDS:
                raise Unreadable("don't recognise the day %r" % bounds[0])
            days.add(DAY_WORDS[bounds[0]])
        elif len(bounds) == 2:
            if bounds[0] not in DAY_WORDS or bounds[1] not in DAY_WORDS:
                raise Unreadable("don't recognise the day range %r" % chunk)
            a, b = DAY_WORDS[bounds[0]], DAY_WORDS[bounds[1]]
            i = a
            days.add(i)
            while i != b:                 # wraps, so Wed-Mon works
                i = (i + 1) % 7
                days.add(i)
        else:
            raise Unreadable("don't recognise the day range %r" % chunk)
    return days


def parse_time(text):
    """'9', '9:30pm', '21:00' -> minutes since midnight."""
    m = re.fullmatch(r"(\d{1,2})(?::(\d{2}))?\s*(a\.?m\.?|p\.?m\.?)?", text.strip(), re.I)
    if not m:
        raise Unreadable("don't recognise the time %r" % text)
    hour, minute = int(m.group(1)), int(m.group(2) or 0)
    suffix = (m.group(3) or "").replace(".", "").lower()
    if suffix == "pm" and hour != 12:
        hour += 12
    elif suffix == "am" and hour == 12:
        hour = 0
    elif not suffix and hour <= 11:
        # "11-9" almost always means 11am to 9pm for a restaurant, but we
        # won't guess about the opening time without a suffix somewhere.
        pass
    if hour > 24:
        raise Unreadable("hour out of range in %r" % text)
    return hour * 60 + minute


def serving_at_start(open_min, close_min):
    if close_min <= open_min:      # closes after midnight
        close_min += 24 * 60
    return open_min <= START_MINUTES < close_min


def parse_hours(text):
    """Hours text -> sorted day names still serving at the start time."""
    text = normalise(text)
    if not text:
        raise Unreadable("empty")

    matches = list(SEGMENT.finditer(text))
    if not matches:
        raise Unreadable("found no 'days + times' pairs in %r" % text)

    covered = "".join(m.group(0) for m in matches)
    if len(covered) < len(re.sub(r"[;,.\s]", "", text)) * 0.5:
        raise Unreadable("only understood part of %r" % text)

    serving, closed, seen_any_days = set(), set(), False
    last_days = None
    for m in matches:
        spec, times = m.group("days"), m.group("times").lower()
        if spec:
            days = parse_day_spec(spec)
            last_days = days
            seen_any_days = True
        elif last_days is not None:
            # Split service: "Friday 11:30 AM-2:30 PM 5-10 PM" gives two ranges
            # for one day. A range with no day of its own belongs to the day
            # above it, not to the whole week.
            days = last_days
        else:
            # Nothing but times, e.g. "5:00 pm - 9:30 pm" — assume every day.
            days = set(range(7))

        if times == "closed":
            closed |= days
            continue
        if re.fullmatch(r"open\s*24\s*hours", times):
            serving |= days
            continue

        parts = re.split(r"\s*(?:-|to|until|til)\s*", times)
        if len(parts) != 2:
            raise Unreadable("don't recognise the time range %r" % times)
        o, c = parse_time(parts[0]), parse_time(parts[1])
        # "11-9" with no am/pm: a 9am close is implausible for dinner service
        if c < o and c + 12 * 60 <= 24 * 60 and not re.search(r"a\.?m|p\.?m", times):
            c += 12 * 60
        if serving_at_start(o, c):
            serving |= days

    if not seen_any_days and not serving and not closed:
        raise Unreadable("no days found in %r" % text)

    result = sorted(serving - closed)
    return [DAYS[i] for i in result]


# ----------------------------------------------------------------- the file

def load_entries():
    """Minimal read of id/name/area/address/open_days/active, in file order."""
    lines = io.open(YAML_PATH, encoding="utf-8").read().split("\n")
    entries, cur = [], None
    for i, line in enumerate(lines):
        m = re.match(r"^  - id:\s*(\S+)\s*$", line)
        if m:
            cur = {"id": m.group(1), "line": i, "fields": {}}
            entries.append(cur)
            continue
        if cur is not None:
            f = re.match(r"^    (\w+):\s*(.*)$", line)
            if f:
                cur["fields"][f.group(1)] = f.group(2).strip()
    return lines, entries


def maps_url(e):
    f = e["fields"]
    where = f.get("address")
    if not where:
        area = f.get("area", "")
        region = paths.region_for(area)
        where = area + (", " + region if region else "")
    return ("https://www.google.com/maps/search/?api=1&query=" +
            urllib.parse.quote(f.get("name", "") + ", " + where))


def write_open_days(lines, entry, days):
    """Insert or replace the open_days line for one entry."""
    start = entry["line"]
    end = len(lines)
    for j in range(start + 1, len(lines)):
        if re.match(r"^  - id:", lines[j]) or lines[j].startswith("  # ==="):
            end = j
            break
    value = "    open_days: " + " ".join(days)
    for j in range(start, end):
        if re.match(r"^    open_days:", lines[j]):
            lines[j] = value
            return lines
    anchor = start
    for j in range(start, end):
        if re.match(r"^    (cuisine|address|area):", lines[j]):
            anchor = j
    lines.insert(anchor + 1, value)
    return lines


def save(lines):
    io.open(YAML_PATH, "w", encoding="utf-8", newline="\n").write("\n".join(lines))


def missing(entries):
    return [e for e in entries
            if e["fields"].get("active", "yes") != "no"
            and not e["fields"].get("open_days")]


# ------------------------------------------------------------------ commands

def cmd_todo(args):
    _, entries = load_entries()
    todo = missing(entries)
    if not todo:
        print("Every active restaurant has open_days. Nothing to do.")
        return 0
    print("%d restaurants still need open_days.\n" % len(todo))
    print("Open the link, copy the opening hours, then run:")
    print('  python scripts/hours.py set <id> "<the hours you copied>"\n')
    for e in todo:
        f = e["fields"]
        print("%-26s %s" % (e["id"], f.get("name", "")))
        print("   %s\n" % maps_url(e))
    return 0


def cmd_check(args):
    try:
        days = parse_hours(args.hours)
    except Unreadable as exc:
        print("Could not read those hours: %s" % exc)
        print("Write them out day by day, e.g. \"Mon-Fri 11am-9pm, Sat 11am-10pm, Sun closed\".")
        return 1
    if not days:
        print("open_days: (none) - never serving at %s, so it can't host us." % START_LABEL)
    else:
        print("open_days: " + " ".join(days))
    return 0


def cmd_set(args):
    blocked = paths.require_own_data("record opening hours against")
    if blocked:
        print(blocked)
        return 1
    lines, entries = load_entries()
    match = [e for e in entries if e["id"] == args.id]
    if not match:
        print('No restaurant with id "%s".' % args.id)
        return 1
    try:
        days = parse_hours(args.hours)
    except Unreadable as exc:
        print("Could not read those hours: %s" % exc)
        print("Nothing was written. Try writing them day by day, e.g.")
        print('  "Mon-Fri 11am-9pm, Sat 11am-10pm, Sun closed"')
        return 1

    name = match[0]["fields"].get("name", args.id)
    if not days:
        print("%s is never serving at %s on those hours." % (name, START_LABEL))
        print("Leave open_days off and set active: no with a note, the way we")
        print("did for K and J Soul Bar and Grill.")
        return 1

    print("%s -> open_days: %s" % (name, " ".join(days)))
    if args.dry_run:
        print("(dry run, nothing written)")
        return 0
    save(write_open_days(lines, match[0], days))
    print("Written. Run scripts/validate.py to check the file.")
    return 0


def cmd_fetch(args):
    if args.apply:
        blocked = paths.require_own_data("record opening hours against")
        if blocked:
            print(blocked)
            return 1
    key = os.environ.get("GOOGLE_MAPS_API_KEY")
    if not key:
        print("No GOOGLE_MAPS_API_KEY in the environment, so there's nothing to")
        print("fetch with. This step is optional - use `todo` and `set` instead.")
        print("See the notes at the top of this file.")
        return 1

    lines, entries = load_entries()
    todo = missing(entries)
    print("Looking up %d restaurants via the Google Places API.\n" % len(todo))
    done, failed = 0, []
    for e in todo:
        f = e["fields"]
        query = f.get("name", "") + ", " + (f.get("address") or f.get("area", ""))
        body = json.dumps({"textQuery": query, "maxResultCount": 1}).encode()
        req = urllib.request.Request(
            "https://places.googleapis.com/v1/places:searchText",
            data=body,
            headers={
                "Content-Type": "application/json",
                "X-Goog-Api-Key": key,
                "X-Goog-FieldMask":
                    "places.displayName,places.regularOpeningHours.weekdayDescriptions",
            },
        )
        try:
            data = json.load(urllib.request.urlopen(req, timeout=30))
            places = data.get("places") or []
            desc = places[0]["regularOpeningHours"]["weekdayDescriptions"]
            days = parse_hours("; ".join(desc))
        except Exception as exc:
            failed.append((e["id"], type(exc).__name__))
            continue
        if not days:
            failed.append((e["id"], "never open at " + START_LABEL))
            continue
        print("  %-26s %s" % (e["id"], " ".join(days)))
        if args.apply:
            lines = write_open_days(lines, e, days)
        done += 1

    if args.apply and done:
        save(lines)
        print("\nWrote %d entries. Run scripts/validate.py." % done)
    elif done:
        print("\n%d resolved. Re-run with --apply to write them." % done)
    if failed:
        print("\nCouldn't resolve %d — do these by hand with `todo`/`set`:" % len(failed))
        for rid, why in failed:
            print("  %-26s %s" % (rid, why))
    return 0


def main():
    p = argparse.ArgumentParser(
        description="Fill in open_days on the restaurant list.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("todo", help="list restaurants still missing open_days")

    s = sub.add_parser("set", help="parse hours and write open_days for one restaurant")
    s.add_argument("id")
    s.add_argument("hours")
    s.add_argument("--dry-run", action="store_true")

    c = sub.add_parser("check", help="parse hours without writing anything")
    c.add_argument("hours")

    fe = sub.add_parser("fetch", help="optional: look everything up via Google Places")
    fe.add_argument("--apply", action="store_true")

    args = p.parse_args()
    return {"todo": cmd_todo, "set": cmd_set,
            "check": cmd_check, "fetch": cmd_fetch}[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
