# Lecture 009: Graphs: Traversal, Shortest Steps, Cycles and Ordering

> **For:** Timothy · **Date:** 2026-10-11
> **Prerequisites:** lecture 007 (trees: DFS, and BFS with a level loop). Lecture 008 (valid sets for neighbours). Lecture 001 §8 introduced grid flood fill and Rotting Oranges, and this lecture builds the general version.
> **Why this topic, why now:** it's the first lecture of Group 2 in the roadmap. Graph problems are among the most common interview questions, and your two graph attempts (Sep 12) failed on **bookkeeping**, not on the idea:
> - **Rotting Oranges:** you computed `r + dr` for the bounds check, then checked and appended `(r, c)`, the current cell, instead of the neighbour. Nothing ever rotted. (Traced in lecture 003 §6.4.)
> - **Course Schedule:** your algorithm was **correct** (edges `pre → course`, a `visited` set plus a `path` set), but the function had no final `return True`, so it returned `None`. Gemini then talked you into believing the idea was wrong.
>
> So the goal here is less about new ideas and more about **one reliable template per pattern**, with every name and every valid set written down.
> **Format notes:** full problems (paraphrased) with examples and constraints; derivations, not conventions; no firmware analogies.
> **Verification:** every solution was tested against an independent brute force (union-find for components, step-by-step simulation for Rotting Oranges, relaxation for shortest paths, all permutations for course ordering, structural comparison for Clone Graph) on 2,000 random inputs. Traces were produced by running the code.

---

## Core ideas (the answer key)

1. **A graph is nodes plus edges.** A tree is a graph with no cycles and one path between any two nodes. A grid is a graph whose edges are "up/down/left/right". Most graph problems are trees **without** those guarantees, which is why you need a `seen` set.
2. **Every traversal has the same three parts:** a **frontier** (what to visit next: a stack for DFS, a queue for BFS), a **seen** set (what's already been discovered), and a **neighbours** rule.
3. **Mark a node as seen when you add it to the frontier, not when you take it out.** Otherwise the same node gets added many times, and in BFS the distances go wrong.
4. **Name the neighbour (`nxt`, or `nr, nc`) and test its valid set before using it.** That's exactly the line your Rotting Oranges was missing.
5. **Counting components:** loop over every node; each unseen node starts a new traversal, and counts as one more component.
6. **BFS gives shortest paths in unweighted graphs**, because it visits nodes in order of distance. Use the level loop (`for _ in range(len(queue))`) when the answer is a number of steps or minutes.
7. **Build the adjacency list from the edge list first** (`graph[a].append(b)`). Decide the edge **direction** from the problem's wording, and write that sentence down.
8. **Cycle detection in a directed graph needs three states:** unvisited, on the current path, done. Reaching a node that's **on the current path** means a cycle. (Your `visited` + `path` sets *are* these three states.)
9. **Topological order (Kahn's algorithm):** repeatedly take a node with no remaining prerequisites (indegree 0). If you can't take all `n`, there's a cycle.
10. **Copying a graph needs a map from old node to new node.** That map doubles as the `seen` set.

---

## Table of Contents

- [0. The map: what kind of graph question is it?](#0-the-map-what-kind-of-graph-question-is-it)
- [1. Representing a graph](#1-representing-a-graph)
- [2. The traversal template (and why "mark when pushed")](#2-the-traversal-template-and-why-mark-when-pushed)
- [3. Reachability and components (1971, 547, 200)](#3-reachability-and-components-1971-547-200)
- [4. Shortest steps with BFS (994, 1091)](#4-shortest-steps-with-bfs-994-1091)
- [5. Directed graphs: cycles (207), and your Course Schedule](#5-directed-graphs-cycles-207-and-your-course-schedule)
- [6. Topological order: Kahn's algorithm (210)](#6-topological-order-kahns-algorithm-210)
- [7. Copying a graph (133)](#7-copying-a-graph-133)
- [8. Complexity](#8-complexity)
- [9. Tracing graph code](#9-tracing-graph-code)
- [10. Recognizing graph problems](#10-recognizing-graph-problems)
- [11. Practice ladder](#11-practice-ladder)
- [Common mistakes](#common-mistakes)
- [Interview relevance](#interview-relevance)
- [Self-check questions](#self-check-questions)
- [Sources](#sources)

---

## 0. The map: what kind of graph question is it?

| The question | Pattern | Frontier | Problems |
|---|---|---|---|
| "Can I get from A to B?" / "Is it connected?" | Reachability | stack (DFS) or queue (BFS), either works | 1971 Find if Path Exists |
| "How many groups / islands / provinces?" | Count components | DFS from every unseen node | 547 Number of Provinces, 200 Number of Islands |
| "Fewest steps / minutes / moves?" (all moves cost the same) | **BFS** with levels | queue | 994 Rotting Oranges, 1091 Shortest Path in Binary Matrix |
| "Is there a cycle?" / "Can all tasks be finished?" (directed) | Cycle detection with 3 states | recursion | 207 Course Schedule |
| "In what order can tasks be done?" | Topological sort | queue of indegree-0 nodes | 210 Course Schedule II |
| "Copy this graph" | Traversal + old→new map | stack | 133 Clone Graph |

**DFS or BFS?** For reachability and counting components, either works: pick the one you write more reliably (DFS with an explicit stack is shortest). For **shortest number of steps**, only BFS is correct (§4). For **cycles in directed graphs**, use DFS (§5) or Kahn's algorithm (§6).

---

## 1. Representing a graph

### 1.1 Three forms you'll be given

| Given as | Example | Neighbours of `x` |
|---|---|---|
| **Edge list** | `edges = [[0,1],[1,2]]` | build an adjacency list first (below) |
| **Adjacency matrix** | `isConnected[i][j] == 1` | all `j` with `matrix[x][j] == 1`, which takes O(n) per node |
| **Implicit** (grid) | `grid[r][c]` | the 4 (or 8) cells around `(r, c)` that pass the valid-set test |

### 1.2 Building an adjacency list from an edge list

```python
graph = [[] for _ in range(n)]       # graph[x] = list of x's neighbours; nodes are 0..n-1
for a, b in edges:
    graph[a].append(b)
    graph[b].append(a)               # ONLY for undirected graphs
```

Two decisions to write down **before** this loop:

1. **Directed or undirected?** "Bidirectional", "friends", "roads both ways" → undirected (add both directions). "Prerequisite", "depends on", "one-way" → directed (add one).
2. **For directed edges, which way?** Write the sentence. For Course Schedule, `[a, b]` means "to take `a` you must first take `b`." If the edge means "`b` must come before `a`," the edge goes `b → a`: `graph[b].append(a)`. You reasoned exactly this on Sep 12 ("I can indicate this by representing a connection from 1 to 0"), correctly.

**Why use `[[] for _ in range(n)]` and not `[[]] * n`?** The second creates **one** list referenced n times, so every node would share one neighbour list. It's the same trap as `[[0]*n]*m` for grids (lecture 001 §5.4).

If node labels aren't `0 … n-1` (strings, large numbers), use `defaultdict(list)` instead.

---

## 2. The traversal template (and why "mark when pushed")

### 2.1 The template

```python
seen = {start}              # discovered nodes
frontier = [start]          # to visit next: a list used as a stack (DFS) or a deque (BFS)
while frontier:
    node = frontier.pop()   # BFS: frontier.popleft() with a deque
    # ... process node ...
    for nxt in neighbours(node):
        if nxt not in seen:         # (for grids: also test the valid set FIRST)
            seen.add(nxt)           # mark when PUSHED
            frontier.append(nxt)
```

Three parts, each with one job:

| Part | Holds | Invariant |
|---|---|---|
| `seen` | every node ever discovered | each node is added to `frontier` **at most once** |
| `frontier` | discovered but not yet processed | `frontier ⊆ seen` |
| neighbour rule | edges out of `node` | for grids, only cells in the valid set (§2.3) |

### 2.2 Why mark when pushed, not when popped

If you mark when popping, a node can be pushed once by **each** neighbour before it's ever popped. On a grid of all land, interior cells get pushed up to 4 times. The answer is still right for DFS (just slower), but **BFS distances can break**: a copy of a cell pushed later, from a farther neighbour, carries a larger distance.

Marking on push gives a simple guarantee: **every node enters the frontier exactly once.** That's also what makes the complexity O(V + E) (§8).

### 2.3 Grid neighbours: name them, then test the valid set

The neighbour rule for grids, written with the boundary method from Oct 5:

```python
DIRS = ((1, 0), (-1, 0), (0, 1), (0, -1))
for dr, dc in DIRS:
    nr, nc = r + dr, c + dc                          # 1. NAME the neighbour
    if 0 <= nr < rows and 0 <= nc < cols:            # 2. its valid set (array indices)
        if grid[nr][nc] == "1" and (nr, nc) not in seen:   # 3. use ONLY nr, nc from here on
            ...
```

Your Sep 12 Rotting Oranges did step 2 with `r + dr` written inline, then used `grid[r][c]` and `(r, c)` in step 3. Once `nr, nc` exist as names, using `r, c` by accident becomes much easier to spot: **after the naming line, `r` and `c` should not appear again inside the loop.**

The bounds test comes **first** so that `grid[nr][nc]` is never read out of range. Python's `and` stops at the first False. (A negative `nr` wouldn't even raise an error: `grid[-1]` silently reads the last row. Lecture 008 §8.)

---

## 3. Reachability and components (1971, 547, 200)

### 3.1 Find if Path Exists in Graph (1971)

**Problem (paraphrased).** There are `n` nodes labelled `0 … n-1` and a list of undirected edges `edges[i] = [u, v]`. Return `True` if there is a path from `source` to `destination`.
Examples: `n = 3, edges = [[0,1],[1,2],[2,0]], source = 0, destination = 2` → `True`. `n = 6, edges = [[0,1],[0,2],[3,5],[5,4],[4,3]], source = 0, destination = 5` → `False`.
Constraints: `1 <= n <= 2·10^5`; up to `2·10^5` edges; no duplicate edges or self-loops.

```python
def validPath(n, edges, source, destination):
    graph = [[] for _ in range(n)]
    for a, b in edges:
        graph[a].append(b)
        graph[b].append(a)                 # undirected
    seen = {source}
    stack = [source]
    while stack:
        node = stack.pop()
        if node == destination:
            return True
        for nxt in graph[node]:
            if nxt not in seen:
                seen.add(nxt)
                stack.append(nxt)
    return False                            # tail: explored everything reachable, never met destination
```

Note the explicit `return False` at the end. That's the same "final return" your Course Schedule was missing. **Every function that returns a bool needs both outcomes written out.**

### 3.2 Number of Provinces (547): components from an adjacency matrix

**Problem (paraphrased).** There are `n` cities. `isConnected[i][j] == 1` if cities `i` and `j` are directly connected (the matrix is symmetric, and `isConnected[i][i] == 1`). A province is a group of cities connected directly or indirectly, with no connections outside the group. Return the number of provinces.
Examples: `[[1,1,0],[1,1,0],[0,0,1]]` → `2`. `[[1,0,0],[0,1,0],[0,0,1]]` → `3`.
Constraints: `1 <= n <= 200`.

**Counting components:** loop over every node. Each one that hasn't been seen yet starts a traversal, and that traversal covers its whole component, so **count one per new start**.

```python
def findCircleNum(isConnected):
    n = len(isConnected)
    seen = set()
    def dfs(city):                               # marks every city reachable from `city`
        for other in range(n):
            if isConnected[city][other] == 1 and other not in seen:
                seen.add(other)
                dfs(other)
    provinces = 0
    for city in range(n):
        if city not in seen:                     # a city no earlier traversal reached
            provinces += 1                       # → a new component
            seen.add(city)
            dfs(city)
    return provinces
```

(Recursive DFS is fine here: depth ≤ n ≤ 200.)

### 3.3 Number of Islands (200): components on a grid

**Problem (paraphrased).** Given a grid of `"1"` (land) and `"0"` (water), count the islands. An island is a group of land cells connected horizontally or vertically. Everything outside the grid is water.
Examples: `[["1","1","1","1","0"],["1","1","0","1","0"],["1","1","0","0","0"],["0","0","0","0","0"]]` → `1`. `[["1","1","0","0","0"],["1","1","0","0","0"],["0","0","1","0","0"],["0","0","0","1","1"]]` → `3`.
Constraints: `1 <= rows, cols <= 300`; cells are `"0"` or `"1"`.

The same component count. The nodes are land cells and the neighbour rule is §2.3:

```python
DIRS = ((1, 0), (-1, 0), (0, 1), (0, -1))

def numIslands(grid):
    rows, cols = len(grid), len(grid[0])
    seen = set()
    islands = 0
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] != "1" or (r, c) in seen:
                continue                                  # water, or already part of a counted island
            islands += 1                                  # a new island starts here
            seen.add((r, c))
            stack = [(r, c)]
            while stack:
                cr, cc = stack.pop()                      # name the current cell
                for dr, dc in DIRS:
                    nr, nc = cr + dr, cc + dc             # name the neighbour
                    if (0 <= nr < rows and 0 <= nc < cols
                            and grid[nr][nc] == "1" and (nr, nc) not in seen):
                        seen.add((nr, nc))
                        stack.append((nr, nc))
    return islands
```

Notice the naming: `r, c` is the outer scan position, `cr, cc` the cell being processed, `nr, nc` its neighbour. Three different things, three different names, so none of them can be used in place of another without it being visible. (Lecture 001 §8.1 shows a version that marks land by overwriting it with `"0"`. That's fine too if modifying the input is allowed.)

Why an explicit stack instead of recursion: an all-land 300×300 grid can need about 90,000 levels of recursion, far past Python's default limit of about 1,000.

---

## 4. Shortest steps with BFS (994, 1091)

### 4.1 Why BFS, and only BFS, gives shortest steps

BFS takes nodes from the queue in the order they were added. The start goes in first (distance 0). Its neighbours go in next (distance 1). *Their* new neighbours come after all of those (distance 2), and so on. So **the queue always holds at most two consecutive distances, in increasing order**, and the first time a node is discovered is via a shortest path.

DFS dives down one path first, so the first time it reaches a node can be via a long detour. It finds *a* path, not the shortest one.

The **level loop** makes the distance explicit: at the start of each `while` pass, the queue holds exactly the nodes at the current distance.

```python
while queue:
    for _ in range(len(queue)):      # exactly the nodes at the current distance
        node = queue.popleft()
        ...push unseen neighbours (distance + 1)...
    distance += 1
```

`len(queue)` is evaluated once, at the start of the `for`, so nodes pushed during this level wait for the next one (lecture 001 §8.2).

### 4.2 Rotting Oranges (994): your Sep 12 attempt, fixed

**Problem (paraphrased).** A grid holds `0` (empty), `1` (fresh orange) or `2` (rotten orange). Every minute, each fresh orange next to a rotten one (up, down, left, right) becomes rotten. Return the minimum number of minutes until no fresh orange remains, or `-1` if that's impossible.
Examples: `[[2,1,1],[1,1,0],[0,1,1]]` → `4`. `[[2,1,1],[0,1,1],[1,0,1]]` → `-1` (the bottom-left orange can't be reached). `[[0,2]]` → `0`.
Constraints: `1 <= rows, cols <= 10`.

Your attempt had the right shape: all rotten oranges start in the queue together (multi-source BFS), one level per minute, and a `fresh` count. Three lines differed:

| Your line | What it did | Fix |
|---|---|---|
| `... or grid[r][c] != 1 or (r,c) in visited` | tested the **current** cell, which is rotten (2), so it always skipped | name `nr, nc`, test `grid[nr][nc] == 1` |
| `rotten.append((r,c))` | re-queued the current cell | append `(nr, nc)` |
| (missing) | `fresh` never decreased | `fresh -= 1` when an orange rots |

```python
from collections import deque

def orangesRotting(grid):
    rows, cols = len(grid), len(grid[0])
    queue = deque()
    fresh = 0
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] == 2:
                queue.append((r, c))          # every rotten orange is a source
            elif grid[r][c] == 1:
                fresh += 1
    minutes = 0
    while queue and fresh > 0:
        for _ in range(len(queue)):           # the oranges that rotted in the previous minute
            r, c = queue.popleft()
            for dr, dc in DIRS:
                nr, nc = r + dr, c + dc
                if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] == 1:
                    grid[nr][nc] = 2          # marks it seen AND rotten
                    fresh -= 1
                    queue.append((nr, nc))
        minutes += 1
    return minutes if fresh == 0 else -1
```

Here, setting the cell to `2` is the "mark when pushed" step: a rotten cell can never be queued again.

Trace on `[[2,1,1],[1,1,0],[0,1,1]]` (from running it):

| minute | queue at start of minute | newly rotten | fresh left |
|---|---|---|---|
| 1 | (0,0) | (1,0), (0,1) | 4 |
| 2 | (1,0), (0,1) | (1,1), (0,2) | 2 |
| 3 | (1,1), (0,2) | (2,1) | 1 |
| 4 | (2,1) | (2,2) | 0 |

Answer 4 ✓. Why `while queue and fresh > 0`: without `fresh > 0`, the loop would run one extra round for the last oranges (which have nothing left to infect) and count an extra minute.

### 4.3 Shortest Path in Binary Matrix (1091): BFS distance with 8 directions

**Problem (paraphrased).** In an `n × n` grid of `0` (open) and `1` (blocked), return the length of the shortest path from the top-left cell to the bottom-right cell, moving through open cells in any of 8 directions (including diagonals). The length counts **cells** on the path. Return `-1` if no path exists.
Examples: `[[0,1],[1,0]]` → `2`. `[[0,0,0],[1,1,0],[1,1,0]]` → `4`. `[[1,0,0],[1,1,0],[1,1,0]]` → `-1`.
Constraints: `1 <= n <= 100`.

```python
from collections import deque

def shortestPathBinaryMatrix(grid):
    n = len(grid)
    if grid[0][0] == 1 or grid[n-1][n-1] == 1:
        return -1                                  # start or end blocked
    queue = deque([(0, 0)])
    seen = {(0, 0)}
    length = 1                                     # path length in CELLS: the start alone is 1
    while queue:
        for _ in range(len(queue)):
            r, c = queue.popleft()
            if (r, c) == (n - 1, n - 1):
                return length
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    nr, nc = r + dr, c + dc        # (dr, dc) = (0, 0) gives (r, c), already seen
                    if 0 <= nr < n and 0 <= nc < n and grid[nr][nc] == 0 and (nr, nc) not in seen:
                        seen.add((nr, nc))
                        queue.append((nr, nc))
        length += 1
    return -1
```

**Counting cells vs steps** (lecture 008 §3): a path through `k` cells takes `k - 1` steps. This problem counts cells, so `length` starts at **1**. If it counted steps, it would start at 0. Read the definition, then set the starting value to match it.

---

## 5. Directed graphs: cycles (207), and your Course Schedule

**Problem (paraphrased).** There are `numCourses` courses labelled `0 … numCourses-1`. `prerequisites[i] = [a, b]` means you must take course `b` before course `a`. Return `True` if it's possible to finish every course.
Examples: `numCourses = 2, [[1,0]]` → `True` (take 0, then 1). `numCourses = 2, [[1,0],[0,1]]` → `False` (each needs the other).
Constraints: `1 <= numCourses <= 2000`; up to 5000 prerequisites; all pairs distinct.

### 5.1 The idea

All courses can be finished **exactly when the "must come before" graph has no cycle.** A cycle means some course needs itself, indirectly.

### 5.2 Why two states aren't enough

In an **undirected** graph, `seen` alone works. In a **directed** graph, reaching an already-seen node is *not* always a cycle:

```
0 → 1 → 3
0 → 2 → 3
```

Exploring from 0: `0 → 1 → 3` (3 is now seen), then `0 → 2 → 3`, and 3 is seen again. That's no cycle: 3 is simply reachable two ways. A cycle only happens when you reach a node **that's still on the path you're currently exploring** (an ancestor in the current DFS).

So each node needs **three** states:

| State | Meaning |
|---|---|
| `UNVISITED` | never reached |
| `ON_PATH` | being explored right now: it's an ancestor of where the DFS currently is |
| `DONE` | fully explored, and no cycle was found below it |

Reaching an `ON_PATH` node means you've gone around a loop. Reaching a `DONE` node is safe, because everything below it is already known to be cycle-free.

### 5.3 Your Sep 12 solution *was* this

Your code used two sets:

| Your sets | Equivalent state |
|---|---|
| in `path` | `ON_PATH` |
| in `visited` but not in `path` | `DONE` |
| in neither | `UNVISITED` |

Your checks were in the right order (`path` first → cycle; then `visited` → safe), you added to both on entry, and you removed from `path` when leaving. **That's the three-state algorithm.** Gemini's "you need a three-state solution" was describing what you'd already written. The only bug was the missing `return True` after the outer loop, so acyclic inputs fell off the end of the function and returned `None`. I ran it: with that one line added, it returns the correct answer on every test case I tried.

That's worth remembering for two reasons:

1. **Your idea was right, and you found the real bug yourself.**
2. **An AI's suggestion should be checked against a trace or a failing input, not accepted on authority.** That's the rule in your profile: ask the AI for a failing input, not a fix.

### 5.4 The clean version

```python
def canFinish(numCourses, prerequisites):
    graph = [[] for _ in range(numCourses)]
    for course, pre in prerequisites:
        graph[pre].append(course)            # pre must come before course: edge pre -> course
    UNVISITED, ON_PATH, DONE = 0, 1, 2
    state = [UNVISITED] * numCourses
    def has_cycle(node):                     # contract: is there a cycle reachable from node?
        if state[node] == ON_PATH:
            return True                      # came back to an ancestor: a loop
        if state[node] == DONE:
            return False                     # already fully checked
        state[node] = ON_PATH
        for nxt in graph[node]:
            if has_cycle(nxt):
                return True
        state[node] = DONE                   # leaving: no cycle through here
        return False
    for node in range(numCourses):
        if has_cycle(node):
            return False
    return True                              # tail: no cycle anywhere
```

The contract is in the comment (lecture 002): `has_cycle(node)` answers one yes/no question. Every return statement is visible, including the two at the ends of the functions. That's the "closing checklist" from your profile in practice.

(With up to 2000 nodes, a long prerequisite chain could recurse 2000 deep. Add `sys.setrecursionlimit(10_000)` on LeetCode, or use Kahn's algorithm below, which has no recursion.)

---

## 6. Topological order: Kahn's algorithm (210)

**Problem (paraphrased).** Same setup as 207, but return an order in which all courses can be taken (any valid order), or `[]` if it's impossible.
Examples: `numCourses = 2, [[1,0]]` → `[0,1]`. `numCourses = 4, [[1,0],[2,0],[3,1],[3,2]]` → `[0,1,2,3]` or `[0,2,1,3]`. `numCourses = 1, []` → `[0]`.
Constraints: `1 <= numCourses <= 2000`; up to `numCourses · (numCourses − 1)` prerequisites, all distinct.

### 6.1 Derivation

1. **Name the count** that decides when a course is available: `indegree[c]` = the number of prerequisites of `c` **not yet taken**.
2. A course can be taken now exactly when `indegree[c] == 0`. Put all of those in a queue.
3. **Take** one: add it to the order. Every course that depended on it now has one fewer missing prerequisite: `indegree[nxt] -= 1`. If that reaches 0, it's newly available, so queue it.
4. **Stop** when the queue is empty. If the order has all `numCourses` courses, it's valid. If some are missing, they were stuck waiting on each other, which is a cycle.

```python
from collections import deque

def findOrder(numCourses, prerequisites):
    graph = [[] for _ in range(numCourses)]
    indegree = [0] * numCourses                    # prerequisites not yet taken
    for course, pre in prerequisites:
        graph[pre].append(course)
        indegree[course] += 1
    queue = deque(c for c in range(numCourses) if indegree[c] == 0)
    order = []
    while queue:
        node = queue.popleft()
        order.append(node)                         # take it
        for nxt in graph[node]:
            indegree[nxt] -= 1                     # one fewer missing prerequisite
            if indegree[nxt] == 0:
                queue.append(nxt)                  # newly available
    return order if len(order) == numCourses else []
```

Trace on `numCourses = 4, [[1,0],[2,0],[3,1],[3,2]]` (from running it). Starting indegrees `[0, 1, 1, 2]`, queue `[0]`:

| take | its dependents | indegree after | newly available | queue | order |
|---|---|---|---|---|---|
| 0 | 1, 2 | [0, 0, 0, 2] | 1, 2 | [1, 2] | [0] |
| 1 | 3 | [0, 0, 0, 1] | — | [2] | [0, 1] |
| 2 | 3 | [0, 0, 0, 0] | 3 | [3] | [0, 1, 2] |
| 3 | — | [0, 0, 0, 0] | — | [] | [0, 1, 2, 3] |

All 4 taken, so the answer is `[0, 1, 2, 3]` ✓. The same algorithm answers 207 too: `return len(order) == numCourses`.

**DFS (§5) or Kahn's?** Both are O(V + E). Kahn's has no recursion and directly produces the order. Know one well and recognize the other.

---

## 7. Copying a graph (133)

**Problem (paraphrased).** Given a reference to one node of a connected undirected graph, return a **deep copy** of the graph: new node objects with the same values and the same connections. Each node has `val` (an int, unique, 1 … n) and `neighbors` (a list of nodes).
Examples: adjacency list `[[2,4],[1,3],[2,4],[1,3]]` (node 1's neighbours are 2 and 4, …) → a copy with the same structure. `[[]]` → a single node, no neighbours. `[]` → `None`.
Constraints: 0 to 100 nodes.

**Name the quantity:** `copy_of[old]` = the new node that copies `old`. This dictionary does two jobs: it finds the copy of a neighbour that's already been made, and it's the `seen` set.

```python
class Node:
    def __init__(self, val=0, neighbors=None):
        self.val = val
        self.neighbors = neighbors if neighbors is not None else []

def cloneGraph(node):
    if node is None:
        return None
    copy_of = {node: Node(node.val)}             # old node -> its copy; also the "seen" set
    stack = [node]
    while stack:
        old = stack.pop()
        for nb in old.neighbors:
            if nb not in copy_of:                # first time we meet nb: make its copy, explore it later
                copy_of[nb] = Node(nb.val)
                stack.append(nb)
            copy_of[old].neighbors.append(copy_of[nb])   # connect the COPIES
    return copy_of[node]
```

The key line is the last one in the loop: copies connect to **copies**, never to originals. And `neighbors=None` in the constructor (not `neighbors=[]`) avoids Python's shared-default-argument trap, where every node would share one list.

---

## 8. Complexity

With `V` nodes and `E` edges, using an adjacency list:

- Every node enters the frontier **at most once** (mark when pushed), so O(V) pushes and pops.
- Each node's neighbour list is scanned once when it's processed. Summed over all nodes, that's every edge once (twice for undirected): O(E).
- **Total: O(V + E) time, O(V) space** for `seen` and the frontier.

| Representation | Time to traverse |
|---|---|
| Adjacency list | O(V + E) |
| Adjacency matrix | O(V²) (each node scans a full row) |
| Grid `R × C` | O(R·C) (each cell has at most 4 or 8 neighbours) |

---

## 9. Tracing graph code

The lecture 003 protocol, with the layouts from lecture 003 §5.3 and §5.6:

| Pattern | Rows | Columns |
|---|---|---|
| DFS / components | one row per pop | `popped | neighbours checked (name, valid?, seen?) | pushed | stack after | seen after` |
| BFS shortest steps | one row per **level** | `level | queue at start | newly discovered | counters (fresh, length)` |
| Directed cycle | one line per call, indented (a call tree) | `node | state before | state after`, and "back to ON_PATH → cycle" |
| Kahn's | one row per node taken | `take | dependents | indegree after | newly available | queue | order` (§6 trace) |

Draw the graph first, as nodes with arrows, from the edge list, and **write the edge-direction sentence above it.** For grids, draw the grid and fill cells in as they're discovered.

Good trace inputs: a graph with **two components**; a node with **no edges**; for directed graphs, a **diamond** (`0→1→3, 0→2→3`, which has no cycle) and a **2-cycle** (`0→1→0`); for grids, a fresh orange that **can't be reached**.

---

## 10. Recognizing graph problems

| Signal | Think |
|---|---|
| grid of cells + "connected", "region", "island", "flood" | grid DFS/BFS, count components |
| "minimum steps / moves / minutes", all moves cost the same | BFS with the level loop |
| several starting points spreading at once | multi-source BFS (all sources in the queue at the start) |
| "prerequisite", "depends on", "order of tasks", "build order" | directed graph: cycle detection or topological sort |
| a list of pairs `[a, b]` + "connected", "friends", "network" | build an adjacency list, then traverse or count components |
| "copy", "clone" a structure with cycles | traversal + old→new map |
| weighted edges + "cheapest / shortest" | **not plain BFS** (Dijkstra; a later topic) |

Before coding, three comment lines (the same habit as lectures 004–006):

```python
# graph: nodes = ___, edge a -> b means ___ (directed/undirected)
# pattern: reachability / components / BFS distance / cycle / topo order / clone
# seen: ___ (marked when pushed);  neighbour valid set: ___
```

---

## 11. Practice ladder

| # | Problem | Pattern | Full problem |
|---|---|---|---|
| 1 | 1971 Find if Path Exists in Graph | build adjacency list + DFS | §3.1 |
| 2 | 547 Number of Provinces | components (matrix) | §3.2 |
| 3 | 200 Number of Islands | components (grid) | §3.3 |
| 4 | 994 Rotting Oranges (redo from Sep 12) | multi-source BFS levels | §4.2 |
| 5 | 1091 Shortest Path in Binary Matrix | BFS distance, cells vs steps | §4.3 |
| 6 | 207 Course Schedule (redo, with the final return) | 3-state DFS | §5 |
| 7 | 210 Course Schedule II | Kahn's algorithm | §6 |
| 8 | 133 Clone Graph | old→new map | §7 |
| stretch | 695 Max Area of Island, 417 Pacific Atlantic Water Flow, 542 01 Matrix | variations | |

Log each attempt in the tracker. The tags to watch here are `ALIAS` (wrong cell/node name), `TAIL` (missing final return/decrement) and `BOUNCER` (missing or late bounds check), which are the three graph bugs you've had.

---

## Common mistakes

| Mistake | Your history | Fix |
|---|---|---|
| Using the current cell instead of the neighbour | Rotting Oranges, Sep 12 | `nr, nc = r + dr, c + dc`; after that line, don't use `r, c` |
| Counter never decremented | Rotting Oranges (`fresh`) | Decrement exactly where the state changes (when an orange rots) |
| Missing final `return True` / `return False` | Course Schedule, Sep 12 | Write both outcomes; check the last line of every function |
| Marking seen when popping | — | Mark when pushing |
| Two states for a directed cycle | — | Three states: `ON_PATH` ≠ `DONE` |
| Wrong edge direction | — | Write the sentence "`[a, b]` means ___, so the edge is ___ → ___" |
| `[[]] * n` adjacency list | — | `[[] for _ in range(n)]` |
| Bounds check after indexing | — | Bounds first; `and` short-circuits |
| Recursion on large grids | — | Explicit stack (Python's limit is ~1000) |
| DFS for "minimum steps" | — | BFS with levels |

---

## Interview relevance

- Number of Islands, Rotting Oranges, Course Schedule I/II and Clone Graph are among the most frequently asked medium problems.
- **What to say:** "I'll model this as a graph: nodes are ___, edges are ___. I need the fewest steps, so BFS, marking cells when I enqueue them. That's O(rows × cols)."
- **Follow-ups to expect:** "what if the grid is huge?" (iterative, not recursive); "can you do it in place?" (overwrite visited cells); "what if the edges have weights?" (Dijkstra); "find the order, not just whether it's possible" (Kahn's).
- Saying out loud why a directed graph needs three states is a strong signal. Most candidates just memorize it.

---

## Self-check questions

1. What are the three parts of every traversal?
<details><summary>Answer</summary>

A frontier (stack for DFS, queue for BFS), a seen set, and a neighbour rule.
</details>

2. Why mark a node as seen when pushing it rather than when popping it?
<details><summary>Answer</summary>

So each node enters the frontier at most once. Marking on pop lets several neighbours push the same node, which wastes work, and in BFS a later copy can carry a wrong (larger) distance.
</details>

3. In your Sep 12 Rotting Oranges, which three lines were wrong?
<details><summary>Answer</summary>

The condition tested `grid[r][c]` (the current cell) instead of the neighbour; it appended `(r, c)` instead of `(nr, nc)`; and `fresh` was never decremented.
</details>

4. How do you count connected components?
<details><summary>Answer</summary>

Loop over every node; whenever one hasn't been seen yet, count one more component and run a traversal from it that marks its whole component.
</details>

5. Why does BFS give the shortest number of steps, and DFS doesn't?
<details><summary>Answer</summary>

BFS processes nodes in order of distance (the queue holds distance d, then d+1), so the first discovery of a node is via a shortest path. DFS follows one path deeply first, so its first discovery can be via a detour.
</details>

6. Shortest Path in Binary Matrix counts cells, not steps. What's the starting `length`, and why?
<details><summary>Answer</summary>

1. The path consisting of just the start cell has 1 cell (and 0 steps).
</details>

7. In a directed graph, why can reaching an already-seen node be fine?
<details><summary>Answer</summary>

It may be fully explored already (DONE) and reachable by two different paths, as in the diamond `0→1→3, 0→2→3`. Only reaching a node that's still on the current DFS path (an ancestor) means a cycle.
</details>

8. Map your Sep 12 `visited` and `path` sets to the three states.
<details><summary>Answer</summary>

In `path` → ON_PATH. In `visited` but not `path` → DONE. In neither → UNVISITED.
</details>

9. For `prerequisites[i] = [a, b]` ("take `b` before `a`"), which way does the edge point?
<details><summary>Answer</summary>

`b → a` (`graph[b].append(a)`), "b comes before a." Then `indegree[a] += 1`.
</details>

10. How does Kahn's algorithm detect a cycle?
<details><summary>Answer</summary>

Nodes on a cycle never reach indegree 0, so they're never taken. If the final order has fewer than `numCourses` nodes, there's a cycle.
</details>

11. In Clone Graph, what two jobs does the `copy_of` dictionary do?
<details><summary>Answer</summary>

It maps each original node to its copy (so neighbours are connected to the right copies), and it acts as the seen set (a node is in it exactly when it's been discovered).
</details>

12. What's the time complexity of BFS on an adjacency list, and why?
<details><summary>Answer</summary>

O(V + E): each node is pushed and popped once (mark when pushed), and each node's edge list is scanned once when it's processed.
</details>

---

## Sources

- Problems: LeetCode 1971, 547, 200, 994, 1091, 207, 210, 133 (stretch: 695, 417, 542). Statements paraphrased; examples and constraints from long-standing problem pages (from my own knowledge, not re-fetched; 2026-10-11).
- Kahn's algorithm: A. B. Kahn, "Topological sorting of large networks," *Communications of the ACM* 5(11), 1962. Three-state (white/grey/black) DFS for directed cycle detection: Cormen et al., *Introduction to Algorithms*, chapter on elementary graph algorithms.
- Python: `collections.deque` (https://docs.python.org/3/library/collections.html#collections.deque); default recursion limit (https://docs.python.org/3/library/sys.html#sys.getrecursionlimit); mutable default arguments (https://docs.python.org/3/reference/compound_stmts.html#function-definitions).
- Your Sep 12 Rotting Oranges and Course Schedule attempts (`001_practice_medium.py`) were re-run on 2026-10-04.
- Verification (2026-10-11): every function was tested against independent brute-force references on 2,000 random graphs and grids (union-find, step simulation, distance relaxation, all-permutations ordering, structural comparison for clones), plus the listed examples. Traces were produced by running the code.
