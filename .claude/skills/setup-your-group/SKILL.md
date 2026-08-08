---
name: setup-your-group
description: Set up a fresh fork of the restaurant picker as a particular group's own — copy the examples into place, define the areas, and replace the demo restaurants with real ones. Use right after forking, when the site is still showing example data like "Market Street Pizza" and "Riverside", or when someone asks how to make this theirs.
---

# Setting up a fresh fork

A new fork runs on the shipped example data — invented restaurants in invented
areas. That's deliberate: the site works immediately so people can see what
they've got. This skill turns it into a real one.

## The contract, first

**Add files. Never edit or delete upstream's.** That single rule is what keeps
"Sync fork" a one-click operation forever. Concretely:

| Yours — create and edit freely | Upstream's — leave alone |
| --- | --- |
| `config.json` | `config.example.json` |
| `data/restaurants.yaml` | `data/example/restaurants.yaml` |
| `data/history.csv` | `data/example/history.csv` |
| `GROUP.md` | everything else |

Deleting the examples looks tidy and costs nothing today, but the moment
upstream edits one of those files it becomes a modify/delete conflict that a
volunteer has to resolve by hand. They're a couple of kilobytes. Leave them.

## 1. Put the files in place

```bash
python scripts/setup.py --name "Their Group Name" --blank-history
```

Copies the three examples to the paths the site prefers. It never moves or
overwrites anything, and re-running is a no-op. There's also a **Set up my
group** button under the repo's Actions tab that does the same and commits the
result — better for someone who doesn't want a terminal.

Use `--blank-history` unless they have past meetups to backfill. Fake history
would give the picker fake cooldowns.

## 2. Work out the areas

This is the decision that matters most, and it's worth slowing down for. The
picker's whole job is spreading meetups across areas, so the areas *are* the
model of the region.

Ask how they'd naturally divide their patch — usually towns, suburbs or
districts people already name. Then sanity-check:

- **Five to eight is a good range.** Too few and the spread is meaningless;
  too many and each has one restaurant and the cooldowns thrash.
- **Every area needs at least two or three places**, or visiting its only
  option locks the area out for the whole restaurant cooldown.
- **Boundaries will be argued about.** Pick something and write the reasoning
  in `GROUP.md`; the exact line matters less than it being consistent.

Set them in `config.json`. `scripts/validate.py` rejects any restaurant whose
area isn't listed, so typos surface immediately.

## 3. Replace the example restaurants

The demo entries are invented and their areas won't match the new ones, so
`validate.py` will complain until they're gone. Replace them rather than
editing around them — see the `add-restaurant` skill for the method, which
matters more than it sounds.

Aim for **at least two or three per area** before the first real draw.
`python scripts/report.py` shows the counts.

## 4. Write down what makes somewhere suitable

Create `GROUP.md` with the group's own acceptance criteria — price ceiling,
seating, noise, dietary range, whatever they care about. Upstream ships a
starting list in comments at the top of the example restaurants file, but it's
a starting point, not a standard.

The criteria that matter get discovered by getting it wrong. When somewhere is
ruled out, record **why**, naming the place: *"we don't do shared-plate
formats — that's why X is off the list."* That reasoning is the thing that
stops it being re-litigated in six months, and it's what a new volunteer needs
most.

`GROUP.md` is a file upstream will never create, so it can never conflict.

## 5. Turn the site on

Settings → Pages → Deploy from a branch → `main` → `/ (root)`. No build step;
the site is the files in the repo.

Two things GitHub doesn't carry across on a fork:

- **Pages is off by default** — each fork owner enables it.
- **Actions are disabled on new forks** until the owner enables them, so the
  data validation won't run until they do.

## 6. Check

```bash
python scripts/validate.py
python scripts/report.py
```

Validator green, and the report showing sensible per-area counts with no area
sitting on one option.
