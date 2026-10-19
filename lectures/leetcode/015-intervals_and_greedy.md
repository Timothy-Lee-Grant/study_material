# Lecture 015: Intervals and Greedy: Why the "Random" Choices Aren't Random

> **For:** Timothy · **Date:** 2026-10-19
> **Prerequisites:** lecture 008 (closed ranges, valid sets, name → valid set → test), lecture 006 (two pointers: the "ruled out because…" sentence), lecture 009 (BFS levels, for §8). Written out of order (011 and 014 are still to come).
> **Why this lecture:** you said interval and greedy problems "always seem so random." That's a fair description of how they're usually *taught*: "sort by end," "keep the farthest," with no reason given. Each of those choices has a reason you can derive, and this lecture derives every one. Two earlier pieces of evidence point to what to fix:
> - your July Merge Intervals was missing a `max()` for a nested interval (you'd even written down the assumption you were unsure about);
> - in your Decode Ways and House Robber comments you ruled out greedy with two tests: *"my decision here limits my future options"* and *"we are not asked to find the 'lowest' of something."* The first test is not reliable, and §6 shows a problem where every decision limits the future and greedy is still correct. The second is right for counting problems, but greedy also solves yes/no problems (§7).
> **Format notes:** every problem has its full statement (paraphrased), examples and constraints; every name is defined before it's used; every "why" is a numbered derivation, not a rule to remember; no firmware analogies.
> **Verification:** every function here was compared with a brute-force reference on 3,000 random inputs (for 435 and 452, by trying every subset of intervals; for the jump games, by BFS over every position). Traces and counterexamples were produced by running the code.

---

## Core ideas (the answer key)

1. **An interval problem has two hidden decisions: what to sort by, and what to remember while you walk.** Both can be derived from the question being asked. Neither is a convention.
2. **Two closed intervals `[a, b]` and `[c, d]` overlap exactly when `a <= d and c <= b`.** Derive it from the opposite ("one ends before the other starts"). After sorting by start, it shrinks to one comparison: `next_start <= current_end`.
3. **Whether touching counts as overlapping changes from problem to problem.** Read it from the examples (`[1,4]` and `[4,5]`), then write `<=` or `<` to match. That's the whole "`<` vs `<=`" decision.
4. **Sort by start when you're building or combining intervals** (merge, insert). Once the next start is past your current end, nothing later can touch the current interval, so it's finished.
5. **Sort by end when you're choosing as many non-overlapping intervals as possible** (435, 452). The interval that ends first leaves the most room for everything after it. An exchange argument (§5.2) proves it.
6. **Count overlaps at a point with a sweep:** +1 at each start, −1 at each end, in time order. The largest running count is the number of rooms/groups needed (§5.4).
7. **Greedy means: make the choice that looks best now, never undo it.** It's correct only when you can show the greedy choice is never worse than any other choice.
8. **The greedy test, in order:** state the greedy choice in one sentence → try to break it with 2–3 items (two minutes) → if it survives, argue an exchange: "take any best answer, swap in my choice, and it's still valid and just as good."
9. **"My choice limits future options" does NOT rule out greedy.** Every choice limits the future. What rules out greedy is a small counterexample. What rules it *in* is an argument.
10. **Jump Game is greedy because the reachable positions always form one unbroken range `0 … farthest`.** Then you only need to remember one number. Jump Game II counts jumps the way BFS counts levels.

---

## Table of Contents

- [0. Why these problems feel random](#0-why-these-problems-feel-random)
- [1. Intervals: the overlap condition, derived](#1-intervals-the-overlap-condition-derived)
- [2. Why sorting, and why by start (for combining)](#2-why-sorting-and-why-by-start-for-combining)
- [3. Merge Intervals (56)](#3-merge-intervals-56)
- [4. Insert Interval (57)](#4-insert-interval-57)
- [5. Choosing and counting intervals](#5-choosing-and-counting-intervals)
  - [5.1 Non-overlapping Intervals (435): the problem](#51-non-overlapping-intervals-435-the-problem)
  - [5.2 Why sort by end: counterexamples, then the exchange argument](#52-why-sort-by-end-counterexamples-then-the-exchange-argument)
  - [5.3 Minimum Number of Arrows (452): the same idea, closed ends](#53-minimum-number-of-arrows-452-the-same-idea-closed-ends)
  - [5.4 Counting overlaps: Divide Intervals Into Minimum Number of Groups (2406)](#54-counting-overlaps-divide-intervals-into-minimum-number-of-groups-2406)
- [6. Greedy in general: how to decide if it's safe](#6-greedy-in-general-how-to-decide-if-its-safe)
- [7. Jump Game (55)](#7-jump-game-55)
- [8. Jump Game II (45)](#8-jump-game-ii-45)
- [9. Recognizing these problems](#9-recognizing-these-problems)
- [10. Python details](#10-python-details)
- [11. Practice ladder](#11-practice-ladder)
- [Common mistakes](#common-mistakes)
- [Self-check questions](#self-check-questions)
- [Sources](#sources)

---

## 0. Why these problems feel random

A typical solution to an interval problem looks like this: "sort by the second element, keep a variable, compare with `>=`." Three choices, none explained. If you try to memorize them, every new problem has a slightly different set, and it feels random.

There are really only three questions behind every solution in this lecture:

| Question | What it decides | Where it's derived |
|---|---|---|
| **When do two intervals conflict?** | the comparison (`<=` or `<`) | §1 |
| **In what order should I look at them?** | the sort key (start or end) | §2 (start), §5.2 (end) |
| **What do I need to remember about the ones I've already seen?** | the variable(s) you keep (`merged[-1]`, `last_end`, `farthest`) | each problem's "names" table |

And for greedy, one more:

| Question | What it decides |
|---|---|
| **Can I prove the choice I make now is never worse?** | whether greedy is allowed at all (§6) |

If you answer those four questions in order, you get the solution, and you'll know *why* it's right. That's what removes the randomness.

---

## 1. Intervals: the overlap condition, derived

**Representation.** An interval is a pair `[start, end]` with `start <= end`. In these problems, intervals are **closed**: both endpoints belong to the interval (lecture 008's boxes, not cuts). `[2, 5]` includes 2, 3, 4 and 5.

**Name the question:** when do `A = [a, b]` and `B = [c, d]` overlap (share at least one point)?

Deriving it directly is awkward, because there are many ways to overlap (partly, one inside the other, exactly equal). The opposite is simpler, so derive that first (your positive-test habit, used in reverse to find the positive form):

1. **They don't overlap** exactly when one is completely to the left of the other.
2. "A is completely to the left of B" means A ends before B starts: `b < c`.
3. "B is completely to the left of A" means `d < a`.
4. So **no overlap** is `b < c or d < a`.
5. **Overlap** is the opposite: `not (b < c or d < a)`. The opposite of an `or` is an `and` of the opposites: `b >= c and d >= a`.
6. Written start-first: **`c <= b and a <= d`**. In words: *each one starts before (or when) the other ends.*

Draw the cases on a number line to see it hold:

```
A partly overlaps B          A contains B               A left of B (no overlap)
A: [1-------5]               A: [1-----------8]         A: [1---3]
B:      [4-------9]          B:     [3---5]             B:          [5---8]
c=4 <= b=5 ✓, a=1 <= d=9 ✓   c=3 <= b=8 ✓, a=1 <= d=5 ✓  c=5 <= b=3 ✗
```

**After sorting by start**, you know `a <= c` (A starts first). Then `a <= d` is automatically true (since `a <= c <= d`), so the whole condition is just:

> **`c <= b`: the next interval starts before (or when) the current one ends.**

That single comparison appears in almost every interval solution.

### Touching endpoints: decide from the problem, not from habit

What about `[1, 4]` and `[4, 5]`? They share exactly the point 4. Whether that counts depends on what the intervals *mean*:

| Problem | Meaning | Do `[1,4]` and `[4,5]` conflict? | Comparison |
|---|---|---|---|
| 56 Merge Intervals | covered ranges | **yes** (example: they merge to `[1,5]`) | `next_start <= current_end` |
| 435 Non-overlapping | meetings: one can end as the next begins | **no** (example: `[1,2],[2,3]` need no removal) | conflict when `next_start < last_end` |
| 452 Arrows | balloons; an arrow at x hits a balloon if `start <= x <= end` | **yes** (one arrow at 4 hits both) | conflict when `next_start <= arrow_at` |
| 2406 Groups | intervals are inclusive | **yes** (stated in the problem) | process starts before ends at equal times |

So the `<` vs `<=` choice isn't something to remember. **Find the example that has touching endpoints and read off the answer.** If none exists, ask the interviewer: "Do intervals that touch at an endpoint count as overlapping?" That's a strong clarifying question.

---

## 2. Why sorting, and why by start (for combining)

Without sorting, any interval could overlap any other, so you'd compare all pairs: O(n²).

**After sorting by start**, walk left to right, and keep one **current** interval (the one you're building). For the next interval, there are only two cases:

1. It starts at or before the current end (`next_start <= current_end`): it overlaps, so it belongs to the current group.
2. It starts after the current end: it doesn't overlap the current interval. And **no later interval can either**, because every later interval starts even later (that's what sorting gave you). So the current interval is **finished**, and you'll never need to look at it again.

That second point is the "ruled out because…" sentence from lecture 006: *the current interval is ruled out from any future merge because every remaining interval starts after `next_start`, which is already past `current_end`.* It's why one pass after sorting is enough, and the total cost is O(n log n) for the sort plus O(n) for the pass.

---

## 3. Merge Intervals (56)

**Problem (paraphrased).** Given a list `intervals` where `intervals[i] = [start_i, end_i]`, merge all overlapping intervals, and return a list of non-overlapping intervals that covers exactly the same points. The order of the output doesn't matter.
Examples: `[[1,3],[2,6],[8,10],[15,18]]` → `[[1,6],[8,10],[15,18]]` (`[1,3]` and `[2,6]` overlap); `[[1,4],[4,5]]` → `[[1,5]]` (touching counts).
Constraints: `1 <= len(intervals) <= 10^4`; `0 <= start_i <= end_i <= 10^4`.

**Names:**

| Name | Stands for |
|---|---|
| `merged` | the finished intervals, plus the one being built at the end |
| `merged[-1]` | **the interval currently being built** (the current group) |
| `merged[-1][1]` | the current group's end: the **largest end** of any interval in the group |

That last line is where your July bug came from. The current end is not "the end of the last interval added." It's the largest end of *any* interval in the group. Here's why that matters:

```
[1-----------------10]       ← first interval
    [2--3]                   ← starts inside, ends inside: a NESTED interval
         [4--5]              ← also inside [1, 10]
```

If you set the end to the newest interval's end, then adding `[2, 3]` *shrinks* the group's end from 10 to 3. Then `[4, 5]` looks like it starts after the end and becomes a separate interval. The bug version returns `[[1,3],[4,5]]` (from running it), but the right answer is `[[1,10]]`. The fix is to keep the larger end: `max(current_end, end)`.

Test for this case every time: **"what if the next interval is completely inside the current one?"**

```python
def merge(intervals):
    intervals.sort(key=lambda iv: iv[0])          # by start: then only the current group can overlap the next one
    merged = []                                    # finished groups; merged[-1] is the group being built
    for start, end in intervals:
        if merged and start <= merged[-1][1]:      # starts before (or when) the current group ends: touching counts
            merged[-1][1] = max(merged[-1][1], end)    # largest end in the group (a nested interval mustn't shrink it)
        else:
            merged.append([start, end])            # the previous group is finished; start a new one
    return merged
```

Trace the first example (from running it):

| next interval | comparison | `merged` after |
|---|---|---|
| `[1, 3]` | `merged` empty: new group | `[[1, 3]]` |
| `[2, 6]` | `2 <= 3`: overlap; end = max(3, 6) | `[[1, 6]]` |
| `[8, 10]` | `8 <= 6`? no: new group | `[[1, 6], [8, 10]]` |
| `[15, 18]` | `15 <= 10`? no: new group | `[[1, 6], [8, 10], [15, 18]]` |

**O(n log n) time** (the sort), O(n) space for the output.

---

## 4. Insert Interval (57)

**Problem (paraphrased).** You're given `intervals`, a list of **non-overlapping** intervals **sorted by start**, and one more interval `newInterval`. Insert it so the list is still sorted and non-overlapping, merging wherever needed, and return the new list.
Examples: `intervals = [[1,3],[6,9]]`, `newInterval = [2,5]` → `[[1,5],[6,9]]`; `intervals = [[1,2],[3,5],[6,7],[8,10],[12,16]]`, `newInterval = [4,8]` → `[[1,2],[3,10],[12,16]]`.
Constraints: `0 <= len(intervals) <= 10^4`; the list is sorted and non-overlapping; `0 <= start <= end <= 10^5`.

**The easy answer:** append `newInterval`, then run `merge`. That's correct, but it's O(n log n). Because the list is already sorted, you can do it in **O(n)** with one pass in three phases.

**Derive the phases from the overlap condition (§1).** Call the new interval `[new_start, new_end]`. Each existing interval `[s, e]` is in exactly one of three places:

| Phase | Where it is | Condition | What to do |
|---|---|---|---|
| 1. before | completely left of the new one | `e < new_start` (ends before the new one starts) | copy it as is |
| 2. overlapping | touches the new one | `s <= new_end` (and it isn't in phase 1) | absorb it: widen the new interval |
| 3. after | completely right | everything left over (`s > new_end`) | copy it as is |

Because the list is sorted, the phases come **in that order**, so three `while` loops in a row handle them.

```python
def insert(intervals, newInterval):
    new_start, new_end = newInterval              # grows as overlapping intervals are absorbed
    result = []
    i = 0                                          # box index of the next interval to look at
    n = len(intervals)
    while i < n and intervals[i][1] < new_start:  # phase 1: ends before the new one starts
        result.append(intervals[i])
        i += 1
    while i < n and intervals[i][0] <= new_end:   # phase 2: starts before (or when) the new one ends
        new_start = min(new_start, intervals[i][0])
        new_end = max(new_end, intervals[i][1])
        i += 1
    result.append([new_start, new_end])
    while i < n:                                   # phase 3: everything after
        result.append(intervals[i])
        i += 1
    return result
```

Trace the second example (`newInterval = [4, 8]`; from running it):

| interval | phase | `[new_start, new_end]` after | `result` after |
|---|---|---|---|
| `[1, 2]` | 1: `2 < 4` | `[4, 8]` | `[[1, 2]]` |
| `[3, 5]` | 2: `3 <= 8` | `[3, 8]` | |
| `[6, 7]` | 2: `6 <= 8` | `[3, 8]` | |
| `[8, 10]` | 2: `8 <= 8` (touching counts) | `[3, 10]` | |
| — | add the new interval | | `[[1, 2], [3, 10]]` |
| `[12, 16]` | 3 | | `[[1, 2], [3, 10], [12, 16]]` |

**Why phase 2 only checks `s <= new_end`:** any interval reaching phase 2 already failed phase 1's test, so its end is `>= new_start`. That's the other half of the overlap condition, already known. (Same simplification as "after sorting" in §1.)

**O(n) time.** Edge cases: empty `intervals` (only the middle `append` runs); the new interval before everything; after everything; covering everything.

---

## 5. Choosing and counting intervals

### 5.1 Non-overlapping Intervals (435): the problem

**Problem (paraphrased).** Given `intervals`, return the **minimum number of intervals to remove** so that the rest don't overlap. Intervals that only touch at an endpoint (like `[1,2]` and `[2,3]`) do **not** overlap.
Examples: `[[1,2],[2,3],[3,4],[1,3]]` → `1` (remove `[1,3]`); `[[1,2],[1,2],[1,2]]` → `2`; `[[1,2],[2,3]]` → `0`.
Constraints: `1 <= len(intervals) <= 10^5`; `-5·10^4 <= start < end <= 5·10^4`.

**Reframe it first.** "Remove as few as possible" is the same as "**keep as many as possible**, with no two overlapping." Answer = `n - (most you can keep)`. Keeping is easier to think about.

### 5.2 Why sort by end: counterexamples, then the exchange argument

This is the "random" choice everyone memorizes. Here's how you'd discover it.

**Step 1: list the reasonable greedy choices.** "Keep intervals one at a time, each time picking the one that…"
- (a) starts earliest,
- (b) is shortest,
- (c) ends earliest.

**Step 2: try to break each one with 2–3 intervals** (two minutes per idea, on paper).

- (a) **Starts earliest:** `[1,100], [2,3], [4,5]`. Picking `[1,100]` first blocks both others, so you keep 1. The best is 2 (`[2,3]` and `[4,5]`). **Broken.** (From running it: keeps 1.)
- (b) **Shortest:** `[1,5], [4,7], [6,10]`. The shortest is `[4,7]` (length 3), and it overlaps both others, so you keep 1. The best is 2 (`[1,5]` and `[6,10]`). **Broken.** (From running it: keeps 1.)
- (c) **Ends earliest:** both counterexamples above give 2 with this rule. Try to break it… you won't. That's the signal to try to *prove* it.

**Step 3: the exchange argument.** Show that some best answer starts with the greedy choice, in small steps:

1. Let `g` be the interval that **ends earliest** of all of them.
2. Take *any* best answer, `BEST` (a largest set of non-overlapping intervals), and look at its interval that ends earliest; call it `o`.
3. `g` ends earliest of all intervals, so `g.end <= o.end`.
4. Swap `o` out of `BEST` and `g` in. Does anything now overlap `g`? Every other interval in `BEST` didn't overlap `o` and ends no earlier than `o`, so it starts at or after `o.end`. Since `g.end <= o.end`, it also starts at or after `g.end`: **no overlap with `g`.**
5. The swapped set is still valid and the same size, so it's also a best answer, and it **starts with `g`**.
6. So choosing `g` first is never a mistake. Remove `g` and every interval that overlaps it, and what's left is the same problem, only smaller. Repeat step 1 on it.

The intuition in one sentence: **the interval that ends first leaves the most room for everything after it.** But the sentence comes *after* the argument; the argument is what makes it safe.

**Names for the code:**

| Name | Stands for |
|---|---|
| `last_end` | the end of the last interval you **kept** (where the free room starts) |
| `kept` | how many you've kept |

Walk the intervals in order of end. One can be kept if it starts at or after `last_end` (touching is fine in 435, so `>=`).

```python
def eraseOverlapIntervals(intervals):
    intervals.sort(key=lambda iv: iv[1])          # by END: the earliest-ending interval leaves the most room
    kept = 0
    last_end = float("-inf")                       # nothing kept yet: every interval fits
    for start, end in intervals:
        if start >= last_end:                      # starts at or after the last kept one ends (touching is OK)
            kept += 1
            last_end = end
        # otherwise it overlaps the last kept one: remove it (counted below)
    return len(intervals) - kept
```

Trace the first example, sorted by end (from running it):

| interval | decision | `last_end` after | `kept` after |
|---|---|---|---|
| `[1, 2]` | keep | 2 | 1 |
| `[2, 3]` | keep (`2 >= 2`) | 3 | 2 |
| `[1, 3]` | remove (`1 < 3`) | 3 | 2 |
| `[3, 4]` | keep | 4 | 3 |

Answer: `4 - 3 = 1` ✓.

**Why you only compare with the last kept interval:** every kept interval ends at or before `last_end` (they were kept in order of end). If the new interval starts at or after `last_end`, it's after all of them. One comparison covers them all.

### 5.3 Minimum Number of Arrows (452): the same idea, closed ends

**Problem (paraphrased).** Balloons are horizontal intervals `points[i] = [x_start, x_end]`. An arrow shot straight up at position `x` bursts every balloon with `x_start <= x <= x_end`. Return the **minimum number of arrows** to burst them all.
Examples: `[[10,16],[2,8],[1,6],[7,12]]` → `2` (arrows at 6 and 11); `[[1,2],[3,4],[5,6],[7,8]]` → `4`; `[[1,2],[2,3],[3,4],[4,5]]` → `2` (touching balloons share an arrow).
Constraints: `1 <= len(points) <= 10^5`; `-2^31 <= x_start < x_end <= 2^31 - 1`.

**It's 435 in disguise.** Sort by end. The first balloon to end must be hit by some arrow, and that arrow can be no further right than the balloon's end. Shooting **exactly at its end** hits it and as many later balloons as possible (exchange argument: any arrow further left hits a subset of what this one hits among the remaining balloons). Then skip every balloon that arrow hits.

The only difference from 435 is the touching rule: here a balloon starting exactly at the arrow **is** hit (`x_start <= x`), so a new arrow is needed only when `start > arrow_at`.

```python
def findMinArrowShots(points):
    points.sort(key=lambda p: p[1])              # by end
    arrows = 0
    arrow_at = float("-inf")                      # position of the last arrow shot
    for start, end in points:
        if start > arrow_at:                      # the last arrow misses this balloon (touching = hit)
            arrows += 1
            arrow_at = end                        # shoot at this balloon's end
    return arrows
```

Compare with 435: same sort, same one-variable walk, `>=` became `>`. That's the touching rule from §1, read from the third example.

### 5.4 Counting overlaps: Divide Intervals Into Minimum Number of Groups (2406)

This is the free version of the well-known "how many meeting rooms?" question.

**Problem (paraphrased).** Given `intervals[i] = [left_i, right_i]` (**inclusive**), divide them into the minimum number of groups so that no two intervals in the same group intersect. Intervals that share even one point intersect (`[1,5]` and `[5,8]` do). Return the minimum number of groups.
Examples: `[[5,10],[6,8],[1,5],[2,3],[1,10]]` → `3`; `[[1,3],[5,6],[8,10],[11,13]]` → `1`.
Constraints: `1 <= len(intervals) <= 10^5`; `1 <= left_i <= right_i <= 10^6`.

**Name the question:** at any moment, the intervals that are "happening" all need different groups. So you need at least as many groups as **the most intervals happening at once**. (That's also enough: when an interval starts, at most `best - 1` others are happening, so some group is free. That's the matching upper bound.)

**How to count "happening at once" without checking every point: a sweep.**
- Turn each interval into two **events**: a start (+1) and an end (−1).
- Sort the events by time, and walk them, keeping `active` = the number of intervals currently happening.
- The answer is the largest `active` ever seen.

**The tie rule, derived from the touching rule.** If one interval ends at 5 and another starts at 5, they intersect (inclusive). So at time 5, both must be counted as happening at the same time: process the **start before the end**. Encoding a start as `0` and an end as `1` makes Python's tuple sort do exactly that, because `(5, 0)` sorts before `(5, 1)`.

```python
def minGroups(intervals):
    events = []                                    # (time, kind): kind 0 = start, 1 = end
    for start, end in intervals:
        events.append((start, 0))
        events.append((end, 1))
    events.sort()                                  # by time; at equal times, starts (0) before ends (1)
    active = 0                                     # intervals happening right now
    best = 0
    for time, kind in events:
        if kind == 0:
            active += 1
            best = max(best, active)
        else:
            active -= 1
    return best
```

For `[[1,5],[5,6],[2,3]]` the sorted events are `(1,0) (2,0) (3,1) (5,0) (5,1) (6,1)` (from running it). At time 5, the start of `[5,6]` is processed before the end of `[1,5]`, so `active` reaches 2 there, and the answer is 2 (`[1,5]` and `[5,6]` can't share a group).

If touching did **not** count (meetings that can be back to back), you'd flip the tie rule: ends before starts.

---

## 6. Greedy in general: how to decide if it's safe

**Greedy** means building the answer one choice at a time, always taking the option that looks best right now, and never going back. It's fast (usually one pass, after a sort). The danger is that "best right now" might be wrong later.

### Your July tests, checked

| Your test | Verdict |
|---|---|
| "My decision limits my future options, so it's not greedy" | **Not reliable.** In 435, keeping an interval blocks every interval that overlaps it, which limits the future, and greedy is still correct. Every decision in every problem limits the future somehow |
| "We're not asked for the lowest of something, so it's not greedy" | **Half right.** Greedy never fits *counting* problems ("how many ways"), because counting needs every way, not one good one. That's a correct reason to rule it out for Decode Ways. But greedy does solve yes/no problems (§7) and construction problems |

### The test that works

1. **State the greedy choice in one sentence.** "Rob the largest house first." "Keep the interval that ends first." "Always jump as far as possible." If you can't say it in one sentence, it isn't a clear greedy idea yet.
2. **Try to break it with 2–3 items, for about two minutes.** For House Robber, `[2, 3, 2]`: "largest first" robs the 3 and then can't rob either neighbour, for a total of 3. The best is `2 + 2 = 4`. **Broken: greedy is out, use DP** (and that's the real reason greedy fails there, not "decisions limit the future").
3. **If you can't break it, argue an exchange:** take any best answer, and show you can swap its first choice for your greedy choice without making it invalid or worse (§5.2 steps 1–6). If you can, greedy is safe.

In an interview, step 2 out loud is often enough: "Let me try to break this… `[1,100],[2,3],[4,5]` breaks sorting by start; sorting by end survives, and here's why: the interval ending first leaves the most room."

### Two shapes of "why greedy is right"

| Shape | The sentence | Used in |
|---|---|---|
| **Exchange** | "Any best answer can be changed to start with my choice without getting worse" | 435, 452 |
| **Stays ahead** | "After every step, what I have is at least as good as what any other strategy could have at that step" | 55 (`farthest` is the farthest anyone could reach), 45 (BFS levels) |

---

## 7. Jump Game (55)

**Problem (paraphrased).** You start at index 0 of the array `nums`. `nums[i]` is the **maximum** jump length from index `i`: from `i` you can jump to any index from `i + 1` to `i + nums[i]`. Return `True` if you can reach the last index.
Examples: `[2,3,1,1,4]` → `True` (0 → 1 → 4); `[3,2,1,0,4]` → `False` (every path lands on index 3, whose jump is 0).
Constraints: `1 <= len(nums) <= 10^4`; `0 <= nums[i] <= 10^5`.

**Brute force:** try every jump from every position (DFS/DP): up to O(n²) or worse. The greedy version is O(n), and here's why it's allowed.

**Name:** `farthest` = the farthest index you can reach using jumps from the positions looked at so far.

**The fact that makes one number enough: the reachable positions are always one unbroken range `0 … farthest`.** Derive it:

1. Suppose index `j` is reachable, and from `j` you can jump up to `nums[j]`.
2. Then every index from `j + 1` up to `j + nums[j]` is reachable from `j` (the jump can be *any* length up to the maximum).
3. So reaching a far index never "skips" one in between: if `j` can reach `j + nums[j]`, it can also reach everything before it.
4. Starting from `0 … 0` (just index 0) and extending one reachable position at a time, the reachable set stays a range with no gaps.

So you only need to remember the range's right end, `farthest`. Walk `i` from left to right:
- If `i > farthest`, index `i` is outside the range: unreachable, and so is everything after it. Return `False`.
- Otherwise `i` is reachable, so its jump extends the range: `farthest = max(farthest, i + nums[i])`.

```python
def canJump(nums):
    farthest = 0                         # every index 0 … farthest is reachable (no gaps)
    for i, jump in enumerate(nums):
        if i > farthest:                 # i is past the reachable range: stuck
            return False
        farthest = max(farthest, i + jump)
    return True
```

Trace `[3,2,1,0,4]` (from running it):

| `i` | `nums[i]` | `farthest` after | note |
|---|---|---|---|
| 0 | 3 | 3 | |
| 1 | 2 | 3 | |
| 2 | 1 | 3 | |
| 3 | 0 | 3 | |
| 4 | 4 | — | `4 > 3`: unreachable → **False** |

**This is "stays ahead":** after looking at positions `0 … i`, `farthest` is the farthest index *any* sequence of jumps through those positions can reach. No cleverer strategy can do better, because `farthest` already includes every option.

---

## 8. Jump Game II (45)

**Problem (paraphrased).** Same setup as 55, but now the last index is **guaranteed** to be reachable. Return the **minimum number of jumps** to reach it.
Examples: `[2,3,1,1,4]` → `2` (0 → 1 → 4); `[2,3,0,1,4]` → `2`.
Constraints: `1 <= len(nums) <= 10^4`; `0 <= nums[i] <= 1000`; the last index is reachable.

**Think of it as BFS (lecture 009)** where each jump is one level:
- Level 0: index 0.
- Level 1: every index reachable with 1 jump.
- Level 2: every index reachable with 2 jumps but not fewer. And so on.

By §7's fact, each level is a range with no gaps, and each level starts right after the previous one ends. So you don't need a queue. You need two numbers:

| Name | Stands for |
|---|---|
| `current_end` | the last index of the range reachable with `jumps` jumps |
| `farthest` | the farthest index reachable with **one more** jump, from any position scanned so far |
| `jumps` | how many jumps it takes to reach the range you're scanning now |

Walk `i` left to right. Each `i` updates `farthest`. When `i` reaches `current_end`, you've scanned the whole current level, so the next level is everything up to `farthest`, and it costs one more jump.

**Why the loop stops at `n - 2` (`range(len(nums) - 1)`):** a jump is counted when you *leave* a level. Once you're standing on the last index, you don't leave it. If the loop also ran at `i = n - 1`, and `n - 1` happened to be exactly `current_end`, it would count a jump you never take. Check with the smallest input, `[0]`: `n = 1`, the loop runs zero times, and the answer is 0 jumps ✓.

```python
def jump(nums):
    jumps = 0
    current_end = 0                      # last index reachable with `jumps` jumps
    farthest = 0                         # farthest index reachable with one more jump
    for i in range(len(nums) - 1):       # not the last index: you never jump FROM it
        farthest = max(farthest, i + nums[i])
        if i == current_end:             # finished scanning this level
            jumps += 1
            current_end = farthest       # the next level ends here
    return jumps
```

Trace `[2,3,1,1,4]` (from running it):

| `i` | `nums[i]` | `farthest` after | `i == current_end`? |
|---|---|---|---|
| 0 | 2 | 2 | yes → `jumps = 1`, `current_end = 2` |
| 1 | 3 | 4 | no |
| 2 | 1 | 4 | yes → `jumps = 2`, `current_end = 4` |
| 3 | 1 | 4 | no |

Index 4 (the last) is inside the range ending at 4, so the answer is **2** ✓.

**O(n) time, O(1) space.** The greedy part: you never decide *which* index to jump to. You only track how far each level reaches, which includes every choice at once.

---

## 9. Recognizing these problems

| The problem says… | Think | Sort by | Remember |
|---|---|---|---|
| "merge overlapping," "union," "total covered length" | combine (§3) | start | the current group (`merged[-1]`) |
| "insert into a sorted, non-overlapping list" | three phases (§4) | already sorted | the growing new interval |
| "remove the fewest so none overlap," "most non-overlapping," "max meetings attended" | choose (§5.2) | **end** | `last_end` |
| "fewest points/arrows that hit every interval" | choose, closed ends (§5.3) | **end** | `arrow_at` |
| "minimum rooms/groups," "most overlapping at once," "is any time over capacity?" | sweep (§5.4) | events by time | `active` |
| "intersections of two sorted lists of intervals" | two pointers (986 in §11) | already sorted | one pointer per list |
| "can you reach the end," "farthest you can get" | stays ahead (§7) | — | `farthest` |
| "fewest steps when each position allows a range of moves" | BFS levels as ranges (§8) | — | `current_end`, `farthest` |
| "how many ways," "count all" | **not greedy**: DP or backtracking | — | — |

---

## 10. Python details

| Detail | What to know |
|---|---|
| `intervals.sort()` | sorts lists by first element, then second on ties. Fine for "by start" |
| `intervals.sort(key=lambda iv: iv[1])` | sorts by end |
| `sort()` vs `sorted()` | `sort()` changes the input list in place (fine in LeetCode, but say so in an interview); `sorted()` returns a new list |
| `for start, end in intervals:` | unpacks each pair; much easier to read than `iv[0]`, `iv[1]` |
| `merged[-1][1] = …` | changes the last group's end in place (lists inside lists are mutable) |
| `float("-inf")` | a starting value smaller than every real start, so the first interval always passes the test |
| tuples `(time, kind)` | sort by `time`, then by `kind`: use `kind` to control tie order (§5.4) |

---

## 11. Practice ladder

Do them in order. For each one, **write the three answers from §0 as comments before coding** (when do two conflict, including touching; what to sort by and why; what to remember), and for greedy problems, write your 2–3 item attempt to break it.

| # | Problem | Level | What it practises |
|---|---|---|---|
| 1 | 56 Merge Intervals (redo) | Medium | sort by start; the nested-interval `max` |
| 2 | 57 Insert Interval | Medium | three phases from the overlap condition |
| 3 | 435 Non-overlapping Intervals | Medium | sort by end; reframe as "keep the most" |
| 4 | 452 Minimum Number of Arrows to Burst Balloons | Medium | same as 435, closed touching rule |
| 5 | 986 Interval List Intersections | Medium | two pointers on two sorted lists: move the pointer whose interval ends first |
| 6 | 2406 Divide Intervals Into Minimum Number of Groups | Medium | sweep with events; tie order |
| 7 | 1094 Car Pooling | Medium | sweep with weighted events (passengers instead of +1) |
| 8 | 55 Jump Game | Medium | reachable range, `farthest` |
| 9 | 45 Jump Game II | Medium | BFS levels as ranges |
| 10 | 763 Partition Labels | Medium | intervals in disguise: each letter's first and last position |
| stretch | 134 Gas Station, 846 Hand of Straights, 1288 Remove Covered Intervals | Medium | exchange/stays-ahead arguments in new settings |

**Hint for 986 (without the code):** at each step, the overlap of the two current intervals is `[max(starts), min(ends)]` if that's a valid interval. Then advance the pointer whose interval ends first: derive why with "ruled out because…".

**Hint for 763:** for each letter, its first and last positions form an interval. A part must contain each letter's whole interval. That's merging (§3), done in one pass with `last[letter]`.

---

## Common mistakes

| Mistake | Fix |
|---|---|
| Merge: setting the end to the newest interval's end | `max(current_end, end)`: test a nested interval (§3) |
| Guessing `<` vs `<=` | find the touching example in the statement; ask if there isn't one (§1) |
| Sorting by start in 435/452 | sort by end; the counterexample `[1,100],[2,3],[4,5]` (§5.2) |
| Answering 435's "remove" directly | reframe: keep the most, answer `n - kept` |
| Sweep: wrong tie order at equal times | derive it from whether touching intervals conflict (§5.4) |
| Ruling greedy in or out by feel | one-sentence choice → 2–3 item counterexample → exchange argument (§6) |
| "Decisions limit the future, so not greedy" | not a valid test; 435 is the counterexample (§6) |
| Jump Game II counting a jump at the last index | loop over `range(len(nums) - 1)`; check `[0]` → 0 |
| Forgetting that `sort()` changes the input | say it, or use `sorted()` |
| Merging into a list without checking `merged` is empty | `if merged and …` |

---

## Self-check questions

1. Derive the overlap condition for `[a, b]` and `[c, d]` from "one is completely to the left of the other."
<details><summary>Answer</summary>

No overlap: `b < c or d < a`. Overlap is the opposite: `b >= c and d >= a`, i.e. `c <= b and a <= d` ("each starts before or when the other ends").
</details>

2. After sorting by start, why does the overlap check shrink to `next_start <= current_end`?
<details><summary>Answer</summary>

With `a <= c`, the other half, `a <= d`, is automatically true because `a <= c <= d`.
</details>

3. How do you decide whether touching endpoints count as overlapping?
<details><summary>Answer</summary>

From the problem's meaning and its examples (`[1,4],[4,5]` merging in 56; `[1,2],[2,3]` needing no removal in 435). If there's no example, ask.
</details>

4. In Merge Intervals, why `max(current_end, end)` instead of `end`?
<details><summary>Answer</summary>

A nested interval like `[2,3]` inside `[1,10]` would otherwise shrink the group's end to 3, and later intervals inside `[1,10]` would wrongly start new groups.
</details>

5. Why is one pass enough after sorting by start?
<details><summary>Answer</summary>

Once the next interval starts after the current group's end, every later interval starts even later, so none can touch the current group: it's finished.
</details>

6. Give counterexamples for "keep the earliest-starting" and "keep the shortest" in 435.
<details><summary>Answer</summary>

Earliest start: `[1,100],[2,3],[4,5]` keeps 1 instead of 2. Shortest: `[1,5],[4,7],[6,10]` keeps 1 (`[4,7]`) instead of 2.
</details>

7. Write the exchange argument for "keep the interval that ends first."
<details><summary>Answer</summary>

Let `g` end earliest overall and `o` be the earliest-ending interval of any best answer. `g.end <= o.end`. Every other kept interval starts at or after `o.end`, so also at or after `g.end`. Swapping `o` for `g` keeps the answer valid and the same size, so some best answer starts with `g`. Repeat on what's left.
</details>

8. Why does 452 use `start > arrow_at` where 435 uses `start >= last_end`?
<details><summary>Answer</summary>

In 452 a balloon that starts exactly at the arrow is hit (touching counts), so a new arrow is needed only when it starts strictly after. In 435 touching intervals don't conflict, so an interval starting exactly at `last_end` can be kept.
</details>

9. In the sweep, why do starts come before ends at equal times in 2406?
<details><summary>Answer</summary>

The intervals are inclusive, so one ending at 5 and one starting at 5 intersect and must be counted as active together. Encoding starts as 0 and ends as 1 sorts starts first.
</details>

10. Why is "my choice limits my future options" not a valid reason to rule out greedy? What is?
<details><summary>Answer</summary>

Every choice limits the future, including in 435, where greedy is correct. The valid reason is a concrete counterexample (e.g. `[2,3,2]` for "rob the largest first").
</details>

11. In Jump Game, why is one number (`farthest`) enough?
<details><summary>Answer</summary>

The reachable indices are always one unbroken range `0 … farthest`: from a reachable `j` you can land on every index up to `j + nums[j]`, so no gaps form.
</details>

12. In Jump Game II, what do `current_end` and `farthest` stand for, and why does the loop skip the last index?
<details><summary>Answer</summary>

`current_end` is the end of the range reachable with `jumps` jumps; `farthest` is the farthest reachable with one more. A jump is counted when leaving a level, and you never leave the last index, so scanning it could count a jump you don't take.
</details>

---

## Sources

- Problems: LeetCode 56, 57, 435, 452, 2406, 55, 45 (ladder: 986, 1094, 763; stretch: 134, 846, 1288). Statements are paraphrased; examples and constraints come from long-standing problem pages (from my own knowledge, not re-fetched; 2026-10-19). "Meeting Rooms" (252/253) is Premium, so 2406 is used instead.
- Greedy correctness (exchange arguments, "greedy stays ahead"): Kleinberg & Tardos, *Algorithm Design*, chapter 4 (interval scheduling is its first example); Cormen et al., *Introduction to Algorithms*, chapter on greedy algorithms (activity selection).
- Python: `list.sort` and `sorted` with `key` (https://docs.python.org/3/howto/sorting.html).
- Verification (2026-10-19): every function compared against a brute-force reference on 3,000 random inputs (subsets for 435/452, point coverage for 56/57/2406, BFS for 55/45). Counterexamples and traces produced by running the code.
