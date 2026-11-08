# Problem Deep Dives

One lecture per problem. When a problem gives me trouble, that's a sign of a misunderstanding underneath it, so the lecture goes after the **general concepts** the problem exposed, using the problem as the running example.

**How the loop works**
1. I attempt a problem, writing my reasoning in comments as I go (in `../examples.py` as usual, or pasted into the chat).
2. I say: *"analyze problem X and generate the deep dive."*
3. The assistant runs my code, finds where it breaks and why, traces each gap to the concept behind it, and writes the next `NNN-…md` here. (Instructions for the assistant: [`CLAUDE.md`](CLAUDE.md).)
4. I read it, then retry the problem (and the related problems it lists). A retry that shows new gaps gets a new deep dive.

**How this differs from the other folders**
- `../` (numbered lectures): a whole topic, taught before I practise it.
- `../attempt_reviews/`: a batch of recent attempts, mostly about speed and confidence.
- `../recaps/`: what my explain-backs of lectures showed I still need.
- **Here:** one problem I struggled with, and the root misunderstandings behind it.

## Index

| # | Problem | Attempted | Root concepts covered | Retry |
|---|---|---|---|---|
| 001 | [46 Permutations](001-0046_permutations.md) | 2026-11-06 | what each backtracking level decides (include/exclude = which numbers, placement = which order); count the leaves before coding; placement state (`path`, `used`, next position = `len(path)`); base case = "answer complete"; call-tree tracing; recursive helper must call itself | 11-07: placement model correct; `valid_set` filled with `1 … n-1` instead of the values in `nums`, so it returns `[]` (hint in deep dive 002 §6) |
| 002 | [380 Insert Delete GetRandom O(1)](002-0380_insert_delete_getrandom_o1.md) | 2026-11-08 | question the property, not the structure (a set's list needn't keep order → swap with last, pop); operations as lookup questions; the dict stores *where* in the source of truth; invariant sentence; update the moved element's index; delete-last edge case | planned |
