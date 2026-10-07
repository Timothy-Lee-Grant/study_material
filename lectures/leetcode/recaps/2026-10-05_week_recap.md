# Weekly Recap: Week of 2026-10-05 (Mon) → 2026-10-11 (Sun)

> **What this is:** a running document for this week. Each time you explain a concept back to me (a recall), I add what you're still missing, any misconceptions, or extra depth you asked for. **Your earlier lectures stay untouched.** Read this at the end of the week.
> **Rules I follow when adding here:** only add what your explanation shows you need. If a topic came through solid, it gets one line saying so, not filler. Every example problem includes the full problem (paraphrased), examples and constraints, so you don't need to open LeetCode to follow along. No firmware analogies, no characters.
> **Entries this week:** 1

---

## Contents

- [Entry 1 (Oct 6): Binary search (from your recall of lecture 004)](#entry-1-oct-6-binary-search-from-your-recall-of-lecture-004)

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

*(Further entries this week will be added below.)*
