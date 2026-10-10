# Lecture 008: Indices and Bounds: A Toolkit of Ways to Get Them Right

> **For:** Timothy · **Date:** 2026-10-10
> **Why this lecture:** you asked for a lecture dedicated to the block you have with arrays, bounds and indexing, with many different techniques so that several ways of seeing the same thing can reinforce each other. That request fits the evidence. In two and a half months, almost every bug in your tracker has been an index or bound decision, not an algorithm decision:
>
> | When | Problem | The index decision that went wrong |
> |---|---|---|
> | Jul | 3Sum | `p2 = 1` instead of `i + 1` |
> | Jul | Birthday Chocolate | element added twice at the window boundary; `d` used for `m` |
> | Jul | Rotate List | the pointer stopped one node late (`while fast` vs `while fast.next`) |
> | Oct 2–5 | Spiral Matrix ×4 | mixed closed/half-open walls; backward `range` built forward |
> | Oct 3 | Spiral trace | read `range(2, 2)` as containing 2 |
> | Oct 4 | Climbing Stairs | `if not i+2<n` instead of `if i + 2 <= n` |
> | Sep 12 | Decode Ways | didn't see why the base case is `i == len(s)` |
> | Oct 9 | Fixed windows | long struggle deciding between `r - m` and `r - m + 1`, and `>` vs `>=` |
> | Oct 10 | Merge-sort counting | ~20 min choosing between `len - i`, `len - 1 - i` and `len - (i - 1)` |
>
> **How to use this lecture:** you don't need every technique. Read it once, try the drills (§13), and keep the ones that feel natural. The reference card (§14) is meant to be printed. The goal is that for any index question, you have **at least two independent ways** to get the answer, so one can check the other.
> **Format notes:** no firmware analogies; everything is derived. Every number in the examples and drill answers was checked by running Python.

---

## Core ideas (the answer key)

1. **There are two different things an index can mean:** a **box** (the element at that position) or a **cut** (the boundary between two elements). Most confusion comes from switching between them without noticing.
2. **Slices and `range` use cuts.** `a[start:stop]` is everything between cut `start` and cut `stop`, so its size is **`stop - start`**.
3. **Count rule for a closed range** `[first, last]` (both boxes included): **`last - first + 1`**. It's the slice rule in disguise: `[first, last]` = `a[first:last+1]`.
4. **Distance is not count.** The distance (number of steps) from index `i` to `j` is `j - i`. The number of elements from `i` to `j` inclusive is `j - i + 1`. Posts vs fence sections.
5. **Name it → valid set → test positively** (the method that clicked for you on Oct 5) works for every index expression: name the index you're about to use, write which values are legal, test membership with no `not`.
6. **A linear formula is fixed by two points.** If an index formula is right at both extremes (`i = 0` and `i = n - 1`), it's right in between. Two plug-ins replace a lot of reasoning.
7. **Count possibilities by counting their valid starts.** "How many windows of length k?" = how many legal start positions = `n - k + 1`.
8. **Pick one convention per variable and put it in the name** (`end_excl`, `last`) or a comment. Never decide a convention halfway through a loop.
9. **Write it down instead of holding it in your head:** a ruler of indices above the array, brackets for ranges, and a 3-element example in a comment.
10. **Practice with immediate feedback:** predict, then check in a Python REPL. Calibration comes from finding out you were wrong quickly and often.

---

## Table of Contents

- [1. Two pictures: boxes and cuts](#1-two-pictures-boxes-and-cuts)
- [2. Counting: the slice rule and the closed rule](#2-counting-the-slice-rule-and-the-closed-rule)
- [3. Distance vs count (posts and fence sections)](#3-distance-vs-count-posts-and-fence-sections)
- [4. The start / last / length triangle](#4-the-start--last--length-triangle)
- [5. Name → valid set → test (for any index expression)](#5-name--valid-set--test-for-any-index-expression)
- [6. Two-point checking: why plugging in both ends is enough](#6-two-point-checking-why-plugging-in-both-ends-is-enough)
- [7. Counting possibilities by counting starts](#7-counting-possibilities-by-counting-starts)
- [8. Python's conventions, all in one place](#8-pythons-conventions-all-in-one-place)
- [9. Loops: what the loop variable means](#9-loops-what-the-loop-variable-means)
- [10. Writing it down: rulers, brackets and comment templates](#10-writing-it-down-rulers-brackets-and-comment-templates)
- [11. Special cases you meet often](#11-special-cases-you-meet-often)
- [12. When you're stuck: a decision procedure](#12-when-youre-stuck-a-decision-procedure)
- [13. Drills](#13-drills)
- [14. Reference card](#14-reference-card)
- [Sources](#sources)

---

## 1. Two pictures: boxes and cuts

Take `a = [10, 20, 30, 40, 50]` (length `n = 5`). There are two different ways to number it.

**Picture 1: boxes.** An index labels an element. Indices `0 … n-1`.

```
index:     0    1    2    3    4
         [10] [20] [30] [40] [50]
```

**Picture 2: cuts.** An index labels a boundary *between* elements. Cuts `0 … n` (one more than the boxes).

```
cut:     0    1    2    3    4    5
         | 10 | 20 | 30 | 40 | 50 |
```

Cut `i` sits **just before** box `i`. Cut `0` is before everything; cut `n` is after everything.

**Which picture each tool uses:**

| Tool | Uses | Example |
|---|---|---|
| `a[i]` | a **box** | `a[2]` = 30 |
| `a[start:stop]` | two **cuts** | `a[1:3]` = everything between cut 1 and cut 3 = `[20, 30]` |
| `range(start, stop)` | cuts (the numbers produced are the boxes in between) | `range(1, 3)` → `1, 2` |
| `prefix[i]` (lecture 005) | a **cut**: the sum of everything before cut `i` | `prefix[0]` = 0, `prefix[5]` = whole sum |
| `first_true` answer in binary search (lecture 004) | a **cut**: "the switch happens here"; `n` means "after everything" | |
| `len(a)` | the **last cut** | 5 |

That's why `prefix` has `n + 1` entries, why binary search's answer can be `n`, and why `range(0, n)` stops at `n - 1`. **They're all cut-based.** On Oct 9 you explained prefix sums from exactly this picture, so you already have it. This lecture is about using it deliberately everywhere.

**The habit:** when an index shows up, ask *"is this a box or a cut?"* If it's going into `a[...]` by itself, it's a box. If it's going into a slice, a `range`, a prefix array, or it's an answer that can equal `n`, it's a cut.

---

## 2. Counting: the slice rule and the closed rule

### 2.1 The slice rule

> **`a[start:stop]` has `stop - start` elements** (when `0 <= start <= stop <= n`).

Why: it's the distance between two cuts, and each step between neighbouring cuts passes exactly one box.

```
cut:     0    1    2    3    4    5
         | 10 | 20 | 30 | 40 | 50 |
              └─────────┘
              a[1:3]: from cut 1 to cut 3 → 3 - 1 = 2 elements
```

### 2.2 The closed rule

> **Boxes `first … last` (both included) contain `last - first + 1` elements.**

Derivation from the slice rule: the boxes `first … last` are the slice `a[first : last + 1]` (the cut *after* box `last` is `last + 1`). Count = `(last + 1) - first`.

### 2.3 Translate, don't decide

Whenever you need a count, **translate the words into a slice first.** Then you never decide about a `-1`:

| In words | Slice | Count |
|---|---|---|
| from `i` to the end | `a[i:n]` | `n - i` |
| everything before `i` | `a[0:i]` | `i` |
| everything after `i` (not including `i`) | `a[i+1:n]` | `n - i - 1` |
| from `i` to `j`, both included | `a[i:j+1]` | `j - i + 1` |
| strictly between `i` and `j` | `a[i+1:j]` | `j - i - 1` |
| the first `k` | `a[0:k]` | `k` |
| the last `k` | `a[n-k:n]` | `k` |

Your Oct 10 merge question, done this way: "from `i` to the end of `left`" → `left[i:len(left)]` → `len(left) - i`. One translation, no argument.

---

## 3. Distance vs count (posts and fence sections)

Two different questions get mixed up constantly:

| Question | Formula | Example (`i = 3`, `j = 7`) |
|---|---|---|
| **How many steps** from index `i` to index `j`? | `j - i` | 4 steps |
| **How many elements** from `i` to `j`, both included? | `j - i + 1` | 5 elements (3, 4, 5, 6, 7) |

Picture a fence: the posts are at 3, 4, 5, 6, 7 (5 posts), with 4 sections between them. **Elements are posts, steps are sections.** Counting posts gives one more than counting sections, because both ends have a post.

Where each one shows up:

- **Steps:** "move `fast` k steps ahead," "the width of a container" (`hi - lo`, lecture 006 §2), "the diameter in edges" (lecture 007 §6).
- **Elements:** "window length," "how many in this range," "number of nodes on a path."

**The habit:** before writing `j - i`, ask *"am I counting steps or things?"* If things, and both ends are included, it's `+ 1`.

---

## 4. The start / last / length triangle

Many index bugs are converting between three quantities. Here they are, derived once, for both conventions:

| Know | Want | Closed (`last` included) | Half-open (`stop` excluded) |
|---|---|---|---|
| start, length | end | `last = start + length - 1` | `stop = start + length` |
| end, length | start | `start = last - length + 1` | `start = stop - length` |
| start, end | length | `length = last - start + 1` | `length = stop - start` |

You only need **one line** to derive all of them: *a closed range has `last - start + 1` elements.* Set that equal to `length` and solve for whatever you need.

Example: your fixed window (Oct 9). The window has `m` elements and its newest element is `r` (included), so `r` is `last`:
`start = r - m + 1`. The element that leaves when the window moves from ending at `r - 1` to ending at `r` is the old start: `(r - 1) - m + 1 = r - m`.

Notice the half-open column never has a `±1`. That's the main reason half-open is the default in Python and in most library code: **fewer `±1`s means fewer chances to get one wrong.**

---

## 5. Name → valid set → test (for any index expression)

The method that clicked for you on Oct 5 (Climbing Stairs), stated generally:

1. **Name** the index you're about to use. `nxt = i + 2`. `nr = r + dr`. `leaving = r - m`. `start = r - m + 1`.
2. **Write its valid set.** For an array index: `0 <= x <= n - 1`. For a cut (slice end, prefix position, "answer can be n"): `0 <= x <= n`. For a position with an inclusive destination (stairs): `0 <= x <= n`.
3. **Test membership positively,** using only the side that can fail: `if nxt <= n:`, `if leaving >= 0:`, `if 0 <= nr < rows:`.

| Expression | Name | Valid set | The test you write |
|---|---|---|---|
| `i + 2` (two steps up a staircase with top `n`) | `nxt` | `0 … n` | `nxt <= n` |
| `r + dr` (grid neighbour) | `nr` | `0 … rows - 1` | `0 <= nr < rows` |
| `r - m` (leaving element) | `leaving` | `0 … n - 1` | `leaving >= 0` |
| `i - 1` (previous element, 3Sum dedup) | `prev` | `0 … n - 1` | `i - 1 >= 0`, i.e. `i > 0` |
| `binary-search answer` | `first_true` | `0 … n` (n = none) | `ans < n` before `nums[ans]` |

**Strict or non-strict?** It falls out of the valid set. `x <= n - 1` and `x < n` mean the same for integers. Use whichever matches how you wrote the valid set, and prefer `< n` for array indices because it pairs with `range(n)` and `len`.

**Avoid negation.** `if not i + 2 < n` makes you flip both the comparison and the meaning. Write the **valid** condition directly.

---

## 6. Two-point checking: why plugging in both ends is enough

Almost every index formula in these problems is **linear** in the loop variable: `n - i`, `r - m + 1`, `len(left) - i`, `2 * i + 1`. A linear formula is a straight line. **A straight line is completely fixed by two points.** So:

> If your formula gives the right answer at the **smallest** and the **largest** value of the variable, it's right for every value in between.

Example: count of elements from `i` to the end, `n = 5`.

| Check | Expected (count by hand) | `n - i` | `n - 1 - i` | `n - (i - 1)` |
|---|---|---|---|---|
| `i = 0` (everything) | 5 | 5 ✓ | 4 ✗ | 6 ✗ |
| `i = 4` (just the last) | 1 | 1 ✓ | 0 ✗ | 2 ✗ |

Two rows, and the three candidates you were weighing on Oct 10 are settled in about 20 seconds. Notice also *how* the wrong ones are wrong: off by exactly 1 at both ends. If both checks are off by the same amount, **add or subtract that amount** and you're done.

**The habit:** for any `±1` doubt, don't reason. Make the two-row table with the extremes and count by hand.

---

## 7. Counting possibilities by counting starts

"How many windows / subarrays / placements…?" questions become easy if you count **legal starting positions** with §5:

**How many windows of length `k` in an array of length `n`?**

1. Name the start: `s`. The window is `s … s + k - 1`.
2. Valid set: `s >= 0` and its last element `s + k - 1 <= n - 1`, so `0 <= s <= n - k`.
3. Count the integers `0 … n - k`: closed rule, `(n - k) - 0 + 1 = n - k + 1`.

Check with two points: `k = 1` → `n` windows ✓; `k = n` → 1 window ✓.

The same move answers:

| Question | Starts | Count |
|---|---|---|
| windows of length `k` | `0 … n-k` | `n - k + 1` |
| pairs `(i, j)` with `i < j` | for each `i`, `j` in `i+1 … n-1` | `n(n - 1) / 2` |
| all non-empty subarrays | pairs of cuts `start < stop` from `0 … n` | `n(n + 1) / 2` |
| positions where a word of length `m` fits in a string of length `n` | `0 … n-m` | `n - m + 1` |

---

## 8. Python's conventions, all in one place

| Thing | What it does | Box or cut |
|---|---|---|
| `range(n)` | `0, 1, …, n-1` (`n` values) | stops before cut `n` |
| `range(a, b)` | `a, …, b-1` (`b - a` values; empty if `a >= b`) | cuts `a` to `b` |
| `range(first, last + step, step)` | walks `first … last` **inclusive** in either direction (lecture 001 Addendum A.3) | |
| `range(5, 1, -1)` | `5, 4, 3, 2` (stops before 1) | |
| `a[i:j]` | `j - i` elements; never raises, even out of range | cuts |
| `a[-k]` | the element `k` from the end = `a[n - k]` | box |
| `len(a)` | `n` = the last cut | cut |
| `enumerate(a)` | `(index, value)` pairs, index from 0 | box |
| `bisect_left(a, x)` | first cut where `x` could be inserted | cut, `0 … n` |
| `(lo + hi) // 2` | rounds down: lower middle | box |

Two Python behaviours that hide index bugs:

- **Negative indices don't raise.** `a[-1]` silently means the last element. Your Birthday attempt read `s[2 - 3]` = `s[-1]` and got the wrong element without any error (lecture 003 §6.1). If an index *could* go negative, test `>= 0` yourself.
- **Slices don't raise either.** `a[3:100]` on a 5-element list returns `a[3:5]`. Convenient, but it can hide a wrong `stop`.

---

## 9. Loops: what the loop variable means

Most index bugs inside loops come from not stating **what the loop variable means at the top of each pass.** Write it as a comment using cuts:

```python
for i in range(n):
    # processed = a[0:i]  (i elements done), current = a[i]
```

With that sentence, many decisions answer themselves:

| Question | Read it off the sentence |
|---|---|
| How many elements are processed before `a[i]`? | `i` |
| How many are left after `a[i]`? | `a[i+1:n]` → `n - i - 1` |
| What's the first `i`? What's the last? | `0` and `n - 1` |
| After the loop, how many are processed? | all `n` (`a[0:n]`) |

For **while loops with two pointers**, write which convention the pointers use:

| Loop | Pointers mean | Range of candidates | Count | Non-empty while |
|---|---|---|---|---|
| `while lo <= hi` | closed `[lo, hi]` | boxes `lo … hi` | `hi - lo + 1` | `lo <= hi` |
| `while lo < hi` (first_true) | closed answers `[lo, hi]`, one candidate left when equal | | `hi - lo + 1` | stop when `lo == hi` |
| `while lo < hi` (half-open scan) | cuts `[lo, hi)` | boxes `lo … hi-1` | `hi - lo` | `lo < hi` |

The loop condition isn't something you choose. It's **"the range is not empty yet,"** written in that range's convention.

---

## 10. Writing it down: rulers, brackets and comment templates

Your note on Oct 10, "maybe I might be able to explicitly write out an example in the comments," is a good instinct. These are the formats that work best.

### 10.1 The ruler

Above any array you're reasoning about, write the indices (boxes) and, if you're using slices, the cuts:

```
#  cut:   0   1   2   3   4   5
#  idx:     0   1   2   3   4
#  a  :  [  3,  5,  8, 10, 12 ]
```

### 10.2 Brackets

Mark the range you mean with brackets directly under the ruler. Then count the elements inside on your fingers:

```
#  a  :  [  3,  5,  8, 10, 12 ]
#                [-------]            a[1:4] = [5, 8, 10] -> 3 elements -> 4 - 1 = 3 ✓
```

### 10.3 The three-line comment template

```python
# want: <the range in words>
# as a slice: a[<start>:<stop>]  ->  count = <stop> - <start>
# check: a = [3, 5, 8], <variable> = 1  ->  <the actual elements>  ->  <count> ✓
```

Filled in for the merge step:

```python
# want: elements of left from i to the end
# as a slice: left[i:len(left)]  ->  count = len(left) - i
# check: left = [3, 5, 8], i = 1  ->  [5, 8]  ->  2 = 3 - 1 ✓
cross += len(left) - i
```

### 10.4 The convention comment

At the top of any function with boundaries:

```python
# lo, hi are CLOSED: both are valid candidates
```

or name variables so the convention can't be forgotten: `last` vs `end_excl`, `lo_incl` vs `hi_excl`. It looks verbose, and that's the point: the convention is on screen, not in your head.

---

## 11. Special cases you meet often

| Situation | Formula | Derivation (one line) |
|---|---|---|
| Mirror of index `i` (reverse position) | `n - 1 - i` | first + last = `0 + (n - 1)`, so `i` and its mirror sum to `n - 1` |
| Negative index `-k` | `n - k` | `-1` is the last box, `n - 1` |
| Middle of `a` | `n // 2` (upper middle for even `n`); `(n - 1) // 2` (lower middle) | `n = 6`: 3 and 2, the two middles; `n = 5`: both give 2 |
| 1-based "k-th" item from a problem | index `k - 1` | the 1st item is index 0 |
| 1-based answers (Two Sum II) | return `index + 1` | |
| Flatten a grid cell | `r * cols + c` | `r` full rows before it, then `c` more |
| Unflatten | `r, c = divmod(i, cols)` | |
| `k` steps from the head of a linked list | lands on node number `k` (0-based) | 0 steps = the head = node 0 |
| Last valid start for a length-`k` window | `n - k` | §7 |

---

## 12. When you're stuck: a decision procedure

When an index question has you going in circles (like the 20 minutes on Oct 10), stop reasoning and run this, in order:

```
1. WORDS     Say what you want in words. ("elements from i to the end")
2. PICTURE   Draw the ruler. Box or cut?
3. SLICE     Translate to a[start:stop]. Count = stop - start.
             (Or closed [first, last]: count = last - first + 1.)
4. NAME      If it's an index you'll USE: name it, write its valid set, test positively.
5. TWO POINTS  Plug in the smallest and largest value of the variable.
               Count by hand. Both match? Done. Both off by the same amount? Adjust by it.
6. REPL      (Practice only) Check with list(range(...)) or a[...] in Python.
```

Steps 1–3 usually settle it. Step 5 settles anything left. If you're still unsure after step 5, the problem isn't the index. You're probably unclear about *what you want* (step 1), and that's worth fixing first.

---

## 13. Drills

Do these without running anything, then check with Python. Write your answer first. The point is to find out where your intuition is off, quickly. Use any technique from this lecture; try at least two different ones on the harder items.

**Counting**

1. `a` has length 7. How many elements are in `a[2:5]`?
2. How many indices from 3 to 9, both included?
3. How many steps from index 3 to index 9?
4. In an array of length `n`, how many elements are strictly after index `i`?
5. How many windows of length 4 are there in an array of length 10?

**Converting**

6. A window of length 4 ends at index 10 (included). Where does it start? Write it as a slice.
7. A window of length 4 starts at index 5. What's its last index? Its `stop`?
8. Mirror of index 2 in an array of length 7?
9. `a[-3]` in an array of length 7 is which index?

**Ranges**

10. `list(range(5, 1, -1))`?
11. Write a `range` that visits 9 down to 3, both included.
12. `list(range(4, 4))`?

**Valid sets**

13. Climbing to step `n`; from step `i`, when is a 3-step move allowed?
14. In a grid with `rows` rows, when is the cell above `(r, c)` valid?
15. A binary search returned `ans` (valid set `0 … n`). What must you check before reading `nums[ans]`?

**Mixed**

16. Middle index of a length-5 array? The two middles of a length-6 array?
17. In a 4×5 grid, flat index of `(2, 3)`? Which cell is flat index 17?
18. `left` has 5 elements and you're at `i = 3`. How many elements of `left` are from `i` to the end?
19. A `first_true` search has `lo = 3, hi = 7` (closed candidates). How many candidates are left?
20. How many pairs `(i, j)` with `i < j` in 4 elements? How many non-empty subarrays?

<details><summary><b>Answers</b> (all checked in Python)</summary>

1. **3** (`5 - 2`).
2. **7** (`9 - 3 + 1`).
3. **6** (`9 - 3`).
4. **`n - i - 1`** (`a[i+1:n]`).
5. **7** (`10 - 4 + 1`; starts `0 … 6`).
6. Start **7** (`10 - 4 + 1`); slice **`a[7:11]`**.
7. Last **8** (`5 + 4 - 1`); stop **9**.
8. **4** (`7 - 1 - 2`).
9. **4** (`7 - 3`).
10. **`[5, 4, 3, 2]`**.
11. **`range(9, 2, -1)`** (first = 9, last = 3, step = -1 → stop = 3 - 1 = 2).
12. **`[]`** (start ≥ stop).
13. **`i + 3 <= n`** (name `nxt = i + 3`, valid set `0 … n`).
14. **`r - 1 >= 0`** (the only side that can fail).
15. **`ans < n`** (and then `nums[ans] == target` if that's what you need).
16. **2**; **2 and 3** (`(n-1)//2` and `n//2`).
17. **13** (`2·5 + 3`); **(3, 2)** (`divmod(17, 5)`).
18. **2** (`5 - 3`).
19. **5** (`7 - 3 + 1`, closed).
20. **6** pairs (`4·3/2`); **10** subarrays (`4·5/2`).
</details>

**Repeat drill:** in 2–3 days, do them again from a blank page. Write down which ones you hesitated on. Those show which technique you haven't absorbed yet.

---

## 14. Reference card

```
INDICES AND BOUNDS: REFERENCE CARD

TWO PICTURES      box = an element (a[i], 0..n-1)     cut = a boundary (slices, range, prefix, 0..n)
                  cut i sits just BEFORE box i;  n boxes have n+1 cuts

COUNT             slice a[start:stop]      -> stop - start            (no ±1, ever)
                  closed [first, last]     -> last - first + 1
                  steps from i to j        -> j - i                   (sections, not posts)

TRIANGLE          closed: last = start + len - 1      half-open: stop = start + len

TRANSLATE         "i to the end" = a[i:n] -> n - i     "before i" = a[0:i] -> i
                  "after i" = a[i+1:n] -> n - i - 1    "i..j incl" = a[i:j+1] -> j - i + 1

ANY INDEX YOU USE name it -> write its valid set -> test positively (no `not`)
                  array index 0..n-1 (x < n)   cut/answer 0..n (x <= n)

DOUBT?            two-point check: plug in the smallest and largest value, count by hand
                  both off by the same d? adjust by d

COUNT CHOICES     count legal starts: windows of length k = n - k + 1

RANGE INCLUSIVE   range(first, last + step, step)

LOOP SENTENCE     "at the top of pass i: processed = a[0:i]"
WHILE CONDITION   "the range is not empty", in its own convention

SPECIALS          mirror n-1-i · a[-k] = a[n-k] · middles (n-1)//2, n//2 · flat r*cols+c
```

---

## Sources

- Python semantics (`range`, slicing, negative indices): https://docs.python.org/3/library/stdtypes.html#common-sequence-operations and https://docs.python.org/3/library/stdtypes.html#range
- The cut/box view of half-open ranges is the standard argument for zero-based, half-open intervals. See Edsger W. Dijkstra, "Why numbering should start at zero" (EWD831, 1982), https://www.cs.utexas.edu/users/EWD/transcriptions/EWD08xx/EWD831.html
- Your own history: tracker entries and lectures 001 (Addendum A), 003 §6, 004, 005 §5, 006 §5 and this week's recap entries 3.2 and 4.
- Verification (2026-10-10): every numeric example and all 20 drill answers were computed in Python.
