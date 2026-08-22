# Restaurant Picker — notes for Claude

Picks a few restaurant candidates a month for a group that meets to eat,
spread across a region, avoiding places visited recently. A static page on
GitHub Pages that reads a few files out of this repo and does everything in
the browser.

**Volunteers run this, and most of them don't write code.** Optimise for
someone moderately techie being able to take over — that constraint outranks
elegance. No build step, no framework, no server, no dependencies to install.
The site *is* the files in the repo. Keep it that way.

## If this is a fork

Group-specific things — the areas, the acceptance criteria, the reasons
particular places were ruled out — belong in **`GROUP.md`**, not in this file.
Read it if it exists; that's where the local knowledge lives.

**The contract that keeps upstream syncs painless: add files, never edit or
delete upstream's.**

| Fork's own | Upstream's — leave alone |
| --- | --- |
| `config.json` | `config.example.json` |
| `data/restaurants.yaml` | `data/example/restaurants.yaml` |
| `data/history.csv` | `data/example/history.csv` |
| `GROUP.md` | everything else |

The fork's files take precedence; the examples are the fallback, which is why
a fresh fork works before anyone has configured it. Never "tidy up" by
deleting the examples — the moment upstream edits one it becomes a
modify/delete conflict for a volunteer to untangle.

## Rules that matter

**Never invent restaurant data.** Addresses, hours and prices come from a real
source or from a human who has been there. If you can't verify something,
leave the field out and say so — a missing `address` degrades gracefully (the
map link searches by name), a wrong one sends people to the wrong place.

**Don't scrape Google Maps.** Against their terms, and a scraper would rot
silently and leave the group trusting stale hours. The working pattern is:
open the listing in a browser a human can see, let them copy the hours, and
run them through `scripts/hours.py set`.

**Search-result summaries are not a source for opening hours.** In the
project's own history, of thirteen entries filled in that way, eight were
later checked against the listing and **four were wrong** — always a *missing*
day, usually a weekend one. Summaries report the weekday pattern and drop the
edges. Read the listing.

**Aggregator sites are often wrong where the business's own listing is right.**
Prefer the restaurant's own site or the Google listing for addresses.

**Always run the checks:**

```bash
python scripts/validate.py      # after any change under data/ or config.json
python scripts/test_hours.py    # after any change to scripts/hours.py
python scripts/test_config.py   # after any change to scripts/paths.py
```

**Nothing group-specific goes in the app.** This is upstream: no place names,
no state codes, no start times, no venue assumptions baked into `app.js` or
`scripts/`. Anything that varies between groups belongs in `config.json` with
a default that keeps existing forks working. Two of these leaked out of the
original single-group version — a hardcoded `'SC' : 'GA'` and a hardcoded poll
question — and both were found by a human reading the code, not by any test,
because wrong-but-plausible output looks fine.

**Don't hand-write throwaway queries against the data.** `scripts/report.py`
answers the recurring questions — per-area counts, which day is thinnest,
what's missing, where the group has and hasn't been. If you find yourself
writing a one-off `python -c` against `restaurants.yaml`, that's a sign the
report should grow a line instead.

**`open_days` means "open AND still serving when the group arrives."** A place
open Monday that closes before the start time must not have Mon in the list.
Missing `open_days` is treated as "open every day", so leaving it out is safe;
guessing is not.

**Three ways out of the draw, and they are not interchangeable:**

| | |
| --- | --- |
| `active: no` | closed, or ruled out for good |
| `category: special` | real and open, just too pricey for an ordinary month |
| `unavailable_until: 2026-10` | temporary — roadworks, a refit, a season |

Reach for `unavailable_until` whenever the reason has an end. It expires by
itself; `active: no` waits for a human who will not come. Retiring a place
that was only having its car park dug up is how a list quietly shrinks.

**Names never contain locations.** Not `The Feed Sack (Aiken)` — the site adds
the area itself. Two branches of a chain are distinguished by `area` and
`address`; the `id` carries the distinction (`the-feed-sack-aiken`).

**Closed places stay in the file.** Set `active: no` with a reason rather than
deleting, so `history.csv` keeps resolving and nobody re-adds them.

## A trap worth knowing about

**Ghost kitchens.** Delivery-only brands appear on listings sites looking like
real restaurants. One got onto the original list and turned out to be a
national chain's kitchen operating under another name — there was nowhere to
sit. Click the map link: if it lands on a *different* restaurant's address,
that's what you've found.

## Skills

- `setup-your-group` — turning a fresh fork into a particular group's own.
- `add-restaurant` — adding or verifying a place, and the traps above.
- `monthly-meetup` — the pick, poll, event and record cycle.
