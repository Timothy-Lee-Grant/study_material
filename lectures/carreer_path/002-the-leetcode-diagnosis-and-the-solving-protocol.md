# Lecture 002 — The LeetCode Diagnosis, and the Protocol That Fixes It

> **For:** Timothy Lee Grant · **Date:** 2026-07-26
> **Evidence base:** every line of `LEARNING/dsa/6_baseline_assessment.py` (654 lines, 7 problems,
> 15 attempts), `7_baseline_assessment.py` (Basic Calculator, July 2), `001_practice.py`
> (Birthday Chocolate, today), plus `skill_tracker.md`, `problem_log.md`, `patterns_and_pitfalls.md`.
> **I ran your code.** Every claim below about a bug is a verified execution, not a guess.
>
> **Read time:** ~60 min. **This is the most important document in the repo right now**, because
> coding is the gate and your practice files contain a *very specific, very fixable* pattern.

---

## 0. The headline, before anything else

**You do not have an algorithms problem. You have a verification problem.**

Your self-rating says 30% on mediums, and you've built a story around "I'm not good at LeetCode."
Your files say something completely different, and I can prove it:

| Problem | What actually happened |
|---|---|
| **Reorder List** (medium) | You decomposed it correctly — split, reverse, merge — **unaided, in 28 minutes, first try.** You failed only because you couldn't execute "reverse a linked list." Strategy: perfect. Primitive: missing. |
| **Merge Intervals** (medium) | Attempt 2 was **one `max()` call away from accepted.** You had sort + stack sweep + the right collision condition. |
| **Basic Calculator** (**HARD**, LC 224) | You derived the save-state-on-`(`, restore-on-`)` model **from first principles**, and independently noticed it's the same shape as a function call frame. That is a real insight. It fails on one wrong initial value. |
| **Group Anagrams** (medium) | Correct algorithm on attempt #1. Three attempts were spent entirely on Python return types. |
| **Longest Substring** (medium) | Solved unaided. One Python API lookup (`del` vs `.remove`). |
| **3Sum** (medium) | Failed — but for a reason you never diagnosed, and it isn't "I don't understand two pointers." |

A person who cannot do mediums does not derive a solution to LC 224 from scratch. **The 30% number
is measuring your last mile, not your ability.**

So this lecture is not "here are more algorithms." It's: *here is the precise mechanism by which
correct thinking is turning into wrong code, and here is the protocol that closes the gap.*

---

## 1. Forensics — what actually broke, with receipts

I ran each of these. The outputs below are real.

### 1.1 3Sum — the bug you never looked at

Your `p2` initialization, in **all four attempts**:

```python
while p1 <= (lenArray - 1) - 2:
    p2 = 1                     # ← this is the bug. It should be p1 + 1.
    p3 = lenArray - 1
```

Here's the actual trace on `[-1,0,1,2,-1,-4]`:

```
sorted: [-4, -1, -1, 0, 1, 2]
  p1=0(-4) p2=1(-1) p3=5(2)  sum=-3
  ...
  p1=1(-1) p2=1(-1) p3=5(2)  sum=0     ← p2 == p1. The SAME element used twice.
```

You know the correct relationship — you write `p2 = p1 + 1` *inside* the loop after a hit. You just
never wrote it at setup. **The invariant "p2 and p3 scan strictly to the right of p1" was never
established at initialization.**

And there's a second, worse bug you also never found. Your code **infinite-loops**:

```
   -> HIT, dedup moved p1 to 1
  p1=1 p2=2 p3=5 sum=0
   -> HIT, dedup moved p1 to 1     (forever — 21 identical triplets and counting)
```

Because after a match you *reset* `p2 = p1+1, p3 = len-1` instead of *shrinking* the range. The
search space never gets smaller, so the loop never ends. Nothing in your process asks
**"does every branch of this loop make progress?"** — so nothing caught it.

Also: your dedup condition is inverted (`nums[p1] != nums[p1+1]` advances while values *differ*;
you want to skip while they're the *same*), and `myset = set` in attempt 1 is the class, not an
instance.

Four attempts, thirty minutes, and the fix is `p2 = p1 + 1` plus `lo += 1; hi -= 1` after a hit.

### 1.2 Basic Calculator — a HARD you solved, broken by one initial value

Your July 2 solution:

```python
prev_total = 0
prev_operator = -1        # ← should be +1
```

I ran it:

```
calc('1 + 1')               = 0   expected 2
calc('2-1 + 2')             = -1  expected 3
calc('(1+(4+5+2)-3)+(6+8)') = 3   expected 23
```

The very first number gets negated, and the same wrong reset happens inside every `(`. **The
algorithm is right. The engine is right. It starts in the wrong state.** Change two `-1`s to `1`
and this is an accepted solution to a LeetCode Hard.

Sit with that for a second. You have been telling yourself you're at 30% on *mediums*.

### 1.3 Merge Intervals — one function call away

Your attempt 2 (after a concept-only hint, no code):

```python
new_merged_element = [last_start, intervals[i][1]]
```

should be:

```python
new_merged_element = [last_start, max(last_stop, intervals[i][1])]
```

Fails on a **nested** interval: `[[1,10],[2,3]]` → you return `[[1,3]]`, losing the tail.

Now the part that matters. You *wrote this down at the time*:

> *"I think it is guaranteed that the current index of investigation will have the later stop time.
> So I will do that as a way to purposefully test my understanding."*

You **identified the exact uncertainty, named it, chose not to test it, and shipped the guess.**
Ten seconds with `[[1,10],[2,3]]` on paper resolves it. This is the single most expensive habit in
your entire practice file, and I'll come back to it in §3.3.

### 1.4 Birthday Chocolate (today) — two bugs, one of them silent

```python
windowSum += s[i]
windowSum -+ s[i-(m-1)]        # ← "-+" not "-=". Python computes it and throws it away.
```

`windowSum -+ x` is a legal expression statement. **No error. No warning. It just does nothing.**
And the slide itself is off by one: at `i = m-1` the window is already `s[0..m-1]`, so `s[i]` is
*already inside* the window — you're adding an element you already have.

I ran it: `birthday([1,2,1,3,2], 3, 2)` → **1**, expected **2**.

Same structural signature as 3Sum: **the window is built correctly, then the transition is set up
wrong at the boundary between "initialize" and "iterate."**

### 1.5 Reorder List — the one that proves the diagnosis

- **Attempt 1 (timed, 28:54):** correct decomposition immediately. Then: *"while # I have no idea
  about how I would actually go about reversing a linked list."* Stopped. **Blocked by a missing
  primitive, not missing strategy.**
- **Attempt 2:** `while curr.next` (should be `while curr`), and `future = future.next` before a
  null check. You literally wrote `# will this be a null exception???` — and then moved on
  without checking. Same habit as §1.3.
- **Attempt 3 (June 26, untimed, deliberate):** clean, correct, and the comments contain this:

  > *"I think it might be helpful for me to ask myself 'what should the end state of each pass of
  > this loop be?'... actually `future` should not be a variable set up before my loop starts...
  > Notice: this means my block above for `if not head2` would not be needed!"*

**Timothy — you independently derived loop-invariant reasoning, and used it to discover that
correct initialization removes the need for a defensive special case.** That is the exact cure for
every bug in §1.1–1.4. You found the medicine on June 26 and then didn't take it on July 2 or
July 26.

That's the whole lecture in one sentence. Everything below is about turning that one-time insight
into a permanent, automatic ritual.

### 1.6 Group Anagrams & Longest Substring — the friction tax

Group Anagrams: 3 attempts, 12:54 — `sorted()` returns an unhashable list; `dict_values` isn't a
`list`. Longest Substring: `checker.remove` instead of `del checker[k]`. **Zero algorithmic error
across both.** This is a vocabulary tax, and it's the cheapest thing on this list to eliminate
(§8.4).

---

## 2. The scoreboard, re-scored

Here's your baseline rescored by *cause* instead of by pass/fail:

| Problem | Algorithm correct? | Failed on |
|---|---|---|
| Group Anagrams | ✅ attempt 1 | Python types |
| Longest Substring | ✅ | Python API |
| Reorder List | ✅ strategy | missing primitive (reverse/merge) |
| 3Sum | ⚠️ right pattern | **initialization + no progress guarantee** |
| Merge Intervals | ✅ (attempt 2) | **untested assumption** (`max`) |
| Basic Calculator (HARD) | ✅ | **initialization** |
| Birthday Chocolate | ✅ | **transition off-by-one + silent typo** |

**Five of seven failures are last-mile mechanical. One was a missing primitive. Zero were "I don't
understand the algorithm."**

If you fixed nothing but initialization and verification, your medium rate goes from ~30% to
somewhere north of 70% *with no new algorithmic knowledge at all*. That is the highest-ROI fact in
this document.

---

## 3. Psychological analysis — what your brain is actually doing

I read your comments as much as your code. Your comments are unusually honest and they expose the
machinery. Six mechanisms:

### 3.1 You reason about *steady state* brilliantly and about *initial state* by vibes

Every one of your loops is correct once it's running. `curr.next = prev; prev = curr; curr = future`
is textbook. The sliding-window body is right. The calculator's fold logic is right. The 3Sum inner
comparison chain is right.

And then: `p2 = 1`. `prev_operator = -1`. `i = m - 1`. `future = curr.next` before the loop.

Why the asymmetry? Because the loop body is where your attention is — it's the interesting part,
the part you're actively reasoning about. Initialization feels like paperwork, so it gets
*intuition* instead of *derivation*. But initialization is not paperwork. **It is the loop's
precondition, and it is exactly as load-bearing as the body.** §4 is the fix.

### 3.2 You debug the symptom, not the cause

3Sum, four attempts:

- Test `[0,0,0]` failed → you changed the outer bound `<` to `<=`.
- Test `[0,0,0,0]` gave a duplicate → you added a dedup while-loop.
- Never once did you re-derive the whole thing from the invariant.

The failing tests pointed at *dedup*, so you only looked at *dedup*. The actual bug (`p2 = 1`) was
sitting in plain sight in a line the tests never pointed at. **You debug where the pain is, not
where the cause is** — and after four patches you had a mutated, tangled loop that infinite-loops.

This is patch-driven debugging, and it has a compounding cost: each patch makes the code harder to
reason about, which makes the next bug harder to find. §11 replaces it.

### 3.3 Your error *detection* is excellent and your error *handling* is missing

This is the most striking thing in the whole dataset. Direct quotes:

> *"I am going to just YOLO it and hope the default settings are such that it will take the 0th element."*
> *"So I will do that as a way to purposefully test my understanding."* (then never tested it)
> *"will this be a null exception???"* (then moved on)
> *"I notice that I keep increasing the number of edge cases... I feel that I am not on the right track."*

Your metacognition is **firing correctly every single time.** You raise the flag. And then there's
no handler — you keep going and hope.

Think of it in your own domain: you have an interrupt that fires reliably and an empty ISR.

This is genuinely great news, because the hard part — *noticing* — is the part most people can't
learn. You already have it. You just need a rule that converts a noticed doubt into a mandatory
3-second action. §6.

### 3.4 You reason verbally, not tabularly

Your comments are essays — long, articulate, well-structured prose. Some are 400 words. That is a
real strength (it's exactly what interviewers want to hear out loud), but it has a failure mode:

**You talk yourself into confidence instead of testing your way into it.**

Prose can hold a wrong belief comfortably for 300 words. A 4-column table of `i / p2 / p3 / sum`
cannot — the wrong value is just *visibly there* in row 2. Almost every bug above dies instantly to
a five-row table. §5.

### 3.5 You never sanity-check the complexity of your own idea

Merge Intervals attempt 1: a dict mapping every integer coordinate to the intervals covering it.
That's O(sum of interval lengths). Coordinates on LeetCode routinely go to 10⁵ or 10⁹. **The
approach was dead on arrival and you spent 32 minutes in it.**

You never asked "what does this cost, and does that fit the constraints?" That question takes ten
seconds and would have killed the idea before you wrote a line. §7.

### 3.6 Defensive complexity as anxiety management

> *"linked lists have so many edge cases that I always need to worry about... based on if there is
> 0 nodes, 1 node, 2 nodes, or more than 2 nodes"*

Reorder List attempt 1: you computed the length, then branched on even/odd for the midpoint. Attempt
3: fast/slow handles both, no branch. Attempt 3 also has `if not head2: return head` — which you
then realized was unnecessary once initialization was right.

**Special cases are a symptom of a weak invariant.** When you don't trust the general argument, you
armour the edges. When the invariant is right, the edges take care of themselves. That's not just a
LeetCode thing — it's the same instinct that makes production code brittle, so this is worth
internalizing beyond the interview.

### 3.7 The elephant: cadence

Your last logged DSA session before today was **June 27**. Today is **July 26**. That's a month with
one easy problem in it — during which you did resume work and work-strategy docs (both valuable, but
neither is the gate).

I'm not scolding you; I'm naming it because the plan's entire spine is "daily reps," and the spine
isn't there. **Three problems a week, forever, beats twelve problems in one heroic weekend and then
a month off.** Consistency is doing more work here than intensity, and given the wife/Seattle clock,
a month of drift is the most expensive thing in this file. §13 gives you a cadence you can actually
hold alongside a full-time job.

---

## 4. Core concept #1 — A loop is a machine with four parts

**This is the highest-ROI concept in this document. If you take one thing, take this.**

Every loop you will ever write has exactly four components. Most people only consciously design one
of them (the body). You design one and a half. Design all four, on paper, *before* you type:

| # | Part | The question it answers |
|---|---|---|
| **1. Invariant** | What is *always true* at the top of each iteration? |
| **2. Initialization** | What must I set so the invariant is true **before the first iteration**? |
| **3. Progress** | What strictly shrinks every single pass, in **every branch**? |
| **4. Termination** | When the loop exits, what does the invariant + exit condition give me? |

Correct code is: *invariant true at the start* + *body preserves it* + *guaranteed progress* ⇒
*invariant true at the end*, which is your answer. This is not academic — it's a mechanical
derivation that removes guessing from the two places you guess.

### 4.1 Applied to 3Sum

**Invariant:** `nums` is sorted; `i` is the fixed first element; `lo` and `hi` bound the *unexamined*
region **strictly to the right of `i`**; every valid triplet with first element `nums[i]` lies
within `[lo, hi]`.

Read the invariant, then derive:

- *"strictly to the right of `i`"* → **`lo = i + 1`.** Not 1. The invariant hands you the
  initialization. You don't have to guess, and you can't get it wrong.
- *"bound the unexamined region"* → after recording a hit, both ends must move **inward**:
  `lo += 1; hi -= 1`. Resetting `hi = n-1` re-expands the region, which violates progress → your
  infinite loop, derived on paper without running anything.
- **Progress check, every branch:** `lo += 1` ✅ / `hi -= 1` ✅ / hit → both move ✅. The measure
  `hi - lo` strictly decreases in all three. Loop must terminate.

The corrected version (verified — I ran it):

```python
def threeSum(nums):
    nums.sort()
    n, res = len(nums), []
    for i in range(n - 2):
        if i > 0 and nums[i] == nums[i-1]:   # dedup the FIXED element: skip repeats
            continue
        if nums[i] > 0:                       # sorted ⇒ no way to reach 0 from here
            break
        lo, hi = i + 1, n - 1                 # ← the invariant, written down
        while lo < hi:
            s = nums[i] + nums[lo] + nums[hi]
            if s < 0:    lo += 1              # too small → need a bigger number
            elif s > 0:  hi -= 1              # too big  → need a smaller number
            else:
                res.append([nums[i], nums[lo], nums[hi]])
                lo += 1; hi -= 1              # progress: BOTH move
                while lo < hi and nums[lo] == nums[lo-1]: lo += 1   # dedup
                while lo < hi and nums[hi] == nums[hi+1]: hi -= 1
    return res
```

Note the structural change: **the outer loop is a `for`, and `i` is never touched inside.** In your
version, the dedup logic mutated `p1` *and* the outer loop incremented it — two owners of one
variable. Rule: **one variable, one owner.** If two places modify a loop variable, you have a bug you
haven't found yet.

### 4.2 Applied to Basic Calculator

**Invariant at the top of each character:** `total` is the fully-resolved value of everything before
the current pending term; `sign` is the operator that will be applied to the number currently being
built; `curr` is the number built so far.

Derive the initialization: before *any* character, nothing is resolved (`total = 0`), nothing is
built (`curr = 0`), and the implicit operator in front of the first number is **`+`** (because `"5"`
means `+5`). Therefore **`sign = 1`**, not `-1`.

The invariant *tells you the answer*. You never have to feel around for it.

```python
def calculate(s):
    stack, total, sign, curr = [], 0, 1, 0
    for c in s:
        if c.isdigit():
            curr = curr * 10 + int(c)
        elif c in '+-':
            total += sign * curr                 # resolve the pending term
            curr, sign = 0, (1 if c == '+' else -1)
        elif c == '(':
            stack.append((total, sign))          # push the frame
            total, sign = 0, 1                   # same as the very start — a fresh sub-expression
        elif c == ')':
            total += sign * curr; curr = 0       # resolve inside the parens
            prev_total, prev_sign = stack.pop()
            total = prev_total + prev_sign * total
            sign = 1
    return total + sign * curr                   # flush the final pending term
```

Verified: `1 + 1` → 2, `2-1 + 2` → 3, `(1+(4+5+2)-3)+(6+8)` → 23, ` 2-(5-6) ` → 3.

**Compare it to yours.** It's your algorithm, character for character. Your insight that `(` is a
function call and the stack holds the frame — that's the whole problem, and you got it. What changed
is `sign = 1`. That's the entire delta between "I can't do mediums" and "I solved a Hard."

### 4.3 Applied to the sliding window (Birthday Chocolate)

**Invariant at the top of iteration `r`:** `ws` is exactly the sum of the window `s[r-m+1 .. r]`.

Derive both boundaries from that sentence:
- To make it true before the loop, the window must already be full → `ws = sum(s[:m])`, and the first
  window's check happens *before* any sliding.
- The step must *maintain* it: entering `s[r]`, leaving `s[r-m]`. Both, together, once.

```python
def birthday(s, d, m):
    ws = sum(s[:m])                 # invariant established for the window ending at m-1
    ways = 1 if ws == d else 0      # check the first window explicitly
    for r in range(m, len(s)):      # r = the index ENTERING the window
        ws += s[r] - s[r - m]       # one line: add entering, remove leaving
        if ws == d: ways += 1
    return ways
```

Verified: `([1,2,1,3,2],3,2)` → 2. `([1,1,1,1,1],1,1)` → 5. `([4],4,1)` → 1.

**The universal window transition, memorize it:** `ws += arr[r] - arr[r - k]` where `r` is the index
*entering*. One line, no fence-post to re-derive, ever again. Your named "fence-post" pitfall is not
a fundamental weakness — it's a missing memorized form.

### 4.4 The drill

For the next 20 problems, before you write a single line of loop body, write these four comments:

```python
# INVARIANT:  at the top of each pass, <what is always true>
# INIT:       therefore <vars> start at <values>
# PROGRESS:   <measure> strictly decreases in every branch
# TERMINATION: on exit, <condition> + invariant ⇒ <the answer>
```

It costs 60–90 seconds. It would have prevented **four of your seven failures outright.** Nothing
else in your practice has that return.

---

## 5. Core concept #2 — The 3-row trace table

You are a verbal reasoner. Verbal reasoning is where your bugs hide. The antidote is one specific,
mechanical, boring artifact: **a table**.

**The rule: before you run any code, hand-trace 3–5 elements in a table, one row per iteration, one
column per variable.** Not in your head. Not in prose. In a grid, on paper.

3Sum, first three rows, sorted `[-4,-1,-1,0,1,2]`, with your original code:

| pass | p1 | p2 | p3 | nums[p1] | nums[p2] | sanity: is p2 > p1? |
|---|---|---|---|---|---|---|
| 1 | 0 | 1 | 5 | -4 | -1 | yes |
| 2 | 1 | **1** | 5 | -1 | **-1** | **NO ← bug, visible in row 2** |

Thirty seconds. Four attempts and thirty minutes, versus thirty seconds.

**The sanity column is the trick.** Don't just record values — add a column that asserts your
invariant, and watch for the row where it goes false. That column *is* the invariant, made visible.

### 5.1 The three inputs to always trace

1. **The smallest non-trivial input** (n = 1 or 2). Catches initialization bugs — your #1 class.
2. **The all-same input** (`[0,0,0,0]`, `"aaaa"`). Catches dedup and window bugs.
3. **The nested/contained input** (`[[1,10],[2,3]]`). Catches "I assumed monotonicity" bugs — this
   is exactly what killed Merge Intervals.

Write those three on a sticky note. They are the counterexamples your specific brain doesn't
generate on its own, because you reason forward from the typical case.

### 5.2 Trace *before* you code, too

Trace the **problem**, not just your code. Merge Intervals: had you hand-traced `[[1,10],[2,3]]`
through the *problem statement* before coding, the nested case would have been on your radar as a
scenario, and `max()` would have been obvious. Your `patterns_and_pitfalls.md` already says "work a
tiny example by hand" as step 4 of the stuck-checklist. **Promote it from a recovery step to a
mandatory opening step.**

---

## 6. Core concept #3 — Doubt is a stop signal

You already generate the signal. Install the handler.

> **THE RULE: The moment you write or think "I think…", "I assume…", "I hope…", "probably",
> "I'll just YOLO it", or "does this crash?" — you STOP and spend 30 seconds resolving it. No
> exceptions. Doubt is not noise. Doubt is your subconscious having already found the bug.**

Look at the hit rate on your own flags:

| What you wrote | Was it actually a bug? |
|---|---|
| *"I'm going to just YOLO it"* (sort of list-of-lists) | No — you got lucky |
| *"I think it is guaranteed the current will have the later stop time"* | **YES — this exact line failed the problem** |
| *"will this be a null exception???"* | **YES** |
| *"I have no idea about how I would reverse a linked list"* | **YES — ended the attempt** |
| *"I feel that I am not on the right track"* | **YES — the approach was O(coordinate range)** |

**Four out of five.** Your doubt is ~80% precise. That's a better signal than most of your test cases,
and you are currently ignoring it.

The 30-second resolution menu:
- **Assumption about ordering/monotonicity?** → construct the counterexample. Try the nested case.
- **"Will this be null?"** → trace the last iteration specifically. Not the middle — the *last*.
- **Python API doubt?** → 10 seconds in a REPL. Don't reason about it, run it.
- **"I'm not on the right track"?** → **stop coding.** Go back to §7 and re-select the approach.
  Sunk-cost is what kept you in the number-line dict for 32 minutes.

If you install nothing else from this lecture, install this rule and the 3-row table. Together
they're worth more than the next 50 problems you'd solve without them.

---

## 7. Core concept #4 — Constraints → complexity → algorithm

This is a genuine hole in your toolkit and it's pure gain, because it's a *lookup table*, not a
skill you have to develop.

Before choosing an approach, read the constraints and work backwards. Interviewers and problem
setters choose `n` deliberately — **the constraint is a hint about the intended complexity.**

| If n is up to… | Target complexity | What that means you're reaching for |
|---|---|---|
| 10–12 | O(n!) | permutations, brute-force backtracking |
| ~20 | O(2ⁿ) | subsets, bitmask DP |
| ~500 | O(n³) | triple loop, Floyd–Warshall, some 2-D DP |
| ~5,000 | O(n²) | double loop, most 2-D DP, LCS-type |
| ~10⁵–10⁶ | **O(n log n)** | **sort + sweep**, heap, binary search — *the medium sweet spot* |
| ~10⁷–10⁸ | O(n) | single pass, two pointers, sliding window, hashmap |
| ≥ 10⁹ | O(log n) or O(1) | binary search, math, bit tricks |

Two rules that fall straight out of this and would have saved you 32 minutes:

**Rule A — "n up to 10⁵ and you can't see an O(n) trick" ⇒ sort first.** The `log n` is free at that
size; sorting is *the* default move for array/interval problems. Merge Intervals: `n ≤ 10⁴`,
coordinates up to 10⁵. Sorting costs nothing. Your number-line dict costs O(10⁵ × intervals) and
also breaks entirely if the problem allows coordinates up to 10⁹. **A ten-second complexity estimate
kills that approach before you write a line.**

**Rule B — cost your idea before you build it.** Every time you invent a data structure, immediately
ask: *how many entries can this hold, worst case?* If the answer is "proportional to the range of
the values rather than the number of items," it's wrong. That single question is a complete filter
for the number-line mistake, and it will recur (it's the same instinct as "don't allocate per-value,
allocate per-item").

**Add to your §1 trigger table in `patterns_and_pitfalls.md`:**

| Signal | Reach for |
|---|---|
| "count the ways / how many ways" | sliding window (fixed length) or DP |
| answer is a *number* that's monotonic in a parameter | **binary search on the answer** |
| "k-th" anything | heap, or quickselect, or binary search on value |
| nested structure, matching pairs, "undo/resume later" | **stack** (you now own this one — LC 224) |
| "in-place" + array | two pointers (read/write pointer pattern) |
| optimum over choices with overlapping subproblems | DP — **define the state before anything else** |
| unsorted + "pair/triplet summing to X" | sort, then two pointers inward |

---

## 8. Core concept #5 — Templates are about *retrieval*, not understanding

Here's a distinction that matters more than it sounds:

- **Understanding** = "given time, I can derive it." You have this in abundance.
- **Retrieval** = "it comes out of my fingers in 90 seconds, cold, correct, no thought."

You're trying to run interviews on understanding. Understanding costs 10–15 minutes per primitive,
and you only have ~35. **Reorder List attempt 1 died at exactly this: you understood everything and
couldn't retrieve `reverse a linked list`.** The strategy took 5 minutes; the missing primitive ate
the other 23.

Retrieval only comes from **blank-page reproduction**, not from reading solutions. Reading a solution
produces recognition ("yes, that's right"), which feels like learning and isn't.

### 8.1 The 10 templates you need in your fingers

Your skill tracker says linked-list primitives are acquired. These are the rest. Each should be
reproducible **cold, from a blank page, in under 3 minutes**:

1. **Two pointers inward** (sorted array, `lo`/`hi` converging) — *you failed this; do it first*
2. **Sliding window, variable** (expand right, shrink left while invalid) — ✅ you have this
3. **Sliding window, fixed** (`ws += a[r] - a[r-k]`) — today's gap
4. **Intervals: sort by start, sweep, merge with `max`** — *you failed this; do it second*
5. **Binary search** (the `lo <= hi` form) **+ binary search on the answer** — unassessed, high frequency
6. **Tree DFS** (recursive, with the "what do I return up?" question) — unassessed
7. **Tree BFS** (queue + level-size loop for level-order) — unassessed
8. **Graph BFS/DFS on a grid** (visited set, 4-directional neighbors) — unassessed
9. **Heap** (`heapq`, size-k pattern, and the negate-for-max-heap trick) — unassessed
10. **Backtracking skeleton** (choose → recurse → un-choose) — unassessed

Items 5–10 are **entirely unassessed in your tracker** and they cover — conservatively — half of all
Microsoft mediums. Trees and graphs alone are the single largest untested surface in your practice.
That's not a weakness; it's unclaimed territory.

### 8.2 The drill (20 minutes, high yield)

1. Blank file. Write the template from memory. **No looking.**
2. Run it against 3 hand-made inputs including n = 1.
3. Diff against a canonical version. Note *what you forgot*, not just that you forgot.
4. Delete the file.
5. Redo the same template **3 days later**, then **7 days later**. (Spacing is what moves it from
   understanding to retrieval. Same-day repetition mostly doesn't.)

### 8.3 The redo rule — this is *the* highest-yield habit in your data

Reorder List: total failure → clean mastery in **4 days** via deliberate redo.
Basic Calculator: floundering June 28 → essentially solved July 2.

**Your redo success rate is 100%.** Your first-attempt success rate is ~40%. Yet your log shows far
more first attempts than redos. You are under-using the one thing that demonstrably works for you.

> **Rule: every failed problem gets redone in 3 days and again in ~10 days. A problem is not "done"
> until you've solved it cold, from scratch, without notes.** Failed problems are worth 3× a new
> problem. Right now you have five sitting in the bank — 3Sum, Merge Intervals, Basic Calculator,
> Birthday Chocolate, and Reorder List (for speed). **Do those before you touch anything new.**

### 8.4 Kill the Python tax (one afternoon, permanent)

Group Anagrams cost you 3 attempts on this. Make `LEARNING/dsa/python_cheatsheet.md` and never pay
it again:

```python
# --- hashing / keys ---
key = tuple(sorted(word))          # sorted() → list (unhashable!). tuple it. Or "".join(sorted(w))
from collections import defaultdict, Counter, deque
d = defaultdict(list); d[k].append(v)      # no "if key in d" dance
Counter("aab")                              # → {'a':2,'b':1}; .most_common(k)
del d[k]                                    # remove a key (NOT .remove — that's for lists/sets)
list(d.values())                            # .values() is a VIEW, not a list

# --- sorting ---
arr.sort()                                  # in place, returns None  ← don't do x = arr.sort()
sorted(arr, key=lambda x: x[0])             # explicit key. For list-of-lists, default is lexicographic
sorted(arr, key=lambda x: (-x[1], x[0]))    # multi-key, descending via negation

# --- heaps (min-heap only) ---
import heapq
heapq.heappush(h, x); heapq.heappop(h)
heapq.heappush(h, -x)                       # max-heap: negate on the way in AND out
heapq.nlargest(k, arr)

# --- deque / stack ---
q = deque([start]); q.popleft(); q.append(x) # O(1) both ends. list.pop(0) is O(n) — never use it

# --- misc that bites ---
float('inf'), float('-inf')
divmod(a, b)                                # (quotient, remainder)
for i, v in enumerate(arr):                 # index AND value
for a, b in zip(x, y):
s = set()                                   # set() with parens — `set` alone is the class
matrix = [[0]*n for _ in range(m)]          # NOT [[0]*n]*m — that aliases the same row m times!
```

That last one will bite you the first time you do a grid DP. Learn it now, for free, instead of in
an interview.

---

## 9. The Solve Protocol

A repeatable ritual. Use it on every problem until it's automatic. Timings are for a 35-minute
medium.

**Phase 1 — READ (2 min).** Restate the problem in one sentence in your own words. State input type,
output type, and what "valid" means. *Your Merge Intervals comments show you doing this well — keep
it.*

**Phase 2 — EXAMPLES (3 min).** Write the given example. Then write **three of your own**: n = 1,
all-same, and the weird/nested one. Solve them **by hand**. If you can't solve them by hand, you
cannot code them.

**Phase 3 — CONSTRAINTS → TARGET (1 min).** Read the constraints. Look up the target complexity in
§7's table. Say it out loud: *"n is 10⁵, so I'm looking for O(n log n) — probably sort-based."*

**Phase 4 — APPROACH (5 min).** Run your §1 trigger table. Pick a candidate. **Cost it.** If the cost
exceeds the target from Phase 3, discard it and pick again — *before* writing code. If nothing comes
in 5 minutes, run the stuck-checklist in `patterns_and_pitfalls.md` §2.

**Phase 5 — CONTRACT (2 min).** Write the four comments from §4.4: invariant, init, progress,
termination. **This is the phase you currently skip, and it is where your bugs come from.** Do not
skip it, even when it feels obvious. *Especially* when it feels obvious.

**Phase 6 — CODE (10 min).** Now type. The contract makes this mostly transcription. If you find
yourself *thinking hard* here, that means Phase 5 was incomplete — go back rather than pushing
through.

**Phase 7 — TRACE (4 min, MANDATORY, BEFORE RUNNING).** Table-trace your three examples from Phase 2.
Include the invariant sanity column. **Do not hit Run until this passes.** Running first outsources
your thinking to the judge, which is what trained the symptom-driven debugging in §3.2.

**Phase 8 — EDGE SWEEP (2 min).** Empty input. Single element. All identical. Largest/smallest values.
Does every branch make progress?

**Phase 9 — RUN.** By now it usually just passes.

**Phase 10 — LOG (3 min).** Into `problem_log.md`: what pattern it was, what the invariant was, what
went wrong, **and which failure mode from §3 it belonged to.** Tracking failure *modes* rather than
problems is how you'll see this improve.

> **The reframe:** Phases 1–5 are 13 of the 35 minutes. That feels wasteful. It isn't — you spent
> **30 minutes on 3Sum and got nothing**, and **32 minutes on Merge Intervals and got nothing**. Your
> current bottleneck is not speed. It's aiming.

---

## 10. The debugging protocol (replaces patch-driven debugging)

When a test fails, **do not immediately edit code.** Do this instead:

1. **Reproduce on the smallest failing input.** Shrink it until removing anything makes it pass.
2. **Re-read your invariant** (you wrote it in Phase 5 — this is why Phase 5 pays off twice).
3. **Trace the small input in a table, with the sanity column.** Find the *first row* where the
   invariant goes false. **That row is the bug.** Not the row where the output looks wrong — the row
   where the invariant first breaks.
4. **Check initialization first.** It's your #1 bug class; look there before anywhere else. *Ask
   specifically: is the invariant true before iteration 1?*
5. **Check progress in every branch.** Does each branch strictly shrink the measure?
6. **Only then** change code — and change **one thing**, with a reason you can state.

Rule: **if you've made three patches without a hypothesis, stop and rewrite from the invariant.**
Your 3Sum attempt 4 is a code base with four unrelated patches and no single coherent model. That's
strictly harder to debug than a clean rewrite.

---

## 11. Getting to hards

You already solved one. Here's the general shape, because it's less mysterious than it looks:

**Most hards are (a) two mediums composed, (b) a medium plus one non-obvious insight, or (c) a
medium with a nasty implementation.** They are rarely a whole new idea.

- **Reorder List** (medium) is already a composition: find middle + reverse + merge. You do this.
- **Basic Calculator** (hard) = string parsing + stack-as-call-frame. You derived both.
- **Merge k Sorted Lists** (hard) = merge two lists (you have it) + a heap.
- **Trapping Rain Water** (hard) = two pointers + one insight about prefix maxima.
- **Sliding Window Maximum** (hard) = sliding window + monotonic deque.

So the path to hards is **not** "learn hard algorithms." It's:
1. Make the ~10 mediums-level templates *retrieval-fast* (§8), so composing two costs 6 minutes of
   your budget instead of 25.
2. Practice **decomposition out loud**: "this is X followed by Y." Your Reorder List attempt 1 proves
   you can already do this — it's your strongest single skill and you should say it in interviews.
3. Accept that hards usually need one insight you may not find in 35 minutes. **That's expected and
   it's fine — SDE I loops are mediums.** Do a hard once a week for the composition practice, not
   because you need them.

**Do not chase hards yet.** Your mediums-with-verification rate is the number that gets the offer.

---

## 12. What to practice, in order

**Tier 0 — the bank (do these before anything new).** Five redos, using the full protocol:
3Sum → Merge Intervals → Basic Calculator → Birthday Chocolate → Reorder List (timed, for speed).
You will pass all five. That matters psychologically as much as technically — it converts "I fail
mediums" into "I have five clean solves," which is the accurate story.

**Tier 1 — install the missing templates** (§8.1 items 5–10, in this order):

| Template | Problems |
|---|---|
| Binary search | #704 Binary Search → #33 Search in Rotated → #153 Find Minimum in Rotated |
| Tree DFS | #104 Max Depth → #226 Invert → #98 Validate BST |
| Tree BFS | #102 Level Order → #199 Right Side View |
| Graph BFS/DFS | #200 Number of Islands → #133 Clone Graph → #207 Course Schedule |
| Heap | #215 Kth Largest → #23 Merge k Sorted Lists |
| Backtracking | #78 Subsets → #46 Permutations → #39 Combination Sum |
| Intervals (cement) | #57 Insert Interval → #435 Non-overlapping |
| Two pointers (cement) | #167 Two Sum II → #11 Container With Most Water → #42 Trapping Rain Water |

**Tier 2 — 1-D DP** (#70 Climbing Stairs → #198 House Robber → #322 Coin Change → #300 LIS). Start
here only after Tier 1, and always **define the state in English first**: *"dp[i] = the best answer
considering the first i items."* Nearly all DP confusion is a vague state definition.

**Cadence that survives a full-time job:**
- **Weekdays: 1 problem, 45 min, full protocol.** Non-negotiable, even a tired easy one. Streak > volume.
- **One weekday slot: 20-min template drill** instead of a problem.
- **Weekend: 2 problems + all redos due.**
- **Weekly: 15 min updating `skill_tracker.md`** — and log the **failure mode**, not just pass/fail.

That's ~5 hours a week. At that rate the Tier 0 + Tier 1 list is roughly **6 weeks**, which puts you
in genuinely solid medium territory well before the referral window.

**The metric that matters isn't the pass rate.** Track this instead:

> **"Did my traced solution pass on the first Run?"**

That's the verification metric. Get it above 70% and the medium rate follows automatically, because
it's the *same skill* the interviewer is actually watching — nobody in a real loop gives you a
judge to patch against.

---

## 13. The psychological close

Timothy — I want to be precise about the evidence, because you're not.

You have a file where you tell yourself you're at 30% on mediums. In that same folder is a file where
you **solve a LeetCode Hard from first principles**, catch yourself mid-solution and note that a
parenthesis is a function call frame, and reason about loop invariants with vocabulary nobody taught
you. Also in that folder: a linked-list problem you went from *"I have no idea how to reverse a
linked list"* to clean mastery on **in four days**.

That is not a 30% profile. That's a person with a **high learning rate, strong decomposition, and an
untrained last mile.** The last mile is mechanical, and mechanical things are the *easy* kind of
problem to fix — that's the good news you should actually take from this document.

The reason you feel like you're failing is that **your metacognition is far ahead of your execution.**
You can see every gap in your own work in real time — you write them down as you go. That's a rare
and genuinely valuable trait, and it's *also* what makes you feel incompetent, because you're
comparing yourself against your own extremely detailed map of your gaps, while comparing others
against their finished, silent output. Your `Ghosts` file and your practice comments are the same
phenomenon: **exceptional visibility into your own uncertainty, which you're misreading as
exceptional deficiency.**

The fix isn't confidence. It's a protocol — so the doubt gets *handled* instead of just *felt*.
That's what §4, §5, and §6 are. Three mechanical habits:

1. **Write the invariant, derive the initialization.** (Kills your #1 bug class.)
2. **Table-trace three examples before you Run.** (Kills your #2.)
3. **Named doubt = stop and test, 30 seconds.** (Kills your #3.)

Do those and your existing ability shows up on the scoreboard. Nothing else needs to change.

One last thing, said plainly because it's the thing that actually threatens this: **June 27 to
July 26 with one easy problem is the real risk**, not your ability. The wife-in-Seattle clock is
running, and the coding gate is the only thing between you and the loop. Three problems this week
beats a perfect plan you start in August.

Do the five redos in Tier 0 this week. You'll pass all five, and you'll have replaced a story with
data.

---

## Appendix — the one-page card

Print this. Keep it next to your keyboard.

```
BEFORE CODING
  1. Restate the problem in one sentence.
  2. Write 3 examples: n=1, all-same, nested/weird. Solve BY HAND.
  3. Read constraints → target complexity (10^5 ⇒ O(n log n) ⇒ probably SORT FIRST).
  4. Pick pattern from the trigger table. COST IT. Over budget? Pick again.
  5. Write the contract:
        # INVARIANT:   true at the top of every pass
        # INIT:        therefore vars start at ___   ← derive, never guess
        # PROGRESS:    ___ strictly shrinks in EVERY branch
        # TERMINATION: on exit ⇒ the answer

WHILE CODING
  - One variable, one owner. Never mutate a loop var from inside the body.
  - Thinking hard? The contract was incomplete. Go back.

BEFORE RUNNING  (mandatory)
  - Table-trace 3 examples. One column asserting the invariant.
  - The first row where the invariant goes false IS the bug.
  - Edge sweep: empty / 1 elem / all same / does every branch progress?

STOP SIGNALS  ("I think…", "I assume…", "probably", "will this crash?", "YOLO")
  → 30 seconds. Counterexample, trace the LAST iteration, or a REPL check.
  → Your doubt has been right ~80% of the time. Believe it.

WHEN A TEST FAILS
  → Do NOT patch. Shrink input → re-read invariant → trace → CHECK INIT FIRST.
  → 3 patches with no hypothesis ⇒ rewrite from the invariant.

AFTER
  → Log the FAILURE MODE, not just pass/fail. Redo failures at +3 and +10 days.
  → Metric that matters: "did it pass on the FIRST Run after tracing?"
```

---
*Lecture 002 — created 2026-07-26. Analysis source: `LEARNING/dsa/6_baseline_assessment.py`,
`7_baseline_assessment.py`, `001_practice.py`. All bug claims verified by execution.
Companions: `LEARNING/dsa/patterns_and_pitfalls.md` (fold §5 and §7 into it),
`LEARNING/dsa/skill_tracker.md` (add a failure-mode column), `LECTURES/001-…`.*
