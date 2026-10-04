# Lecture 002: Recursion That Returns Answers: State, Contracts, Base Cases, and Memoization

> **For:** Timothy · **Date:** 2026-10-04
> **Built from:** your own attempts in `lectures/leetcode/001_practice_medium.py`: LCS (5 attempts), Uncrossed Lines, House Robber (2), Decode Ways (2), Word Search, and Sum Root to Leaf. Every claim about what your code did comes from running it.
> **Prerequisites:** none. §4 connects to the closed vs half-open idea from `001-matrix_and_simulation_problems.md` §4, but it re-explains what it needs.
> **Why this lecture:** your profile (`private/001-leetcode_profile_and_assessment.md`) found that **100% of your DP-family failures share one root cause**: the answer is carried *down* through parameters instead of being *returned up*. You described the confusion yourself: *"I know intellectually that the definition of state means that it fully describes the system. But I absolutely don't have an intuitive understanding for that."* This lecture is aimed at that sentence.
> **Verification:** every solution here was tested against brute force on hundreds of random inputs. Uncrossed Lines with memoization runs n=500 in 0.21 s; your version took 5.4 s at n=12.

---

## Core ideas (the answer key)

1. **There are two kinds of recursive function.** *Answer-up* returns the answer to a subproblem (for counting and optimizing). *Accumulate-down* builds a partial solution in parameters or shared state (for listing all solutions). Your DP bugs came from using the second kind on problems that need the first.
2. **State = the smallest set of values that decides the answer to the remaining problem.** The answer itself is *not* state. It's the function's **return value**. ("Three variables but state only has two": the third one is the output.)
3. **Write the Contract Sentence before any code:** `f(i) = <the answer> for <the remaining problem described by i>`. Example: "`f(i)` = the most money from houses `nums[i:]`."
4. **The memo test:** if two calls with the same arguments could return different values, your parameters are wrong. Memoization only works on functions that pass this test.
5. **Inside `f`, assume `f` already works on smaller subproblems.** Your only job is: list the choices at this step, ask `f` for the answer to the subproblem each choice leaves, and combine (`max`, `min`, `+`).
6. **An index usually means "everything before here is done; the remaining problem is `s[i:]`."** So `i == len(s)` means *empty remaining problem*. That's not "out of bounds", it's the base case.
7. **The base case returns the answer for the empty problem:** ways to do nothing = **1**, best sum of nothing = **0**, longest common subsequence of an empty string = **0**.
8. **With two sequences, the state is two indices, `(i, j)`.** When the characters don't match you don't have to *decide* which index to move. You **try both** and take the better one.
9. **Backtracking (listing all solutions) needs choose → explore → un-choose.** Forgetting the un-choose leaves cells blocked for other branches. Your Word Search had this bug, with a concrete failing board in §7.
10. **To check recursive code, trace the call tree with each call's return value written next to it.** Answers flowing up become visible, and so do bugs.

---

## Table of Contents

- [0. Direct answers to the questions in your comments](#0-direct-answers-to-the-questions-in-your-comments)
- [1. The map: two kinds of recursive function](#1-the-map-two-kinds-of-recursive-function)
- [2. State, precisely](#2-state-precisely)
- [3. House Robber: your attempt, then the answer-up version](#3-house-robber-your-attempt-then-the-answer-up-version)
- [4. Base cases and what an index means (Decode Ways)](#4-base-cases-and-what-an-index-means-decode-ways)
- [5. Two sequences, two indices (LCS and Uncrossed Lines)](#5-two-sequences-two-indices-lcs-and-uncrossed-lines)
- [6. Memoization mechanics, and the bottom-up table](#6-memoization-mechanics-and-the-bottom-up-table)
- [7. Accumulate-down done right: backtracking (Word Search)](#7-accumulate-down-done-right-backtracking-word-search)
- [8. Choosing the family from the question](#8-choosing-the-family-from-the-question)
- [9. Tracing recursion: the call tree](#9-tracing-recursion-the-call-tree)
- [10. The recursive-function checklist](#10-the-recursive-function-checklist)
- [11. Practice ladder](#11-practice-ladder)
- [Misconceptions](#misconceptions)
- [Interview relevance](#interview-relevance)
- [Self-check questions](#self-check-questions)
- [Sources](#sources)

---

## 0. Direct answers to the questions in your comments

You left a lot of real questions in your practice file. Short answers first; the sections after this teach the *why*.

| # | Your question (paraphrased) | Short answer | Section |
|---|---|---|---|
| 1 | "What does state actually mean?" | The smallest set of values that **determines the answer to what's left**. Not everything you know, and **not the answer so far**. | §2 |
| 2 | "Three variables but my state only has two. Is that why I was confused?" | Yes, exactly. The third "variable" (the length so far, the total so far) is the **return value**, not an input. | §2 |
| 3 | "Why do we return 0 at the base case? I'm used to returning the builder variable." | Because the function returns *the answer for the remaining problem*, and when nothing remains, that answer is 0. It doesn't return "everything collected so far." | §1, §3 |
| 4 | "Why `if i == len(s): return 1`? That seems to go past my index." | `i` marks the start of what's left (`s[i:]`). `i == len(s)` means nothing is left, and there is exactly **one** way to decode an empty string: decode nothing. | §4 |
| 5 | "With two strings, do I move index 1 or index 2?" | You don't choose. You **try both** and take the max. That's what the recursion is for. | §5 |
| 6 | "Is calling `len()` in the base case bad for complexity?" | No. `len()` on a Python list or string is **O(1)**; the length is stored, not counted. | §6 |
| 7 | "Base cases: sometimes I block invalid moves at the top, sometimes I only call valid ones. Which is right?" | Both are valid styles. **Pick one per function.** Mixing them is where the confusion comes from. | §4.4 |
| 8 | "In Word Search, `visited` doesn't make sense because we explore all paths." | Correct, and an excellent observation. It's a *path* set, and a path set needs **un-choose**, which your version was missing. | §7 |
| 9 | "Why did my House Robber memo give wrong answers?" | Your function returned something that depended on `curr_total`, but the memo was keyed on `i` alone. Same key, different correct answers: the memo test fails. | §3.2 |
| 10 | "This two-structure thing is really causing problems." | Two structures just means two indices in the state. Once the Contract Sentence names both (`text1[i:]`, `text2[j:]`), they stop being confusing. | §5 |

---

## 1. The map: two kinds of recursive function

Every recursive function you've written is one of these two. Your bugs came from not knowing which one you were writing.

| | **Answer-up** | **Accumulate-down** |
|---|---|---|
| What the parameters hold | Only **where you are** in the problem (`i`, or `i, j`) | Where you are **plus the partial solution so far** (`path`, `total`, `current_choices`) |
| What it returns | **The answer to the remaining subproblem** | Usually nothing (it records solutions into an outer list), or True/False for "found one" |
| The base case returns | The answer for an **empty** problem (0, 1, True…) | Records the finished partial solution |
| Can it be memoized? | **Yes**: same arguments → same answer | **No**: the result depends on the path taken to get there |
| Use it for | **How many** ways, **max**, **min**, **is it possible**: counting and optimizing | **List all** solutions; find one valid arrangement (Word Search, subsets, permutations) |
| Your examples | House Robber #2 ✅, Decode Ways #2 ✅, LCS #5 ✅ (all after AI help) | Word Search ✅ (correct style); LCS #1, Uncrossed Lines, House Robber #1, Decode Ways #1 ❌ (wrong style for the problem) |

And there's one hybrid you already did perfectly:

| | **Context down, answer up** |
|---|---|
| Example | **Sum Root to Leaf** (09-26, correct on your first try) |
| Down | `path`: the digits from the root to here. This is *context*: the remaining problem really does depend on it, because the number at each leaf depends on the digits above it. |
| Up | The sum of the leaf numbers in this subtree. That's the *answer*. |

Look closely at why this one is legitimate. `path` is part of the **state**: two calls on the same node with different `path` values *should* return different sums. Compare that with House Robber, where two calls at the same house with different `curr_total` values have the **same** best future. The total so far doesn't change what's possible from here on. That difference is the whole of §2.

---

## 2. State, precisely

### 2.1 The definition you can actually use

> **State** = the smallest set of values such that, if you know them, **the best (or total) answer for the rest of the problem is fully determined.**

Two words in that definition do the work:

- **"rest of the problem"**: state describes what is *left*, not what has *happened*.
- **"determined"**: if two different histories lead to the same state, the answer from that point on must be the same.

### 2.2 The test: "Does the future depend on it?"

For each candidate parameter, ask: *if I change this value and keep the others fixed, does the best I can do **from here on** change?*

| Problem | Candidate | Does the future depend on it? | So… |
|---|---|---|---|
| House Robber | `i` (which house I'm at) | Yes: different houses remain | **state** |
| House Robber | `curr_total` (money robbed so far) | **No**: the houses left and the rules are identical whatever you've robbed | **not state**: it's part of the answer |
| Decode Ways | `i` | Yes | **state** |
| Decode Ways | "the previous digit" | **No**, if you design the choices to look *forward* (§4) | not state |
| LCS | `i`, `j` | Yes, both | **state** (two of them) |
| LCS | `currentLength` | No | not state |
| Sum Root to Leaf | `node` | Yes | **state** |
| Sum Root to Leaf | `path` (digits above) | **Yes**: it changes every leaf number below | **state** |

Your LCS comment, *"there are three variables… but my state only has two"*, is this table. The third variable is the **output**.

### 2.3 Where the answer goes instead: the return value

Once the answer-so-far isn't a parameter, it has to live somewhere. It lives in the **return value**, and it's built on the way *back up*:

```
accumulate-down:  f(i, total_so_far) → ... → base case returns total_so_far
answer-up:        f(i) = combine( choice_value + f(next_i) , ... )   base case returns 0 / 1
```

In answer-up, nothing is ever "so far." Each call only knows *where it is*, and trusts its recursive calls to return the answers for *what comes after*.

### 2.4 The Contract Sentence

Before any recursive code, write one line:

```python
# f(i) = <answer> for <remaining problem described by i>
```

| Problem | Contract Sentence |
|---|---|
| House Robber | `f(i)` = the most money you can rob from houses `nums[i:]` |
| Decode Ways | `f(i)` = the number of ways to decode `s[i:]` |
| LCS | `f(i, j)` = the length of the longest common subsequence of `text1[i:]` and `text2[j:]` |
| Climbing Stairs | `f(i)` = the number of ways to get from step `i` to step `n` |
| Coin Change | `f(rem)` = the fewest coins that sum to exactly `rem` (∞ if impossible) |

You suggested this yourself in your LCS notes: *"for this state, what is promised to give back to me as a result?"* That's the Contract Sentence. The sentence is the promise. Everything else follows from it:

- **Parameters** = the variables named in the "remaining problem" part.
- **Return value** = the "answer" part.
- **Base case** = the remaining problem when it's empty.
- **The top-level call** = the remaining problem when nothing is done yet: `f(0)` or `f(0, 0)`.

### 2.5 The memo test

> If I call `f` twice with the same arguments, **must** it return the same value?

If yes, you can memoize (cache by arguments). If not, something that belongs in the return value is sitting in the parameters, or something global is being mutated. That's the bug.

---

## 3. House Robber: your attempt, then the answer-up version

### 3.1 What your first attempt did

```python
def bt(i, curr_total):
    if i >= len(nums):
        return 0
    if i == len(nums)-1:
        return curr_total
    if dp[i] != -1:
        return dp[i]
    r1 = bt(i+2, curr_total+nums[i])
    r2 = bt(i+1, curr_total)
    dp[i] = max(r1, r2)
    return max(r1, r2)
```

Results from running it: `[1,2,3,1] → 2` (expected 4), `[2,7,9,3,1] → 11` (expected 12), `[5] → 0` (expected 5).

Here is the actual call trace on `[1,2,3,1]`:

```
bt(0, total=0)
    bt(2, total=1)
        bt(4, total=4) -> 0   (i >= len: total thrown away)
        bt(3, total=1) -> 1   (last house: returns total WITHOUT robbing it)
    bt(2, total=1) -> max(0,1) = 1
    bt(1, total=0)
        bt(3, total=2) -> 2   (last house: returns total WITHOUT robbing it)
        bt(2, total=0) -> 1   (memo hit, but memo[2] was computed with a different total)
    bt(1, total=0) -> max(2,1) = 2
bt(0, total=0) -> max(1,2) = 2
```

Three bugs, and **all three come from the accumulate-down style**:

| Line | What goes wrong | Why the style causes it |
|---|---|---|
| `if i >= len(nums): return 0` | The path that robbed houses 0 and 2 (total 4) reaches the end and returns **0**. The total is thrown away. | Accumulate-down's base case must return the accumulator. You wrote the answer-up base case (`0`) by habit. The two styles were mixed in one function. |
| `if i == len(nums)-1: return curr_total` | At the last house, it never considers robbing it. `[5] → 0`. | A special case added to "finish" the accumulation. It goes away in answer-up. |
| `dp[i]` keyed on `i` only | `bt(2, total=0)` reuses the value computed for `bt(2, total=1)`. | The **memo test fails**: the return value depends on `curr_total`, which isn't in the key. |

And here's the line from your comment that already contains the fix:

> *"curr_total is infinite, and curr_total is also the thing that I am trying to find, it is the number that should go INTO my dp array."*

Exactly. The thing you're trying to find goes **into the memo**, which means it's the **return value**, which means it isn't a parameter.

### 3.2 Deriving the answer-up version, step by step

**Step 1: Contract Sentence.** `f(i)` = the most money you can rob from houses `nums[i:]`.

**Step 2: The choices at house `i`.**
- **Take** house `i`: you get `nums[i]`, and you can't take `i+1`, so the rest is houses `nums[i+2:]`, which is `f(i+2)` by the contract.
- **Skip** house `i`: the rest is `nums[i+1:]`, which is `f(i+1)`.

**Step 3: Combine.** You want the most money: `f(i) = max(nums[i] + f(i+2), f(i+1))`.

**Step 4: Base case.** When is the remaining problem empty? When `i >= len(nums)` (note `i+2` can jump past the end, so use `>=`). The most money from zero houses is **0**.

**Step 5: Top-level call.** Nothing robbed yet, all houses remain: `f(0)`.

```python
from functools import cache

def rob(nums):
    # f(i) = the most money you can rob from houses nums[i:]
    @cache
    def f(i):
        if i >= len(nums):          # no houses left
            return 0
        take = nums[i] + f(i + 2)
        skip = f(i + 1)
        return max(take, skip)
    return f(0)
```

Notice what's gone: there's no `curr_total`, no special case for the last house, and no way for the memo to be wrong. `f(2)` means the same thing no matter how you got there.

### 3.3 The trace, with return values

```
f(0): take 1 + f(2)  vs  skip f(1)
    f(2): take 3 + f(4)  vs  skip f(3)
        f(4) = 0   (no houses left)
        f(3): take 1 + f(5)  vs  skip f(4)
            f(5) = 0   (no houses left)
            f(4) = 0   (no houses left)
        f(3) = max(1, 0) = 1
    f(2) = max(3, 1) = 3
    f(1): take 2 + f(3)  vs  skip f(2)
        f(3) = 1   (memo)
        f(2) = 3   (memo)
    f(1) = max(3, 3) = 3
f(0) = max(4, 3) = 4
```

Read it bottom-up. Every number is the answer to a smaller version of the problem, and each line uses only the numbers directly below it. The memo hits are *safe* now, because `f(3)` and `f(2)` mean the same thing wherever they're called from.

### 3.4 The "leap of faith", stated precisely

While writing `f(i)`, you don't think about how `f(i+2)` works. You **assume the contract holds for smaller inputs** and only check two things:

1. The base case satisfies the contract (zero houses → 0 ✓).
2. *If* `f(i+1)` and `f(i+2)` satisfy the contract, then your combination makes `f(i)` satisfy it too (best of take-or-skip ✓).

That's induction. It's also why your function can't "see" the whole problem, and doesn't need to.

---

## 4. Base cases and what an index means (Decode Ways)

### 4.1 Two meanings of `i`

| Meaning | Picture | Natural "done" condition |
|---|---|---|
| **Cursor:** "the element I'm standing on" | `s = "2 2 6"`, `i` points *at* one digit | `i == len(s) - 1` ("I'm on the last one") |
| **Boundary:** "everything before `i` is handled; what's left is `s[i:]`" | `s = "2 2 6"`, `i` sits *between* digits | `i == len(s)` ("nothing is left") |

You've been using the **cursor** meaning. Suffix-style recursion uses the **boundary** meaning. That's why `i == len(s)` looked like "going past my index" to you: under the cursor meaning it is out of bounds; under the boundary meaning it's the empty suffix `s[len(s):] == ""`.

This is the closed vs half-open idea from lecture 001 §4 in a new place. A boundary index is half-open: `s[i:]` starts *at* `i` and includes everything after, and `i` can legally equal `len(s)`.

### 4.2 The empty-problem table

The base case answers the Contract Sentence for an **empty** remaining problem:

| Kind of question | Answer for "nothing left" | Why |
|---|---|---|
| Number of ways | **1** | There is exactly one way to do nothing (the empty decoding, the empty path) |
| Max / min sum | **0** | Taking nothing gives 0 |
| Length of common subsequence | **0** | The empty string has nothing in common |
| Is it possible? | **True** | Nothing left to satisfy |
| Fewest coins for amount 0 | **0** | Zero coins |
| Fewest coins for an impossible amount | **∞** | So `min` never picks it |

The "ways = 1" row is the one Gemini handed you without explanation. If the empty suffix returned 0, *every* complete decoding would end in a 0, and every count would collapse to 0. Each full path through the choices must contribute **one** way, and the base case is where that one comes from.

### 4.3 Decode Ways, derived

**Contract:** `f(i)` = the number of ways to decode `s[i:]`.

**Choices at `i`** (looking *forward*, not back at the previous digit):
- Decode `s[i]` alone. Valid if `s[i] != "0"`. Leaves `s[i+1:]` → `f(i+1)`.
- Decode `s[i:i+2]` as a pair. Valid if `s[i] != "0"`, two characters exist, and the value is ≤ 26. Leaves `s[i+2:]` → `f(i+2)`.

**Combine:** "number of ways" → **add**.

**Base case:** `i == len(s)` → 1.

```python
from functools import cache

def numDecodings(s):
    # f(i) = number of ways to decode s[i:]
    @cache
    def f(i):
        if i == len(s):                 # empty suffix: exactly one way
            return 1
        if s[i] == "0":                 # no code starts with 0
            return 0
        ways = f(i + 1)                 # one digit
        if i + 1 < len(s) and int(s[i:i + 2]) <= 26:
            ways += f(i + 2)            # two digits
        return ways
    return f(0)
```

Your first attempt tracked `currentChoices`, the digits you'd already grouped, so you could look *back* and check "was the previous digit a 9?" That's the accumulate-down instinct again. You noticed it too: *"I am thinking that I might change the definition of state to include… But this still feels like I am not thinking about it correctly."* The fix is to make every choice **look forward**: at `i`, decide how many digits to take *starting* here. Then nothing about the past is needed, and the state is just `i`.

(Your first attempt also had two Python bugs: `currentChoices[0]` on an empty list, and `.copy().append(x)`, which returns `None` because `append` mutates and returns nothing. So the recursive call received `None`.)

### 4.4 Your guard-style question, answered

You wrote: *"In some cases I go down all possible paths and block in the base cases; other times I only traverse down those valid ones."* There are two legitimate styles:

| Style | How it looks | Good for |
|---|---|---|
| **Check at entry** | Call freely; the top of `f` rejects invalid states (`if out of bounds: return False`) | Grids (4 neighbors, most invalid), Word Search |
| **Filter before calling** | Only call `f` for valid choices (`if two-digit ≤ 26: ways += f(i+2)`) | Choices with simple validity rules: Decode Ways, Coin Change |

Rule: **pick one style per function.** If you check at entry, don't also half-filter before calling. If you filter, the base case only needs to handle the genuinely empty problem.

---

## 5. Two sequences, two indices (LCS and Uncrossed Lines)

### 5.1 What your first attempt did

```python
def traverse(t1i, t2i, currentLength):
    if t2i >= lenText2:
        return currentLength
    if text2[t2i] != text1[t1i]:
        return traverse(t1i, t2i+1, currentLength)
    return traverse(t1i, t2i+1, currentLength+1)
```

It returns about 1 for everything (`"abcde","ace" → 1`). On a match it advances `t2i` but **never `t1i`**, so `text1[t1i]` stays fixed and the function counts how often that *one* character appears in `text2`. The outer `for index in range(len(text1))` tries different starting characters, but each call still only ever matches one.

The underlying issue is that you didn't have a sentence for "what does `traverse(t1i, t2i)` represent?" Without it, there's no way to decide what a match should do to each index.

### 5.2 The contract makes the moves obvious

**Contract:** `f(i, j)` = the length of the LCS of `text1[i:]` and `text2[j:]`.

Now ask what's true about the two first characters, `text1[i]` and `text2[j]`:

- **They match.** Use them. The rest is `text1[i+1:]` and `text2[j+1:]`, so the answer is `1 + f(i+1, j+1)`. *Both* indices move, because both characters are used up.
- **They don't match.** At least one of them isn't in the LCS. You don't know which, so **try both**: drop `text1[i]` → `f(i+1, j)`, or drop `text2[j]` → `f(i, j+1)`. Take the max.

You found this yourself while annotating: *"the answer is that I actually try both!"* That's the general rule: **when you don't know which choice is right, the recursion tries all of them and combines.** The memo is what makes trying everything affordable.

**Base case:** either suffix empty → 0.

```python
from functools import cache

def longestCommonSubsequence(text1, text2):
    # f(i, j) = length of the LCS of text1[i:] and text2[j:]
    @cache
    def f(i, j):
        if i == len(text1) or j == len(text2):
            return 0
        if text1[i] == text2[j]:
            return 1 + f(i + 1, j + 1)
        return max(f(i + 1, j), f(i, j + 1))
    return f(0, 0)
```

Why it's safe to *always* take a match (your attempt-1 comment asked "is there any advantage to not including it?"): if `text1[i] == text2[j]`, any common subsequence that skips one of them can be rewritten to use this pair instead, without getting shorter. So the match branch alone is optimal. Your instinct was correct.

### 5.3 Your memoized attempt (#4): two bugs, and why the comments didn't catch them

```python
if answer_pad[i][j] != -1:
    return answer_pad[i][j]
# They match: ... move the index on both
return 1 + recurse(i+1, j+1)
# They don't match: ...
return max(recurse(i+1, j), recurse(i, j+1))
```

1. The comment says "They match:", but the code **never checks** `text1[i] == text2[j]`. It returns `1 + …` unconditionally, so `"abc","def" → 3`.
2. Nothing is ever **written** into `answer_pad`, so the memo is always -1 and does nothing.

Both are **end-of-step omissions**: the check you described but didn't write, and the store you planned but didn't do. That's the same pattern as the missing `return True` in Course Schedule and the missing un-choose in Word Search. §10 is a checklist for exactly this.

### 5.4 Uncrossed Lines: the transfer test

You tried 1035 to see whether LCS had transferred. Excellent instinct. Your version:

```python
def bt(i1, i2, current_answer):
    ...
    if nums1[i1] == nums2[i2]:
        return max(bt(i1+1, i2+1, current_answer+1), bt(i1+1, i2, current_answer), bt(i1, i2+1, current_answer))
    return max(bt(i1+1, i2, current_answer), bt(i1, i2+1, current_answer))
```

It gives correct answers, but it's **exponential**: 0.01 s at n=8, 0.3 s at n=10, **5.4 s at n=12**. LeetCode allows n=500. It can't be memoized, because `current_answer` is a parameter (memo test fails).

This was a week after you carefully annotated the answer-up LCS solution. That's important evidence about how *you* learn: **annotating a solution taught you to recognize it, not to produce it.** Under fresh conditions, the default style came back.

The answer-up version is *the same code as LCS*. "Uncrossed lines" is LCS on arrays: a line connects equal values, and uncrossed means the matched pairs appear in the same order in both arrays, which is the definition of a common subsequence.

```python
from functools import cache

def maxUncrossedLines(nums1, nums2):
    # f(i, j) = max uncrossed lines between nums1[i:] and nums2[j:]
    @cache
    def f(i, j):
        if i == len(nums1) or j == len(nums2):
            return 0
        if nums1[i] == nums2[j]:
            return 1 + f(i + 1, j + 1)
        return max(f(i + 1, j), f(i, j + 1))
    return f(0, 0)
```

n=500 runs in 0.21 s. The state space is at most 501 × 501 ≈ 250k pairs, each computed once.

---

## 6. Memoization mechanics, and the bottom-up table

### 6.1 Three ways to memoize in Python

| Way | Code | Notes |
|---|---|---|
| `@cache` | `from functools import cache` then `@cache` above `def f(...)` | The simplest. Arguments must be hashable (ints, strings, tuples, not lists). Available on LeetCode (Python 3.9+) |
| `@lru_cache(None)` | `from functools import lru_cache` | Same thing; older spelling |
| Manual list/dict | `memo = {}`, then `if key in memo: return memo[key]` … `memo[key] = ans; return ans` | What interviewers sometimes ask for. Every return path must store first (your LCS #4 bug) |

The manual pattern, written so the store can't be forgotten:

```python
memo = {}
def f(i):
    if i >= len(nums):
        return 0
    if i in memo:
        return memo[i]
    ans = max(nums[i] + f(i + 2), f(i + 1))   # compute into ONE variable
    memo[i] = ans                              # store
    return ans                                 # return what you stored
```

**Rule: compute into `ans`, store, return `ans`.** Never `return` an expression directly in a memoized function, because that's how the store gets skipped.

Your `-1` sentinel works for House Robber (answers are never negative), but a dict avoids needing a sentinel at all. Your `[[-1 for j in …] for i in …]` comprehension was correct, too.

### 6.2 Your `len()` question

> *"Is it actually a problem to do len here? … it seems like this would increase the time complexity."*

No. Python lists and strings store their length, so `len(x)` is **O(1)**. (In C, `strlen` walks the string, which may be where the worry came from.) Calling it in every base-case check is fine.

### 6.3 Complexity of a memoized recursion

> **Time = (number of distinct states) × (work per state, not counting recursive calls).**

| Problem | States | Work each | Total |
|---|---|---|---|
| House Robber | n | O(1) | O(n) |
| Decode Ways | n + 1 | O(1) | O(n) |
| LCS / Uncrossed Lines | (m+1)(n+1) | O(1) | O(mn) |
| Coin Change | amount + 1 | O(#coins) | O(amount · #coins) |

Do this one-line calculation before coding and compare it with the constraints. For Uncrossed Lines without a memo, the state count is unbounded (paths, not states), which is how the exponential blow-up shows up.

### 6.4 Recursion limit

Python's default recursion depth is about 1000. LCS on two 1000-character strings recurses about 2000 deep. On LeetCode, either add `import sys; sys.setrecursionlimit(10**5)`, or convert to a table (next section). Say this out loud in an interview. It shows you know the language's limits.

### 6.5 The same contract, as a table (bottom-up)

The memoized function fills in `f(i)` for every `i`, in whatever order the recursion reaches them. A table fills the same values **in an order where the dependencies are always ready**. `f(i)` needs `f(i+1)` and `f(i+2)`, so fill from the end backwards:

```python
def rob(nums):
    n = len(nums)
    dp = [0] * (n + 2)                 # dp[i] = f(i); dp[n] and dp[n+1] = 0 (base cases)
    for i in range(n - 1, -1, -1):     # i = n-1 → 0, step -1
        dp[i] = max(nums[i] + dp[i + 2], dp[i + 1])
    return dp[0]
```

```python
def longestCommonSubsequence(text1, text2):
    m, n = len(text1), len(text2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]   # dp[i][j] = f(i, j); row m / col n = base case 0
    for i in range(m - 1, -1, -1):
        for j in range(n - 1, -1, -1):
            if text1[i] == text2[j]:
                dp[i][j] = 1 + dp[i + 1][j + 1]
            else:
                dp[i][j] = max(dp[i + 1][j], dp[i][j + 1])
    return dp[0][0]
```

The `+1` / `+2` padding gives the base cases real cells (the half-open convention on purpose, as in lecture 001 §6.5). The backward `range(n - 1, -1, -1)` is `range(first, last + step, step)` from lecture 001 Addendum A.3: first = n-1, last = 0, step = -1.

**Recommendation:** always write the memoized recursion first. It comes straight from the Contract Sentence. Convert to a table only if asked, or if recursion depth is a problem. The table is a mechanical rewrite of the same recurrence.

---

## 7. Accumulate-down done right: backtracking (Word Search)

Accumulate-down isn't wrong. It's the right tool for **listing or finding arrangements**, where the path itself is the thing you care about. Word Search is one: you need to know which cells are already used *on this path*.

### 7.1 Your attempt, and the bug that's still in it

After adding the letter check, you reported it passed. I ran your fixed version against brute force on 3,000 random boards: **11 false negatives.** Here's the smallest failing case:

```
board = a a a        word = "baaaa"
        a b a
```

A valid path exists: start at `b` (1,1) → left (1,0) → up (0,0) → right (0,1) → right (0,2). Your code returns **False**.

Why: your search tries **up** first from `b`, wanders through `(0,1), (0,2), (1,2), (0,0), (1,0)`, fails, and backs out. But it **never removes those cells from `path`**. When the search later tries going left from `b`, every cell it needs is still marked as used by the dead branch.

### 7.2 The skeleton: choose → explore → un-choose

```python
def exist(board, word):
    rows, cols = len(board), len(board[0])
    path = set()
    def dfs(r, c, k):                          # can word[k:] be matched starting at (r, c)?
        if not (0 <= r < rows and 0 <= c < cols):
            return False
        if (r, c) in path or board[r][c] != word[k]:
            return False
        if k == len(word) - 1:
            return True
        path.add((r, c))                       # choose
        for dr, dc in ((-1, 0), (1, 0), (0, 1), (0, -1)):
            if dfs(r + dr, c + dc, k + 1):     # explore
                return True
        path.remove((r, c))                    # un-choose
        return False
    return any(dfs(r, c, 0) for r in range(rows) for c in range(cols))
```

The invariant: **when `dfs` returns False, `path` is exactly what it was before the call.** Every `add` is matched by a `remove` on the way out. That's what makes the set mean "cells on the *current* path" instead of "cells ever touched."

(Returning True early without removing is fine. The whole search is over at that point.)

Your note *"visited does not make as much sense… we are going over all possible paths"* was the right insight. The un-choose step is what turns `visited` (cells ever seen, for single traversals like BFS) into `path` (cells on the current branch, for exploring all paths).

### 7.3 The general backtracking template (78. Subsets)

```python
def subsets(nums):
    out, cur = [], []
    def dfs(i):                     # decide nums[i:], with cur holding the choices so far
        if i == len(nums):
            out.append(cur[:])      # record a COPY: cur keeps changing
            return
        cur.append(nums[i])         # choose: include nums[i]
        dfs(i + 1)                  # explore
        cur.pop()                   # un-choose
        dfs(i + 1)                  # explore: exclude nums[i]
    dfs(0)
    return out
```

Same three beats. Note `cur[:]`: appending `cur` itself would record a reference to a list that keeps changing.

### 7.4 Side by side

| | Answer-up (DP) | Accumulate-down (backtracking) |
|---|---|---|
| Question | how many / best / possible | list all / find an arrangement |
| Parameters | position only | position + partial solution (or a shared `path`) |
| Returns | answer for the rest | nothing (records into `out`), or True/False |
| Base case | answer for empty problem | record the complete solution |
| Must have | memo (for speed) | **un-choose** (for correctness) |
| Typical cost | states × work | exponential (number of solutions) |

---

## 8. Choosing the family from the question

You already reason about this explicitly ("not greedy because my decision limits future options"), which is good. The missing piece is the last split:

| The problem asks… | Family | Function style |
|---|---|---|
| **List / return all** combinations, subsets, paths | Backtracking | Accumulate-down + un-choose |
| **Does an arrangement exist** where the path matters (Word Search, N-Queens) | Backtracking | Accumulate-down, return True on first success |
| **How many** ways | DP | Answer-up, combine with `+` |
| **Max / min / longest / fewest** | DP (unless greedy is provably optimal) | Answer-up, combine with `max` / `min` |
| **Can you reach / is it possible** (Word Break, Jump Game) | DP or greedy | Answer-up, combine with `or` / `any` |

**Decode Ways asks "how many," so it's DP, not backtracking.** Your reasoning ("my decision limits my future options") correctly ruled out greedy. The extra question to ask is *"do they want the list, or a number?"* A number with overlapping subproblems means DP.

A quick overlap check: draw two levels of the call tree for a small input. If the same call (like `f(3)`) shows up twice, there's overlap, and a memo will pay off. The House Robber trace in §3.3 has two memo hits in a 4-element input.

---

## 9. Tracing recursion: the call tree

The side-level trace table from lecture 001 Addendum A.5 is for loops. For recursion, trace the **call tree**: one line per call, indented by depth, with the **return value** written when the call finishes.

```
f(0) on '226'
    f(1) on '26'
        f(2) on '6'
            f(3) = 1   (empty suffix: one way)
        f(2) = 1
        f(3) = 1   (empty suffix: one way)
    f(1) = 2
    f(2) on '6'
        f(3) = 1   (empty suffix: one way)
    f(2) = 1
f(0) = 3
```

How to do it fast, on paper:

1. **Pick a tiny input that exercises every branch.** For Decode Ways: `"226"` (both branches) and `"106"` (a zero). Two or three elements is plenty.
2. **Write the call, then its children, indented.** Don't expand a call you've already finished. Write `(memo)` and reuse the number.
3. **Write each return value as soon as it's known,** and check it against the Contract Sentence: "is 2 really the number of ways to decode `'26'`?" (Yes: `2,6` and `26`.) **That check is the whole point.** Each line can be verified on its own.
4. **The first line whose value contradicts the contract is the bug.**

Your House Robber #1 trace (§3.1) is a good example of step 4. The line `bt(4, total=4) -> 0` contradicts the intent (we robbed 4 and got 0 back). It's the first wrong line, and it points straight at the base case.

Time budget: a 3-element call tree takes about 2–3 minutes. Much faster than tracing loops, because each line is checked against one sentence.

---

## 10. The recursive-function checklist

Run it before tracing. About 30 seconds.

```
BEFORE CODING
  □ Family: list-all (backtracking) or count/optimize (DP)?            (§8)
  □ Contract Sentence: f(...) = <answer> for <remaining problem>        (§2.4)
  □ Every parameter passes "does the future depend on it?"              (§2.2)
  □ Index meaning: boundary (s[i:]), so empty is i == len               (§4.1)
  □ Base case = answer for the EMPTY problem                            (§4.2)
  □ Complexity: states × work vs constraints                            (§6.3)

AFTER CODING (closing steps: where your bugs live)
  □ Every branch is CHECKED, not just commented ("They match:" → if …)  (§5.3)
  □ Every path out of the function returns the right type
  □ Memo: compute into ans → store → return ans                         (§6.1)
  □ Backtracking: every choose has an un-choose                         (§7.2)
  □ Recorded solutions are copies (cur[:])                              (§7.3)
  □ Mutating calls aren't used as values (.append/.sort return None)    (§4.3)

THEN
  □ Call-tree trace on a tiny input; check each return value against the contract  (§9)
```

---

## 11. Practice ladder

Use these in "gradient" order: each day, take the next problem that targets the weakness that's currently most expensive. Redos of failed problems count *more* than new ones. A problem counts as solved only after a **blank-page redo 3+ days later passes**, with no AI and no notes.

| Order | Problem | What it trains | Notes |
|---|---|---|---|
| 1 | 70 Climbing Stairs | Contract Sentence + "ways" base case = 1 | Should take 10 minutes. Write the contract first |
| 2 | 746 Min Cost Climbing Stairs | `min` combine; base case 0 | |
| 3 | **198 House Robber (redo, blank page)** | Take/skip, no accumulator | Compare with your attempt #1 afterwards |
| 4 | **91 Decode Ways (redo, blank page)** | `i == len` → 1, forward-looking choices | Trace `"226"` and `"106"` |
| 5 | 322 Coin Change | Answer for impossible = ∞; loop over choices | |
| 6 | 139 Word Break | `or` combine (possible?) | |
| 7 | 62 Unique Paths | Two-index state on a grid | |
| 8 | **1143 LCS (redo, blank page)** | Two sequences, "try both" | No annotation, no looking |
| 9 | **1035 Uncrossed Lines (redo)** | Recognizing it's LCS | Measure: should pass n=500 |
| 10 | 78 Subsets → 46 Permutations | choose → explore → un-choose | Backtracking on purpose |
| 11 | **79 Word Search (redo)** | Un-choose on a grid | Test the `"baaaa"` board above |
| 12 | 213 House Robber II, 300 LIS | Transfer | Only after 1–9 are clean |

Before each: Contract Sentence written as the first comment. After each: log the result and any R-codes in `private/000-weakness_tracker.md`.

---

## Misconceptions

| You thought | Reality | Why it matters |
|---|---|---|
| "State fully describes the system, so it includes the total so far." | State describes **the remaining problem**. The total is the *answer* and belongs in the return value. | Totals in parameters break memoization and turn O(n) into O(2ⁿ). |
| "Recursive functions return a builder variable at the base case." | That's accumulate-down, the right tool only for *listing* solutions. Counting and optimizing return the answer for the *rest* of the problem. | Mixing the two put `return 0` in an accumulator function (House Robber #1). |
| "`i == len(s)` is out of bounds." | With the boundary meaning, it's the empty suffix, a valid state, and the base case. | It's why "ways" base cases return 1. |
| "With two strings I have to decide which index to move." | Try both; take the max. | This is the core of every two-sequence DP (LCS, Edit Distance, …). |
| "A comment describing the branch is enough." | Comments don't run. LCS #4 described a match check and never performed it. | Read code and comments together in the closing checklist. |
| "If the visited set worked for BFS, it works for path search." | BFS `visited` = ever seen. Path search needs **un-choose**, so the set is the current branch only. | Without it: false negatives (the `"baaaa"` board). |
| "Annotating a correct solution means I've learned it." | It builds recognition. Uncrossed Lines a week later reverted to the old style. | Learn by blank-page redo 3+ days later. |
| "`len()` in the base case costs O(n)." | O(1) in Python. | Don't contort code to avoid it. |

---

## Interview relevance

- **1-D and 2-D DP are a large share of medium questions** (Robber, Decode Ways, Coin Change, Word Break, LCS, Unique Paths, LIS). They're all the same move: Contract Sentence → choices → combine → base case.
- **Say the Contract Sentence out loud.** "Let `f(i)` be the most money from houses `i` onward." It's the single most convincing thing you can say in a DP interview, because it shows you're reasoning from a definition, not a memorized solution.
- **Order of presentation interviewers like:** brute-force recursion with the contract → "the same `(i)` is computed many times" → add `@cache` → state the complexity as states × work → optionally convert to a table and mention the recursion limit.
- **Backtracking questions** (Subsets, Permutations, Word Search, Combination Sum) check whether you un-choose and whether you copy results (`cur[:]`). Name both.
- **No AI and no judge in the room.** The call-tree trace (§9) is how you show the interviewer it works before they run it.

---

## Self-check questions

1. Write the Contract Sentence for House Robber. Which parameter from your first attempt fails the "does the future depend on it?" test?
<details><summary>Answer</summary>

`f(i)` = the most money from houses `nums[i:]`. `curr_total` fails: the houses left and the rules are the same whatever you've already robbed, so the best future doesn't depend on it.
</details>

2. Why can't you memoize `bt(i, curr_total)` on `i` alone?
<details><summary>Answer</summary>

Its return value depends on `curr_total`, so two calls with the same `i` but different totals should return different values, but the memo returns whichever was stored first. The memo test fails.
</details>

3. In Decode Ways, what does `i == len(s)` mean, and why return 1?
<details><summary>Answer</summary>

The remaining suffix `s[i:]` is empty. There's exactly one way to decode an empty string (decode nothing). Each complete decoding path ends there and contributes 1 to the count.
</details>

4. Base case values: max-sum of nothing? number of ways to do nothing? fewest coins for an impossible amount?
<details><summary>Answer</summary>

0; 1; ∞ (so `min` never chooses it, then convert to -1 at the top level).
</details>

5. LCS: when `text1[i] != text2[j]`, which index moves?
<details><summary>Answer</summary>

You try both: `max(f(i+1, j), f(i, j+1))`. You don't know which character is unused, so the recursion explores both possibilities.
</details>

6. Why is Uncrossed Lines the same problem as LCS?
<details><summary>Answer</summary>

A line joins equal values; lines not crossing means the matched pairs appear in the same relative order in both arrays. A set of equal pairs in the same order in both is exactly a common subsequence.
</details>

7. What's the time complexity of memoized LCS, and why?
<details><summary>Answer</summary>

O(m·n): (m+1)(n+1) distinct states `(i, j)`, O(1) work each.
</details>

8. In the manual memo pattern, why "compute into `ans`, store, return `ans`"?
<details><summary>Answer</summary>

So there's no return path that skips the store. LCS #4 returned expressions directly and never wrote the memo.
</details>

9. In Word Search, what invariant does `path.remove((r, c))` protect?
<details><summary>Answer</summary>

When `dfs` returns False, `path` is unchanged from before the call, so `path` always means "cells on the current branch." Without it, dead branches leave cells blocked for later branches (the `"baaaa"` false negative).
</details>

10. Subsets: why `out.append(cur[:])` and not `out.append(cur)`?
<details><summary>Answer</summary>

`cur` is one list that keeps changing. Appending it stores a reference, so every recorded "subset" would end up as the same (finally empty) list. `cur[:]` stores a snapshot.
</details>

11. "Return the number of distinct ways to climb n stairs taking 1 or 2 steps." Backtracking or DP? Contract Sentence?
<details><summary>Answer</summary>

DP (a count, with overlapping subproblems). `f(i)` = the number of ways to get from step `i` to step `n`. `f(n) = 1`, `f(i > n) = 0`, `f(i) = f(i+1) + f(i+2)`.
</details>

12. You're tracing a call tree and see `f(2) = 1` for Decode Ways on `"226"`. How do you check that line by itself?
<details><summary>Answer</summary>

Use the contract: `f(2)` = ways to decode `s[2:] = "6"`. There's one way (`6`). ✓. Each line is checked against the sentence, without re-tracing anything above it.
</details>

---

## Sources

- LeetCode problems referenced: 70, 746, 198, 213, 91, 322, 139, 62, 300, 1143, 1035, 78, 46, 79, 129. Problem numbers from long-standing LeetCode listings (from my own knowledge, not re-fetched; 2026-10-04).
- Python docs: `functools.cache` (3.9+) https://docs.python.org/3/library/functools.html#functools.cache ; `sys.setrecursionlimit` https://docs.python.org/3/library/sys.html#sys.setrecursionlimit ; `len()` is O(1) for built-in sequences (CPython stores `ob_size`), see https://wiki.python.org/moin/TimeComplexity
- Verification (2026-10-04): every solution in this lecture was tested against brute force on 400 random inputs per problem; Word Search on exhaustive small boards; memoized Uncrossed Lines timed at n=500 (0.21 s). Your attempts were executed as written; outputs quoted in §3.1, §5.1, §5.3, §5.4, §7.1.
- Companions: `001-matrix_and_simulation_problems.md` (closed vs half-open §4; range formula, Addendum A.3; trace tables, Addendum A.5); `private/001-leetcode_profile_and_assessment.md` (R1, R2, R4, R6).
