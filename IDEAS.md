# Ideas not yet built

Decided but not done. The notes here should be enough to start without
re-deriving the reasoning.

---

## Opening hours need re-checking on a cycle, and a visit should count

**Wanted, not built.**

Every active entry has hours read off a real listing. That was true on the day
it was done and gets less true every month — restaurants change their hours,
drop a day, stop doing lunch. Nothing in the repo currently distinguishes
hours checked last week from hours checked two years ago, so there's no way to
ask "what's gone stale?" and no prompt to go and look.

**A visit is a check.** If the group turned up on a Tuesday at 6:30 and ate,
that place was open on a Tuesday at 6:30 — better evidence than a listing.
Recording the meetup should therefore refresh that restaurant's hours
confidence for free, which means the maintenance burden falls only on places
nobody has been to lately. That's the same set the picker is trying to send
people to, so the two pressures point in useful opposite directions.

### Shape it would take

- An optional `hours_checked: 2026-08-09` per entry, written by
  `hours.py set` automatically so nobody has to remember it.
- Freshness = the later of `hours_checked` and the last visit in
  `history.csv`. Missing both means never checked.
- `hours.py todo` grows a **stale** section alongside its current *missing*
  one: entries older than some threshold, oldest first. Six months is a
  reasonable starting guess, and it should be a config value rather than a
  constant so groups can disagree with it.
- `report.py` shows the count, so the number is visible without going looking.

### Worth deciding before building

- **Don't make it a warning on the site.** A yellow box that's permanently on
  because eleven places are due a check is a yellow box people stop reading.
  A count in the report and a list in `todo` is enough.
- **Staleness must never hide a restaurant from the draw.** Same reasoning as
  missing `open_days` being treated as "open": the failure mode of dropping
  places quietly is worse than the failure mode of a slightly wrong hour.
- Whether an entry with no `open_days` at all should count as permanently
  stale, or be left out of the stale list because it's already on the missing
  list. Probably the latter — two lists, one entry, is noise.

---

## Known limitations of the picker itself

- **An area you don't want to visit gets pushed hard.** Never-visited areas
  score as "five years since we've been", which is right for somewhere being
  neglected and wrong for somewhere deliberately excluded. Workaround: don't
  put active restaurants there. A per-area `in_rotation` flag in `config.json`
  would fix it properly.
- **Two branches of one chain are independent entries** and can both appear in
  a single draw when they're in different areas.
- **Reroll is all-or-nothing.** It re-draws every slot, so losing one bad
  candidate costs you the other two. `unavailable_until` covers the common
  case (a place that's out for a while), but not "this one's fine, I just
  want a different draw for that slot". Measured: pausing one candidate
  changes 1 of 3 slots, rerolling changes all 3.
- **The day filter is "open on *any* selected day"**, so with several days
  ticked the winning combination of day and place still needs a human glance.
  Running the day poll first and then ticking only the winner avoids it
  entirely, which is what the runbook tells you to do — but nothing stops
  somebody leaving three days ticked and posting the place poll anyway.
