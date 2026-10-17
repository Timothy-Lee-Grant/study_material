# Lecture 013: Stacks: Unresolved Items, Two-Stack Machines, Saved State and Monotonic Stacks

> **For:** Timothy · **Date:** 2026-10-17
> **Prerequisites:** lecture 012 §3.2–3.3 (the queue and browser problems; you've already attempted Browser History), lecture 008 (name → valid set → test), lecture 003 (tracing). Lecture 002 (recursion) helps for §5.
> **Why this lecture:** you said stacks are unfamiliar, and two things confused you. First, how two stacks "morph" into a queue, and the rule that seems to "guard against something or clear things out all at the same time." Second, your own two-stack Browser History works without that rule: *"I did not magically create a queue in this problem. Even though I have two stacks, and I think that I am using them in the exact same way!"* You also said that interleaving operations made you uneasy, as if some order of calls might break things. §2 and §3 answer those questions directly. The rest builds the stack patterns you'll meet most: saved state (§4–5) and monotonic stacks (§6).
> **The one-sentence answer to your question (derived in §2):** the two machines use the same moves, but the stack **tops stand for different things**. In your browser, both tops sit next to the current page, so the item you need next is always on a top. In the queue, the item you need next (the oldest) ends up at the **bottom** of `inbox`. The only way to reach a bottom is to move everything above it, and that move is only correct when nothing older is in the way.
> **Format notes:** every problem has its full statement (paraphrased), examples and constraints. Every name is defined before it's used. No firmware analogies.
> **Verification:** every function and class here was run against a brute-force reference: 5,000 random bracket strings, 2,000 random browser sessions, 2,000 random queue sequences, 3,000 random RPN expressions, 3,000 random paths (against Python's `posixpath.normpath`), 2,000 random nested decode strings, and 3,000 random cases each for Daily Temperatures and Car Fleet. Every trace was produced by running the code.

---

## Core ideas (the answer key)

1. **A stack is a Python list used at one end only:** `append` to push, `pop()` to pop, `[-1]` to look at the top. All three are O(1). Check `if stack` before popping or peeking.
2. **Your model is the right one:** a stack holds **unresolved items**, and it fits when *the next thing to resolve is always the most recent unresolved one* (an inner bracket must close before an outer one).
3. **Before you use a stack, say what its top stands for.** "The top is the current page." "The top is the oldest item, the next to leave." Most stack confusion is not knowing what the top means.
4. **Two stacks with their tops facing each other** (Browser History) act as a **cursor in a line**: moving one item moves the cursor one step, and order is always preserved.
5. **Two stacks with their bottoms facing each other** (the queue) act as a **line with two open ends**: one end for adding, one for removing. When the removing side runs out, the next item is at the other stack's bottom, so you must move *everything*, and only when the removing side is empty.
6. **Interleaved calls are safe when one sentence (the invariant) is true after every method.** Check each method once against the sentence, and every possible sequence of calls is covered.
7. **A stack can save context to come back to:** the string so far and a repeat count (Decode String), the directories so far (Simplify Path), operands waiting for an operator (RPN). This is what recursion's call stack does for you automatically.
8. **A monotonic stack holds items that are still waiting for an answer**, kept in sorted order. Each new item pops (and answers) every waiting item it beats, then waits itself. "Next greater/warmer/smaller to the right" is the signal.
9. **Each item is pushed once and popped at most once**, so a loop with an inner `while stack and …: pop` is O(n) overall, not O(n²).

---

## Table of Contents

- [0. A stack in Python, and how to draw one](#0-a-stack-in-python-and-how-to-draw-one)
- [1. Your model: a stack of unresolved items (Valid Parentheses, 20)](#1-your-model-a-stack-of-unresolved-items-valid-parentheses-20)
- [2. Two stacks, two different machines](#2-two-stacks-two-different-machines)
  - [2.1 Your Browser History: tops facing each other](#21-your-browser-history-tops-facing-each-other)
  - [2.2 Queue using two stacks: bottoms facing each other](#22-queue-using-two-stacks-bottoms-facing-each-other)
  - [2.3 Why the queue needs the rule and your browser doesn't](#23-why-the-queue-needs-the-rule-and-your-browser-doesnt)
- [3. Interleaving: why any order of calls is safe](#3-interleaving-why-any-order-of-calls-is-safe)
- [4. Stacks that save state: Evaluate RPN (150) and Simplify Path (71)](#4-stacks-that-save-state-evaluate-rpn-150-and-simplify-path-71)
- [5. Saving context at a bracket: Decode String (394)](#5-saving-context-at-a-bracket-decode-string-394)
- [6. Monotonic stacks: Daily Temperatures (739) and Car Fleet (853)](#6-monotonic-stacks-daily-temperatures-739-and-car-fleet-853)
- [7. Recognizing a stack problem](#7-recognizing-a-stack-problem)
- [8. Python pitfalls](#8-python-pitfalls)
- [9. Practice ladder](#9-practice-ladder)
- [Common mistakes](#common-mistakes)
- [Self-check questions](#self-check-questions)
- [Sources](#sources)

---

## 0. A stack in Python, and how to draw one

A **stack** is a collection where you can only add or remove at one end, called the **top**. The last item added is the first one removed ("last in, first out"). In Python a stack is a plain list, and the **top is the right end**:

| Operation | Python | Cost |
|---|---|---|
| push x | `stack.append(x)` | O(1) amortized |
| pop (remove and return the top) | `stack.pop()` | O(1) |
| peek (look at the top) | `stack[-1]` | O(1) |
| is it empty? | `not stack` | O(1) |
| size | `len(stack)` | O(1) |

`stack.pop()` and `stack[-1]` on an **empty** list raise `IndexError`. So almost every stack loop has the shape `while stack and <condition on stack[-1]>:`. The `stack and` part is the guard, and it must come first, because `and` stops as soon as the left side is false.

**How to draw a stack in a trace:** exactly as Python prints it, bottom on the left, top on the right: `['{', '[']` means `'{'` is at the bottom and `'['` is on top. If you always draw it this way, your hand trace and a `print(stack)` line up, and you never have to translate.

---

## 1. Your model: a stack of unresolved items (Valid Parentheses, 20)

You described a stack as a way to keep **unresolved items**, with brackets as the example. That's the core use, and it's worth seeing exactly *why* a stack is the right container for them.

**Problem (paraphrased).** Given a string `s` made only of the characters `( ) [ ] { }`, return `True` if it's valid: every opening bracket is closed by the same type of bracket, brackets close in the correct order (an inner pair closes before the outer one), and every closing bracket has a matching opener.
Examples: `"()"` → `True`; `"()[]{}"` → `True`; `"(]"` → `False`; `"([)]"` → `False`; `"{[]}"` → `True`.
Constraints: `1 <= len(s) <= 10^4`.

**Why the most recent unresolved opener is the one that must close next.** Suppose `{` is open and then `[` opens. The `[` is inside the `{`. A valid string must close the inside before the outside, so the next closer must close `[`, the **most recently opened** bracket that's still unresolved. That's exactly "last in, first out." So:

- **Name:** `stack` holds the openers that haven't been closed yet, in the order they were opened. **Its top is the opener the next closer must match.**
- An opener: push it (it's now unresolved).
- A closer: it must match the top. If the stack is empty (nothing to close) or the top is the wrong type, the string is invalid. Otherwise pop (that opener is resolved).
- At the end, the string is valid only if nothing is left unresolved.

```python
def isValid(s):
    match = {")": "(", "]": "[", "}": "{"}   # closer -> the opener it needs
    stack = []                               # unresolved openers; top = the one the next closer must match
    for ch in s:
        if ch in match:                      # a closer
            if not stack or stack[-1] != match[ch]:
                return False                 # nothing to close, or the wrong type is on top
            stack.pop()                      # resolved
        else:                                # an opener
            stack.append(ch)
    return not stack                         # valid only if nothing is left unresolved
```

Traces (from running it):

| `"{[]}"` char | action | stack after |
|---|---|---|
| `{` | opener, push | `['{']` |
| `[` | opener, push | `['{', '[']` |
| `]` | matches top `[`, pop | `['{']` |
| `}` | matches top `{`, pop | `[]` → **True** |

| `"([)]"` char | action | stack after |
|---|---|---|
| `(` | opener, push | `['(']` |
| `[` | opener, push | `['(', '[']` |
| `)` | top is `[`, but `)` needs `(` | return **False** |

And `"(("` ends with `['(', '(']`, which is not empty, so **False**. Those three are the three ways to fail: wrong type on top, closer with nothing open, and openers left over. Test all three every time.

**O(n) time, O(n) space.**

**The signal for this pattern:** *does each new event resolve the most recent unresolved thing?* If yes, a stack holds the unresolved things.

---

## 2. Two stacks, two different machines

This section answers your question. You built Browser History with two stacks. The queue (232) also uses two stacks. You moved items between them in the same way in both: pop from one, push onto the other. Yet the queue needs a special rule ("only refill when `outbox` is empty, and then move everything") and your browser doesn't. The difference is **what each stack's top stands for**, and the clearest way to see it is to draw both stacks on one line.

### 2.1 Your Browser History: tops facing each other

**Problem (paraphrased).** A browser with one tab starts on `homepage`. Implement:
- `visit(url)`: go to `url` from the current page. **All forward history is cleared.**
- `back(steps)`: move back up to `steps` pages (stop at the first page); return the current URL.
- `forward(steps)`: move forward up to `steps` pages (stop at the last page that exists); return the current URL.

Example: start at `"leetcode.com"`; visit `"google.com"`, `"facebook.com"`, `"youtube.com"`; `back(1)` → `"facebook.com"`; `back(1)` → `"google.com"`; `forward(1)` → `"facebook.com"`; visit `"linkedin.com"` (clears youtube); `forward(2)` → `"linkedin.com"`; `back(2)` → `"google.com"`; `back(7)` → `"leetcode.com"`.
Constraints: `1 <= steps <= 100`; up to 5000 calls.

Your design, written out with each name defined:

| Name | Stands for | Its top stands for |
|---|---|---|
| `back_stack` | the current page and every page you can go back to | **the current page** |
| `forward_stack` | every page you can go forward to | **the page one step forward** |

Valid set: `back_stack` is never empty (you're always on some page).

```python
class BrowserHistory:
    def __init__(self, homepage):
        self.back_stack = [homepage]     # top = the current page; below it, pages you can go back to
        self.forward_stack = []          # top = the page one step forward

    def visit(self, url):
        self.back_stack.append(url)      # url becomes the current page
        self.forward_stack.clear()       # all forward history is gone

    def back(self, steps):
        while steps > 0 and len(self.back_stack) > 1:      # keep at least the current page
            self.forward_stack.append(self.back_stack.pop())
            steps -= 1
        return self.back_stack[-1]

    def forward(self, steps):
        while steps > 0 and self.forward_stack:
            self.back_stack.append(self.forward_stack.pop())
            steps -= 1
        return self.back_stack[-1]
```

Trace (start at A; from running it):

| call | returns | `back_stack` | `forward_stack` |
|---|---|---|---|
| visit B | | `['A', 'B']` | `[]` |
| visit C | | `['A', 'B', 'C']` | `[]` |
| visit D | | `['A', 'B', 'C', 'D']` | `[]` |
| back(2) | B | `['A', 'B']` | `['D', 'C']` |
| forward(1) | C | `['A', 'B', 'C']` | `['D']` |
| visit E | | `['A', 'B', 'C', 'E']` | `[]` |
| back(5) | A (stopped early) | `['A']` | `['E', 'C', 'B']` |

**Now draw both stacks on the history line.** After `back(2)` the history, oldest to newest, is `A B C D`, and you're on `B`. Write `back_stack` left to right (bottom to top), and write `forward_stack` **mirrored**, right to left (bottom to top), so its top is on the left:

```
history line:    A    B  |  C    D
back_stack:     [A    B]                 bottom A ... top B   (B = current page)
forward_stack:           [C    D]        top C ... bottom D   (the list is ['D', 'C'])
                      ↑     ↑
                     both tops sit next to the cursor "|"
```

**The two tops face each other at the cursor.** That's the whole reason your design works:

- `back` one step: pop `B` from `back_stack`'s top and push it onto `forward_stack`'s top. In the picture, `B` just crosses the cursor: `A | B C D`. The order on the line didn't change. Only the cursor moved.
- `forward` one step: the mirror image.
- `visit(url)`: everything to the right of the cursor is thrown away (`forward_stack.clear()`), and `url` is placed just left of the cursor, as the new current page.

**Why your multi-step pops are fine.** `back(steps)` is just `steps` single moves in a row. Each single move keeps the picture correct (the line's order is unchanged, the cursor moves one step), so any number of them does too. Your loop condition is the valid set: stop when `steps` runs out, or when only the current page is left (`len(self.back_stack) > 1` is "there's a page to go back to").

**Cost:** `visit` is O(1) amortized (`clear()` takes time for each page in `forward_stack`, but every one of those pages was put there by an earlier `back` step, so that work is already paid for). `back` and `forward` are O(steps), at most 100 by the constraints. Lecture 012 §4.3 has the array-and-cursor design where `back` and `forward` are O(1).

### 2.2 Queue using two stacks: bottoms facing each other

**Problem (paraphrased).** Implement a first-in-first-out queue using only two stacks (only push to top, pop from top, peek at top, size and is-empty are allowed). Support `push(x)` (add `x` at the back), `pop()` (remove and return the front), `peek()` (return the front) and `empty()`. Calls to `pop` and `peek` are always valid (the queue isn't empty).
Example: `push(1), push(2), peek() → 1, pop() → 1, empty() → False`.
Constraints: `1 <= x <= 9`; up to 100 calls. Follow-up: amortized O(1) per operation.

A queue is a line with two ends that do different jobs: items **join at the back** and **leave from the front**. A stack only has one open end. So each stack takes one end of the line:

| Name | Stands for | Its top stands for |
|---|---|---|
| `inbox` | the back part of the line | **the newest item** (the very back) |
| `outbox` | the front part of the line | **the oldest item** (the very front: the next to leave) |

Draw them on the line the same way as before. The queue holds `1 2 3 4` (1 oldest). Suppose `1 2` are in `outbox` and `3 4` are in `inbox`:

```
queue line (front → back):    1    2   |   3    4
outbox:                     [1    2]                  top 1 ... bottom 2    (the list is [2, 1])
inbox:                                 [3    4]       bottom 3 ... top 4    (the list is [3, 4])
                            ↑                   ↑
                         outbox's top        inbox's top
                         at the front        at the back
```

This time the **tops point outward**, one at each end of the line, and the **bottoms face each other** in the middle. That matches what a queue needs: `push` uses `inbox`'s top (the back), and `pop` uses `outbox`'s top (the front).

**The problem appears when `outbox` runs empty.** After popping 1 and 2:

```
queue line:      |   3    4
outbox:        []
inbox:               [3    4]      the front of the line (3) is inbox's BOTTOM
```

The next item to leave is `3`, and it's at the **bottom** of `inbox`. A stack can only reach its top. The only way to get at a bottom is to remove everything above it. So pop every item off `inbox` and push it onto `outbox`. Popping reverses the order, and here that's exactly what you want: `4` goes in first (ends at `outbox`'s bottom), `3` goes in last (ends on top). Now `outbox`'s top is the front of the line again:

```
outbox:        [3    4]      top 3 ... bottom 4    (the list is [4, 3])
inbox:         []
```

That's the "clear things out all at once" part: **you must move everything, because the item you need is at the bottom.** Moving only the top item of `inbox` would give you `4`, the newest item, which is the wrong end of the line.

**Now the guard: why only when `outbox` is empty.** Run the version without the guard (from running it):

| call | returns | `inbox` | `outbox` | what happened |
|---|---|---|---|---|
| push 1 | | `[1]` | `[]` | |
| push 2 | | `[1, 2]` | `[]` | |
| pop | 1 | `[]` | `[2]` | `outbox` was empty: move all, giving `[2, 1]`; pop 1 ✓ |
| push 3 | | `[3]` | `[2]` | |
| pop | **3** ✗ (should be 2) | `[]` | `[2]` | no guard: 3 was moved on top of 2, giving `[2, 3]`; pop 3 |

On the line, the queue was `2 | 3`: `2` at the front (in `outbox`), `3` at the back (in `inbox`). Moving `3` onto `outbox`'s top put it **in front of** `2`. The newest item jumped the line. With the guard, the `pop` sees that `outbox` still has `2`, doesn't move anything, and returns `2`; `3` waits in `inbox` until `outbox` is empty.

So the two parts of the rule each come from the picture:

- **"Move everything"**: the front of the line is at `inbox`'s bottom, and a bottom can only be reached by removing everything above it.
- **"Only when `outbox` is empty"**: everything in `outbox` is older than everything in `inbox`. Putting `inbox` items on top of a non-empty `outbox` puts newer items in front of older ones.

```python
class MyQueue:
    def __init__(self):
        self.inbox = []                  # back part of the line; top = newest
        self.outbox = []                 # front part of the line; top = oldest (next to leave)

    def push(self, x):
        self.inbox.append(x)

    def _refill(self):
        if not self.outbox:              # only when the front part is used up
            while self.inbox:            # move everything: the front is at inbox's bottom
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

**Why it's O(1) amortized:** a single `pop` can move n items. But follow one item through its whole life: pushed onto `inbox` once, moved to `outbox` once, popped once. That's at most 3 operations per item, ever, so m calls do at most 3m operations in total, which is O(1) per call on average.

### 2.3 Why the queue needs the rule and your browser doesn't

Side by side:

| | Your Browser History | Queue via two stacks |
|---|---|---|
| What the line is | pages, oldest to newest | items, front to back |
| How the stacks sit on the line | **tops face each other** at the cursor | **bottoms face each other**; tops at the two ends |
| The item you need next | the neighbour of the cursor, which is **always a top** | the front of the line, which is `outbox`'s top, or `inbox`'s **bottom** once `outbox` is empty |
| One move (pop → push) | moves one page across the cursor; **order kept** | moves `inbox`'s newest item to the far end; only correct as part of moving everything |
| How many to move | exactly `steps` (stop any time) | **all of `inbox`**, only when `outbox` is empty |

So you're right that you're using the stacks "in the exact same way" mechanically: pop from one, push onto the other. The difference is what the tops stand for. Your browser's tops meet at the cursor, so moving one item is a complete, correct step on its own. The queue's tops are at opposite ends of the line, so the only correct move is the full reversal, and only when nothing older is in the way.

**The general habit (core idea 3):** before using a stack, write what its top stands for. Then the rules follow from the names, the same way lecture 008's boundaries follow from naming what an index stands for. You don't have to memorize "the guard." Ask: "the item I need next, where is it? On a top, or at a bottom?"

---

## 3. Interleaving: why any order of calls is safe

You said that interleaved calls made you uneasy: back, then visit, then forward, then back again… How do you know no order breaks it? You can't test every order: there are infinitely many. But you don't have to.

**The method: write one sentence that's true after every method, and check each method once.**

For your browser:

> **Invariant:** reading `back_stack` from bottom to top, then `forward_stack` from top to bottom, gives the history line in order; and `back_stack`'s top is the current page.

Check each method, assuming the sentence is true before the call:

| Method | What it does to the line | Still true after? |
|---|---|---|
| `visit(url)` | drops everything right of the cursor, puts `url` just left of it | ✓ `url` is now `back_stack`'s top and the line is `…, current, url` |
| one step of `back` | moves the page left of the cursor to its right side | ✓ the order on the line is unchanged, and the new top of `back_stack` is the new current page |
| one step of `forward` | the mirror image | ✓ |

For the queue:

> **Invariant:** reading `outbox` from top to bottom, then `inbox` from bottom to top, gives the queue from front to back.

| Method | Still true after? |
|---|---|
| `push(x)` | ✓ `x` is added at `inbox`'s top, which is the end of the reading: the back of the queue |
| `pop` / `peek` with `outbox` non-empty | ✓ `outbox`'s top is the first in the reading: the front |
| `_refill` with `outbox` empty | ✓ the reading was just `inbox` bottom to top; after reversing, `outbox` top to bottom is the same order, and `inbox` is empty |
| `_refill` with `outbox` **non-empty** (the broken version) | ✗ items from `inbox`'s top land before `outbox`'s items in the reading |

**Why this covers every possible order.** Any sequence of calls is one method after another. The sentence is true at the start (after `__init__`). Each method keeps it true. So it's true after the first call, so after the second, and so on: after every call, in every order. That's the same induction as a loop invariant (lecture 003), applied to calls instead of loop iterations.

So the remedy for "what if some order breaks it?" is: **write the invariant, check each method against it once, and then the order no longer matters.** If one method breaks the sentence, you've found the bug without guessing at sequences.

**Backing that up in practice:** a random test against a simple reference catches what your reasoning missed. This is how both classes here were checked:

```python
import random
from collections import deque

def test_queue(trials=2000):
    for _ in range(trials):
        q, ref = MyQueue(), deque()      # ref: a simple, obviously correct queue
        for _ in range(30):
            if ref and random.random() < 0.5:
                assert q.pop() == ref.popleft()
            else:
                v = random.randint(0, 99)
                q.push(v)
                ref.append(v)
    print("queue ok")

test_queue()
```

Swap `MyQueue` for the unguarded version and the assertion fails within the first few trials.

---

## 4. Stacks that save state: Evaluate RPN (150) and Simplify Path (71)

In §1 the stack held things *waiting to be resolved*. A closely related use: the stack holds **things you've read but can't use yet**, and a later item tells you what to do with the most recent ones.

### 4.1 Evaluate Reverse Polish Notation (150)

**Problem (paraphrased).** You're given `tokens`, an arithmetic expression in **Reverse Polish Notation** (RPN): every operator comes *after* its two operands. For example, `["2", "1", "+", "3", "*"]` means `(2 + 1) * 3`. Each token is an integer or one of `+ - * /`. Evaluate it and return the integer result. Division **truncates toward zero** (`7 / -2` is `-3`). The expression is always valid, and there's no division by zero.
Examples: `["2","1","+","3","*"]` → `9`; `["4","13","5","/","+"]` → `6` (that's `4 + 13/5 = 4 + 2`); `["10","6","9","3","+","-11","*","/","*","17","+","5","+"]` → `22`.
Constraints: `1 <= len(tokens) <= 10^4`; every intermediate value fits in 32 bits.

**Name:** `stack` holds numbers that have been read (or computed) but not yet used by an operator. **Its top is the most recent number.**

When an operator arrives, it applies to the **two most recent** numbers. Which is the left operand? Derive it from a tiny case: `["5", "3", "-"]` means `5 - 3`. `5` was pushed first, `3` second, so `3` is on top. The **first pop is the right operand**, and the second pop is the left one. That order matters for `-` and `/`.

**Truncating toward zero in Python:** `//` rounds **down** (toward −∞), so `-7 // 2` is `-4`, but the problem wants `-3`. `int(left / right)` divides as a float, then `int` drops the fractional part, which is truncation toward zero: `int(-7 / 2)` is `int(-3.5)`, which is `-3`. (Float division is exact enough here because the values fit in 32 bits.)

```python
def evalRPN(tokens):
    stack = []                           # numbers read or computed, not yet used; top = most recent
    for tok in tokens:
        if tok in "+-*/":                # "-11" is a number, not an operator: it isn't one of these four strings
            right = stack.pop()          # most recent = the RIGHT operand ("5 3 -" is 5 - 3)
            left = stack.pop()
            if tok == "+":
                stack.append(left + right)
            elif tok == "-":
                stack.append(left - right)
            elif tok == "*":
                stack.append(left * right)
            else:
                stack.append(int(left / right))   # truncate toward zero (not //)
        else:
            stack.append(int(tok))
    return stack[-1]
```

A note on `tok in "+-*/"`: for a string, `in` checks for a **substring**, so `"-11" in "+-*/"` is `False` (good), and so is any multi-character number. A single `"-"` is `True`. It works here, but `tok in {"+", "-", "*", "/"}` says what you mean more clearly.

Trace `["4","13","5","/","+"]` (from running it):

| token | action | stack after |
|---|---|---|
| 4 | push | `[4]` |
| 13 | push | `[4, 13]` |
| 5 | push | `[4, 13, 5]` |
| / | right = 5, left = 13 → `int(13 / 5)` = 2 | `[4, 2]` |
| + | right = 2, left = 4 → 6 | `[6]` |

**O(n) time, O(n) space.**

### 4.2 Simplify Path (71)

**Problem (paraphrased).** Given an absolute Unix-style file path `path` (it starts with `/`), return its simplified **canonical** form. The rules: `.` means the current directory (ignore it); `..` means go up one directory (at the root, stay at the root); several slashes in a row count as one slash; any other name, **including `...`**, is an ordinary directory name. The canonical path starts with a single `/`, has exactly one `/` between names, has no trailing `/`, and contains no `.` or `..`.
Examples: `"/home/"` → `"/home"`; `"/home//foo/"` → `"/home/foo"`; `"/home/user/Documents/../Pictures"` → `"/home/user/Pictures"`; `"/../"` → `"/"`; `"/.../a/../b/c/../d/./"` → `"/.../b/d"`.
Constraints: `1 <= len(path) <= 3000`; letters, digits, `.`, `/` and `_` only.

**Name:** `stack` holds the directories of the current location, from the root down. **Its top is the directory you're in.** `..` means "leave the directory you're in," so it pops the top.

`path.split("/")` does the slash handling for you. Splitting `"/a//b/"` gives `['', 'a', '', 'b', '']`: every empty string comes from a leading, doubled or trailing slash, so empty parts are skipped.

```python
def simplifyPath(path):
    stack = []                           # directories from the root down; top = the one you're in
    for part in path.split("/"):
        if part == "" or part == ".":    # extra slashes, or "stay here"
            continue
        if part == "..":
            if stack:                    # at the root, ".." does nothing
                stack.pop()
        else:
            stack.append(part)           # any other name, including "...", is a directory
    return "/" + "/".join(stack)
```

Trace `"/a/./b/../../c/"` (from running it):

| part | action | stack after |
|---|---|---|
| `''` | skip | `[]` |
| `'a'` | push | `['a']` |
| `'.'` | skip | `['a']` |
| `'b'` | push | `['a', 'b']` |
| `'..'` | pop | `['a']` |
| `'..'` | pop | `[]` |
| `'c'` | push | `['c']` |
| `''` | skip | `['c']` → `"/c"` |

When the stack ends empty, `"/".join([])` is `""`, and the answer is `"/"`, which is correct for the root. **O(n) time and space.**

---

## 5. Saving context at a bracket: Decode String (394)

**Problem (paraphrased).** A string is encoded with the rule `k[encoded]`: the part inside the brackets is repeated exactly `k` times (`k` is a positive integer). Brackets can be nested. Return the decoded string. The input is always valid, digits appear only as repeat counts (so `3a` or `2[4]` never appear), and the original text has no digits.
Examples: `"3[a]2[bc]"` → `"aaabcbc"`; `"3[a2[c]]"` → `"accaccacc"`; `"2[abc]3[cd]ef"` → `"abcabccdcdcdef"`.
Constraints: `1 <= len(s) <= 30`; `1 <= k <= 300`; the output length is at most 10⁵.

**Why a stack.** Inside `3[a2[c]]`, when you reach the inner `[`, you're in the middle of building the outer bracket's string (`"a"` so far), and you still have to remember that the outer bracket repeats 3 times. The inner bracket has to be finished first (inner before outer, as in §1), and then you **come back** to the outer one and continue. Each `[` is a point you'll return to, and the most recent one is returned to first. So at each `[`, save what you'll need when you come back.

**Names:**

| Name | Stands for |
|---|---|
| `current` | the decoded string built so far **at the current bracket depth** |
| `count` | the number being read, digit by digit, for the next `[` |
| `stack` | one entry per open `[`: `(before, times)`, where `before` is the string built before this bracket opened, and `times` is how many times this bracket's contents repeat |

The four kinds of character:

- **digit:** extend the number. Reading `"12"` gives `count = 1`, then `count = 1 * 10 + 2 = 12`, which is why `count = count * 10 + int(ch)` (lecture 005's "read a number digit by digit").
- **`[`:** save `(current, count)`, then start fresh: `current = ""`, `count = 0`.
- **`]`:** this bracket is done. Pop `(before, times)` and set `current = before + current * times`: the string from before the bracket, then this bracket's contents repeated.
- **letter:** add it to `current`.

```python
def decodeString(s):
    stack = []                           # one (before, times) per open "["
    current = ""                         # decoded string at the current bracket depth
    count = 0                            # repeat count being read for the next "["
    for ch in s:
        if ch.isdigit():
            count = count * 10 + int(ch)
        elif ch == "[":
            stack.append((current, count))   # save what to come back to
            current, count = "", 0
        elif ch == "]":
            before, times = stack.pop()
            current = before + current * times
        else:
            current += ch
    return current
```

Trace `"3[a2[c]]"` (from running it):

| char | `stack` after | `current` after | `count` after |
|---|---|---|---|
| 3 | `[]` | `''` | 3 |
| [ | `[('', 3)]` | `''` | 0 |
| a | `[('', 3)]` | `'a'` | 0 |
| 2 | `[('', 3)]` | `'a'` | 2 |
| [ | `[('', 3), ('a', 2)]` | `''` | 0 |
| c | `[('', 3), ('a', 2)]` | `'c'` | 0 |
| ] | `[('', 3)]` | `'a' + 'c'*2` = `'acc'` | 0 |
| ] | `[]` | `'' + 'acc'*3` = `'accaccacc'` | 0 |

**Connection to recursion (lecture 002).** A recursive solution would call itself at `[` and return at `]`. The call stack would hold each call's `current` and `count` for you. Here you hold them yourself. Whenever a problem says "nested," either recursion or an explicit stack of saved context works, and they're the same idea.

**Time:** O(length of the output), since the repetitions build it. **Space:** O(output + depth).

---

## 6. Monotonic stacks: Daily Temperatures (739) and Car Fleet (853)

### 6.1 Daily Temperatures (739)

**Problem (paraphrased).** Given `temperatures`, the daily temperatures, return `answer` where `answer[i]` is the number of days you have to wait after day `i` to get a **warmer** temperature (strictly greater). If no future day is warmer, `answer[i] = 0`.
Examples: `[73,74,75,71,69,72,76,73]` → `[1,1,4,2,1,1,0,0]`; `[30,40,50,60]` → `[1,1,1,0]`; `[30,60,90]` → `[1,1,0]`.
Constraints: `1 <= len(temperatures) <= 10^5`; `30 <= temperatures[i] <= 100`.

**Brute force:** for each day, scan forward until a warmer day. That's O(n²), and up to 10¹⁰ steps at n = 10⁵: too slow.

**The unresolved-items idea again (§1).** Walk the days left to right. A day is **unresolved** until a warmer day shows up. Keep the unresolved days on a stack.

**Name:** `waiting` holds the **indices** of days that haven't found a warmer day yet. (Indices, not temperatures, because the answer is a distance in days, `day - earlier`, and you can always read the temperature from the index.)

When today arrives, which waiting days does it resolve? Every waiting day that's **colder than today**. And here's the fact that makes the stack work:

**Fact: the temperatures of the waiting days never increase from bottom to top.** Why: when a day is pushed, every waiting day colder than it was just popped. So everything left below it is at least as warm as it. That's true each time something is pushed, so it's true for the whole stack.

**Consequence: you only ever need to compare with the top.** If the top day isn't colder than today, nothing below it is either (they're all at least as warm as the top). So: pop while the top is colder, then stop. Each pop resolves one day with `answer[earlier] = day - earlier`.

**Name → valid set → test positively** for the pop condition: "warmer" means strictly greater, so a waiting day is resolved when **`temperatures[top] < today`**. A day with the same temperature is not resolved and stays waiting.

```python
def dailyTemperatures(temperatures):
    answer = [0] * len(temperatures)     # stays 0 for days that never find a warmer day
    waiting = []                         # indices of unresolved days; their temps never increase bottom -> top
    for day, temp in enumerate(temperatures):
        while waiting and temperatures[waiting[-1]] < temp:   # today is strictly warmer than the top day
            earlier = waiting.pop()
            answer[earlier] = day - earlier
        waiting.append(day)              # today waits for its own warmer day
    return answer
```

Trace `[73,74,75,71,69,72,76,73]` (from running it; the stack shows `index(temp)`):

| day | temp | resolved this step | `waiting` after |
|---|---|---|---|
| 0 | 73 | — | `0(73)` |
| 1 | 74 | day 0 → 1 | `1(74)` |
| 2 | 75 | day 1 → 1 | `2(75)` |
| 3 | 71 | — | `2(75) 3(71)` |
| 4 | 69 | — | `2(75) 3(71) 4(69)` |
| 5 | 72 | day 4 → 1, day 3 → 2 | `2(75) 5(72)` |
| 6 | 76 | day 5 → 1, day 2 → 4 | `6(76)` |
| 7 | 73 | — | `6(76) 7(73)` |

Days 6 and 7 are still waiting at the end, so their answers stay 0. Result: `[1,1,4,2,1,1,0,0]`.

**Why it's O(n), even with a loop inside a loop** (core idea 9): each index is pushed once and popped at most once. Over the whole run the inner `while` pops at most n times **in total**, not n times per day. Count the work per item, not per loop.

**The general pattern:** a **monotonic stack** is a stack kept in sorted order (here, never increasing). It answers "for each item, the **next** item to its right that beats it" in one pass. Change the comparison and the order to get the variants:

| Question | Pop while the top is… | Order of the stack (bottom → top) |
|---|---|---|
| next **greater** to the right | `<` today | never increasing |
| next **greater or equal** | `<=` today | strictly decreasing |
| next **smaller** to the right | `>` today | never decreasing |

You don't need to memorize the table: name what "resolves" a waiting item, write that as the pop condition, and the order follows.

### 6.2 Car Fleet (853), which you already solved

**Problem (paraphrased).** `n` cars drive toward the same `target` on a one-lane road. Car `i` starts at `position[i]` with speed `speed[i]` (all positions are different). A car can't pass the car in front of it. When it catches up, it slows down and drives with it as one **fleet** at the slower speed. A car that catches up exactly at the target joins that fleet. Return how many fleets arrive at the target.
Example: `target = 12`, `position = [10,8,0,5,3]`, `speed = [2,4,1,1,3]` → `3`. Also `target = 10, position = [3], speed = [3]` → `1`; `target = 100, position = [0,2,4], speed = [4,2,1]` → `1`.
Constraints: `1 <= n <= 10^5`; `0 <= position[i] < target <= 10^6`; `1 <= speed[i] <= 10^6`.

You solved this ✅. In your comments you wrote that it "feels like a monotonic stack type of problem," but that it might be as simple as walking the cars from the front and comparing arrival times. Both are right, and here's why they're the same solution.

**Names:**

- `arrival` = `(target - pos) / spd`: when this car would reach the target **if nothing blocked it**.
- `fleets`: the arrival times of the fleets found so far, one per fleet, front fleet at the bottom.

Process cars from the **front** (closest to the target) backward. A car behind a fleet either catches it (its own arrival is `<=` the fleet's, so it's blocked and joins) or doesn't (its arrival is **later**, so it forms a new fleet). Test positively: a new fleet when `arrival > fleets[-1]`.

```python
def carFleet(target, position, speed):
    cars = sorted(zip(position, speed), reverse=True)   # front car (largest position) first
    fleets = []                          # one arrival time per fleet; strictly increasing bottom -> top
    for pos, spd in cars:
        arrival = (target - pos) / spd   # when this car would arrive alone
        if not fleets or arrival > fleets[-1]:
            fleets.append(arrival)       # can't catch the fleet ahead: a new fleet
        # otherwise it catches up and joins the fleet ahead (which keeps its arrival time)
    return len(fleets)
```

Trace for the first example (from running it):

| car (pos, speed) | arrival | `fleets` after |
|---|---|---|
| (10, 2) | 1.0 | `[1.0]` |
| (8, 4) | 1.0 | `[1.0]`: not later, joins |
| (5, 1) | 7.0 | `[1.0, 7.0]` |
| (3, 3) | 3.0 | `[1.0, 7.0]`: not later, joins the 7.0 fleet |
| (0, 1) | 12.0 | `[1.0, 7.0, 12.0]` → **3** |

**Why your single variable works too.** This stack is only ever pushed, never popped, and only its top is ever read. A stack you only push and only peek is the same as **one variable holding the latest value** plus a counter. That's what you wrote. Recognizing "this could be a stack" and then noticing "I only need the top" is a good simplification, not a shortcut.

**O(n log n)** for the sort, then O(n).

---

## 7. Recognizing a stack problem

| What the problem says or needs | Stack use | Example |
|---|---|---|
| nested structure; "close the most recent open thing" | stack of unresolved openers | 20 Valid Parentheses |
| operators after operands; "the last two values" | stack of operands | 150 Evaluate RPN |
| `..` / "undo" / "go back one level" | stack of the levels so far | 71 Simplify Path |
| `k[...]` nesting; "come back to where you were" | stack of saved context (or recursion) | 394 Decode String |
| "next greater / warmer / smaller to the right"; "how many days until" | monotonic stack of waiting indices | 739 Daily Temperatures, 496 |
| "cars/items merge with the one ahead" | stack (or one variable) of group values | 853 Car Fleet |
| back/forward through history | two stacks, tops facing each other | 1472 Browser History |
| FIFO using only stacks | two stacks, bottoms facing each other | 232 Queue using Stacks |
| min/max of a stack at any time | store the aggregate with each entry | 155 Min Stack (lecture 012 §4.1) |
| "largest rectangle" / "how far can this bar extend left and right" | monotonic stack, popping computes an area | 84 (stretch) |

**The question to ask yourself:** *when a new item arrives, does it settle the most recent unsettled things?* If yes, the unsettled things go on a stack.

---

## 8. Python pitfalls

| Pitfall | What happens | Fix |
|---|---|---|
| `stack.pop()` or `stack[-1]` on an empty list | `IndexError` | guard first: `while stack and …`, `if not stack: …` |
| `while stack[-1] < x and stack:` | crashes when empty: the left side runs first | put `stack` **first**: `while stack and stack[-1] < x:` |
| `stack.pop(0)` / `stack.insert(0, x)` | O(n): every other element shifts | use `collections.deque` with `popleft()` / `appendleft()` |
| `//` for "divide, truncating toward zero" | `-7 // 2` is `-4` (rounds down) | `int(a / b)` |
| right and left operands popped in the wrong order | `5 3 -` gives `-2` | first pop = right operand |
| pushing values when you need distances | can't compute `day - earlier` | push indices; read values with `arr[i]` |
| `forward_stack = []` inside a method without `self.` | creates a local variable; the real stack isn't cleared | `self.forward_stack.clear()` (or `self.forward_stack = []`) |
| strings built with `+=` in a loop | fine for these sizes; O(n²) in the worst case for huge inputs | collect parts in a list and `"".join` when it matters |

---

## 9. Practice ladder

Do them in order. For each one, **write what the stack (and its top) stands for before coding**, trace with the stack drawn bottom → top, and test the empty and "left over" cases.

| # | Problem | What it practises | Section |
|---|---|---|---|
| 1 | 20 Valid Parentheses | unresolved items; the three ways to fail | §1 |
| 2 | 1472 Design Browser History (redo **both** ways: your two stacks, then the array + cursor of lecture 012 §4.3) | tops facing each other; boundary vs data | §2.1 |
| 3 | 232 Implement Queue using Stacks | bottoms facing each other; the refill rule from the picture | §2.2 |
| 4 | 155 Min Stack | aggregate stored per entry | lecture 012 §4.1 |
| 5 | 150 Evaluate Reverse Polish Notation | operand order; truncation | §4.1 |
| 6 | 71 Simplify Path | split, skip, pop | §4.2 |
| 7 | 394 Decode String | saved context | §5 |
| 8 | 739 Daily Temperatures | monotonic stack; amortized O(n) | §6.1 |
| 9 | 496 Next Greater Element I | §6.1 plus a dict from value to answer | §6.1 |
| 10 | 853 Car Fleet (redo with an explicit stack) | stack vs one variable | §6.2 |
| stretch | 84 Largest Rectangle in Histogram, 901 Online Stock Span, 42 Trapping Rain Water (stack version) | monotonic stack where a pop computes something | §6.1 |

**496, in brief** (do it without looking further if you can): `nums1` is a subset of `nums2` (all values distinct). For each value in `nums1`, return the first greater value to its right **in `nums2`**, or `-1`. Run §6.1's loop over `nums2`, storing `next_greater[value] = today's value` when a value is popped, then look up each `nums1` value with `next_greater.get(v, -1)`.

**84, as a hint only:** for each bar, the largest rectangle using that bar's full height stretches left and right until a **shorter** bar. "The first shorter bar to the right" is a monotonic-stack question, and a bar's area can be computed at the moment it's popped. Try it after 739 and 496 feel automatic.

---

## Common mistakes

| Mistake | Fix |
|---|---|
| Using a stack without saying what its top stands for | write it as a comment on the line that creates the stack |
| Peeking or popping without checking for empty | `stack and` comes first in the condition |
| Valid Parentheses: returning `True` without checking for leftovers | `return not stack` |
| Two-stack queue: refilling while `outbox` still has items | refill only when `outbox` is empty, and then move everything (§2.2) |
| Two-stack queue: moving one item instead of all | the front is at `inbox`'s **bottom**; only moving everything reaches it |
| Thinking the browser's two stacks need the queue's rule | the browser's tops face each other: each single move is complete (§2.3) |
| Worrying about every possible order of calls | write the invariant; check each method once (§3) |
| RPN: popping left before right | first pop = right |
| RPN: `//` for division | `int(left / right)` |
| Decode String: forgetting multi-digit counts | `count = count * 10 + int(ch)` |
| Monotonic stack: `<=` vs `<` guessed | write what "resolves" a waiting item; strictly warmer → `<` |
| Calling a while-inside-for O(n²) | count pushes and pops per item: each happens once → O(n) |

---

## Self-check questions

1. In Valid Parentheses, why must a closer match the **most recent** unresolved opener?
<details><summary>Answer</summary>

The most recent unresolved opener is the innermost open bracket, and a valid string closes inner brackets before outer ones. So the next closer has to close it.
</details>

2. Name the three ways a bracket string can be invalid, and the line of code that catches each.
<details><summary>Answer</summary>

A closer when nothing is open (`not stack`), a closer of the wrong type (`stack[-1] != match[ch]`), and openers left at the end (`return not stack`).
</details>

3. In your Browser History, what does each stack's top stand for?
<details><summary>Answer</summary>

`back_stack`'s top is the current page. `forward_stack`'s top is the page one step forward.
</details>

4. Draw both of your browser's stacks on the history line. Why does moving one page from one stack to the other keep the history in order?
<details><summary>Answer</summary>

The tops face each other at the cursor (the current position). Moving the top of `back_stack` onto `forward_stack` moves one page across the cursor. The order of pages on the line is unchanged; only the cursor moves one step.
</details>

5. In the two-stack queue, where is the front of the line when `outbox` is empty, and why does that force you to move everything?
<details><summary>Answer</summary>

At the **bottom** of `inbox`. A stack only exposes its top, so the only way to reach the bottom is to pop everything above it. Moving it all onto `outbox` reverses the order, which puts the oldest on top.
</details>

6. Give the shortest call sequence that breaks the queue if you refill while `outbox` isn't empty, and say what goes wrong.
<details><summary>Answer</summary>

`push 1, push 2, pop, push 3, pop`. The first `pop` moves both, leaving `outbox = [2]` after returning 1. Refilling then puts 3 on top of 2, so the second `pop` returns 3 instead of 2: the newest item jumped ahead of an older one.
</details>

7. State the invariant for the two-stack queue, and explain why checking each method against it covers every possible order of calls.
<details><summary>Answer</summary>

Reading `outbox` top to bottom, then `inbox` bottom to top, gives the queue front to back. It's true after `__init__`, and each method keeps it true. Any sequence of calls is one method after another, so it's true after every call in every sequence (induction).
</details>

8. In Evaluate RPN, why is the first popped value the right operand?
<details><summary>Answer</summary>

In `5 3 -` (5 − 3), `3` is pushed last, so it's on top and pops first. The value pushed last is the one written closer to the operator, which is the right operand.
</details>

9. Why `int(a / b)` instead of `a // b` in RPN?
<details><summary>Answer</summary>

The problem truncates toward zero. `//` rounds down, so `-7 // 2` is `-4`, but the answer should be `-3`. `int(-7 / 2)` is `int(-3.5)`, which is `-3`.
</details>

10. In Decode String, what does each stack entry `(before, times)` stand for, and what happens at `]`?
<details><summary>Answer</summary>

`before` is the decoded string built before this `[` opened, and `times` is this bracket's repeat count. At `]`, pop it and set `current = before + current * times`.
</details>

11. In Daily Temperatures, why is it enough to compare today with the **top** of `waiting` only?
<details><summary>Answer</summary>

The waiting days' temperatures never increase from bottom to top. If the top isn't colder than today, every day below it is at least as warm as the top, so none of them is colder than today either.
</details>

12. Why is Daily Temperatures O(n) even though there's a `while` loop inside the `for` loop?
<details><summary>Answer</summary>

Each index is pushed once and popped at most once, so the inner loop pops at most n times over the whole run, not per day.
</details>

13. In Car Fleet, why does a stack that's never popped reduce to a single variable?
<details><summary>Answer</summary>

Only its top is ever read and nothing is removed, so the only value that matters is the latest one pushed. One variable holding it, plus a count of pushes, does the same job.
</details>

---

## Sources

- Problems: LeetCode 20, 1472, 232, 150, 71, 394, 739, 853 (also 155, 496; stretch 84, 901, 42). Statements are paraphrased; examples and constraints come from long-standing problem pages (from my own knowledge, not re-fetched; 2026-10-17).
- Python: lists as stacks (https://docs.python.org/3/tutorial/datastructures.html#using-lists-as-stacks), `collections.deque` (https://docs.python.org/3/library/collections.html#collections.deque), `str.split` (https://docs.python.org/3/library/stdtypes.html#str.split), time complexity of built-ins (https://wiki.python.org/moin/TimeComplexity).
- Amortized analysis of the two-stack queue: Cormen et al., *Introduction to Algorithms*, chapter on amortized analysis.
- Verification (2026-10-17): every function and class was checked against a brute-force reference on thousands of random inputs (see the header). The unguarded queue was confirmed to fail on `push 1, push 2, pop, push 3, pop`. All traces were produced by running the code.
