# Lecture 001: Matrix and Simulation Problems, and How to Stop Losing Them to Off-by-Ones

> **For:** Timothy · **Date:** 2026-10-03
> **Prerequisites:** none. It helps to know Python's `range(start, stop, step)` and list-of-lists indexing.
> **Companion:** `lectures/carreer_path/002-the-leetcode-diagnosis-and-the-solving-protocol.md` covers the *general* solving protocol (loop invariants, trace tables, the debugging rules). You haven't read it yet, so this lecture teaches the parts of it that grid problems need (§4 and §8). Read 002 later for the full version.
> **Why this lecture:** you tried **54. Spiral Matrix** today (`lectures/leetcode/examples.py`), it didn't work, and you said you hate these problems because you're bad at them. This lecture is about the whole **matrix / simulation family**, not just spiral. But it starts from your attempt, because your attempt shows exactly which skill is missing. (Spoiler: it isn't the one you think.)
> **Verification:** every code block here was run in Python 3 against a brute-force reference on thousands of random grids (sizes 1×1 up to 7×7, including 1×n and n×1). Your original code was run too; its real output is shown in §0.

---

## Core ideas (the answer key)

1. **Grid problems are rarely hard algorithmically. They're hard at the *bookkeeping* level:** indices, boundaries, and which cells you've already used.
2. **Your spiral strategy was correct.** "Keep four walls (top, bottom, left, right), walk one side, move that wall inward" *is* the standard solution. What broke was bookkeeping.
3. **Pick one boundary convention and never mix it.** Closed `[lo, hi]` or half-open `[lo, hi)`. Mixing them means every loop needs its own hand-made ±1 fix, and you will get some of them wrong.
4. **Walls only move inward.** `top` and `left` only increase; `bottom` and `right` only decrease. A wall that moves outward is always a bug, and you can spot it without running anything.
5. **A direction table `DIRS = [(0,1),(1,0),(0,-1),(-1,0)]` turns four hand-written loops into one loop.** One loop can't suffer copy-paste drift.
6. **A matrix is a flat buffer in row-major order:** cell `(r, c)` lives at index `r * cols + c`, and `divmod(i, cols)` takes you back. Several "2D" problems are really 1D problems in disguise.
7. **Most transforms are index rewrites:** transpose `(r,c)→(c,r)`, horizontal flip `c→cols-1-c`, rotate 90° clockwise = transpose then flip. Same diagonal ⇔ same `r-c`; same anti-diagonal ⇔ same `r+c`.
8. **In-place problems are a read/write hazard:** you're overwriting cells you still need to read. There are three fixes: copy, encode the new state alongside the old one, or pick a write order that never clobbers unread data.
9. **When a grid is really a graph** (islands, spreading, shortest steps), use flood fill (DFS/BFS) with a visited mark. Use **BFS with a level loop** when the question says "minimum steps" or "minutes."
10. **Always test on 1×1, 1×n, n×1, and a non-square grid like 3×4.** Square-only thinking hides most grid bugs.

---

## Table of Contents

- [0. Direct answers: what actually happened in your spiral attempt](#0-direct-answers-what-actually-happened-in-your-spiral-attempt)
- [1. The map: the matrix/simulation family](#1-the-map-the-matrixsimulation-family)
- [2. The coordinate system, and the firmware twin](#2-the-coordinate-system-and-the-firmware-twin)
- [3. The cast of characters](#3-the-cast-of-characters)
- [4. Tool #1: one boundary convention](#4-tool-1-one-boundary-convention)
- [5. Spiral Matrix, solved properly, two ways](#5-spiral-matrix-solved-properly-two-ways)
- [6. Tool #2: index math and transforms](#6-tool-2-index-math-and-transforms)
- [7. Tool #3: the in-place hazard](#7-tool-3-the-in-place-hazard)
- [8. Tool #4: the grid is a graph](#8-tool-4-the-grid-is-a-graph)
- [9. The grid checklist (use it on every problem)](#9-the-grid-checklist-use-it-on-every-problem)
- [10. Lab: predict, then run](#10-lab-predict-then-run)
- [11. Practice ladder](#11-practice-ladder)
- [Misconceptions and common mistakes](#misconceptions-and-common-mistakes)
- [Interview relevance](#interview-relevance)
- [Self-check questions](#self-check-questions)
- [Sources](#sources)

---

## 0. Direct answers: what actually happened in your spiral attempt

### 0.1 Your strategy was right

Here is your first comment:

> *"I want the outer loop to keep going until everything is completely done… inside of this loop I should keep track of the valid top, bottom, left and right. Then I can go along each of those directions."*

That *is* the textbook solution. Nobody gave it to you; you came up with it. The algorithm wasn't the problem. Hold on to that, because the "I'm bad at these" story is about to meet the evidence.

### 0.2 What it actually did

I ran your code exactly as written:

| Input | Expected | Your code |
|---|---|---|
| `[[1,2,3],[4,5,6],[7,8,9]]` | `[1,2,3,6,9,8,7,4,5]` | `IndexError` |
| `[[1,2,3,4],[5,6,7,8],[9,10,11,12]]` | `[1,2,3,4,8,12,11,10,9,5,6,7]` | `IndexError` |
| `[[1,2,3]]` (1×3) | `[1,2,3]` | `IndexError` |
| `[[1],[2],[3]]` (3×1) | `[1,2,3]` | `IndexError` |
| `[[1]]` | `[1]` | `[1]` ✅ |

Here is the state after each side on the 3×3. This kind of table is the most useful debugging tool you have:

| Step | Read | top | bottom | left | right | answer so far |
|---|---|---|---|---|---|---|
| start | | 0 | 2 | 0 | **3** | `[]` |
| top row → | 1,2,3 ✅ | 1 | 2 | 0 | 3 | `[1,2,3]` |
| right col ↓ | 6 ❌ (missed 9) | 1 | 2 | 0 | 2 | `[1,2,3,6]` |
| bottom row ← | **6,5,4** ❌ (re-read row 1) | 1 | **3** | 0 | 2 | `[1,2,3,6,6,5,4]` |
| left col ↑ | nothing | 1 | **4** | 0 | 2 | same |
| top row → | 4,5 ❌ | 2 | 4 | 0 | 2 | … |
| bottom row ← | **crash**: `matrix[3]` doesn't exist | | | | | |

The first side was perfect. Every side after it was wrong in a *different* way. That's the fingerprint of one root cause showing up in several places.

### 0.3 The root cause: two conventions in one loop

```python
top = 0
bottom = len(matrix) - 1     # closed: bottom IS a valid row
left = 0
right = len(matrix[0])       # half-open: right is ONE PAST the last valid column
```

Three walls are **closed** (they point *at* a valid row or column). One wall is **half-open** (it points one past). From there, every loop needed its own correction, and you saw this happening:

> *"…when I index those two, I need to actually cut out the invalid index by one"*

That comment is the bug, described accurately as it happened. You noticed that the indices felt off, so you added `-1` corrections by hand, one loop at a time. Each correction needed a fresh judgment about which variable was closed and which was open, and with mixed conventions that judgment is different every time. Result:

| Line | Bug | Category |
|---|---|---|
| `right = len(matrix[0])` | Mixed convention (root cause) | Convention |
| `while left <= right or top <= bottom` | Should be `and`. You keep going only while there are rows **and** columns left. | Loop condition |
| `range(top, bottom)` (right column ↓) | `bottom` is closed, so this skips the last row (missed the 9) | Convention |
| `matrix[bottom-1][i]` (bottom row ←) | The `-1` fix belongs to `right`, not `bottom`. Reads the wrong row. | Convention |
| `bottom += 1` (after bottom row) | A wall moved **outward**. Should be `bottom -= 1`. | Progress |
| `range(bottom, top-1)` (left col ↑) | Counting *up* from a bigger number with no `-1` step, so it's empty | Direction |
| `matrix[bottom][i]` (left col ↑) | Fixed the row and varied the column. A column walk fixes the **column**: `matrix[r][left]`. | Copy-paste drift |
| `bottom += 1` (after left col) | Should be `left += 1`. A copy of the line above. | Copy-paste drift |

Look at the categories. **None of them is "didn't know the algorithm."** They are:

1. **Convention mixing** (§4 fixes this)
2. **Walls moving the wrong way** (§4.3: "walls only move inward")
3. **Copy-paste drift between the four sides** (§5.3: the direction table removes the four copies)

Grid problems pile up exactly these three bug types, which is why they feel so much harder than they are.

### 0.4 Your real gap, named honestly

You think "I'm bad at these problems." The evidence says: **you're good at the idea and untrained at index bookkeeping.** Bookkeeping is mechanical, so a few fixed rules fix it. You don't need talent for it. The rest of this lecture is those rules, plus the handful of ideas that cover the rest of the family.

One more honest point. The final section of your file is a near-copy of the section above it (`bottom += 1` twice, `matrix[bottom][...]` twice). That usually happens when you're tired or frustrated and pattern-matching on your own code instead of deriving it. It's normal. The fix is structural (§5.3), not willpower.

---

## 1. The map: the matrix/simulation family

Before any code, here's the whole territory. Nearly every grid problem on LeetCode falls into one of these seven rows. **Recognizing the row is most of the work.**

| # | Sub-family | Trigger in the problem statement | Core tool | Classic problems | Tag |
|---|---|---|---|---|---|
| A | **Traversal order** | "return the elements in ___ order": spiral, diagonal, zigzag | Walls (§5.2) or direction table (§5.3); diagonals via `r+c` (§6.3) | 54 Spiral Matrix, 59 Spiral Matrix II, 498 Diagonal Traverse | 🟢 OWN IT |
| B | **Geometric transform** | "rotate", "transpose", "flip", "in place" | Index rewrites (§6.2) | 48 Rotate Image, 867 Transpose Matrix | 🟢 OWN IT |
| C | **In-place update with dependencies** | "simultaneously", "in place", "O(1) extra space", "set the whole row/column" | Encode or marker trick (§7) | 73 Set Matrix Zeroes, 289 Game of Life | 🟢 / 🔵 |
| D | **Sorted matrix search** | "rows are sorted…", "each row's first > previous row's last" | Flatten to 1D (§6.1) or staircase (§6.4) | 74 Search a 2D Matrix, 240 Search a 2D Matrix II | 🟢 OWN IT |
| E | **Grid as a graph** | "islands", "connected", "regions", "spread", "minimum minutes/steps" | DFS/BFS flood fill, multi-source BFS (§8) | 200 Number of Islands, 994 Rotting Oranges, 695 Max Area of Island, 733 Flood Fill | 🟢 OWN IT (most common) |
| F | **Region sums** | "sum of a sub-rectangle", many queries | 2D prefix sums (§6.5) | 304 Range Sum Query 2D | 🔵 CONTRACT |
| G | **Grid DP** | "number of paths", "minimum path sum", "can only move right/down" | Dynamic programming | 62 Unique Paths, 64 Minimum Path Sum | ⚫ separate lecture |

Tags: 🟢 **OWN IT**: be able to write it cold. 🔵 **CONTRACT**: know the idea and the shape; you can look up details. ⚫ **BLACK BOX (for now)**: real, but a different skill (DP) that deserves its own lecture. Skip it here.

**Honest sizing:** row E (grid-as-graph) shows up in interviews more than all the others combined, because it tests BFS/DFS, which interviewers love. Rows A–C are the "matrix" problems on the standard study lists (Spiral, Rotate, Set Zeroes are all in the Blind 75). Row D is short and very learnable. Row F is a nice-to-know. Row G is important, just not here.

"Simulation" means **the problem tells you the rules and you just carry them out faithfully** (walk in a spiral, apply Game of Life rules, let oranges rot minute by minute). The challenge is never inventing the rules. It's carrying them out without bookkeeping bugs. That's why one lecture can cover all of these.

---

## 2. The coordinate system, and the firmware twin

### 2.1 Rows and columns, not x and y

```python
rows = len(matrix)        # how many lists in the outer list
cols = len(matrix[0])     # how long each inner list is
matrix[r][c]              # row first, then column. ALWAYS.
```

- `r` goes **down** (0 is the top row). `c` goes **right**.
- `matrix[r][c]` is **not** `matrix[x][y]`. If you think in x/y, then x = c and y = r, which is backwards from the indexing order. Most people who mix up rows and columns are secretly thinking in x/y. **Use the names `r` and `c` for every grid variable, always.** Don't use `i` and `j`. In your spiral code, `i` meant a column in one loop and a row in the next, which made the copy-paste bugs invisible.

| Move | `(dr, dc)` |
|---|---|
| right → | `(0, +1)` |
| down ↓ | `(+1, 0)` |
| left ← | `(0, -1)` |
| up ↑ | `(-1, 0)` |

### 2.2 Firmware twin: the framebuffer

You've worked with memory-mapped buffers. A 2D Python list is a list of row lists, but conceptually it's a **framebuffer**: a flat block of memory where pixel `(r, c)` lives at address

```
index = r * cols + c          # row-major order, like a display framebuffer
r, c  = divmod(index, cols)   # and back again
```

This isn't just a metaphor. **74. Search a 2D Matrix** is solved by treating the grid as that flat buffer and binary-searching indices `0 … rows*cols-1` (§6.1). Whenever a problem says "if you laid the matrix out in one line…", think framebuffer.

Two more firmware twins come later: the **direction state machine** (§5.3) and the **status-register bit packing** used for in-place updates (§7.3).

---

## 3. The cast of characters

Every simulation has the same four characters. Name them in your head, and in code comments, before you write anything:

| Character | Variable(s) | Job | What it wants |
|---|---|---|---|
| **The Cursor** | `r, c` | The cell you're standing on | To read or write exactly one valid cell per step |
| **The Compass** | `d` (index into `DIRS`) | Which way you're facing | To turn only when the rules say so |
| **The Fence** | `top, bottom, left, right` *or* a `seen` grid | Marks what's still allowed | To shrink only, never grow back |
| **The Bouncer** | `0 <= r < rows and 0 <= c < cols` | Rejects out-of-bounds moves | To be checked **before** every read |

Your spiral attempt had a Cursor (`i`), a Fence (the four walls), and no Compass. Instead it had four copies of hand-written logic, one per direction. §5.3 introduces the Compass and the copies disappear.

---

## 4. Tool #1: one boundary convention

### 4.1 The two conventions

| | **Closed** `[lo, hi]` | **Half-open** `[lo, hi)` |
|---|---|---|
| Meaning | `hi` **is** the last valid index | `hi` is **one past** the last valid index |
| Init for length `n` | `hi = n - 1` | `hi = n` |
| "Still non-empty?" | `lo <= hi` | `lo < hi` |
| Python forward loop | `range(lo, hi + 1)` | `range(lo, hi)` |
| Python backward loop | `range(hi, lo - 1, -1)` | `range(hi - 1, lo - 1, -1)` |
| The last element | `a[hi]` | `a[hi - 1]` |
| Size | `hi - lo + 1` | `hi - lo` |
| Where it's natural | **Walls you index directly** (spiral, two pointers, binary search) | Slicing, `range`, sizes, sliding windows |

Neither one is "right." **Mixing them is wrong.** Each variable's meaning has to be remembered separately, so every loop becomes a fresh puzzle.

> **Rule:** at the top of the function, write one comment: `# walls are CLOSED: each points at a valid row/col`. Then every loop is a lookup in the table above, not a judgment call.

For spiral, use **closed**, because you index the walls directly (`matrix[top][c]`, `matrix[r][right]`). Then `matrix[top]`, `matrix[bottom]`, `[left]` and `[right]` are all valid with no `-1` anywhere.

### 4.2 Python's `range` is half-open, and that's where the confusion comes from

`range(a, b)` gives `a, a+1, …, b-1`. That's half-open. With **closed** walls, every forward loop has to say `range(lo, hi + 1)`. That `+1` isn't a fudge. It's the conversion from closed to half-open, and it's always the same. Backward loops are `range(hi, lo - 1, -1)`: start at `hi`, stop *before* `lo - 1`, so `lo` is included.

Reading test: `range(right, left - 1, -1)` = "from right down to left, both included." If you can read that line aloud correctly, you're fine.

### 4.3 Walls only move inward

| Wall | After you consume it | Never |
|---|---|---|
| `top` | `top += 1` | `top -= 1` |
| `bottom` | `bottom -= 1` | `bottom += 1` ← your bug |
| `left` | `left += 1` | `left -= 1` |
| `right` | `right -= 1` | `right += 1` |

This is the **progress** rule: the unvisited region has to strictly shrink every pass, or the loop never ends (or, like yours, runs off the edge). You can check it in five seconds by looking at the code, without running anything. **Make it a habit: after writing any loop that moves boundaries, scan every `+=` and `-=` and ask "inward?"**

### 4.4 The invariant (the one sentence that writes the code for you)

An **invariant** is a statement that's true at the top of every loop pass. For spiral:

> **Invariant:** the unvisited cells form exactly the rectangle rows `top..bottom` × columns `left..right` (closed), and `answer` holds every visited cell in spiral order.

Now derive the code from it instead of guessing:

- **Init:** before anything is visited, the rectangle is the whole matrix, so `top=0, bottom=rows-1, left=0, right=cols-1`. (Derived, not guessed.)
- **Loop condition:** keep going while the rectangle is non-empty. With closed walls, that's `top <= bottom and left <= right`. **`and`**, because a rectangle with zero rows *or* zero columns is empty.
- **Body:** peel the top row, then the right column, then the bottom row, then the left column. After each peel, move that wall inward so the invariant holds again.
- **Termination:** when the rectangle is empty, every cell is in `answer`. Done.

This four-part habit (invariant, init, progress, termination) is the main idea of the companion lecture 002. You can't skip init by "feel" if you've written the invariant down. The invariant *tells* you the init.

---

## 5. Spiral Matrix, solved properly, two ways

### 5.1 Before coding: by hand on a non-square grid

Always hand-solve a **non-square** case. 3×4:

```
 1  2  3  4
 5  6  7  8
 9 10 11 12
```

Expected: `1 2 3 4 → 8 12 → 11 10 9 → 5 → 6 7`. Notice the last lap is a single row (`6 7`). That's the case that breaks naive solutions.

### 5.2 Way 1: four walls (closed convention)

```python
def spiralOrder(matrix):
    # Walls are CLOSED: each one points at a valid row/col that hasn't been visited.
    top, bottom = 0, len(matrix) - 1
    left, right = 0, len(matrix[0]) - 1
    out = []
    while top <= bottom and left <= right:
        for c in range(left, right + 1):          # top row, left → right
            out.append(matrix[top][c])
        top += 1
        for r in range(top, bottom + 1):          # right column, top → bottom
            out.append(matrix[r][right])
        right -= 1
        if top <= bottom:                         # a row is still left
            for c in range(right, left - 1, -1):  # bottom row, right → left
                out.append(matrix[bottom][c])
            bottom -= 1
        if left <= right:                         # a column is still left
            for r in range(bottom, top - 1, -1):  # left column, bottom → top
                out.append(matrix[r][left])
            left += 1
    return out
```

Compare it with yours line by line. It's **your design**. The only changes are one convention, `and`, inward-only walls, and `matrix[r][left]` for the column walk.

**Why the two `if`s?** The first two sides (top row, right column) move *forward* into fresh territory. If nothing is left, their `range` is simply empty, and empty ranges cost nothing. The last two sides move *backward* over a row or column that might be **the same one you just consumed**. Example: `[[1,2,3]]`. After the top row, `top=1 > bottom=0`. Without the guard, the bottom-row loop would read row 0 again, backwards, and you'd output `1 2 3 2 1` (verified). The guard says "only walk back if there's actually a different row (or column) to walk on."

**Trace table** (3×4), produced by running the code:

| Side | Read | top | bottom | left | right |
|---|---|---|---|---|---|
| top row → | 1,2,3,4 | 1 | 2 | 0 | 3 |
| right col ↓ | 8,12 | 1 | 2 | 0 | 2 |
| bottom row ← | 11,10,9 | 1 | 1 | 0 | 2 |
| left col ↑ | 5 | 1 | 1 | 1 | 2 |
| top row → | 6,7 | 2 | 1 | 1 | 2 |
| right col ↓ | (empty range) | 2 | 1 | 1 | 1 |
| bottom row ← | skipped: `top > bottom` | | | | |
| left col ↑ | (empty range) | 2 | 1 | 2 | 1 |

Check the "walls only move inward" rule down each column: `top` 0→1→2 ✅, `bottom` 2→1 ✅, `left` 0→1→2 ✅, `right` 3→2→1 ✅. Then the loop condition fails and we stop.

### 5.3 Way 2: Cursor + Compass (the direction table)

The four-walls version has four near-identical blocks, and near-identical blocks are where copy-paste drift lives. The simulation version has **one** block:

```python
DIRS = [(0, 1), (1, 0), (0, -1), (-1, 0)]   # right, down, left, up (clockwise)

def spiralOrder(matrix):
    rows, cols = len(matrix), len(matrix[0])
    seen = [[False] * cols for _ in range(rows)]
    r = c = d = 0                              # Cursor at (0,0), Compass facing right
    out = []
    for _ in range(rows * cols):               # exactly one step per cell: no while-loop guessing
        out.append(matrix[r][c])
        seen[r][c] = True
        dr, dc = DIRS[d]
        nr, nc = r + dr, c + dc
        if not (0 <= nr < rows and 0 <= nc < cols) or seen[nr][nc]:   # Bouncer says no
            d = (d + 1) % 4                    # turn clockwise
            dr, dc = DIRS[d]
            nr, nc = r + dr, c + dc
        r, c = nr, nc
    return out
```

The rules, in English: *walk forward; if the next cell is off the grid or already visited, turn right.* That is literally how you'd describe a spiral to a child, and the code is that sentence.

**Firmware twin: a state machine.** `d` is a 2-bit state register (0=RIGHT, 1=DOWN, 2=LEFT, 3=UP). The transition is `d = (d + 1) % 4` when the guard condition fires. `DIRS[d]` is a lookup table mapping state to output. You've written this exact structure in firmware: a state enum, a transition on an event, and a table instead of a `switch` full of copy-pasted cases.

**Why the loop is `for _ in range(rows * cols)` and not a `while`:** you know exactly how many cells there are. A counted loop *can't* run forever and *can't* stop early, so a whole class of termination bugs is impossible. **Whenever you know the step count in advance, use a counted loop.**

| | Four walls | Cursor + Compass |
|---|---|---|
| Extra space | O(1) | O(rows·cols) for `seen` (can be avoided if you're allowed to overwrite visited cells with a sentinel) |
| Bug surface | Four loops, two guards, four wall updates | One loop, one turn rule |
| Generalizes to | Spiral only | Spiral II (59), Spiral III (885), robot/snake simulations, anything with "move and turn" |
| Interview pick | Expected, show you can do it | Easier to get right under pressure |

**Recommendation:** learn both. Reach for Cursor + Compass first when you're nervous, because it has fewer places to be wrong. Know four walls because interviewers often ask for O(1) space.

### 5.4 The sibling: 59. Spiral Matrix II (generate it)

Same Cursor + Compass. "Visited" just becomes "already non-zero":

```python
def generateMatrix(n):
    grid = [[0] * n for _ in range(n)]       # NOT [[0]*n]*n: that's n references to ONE row
    r = c = d = 0
    for k in range(1, n * n + 1):
        grid[r][c] = k
        dr, dc = DIRS[d]
        nr, nc = r + dr, c + dc
        if not (0 <= nr < n and 0 <= nc < n) or grid[nr][nc] != 0:
            d = (d + 1) % 4
            dr, dc = DIRS[d]
            nr, nc = r + dr, c + dc
        r, c = nr, nc
    return grid
```

Notice the `[[0]*n]*n` trap in the comment. It creates *one* row list referenced `n` times, so writing one cell writes the whole column. It's the most common Python grid bug. Always build grids with a comprehension.

---

## 6. Tool #2: index math and transforms

A lot of "clever" matrix solutions are just one line of index algebra. Learn the vocabulary once.

### 6.1 Flatten / unflatten (the framebuffer)

```python
i = r * cols + c
r, c = divmod(i, cols)
```

**74. Search a 2D Matrix:** each row is sorted, and each row starts after the previous row ends. So the framebuffer is one sorted array of length `rows*cols`. Binary-search the *index*:

```python
def searchMatrix(matrix, target):
    rows, cols = len(matrix), len(matrix[0])
    lo, hi = 0, rows * cols - 1        # CLOSED convention, same as spiral
    while lo <= hi:
        mid = (lo + hi) // 2
        r, c = divmod(mid, cols)
        val = matrix[r][c]
        if val == target:
            return True
        if val < target:
            lo = mid + 1               # walls move inward
        else:
            hi = mid - 1
    return False
```

Notice it's the same convention table as §4.1, with the same `lo <= hi` and the same "walls only move inward." **Binary search and spiral are the same bookkeeping skill.**

### 6.2 Geometric transforms

| Transform | Cell `(r, c)` goes to | Code idea |
|---|---|---|
| Transpose | `(c, r)` | swap across the main diagonal |
| Flip horizontally (mirror left↔right) | `(r, cols-1-c)` | `row.reverse()` for each row |
| Flip vertically (top↔bottom) | `(rows-1-r, c)` | `matrix.reverse()` |
| **Rotate 90° clockwise** | `(c, n-1-r)` | **transpose, then flip horizontally** |
| Rotate 90° counter-clockwise | `(n-1-c, r)` | transpose, then flip vertically |
| Rotate 180° | `(n-1-r, n-1-c)` | flip both |

**48. Rotate Image** (n×n, in place):

```python
def rotate(matrix):
    n = len(matrix)
    for r in range(n):
        for c in range(r + 1, n):      # c > r: only the upper triangle, or you'd swap everything twice
            matrix[r][c], matrix[c][r] = matrix[c][r], matrix[r][c]
    for row in matrix:
        row.reverse()
```

The `c in range(r + 1, n)` detail matters. If you looped over *all* `(r, c)`, every pair would be swapped twice and you'd end up with the original matrix. This is the in-place hazard from §7 in miniature.

How to *derive* "transpose then flip" instead of memorizing it: write a 3×3 with letters, rotate it by hand, and look at where the first row went. `a b c` becomes the last column, read top to bottom. A transpose turns row 0 into column 0. A horizontal flip then moves column 0 to column 2. Two steps you already know replace one you'd have to memorize.

### 6.3 Diagonals

- Cells on the same **diagonal** (↘) share `r - c`.
- Cells on the same **anti-diagonal** (↙) share `r + c`.

**498. Diagonal Traverse:** walk anti-diagonals `s = 0 … rows+cols-2`, alternating direction:

```python
def findDiagonalOrder(mat):
    rows, cols = len(mat), len(mat[0])
    out = []
    for s in range(rows + cols - 1):
        # rows r on anti-diagonal s, with c = s - r kept in [0, cols-1]
        diag = [mat[r][s - r] for r in range(max(0, s - cols + 1), min(rows - 1, s) + 1)]
        out.extend(diag if s % 2 else reversed(diag))
    return out
```

The `range(max(...), min(...) + 1)` is a closed interval clipped by the Bouncer: `r` must be valid, and `c = s - r` must be valid. Work out both bounds on paper once and you'll own this.

Related index trick: in a 9×9 Sudoku, the 3×3 box of `(r, c)` is `(r // 3) * 3 + c // 3`. That's the framebuffer formula again, applied to the coarse 3×3 grid of boxes.

### 6.4 The staircase (240. Search a 2D Matrix II)

Here rows are sorted left→right and columns top→bottom, but rows don't chain into each other. So it isn't one sorted array. Start in the **top-right** corner:

- If the value is too big, the whole column below is even bigger, so drop the column (`c -= 1`).
- If the value is too small, the whole row to the left is even smaller, so drop the row (`r += 1`).

```python
def searchMatrix(matrix, target):
    r, c = 0, len(matrix[0]) - 1
    while r < len(matrix) and c >= 0:
        val = matrix[r][c]
        if val == target:
            return True
        if val > target:
            c -= 1
        else:
            r += 1
    return False
```

Each step eliminates a whole row or column, so it's O(rows + cols). It's the "walls move inward" idea one more time: the unexplored region is always the rectangle below-left of the cursor, and it shrinks every step.

### 6.5 2D prefix sums (🔵 CONTRACT)

For "sum of any sub-rectangle, many times," precompute `P[r+1][c+1]` = sum of everything above-left of and including `(r, c)`. Then any rectangle is four lookups (inclusion–exclusion):

```python
class NumMatrix:
    def __init__(self, matrix):
        rows, cols = len(matrix), len(matrix[0])
        self.P = [[0] * (cols + 1) for _ in range(rows + 1)]   # padded by one: row 0 / col 0 are zeros
        for r in range(rows):
            for c in range(cols):
                self.P[r+1][c+1] = matrix[r][c] + self.P[r][c+1] + self.P[r+1][c] - self.P[r][c]

    def sumRegion(self, r1, c1, r2, c2):
        P = self.P
        return P[r2+1][c2+1] - P[r1][c2+1] - P[r2+1][c1] + P[r1][c1]
```

The `+1` padding is a **half-open** convention used deliberately: `P` is one bigger than the grid, so there's never an `r-1 < 0` special case. That's the point of §4. Convention is a tool you choose on purpose, not an accident.

---

## 7. Tool #3: the in-place hazard

### 7.1 The problem

"Update the grid **in place**" plus "each new value depends on **old** neighbor values" is a trap: once you've written a cell, its neighbors read the *new* value when they needed the old one.

**Firmware twin: double buffering.** A display driver never draws into the buffer that's currently being scanned out. It draws into a back buffer and swaps. Same hazard, same family of fixes.

### 7.2 The three fixes, in order of preference

| Fix | How | Cost | Use when |
|---|---|---|---|
| **1. Copy (double buffer)** | Read from a copy, write to the original | O(rows·cols) extra space | Always acceptable first answer. Say it out loud, then optimize. |
| **2. Encode** | Store old and new state in the same cell (extra bits or sentinel values) | O(1) extra | Values are small (booleans, small ints) |
| **3. Order the writes / use markers** | Record decisions somewhere you've already finished reading, or write in an order that never clobbers unread data | O(1) extra | When the structure allows it (Set Matrix Zeroes, the Rotate Image triangle) |

**Interview move:** give fix 1 first ("the straightforward version uses a copy, which is O(mn) space"), then offer the O(1) version. Interviewers reward hearing both, and fix 1 is your safety net.

### 7.3 289. Game of Life (encode). Firmware twin: bit packing.

Each cell is 0 or 1, so only bit 0 is in use. Store the **next** state in **bit 1** (like packing two flags into one status register), then shift everything right at the end:

```python
def gameOfLife(board):
    rows, cols = len(board), len(board[0])
    for r in range(rows):
        for c in range(cols):
            live = 0
            for dr in (-1, 0, 1):                 # 8 neighbors
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < rows and 0 <= nc < cols:
                        live += board[nr][nc] & 1     # bit 0 = OLD state, never touched in pass 1
            if board[r][c] & 1 and live in (2, 3):
                board[r][c] |= 2                       # bit 1 = NEW state: stays alive
            elif not board[r][c] & 1 and live == 3:
                board[r][c] |= 2                       # bit 1 = NEW state: born
    for r in range(rows):
        for c in range(cols):
            board[r][c] >>= 1                          # promote new state to bit 0
```

The invariant for pass 1: **bit 0 always holds the old generation.** Pass 1 only ever writes bit 1, so every neighbor read (`& 1`) is clean. The shift at the end is the "buffer swap."

### 7.4 73. Set Matrix Zeroes (markers)

First the honest O(m+n) version, which is always a fine first answer:

```python
def setZeroes(matrix):
    rows, cols = len(matrix), len(matrix[0])
    zero_rows, zero_cols = set(), set()
    for r in range(rows):
        for c in range(cols):
            if matrix[r][c] == 0:
                zero_rows.add(r); zero_cols.add(c)
    for r in range(rows):
        for c in range(cols):
            if r in zero_rows or c in zero_cols:
                matrix[r][c] = 0
```

The O(1) version uses **row 0 and column 0 as the two sets.** The catch is that row 0 and column 0 are *also data*, so you have to remember whether *they* originally had a zero before you start writing markers into them:

```python
def setZeroes(matrix):
    rows, cols = len(matrix), len(matrix[0])
    first_row_zero = any(matrix[0][c] == 0 for c in range(cols))   # save before we overwrite
    first_col_zero = any(matrix[r][0] == 0 for r in range(rows))
    for r in range(1, rows):                    # 1. record markers in row 0 / col 0
        for c in range(1, cols):
            if matrix[r][c] == 0:
                matrix[r][0] = 0
                matrix[0][c] = 0
    for r in range(1, rows):                    # 2. apply markers to the interior
        for c in range(1, cols):
            if matrix[r][0] == 0 or matrix[0][c] == 0:
                matrix[r][c] = 0
    if first_row_zero:                          # 3. finally the marker row/col themselves
        for c in range(cols): matrix[0][c] = 0
    if first_col_zero:
        for r in range(rows): matrix[r][0] = 0
```

The order (save the flags → mark → apply interior → apply edges) is fix #3, "order the writes." Step 3 has to come last, because row 0 and column 0 are still being *read* as markers in step 2.

---

## 8. Tool #4: the grid is a graph

When the problem talks about **connected regions** or **things spreading**, stop thinking "matrix" and think "graph": each cell is a node, and its 4 (or 8) neighbors are its edges. You don't build a graph. The grid already *is* the adjacency structure, and `DIRS` lists the edges.

### 8.1 Flood fill (200. Number of Islands)

> For each unvisited land cell, start a fill that marks the whole island. Count how many fills you started.

```python
def numIslands(grid):
    rows, cols = len(grid), len(grid[0])
    count = 0
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] != "1":
                continue
            count += 1                       # found a new island
            grid[r][c] = "0"                 # mark visited WHEN PUSHED, not when popped
            stack = [(r, c)]
            while stack:
                cr, cc = stack.pop()
                for dr, dc in DIRS:
                    nr, nc = cr + dr, cc + dc
                    if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] == "1":
                        grid[nr][nc] = "0"
                        stack.append((nr, nc))
    return count
```

Three details that matter:

1. **Bouncer before read:** `0 <= nr < rows and 0 <= nc < cols` comes *before* `grid[nr][nc]`. Python's `and` short-circuits, so the read never happens out of bounds. (Note: in Python, a negative index like `grid[-1]` does **not** raise an error. It silently wraps to the last row. The Bouncer is your only protection against that.)
2. **Mark when you push, not when you pop.** Otherwise the same cell gets pushed many times by different neighbors. Still correct, but slower, and in BFS it gives wrong distances.
3. **Iterative stack, not recursion,** for big grids. Python's default recursion limit is about 1000, and a 300×300 island blows it. Recursive DFS is fine in interviews if you mention this.

Overwriting `"1"` with `"0"` is the in-place marker trick from §7. If you're not allowed to modify the input, use a `seen` set.

### 8.2 Multi-source BFS with levels (994. Rotting Oranges)

"How many **minutes** until…" / "**minimum steps**" means BFS, processed **one level at a time**. Every rotten orange starts in the queue together (multi-source), and each level of the BFS is one minute:

```python
from collections import deque

def orangesRotting(grid):
    rows, cols = len(grid), len(grid[0])
    queue, fresh = deque(), 0
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] == 2:
                queue.append((r, c))
            elif grid[r][c] == 1:
                fresh += 1
    minutes = 0
    while queue and fresh > 0:
        for _ in range(len(queue)):          # exactly the cells that rotted LAST minute
            r, c = queue.popleft()
            for dr, dc in DIRS:
                nr, nc = r + dr, c + dc
                if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] == 1:
                    grid[nr][nc] = 2         # mark when pushed
                    fresh -= 1
                    queue.append((nr, nc))
        minutes += 1
    return minutes if fresh == 0 else -1
```

The `for _ in range(len(queue))` line is the **level loop**. `len(queue)` is captured once, at the start of the minute, so cells added during this minute wait until the next one. It's the same idea as "simultaneously" in Game of Life: the new generation doesn't act until the old one is finished.

Why `fresh > 0` is in the `while` condition: without it, you'd count one extra minute for the last wave of oranges that has nobody left to infect.

**DFS or BFS?** Counting regions or measuring their size: either works, so use DFS (simpler). Distance, minutes, or "fewest steps": **BFS only**, because BFS reaches cells in order of distance and DFS doesn't.

---

## 9. The grid checklist (use it on every problem)

Before writing code, answer these out loud or in a comment block. It takes about two minutes and prevents most of the bugs in this lecture.

```
GRID CHECKLIST
1. SHAPE     rows = len(g), cols = len(g[0]). Can it be 1×1? 1×n? n×1? (Constraints say.)
2. FAMILY    Which row of the §1 map? (order / transform / in-place / sorted / graph / sums / DP)
3. ORDER     In what order do I visit cells? (row-major / walls / Cursor+Compass / BFS levels)
4. HAZARD    Do I write into the grid I'm reading? → copy, encode, or order the writes.
5. NEIGHBORS 4-dir or 8-dir? → write DIRS once at the top.
6. CONVENTION Closed or half-open? Write it in a comment. Walls only move inward.
7. INVARIANT  One sentence: what's true at the top of every pass? Derive init from it.
8. TEST GRIDS 1×1, 1×n, n×1, 3×4. Hand-trace one non-square grid in a table BEFORE running.
```

Line 8 alone would have caught your bugs. Your code was only ever run (mentally) on a square grid. On a 1×3, the very first iteration of the bottom-row loop already does something visibly wrong.

---

## 10. Lab: predict, then run

About 30 minutes. Do it in `lectures/leetcode/examples.py` or a scratch file.

**Part A: predict your own bugs.** Keep your original `spiralOrder` and don't change it yet. For each input, write down what you **predict** it does *before* running it:

| Input | Your prediction | Actual |
|---|---|---|
| `[[1]]` | | |
| `[[1,2,3]]` | | |
| `[[1],[2],[3]]` | | |
| `[[1,2],[3,4]]` | | |

(Predicting first matters. A prediction that turns out wrong is the strongest learning signal you can get. Just running the code and reading the output teaches you much less.)

**Part B: one-convention fix.** Edit *your* code (not mine) with one rule only: make all four walls closed. Then fix every loop by **looking it up in the §4.1 table**, not by reasoning about ±1. Then apply the "walls only move inward" scan. Count how many edits it took.

**Part C: blank page.** Close everything. Write the Cursor + Compass version from memory. Test on the four inputs plus the 3×4.

**Part D: transfer.** Without looking anything up, do 59. Spiral Matrix II with Cursor + Compass. If Part C stuck, this takes under 10 minutes.

---

## 11. Practice ladder

Do these in order. Each one reuses a tool from the one before it.

| # | Problem | Tool it trains | Target time |
|---|---|---|---|
| 1 | 54 Spiral Matrix (redo, blank page) | Convention + walls (§4–5) | 20 min |
| 2 | 59 Spiral Matrix II | Cursor + Compass (§5.3) | 15 min |
| 3 | 48 Rotate Image | Transforms (§6.2) | 15 min |
| 4 | 74 Search a 2D Matrix | Framebuffer + binary search (§6.1) | 15 min |
| 5 | 73 Set Matrix Zeroes (both versions) | In-place markers (§7.4) | 25 min |
| 6 | 733 Flood Fill → 200 Number of Islands | Flood fill (§8.1) | 15 + 20 min |
| 7 | 994 Rotting Oranges | Multi-source BFS levels (§8.2) | 25 min |
| 8 | 289 Game of Life | Encode (§7.3) | 25 min |
| 9 | 240 Search a 2D Matrix II | Staircase (§6.4) | 15 min |
| 10 | 498 Diagonal Traverse | `r+c` diagonals (§6.3) | 25 min |
| stretch | 695 Max Area of Island, 130 Surrounded Regions, 542 01 Matrix, 36 Valid Sudoku | variants | — |

**The redo rule (the most important line in this section):** any problem you fail gets redone **from a blank page** 3 days later, and again about 10 days later. A problem isn't "done" until you've solved it cold. Reading a solution gives you *recognition* ("yeah, that makes sense"), which feels like learning but doesn't hold up in an interview. Spiral Matrix is redo #1, and it's due around **2026-10-06**.

**What to log for each problem:** not just pass/fail, but **which bug category** happened (convention / progress / copy-paste / bouncer / in-place hazard / wrong family). After ten problems you'll see your personal top two, and that's where to focus.

---

## Misconceptions and common mistakes

| You might think | Reality | Why it matters |
|---|---|---|
| "I'm bad at these problems." | You produced the standard algorithm unaided. The failures were bookkeeping. | Bookkeeping can be fixed with rules. Talent isn't required. |
| "Off-by-one errors are random; I just need to be more careful." | They come from **mixing conventions**. One convention plus the lookup table removes most of them. | "Be more careful" isn't a technique. A table is. |
| "I'll fix the indices as I go with -1s." | Ad-hoc ±1 corrections each need a separate judgment, and under pressure some will be wrong. | Your spiral had three corrections and all three were wrong. |
| "`matrix[x][y]`" | It's `matrix[r][c]`: row (vertical) first. | Swapping these breaks every non-square grid. |
| "Square examples are enough." | Non-square grids (1×n, n×1, 3×4) expose most bugs. | The given examples are often the friendliest cases. |
| "`grid[-1]` will throw if I go out of bounds." | Python wraps negative indices to the end. No error, just wrong data. | Always check bounds explicitly first. |
| "`[[0]*n]*n` makes an n×n grid." | It makes one row referenced n times. | Writing one cell changes a whole column. |
| "DFS and BFS are interchangeable." | Only for connectivity. For distance/minutes, use BFS. | Rotting Oranges with DFS gives wrong answers. |
| "Transposing means swapping every `(r,c)` with `(c,r)`." | Only the upper triangle (`c > r`), or every pair swaps twice. | You'd end up with the original matrix. |
| "In-place means I have to be clever right away." | State the copy version first, then optimize. | It's a safe answer, and interviewers like seeing the progression. |

---

## Interview relevance

- **Grid-as-graph (row E)** is the most common grid category in real interviews. If you only have time for one row, do Number of Islands and Rotting Oranges until you can write them cold.
- **Spiral Matrix, Rotate Image, and Set Matrix Zeroes** are on the Blind 75 matrix list. They come up because they test exactly what this lecture covers: careful indexing under pressure. Interviewers know the algorithm is easy. They're watching your bookkeeping and testing.
- **What interviewers watch for:** do you name your convention, check edge shapes (1×n), test on a non-square example *before* saying "done," and state the copy solution before the O(1) one? Saying the §9 checklist out loud is exactly the narration they want to hear.
- **Talking point you can use honestly:** "I treat grids as row-major buffers. I come from firmware, so `r * cols + c` is how I think about framebuffers." That's a real, memorable connection, and it's true.

---

## Self-check questions

1. In your original code, which single line was the root cause, and why did it lead to three *different* wrong corrections?
<details><summary>Answer</summary>

`right = len(matrix[0])`. It made `right` half-open while `top`, `bottom`, and `left` were closed. Each loop then needed a hand-made ±1 adjustment that depended on which variable it used. The adjustments ended up applied to the wrong variable (`bottom-1`), missing (`range(top, bottom)` skipped the last row), or pointed the wrong way.
</details>

2. Closed convention, walls `top=1, bottom=1`. Is there still a row left?
<details><summary>Answer</summary>

Yes. Closed means `bottom` points at a valid unvisited row, and `top <= bottom` (1 ≤ 1), so exactly one row (row 1) remains.
</details>

3. Write the Python loop that walks a closed range from `right` down to `left`, inclusive.
<details><summary>Answer</summary>

`for c in range(right, left - 1, -1):`. It stops *before* `left - 1`, so `left` is included.
</details>

4. Why does the four-walls spiral need `if top <= bottom` before the bottom-row pass, but no guard before the right-column pass?
<details><summary>Answer</summary>

The right-column pass moves forward into new rows. If none remain, `range(top, bottom + 1)` is empty and nothing happens. The bottom-row pass walks *back* along `bottom`. If `top > bottom`, that row was already consumed as the top row, so without the guard you'd re-read part of it (e.g. `[[1,2,3]]` → `1 2 3 2 1`).
</details>

5. Your code has `bottom += 1` after consuming the bottom row. What rule catches this without running anything?
<details><summary>Answer</summary>

"Walls only move inward." `bottom` may only decrease. Any `+=` on `bottom` or `right`, or `-=` on `top` or `left`, is a bug.
</details>

6. In a 4×5 matrix, what `(r, c)` is flat index 13? What flat index is `(2, 3)`?
<details><summary>Answer</summary>

`divmod(13, 5) = (2, 3)`. And `2*5 + 3 = 13`. (They're the same cell, which is a nice check.)
</details>

7. Rotate 90° clockwise = which two simpler transforms, in which order?
<details><summary>Answer</summary>

Transpose, then reverse each row (flip horizontally). Check: the first row `a b c` becomes the first column after a transpose, then the last column after the flip. That's where it belongs.
</details>

8. Which cells are on the same anti-diagonal (↙) as `(1, 3)`?
<details><summary>Answer</summary>

All `(r, c)` with `r + c = 4`: `(0,4), (1,3), (2,2), (3,1), (4,0)` (whichever are in bounds).
</details>

9. In Game of Life, why is it safe to read `board[nr][nc] & 1` after some neighbors have already been processed?
<details><summary>Answer</summary>

Pass 1 only ever sets bit 1 (`|= 2`). Bit 0, the old state, is never modified until the final shift. So `& 1` always reads the old generation.
</details>

10. Set Matrix Zeroes, O(1) version: why do you need `first_row_zero` and `first_col_zero` as separate variables?
<details><summary>Answer</summary>

Row 0 and column 0 are used as marker storage, so after step 1 you can't tell whether a zero there was original or a marker. You have to record their original state first, and zero them out *last*, after step 2 has finished reading them as markers.
</details>

11. "Minimum number of minutes until all oranges rot": DFS or BFS, and why?
<details><summary>Answer</summary>

BFS with a level loop. BFS visits cells in order of distance from the sources, so level k = minute k. DFS goes deep along one path and doesn't measure shortest distance.
</details>

12. In Number of Islands, why mark a cell visited when you **push** it rather than when you pop it?
<details><summary>Answer</summary>

Otherwise several neighbors can each push the same cell before it's popped. That means duplicate work, and in BFS it can record a non-shortest distance.
</details>

13. Name the four test shapes you should hand-trace for any grid problem.
<details><summary>Answer</summary>

1×1, 1×n, n×1, and a non-square grid like 3×4. (Plus the empty grid if the constraints allow it. For Spiral Matrix they don't: `m, n ≥ 1`.)
</details>

14. Why prefer `for _ in range(rows * cols)` over `while` in the Cursor + Compass spiral?
<details><summary>Answer</summary>

The number of steps is known exactly. A counted loop can't run forever or stop early, so the termination question is settled before you write the body.
</details>

---

## Sources

- LeetCode problem statements (problem numbers and titles as used above): 54 Spiral Matrix, 59 Spiral Matrix II, 48 Rotate Image, 73 Set Matrix Zeroes, 289 Game of Life, 74 Search a 2D Matrix, 240 Search a 2D Matrix II, 200 Number of Islands, 994 Rotting Oranges, 498 Diagonal Traverse, 304 Range Sum Query 2D - Immutable, 733 Flood Fill, 695 Max Area of Island, 62 Unique Paths. https://leetcode.com/problemset/ (numbers from my own knowledge of these long-standing problems, not re-fetched; checked 2026-10-03).
- Blind 75 list (Spiral Matrix, Rotate Image, Set Matrix Zeroes in its matrix section): widely mirrored, e.g. https://neetcode.io/practice (from my own knowledge, not re-fetched; 2026-10-03).
- Python `range`, negative indexing, and the default recursion limit (`sys.getrecursionlimit()` = 1000): https://docs.python.org/3/library/stdtypes.html#range and https://docs.python.org/3/library/sys.html#sys.getrecursionlimit
- Code verification: every solution was run against brute-force references on 3,000 random grids (1×1 to 7×7) on 2026-10-03. Your original attempt was run on the five inputs in §0.2.
- Companion lecture: `lectures/carreer_path/002-the-leetcode-diagnosis-and-the-solving-protocol.md` (the general Solve Protocol, invariants, trace tables, and the redo rule).

**Next lecture in this folder (when you want it):** grid-as-graph in depth (BFS/DFS on grids, including 0-1 matrix, surrounded regions, shortest path in a binary matrix), or grid DP. Ask for whichever you hit next.
