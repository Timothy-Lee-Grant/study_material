# LeetCode Gradient Roadmap

> **What this is:** the plan for which topics come next, and why, kept in one place so it can't get lost again. Updated 2026-10-11 (added: kinds of problems; LeetCode vs HackerRank vs interviews; design problems moved to lecture 012).
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
| 008 | `008-indices_and_bounds_toolkit.md` | Indices and bounds: boxes vs cuts, counting rules, valid sets, two-point checks, drills (your request, Oct 10) | applied (Car Fleet `range` reasoning, Oct 10) |
| 009 | `009-graphs_traversal_and_ordering.md` | Graphs: traversal template, components, BFS shortest steps, 3-state cycles, Kahn's topological order, clone | not yet |

---

## Checkpoint A (now): consolidate 004–007 before adding more

Four topics have been read in five days, with almost no problems attempted. The highest-value step right now is turning those lectures into working code, not another topic.

- From each lecture's practice ladder, do the first **2–3 problems** from a blank page, tracing before submitting (lecture 003).
- Do the drills in lecture 008 §13 first (15 minutes), then repeat them 2–3 days later.
- Good first set: **35, 875** (binary search) · **1, 560** (hash/prefix) · **167, 209, 15** (pointers/windows) · **104, 112, 98** (trees).
- Explain lecture 007 back when you've read it.
- Log every attempt in the tracker. The bug tags tell us which topic actually needs more work.

---

## Group 2 (recommended next): traversal and structure

| # | Planned lecture | Why it's next |
|---|---|---|
| ~~009~~ | ~~Graphs~~ | **Done Oct 11** (see the table above) |
| 010 | **Linked lists: dummy heads, reversing, merging, fast/slow, "where does the pointer land?"** (206, 21, 19, 141, 143, 61) | Targets the "pointer lands one node off" bug (Rotate List). Reorder List was blocked in July by not knowing how to reverse a list. Needed for LRU Cache |
| 011 | **Backtracking in depth: choose / explore / un-choose, pruning, subsets vs permutations vs combinations** (78, 46, 39, 40, 79, 131) | Completes the recursion family (the "accumulate down" style). Targets the missing un-choose (Word Search) and the end-of-function steps that tend to get dropped |

## Group 3: design problems, ordering and selection

| # | Planned lecture | Why |
|---|---|---|
| 012 | **Data-structure design problems** (146 LRU Cache redo, 155 Min Stack, 981 Time Based Key-Value Store, 380 Insert Delete GetRandom O(1), 933 Number of Recent Calls → your rate limiter) | You've already faced one in a real Microsoft interview. Comes right after linked lists because LRU needs a doubly linked list. See "Kinds of problems" below for what makes these different |
| 013 | Stacks and monotonic stacks (20, 155, 739, 84) | You derived Basic Calculator's stack in July; a monotonic stack is the next step |
| 014 | Heaps / priority queues (215, 347, 23, 295) | Zero attempts so far; Python `heapq` fluency |
| 015 | Intervals and greedy (56, 57, 435, 55, 45) | The July Merge Intervals `max` bug; greedy needs an argument for why it's correct |

## Group 4: dynamic programming II

| # | Planned lecture | Why |
|---|---|---|
| 016 | 2-D DP and knapsack-style problems (62, 1143 redo, 518, 72, 416) | Builds on lecture 002 once 1-D DP is solid |
| 017 | Sequence DP (300, 139, 152, 5) | |

## Group 5: lower priority (later)

Union-find, tries, bit manipulation, and **divide-and-conquer counting** (merge-sort inversion counting: 493 Reverse Pairs, 315 Count of Smaller Numbers After Self; added Oct 10 after the video you watched). (Design problems moved up to lecture 012 on Oct 11.)

---

## Kinds of problems you'll meet, and where (added Oct 11)

You asked three questions: what "design problems" are, why some problems that aren't algorithmically hard still trip you up, and how LeetCode, HackerRank and real interviews differ. Short answer: they test different skills, and your plan should train all three, in different amounts.

### 1. Four kinds of problems

| Kind | What you're given | What's actually being tested | Examples you've done |
|---|---|---|---|
| **Algorithm / pattern** | one function, input → output | recognizing a pattern (binary search, window, DP…) and applying it correctly | 3Sum, LCS, Koko, Course Schedule |
| **Implementation / simulation** | rules to carry out exactly | turning a precise description into code with many small decisions: indices, order of updates, edge cases | Spiral Matrix, Car Fleet, Birthday Chocolate, Reverse Integer, Game of Life |
| **Data-structure design** ("design a class") | a class with several methods, often with required speeds | choosing and combining data structures so *every* method is fast, and keeping them consistent across many calls | LRU Cache, the rate limiter (your Microsoft interview) |
| **System design** | an open-ended product ("design a URL shortener", "a distributed rate limiter") | architecture: services, storage, caching, scaling, trade-offs, at the whiteboard, with no code | (not practised yet; separate prep, common for SWE II) |

Most interviews mix kinds 1 and 2. Kind 3 is common for mid-level roles and is often how kind 4 *starts* ("now make it work across 10 servers").

### 2. What makes a "design problem" (kind 3) different

You're not asked for one answer. You're asked for an **object that answers many requests over time.** For example, LRU Cache: `get(key)` and `put(key, value)`, both O(1), with the least recently used item evicted when full. What sets these apart:

| Feature | Algorithm problem | Design problem |
|---|---|---|
| Interface | one function | a class with 2–4 methods; you're given (or have to clarify) the API |
| State | lives only during one call | **persists between calls**; the order of calls matters |
| Goal | correct output, good total complexity | **each operation** meets its own complexity target (usually O(1) or O(log n)) |
| Typical solution | one pattern | **two structures combined**, each covering the other's weakness (LRU: a dict for O(1) lookup + a doubly linked list for O(1) recency order) |
| Main source of bugs | indices, base cases | **the structures drifting out of sync**: an item removed from one but not the other |
| How it's judged | correct + complexity | the above, plus **clarifying questions**, clean method boundaries (helpers like `_remove`, `_add_front`), naming, and **follow-ups** |

**The core skill is consistency between structures.** Your rate-limiter interview showed the classic version of this: per-user queues plus a global queue both "owned" the same requests, and you correctly spotted the risk that clearing one wouldn't clear the other. Lecture 012 will teach the habit of naming **one source of truth** and treating the other structure as an index that must be updated in the same method, every time.

**Common follow-ups** (and what they're really testing): "what if many threads call this?" (locking, atomic operations), "what if it doesn't fit on one machine?" (the step into system design), "what's the memory cost per item?", "what if the capacity is 0?" (edge cases in the spec).

### 3. "Not algorithmically hard, but they trip me up" (kind 2)

These are **implementation / simulation** problems. There's no clever insight to find. The difficulty is that they contain **many small decisions in a row**, and each one is a chance for an off-by-one, a wrong variable, or a step in the wrong order:

| Problem | How many decisions | Where you slipped |
|---|---|---|
| Spiral Matrix | 4 loops × (start, stop, step, guard, wall update) ≈ 20 | conventions, a backward `range`, row/column |
| Birthday Chocolate | window build, slide, check order | `-+`, double add, `d` vs `m` |
| Car Fleet | sort key, direction, comparison, tie case | (correct; ties were handled by accident of structure) |
| Reverse Integer | digit order, sign, overflow | built the digits in the wrong order |

So it isn't randomness. **It's decision density.** Pattern problems have one hard decision. Implementation problems have twenty easy ones, and twenty easy ones fail more often than one hard one unless each is made deliberately. That's also why your mistakes cluster here: lecture 008's toolkit is exactly the tool for these.

**Playbook for implementation problems:**

1. **Spec first.** Restate the rules in your own words, and list the edge cases *before* coding (empty, one element, ties, negative numbers, overflow, already done).
2. **Split into named steps** (helpers or commented blocks): "sort by position", "compute arrival times", "count fleets". Each step is small enough to get right.
3. **Name every index and its valid set** (lecture 008 §5). Convert every count to a slice (§2).
4. **Trace only the risky step** (lecture 003 §3.1), usually the loop with the most index decisions.
5. **Check ties and equality cases deliberately.** "What happens when two values are equal?" is where these problems hide their traps.

These are worth practicing in their own right: about one implementation problem a week, mixed in with pattern problems.

### 4. LeetCode vs HackerRank vs a real interview

| | LeetCode | HackerRank (practice tracks) | Online assessment (OA) | Live interview (e.g. Microsoft) |
|---|---|---|---|---|
| **Input/output** | given a function signature; the platform parses input for you | often **read from stdin and print** (or a stub with generated `main` code, like your Birthday Chocolate file) | either style, depending on the platform the company uses | a shared editor; usually just a function, often **not run at all** |
| **Statement style** | short, abstract, constraints listed | often a **story** ("Lily and Ron share a chocolate bar") you must translate into an abstract problem; implementation-heavy; math puzzles | usually LeetCode-medium-like, sometimes story-style | a short prompt, often deliberately **underspecified**: you're expected to ask clarifying questions |
| **Feedback** | shows the failing input | often only "n of m tests passed"; hidden cases | usually hidden tests, partial credit | a human; you trace, they watch |
| **What's graded** | correctness + speed | correctness (per test case) | correctness, sometimes time taken | **your reasoning out loud**, correct code, testing your own code, complexity, handling follow-ups, communication |
| **Time** | untimed (unless a contest) | untimed | timed (often 60–90 min for 2–3 problems) | ~45–60 min per conversation, including talking |

**Why they feel so different:** HackerRank's practice problems lean toward implementation (kind 2) and story-style wording, and they make you handle I/O. LeetCode leans toward recognizable patterns (kind 1) and design classes (kind 3). Real interviews use mostly LeetCode-*style* problems but judge **how you get there**, not just the final answer.

**What to expect at Microsoft (as reported; formats vary by team):** Microsoft's own description is two to four conversations of up to an hour each. Candidate reports for SWE roles describe an online assessment before live rounds, then several technical interviews focused on data structures and algorithms at roughly LeetCode-medium difficulty, with behavioral questions woven in. System design shows up more often for SWE II and above. Object/data-structure design questions like your rate limiter also appear. Guides consistently stress clarifying the requirements, explaining your reasoning, and testing edge cases. **Ask your recruiter** which platform the online assessment uses and whether there's a design round.

**One small skill to add for HackerRank-style platforms:** reading input yourself. The whole template is:

```python
import sys

def main():
    data = sys.stdin.read().split()      # every whitespace-separated token, as strings
    n = int(data[0])
    nums = list(map(int, data[1:1 + n])) # the next n tokens: slice from cut 1 to cut 1+n
    print(solve(nums))

main()
```

It's worth doing once or twice so it isn't new on test day.

### 5. What this changes in the plan

- **Design problems get their own lecture** (012, right after linked lists), not "later."
- **Implementation problems** are a weekly practice item (one per week, using the playbook in §3), not a separate lecture yet. If they keep causing most of your bugs, they'll get one.
- **System design** is outside this LeetCode roadmap. When you want to start it, it should be its own track.
- **Mock interview habit:** once a week, do one problem out loud, timed, without running the code, then trace and test it yourself before checking. That's the format that actually gets graded.

Sources for §4: Microsoft's interview overview as summarized in [PracHub's Microsoft SWE guide](https://prachub.com/resources/microsoft-software-engineer-interview-guide) (accessed 2026-10-11); candidate reports in [Dataford's Microsoft SWE interview experiences](https://dataford.io/interview-guides/microsoft/software-engineer/experiences) (anonymous, small sample; accessed 2026-10-11). Platform comparisons: [DesignGurus, "Is LeetCode harder than HackerRank?"](https://designgurus.io/answers/detail/is-leetcode-harder-than-hackerrank) and [Coddy, HackerRank vs LeetCode](https://coddy.tech/vs/hackerrank-vs-leetcode). Format details vary by company and team and change over time, so confirm with your recruiter.

---

## How the order can change

- If a practice attempt shows a bug class growing again (for example boundaries, or a forgotten final step), the next lecture targets that class, even if it's out of order.
- A topic counts as **done** when you've explained it back *and* passed 2 problems from it from a blank page, with a redo at least 3 days later.
