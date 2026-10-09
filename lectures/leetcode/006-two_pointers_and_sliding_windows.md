# Lecture 006: Two Pointers and Sliding Windows: Ruling Things Out One Step at a Time

> **For:** Timothy · **Date:** 2026-10-09
> **Prerequisites:** lecture 004 (binary search, the idea of "ruling out candidates") and lecture 005 (prefix sums; why negative numbers break windows). Lecture 003's trace tables are used throughout.
> **Why this topic, why now:** it's the next step in the gradient plan (lecture 005 §10 pointed here). It targets your history directly:
> - **Birthday Chocolate (July):** a fixed window with a silent `-+` typo, an element added twice at the boundary, then `d` used where `m` belonged.
> - **3Sum (July):** `p2 = 1` instead of `i + 1`, ranges *reset* instead of *shrunk* (infinite loop), and an inverted dedup condition.
> - **Divisible Sum Pairs (Sep):** labeled "two pointers" when it was a double loop.
>
> Every one of those is a boundary, initialization or progress bug, which is still your biggest bug class. Pointer problems are also extremely common in interviews.
> **Format notes:** every problem includes the full statement (paraphrased), examples and constraints. Every rule is derived.
> **Verification:** every solution was tested against brute force on 3,000 random inputs. Trace tables were produced by running the code.

---

## Core ideas (the answer key)

1. **Two pointers and sliding windows are both "rule out candidates without checking them one by one."** Each pointer move eliminates a whole set of pairs or subarrays at once, which is why O(n²) becomes O(n).
2. **Every pointer move needs a reason you can say:** "`nums[lo]` can't be part of any answer, because…" If you can't finish that sentence, the move is a guess.
3. **Inward pointers (sorted data):** if `nums[lo] + nums[hi]` is too small, `lo` is ruled out, because even the largest remaining partner isn't enough. If too big, `hi` is ruled out. Each step removes one element.
4. **Pointers only move toward unchecked territory.** `lo` only increases and `hi` only decreases. Resetting a pointer outward is the infinite-loop bug from your 3Sum (the same "walls only move inward" rule as Spiral).
5. **Fixed window of size k:** name the window `nums[r-k+1 .. r]`. When `r` enters, `nums[r]` is added; the element leaving is `nums[r-k]`, which exists only when `r - k >= 0`. The window is complete only when `r - k + 1 >= 0`.
6. **Variable window:** extend `r` by one every step; shrink `l` while the window is invalid (or, for minimum problems, while it's still valid). Then update the answer.
7. **A variable window only works if validity is monotone:** shrinking a valid window keeps it valid (or growing an invalid one keeps it invalid). That's the same shape requirement as binary search. Negative numbers break it for sums, which is why lecture 005 used prefix sums.
8. **Read/write pointers (same direction):** the invariant is "`nums[0:write]` is the finished part of the answer." `read` scans every element; `write` only advances when something is kept.
9. **3Sum = sort + fix one element + inward two pointers on the rest.** Start the pair at `i + 1` (derived from "strictly to the right of i"), and skip duplicates by comparing with the *previous* value.
10. **Every pointer loop is O(n) because of an amortized count:** each pointer moves at most n times in total, even when there's a `while` inside a `for`.

---

## Table of Contents

- [0. The map: three pointer patterns](#0-the-map-three-pointer-patterns)
- [1. Inward pointers: Two Sum II, derived (167)](#1-inward-pointers-two-sum-ii-derived-167)
- [2. Inward pointers when the reason is less obvious: Container With Most Water (11)](#2-inward-pointers-when-the-reason-is-less-obvious-container-with-most-water-11)
- [3. 3Sum, rebuilt from your July attempt (15)](#3-3sum-rebuilt-from-your-july-attempt-15)
- [4. Read/write pointers (26, 283)](#4-readwrite-pointers-26-283)
- [5. Fixed windows: Birthday Chocolate and 643, derived](#5-fixed-windows-birthday-chocolate-and-643-derived)
- [6. Variable windows: the expand/shrink template (3, 209)](#6-variable-windows-the-expandshrink-template-3-209)
- [7. When a window works, and when it doesn't](#7-when-a-window-works-and-when-it-doesnt)
- [8. Why these are O(n): the amortized count](#8-why-these-are-on-the-amortized-count)
- [9. Tracing pointer code](#9-tracing-pointer-code)
- [10. Recognizing the pattern](#10-recognizing-the-pattern)
- [11. Practice ladder](#11-practice-ladder)
- [Common mistakes](#common-mistakes)
- [Interview relevance](#interview-relevance)
- [Self-check questions](#self-check-questions)
- [Sources](#sources)

---

## 0. The map: three pointer patterns

| Pattern | Pointers | Typical data | The question | Classic problems |
|---|---|---|---|---|
| **Inward** | `lo` at the left end, `hi` at the right end, moving toward each other | **sorted** array, or a problem where the two ends compete | "Which pair (or triple) satisfies…?" / "best pair" | 167 Two Sum II, 11 Container With Most Water, 15 3Sum |
| **Read/write** (same direction) | `read` scans everything, `write` marks where the next kept element goes | any array, modified **in place** | "Remove / compact / partition in place" | 26 Remove Duplicates, 283 Move Zeroes |
| **Sliding window** (same direction) | `l` and `r` bound a contiguous range; both only move right | array or string | "Best / count of **contiguous** subarray or substring with a property" | 643, 3 Longest Substring, 209 Minimum Size Subarray Sum, Birthday Chocolate |

What they share: **each pointer only moves in one direction, and every move rules something out for good.** That's the whole source of the speedup. A double loop checks all n² pairs; these check n of them and *prove* the rest can't matter.

On your Divisible Sum Pairs label: a double loop `for i … for j in range(i+1, n)` has two indices, but neither is a "pointer" in this sense. The inner one restarts for every `i`, so nothing is ruled out. If an index ever jumps back, it isn't this pattern.

---

## 1. Inward pointers: Two Sum II, derived (167)

**Problem (paraphrased).** Given a **sorted** (non-decreasing) array `numbers` and a `target`, return the 1-based indices `[index1, index2]` (`index1 < index2`) of the two numbers that add up to `target`. There is exactly one solution, and you may not use the same element twice. Use only constant extra space.
Examples: `[2,7,11,15], 9` → `[1,2]`. `[2,3,4], 6` → `[1,3]`. `[-1,0], -1` → `[1,2]`.
Constraints: `2 <= len(numbers) <= 3·10^4`; `-1000 <= numbers[i] <= 1000`; exactly one solution.

Lecture 005's dictionary solves this in O(n) time but O(n) space. Sortedness lets you do O(1) space.

### 1.1 Derivation

**Name the candidates.** At any moment, the pairs still possible are pairs **inside** `[lo, hi]` (both indices in that range). Start with everything: `lo, hi = 0, n - 1`.

**Invariant:** *any pair that uses an index outside `[lo, hi]` has already been ruled out.*

**Look at the pair of ends:** `s = numbers[lo] + numbers[hi]`.

| Case | Reasoning | Move |
|---|---|---|
| `s == target` | Found it | return |
| `s < target` | `numbers[hi]` is the **largest** value still in play. Even paired with the largest, `numbers[lo]` is too small, so `lo` can't be in **any** remaining answer | `lo += 1` (rule `lo` out) |
| `s > target` | `numbers[lo]` is the **smallest** in play. Even paired with the smallest, `numbers[hi]` is too big, so `hi` is out | `hi -= 1` (rule `hi` out) |

Each case states a reason in the form "X can't be part of any answer because…". That sentence is what makes a pointer move correct, not a guess.

**Loop condition:** a pair needs two different indices, so continue while `lo < hi`.

```python
def twoSum(numbers, target):
    lo, hi = 0, len(numbers) - 1          # candidates: pairs inside [lo, hi]
    while lo < hi:                        # a pair needs two distinct indices
        s = numbers[lo] + numbers[hi]
        if s == target:
            return [lo + 1, hi + 1]       # the problem uses 1-based indices
        if s < target:
            lo += 1                       # lo too small even with the largest partner
        else:
            hi -= 1                       # hi too big even with the smallest partner
    return []
```

Trace on `[2, 7, 11, 15], 9`:

| lo | hi | sum | decision |
|---|---|---|---|
| 0 | 3 | 2 + 15 = 17 | > 9 → `hi -= 1` (15 is too big even with 2) |
| 0 | 2 | 2 + 11 = 13 | > 9 → `hi -= 1` |
| 0 | 1 | 2 + 7 = 9 | == 9 → return `[1, 2]` |

---

## 2. Inward pointers when the reason is less obvious: Container With Most Water (11)

**Problem (paraphrased).** You're given `height`, where `height[i]` is the height of a vertical line at position `i`. Choose two lines; together with the x-axis they form a container. Its water is `(j - i) * min(height[i], height[j])`. Return the maximum water any two lines can hold.
Example: `[1,8,6,2,5,4,8,3,7]` → `49` (lines at positions 1 and 8: width 7, height `min(8, 7) = 7`). `[1,1]` → `1`.
Constraints: `2 <= len(height) <= 10^5`; `0 <= height[i] <= 10^4`.

No sorting here, but the same "rule one end out" idea works, as long as the reason is valid.

**The reason.** Start with the widest pair, `lo = 0, hi = n - 1`. Suppose `height[lo] < height[hi]`. Every **other** container using `lo` pairs it with some `j` between `lo` and `hi`:

- its width is **smaller** (`j - lo < hi - lo`),
- its height is at most `height[lo]` (the shorter side caps it, whatever `height[j]` is).

So every remaining container that uses `lo` holds **no more** than the one just measured. `lo` is ruled out, so move it. (If `height[hi]` is the shorter one, the same argument rules out `hi`.)

```python
def maxArea(height):
    lo, hi = 0, len(height) - 1
    best = 0
    while lo < hi:
        best = max(best, (hi - lo) * min(height[lo], height[hi]))
        if height[lo] < height[hi]:
            lo += 1                       # every other container using lo is narrower and no taller
        else:
            hi -= 1                       # same argument for hi
    return best
```

The lesson: you can't move a pointer because it "seems right." **Move the pointer you can prove is useless for every remaining answer.** In an interview, that one-sentence proof is what separates this solution from a guess.

---

## 3. 3Sum, rebuilt from your July attempt (15)

**Problem (paraphrased).** Given an integer array `nums`, return all **unique** triplets `[a, b, c]` of values at three different indices with `a + b + c == 0`. The answer must not contain duplicate triplets (order inside a triplet and order of triplets don't matter).
Examples: `[-1,0,1,2,-1,-4]` → `[[-1,-1,2],[-1,0,1]]`. `[0,1,1]` → `[]`. `[0,0,0]` → `[[0,0,0]]`.
Constraints: `3 <= len(nums) <= 3000`; `-10^5 <= nums[i] <= 10^5`.

### 3.1 What went wrong in July (from lecture carreer_path/002 §1.1)

| Your line | Problem | Category |
|---|---|---|
| `p2 = 1` | The pair must be strictly right of `p1`; `p2 = 1` lets `p2 == p1` (the same element used twice) | Initialization by feel |
| After a hit: reset `p2 = p1 + 1, p3 = len - 1` | The search range grew back, so no progress and an infinite loop | Pointers moved outward |
| Dedup advanced while values *differ* | Inverted condition | Condition derived in the head |

All three are mechanical, and all three fall out of a derivation.

### 3.2 Derivation

1. **Sort.** Then for each fixed first element `nums[i]`, the problem becomes Two Sum II on the rest with `target = -nums[i]`.
2. **Name the pair's range:** "the other two elements are strictly to the right of `i`." Valid set: indices `i+1 … n-1`. So **`lo = i + 1`, `hi = n - 1`**. Init derived, not guessed.
3. **Inward moves:** exactly §1's reasoning (sum too small → `lo` ruled out; too big → `hi` ruled out).
4. **On a hit:** record it, then **both** pointers move inward. `nums[lo]` with any other partner would need the same partner value to hit 0 again, which gives a duplicate. Moving inward is also what guarantees progress.
5. **Duplicates.** Two places can create the same triplet:
   - The **same first value** twice: skip `i` when `nums[i] == nums[i - 1]` (the previous `i` already found every triplet starting with that value).
   - The **same second value** after a hit: advance `lo` while `nums[lo] == nums[lo - 1]`.

   Phrase both positively: *skip while it equals the previous one*. That's the click from Oct 5 (state the condition you want, not its negation).

```python
def threeSum(nums):
    nums.sort()
    n = len(nums)
    out = []
    for i in range(n - 2):                          # need room for two more after i
        if i > 0 and nums[i] == nums[i - 1]:
            continue                                # this first value was already fully searched
        lo, hi = i + 1, n - 1                       # the pair lives strictly right of i
        while lo < hi:
            s = nums[i] + nums[lo] + nums[hi]
            if s < 0:
                lo += 1
            elif s > 0:
                hi -= 1
            else:
                out.append([nums[i], nums[lo], nums[hi]])
                lo += 1                             # both move inward: progress
                hi -= 1
                while lo < hi and nums[lo] == nums[lo - 1]:
                    lo += 1                         # skip a repeated second value
    return out
```

Complexity: sort O(n log n), then n outer steps × O(n) inner = **O(n²)**. With n ≤ 3000 that's about 9 million steps: fine. (The brute force over all triples, O(n³) ≈ 2.7·10¹⁰, isn't.)

Note the guard `i > 0` in `nums[i] == nums[i - 1]`: `i - 1` is only a valid index when `i >= 1`. Name → valid set → test, again.

---

## 4. Read/write pointers (26, 283)

### 4.1 Remove Duplicates from Sorted Array (26)

**Problem (paraphrased).** Given a sorted array `nums`, remove duplicates **in place** so each value appears once, keeping the original order. Return `k`, the number of unique values. The first `k` positions of `nums` must hold them; what's beyond `k` doesn't matter.
Examples: `[1,1,2]` → `k = 2`, `nums` starts `[1,2]`. `[0,0,1,1,1,2,2,3,3,4]` → `k = 5`, `nums` starts `[0,1,2,3,4]`.
Constraints: `1 <= len(nums) <= 3·10^4`; `-100 <= nums[i] <= 100`; sorted non-decreasing.

**Name the two positions:**

- `read` = the next element to look at (scans every index).
- `write` = where the next kept element goes. **Invariant:** `nums[0:write]` is the finished answer so far (unique values, in order).

**Init:** the first element is always kept, so `nums[0:1]` is already finished, and `write = 1`, `read` starts at 1.
**Keep rule:** `nums[read]` is new exactly when it differs from the last kept value, `nums[write - 1]`.

```python
def removeDuplicates(nums):
    write = 1                                  # nums[0:1] is already the finished answer
    for read in range(1, len(nums)):
        if nums[read] != nums[write - 1]:      # differs from the last KEPT value
            nums[write] = nums[read]
            write += 1
    return write                               # length of the finished part
```

### 4.2 Move Zeroes (283)

**Problem (paraphrased).** Move every `0` in `nums` to the end **in place**, keeping the relative order of the non-zero elements.
Example: `[0,1,0,3,12]` → `[1,3,12,0,0]`. `[0]` → `[0]`.
Constraints: `1 <= len(nums) <= 10^4`.

Same invariant: `nums[0:write]` holds the non-zero elements seen so far, in order. Swapping (instead of overwriting) leaves the zeros behind, after `write`.

```python
def moveZeroes(nums):
    write = 0                                  # nums[0:write] = non-zeros so far, in order
    for read in range(len(nums)):
        if nums[read] != 0:
            nums[write], nums[read] = nums[read], nums[write]
            write += 1
```

---

## 5. Fixed windows: Birthday Chocolate and 643, derived

### 5.1 Birthday Chocolate, rewritten with named positions

**Problem (HackerRank, paraphrased).** A chocolate bar is a row of squares with integers `s`. Count the contiguous segments of exactly `m` squares whose integers sum to `d`.
Example: `s = [1,2,1,3,2], d = 3, m = 2` → `2` (`[1,2]` and `[2,1]`).
Constraints: `1 <= len(s) <= 100`; `1 <= s[i] <= 5`; `1 <= d <= 31`; `1 <= m <= 12`.

In July this cost you a silent `-+` typo, a double-added element, and `d` used for `m`. Here's a version with every position named and its valid set written down.

**Let `r` be the index of the newest element** (the window's right end). Then:

| Name | Expression | Valid when |
|---|---|---|
| window start | `r - m + 1` | `>= 0`, i.e. the window is **complete** only when `r >= m - 1` |
| element leaving | `r - m` | `>= 0`, i.e. something leaves only when `r >= m` |

Each step: **add** `s[r]`; **remove** `s[r - m]` if that index exists; **check** if the window is complete.

```python
def birthday(s, d, m):
    window_sum = 0
    ways = 0
    for r in range(len(s)):
        window_sum += s[r]                     # newest element enters
        if r - m >= 0:
            window_sum -= s[r - m]             # the element that just fell out of the window
        if r - m + 1 >= 0 and window_sum == d: # window start valid -> window complete
            ways += 1
    return ways
```

One loop, no separate "build the first window" phase, so there's no hand-off between two loops where the July bugs lived. Every index used is named and checked against its valid set. The parameter names are used directly (`m` for length, `d` for the target), so there's no aliasing to drift.

### 5.2 Maximum Average Subarray I (643)

**Problem (paraphrased).** Given `nums` and an integer `k`, find the contiguous subarray of length exactly `k` with the largest average, and return that average.
Example: `[1,12,-5,-6,50,3], k = 4` → `12.75` (`(12 - 5 - 6 + 50) / 4`). `[5], k = 1` → `5.0`.
Constraints: `1 <= k <= len(nums) <= 10^5`; `-10^4 <= nums[i] <= 10^4`.

The largest average has the largest sum (k is fixed), so slide a sum. This version builds the first window, then slides. Both styles are fine as long as every index is named:

```python
def findMaxAverage(nums, k):
    window_sum = sum(nums[:k])                 # window nums[0 .. k-1]
    best = window_sum
    for r in range(k, len(nums)):              # r = newest index; window is nums[r-k+1 .. r]
        window_sum += nums[r] - nums[r - k]    # enter r, leave r-k
        best = max(best, window_sum)
    return best / k
```

Check the hand-off with C1: at the first slide, `r = k`. The leaving index is `r - k = 0`, the first element of the first window ✓. The new window is `nums[1 .. k]` ✓. Plug in the edge `k = len(nums)`: the `for` range is empty, and the answer is the one full window ✓.

---

## 6. Variable windows: the expand/shrink template (3, 209)

### 6.1 The template

```
for r in range(n):                 # 1. extend: nums[r] enters the window
    add nums[r] to the window state
    while <window is invalid>:     # 2. shrink from the left until valid again
        remove nums[l] from the state
        l += 1
    update the answer with the window nums[l .. r]    # 3. window is valid here
```

**Invariant after step 2:** `nums[l .. r]` is the **longest valid window that ends at `r`**. (Any longer one would have to start before `l`, and those were shown invalid when `l` passed them.) So the best answer over all `r` is the best over all valid windows.

Window length is `r - l + 1` (closed on both ends: `l` and `r` are both in the window).

### 6.2 Longest Substring Without Repeating Characters (3)

**Problem (paraphrased).** Given a string `s`, return the length of the longest contiguous substring in which no character appears twice.
Examples: `"abcabcbb"` → `3` (`"abc"`). `"bbbbb"` → `1`. `"pwwkew"` → `3` (`"wke"`; `"pwke"` isn't contiguous).
Constraints: `0 <= len(s) <= 5·10^4`; letters, digits, symbols and spaces.

**Window state:** the set of characters currently in the window. **Invalid** means the incoming character is already in it.

```python
def lengthOfLongestSubstring(s):
    in_window = set()
    l = 0
    best = 0
    for r in range(len(s)):
        while s[r] in in_window:       # adding s[r] would repeat a character
            in_window.remove(s[l])     # shrink from the left until s[r]'s old copy is gone
            l += 1
        in_window.add(s[r])
        best = max(best, r - l + 1)    # window s[l..r] is valid
    return best
```

(This version checks validity *before* adding, so the set never holds a duplicate. Same template, just ordered so the state stays valid.)

Trace on `"pwwkew"` (expected 3):

| r | s[r] | removed while shrinking | l | window | best |
|---|---|---|---|---|---|
| 0 | p | — | 0 | `p` | 1 |
| 1 | w | — | 0 | `pw` | 2 |
| 2 | w | `p`, `w` | 2 | `w` | 2 |
| 3 | k | — | 2 | `wk` | 2 |
| 4 | e | — | 2 | `wke` | 3 |
| 5 | w | `w` | 3 | `kew` | 3 |

Row 2 shows the shrink: the new `w` duplicates the `w` at index 1, so everything up to and including that old `w` has to leave.

Your July note on this problem: `checker.remove` on a dict should have been `del checker[k]`. With a **set**, `.remove(x)` is right. For a dict, `del d[k]`.

### 6.3 Minimum Size Subarray Sum (209): shrink while still valid

**Problem (paraphrased).** Given an array of **positive** integers `nums` and a positive integer `target`, return the minimum length of a contiguous subarray whose sum is **at least** `target`. Return 0 if none exists.
Examples: `target = 7, [2,3,1,2,4,3]` → `2` (`[4,3]`). `target = 4, [1,4,4]` → `1`. `target = 11, [1,1,1,1,1,1,1,1]` → `0`.
Constraints: `1 <= target <= 10^9`; `1 <= len(nums) <= 10^5`; `1 <= nums[i] <= 10^4`.

For a **minimum**, flip step 2: while the window is **valid**, record it, then shrink to see if a shorter one still works.

```python
def minSubArrayLen(target, nums):
    l = 0
    window_sum = 0
    best = float('inf')                # "no valid window yet"
    for r in range(len(nums)):
        window_sum += nums[r]
        while window_sum >= target:    # valid: record, then try shorter
            best = min(best, r - l + 1)
            window_sum -= nums[l]
            l += 1
    return 0 if best == float('inf') else best
```

Trace on `target = 7, [2,3,1,2,4,3]` (expected 2):

| r | add | windows recorded while shrinking | l after | window after | best |
|---|---|---|---|---|---|
| 0 | +2 | — | 0 | `[2]` sum 2 | ∞ |
| 1 | +3 | — | 0 | `[2,3]` sum 5 | ∞ |
| 2 | +1 | — | 0 | `[2,3,1]` sum 6 | ∞ |
| 3 | +2 | len 4 | 1 | `[3,1,2]` sum 6 | 4 |
| 4 | +4 | len 4, len 3 | 3 | `[2,4]` sum 6 | 3 |
| 5 | +3 | len 3, len 2 | 5 | `[3]` sum 3 | **2** ✓ |

---

## 7. When a window works, and when it doesn't

The variable window relies on one property, which is the same as binary search's F…F T…T requirement:

> **Monotone validity:** if a window is valid, every shorter window inside it (same right end) is also valid. Equivalently: once a window becomes invalid, growing it can't fix it.

| Problem | Does shrinking a valid window keep it valid? | Window works? |
|---|---|---|
| No repeated characters | Yes: removing characters can't create a repeat | ✅ |
| Sum ≥ target, **all positive** | For "at least": growing only increases the sum, so a valid window stays valid as it grows (minimum problems shrink while valid) | ✅ |
| Sum == k, **negatives allowed** | No: adding a negative can make an invalid window valid again | ❌ → prefix sums + dictionary (lecture 005 §6) |
| At most k distinct characters | Yes | ✅ |

**Before using a window, say the monotone sentence out loud:** "If this window is invalid, any larger window ending here is also invalid, so moving `l` right is safe." If you can't say it truthfully, the window approach is wrong for this problem.

---

## 8. Why these are O(n): the amortized count

The variable window has a `while` inside a `for`, which looks like O(n²). It isn't:

- `r` moves right n times in total (once per `for` step).
- `l` only ever moves right, and never past `r`, so it moves at most n times **in total, across the whole run** (not per `for` step).
- Total pointer moves ≤ 2n, so **O(n)**.

The same count works for inward pointers (`lo` and `hi` together move at most n times) and read/write (`read` n times, `write` ≤ n). **The argument is always "each pointer only moves one way, and its total distance is at most n."** Say it in interviews when someone asks about the nested loop.

---

## 9. Tracing pointer code

Lecture 003's protocol, with these columns:

| Pattern | Columns | CHECK |
|---|---|---|
| Inward | `lo | hi | values | sum | decision + reason` | the ruled-out element really can't be in any answer |
| Read/write | `read | value | kept? | write | nums[0:write]` | `nums[0:write]` is a correct prefix of the expected output |
| Fixed window | `r | enters | leaves (index, valid?) | window | sum | count` | window = the real slice `s[r-m+1 .. r]` |
| Variable window | `r | enters | removed while shrinking | l | window | best` | the window after shrinking is valid; no longer valid window ends at `r` |

Good trace inputs: an answer at **the very start and the very end**; **duplicates** (3Sum, Remove Duplicates); **window size = whole array** (fixed); **no valid window at all** (209 returns 0); **the empty string** (problem 3).

---

## 10. Recognizing the pattern

| Signal | Pattern |
|---|---|
| **Sorted** array + pair/triple with a target sum | Inward pointers (O(1) space) |
| "Two ends compete" (widths, heights, palindromes) | Inward pointers, with a "which end is useless" proof |
| "In place", "remove", "compact", "partition", "O(1) extra space" | Read/write pointers |
| "Contiguous subarray/substring of length k" | Fixed window |
| "Longest/shortest contiguous … such that …", and validity is monotone | Variable window |
| "Contiguous subarray sum equals k" **with negatives** | Not a window: prefix sums + dictionary (lecture 005) |
| Unsorted pair-sum | Dictionary (lecture 005), or sort + inward if you need O(1) space |
| Linked list: middle, cycle, k-th from end | Fast/slow pointers (same idea: each moves one way; see the printable problem set Part 6) |

**Three comment lines before coding** (same habit as lectures 004 and 005):

```python
# pattern: <inward / read-write / fixed window / variable window>
# invariant: <what's ruled out / what nums[0:write] holds / what the window satisfies>
# move rule: <which pointer moves, and the one-sentence reason it's safe>
```

---

## 11. Practice ladder

| # | Problem | New idea | Full problem |
|---|---|---|---|
| 1 | 167 Two Sum II | Inward pointers + the "ruled out because…" sentence | §1 |
| 2 | 26 Remove Duplicates from Sorted Array | Read/write invariant | §4.1 |
| 3 | 283 Move Zeroes | Read/write with swap | §4.2 |
| 4 | Birthday Chocolate (redo from July) | Fixed window with named positions | §5.1 |
| 5 | 643 Maximum Average Subarray I | Fixed window, build-then-slide | §5.2 |
| 6 | 3 Longest Substring Without Repeating (on your to-do list) | Variable window, longest | §6.2 |
| 7 | 209 Minimum Size Subarray Sum | Variable window, shortest | §6.3 |
| 8 | 11 Container With Most Water | Inward with a non-obvious proof | §2 |
| 9 | 15 3Sum (redo from July) | Fix one + inward + dedup | §3 |
| stretch | 424 Longest Repeating Character Replacement, 76 Minimum Window Substring | Window state is a count dictionary | |

Log each attempt in the tracker. Tag pointer bugs as `INIT` (start position), `PROGRESS` (moved the wrong way or reset), `COND` (loop/shrink condition) or `LANDING`, so we can see whether these classes are shrinking.

---

## Common mistakes

| Mistake | Your history | Fix |
|---|---|---|
| Second pointer starts at a fixed index (`p2 = 1`) | 3Sum, July | Name its range ("strictly right of `i`") → `i + 1` |
| Resetting pointers after a hit | 3Sum, July (infinite loop) | Pointers only move inward. On a hit, move both inward |
| Dedup comparing with the *next* element, or inverted | 3Sum, July | Skip while equal to the **previous** value (`nums[lo] == nums[lo-1]`) |
| Separate "build first window" loop with an off-by-one hand-off | Birthday, July | Name `r - k` (leaving) and `r - k + 1` (start) and check their valid sets; or use one loop (§5.1) |
| Using a window when values can be negative | — | Check monotone validity (§7); otherwise prefix sums |
| `r - l` as the window length | — | Closed window `[l, r]` has `r - l + 1` elements |
| Moving a pointer "because it seems right" | — | Say the "X can't be in any answer because…" sentence |
| `in_window.remove` vs `del d[k]` confusion | Longest Substring, July | set → `.remove(x)`; dict → `del d[k]` |

---

## Interview relevance

- Two pointers and sliding windows are **among the most frequent patterns** in phone screens. 3, 11, 15 and 209 are classic mediums.
- **The proof sentence is what interviewers look for.** "Moving the shorter line is safe because every other container using it is narrower and no taller" turns a memorized trick into reasoning.
- **Expect the follow-up "why is this O(n) with a nested loop?"** Answer with §8's amortized count.
- **Pattern choice is often the real test:** "subarray sum equals k" looks like a window but needs prefix sums when negatives are allowed. Saying *why* shows depth.

---

## Self-check questions

1. In Two Sum II, the sum is too small. Why is it safe to move `lo` and not `hi`?
<details><summary>Answer</summary>

`numbers[hi]` is the largest value still in play. If `numbers[lo]` plus the largest partner is still too small, `numbers[lo]` can't reach the target with any remaining partner, so it's ruled out. Moving `hi` down would only make sums smaller.
</details>

2. In Container With Most Water, why move the shorter line?
<details><summary>Answer</summary>

Every other container using the shorter line is narrower (its partner is closer) and no taller (the shorter line caps the height). So none of them can beat the one just measured, and the shorter line is ruled out.
</details>

3. In 3Sum, derive the starting value of `lo` for a fixed `i`.
<details><summary>Answer</summary>

The other two elements must be at indices strictly right of `i`, so the valid set is `i+1 … n-1`, giving `lo = i + 1`, `hi = n - 1`.
</details>

4. What went wrong when your July 3Sum reset `p2` and `p3` after a hit?
<details><summary>Answer</summary>

The search range grew back to its original size, so there was no progress, and it found the same triplet forever (an infinite loop). Pointers must only move inward: on a hit, `lo += 1` and `hi -= 1`.
</details>

5. In Remove Duplicates, what's the invariant, and why does `write` start at 1?
<details><summary>Answer</summary>

`nums[0:write]` is the finished answer (unique values in order). The first element is always kept, so `nums[0:1]` is already finished.
</details>

6. Fixed window of size m with `r` as the newest index: which index leaves, and when does it exist?
<details><summary>Answer</summary>

`r - m`; it exists when `r - m >= 0`, i.e. `r >= m`. The window is complete when its start `r - m + 1 >= 0`.
</details>

7. State the variable-window invariant after the shrink loop.
<details><summary>Answer</summary>

`nums[l .. r]` is the longest valid window ending at `r`.
</details>

8. Why can't "subarray sum equals k" with negative numbers use a sliding window?
<details><summary>Answer</summary>

Validity isn't monotone: adding a negative number can bring an over-target window back to exactly k, so "shrink when too big" can skip valid windows. Use prefix sums + a count dictionary.
</details>

9. Longest Substring has a `while` inside a `for`. Why is it still O(n)?
<details><summary>Answer</summary>

`l` only moves right and never passes `r`, so across the whole run it moves at most n times. `r` moves n times. Total work is O(n).
</details>

10. What's the length of the window `nums[l .. r]` (both included)?
<details><summary>Answer</summary>

`r - l + 1`.
</details>

11. For Minimum Size Subarray Sum, why do you shrink while the window is *valid* rather than invalid?
<details><summary>Answer</summary>

You want the shortest valid window. Each valid window is recorded, then shortened to see if a shorter one still meets the target. When it stops being valid, extend `r` again.
</details>

12. Your Sep 26 Divisible Sum Pairs used `for i … for j in range(i+1, n)`. Why isn't that two pointers?
<details><summary>Answer</summary>

The inner index restarts for every `i`, so nothing is ruled out and all n² pairs are checked. Two-pointer patterns only move each pointer in one direction, so the total work is O(n).
</details>

---

## Sources

- Problems: LeetCode 167, 11, 15, 26, 283, 643, 3, 209, 424, 76 and HackerRank "Birthday Chocolate" ("Subarray Division"). Statements paraphrased; examples and constraints from long-standing problem pages (from my own knowledge, not re-fetched; 2026-10-09).
- Your July attempts (3Sum, Birthday Chocolate, Longest Substring) as analysed in `lectures/carreer_path/002-the-leetcode-diagnosis-and-the-solving-protocol.md` §1. Your Birthday Chocolate attempts were also re-run on 2026-10-04.
- Verification (2026-10-09): every function tested against brute force on 3,000 random inputs (including duplicates, negatives, empty strings and whole-array windows). Trace tables were generated by running the code.
- Companions: lecture 004 (monotone shape, "ruling out candidates"), lecture 005 §6 (prefix sums for negative numbers), lecture 003 (trace protocol), lecture 001 §4 (walls only move inward).
