# Monthly runbook

Everything here happens in a web browser. You don't need to install anything
or know how to code. You do need a GitHub account with write access to this
repo.

The site is your GitHub Pages URL — `https://<owner>.github.io/<repo>/`.

> **Adapt this file.** It ships generic. Put your group's own start time,
> poll venue and quirks in, and delete the bits that don't apply. It's yours
> now; upstream won't overwrite it.

---

## The monthly process

### 1. Settle the day

Open the site and go to the **Pick** tab.

Open the **Days** dropdown at the top and tick the days you're willing to
offer. Each becomes an answer under **Step 1 — poll the day**, with a count of
how many places are open on it. If a day shows **0 open**, untick it — if it
wins you'll have nowhere to go, and the page says so in yellow.

Post that poll. A Discord poll **cannot** be made by pasting a block of text:
use the **+** next to the message box → **Create Poll**, and paste the
Question and each Answer into their own fields. Set the duration yourself.

> If your group doesn't vote on the day, set `"dayPoll": false` in
> `config.json` and this step disappears.

### 2. Settle the place

When the day poll closes, come back and tick **only the winning day**. The
shortlist under **Candidates** is now restaurants that are genuinely open when
you'll be there, and **Step 2 — poll the place** is the poll for it.

The draw is seeded from the month, so it isn't really random — anyone opening
the page this month sees the same shortlist. That's on purpose, so nobody
wonders whether it was rerolled until somebody's favourite came up.

If a candidate genuinely won't work — closed, bad night, can't seat you —
click **Reroll**. The page will say it's showing a reroll rather than the
first draw. Mention that when you post, so it's above board.

**Special spots** stays on "Exclude specials" for an ordinary month. "Only
specials" draws from the pricier places set aside for a celebration.

Pick the **Date** from the dropdown while you're there. It lists only the
dates in this month that fall on a ticked day, so you can't announce a Tuesday
that lands on a Wednesday. It's only required if your templates mention the
date.

Discord caps answers at **55 characters** and won't accept links, which is why
the site gives you short answers plus a separate follow-up message carrying
the addresses and map links. Send that as an ordinary message straight after.

That message is written for how Discord renders rather than how it looks in
the box: no indentation (Discord collapses it), no numbered lines (Discord
turns those into a list of its own), and the map links are in angle brackets
so you don't get three large map previews stacked underneath.

**If you tick more than one day here**, the shortlist is places open on *any*
of them, so the winning combination still needs a human glance. Ticking the
one winning day avoids that entirely.

### 3. Create the event

Go to the **Announce** tab and pick the month and the winner. Three boxes fill
in — **Event name**, **Location** and **Description** — each with a Copy
button, matching the fields most event tools ask for.

Set the date and time yourself. **Check the winner is actually open that day**
before you commit to it: the day filter offers places open on *any* of the
days you ticked, so a Thursday/Friday shortlist can legitimately include
somewhere open only on the Thursday.

Nothing is saved at this point. Announcing it and writing it down are separate
tabs because they're weeks apart — you record what actually happened, which
matters when a booking falls through.

### 4. After you've been, record it

**Don't skip this.** It's the only thing keeping the cooldowns honest. If a
month goes unrecorded, the picker will happily send you back to the same place.

1. On the **Record** tab, choose the month and where you went, and add a note
   if you like.
   - Record **where you actually ate**, even if it wasn't one of the
     candidates.
   - The note is optional and nothing about it is fixed — it's just the third
     column of `history.csv`. Add one later, or change your mind about it, by
     editing that file the same way.
2. Click **Copy line**. You'll get something like `2026-08,the-blue-door,`.
3. Click **Open history.csv in the GitHub editor**.
4. Paste it on its own new line at the bottom.
5. Click **Commit changes…**, then **Commit changes**.

Give it a minute and reload. It should appear at the top of **Recent months**
on that same tab, and under **The list → History**.

**Recent months** is there so you can see at a glance whether anything got
missed — a month showing "not recorded" in yellow is one nobody wrote down.
Fill it in the same way, choosing that month.

Only visits recorded here start a cooldown. A candidate that lost the vote is
fully eligible again next month.

---

## Adding a restaurant

Open `data/restaurants.yaml` in the GitHub editor, copy an existing block,
paste it at the bottom, and change the values:

```yaml
  - id: some-new-place
    name: Some New Place
    area: Riverside
    address: 123 Example Rd, Riverside
    cuisine: Barbecue
    open_days: Mon Tue Wed Thu Fri
    notes: Big back room, easy parking.
    active: yes
```

Rules that will bite you if you ignore them:

- **Keep the indentation.** Two spaces before `- id:`, four before every other
  line.
- **`id` must be unique and lowercase-with-dashes**, and once a visit has been
  recorded against it you must never change it — `history.csv` points at it.
- **`name` is just the name.** Don't write "Joe's Diner (Northgate)" — the
  site adds the area for you. Two branches of a chain are told apart by their
  `area` and `address`; the `id` is where you note which is which.
- **`area` must be one of the ones in `config.json`.**
- **Don't quote the address** even though it has commas. YAML is fine with it.
- If a value contains a colon (`Bar: The Place`), wrap that value in double
  quotes.
- **`open_days` is optional but useful.** Only the days they're open *and
  still serving when you arrive*. Leave the line out if you don't know — the
  picker treats missing as "open every day" rather than hiding the place.
  Rather than working it out, paste what the listing says:

  ```bash
  python scripts/hours.py set some-new-place "Mon-Fri 11am-9pm, Sun closed"
  ```

- **`category: special`** marks a real, open place that's simply too pricey
  for an ordinary month.

### Does it belong on the list?

Write your own criteria here — and in `GROUP.md` — as you discover them. The
useful ones tend to be learned by getting it wrong once, so when you rule
somewhere out, **record why, naming the place**. That reasoning is what stops
the same argument recurring in six months.

Things groups commonly end up caring about: seating for the size you actually
turn up at, price, noise, enough menu range that nobody is stuck, whether
everyone can order their own plate, whether they'll split the bill, and
whether they're still serving when you get there.

### Removing a restaurant

Set `active: no` rather than deleting. That keeps its history resolving and
stops the numbers going strange. Always leave a note saying why — that note is
the only reason the next person won't re-add it.

Use it for places that have **closed** or been **ruled out for good**. Don't
use it for expensive places: leave `active: yes` and add `category: special`
so they stay available for an occasion.

---

## Changing how it picks

`config.json` holds the knobs:

| Setting | Meaning |
| --- | --- |
| `groupName` | Shown in the page title and available to the templates as `{group}` |
| `startTime` | 24-hour `"HH:MM"`. What `open_days` means by "still serving" |
| `candidatesPerMonth` | How many options go to the vote |
| `restaurantCooldownMonths` | Months before the same place can come up again |
| `areaCooldownMonths` | Months before the same area can come up again |
| `areaWeightExponent` | How hard to favour neglected areas. 1 gentle, 2 default, 3 aggressive |
| `areas` | Your areas. Adding one here is required before any restaurant can use it |
| `mapsRegion` | State or region added to map searches. See below |
| `areaRegions` | Per-area exceptions to `mapsRegion`. Optional |
| `dayPoll` | `false` hides the day poll for groups that just declare the day |
| `dayPollQuestionTemplate` | Step 1's question |
| `pollQuestionTemplate` | Step 2's question |
| `followUpTemplate` | Opening line of the message you post under the poll |
| `eventNameTemplate` | |
| `eventDescriptionTemplate` | |

**Placeholders.** Every template above takes `{group}`, `{month}`
(*August*), `{monthYear}` (*August 2026*), and — once you've chosen a date on
the Pick tab — `{date}` (*Tuesday 18 August*), `{day}` (*Tuesday*) and
`{dayNum}` (*18*). Write the date whichever way round your group does:
`{date}` for *Tuesday 18 August*, or `{day}, {month} {dayNum}` for
*Tuesday, August 18*.

The two event templates also take `{name}`, `{area}`, `{address}` and
`{maps}`. Those aren't offered to the poll templates, which are written before
anyone knows the winner.

A template that mentions the date won't render until you've picked one — the
box tells you so rather than posting *"@everyone  it is!"* with a hole in it.

**`mapsRegion` only matters for restaurants with no address.** With one, the
map link searches the address and is unambiguous. Without one it falls back to
the name and the area, and "Northgate" on its own could be anywhere — so the
region gets appended. Set it to whatever disambiguates your patch (`"GA"`,
`"Kent"`, `"NSW"`), or leave it empty to append nothing.

If your area list **straddles a border**, list the exceptions in
`areaRegions` rather than picking a side:

```json
"mapsRegion": "GA",
"areaRegions": { "Aiken": "SC", "North Augusta": "SC" }
```

A misspelled area name there does nothing at all rather than complaining, so
`validate.py` checks them against your `areas` list.

Only one area is used per month, so with N areas an `areaCooldownMonths` above
roughly N−2 will start forcing the picker to relax its own rules. It says so
on the Pick tab when that happens.

---

## When something breaks

**The site says "Could not load the data."**
Somebody's last edit broke a file. Check the recent commits — the newest is
the culprit. Revert it, or fix it directly; the error names the file and
usually the line.

**There's a yellow box at the top of the site.**
A warning, not a crash. It says exactly what's wrong — usually a history row
pointing at a restaurant id that no longer exists.

**A red X on a commit or pull request.**
The data check caught something. Click the X → **Details** and read the bottom
of the log; it's written in plain English.

**"It picked somewhere we just went."**
Check the previous month actually got recorded. That's nearly always it.

**You changed something but the site looks the same.**
Your browser is holding an old copy. Hard-refresh with **Ctrl+Shift+R**
(**Cmd+Shift+R** on a Mac).

**You want to try something without breaking anything.**
Change the month at the top of the site and look at what it would pick.
Nothing is saved, so you can't do any harm poking about.

---

## Checking the data

```bash
python scripts/validate.py    # is it valid?
python scripts/report.py      # what does it say? area counts, thin days, gaps
```

`validate.py` also runs automatically on every push.
