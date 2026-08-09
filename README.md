# Restaurant Picker

Picks a few restaurant candidates each month for a group that meets to eat,
spread across the region, avoiding places you've been to recently. You put the
shortlist to a vote however you normally would; the picker's job is to stop the
same three places winning forever and to keep the meetups moving around.

**Live demo:** https://welbow.github.io/restaurant-picker/ — running on invented
data, so you can click about before deciding anything.

Built for a Meshtastic group in the Augusta area, but there's nothing regional
about the code. Fork it and it's yours.

## What it is

A static page on GitHub Pages that reads a few files out of the repo and does
the picking in your browser. **No server, no database, no build step, no
dependencies to install.** The site *is* the files in this repo.

That's a deliberate constraint rather than a limitation. This kind of thing is
run by volunteers, and the most common way it dies is that the toolchain rots
and nobody can rebuild it. Plain files in git will still work in five years.

| File | What it is |
| --- | --- |
| `data/restaurants.yaml` | Your list. Hand-edited, usually through GitHub's web editor. |
| `data/history.csv` | One row per meetup: `month,restaurant_id,notes`. |
| `config.json` | Areas, cooldowns, how many candidates, event wording. |
| `index.html` `app.js` `style.css` | The whole app. Vanilla JS. |
| `vendor/js-yaml.min.js` | YAML parser, vendored so there's nothing to install. |
| `scripts/setup.py` | Sets a fresh fork up as yours. |
| `scripts/validate.py` | Data checks. Runs in CI on every push. |
| `scripts/hours.py` | Turns pasted opening hours into the `open_days` field. |
| `scripts/report.py` | Health check — area counts, thin days, gaps, history. |
| `scripts/test_hours.py` | Regression tests for the hours parser. |
| `scripts/test_config.py` | Regression tests for the config helpers. |
| `RUNBOOK.md` | The monthly process, written for a non-technical volunteer. |
| `CLAUDE.md`, `.claude/` | Context for [Claude Code](https://claude.com/claude-code), if you use it. |

## How the picking works

1. Each **area** is scored by how many months since you last ate there; never
   visited counts as five years.
2. Areas inside the area cooldown, or with no eligible restaurants, drop out.
3. Areas are drawn at random, weighted by score squared — long-neglected areas
   are much likelier, but nothing is guaranteed.
4. Within each area, one restaurant is drawn, weighted the same way, from those
   outside the restaurant cooldown.
5. If the cooldowns leave too few options they're loosened a month at a time,
   and the page says so.

**Areas are picked before restaurants on purpose.** Draw from all restaurants at
once and whichever area has the most entries wins most of the time — exactly the
favouritism this is meant to prevent.

The draw is **seeded from the month**, so everyone loading the page in a given
month sees the same candidates. That heads off "did you reroll until your
favourite came up?" before anyone thinks it. Rerolling is possible and visibly
disclosed.

## Making it yours

1. **Fork this repo.**
2. **Run setup** — Actions tab → *Set up my group* → Run workflow. Or locally:
   ```bash
   python scripts/setup.py --name "Your Group" --blank-history
   ```
   This copies the examples to `config.json` and `data/`. It copies, never
   moves.
3. **Edit `config.json`** — your group's name and your areas. Five to eight
   areas works well; each wants two or three restaurants so that visiting one
   doesn't empty the area.
4. **Replace the example restaurants** in `data/restaurants.yaml` with real
   ones.
5. **Enable Pages** — Settings → Pages → Deploy from a branch → `main` →
   `/ (root)`.
6. **Enable Actions** if you want the data validation to run. GitHub disables
   workflows on new forks until the owner turns them on.

A fresh fork works before you do any of this — it just shows the demo data.

### The one rule: add files, don't edit or delete upstream's

| Yours | Upstream's — leave alone |
| --- | --- |
| `config.json` | `config.example.json` |
| `data/restaurants.yaml` | `data/example/restaurants.yaml` |
| `data/history.csv` | `data/example/history.csv` |
| `GROUP.md` | everything else |

Your files take precedence automatically; the examples are just the fallback.

Because upstream only ever touches its own files and you only ever touch yours,
**"Sync fork" stays a one-click operation** — you can pull improvements without
ever resolving a merge conflict.

Deleting `data/example/` looks tidy and seems free. It isn't: the next time
upstream edits one of those files you get a modify/delete conflict that someone
has to untangle by hand. They're two kilobytes. Leave them.

## The example data is invented

Every restaurant in `data/example/` is made up — "Market Street Pizza" in
"Riverside" and so on. Nothing there is a real business, and none of it needs
maintaining or verifying.

## Known limitations

- **An area you don't actually want to visit will be pushed hard.** Never-visited
  areas score as "five years since we've been", which is right for somewhere
  you're neglecting and wrong for somewhere you've deliberately excluded. The
  workaround is not to add active restaurants there. A per-area `in_rotation`
  flag would fix it properly.
- **Two branches of one chain are independent entries** and can both appear in
  the same draw if they're in different areas.
- **The day filter is "open on *any* selected day"**, so the winning
  combination of day and place still needs a human glance.

## Using Claude Code on this repo

Optional — all of this works by hand. But the repo carries its own context so
an assistant starts informed rather than guessing: `CLAUDE.md` loads
automatically, and there are skills for `setup-your-group`, `add-restaurant`
and `monthly-meetup`. Start Claude Code from inside the repo directory or none
of it loads.

## Licence

MIT — see [LICENSE](LICENSE). Fork it, change it, host it, no obligations. The
example data is invented and equally free.
