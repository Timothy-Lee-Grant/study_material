# Deep Dive 002: Insert Delete GetRandom O(1) (380): Which Properties a Structure Really Has to Keep

> **For:** Timothy · **Date:** 2026-11-08
> **Source:** your Nov 8 attempt in `../examples.py` (the method stubs plus your operations table and notes above `class RandomizedSet`), and the thinking you described in chat. You worked it blind from lecture 012 §3.4 (statement only, no structures shown).
> **Status:** attempted; design not finished, no code yet. Retry planned, so the full solution in §7 is collapsed.
> **Why this lecture:** you got almost all of the way there. You picked a list for `getRandom`, a hash structure for lookups, then a **dict** because its value can "connect" to the other structure; you saw that the list's valid elements are positions `0 … n-1`; and you found the exact wall: *"removing an element within that valid range makes a hole in our list"* and *"a list is not going to be able to perform an immediate removal."* The missing step is one question: **does this list actually need to keep its order?** It doesn't, and that changes everything.
> **Format notes:** numbers before symbols; one canonical design with the invariant written as one sentence; every update order derived; no firmware analogies.
> **Verification:** the solution in §7 was run against a plain-`set` reference on 2,000 random sequences of 30 calls, with the invariant checked after every call; `getRandom` was sampled 40,000 times (each of 4 values came out about 25%). The two broken variants in §5 were found to fail on the same tests. All traces were printed by running the code.

---

## Core ideas (the answer key)

1. **A list can remove from the middle in O(1) if you don't care about order:** move the **last** element into the hole, then `pop()` the end. Shifting is only needed to *keep the order*, and a set has no order.
2. **Before ruling a structure out, ask which of its properties the problem actually needs.** "A list removal is O(n)" is true only under the assumption "the remaining items keep their order." Question the assumption, not just the structure.
3. **What the list must keep is "no holes": the elements are exactly `items[0:n]`.** You already said this ("all elements between zero and n are valid"). That invariant, not the order, is what makes `getRandom` work.
4. **Split each operation into the questions it asks.** `remove(val)` asks two: **"where is `val`?"** and then "take it out." The first question is a lookup, and its answer is a **position**.
5. **When you combine two structures, the dict's value is "where to find this key in the other structure."** Here: `index_of[val]` = val's position in `items`. (In LRU it's the node; in TimeMap it's that key's list.) That's the "connection" you were looking for.
6. **The invariant in one sentence:** `items` holds each element exactly once, and `index_of[v] == i` exactly when `items[i] == v`.
7. **Every line that moves an element must update its position in the dict.** Moving the last element into the hole changes *its* index, so `index_of[last] = hole`. That's the line people forget.
8. **Trace the edge case where the removed element *is* the last one.** The order of the last two dict lines matters there (§5.2).
9. **Prefer computing over storing:** the number of elements is `len(items)`, so no separate counter (lecture 012 §5.1, rule 2).

---

## Table of Contents

- [0. What your attempt showed](#0-what-your-attempt-showed)
- [1. The problem](#1-the-problem)
- [2. The wall you hit, in numbers](#2-the-wall-you-hit-in-numbers)
- [3. Root 1: question the property, not the structure](#3-root-1-question-the-property-not-the-structure)
- [4. Root 2: split operations into lookup questions; the dict stores *where*](#4-root-2-split-operations-into-lookup-questions-the-dict-stores-where)
- [5. Root 3: the invariant, and the order of updates](#5-root-3-the-invariant-and-the-order-of-updates)
- [6. Your permutations retry (Nov 7), briefly](#6-your-permutations-retry-nov-7-briefly)
- [7. A solution, derived step by step (collapsed)](#7-a-solution-derived-step-by-step-collapsed)
- [8. Where else this shows up](#8-where-else-this-shows-up)
- [Drills](#drills)
- [Self-check questions](#self-check-questions)
- [Sources](#sources)

---

## 0. What your attempt showed

| What you wrote | What's right | What tripped you up |
|---|---|---|
| "I should go and follow the workflow outlined in … 012" + an operations table per method | ✓ exactly the method: you used it from a blank page | The "question" column lists **capabilities** ("must have way to immediately remove") instead of **lookups** ("where is `val`?") (§4) |
| "a single mutator helper … so both structures always get changed at the same time. This prevents drift" | ✓ the consistency rule from 012 §5, applied before writing any code | |
| clarifying question: does random mean per insert or per value? → "each element val is guaranteed … unique" | ✓ a real clarifying question, answered from the statement | |
| list for `getRandom`; "all elements between zero and n are valid" | ✓ that's the invariant the solution keeps (§3) | |
| "Arrays need to move everything over (arrays eliminated)" | true **if order must be kept** | the assumption "order must be kept" was never questioned (§3) |
| "Maybe I actually select a dict … So what info would I want for the val?" | ✓ the right question, and the right structure | not answered yet: the value should be the **position in the list** (§4) |
| "just keep a state variable increasing and decreasing for each insert / remove" | works | redundant: it's `len(items)`, and a separate counter can drift |
| "I have no idea how to combine them" | | §4–5: the list is the source of truth, the dict is an index into it, one invariant sentence links them |

---

## 1. The problem

**Insert Delete GetRandom O(1) (380), paraphrased.** Implement a class `RandomizedSet`:
- `insert(val)`: add `val` if it isn't present. Return `True` if it was added, `False` if it was already there.
- `remove(val)`: remove `val` if it's present. Return `True` if it was removed, `False` if it wasn't there.
- `getRandom()`: return a random element of the current set; **every element must be equally likely.** It's only called when the set isn't empty.

Each method must run in **O(1) average time.**
Example: `insert(1) → True`, `remove(2) → False`, `insert(2) → True`, `getRandom() → 1 or 2`, `remove(1) → True`, `insert(2) → False`, `getRandom() → 2`.
Constraints: values fit in 32-bit signed integers; at most 2·10⁵ calls in total.

---

## 2. The wall you hit, in numbers

Say the set holds `10, 20, 30, 40`, stored in a list:

```
box:     0    1    2    3
items:  [10,  20,  30,  40]
```

`getRandom` picks a random box from `0 … 3` (`random.choice(items)` does exactly that). That only works because **every box from 0 to `len(items) - 1` holds a real element**. That's your "all elements between zero and n are valid."

Now `remove(20)`. You need box 1 to stop holding 20, and the list to have no hole:

**Option A, what `del items[1]` does:** shift every later element one box left.

```
before:  [10, 20, 30, 40]
after:   [10, 30, 40]        30 moved from box 2 to 1, 40 from box 3 to 2
```

Two elements moved. Removing from the front of a list of `n` would move `n - 1`. That's the O(n) you were worried about, and you were right that it's too slow.

**Option B:** leave a marker (`None`) in the hole. No shifting, but now `getRandom` can land on a hole and has to try again; after many removals, most boxes are holes, and it's no longer O(1). The "no holes" invariant is gone.

So both options you could see fail. That's exactly where your notes stopped.

---

## 3. Root 1: question the property, not the structure

Look at what Option A spends its time on: moving 30 and 40 **so that they stay in the same order**. Now ask the question your notes never asked:

> **Does the order of elements in `items` matter to any operation?**

Go through the three operations:

| Operation | Does it depend on the order of `items`? |
|---|---|
| `insert` | no: it only needs to put the element somewhere |
| `remove` | no: it needs to find the element, not its neighbours |
| `getRandom` | no: a uniformly random box is uniformly random whatever is in each box |

A **set** has no order, so nothing in the problem requires one. That means you can fill the hole with **any** element, and there's exactly one element you can move in O(1) without making a new hole: **the last one.**

**Option C: move the last element into the hole, then remove the end.**

```
before:            [10, 20, 30, 40]      remove 20 (box 1)
copy last into 1:  [10, 40, 30, 40]
pop the end:       [10, 40, 30]          no hole; boxes 0 … 2 all valid
```

One copy and one `pop()`, both O(1). The order changed (40 now comes before 30), and nothing cares.

**The general move.** When a structure seems to fail an operation:
1. Say *why* the operation is slow ("a removal shifts everything to keep the order").
2. That "why" contains an assumption ("keep the order").
3. Check whether the problem needs that assumption. If it doesn't, the structure may not fail after all.

You've seen the same move before: Browser History (lecture 012 §4.3) didn't delete forward pages, it moved the `last` boundary, because nothing needed the data to actually be gone. Here, nothing needs the order to be kept.

---

## 4. Root 2: split operations into lookup questions; the dict stores *where*

Your operations table had the right rows, but the "question" column described what a structure must be **able to do** ("must have way to immediately remove"). Lecture 012's step 3 asks for the **question being answered**, phrased as a lookup. Rewrite `remove` that way, and it splits into two questions:

| Operation | Question(s) it asks | Answered fast by |
|---|---|---|
| `insert(val)` | "is `val` already present?" | dict / set |
| `remove(val)` | **1.** "is `val` present, and **where** is it in `items`?" **2.** "take it out without leaving a hole" | **1.** a dict from `val` to its box index · **2.** swap with last, then `pop()` (§3) |
| `getRandom()` | "which element is in a uniformly random box?" | the list |

Question 1 of `remove` is the one that answers your note *"So what info would I want for the val?"*: Option C needs to know **which box** to fill. A set can say *whether* `val` is present but not *where* it is. A dict can say both, if its value is the position:

> **`index_of[val]` = the box in `items` where `val` lives.**

That's the "connection" you were reaching for, and it's the same pattern every time two structures are combined: the dict maps a key to **where to find it in the source of truth**.

| Problem | Source of truth | Index (dict) maps key to… |
|---|---|---|
| 380 RandomizedSet | `items` (a list) | the element's **box index** in `items` |
| 146 LRU Cache | the doubly linked list | the key's **node** |
| 981 TimeMap | per-key lists of (time, value) | that key's **lists** |

**Which one is the source of truth?** The one that really holds the elements in the shape an operation needs: `items` (only a list can answer `getRandom`). The dict is a shortcut into it. And `len(items)` is the element count, so the counter you were planning isn't needed.

---

## 5. Root 3: the invariant, and the order of updates

### 5.1 The invariant sentence

> **`items` holds each element exactly once (boxes `0 … len(items)-1`, no holes), and `index_of[v] == i` exactly when `items[i] == v`.**

Every method has to leave that sentence true. Check Option C against it with the §2 numbers:

| Step | `items` | `index_of` | invariant? |
|---|---|---|---|
| before | `[10, 20, 30, 40]` | `{10:0, 20:1, 30:2, 40:3}` | ✓ |
| `hole = index_of[20]` → 1; `last = items[-1]` → 40 | | | |
| `items[hole] = last` | `[10, 40, 30, 40]` | unchanged | ✗ (40 is in two boxes, and `index_of[40]` says 3) |
| `index_of[last] = hole` | | `{10:0, 20:1, 30:2, 40:1}` | ✗ (still has 20, list still too long) |
| `items.pop()` | `[10, 40, 30]` | | ✗ (still has 20) |
| `del index_of[20]` | | `{10:0, 30:2, 40:1}` | ✓ |

(From running it.) The invariant is broken in the middle of the method, which is fine, but must be true again at the end.

**`index_of[last] = hole` is the line that's easy to forget**, because it's about a *different* element than the one being removed. Your name-vs-lines check catches it: "the element `last` moved boxes; which line updates where `last` lives?" Without that line (from running a version that skips it): insert 1, 2, 3; remove 1 → `items = [3, 2]`, but `index_of[3]` still says 2. A later `remove(3)` writes to box 2, which no longer exists: `IndexError`.

### 5.2 The edge case: removing the last element itself

Now take the case where the element being removed **is** in the last box. Say `items = [1, 2]`, `index_of = {1:0, 2:1}`, and `remove(2)`:

| Step | values | `items` | `index_of` |
|---|---|---|---|
| `hole = index_of[2]` | 1 | | |
| `last = items[-1]` | 2 (the same element!) | | |
| `items[hole] = last` | | `[1, 2]` (no change) | |
| `index_of[last] = hole` | | | `{1:0, 2:1}` (no change) |
| `items.pop()` | | `[1]` | |
| `del index_of[2]` | | | `{1:0}` ✓ |

It works because the `del` comes **last**. If the `del` came first (from running that version), the next line, `index_of[last] = hole`, would put 2 straight back in: the result is `items = [1]` but `index_of = {1:0, 2:1}`. The dict says 2 is still present.

**The habit:** for any "swap with last" removal, trace the case where the removed element *is* the last one, with a 2-element example.

---

## 6. Your permutations retry (Nov 7), briefly

You also retried Permutations (46) after deep dive 001. The model is now right: you reasoned in **placement** ("what should I place at this index?"), kept a collection of the remaining valid numbers, undid both changes after each branch, copied the valid numbers before looping over them so they don't change underneath you, and worked out O(n!) correctly.

Running it before you trace it: `[1,2,3]` returns `[]` (so do `[0,1]` and `[1]`). A hint, not the fix: **look at what you put into `valid_set` before `bt(0)`, and compare it with what the problem says the numbers are.** It's the same "what does this number stand for?" question as the window lectures (a value vs. a position). Trace `[1, 2]` with the call-tree format from deep dive 001 §6 and you'll see it on the first line.

---

## 7. A solution, derived step by step (collapsed)

Retry first: rewrite your operations table with lookup questions (§4), write the invariant sentence (§5.1) as a comment, write `remove` in words, then code it and trace the two-element case (§5.2).

<details><summary>Open after your retry: the solution</summary>

1. **Source of truth:** `items`, a list with no holes (§3).
2. **Index:** `index_of`, a dict from value to its box in `items` (§4).
3. **Invariant:** §5.1.
4. **insert:** if present, `False`; otherwise its box will be the current length, so record that, then append.
5. **remove:** if absent, `False`; otherwise find the hole, move the last element into it, update **its** index, pop the end, and delete `val` from the dict **last**.
6. **getRandom:** a uniformly random box of `items`.

```python
import random

class RandomizedSet:
    def __init__(self):
        self.items = []                  # source of truth: each element once, boxes 0 … len-1, no holes, any order
        self.index_of = {}               # index: value -> its box in items
        # invariant: index_of[v] == i  exactly when  items[i] == v

    def insert(self, val):
        if val in self.index_of:
            return False
        self.index_of[val] = len(self.items)   # it will go in the next box (the current length)
        self.items.append(val)
        return True

    def remove(self, val):
        if val not in self.index_of:
            return False
        hole = self.index_of[val]        # where val is
        last = self.items[-1]            # the element we can move in O(1)
        self.items[hole] = last          # fill the hole (order doesn't matter in a set)
        self.index_of[last] = hole       # last moved: update where it lives
        self.items.pop()                 # drop the now-duplicate end
        del self.index_of[val]           # LAST: correct even when val is the last element
        return True

    def getRandom(self):
        return random.choice(self.items) # every box equally likely, and every box is a real element
```

All three methods are O(1) average: dict lookups and updates are O(1) on average, and `append`, `pop()` from the end and indexing a list are O(1).

Lecture 012 §4.4 has the same design, with a `_check()` method you can use to test your version (012 §5.2).
</details>

---

## 8. Where else this shows up

| Problem | Statement (paraphrased) | Examples | Constraints | What it tests |
|---|---|---|---|---|
| **27 Remove Element** | Remove every occurrence of `val` from `nums` **in place**; the order of the remaining elements **may change**. Return `k`, the number of elements not equal to `val`; the first `k` boxes must hold them | `[3,2,2,3], val = 3` → `2` (`nums` starts `[2,2,…]`); `[0,1,2,2,3,0,4,2], val = 2` → `5` | `0 <= len <= 100`; `0 <= nums[i] <= 50`; `0 <= val <= 100` | "order may change" → fill holes from the end (and it's also a reader/writer problem: try both) |
| **1472 Design Browser History** (array version) | see lecture 012 §3.3 | | | moving a boundary instead of deleting data: the same "what does the problem really need?" question |
| **146 LRU Cache** (redo) | see lecture 012 §3.8 (and lecture 010) | | | the opposite case: here order **does** matter (recency), so the list must be a doubly linked list, not swap-with-last |
| **381 Insert Delete GetRandom O(1) - Duplicates allowed** (stretch, Hard) | Like 380, but values can repeat. `insert(val)` adds one copy and returns `True` if `val` wasn't present before; `remove(val)` removes **one** copy, returning whether one was present; `getRandom` picks each **copy** with equal probability | `insert(1) → True, insert(1) → False, insert(2) → True, getRandom()` → 1 with probability 2/3, `remove(1) → True, getRandom()` → 1 or 2 | values fit in 32 bits; at most 2·10⁵ calls | what should the dict's value be when a value can live in **several** boxes? |

---

## Drills

1. `items = [7, 3, 9, 5, 1]`. Using Option C, show `items` after `remove(3)`, then after `remove(1)`.
2. For drill 1, write `index_of` before and after each removal.
3. Which line, if missing, makes this sequence crash: insert 1, 2, 3; remove 1; remove 3? Explain with boxes.
4. For each of these, does the problem need the order kept? (a) a set; (b) a queue; (c) "remove all zeros, keeping the other elements in order"; (d) 27 Remove Element.
5. Rewrite this operations-table row as lookup questions: "`delete(key)`: must have a way to immediately remove the key's record from the list."

<details><summary>Answers</summary>

1. `remove(3)`: hole = box 1, last = 1 → `[7, 1, 9, 5]`. `remove(1)`: hole = box 1, last = 5 → `[7, 5, 9]`.
2. Start `{7:0, 3:1, 9:2, 5:3, 1:4}`. After `remove(3)`: `{7:0, 1:1, 9:2, 5:3}`. After `remove(1)`: `{7:0, 5:1, 9:2}`.
3. `index_of[last] = hole`. After removing 1, 3 moves from box 2 to box 0 and the list is `[3, 2]`, but the dict still says 3 is in box 2. `remove(3)` then writes into box 2, which no longer exists.
4. (a) no; (b) yes (first in, first out); (c) yes; (d) no ("the order may change").
5. "Where is `key`'s record in the list?" (answered by a dict from key to position/node) and "take that record out" (how depends on whether the order must be kept).
</details>

---

## Self-check questions

1. Why is `del items[i]` O(n), and what assumption makes it O(n)?
<details><summary>Answer</summary>

It shifts every later element one box left so they keep their order. Without the need to keep the order, you can fill the hole with the last element instead.
</details>

2. Why can a set's list fill a hole with the last element?
<details><summary>Answer</summary>

None of the three operations depends on the order of `items`, and a set has no order. Moving the last element creates no new hole, and `pop()` removes the duplicate at the end in O(1).
</details>

3. What does `index_of[val]` store, and why that and not just `True`?
<details><summary>Answer</summary>

`val`'s box in `items`. `remove` has to know which box to fill; "present" alone doesn't say where.
</details>

4. State the invariant.
<details><summary>Answer</summary>

`items` holds each element exactly once in boxes `0 … len(items)-1` (no holes), and `index_of[v] == i` exactly when `items[i] == v`.
</details>

5. Which update is easiest to forget in `remove`, and why?
<details><summary>Answer</summary>

`index_of[last] = hole`: it's about the element that moved, not the one being removed.
</details>

6. Why must `del index_of[val]` come last?
<details><summary>Answer</summary>

When `val` is the last element, `last == val`, and `index_of[last] = hole` writes `val` back into the dict. Deleting afterwards removes it; deleting before would leave it there.
</details>

7. Why is a separate element counter worse than `len(items)`?
<details><summary>Answer</summary>

It's a second copy of a fact that already exists, so every path has to update it; `len(items)` can't drift.
</details>

---

## Sources

- Problems: LeetCode 380, 27, 1472, 146, 381. Statements paraphrased; examples and constraints from long-standing problem pages (from my own knowledge, not re-fetched; 2026-11-08).
- Python: `random.choice` (https://docs.python.org/3/library/random.html#random.choice); list and dict operation costs (https://wiki.python.org/moin/TimeComplexity).
- Verification (2026-11-08): the §7 solution matched a plain-`set` reference on 2,000 random sequences of 30 calls with the invariant checked after every call; `getRandom` sampled 40,000 times on 4 values (each about 25%). The "delete first" and "forget `index_of[last]`" variants both failed those tests (the §5 examples were printed from them). Your Nov 7 `permute` was run as written on `[1,2,3]`, `[0,1]` and `[1]`.
