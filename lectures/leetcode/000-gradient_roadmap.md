# LeetCode Gradient Roadmap

> **What this is:** the plan for which topics come next, and why, kept in one place so it can't get lost again. Updated 2026-10-09.
> **How the plan works:** "gradient" order. Each step targets whatever is currently the most expensive weakness, while also filling the biggest gaps in topic coverage. The order below is a default, not a schedule. If practice shows a new weakness, it jumps the queue.
> **Language:** Python. **Free problems only** (no Premium). Every lecture includes full problem statements (paraphrased), derivations rather than conventions, and no firmware analogies.

---

## Done (lectures written)

| # | Lecture | Topic | Explained back? |
|---|---|---|---|
| 001 | `001-matrix_and_simulation_problems.md` (+ Addendum A) | Matrices, boundaries, closed vs half-open, range formula | partly (applied in Spiral attempts) |
| 002 | `002-recursion_that_returns_answers.md` | Recursion contracts, base cases, memoization, backtracking intro | applied (Climbing Stairs) |
| — | `002-printable_problem_set.md` | ~45 problems with solutions, by family (for paper practice) | — |
| 003 | `003-walking_through_code.md` | Tracing any problem by hand | applied (Spiral II, found his own bug) |
| 004 | `004-binary_search_one_template.md` | Binary search: first True in F…F T…T | ✅ Oct 6 (recap entry 1) |
| 005 | `005-hash_maps_and_prefix_sums.md` | Double loop → lookup; prefix sums | partly ✅ Oct 9 (recap entry 2) |
| 006 | `006-two_pointers_and_sliding_windows.md` | Inward / read-write pointers, fixed and variable windows, 3Sum | ✅ Oct 9 (recap entry 3) |
| 007 | `007-binary_trees_contracts_on_a_tree.md` | Trees: answer up, context down, global best, BFS levels, LCA | not yet |

---

## Checkpoint A (now): consolidate 004–007 before adding more

Four topics have been read in five days, with almost no problems attempted. The highest-value step right now is turning those lectures into working code, not another topic.

- From each lecture's practice ladder, do the first **2–3 problems** from a blank page, tracing before submitting (lecture 003).
- Good first set: **35, 875** (binary search) · **1, 560** (hash/prefix) · **167, 209, 15** (pointers/windows) · **104, 112, 98** (trees).
- Explain lecture 007 back when you've read it.
- Log every attempt in the tracker. The bug tags tell us which topic actually needs more work.

---

## Group 2 (recommended next): traversal and structure

| # | Planned lecture | Why it's next |
|---|---|---|
| 008 | **Graphs: DFS/BFS on grids and adjacency lists, cycle detection, topological sort** (200, 994, 207, 210, 133) | Very high interview frequency. Your past graph bugs were all bookkeeping (Oranges used `(r, c)` instead of the neighbor; Course Schedule was missing `return True`). Builds directly on the tree lecture (DFS) and the BFS level loop |
| 009 | **Linked lists: dummy heads, reversing, merging, fast/slow, "where does the pointer land?"** (206, 21, 19, 141, 143, 61) | Targets the "pointer lands one node off" bug (Rotate List). Reorder List was blocked in July by not knowing how to reverse a list. Needed for LRU Cache |
| 010 | **Backtracking in depth: choose / explore / un-choose, pruning, subsets vs permutations vs combinations** (78, 46, 39, 40, 79, 131) | Completes the recursion family (the "accumulate down" style). Targets the missing un-choose (Word Search) and the end-of-function steps that tend to get dropped |

## Group 3: ordering and selection

| # | Planned lecture | Why |
|---|---|---|
| 011 | Stacks and monotonic stacks (20, 155, 739, 84) | You derived Basic Calculator's stack in July; a monotonic stack is the next step |
| 012 | Heaps / priority queues (215, 347, 23, 295) | Zero attempts so far; Python `heapq` fluency |
| 013 | Intervals and greedy (56, 57, 435, 55, 45) | The July Merge Intervals `max` bug; greedy needs an argument for why it's correct |

## Group 4: dynamic programming II

| # | Planned lecture | Why |
|---|---|---|
| 014 | 2-D DP and knapsack-style problems (62, 1143 redo, 518, 72, 416) | Builds on lecture 002 once 1-D DP is solid |
| 015 | Sequence DP (300, 139, 152, 5) | |

## Group 5: lower priority (later)

Union-find, tries, bit manipulation, **divide-and-conquer counting** (merge-sort inversion counting: 493 Reverse Pairs, 315 Count of Smaller Numbers After Self; added Oct 10 after the video you watched), and redoing design problems (LRU Cache, the rate limiter from your interview).

---

## How the order can change

- If a practice attempt shows a bug class growing again (for example boundaries, or a forgotten final step), the next lecture targets that class, even if it's out of order.
- A topic counts as **done** when you've explained it back *and* passed 2 problems from it from a blank page, with a redo at least 3 days later.
