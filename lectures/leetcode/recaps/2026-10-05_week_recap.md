# Weekly Recap: Week of 2026-10-05 (Mon) → 2026-10-11 (Sun)

> **What this is:** a running document for this week. Each time you explain a concept back to me (a recall), I add what you're still missing, any misconceptions, or extra depth you asked for. **Your earlier lectures stay untouched.** Read this at the end of the week.
> **Rules I follow when adding here:** only add what your explanation shows you need. If a topic came through solid, it gets one line saying so, not filler. Every example problem includes the full problem (paraphrased), examples and constraints, so you don't need to open LeetCode to follow along. No firmware analogies, no characters.
> **Entries this week:** 4

---

## Contents

- [Entry 1 (Oct 6): Binary search (from your recall of lecture 004)](#entry-1-oct-6-binary-search-from-your-recall-of-lecture-004)
- [Entry 2 (Oct 9): Prefix sums (from your recall of lecture 005)](#entry-2-oct-9-prefix-sums-from-your-recall-of-lecture-005)
- [Entry 3 (Oct 9): Two pointers and sliding windows (from your recall of lecture 006)](#entry-3-oct-9-two-pointers-and-sliding-windows-from-your-recall-of-lecture-006)
- [Entry 4 (Oct 10): Counting elements in a range, and the merge-sort pair count](#entry-4-oct-10-counting-elements-in-a-range-and-the-merge-sort-pair-count)

---

## Entry 1 (Oct 6): Binary search (from your recall of lecture 004)

### What came through solid (no action needed)

- The **monotone F…F T…T** framing and "find the first True", including your observation that the last False could be at index -1 (everything True).
- **Why `hi = mid` and `lo = mid + 1`:** your explanation ("the next potential lowest candidate is the right neighbor of the index I just ruled out") is exactly right, and better phrased than the lecture.
- **Why `hi` starts at `n`:** an extra answer meaning "no True anywhere."
- **Why `while lo < hi`:** both ends inclusive, so `lo == hi` means exactly one candidate is left, and it's the answer.
- **Koko:** you derived the `can_finish` question, corrected your lower bound from 0 to 1 by reasoning about which values are valid answers, and found the upper bound `max(piles)` *before reading the solution*.

### 1.1 The gap you flagged: why floor division, in a way you can feel

You said you can reproduce `mid = (lo + hi) // 2` but don't feel why. Here is a derivation in four steps, using the same "name it, write its valid set" method.

**Step 1: What `mid` has to do.** `mid` splits the candidates `[lo, hi]` into two groups:

```
[lo ........ mid] [mid+1 ........ hi]
   "keep if True"     "keep if False"
```

If `mid` is True, you keep the **left** group (`hi = mid`). If False, you keep the **right** group (`lo = mid + 1`).

**Step 2: Both groups must be non-empty.** If one group could be empty, then choosing the *other* group would keep **all** the candidates: no progress, infinite loop. So:

- left group `[lo, mid]` is non-empty → always true, as long as `mid >= lo`.
- right group `[mid+1, hi]` is non-empty → requires `mid + 1 <= hi`, i.e. **`mid <= hi - 1`**.

**Step 3: Valid set of `mid`.** Put those together:

```
lo <= mid <= hi - 1
```

So `mid` must **never equal `hi`**. That's the whole requirement.

**Step 4: Which rounding guarantees that?** The dangerous case is the smallest one: **two candidates left**, `hi = lo + 1`. The true midpoint is `lo + 0.5`, and you must pick a whole number.

| Rounding | `mid` when `[lo, hi] = [4, 5]` | Allowed (`mid <= hi - 1 = 4`)? | If `mid` is True… |
|---|---|---|---|
| floor `(4+5)//2` | **4** | ✓ | `hi = 4` → one candidate left → done |
| ceil `(4+5+1)//2` | **5** | ✗ | `hi = 5` → nothing changed → **infinite loop** |

With more than two candidates, both roundings land strictly inside, so either works. **Rounding only matters in the last step, with two candidates left, and floor is the rounding that keeps `mid` off `hi`.** (Verified: with ceil, `[False, True]` loops forever.)

**The rule you can actually use:**

> **The branch that *keeps* `mid` decides the rounding. Round away from that side.**
> In `first_true`, the True branch keeps `mid` in the **high** group (`hi = mid`), so round **down**.

### 1.2 The mirror template (so the rule isn't a one-off)

Some problems have the shape **T…T F…F** and ask for the **last True** ("the largest X that still works"). The keep-`mid` branch flips sides, so the rounding flips too:

```python
def last_true(a):          # a looks like T T T F F; returns -1 if no True
    lo, hi = -1, len(a) - 1           # answer's valid set: -1 .. n-1  (-1 means "no True")
    while lo < hi:
        mid = (lo + hi + 1) // 2      # ceil: keeps mid off lo
        if a[mid]:
            lo = mid                  # True keeps mid, on the LOW side
        else:
            hi = mid - 1              # False rules mid out
    return lo
```

Same derivation, mirrored: the True branch keeps `mid` on the **low** side, so `mid` must never equal `lo`, so round **up**. (Verified on 2,000 random T…T F…F arrays.)

You don't need to memorize this one. The point is that the rounding isn't a magic convention: it falls out of "which side keeps `mid`." In practice you can always use `first_true` and flip the question instead (lecture 004 §8, last row).

### 1.3 Core ideas you didn't mention (quick refresh)

You didn't bring these up. That doesn't mean you don't know them, but they're worth a 30-second check:

- **Exact search is `first_true` + one check.** Find the first `i` with `nums[i] >= target`, then: `if i < len(nums) and nums[i] == target`. The `i < len(nums)` comes first because `n` is in the answer's valid set but isn't a valid index.
- **`lo = mid` (without `+1`) is the infinite-loop bug.** It's the same story as 1.1: with two candidates, `mid == lo`, so `lo = mid` changes nothing.
- **Tracing:** `lo | hi | mid | question(mid) | decision`, 3–4 rows. Try it on the next problem before submitting.

### 1.4 One small precision point (Koko)

You said the upper bound works "assuming there are more hours than piles." It's **at least as many** (`h >= len(piles)`): at speed `max(piles)` each pile takes exactly one hour, so `len(piles)` hours are needed, and `h == len(piles)` is enough. LeetCode guarantees `piles.length <= h`, so `max(piles)` is always a valid answer.

### 1.5 Problems to try this week (full problems included, as you asked)

**35. Search Insert Position (Easy).** *(problem paraphrased)* You get a sorted array `nums` of distinct integers and a `target`. Return the index of `target` if it's in the array; otherwise return the index where it would go to keep the array sorted. Required: O(log n).
Examples: `[1,3,5,6], 5` → `2`; `[1,3,5,6], 2` → `1`; `[1,3,5,6], 7` → `4`.
Constraints: length 1 to 10^4; values and target between -10^4 and 10^4; sorted ascending, distinct.

**278. First Bad Version (Easy).** *(problem paraphrased)* Versions are numbered `1, 2, …, n`. Once a version is bad, every later version is also bad. You can call `isBadVersion(v)`, which returns True if version `v` is bad. Return the first bad version, using as few calls as possible.
Examples: `n = 5`, first bad is 4 → `4`; `n = 1`, first bad is 1 → `1`.
Constraints: `1 <= bad <= n <= 2^31 - 1`.
*Watch:* versions start at **1**, not 0. Name the answer and write its valid set before choosing `lo` and `hi`.

**875. Koko Eating Bananas (Medium).** *(problem paraphrased)* There are piles of bananas, `piles[i]` in pile `i`, and `h` hours. Koko picks a whole-number speed `k`. Each hour she picks one pile and eats `k` bananas from it; if the pile has fewer than `k`, she finishes that pile and eats nothing else that hour. Return the smallest `k` that lets her finish every pile within `h` hours.
Examples: `[3,6,7,11], h = 8` → `4`; `[30,11,23,4,20], h = 5` → `30`; `[30,11,23,4,20], h = 6` → `23`.
Constraints: `1 <= len(piles) <= 10^4`; `len(piles) <= h <= 10^9`; `1 <= piles[i] <= 10^9`.
*You've already reasoned this one out. Now write it from a blank page and trace `[3,6,7,11], h = 8`.*

---

## Entry 2 (Oct 9): Prefix sums (from your recall of lecture 005)

### What came through solid

- **The definition, in its half-open form:** `prefix[i]` = sum of `nums[0:i]`, everything *before* index `i`.
- **Why the indices look offset:** each prefix index describes the range that stops just before that index.
- **Why `prefix[0] = 0`:** it's the sum of an empty range.

That's exactly the part people usually get confused by, and you explained it from the convention, not from memory.

### 2.1 The one thing to add: what the definition is *for*

Your recall described what `prefix` stores, but not the line that makes it useful:

```
sum(nums[l:r]) = prefix[r] - prefix[l]          (0 <= l <= r <= n)
```

The first `r` elements minus the first `l` elements leaves exactly elements `l … r-1`. Because both prefixes are half-open, **no `-1` appears anywhere**, and `l = 0` needs no special case (`prefix[0] = 0`). That's the payoff of the convention you just explained.

Example: `nums = [3, 1, 4, 1, 5]`, `prefix = [0, 3, 4, 8, 9, 14]`. Sum of `nums[1:4]` = `prefix[4] - prefix[1]` = `9 - 3` = **6** (1 + 4 + 1 ✓).

### 2.2 Parts of lecture 005 you didn't mention (quick self-test)

You only described the prefix-sum half, which is fine. Before your next explanation, check you can answer these without looking (answers are in lecture 005):

1. A double loop's inner loop asks "is there an earlier `j` with ___?" What three steps turn it into a dictionary lookup? (§2)
2. Why look up **before** inserting the current element? (§2 step 5)
3. In Subarray Sum Equals K, what does `{0: 1}` stand for? Hint: it's your `prefix[0] = 0`, used as a dictionary entry. (§6.1)
4. Why is it `need = (k - r) % k` and not `k - r`? (§3.2)

---

## Entry 3 (Oct 9): Two pointers and sliding windows (from your recall of lecture 006)

### What came through solid

- **Validity has to be monotone** for a window to work, and you connected it to binary search's F…F T…T shape yourself.
- **Why a minimum-length window can stop growing:** with positive numbers, once a window is valid, growing it keeps it valid, just longer.
- **3Sum, both pointers move after a hit.** You worked out the reason while explaining it: with one of the two values unchanged, the only partner that sums to 0 has the same value as before, which would be a duplicate. That reasoning is correct.

Your three open questions are below, in the order you asked them.

### 3.1 "If I move `l` and the window is valid again, how do I know it's the smallest one for that start? Why doesn't `r` go back?"

This is the right question to ask. The lecture stated the shrink rule without proving it. Here's the proof, in two facts.

**Fact A (what the loop guarantees).** At the start of each step, *before* `nums[r]` is added, the window `[l, r-1]` is **invalid** (sum < target). That's because the shrink loop only stops once the window is invalid.

**Fact B (all values positive).** A window that sits **inside** an invalid window is also invalid: removing positive numbers can only lower the sum.

Now take any start `l'` that the shrink loop visits at step `r`:

- Every window `[l', end]` with `end < r` sits inside `[l, r-1]`, which is invalid by Fact A. So by Fact B, **no end before `r` works for `l'`.**
- If `[l', r]` is valid, then **`r` is the smallest valid end for `l'`**, so the recorded length `r - l' + 1` is the best possible for that start.

That's also why `r` never moves back: for every later start, every end before `r` is inside an invalid window.

**Your example, made concrete.** `nums = [1, 1, 1, 1, 10, 20]`, target `12`. For each start, here is the smallest end that works (computed by brute force):

| start `l` | smallest valid end | length |
|---|---|---|
| 0 | 4 | 5 |
| 1 | 4 | 4 |
| 2 | 4 | 3 |
| 3 | 5 | 3 |
| 4 | 5 | 2 |
| 5 | 5 | 1 |

The smallest valid end never decreases as the start moves right. That's the property the algorithm relies on. Here's what the algorithm actually does (from running it):

| r | add | windows recorded while shrinking | after shrinking |
|---|---|---|---|
| 0–3 | 1, 1, 1, 1 | — | `[0..3]` sum 4 |
| 4 | +10 | `[0..4]` len 5 ✓, `[1..4]` len 4 ✓, `[2..4]` len 3 ✓ | `[3..4]` sum 11 (invalid) |
| 5 | +20 | `[3..5]` len 3 ✓, `[4..5]` len 2 ✓, `[5..5]` len 1 ✓ | empty |

Every recorded window matches the "smallest valid end" table exactly. The algorithm never records a window that isn't the best for its start.

**Where the F…F T…T shape lives.** You noticed that moving `l` "breaks" the shape. The shape isn't along one line. Draw every window as a grid, with rows = start `l`, columns = end `r`, T = valid:

```
        r=0  1  2  3  4  5
l=0      F   F  F  F  T  T
l=1      ·   F  F  F  T  T
l=2      ·   ·  F  F  T  T
l=3      ·   ·  ·  F  F  T
l=4      ·   ·  ·  ·  F  T
l=5      ·   ·  ·  ·  ·  T
```

- **Each row is F…F T…T.** For a fixed start, growing the end keeps it valid. That's binary search's shape.
- **The boundary only moves right as you go down.** That's Fact B.

The sliding window walks along this **staircase boundary**: step right while you're on F, step down while you're on T. It's the same move as Search a 2D Matrix II (lecture 001 §6.4). Each step either moves `r` right or `l` down, never back, which is also why the whole thing is O(n).

### 3.2 The fixed-window formula: where `r - m` and `r - m + 1` come from

You got stuck deciding about the `-1` and whether to use `=`. Don't decide those by reasoning about the inequality. **Derive them from one counting rule:**

> A closed range `[a, b]` contains `b - a + 1` elements.

**Step 1: Name the window's start.** The window has `m` elements and ends at `r` (included). Call its start `start`. Counting: `r - start + 1 = m`, so **`start = r - m + 1`**.

**Step 2: Name the element that leaves.** Last step the window ended at `r - 1`, so it started at `(r - 1) - m + 1 = r - m`. That element is in the old window but not the new one, so it's the one leaving: **`leaving = r - m`**.

**Step 3: Valid sets.** Both are indices, so each must be in `0 … n-1`. The upper end is never a problem, so the test is `>= 0`:

- the window is complete when `start >= 0`, i.e. `r - m + 1 >= 0`
- something leaves when `leaving >= 0`, i.e. `r - m >= 0`

It's `>= 0` and not `> 0` because **0 is a valid index**. That's the name → valid set → test method again.

**Step 4: Check with a table** (`m = 2`):

| r | start = r − 1 | leaving = r − 2 | window | what happens |
|---|---|---|---|---|
| 0 | -1 (invalid) | -2 (invalid) | — | add `s[0]`; window not complete yet |
| 1 | 0 ✓ | -1 (invalid) | `s[0..1]` | add `s[1]`; first complete window, nothing leaves |
| 2 | 1 ✓ | 0 ✓ | `s[1..2]` | add `s[2]`, remove `s[0]` |
| 3 | 2 ✓ | 1 ✓ | `s[2..3]` | add `s[3]`, remove `s[1]` |

To answer your wording: **`start` is the leftmost element still in the window** (and it'll be the one leaving at the next step). **`leaving` is the element removed at this step** (it was the start of the previous window).

### 3.3 3Sum: what happens after a hit

Here's the sequence of moves that confused you, written out. For each "wall" value `nums[i]`:

1. Run the normal Two Sum II loop on `nums[i+1 … n-1]` with `lo` and `hi`.
2. **On a hit:** record it, move **both** `lo` and `hi` inward, then skip `lo` forward while it equals the previous value.
3. **Keep going in the same loop.** The wall doesn't move after a hit. There may be another, different pair for the same wall.
4. Only when `lo >= hi` is this wall done. Move to the next wall, skipping walls that equal the previous wall.

**Why only `lo` gets a duplicate-skip:** if `hi` is still on a repeated value, the normal comparison handles it. `lo` now holds a strictly larger value than before, so with the same `hi` value the sum is too big, and the loop moves `hi` down on its own.

Trace on `[-4, 0, 0, 1, 3, 4, 4]` (from running the code). The wall `-4` has **two different** answers, which shows why the loop continues after a hit:

```
wall i=0 (-4)
   lo=1(0) hi=6(4) sum 0 → RECORD, lo+1, hi-1
      skip lo=2(0): same as previous
   lo=3(1) hi=5(4) sum 1 > 0 → hi-1           ← duplicate 4 handled by the normal comparison
   lo=3(1) hi=4(3) sum 0 → RECORD, lo+1, hi-1   ← second answer, same wall
   lo=4 hi=3: lo<hi False → next wall
wall i=1 (0)
   ... sums all > 0, hi walks down until lo<hi fails
i=2 (0): same as previous wall → skip
wall i=3 (1) ... no hits
wall i=4 (3) ... no hits
result: [[-4, 0, 4], [-4, 1, 3]]   (matches brute force)
```

So: you don't redo the problem, and you don't need to move both pointers until a new value appears. After the hit, both move once, `lo` skips its duplicates, and the ordinary comparisons take care of everything else.

### 3.4 Parts of lecture 006 you didn't mention

These are worth a one-minute look before your next practice session:

- **Inward pointers: the "ruled out because…" sentence.** Sum too small means `lo` can't work even with the largest partner, so `lo` moves (§1).
- **Read/write pointers:** the invariant "`nums[0:write]` is the finished answer" (§4).
- **Why the window is O(n) even with a `while` inside a `for`:** `l` only moves right, at most n times in total (§8). The staircase picture in 3.1 shows the same thing.

---

## Entry 4 (Oct 10): Counting elements in a range, and the merge-sort pair count

> From your message about the video on counting pairs with merge sort. You found the right count (`len(left) - i`) but it took about 20 minutes, and you asked for a way to *represent* these questions so they stop being a guess between `n - i`, `n - 1 - i` and `n - (i - 1)`.

### 4.1 The one tool: write it as a slice, then count is `stop - start`

Every "how many elements" question in an array is the same question in disguise:

> **How many elements are in a range?** Write the range as a Python slice `a[start:stop]` (half-open: `start` included, `stop` excluded). **The count is `stop - start`.** Nothing else.

That's the whole rule. The `-1`s you were juggling only appear when you mix in a *closed* range (`last` included). So don't: **always translate to a slice first.**

| You say in words | As a slice | Count = stop − start |
|---|---|---|
| "from index `i` to the end" | `a[i:n]` | `n - i` |
| "everything before `i`" | `a[0:i]` | `i` |
| "from `i` to `j`, both included" | `a[i:j+1]` | `j - i + 1` |
| "the `k` elements ending at `r`, `r` included" | `a[r-k+1:r+1]` | `k` ✓ (a sanity check) |
| "strictly between `i` and `j`" | `a[i+1:j]` | `j - i - 1` |

In the merge step: you're at index `i` of `left`, and every element from `i` to the end of `left` is bigger than `right[j]`. In words: "from `i` to the end." As a slice: `left[i:len(left)]`. Count: **`len(left) - i`**. One step, no `-1` to argue about.

The closed-range formula from Entry 3.2 (`last - first + 1`) is the same rule: `[first, last]` is the slice `[first:last+1]`, so the count is `(last + 1) - first`. If you only remember one form, remember the slice form.

### 4.2 Why this is the same picture you already understand

On Oct 9 you explained prefix sums in your own words: `prefix[i]` covers everything **before** `i`, so `prefix[0]` is the empty range. That's the picture where indices are **boundaries between elements**, not the elements themselves:

```
boundaries:  0     1     2     3      ← these are the numbers you put in a slice
elements:    |  3  |  5  |  8  |
               a[0]  a[1]  a[2]
```

A slice `a[start:stop]` is "everything between boundary `start` and boundary `stop`." The count is the distance between the two boundaries: `stop - start`. That's the fence-post idea you remembered: **boundaries are the posts, elements are the fence sections between them.** `n` elements have `n + 1` posts (`0 … n`), which is also why `prefix` has `n + 1` entries.

`left[1:3]` in the picture: posts 1 to 3 enclose `5` and `8`, so 2 elements, `3 - 1 = 2` ✓.

### 4.3 What to write in the comments (your "representation" question)

Yes: writing a tiny example in a comment is the right move, and it works best in this exact form. **Name the range in words, write the slice, then check it on a 3-element example:**

```python
# count = elements of left from i to the end  ->  left[i:len(left)]  ->  len(left) - i
# check: left = [3, 5, 8], i = 1  ->  left[1:3] = [5, 8]  ->  2  ->  3 - 1 = 2 ✓
cross += len(left) - i
```

That's two comment lines and about 30 seconds. They do three different jobs:

1. **The words** stop you from guessing the formula. You're translating a sentence, not inventing an equation.
2. **The slice** puts the range in the only form whose count you never have to think about.
3. **The tiny example** catches the remaining mistakes: you can *see* `[5, 8]` and count it on your fingers.

For the edges, plug in the two extremes: `i = 0` should give "all of `left`" (`3 - 0 = 3` ✓), and `i = len(left) - 1` should give "just the last one" (`3 - 2 = 1` ✓). If both ends are right, the formula is right in between, because it's a straight line.

**What to say to yourself, in order:** "What range, in words? → As a slice? → stop minus start. → Check on three elements." Say it out loud the same way every time until it's automatic.

### 4.4 The merge-sort trick itself

**The problem (this is "counting inversions," paraphrased).** Given an array `nums`, count the pairs of indices `(i, j)` with `i < j` and `nums[i] > nums[j]`.
Example: `[2, 4, 1, 3, 5]` → `3` (the pairs of values (2,1), (4,1), (4,3)).
Typical constraint: `n` up to about 10⁵, so the O(n²) double loop (~5·10⁹ checks) is too slow and you need O(n log n).
(LeetCode relatives: 493 Reverse Pairs, which counts `nums[i] > 2 * nums[j]`, and 315 Count of Smaller Numbers After Self.)

**Why merge sort helps, in three steps:**

1. Every pair `(i, j)` is one of three kinds: both in the left half, both in the right half, or **one in each** (`i` on the left, `j` on the right). The first two kinds are counted by the recursive calls (answer flows up, lecture 002).
2. For the "one in each" kind, the original order doesn't matter any more: every left-half element came before every right-half element. So you're free to **sort each half** without changing which cross pairs count.
3. With both halves sorted, the cross pairs can be counted during the merge in one pass. When `left[i] > right[j]`, every element in `left[i:]` is at least `left[i]`, so all of them beat `right[j]`. Count `len(left) - i` (§4.1) and move `j`.

```python
def count_inversions(nums):
    # returns (sorted copy of nums, number of pairs i < j with nums[i] > nums[j])
    if len(nums) <= 1:
        return nums[:], 0
    mid = len(nums) // 2
    left, a = count_inversions(nums[:mid])        # pairs inside the left half
    right, b = count_inversions(nums[mid:])       # pairs inside the right half
    merged = []
    cross = 0
    i = j = 0
    while i < len(left) and j < len(right):
        if left[i] <= right[j]:
            merged.append(left[i]); i += 1
        else:
            # left[i:] are all >= left[i] > right[j]  ->  len(left) - i pairs
            cross += len(left) - i
            merged.append(right[j]); j += 1
    merged.extend(left[i:]); merged.extend(right[j:])
    return merged, a + b + cross
```

(Verified against the brute-force double loop on 3,000 random arrays.)

Trace of one merge, `left = [3, 5, 8]`, `right = [1, 6]` (from running it):

| i | left[i] | j | right[j] | decision | counted | cross |
|---|---|---|---|---|---|---|
| 0 | 3 | 0 | 1 | 3 > 1: take right | `left[0:]` = [3, 5, 8] → 3 | 3 |
| 0 | 3 | 1 | 6 | 3 ≤ 6: take left | — | 3 |
| 1 | 5 | 1 | 6 | 5 ≤ 6: take left | — | 3 |
| 2 | 8 | 1 | 6 | 8 > 6: take right | `left[2:]` = [8] → 1 | 4 |

Check by hand: cross pairs are (3,1), (5,1), (8,1), (8,6) = 4 ✓.

### 4.5 "I would never have come up with that on my own"

That's true for almost everyone the first time, and it isn't the skill being tested. This solution is a **known technique** (merge-sort counting is the standard answer to "count pairs `i < j` with an order condition"). People who solve it in interviews have seen the pattern before, and they recognize it from the trigger:

> **Trigger:** "count pairs `i < j` where `nums[i]` ___ `nums[j]`" + `n` too large for O(n²) → **divide and conquer: count cross pairs while merging sorted halves.**

What *is* derivable, and what you did derive, is the counting step inside the merge. That's the part this entry is about. The roadmap now lists divide-and-conquer counting as a later topic, so you'll get a proper lecture on recognizing it.

---

*(Further entries this week will be added below.)*
