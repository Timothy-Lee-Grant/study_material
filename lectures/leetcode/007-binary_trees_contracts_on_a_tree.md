# Lecture 007: Binary Trees: Recursion Contracts on a Tree

> **For:** Timothy · **Date:** 2026-10-09
> **Prerequisites:** lecture 002 (the Contract Sentence, answer-up vs accumulate-down, base case = the empty problem). Lecture 003 §5.5 (call-tree traces). Lecture 006 §6 (BFS-style level loops show up again here).
> **Why this topic, why now:**
> - **Your #2 weakness is the recursion contract** ("answers flow up"). Trees are where that skill gets used most. Almost every tree problem is one recursive function plus a Contract Sentence.
> - **You've done only one tree problem** (Sum Root to Leaf, Sep 26), and you got it **right on the first try**, passing the path down and the sum up. This lecture builds on that.
> - **Trees are one of the most frequent interview topics,** and they're short to code, so practice is cheap.
> - **Validate BST** is the cleanest use yet of the method that clicked for you (name → valid set → test membership): each node gets an explicit valid range.
>
> **Format notes:** every problem includes the full statement (paraphrased), examples and constraints. Every rule is derived. All tree examples use LeetCode's array format, which §1.2 explains.
> **Verification:** every solution was tested against brute force on 3,000 random trees (0–9 nodes, including empty and single-node trees). Trace output was produced by running the code.

---

## Core ideas (the answer key)

1. **A binary tree is recursive by definition:** a tree is either empty (`None`) or a node with a left tree and a right tree. So the natural function on a tree is one that calls itself on `node.left` and `node.right`.
2. **Write the Contract Sentence for one node:** `f(node)` = <the answer> for the subtree rooted at `node`.
3. **The base case is the empty tree, `node is None`,** and it returns the answer for an empty problem: depth 0, sum 0, "valid" True, "found" False.
4. **Answer up:** combine the children's answers (`1 + max(left, right)`, `left + right`, `left and right`). That's lecture 002's "leap of faith": trust `f` on the children.
5. **Context down:** information the subtree needs from its ancestors (the number built so far, the remaining target, the allowed value range) goes in as a **parameter**. Your Sum Root to Leaf did exactly this.
6. **Answer up + global best:** when the best answer might pass *through* a node but the parent needs something different (diameter, max path sum), return what the parent needs and update a separate `best` on the side.
7. **Validate BST = a valid range per node.** Each node's value must lie in an open range `(lo, hi)` inherited from its ancestors. Checking only the children is the classic bug.
8. **Level-by-level questions use BFS with a level loop** (`for _ in range(len(queue))`), the same as Rotting Oranges.
9. **Leaf ≠ empty.** A leaf is a node with no children (`node.left is None and node.right is None`). Path problems ("root-to-leaf") must stop at leaves, not at `None`.
10. **Trace a tree function by drawing the tree and writing each node's return value next to it,** bottom-up. The call tree *is* the tree.

---

## Table of Contents

- [0. The map: four ways information moves in a tree](#0-the-map-four-ways-information-moves-in-a-tree)
- [1. Tree basics you need (and LeetCode's array format)](#1-tree-basics-you-need-and-leetcodes-array-format)
- [2. The tree recipe, derived](#2-the-tree-recipe-derived)
- [3. Answer up (104, 226, 100)](#3-answer-up-104-226-100)
- [4. Context down (112, 129 revisited)](#4-context-down-112-129-revisited)
- [5. Validate BST: a valid range for every node (98)](#5-validate-bst-a-valid-range-for-every-node-98)
- [6. Answer up + global best (543, 110)](#6-answer-up--global-best-543-110)
- [7. Level by level: BFS (102, 199)](#7-level-by-level-bfs-102-199)
- [8. Lowest Common Ancestor: what does the function report? (236)](#8-lowest-common-ancestor-what-does-the-function-report-236)
- [9. Tracing tree code](#9-tracing-tree-code)
- [10. Recognizing which flow you need](#10-recognizing-which-flow-you-need)
- [11. Practice ladder](#11-practice-ladder)
- [Common mistakes](#common-mistakes)
- [Interview relevance](#interview-relevance)
- [Self-check questions](#self-check-questions)
- [Sources](#sources)

---

## 0. The map: four ways information moves in a tree

| # | Flow | What goes down (parameters) | What comes up (return value) | Problems |
|---|---|---|---|---|
| A | **Answer up** | just the node | the answer for this subtree | 104 Max Depth, 226 Invert, 100 Same Tree |
| B | **Context down** | something about the path from the root (number so far, remaining target, allowed range) | the answer for this subtree, *given* that context | 112 Path Sum, 129 Sum Root to Leaf, 98 Validate BST |
| C | **Answer up + global best** | just the node | what the **parent** needs (e.g. height), while a separate `best` records the answer *through* this node | 543 Diameter, 124 Max Path Sum, 110 Balanced (variant) |
| D | **Level by level** | — (no recursion) | — | 102 Level Order, 199 Right Side View |

Flows A–C are lecture 002's two styles, specialised to trees:

- **A** is pure answer-up.
- **B** is answer-up with **context** parameters. Context is fine as a parameter when it really changes what the subtree's answer is (lecture 002 §2.2: "does the future depend on it?"). The digits above a node *do* change the numbers below it, so they belong in the parameters.
- **C** adds a side variable for answers that can't be passed to the parent.

Choosing the flow is most of the work. The code is usually 5–10 lines.

---

## 1. Tree basics you need (and LeetCode's array format)

### 1.1 The node

```python
class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right
```

| Term | Meaning |
|---|---|
| **root** | the top node; the whole tree is passed to you as `root` (which can be `None`: an empty tree) |
| **leaf** | a node with **no** children: `node.left is None and node.right is None` |
| **subtree of `node`** | `node` plus everything below it |
| **depth / height** | number of nodes on the longest root-to-leaf path (LeetCode's "max depth" counts nodes; "diameter" counts edges, so read each problem's definition) |
| **BST** (binary search tree) | every value in a node's left subtree is smaller than the node, every value in its right subtree is larger |

### 1.2 Reading LeetCode's array format

LeetCode writes trees as a list read **level by level, left to right**, with `null` (Python `None`) for a missing child:

```
[3, 9, 20, null, null, 15, 7]

level 0:        3
level 1:     9     20
level 2:   (·)(·) 15   7       ← 9's children are null, null; 20's children are 15, 7
```

Rules: the first value is the root. Then each existing node, in order, takes the next two values as its left and right child. Missing children don't get children slots of their own. Trailing `null`s are usually omitted.

**When you trace a tree problem, draw the tree from this array first.** It takes 20 seconds and prevents misreading.

---

## 2. The tree recipe, derived

The same five steps as lecture 002 §3.2, specialised to trees:

**Step 1: Contract Sentence for one node.** `f(node)` = <answer> for the subtree rooted at `node`. If the subtree needs information from above, name it as a parameter: `f(node, context)`.

**Step 2: Base case = the empty tree.** `node is None` → the answer for an empty subtree (lecture 002 §4.2's empty-problem table):

| Question | Empty tree answers |
|---|---|
| depth / height / number of nodes / sum | 0 |
| "is it valid / balanced / symmetric?" | True |
| "does a path / node exist?" | False |
| "the node (or `None`)" | None |

**Step 3: Leap of faith.** Assume `f(node.left)` and `f(node.right)` already satisfy the contract.

**Step 4: Combine.** Write the current node's answer using only `node.val`, the two children's answers, and the context.

**Step 5: Leaf check (only if the problem is about root-to-leaf paths).** A leaf is a node with two `None` children. Decide whether the answer is produced *at* the leaf (path problems) or whether `None` is enough (most other problems).

Complexity is almost always **O(n) time** (each node visited once) and **O(h) space** for the recursion stack, where `h` is the height (`log n` for a balanced tree, up to `n` for a chain).

---

## 3. Answer up (104, 226, 100)

### 3.1 Maximum Depth of Binary Tree (104)

**Problem (paraphrased).** Return the maximum depth of a binary tree: the number of nodes on the longest path from the root down to a leaf.
Examples: `[3,9,20,null,null,15,7]` → `3`. `[1,null,2]` → `2`. `[]` → `0`.
Constraints: 0 to 10⁴ nodes; values between -100 and 100.

1. **Contract:** `depth(node)` = number of nodes on the longest downward path starting at `node`.
2. **Base:** empty tree → 0.
3–4. **Combine:** this node (1) plus the deeper child.

```python
def maxDepth(root):
    if root is None:
        return 0
    return 1 + max(maxDepth(root.left), maxDepth(root.right))
```

### 3.2 Invert Binary Tree (226)

**Problem (paraphrased).** Mirror a binary tree (swap every node's left and right subtrees) and return its root.
Example: `[4,2,7,1,3,6,9]` → `[4,7,2,9,6,3,1]`. `[]` → `[]`.
Constraints: 0 to 100 nodes.

**Contract:** `invert(node)` mirrors the subtree at `node` and returns its root.

```python
def invertTree(root):
    if root is None:
        return None
    root.left, root.right = invertTree(root.right), invertTree(root.left)
    return root
```

Python evaluates the whole right-hand side before assigning, so both recursive calls see the original children. (Assigning on two separate lines would overwrite `root.left` before it's used: the in-place hazard from lecture 001 §7.)

### 3.3 Same Tree (100)

**Problem (paraphrased).** Given the roots `p` and `q` of two binary trees, return `True` if they have the same shape and the same values in every position.
Examples: `[1,2,3]` vs `[1,2,3]` → `True`. `[1,2]` vs `[1,null,2]` → `False`.
Constraints: 0 to 100 nodes each.

**Contract:** `same(p, q)` = whether the subtrees at `p` and `q` are identical. With **two** inputs, there are **three** base-case situations, and naming them all positively avoids the negation trap:

```python
def isSameTree(p, q):
    if p is None and q is None:        # both empty: identical
        return True
    if p is None or q is None:         # exactly one empty: different shapes
        return False
    return p.val == q.val and isSameTree(p.left, q.left) and isSameTree(p.right, q.right)
```

---

## 4. Context down (112, 129 revisited)

### 4.1 Path Sum (112)

**Problem (paraphrased).** Given a tree and an integer `targetSum`, return `True` if some **root-to-leaf** path has values summing to `targetSum`.
Examples: `[5,4,8,11,null,13,4,7,2,null,null,null,1], 22` → `True` (5→4→11→2). `[1,2,3], 5` → `False`. `[], 0` → `False` (no paths in an empty tree).
Constraints: 0 to 5000 nodes; values and target between -1000 and 1000.

**What the subtree needs from above:** how much of the target is still left. Name it `remaining`.

1. **Contract:** `has(node, remaining)` = whether some path from `node` down to a leaf sums to `remaining`.
2. **Base (empty):** no path exists → `False`.
3. **Leaf:** the path ends here, so it works exactly when this node's value uses up the rest.
4. **Combine:** either child can finish the job (`or`).

```python
def hasPathSum(root, targetSum):
    if root is None:
        return False                                   # an empty tree has no paths
    remaining = targetSum - root.val
    if root.left is None and root.right is None:       # leaf: the path ends here
        return remaining == 0
    return hasPathSum(root.left, remaining) or hasPathSum(root.right, remaining)
```

**Why the leaf check is needed** (core idea 9): for `[1,2], targetSum = 1`, the root has a missing right child. Without the leaf check, `hasPathSum(None, 0)` would be the "end" of the path 1 → (nothing), which sums to 1. But node 1 isn't a leaf, so `1` alone is not a root-to-leaf path. **`None` means "no tree here," not "the path ended."** The only valid stopping point is a real leaf.

### 4.2 Sum Root to Leaf Numbers (129): your Sep 26 solution, revisited

**Problem (paraphrased).** Every node holds a digit 0–9. Each root-to-leaf path spells a number (root digit first). Return the sum of all those numbers.
Examples: `[1,2,3]` → `25` (12 + 13). `[4,9,0,5,1]` → `1026` (495 + 491 + 40).
Constraints: 1 to 1000 nodes; values 0–9; depth ≤ 10.

Your solution passed the digits down as a **string** and converted at the leaf. That was correct (I ran it: 1026 and 25). It's the right flow: context (the number so far) down, answer (sum of leaf numbers) up. The integer version names the context as a number:

```python
def sumNumbers(root):
    def dfs(node, prefix):                       # prefix = the number spelled by the path ABOVE node
        if node is None:
            return 0                             # empty subtree: contributes nothing
        number = prefix * 10 + node.val          # append this digit
        if node.left is None and node.right is None:
            return number                        # leaf: the path's number is complete
        return dfs(node.left, number) + dfs(node.right, number)
    return dfs(root, 0)
```

`prefix * 10 + digit` is how you append a digit to a number. (It's exactly the line you commented out in Reverse Integer back in July, `answer*10 + ...`. It was correct there too.)

Your version also had `if not path: return 0` at the leaf. That check could never be true (the path always has at least the leaf's digit), so it can go. Not a bug, just dead code.

---

## 5. Validate BST: a valid range for every node (98)

**Problem (paraphrased).** Return `True` if the tree is a valid binary search tree: for every node, **all** values in its left subtree are strictly less than the node's value, **all** values in its right subtree are strictly greater, and both subtrees are valid BSTs too.
Examples: `[2,1,3]` → `True`. `[5,1,4,null,null,3,6]` → `False` (4 is in 5's right subtree but less than 5). `[5,4,6,null,null,3,7]` → `False`.
Constraints: 1 to 10⁴ nodes; values between -2³¹ and 2³¹ − 1.

### 5.1 The tempting wrong solution

"Each node's left child is smaller and right child is bigger." Check that on `[5,4,6,null,null,3,7]`:

```
        5
      4   6
         3  7
```

At node 5: left 4 < 5 ✓, right 6 > 5 ✓. At node 6: left 3 < 6 ✓, right 7 > 6 ✓. Every parent-child pair passes, but **3 sits in 5's right subtree and is less than 5**. The rule is about *all* values in a subtree, not just the children.

### 5.2 Derivation with name → valid set → test

**Name the quantity:** the range of values a node is *allowed* to have, given all its ancestors.

**Write the valid set:** an open interval `(lo, hi)`. The root can be anything: `(-∞, +∞)`.

**How it changes going down:**

- Going **left** from a node with value `v`: everything there must also be `< v`. The upper bound tightens: `(lo, v)`.
- Going **right**: everything must be `> v`. The lower bound tightens: `(v, hi)`.

**Test membership, positively:** `lo < node.val < hi`.

```python
def isValidBST(root):
    def ok(node, lo, hi):                   # every value in this subtree must be in (lo, hi)
        if node is None:
            return True                     # an empty tree is a valid BST
        if not (lo < node.val < hi):
            return False
        return ok(node.left, lo, node.val) and ok(node.right, node.val, hi)
    return ok(root, float('-inf'), float('inf'))
```

The `not (...)` here wraps a single, positively written membership test, so there's only one negation and it's of a condition you wrote first. The C1 rule is about not *deriving* a condition through negation, and that's respected here.

Trace on `[5,4,6,null,null,3,7]` (from running the code):

```
ok(5, (-inf, inf)): -inf < 5 < inf → True
    ok(4, (-inf, 5)): -inf < 4 < 5 → True
    ok(6, (5, inf)): 5 < 6 < inf → True
        ok(3, (5, 6)): 5 < 3 < 6 → False        ← 3 inherited the lower bound 5 from the root
```

The range column is what makes the bug visible: 3 inherits `lo = 5` from two levels up. A child-only check never sees it.

Equivalent alternative: an in-order traversal (left, node, right) of a BST produces strictly increasing values. Both are fine. The range version is the one that shows context-down cleanly.

---

## 6. Answer up + global best (543, 110)

### 6.1 Diameter of Binary Tree (543)

**Problem (paraphrased).** Return the length of the longest path between **any** two nodes, measured in **edges**. The path doesn't have to pass through the root.
Examples: `[1,2,3,4,5]` → `3` (4→2→1→3, or 5→2→1→3). `[1,2]` → `1`.
Constraints: 1 to 10⁴ nodes.

**Why plain answer-up doesn't work.** Try the contract "`f(node)` = diameter of the subtree at `node`." To combine at a node, you'd need the longest path that *goes through* the node: down the left side as far as possible, and down the right side as far as possible. That needs the children's **heights**, not their diameters. So the parent needs one thing (height) and the answer is something else (diameter).

**The fix: two named quantities.**

- **Return value (what the parent needs):** `height(node)` = number of nodes on the longest downward path from `node`. Empty = 0.
- **Side variable (the answer):** `best` = the longest path seen so far. At each node, the longest path that bends *at* that node has `height(left) + height(right)` edges.

```python
def diameterOfBinaryTree(root):
    best = 0                                  # longest path (in edges) seen anywhere so far
    def height(node):
        nonlocal best                         # we assign to the outer variable
        if node is None:
            return 0
        left = height(node.left)
        right = height(node.right)
        best = max(best, left + right)        # the longest path that bends at this node
        return 1 + max(left, right)           # what the PARENT needs
    height(root)
    return best
```

Trace on `[1,2,3,4,5]` (from running the code), listed in the order calls *finish*:

```
        height(4): left=0, right=0, through-here=0, best=0, returns 1
        height(5): left=0, right=0, through-here=0, best=0, returns 1
    height(2): left=1, right=1, through-here=2, best=2, returns 2
    height(3): left=0, right=0, through-here=0, best=2, returns 1
height(1): left=2, right=1, through-here=3, best=3, returns 3
```

Answer 3 ✓. Note how the values for node 2 split: it **returns** 2 (its height, for node 1's use) but **records** 2 into `best` (the path 4-2-5). Different questions, different variables.

**Python note:** `nonlocal best` is required because the inner function *assigns* to `best`. Without it, Python treats `best` as a new local variable and throws `UnboundLocalError`. (Reading an outer variable needs no declaration; assigning does. A mutable container like `best = [0]` with `best[0] = …` also works.)

### 6.2 Balanced Binary Tree (110): an answer that can also mean "failed"

**Problem (paraphrased).** Return `True` if, for every node, the heights of its left and right subtrees differ by at most 1.
Examples: `[3,9,20,null,null,15,7]` → `True`. `[1,2,2,3,3,null,null,4,4]` → `False`. `[]` → `True`.
Constraints: 0 to 5000 nodes.

Same shape as diameter: the parent needs heights, and the answer is about every node. Here, instead of a side variable, use a **sentinel return value**: `-1` means "this subtree is already unbalanced." Heights are never negative, so `-1` can't be mistaken for a real height (the same reasoning as your `-1` memo sentinel in LCS).

```python
def isBalanced(root):
    def height(node):                         # height, or -1 if this subtree is unbalanced
        if node is None:
            return 0
        left = height(node.left)
        if left == -1:
            return -1                         # already failed below: pass it up
        right = height(node.right)
        if right == -1 or abs(left - right) > 1:
            return -1
        return 1 + max(left, right)
    return height(root) != -1
```

---

## 7. Level by level: BFS (102, 199)

### 7.1 Binary Tree Level Order Traversal (102)

**Problem (paraphrased).** Return the node values level by level, left to right within each level, as a list of lists.
Examples: `[3,9,20,null,null,15,7]` → `[[3],[9,20],[15,7]]`. `[1]` → `[[1]]`. `[]` → `[]`.
Constraints: 0 to 2000 nodes.

This is **not** a recursion-contract problem. It's the BFS level loop from Rotting Oranges (lecture 001 §8.2): the queue at the start of each round holds exactly one level.

```python
from collections import deque

def levelOrder(root):
    if root is None:
        return []
    out = []
    queue = deque([root])
    while queue:
        level = []
        for _ in range(len(queue)):           # exactly the nodes of the current level
            node = queue.popleft()
            level.append(node.val)
            if node.left:
                queue.append(node.left)
            if node.right:
                queue.append(node.right)
        out.append(level)
    return out
```

### 7.2 Binary Tree Right Side View (199)

**Problem (paraphrased).** Imagine standing to the right of the tree. Return the values of the nodes you can see, top to bottom: the **last** node of each level.
Examples: `[1,2,3,null,5,null,4]` → `[1,3,4]`. `[1,null,3]` → `[1,3]`. `[]` → `[]`.
Constraints: 0 to 100 nodes.

Once level order works, it's one line:

```python
def rightSideView(root):
    return [level[-1] for level in levelOrder(root)]
```

(Interviewers might ask for it without building every level: inside the level loop, record the node popped when `_ == size - 1`.)

---

## 8. Lowest Common Ancestor: what does the function report? (236)

**Problem (paraphrased).** Given a binary tree and two of its nodes `p` and `q` (both guaranteed to be in the tree), return their lowest common ancestor: the deepest node that has both `p` and `q` in its subtree. A node counts as being in its own subtree.
Examples: tree `[3,5,1,6,2,0,8,null,null,7,4]`, `p = 5, q = 1` → `3`. Same tree, `p = 5, q = 4` → `5` (5 is an ancestor of 4).
Constraints: 2 to 10⁵ nodes; all values unique; `p != q`; both exist.

This one is hard because the contract isn't obvious. Write it carefully:

> `lca(node)` = **if both `p` and `q` are in this subtree, their LCA; if exactly one is, that node; if neither, `None`.**

In other words, the function **reports what it found** in its subtree.

- **Base:** empty → found nothing → `None`. If `node` is `p` or `q` itself → report `node`. (Whether or not the other one is below it: if it is, `node` is the LCA anyway, because a node is its own ancestor.)
- **Combine:** ask both children.
  - Both report something → `p` and `q` are on different sides, so `node` is the lowest point that has both → return `node`.
  - Only one side reports → pass that report up unchanged.

```python
def lowestCommonAncestor(root, p, q):
    if root is None or root is p or root is q:
        return root
    left = lowestCommonAncestor(root.left, p, q)
    right = lowestCommonAncestor(root.right, p, q)
    if left and right:                  # p and q were found on different sides
        return root
    return left if left else right      # pass up whatever was found (or None)
```

**`is` vs `==`:** `root is p` asks whether these are the *same node object*. Use `is` for node identity. (`==` on objects without a custom `__eq__` also compares identity, but `is` says what you mean.)

---

## 9. Tracing tree code

The lecture 003 call-tree trace becomes even simpler on trees: **draw the tree, then write each node's return value next to it, bottom-up** (children before parents, the order calls finish).

```
            1  → 3 (height), best=3
          /   \
   2 → 2,best=2   3 → 1
     /   \
  4 → 1   5 → 1
```

**Check each node's number against the Contract Sentence on its own:** "is 2 really the height of the subtree at node 2?" (Yes: 2-4.) That's lecture 002 §9 step 3, and it works on a tree because every node is its own subproblem.

**For context-down problems, also write the context next to each node** (the `(lo, hi)` range for Validate BST, the `prefix` for Sum Root to Leaf, `remaining` for Path Sum). The bug is usually a node whose context is wrong.

Good trace inputs for trees:

| Input | Why |
|---|---|
| `[]` | the empty tree (base case only) |
| `[1]` | a single node: root *and* leaf |
| `[1,2]` | one child missing: catches "`None` treated as a leaf" |
| `[1,2,3,4,5]` | uneven depths |
| a "chain" `[1,null,2,null,3]` | the recursion depth equals n |
| for BST: `[5,4,6,null,null,3,7]` | the grandparent-violation case |

---

## 10. Recognizing which flow you need

| The question | Flow | First line to write |
|---|---|---|
| depth, size, sum, "is it symmetric/same/inverted" | **A: answer up** | `# f(node) = ___ for the subtree at node` |
| anything about a **root-to-leaf path** or depending on ancestors (target remaining, number so far, allowed range) | **B: context down** | `# f(node, ctx) = ___ for the subtree at node, given ctx from above` |
| longest/best path **between any two nodes**, or a property of *every* node that needs child heights | **C: up + global best** (or a sentinel) | `# returns: ___ (for the parent);  best: ___ (the answer)` |
| "level", "row", "depth-by-depth", "visible from the side", "minimum depth by levels" | **D: BFS** | `queue = deque([root]); for _ in range(len(queue))` |
| "ancestor", "find node(s) and report" | answer up, with a **reporting** contract | `# f(node) = what this subtree found` |

---

## 11. Practice ladder

| # | Problem | Flow | Full problem |
|---|---|---|---|
| 1 | 104 Maximum Depth | A | §3.1 |
| 2 | 226 Invert Binary Tree | A | §3.2 |
| 3 | 100 Same Tree | A, two inputs | §3.3 |
| 4 | 112 Path Sum | B, leaf check | §4.1 |
| 5 | 129 Sum Root to Leaf (redo with integers) | B | §4.2 |
| 6 | 102 Level Order | D | §7.1 |
| 7 | 199 Right Side View | D | §7.2 |
| 8 | 98 Validate BST | B, valid range | §5 |
| 9 | 543 Diameter | C | §6.1 |
| 10 | 110 Balanced | C, sentinel | §6.2 |
| 11 | 236 Lowest Common Ancestor | reporting contract | §8 |
| stretch | 124 Binary Tree Maximum Path Sum | C, with negative values | |

For each: write the Contract Sentence (or the BFS line) first, draw the tree from the array, trace the inputs from §9, then submit. Log any `CONTRACT`, `BASE` or `TAIL` bugs in the tracker. Those are the categories this lecture is meant to drive down.

---

## Common mistakes

| Mistake | Why it's wrong | Fix |
|---|---|---|
| Base case at the leaf only, no `None` check | Crashes on a node with one child (`None.left`) | Always handle `node is None` first |
| Treating `None` as a leaf in path problems | Counts "paths" that stop at a missing child (`[1,2], 1` → True) | Path answers happen only at real leaves |
| Validate BST by comparing with children only | Misses grandparent violations (`[5,4,6,null,null,3,7]`) | Pass `(lo, hi)` down |
| Using `<=` in Validate BST | Duplicates aren't allowed ("strictly") | `lo < val < hi` |
| Returning the answer when the parent needs something else (diameter) | Can't combine diameters into a diameter | Return height; keep `best` separately |
| Assigning to an outer variable without `nonlocal` | `UnboundLocalError` | `nonlocal best` |
| Swapping children on two lines in Invert | The second line reads the already-overwritten child | One tuple assignment |
| BFS without the level loop | Levels mix together | `for _ in range(len(queue))` |
| `root == p` vs `root is p` | Works only by accident if `__eq__` is defined differently | `is` for identity |

---

## Interview relevance

- Trees are among the most common interview topics. 104, 226, 102, 98, 543 and 236 are all frequent, and they're short enough that interviewers expect clean code *and* a clear explanation.
- **Say the Contract Sentence first:** "Let `height(node)` return the height of the subtree; the diameter through a node is left height plus right height." That one sentence shows you're reasoning, not reciting.
- **Complexity:** O(n) time; O(h) space for recursion (O(log n) balanced, O(n) for a chain). Mention that a very deep chain could exceed Python's recursion limit (~1000), and that BFS/iterative versions avoid it.
- **Follow-ups to expect:** "do it iteratively" (use an explicit stack or the BFS loop), "what if it's a BST?" (use ordering to prune, e.g. LCA in a BST walks down by comparing values).

---

## Self-check questions

1. What's the base case for almost every tree function, and how do you choose its return value?
<details><summary>Answer</summary>

`node is None` (the empty tree). It returns the answer for an empty problem: 0 for depth/size/sum, True for "valid/balanced", False for "exists", None for "which node".
</details>

2. Write the Contract Sentence for Maximum Depth.
<details><summary>Answer</summary>

`depth(node)` = the number of nodes on the longest downward path starting at `node` (0 for an empty tree).
</details>

3. In Path Sum, why does `[1,2]` with `targetSum = 1` return False, and what bug would make it True?
<details><summary>Answer</summary>

The only root-to-leaf path is 1 → 2 (sum 3). Node 1 isn't a leaf because it has a left child. Treating the missing right child (`None`) as "the path ended" would wrongly count the path [1].
</details>

4. In Sum Root to Leaf, what is the context parameter, and why is it legitimately a parameter (not an accumulated answer)?
<details><summary>Answer</summary>

`prefix`, the number spelled by the path above the node. It changes what the subtree's answer is (every number below starts with those digits), so the subtree's answer genuinely depends on it. That passes the "does the future depend on it?" test.
</details>

5. Why does checking only parent-child pairs fail for Validate BST? Give the range for node 3 in `[5,4,6,null,null,3,7]`.
<details><summary>Answer</summary>

The BST rule applies to whole subtrees. Node 3 is in 5's right subtree and 6's left subtree, so its range is `(5, 6)`; 3 is outside it. The child-only check never compares 3 with 5.
</details>

6. In Diameter, what does `height` return, what does `best` record, and why are they different?
<details><summary>Answer</summary>

`height` returns the longest downward path length (in nodes), which is what the parent needs to compute paths through itself. `best` records the longest path that bends at some node (`left + right` edges), which is the answer. A parent can't build its answer from children's diameters, only from their heights.
</details>

7. Why is `nonlocal best` needed?
<details><summary>Answer</summary>

The inner function assigns to `best`. Without `nonlocal`, Python treats it as a new local variable, and reading it first raises `UnboundLocalError`.
</details>

8. In Balanced Binary Tree, why is `-1` a safe "failed" signal?
<details><summary>Answer</summary>

A real height is always ≥ 0, so -1 can never be confused with a valid height. It's outside the valid set of the return value.
</details>

9. What makes level order different from the other problems here?
<details><summary>Answer</summary>

It's about levels, not subtrees, so it uses BFS with a level loop (`for _ in range(len(queue))`) instead of a recursive contract.
</details>

10. State the LCA function's contract.
<details><summary>Answer</summary>

`lca(node)` returns the LCA if both p and q are in the subtree, the one that's present if only one is, and None if neither. If both children report something, the current node is the LCA.
</details>

11. Draw the tree for `[1,2,3,null,5,null,4]`.
<details><summary>Answer</summary>

Root 1; children 2 (left) and 3 (right); 2 has no left child and a right child 5; 3 has no left child and a right child 4.
</details>

12. What's the space complexity of recursive DFS on a tree that's a single chain of n nodes, and what's the Python-specific risk?
<details><summary>Answer</summary>

O(n) for the recursion stack (the height is n). Python's default recursion limit (~1000) can be exceeded. Raise it with `sys.setrecursionlimit` or use an iterative version.
</details>

---

## Sources

- Problems: LeetCode 104, 226, 100, 112, 129, 98, 543, 110, 102, 199, 236, 124. Statements paraphrased; examples and constraints from long-standing problem pages (from my own knowledge, not re-fetched; 2026-10-09).
- Python docs: `nonlocal` (https://docs.python.org/3/reference/simple_stmts.html#the-nonlocal-statement), `collections.deque` (https://docs.python.org/3/library/collections.html#collections.deque), identity comparison with `is` (https://docs.python.org/3/reference/expressions.html#is-not).
- Verification (2026-10-09): every function was tested against brute-force references on 3,000 random trees with 0–9 nodes (including empty trees, single nodes and chains), plus the listed examples. Diameter was checked against all-pairs path lengths, and LCA against an ancestor walk. Your Sep 26 Sum Root to Leaf was re-run (1026, 25, 0 ✓). Traces were produced by running the code.
- Companions: lecture 002 (contracts, empty-problem table, call-tree traces), lecture 001 §8.2 (BFS level loop), lecture 003 (tracing).
