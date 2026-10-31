# Attempt Reviews

Lectures built from **your own attempts**, kept outside the gradient roadmap (`../000-gradient_roadmap.md`).

- **Gradient lectures** (`../001-…`, `../002-…`) teach new topics.
- **Attempt reviews** (this folder) take the problems you actually did, find where you were stuck, slow or unsure (using the comments you write while solving), and go over those ideas again from several angles until they're fluent.

**How it works:** solve problems from `../000-practice_queue.md`, write your thinking in comments as you go, and log each attempt there. When you've built up a few, ask for a review. Problems you're planning to go back to on your own are left out of the review, so nothing gets spoiled.

| # | Date of attempts | Problems | Main ideas |
|---|---|---|---|
| 001 | 2026-10-18 | 643, 187, 26, 112 | Fixed-window bounds four ways; `<` vs `<=` as sets; two-point check; brute-force checker; "build, then slide"; reader/writer and why `writer` is the count; name-vs-lines check; shrink-the-constant tracing; brute force first; leaf vs `None` |
| 002 | 2026-10-31 | Birthday Chocolate (revisit) + July attempts | **One model** for window bounds: loop over the left cut `start`, window `s[start:start+m]`; the only `-1` is "slice `[a:b]` holds boxes `a … b-1`"; box that leaves vs first box that stays; why one example can't pin a formula; sum-each-slice first; translation to `i` = box entering; a stuck protocol |
