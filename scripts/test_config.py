#!/usr/bin/env python3
"""Tests for the config-driven bits of paths.py.

Small, but worth having: this is plumbing between config.json and the map
links, and when it breaks it doesn't raise anything. It just quietly sends
people to the wrong state.

    python scripts/test_config.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths  # noqa: E402

BORDER = {
    "mapsRegion": "GA",
    "areaRegions": {"Aiken": "SC", "North Augusta": "SC"},
}

CASES = [
    # (config, area, expected, what it's checking)
    ({}, "Riverside", "",
     "nothing configured appends nothing, rather than a stray comma"),
    ({"mapsRegion": "GA"}, "Riverside", "GA",
     "one region for the whole patch"),
    (BORDER, "Augusta", "GA",
     "an area with no override falls back to mapsRegion"),
    (BORDER, "Aiken", "SC",
     "an override wins - this is the border case the setting exists for"),
    ({"mapsRegion": "GA", "areaRegions": {"Riverside": ""}}, "Riverside", "",
     "an override set to empty means 'append nothing here', not 'fall back'"),
    ({"mapsRegion": "GA", "areaRegions": {}}, "Riverside", "GA",
     "an empty override table is not an error"),
    ({"mapsRegion": None}, "Riverside", "",
     "a null reads as unset rather than the string 'None'"),
    ({"areaRegions": {"Riverside": "Kent"}}, "Riverside", "Kent",
     "regions are free text - not everywhere has states"),
]


def main():
    failed = 0
    for cfg, area, expected, what in CASES:
        got = paths.region_for(area, cfg)
        ok = got == expected
        if not ok:
            failed += 1
        print("  %-5s %-14s -> %-6s %s"
              % ("ok" if ok else "FAIL", area, repr(got), what))
        if not ok:
            print("        expected %r" % expected)

    print()
    if failed:
        print("%d of %d failed." % (failed, len(CASES)))
        return 1
    print("All %d passed." % len(CASES))
    return 0


if __name__ == "__main__":
    sys.exit(main())
