#!/usr/bin/env python3
"""Tests for the opening-hours parser in hours.py.

    python scripts/test_hours.py

Every case here came from a real listing. If you teach the parser a new
format, add the example that prompted it — the awkward ones are why this file
exists.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hours import parse_hours, Unreadable  # noqa: E402

# How Google Maps lays hours out when you copy them: day and times on separate
# lines, and "Closed" following the day it belongs to. Getting this wrong once
# shifted every day by one and wrote bad data, hence the test.
GOOGLE_PASTE = """Friday
11 AM–10 PM

Saturday
11 AM–10 PM

Sunday
Closed

Monday
Closed

Tuesday
11 AM–9:30 PM

Wednesday
11 AM–9:30 PM

Thursday
11 AM–9:30 PM"""

# (hours text, expected open_days, why it's here)
CASES = [
    (GOOGLE_PASTE, "Tue Wed Thu Fri Sat",
     "Google's copy format, Closed trailing its own day"),
    ("Monday Closed Tuesday 11 AM–9 PM", "Tue",
     "same shape, run together on one line"),
    ("Closed Tuesdays; Wednesday-Monday 4:30 pm - 9:00 pm", "Mon Wed Thu Fri Sat Sun",
     "Closed leading a clause, and a day range that wraps the week"),
    ("""Friday
11:30 AM–2:30 PM
5–10 PM

Saturday
11:30 AM–2:30 PM
5–10 PM

Sunday
11:30 AM–2:30 PM

Monday
11:30 AM–2:30 PM
5–9 PM

Tuesday
11:30 AM–2:30 PM
5–9 PM

Wednesday
11:30 AM–2:30 PM
5–9 PM

Thursday
11:30 AM–2:30 PM
5–9 PM""", "Mon Tue Wed Thu Fri Sat",
     "split lunch/dinner service. Sunday is lunch only, so it must drop out — "
     "a second range with no day of its own belongs to the day above it"),
    ("Thursday-Saturday 10:00 am - 9:00 pm", "Thu Fri Sat", "Sconyers"),
    ("Wed-Sat 11:00 am - 9:00 pm", "Wed Thu Fri Sat", "Augsburg Haus"),
    ("Monday-Friday 11:00 am - 8:00 pm", "Mon Tue Wed Thu Fri", "Goolsby's"),
    ("Tue-Fri 11am-6pm, Sun 11am-4pm", "",
     "K and J: shuts at 6, so never serving at our 6:30 start"),
    ("Mo-Fr 09:00-17:00", "", "OpenStreetMap style, closes before we start"),
    ("Mo-Th 11:00-21:30; Fr,Sa 11:00-22:00; Su 12:00-21:30",
     "Mon Tue Wed Thu Fri Sat Sun", "OSM style with a comma-joined day list"),
    ("We-Mo 11:00-21:00", "Mon Wed Thu Fri Sat Sun", "wrapping range, Tue off"),
    ("Mon-Sat 10:30 am - 11:00 pm; Su closed", "Mon Tue Wed Thu Fri Sat",
     "closed trailing, already in the right order"),
    ("Mon 4:30pm-10pm, Tue closed, Wed-Thu 4:30pm-10pm, Fri-Sat 4:30pm-10:30pm",
     "Mon Wed Thu Fri Sat", "Fukuro: mid-list closure"),
    ("Sunday 11:00 AM – 9:00 PM; Monday 11:00 AM – 10:00 PM", "Mon Sun",
     "en-dashes and full day names"),
    ("Daily 11am-10pm", "Mon Tue Wed Thu Fri Sat Sun", "no day list at all"),
    ("5:00 pm - 9:30 pm", "Mon Tue Wed Thu Fri Sat Sun", "bare range, assume every day"),
    ("Open 24 hours", "Mon Tue Wed Thu Fri Sat Sun", "always open"),
    ("Mon-Fri 11-9, Sat 11-10", "Mon Tue Wed Thu Fri Sat", "no am/pm markers"),
    ("call ahead lol", None, "nonsense must be refused, not guessed at"),
    ("", None, "empty must be refused"),
]


def main():
    failures = []
    for text, expected, why in CASES:
        label = " ".join(text.split())[:52] or "(empty)"
        try:
            got = " ".join(parse_hours(text))
            ok = expected is not None and got == expected
        except Unreadable:
            got, ok = "REFUSED", expected is None
        if ok:
            print("  ok    %-52s %s" % (label, got or "(none)"))
        else:
            failures.append((label, got, expected, why))
            print("  FAIL  %-52s got %r, wanted %r" % (label, got, expected))

    print()
    if failures:
        print("%d of %d failed." % (len(failures), len(CASES)))
        for label, got, expected, why in failures:
            print("  - %s\n      %s\n      got %r wanted %r" % (label, why, got, expected))
        return 1
    print("All %d passed." % len(CASES))
    return 0


if __name__ == "__main__":
    sys.exit(main())
