# Attempt Review 002 (2026-10-31): One Model for Window Bounds (Birthday Chocolate, Revisited)

> **For:** Timothy · **Date:** 2026-10-31
> **Source:** your Oct 31 write-up while re-solving Birthday Chocolate from memory (spaced revisit of lectures 006 and 008), plus your two July attempts in `001_practice_medium.py`.
> **What's different about this review:** review 001 gave you **four** framings of the same window facts. Today's write-up shows that having several framings in your head at once is part of the problem: you were holding a box-based loop variable and a cut-based count formula at the same time, and they disagree by exactly 1. So this review gives you **one** model to use every time, and treats everything else as a translation of it.
> **Format notes:** numbers before symbols in every section; every formula derived; all code run against a brute-force reference on 5,000 random inputs.

---

## Core ideas (the answer key)

1. **Your revisit worked as designed.** Spaced retrieval is supposed to show what didn't stick. It found it: the box/cut conversion inside a moving window. That's a specific, fixable gap, not a sign that nothing stuck.
2. **The confusion comes from mixing two models in one loop.** Your loop variable `i` was a **box** (included), and your count formula `stop - start` is about **cuts**. Each is right; used together without a conversion, they're off by one. (It's the same root cause as your first Spiral Matrix, lecture 001 §0.3.)
3. **The one model: make your loop variable a cut, and write the window as a slice.** For a window of `m` boxes, loop over its left cut `start`; the window is `s[start : start + m]`. Then every other number comes from slices.
4. **The only conversion you need:** the slice `s[a:b]` holds boxes `a, a+1, …, b-1`. Its first box is `a`, its last box is `b - 1`. That `- 1` is the only "1" in the whole topic.
5. **"The box that leaves" and "the first box that stays" are two different boxes**, next to each other. In your write-up, `i - 1` and `i - m + 1` were both trying to be "the box to kick out," which is why the `+1` felt mysterious.
6. **One example can't pin down a formula.** With `m = 1`, the formulas `i - 1` and `i - m` give the same number, so the example can't tell you which one is right. Always test with **two** values of `m` (like 1 and 3).
7. **Correct first, fast second.** Birthday Chocolate has `n ≤ 100`, so summing every slice (`sum(s[start:start+m])`) is fast enough and has no ±1 decisions beyond the range. The sliding version is an optimization you add after.
8. **When you're stuck for 20 minutes on a ±1, stop reasoning in symbols.** Write a table with real numbers (a 6-box array, `m = 3`), read the pattern off the table, then check it with a second `m`.

---

## Table of Contents

- [0. What happened in your write-up](#0-what-happened-in-your-write-up)
- [1. The problem](#1-the-problem)
- [2. The one model: the loop variable is a cut](#2-the-one-model-the-loop-variable-is-a-cut)
- [3. Solve it with no sliding at all](#3-solve-it-with-no-sliding-at-all)
- [4. Add the slide, still in the one model](#4-add-the-slide-still-in-the-one-model)
- [5. If you prefer `i` = the box entering: a translation, not a new model](#5-if-you-prefer-i--the-box-entering-a-translation-not-a-new-model)
- [6. How to get a formula from numbers (and why one example wasn't enough)](#6-how-to-get-a-formula-from-numbers-and-why-one-example-wasnt-enough)
- [7. Your July attempts, read with the one model](#7-your-july-attempts-read-with-the-one-model)
- [8. A stuck protocol](#8-a-stuck-protocol)
- [9. Drills (numbers first)](#9-drills-numbers-first)
- [Self-check questions](#self-check-questions)

---

## 0. What happened in your write-up

Here's what your write-up shows, piece by piece.

| What you wrote | What's right | What tripped you up |
|---|---|---|
| "a range has n elements and n is the number of steps from the start to the stop … if start and stop are the same, we've taken no steps" | ✓ exactly the slice model (lecture 008). | You wrote the count as `start - stop`; it's **`stop - start`** (stop is the bigger cut). A small slip, but it's one more thing to doubt. |
| "my index, which is the leading number … represents the stop, is actually going to be **included**" | ✓ you noticed the real problem: your `i` is a box, not a cut. | Then you tried to bend the slice model to fit a box. Instead, **convert once**: the cut just after box `i` is `i + 1`. That's all. |
| "if I only have one element … the element I want to kick out is `i - 1`, so it should be `i - m + 1`" | ✓ testing with the smallest case is the right instinct. | `i - m + 1` with `m = 1` is `i`, not `i - 1`. These are two **different** boxes: `i - m + 1` is the **first box that stays**, and `i - m` is the **box that leaves**. And `m = 1` can't tell `i - 1` from `i - m` (§6). |
| "I have spent almost an hour and a half" | | A sign the stuck protocol (§8) should have kicked in at about 20 minutes. |

None of this means the lectures didn't land. You remembered the slice model, the count rule, the boxes framing, and the smallest-case test. What you didn't have was **one consistent way to put them together** under pressure. That's what this review is for.

---

## 1. The problem

**Birthday Chocolate (HackerRank "Subarray Division"), paraphrased.** A chocolate bar is a row of squares with integers on them: `s[0], s[1], …, s[n-1]`. Lily wants to give Ron a **contiguous** piece of exactly `m` squares (his birth month) whose numbers add up to `d` (his birth day). Return how many such pieces there are.
Examples: `s = [2,2,1,3,2], d = 4, m = 2` → `2` (the pieces `[2,2]` and `[1,3]`); `s = [1,2,1,3,2], d = 3, m = 2` → `2` (`[1,2]` and `[2,1]`); `s = [1,1,1,1,1,1], d = 3, m = 2` → `0`; `s = [4], d = 4, m = 1` → `1`.
Constraints: `1 <= n <= 100`; `1 <= s[i] <= 5`; `1 <= d <= 31`; `1 <= m <= 12`. (Note `m` can be bigger than `n`: then there are no pieces.)

---

## 2. The one model: the loop variable is a cut

### 2.1 Start with numbers

Take `s = [2, 2, 1, 3, 2]` (`n = 5`) and `m = 2`. Draw boxes and cuts:

```
cuts:    0     1     2     3     4     5
         |  2  |  2  |  1  |  3  |  2  |
boxes:      0     1     2     3     4
```

Every piece of 2 squares is a slice between two cuts that are 2 apart:

| left cut `start` | slice | boxes inside | sum |
|---|---|---|---|
| 0 | `s[0:2]` | 0, 1 | 4 ✓ |
| 1 | `s[1:3]` | 1, 2 | 3 |
| 2 | `s[2:4]` | 2, 3 | 4 ✓ |
| 3 | `s[3:5]` | 3, 4 | 5 |

Answer: 2 ✓. Notice what never appeared: no `+1`, no `-1`, no "is it included?" Every row is just `s[start : start + 2]`.

### 2.2 The model in symbols

> **Loop over `start`, the window's left cut. The window is `s[start : start + m]`.**

Everything else comes from two facts you already trust:

| Fact | Where it comes from |
|---|---|
| the slice `s[a:b]` holds `b - a` boxes | the count rule (stop − start) |
| the slice `s[a:b]` holds boxes `a … b-1` | its first box is the one right after cut `a`; its last box is the one right before cut `b` |

From them:

| Question | Answer | Check with `m = 2`, `start = 1` |
|---|---|---|
| How many boxes in the window? | `(start + m) - start = m` | `s[1:3]` has 2 ✓ |
| The window's first box | `start` | box 1 ✓ |
| The window's last box | `start + m - 1` | box 2 ✓ |
| Which `start` values give a real window? | the right cut `start + m` can be at most `n` (the last cut), so `start <= n - m` | with `n = 5`: `start` up to 3 ✓ (the table above) |
| The loop | `for start in range(n - m + 1)` | `range(4)`: 0, 1, 2, 3 ✓ |

The `- 1` in "last box is `start + m - 1`" is the only one, and it's the box/cut conversion from the second fact. You never have to wonder where it came from.

---

## 3. Solve it with no sliding at all

With `n <= 100` and `m <= 12`, adding up each slice costs at most `100 × 12 = 1,200` additions. That's nothing. So the first correct solution is just the table from §2.1, written as code:

```python
def birthday(s, d, m):
    ways = 0
    for start in range(len(s) - m + 1):          # every left cut that leaves room for m boxes
        if sum(s[start:start + m]) == d:         # the piece is exactly the slice
            ways += 1
    return ways
```

- If `m > n`, then `range(len(s) - m + 1)` is a range with a negative or zero stop: it runs **zero** times, and the answer is 0 ✓. No special case needed.
- It matched the brute force on all 5,000 random inputs, including `m > n`.

**In an interview,** say: "With these constraints, summing each window is O(n·m), about a thousand operations, so I'll write that first. If `m` could be large, I'd slide the window to make it O(n)." That's a strong answer, not a weak one, because it's correct and you've stated when it stops being enough.

---

## 4. Add the slide, still in the one model

Sliding means: don't re-add the whole window; update the previous sum.

**Numbers first** (`s = [2,2,1,3,2]`, `m = 2`, from running it):

| `start` | window | which box left | which box entered | sum |
|---|---|---|---|---|
| 0 | `s[0:2]` = `[2, 2]` | (first window: built with `sum`) | | 4 |
| 1 | `s[1:3]` = `[2, 1]` | box 0 | box 2 | 4 − 2 + 1 = 3 |
| 2 | `s[2:4]` = `[1, 3]` | box 1 | box 3 | 3 − 2 + 3 = 4 |
| 3 | `s[3:5]` = `[3, 2]` | box 2 | box 4 | 4 − 1 + 2 = 5 |

Read the pattern off the table: when the left cut is `start`, the box that left is `start - 1`, and the box that entered is `start + 1`… but that's only with `m = 2`. Derive it from the slices instead, so it works for every `m`:

1. The old window is `s[start - 1 : start - 1 + m]`. Its boxes are `start - 1 … start + m - 2`.
2. The new window is `s[start : start + m]`. Its boxes are `start … start + m - 1`.
3. **Left:** in the old one, not in the new one: box **`start - 1`** (the old window's first box).
4. **Entered:** in the new one, not in the old one: box **`start + m - 1`** (the new window's last box).

Check with the table (`m = 2`, `start = 2`): left box 1 ✓, entered box `2 + 2 - 1 = 3` ✓.

```python
def birthday_sliding(s, d, m):
    n = len(s)
    if m > n:                                    # no window fits
        return 0
    window_sum = sum(s[0:m])                     # the first window, s[0:m]
    ways = 1 if window_sum == d else 0
    for start in range(1, n - m + 1):            # the remaining left cuts
        window_sum -= s[start - 1]               # the old window's first box leaves
        window_sum += s[start + m - 1]           # the new window's last box enters
        if window_sum == d:
            ways += 1
    return ways
```

Both box numbers come straight from "slice `[a:b]` holds boxes `a … b-1`." Nothing to memorize.

---

## 5. If you prefer `i` = the box entering: a translation, not a new model

Your write-up (and your 643 solution) used `i` = **the box that just entered**, the window's last box. That's fine. It isn't a second model to learn. It's the same model with one substitution:

| In the one model | Box entering is… | So |
|---|---|---|
| left cut `start` | `start + m - 1` | `i = start + m - 1` |
| | | `start = i - m + 1` |

Now translate every fact by replacing `start` with `i - m + 1`:

| Fact | One model (by `start`) | Same fact, by `i` (box entering) |
|---|---|---|
| the window | `s[start : start + m]` | `s[i - m + 1 : i + 1]` |
| first box that stays | `start` | **`i - m + 1`** |
| box that left | `start - 1` | **`i - m`** |
| last box (entering) | `start + m - 1` | `i` |
| first full window | `start = 0` | `i = m - 1` |
| window is full when | always (start ≥ 0) | `i >= m - 1` |

So here's where your `+1` comes from: **`i - m + 1` is the first box that stays, and `i - m` is the box that left. They're neighbours.** Both come from `start = i - m + 1`, which comes from "the last box of `s[start:start+m]` is `start + m - 1`."

If you use this version, write the translation line as a comment at the top of the loop so you never have to re-derive it:

```python
def birthday_by_entering_box(s, d, m):
    window_sum = 0
    ways = 0
    for i in range(len(s)):                      # i = the box entering; window = s[i-m+1 : i+1]
        window_sum += s[i]
        if i >= m:                               # the window had m boxes already: box i-m leaves
            window_sum -= s[i - m]
        if i >= m - 1 and window_sum == d:       # full window (first one ends at box m-1)
            ways += 1
    return ways
```

**My recommendation:** use the `start` version until it's automatic. It only ever asks "what slice is this?", and that's the question you're most sure of.

---

## 6. How to get a formula from numbers (and why one example wasn't enough)

You tried `m = 1`: the window is just box `i`, so the box that leaves is `i - 1`. That's correct. But then you needed a formula with `m` in it, and **several formulas give `i - 1` when `m = 1`**:

| candidate | value when `m = 1` | value when `m = 3`, `i = 5` | correct? (`m = 3`, `i = 5`: window is boxes 3, 4, 5, so box 2 left) |
|---|---|---|---|
| `i - 1` | `i - 1` | 4 | ✗ |
| `i - m` | `i - 1` | 2 | ✓ |
| `i - m + 1` | `i` | 3 | ✗ (that's the first box that **stays**) |
| `i - 2*m + 1` | `i - 1` | 0 | ✗ |

With only `m = 1`, the first, second and fourth rows look identical. **One example can't choose between them. A second, bigger example can.** That's the two-point check (attempt review 001 §2) used to *find* a formula, not just to check one.

**The procedure:**
1. Pick a concrete array with at least 6 boxes and write the indices under it.
2. Pick `m = 3` (big enough that `m`, `m - 1` and `m + 1` are all different).
3. Draw two windows next to each other with brackets and write which box left and which entered.
4. Write the candidate formula and plug in the numbers.
5. Check it with `m = 1` as well.

```
boxes:   0  1  2  3  4  5
m = 3:  [0  1  2] 3  4  5      window ending at box 2
         0 [1  2  3] 4  5      window ending at box 3: box 0 left, box 3 entered
```

Box entering `i = 3`, box leaving `0 = 3 - 3 = i - m` ✓. With `m = 1`: `i - 1` ✓.

---

## 7. Your July attempts, read with the one model

Your two July attempts (in `001_practice_medium.py`) had the same gap in a different form.

**Attempt 1:** `windowSum -+ s[i-(m-1)]`. Two separate issues:
- `-+` is a typo for `-=` (as written, it computes a value and throws it away, so nothing leaves the window).
- `i - (m - 1)` is `i - m + 1`: the first box that **stays**, not the box that leaves. Same mix-up as today.

**Attempt 2:** `windowSum -= s[i-(d)]`. The loop variable `i` is the box entering (it starts at `m`), so the box leaving is `i - m`. The code uses `d` (the birth **day**) instead of `m` (the **month**). Your comment reasoned about steps with "`d`" while meaning the window length. On random inputs where a window fits (`m <= n`), this version was wrong (or crashed) more than half the time; replacing `d` with `m` makes it correct. In the one model this can't happen in the same way, because the only quantity in every index is `m`, written next to `start`.

Your comment in attempt 2 also asked: *"why is it that I actually need to build the first one outside of the loop?"* Answer from §4: the slide needs a previous window to update. The first window has no previous one, so it's built directly with `sum(s[0:m])`. (The `by_entering_box` version in §5 avoids building it separately by letting the window grow until it's full.)

---

## 8. A stuck protocol

An hour and a half on one ±1 isn't a lack of ability. It's a missing **exit**: a point where you switch tactics. Use these, with a timer:

| After | Do this |
|---|---|
| 10 min on one index | Stop reasoning in symbols. Write the numbers table (§6 procedure): 6 boxes, `m = 3`, brackets. |
| 20 min | Write the version with **no** index arithmetic (§3: `sum(s[start:start+m])`). Make that pass. |
| 30 min | Use the working version as a checker (attempt review 001 §2, check 3) and test your sliding version against it on small random inputs. |
| 45 min | Stop. Write down the exact question you're stuck on in one sentence, and bring it here. The question itself is the useful output. |

---

## 9. Drills (numbers first)

Do these on paper. Use the one model (`start` = left cut) unless the drill says otherwise.

1. `s = [5, 1, 4, 2, 3, 6]`, `m = 3`. List every window as a slice and its boxes.
2. Same array and `m`. For `start = 2`, which box left (compared with `start = 1`) and which entered?
3. `n = 8`, `m = 8`. How many windows? What's the `range` for `start`?
4. `n = 3`, `m = 5`. How many windows? What does `range(n - m + 1)` produce?
5. Translate: if `i` is the box entering and `m = 4`, write the window as a slice, the first box that stays, and the box that left, for `i = 6`.
6. Fill in the table for `m = 4`, `i = 9`: candidates `i - m`, `i - m + 1`, `i - m - 1`. Which one is the box that left? Draw it.
7. Without looking: write `birthday` in the §3 version, then in the §4 version.

<details><summary>Answers</summary>

1. `s[0:3]` boxes 0–2 `[5,1,4]`; `s[1:4]` boxes 1–3 `[1,4,2]`; `s[2:5]` boxes 2–4 `[4,2,3]`; `s[3:6]` boxes 3–5 `[2,3,6]`. Four windows (`6 - 3 + 1`).
2. Box `start - 1 = 1` left (value 1); box `start + m - 1 = 4` entered (value 3).
3. One window (`8 - 8 + 1`); `range(1)`, so `start = 0` only: `s[0:8]`.
4. Zero windows; `range(-1)` produces nothing, so the loop doesn't run.
5. Window `s[3:7]` (boxes 3–6); first box that stays `6 - 4 + 1 = 3`; box that left `6 - 4 = 2`.
6. `i - m = 5` left. The window is boxes 6–9 (`i - m + 1 = 6` stays). `i - m - 1 = 4` left one step earlier.
7. Compare with §3 and §4.
</details>

---

## Self-check questions

1. What's the one model, in one sentence?
<details><summary>Answer</summary>

Loop over the window's left cut `start`; the window is the slice `s[start : start + m]`, and every other number comes from slices.
</details>

2. What does `s[a:b]` hold, and where does the only `- 1` come from?
<details><summary>Answer</summary>

Boxes `a … b-1`, that's `b - a` of them. The last box is `b - 1` because cut `b` comes right after it.
</details>

3. Why does `start` run up to `n - m`?
<details><summary>Answer</summary>

The window's right cut, `start + m`, can be at most `n` (the last cut). So `start <= n - m`, which is `range(n - m + 1)`.
</details>

4. When the window moves from left cut `start - 1` to `start`, which box leaves and which enters?
<details><summary>Answer</summary>

Box `start - 1` (the old first box) leaves; box `start + m - 1` (the new last box) enters.
</details>

5. With `i` = the box entering, what are `i - m` and `i - m + 1`?
<details><summary>Answer</summary>

`i - m` is the box that left; `i - m + 1` is the first box that stays. They're neighbours. Both come from `start = i - m + 1`.
</details>

6. Why couldn't the `m = 1` example decide the formula?
<details><summary>Answer</summary>

Several different formulas (`i - 1`, `i - m`, `i - 2m + 1`) all give `i - 1` when `m = 1`. A second example with a bigger `m` tells them apart.
</details>

7. What should you do after 20 minutes stuck on an index?
<details><summary>Answer</summary>

Write the version with no index arithmetic (sum each slice), make it pass, and use it to check the faster version.
</details>
