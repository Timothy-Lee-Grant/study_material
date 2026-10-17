# Lecture 012: Data-Structure Design Problems: Choosing, Combining and Keeping Structures in Sync

> **For:** Timothy · **Date:** 2026-10-12
> **Prerequisites:** lecture 010 (linked lists; §8–9 doubly linked lists, sentinels, LRU Cache), lecture 005 (dictionaries), lecture 004 (binary search). The roadmap's "Kinds of problems" §2 introduced what design problems are.
> **Why this lecture:** you asked for an in-depth lecture because these problems "threw you off": *"not only do you need to figure out what data structure to use, but also how to combine things together."* You're also right that they matter for you specifically. Your one in-person Microsoft interview question so far was one (design a rate limiter), and mid-level loops use them often.
> **What makes this lecture different:** design problems aren't solved by recognizing one pattern. They're solved by a **method**: list the operations, ask what question each must answer quickly, pick the structure that answers it, and if no single structure answers all of them, combine two and write down the rule that keeps them in sync. §1 is that method. Everything after it is the method applied to the problems you're most likely to meet, including your rate limiter, designed properly in §4.7.
> **Format notes:** every problem has its full statement (paraphrased), examples and constraints; every structure's *role* is named before it's used (your Oct 11 rule: say what each thing stands for); no firmware analogies.
> **Verification:** every class here was checked against a brute-force reference on 2,000 random sequences of 20–40 calls. The rate limiter and RandomizedSet were also checked against their **invariants** after every single call (§5). `getRandom` was sampled 40,000 times to confirm it's uniform. Traces were produced by running the code.

---

## Core ideas (the answer key)

1. **A design problem is a class whose state persists between calls.** You're judged on every method's complexity, on correctness across *any* sequence of calls, and on how you clarify, explain and test.
2. **Start from an operations table:** each method, what it must answer, and its required complexity. The data structures come *after* the table.
3. **For each operation, ask "what question must be answered fast?"** ("where is key k?", "what's the minimum?", "which is the oldest?") and pick the structure that answers that question in the required time.
4. **If one structure can't answer every question, combine two**, each covering the other's weakness (§4 shows which combination each problem in §3 needs).
5. **Name each structure's role.** One is the **source of truth** (the real data); the others are **indexes** (shortcuts to find things in it). Write one **invariant** sentence that links them, e.g. "the dict has exactly the keys in the list, and maps each to its node."
6. **Every method that changes one structure changes all of them, in the same method,** usually through small helpers (`_remove`, `_add_front`). Most design bugs are structures drifting out of sync.
7. **Store derived answers next to the data they come from** when they can't be recomputed cheaply.
8. **Amortized O(1) is a legitimate answer:** if each item is moved at most a constant number of times over its whole life, the average cost per call is O(1), even if one call occasionally does a lot of work.
9. **Clarifying questions are part of the answer:** capacity, duplicates, what "the last N seconds" includes, whether timestamps only increase, what to return when empty, single-threaded or not.
10. **Test with a call-sequence trace:** one row per call, a column per structure, plus the return value, and check the invariant on every row.

---

## Table of Contents

- [0. What you're actually being asked to do](#0-what-youre-actually-being-asked-to-do)
- [1. The design method (use it every time)](#1-the-design-method-use-it-every-time)
- [2. The toolbox: what each structure answers quickly](#2-the-toolbox-what-each-structure-answers-quickly)
- [3. The problems (statements only)](#3-the-problems-statements-only)
  - [3.1 Min Stack (155)](#31-min-stack-155)
  - [3.2 Implement Queue using Stacks (232)](#32-implement-queue-using-stacks-232)
  - [3.3 Design Browser History (1472)](#33-design-browser-history-1472)
  - [3.4 Insert Delete GetRandom O(1) (380)](#34-insert-delete-getrandom-o1-380)
  - [3.5 Time Based Key-Value Store (981)](#35-time-based-key-value-store-981)
  - [3.6 Number of Recent Calls (933)](#36-number-of-recent-calls-933)
  - [3.7 Rate limiter (your Microsoft interview question)](#37-rate-limiter-your-microsoft-interview-question)
  - [3.8 LRU Cache (146)](#38-lru-cache-146)
- [4. Solutions: the structures, invariants and code](#4-solutions-the-structures-invariants-and-code) (answers; subsections not listed here so the headings don't give them away)
- [5. Invariants and consistency: the core skill](#5-invariants-and-consistency-the-core-skill)
- [6. Testing a design: the call-sequence trace](#6-testing-a-design-the-call-sequence-trace)
- [7. The interview: what to say, in what order](#7-the-interview-what-to-say-in-what-order)
- [8. Recognizing which structures a requirement needs](#8-recognizing-which-structures-a-requirement-needs)
- [9. Practice ladder](#9-practice-ladder)
- [Common mistakes](#common-mistakes)
- [Self-check questions](#self-check-questions)
- [Sources](#sources)

---

## 0. What you're actually being asked to do

An algorithm problem asks for **one answer**: input in, output out. A design problem asks for **an object that keeps answering** while things change:

```python
cache = LRUCache(2)
cache.put(1, 1)
cache.put(2, 2)
cache.get(1)      # the answer depends on EVERYTHING that happened before this call
cache.put(3, 3)
```

Three things follow from that:

| Because… | …you have to think about |
|---|---|
| state persists between calls | what the object stores, and what must be true about it **after every call** (the invariant) |
| each method has its own complexity target | the cost of **every** operation, not just the total |
| calls can come in any order | correctness for **any sequence**: empty, full, repeated keys, an update right after a delete… |

**What the interviewer is looking for** (from the roadmap's Kinds of Problems §2): clarifying the API, a justified choice of structures, clean methods with helpers, a stated invariant, testing with a call sequence, and handling follow-ups. A working class with no explanation scores lower than a nearly working class with a clear design and tests.

---

## 1. The design method (use it every time)

Eight steps. In an interview, steps 1–4 are spoken and written as comments before any real code.

**Step 1: Clarify the API and its meaning.** Write the method signatures and what each returns. Then ask the questions that decide the design (§7.2 has a full list). Examples: Can keys repeat? What's returned when it's empty? Do timestamps only increase? Does "the last 10 seconds" include the boundary?

**Step 2: Write the operations table.**

```
operation        | must answer / do                          | required time
get(key)         | find key's value; mark it most recent     | O(1)
put(key, value)  | insert/update; mark most recent; evict LRU | O(1)
```

**Step 3: For each row, name the *question* behind it.** "Find key's value" → *where is key k?* "Evict LRU" → *which key is the oldest by use?* "Mark most recent" → *move this item to the newest end of an order.*

**Step 4: Pick a structure for each question** from the toolbox (§2). If one structure answers every question in time, you're done. Usually it doesn't.

**Step 5: Combine.** Choose the **source of truth** (where the data really lives) and the **index(es)** (shortcuts into it). Write the **invariant** linking them in one sentence.

**Step 6: Write helpers that preserve the invariant.** Each helper does one change to *all* structures (`_add`, `_remove`, `_move_to_front`). The public methods call helpers, so there's no other way to change state.

**Step 7: Trace a call sequence** (§6): empty, one item, at capacity, a repeated key, the boundary case from your clarifying questions.

**Step 8: State the complexities and the follow-ups:** per-operation time, total space, and what changes for concurrency or scale.

This is the same habit as the three comment lines from lectures 004–010, scaled up to a class.

---

## 2. The toolbox: what each structure answers quickly

The point of this table is **questions**, not structures. In step 4 you look up the question and read off the structure.

| Question you need answered fast | Structure | Cost | What it's bad at |
|---|---|---|---|
| "What's stored under key k?" / "Is k present?" | `dict` / `set` | O(1) avg | no order (well, insertion order only); no "min"; no "random element" |
| "What's the item at position i?" / "a random item" | `list` (array) | O(1) | removing from the middle is O(n) |
| "Add/remove at the end" | `list` | O(1) amortized | the front: `pop(0)` is O(n) |
| "Add/remove at either end" (oldest + newest) | `collections.deque` | O(1) | the middle; random access is O(n) in the worst case |
| "Remove *this* node I'm holding, or move it to an end" | doubly linked list + sentinels (lecture 010 §8) | O(1) | finding a node by key (needs a dict) |
| "Last in, first out" / "undo" | `list` as a stack | O(1) | anything except the top |
| "Smallest (or largest) item, repeatedly, as items arrive" | `heapq` (heap) | peek O(1), push/pop O(log n) | removing an arbitrary item; finding a key |
| "Largest value ≤ x" / "first item at or after time t" in sorted data | sorted `list` + `bisect` (lecture 004) | search O(log n) | inserting in the middle is O(n), **unless** items arrive already in order (then just append) |
| "Running total / count over a range" | prefix sums (lecture 005) | O(1) query | updates are O(n) |
| "A derived value (min, max, sum) of everything *so far*" | store it **alongside each entry** | O(1) | — |

**Python note:** `dict` and `set` are O(1) *on average*. The worst case (many hash collisions) is O(n), and interviewers accept "O(1) average." `list.pop(0)` and `list.insert(0, x)` look cheap but are O(n), which is the most common hidden cost in design answers. Use `deque` for the front.

---

## 3. The problems (statements only)

Each problem below is what you'd get in an interview: a title and a statement, with no hint about which structures to use. Work each one with the §1 method before looking at the answer. The solutions are in §4, after the line below.

### 3.1 Min Stack (155)

**Problem (paraphrased).** Design a stack that supports `push(val)`, `pop()`, `top()` and `getMin()` (the minimum element currently in the stack), **all in O(1)**. `pop`, `top` and `getMin` are only called on a non-empty stack.
Example: `push(-2), push(0), push(-3), getMin() → -3, pop(), top() → 0, getMin() → -2`.
Constraints: values fit in 32 bits; up to 3·10⁴ calls.

*Before scrolling: write the operations table, the question behind each operation, your structures and an invariant sentence. Then compare with §4.1.*

### 3.2 Implement Queue using Stacks (232)

**Problem (paraphrased).** Implement a first-in-first-out queue using only two stacks (push to top, pop from top, peek top, size/empty). Support `push(x)`, `pop()` (remove and return the front), `peek()` (return the front) and `empty()`. Calls to `pop`/`peek` are always valid.
Example: `push(1), push(2), peek() → 1, pop() → 1, empty() → False`.
Constraints: `1 <= x <= 9`; up to 100 calls. Follow-up: amortized O(1) per operation.

*Before scrolling: write the operations table, the question behind each operation, your structures and an invariant sentence. Then compare with §4.2.*

### 3.3 Design Browser History (1472)

**Problem (paraphrased).** A browser with one tab starts on `homepage`. Implement:
- `visit(url)`: go to `url` from the current page. **All forward history is cleared.**
- `back(steps)`: move back up to `steps` pages (stop at the first page); return the current URL.
- `forward(steps)`: move forward up to `steps` pages (stop at the last page that exists); return the current URL.

Example: start at `"leetcode.com"`; visit `"google.com"`, `"facebook.com"`, `"youtube.com"`; `back(1)` → `"facebook.com"`; `back(1)` → `"google.com"`; `forward(1)` → `"facebook.com"`; visit `"linkedin.com"` (clears youtube); `forward(2)` → `"linkedin.com"`; `back(2)` → `"google.com"`; `back(7)` → `"leetcode.com"`.
Constraints: `1 <= steps <= 100`; up to 5000 calls.

*Before scrolling: write the operations table, the question behind each operation, your structures and an invariant sentence. Then compare with §4.3.*

### 3.4 Insert Delete GetRandom O(1) (380)

**Problem (paraphrased).** Implement a set with `insert(val)` (add if absent, return whether it was added), `remove(val)` (remove if present, return whether it was removed) and `getRandom()` (return a uniformly random current element; only called when non-empty). **Each in O(1) average time.**
Example: `insert(1) → True, remove(2) → False, insert(2) → True, getRandom() → 1 or 2, remove(1) → True, insert(2) → False, getRandom() → 2`.
Constraints: values fit in 32 bits; up to 2·10⁵ calls.

*Before scrolling: write the operations table, the question behind each operation, your structures and an invariant sentence. Then compare with §4.4.*

### 3.5 Time Based Key-Value Store (981)

**Problem (paraphrased).** Store values for keys at different times. `set(key, value, timestamp)` records `value` for `key` at `timestamp`. `get(key, timestamp)` returns the value set for `key` at the **largest timestamp ≤ `timestamp`**, or `""` if there is none.
Example: `set("foo","bar",1)`, `get("foo",1) → "bar"`, `get("foo",3) → "bar"`, `set("foo","bar2",4)`, `get("foo",4) → "bar2"`, `get("foo",5) → "bar2"`. Also `get("foo",0) → ""`.
Constraints: **timestamps passed to `set` are strictly increasing**; up to 2·10⁵ calls.

*Before scrolling: write the operations table, the question behind each operation, your structures and an invariant sentence. Then compare with §4.5.*

### 3.6 Number of Recent Calls (933)

**Problem (paraphrased).** `RecentCounter` has `ping(t)`: record a request at time `t` (milliseconds) and return how many requests happened in the inclusive range `[t - 3000, t]`. Every call uses a **strictly larger** `t` than the previous one.
Example: `ping(1) → 1`, `ping(100) → 2`, `ping(3001) → 3`, `ping(3002) → 3` (the request at 1 is now outside `[2, 3002]`).
Constraints: `1 <= t <= 10^9`; up to 10⁴ calls.

*Before scrolling: write the operations table, the question behind each operation, your structures and an invariant sentence. Then compare with §4.6.*

### 3.7 Rate limiter (your Microsoft interview question)

You were asked this in person at Microsoft. In the real interview most details weren't given: asking for them was part of the problem.

**Problem (as you remembered it).** Design a rate limiter with two methods:
- `request(userId, timestamp)`: should this request be allowed? Each user may make at most some number of requests within a time window.
- `clearAllOld(...)`: throw away stored requests that no longer matter.

Interviewer's follow-up: `clearAllOld` must **only touch the requests that are actually expired**, not do work for every user.

No examples or constraints were given. Write your clarifying questions first (what the limit is, what the window includes, and so on), then design.

*Before scrolling: write the operations table, the question behind each operation, your structures and an invariant sentence. Then compare with §4.7.*

### 3.8 LRU Cache (146)

**Problem (paraphrased).** Design a cache with a fixed `capacity`:
- `get(key)`: return the key's value if it's in the cache, otherwise `-1`.
- `put(key, value)`: set the key's value (update it if the key exists, insert it otherwise). If inserting makes the number of keys exceed `capacity`, evict the **least recently used** key. Both a `get` and a `put` of a key count as "using" it.

`get` and `put` must each run in **O(1) average time**.

Example (capacity 2): `put(1,1)`, `put(2,2)`, `get(1) → 1`, `put(3,3)` (evicts key 2), `get(2) → -1`, `put(4,4)` (evicts key 1), `get(1) → -1`, `get(3) → 3`, `get(4) → 4`.
Constraints: `1 <= capacity <= 3000`; `0 <= key <= 10^4`; `0 <= value <= 10^5`; up to 2·10⁵ calls.

*Before scrolling: write the operations table, the question behind each operation, your structures and an invariant sentence. Then compare with §4.8.*

---

> **Answers start here.** Everything below this line names the structures for the problems in §3.

## 4. Solutions: the structures, invariants and code

Each solution follows the same order: **operations table → why one structure isn't enough → the combination and its invariant → code → trace → complexity → follow-ups.**

### 4.1 Store the derived answer with each entry: Min Stack (155)

| operation | question | plain stack alone? |
|---|---|---|
| push / pop / top | the newest item | ✓ O(1) |
| getMin | the minimum of what's in the stack **now** | ✗ O(n) scan |

**Why a single "current min" variable fails:** after you pop the minimum, you don't know the *next* smallest without scanning.

**The idea: store the derived answer with each entry.** The minimum of the stack depends only on what's below it, and what's below an entry never changes while that entry is on the stack. So when you push, record "the minimum of the stack up to and including me." When you pop, the entry below still has *its* correct minimum.

**Invariant:** `stack[i] = (value, min of stack[0..i])`.

```python
class MinStack:
    def __init__(self):
        self.stack = []                  # entries: (value, min of the stack up to and including this entry)

    def push(self, val):
        current_min = val if not self.stack else min(val, self.stack[-1][1])
        self.stack.append((val, current_min))

    def pop(self):
        self.stack.pop()                 # the entry below already holds ITS correct minimum

    def top(self):
        return self.stack[-1][0]

    def getMin(self):
        return self.stack[-1][1]
```

Trace: push 5, 3, 7, 3, 1, then pop (from running it):

| call | stack after (value, min so far) | getMin |
|---|---|---|
| push 5 | (5,5) | 5 |
| push 3 | (5,5) (3,3) | 3 |
| push 7 | (5,5) (3,3) (7,3) | 3 |
| push 3 | (5,5) (3,3) (7,3) (3,3) | 3 |
| push 1 | … (3,3) (1,1) | 1 |
| pop | (5,5) (3,3) (7,3) (3,3) | **3**: restored with no scan |

**All O(1); O(n) space.** **Generalizes to:** any "aggregate of everything so far" that must survive removals from one end: max stack, a stack's running sum, "minimum in the queue" (with two such stacks, §4.2).

### 4.2 Amortized O(1): Queue using two stacks (232)

**Name the two roles:** `inbox` receives new items (newest on top). `outbox` holds items **in removal order** (oldest on top). Moving everything from `inbox` to `outbox` reverses it, so the oldest ends up on top.

**Invariant:** the queue's order is: `outbox` from top to bottom, then `inbox` from bottom to top. **Only refill `outbox` when it's empty**, or the order breaks.

```python
class MyQueue:
    def __init__(self):
        self.inbox = []                  # newest on top
        self.outbox = []                 # oldest on top (removal order)

    def push(self, x):
        self.inbox.append(x)

    def _refill(self):
        if not self.outbox:              # ONLY when empty: otherwise newer items would jump ahead
            while self.inbox:
                self.outbox.append(self.inbox.pop())

    def pop(self):
        self._refill()
        return self.outbox.pop()

    def peek(self):
        self._refill()
        return self.outbox[-1]

    def empty(self):
        return not self.inbox and not self.outbox
```

**Why it's O(1) amortized** (core idea 8): one `pop` can move n items, which is O(n) for that call. But follow a single item through its life: pushed onto `inbox` once, moved to `outbox` once, popped once. **At most 3 operations per item, ever.** Over m calls, total work ≤ 3m, so the average per call is O(1). That's the same counting argument as the sliding window in lecture 006 §8 ("each element moves at most once"), and the rate limiter in §4.7 uses it too.

### 4.3 An array plus a cursor: Browser History (1472)

This one is mostly an **index problem**, and that's why it's here: it's lecture 008's name → valid set → test, inside a design.

**Name the three values:**

| Name | Stands for | Valid set |
|---|---|---|
| `pages` | every page in the history, oldest first (may contain stale entries past `last`) | — |
| `cur` | box index of the page you're on | `0 … last` |
| `last` | box index of the last page you can go **forward** to | `cur … len(pages) - 1` |

`back` and `forward` are then **clamping into the valid set**: `back` can't go below 0; `forward` can't go above `last`.

```python
class BrowserHistory:
    def __init__(self, homepage):
        self.pages = [homepage]
        self.cur = 0                     # box index of the current page
        self.last = 0                    # box index of the furthest page you can go forward to

    def visit(self, url):
        self.cur += 1
        if self.cur < len(self.pages):
            self.pages[self.cur] = url   # overwrite a stale entry: O(1), no slicing
        else:
            self.pages.append(url)
        self.last = self.cur             # everything after cur is now "cleared"

    def back(self, steps):
        self.cur = max(0, self.cur - steps)            # clamp to the valid set's lower end
        return self.pages[self.cur]

    def forward(self, steps):
        self.cur = min(self.last, self.cur + steps)    # clamp to the valid set's upper end
        return self.pages[self.cur]
```

**Design point:** "clear forward history" doesn't delete anything. It just moves `last`. Entries beyond `last` are stale and get overwritten later. That makes `visit` O(1) instead of O(n) for slicing. **Changing what a boundary means is often cheaper than changing the data.** (Two stacks, back and forward, is the other standard answer, also O(1) per step.)

### 4.4 Dict + array, swap with last: Insert Delete GetRandom O(1) (380)

| operation | question | dict/set | list |
|---|---|---|---|
| insert | is it present? then add | ✓ | ✗ presence is O(n) |
| remove | is it present? where? then delete | ✓ | ✗ O(n) to find, O(n) to delete from the middle |
| getRandom | pick a uniform element | ✗ no O(1) "element number i" | ✓ `random.choice` |

Neither alone works. **Combine:**

- **Source of truth:** `items`, a list of the elements (gives O(1) random access).
- **Index:** `index_of`, a dict from value to its position in `items` (gives O(1) presence and position).
- **Invariant:** `items` holds each element exactly once, and `index_of[v] == i` exactly when `items[i] == v`.

**The trick for O(1) removal from a list: swap with the last element, then pop the end.** Order in `items` doesn't matter (it's a set), so fill the hole with the last element instead of shifting everything.

```python
import random

class RandomizedSet:
    def __init__(self):
        self.items = []                  # source of truth: each element once, any order
        self.index_of = {}               # index: value -> its position in items

    def insert(self, val):
        if val in self.index_of:
            return False
        self.index_of[val] = len(self.items)   # its position will be the current length (the next box)
        self.items.append(val)
        return True

    def remove(self, val):
        if val not in self.index_of:
            return False
        i = self.index_of[val]           # the hole
        last = self.items[-1]
        self.items[i] = last             # move the last element into the hole
        self.index_of[last] = i          # ...and update ITS index (the step people forget)
        self.items.pop()                 # drop the now-duplicate end
        del self.index_of[val]           # AFTER updating last: covers the case val IS last
        return True

    def getRandom(self):
        return random.choice(self.items)
```

Trace: insert 10, 20, 30, 40, then remove 20 (from running it):

```
before:  items = [10, 20, 30, 40]   index_of = {10:0, 20:1, 30:2, 40:3}
remove 20:  hole i = 1, last = 40 → items[1] = 40, index_of[40] = 1, pop, delete 20
after:   items = [10, 40, 30]       index_of = {10:0, 30:2, 40:1}
```

**Order matters in `remove`:** if `val` is the last element, then `last == val`, and the code writes `index_of[val] = i` and then deletes it, so it ends up correctly absent. Deleting first and updating `last` second would re-insert `val`. Trace the "remove the last element" case every time you write this. It's the edge case for this pattern.

### 4.5 Dict of sorted lists + binary search: Time Based Key-Value Store (981)

| operation | question | structure |
|---|---|---|
| set | append a (time, value) under a key | dict of lists: **append keeps each list sorted**, because timestamps only increase (a clarifying question that pays off) |
| get | "the last time ≤ t" within one key's list | binary search (lecture 004) |

**Name the search:** in `times` (sorted), the answer is the **last** time ≤ `t`. In first-True terms (lecture 004): find the first index whose time is **> t**, then step one back. That's `bisect_right(times, t) - 1`.

```python
import bisect
from collections import defaultdict

class TimeMap:
    def __init__(self):
        self.times = defaultdict(list)   # key -> timestamps, increasing (append keeps them sorted)
        self.values = defaultdict(list)  # key -> values, same positions as times

    def set(self, key, value, timestamp):
        self.times[key].append(timestamp)
        self.values[key].append(value)

    def get(self, key, timestamp):
        times = self.times.get(key)      # .get: don't create an entry just by reading
        if not times:
            return ""
        i = bisect.bisect_right(times, timestamp)   # first index with time > timestamp (a cut, 0..n)
        if i == 0:
            return ""                    # every stored time is after `timestamp`
        return self.values[key][i - 1]   # the box just before that cut: the last time <= timestamp
```

The index logic is lecture 008 exactly: `i` is a **cut** (valid set `0 … n`); the box just before cut `i` is `i - 1`, which exists only when `i >= 1`.

**Invariant:** for every key, `times[key]` and `values[key]` have the same length and line up position by position. (A list of `(time, value)` pairs works too. Two parallel lists just make `bisect` simpler.)

**Follow-up:** "what if timestamps aren't increasing?" Then append no longer keeps the list sorted. You'd insert with `bisect.insort` (O(n) per set) or use a balanced tree / sorted container. Asking about the timestamp order in step 1 is what makes this design O(1) / O(log n).

### 4.6 A queue as a sliding window over time: Number of Recent Calls (933)

This is the sliding window from lecture 006, measured in **time** instead of array positions: new pings join at the back, and old pings leave from the front. A `deque` is exactly that.

**Name the boundary** (C1): `cutoff = t - 3000`. A ping `p` is still counted when `cutoff <= p <= t`, so it should leave when **`p < cutoff`**.

```python
from collections import deque

class RecentCounter:
    def __init__(self):
        self.recent = deque()            # pings inside the window, oldest at the front

    def ping(self, t):
        self.recent.append(t)
        cutoff = t - 3000                # pings at or after cutoff are still counted
        while self.recent[0] < cutoff:   # oldest is outside the window
            self.recent.popleft()
        return len(self.recent)
```

Amortized O(1): each ping is appended once and removed at most once (§4.2's argument). Space: at most the number of pings in a 3000 ms window. This is the core of the rate limiter.

### 4.7 Your interview question: the rate limiter, designed step by step

You were asked this in person at Microsoft. Here it is again, the way you'd want to run it in an interview, using the method from §1.

**The question as you remembered it:** design a rate limiter with `request(userId, timestamp)` (should this request be allowed?) and `clearAllOld()` (throw away requests that no longer matter). The interviewer pushed back on your first design because `clearAllOld` looked at every user, and asked for a version that **only touches the requests that are actually expired.**

#### Step 1: Clarifying questions (and the answers this design assumes)

| Question | Assumed answer | Why it matters |
|---|---|---|
| What's the limit? | at most `limit` **allowed** requests per user in any window of `window` seconds | the core rule |
| Does the window include its boundary? | a request at time `p` counts at time `now` when `p > now - window` | decides `<` vs `<=` (C1: name `cutoff`, write the valid set) |
| Do rejected requests count toward the limit? | **no** (only allowed ones are recorded) | changes what gets stored |
| Do timestamps only increase (across all users)? | **yes, non-decreasing** | lets a single queue stay sorted by append, just like TimeMap |
| What does `clearAllOld` take? | the current time, `clearAllOld(now)` | it needs a `now` to know what's old |
| Single-threaded? | yes, for now (follow-up below) | |

Asking these out loud is a big part of the score. You'll notice that two of them (boundary, increasing timestamps) are exactly what makes the design simple.

#### Step 2: Operations table

```
operation            | must answer / do                                   | target
request(user, now)   | how many of THIS user's requests are in the window? | O(1) amortized
                     | record it if allowed                                |
clear_all_old(now)   | which requests (of ANY user) are now expired?       | O(number expired)
                     | remove them everywhere                              |
```

#### Step 3–4: The questions and the structures

| Question | Best structure |
|---|---|
| "How many of user u's requests are in the window?" | per-user `deque` of timestamps (oldest at the front): a RecentCounter per user (§4.6) |
| "Which requests, across all users, are expired?" | **one global `deque`** of `(timestamp, user)`, oldest at the front: expired requests are exactly a prefix of it |

Your first design had only the per-user deques. Then `clearAllOld` has to visit every user, even users with nothing expired. The interviewer's requirement ("only touch expired requests") is a question that only a **global, time-ordered** structure can answer. That's the moment a design problem turns into a combination problem.

#### Step 5: Combine, with an invariant

Two structures now hold the same requests, and that's the hazard you correctly spotted in the interview: *"If I clear out those requests [from a user's queue]… those same requests will still be in my global queue."*

The fix is to decide **who is allowed to remove things**:

- **Only `clear_all_old` removes requests,** and it removes each one from **both** structures at once.
- `request` **calls `clear_all_old(now)` first**, so the per-user deque is always up to date before you count it.

**Invariant:** *the global queue contains exactly the union of all per-user deques, in time order; and no user is stored with an empty deque.*

Why removing from both at once is easy: both are ordered by time. The oldest request in the global queue, say `(t, u)`, must also be the **oldest** request in `u`'s deque (any older request of `u`'s would be older in the global queue too). So `by_user[u].popleft()` removes exactly that request, with no searching.

#### Step 6: Code

```python
from collections import deque

class RateLimiter:
    def __init__(self, limit, window):
        self.limit = limit
        self.window = window
        self.by_user = {}                 # user -> deque of their allowed timestamps (oldest first); no empty deques
        self.all_requests = deque()       # (timestamp, user) for every stored request, oldest first

    def clear_all_old(self, now):
        cutoff = now - self.window        # a request at time t is still in the window when t > cutoff
        while self.all_requests and self.all_requests[0][0] <= cutoff:
            t, user = self.all_requests.popleft()   # oldest overall...
            user_times = self.by_user[user]
            user_times.popleft()                     # ...is also this user's oldest: remove from BOTH
            if not user_times:
                del self.by_user[user]               # keep the invariant: no empty deques

    def request(self, user, now):
        self.clear_all_old(now)           # bring both structures up to date first
        user_times = self.by_user.get(user)
        if user_times is not None and len(user_times) >= self.limit:
            return False                  # rejected requests are not recorded
        if user_times is None:
            user_times = deque()
            self.by_user[user] = user_times
        user_times.append(now)            # add to BOTH structures
        self.all_requests.append((now, user))
        return True
```

#### Step 7: Trace (limit 2 per 10 seconds; from running it)

| call | returns | `by_user` after | `all_requests` after |
|---|---|---|---|
| request("a", 0) | True | a: [0] | (0,a) |
| request("b", 1) | True | a: [0], b: [1] | (0,a) (1,b) |
| request("a", 2) | True | a: [0, 2], b: [1] | (0,a) (1,b) (2,a) |
| request("a", 5) | **False**: a already has 2 in (−5, 5] | unchanged | unchanged |
| request("a", 11) | True: cutoff 1 expires (0,a) and (1,b); b's deque empties, so b is deleted | a: [2, 11] | (2,a) (11,a) |
| request("b", 12) | True: cutoff 2 expires (2,a) | a: [11], b: [12] | (11,a) (12,b) |

Check the invariant on every row: the global queue's pairs are exactly the per-user timestamps. In testing, that check ran after every call on 2,000 random sequences.

#### Step 8: Complexity and follow-ups

- **Time:** `clear_all_old` costs O(number of requests it removes). Each stored request is added once and removed once, so **`request` is O(1) amortized** (§4.2).
- **Space:** O(number of allowed requests inside the current window), never more.

| Follow-up | Answer |
|---|---|
| "Memory per user is too high for high limits" | **Fixed-window counter** (count per user per time bucket; O(1) memory, but allows bursts at bucket edges) or a **token bucket** (store `tokens` and `last_refill_time` per user; refill on each request; O(1) memory, smooth limiting) |
| "Many threads call `request`" | a lock around `request`/`clear_all_old`, or per-user locks plus a separate cleanup thread; the shared global queue is the contention point |
| "Many servers" | the state moves to a shared store (commonly Redis with atomic increments or sorted sets), which is the step into system design |
| "Timestamps can arrive out of order" | the global queue is no longer sorted by append; you'd need a heap keyed by timestamp (pop expired from the top), at O(log n) per operation |

What happened in the interview, in this lecture's terms: you reached step 5 live (the global queue) and saw the consistency hazard on your own. What was missing was the **rule that removes the hazard** ("only one method removes, and it removes from both") plus the **invariant sentence**. That rule is a skill you can practise, and §5 is about it.

### 4.8 Dict + doubly linked list: LRU Cache (146), as a design story

The full code and the "why a doubly linked list" explanation are in lecture 010 §8–9. Here it is in the §1 method, to show the same reasoning applies:

| operation | question | structure |
|---|---|---|
| get(key) | where is key k? | dict: key → node |
| get / put "mark as most recent" | move this item to the newest end | doubly linked list: O(1) remove + O(1) add at front |
| put "evict LRU" | which key is oldest by use? | the list's other end (`tail.prev`) |

- **Source of truth:** the linked list (it holds the order and the values).
- **Index:** the dict (a shortcut to each node).
- **Invariant:** *the dict's keys are exactly the list's keys, each mapped to its node, and the list is ordered from most to least recently used.*
- **Helpers:** `_remove(node)`, `_add_front(node)`. Every public method is built from them, so the invariant can't drift.
- **Detail that follows from the invariant:** each node stores its **key**, because eviction finds the node through the list and must then delete the key from the dict.

**LFU (460, hard)** extends this: a dict from key to node, plus a dict from **frequency to its own doubly linked list**, plus a `min_freq` variable. It's the same method with one more index. Read it after LRU is automatic.

---

## 5. Invariants and consistency: the core skill

Every combination above has the same shape: **one source of truth, one or more indexes, one invariant sentence, and helpers that update everything together.** Most bugs in design problems are violations of that:

| Bug | Pattern it breaks |
|---|---|
| Evicting from the list but not deleting the key from the dict (LRU) | an index points to a removed item |
| Moving the last element into the hole but not updating its position (RandomizedSet) | the index has a wrong position |
| Removing a request from a user's deque in `request` but leaving it in the global queue (your first rate limiter) | two structures disagree; later cleanup removes the wrong thing |
| A separate `size` counter that isn't updated on every path (your August LRU kept one) | a derived value drifts from the data |

### 5.1 Four rules

1. **Write the invariant as a comment at the top of the class.** One or two sentences: what each structure stands for and how they relate.
2. **Prefer computing over storing.** `len(self.node_of)` can't drift; a `self.size` counter can. Store a derived value only when recomputing it is too slow (Min Stack is the case where it is).
3. **Only helpers mutate.** Public methods call `_add`/`_remove`-style helpers that change all structures together. Then there are only one or two places to get right.
4. **Order of updates inside a helper matters.** Use save-before-overwrite (lecture 010 §2) and trace the edge cases: remove the only item, remove the last item (RandomizedSet), evict when capacity is 1.

### 5.2 A practice-only tool: `_check()`

While practising (not in the interview), add a method that asserts the invariant, and call it after every operation in your local tests:

```python
def _check(self):                                        # RandomizedSet
    assert len(self.items) == len(self.index_of)
    for v, i in self.index_of.items():
        assert self.items[i] == v
```

If a bug breaks the invariant, the assertion fails **on the call that broke it**, not ten calls later when a wrong answer finally shows up. It's the trace protocol's "first wrong row" (lecture 003), automated. That's how the RandomizedSet and the rate limiter in this lecture were verified.

---

## 6. Testing a design: the call-sequence trace

The lecture 003 protocol, adapted: **one row per call**, a column per structure, the return value, and an invariant ✓.

```
| call            | returns | structure A after | structure B after | invariant ✓ |
```

**Choose the call sequence to hit the edges:**

| Category | Example |
|---|---|
| empty | `get` on an empty cache; `remove` from an empty set |
| one item | insert one, remove it, insert again |
| at the boundary | capacity exactly reached; then one more (eviction) |
| capacity 1 | every `put` of a new key evicts |
| repeated key | `put` the same key twice (update, not insert) |
| the pattern's special case | RandomizedSet: remove the **last** element; TimeMap: `get` before the first timestamp; rate limiter: a request exactly `window` seconds after another |
| interleaving | an update to a key right after it was nearly evicted |

In an interview, trace 5–8 calls out loud with the structures drawn. That's usually what convinces the interviewer.

---

## 7. The interview: what to say, in what order

### 7.1 A 45-minute shape

| Time | You do | What it shows |
|---|---|---|
| 0–5 | Restate the problem; ask clarifying questions (§7.2); confirm the API | you don't build the wrong thing |
| 5–10 | Operations table; the question behind each; name candidate structures and why one isn't enough | reasoning, not recall |
| 10–12 | State the combination, the roles (truth vs index) and the invariant | design maturity |
| 12–30 | Write the class: invariant comment, helpers first, then the public methods | clean code |
| 30–38 | Trace a call sequence covering the edge cases | verification |
| 38–45 | Complexity per method; follow-ups (concurrency, scale, alternative designs) | depth |

### 7.2 Clarifying questions that come up again and again

- **Keys/values:** can keys repeat? Is `put` on an existing key an update? What types and ranges?
- **Capacity:** fixed? can it be 0? what happens when full?
- **Empty behaviour:** what do `get` / `pop` / `getRandom` return or do when empty?
- **Time:** do timestamps only increase? Is the window boundary inclusive? Are times integers?
- **Ties:** if two items are equally old or frequent, which goes?
- **Counting:** do rejected/failed operations count?
- **Scale & concurrency:** roughly how many calls? single-threaded?

### 7.3 Phrases worth having ready

- "Let me list the operations and what each one needs to answer quickly."
- "A dictionary gives me lookup but not order; a doubly linked list gives me order with O(1) moves, but not lookup. So I'll combine them."
- "The list is the source of truth; the dictionary is an index into it. The invariant is…"
- "Every mutation goes through these two helpers, so both structures always change together."
- "Each item is added once and removed once, so this is O(1) amortized."
- "If we needed this across multiple servers, the state would move to a shared store, and that's where it becomes system design."

---

## 8. Recognizing which structures a requirement needs

| Requirement in the problem | Reach for |
|---|---|
| "O(1) lookup by key" | dict |
| "…and evict least recently used / move to front" | + doubly linked list with sentinels (§4.8) |
| "…and get a random element" | + array, swap-with-last removal (§4.4) |
| "…and the value at time t / latest version ≤ t" | + per-key sorted list + `bisect` (§4.5) |
| "min / max of the current contents, with removal from one end" | store the aggregate with each entry (§4.1) |
| "min / max of a changing set, any removals" | heap (with lazy deletion) or a sorted structure (lecture 014) |
| "count of events in the last T" | deque as a time window (§4.6) |
| "…per user, and clean up only expired" | per-user deques + a global time-ordered deque (§4.7) |
| "FIFO using only stacks" / "undo + redo" | two stacks (§4.2, §4.3) |
| "back / forward through history" | array + cursor + boundary, or two stacks (§4.3) |
| "least *frequently* used" | dict + frequency → list + `min_freq` (LFU) |
| "median of a stream" | two heaps (lecture 014) |

---

## 9. Practice ladder

Do them in order. Each one adds one idea, and every problem's full statement is above. For each: write the operations table and the invariant **before** coding, use helpers, add a `_check()` while testing locally, and trace a call sequence that hits §6's edge cases.

| # | Problem | Pattern | Section |
|---|---|---|---|
| 1 | 155 Min Stack | derived answer per entry | §4.1 |
| 2 | 232 Implement Queue using Stacks | amortized O(1) | §4.2 |
| 3 | 933 Number of Recent Calls | deque as a time window | §4.6 |
| 4 | 1472 Design Browser History | array + cursor + boundary | §4.3 |
| 5 | 981 Time Based Key-Value Store | dict + sorted list + bisect | §4.5 |
| 6 | 380 Insert Delete GetRandom O(1) | dict + array, swap with last | §4.4 |
| 7 | 146 LRU Cache (redo) | dict + doubly linked list | §4.8, lecture 010 §9 |
| 8 | Rate limiter (your interview question) | per-user + global deques, invariant | §4.7 |
| stretch | 460 LFU Cache, 355 Design Twitter, 295 Find Median from Data Stream (after the heap lecture) | | |

For the rate limiter, do it as a **mock interview**: set a 45-minute timer, say the clarifying questions out loud, and write it without looking at §4.7. Then compare.

---

## Common mistakes

| Mistake | Fix |
|---|---|
| Choosing structures before listing the operations | operations table first (§1 step 2) |
| Using one structure and accepting an O(n) operation without saying so | name every operation's cost; combine when one misses its target |
| Two structures updated in different methods | only helpers mutate; each helper updates everything (§5.1) |
| Separate counters (`size`) that can drift | compute from the data (`len(...)`) |
| Not storing the key in the node (LRU) | eviction can't update the dict without it |
| RandomizedSet: forgetting `index_of[last] = i`, or deleting before updating | update the moved element, then delete; trace "remove the last element" |
| `list.pop(0)` / `list.insert(0, x)` as "O(1)" | they're O(n): use `deque` |
| TimeMap: `bisect_left` instead of `bisect_right`, or no `i == 0` check | "last time ≤ t" = `bisect_right(...) - 1`, valid only when the cut is ≥ 1 |
| Window boundary guessed (`<` vs `<=`) | name `cutoff`, write the valid set (§4.6, §4.7) |
| No clarifying questions | the interviewer often holds back a constraint that makes the problem simpler |
| Silent coding | narrate roles, invariant and complexity: it's half the score |

---

## Self-check questions

1. What are the first two things you write in a design problem, before choosing any structure?
<details><summary>Answer</summary>

The API (method signatures with meanings, after clarifying questions) and the operations table: each operation, the question it must answer, and its required complexity.
</details>

2. Why can't Min Stack keep a single `current_min` variable?
<details><summary>Answer</summary>

After popping the minimum, the next minimum is unknown without a scan. Storing "min so far" with each entry means the entry below always holds its own correct minimum.
</details>

3. In the two-stack queue, why must `outbox` be refilled only when it's empty?
<details><summary>Answer</summary>

`outbox` holds older items in removal order. Moving `inbox` items on top while `outbox` still has items would put newer items ahead of older ones.
</details>

4. Explain why the two-stack queue is O(1) amortized even though one `pop` can take O(n).
<details><summary>Answer</summary>

Each item is pushed to `inbox` once, moved to `outbox` once and popped once, so there are at most 3 operations per item over its whole life. Total work over m calls is O(m), so O(1) per call on average.
</details>

5. In Browser History, how does `visit` "clear forward history" in O(1)?
<details><summary>Answer</summary>

It sets `last = cur`. Entries beyond `last` become stale (outside the valid set) and are overwritten later. Nothing is deleted.
</details>

6. In RandomizedSet, which two structures are used, which is the source of truth, and what's the invariant?
<details><summary>Answer</summary>

A list `items` (source of truth: O(1) random access) and a dict `index_of` (index: value → position). Invariant: each element appears once in `items`, and `index_of[v] == i` exactly when `items[i] == v`.
</details>

7. Walk through `remove(val)` when `val` is the last element. Why does the order of the last two dict operations matter?
<details><summary>Answer</summary>

`i` is the last position and `last == val`. `items[i] = last` changes nothing, `index_of[val] = i` rewrites the same entry, `pop` removes it from the list, and `del index_of[val]` removes it from the dict. If the `del` came before `index_of[last] = i`, that line would put `val` back into the dict.
</details>

8. In TimeMap, why is it `bisect_right(times, t) - 1`, and when is there no answer?
<details><summary>Answer</summary>

`bisect_right` returns the first cut after every time ≤ t (the first index with time > t). The last time ≤ t is the box just before that cut, `i - 1`. If `i == 0`, every stored time is after t, so return `""`.
</details>

9. Which clarifying answer makes TimeMap's `set` O(1)?
<details><summary>Answer</summary>

Timestamps passed to `set` are strictly increasing, so appending keeps each key's list sorted with no insertion cost.
</details>

10. In RecentCounter, name the boundary and state when a ping leaves the window.
<details><summary>Answer</summary>

`cutoff = t - 3000`. A ping `p` is counted when `cutoff <= p <= t`, so it leaves when `p < cutoff`.
</details>

11. In the rate limiter, why can `clear_all_old` remove from the user's deque with `popleft()` and no searching?
<details><summary>Answer</summary>

Both structures are ordered by time. The oldest request overall, `(t, u)`, must also be `u`'s oldest stored request, so it's at the front of `u`'s deque.
</details>

12. State the rate limiter's invariant, and the rule that keeps the two structures consistent.
<details><summary>Answer</summary>

The global queue contains exactly the union of all per-user deques, in time order, and no user has an empty deque. Rule: only `clear_all_old` removes requests, and it removes each one from both structures. `request` calls it first, then adds the new request to both.
</details>

13. Give two lower-memory alternatives to storing every timestamp in a rate limiter, and the trade-off of each.
<details><summary>Answer</summary>

A fixed-window counter (O(1) per user, but allows bursts at window edges) and a token bucket (O(1) per user, smooth limiting, but approximates "N per window" as a refill rate).
</details>

14. Why should LRU nodes store their key?
<details><summary>Answer</summary>

Eviction finds the victim through the list (`tail.prev`), then must delete its key from the dict. The node is the only O(1) way to know that key.
</details>

---

## Sources

- Problems: LeetCode 155, 232, 1472, 380, 981, 933, 146 (stretch 460, 355, 295). Statements paraphrased; examples and constraints from long-standing problem pages (from my own knowledge, not re-fetched; 2026-10-12). The rate-limiter question is reconstructed from your own notes on your interview (`001_practice_medium.py`).
- Python: `collections.deque` and `defaultdict` (https://docs.python.org/3/library/collections.html), `bisect` (https://docs.python.org/3/library/bisect.html), `random.choice` (https://docs.python.org/3/library/random.html#random.choice), time complexity of built-ins (https://wiki.python.org/moin/TimeComplexity).
- Rate-limiting algorithms (sliding window log, fixed window counter, token bucket) are standard techniques, covered in most system-design references.
- Amortized analysis of the two-stack queue: Cormen et al., *Introduction to Algorithms*, chapter on amortized analysis.
- Verification (2026-10-12): every class was checked against a brute-force reference model on 2,000 random sequences of 20–40 calls. RandomizedSet's and the rate limiter's invariants were asserted after every call. `getRandom` was sampled 40,000 times on 4 elements (each ~25%). Traces were produced by running the code.
