# Practice Queue

> **How to use this:** when you have time, pick **any one** problem from "Pick one now" (the top is the most useful, but any is fine). Solve it from a blank page, trace before submitting, then add a row to the **Attempt log** at the bottom. That's all you need to write. Claude reads the log, updates your notes, and re-ranks the list.
> **Times** are rough targets for a first attempt: Easy ≈ 20 min, Medium ≈ 30–45 min. Going over is fine; just write down how long it took.
> **Free problems only.** Each one links to its lecture section in case you get stuck (read it *after* a real attempt).
> Last re-ranked: 2026-10-18 (two-pointer / sliding-window ladder added).

---

## Pick one now (top 12)

Five of these are two-pointer / sliding-window problems (marked 🪟), since that's the area you asked to practise. The full window ladder is in the next section.

| # | Problem | Level | Lecture | ~Time | Why this one |
|---|---|---|---|---|---|
| 1 | 🪟 [643 Maximum Average Subarray I](https://leetcode.com/problems/maximum-average-subarray-i/) | Easy | 006 | 15 | The plainest fixed window: add the box entering, remove the box leaving |
| 2 | [232 Implement Queue using Stacks](https://leetcode.com/problems/implement-queue-using-stacks/) | Easy | 013 §2.2 | 20 | The two-stack question you asked about. Write what each top stands for first |
| 3 | 🪟 [125 Valid Palindrome](https://leetcode.com/problems/valid-palindrome/) | Easy | 006 | 15 | Inward pointers. Say what's ruled out after each move |
| 4 | [20 Valid Parentheses](https://leetcode.com/problems/valid-parentheses/) | Easy | 013 §1 | 15 | Your "unresolved items" model. Test all three ways to fail |
| 5 | 🪟 [26 Remove Duplicates from Sorted Array](https://leetcode.com/problems/remove-duplicates-from-sorted-array/) | Easy | 006 | 15 | Read/write pointers. Name what `nums[:write]` holds |
| 6 | 🪟 [3 Longest Substring Without Repeating Characters](https://leetcode.com/problems/longest-substring-without-repeating-characters/) | Medium | 006 | 35 | Variable window, longest. Write the "window is valid when…" sentence first |
| 7 | [1472 Design Browser History](https://leetcode.com/problems/design-browser-history/), **array version** | Medium | 012 §3.3 | 30 | Make `visit` O(1) with no deleting. You've done the two-stack version |
| 8 | 🪟 [11 Container With Most Water](https://leetcode.com/problems/container-with-most-water/) | Medium | 006 | 30 | Inward pointers where the "ruled out because…" sentence is the whole solution |
| 9 | [739 Daily Temperatures](https://leetcode.com/problems/daily-temperatures/) | Medium | 013 §6.1 | 30 | First monotonic stack. Name what `waiting` holds |
| 10 | [875 Koko Eating Bananas](https://leetcode.com/problems/koko-eating-bananas/) (finish it) | Medium | 004 | 25 | Your attempt is in `examples.py`; see its log row for a failing input to start from |
| 11 | [54 Spiral Matrix](https://leetcode.com/problems/spiral-matrix/) (redo) | Medium | 001 | 30 | Overdue redo. Comment every range; trace a 1×3 |
| 12 | [155 Min Stack](https://leetcode.com/problems/min-stack/) | Medium | 012 §3.1 | 20 | First design problem, small. Operations table first |

---|---|---|---|---|---|
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

## Focus: two pointers and sliding windows (added 2026-10-18)

Work down each group; you don't need to finish one group before starting the next. Lecture 006 has the templates.

**Before writing any loop, write three comment lines:**
1. What each pointer stands for, as a box or a cut (lecture 008): is the window `s[l:r]` (cuts, `r - l` items) or `l … r` (boxes, `r - l + 1` items)?
2. The window's rule: "the window is valid when …" (variable windows), or "it always holds exactly k items" (fixed windows).
3. For inward pointers: after each move, the sentence "this is ruled out because …".

**Fixed-window bounds, derived once:** a window of length `k` starting at box `start` covers boxes `start … start + k - 1`. The last box must exist: `start + k - 1 <= n - 1`, so `start <= n - k`. That gives `n - k + 1` windows and `for start in range(n - k + 1)`. For `k = 10` that's the same set as `while start + 9 < n`.

**Tracing windows:** don't trace the full example string. Make your own tiny input (length k + 2 or so, with k shrunk to 2 or 3 if the problem allows it), and draw the window as brackets: `a[bc]d`. One row per move.

### A. Inward pointers (opposite ends)

| Problem | Level | Status |
|---|---|---|
| [125 Valid Palindrome](https://leetcode.com/problems/valid-palindrome/) | Easy | ⬜ |
| [977 Squares of a Sorted Array](https://leetcode.com/problems/squares-of-a-sorted-array/) | Easy | ⬜ |
| [167 Two Sum II](https://leetcode.com/problems/two-sum-ii-input-array-is-sorted/) | Medium | ⬜ |
| [11 Container With Most Water](https://leetcode.com/problems/container-with-most-water/) | Medium | ⬜ |
| [881 Boats to Save People](https://leetcode.com/problems/boats-to-save-people/) | Medium | ⬜ |
| [15 3Sum](https://leetcode.com/problems/3sum/) | Medium | 🟡 redo (July) |

### B. Read/write pointers (same direction)

| Problem | Level | Status |
|---|---|---|
| [26 Remove Duplicates from Sorted Array](https://leetcode.com/problems/remove-duplicates-from-sorted-array/) | Easy | ⬜ |
| [283 Move Zeroes](https://leetcode.com/problems/move-zeroes/) | Easy | ⬜ |
| [88 Merge Sorted Array](https://leetcode.com/problems/merge-sorted-array/) (fill from the back) | Easy | ⬜ |
| [80 Remove Duplicates from Sorted Array II](https://leetcode.com/problems/remove-duplicates-from-sorted-array-ii/) | Medium | ⬜ |

### C. Fixed-size windows

| Problem | Level | Status |
|---|---|---|
| [643 Maximum Average Subarray I](https://leetcode.com/problems/maximum-average-subarray-i/) | Easy | ⬜ |
| [187 Repeated DNA Sequences](https://leetcode.com/problems/repeated-dna-sequences/) | Medium | ✅ 2026-10-18 |
| [1456 Maximum Number of Vowels in a Substring of Given Length](https://leetcode.com/problems/maximum-number-of-vowels-in-a-substring-of-given-length/) | Medium | ⬜ |
| [567 Permutation in String](https://leetcode.com/problems/permutation-in-string/) | Medium | ⬜ |
| [438 Find All Anagrams in a String](https://leetcode.com/problems/find-all-anagrams-in-a-string/) | Medium | ⬜ |

### D. Variable windows: longest valid window

| Problem | Level | Status |
|---|---|---|
| [3 Longest Substring Without Repeating Characters](https://leetcode.com/problems/longest-substring-without-repeating-characters/) | Medium | ⬜ |
| [1004 Max Consecutive Ones III](https://leetcode.com/problems/max-consecutive-ones-iii/) | Medium | ⬜ |
| [904 Fruit Into Baskets](https://leetcode.com/problems/fruit-into-baskets/) | Medium | ⬜ |
| [424 Longest Repeating Character Replacement](https://leetcode.com/problems/longest-repeating-character-replacement/) | Medium | ⬜ |

### E. Variable windows: shortest valid window, and counting windows

| Problem | Level | Status |
|---|---|---|
| [209 Minimum Size Subarray Sum](https://leetcode.com/problems/minimum-size-subarray-sum/) | Medium | ⬜ |
| [713 Subarray Product Less Than K](https://leetcode.com/problems/subarray-product-less-than-k/) (count windows: each `r` adds `r - l + 1`) | Medium | ⬜ |
| [76 Minimum Window Substring](https://leetcode.com/problems/minimum-window-substring/) (stretch) | Hard | ⬜ |
| [239 Sliding Window Maximum](https://leetcode.com/problems/sliding-window-maximum/) (stretch; uses lecture 013's monotonic idea with a deque) | Hard | ⬜ |

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
| [875 Koko Eating Bananas](https://leetcode.com/problems/koko-eating-bananas/) | Medium | 🟡 unfinished |
| [33 Search in Rotated Sorted Array](https://leetcode.com/problems/search-in-rotated-sorted-array/) | Medium | ⬜ |

### Hash maps and prefix sums (lecture 005)

| Problem | Level | Status |
|---|---|---|
| [1 Two Sum](https://leetcode.com/problems/two-sum/) | Easy | ⬜ |
| [238 Product of Array Except Self](https://leetcode.com/problems/product-of-array-except-self/) | Medium | ⬜ |
| [560 Subarray Sum Equals K](https://leetcode.com/problems/subarray-sum-equals-k/) | Medium | ⬜ |
| [974 Subarray Sums Divisible by K](https://leetcode.com/problems/subarray-sums-divisible-by-k/) | Medium | ⬜ |

### Two pointers and sliding windows (lecture 006)

See **Focus: two pointers and sliding windows** above for the full ladder.

### Binary trees (lecture 007)

| Problem | Level | Status |
|---|---|---|
| [104 Maximum Depth of Binary Tree](https://leetcode.com/problems/maximum-depth-of-binary-tree/) | Easy | ✅ |
| [112 Path Sum](https://leetcode.com/problems/path-sum/) | Easy | ✅ |
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
| before 10-08 | 875 Koko Eating Bananas | 🟡 | — | — | Unfinished: the check function isn't written yet. Start here: with your branches, `piles = [3,6,7,11], h = 8` returns 11 (expected 4). When speed `mid` works, is `mid` ruled out? Also, is speed 0 in the valid set? | examples.py |
| 2026-10-08 | 112 Path Sum | ✅ | — | — | Correct (checked on 3,000 random trees). Leaf check before comparing the sum, as your comment says | examples.py |
| 2026-10-18 | 187 Repeated DNA Sequences | ✅ (after ChatGPT's idea) | long | started a trace; it got too big | First try stuck on the idea. Then `i+10 < len(s)` missed the last window; `i+9 < len(s)` passed. Your reasoning ("the last box I index is i+9") was right | examples.py |
| | | | | | | |
