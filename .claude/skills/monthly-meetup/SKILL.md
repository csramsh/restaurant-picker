---
name: monthly-meetup
description: Run the monthly meetup cycle — draw candidates, produce the Discord poll fields, create the event, and record the result in history.csv. Use when someone says it's time to pick this month's restaurant, wants the poll text, or needs to log where the group actually went.
---

# The monthly cycle

Four steps: draw, poll, event, record — one per tab, in that order.
`RUNBOOK.md` is the human-facing version of the same process — keep the two in
step if you change either.

The site is at https://<owner>.github.io/<repo>/ and everything happens in
the browser. To drive it locally instead:

```bash
python -m http.server 8731
```

## 1. Draw the candidates

The **Pick** tab shows three restaurants, one per area. The draw is seeded
from the month, so everyone loading the page that month sees the same three —
that's deliberate, so nobody wonders whether it was rerolled until someone's
favourite came up. **Reroll** bumps a visible nonce; if you use it, say so in
Discord.

If the day is already decided, tick it in the **Days** dropdown first. Places
open on *any* ticked day are offered — the poll settles day and place
together, so anywhere working on at least one candidate day is fair game.

**Special spots** stays on "Exclude specials" for a normal month. "Only
specials" draws from the pricier places set aside for holiday dinners.

## 2. Post the poll

**A Discord poll cannot be made by pasting a block of text.** The site gives
you each field separately because Discord's poll form takes them one at a
time: **+** next to the message box → **Create Poll** → paste the Question and
each Answer → set Duration.

Answers are capped at **55 characters** and can't contain links, which is why
they're just name and area. The site shows a live character count.

Then send the *Post this straight after* block as an ordinary message — it
carries the addresses and map links that won't fit in the poll.

## 3. Create the Discord event

On the **Announce** tab, pick the month and the winner. Three fields fill in —
Event name, Location, Description — matching Discord's **Events → Create
Event → Somewhere Else** form.

Set the date and time from the poll. If your group always starts at the same
time, record that in GROUP.md so nobody has to ask.

Because the day filter is "any of the ticked days", **check the winner is
actually open on the winning day** before creating the event. A Thursday/Friday
poll can legitimately offer somewhere open only on the Thursday.

## 4. After the meetup, record it

On the **Record** tab. **Announce and Record are deliberately separate tabs**
— the event goes out when the vote closes, the history line is written weeks
later, after everyone's actually been. That ordering matters: recording
afterwards means the file says what happened rather than what was planned,
which is the difference when a booking falls through. The two tabs share the
month and winner, so setting it on one sets it on the other.

This is the step that keeps the cooldowns honest — skip it and the picker will
happily suggest the same place again.

Record **where they actually ate**, even if it wasn't one of the three
candidates. The site produces the CSV line and a link straight to
`data/history.csv` in the GitHub editor; paste it as a new last line and
commit.

```
2026-08,the-blue-door,August meetup
```

The note is how it went, so it can't exist at announcement time. It's
optional, it's just the third column, and it can be added or changed later by
editing the file.

**Recent months**, under the form, lists the last four months and marks any
that were never written down. That's the one place a skipped month is visible
to the person able to fix it — if a draw looks wrong, look there first.

Only visits recorded here start a cooldown. A candidate that lost the poll is
fully eligible again next month.

Afterwards:

```bash
python scripts/validate.py
```

A history row pointing at an id that isn't in `restaurants.yaml` is an error,
not a warning — that's the usual cause of a red X in CI.

## If the draw looks thin

```bash
python scripts/report.py
```

That shows per-area counts, which day is thinnest, and whether any months are
missing from the history. The Pick tab also explains itself when it has to
relax the rules. Causes, in order of likelihood:

- **Last month wasn't recorded**, so an area that should be on cooldown isn't
  (or vice versa). Check `history.csv` first.
- **The day filter is biting.** Sunday is the thinnest day; the page says how
  many places the filter is excluding.
- **An area has genuinely run out.** Time to add restaurants — see the
  `add-restaurant` skill.
