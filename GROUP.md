# CSRA Mesh — how this group uses the picker

[CSRA Mesh](https://github.com/csramsh) is a Meshtastic community around
Augusta, Georgia and Aiken, South Carolina. We eat together once a month and
call it **Meet & Mesh**.

This file is CSRA's own. `RUNBOOK.md` and the rest come from
[welbow/restaurant-picker](https://github.com/welbow/restaurant-picker)
upstream — if you want to change how the *app* works, that's where it lives.
What's here is the local knowledge: how we run it and what we've learned the
hard way.

## The fixed points

| | |
| --- | --- |
| **Start time** | **6:30pm, always.** Everything downstream assumes it. |
| **Where we vote** | Discord poll, three options, no links in the answers. |
| **Day** | Polled along with the place, so it isn't fixed month to month. |
| **Areas** | Eight, spanning both sides of the river — see below. |

Because the start time never moves, `open_days` in `data/restaurants.yaml`
means **open *and still serving* at 6:30pm**, not merely open that day. K & J
was open Mondays and closed at six; it was no use to us. Check the closing
time, not just the day.

## What qualifies

A place goes on the list if it has all of these. Each one is here because
getting it wrong cost us an evening, so the name attached to it is the point.

- **Decent seating for a group.** We turn up in numbers.
- **A real dining room.** Ordering at the counter is fine — we've met at
  McAlister's and it worked. Drive-thru fast food is not.
- **Enough decent food under $20 that everyone has a real choice.** The test
  is what you *can* eat for under $20, not what the priciest dish costs. A few
  expensive plates don't rule anywhere out — The Feed Sack and Ironwood Tavern
  both stay in normal rotation on that basis despite listings quoting them
  higher. Somewhere becomes `category: special` only when there isn't enough
  under $20 to pick from.
- **Menu range, so nobody is stuck** with nothing they can eat.
- **Quiet enough to hold a conversation.** *Doc's Porchside* is retired over
  this. Note that noise can be conditional rather than constant — Farmhaus
  Burger is fine most nights and too loud to talk on the nights they host
  events, so it's the date that decides, not the place. Check their schedule
  before proposing it.
- **Everyone can order their own plate.** *Meimei's* is off the list because
  dim sum means ordering à la carte and sharing, which trips up anyone new to
  it.
- **They'll split checks and won't spring an automatic gratuity** on a large
  table. Worth asking when you call ahead — *Frog and the Hen* is off the list
  for doing both.
- **An actual building you can sit in.** *The Saucy Hen* looked like a
  restaurant on every listing site and turned out to be Ruby Tuesday's kitchen
  operating under another name — delivery only, nowhere to sit. Click the map
  link before adding anywhere. If it lands on a *different* restaurant's
  address, that's what you've found.

Retired entries stay in the file with `active: no` and a note saying why. That
note is the only thing stopping the next person re-adding them.

## The areas

Augusta, South Augusta, Hephzibah, Martinez, Evans, Grovetown, North Augusta,
Aiken. North Augusta and Aiken are the South Carolina side.

**Augusta versus Martinez** is by where the member reporting it thought they
were, not by the city limits — Washington Road runs through both and the
listing addresses don't match how anyone talks about it. Don't relitigate a
placement that's already in the file.

**Hephzibah is a trap.** It exists as an area because Toritos turned out to be
down there, but we don't meet in Hephzibah. It currently stays out of the draw
only because it has no *active* restaurants. The moment somebody adds one, the
never-visited weighting will make Hephzibah the **most** likely area to come
up, since it scores as "five years since we've been". That weighting is
exactly what we want for Aiken and North Augusta and exactly wrong here. If it
ever matters, upstream's `IDEAS.md` has the fix (a per-area `in_rotation`
flag).

**South Augusta is thin.** Two normal options, and one of them — Sconyers — is
Thursday to Saturday only. Poll a Monday, Tuesday or Wednesday and the area is
down to a single restaurant; visit it and South Augusta drops out entirely for
six months. Aiken had this worse (one option) and it was fixed in August 2026
by adding The Feed Sack and The Pizza Joint. The same treatment works here:
point the suggestions survey at the south side specifically.

## Things we already know are wrong or missing

**Two months of history are gone.** October and November 2025 happened, but
the Discord invites carrying the details expired and nobody kept a record. The
gap in `data/history.csv` is real and can't be recovered — don't go looking.

**Five `open_days` values were never read off a listing.**
`taqueria-mi-casita`, `poblanos-martinez`, `azteca-maya`, `habaneros-grovetown`
and `izumi-evans` came from web-search summaries rather than the Google
listing. Low priority, and here is the reasoning so nobody redoes it: thirteen
entries came from that source, eight were later checked, and **four were
wrong** — Goolsby's, Augsburg Haus, Oliviana and Yummy Pho. Every error was a
*missing* day and three of the four were specifically a missing Sunday; the
summaries report the weekday pattern and drop the weekend edges. These five all
claim all seven days, so they're structurally immune to the only failure mode
we've actually seen. Check them if you're passing anyway.

**Per-person price bands on listings sites are crowd estimates, not menu
facts.** The two Ironwood Tavern locations report $10–20 and $20–30 for the
same menu. Use them as a hint and never as a verdict — the rule above is what
decides.

**Aggregator sites get addresses wrong** where the business's own listing gets
them right. Two were corrected that way. Prefer the restaurant's own site or
the Google listing.

## Keeping up with upstream

Click **Sync fork** on GitHub when it says there are new commits. It should
always be a clean fast-forward, because this fork only *adds* files:

| Ours | Upstream's — don't edit or delete |
| --- | --- |
| `config.json` | `config.example.json` |
| `data/restaurants.yaml` | `data/example/restaurants.yaml` |
| `data/history.csv` | `data/example/history.csv` |
| `GROUP.md` | everything else |

The example data sitting there unused is deliberate. Deleting it would feel
tidy right up until upstream edits one of those files, at which point Sync
fork becomes a merge conflict for whoever happens to be holding it.
