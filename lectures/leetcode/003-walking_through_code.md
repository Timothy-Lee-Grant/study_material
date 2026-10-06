# Lecture 003: Walking Through Code: How to Trace Any Problem Without Losing Track

> **For:** Timothy · **Date:** 2026-10-05
> **Prerequisites:** none. Lecture 001 Addendum A.5 introduced a trace table for Spiral Matrix and lecture 002 §9 introduced call-tree traces. This lecture generalizes both into one method that works for every problem type.
> **Why this lecture:** in your words: *"I have so many different things that I'm trying to keep track of, and then I forget if I changed or updated one thing… it just gets into a huge mess… halfway through I lose track of the state that I'm at."* Your tracker lists verification as your #1 weakness, and every bug you've had in the last 10 weeks would have been caught by a working trace. So this skill has the highest payoff of anything you can practice right now.
> **Your lab:** your Spiral Matrix II attempt from today (`examples.py`, Oct 5) is **not** analysed in the body of this lecture. §9 sets it up for you to trace yourself, and the answer key is hidden in a collapsed block.
> **Verification:** every trace table in this lecture was produced by actually running the code being traced, so the values are real.

---

## Core ideas (the answer key)

1. **You lose track because the state lives in your head.** A trace only works if **every value that changes is written down**, in a fixed layout, at fixed moments.
2. **Decide the layout before you start:** the input, the expected output, the granularity (one row per *what*?), and the columns. Changing the plan halfway is how traces turn into a mess.
3. **Never erase or overwrite a value. Add a new row.** "Did I already update `top`?" is answered by looking at the previous row, not by remembering.
4. **Copy unchanged values forward into every row.** It feels wasteful, but it's what stops you from losing track: every row is a complete snapshot.
5. **Execute the code literally, line by line, with your eyes on the code, not your memory of it.** Your bugs live in the gap between what you meant and what you wrote. Tracing what you *meant* skips exactly that gap.
6. **Write the expected answer (or an invariant) next to every row.** The trace's job is to find the **first row where actual ≠ expected**. That row is the bug.
7. **Pick the smallest input that exercises every branch.** Most traces should be 4–8 rows and take 3–5 minutes. If a trace is taking 20 minutes, the input is too big or the rows are too fine-grained.
8. **Each data structure has a best way to write it down:** a table for scalars, a picture of the grid for matrices, boxes and arrows for linked lists, a call tree for recursion, one row per level for BFS.
9. **Don't fix code mid-trace.** Mark the suspicious row, finish or stop the trace, then fix one line and re-trace from the start.
10. **When practicing, check your hand trace against a printed trace afterwards.** The place where they first differ is the specific tracing mistake you need to train out.

---

## Table of Contents

- [0. Why your traces fall apart (diagnosis)](#0-why-your-traces-fall-apart-diagnosis)
- [1. The Trace Protocol (the whole method on one page)](#1-the-trace-protocol-the-whole-method-on-one-page)
- [2. Choosing the input](#2-choosing-the-input)
- [3. Choosing granularity and columns](#3-choosing-granularity-and-columns)
- [4. Executing literally](#4-executing-literally)
- [5. Layouts for each kind of problem](#5-layouts-for-each-kind-of-problem)
- [6. Worked traces on your own past code](#6-worked-traces-on-your-own-past-code)
- [7. Tracing in an interview](#7-tracing-in-an-interview)
- [8. Training the skill: hand trace vs printed trace](#8-training-the-skill-hand-trace-vs-printed-trace)
- [9. Lab: trace your Spiral Matrix II](#9-lab-trace-your-spiral-matrix-ii)
- [10. Common tracing mistakes](#10-common-tracing-mistakes)
- [Self-check questions](#self-check-questions)
- [Sources](#sources)

---

## 0. Why your traces fall apart (diagnosis)

Your description, the Oct 3 Spiral trace (20 minutes, then misread `range(2, 2)` and stopped mid-pass), and how professionals trace point to six specific causes. Each one has a specific fix.

| # | What happens | Why it causes the mess | The fix |
|---|---|---|---|
| 1 | You hold some values in your head ("top is 1 now") | Working memory holds about 4 items. A spiral has 4 walls, a loop variable and an output list | **Everything that changes is on paper** (§1) |
| 2 | You update a value by changing it in place (crossing out or rewriting `top`) | Afterwards you can't tell whether a value is old or new: *"I forget if I changed or updated one thing"* | **Append-only rows**: never erase, always add a new row (§3.3) |
| 3 | You write only the value that changed | To know the current `left`, you have to scan back through rows | **Copy unchanged values forward** (§3.3) |
| 4 | You trace what the code is *supposed* to do | Your bugs are exactly where the code differs from the intent (`range(2, 2)`, `matrix[left][i]`) | **Execute literally**, one line at a time, eyes on the code (§4) |
| 5 | You don't know what the right value is at each step | You can't tell a wrong row from a right one, so you trace to the end and only learn "it's wrong somewhere" | **Expected-value column** (§3.4) |
| 6 | The input is big and the rows are too fine (one row per array element) | 30 rows, 20 minutes, no attention left by the time the bug shows up | **Smallest input that hits every branch; one row per meaningful step** (§2, §3.1) |

Notice that none of these is about intelligence or "being bad at this." Tracing is a clerical procedure. It feels hard because it's usually done *without* a procedure.

---

## 1. The Trace Protocol (the whole method on one page)

```
TRACE PROTOCOL
0. EXPECTED   Solve the input by hand, without the code. Write the expected output.
1. INPUT      Smallest input that runs every branch at least once (and every loop at least twice).
2. GRANULARITY One row per: loop iteration | block of code | function call | BFS level.
3. COLUMNS    Write the header now: the variables that change + the output-so-far + a CHECK column.
              Add a separate drawing for big structures (grid, list, tree).
4. EXECUTE    Finger on the code line. Do exactly what the line says. Evaluate every range()
              and every condition to a literal value. Write a NEW row at each checkpoint.
              Copy unchanged values forward. Never erase.
5. CHECK      At every row: does it match the expected value / invariant? First mismatch → STOP.
6. CONCLUDE   The first wrong row names the line that's wrong. Fix ONE thing. Re-trace from scratch.
```

Budget: **steps 0–3 take 1–2 minutes, step 4 takes 3–5 minutes.** If step 4 is going past 8 minutes, stop and choose a smaller input or a coarser granularity.

The rest of this lecture expands each step, then shows the layouts and worked examples.

---

## 2. Choosing the input

### 2.1 The rule

> **Smallest input that makes every branch run at least once, and every loop run at least twice.**

- **Every branch:** if the code has `if top <= bottom:`, you need an input where it's False *at some point*. Otherwise you never test the guard.
- **Every loop twice:** a loop that runs once can't show direction or update bugs. (Your Oct 3 Spiral: the left-column loop ran once, `range(1, 2) → [1]`, and gave the right answer by coincidence.)
- **Smallest:** every extra element is another row of work, with no new information.

### 2.2 The menu of good trace inputs

| Problem type | First trace (finds crashes) | Second trace (finds logic bugs) |
|---|---|---|
| Array / string | length 1, or the shortest valid input | length 4–5 with one "interesting" feature (duplicate, the target at the end) |
| Sliding window (size k) | n = k (exactly one window) | n = k + 2 (3 windows, so the slide runs twice) |
| Matrix | 1×n, n×1 | 3×3 or 3×4 (non-square), 4×4 if an inner loop must run twice |
| Linked list | 1 node, 2 nodes | 4–5 nodes |
| Recursion | the base case + one step above it (n=1, n=2, `"1"`, `"12"`) | 3 elements: `"226"`, `[1,2,3,1]` |
| Graph / BFS | 1 node, or no edges | 3–4 nodes with one branch, or a 3×3 grid |
| Two pointers / binary search | 2 elements | 5 elements with the target at an end |

### 2.3 Write the expected output first

Before looking at the code, solve the input **by hand** and write the answer at the top of the page. For step-by-step problems, also write a few intermediate expectations ("after the first pass, the top row should be 1 2 3"). These go into the CHECK column.

If you can't produce the expected output by hand, stop. You don't understand the problem yet, and tracing code won't fix that.

---

## 3. Choosing granularity and columns

### 3.1 Granularity: one row per *what*?

The most important decision, and the one that decides whether a trace takes 4 minutes or 20.

| Code shape | One row per… | Not per… |
|---|---|---|
| Single loop over an array | **iteration** | individual line |
| A loop body made of several blocks (spiral's four sides) | **block** (top row, right column…) | element written |
| Nested loops where the inner loop is simple | **outer iteration**, with the inner result summarized in one cell | inner iteration |
| Recursion | **call** (one line in the call tree) | line inside the call |
| BFS | **level** (or each pop if the queue is tiny) | each neighbor check |
| Linked list rewiring | **iteration**, drawn as a fresh snapshot of the list | each assignment, unless the assignment order is what you're testing |

**Rule:** zoom out to the coarsest step at which values *can* go wrong. Zoom in (line by line) only inside the one step you suspect.

### 3.2 Columns: decide them before the first row

A trace table has three kinds of columns:

| Kind | What goes in it | Example (Spiral) |
|---|---|---|
| **Position / control** | The step label, plus any condition evaluated at that step | `side`, `guard top<=bottom → T/F` |
| **State** | Every variable that changes, each in its own column | `top bottom left right number` |
| **Work + check** | What this step did (the `range` as a literal list, the cells written) + **expected / OK?** | `range(1,3)→[1,2]`, `wrote [1][2]=4 ✓` |

**List the state columns by scanning the code for every assignment** (`=`, `+=`, `.append`, `.add`, `.pop`). Every variable that gets assigned inside the loop gets a column. Loop-invariant inputs (`n`, the input array) don't.

### 3.3 The two bookkeeping rules that stop you losing track

**Rule A: append-only.** Every checkpoint gets a **new row**. Never cross out a number and write a new one in the same cell. If you made a tracing mistake, draw a line through the whole row and write a corrected row below it.

**Rule B: copy forward.** Every row contains the **full current value of every state column**, even the ones that didn't change. Copying `0` into the `left` column four times feels pointless, but it makes "what is `left` right now?" a lookup in one row, instead of a memory test.

Together they mean **the last row is always the complete current state.** That's exactly what you've been missing.

### 3.4 The CHECK column

Every row ends with a check against something you know independently:

- **Expected value:** from your hand solution ("top row should be 1 2 3 → ✓").
- **Invariant:** a statement that should be true every row ("window sum = sum of the actual window"; "walls only move inward"; "`fresh` = number of 1s left in the grid").
- **Contract:** for recursion, "is this return value really the answer for this subproblem?" (lecture 002 §9).
- **Write-once:** for fill-in problems, "was this cell empty before I wrote it?"

**The first ✗ is the bug.** Not the last wrong output, the *first* wrong row.

---

## 4. Executing literally

### 4.1 Be the interpreter, not the author

When you trace, you are not the person who wrote the code and knows what it's for. You're Python: you read one line, do exactly what it says, and move to the next. Practical habits:

1. **Point at the line** (finger, cursor, or a line number in a `line` column). Never trace from memory of the code.
2. **Read every index literally.** `matrix[left][i]` with `left=0, i=1` is `matrix[0][1]`. Write the literal cell, not "the left column."
3. **Evaluate every `range` to a literal list** before using it: `range(1, 0, -1) → [1]`. `range(2, 2) → []`. If you can't evaluate it instantly, that's a `range` drill item (lecture 001 Addendum A.6).
4. **Evaluate every condition to `True`/`False`** with the actual numbers: `top <= bottom` → `2 <= 1` → `False`. Write the `T/F` in the row.
5. **Follow control flow exactly.** A `while` condition is checked only at the top. A `return` inside a loop leaves the function immediately. A `continue` skips the rest of the body.

### 4.2 Literal-reading checklist for the lines that bite you

| Line pattern | Ask | Your history |
|---|---|---|
| `range(a, b, step)` | Literal list? Empty? Which direction? | Spiral ×4 |
| `x[a][b]` | Which is the row, which is the column? Is that what this block walks? | Spiral 10-02, Spiral II today? (see §9) |
| `if <condition>` | Evaluate with numbers. Strict or non-strict? Is there a `not`? | Climbing Stairs `not i+2<n` |
| A name that's similar to another name | Is it the *right* variable? (`d` vs `m`, `r` vs `nr`) | Birthday, Oranges |
| The last line of a block or function | Does it exist? (`return True`, un-choose, memo store) | Course Schedule, Word Search, LCS |

---

## 5. Layouts for each kind of problem

### 5.1 Scalars in a loop (sliding window, two pointers, counters)

A plain table, plus **the array written once at the top with index numbers**, so you can point at positions:

```
idx:  0  1  2  3  4
s  :  1  2  1  3  2         d=3, m=2   expected ways = 2   (windows [1,2],[2,1] sum to 3)

| i | add      | remove   | ws | actual window (CHECK) | ways |
|---|----------|----------|----|-----------------------|------|
```

The "actual window" column is the invariant check: compute the real sum of the window the code *should* hold and compare it with `ws`.

### 5.2 Matrices: draw the grid

For anything that reads or writes a grid, **draw the grid** and keep a table for the boundary variables:

```
grid after each block (write-once: fill cells as they're written; an already-filled cell = ✗)

 . . .        1 2 3        1 2 3
 . . .   →    . . .   →    . . 4   → ...
 . . .        . . .        . . 5
```

Two rules:
- **Write each value into the grid the moment the code writes it.** Draw the grid fresh after each *block* (not each cell), or keep one grid in pencil and fill cells in as you go. For fill problems, each cell is written once, so filling in never needs an eraser.
- **A write into a cell that's already filled is an immediate ✗** (for fill-once problems like Spiral II and Rotting Oranges).

### 5.3 Hash maps, sets, stacks, queues: a "board" next to the table

Collections are too big to copy into every row. Keep them in a **separate board** to the right, one line per change, with the step number:

```
| step | i | x | ... |        BOARD: seen (dict value → index)
|------|---|---|-----|        step 1: {2:0}
| 1    | 0 | 2 |     |        step 2: {2:0, 7:1}
| 2    | 1 | 7 |     |        step 3: {2:0, 7:1, 11:2}
```

Rewrite the **whole** collection on each changed line (it's usually small). That keeps the append-only rule: the latest line is the current state.

For **stacks**, write the stack horizontally with the top on the right: `[ 1, +, ( ]`. For **queues**, the front on the left: `front→ (0,0) (1,1) ←back`.

### 5.4 Linked lists: snapshot boxes and arrows

Pointer rewiring is destructive (once `curr.next` changes, the old link is gone), so **redraw the list for each iteration**, with variable labels under the nodes:

```
iteration 0:   1 → 2 → 3 → 4 → 5 → None
               ^slow   ^fast
```

For problems where the *order* of assignments matters (reversing a list), zoom in to one row per assignment for the first iteration only, then go back to one row per iteration.

**Always ask the landing question at the end:** "Which node is each pointer on when the loop exits?" (Your Rotate List bug is exactly a landing bug; see §6.2.)

### 5.5 Recursion: the call tree

From lecture 002 §9. One line per call, indented by depth, **return value written when the call finishes**, checked against the Contract Sentence:

```
f(0) on '226'
    f(1) on '26'
        f(2) on '6'
            f(3) = 1   (empty suffix)
        f(2) = 1       ✓ one way to decode "6"
        ...
```

For backtracking, add the shared state on each line: `dfs(1,1,k=0)  path={(1,1)}`. Then the un-choose (or the lack of one) is visible.

### 5.6 BFS: one row per level

```
| level | queue at start of level | popped → pushed (with marks) | visited/fresh after | CHECK |
```

The level loop (`for _ in range(len(queue))`) maps exactly onto one row. Distance or minutes = row number.

### 5.7 DP tables: fill in fill order

Draw the table with its base-case row/column already filled, then fill cells **in the order the loops visit them**, writing each cell's dependencies the first few times (`dp[2][1] = 1 + dp[3][2] = 1`).

---

## 6. Worked traces on your own past code

All values below came from running the code. In each one, look for the **first ✗**.

### 6.1 Sliding window: Birthday Chocolate, your attempt 2 (July)

The loop (after building the first window):

```python
i = length                          # length = m
while i < lengthS:
    windowSum += s[i]
    windowSum -= s[i-(d)]
    if windowSum == targetSum:
        ways += 1
    i += 1
```

Input `s = [1,2,1,3,2], d = 3, m = 2`. **Expected: 2** (windows `[1,2]` and `[2,1]`). Granularity: one row per iteration. The CHECK column is the invariant "`ws` equals the sum of the real window `s[i-m+1 .. i]`."

| i | add | remove | ws | real window (CHECK) | ways |
|---|---|---|---|---|---|
| init | `s[0]+s[1]` | — | 3 | `[1,2]` = 3 ✓ | 1 |
| 2 | `+s[2]=1` | `-s[2-3]=s[-1]=2` | 2 | `[2,1]` = 3 **✗** | 1 |
| 3 | `+s[3]=3` | `-s[0]=1` | 4 | `[1,3]` = 4 (coincidence) | 1 |
| 4 | `+s[4]=2` | `-s[1]=2` | 4 | `[3,2]` = 5 ✗ | 1 |

The first ✗ is at `i=2`, and the `remove` cell, read literally, shows the problem: `s[2-3]` is `s[-1]`, the **last** element of the array (Python negative index), not the element leaving the window. The line uses `d` (the day, 3) where it needs `m` (the window length, 2). Three rows, about two minutes. Without the "real window" column, you'd only learn at the end that the answer was 1 instead of 2.

### 6.2 Linked list: Rotate List, your attempt (July)

```python
while steps < k:
    steps += 1
    fast = fast.next
while fast:
    fast = fast.next
    slow = slow.next
new_head = slow.next
```

Input `1→2→3→4→5`, `k = 2`. **Expected result `4→5→1→2→3`, so `slow` must land on node 3** (the node *before* the new head). Granularity: one snapshot per iteration.

| step | fast | slow | CHECK |
|---|---|---|---|
| start | 1 | 1 | |
| advance 1 | 2 | 1 | |
| advance 2 | 3 | 1 | fast is k=2 ahead ✓ |
| loop 1 | 4 | 2 | |
| loop 2 | 5 | 3 | slow on 3 ← where we want to stop |
| loop 3 | None | 4 | **✗** loop continued: `while fast` was still True at fast=5 |

Exit: `slow = 4`, so `new_head = 5`, and the result is `5→1→2→3→4`. The first ✗ is the row where the loop *should* have stopped and didn't. To stop with `fast` on the last node (and `slow` one before the new head), the condition must be `while fast.next`. That's the landing question from §5.4.

### 6.3 Recursion: Climbing Stairs, your attempt (Oct 4)

```python
def bt(i):
    if i == n: return 1
    if dp[i] != -1: return dp[i]
    one_step_ways = bt(i+1)
    two_step_ways = 0
    if not i+2<n:
        two_step_ways = bt(i+2)
    ...
```

Input **n = 2** (base case + one step above it). **Expected 2** (`1+1`, `2`). Contract: `bt(i)` = ways from step `i` to the top. `dp` has 2 slots: `dp[0]`, `dp[1]`.

```
bt(0)
    bt(1)                         condition for two-step: not (1+2 < 2) = not False = True
        bt(2) = 1                 ✓ at the top: one way
        bt(3)                     ✗ step 3 is past the top; the contract has no meaning here
            3 == 2? no → dp[3] → IndexError (dp has 2 slots)
```

You don't even need to reach the crash. The moment you *write down* the call `bt(3)` and check it against the contract ("ways from step 3 to step 2?"), the line is wrong. Evaluating the condition literally (`not (3 < 2)` → `True`) shows that the guard lets the call through.

### 6.4 BFS: Rotting Oranges, your attempt (Sep 12)

```python
for _ in range(num_in_q):
    r, c = rotten.popleft()
    for dr, dc in [(-1,0), (1,0), (0,-1), (0,1)]:
        if r+dr>=len(grid) or r+dr<0 or c+dc>=len(grid[0]) or c+dc<0 or grid[r][c] != 1 or (r,c) in visited:
            continue
        rotten.append((r,c))
        visited.add((r,c))
days += 1
```

Input `[[2,1,1],[1,1,0],[0,1,1]]`. **Expected 4.** Granularity: one row per level, and for the first level only, zoom in to one row per neighbor (because the first level is where the logic is).

| level | popped | neighbor `(r+dr, c+dc)` | condition evaluated **literally** | pushed |
|---|---|---|---|---|
| 1 | (0,0) | (-1,0) | out of bounds → skip | — |
| | | (1,0) | in bounds; `grid[r][c]` = `grid[0][0]` = 2 ≠ 1 → skip **✗** (meant: `grid[1][0]` = 1) | — |
| | | (0,-1) | out of bounds → skip | — |
| | | (0,1) | `grid[0][0]` = 2 ≠ 1 → skip **✗** | — |
| end | queue empty | | | days = 1 → loop ends → `return -1` |

Reading `grid[r][c]` literally as `grid[0][0]` is what exposes it: the condition checks the cell being processed, not its neighbor. Your intent ("is the neighbor fresh?") and your code ("is *this* cell fresh?") differ, and only a literal reading shows that. The fix is to name the neighbor (`nr, nc = r + dr, c + dc`) and use only `nr, nc` afterwards.

### 6.5 What the four have in common

| Trace | Rows until the first ✗ | What made the ✗ visible |
|---|---|---|
| Birthday | 2 | the invariant column (real window sum) |
| Rotate List | 6 | the expected landing node, written before tracing |
| Climbing Stairs | 4 call lines | checking each call against the contract |
| Oranges | 2 | reading `grid[r][c]` literally |

All four would have been found **in under 5 minutes**, on inputs of size 2–5. None needed the full trace.

---

## 7. Tracing in an interview

Interviews are usually in a shared doc or a plain editor with no run button. Interviewers expect you to walk through an example after writing code, and they're watching *how* you do it as much as whether you find the bug.

### 7.1 The format: comments under the code

Write the trace as a comment block right under your function. It's visible, it's append-only, and it's easy to follow:

```python
# Trace: n = 3, expected [[1,2,3],[8,9,4],[7,6,5]]
# side      top bot lef rig  num   cells written            check
# top  →     0   2   0   2    1   [0][0..2] = 1 2 3        ✓
# right ↓    1   2   0   2    4   [1][2]=4 [2][2]=5        ✓
# ...
```

### 7.2 What to say

1. *"Let me test this on a small input. n = 3 is enough to run every block, and I'll check n = 1 for the edge."*
2. *"Expected output is …"* (write it).
3. *"I'll track top, bottom, left, right and the counter."* (Name your columns; it shows you have a plan.)
4. While tracing, read the literal values out loud: *"range of 1 to 0 step -1, that's just [1]; we write row 1, column 0 …"*
5. When something's off: *"This row doesn't match. We wrote cell 0,1, which was already filled. The index order is swapped here."* Then fix that one line and re-check that row.

Finding your own bug this way is a **positive signal** in an interview, not a failure. It's the thing they're testing.

### 7.3 Time budget

About 3–5 minutes for the main trace, 1 minute for the edge input. If the code is long, trace one full iteration of the main loop carefully, then summarize: *"the next iterations repeat the same pattern with smaller walls."*

---

## 8. Training the skill: hand trace vs printed trace

In practice you have something you don't have in an interview: a computer. Use it to **grade your tracing**, not to replace it.

1. Trace by hand first (protocol §1). Write down your predicted final output.
2. Then add one `print` per checkpoint, using the **same columns as your table**, and run it:

```python
print(f"{'top →':8} top={top} bottom={bottom} left={left} right={right} number={number}")
```

3. Compare your table with the printed lines, row by row. **The first row where they differ is a tracing mistake**, not a code bug. Note what kind it was:

| Kind of tracing mistake | Example | Drill |
|---|---|---|
| Misread `range` | thought `range(2,2)` contains 2 | lecture 001 Addendum A.6 |
| Traced intent, not code | "wrote the left column" when the code wrote row 0 | read indices literally (§4.1) |
| Skipped a line | forgot `top += 1` | finger on the line |
| Lost a value | used an old `right` | copy forward (§3.3) |
| Wrong control flow | assumed `while` exits mid-body | §4.1 point 5 |

4. Log the kind in your tracker. After about 10 traces you'll know your personal top-2 tracing mistakes, and they'll fade.

Only **after** that, Submit. The metric worth tracking: *"Did my hand trace agree with the printed trace?"* and *"Did the traced solution pass on the first Submit?"*

---

## 9. Lab: trace your Spiral Matrix II

Your attempt from today (`examples.py`, Oct 5). Don't submit it yet and don't run it. Trace it by hand with the protocol, *then* run it, *then* open the answer key.

**Step 0: Expected output.** Fill in by hand for n = 3:

```
 _ _ _
 _ _ _
 _ _ _
```

**Step 1: Input.** n = 3 runs all four blocks and a second lap. Then n = 1 as the edge.

**Step 2: Granularity.** One row per block (top / right / bottom / left), plus one row for each `while` check.

**Step 3: Columns.** Fill this table in (append-only, copy forward):

| # | block | guard → T/F | `range(...)` → literal list | cells written (literal `[r][c]=v`) | top | bot | left | right | number | CHECK (write-once? matches expected?) |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 | start | | | | 0 | 2 | 0 | 2 | 1 | |
| 1 | while | `1 <= 9` → | | | | | | | | |
| 2 | top → | — | | | | | | | | |
| 3 | right ↓ | `top<=bottom` → | | | | | | | | |
| 4 | bottom ← | | | | | | | | | |
| 5 | left ↑ | | | | | | | | | |
| 6 | while | | | | | | | | | |
| … | | | | | | | | | | |

And keep the grid drawing next to it, filling cells as they're written:

```
 . . .
 . . .
 . . .
```

**Step 4:** for every row, read the code line literally, especially the indices inside `matrix[...][...]`.

**Step 5:** stop at the first ✗.

**Step 6:** if you find a bug, fix that one line, re-trace n = 3 from the start, then trace n = 1. Then run it with prints (§8) and compare with your table. Then submit.

**Your guard question from the comments, answered:** before a block that walks *along* a row (the bottom row), the thing that must exist is **that row**: `top <= bottom`. The columns it walks across are handled by the `range` itself: if `left > right`, the range is empty and nothing happens. So the guard checks the dimension you walk **on**, and the range handles the dimension you walk **along**. Checking both (as you did) is also correct, just more than needed. And if you're unsure about a guard, the trace is how you settle it: trace the input where the guard matters (here, the n = 3 second lap) and see what happens with and without it.

<details><summary><b>Answer key: open only after you've traced it yourself</b></summary>

Expected for n = 3:

```
1 2 3
8 9 4
7 6 5
```

The actual run of your code:

| block | `range` → list | cells written | top | bot | left | right | number | CHECK |
|---|---|---|---|---|---|---|---|---|
| top → | `range(0,3)` → [0,1,2] | `[0][0]=1 [0][1]=2 [0][2]=3` | 1 | 2 | 0 | 2 | 4 | ✓ |
| right ↓ | `range(1,3)` → [1,2] | `[1][2]=4 [2][2]=5` | 1 | 2 | 0 | 1 | 6 | ✓ |
| bottom ← | `range(1,-1,-1)` → [1,0] | `[2][1]=6 [2][0]=7` | 1 | 1 | 0 | 1 | 8 | ✓ |
| left ↑ | `range(1,0,-1)` → [1] | **`[0][1]=8`** | 1 | 1 | 1 | 1 | 9 | **✗ write-once: `[0][1]` already holds 2. Expected `[1][0]=8`** |
| top → | `range(1,2)` → [1] | `[1][1]=9` | 2 | 1 | 1 | 1 | 10 | ✓ |
| (remaining guards False) | | | | | | | | |

Output: `[[1,8,3],[-1,9,4],[7,6,5]]`.

**The bug:** in the left-column block, `matrix[left][i] = number` has the indices swapped. Walking *up a column* keeps the **column** fixed and changes the **row**: `matrix[i][left] = number`. With that one change, it produces the correct matrix for every n from 1 to 11 (verified).

Note that n = 2 passes even with the bug (the left-column block never runs for n = 2), and n = 1 passes too. **Only an input where the left column runs, n ≥ 3, can show this bug.** That's §2.1's "every branch runs" rule doing its job.

Everything else in your attempt was correct: the closed walls, `number <= n*n`, all four `range` calls, the guards and the wall updates. That's real progress since Oct 2. The remaining slip is the row/column order inside the subscript, the same kind as Spiral 10-02's `matrix[bottom][i]` in the column walk.
</details>

---

## 10. Common tracing mistakes

| Mistake | Symptom | Fix |
|---|---|---|
| Starting without an expected output | You reach the end and can't tell where it went wrong | §2.3: solve by hand first |
| Input too big | 20+ minutes, attention gone before the bug | §2.1: smallest input that hits every branch |
| Rows too fine | one row per element; dozens of rows | §3.1: one row per block/iteration/call/level |
| Values in your head | "wait, did I already decrement right?" | §3.3: append-only + copy forward |
| Tracing the intent | the trace "passes" but the submit fails | §4.1: literal reading, finger on the line |
| Fixing while tracing | half-old, half-new code in your head | §1 step 6: finish or stop, then fix one line |
| Stopping at "it looks done" | the bug is in the last block of the pass | finish the whole pass; the `while` only checks at the top |
| No CHECK column | you see wrong output but not the first wrong step | §3.4: expected / invariant / contract / write-once |
| Only one input | the guard or edge case never ran | always a second, tiny edge input (n = 1, 1×n, empty) |

---

## Self-check questions

1. Name the two bookkeeping rules that keep a trace from turning into a mess.
<details><summary>Answer</summary>

Append-only (never erase; a new row per checkpoint) and copy forward (every row has the full current value of every state variable).
</details>

2. What's the rule for choosing a trace input?
<details><summary>Answer</summary>

The smallest input that makes every branch run at least once and every loop run at least twice. Plus a second, tiny edge input.
</details>

3. Why write the expected output before tracing?
<details><summary>Answer</summary>

So each row can be checked as you go and you can stop at the first mismatch. Without it, you only learn at the end that something is wrong. And if you can't produce it by hand, you don't understand the problem yet.
</details>

4. You're tracing a spiral and the inner loop writes 5 cells. One row per cell, or one row per block?
<details><summary>Answer</summary>

One row per block, with the cells written listed in one cell of that row (and the grid drawing updated). Zoom in to single cells only inside a block you suspect.
</details>

5. What goes in a CHECK column? Name four kinds.
<details><summary>Answer</summary>

The expected value from your hand solution; an invariant (e.g. "window sum = real window sum", "walls only move inward"); the contract for recursion ("is this the answer for this subproblem?"); write-once for fill problems.
</details>

6. In the Birthday trace, which column exposed the bug, and how?
<details><summary>Answer</summary>

The "real window" invariant column: at `i=2` the code's `ws` was 2 but the real window `[2,1]` sums to 3. Reading the remove index literally showed `s[2-3] = s[-1]`, the wrong element, because `d` was used instead of `m`.
</details>

7. Why can't n = 2 reveal the bug in your Spiral II?
<details><summary>Answer</summary>

For n = 2 the left-column block never runs (its guard is False by then), so the buggy line never executes. Only inputs where every block runs, n ≥ 3, can expose it.
</details>

8. In a linked-list trace, what's the "landing question"?
<details><summary>Answer</summary>

"When this loop exits, which node is each pointer on?" Write the node you *want* it on before tracing, then check.
</details>

9. How do you trace a collection (dict, set, queue) without copying it into every row?
<details><summary>Answer</summary>

A separate board next to the table: one line per change, labeled with the step number, rewriting the whole (small) collection each time, so the latest line is the current state.
</details>

10. During practice, what's the difference between a hand trace that disagrees with a printed trace, and a printed trace that disagrees with the expected output?
<details><summary>Answer</summary>

Hand ≠ printed means a tracing mistake (you misread or lost track): train that. Printed ≠ expected means a code bug: fix the code at the first wrong row.
</details>

---

## Sources

- Every trace table in §6 and the §9 answer key was generated by running the code shown (your original attempts from `001_practice_medium.py` and `examples.py`) on 2026-10-05. Your Spiral Matrix II attempt was run for n = 1..5 as written, and for n = 1..11 with the one-line fix.
- Python semantics referenced: `range` (https://docs.python.org/3/library/stdtypes.html#range), negative indexing on sequences (https://docs.python.org/3/library/stdtypes.html#common-sequence-operations).
- Companions: `001-matrix_and_simulation_problems.md` Addendum A (range rule, side-level trace), `002-recursion_that_returns_answers.md` §9 (call trees), `private/000-weakness_tracker.md` (W2 verification, W7 submit-before-trace).
