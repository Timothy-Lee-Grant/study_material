# Attempt Review 001 (2026-10-18): Window Bounds, Reader/Writer, and Knowing You're Right

> **For:** Timothy · **Date:** 2026-10-19
> **What this folder is:** lectures built from **your own attempts**, outside the gradient roadmap. Each one takes the problems you did on a given day, finds the places where you were stuck, slow or unsure, and goes over those ideas again from several angles. The gradient lectures teach new topics. These make the topics you've already met fluent.
> **Source attempts (in `examples.py`, 2026-10-18):** 112 Path Sum, 187 Repeated DNA Sequences, 643 Maximum Average Subarray I, 26 Remove Duplicates from Sorted Array. **Not covered:** 33 Search in Rotated Sorted Array and 875 Koko, since you're going back to those yourself. This lecture says nothing about them.
> **Format notes:** each idea gets several framings, because you said that seeing an idea framed in different ways is what makes it click. Every symbol is named before it's used. All code here was run, and every trace was produced by running it.

---

## Core ideas (the answer key)

1. **You were right more often than you felt you were.** Every index bound you wrote on Oct 18 was correct. What's missing is not correctness but a **fast way to confirm it**. §1 gives you four framings of the same window facts, and §2 gives you checks that turn "I think it's right" into "I've shown it's right."
2. **A window of `k` boxes ending at box `i` is boxes `i - k + 1 … i`.** Every other window fact (the box leaving, when it's full, how many windows there are) follows from that one line.
3. **Two different loop shapes solve fixed windows:** "one loop with a building phase" (what you wrote for 643) and "build the first window, then slide" (fewer conditions). Both are correct; the second has fewer places to make a mistake.
4. **`<` versus `<=` doesn't matter by itself.** What matters is the set of values each one allows. If two conditions allow the same set, they're the same condition.
5. **The doubt-remover is the two-point check:** plug in the first and the last iteration with real numbers. If both are right, the whole loop's range is right.
6. **A second doubt-remover: a brute-force checker.** Six lines of code that compare your answer to an obviously correct slow one on random inputs. It's how every solution in these lectures is verified, and you can run it yourself.
7. **In reader/writer, `writer` is a cut, and a cut in front of the kept part is also the count of kept items.** The answer to 26 was already in `writer`.
8. **Check every name against every line that changes it.** In 26, `k` was named "the number of unique elements," but it went up in the duplicate branch.
9. **When a problem has a fixed constant (like 10), shrink it to test.** Write the code with `K` instead of `10`, then trace `K = 2` on a 4-letter string.
10. **When no idea comes, write the brute force in one sentence.** In 187, the brute force sentence already contains the real solution.

---

## Table of Contents

- [0. What your Oct 18 attempts showed](#0-what-your-oct-18-attempts-showed)
- [1. Fixed-window bounds, four ways](#1-fixed-window-bounds-four-ways)
- [2. Knowing you're right: three checks that remove the doubt](#2-knowing-youre-right-three-checks-that-remove-the-doubt)
- [3. Two shapes for a fixed window](#3-two-shapes-for-a-fixed-window)
- [4. Reader/writer, and the walk-through you planned (26)](#4-readerwriter-and-the-walk-through-you-planned-26)
- [5. Tracing a window problem without the trace exploding (187)](#5-tracing-a-window-problem-without-the-trace-exploding-187)
- [6. When no idea comes: brute force first (187)](#6-when-no-idea-comes-brute-force-first-187)
- [7. Why Path Sum checks at the leaf, not at `None` (112)](#7-why-path-sum-checks-at-the-leaf-not-at-none-112)
- [8. Drills](#8-drills)
- [Self-check questions](#self-check-questions)

---

## 0. What your Oct 18 attempts showed

| Problem | Result | Where you were stuck, slow or unsure | Section |
|---|---|---|---|
| 643 Maximum Average Subarray I | ✅ | Three bounds correct, but "this took way too long to reason through" | §1, §3 |
| 187 Repeated DNA Sequences | ✅ (after an idea hint) | No brute force came to mind; `i+10 < len(s)` missed the last window; your correct `i+9 < len(s)` "just does not feel right"; the trace got too long | §1, §2, §5, §6 |
| 26 Remove Duplicates | 🟡 | The array was always right, but `return k` returned the number of duplicates. You spotted it and planned a walk-through | §4 |
| 112 Path Sum | ✅ | No problem, and your comment explains *why* the check is at the leaf. §7 makes that reason concrete | §7 |

The common thread: **your reasoning was right, your confidence wasn't.** Confidence comes from having a quick way to check, so most of this lecture is about checks.

---

## 1. Fixed-window bounds, four ways

All four framings below describe the same facts. Use whichever one clicks, and use another one to double-check it.

**The names:**

| Name | Stands for |
|---|---|
| `n` | the number of boxes (`len(nums)` or `len(s)`) |
| `k` | the number of boxes in the window |
| `i` | the box that just **entered** the window (the newest box, its right end) |
| `start` | the window's **first** box (its left end) |

### Framing A: the ruler

Draw the boxes, with `n = 7` and `k = 3`, and the window whose last box is `i = 4`:

```
box index:    0    1    2    3    4    5    6
                        [ 2    3    4 ]
                          ↑          ↑
                        start        i
cuts:        0    1    2    3    4    5    6    7
                       ↑               ↑
                     cut 2           cut 5
```

- The window holds boxes `2, 3, 4`: that's `i - k + 1 = 2` through `i = 4`.
- As a slice it's `nums[2:5]`: from the cut before box 2 to the cut after box 4. The cut after box `i` is `i + 1`. So the slice is `nums[i - k + 1 : i + 1]`, and its length is `(i + 1) - (i - k + 1) = k` ✓.
- When box 4 entered, the box that left was box 1: one before `start`, which is `i - k`.

### Framing B: counting boxes placed

Walk `i` from 0 upward, adding one box each step. After adding box `i`, you've placed **`i + 1` boxes** (boxes `0 … i`; a closed range counts `last - first + 1 = i - 0 + 1`).

| After adding box `i` | Boxes placed | Window status |
|---|---|---|
| `i = 0` | 1 | building |
| … | … | building |
| `i = k - 1` | `k` | **just became full** (you called this "placing the final block") |
| `i = k` | `k + 1` | one too many, so one box must leave |

So:
- "Still building, including the final block" means `i + 1 <= k`, which is `i <= k - 1`, which is **`i < k`**. That's your 643 condition, and now you can see it in one line.
- "Just became full" means `i + 1 == k`, which is **`i == k - 1`**.
- "Full, and a box must leave" means `i + 1 > k`, which is **`i >= k`**.

### Framing C: the box exactly k behind

When box `i` enters a full window, the window must still hold exactly `k` boxes, so one leaves. The window after the step is `i - k + 1 … i`. The window before it was `i - k … i - 1`. The only box in "before" that isn't in "after" is **`i - k`**: the box exactly `k` steps behind the box entering.

**Check it with the smallest real case, `k = 1`:** the window is a single box. When box `i` enters, the box leaving should be the previous one, `i - 1`. The formula gives `i - k = i - 1` ✓. (In your 643 comment you tried "if i is 0, then I want 0 elements" to check this; that's checking a `k = 0` window, which can't happen. `k = 1` is the smallest window that exists, so test there.)

### Framing D: the window's first box (what you used in 187)

Instead of tracking the last box, track the first box, `start`. The window is `start … start + k - 1`, which is `s[start : start + k]`.

The window is only real if its last box exists: `start + k - 1 <= n - 1`. Move things around: `start <= n - k`. So:

- `start` runs `0, 1, …, n - k`, which is **`n - k + 1` windows**.
- In a `for` loop: `for start in range(n - k + 1)`.
- In a `while` loop: `while start + k - 1 < n`, which for `k = 10` is `while start + 9 < n`. That's exactly your 187 condition.

**The four framings side by side:**

| Fact | A: ruler | B: counting | C: k behind | D: first box |
|---|---|---|---|---|
| window = | `i - k + 1 … i` | the last `k` of the `i + 1` placed | — | `start … start + k - 1` |
| box leaving when `i` enters | one before `start` | the `(i + 1 - k)`-th box placed, index `i - k` | `i - k` | (the old `start`) |
| first full window | `i = k - 1` | `i + 1 == k` | — | `start = 0` |
| last window | `i = n - 1` | — | — | `start = n - k` |
| number of windows | `n - k + 1` | — | — | `n - k + 1` |

---

## 2. Knowing you're right: three checks that remove the doubt

You wrote, about `while i+9 < len(s)`: *"this just does not feel right. Because I know that I am doing the < and not <=."* Here are three ways to settle that kind of doubt for good.

### Check 1: compare the sets, not the symbols

`<` vs `<=` isn't right or wrong by itself. Each condition allows a **set** of values. Write the set out:

| Condition | Allowed `i` (with `n = 12`) | Same set? |
|---|---|---|
| `i + 9 < n` | `i + 9 <= 11`, so `i <= 2`: `{0, 1, 2}` | ✓ |
| `i + 9 <= n - 1` | `i <= 2`: `{0, 1, 2}` | ✓ |
| `i <= n - 10` | `i <= 2`: `{0, 1, 2}` | ✓ |
| `i < n - 9` | `i < 3`: `{0, 1, 2}` | ✓ |
| `i + 10 < n` (your first version) | `i <= 1`: `{0, 1}` | ✗ (misses `i = 2`) |
| `i + 10 <= n` | `i <= 2`: `{0, 1, 2}` | ✓ |

Four of the "different-looking" conditions are the **same condition**. The rule that decides it isn't "use `<`" or "use `<=`". It's: **the last box you touch, `i + 9`, must be a box that exists, so `i + 9 <= n - 1`.** Any condition with the same set is correct.

That's the "name → valid set → test positively" method (lecture 008) from the other direction: once you know the valid set, the symbol is just a way to write it down.

### Check 2: the two-point check (first and last iteration)

A loop's range is right if its **first** and **last** iterations are right. Plug in real numbers:

- **First:** with `i = 0`, is the window `s[0:10]`, the first 10 letters? ✓
- **Last:** take the smallest interesting length, `n = 11` (exactly two windows: boxes `0…9` and `1…10`). The last allowed `i` should be `1`. `i + 9 < 11` means `i < 2`, so `i = 1` is the last ✓. With your first version, `i + 10 < 11` means `i < 1`, so only `i = 0` runs ✗. The second window is missed.

**It took you a long time because you reasoned in general (with `len(s)`). The two-point check reasons with specific numbers, which is faster and leaves no doubt.**

### Check 3: a brute-force checker you can run yourself

When you're still unsure after the first two checks, let the computer check. Write the **slowest, most obviously correct** version of the answer, then compare it with yours on many random small inputs.

```python
import random

def brute_max_average(nums, k):                  # obviously correct: try every window
    return max(sum(nums[start:start + k]) for start in range(len(nums) - k + 1)) / k

def check(solution, trials=2000):
    for _ in range(trials):
        n = random.randint(1, 8)                  # small inputs: failures are easy to read
        nums = [random.randint(-5, 5) for _ in range(n)]
        k = random.randint(1, n)
        got, want = solution(nums, k), brute_max_average(nums, k)
        assert abs(got - want) < 1e-9, (nums, k, got, want)   # shows the failing input
    print("all", trials, "passed")
```

If the assertion fails, it prints the **exact small input** that broke your code. That input is the perfect thing to trace (lecture 003's "first wrong row," found for you). This is how every solution in these lectures is checked, and nothing stops you from doing it on every practice problem. In an interview you can't run it, but in practice it builds the confidence you're missing, because you'll see over and over that your derivations were right.

---

## 3. Two shapes for a fixed window

### Shape 1: one loop with a building phase (what you wrote)

Your 643 solution, condensed (the logic is unchanged):

```python
def findMaxAverage_one_loop(nums, k):
    total = 0                            # sum of the boxes currently in the window
    current_max = 0
    for i in range(len(nums)):           # i = the box entering
        if i < k:                        # still building (including the final block)
            total += nums[i]
            if i == k - 1:               # just became full: the first real window
                current_max = total / k
        else:                            # full: box i - k leaves, box i enters
            total -= nums[i - k]
            total += nums[i]
            current_max = max(current_max, total / k)
    return current_max
```

Trace `nums = [4, 1, 6, 2]`, `k = 2` (from running it):

| `i` | branch | `total` after | window | `current_max` after |
|---|---|---|---|---|
| 0 | building | 4 | `[4] 1 6 2` (not full) | 0 (unset) |
| 1 | building, just full | 5 | `[4 1] 6 2` | 2.5 |
| 2 | slide: 4 leaves, 6 enters | 7 | `4 [1 6] 2` | 3.5 |
| 3 | slide: 1 leaves, 2 enters | 8 | `4 1 [6 2]` | 4.0 |

Correct, and the "0 (unset)" row shows why setting `current_max` at `i == k - 1` mattered. If you'd compared against `0` instead, an array of all negative numbers would have returned 0.

### Shape 2: build the first window, then slide

The building phase only happens once, so do it once, **before** the loop. Then every loop step is the same "one leaves, one enters" step, with no `if`:

```python
def findMaxAverage(nums, k):
    total = sum(nums[:k])                # the first window: boxes 0 … k-1 (k boxes)
    best = total                         # the first window is a real window: a safe start
    for i in range(k, len(nums)):        # i = the box entering: k, k+1, …, n-1
        total += nums[i] - nums[i - k]   # box i - k leaves (Framing C)
        best = max(best, total)
    return best / k
```

Where each bound comes from, using §1:
- `nums[:k]` is the slice of boxes `0 … k-1`: that's `k` boxes (slice length `stop - start = k - 0`).
- The loop starts at `i = k` because box `k` is the first box that enters a **full** window (Framing B: `i >= k`).
- The loop ends at `i = n - 1`, the last box (that's what `range(k, n)` gives).
- Comparing sums and dividing once at the end avoids dividing every step (it's the same maximum, since all sums are divided by the same `k`).

| | Shape 1 | Shape 2 |
|---|---|---|
| Conditions to get right | `i < k`, `i == k - 1`, `i - k` | `[:k]`, `range(k, n)`, `i - k` |
| `if`s inside the loop | 2 | 0 |
| Initial value of the maximum | must be set at the first full window | the first window itself |

Both are correct. Shape 2 has fewer places to go wrong, and once you've written it a few times it's quicker. Both shapes checked out on 2,000 random inputs with the `check` function from §2.

---

## 4. Reader/writer, and the walk-through you planned (26)

You left this note on your 26 attempt: *"I should do a walk through of this code in the future and see that I can catch this error."* Here it is. Try it yourself first; the filled-in table is collapsed below.

**Problem (paraphrased).** Given `nums`, sorted in non-decreasing order, remove the duplicates **in place** so each distinct value appears once, keeping their order. Return `k`, the number of distinct values. The first `k` positions of `nums` must hold those values; what's after them doesn't matter.
Examples: `[1,1,2]` → `2`, with `nums` starting `[1,2,…]`; `[0,0,1,1,1,2,2,3,3,4]` → `5`, with `nums` starting `[0,1,2,3,4,…]`.
Constraints: `1 <= len(nums) <= 3·10^4`; sorted.

**Walk-through exercise:** trace your submitted code on `nums = [1, 1, 2]`, with one row per loop iteration and columns `reader`, `writer`, branch taken, `k` after, `nums` after. Then compare the final `k` with the expected answer.

<details><summary>Filled-in trace (from running your code)</summary>

| `reader` (start of step) | `writer` | branch | `k` after | `nums` after |
|---|---|---|---|---|
| 0 | 0 | first element | 0 | `[1, 1, 2]` |
| 1 | 1 | duplicate (`nums[1] == nums[0]`) | **1** | `[1, 1, 2]` |
| 2 | 1 | write `nums[1] = 2` | 1 | `[1, 2, 2]` |

End: `reader = 3`, `writer = 2`, `k = 1`. Expected 2. The array is right (`[1, 2, …]`), and **`writer` is 2**: the correct answer was in `writer` the whole time. `k` went up once, in the duplicate branch: it counted duplicates.

Why example 2 still passed: `[0,0,1,1,1,2,2,3,3,4]` has 5 duplicates **and** 5 distinct values, so counting the wrong thing gave the right number by coincidence. That's a reason to always run example 1 too, not just the biggest one.
</details>

### Three framings of why `writer` is the answer

1. **As a cut:** `writer` is the cut just after the kept part. The kept part is the slice `nums[:writer]`, and a slice's length is `stop - start = writer - 0 = writer`.
2. **As a counter:** `writer` goes up by exactly 1 each time a distinct value is written, and never otherwise. That's precisely "the number of distinct values found so far."
3. **As an invariant:** *after each step, `nums[:writer]` holds the distinct values of `nums[:reader]`, in order.* At the end, `reader = n`, so `nums[:writer]` holds the distinct values of the whole array, and there are `writer` of them.

### Starting values from the invariant (your "I should have just had reader and writer start at 1")

You were right. Use the invariant to find the start. Box 0 is always distinct (nothing comes before it), so after looking at one box, `nums[:1]` holds the distinct values of `nums[:1]`: the invariant holds with **`reader = 1`, `writer = 1`**. Starting there removes the `reader == 0` branch:

```python
def removeDuplicates(nums):
    writer = 1                           # nums[:writer] = the distinct values seen so far (box 0 always counts)
    for reader in range(1, len(nums)):   # reader = the box being looked at
        if nums[reader] != nums[writer - 1]:     # differs from the last kept value: it's new
            nums[writer] = nums[reader]
            writer += 1
    return writer                        # the cut after the kept part = how many were kept
```

(Comparing with `nums[writer - 1]`, the last **kept** value, works as well as comparing with `nums[reader - 1]`, because the array is sorted. Checked on 3,000 random sorted arrays.)

### The habit that would have caught it: names against lines

For every variable you named, list the lines that change it, and check each one against the name:

| Name | Your meaning | Lines that change it | Matches? |
|---|---|---|---|
| `writer` | the next box to write to | `writer += 1` after a write | ✓ |
| `k` | "how many unique elements" (your comment) | `k += 1` in the **duplicate** branch | ✗ |

That table takes a minute, and it's the second check in the practice queue's "before you submit" list.

### Recognizing reader/writer without a label

You noticed: *"from immediate reading of the problem, I don't think I would have guessed that this is a sliding window problem."* (It isn't one, you realized: it's reader/writer.) The signals in the statement:

| Statement says | Points to |
|---|---|
| "in place," "do not allocate extra space" | you'll overwrite the array you're reading |
| "keep the relative order" | one pass, left to right |
| "return the number kept; what's after doesn't matter" | the answer is a cut (`writer`), and the tail is junk |
| a filter rule (no duplicates, no zeros, no `val`) | `if keep(reader): write it` |

When three or more of those appear together, think reader/writer.

---

## 5. Tracing a window problem without the trace exploding (187)

You started a row-by-row trace on the full example and stopped: *"this is going to take a long long time,"* and `seen` grew too large to write. That was a good observation. The fix is to **shrink the problem, not to trace faster.**

**Step 1: replace the constant with a name.** Write the code with `K` instead of `10`:

```python
def findRepeated(s, K=10):
    seen, added, result = set(), set(), []
    start = 0
    while start + K - 1 < len(s):        # the window's last box, start + K - 1, must exist
        window = s[start:start + K]
        if window in seen and window not in added:
            added.add(window)
            result.append(window)
        seen.add(window)
        start += 1
    return result
```

With `K = 10`, the condition `start + K - 1 < len(s)` is your `start + 9 < len(s)`.

**Step 2: trace with `K = 2` and a 4-letter string.** `s = "ABAB"` has three windows (`n - K + 1 = 3`), and the last one is a repeat, so it's exactly the case your first version got wrong. Draw the window as brackets:

| `start` | window drawn | already in `seen`? | `seen` after |
|---|---|---|---|
| 0 | `[AB]AB` | no | `{AB}` |
| 1 | `A[BA]B` | no | `{AB, BA}` |
| 2 | `AB[AB]` | **yes** → add to result | `{AB, BA}` |

Result `["AB"]` ✓. Now trace your first condition, `start + K < len(s)` (that's `start + 10 < len(s)` with `K = 2`): `start + 2 < 4` means `start < 2`, so only rows 0 and 1 run, and the result is `[]` ✗. **Three rows found the bug** that the full example would have needed 20+ rows to find.

**A Python fact that makes this bug silent:** slicing never raises an error, even past the end. `"ABAB"[3:5]` is `"B"` and `"ABAB"[4:6]` is `""`. So a loop that runs too far doesn't crash: it quietly makes short windows. A loop that stops too early (your first version) also doesn't crash: it quietly misses windows. Either way, only a check (§2) or a small trace finds it.

**General recipe for tracing any window problem:**
1. Replace constants with names, and shrink them (`K = 2` or `3`).
2. Make the input as short as possible while still including the case you're worried about (here: a repeat in the **last** window).
3. Draw the window with brackets on the string.
4. Write only the columns that change, and write sets as their contents (they stay small on tiny inputs).

---

## 6. When no idea comes: brute force first (187)

Your first comments on 187: *"I actually don't quite know what the brute force approach would be here,"* and then *"I need to think about what even makes this problem hard."* That second sentence is a good instinct. Here's a reliable way to answer it.

**Step 1: say the brute force as one sentence about candidates.** "The answer is a set of 10-letter strings. **Every** candidate is some window of `s`. So: look at every window, and keep the ones that appear more than once."

**Step 2: write what each step costs.** "For each window, compare it with every other window": about `n` windows, times `n` comparisons, times 10 letters each. That's O(10·n²), too slow when `n = 10^5`.

**Step 3: find the repeated question.** The inner loop asks, over and over, "**have I seen this window before?**" That's exactly the question a set answers in O(1) (lecture 005: "double loop → lookup"). So `seen` replaces the inner loop, and the cost drops to O(10·n).

That's the whole solution, and it came out of the brute-force sentence. You did reach it, with ChatGPT's hint (and you took only the idea, then wrote all the code yourself, which is the right way to use a hint). Next time, write the three steps above *before* asking: they'll often get you there alone.

**About your first idea** (count the letters in each window): you rejected it yourself because it loses the order of the letters ("AC" and "CA" have the same counts). That's exactly the right test for a representation: *does it keep everything that makes two answers different?* Counts don't keep order; the string itself does.

---

## 7. Why Path Sum checks at the leaf, not at `None` (112)

Your solution was correct, and your comment gave the reason: *"I can not calculate the sum at the invalid [None] because that will not tell me if the parent is a leaf."* Here's that reason as a concrete counterexample, so it's something you can show, not just say.

**Problem (paraphrased).** Given the root of a binary tree and an integer `targetSum`, return `True` if some **root-to-leaf** path (a leaf is a node with no children) has values adding up to `targetSum`.

The tempting wrong version checks the sum when it reaches `None`:

```python
def hasPathSum_wrong(root, targetSum):
    def go(node, sum_above):
        if not node:
            return sum_above == targetSum    # WRONG: a None child doesn't mean its parent is a leaf
        return go(node.left, sum_above + node.val) or go(node.right, sum_above + node.val)
    return go(root, 0)
```

**Counterexample:** root `1` with only a left child `2`, and `targetSum = 1`.

```
    1
   /
  2
```

The only root-to-leaf path is `1 → 2`, with sum 3. So the answer is `False`. But the wrong version also visits the root's **missing right child**, where the sum so far is 1, and returns `True` (from running it). Node 1 isn't a leaf, but its `None` child made it look like one.

Your version checks `if not node.left and not node.right` **at the node itself**, which is the definition of a leaf. That's why it's right. The contract, in lecture 002/007 terms: the sum so far goes **down** as a parameter, and "found a path?" comes **up** through the `or`.

---

## 8. Drills

Do these on paper, without running anything, in 15–20 minutes. Answers are collapsed.

1. `n = 9`, `k = 4`. Which box leaves when box 6 enters? What's the slice of the window ending at box 6?
2. How many windows of length 4 are there in 9 boxes? What are the first and last `start` values?
3. Which of these allow exactly the starts of every length-3 window in `n = 7` boxes? (a) `start < n - 3` (b) `start <= n - 3` (c) `start + 2 < n` (d) `start + 3 <= n` (e) `start + 3 < n`
4. Write the "build, then slide" loop header for windows of length `k` where `i` is the box entering. What's the first `i`?
5. Do the two-point check for `for start in range(n - k + 1)` with `n = 5`, `k = 5`.
6. A reader/writer loop ends with `writer = 4`. How many items were kept, and what slice holds them?
7. Name→lines check: `count` is "the number of zeros seen." Lines: `count += 1` inside `if nums[r] == 0`, and `count -= 1` inside `if nums[l] == 0` when `l` leaves the window. Do both match?
8. Shrink-the-constant: 187 asks for length 10. Make a 5-letter string whose only repeat (with `K = 2`) is in the last window.

<details><summary>Answers</summary>

1. Box `6 - 4 = 2` leaves. The window is boxes `3 … 6`: `nums[3:7]`.
2. `9 - 4 + 1 = 6` windows; `start` runs `0 … 5`.
3. (b), (c) and (d): each allows `start` in `{0,1,2,3,4}` (the last window is boxes `4…6`). (a) and (e) allow only `{0,1,2,3}`, missing the last window.
4. `for i in range(k, len(nums)):`, first `i = k`.
5. `range(5 - 5 + 1) = range(1)` gives `start = 0` only: the single window `nums[0:5]` (boxes 0…4) ✓. Both first and last are 0.
6. 4 items, in `nums[:4]` (boxes 0…3).
7. Yes: each line changes `count` exactly when a zero enters or leaves the window, which keeps "zeros in the window" correct. (Notice the name should really be "zeros **in the window**," not "seen," since it also goes down. Fixing the name is part of the check.)
8. For example `"ABCAB"`: windows `AB, BC, CA, AB`. The only repeat, `AB`, is the last window (`start = 3 = n - K`).
</details>

---

## Self-check questions

1. Write the window of `k` boxes ending at box `i`, as a closed range and as a slice.
<details><summary>Answer</summary>

Boxes `i - k + 1 … i`; slice `nums[i - k + 1 : i + 1]`.
</details>

2. Explain `if i < k:` in 643 using "boxes placed."
<details><summary>Answer</summary>

After adding box `i`, `i + 1` boxes have been placed. The building phase (including the final block) is while `i + 1 <= k`, which is `i < k`.
</details>

3. How do you decide between two conditions that use `<` and `<=`?
<details><summary>Answer</summary>

Write the set of values each allows. If the sets are the same, the conditions are the same. The set itself comes from naming what must be true (e.g. "the last box I touch must exist").
</details>

4. What's the two-point check, and why is it faster than reasoning in general?
<details><summary>Answer</summary>

Plug real numbers into the first and last iterations and check that each is right. It uses specific values (n = 11, i = 1) instead of symbols, so there's nothing to hold in your head.
</details>

5. What are the three parts of a brute-force checker?
<details><summary>Answer</summary>

An obviously correct slow solution; a loop generating many small random inputs; an assertion comparing the two that prints the failing input.
</details>

6. Why is `writer` the answer to Remove Duplicates? Give two framings.
<details><summary>Answer</summary>

As a cut: the kept part is `nums[:writer]`, whose length is `writer`. As a counter: it goes up by one exactly when a distinct value is written.
</details>

7. Why can slicing bugs in Python be silent?
<details><summary>Answer</summary>

Slicing never raises an error: past the end it returns a shorter (or empty) result. So a loop that runs too far makes short windows, and one that stops early just misses windows, with no crash either way.
</details>

8. In Path Sum, give a tree that breaks the "check at `None`" version.
<details><summary>Answer</summary>

Root 1 with only a left child 2, target 1. The missing right child of the root sees a sum of 1 and returns True, but the only root-to-leaf path sums to 3.
</details>

9. In 187, what's the brute-force sentence, and what repeated question turns it into the real solution?
<details><summary>Answer</summary>

"Look at every window and keep those that appear more than once." The repeated question is "have I seen this window before?", answered in O(1) by a set.
</details>
