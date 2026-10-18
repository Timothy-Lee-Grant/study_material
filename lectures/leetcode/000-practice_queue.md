# Practice Queue

> **How to use this:** when you have time, pick **any one** problem from "Pick one now" (the top is the most useful, but any is fine). Solve it from a blank page, trace before submitting, then add a row to the **Attempt log** at the bottom. That's all you need to write. Claude reads the log, updates your notes, and re-ranks the list.
> **Times** are rough targets for a first attempt: Easy ≈ 20 min, Medium ≈ 30–45 min. Going over is fine; just write down how long it took.
> **Free problems only.** Each one links to its lecture section in case you get stuck (read it *after* a real attempt).
> Last re-ranked: 2026-10-17.

---

## Pick one now (top 12)

| # | Problem | Level | Lecture | ~Time | Why this one |
|---|---|---|---|---|---|
| 1 | [232 Implement Queue using Stacks](https://leetcode.com/problems/implement-queue-using-stacks/) | Easy | 013 §2.2 | 20 | The two-stack question you asked about. Write what each top stands for first |
| 2 | [20 Valid Parentheses](https://leetcode.com/problems/valid-parentheses/) | Easy | 013 §1 | 15 | Your "unresolved items" model. Test all three ways to fail |
| 3 | [1472 Design Browser History](https://leetcode.com/problems/design-browser-history/), **array version** | Medium | 012 §3.3 | 30 | Make `visit` O(1) with no deleting. You've done the two-stack version |
| 4 | [739 Daily Temperatures](https://leetcode.com/problems/daily-temperatures/) | Medium | 013 §6.1 | 30 | First monotonic stack. Name what `waiting` holds |
| 5 | [54 Spiral Matrix](https://leetcode.com/problems/spiral-matrix/) (redo) | Medium | 001 | 30 | Overdue redo. Comment every range; trace a 1×3 |
| 6 | [155 Min Stack](https://leetcode.com/problems/min-stack/) | Medium | 012 §3.1 | 20 | First design problem, small. Operations table first |
| 7 | [875 Koko Eating Bananas](https://leetcode.com/problems/koko-eating-bananas/) | Medium | 004 | 30 | Binary search on the answer: name the F…F T…T |
| 8 | [560 Subarray Sum Equals K](https://leetcode.com/problems/subarray-sum-equals-k/) | Medium | 005 | 30 | Prefix sums + `{0: 1}`. Look up before insert |
| 9 | [209 Minimum Size Subarray Sum](https://leetcode.com/problems/minimum-size-subarray-sum/) | Medium | 006 | 30 | Variable window: say why `left` moves |
| 10 | [198 House Robber](https://leetcode.com/problems/house-robber/) (redo, answer-up) | Medium | 002 | 30 | Write the contract sentence before any code |
| 11 | [380 Insert Delete GetRandom O(1)](https://leetcode.com/problems/insert-delete-getrandom-o1/) | Medium | 012 §3.4 | 40 | Two structures in sync. Trace "remove the last element" |
| 12 | [206 Reverse Linked List](https://leetcode.com/problems/reverse-linked-list/) | Easy | 010 | 20 | Save before overwrite. Draw the three pointers |

---

## Full list by topic

Status: ⬜ not tried · 🟡 tried, not passed · ✅ passed · 🔁 passed, redo later. Update the status here if you like, or just log it below and Claude will.

### Matrices and simulation (lecture 001)

| Problem | Level | Status |
|---|---|---|
| [54 Spiral Matrix](https://leetcode.com/problems/spiral-matrix/) | Medium | 🟡 redo |
| [59 Spiral Matrix II](https://leetcode.com/problems/spiral-matrix-ii/) | Medium | 🟡 traced and fixed, not submitted |
| [48 Rotate Image](https://leetcode.com/problems/rotate-image/) | Medium | ⬜ |
| [73 Set Matrix Zeroes](https://leetcode.com/problems/set-matrix-zeroes/) | Medium | ⬜ |

### Recursion and 1-D DP (lecture 002)

| Problem | Level | Status |
|---|---|---|
| [70 Climbing Stairs](https://leetcode.com/problems/climbing-stairs/) | Easy | ✅ |
| [746 Min Cost Climbing Stairs](https://leetcode.com/problems/min-cost-climbing-stairs/) | Easy | ⬜ |
| [198 House Robber](https://leetcode.com/problems/house-robber/) | Medium | 🟡 redo answer-up |
| [91 Decode Ways](https://leetcode.com/problems/decode-ways/) | Medium | 🟡 redo answer-up |
| [1143 Longest Common Subsequence](https://leetcode.com/problems/longest-common-subsequence/) | Medium | 🟡 redo answer-up |

### Binary search (lecture 004)

| Problem | Level | Status |
|---|---|---|
| [35 Search Insert Position](https://leetcode.com/problems/search-insert-position/) | Easy | ✅ |
| [704 Binary Search](https://leetcode.com/problems/binary-search/) | Easy | ⬜ |
| [875 Koko Eating Bananas](https://leetcode.com/problems/koko-eating-bananas/) | Medium | ⬜ |
| [33 Search in Rotated Sorted Array](https://leetcode.com/problems/search-in-rotated-sorted-array/) | Medium | ⬜ |

### Hash maps and prefix sums (lecture 005)

| Problem | Level | Status |
|---|---|---|
| [1 Two Sum](https://leetcode.com/problems/two-sum/) | Easy | ⬜ |
| [238 Product of Array Except Self](https://leetcode.com/problems/product-of-array-except-self/) | Medium | ⬜ |
| [560 Subarray Sum Equals K](https://leetcode.com/problems/subarray-sum-equals-k/) | Medium | ⬜ |
| [974 Subarray Sums Divisible by K](https://leetcode.com/problems/subarray-sums-divisible-by-k/) | Medium | ⬜ |

### Two pointers and sliding windows (lecture 006)

| Problem | Level | Status |
|---|---|---|
| [167 Two Sum II](https://leetcode.com/problems/two-sum-ii-input-array-is-sorted/) | Medium | ⬜ |
| [15 3Sum](https://leetcode.com/problems/3sum/) | Medium | 🟡 redo (July) |
| [209 Minimum Size Subarray Sum](https://leetcode.com/problems/minimum-size-subarray-sum/) | Medium | ⬜ |
| [3 Longest Substring Without Repeating Characters](https://leetcode.com/problems/longest-substring-without-repeating-characters/) | Medium | ⬜ |
| [424 Longest Repeating Character Replacement](https://leetcode.com/problems/longest-repeating-character-replacement/) | Medium | ⬜ |

### Binary trees (lecture 007)

| Problem | Level | Status |
|---|---|---|
| [104 Maximum Depth of Binary Tree](https://leetcode.com/problems/maximum-depth-of-binary-tree/) | Easy | ✅ |
| [112 Path Sum](https://leetcode.com/problems/path-sum/) | Easy | ⬜ |
| [543 Diameter of Binary Tree](https://leetcode.com/problems/diameter-of-binary-tree/) | Easy | ⬜ |
| [102 Binary Tree Level Order Traversal](https://leetcode.com/problems/binary-tree-level-order-traversal/) | Medium | ⬜ |
| [98 Validate Binary Search Tree](https://leetcode.com/problems/validate-binary-search-tree/) | Medium | ⬜ |
| [236 Lowest Common Ancestor of a Binary Tree](https://leetcode.com/problems/lowest-common-ancestor-of-a-binary-tree/) | Medium | ⬜ |

### Graphs (lecture 009)

| Problem | Level | Status |
|---|---|---|
| [200 Number of Islands](https://leetcode.com/problems/number-of-islands/) | Medium | ⬜ |
| [994 Rotting Oranges](https://leetcode.com/problems/rotting-oranges/) | Medium | 🟡 redo |
| [207 Course Schedule](https://leetcode.com/problems/course-schedule/) | Medium | 🟡 redo |
| [210 Course Schedule II](https://leetcode.com/problems/course-schedule-ii/) | Medium | ⬜ |
| [133 Clone Graph](https://leetcode.com/problems/clone-graph/) | Medium | ⬜ |
| [79 Word Search](https://leetcode.com/problems/word-search/) | Medium | 🟡 redo (needs un-choose) |

### Linked lists (lecture 010)

| Problem | Level | Status |
|---|---|---|
| [206 Reverse Linked List](https://leetcode.com/problems/reverse-linked-list/) | Easy | ⬜ |
| [21 Merge Two Sorted Lists](https://leetcode.com/problems/merge-two-sorted-lists/) | Easy | ⬜ |
| [141 Linked List Cycle](https://leetcode.com/problems/linked-list-cycle/) | Easy | ⬜ |
| [19 Remove Nth Node From End of List](https://leetcode.com/problems/remove-nth-node-from-end-of-list/) | Medium | ⬜ |
| [143 Reorder List](https://leetcode.com/problems/reorder-list/) | Medium | 🔁 (July) |

### Design problems (lecture 012)

Do these **blind**: read only the statement in §3, and write the operations table and your structures before looking at §4.

| Problem | Level | Status |
|---|---|---|
| [155 Min Stack](https://leetcode.com/problems/min-stack/) | Medium | ⬜ |
| [933 Number of Recent Calls](https://leetcode.com/problems/number-of-recent-calls/) | Easy | ⬜ |
| [1472 Design Browser History](https://leetcode.com/problems/design-browser-history/) | Medium | ✅ two stacks · ⬜ array version |
| [981 Time Based Key-Value Store](https://leetcode.com/problems/time-based-key-value-store/) | Medium | ⬜ |
| [380 Insert Delete GetRandom O(1)](https://leetcode.com/problems/insert-delete-getrandom-o1/) | Medium | ⬜ |
| [146 LRU Cache](https://leetcode.com/problems/lru-cache/) | Medium | 🔁 redo (August) |
| Rate limiter (012 §3.7), as a 45-min mock interview | — | ⬜ |

### Stacks (lecture 013)

| Problem | Level | Status |
|---|---|---|
| [20 Valid Parentheses](https://leetcode.com/problems/valid-parentheses/) | Easy | ⬜ |
| [232 Implement Queue using Stacks](https://leetcode.com/problems/implement-queue-using-stacks/) | Easy | ⬜ |
| [150 Evaluate Reverse Polish Notation](https://leetcode.com/problems/evaluate-reverse-polish-notation/) | Medium | ⬜ |
| [71 Simplify Path](https://leetcode.com/problems/simplify-path/) | Medium | ⬜ |
| [394 Decode String](https://leetcode.com/problems/decode-string/) | Medium | ⬜ |
| [739 Daily Temperatures](https://leetcode.com/problems/daily-temperatures/) | Medium | ⬜ |
| [496 Next Greater Element I](https://leetcode.com/problems/next-greater-element-i/) | Easy | ⬜ |
| [853 Car Fleet](https://leetcode.com/problems/car-fleet/) | Medium | ✅ |
| [84 Largest Rectangle in Histogram](https://leetcode.com/problems/largest-rectangle-in-histogram/) (stretch) | Hard | ⬜ |

---

## Attempt log

Add one row per attempt, newest at the bottom. Short is fine. Put your code in `examples.py` or `001_practice_medium.py` as usual, and say which file.

- **Result:** ✅ passed · 🟡 partly (say what was left) · ❌ stuck
- **Hard part:** one line on where you got stuck or slowed down (that's the most useful column)

| Date | Problem | Result | Time (min) | Traced before submit? | Hard part / notes | Code in |
|---|---|---|---|---|---|---|
| 2026-10-10 | 104 Maximum Depth | ✅ | — | yes | — | examples.py |
| 2026-10-10 | 853 Car Fleet | ✅ | — | no | — | examples.py |
| 2026-10-11 | 35 Search Insert Position | ✅ | — | — | — | examples.py |
| 2026-10-17 | 1472 Browser History (two stacks) | ✅ | — | hand-traced back() | why the queue needs a refill rule (answered in 013 §2) | message |
| | | | | | | |
