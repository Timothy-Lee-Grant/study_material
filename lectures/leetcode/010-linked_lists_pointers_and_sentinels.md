# Lecture 010: Linked Lists: Pointers, Landing Spots, Dummy Nodes and Doubly Linked Lists

> **For:** Timothy · **Date:** 2026-10-12
> **Prerequisites:** lecture 008 (indices and bounds: "what does each number stand for?"). Lecture 003 (tracing; §5.4 introduced box-and-arrow snapshots).
> **Why this topic:** it's next in Group 2 of the roadmap, and you asked for it specifically, including **doubly linked lists, why and when you need them, how to tell, and what a dummy node actually does.** Your history with linked lists:
> - **Reorder List (July):** you decomposed it correctly (find middle, reverse, merge), then stopped at *"I have no idea about how I would actually go about reversing a linked list."* A missing primitive, not a missing strategy.
> - **Rotate List (July):** the right plan (length, `k % length`, fast/slow), but the slow pointer **landed one node too late** and the code crashed when `k % length == 0`.
> - **LRU Cache (Aug):** correct after watching a video, but the insert-at-front code was pasted three times, and every access built a brand-new node.
>
> All three are about pointers: where they point, where they land, and what order you change them in. That's what this lecture is built around.
> **Format notes:** every problem includes the full statement (paraphrased), examples and constraints; every symbol is defined before it's used (your Oct 11 rule); no firmware analogies.
> **Verification:** every solution was tested against a plain Python-list reference on 3,000 random lists (including empty and single-node lists). The LRU Cache was checked against `OrderedDict` on 500 random sequences of 60 operations, including a forward-and-backward walk of the list after every sequence. Traces were produced by running the code.

---

## Core ideas (the answer key)

1. **A linked list is nodes joined by references.** Each node holds a value and `next`, a reference to the following node (or `None` at the end). You only ever hold a reference to the **head**. There's no `a[i]`; reaching the i-th node means walking `i` steps.
2. **Every pointer variable stands for one node** (or `None`). Before writing a loop, say which node each variable stands for, and where it must be when the loop ends (the **landing question**).
3. **`while cur:` ends with `cur` = `None` (past the last node). `while cur.next:` ends with `cur` = the last node.** Pick the condition from where you need to land.
4. **To delete or insert, you need the node *before* the spot,** because that's the node whose `next` changes.
5. **A dummy node is a fake node placed before the head.** It gives every real node a "node before," so deleting or inserting at the head needs no special case, and `dummy.next` is always the current head, even if the head changed.
6. **Rewiring rule: save before you overwrite.** Once you change `x.next`, the old `x.next` is gone unless you saved it first.
7. **Reverse = three named pointers** (`prev`, `cur`, `nxt`): save `nxt`, point `cur` backward, step both forward.
8. **Fast/slow pointers** (fast moves 2, slow moves 1) find the middle and detect cycles. A fast pointer `n` steps ahead finds the n-th node from the end.
9. **A doubly linked list adds `prev` to each node.** You need it when you must **remove a node you're holding a reference to, in O(1)**, because in a singly linked list you can't reach the node before it without walking from the head.
10. **Head and tail sentinels** in a doubly linked list mean every real node always has a real `prev` and `next`, so insert and remove are 4 assignments with no `None` checks. That's the core of LRU Cache: a dictionary to *find* a node in O(1), plus a doubly linked list to *move or remove* it in O(1).

---

## Table of Contents

- [0. What a linked list is, and what each name stands for](#0-what-a-linked-list-is-and-what-each-name-stands-for)
- [1. Walking a list: the landing question](#1-walking-a-list-the-landing-question)
- [2. Rewiring safely: save before you overwrite](#2-rewiring-safely-save-before-you-overwrite)
- [3. Reverse a linked list (206)](#3-reverse-a-linked-list-206)
- [4. Dummy nodes: what they are, what they fix, when to use one (203, 21)](#4-dummy-nodes-what-they-are-what-they-fix-when-to-use-one-203-21)
- [5. Fast and slow pointers (876, 141, 19)](#5-fast-and-slow-pointers-876-141-19)
- [6. Rotate List, your July attempt fixed (61)](#6-rotate-list-your-july-attempt-fixed-61)
- [7. Reorder List: composing the primitives (143)](#7-reorder-list-composing-the-primitives-143)
- [8. Doubly linked lists: why, when, and how to tell](#8-doubly-linked-lists-why-when-and-how-to-tell)
- [9. LRU Cache: a dictionary plus a doubly linked list (146)](#9-lru-cache-a-dictionary-plus-a-doubly-linked-list-146)
- [10. Tracing linked-list code](#10-tracing-linked-list-code)
- [11. Recognizing linked-list techniques](#11-recognizing-linked-list-techniques)
- [12. Practice ladder](#12-practice-ladder)
- [Common mistakes](#common-mistakes)
- [Interview relevance](#interview-relevance)
- [Self-check questions](#self-check-questions)
- [Sources](#sources)

---

## 0. What a linked list is, and what each name stands for

### 0.1 The node

```python
class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val      # the data
        self.next = next    # a reference to the next node, or None if this is the last node
```

A list `1 → 2 → 3` is three node objects:

```
head
 │
 ▼
[1|•]──►[2|•]──►[3|None]
```

**What each name stands for:**

| Name | Stands for | Can it be `None`? |
|---|---|---|
| `head` | the first node (the only one you're given) | yes: the empty list |
| `node.val` | that node's data | no |
| `node.next` | the node after `node` | yes: `node` is the last node |
| `cur` (and other loop variables) | **one specific node** at a time | yes, if the loop walks past the end |

A variable like `cur` doesn't *contain* a node. It's a **name pointing at** a node. `cur = cur.next` moves the name; it doesn't change the list. `cur.next = something` changes the list. **Moving a name is safe; changing a `.next` is surgery.** Keep those two apart in your head and in your traces.

### 0.2 Linked list vs array

| Operation | Array (Python list) | Singly linked list |
|---|---|---|
| Read the i-th item | O(1): `a[i]` | O(i): walk i steps |
| Insert/delete at the front | O(n): everything shifts | **O(1)** |
| Insert/delete after a node you hold | O(n) | **O(1)** |
| Delete a node you hold (need the node *before* it) | — | O(n) to find the previous node (O(1) with a **doubly** linked list, §8) |
| Know the length | O(1) | O(n): count it |

Interviews use linked lists mostly to test **pointer manipulation** without mistakes. Real code uses them where O(1) insert/remove at a known spot matters, which is exactly the LRU Cache case (§9).

### 0.3 Two helpers for testing locally

LeetCode builds the list for you. To practise offline, these two are enough:

```python
def build(vals):                 # [1, 2, 3] -> 1 -> 2 -> 3, returns the head
    dummy = ListNode()
    tail = dummy
    for v in vals:
        tail.next = ListNode(v)
        tail = tail.next
    return dummy.next

def to_list(head):               # 1 -> 2 -> 3 -> [1, 2, 3]
    out = []
    while head:
        out.append(head.val)
        head = head.next
    return out
```

(`build` already uses a dummy node; §4 explains why.)

---

## 1. Walking a list: the landing question

Most linked-list bugs are **landing bugs**: the loop stops one node too early or too late. That's the linked-list version of lecture 008's off-by-one. Answer it with the same tool: **name where the pointer must be when the loop ends, and choose the condition from that.**

### 1.1 The two basic conditions

| Loop | `cur` when the loop ends | Use it when you need… |
|---|---|---|
| `while cur:` → `cur = cur.next` | `None` (one past the last node) | to visit **every** node (count, sum, print) |
| `while cur.next:` → `cur = cur.next` | the **last** node | to stand on the last node (to attach something after it) |

`while cur.next` crashes on an empty list (`None.next`), so check `head is None` first.

### 1.2 Counting steps (lecture 008 §3, applied)

> Starting at `head` (node 0), after **k** moves of `cur = cur.next`, `cur` is on **node k**.

| Moves | Lands on |
|---|---|
| 0 | node 0 (the head) |
| 1 | node 1 |
| k | node k |
| `length - 1` | the last node |
| `length` | `None` |

So "go to the node **before** position p" is `p - 1` moves. Name it, then count: a `for _ in range(p - 1)` loop does exactly `p - 1` moves (the slice rule: `range(0, p-1)` has `p - 1` values).

### 1.3 The landing question, as a habit

Before every pointer loop, write one comment:

```python
# landing: after this loop, slow must be on <which node, and why>
```

Then check it on a 3-node example (lecture 008 §6: two points, the smallest and largest case, settle it).

---

## 2. Rewiring safely: save before you overwrite

When you change `x.next`, **the old `x.next` is gone**. If it was the only reference to the rest of the list, the rest of the list is lost.

```python
cur.next = prev          # cur now points backward…
cur = cur.next           # …so this moves BACKWARD, not forward: the rest of the list is unreachable
```

**The rule:** before overwriting a `.next`, save anything you'll still need into a **named** variable.

```python
nxt = cur.next           # 1. save the rest of the list
cur.next = prev          # 2. now it's safe to rewire
```

A second rule for multi-step rewiring (inserting into the middle, or a doubly linked list): **set the new node's own pointers first, then point the neighbours at it.** The new node's fields aren't part of the list yet, so changing them can't lose anything. Each section below shows the order explicitly.

---

## 3. Reverse a linked list (206)

**Problem (paraphrased).** Given the head of a singly linked list, reverse the list and return the new head.
Examples: `1→2→3→4→5` → `5→4→3→2→1`. `1→2` → `2→1`. Empty → empty.
Constraints: 0 to 5000 nodes.

This is the primitive that stopped your Reorder List in July. Derive it from names, not memory.

**Name the three pointers:**

| Name | Stands for |
|---|---|
| `prev` | the head of the **already reversed** part (starts as `None`: nothing reversed yet) |
| `cur` | the first node **not yet reversed** (starts as `head`) |
| `nxt` | the node after `cur`, saved before rewiring (§2) |

**Invariant (true at the top of each pass):** the nodes before `cur` form a reversed list whose head is `prev`; the nodes from `cur` onward are untouched.

**One pass:** save `nxt`, point `cur` backward at `prev`, then both names step forward.

```python
def reverseList(head):
    prev = None                  # reversed part: empty
    cur = head                   # untouched part starts here
    while cur:                   # landing: cur = None means everything is reversed
        nxt = cur.next           # 1. save the rest
        cur.next = prev          # 2. rewire: cur now points into the reversed part
        prev = cur               # 3. reversed part grows by cur
        cur = nxt                # 4. move to the rest
    return prev                  # prev is the head of the fully reversed list
```

Trace on `1→2→3` (from running it):

| pass | reversed part (`prev`) | untouched part (`cur`) |
|---|---|---|
| start | `None` | `1→2→3` |
| 1 | `1` | `2→3` |
| 2 | `2→1` | `3` |
| 3 | `3→2→1` | `None` → stop |

Return `prev`, not `cur`: by the landing question, `cur` ends at `None`. The 4-line loop body is worth knowing by heart. It's the most reused linked-list primitive.

---

## 4. Dummy nodes: what they are, what they fix, when to use one (203, 21)

### 4.1 The problem a dummy node solves

To remove a node, you change the `next` of the node **before** it (core idea 4). Every node has a node before it… **except the head.** So without a dummy, every delete/insert routine needs two branches:

```python
if the node to remove is the head:
    head = head.next             # special case: there's no "before"
else:
    prev.next = prev.next.next   # normal case
```

The two branches are where bugs live: forgetting the head case, or forgetting to return the new head.

**A dummy node is a fake node placed in front of the head:**

```
dummy ──► head ──► ... 
[0|•]──►[1|•]──►[2|•]──►[3|None]
```

Now **every real node, including the head, has a node before it.** One code path handles all cases. And at the end, `dummy.next` is the real head, **whatever happened to the original head** (deleted, replaced, or the list became empty).

### 4.2 When you need one: the test

> **Could the head change?** If yes, use a dummy node.

| Situation | Can the head change? | Dummy? |
|---|---|---|
| Delete nodes matching a condition (203) | yes: the head might match | **yes** |
| Remove the n-th node from the end (19) | yes: it might be the head | **yes** |
| Build a new list node by node (merge, partition, `build`) | the head doesn't exist yet | **yes**: append to `tail`, return `dummy.next` |
| Insert in sorted position | yes: it might go first | **yes** |
| Reverse a whole list (206) | yes, but the algorithm already tracks the new head (`prev`) | not needed |
| Find the middle, detect a cycle | no (read-only) | no |

The value stored in the dummy doesn't matter. It's never read. What matters is that it's a real object with a `.next`.

### 4.3 Remove Linked List Elements (203)

**Problem (paraphrased).** Remove every node whose value equals `val`, and return the new head.
Examples: `1→2→6→3→4→5→6`, `val = 6` → `1→2→3→4→5`. `7→7→7→7`, `val = 7` → empty. Empty → empty.
Constraints: 0 to 10⁴ nodes.

**Name:** `prev` = the last node that is definitely **kept**. We look at `prev.next` and decide.

```python
def removeElements(head, val):
    dummy = ListNode(0, head)        # every real node now has a node before it
    prev = dummy                     # last node known to be kept
    while prev.next:
        if prev.next.val == val:
            prev.next = prev.next.next   # unlink it; DON'T move prev (the new prev.next is unchecked)
        else:
            prev = prev.next             # keep it; move on
    return dummy.next                # the real head, even if the old head was deleted
```

`7→7→7→7` is the input that shows why the dummy matters: every node, including each successive head, is removed by the same line, and `dummy.next` ends as `None`.

Note the asymmetry: after deleting, `prev` **stays**, because the node that just slid into `prev.next` hasn't been checked yet. Moving `prev` there would skip it, and two 7s in a row would leave one behind.

### 4.4 Merge Two Sorted Lists (21): a dummy as the start of a list you're building

**Problem (paraphrased).** Merge two sorted linked lists into one sorted list by relinking their nodes, and return its head.
Examples: `1→2→4` and `1→3→4` → `1→1→2→3→4→4`. Empty and empty → empty. Empty and `0` → `0`.
Constraints: 0 to 50 nodes each; sorted non-decreasing.

**Names:** `dummy` is the fixed start of the merged list; `tail` is the **last node of the merged list so far** (we always attach after it).

```python
def mergeTwoLists(list1, list2):
    dummy = ListNode()               # the merged list starts here (fake)
    tail = dummy                     # last node of the merged list so far
    while list1 and list2:
        if list1.val <= list2.val:
            tail.next = list1        # attach the smaller front node
            list1 = list1.next
        else:
            tail.next = list2
            list2 = list2.next
        tail = tail.next             # tail moves onto the node just attached
    tail.next = list1 if list1 else list2    # tail: attach whatever is left (already sorted)
    return dummy.next
```

Without the dummy, the first attachment would need its own branch ("if the merged list is empty, set head"). The last line is the "closing step" kind of line your tracker watches for (`TAIL`). Forget it and the leftover nodes vanish.

---

## 5. Fast and slow pointers (876, 141, 19)

### 5.1 Middle of the Linked List (876)

**Problem (paraphrased).** Return the middle node. If there are two middles (even length), return the **second** one.
Examples: `1→2→3→4→5` → node 3 (returns `3→4→5`). `1→2→3→4→5→6` → node 4 (returns `4→5→6`).
Constraints: 1 to 100 nodes.

`fast` moves 2 per step, `slow` moves 1, so `slow` has always made half as many moves. When `fast` can't move 2 more, `slow` is in the middle.

```python
def middleNode(head):
    slow = fast = head
    while fast and fast.next:        # fast can still move 2
        slow = slow.next
        fast = fast.next.next
    return slow
```

**Landing check (two points):** length 5 (nodes 0–4): fast goes 0 → 2 → 4, stops (`fast.next` is `None`), slow is at node 2 ✓ (the middle). Length 6 (nodes 0–5): fast goes 0 → 2 → 4 → `None`, slow is at node 3 ✓ (the second middle). If you want the **first** middle for even lengths, use `while fast.next and fast.next.next` (§7 uses that).

### 5.2 Linked List Cycle (141)

**Problem (paraphrased).** Return `True` if following `next` pointers from the head ever revisits a node (the list has a cycle), otherwise `False`.
Examples: `3→2→0→-4` with `-4` pointing back to `2` → `True`. `1→2` with `2` pointing back to `1` → `True`. `1` with no cycle → `False`.
Constraints: 0 to 10⁴ nodes. Follow-up: O(1) extra memory.

```python
def hasCycle(head):
    slow = fast = head
    while fast and fast.next:
        slow = slow.next
        fast = fast.next.next
        if slow is fast:             # same node object: fast lapped slow inside a cycle
            return True
    return False                     # fast reached the end: no cycle
```

**Why they must meet if there's a cycle:** once both are inside the cycle, each step the gap from slow to fast (measured along the cycle) changes by exactly 1 (fast gains one node per step). A gap that shrinks by one per step must reach 0, so they can't jump over each other. Use `is` (same object), not `==`.

(The O(n)-memory alternative: walk once with a `set` of seen nodes. Fine to mention first; the two-pointer version is the follow-up answer.)

### 5.3 Remove Nth Node From End of List (19)

**Problem (paraphrased).** Remove the n-th node counted from the end, and return the head.
Examples: `1→2→3→4→5`, `n = 2` → `1→2→3→5`. `1`, `n = 1` → empty. `1→2`, `n = 1` → `1`.
Constraints: 1 to 30 nodes; `1 <= n <= length`.

**Name what you need:** the node **before** the one to remove, call it `slow`. The head might be removed (`1`, `n = 1`), so use a dummy (§4.2).

**Derive the gap:** if `fast` is `n` nodes ahead of `slow`, then when `fast` is on the **last** node, `slow` is `n` nodes before the last, which is exactly the node before the n-th from the end.

```python
def removeNthFromEnd(head, n):
    dummy = ListNode(0, head)
    fast = slow = dummy
    for _ in range(n):               # fast is now n nodes ahead of slow
        fast = fast.next
    while fast.next:                 # landing: fast on the LAST node
        fast = fast.next
        slow = slow.next
    slow.next = slow.next.next       # slow is the node before the one to remove
    return dummy.next
```

Trace on `1→2→3→4→5`, `n = 2` (from running it): after the `for`, `fast` is on node `2` and `slow` on `dummy`. Then `fast 3 / slow 1`, `fast 4 / slow 2`, `fast 5 / slow 3`. Fast is on the last node, so stop. `slow` is on `3`, so remove `3.next` (= `4`) → `1→2→3→5` ✓.

Notice how the two ideas combine: `while fast.next` (land on the last node, §1.1) plus a dummy (the head might go) plus a fixed gap.

---

## 6. Rotate List, your July attempt fixed (61)

**Problem (paraphrased).** Rotate the list to the right by `k` places: the last `k` nodes move to the front, in order.
Examples: `1→2→3→4→5`, `k = 2` → `4→5→1→2→3`. `0→1→2`, `k = 4` → `2→0→1` (4 rotations of length 3 = 1 rotation).
Constraints: 0 to 500 nodes; `0 <= k <= 2·10^9`.

Your plan was right: find the length, reduce `k` with `% length`, find where to cut. What broke (lecture 003 §6.2 traced it): the fast/slow loop used `while fast`, so `slow` landed **one node past** the node you needed, and `k % length == 0` and the empty list crashed.

**Derive it with names and counts instead:**

1. **Name** the node where the list gets cut: `new_tail` = the node that becomes the last node. Everything after it moves to the front.
2. **Which node is it?** The last `k` nodes move, so `new_tail` is node number `length - k - 1` (0-based). Check with two points: `k = 1` → node `length - 2`, the second-to-last ✓; `k = length - 1` → node 0, the head ✓.
3. **How many moves from the head?** Landing on node `j` takes `j` moves (§1.2), so `length - k - 1` moves.
4. **Edge cases first:** empty list → return `None`; `k % length == 0` → nothing changes.

```python
def rotateRight(head, k):
    if head is None:
        return None
    length = 1
    tail = head
    while tail.next:                     # landing: tail on the last node, length counted
        tail = tail.next
        length += 1
    k %= length
    if k == 0:
        return head                      # rotating by a multiple of length changes nothing
    new_tail = head
    for _ in range(length - k - 1):      # land on node (length - k - 1)
        new_tail = new_tail.next
    new_head = new_tail.next             # save before overwriting (§2)
    new_tail.next = None                 # cut
    tail.next = head                     # old tail connects to old head
    return new_head
```

The rewiring order follows §2: `new_head` is saved **before** `new_tail.next` is overwritten. Compare with your version: same idea, but the landing spot is now derived (`length - k - 1` moves) instead of produced by a loop condition you had to guess.

---

## 7. Reorder List: composing the primitives (143)

**Problem (paraphrased).** Given `L0 → L1 → … → Ln-1 → Ln`, reorder it in place to `L0 → Ln → L1 → Ln-1 → L2 → Ln-2 → …`. Change links, not values.
Examples: `1→2→3→4` → `1→4→2→3`. `1→2→3→4→5` → `1→5→2→4→3`.
Constraints: 1 to 5·10⁴ nodes.

Your July decomposition was exactly right, and now every piece is a primitive from this lecture:

1. **Find the end of the first half** (fast/slow, §5.1, first-middle version).
2. **Cut** after it, and **reverse** the second half (§3).
3. **Weave** the two halves together, saving each `next` before overwriting (§2).

```python
def reorderList(head):
    if head is None or head.next is None:
        return
    slow = fast = head
    while fast.next and fast.next.next:      # landing: slow = last node of the first half
        slow = slow.next
        fast = fast.next.next
    second = slow.next                        # save the second half
    slow.next = None                          # cut
    prev = None                               # reverse the second half (§3)
    while second:
        nxt = second.next
        second.next = prev
        prev = second
        second = nxt
    first, second = head, prev
    while second:                             # weave: the second half is never longer
        first_next, second_next = first.next, second.next   # save both before overwriting
        first.next = second
        second.next = first_next
        first, second = first_next, second_next
```

Check on `1→2→3→4→5`: the first half ends at `3` (`1→2→3`), the second half `4→5` reverses to `5→4`, and the weave gives `1→5→2→4→3` ✓ (verified by running it).

This is lecture 002 §11's point about harder problems: **most "hard" linked-list problems are 2–3 primitives composed.** If each primitive is automatic, the composition takes minutes.

---

## 8. Doubly linked lists: why, when, and how to tell

### 8.1 What changes

Each node gets a second reference, `prev`, to the node **before** it:

```python
class DNode:
    def __init__(self, key=0, val=0):
        self.key = key
        self.val = val
        self.prev = None
        self.next = None
```

```
None ◄──[A]◄──►[B]◄──►[C]──► None
```

That costs one extra reference per node and two extra assignments per change. It buys one thing.

### 8.2 The one thing it buys

> **Removing a node you are holding, in O(1).**

To remove node `B` from a list, you must change the `next` of the node **before** `B` (core idea 4).

| | Singly linked | Doubly linked |
|---|---|---|
| You hold a reference to `B`. How do you reach the node before it? | Walk from the head until `x.next is B`: **O(n)** | `B.prev`: **O(1)** |
| Remove `B` | O(n) | O(1) |
| Insert a node before `B` | O(n) | O(1) |
| Walk backward from the end | impossible (without reversing) | O(1) per step |

**Everything else** (walking forward, inserting after a node you hold, removing the node *after* one you hold) is O(1) in both. So a doubly linked list is only worth it when you must work **at or before a node you got from somewhere else**, not by walking to it.

### 8.3 How to tell you need one

Ask: **"Will I be handed a node (usually from a dictionary lookup) and need to remove it or move it, in O(1)?"**

| Signal in the problem | Why it points to a doubly linked list |
|---|---|
| "**O(1)** get / put / delete" plus an **order** to maintain (recency, frequency, insertion) | a dictionary finds the node in O(1), but only a doubly linked list can unlink it in O(1) |
| "**move to front**", "most recently used", "least recently used", "evict the oldest" | moving = remove + insert, and remove needs `prev` |
| "remove from **both ends**" (a deque) | removing the last node needs the second-to-last, which is `tail.prev` |
| a browser history with back/forward, a text-editor cursor | walk in both directions |

If the problem only ever walks forward from the head (reverse, merge, middle, cycle, k-th from end), a **singly** linked list is enough, and that's what LeetCode gives you. In Python, `collections.deque` is already a doubly-linked-list-like structure for "both ends" problems. You build your own doubly linked list mainly for **LRU/LFU-style design problems**, where you need to remove from the *middle* by reference.

### 8.4 Head and tail sentinels: the doubly-linked version of a dummy node

Removing node `B` means: `B.prev.next = B.next` and `B.next.prev = B.prev`. If `B` is the first node, `B.prev` is `None`, and `None.next` crashes. If it's the last, `B.next` is `None`. Without sentinels, remove and insert each need **four** cases (first, last, only, middle).

**Fix: two permanent fake nodes, one at each end.**

```
head ◄──► [A] ◄──► [B] ◄──► [C] ◄──► tail
(fake)                               (fake)
```

Now **every real node always has a real `prev` and a real `next`** (possibly a sentinel). So:

```python
def _remove(self, node):                 # unlink node; works for ANY real node
    node.prev.next = node.next
    node.next.prev = node.prev

def _add_front(self, node):              # insert right after head
    node.prev = self.head                # 1. the new node's own pointers first (§2)
    node.next = self.head.next
    self.head.next.prev = node           # 2. then the neighbours point at it
    self.head.next = node
```

Two assignments to remove, four to insert, **no `if` statements.** The empty list is just `head ◄──► tail`. The "first" real node is `head.next`, and the "last" is `tail.prev` (the least recently used one in LRU).

**Order check for `_add_front`:** the last two lines both touch `self.head.next`. Line 3 uses the **old** `head.next` (the old first node) and sets its `prev` to the new node. Line 4 then overwrites `head.next`. Swap them, and line 3 would set the new node's own `prev` to itself, breaking the list. Save-before-overwrite (§2) is what decides the order.

| | Singly linked list | Doubly linked list |
|---|---|---|
| Fake node | **dummy** before the head | **head and tail sentinels** at both ends |
| Problem it solves | the head has no "node before" | the first node has no `prev`, the last no `next` |
| Result | one code path for insert/delete at any position | remove/insert with no `None` checks at all |

---

## 9. LRU Cache: a dictionary plus a doubly linked list (146)

**Problem (paraphrased).** Design a class `LRUCache(capacity)` with:
- `get(key)`: return the value if the key exists, otherwise `-1`. A successful `get` makes that key the **most recently used**.
- `put(key, value)`: insert or update the key, making it the most recently used. If this makes the number of keys exceed `capacity`, evict the **least recently used** key.

Both must run in **O(1)** average time.
Example: capacity 2; `put(1,1)`, `put(2,2)`, `get(1)` → `1`, `put(3,3)` (evicts 2), `get(2)` → `-1`, `put(4,4)` (evicts 1), `get(1)` → `-1`, `get(3)` → `3`, `get(4)` → `4`.
Constraints: `1 <= capacity <= 3000`; up to 2·10⁵ calls.

### 9.1 Why these two structures (the design reasoning)

| Requirement | Which structure does it in O(1) |
|---|---|
| Find a key's entry | a **dictionary**: `key → node` |
| Know which key is least recently used | a list ordered by recency: the LRU is at one end (`tail.prev`) |
| Move an entry to the "most recent" end | remove it from where it is + insert at the front: needs **O(1) remove of a node you hold** → **doubly linked list** (§8.3) |
| Evict the LRU | remove `tail.prev` (doubly: O(1)) **and** delete its key from the dictionary, which is why each node stores its `key` |

Neither structure alone is enough. A dictionary has no order you can efficiently update; a linked list can't find a key without walking. **Together, each covers the other's weakness.** That's the general shape of design problems (roadmap, "Kinds of problems" §2).

**Single source of truth:** the dictionary and the list must always contain exactly the same keys. Every method that changes one changes the other **in the same method**. That's the consistency rule from your rate-limiter interview.

### 9.2 The implementation

```python
class DNode:
    def __init__(self, key=0, val=0):
        self.key = key                   # stored so eviction can delete it from the dictionary
        self.val = val
        self.prev = None
        self.next = None

class LRUCache:
    def __init__(self, capacity):
        self.capacity = capacity
        self.node_of = {}                # key -> its node (same keys as the list, always)
        self.head = DNode()              # sentinel: head.next = MOST recently used
        self.tail = DNode()              # sentinel: tail.prev = LEAST recently used
        self.head.next = self.tail
        self.tail.prev = self.head

    def _remove(self, node):
        node.prev.next = node.next
        node.next.prev = node.prev

    def _add_front(self, node):
        node.prev = self.head
        node.next = self.head.next
        self.head.next.prev = node
        self.head.next = node

    def get(self, key):
        if key not in self.node_of:
            return -1
        node = self.node_of[key]
        self._remove(node)               # move to front = remove + add_front
        self._add_front(node)
        return node.val

    def put(self, key, value):
        if key in self.node_of:          # update: change value, mark as most recent
            node = self.node_of[key]
            node.val = value
            self._remove(node)
            self._add_front(node)
            return
        node = DNode(key, value)         # new key: add to BOTH structures
        self.node_of[key] = node
        self._add_front(node)
        if len(self.node_of) > self.capacity:
            lru = self.tail.prev         # least recently used
            self._remove(lru)            # remove from BOTH structures
            del self.node_of[lru.key]
```

### 9.3 Compared with your August version

Your version was **correct** (0 mismatches in 300 random runs on Oct 4). Three differences, all about structure rather than correctness:

| Your version | This version | Why it matters |
|---|---|---|
| Insert-at-front code written out 3 times (in `get`, `put`-new, `put`-update) | one `_add_front` helper, called 3 times | Three copies are three chances for copy-paste drift (the same bug class as the 4th spiral side). In an interview, helpers also make the design readable |
| `get` created a **new node** every time and re-pointed the dictionary | moves the **existing** node | fewer objects; the dictionary entry never changes, so there's one less thing to keep in sync |
| Size tracked in a separate `self.size` counter | `len(self.node_of)` | one source of truth instead of a counter that must be updated in parallel |

---

## 10. Tracing linked-list code

From lecture 003 §5.4, adapted:

1. **Draw the list as boxes and arrows, with every pointer name written under the node it points at.**
2. **One snapshot per loop pass** (redraw, don't erase). Pointer rewiring destroys the old picture, so append-only matters even more here.
3. For the **first** pass only, zoom in to **one row per assignment**. That's where save-before-overwrite mistakes show up.
4. **Landing check:** write where each pointer should be at the end *before* tracing, then compare.

```
pass 0:   dummy → 1 → 2 → 3 → 4 → 5 → None
          ^slow       ^fast
```

Good trace inputs: **empty**, **one node**, **two nodes** (catches most landing bugs), the problem's example, and for deletions **"delete the head"** and **"delete everything."** For doubly linked lists, after each operation walk the list **forward from `head` and backward from `tail`**. If the two walks disagree, a `prev` pointer is wrong. (That's how the LRU code above was verified.)

---

## 11. Recognizing linked-list techniques

| Signal | Technique |
|---|---|
| "reverse" (all, part, in groups) | three pointers `prev / cur / nxt` (§3) |
| "remove / insert / the head might change" | dummy node (§4) |
| building a new list from pieces (merge, partition, sum) | dummy + `tail` (§4.4) |
| "middle", "palindrome list", "split in half" | fast/slow (§5.1) |
| "cycle", "loop" | fast/slow, `is` comparison (§5.2) |
| "n-th from the end" | gap of n + dummy (§5.3) |
| "rotate", "move the last k" | length, `% length`, cut at `length - k - 1` (§6) |
| "reorder", "interleave" | compose: middle + reverse + weave (§7) |
| "O(1) get/put with recency", "move to front", "evict least recent" | dictionary + doubly linked list with sentinels (§8, §9) |

Before coding, three comment lines (the same habit as lectures 004–009):

```python
# pointers: <name> = <which node it stands for>
# landing: after the loop, <name> must be on <which node>
# head can change? <yes -> dummy / no>
```

---

## 12. Practice ladder

| # | Problem | Teaches | Full problem |
|---|---|---|---|
| 1 | 206 Reverse Linked List | the core primitive; write it 3 times on 3 days | §3 |
| 2 | 876 Middle of the Linked List | fast/slow landing | §5.1 |
| 3 | 21 Merge Two Sorted Lists | dummy + tail | §4.4 |
| 4 | 203 Remove Linked List Elements | dummy; don't advance after a delete | §4.3 |
| 5 | 141 Linked List Cycle | fast/slow meeting | §5.2 |
| 6 | 19 Remove Nth Node From End | gap + dummy + landing | §5.3 |
| 7 | 61 Rotate List (redo from July) | derived landing, edge cases | §6 |
| 8 | 143 Reorder List (redo from July) | composition | §7 |
| 9 | 146 LRU Cache (redo from August) | doubly linked list + sentinels + dictionary | §9 |
| stretch | 2 Add Two Numbers, 160 Intersection of Two Linked Lists, 25 Reverse Nodes in k-Group | | |

Tags to watch in the tracker: `LANDING` (stopped one node off), `TAIL` (lost the leftover nodes, missing final attach) and a new one, `OVERWRITE` (changed a `.next` before saving what it pointed to).

---

## Common mistakes

| Mistake | Symptom | Fix |
|---|---|---|
| `while cur` when you needed the last node (or vice versa) | lands one node off (your Rotate List) | §1.1 table; write the landing comment first |
| Overwriting `cur.next` before saving it | the rest of the list is lost; the loop goes backward or ends early | `nxt = cur.next` first (§2) |
| Returning `cur` after reversing | returns `None` | `cur` lands on `None`; the new head is `prev` |
| No dummy when the head can be deleted | crash or the old head returned | dummy + `return dummy.next` (§4) |
| Advancing `prev` right after deleting `prev.next` | consecutive matches survive (`7→7`) | after a delete, stay; the new `prev.next` is unchecked |
| Forgetting `tail.next = list1 or list2` | leftover nodes disappear | closing step after the merge loop |
| `fast.next.next` without checking `fast.next` | `AttributeError` on even lengths | `while fast and fast.next` |
| `==` to compare nodes | may compare values, not identity | `is` |
| Doubly linked insert in the wrong order | the new node points to itself; the list breaks | new node's own pointers first, then the neighbours; the old `head.next` before `head.next` changes |
| Dictionary and list out of sync (LRU) | stale keys, wrong evictions | every method updates both; store `key` in the node |
| `k` not reduced with `% length` | timeout for huge `k` | `k %= length` (and handle `length = 0` first) |

---

## Interview relevance

- Reverse Linked List, Merge Two Sorted Lists, Linked List Cycle, Remove Nth From End and LRU Cache are some of the most commonly asked questions. LRU Cache in particular is a classic design question at large companies, including Microsoft.
- Interviewers watch for: **saying where each pointer lands**, handling **empty and one-node** inputs out loud, and **not losing the rest of the list**. Narrate the save-before-overwrite step.
- For LRU, the expected explanation is §9.1's table: "a dictionary for O(1) lookup, a doubly linked list for O(1) reordering and eviction, sentinels to avoid edge cases, and the node stores its key so eviction can update the dictionary." Follow-ups: thread safety (a lock around `get`/`put`), LFU (least *frequently* used: a frequency map of lists), using `OrderedDict` (acceptable to mention; usually they want the manual version).

---

## Self-check questions

1. After `k` moves of `cur = cur.next` from the head, which node is `cur` on? After `length` moves?
<details><summary>Answer</summary>

Node k (0-based). After `length` moves, `None`.
</details>

2. When do you use `while cur:` and when `while cur.next:`?
<details><summary>Answer</summary>

`while cur:` to visit every node (ends with `cur = None`). `while cur.next:` to stop on the last node (ends with `cur` = the last node). Check `head is None` first for the second.
</details>

3. What does "save before you overwrite" protect against? Give the line that saves in Reverse.
<details><summary>Answer</summary>

Losing the only reference to the rest of the list when you change a `.next`. In Reverse: `nxt = cur.next` before `cur.next = prev`.
</details>

4. In Reverse, what do `prev` and `cur` stand for, and why do you return `prev`?
<details><summary>Answer</summary>

`prev` = the head of the already-reversed part; `cur` = the first untouched node. The loop ends when `cur` is `None` (nothing left), so the full reversed list's head is `prev`.
</details>

5. What problem does a dummy node solve, and what's the one-question test for needing one?
<details><summary>Answer</summary>

The head has no "node before it", so deleting or inserting at the head would need a special case. A dummy gives every real node a predecessor, and `dummy.next` is always the current head. Test: "could the head change?"
</details>

6. In Remove Linked List Elements, why doesn't `prev` move after a deletion?
<details><summary>Answer</summary>

After unlinking, `prev.next` is a new, unchecked node. Moving `prev` would skip it, so consecutive matches would survive.
</details>

7. In Remove Nth From End, why does `fast` start `n` nodes ahead, and why do both start at the dummy?
<details><summary>Answer</summary>

When `fast` is on the last node, `slow` is n nodes before it, which is the node before the n-th from the end. Starting at the dummy lets `slow` be "the node before the head" when the head is the one removed.
</details>

8. Rotate List by `k` (after `k %= length`): which node becomes the new tail, and how many moves from the head reach it?
<details><summary>Answer</summary>

Node `length - k - 1` (0-based), reached in `length - k - 1` moves.
</details>

9. What exactly does a doubly linked list let you do that a singly linked list can't do efficiently?
<details><summary>Answer</summary>

Remove (or insert before) a node you're holding a reference to, in O(1), because `node.prev` gives the node before it. A singly linked list would have to walk from the head (O(n)).
</details>

10. How do you tell a problem needs a doubly linked list?
<details><summary>Answer</summary>

You'll be handed a node (typically from a dictionary) and must remove or move it in O(1): "O(1) get/put with an order", "move to front", "evict least recently used", "remove from both ends".
</details>

11. What do head and tail sentinels buy you in a doubly linked list?
<details><summary>Answer</summary>

Every real node always has a real `prev` and `next`, so remove is 2 assignments and insert is 4, with no `None` checks or special cases for first, last or only node.
</details>

12. In LRU Cache, why does each node store its `key`?
<details><summary>Answer</summary>

When evicting `tail.prev`, you must also delete that key from the dictionary, and the node is the only place you can get it from in O(1).
</details>

---

## Sources

- Problems: LeetCode 206, 203, 21, 876, 141, 19, 61, 143, 146 (stretch: 2, 160, 25). Statements paraphrased; examples and constraints from long-standing problem pages (from my own knowledge, not re-fetched; 2026-10-12).
- Python: `collections.OrderedDict` and `deque` (https://docs.python.org/3/library/collections.html); identity comparison with `is` (https://docs.python.org/3/reference/expressions.html#is-not).
- Floyd's cycle detection (tortoise and hare) is described in Knuth, *The Art of Computer Programming*, Vol. 2, §3.1, exercise 6.
- Your July Rotate List / Reorder List and August LRU Cache attempts (`001_practice_medium.py`) were re-run on 2026-10-04. The Rotate List trace is in lecture 003 §6.2.
- Verification (2026-10-12): every function was tested against a Python-list reference on 3,000 random lists (empty to 9 nodes), with cycle detection checked on lists with cycles inserted at random positions; LRU Cache was checked against `OrderedDict` on 500 random 60-operation sequences, with forward and backward walks of the list compared after each. Traces were produced by running the code.
