# Lecture 004: Binary Search: One Template, Derived Instead of Memorized

> **For:** Timothy · **Date:** 2026-10-05
> **Prerequisites:** lecture 001 §4 (closed vs half-open), lecture 003 (the Trace Protocol). Helpful: the boundary method from Oct 5 (name the quantity → write its valid set → test membership positively), which this whole lecture is built on.
> **Why this topic, why now:** see §0. Short version: your most frequent bug type is boundaries (off-by-one, wrong inequality, wrong landing spot), and binary search is the purest boundary problem there is. You have **zero** attempts at it, it shows up constantly in interviews, and it's where the idea that clicked on Oct 5 (*name the quantity → write its valid set → test membership positively*) pays off the most.
> **Companion:** `002-printable_problem_set.md` Part 8 has four of the same problems written in two templates. This lecture teaches **one** template and shows how both of those come from it.
> **Verification:** every function here was tested against brute force (or Python's `bisect`) on 3,000 random inputs. Every trace table was produced by running the code.

---

## Core ideas (the answer key)

1. **Binary search finds the boundary in a yes/no sequence that looks like `F F F F T T T`.** That's the only shape it needs. "Sorted array" is just one way to get that shape.
2. **Name the answer first:** `first_true` = the first index where the question is True. **Write its valid set:** `0 … n`, where `n` means "no True anywhere."
3. **One template, with closed candidates `[lo, hi]`:** `lo, hi = 0, n` → `while lo < hi` → `mid = (lo + hi) // 2` → if `is_true(mid)`: `hi = mid`, else `lo = mid + 1` → return `lo`.
4. **Every line is derived from one invariant:** *the answer is always in `[lo, hi]`*. If `mid` is True, `mid` might be the answer, so keep it: `hi = mid`. If `mid` is False, `mid` can't be the answer: `lo = mid + 1`.
5. **The loop stops when one candidate is left (`lo == hi`). That candidate is the answer.** No extra checks inside the loop.
6. **`lo = mid` (without `+ 1`) is an infinite loop** when two candidates are left. Floor division puts `mid` on `lo`, and nothing moves.
7. **Exact search is a special case:** find the first index with `nums[i] >= target`, then check whether `nums[i] == target`.
8. **Rotated arrays and "binary search on the answer" are the same template with a different question.** Find the question that goes `F…F T…T`.
9. **Binary search on the answer:** when the problem asks "the minimum X such that…", and if X works then every bigger X works too, search over X.
10. **Trace it with columns `lo | hi | mid | question(mid) | decision`** and check the invariant on every row. Traces are 3–4 rows long, because the range halves each step.

---

## Table of Contents

- [0. Why this is the next gradient step](#0-why-this-is-the-next-gradient-step)
- [1. The map: what binary search is actually for](#1-the-map-what-binary-search-is-actually-for)
- [2. Deriving the template, step by step](#2-deriving-the-template-step-by-step)
- [3. The traps, and why the template avoids them](#3-the-traps-and-why-the-template-avoids-them)
- [4. Tracing binary search](#4-tracing-binary-search)
- [5. Exact search, insert position, first and last (704, 35, 34)](#5-exact-search-insert-position-first-and-last-704-35-34)
- [6. Rotated arrays (153, 33)](#6-rotated-arrays-153-33)
- [7. Binary search on the answer (875, 1011)](#7-binary-search-on-the-answer-875-1011)
- [8. Recognizing a binary search problem](#8-recognizing-a-binary-search-problem)
- [9. Python's `bisect`, and the other template you'll see](#9-pythons-bisect-and-the-other-template-youll-see)
- [10. Practice ladder](#10-practice-ladder)
- [Common mistakes](#common-mistakes)
- [Interview relevance](#interview-relevance)
- [Self-check questions](#self-check-questions)
- [Sources](#sources)

---

## 0. Why this is the next gradient step

You asked me to pick. Here's the reasoning, from your weakness tracker:

| Candidate next topic | Weaknesses it trains | Coverage gap it fills | Interview frequency | Verdict |
|---|---|---|---|---|
| **Binary search** | Boundaries, inequalities, landing spots, initialization, conventions; uses the Oct 5 boundary method directly | **Zero attempts** | Very high (sorted data, rotated arrays, "minimum X such that") | **Chosen** |
| Hashing & prefix sums | Pattern recognition, complexity checks | Light (Two Sum, Group Anagrams) | Very high | Next after this |
| Heaps | Python library fluency | Zero attempts | High | Later |
| More DP | Recursion contract | Covered by lecture 002 + its practice ladder | High | Keep practicing from lecture 002 |

Binary search wins because it's **almost nothing but boundary decisions**. The algorithm is three lines. Everything that goes wrong in binary search is a choice between `<` and `<=`, between `mid` and `mid + 1`, and between `n` and `n - 1`. Those are exactly your bugs. Getting this one right, *by derivation*, trains the skill that transfers to everything else.

Also worth noting: you traced Spiral Matrix II with the lecture 003 method and **found the `matrix[left][i]` bug yourself, before submitting.** That's the first bug you've found with your own trace. This lecture uses the same trace format, so keep doing that.

---

## 1. The map: what binary search is actually for

### 1.1 The one shape

Forget "sorted array" for a moment. Binary search needs a **yes/no question asked at each position**, where the answers look like this:

```
position:   0  1  2  3  4  5  6
question:   F  F  F  F  T  T  T
                        ^
                        first_true = 4
```

All the Falses come first, then all the Trues. (Mathematicians call this *monotone*: once the answer turns True, it stays True.) Binary search finds **where the switch happens** in O(log n) questions instead of n.

Why it works: ask at a middle position. If the answer is T, the switch is there or to the left, so the whole right side can be discarded. If it's F, the switch is to the right, so the left side and `mid` itself can be discarded. Each question halves the range.

### 1.2 Where the `F…F T…T` shape comes from

| Problem | Position | The question at each position | Shape |
|---|---|---|---|
| Sorted array, find insert spot for `target` | index `i` | `nums[i] >= target`? | sorted → F…F T…T ✓ |
| First bad version (278) | version `v` | `isBadVersion(v)`? | given as F…F T…T |
| Rotated sorted array, find the minimum (153) | index `i` | `nums[i] <= nums[-1]`? | big rotated part F, small part T ✓ |
| Koko eating bananas (875) | speed `k` | "can she finish in `h` hours at speed `k`?" | too slow F, fast enough T ✓ |
| Ship within days (1011) | capacity `c` | "can we ship in `days` days with capacity `c`?" | F…F T…T ✓ |

**The skill isn't the loop. It's finding the question.** Once the question is right, the loop is identical every time.

---

## 2. Deriving the template, step by step

This is the boundary method that clicked for you on Oct 5 (name → valid set → membership), applied to binary search. Do it once slowly here. After that, the code writes itself.

### Step 1: Name the answer

```
first_true = the smallest position where is_true(position) is True
```

### Step 2: Write its valid set

Positions run `0 … n-1`. But there might be **no** True at all (`F F F F`), and the answer has to say so. Use `n` for "none" (one past the last position):

```
0 <= first_true <= n          # n means "no True anywhere"
```

That's `n + 1` possible answers. Notice that this is the half-open convention appearing naturally: `n` is a legal *answer* even though it isn't a legal *index*.

### Step 3: The candidate range is the valid set

Keep two variables that bracket the possible answers:

```
lo, hi = 0, n                 # first_true is somewhere in [lo, hi], both ends included
```

**Invariant (true at the top of every loop pass):** `first_true` is in `[lo, hi]`. Equivalently: every position left of `lo` is F, and the position `hi` is T (or `hi == n`).

### Step 4: When are we done?

When exactly one candidate is left: `lo == hi`. So keep going **while there's more than one**:

```
while lo < hi:
```

### Step 5: Pick a position to ask about

```
mid = (lo + hi) // 2          # floor, so lo <= mid < hi: mid is never hi
```

`mid` is strictly less than `hi` because `lo < hi` and the division rounds down. That matters in §3.

### Step 6: Shrink the candidates using the answer at `mid`

| `is_true(mid)` | What it tells you | Which candidates survive | Update |
|---|---|---|---|
| **True** | the first True is at `mid` or left of it | `[lo, mid]`, and `mid` **stays** a candidate | `hi = mid` |
| **False** | `mid` and everything left of it is F | `[mid + 1, hi]`, and `mid` is **out** | `lo = mid + 1` |

Both updates keep the invariant. Both strictly shrink the range (because `lo <= mid < hi`).

### Step 7: Return the one remaining candidate

```
return lo                     # lo == hi == first_true
```

### The template

```python
def first_true(lo, hi, is_true):
    # smallest x in [lo, hi) with is_true(x); returns hi if there is none
    while lo < hi:
        mid = (lo + hi) // 2
        if is_true(mid):
            hi = mid
        else:
            lo = mid + 1
    return lo
```

That's it. Every problem in this lecture is this function with a different `is_true` and different starting `lo, hi`.

**The one sentence to say in an interview:** *"I'm looking for the first position where the condition is true. The answer is always in [lo, hi]. If mid satisfies the condition it's still a candidate, so hi = mid. If not, it's ruled out, so lo = mid + 1. When one candidate is left, that's the answer."*

---

## 3. The traps, and why the template avoids them

Every classic binary search bug comes from mixing two conventions or skipping one step of §2.

| Trap | What happens | Why the template avoids it |
|---|---|---|
| **`lo = mid`** (no `+1`) | With two candidates, e.g. `lo=0, hi=1`: `mid = 0`; if False, `lo = 0` again. **Infinite loop.** (Verified: the loop never ends on `[1,3]`, target 3.) | False means `mid` is ruled out, so it must leave the range: `mid + 1` |
| **`hi = mid - 1`** with `while lo < hi` | Throws away `mid`, which might be the answer | True means `mid` is still a candidate: keep it |
| **`while lo <= hi`** with `hi = mid` | When `lo == hi`, `mid == hi`; True → `hi = mid` → no progress → infinite loop | `lo < hi` stops at exactly one candidate |
| **`hi = n - 1`** when there might be no answer | Can never return "none"; returns `n-1` even when `nums[n-1]` is False | Valid set includes `n` ("none") → `hi = n` |
| **Checking `nums[mid] == target` inside the loop and returning** | Works for "any match", but gives *some* match, not the first; mixing it with boundary logic causes bugs | Find the boundary first; check equality once, after the loop |
| **`mid = (lo + hi + 1) // 2`** (ceiling) with this template | `mid` can equal `hi`, `hi = mid` doesn't shrink → infinite loop | Floor division guarantees `mid < hi` |

Notice the pattern: each update has to be consistent with **what `lo` and `hi` mean**. That's the convention lesson from lecture 001 again: pick one meaning, derive every line from it, never mix.

(In C or Java, `(lo + hi) // 2` can overflow for huge values, so people write `lo + (hi - lo) // 2`. Python integers don't overflow, so either is fine in Python. Mention it if asked.)

---

## 4. Tracing binary search

Binary search traces are short (the range halves each row), which makes them good practice for the lecture 003 protocol.

**Columns:** `lo | hi | mid | question at mid (literal) | decision`. **CHECK:** the invariant (everything left of `lo` is F; `hi` is T or `n`).

**Input:** `nums = [1, 3, 5, 6]`, question `nums[i] >= target`. Three targets cover all the branch patterns:

**target = 5** (expected 2)

| lo | hi | mid | `nums[mid] >= 5`? | decision |
|---|---|---|---|---|
| 0 | 4 | 2 | `5 >= 5` → True | `hi = mid` |
| 0 | 2 | 1 | `3 >= 5` → False | `lo = mid + 1` |
| 2 | 2 | — | `lo == hi` → stop | return **2** ✓ |

**target = 2** (expected 1: it would be inserted before the 3)

| lo | hi | mid | `nums[mid] >= 2`? | decision |
|---|---|---|---|---|
| 0 | 4 | 2 | `5 >= 2` → True | `hi = mid` |
| 0 | 2 | 1 | `3 >= 2` → True | `hi = mid` |
| 0 | 1 | 0 | `1 >= 2` → False | `lo = mid + 1` |
| 1 | 1 | — | stop | return **1** ✓ |

**target = 7** (expected 4 = `n`: no element is ≥ 7)

| lo | hi | mid | `nums[mid] >= 7`? | decision |
|---|---|---|---|---|
| 0 | 4 | 2 | `5 >= 7` → False | `lo = mid + 1` |
| 3 | 4 | 3 | `6 >= 7` → False | `lo = mid + 1` |
| 4 | 4 | — | stop | return **4** ✓ (= n, "none") |

Good trace inputs for binary search: the target **in the middle**, **before everything**, **after everything**, and a **duplicate**. Lengths 1, 2 and 4 cover the edge cases.

---

## 5. Exact search, insert position, first and last (704, 35, 34)

### 5.1 Search Insert Position (35): the template, unmodified

"Return the index where `target` is, or where it would be inserted." That's `first_true` with the question `nums[i] >= target`:

```python
def searchInsert(nums, target):
    # answer: first index i with nums[i] >= target; valid set 0..n
    lo, hi = 0, len(nums)
    while lo < hi:
        mid = (lo + hi) // 2
        if nums[mid] >= target:
            hi = mid
        else:
            lo = mid + 1
    return lo
```

### 5.2 Binary Search (704): boundary, then check

```python
def search(nums, target):
    i = searchInsert(nums, target)               # first index with nums[i] >= target
    if i < len(nums) and nums[i] == target:      # valid index AND actually equal
        return i
    return -1
```

The check uses the same boundary method: `i` is a named position, its valid set as an index is `0 <= i < len(nums)`, so test that first, then compare.

### 5.3 First and Last Position (34): two boundaries

- **First** position of `target` = first index with `nums[i] >= target`.
- **Last** position of `target` = (first index with `nums[i] >= target + 1`) − 1. That's the first index past all the `target`s, minus one.

```python
def searchRange(nums, target):
    def first_at_least(x):                       # first index with nums[i] >= x; n if none
        lo, hi = 0, len(nums)
        while lo < hi:
            mid = (lo + hi) // 2
            if nums[mid] >= x:
                hi = mid
            else:
                lo = mid + 1
        return lo
    start = first_at_least(target)
    if start == len(nums) or nums[start] != target:
        return [-1, -1]
    end = first_at_least(target + 1) - 1
    return [start, end]
```

(The `target + 1` trick works because values are integers. For general values, use the question `nums[i] > target` instead.)

---

## 6. Rotated arrays (153, 33)

### 6.1 Find Minimum in Rotated Sorted Array (153)

`[4, 5, 6, 7, 0, 1, 2]`. The array is two sorted runs: a **big** run (`4 5 6 7`) followed by a **small** run (`0 1 2`). The minimum is the first element of the small run.

**Find the question.** Every element of the small run is `<= nums[-1]` (the last element belongs to the small run). Every element of the big run is `> nums[-1]`. So:

```
index:        0  1  2  3  4  5  6
nums:         4  5  6  7  0  1  2
nums[i] <= 2: F  F  F  F  T  T  T      ← the shape. first_true = 4 → minimum = nums[4] = 0
```

**Valid set of the answer:** the last element always satisfies the question, so there's always a True, and the answer is in `0 … n-1`. So `hi = n - 1`, not `n`. (Name → valid set → bounds. The valid set decides the initialization.)

```python
def findMin(nums):
    last = nums[-1]
    lo, hi = 0, len(nums) - 1          # a True always exists (the last element), so no "none"
    while lo < hi:
        mid = (lo + hi) // 2
        if nums[mid] <= last:
            hi = mid
        else:
            lo = mid + 1
    return nums[lo]
```

Trace on `[4,5,6,7,0,1,2]` (expected index 4):

| lo | hi | mid | `nums[mid] <= 2`? | decision |
|---|---|---|---|---|
| 0 | 6 | 3 | `7 <= 2` → False | `lo = 4` |
| 4 | 6 | 5 | `1 <= 2` → True | `hi = 5` |
| 4 | 5 | 4 | `0 <= 2` → True | `hi = 4` |
| 4 | 4 | — | stop | `nums[4] = 0` ✓ |

Unrotated input `[1, 2, 3]`: every element is `<= 3`, so the question is `T T T` and `first_true = 0`. Correct, with no special case.

### 6.2 Search in Rotated Sorted Array (33): two small searches

The printable problem set solves this in one loop with a "which half is sorted?" case analysis. That works, but it's four comparisons with several `<` vs `<=` decisions, exactly where you slip. Here's a version built from pieces you already have:

1. Find `pivot` = the index of the minimum (153's search).
2. If `target <= nums[-1]`, it can only be in the small run `[pivot, n)`. Otherwise only in the big run `[0, pivot)`.
3. Run `searchInsert` on that range, then check equality.

```python
def search(nums, target):
    n = len(nums)
    last = nums[-1]
    lo, hi = 0, n - 1                       # 1. pivot = first index with nums[i] <= last
    while lo < hi:
        mid = (lo + hi) // 2
        if nums[mid] <= last:
            hi = mid
        else:
            lo = mid + 1
    pivot = lo
    if target <= last:                      # 2. which run can hold target?
        lo, hi = pivot, n                   #    small run: indices [pivot, n)
    else:
        lo, hi = 0, pivot                   #    big run:   indices [0, pivot)
    while lo < hi:                          # 3. first index in that run with nums[i] >= target
        mid = (lo + hi) // 2
        if nums[mid] >= target:
            hi = mid
        else:
            lo = mid + 1
    if lo < n and nums[lo] == target:
        return lo
    return -1
```

Still O(log n) (two searches). The benefit is that each piece is the same template you've already traced. **Composing known pieces beats inventing a new case analysis under pressure.** If an interviewer asks for one pass, you can mention the one-loop version afterwards.

---

## 7. Binary search on the answer (875, 1011)

### 7.1 The idea

Sometimes there's no array to search. The problem asks for **the minimum value X such that some condition holds**, and:

- you can **check** whether a given X works (usually in O(n)), and
- if X works, **every bigger X also works** (monotone).

Then the "positions" are the possible values of X, the question is "does X work?", and the shape is `F…F T…T`. The answer is the first True.

### 7.2 Koko Eating Bananas (875)

Piles `[3, 6, 7, 11]`, `h = 8` hours. Each hour she eats up to `k` bananas from one pile. Find the minimum `k`.

Use the derivation procedure:

1. **Name the answer:** `k` = eating speed (bananas per hour).
2. **Valid set:** at least 1. At most `max(piles)`, because at that speed every pile takes exactly 1 hour and anything faster can't help. So `1 <= k <= max(piles)`. A valid speed always exists at `max(piles)` (since `h >= len(piles)`), so `hi = max(piles)` with no "none" value.
3. **The question:** `can_finish(k)`: total hours `= sum(ceil(p / k))` is `<= h`. Faster never hurts, so it's monotone.
4. **Template.**

```python
def minEatingSpeed(piles, h):
    def can_finish(k):
        hours = 0
        for p in piles:
            hours += (p + k - 1) // k      # ceil(p / k) using integers only
        return hours <= h
    lo, hi = 1, max(piles)                 # answer is in [1, max(piles)]
    while lo < hi:
        mid = (lo + hi) // 2
        if can_finish(mid):
            hi = mid
        else:
            lo = mid + 1
    return lo
```

`(p + k - 1) // k` is integer ceiling division: e.g. `p=7, k=3`: `9 // 3 = 3` hours (3+3+1). Avoid `math.ceil(p / k)` with floats in interviews if you can. The integer version is exact.

Trace (expected 4):

| lo | hi | mid | hours at mid | `<= 8`? | decision |
|---|---|---|---|---|---|
| 1 | 11 | 6 | 1+1+2+2 = 6 | True | `hi = 6` |
| 1 | 6 | 3 | 1+2+3+4 = 10 | False | `lo = 4` |
| 4 | 6 | 5 | 1+2+2+3 = 8 | True | `hi = 5` |
| 4 | 5 | 4 | 1+2+2+3 = 8 | True | `hi = 4` |
| 4 | 4 | — | stop | | return **4** ✓ |

Complexity: O(n · log(max(piles))): about 20 checks even for values up to 10⁶.

### 7.3 Capacity to Ship Packages Within D Days (1011): the same shape

1. **Name:** `cap` = ship capacity.
2. **Valid set:** at least `max(weights)` (the heaviest package must fit), at most `sum(weights)` (ship everything in one day).
3. **Question:** `can_ship(cap)`: greedily load packages in order and start a new day when the next one doesn't fit. Is `days_needed <= days`?

```python
def shipWithinDays(weights, days):
    def can_ship(cap):
        needed, load = 1, 0
        for w in weights:
            if load + w > cap:              # next package doesn't fit today
                needed += 1
                load = 0
            load += w
        return needed <= days
    lo, hi = max(weights), sum(weights)
    while lo < hi:
        mid = (lo + hi) // 2
        if can_ship(mid):
            hi = mid
        else:
            lo = mid + 1
    return lo
```

The binary search part is identical to Koko. Only `can_*` and the valid set change.

---

## 8. Recognizing a binary search problem

| Signal in the problem | Think |
|---|---|
| Input is **sorted** (or "rotated sorted") | Binary search over indices |
| "Must run in **O(log n)**" | Binary search, almost always |
| "Find the **minimum / maximum X such that** …" and checking one X is easy | Binary search on the answer: is "X works" monotone? |
| The answer range is huge (up to 10⁹) but `n` is small | Binary search on the answer |
| "First / last occurrence", "insert position", "first bad version" | `first_true` directly |
| A **maximum** X such that something works (works for small X, fails for big) | Shape is `T…T F…F`. Flip it: search for the first X that **fails**, then answer = that − 1. Or flip the question |

Before writing code, write these three lines as comments. They're the whole design:

```python
# answer: <name it>               e.g. k = eating speed
# valid set: <lo> .. <hi>         e.g. 1 .. max(piles)
# question: <is_true(x)>, F…F T…T  e.g. can_finish(k)
```

---

## 9. Python's `bisect`, and the other template you'll see

### 9.1 `bisect`

Python's standard library already has `first_true` for sorted lists:

| Call | Returns | Equivalent question |
|---|---|---|
| `bisect.bisect_left(nums, x)` | first index with `nums[i] >= x` | §5.1 exactly (verified identical on 3,000 random inputs) |
| `bisect.bisect_right(nums, x)` | first index with `nums[i] > x` | |

Fine to use in practice and usually in interviews ("I'll use `bisect_left`, which returns the first index ≥ x"). But be able to write the template yourself. Interviewers often ask for exactly that, and rotated arrays and answer-search need the hand-written version anyway.

### 9.2 The closed `lo <= hi` template

The printable problem set's 704 uses the other common template:

```python
lo, hi = 0, len(nums) - 1
while lo <= hi:
    mid = (lo + hi) // 2
    if nums[mid] == target: return mid
    if nums[mid] < target: lo = mid + 1
    else: hi = mid - 1
return -1
```

It's correct, and it has its own invariant: "if `target` is present, it's in `nums[lo..hi]`". Here `mid` is either the answer (return immediately) or ruled out (both updates skip it), so the loop runs while the range is non-empty (`lo <= hi`).

**Recommendation: learn one template deeply (`first_true`) and recognize the other.** The `lo <= hi` version only finds *an* exact match. The `first_true` version handles every problem in this lecture with the same three update lines. Mixing the two templates' lines (e.g. `lo <= hi` with `hi = mid`) is the most common way to write an infinite loop.

---

## 10. Practice ladder

Gradient order: each one adds exactly one new thing. For each problem: write the three comment lines from §8 first, trace the smallest inputs from §4, and only then Submit.

| # | Problem | What's new | Trace inputs |
|---|---|---|---|
| 1 | 35 Search Insert Position | The template itself | `[1,3,5,6]` with 5, 2, 7, 0 |
| 2 | 704 Binary Search | Boundary, then equality check | target absent, length 1 |
| 3 | 278 First Bad Version | The question is a function call | n = 1, bad = 1 |
| 4 | 34 First and Last Position | Two boundaries | `[5,7,7,8,8,10]`, 8 and 6 |
| 5 | 153 Find Minimum in Rotated | Finding the question; `hi = n-1` from the valid set | rotated, unrotated, length 1 |
| 6 | 33 Search in Rotated | Composing two searches | target in each run, absent |
| 7 | 875 Koko Eating Bananas | Search on the answer | the example; `h == len(piles)` |
| 8 | 1011 Ship Within D Days | Same, a different check | `days = 1`, `days = len(weights)` |
| 9 | 74 Search a 2D Matrix | Template + framebuffer index (lecture 001 §6.1) | 1×1, target in last row |
| stretch | 162 Find Peak Element, 410 Split Array Largest Sum | Less obvious questions | |

Log each in the tracker. Boundary bugs here should be tagged `COND` / `LANDING` / `INIT` so we can see whether boundary bugs are going down.

---

## Common mistakes

| Mistake | Why it's wrong | Correct version |
|---|---|---|
| `lo = mid` | `mid` was ruled out; with two candidates it loops forever | `lo = mid + 1` |
| `hi = mid - 1` in the `lo < hi` template | Discards a possible answer | `hi = mid` |
| `while lo <= hi` with `hi = mid` | No progress when `lo == hi` | `while lo < hi` |
| `hi = len(nums) - 1` when "none" is possible | Can't return "not found / insert at end" | `hi = len(nums)`; then check `i < len(nums)` before indexing |
| Reading `nums[lo]` after the loop without checking `lo < n` | `lo` can be `n` | Valid-set check first: `if lo < n and nums[lo] == target` |
| Wrong question direction (`T…T F…F`) | The template finds the first True, not the last | Flip the question, or search for the first failure and subtract 1 |
| Float ceiling `math.ceil(p / k)` | Fine in Python for small numbers, but exactness is worth the habit | `(p + k - 1) // k` |
| Not proving monotonicity in answer-search | Binary search gives garbage if the shape isn't F…F T…T | Say *why* bigger X keeps working before coding |

---

## Interview relevance

- Binary search is one of the most common interview families, and it's **a favorite for testing precision**: interviewers know the algorithm is short and watch for off-by-one errors.
- **What to say:** name the answer, state the valid set, state the question and why it's monotone, then the invariant sentence from §2. That narration alone signals more than the code does.
- **Search on the answer** (Koko, shipping, splitting arrays) is the medium/hard version. Recognizing it ("minimum X such that…, and X working implies bigger X works") is often the whole difficulty.
- **Rotated arrays** are a classic follow-up to plain binary search. Composing two searches is a valid, clean answer. Say why it's still O(log n).
- Always trace a 4-element example. The trace is 3 rows, and it catches the off-by-one errors interviewers are looking for.

---

## Self-check questions

1. What shape must the yes/no answers have for binary search to work?
<details><summary>Answer</summary>

`F F … F T T … T`: all Falses before all Trues (monotone). Binary search finds the first True.
</details>

2. In `first_true`, why does `hi` start at `n` and not `n - 1`?
<details><summary>Answer</summary>

The answer's valid set is `0 … n`, where `n` means "no True anywhere" (or "insert at the end"). The candidate range must contain every possible answer.
</details>

3. If `is_true(mid)` is True, why `hi = mid` and not `hi = mid - 1`?
<details><summary>Answer</summary>

`mid` itself might be the first True, so it must stay a candidate. Only everything to the right of `mid` is ruled out.
</details>

4. Show that `lo = mid` can loop forever.
<details><summary>Answer</summary>

`lo = 0, hi = 1`: `mid = (0+1)//2 = 0`. If `is_true(0)` is False, `lo = mid = 0`. Nothing changed, so the next pass is identical, forever.
</details>

5. Why is `mid` always strictly less than `hi` in the template?
<details><summary>Answer</summary>

The loop only runs while `lo < hi`, and floor division of `lo + hi` gives at most `hi - 1` when `lo < hi`. So `hi = mid` always shrinks the range.
</details>

6. For Find Minimum in Rotated Sorted Array, what's the question, and why can `hi` start at `n - 1`?
<details><summary>Answer</summary>

`nums[i] <= nums[-1]`. The small run (from the minimum to the end) answers True and the big run answers False. The last element always answers True, so an answer always exists in `0 … n-1`, with no "none" value needed.
</details>

7. How do you get the **last** position of `target` with a first-True search?
<details><summary>Answer</summary>

Find the first index with `nums[i] > target` (or `>= target + 1` for integers) and subtract 1.
</details>

8. Koko: name the answer, its valid set, and the question.
<details><summary>Answer</summary>

`k` = eating speed; `1 <= k <= max(piles)`; `can_finish(k)`: `sum(ceil(p / k)) <= h`, which is monotone because a faster speed never needs more hours.
</details>

9. Compute `ceil(7 / 3)` with integer operations only.
<details><summary>Answer</summary>

`(7 + 3 - 1) // 3 = 9 // 3 = 3`.
</details>

10. After the loop, you want `nums[lo] == target`. What must you check first, and why?
<details><summary>Answer</summary>

`lo < len(nums)`. The answer's valid set includes `n` ("none"), which isn't a valid index. Name → valid set → test membership before using it.
</details>

11. When the problem asks for the **maximum** X that works (true for small X, false for big X), how do you adapt?
<details><summary>Answer</summary>

The shape is `T…T F…F`. Search for the first X where it **fails** (question = "does X fail?", which is F…F T…T) and return that − 1. Or invert the question some other way so it goes F…F T…T.
</details>

12. Trace `searchInsert([1, 3], 3)`. How many rows?
<details><summary>Answer</summary>

`lo=0, hi=2, mid=1`: `3 >= 3` True → `hi=1`. `lo=0, hi=1, mid=0`: `1 >= 3` False → `lo=1`. `lo == hi == 1` → return 1. Two decision rows plus the stop row.
</details>

---

## Sources

- LeetCode problems: 35, 704, 278, 34, 153, 33, 875, 1011, 74, 162, 410 (numbers from long-standing listings, from my own knowledge, not re-fetched; 2026-10-05).
- Python `bisect` module: https://docs.python.org/3/library/bisect.html (`bisect_left` / `bisect_right` semantics).
- Verification (2026-10-05): `searchInsert` was checked to be identical to `bisect.bisect_left` on 3,000 random sorted arrays × 15 targets. `search`, `searchRange`, `findMin`, rotated `search`, `minEatingSpeed` and `shipWithinDays` were all checked against brute force on 3,000 random inputs each. The `lo = mid` variant was confirmed to loop forever on `[1,3]` with target 3. Trace tables were generated by running the code.
- Companions: `001-matrix_and_simulation_problems.md` §4 (conventions), `003-walking_through_code.md` (Trace Protocol), `002-printable_problem_set.md` Part 8 (the same problems, other template).
