# Weekly Recap: Week of 2026-10-19 (Mon) → 2026-10-25 (Sun)

> **What this is:** a running document for this week. Each time you explain a concept back to me, I add what you're still missing, any misconceptions, or extra depth you asked for. **Your earlier lectures stay untouched.** Read this at the end of the week.
> **Rules I follow when adding here:** only add what your explanation shows you need. If a topic came through solid, it gets one line saying so. Every example problem includes the full problem (paraphrased). No firmware analogies. Every claim about code was checked by running it.
> **Entries this week:** 1

---

## Contents

- [Entry 1 (Oct 23): Linked lists (from your notes while working through lecture 010)](#entry-1-oct-23-linked-lists-from-your-notes-while-working-through-lecture-010)
  - [1.1 `current` vs `prev.next` in Remove Elements](#11-current-vs-prevnext-in-remove-elements)
  - [1.2 Merge Two Sorted Lists: your Oct 21 attempt, and the "both empty" case](#12-merge-two-sorted-lists-your-oct-21-attempt-and-the-both-empty-case)
  - [1.3 How to walk through a linked-list problem](#13-how-to-walk-through-a-linked-list-problem)
  - [1.4 What "the middle" means (arrays and lists)](#14-what-the-middle-means-arrays-and-lists)
  - [1.5 Finding the middle with fast/slow, derived on the spot](#15-finding-the-middle-with-fastslow-derived-on-the-spot)
  - [1.6 Remove Nth From End: your worry about `fast` being `None`](#16-remove-nth-from-end-your-worry-about-fast-being-none)
  - [1.7 Jump Game: "there would have been no way for me to come up with this"](#17-jump-game-there-would-have-been-no-way-for-me-to-come-up-with-this)
  - [1.8 Problems to try](#18-problems-to-try)

---

## Entry 1 (Oct 23): Linked lists (from your notes while working through lecture 010)

### What came through solid (no action needed)

- **Reverse Linked List:** correct.
- **What `tail` means in the merge:** "tail just indicates the last element which is in the sorted list," and each step changes what `tail` points to. That's exactly the right name.
- **Seeing that the middle is a real gap**, and connecting it to binary search's `mid` on your own. Noticing a confusion you didn't know you had is the step that lets you fix it. The rest of this entry is mostly about that.

### 1.1 `current` vs `prev.next` in Remove Elements

**The problem (203, paraphrased):** remove every node whose value equals `val` and return the new head. Example: `1→2→6→3→4→5→6`, `val = 6` → `1→2→3→4→5`; `7→7→7→7`, `val = 7` → empty.

Whether your `current` version is the same as the lecture's `prev` version depends on **one question: which node is your pointer standing on when you make the decision?**

| Your pointer stands on… | You check | Can you remove the node you're checking? |
|---|---|---|
| the node **before** the candidate (the lecture's `prev`) | `current.next.val == val` | **yes**: `current.next = current.next.next` |
| the **candidate itself** | `current.val == val` | **not by itself**: in a singly linked list you can't get back to the node before it, and that's the node whose `.next` must change. You'd need a second pointer to the previous node |

So if your `current` checked `current.next.val`, it's the lecture's `prev` with a different name, and it's the same algorithm. If it checked `current.val`, it needed a separate `prev` as well. Either can be correct. The name `prev` is just a reminder of where the pointer stands.

Two things to check in your version, whichever way it went:
1. **After deleting, does the pointer stay put?** The node that slid into the gap hasn't been checked yet. `7→7→7→7` catches this: moving after a delete skips every other 7.
2. **Does it handle deleting the head?** Without a dummy node before the head, the head needs its own code path.

If you paste your version into `examples.py`, I'll check it against these.

### 1.2 Merge Two Sorted Lists: your Oct 21 attempt, and the "both empty" case

**The problem (21, paraphrased):** merge two sorted linked lists into one sorted list by relinking their nodes, and return its head. Example: `1→2→4` and `1→3→4` → `1→1→2→3→4→4`.

**Why your Oct 21 version failed:** `tail` never moves. There's no `tail = tail.next` after attaching a node, so `tail` stays on `dummy` forever, and each step **replaces** `dummy.next` instead of adding after the last node. Running it on the example returns just `4`.

Here's what a walk-through shows (from running it). The column that gives it away is "`tail` is on":

| step | node attached | `dummy.next` is now | `list1` | `list2` | `tail` is on |
|---|---|---|---|---|---|
| 1 | list2's `1` | list2's `1` | `1→2→4` | `3→4` | **dummy** |
| 2 | list1's `1` | list1's `1` (replaced!) | `2→4` | `3→4` | **dummy** |
| 3 | `2` | `2` (replaced) | `4` | `3→4` | **dummy** |
| 4 | `3` | `3` (replaced) | `4` | `4` | **dummy** |
| 5 | list2's `4` | list2's `4` (replaced) | `4` | `None` | **dummy** |
| after | list1's `4` | list1's `4` | | | → returns `4` |

(Ties go to `list2` in your version because you used `<`; that's fine.)

The name check from attempt review 001 finds it without even tracing: **`tail` means "the last node of the merged list." List every line that changes `tail`: there are none.** So after the first attachment, `tail` can't still be the last node.

**Your question about the third case (`else: tail.next = None`).** You're right that it isn't needed. Here's why, step by step:

1. The loop stops as soon as **one** list is empty. The other one was non-empty when the loop checked it, and nothing after that changes it.
2. So after the loop, "both are empty" can only happen if they were **both empty from the start**.
3. In that case the loop never ran, nothing was attached, and `dummy.next` is still what `ListNode()` set it to: `None`.
4. So the answer is already `dummy.next = None`, and the third case sets something that's already `None`.

That's why the lecture writes it in one line: `tail.next = list1 if list1 else list2`. If both are `None`, it attaches `None`, which is harmless.

**About your first attempt (weaving the two lists into each other):** it's a valid idea, but every step has to save two `.next` pointers before overwriting them, which is where it got tangled. The `tail` version only ever writes **one** pointer per step (`tail.next`), so there's nothing to save. When a linked-list solution needs many saves per step, look for a version that builds a new chain at a `tail`.

### 1.3 How to walk through a linked-list problem

You wrote: *"I don't know how to do the walk-throughs on the linked list problems."* Lecture 003 §5.4 gives the picture (redraw the list each iteration). Here's a table format that's quicker to write, using the correct merge as the example.

**Columns:**
1. **step**
2. **decided part:** the result list read from `dummy` **up to `tail`**. Stop at `tail`: the node at `tail` still points into its old list, and anything after it isn't decided yet.
3. **one column per input pointer**, written as the list you'd read starting from that pointer (`2→4`).
4. **one column per "named" pointer** (`tail`), saying which node it's on.

**Per-row check:** does every named pointer still match its name? (`tail` = last node of the decided part.)

The correct merge on `1→2→4` and `1→3→4` (from running it; the lecture's version uses `<=`, so ties go to `list1`):

| step | decided part (`dummy` … `tail`) | `list1` | `list2` | `tail` is on |
|---|---|---|---|---|
| 0 | (empty) | `1→2→4` | `1→3→4` | dummy |
| 1 | `1` | `2→4` | `1→3→4` | list1's 1 ✓ |
| 2 | `1→1` | `2→4` | `3→4` | list2's 1 ✓ |
| 3 | `1→1→2` | `4` | `3→4` | 2 ✓ |
| 4 | `1→1→2→3` | `4` | `4` | 3 ✓ |
| 5 | `1→1→2→3→4` | `None` | `4` | list1's 4 ✓ |
| after | attach `list2` (`4`): `1→1→2→3→4→4` | | | |

**Tiny inputs for linked lists** (same idea as shrinking the window in review 001): one empty list; one node each; and the case your code treats specially (here, a tie). Three rows are usually enough to see a bug.

**At the end, ask the landing question:** "When the loop stops, which node is each pointer on?" Then check that the line after the loop is safe for that node.

### 1.4 What "the middle" means (arrays and lists)

You asked what `n // 2` actually **represents**: an index? a number of steps? You noticed that for 3 elements you want "the second element," that it's index 1, and that this felt like a coincidence. It isn't one, and here's why.

**Three things one number can mean, and why they're the same number:**

In a 0-indexed array (or list), for the box at index `i`:
- its **index** is `i`;
- the **number of boxes before it** is `i` (boxes `0 … i-1`: a slice `[0:i]`, count `i - 0 = i`);
- the **number of steps from the first box** to reach it is `i` (each step moves past one box).

All three are the same number, **because 0-indexing counts boxes before**. That's the reason index 1 is "the second element": one box comes before it. A linked list has no indexes, but it has the other two meanings. So in a list, think of `n // 2` as **"the number of nodes before the middle"** or **"steps from the head."**

**Now define "middle" positively:** a box with **the same number of boxes on each side.**

- **Odd `n`**, say `n = 2k + 1`: the box with `k` before it has `n - k - 1 = k` after it. It's the unique middle. Its index is `k`, and `n // 2 = (2k + 1) // 2 = k` ✓.
- **Even `n`**, say `n = 2k`: no box has equal sides (that would need `k` before and `k` after, which is `2k + 1` boxes). Two boxes come closest:
  - the **lower middle**: `k - 1` before, `k` after. Index `k - 1`.
  - the **upper middle**: `k` before, `k - 1` after. Index `k`.

So the formulas, in "boxes before" terms:

| `n` | middle(s) (index = boxes before) | `n // 2` (upper) | `(n - 1) // 2` (lower) |
|---|---|---|---|
| 1 | 0 | 0 | 0 |
| 2 | 0, 1 | 1 | 0 |
| 3 | 1 | 1 | 1 |
| 4 | 1, 2 | 2 | 1 |
| 5 | 2 | 2 | 2 |
| 6 | 2, 3 | 3 | 2 |

For odd `n` both formulas agree. For even `n`, **`n // 2` is the upper middle and `(n - 1) // 2` is the lower middle.**

**The same thing for any closed range `first … last`** (which is what binary search uses): the lower middle is `(first + last) // 2` and the upper middle is `(first + last + 1) // 2`. With `first = 0, last = n - 1`, these give `(n - 1) // 2` and `n // 2`, matching the table.

**Connection to binary search (lecture 004), which you made yourself:** there, the candidates are the closed range `lo … hi`, and `mid = (lo + hi) // 2` is the **lower** middle. You chose the lower one for a reason (your Oct 6 recall): it guarantees `mid < hi` whenever there are two or more candidates, so `hi = mid` always shrinks the range. The choice of middle comes from what the algorithm needs.

**Which middle a problem wants is a choice, so read it from the problem**, in "nodes before" terms:

| Problem | Wants | Nodes before it |
|---|---|---|
| 876 Middle of the Linked List | the **second** middle if even | `n // 2` |
| 2095 Delete the Middle Node | defines the middle as index `⌊n/2⌋` | `n // 2` (and you need the node **before** it: `n // 2 - 1`) |
| 234 Palindrome / 143 Reorder List | the **last node of the first half** | `(n - 1) // 2` |

### 1.5 Finding the middle with fast/slow, derived on the spot

You said you'd struggle to come up with `while fast.next and fast.next.next` in an interview. You don't have to remember it. Here's a way to derive it in about a minute.

**Step 1: write where each pointer is.** After `s` loop iterations, `slow` has made `s` steps, so it's on index `s` (s nodes before it). `fast` has made `2s` steps, so it's on index `2s`.

**Step 2: choose where `slow` should stop**, from the table in §1.4. Call it `m`.

**Step 3: so `fast` must stop at index `2m`.** Work that out for an odd and an even length:

| want | `n = 5` (`m = 2`): fast stops at | `n = 4`: fast stops at |
|---|---|---|
| upper middle (`m = n // 2`) | index 4: **the last node** | `m = 2`, index 4: **`None`** (past the end) |
| lower middle (`m = (n - 1) // 2`) | index 4: **the last node** | `m = 1`, index 2: **the second-to-last node** |

**Step 4: turn "where fast stops" into "when the loop continues."**
- Upper middle: stop when fast is the last node **or** `None`. Continue while it's neither: **`while fast and fast.next`**.
- Lower middle: stop when fast is the last node **or** the second-to-last. Continue while there are at least two nodes after it: **`while fast.next and fast.next.next`**.

(Checked by running both loops on lengths 1 through 8: the first lands on `n // 2` and the second on `(n - 1) // 2` every time.)

**The interview-safe alternative, with nothing to derive:** count the nodes in one pass, then walk `n // 2` (or `(n - 1) // 2`) steps from the head. It's two passes, still O(n) time and O(1) space, and it uses the "steps from head = nodes before" meaning directly. It's a perfectly good answer. Say "I could also do this in one pass with fast and slow pointers" as a follow-up.

```python
def middle_by_count(head, upper=True):
    n = 0
    node = head
    while node:                          # count the nodes
        n += 1
        node = node.next
    steps = n // 2 if upper else (n - 1) // 2    # nodes before the middle = steps from head
    node = head
    for _ in range(steps):
        node = node.next
    return node
```

### 1.6 Remove Nth From End: your worry about `fast` being `None`

**The problem (19, paraphrased):** remove the n-th node from the end and return the head. Example: `1→2→3→4→5`, `n = 2` → `1→2→3→5`; `1`, `n = 1` → empty. Constraint: `1 <= n <= length`.

Your worry was: after the first loop moves `fast` forward `n` times, `fast` might be `None`, and then `while fast.next` would crash. **That's a real concern, and whether it happens depends on where `fast` starts.** The lecture's version starts at `dummy`, which is why it's safe.

**Number the positions:** `dummy` is position 0, the real nodes are positions `1 … L` (where `L` is the length), and `None` is position `L + 1`.

| `fast` starts at | after `n` steps it's at | valid set of that, using `1 <= n <= L` | `None` possible? |
|---|---|---|---|
| `dummy` (position 0) | position `n` | `1 … L`: always a real node | **no**, so `fast.next` is safe |
| `head` (position 1) | position `n + 1` | `2 … L + 1` | **yes**, when `n = L` (removing the head). From running it: on `1→2→3` with `n = 3`, `fast` ends as `None` |

So starting at the dummy fixes two things at once: the head can be removed, and `fast` never runs off the end.

**Why the second loop is `while fast.next`:** the node to remove is at position `L - n + 1`, so `slow` must stop at position `L - n` (the node before it). `slow` is `n` positions behind `fast`, so `fast` must stop at position `L`: the **last** node. "Stop on the last node" is `while fast.next` (lecture 010 §1).

**The habit your hesitation points to (and it was a good hesitation):** after each loop, write the **valid set** of where each pointer can be, using the constraints. Then check that the next line is safe for every value in that set. That's lecture 008's "name → valid set" applied to pointers.

### 1.7 Jump Game: "there would have been no way for me to come up with this"

(Not linked lists, but it's from this week.) Your Oct 23 solution is correct: it matched a brute force on 5,000 random inputs. Your version stops early in two ways (`furthest >= len(nums) - 1` → `True`; `furthest == i` → stuck, `False`), and both are right.

About the feeling that the "trick" is impossible to find. There's a general move that produces it, and you've already used it several times:

1. **Brute force:** track the **set** of indices you can reach.
2. **Look at what shape that set always has.** Here it's always `0 … something`, with no gaps (lecture 015 §7 derives why).
3. **If a set is always one unbroken range, store only its end(s).** So the set becomes one number: `farthest`.

You've used step 3 before: Browser History's `last` (the valid pages are `0 … last`), binary search's `lo`/`hi` (the candidates are `lo … hi`), and every sliding window (the window is `l … r`). So when the brute force tracks a set, ask: **"is this set always a range?"** If yes, the "trick" is just keeping its ends.

### 1.8 Problems to try

| Problem | What it checks | Statement |
|---|---|---|
| 21 Merge Two Sorted Lists (redo) | the §1.3 trace table, before submitting | see §1.2 |
| 876 Middle of the Linked List | §1.4–1.5: derive the loop from "where should fast stop?" | return the middle node; the second middle if the length is even. `1→2→3→4→5` → node 3; `1→2→3→4→5→6` → node 4. 1 to 100 nodes |
| 2095 Delete the Middle Node of a Linked List | which middle, plus the node **before** it | delete the node at index `⌊n/2⌋` (0-indexed) and return the head. `1→3→4→7→1→2→6` → `1→3→4→1→2→6`; `1→2→3→4` → `1→2→4`; `2→1` → `2`; a single node → empty. 1 to 10⁵ nodes |
| 19 Remove Nth Node From End (redo) | start `fast` at `head` first, find the crash case with §1.6's table, then fix it | see §1.6 |
| 234 Palindrome Linked List | lower middle, then reverse the second half | return `True` if the values read the same forwards and backwards. `1→2→2→1` → `True`; `1→2` → `False`. 1 to 10⁵ nodes, values 0–9; follow-up: O(1) extra space |
