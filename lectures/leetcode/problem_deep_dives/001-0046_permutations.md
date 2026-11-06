# Deep Dive 001: Permutations (46): What Each Level of a Backtracking Tree Decides

> **For:** Timothy · **Date:** 2026-11-06
> **Source:** your Nov 6 attempt in `../examples.py` (`permute`, with helpers `bt` and `bt2`). Not submitted; you stopped to ask whether there's a way to think in terms of **placement** instead of selecting and unselecting.
> **Status:** attempted, not passing. Retry planned, so the full solution in §8 is collapsed.
> **Why this lecture:** you reached for the include/exclude technique ("selecting and then not selecting each step"), saw during your walk-through that it produced partial lists, added a length filter, and felt it "does not feel like the right path." That feeling was right, and your closing question was the right question. The gap isn't in the mechanics (your choose → explore → un-choose was correct). It's one level up: **what each level of a backtracking tree decides.** Include/exclude decides *which numbers*; permutations need *which order*.
> **Format notes:** numbers before symbols; every state variable gets a name | stands for | valid set row; recursion traced as call trees; no firmware analogies.
> **Verification:** your code was run as written. The solutions in §8 were compared with `itertools.permutations` on 500 random inputs (lengths 1–6); the subsets template was compared with `itertools.combinations`. All call trees were printed by running the code.

---

## Core ideas (the answer key)

1. **Every backtracking function answers one question per level.** Write that question down before coding: it decides the shape of the whole tree.
2. **Include/exclude asks "is `nums[i]` in or out?"** It visits the numbers in index order, so it decides **which** numbers are chosen, never their **order**. That's subsets (78), not permutations.
3. **Permutations ask "which unused number goes in the next position?"** One level per position, and at each level, one branch per number that isn't used yet. That's your "placement" idea, and it's the right model.
4. **Count the leaves before coding.** Include/exclude has `2^n` leaves (8 for `[1,2,3]`). Placement has `n × (n-1) × … × 1 = n!` (6 for `[1,2,3]`). If the counts don't match the number of answers you expect, the level question is wrong.
5. **Filtering can only remove answers; it can't create missing ones.** The include/exclude tree has exactly one full-length leaf, `[1,2,3]`, so filtering by length leaves one answer. The orders `[2,1,3]`, `[3,2,1]`… are never built.
6. **State for placement:** `path` (positions filled so far), `used` (which numbers are taken), and the next position is `len(path)`. Choose → explore → un-choose must undo **both** `path` and `used`.
7. **The base case comes from "when is an answer complete?"**, stated positively: `len(path) == len(nums)`. Not "when am I out of bounds."
8. **Trace recursion as a call tree:** one line per call, indented by depth, with the state written at entry and `→ answer` at each leaf. Start with `n = 2`.
9. **A recursive helper must call itself.** `bt2` calls `bt`, so its filter only ran once, at the top. List every recursive-call line and check its name.

---

## Table of Contents

- [0. What your attempt showed](#0-what-your-attempt-showed)
- [1. The problem](#1-the-problem)
- [2. Your attempt, run](#2-your-attempt-run)
- [3. Root 1: what does each level decide?](#3-root-1-what-does-each-level-decide)
- [4. Root 2: the state for placement](#4-root-2-the-state-for-placement)
- [5. Root 3: the base case is "the answer is complete"](#5-root-3-the-base-case-is-the-answer-is-complete)
- [6. Root 4: how to walk through recursion](#6-root-4-how-to-walk-through-recursion)
- [7. The slip: `bt2` calls `bt`](#7-the-slip-bt2-calls-bt)
- [8. A solution, derived step by step (collapsed)](#8-a-solution-derived-step-by-step-collapsed)
- [9. Where else these gaps will show up](#9-where-else-these-gaps-will-show-up)
- [Drills](#drills)
- [Self-check questions](#self-check-questions)
- [Sources](#sources)

---

## 0. What your attempt showed

| What you wrote | What's right | What tripped you up |
|---|---|---|
| `path.append(nums[i]); bt(i+1); path.pop(); bt(i+1)` | ✓ choose → explore → un-choose is exactly right, and `path.copy()` when saving an answer is right | This is the **subsets** tree: each level decides "is `nums[i]` in?" (§3) |
| "I am realizing that this is not correct because I am adding the results where it is less than all of the elements" | ✓ you caught the wrong output **during your own walk-through**, before running it | The partial lists were a symptom; the real problem is that no list ever has a different order |
| `bt2`: `if len(path) == len(nums)` before appending | the filter itself is fine | Filtering can't create the missing orders (§3.3). Also, `bt2` calls `bt`, not itself (§7) |
| "Is there a way to think about this in terms of placement instead of selecting / unselecting elements?" | ✓ **yes, and that's the solution's model** | §3–4 turn it into code |
| "doing a walkthrough with recursion is not immediately coming to me how to express and organize" | ✓ honest and useful | §6 gives a call-tree format |

---

## 1. The problem

**Permutations (46), paraphrased.** Given an array `nums` of **distinct** integers, return every possible ordering (permutation) of them, in any order.
Examples: `[1,2,3]` → `[[1,2,3],[1,3,2],[2,1,3],[2,3,1],[3,1,2],[3,2,1]]`; `[0,1]` → `[[0,1],[1,0]]`; `[1]` → `[[1]]`.
Constraints: `1 <= len(nums) <= 6`; `-10 <= nums[i] <= 10`; all values distinct.

---

## 2. Your attempt, run

Running your code as written on `[1,2,3]`:

| Helper | Output |
|---|---|
| `bt(0)` | `[[1,2,3], [1,2], [1,3], [1], [2,3], [2], [3], []]` |
| `bt2(0)` | the same 8 lists (because `bt2` calls `bt` for its recursion, §7) |
| `bt2` changed to call itself | `[[1,2,3]]`: only one answer |

**The count check finds the problem without any tracing:** `[1,2,3]` should have 6 answers (§3.2). `bt` produced 8, and every one of the 8 is in index order (1 before 2 before 3). Those are exactly the 8 **subsets** of `{1,2,3}`. Your `bt` is a correct solution to a different problem, Subsets (78), as §9 shows.

---

## 3. Root 1: what does each level decide?

A backtracking function builds an answer one decision at a time. **Each level of recursion makes one decision.** So before writing any code, write down:

> **The level question:** "At this level, I decide ______."

That one sentence fixes the parameter, the branches, the base case and the number of answers.

### 3.1 Two different level questions, drawn as trees

**Include/exclude (your `bt`).** Level `i` decides: *is `nums[i]` in the answer?* Two branches: yes or no.

```
level 0: is 1 in?        yes                         no
level 1: is 2 in?    yes      no                yes       no
level 2: is 3 in?  yes  no  yes  no           yes  no   yes  no
leaf:            [1,2,3][1,2][1,3][1]       [2,3] [2]   [3]  []
```

Every path visits 1, then 2, then 3, in index order. So every leaf lists its numbers in index order. **This tree can only decide which numbers, never their order.**

**Placement (your question).** Level `p` decides: *which number goes in position `p`?* One branch per number **not used yet**.

```
position 0:        1                   2                   3
position 1:     2     3             1     3             1     2
position 2:     3     2             3     1             2     1
leaf:        [1,2,3][1,3,2]      [2,1,3][2,3,1]      [3,1,2][3,2,1]
```

Every ordering appears exactly once, because each position can take any number that's still available.

| | Include/exclude | Placement |
|---|---|---|
| Level question | is `nums[i]` in? | which unused number goes in position `p`? |
| What a level stands for | an **index** into `nums` | a **position** in the answer |
| Branches at each level | always 2 | `n - p` (the numbers not used yet) |
| Depth | `n` | `n` |
| Leaves | `2^n` | `n!` |
| Decides | which numbers | which order |
| Solves | Subsets (78) | Permutations (46) |

### 3.2 Count the leaves (the quickest check)

**Numbers first**, with `[1,2,3]`:
- Placement: 3 choices for position 0, then 2 left for position 1, then 1 for position 2: `3 × 2 × 1 = 6`.
- Include/exclude: 2 choices for each of 3 numbers: `2 × 2 × 2 = 8`.

**In symbols:** placement has `n × (n - 1) × … × 1 = n!` leaves (each position has one fewer choice than the last); include/exclude has `2^n`.

**The habit:** before coding, write the level question, then multiply the branches at each level. If the product doesn't equal the number of answers you expect, change the level question **before** writing code. Here, "there should be 3! = 6 orderings" vs "my tree has 2³ = 8 leaves" would have flagged it in 30 seconds.

### 3.3 Why filtering can't fix it

`bt2` kept only the full-length leaves. In the include/exclude tree there's exactly **one** full-length leaf: "yes, yes, yes" = `[1,2,3]`. Running `bt2` (changed to call itself) confirms it: `[[1,2,3]]`.

**General rule:** a filter can only **remove** answers from the tree. If an answer is never built (like `[2,1,3]`), no filter can add it. When the output is missing answers, look at the level question, not the base case.

---

## 4. Root 2: the state for placement

Turn the placement tree into state, one row per name:

| Name | Stands for | Valid set |
|---|---|---|
| `path` | the numbers placed so far: `path[0]` is position 0, … | length `0 … n` |
| `len(path)` | **the next position to fill** (positions `0 … len(path)-1` are full: a slice `path[0:len(path)]`) | `0 … n` |
| `used[j]` | whether `nums[j]` is already in `path` | `True` / `False` for each `j` |

Notice that "the next position" isn't a separate variable. It's `len(path)`, the cut just after the filled positions, the same box/cut idea as the window lectures.

**One level, in words:** for each `j` from `0` to `n - 1`: if `nums[j]` isn't used, **choose** it (mark used, append), **explore** the next position, then **un-choose** it (pop, unmark).

**Name-vs-lines check** (attempt review 001 §4), applied to backtracking:

| Name | Lines that change it | Matches its meaning? |
|---|---|---|
| `path` | `path.append(nums[j])` before the call, `path.pop()` after | ✓ the pop undoes the append |
| `used[j]` | `used[j] = True` before the call, `used[j] = False` after | ✓ only if **both** lines exist |

Forgetting the `used[j] = False` line is the permutation version of the missing un-choose in your earlier Word Search attempt: the number stays "taken" for every later branch.

---

## 5. Root 3: the base case is "the answer is complete"

Your base case was `if i >= len(nums)`: "stop when I'm out of bounds." That's right for include/exclude, because there the level is an **index**, and running out of indices means every number has been decided.

For placement the level is a **position**. Derive the base case positively:

1. An answer is **complete** when every position is filled.
2. There are `n` positions, `0 … n - 1`.
3. They're all filled when the next position to fill is `n`: **`len(path) == len(nums)`**.

So the base case says "the answer is complete, save it." Every leaf of the placement tree is a complete answer, so there's nothing to filter.

**The habit:** write the base case as "an answer is complete when ______" before coding. If you can't fill in the blank, the level question isn't clear yet.

---

## 6. Root 4: how to walk through recursion

You wrote: *"doing a walkthrough with recursion is not immediately coming to me how to express and organize."* Use a **call tree** (lecture 003 §5.5), set up like this:

1. **One line per call**, indented by its depth (4 spaces per level).
2. Write the **state at entry**: the parameter and `path` (and `used`, if there is one).
3. At a base case, write **`→ answer`** plus what gets saved.
4. **Start with `n = 2`**: 2 answers for placement, 4 leaves for include/exclude. It's small enough to finish, big enough to show the shape.
5. At the end, **count the `→ answer` lines** and compare with the expected count (§3.2).

**Your `bt` on `[1,2]`** (printed by running it):

```
bt(0) path=[]
    bt(1) path=[1]
        bt(2) path=[1, 2]
          → answer [1, 2]
        bt(2) path=[1]
          → answer [1]
    bt(1) path=[]
        bt(2) path=[2]
          → answer [2]
        bt(2) path=[]
          → answer []
```

Four answers, where `[1,2]` should have two (`[1,2]` and `[2,1]`). And `[2,1]` never appears: at no point does `2` go into `path` before `1`. The trace shows the problem in 9 lines.

**The placement version on `[1,2,3]`** (printed by running it; `used` shown as the numbers taken):

```
place() path=[] used=[]
    place() path=[1] used=[1]
        place() path=[1, 2] used=[1, 2]
            place() path=[1, 2, 3] used=[1, 2, 3]
              → answer
        place() path=[1, 3] used=[1, 3]
            place() path=[1, 3, 2] used=[1, 2, 3]
              → answer
    place() path=[2] used=[2]
        place() path=[2, 1] used=[1, 2]
            place() path=[2, 1, 3] used=[1, 2, 3]
              → answer
        place() path=[2, 3] used=[2, 3]
            place() path=[2, 3, 1] used=[1, 2, 3]
              → answer
    place() path=[3] used=[3]
        ...                                   (2 more answers, the same way)
```

Notice what the indentation shows: when the trace comes back up a level (from `[1, 2, 3]` to `[1, 3]`), `path` and `used` have been **undone** to what they were at that level. If a line ever shows `used` containing a number that isn't in `path`, the un-choose is missing.

---

## 7. The slip: `bt2` calls `bt`

`bt2` checks the length, then recurses with `bt(i+1)`, not `bt2(i+1)`. So the length filter runs only in the very first call, and every call below it is the old `bt`. That's why `bt(0)` and `bt2(0)` printed the same 8 lists.

It's the recursive version of an alias slip (like `d` for `m` in Birthday Chocolate): a copy-paste from `bt` kept the old name. **Check:** for every recursive helper, list the lines that make recursive calls and confirm each one names the helper itself.

---

## 8. A solution, derived step by step (collapsed)

Try the retry first, using §3–5: write the level question, the state table and the base case as comments, count the leaves, then code it and trace `n = 2`.

<details><summary>Open after your retry: the placement solution</summary>

**Step 1, the level question:** which unused number goes in position `len(path)`?
**Step 2, state:** `path`, `used` (§4 table).
**Step 3, base case:** `len(path) == len(nums)` → save a copy.
**Step 4, branches:** every `j` with `not used[j]`.
**Step 5, choose / explore / un-choose:** both `path` and `used`.

```python
def permute(nums):
    res = []
    path = []                            # numbers placed so far; the next position is len(path)
    used = [False] * len(nums)           # used[j]: nums[j] is already in path
    def place():                         # level question: which unused number goes in position len(path)?
        if len(path) == len(nums):       # every position filled: a complete answer
            res.append(path.copy())      # copy: path keeps changing after this
            return
        for j in range(len(nums)):
            if not used[j]:
                used[j] = True           # choose
                path.append(nums[j])
                place()                  # explore the next position
                path.pop()               # un-choose: undo BOTH changes
                used[j] = False
    place()
    return res
```

**Cost:** `n!` leaves, each copied in O(n): O(n · n!) time, which is 4,320 steps at `n = 6`. O(n) extra space for `path`, `used` and the recursion.

**The same model, written in place (a translation, not a new model).** Keep the array itself split by a cut `i`: `nums[:i]` are the placed positions and `nums[i:]` are the unused numbers. Choosing "which unused number goes in position `i`" is swapping it into box `i`:

```python
def permute_swap(nums):
    nums = nums[:]                       # don't change the caller's list
    res = []
    def place(i):                        # nums[:i] placed; nums[i:] still unused
        if i == len(nums):               # every position placed
            res.append(nums.copy())
            return
        for j in range(i, len(nums)):    # any unused number can go in position i
            nums[i], nums[j] = nums[j], nums[i]    # choose: move it into box i
            place(i + 1)
            nums[i], nums[j] = nums[j], nums[i]    # un-choose: swap back
    place(0)
    return res
```

Here `i` plays the role of `len(path)`, and "unused" is "in the slice `nums[i:]`" instead of a `used` list.
</details>

---

## 9. Where else these gaps will show up

For each one, write the **level question** and **count the leaves** before coding. (The level questions are collapsed below the table, so you can try first.)

| Problem | Statement (paraphrased) | Examples | Constraints |
|---|---|---|---|
| **78 Subsets** | Given distinct integers `nums`, return every subset (including the empty one), with no duplicates, in any order | `[1,2,3]` → 8 subsets; `[0]` → `[[],[0]]` | `1 <= n <= 10`; values `-10 … 10`, distinct |
| **77 Combinations** | Given `n` and `k`, return every way to choose `k` numbers from `1 … n` (order inside a combination doesn't matter) | `n = 4, k = 2` → `[[1,2],[1,3],[1,4],[2,3],[2,4],[3,4]]`; `n = 1, k = 1` → `[[1]]` | `1 <= n <= 20`; `1 <= k <= n` |
| **47 Permutations II** | Like 46, but `nums` **may contain duplicates**; return only the distinct orderings | `[1,1,2]` → `[[1,1,2],[1,2,1],[2,1,1]]`; `[1,2,3]` → 6 | `1 <= n <= 8`; values `-10 … 10` |
| **39 Combination Sum** | Given distinct `candidates` and a `target`, return every combination whose numbers add up to `target`; each number may be used any number of times; two combinations are the same if they use the same numbers the same number of times | `[2,3,6,7], 7` → `[[2,2,3],[7]]`; `[2,3,5], 8` → `[[2,2,2,2],[2,3,3],[3,5]]`; `[2], 1` → `[]` | `1 <= len <= 30`; `2 <= candidates[i] <= 40`; `1 <= target <= 40` |
| **17 Letter Combinations of a Phone Number** | Given a string of digits `2–9`, return every letter string they could spell on a phone keypad (2 = abc, 3 = def, …, 7 = pqrs, 9 = wxyz) | `"23"` → `["ad","ae","af","bd","be","bf","cd","ce","cf"]`; `""` → `[]`; `"2"` → `["a","b","c"]` | `0 <= len(digits) <= 4` |

<details><summary>Level questions (open after trying)</summary>

| Problem | Level question | Leaves |
|---|---|---|
| 78 | is `nums[i]` in or out? (your `bt`: a correct solution to 78) | `2^n` |
| 77 | which number goes next, choosing only numbers **larger** than the last one (so each combination is built in one order only) | `C(n, k)` answers |
| 47 | which unused number goes in the next position, but skip a number equal to one already tried **at this same position** | distinct orderings only |
| 39 | which candidate goes next, from the current candidate onward (it can repeat itself, but never go back) | as many as sum to the target |
| 17 | which letter goes in position `p`, from the letters of `digits[p]` | the product of the letter counts |
</details>

---

## Drills

1. Write the level question and count the leaves for: (a) all orderings of `[4,5,6,7]`; (b) all subsets of `[4,5,6,7]`.
2. In the include/exclude tree for `[1,2,3]`, how many leaves have length 3? How many have length 2?
3. Draw the placement call tree for `[1,2]` with `path` and `used` at each call.
4. A placement solution prints `[[1,2,3],[1,3]]` and then stops finding answers. Which line is probably missing?
5. Write the base case for: (a) placement on `nums`; (b) include/exclude on `nums`; (c) choosing `k` numbers (77).

<details><summary>Answers</summary>

1. (a) "Which unused number goes in position `p`?": `4 × 3 × 2 × 1 = 24`. (b) "Is `nums[i]` in?": `2⁴ = 16`.
2. One leaf of length 3 (`[1,2,3]`); three of length 2 (`[1,2]`, `[1,3]`, `[2,3]`).
3. `place() path=[] used=[]` → `place() path=[1] used=[1]` → `place() path=[1,2] used=[1,2]` → answer; back up; `place() path=[2] used=[2]` → `place() path=[2,1] used=[1,2]` → answer. Two answers.
4. `used[j] = False` after the recursive call: a number stays "taken" after its branch is finished, so later branches can't use it.
5. (a) `len(path) == len(nums)`. (b) `i == len(nums)` (every number decided). (c) `len(path) == k`.
</details>

---

## Self-check questions

1. What's the level question for include/exclude, and why can't that tree produce `[2,1,3]`?
<details><summary>Answer</summary>

"Is `nums[i]` in?", visiting `i` in index order. Every path adds numbers in index order, so 2 can never be added before 1.
</details>

2. What's the level question for permutations, and how many branches does level `p` have?
<details><summary>Answer</summary>

"Which unused number goes in position `p`?" There are `n - p` unused numbers, so `n - p` branches.
</details>

3. How do you check a backtracking design before writing any code?
<details><summary>Answer</summary>

Multiply the branches at each level to count the leaves, and compare with the number of answers you expect (`n!` for permutations, `2^n` for subsets).
</details>

4. Why didn't filtering by length fix your attempt?
<details><summary>Answer</summary>

A filter only removes answers. The include/exclude tree has exactly one full-length leaf, `[1,2,3]`; the other orderings are never built.
</details>

5. Which two changes does the un-choose step undo in the placement solution, and what goes wrong if you forget one?
<details><summary>Answer</summary>

`path.pop()` and `used[j] = False`. Without the second, the number stays marked as used after its branch ends, so later branches can't use it and answers go missing.
</details>

6. Derive the base case for placement.
<details><summary>Answer</summary>

An answer is complete when every position `0 … n-1` is filled, which is when the next position, `len(path)`, equals `n`.
</details>

7. What's the first thing to check in any recursive helper you copied from another one?
<details><summary>Answer</summary>

That every recursive call names the helper itself (not the one it was copied from).
</details>

---

## Sources

- Problems: LeetCode 46, 78, 77, 47, 39, 17. Statements paraphrased; examples and constraints from long-standing problem pages (from my own knowledge, not re-fetched; 2026-11-06).
- Python: `itertools.permutations` and `itertools.combinations` (https://docs.python.org/3/library/itertools.html), used only as test references.
- Verification (2026-11-06): your `bt`/`bt2` run as written on `[1,2,3]` and compared with the Subsets answer on 500 random inputs (identical every time). Both solutions in §8 matched `itertools.permutations` on 500 random inputs of length 1–6. All call trees were printed by running the code.
