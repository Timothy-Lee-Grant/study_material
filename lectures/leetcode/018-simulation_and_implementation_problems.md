# Lecture 018: Simulation Problems: Turning Rules Into Code Without Losing a Step

> **For:** Timothy · **Date:** 2026-10-27
> **Prerequisites:** lecture 008 (boxes and cuts, valid sets, two-point checks), lecture 003 (trace tables), lecture 013 (stacks, for §6). Lecture 001 covered **grid** simulation (Spiral Matrix, Game of Life, the in-place hazard). This lecture is the general version: simulations on lines, queues, circles, numbers, strings and time.
> **Why this lecture:** the roadmap's "Kinds of problems" §3 called these **implementation / simulation** problems. They have no clever insight; the difficulty is **decision density**: twenty small decisions in a row, each a chance for an off-by-one or a step in the wrong order. Your history shows it: Spiral Matrix (about 20 index decisions), Reverse Integer (digit order), Birthday Chocolate (window order), and most recently `tail` never moving in Merge Two Lists (a state update left out of the step). Lecture 001 only treated grids. This lecture gives you **one method for every simulation**, then applies it to seven different kinds.
> **Format notes:** every problem has its full statement (paraphrased), examples and constraints; every name is defined before it's used; every formula is derived; no firmware analogies.
> **Verification:** every solution was compared with a brute-force or step-by-step reference on 3,000 random inputs (plus the overflow edge cases for Reverse Integer). All traces and counterexamples were produced by running the code.

---

## Core ideas (the answer key)

1. **A simulation problem gives you rules and asks for the result of carrying them out.** The work is translating the rules exactly, not finding an idea.
2. **The method:** write the rules in your own words → name the **state** (every value that changes, what it stands for, its valid set) → write **one step** → decide **when it stops** → list the edge cases → trace a few steps.
3. **Write one step as its own block (or helper), from state to next state.** If you can't say what one step does in one sentence, the step isn't defined yet.
4. **Every name in the state needs a line that keeps it true, inside the step.** List the lines that change each name (attempt review 001's name-vs-lines check). A name with no update line, like `tail` in your Merge Two Lists, is the most common simulation bug.
5. **"At the same time" means: compute the whole next state from the old state, then replace it.** Updating in place lets a cell see its neighbour's *new* value.
6. **Directions go in a table** (`DIRS[d]`), and turning is arithmetic on `d`: right is `(d + 1) % 4`, left is `(d + 3) % 4`. No `if`-chains.
7. **Wrapping around a circle is `% length`.** Count `k` boxes starting *at* box `start` (counting the start as 1): the k-th is `(start + k - 1) % length`.
8. **Bouncing between two edges** (zigzag) is a step of `+1` or `-1` that flips when you're **at** an edge, decided after you use the current position.
9. **Before simulating, count the steps.** If the number of steps is far beyond about 10⁸ (like `n = 10⁹` days), you can't simulate them all. Look for a **repeat** (the state space is small), a **per-pass change** (Robot Bounded), or a **formula** (Buy Tickets).
10. **Trace a simulation as one row per step**, with one column per state variable. Simulations are where trace tables work best, because the state is small and each row is one rule applied.

---

## Table of Contents

- [0. What makes a problem a simulation](#0-what-makes-a-problem-a-simulation)
- [1. The method](#1-the-method)
- [2. Queue simulation, then a formula: Time Needed to Buy Tickets (2073)](#2-queue-simulation-then-a-formula-time-needed-to-buy-tickets-2073)
- [3. Position and direction: Robot Bounded in Circle (1041)](#3-position-and-direction-robot-bounded-in-circle-1041)
- [4. Bouncing between edges: Zigzag Conversion (6)](#4-bouncing-between-edges-zigzag-conversion-6)
- [5. A circle that shrinks: Find the Winner of the Circular Game (1823)](#5-a-circle-that-shrinks-find-the-winner-of-the-circular-game-1823)
- [6. Events that interact: Asteroid Collision (735)](#6-events-that-interact-asteroid-collision-735)
- [7. Digit by digit, with a limit: Reverse Integer (7)](#7-digit-by-digit-with-a-limit-reverse-integer-7)
- [8. Simultaneous updates and too many steps: Prison Cells After N Days (957)](#8-simultaneous-updates-and-too-many-steps-prison-cells-after-n-days-957)
- [9. Recognizing a simulation, and checking if it's fast enough](#9-recognizing-a-simulation-and-checking-if-its-fast-enough)
- [10. Practice ladder](#10-practice-ladder)
- [Common mistakes](#common-mistakes)
- [Self-check questions](#self-check-questions)
- [Sources](#sources)

---

## 0. What makes a problem a simulation

| | Pattern problem | Simulation problem |
|---|---|---|
| The statement | describes **what** answer is wanted | describes a **process**: "each second…", "then…", "repeat until…" |
| The hard part | one insight (binary search on the answer, a window, DP) | many small decisions, each easy, all in a row |
| Typical bug | the wrong approach | an index off by one, a step in the wrong order, a variable not updated, an edge case not handled |
| How to get it right | recognize the pattern | **be systematic**: name the state, define one step, trace |

The signals in the statement: words like *each step / each second / each day / in turn / repeat until / then*, a set of rules with cases ("if it's G…, if it's L…"), or a story about people, robots, cards or cells.

**Why these feel easy but fail:** each decision has, say, a 95% chance of being right if you make it by feel. Twenty of them in a row are all right only about 36% of the time (0.95²⁰). The method below doesn't make you smarter at any one decision. It makes each one **deliberate**, so the odds stop multiplying against you.

---

## 1. The method

Use these six steps on every simulation. Steps 1–5 go in comments before the code.

**Step 1: the rules in your own words.** One line per rule, numbered. If the statement says "at the same time" or "simultaneously," write that down; it changes the code (§8).

**Step 2: name the state.** Every value that changes during the process, as a table:

| Name | Stands for | Valid set |
|---|---|---|
| … | … | … |

This is the same habit as lecture 008 (name → valid set) and lecture 012 (operations table), applied to a process.

**Step 3: write one step.** "One step takes the state from *now* to *next*." Write it as a block (or a helper `step(state)`), and for each name in the state, find the line inside the step that keeps it true. **A name with no update line is a bug** (your `tail`).

**Step 4: when does it stop?** One of:
- a fixed number of steps (`for _ in range(n)`);
- until a condition (`while len(friends) > 1`, `while x > 0`);
- until the state repeats (§8);
- you can't simulate to the end at all, and need a formula or a per-pass argument (§2, §3).

**Step 5: list the edge cases before coding.** The usual ones: empty input, one element, a single step, ties or equal values, the boundary value from the constraints (overflow, the largest `n`), and "already finished at the start."

**Step 6: trace 3–6 steps** as a table, one row per step, one column per state name. Use a tiny input (attempt review 001 §5).

---

## 2. Queue simulation, then a formula: Time Needed to Buy Tickets (2073)

**Problem (paraphrased).** `n` people stand in a line; person `i` (0-indexed from the front) wants to buy `tickets[i]` tickets. Each second, the person at the front buys **one** ticket. If they still want more, they go to the **back** of the line (instantly); if they're done, they leave. Return how many seconds pass until person `k` has bought all of their tickets.
Examples: `tickets = [2,3,2], k = 2` → `6`; `tickets = [5,1,1,1], k = 0` → `8`.
Constraints: `1 <= n <= 100`; `1 <= tickets[i] <= 100`; `0 <= k < n`.

### 2.1 The direct simulation

**Rules:** (1) the front person buys one ticket (one second passes); (2) if they need more, they go to the back; otherwise they leave; (3) stop when person `k` has bought their last ticket.

**State:**

| Name | Stands for | Valid set |
|---|---|---|
| `line` | the people waiting, front first (a `deque` of indices) | each index at most once |
| `left[i]` | tickets person `i` still needs | `0 … tickets[i]` |
| `time` | seconds passed so far | `0, 1, 2, …` |

**One step:** pop the front person `p`; `left[p] -= 1`; `time += 1`; if `p == k` and `left[p] == 0`, stop; if `left[p] > 0`, append `p` to the back.

```python
from collections import deque

def timeRequiredToBuy_simulated(tickets, k):
    line = deque(range(len(tickets)))    # indices of people waiting, front first
    left = tickets[:]                     # tickets each person still needs (a copy: don't change the input)
    time = 0                              # seconds passed
    while True:
        p = line.popleft()                # the front person buys one ticket
        left[p] -= 1
        time += 1
        if p == k and left[p] == 0:       # person k just finished: stop (check BEFORE re-queueing)
            return time
        if left[p] > 0:
            line.append(p)                # still needs more: back of the line
```

Trace `tickets = [2,3,2], k = 2` (from running it):

| second | buys | `left` after | `line` after |
|---|---|---|---|
| 1 | 0 | `[1, 3, 2]` | `[1, 2, 0]` |
| 2 | 1 | `[1, 2, 2]` | `[2, 0, 1]` |
| 3 | 2 | `[1, 2, 1]` | `[0, 1, 2]` |
| 4 | 0 | `[0, 2, 1]` | `[1, 2]` (0 is done and leaves) |
| 5 | 1 | `[0, 1, 1]` | `[2, 1]` |
| 6 | 2 | `[0, 1, 0]` | person 2 is done → **6** |

**How many steps is that?** At most `sum(tickets)`, which is at most `100 × 100 = 10⁴` here. That's fast. So the simulation is a complete answer for these constraints, and in an interview it's a good first answer.

### 2.2 Simulate first, then count: the O(n) formula

If the constraints were larger (`tickets[i]` up to 10⁹), the simulation would be too slow. The trace suggests a shortcut: instead of simulating seconds, **count how many tickets each person buys before person `k` finishes**, since each ticket is one second.

Derive it, using rounds (one round = everyone currently in line buys once):

1. Person `k` buys exactly `tickets[k]` tickets, one per round, and finishes in round `tickets[k]`.
2. **A person in front of `k` (`i < k`)** buys in every round up to and including round `tickets[k]`, unless they run out first. So they buy `min(tickets[i], tickets[k])`.
3. **Person `k` itself** buys `tickets[k]`, which is `min(tickets[k], tickets[k])`, so the same formula as `i < k` works (`i <= k`).
4. **A person behind `k` (`i > k`)**: in the last round, `k` finishes **before** they get their turn. So they only buy in rounds `1 … tickets[k] - 1`: `min(tickets[i], tickets[k] - 1)`.

```python
def timeRequiredToBuy(tickets, k):
    total = 0                            # every ticket bought before k finishes = one second
    for i, want in enumerate(tickets):
        if i <= k:                       # at or in front of k: buys in every round up to k's last
            total += min(want, tickets[k])
        else:                            # behind k: misses k's last round
            total += min(want, tickets[k] - 1)
    return total
```

Check with the first example: person 0 buys `min(2, 2) = 2`, person 1 `min(3, 2) = 2`, person 2 `min(2, 2) = 2`, so 6 ✓. The second example: person 0 buys 5; persons 1–3 are behind `k = 0` and buy `min(1, 4) = 1` each, so `5 + 3 = 8` ✓.

**The lesson:** the simulation wasn't wasted. It gave you a correct answer, a trace, and a test oracle, and the trace showed the counting idea. "Simulate, then look at the trace for a shortcut" is a reliable path.

---

## 3. Position and direction: Robot Bounded in Circle (1041)

**Problem (paraphrased).** A robot starts at `(0, 0)` on an infinite plane, facing **north**. It follows a string `instructions`: `G` = go forward 1 unit; `L` = turn 90° left; `R` = turn 90° right. It repeats `instructions` **forever**. Return `True` if there's a circle the robot never leaves (its path stays bounded).
Examples: `"GGLLGG"` → `True` (it goes north 2, turns around, comes back to the origin); `"GG"` → `False` (it keeps going north); `"GL"` → `True` (after 4 repetitions it's back at the origin).
Constraints: `1 <= len(instructions) <= 100`; only `G`, `L`, `R`.

### 3.1 The direction table

**State:**

| Name | Stands for | Valid set |
|---|---|---|
| `x`, `y` | the robot's position (x grows to the east, y grows to the north) | any integers |
| `d` | which way it faces, as an index into `DIRS` | `0 … 3` |

`DIRS` lists the directions **in clockwise order**: north, east, south, west, each as the change in `(x, y)` for one step:

```python
DIRS = [(0, 1), (1, 0), (0, -1), (-1, 0)]   # N, E, S, W: clockwise
```

**Turning, derived from the order of the table:**
- **Right** is the next direction clockwise: `d + 1`. After west (3) comes north (0), so wrap with `% 4`: `(d + 1) % 4`.
- **Left** is the previous direction: `d - 1`. From north (0) that's `-1`, which should be west (3). `(d - 1) % 4` works in Python (Python's `%` returns a value in `0 … 3` even for `-1`), but `(d + 3) % 4` says the same thing without relying on that: turning left once is the same as turning right three times. Check: north (0) → `(0 + 3) % 4 = 3`, west ✓.

(This is lecture 001's direction table in a new setting. Note it uses `(x, y)` with y pointing **north** here, since it's a plane, not a grid's `(row, col)` where rows grow **downward**.)

### 3.2 The stopping problem: "forever"

You can't simulate forever. So ask: **what does one full pass of `instructions` do?** It moves the robot by some fixed change in position and turns it by some fixed amount. Every pass does the same thing, relative to where the robot faces at the start of that pass.

1. **If after one pass the robot is back at `(0, 0)`:** every pass returns it to the origin. Bounded.
2. **If after one pass it faces north again (but isn't at the origin):** the next pass starts in exactly the same orientation, so it moves by the **same** change again, and again. The distance grows without limit. **Unbounded.**
3. **If after one pass it faces any other direction:** the pass's movement gets rotated each time. If it ends facing east or west (a quarter turn), four passes rotate the movement through all four directions, and the four movements cancel out: back at the origin after 4 passes. If it ends facing south (a half turn), two passes cancel. Either way, it returns to the origin, so it's **bounded**.

So: **bounded exactly when, after one pass, the robot is at the origin or isn't facing north.**

```python
DIRS = [(0, 1), (1, 0), (0, -1), (-1, 0)]   # N, E, S, W: clockwise

def isRobotBounded(instructions):
    x = y = 0                            # position
    d = 0                                # index into DIRS: 0 = north
    for ch in instructions:              # ONE pass
        if ch == "G":
            dx, dy = DIRS[d]
            x += dx
            y += dy
        elif ch == "L":
            d = (d + 3) % 4              # one left = three rights
        else:                            # "R"
            d = (d + 1) % 4
    return (x, y) == (0, 0) or d != 0    # back home, or not facing north
```

Trace `"GL"` (from running it): `G` → `(0, 1)` facing N; `L` → `(0, 1)` facing W. Not at the origin, but not facing north, so **True** ✓. The verification ran the robot for 4 full passes and checked it was back at the origin exactly when this function returns `True`, on 3,000 random instruction strings.

**The lesson:** when a simulation never ends, **simulate one repeating unit** (a pass, a cycle, a day) and reason about what repeating it does.

---

## 4. Bouncing between edges: Zigzag Conversion (6)

**Problem (paraphrased).** Write the string `s` in a zigzag on `numRows` rows: down the rows, then diagonally back up, then down again, and so on. Then read the rows left to right, top row first, and return that string.
Example: `s = "PAYPALISHIRING"`, `numRows = 3`:
```
P   A   H   N
A P L S I I G
Y   I   R
```
→ `"PAHNAPLSIIGYIR"`. With `numRows = 4` → `"PINALSIGYAHRPI"`. `s = "A"`, `numRows = 1` → `"A"`.
Constraints: `1 <= len(s) <= 1000`; `1 <= numRows <= 1000`.

**Simplify first:** the columns and spaces don't matter for the answer. Each character just goes onto some row, in order. So the only question is **which row each character goes on.**

**State:**

| Name | Stands for | Valid set |
|---|---|---|
| `rows[r]` | the characters placed on row `r` so far, in order | `r` in `0 … numRows - 1` |
| `row` | the row the **next** character goes on | `0 … numRows - 1` |
| `step` | which way `row` is moving: `+1` (down) or `-1` (up) | `{+1, -1}` |

**One step:** put the character on `row`; then decide the direction; then move.

**The bounce rule, derived:** after placing on row `row`, the next row is `row + step`. That must stay in the valid set `0 … numRows - 1`. If you're **at** the top (`row == 0`), the only valid next row is below, so `step = +1`. If you're **at** the bottom (`row == numRows - 1`), `step = -1`. Otherwise keep going. Decide this **after** placing and **before** moving, so the move never leaves the valid set.

**The edge case the bounce rule can't handle:** `numRows = 1`. Then row 0 is both the top and the bottom, and the zigzag is just the original string. Handle it first.

```python
def convert(s, numRows):
    if numRows == 1:                     # top == bottom: no zigzag, and the bounce rule can't decide
        return s
    rows = [""] * numRows                # characters on each row, in order
    row = 0                              # row for the next character
    step = 1                             # +1 = moving down, -1 = moving up
    for ch in s:
        rows[row] += ch
        if row == 0:                     # at the top edge: the only way is down
            step = 1
        elif row == numRows - 1:         # at the bottom edge: the only way is up
            step = -1
        row += step                      # stays in 0 … numRows-1 because of the two checks above
    return "".join(rows)
```

Rows for the first 7 characters with `numRows = 3` (from running it): `P→0, A→1, Y→2, P→1, A→0, L→1, I→2`. That's the down-up-down pattern.

**What happens without the `numRows == 1` check:** `row == 0` is true, so `step = 1`, then `row` becomes 1, and `rows[1]` doesn't exist on the next character: `IndexError`. A two-point check on the smallest `numRows` catches it.

---

## 5. A circle that shrinks: Find the Winner of the Circular Game (1823)

**Problem (paraphrased).** `n` friends, numbered `1 … n`, sit in a circle clockwise. Start at friend 1. Count `k` friends clockwise, **including the one you start at** (wrapping around the circle). The friend you land on leaves the circle. Start again from the friend **clockwise of the one who left**, and repeat until one friend is left. Return the winner's number.
Examples: `n = 5, k = 2` → `3`; `n = 6, k = 5` → `1`.
Constraints: `1 <= k <= n <= 500`.

**State:**

| Name | Stands for | Valid set |
|---|---|---|
| `friends` | the friends still in the circle, in clockwise order (a list) | length `1 … n` |
| `start` | box index (in `friends`) of the friend where counting starts | `0 … len(friends) - 1` |

**Which box is removed? Derive it with boxes.** Counting `k` friends **including** the start means: the start is the 1st, the next is the 2nd, …, so the k-th is `k - 1` boxes after the start. That's box `start + k - 1`, which may run past the end of the list. Going past the end means wrapping around to the front, which is what `%` does:

> **`out = (start + k - 1) % len(friends)`**

Check with `k = 1`: you count only the start itself, so the start leaves. `(start + 0) % len = start` ✓.

**Where does counting restart?** At the friend clockwise of the one who left. After `friends.pop(out)`, every friend after `out` slides one box left, so the next friend **is now at box `out`**. Unless `out` was the last box: then there's no box `out` any more, and the next friend clockwise is box 0. Both cases are `out % len(friends)` (with the new, shorter length): if `out < len`, it's `out`; if `out == len`, it's 0.

```python
def findTheWinner(n, k):
    friends = list(range(1, n + 1))      # still in the circle, clockwise
    start = 0                             # box where counting starts
    while len(friends) > 1:
        out = (start + k - 1) % len(friends)   # the k-th friend, counting the start as 1st
        friends.pop(out)
        start = out % len(friends)        # the friend clockwise of `out` slid into box `out` (or wrap to 0)
    return friends[0]
```

Trace `n = 5, k = 2` (from running it):

| `friends` | `start` | `out` | leaves |
|---|---|---|---|
| `[1, 2, 3, 4, 5]` | 0 | `(0 + 2 - 1) % 5 = 1` | 2 |
| `[1, 3, 4, 5]` | 1 | `(1 + 2 - 1) % 4 = 2` | 4 |
| `[1, 3, 5]` | 2 | `(2 + 2 - 1) % 3 = 0` (wrapped) | 1 |
| `[3, 5]` | 0 | `(0 + 2 - 1) % 2 = 1` | 5 |
| `[3]` | | | winner **3** ✓ |

**Cost:** `n - 1` rounds, each with an O(n) `pop`, so O(n²), which is 250,000 at most here: fine. (There's an O(n) formula for this game, the Josephus recurrence. It's a stretch topic; the simulation is the expected answer at this size.)

---

## 6. Events that interact: Asteroid Collision (735)

**Problem (paraphrased).** `asteroids` lists asteroids in a row. Each value's absolute value is its size, and its sign is its direction (positive = moving right, negative = moving left). All move at the same speed. When two meet, the smaller one explodes; if they're the same size, both explode. Two asteroids moving in the same direction never meet. Return the asteroids left after all collisions, in order.
Examples: `[5,10,-5]` → `[5,10]` (`-5` hits `10` and explodes); `[8,-8]` → `[]`; `[10,2,-5]` → `[10]` (`-5` destroys `2`, then is destroyed by `10`); `[-2,-1,1,2]` → `[-2,-1,1,2]` (no one meets).
Constraints: `2 <= len(asteroids) <= 10^4`; `-1000 <= asteroids[i] <= 1000`; no zeros.

**When do two asteroids meet? Derive it, don't guess it.** Only when the left one moves **right** and the right one moves **left** (they move toward each other). Every other pair moves apart or in parallel. In particular, a left-moving asteroid on the left and a right-moving one on the right (`[-2, 1]`) move **apart**.

**Which pairs can ever meet?** Process asteroids left to right, and keep the survivors so far. A new asteroid moving right can't hit anything to its left (it moves away from them). A new asteroid moving left can only hit **the nearest survivor to its left**, and only if that one moves right. If it destroys that one, the next-nearest survivor becomes the nearest. "The nearest survivor, and the next one after it's removed" is a stack (lecture 013: the most recent unresolved item).

**State:**

| Name | Stands for |
|---|---|
| `stack` | survivors so far, left to right; top = the nearest one to the left of the new asteroid |
| `alive` | whether the new asteroid is still intact |

**One step (one new asteroid `a`):** while `a` is alive, moves left, and the top of the stack moves right, they collide: three cases by size. Then, if `a` is still alive, push it.

```python
def asteroidCollision(asteroids):
    stack = []                           # survivors, left to right; top = nearest to the new one
    for a in asteroids:
        alive = True                     # is the new asteroid still intact?
        while alive and a < 0 and stack and stack[-1] > 0:   # they move toward each other
            if stack[-1] < -a:           # top is smaller: it explodes, keep checking
                stack.pop()
            elif stack[-1] == -a:        # same size: both explode
                stack.pop()
                alive = False
            else:                        # top is bigger: the new one explodes
                alive = False
        if alive:
            stack.append(a)
    return stack
```

Trace `[10, 2, -5]` (from running it):

| new | collisions | `stack` after |
|---|---|---|
| 10 | none (moving right) | `[10]` |
| 2 | none (moving right) | `[10, 2]` |
| −5 | vs 2: 2 is smaller, pops; vs 10: 10 is bigger, −5 explodes | `[10]` |

**The three cases are the "many small decisions":** smaller, equal, bigger. Each needs its own line, and the equal case (both explode) is the one most often forgotten. Test `[8, -8]` every time.

**Cost:** each asteroid is pushed once and popped at most once, so O(n) (lecture 013's amortized argument).

---

## 7. Digit by digit, with a limit: Reverse Integer (7)

This is one of the problems from your July baseline (the digits came out in the wrong order).

**Problem (paraphrased).** Given a signed 32-bit integer `x`, return `x` with its digits reversed. If the reversed value falls outside the signed 32-bit range `[-2^31, 2^31 - 1]`, return `0`. Assume the environment can't store 64-bit integers.
Examples: `123` → `321`; `-123` → `-321`; `120` → `21`; `1534236469` → `0` (the reverse, 9646324351, is too big).
Constraints: `-2^31 <= x <= 2^31 - 1`.

**The process:** take digits off the **end** of `x` one at a time, and put each onto the **end** of the result.

**State:**

| Name | Stands for |
|---|---|
| `x` | the digits not yet moved (working with `abs(x)`) |
| `rev` | the reversed number built so far |
| `sign` | `1` or `-1`, applied at the end |

**One step, derived:**
- The last digit of `x` is `x % 10`. Removing it is `x //= 10` (lecture 008: `% 10` is "the box at the end," `// 10` is "everything before it").
- Putting a digit on the end of `rev` shifts `rev` one place left, then adds: `rev = rev * 10 + digit`.

Trace `123`: `rev` goes `3`, then `3·10 + 2 = 32`, then `32·10 + 1 = 321` ✓. Taking from the end and adding to the end reverses the order, which is the whole point. (In July the digits were collected in the original order, so the result wasn't reversed.)

**Why work with `abs(x)`:** Python's `%` and `//` round toward −∞ for negative numbers. From running it: `-123 % 10` is `7` and `-123 // 10` is `-13`, not the `3` and `-12` you'd want. Working on the absolute value and applying the sign at the end avoids that whole problem.

**The overflow check, derived** (for the "can't store 64-bit" rule; Python's integers never overflow, but the interviewer is asking whether you can check *before* it happens). The result is allowed up to `limit`: `2^31 - 1` for positive numbers and `2^31` (as an absolute value) for negative ones. The next value is `rev * 10 + digit`, and it must satisfy:

```
rev * 10 + digit <= limit
rev * 10         <= limit - digit
rev              <= (limit - digit) // 10      (integer division: rev is an integer)
```

So **if `rev > (limit - digit) // 10`, the next step would overflow**: return 0 before doing it.

```python
def reverse(x):
    sign = -1 if x < 0 else 1
    x = abs(x)                           # avoid Python's floor behaviour of % and // on negatives
    limit = 2**31 - 1 if sign == 1 else 2**31    # largest allowed absolute value of the result
    rev = 0                              # the reversed number so far
    while x > 0:
        digit = x % 10                   # the last digit of what's left
        x //= 10
        if rev > (limit - digit) // 10:  # rev * 10 + digit would exceed the limit
            return 0
        rev = rev * 10 + digit           # put the digit on the end
    return sign * rev
```

Edge cases, all checked by running: `120` → `21` (the trailing zero becomes a leading zero, which just disappears); `0` → `0` (the loop doesn't run); `-2147483648` → `0`; `1463847412` → `2147483641` (just fits). In Python you could also reverse first and then check the range; say that, and offer the check-before version when the interviewer mentions the 64-bit rule.

---

## 8. Simultaneous updates and too many steps: Prison Cells After N Days (957)

**Problem (paraphrased).** There are 8 prison cells in a row, each occupied (`1`) or empty (`0`). Each day, **all cells change at the same time** by these rules: a cell becomes occupied if its two neighbours were both occupied or both empty the day before; otherwise it becomes empty. The first and last cells have only one neighbour, so they always become empty. Given the starting `cells` and a number of days `n`, return the cells after `n` days.
Examples: `cells = [0,1,0,1,1,0,0,1], n = 7` → `[0,0,1,1,0,0,0,0]`; `cells = [1,0,0,1,0,0,1,0], n = 1000000000` → `[0,0,1,1,1,1,1,0]`.
Constraints: `len(cells) == 8`; `1 <= n <= 10^9`.

### 8.1 "At the same time": build the next state from the old one

"All cells change at the same time" means every cell's new value depends on **yesterday's** neighbours. If you update the list in place, from left to right, cell 2 would look at cell 1's **new** value, which breaks the rule.

From running both on `[0,1,0,1,1,0,0,1]`:
- correct next day: `[0, 1, 1, 0, 0, 0, 0, 0]`;
- updating in place: `[0, 1, 1, 1, 0, 1, 1, 0]` (wrong from cell 3 on).

The fix (lecture 001 §7's in-place hazard): **read from the old list, write into a new one.**

```python
def next_day(cells):
    new = [0] * 8                        # cells 0 and 7 always become empty (one neighbour only)
    for i in range(1, 7):                # cells with two neighbours: boxes 1 … 6
        new[i] = 1 if cells[i - 1] == cells[i + 1] else 0    # reads only YESTERDAY's values
    return new
```

### 8.2 Too many days: find the repeat

**Count the steps first.** `n` can be 10⁹. Even at one fast step per microsecond, that's minutes: far too slow.

**Count the states instead.** Each day's cells are 8 zeros and ones, so there are at most 2⁸ = 256 different states. (After day 1 the two end cells are always 0, so really at most 2⁶ = 64.) If you simulate more days than there are states, **some state must appear twice.** And because each day depends only on the day before, once a state repeats, everything after it repeats too: the sequence is a **cycle**.

**Use the cycle:**
1. Keep a dictionary `seen` from state to the day it was first seen.
2. If today's state is already in `seen`, then `cycle = day - seen[state]` days later it'll be this state again, and again.
3. The days still to go are `n - day`. Whole cycles change nothing, so only `(n - day) % cycle` more days matter. Simulate just those.

```python
def prisonAfterNDays(cells, n):
    seen = {}                            # state (as a tuple) -> the day it was first seen
    day = 0
    while day < n:
        state = tuple(cells)             # lists can't be dict keys; tuples can
        if state in seen:
            cycle = day - seen[state]    # the states repeat every `cycle` days from here on
            for _ in range((n - day) % cycle):   # whole cycles change nothing
                cells = next_day(cells)
            return cells
        seen[state] = day
        cells = next_day(cells)
        day += 1
    return cells                         # n was reached before any repeat
```

For the second example, the first repeat happens at day 15, of the state first seen on day 1 (from running it): a cycle of 14 days. So instead of 10⁹ steps, it does 15, plus at most 13 more.

**The lesson:** when a simulation has too many steps, ask **how many different states there can be.** If that number is small, a repeat is guaranteed, and a dictionary finds it.

---

## 9. Recognizing a simulation, and checking if it's fast enough

### 9.1 The kinds of simulation, and the tool for each

| Kind | Signal | Tool | Section |
|---|---|---|---|
| a queue of people/tasks taking turns | "goes to the back of the line" | `deque`; then look for a counting formula | §2 |
| position + direction | robot, "turn left/right" | `DIRS` table, `% 4` turns; one pass for "forever" | §3 |
| moving back and forth between two edges | zigzag, bouncing, ping-pong | `step = ±1`, flipped **at** an edge | §4 |
| a circle | "in a circle," "wrap around," "clockwise" | `% length`; `(start + k - 1) % len` for "count k including start" | §5 |
| things that meet and interact | collisions, cancelling, matching pairs | a stack of survivors | §6 |
| digits of a number | reverse, sum of digits, palindrome number | `% 10` and `// 10`; work on `abs` | §7 |
| "all at the same time" | each day/round, every cell changes | build the next state in a new list | §8.1 |
| huge number of steps | `n` up to 10⁹ | count the states → find the repeat; or a per-pass change; or a formula | §2.2, §3.2, §8.2 |
| a grid that changes | Game of Life, spiral walk | lecture 001 | — |

### 9.2 Is simulating fast enough? Count before you code

| Steps the simulation takes | Verdict (Python) |
|---|---|
| up to about 10⁶ | fine |
| about 10⁷–10⁸ | risky; look for something faster |
| beyond 10⁸ | too slow: find a repeat, a per-pass change or a formula |

To count, multiply: number of steps × work per step. Buy Tickets: `sum(tickets) ≤ 10⁴` steps × O(1) → fine. Winner: `n` rounds × O(n) pop → 2.5·10⁵ → fine. Prison Cells: 10⁹ days → too slow, so §8.2.

### 9.3 Tracing a simulation

Simulations are the best case for a trace table: the state is a few named values, and each row is one step. Use the state table from step 2 of the method as the column headers. Check each row against the rules **written in step 1**, not against what you expect to happen (your Daily Temperatures trace slipped because a row was written from expectation; here, evaluate each rule's condition on every row).

---

## 10. Practice ladder

For each one, before coding, write the method's steps 1–5 as comments: the rules in your words, the state table, one step, when it stops, and the edge cases. Count the steps against the constraints.

| # | Problem | Level | What it practises |
|---|---|---|---|
| 1 | 2073 Time Needed to Buy Tickets | Easy | queue simulation, then the formula |
| 2 | 1041 Robot Bounded in Circle | Medium | direction table; reasoning about one pass |
| 3 | 735 Asteroid Collision | Medium | interacting events with a stack; the equal case |
| 4 | 6 Zigzag Conversion | Medium | the bounce rule; the `numRows = 1` edge |
| 5 | 1823 Find the Winner of the Circular Game | Medium | `% length` on a shrinking circle |
| 6 | 7 Reverse Integer (redo) | Medium | digits from the end; the overflow check before it happens |
| 7 | 957 Prison Cells After N Days | Medium | simultaneous update; find the repeat |
| 8 | 54 Spiral Matrix (redo, from lecture 001) | Medium | the same method on a grid |
| 9 | 1599 Maximum Profit of Operating a Centennial Wheel | Medium | a long rules-heavy statement; state per rotation |
| 10 | 2391 Minimum Amount of Time to Collect Garbage | Medium | simulate, then count (like §2.2) |
| stretch | 68 Text Justification (Hard), 2069 Walking Robot Simulation II, 289 Game of Life (lecture 001) | | many decisions in a row |

---

## Common mistakes

| Mistake | Fix |
|---|---|
| A state variable with no update line in the step (`tail`) | list the lines that change each name (§1 step 3) |
| Updating "at the same time" rules in place | read from the old state, write a new one (§8.1) |
| Checking the stop condition in the wrong place (re-queueing person `k` after they finish) | write the order of the step's actions in words first (§2.1) |
| `if`-chains for turning | a `DIRS` table in clockwise order; `(d + 1) % 4`, `(d + 3) % 4` (§3.1) |
| Counting `k` without saying whether the start counts | "including the start" → `(start + k - 1) % len` (§5) |
| Moving before checking the edge in a bounce | place, then set the direction at an edge, then move (§4) |
| Forgetting the single-row / single-element case | the two-point check on the smallest input |
| Forgetting the "equal" case in collisions or ties | test `[8, -8]`; list equal cases in step 5 |
| `%` and `//` on negative numbers | work on `abs(x)`; apply the sign at the end (§7) |
| Simulating 10⁹ steps | count the steps first; count the states (§8.2, §9.2) |
| Changing the input list while simulating (`tickets`) | copy it (`tickets[:]`) unless changing it is allowed |

---

## Self-check questions

1. What are the six steps of the simulation method?
<details><summary>Answer</summary>

Rules in your own words; name the state (name, meaning, valid set); write one step; decide when it stops; list edge cases; trace 3–6 steps.
</details>

2. In Buy Tickets, why does a person **behind** `k` buy at most `tickets[k] - 1` tickets?
<details><summary>Answer</summary>

In the round where `k` buys their last ticket, `k` finishes before the people behind them get their turn, so those people only buy in the earlier `tickets[k] - 1` rounds.
</details>

3. Derive "turn left" with a clockwise direction table, without using a negative number.
<details><summary>Answer</summary>

Left is one step counter-clockwise, which equals three steps clockwise: `(d + 3) % 4`. From north (0): `3`, west ✓.
</details>

4. Why is the robot bounded if, after one pass, it doesn't face north?
<details><summary>Answer</summary>

Each pass's movement is rotated by the same turn. After 4 passes (a quarter turn) or 2 (a half turn), the rotated movements point in opposite directions and cancel, so it's back at the origin.
</details>

5. In Zigzag, why is the direction decided after placing a character and before moving?
<details><summary>Answer</summary>

So the next row, `row + step`, is always in `0 … numRows - 1`: at the top the only valid move is down, at the bottom only up.
</details>

6. Why does Zigzag need `numRows == 1` handled separately?
<details><summary>Answer</summary>

Row 0 is both the top and the bottom. The `row == 0` check sets `step = 1`, the row becomes 1, and `rows[1]` doesn't exist.
</details>

7. Derive the index of the friend who leaves in the circular game.
<details><summary>Answer</summary>

Counting `k` friends including the start, the k-th is `k - 1` boxes after the start: `start + k - 1`, wrapped with `% len(friends)`.
</details>

8. After `friends.pop(out)`, why is the next start `out % len(friends)`?
<details><summary>Answer</summary>

The friend after `out` slides into box `out`. If `out` was the last box, there's no box `out` now, and the next friend clockwise is box 0. `out % len` gives `out` in the first case and 0 in the second.
</details>

9. When do two asteroids collide, and why is a stack the right structure?
<details><summary>Answer</summary>

Only when the left one moves right and the right one moves left. A new left-moving asteroid can only hit the nearest survivor to its left, then the next-nearest after that one's destroyed: the most recent survivor first, which is a stack.
</details>

10. Derive the overflow check for `rev * 10 + digit`.
<details><summary>Answer</summary>

`rev * 10 + digit <= limit` ⇔ `rev <= (limit - digit) // 10` (rev is an integer). If `rev > (limit - digit) // 10`, the next step overflows.
</details>

11. Why does Prison Cells need a new list for the next day?
<details><summary>Answer</summary>

All cells change at the same time, based on yesterday's neighbours. Updating in place makes later cells read their neighbours' new values.
</details>

12. Why must the Prison Cells states eventually repeat, and how do you use the repeat?
<details><summary>Answer</summary>

There are at most 2⁸ = 256 states, so within 257 days one repeats; each day depends only on the previous day, so from then on it cycles. With `cycle = day - seen[state]`, only `(n - day) % cycle` more days need simulating.
</details>

---

## Sources

- Problems: LeetCode 2073, 1041, 6, 1823, 735, 7, 957 (ladder: 54, 1599, 2391; stretch: 68, 2069, 289). Statements are paraphrased; examples and constraints come from long-standing problem pages (from my own knowledge, not re-fetched; 2026-10-27).
- Python: `collections.deque` (https://docs.python.org/3/library/collections.html#collections.deque); `%` and `//` on negative numbers (https://docs.python.org/3/reference/expressions.html#binary-arithmetic-operations).
- Robot Bounded's "one pass" argument and the Josephus problem (for 1823's O(n) recurrence): standard results, e.g. Graham, Knuth & Patashnik, *Concrete Mathematics*, §1.3 (the Josephus problem).
- Verification (2026-10-27): every solution compared on 3,000 random inputs with a reference (step-by-step simulation for 2073, 957 and 1823; four full passes for 1041; repeated pairwise collisions for 735; a row-by-position formula for 6; string reversal for 7, plus its overflow edge cases). Traces and counterexamples were produced by running the code.
