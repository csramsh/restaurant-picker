"""Where the data lives.

Your files take precedence; the shipped examples are the fallback. A fresh
fork therefore works straight away — the site and all the scripts run against
the demo data until you add your own.

The examples belong to upstream. Nothing here ever writes to them: that would
break the additive-only contract that keeps "Sync fork" a one-click operation.
See the README.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

REAL_CONFIG = ROOT / "config.json"
REAL_RESTAURANTS = ROOT / "data" / "restaurants.yaml"
REAL_HISTORY = ROOT / "data" / "history.csv"

EXAMPLE_CONFIG = ROOT / "config.example.json"
EXAMPLE_RESTAURANTS = ROOT / "data" / "example" / "restaurants.yaml"
EXAMPLE_HISTORY = ROOT / "data" / "example" / "history.csv"


def config_path():
    return REAL_CONFIG if REAL_CONFIG.exists() else EXAMPLE_CONFIG


def restaurants_path():
    return REAL_RESTAURANTS if REAL_RESTAURANTS.exists() else EXAMPLE_RESTAURANTS


def history_path():
    return REAL_HISTORY if REAL_HISTORY.exists() else EXAMPLE_HISTORY


def using_examples():
    """True when this is still a fresh fork running on the demo data."""
    return not REAL_RESTAURANTS.exists()


def require_own_data(what="write to the restaurant list"):
    """Stop a script modifying the shipped examples.

    Returns None when it's safe to proceed, or a message to print and exit on.
    """
    if not using_examples():
        return None
    return (
        "This fork is still running on the example data, so there's nothing of\n"
        "your own to %s yet.\n\n"
        "Set your group up first — it copies the examples into place without\n"
        "touching the originals:\n\n"
        "    python scripts/setup.py\n\n"
        "(Or run the \"Set up my group\" workflow from the Actions tab.)"
        % what
    )


def start_minutes(default=18 * 60 + 30):
    """Minutes past midnight that the group's meetups start.

    From "startTime" in config.json (24-hour "HH:MM"). This is what makes
    open_days mean "still serving when we arrive" rather than merely "open".
    """
    import json
    try:
        cfg = json.loads(config_path().read_text(encoding="utf-8"))
        hh, mm = str(cfg.get("startTime", "")).split(":")
        return int(hh) * 60 + int(mm)
    except Exception:
        return default


def start_label():
    m = start_minutes()
    h24, mm = divmod(m, 60)
    suffix = "am" if h24 < 12 else "pm"
    h12 = h24 % 12 or 12
    return "%d:%02d%s" % (h12, mm, suffix)
