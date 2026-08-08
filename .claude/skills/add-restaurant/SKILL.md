---
name: add-restaurant
description: Add a restaurant to the picker's list, or verify an existing one. Use when someone suggests a new place, when survey responses come in, or when an entry needs its address, hours or price checked. Covers the listing-data traps that have already caught this project.
---

# Adding a restaurant

The list lives in `data/restaurants.yaml`. Adding an entry is easy; adding a
*correct* entry is the job. Most of this skill is about not writing something
plausible that turns out to be wrong.

Start by seeing where the gaps actually are:

```bash
python scripts/report.py
```

It shows how many options each area has and which days are thinnest. A
suggestion for an area with nine options is worth less than one for an area
with two — say so, rather than treating every addition as equally useful.

## 1. Does it qualify?

**The group's own criteria live in `GROUP.md`.** Read them; they're the
authority, and they're specific to who's actually turning up.

If `GROUP.md` doesn't exist yet, the things groups commonly end up caring
about are: seating for the size they actually turn up at, price, noise,
whether the menu has enough range that nobody is stuck, whether everyone can
order their own plate, whether the bill can be split, and whether they're
still serving when people arrive.

Those criteria get discovered by getting it wrong. When something is ruled
out, **write down why, naming the place** — that reasoning is what stops the
same argument recurring later, and it belongs in `GROUP.md`.

If somewhere fails only on price, it still belongs in the file — as
`category: special`, not `active: no`.

## 2. Look it up

Open the Google Maps listing in a browser the user can see, and have them read
the details off it. **Do not scrape**, and do not fill in details from memory.

Search by **name and city**, not by a street address you aren't sure of — a
wrong house number sends Maps to a random pin. Capture the address, the price
band and the full week's opening hours, which usually needs the hours row
expanded.

### Traps, all of which have already caught this project

**Ghost kitchens.** Delivery-only brands show up on listings sites looking
like real restaurants. One entry turned out to be a national chain's kitchen
under another name — there was nowhere to sit. If the map link lands on a
*different* restaurant's address, that's what you've found.

**Search-result summaries are not a source for opening hours.** Of thirteen
entries filled in that way, eight were later checked against the listing and
**four were wrong** — always a *missing* day, usually a weekend one.
Summaries report the weekday pattern and drop the edges. Read the listing.

**Aggregator data is often wrong** where the business's own listing is right.
Two addresses were corrected this way. Prefer the restaurant's own site or the
Google listing.

**Price bands are crowd estimates, not menu facts.** Two branches of one chain
reported $10–20 and $20–30 for the same menu. Use the band as a prompt to
check, never as the decision — ask the user, they know the menus.

**Chains need `area` to disambiguate, not the name.** Never write
`The Pizza Joint (Aiken)`. Write `name: The Pizza Joint`, `area: Aiken`, and
give it an id like `pizza-joint-aiken`. The site appends the area itself, and
`scripts/validate.py` warns if a name repeats its area.

## 3. Write the entry

Append to the right area section of `data/restaurants.yaml`:

```yaml
  - id: some-new-place
    name: Some New Place
    area: Riverside
    address: 123 Example Rd, Riverside
    cuisine: Barbecue
    notes: Big back room, easy parking.
    active: yes
```

- `id` — lowercase-with-dashes, unique, and **never changed once a visit is
  recorded against it**; `history.csv` points at it
- `area` — one of the areas in `config.json`
- `address` — no quotes needed despite the commas. Omit if unverified.
- `notes` — record *why* a judgement was made, not just what

## 4. Set the opening hours

Don't work `open_days` out by hand. Paste what the listing says:

```bash
python scripts/hours.py set some-new-place "Mon-Fri 11am-9pm, Sat 11am-10pm, Sun closed"
```

It handles the usual shapes — Google's day-per-line copy format, `Closed
Tuesdays`, split lunch/dinner service, en-dashes, after-midnight closing — and
works out which days they're still serving at the group's start time. If it
can't read something confidently it refuses and writes nothing; reformat
rather than forcing it.

If the place is never open when the group meets, it can't host them. Say so
rather than adding it.

## 5. Check

```bash
python scripts/validate.py
python scripts/report.py
```

`validate.py` green with no new warnings, and `report.py` showing the area
count where you expect it, before you call it done.
