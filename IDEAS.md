# Ideas not yet built

Decided but not done. The notes here should be enough to start without
re-deriving the reasoning.

---

## Known limitations of the picker itself

- **An area you don't want to visit gets pushed hard.** Never-visited areas
  score as "five years since we've been", which is right for somewhere being
  neglected and wrong for somewhere deliberately excluded. Workaround: don't
  put active restaurants there. A per-area `in_rotation` flag in `config.json`
  would fix it properly.
- **Two branches of one chain are independent entries** and can both appear in
  a single draw when they're in different areas.
- **The day filter is "open on *any* selected day"**, so the winning
  combination of day and place still needs a human glance. That's deliberate —
  the vote settles day and place together — but it means the picker can't
  guarantee the pairing works.
