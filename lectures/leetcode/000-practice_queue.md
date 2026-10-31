# Practice Queue

> **How to use this:** when you have time, pick **any one** problem from "Pick one now" (the top is the most useful, but any is fine). Solve it from a blank page, trace before submitting, then add a row to the **Attempt log** at the bottom. That's all you need to write. Claude reads the log, updates your notes, and re-ranks the list.
> **Times** are rough targets for a first attempt: Easy ≈ 20 min, Medium ≈ 30–45 min. Going over is fine; just write down how long it took.
> **Free problems only.** Each one links to its lecture section in case you get stuck (read it *after* a real attempt).
> Last re-ranked: 2026-10-23 (after 21, 55).

---

## Pick one now (top 12)

Titles only, so you have to work out the technique yourself. Any order is fine. Two things to avoid looking at before an attempt:
- the collapsed **"Why these problems"** notes right below the table;
- the sections further down, which group problems by technique. Everything you need for an attempt is in this table.

| # | Problem | Level | ~Time |
|---|---|---|---|
| 1 | [26 Remove Duplicates from Sorted Array](https://leetcode.com/problems/remove-duplicates-from-sorted-array/) (finish) | Easy | 10 |
| 2 | [283 Move Zeroes](https://leetcode.com/problems/move-zeroes/) | Easy | 15 |
| 3 | [56 Merge Intervals](https://leetcode.com/problems/merge-intervals/) (redo) | Medium | 30 |
| 4 | [125 Valid Palindrome](https://leetcode.com/problems/valid-palindrome/) | Easy | 15 |
| 5 | [3 Longest Substring Without Repeating Characters](https://leetcode.com/problems/longest-substring-without-repeating-characters/) | Medium | 35 |
| 6 | [232 Implement Queue using Stacks](https://leetcode.com/problems/implement-queue-using-stacks/) | Easy | 20 |
| 7 | [435 Non-overlapping Intervals](https://leetcode.com/problems/non-overlapping-intervals/) | Medium | 30 |
| 8 | [20 Valid Parentheses](https://leetcode.com/problems/valid-parentheses/) | Easy | 15 |
| 9 | [1472 Design Browser History](https://leetcode.com/problems/design-browser-history/) (a different design from your first one) | Medium | 30 |
| 10 | [876 Middle of the Linked List](https://leetcode.com/problems/middle-of-the-linked-list/) | Easy | 15 |
| 11 | [875 Koko Eating Bananas](https://leetcode.com/problems/koko-eating-bananas/) (finish it) | Medium | 25 |
| 12 | [54 Spiral Matrix](https://leetcode.com/problems/spiral-matrix/) (redo) | Medium | 30 |

<details><summary>Why these problems (open after attempting)</summary>

| # | Problem | Group | Lecture | Why this one |
|---|---|---|---|---|
| 1 | 26 Remove Duplicates from Sorted Array (finish) | two pointers / window | 006 / review 001 §4 | Array part right, return value wrong; do the walk-through in attempt review 001 §4 first |
| 2 | 283 Move Zeroes | two pointers / window | 006 | Reader/writer from a blank page; write what nums[:writer] holds first |
| 3 | 56 Merge Intervals (redo) | intervals | 015 §3 | July redo; the nested-interval case. Write the touching rule from the examples first |
| 4 | 125 Valid Palindrome | two pointers / window | 006 | Inward pointers; the 'ruled out because' sentence each move |
| 5 | 3 Longest Substring Without Repeating Characters | two pointers / window | 006 | First variable window: 'the window is valid when…' sentence first |
| 6 | 232 Implement Queue using Stacks | stacks / design | 013 §2.2 | The two-stack question you asked about; what each top stands for |
| 7 | 435 Non-overlapping Intervals | intervals / greedy | 015 §5 | Try to break 2–3 greedy choices with tiny inputs before choosing a sort key |
| 8 | 20 Valid Parentheses | stacks | 013 §1 | Unresolved items; test all three ways to fail |
| 9 | 1472 Design Browser History (a different design from your first one) | design | 012 §3.3 | Array + cursor + boundary: visit in O(1) without deleting |
| 10 | 876 Middle of the Linked List | linked lists | recap 2026-10-19 §1.4–1.5 | Derive the loop condition from 'where should fast stop?' instead of recalling it |
| 11 | 875 Koko Eating Bananas (finish it) | binary search | 004 | Your attempt is in examples.py; see its log row for a failing input |
| 12 | 54 Spiral Matrix (redo) | matrix / simulation | 001 | Overdue redo; comment every range; trace a 1×3 |

</details>

---

## Focus: two pointers and sliding windows (added 2026-10-18)

Work down each group; you don't need to finish one group before starting the next. Lecture 006 has the templates.

**Before writing any loop, write three comment lines:**
1. What each pointer stands for, as a box or a cut (lecture 008): is the window `s[l:r]` (cuts, `r - l` items) or `l … r` (boxes, `r - l + 1` items)?
2. The window's rule: "the window is valid when …" (variable windows), or "it always holds exactly k items" (fixed windows).
3. For inward pointers: after each move, the sentence "this is ruled out because …".

**Before you submit, two 1-minute checks (added 2026-10-18):**
- **The return line:** run example 1 through just the `return`. Does the value you return mean what the problem asks for?
- **Every counter you named:** for each line that changes it, ask "does this line match what the name says it counts?"

**Window facts card.** You've derived each of these yourself; reuse them instead of re-deriving each time (re-derive only if one feels wrong). A window of `k` boxes whose **last box is `i`**:

| Fact | Value | Why |
|---|---|---|
| its first box | `i - k + 1` | `k` boxes ending at `i`: `i - k + 1, …, i` |
| as a slice | `nums[i - k + 1 : i + 1]` | the cut after box `i` is `i + 1` |
| the box that just left when box `i` entered | `i - k` | one before the first box |
| the window is full (has `k` boxes) when | `i >= k - 1` | first full window ends at box `k - 1` |
| number of full windows in `n` boxes | `n - k + 1` | last boxes run `k - 1 … n - 1` |
| read/write: how many kept so far | `writer` | `nums[:writer]` is a slice of `writer` boxes |

**Fixed-window bounds, derived once:** a window of length `k` starting at box `start` covers boxes `start … start + k - 1`. The last box must exist: `start + k - 1 <= n - 1`, so `start <= n - k`. That gives `n - k + 1` windows and `for start in range(n - k + 1)`. For `k = 10` that's the same set as `while start + 9 < n`.

**Tracing windows:** don't trace the full example string. Make your own tiny input (length k + 2 or so, with k shrunk to 2 or 3 if the problem allows it), and draw the window as brackets: `a[bc]d`. One row per move.

### A. Inward pointers (opposite ends)

| Problem | Level | Status |
|---|---|---|
| [125 Valid Palindrome](https://leetcode.com/problems/valid-palindrome/) | Easy | ⬜ |
| [977 Squares of a Sorted Array](https://leetcode.com/problems/squares-of-a-sorted-array/) | Easy | ⬜ |
| [167 Two Sum II](https://leetcode.com/problems/two-sum-ii-input-array-is-sorted/) | Medium | ⬜ |
| [11 Container With Most Water](https://leetcode.com/problems/container-with-most-water/) | Medium | ✅ 2026-10-20 |
| [881 Boats to Save People](https://leetcode.com/problems/boats-to-save-people/) | Medium | ⬜ |
| [15 3Sum](https://leetcode.com/problems/3sum/) | Medium | 🟡 redo (July) |

### B. Read/write pointers (same direction)

| Problem | Level | Status |
|---|---|---|
| [26 Remove Duplicates from Sorted Array](https://leetcode.com/problems/remove-duplicates-from-sorted-array/) | Easy | 🟡 return value |
| [283 Move Zeroes](https://leetcode.com/problems/move-zeroes/) | Easy | ⬜ |
| [88 Merge Sorted Array](https://leetcode.com/problems/merge-sorted-array/) (fill from the back) | Easy | ⬜ |
| [80 Remove Duplicates from Sorted Array II](https://leetcode.com/problems/remove-duplicates-from-sorted-array-ii/) | Medium | ⬜ |

### C. Fixed-size windows

| Problem | Level | Status |
|---|---|---|
| [643 Maximum Average Subarray I](https://leetcode.com/problems/maximum-average-subarray-i/) | Easy | ✅ 2026-10-18 |
| [187 Repeated DNA Sequences](https://leetcode.com/problems/repeated-dna-sequences/) | Medium | ✅ 2026-10-18 |
| [1456 Maximum Number of Vowels in a Substring of Given Length](https://leetcode.com/problems/maximum-number-of-vowels-in-a-substring-of-given-length/) | Medium | ✅ 2026-10-20 |
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
| [21 Merge Two Sorted Lists](https://leetcode.com/problems/merge-two-sorted-lists/) | Easy | 🟡 redo with a trace table |
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
| [739 Daily Temperatures](https://leetcode.com/problems/daily-temperatures/) | Medium | ✅ 2026-10-20 |
| [496 Next Greater Element I](https://leetcode.com/problems/next-greater-element-i/) | Easy | ⬜ |
| [853 Car Fleet](https://leetcode.com/problems/car-fleet/) | Medium | ✅ |
| [84 Largest Rectangle in Histogram](https://leetcode.com/problems/largest-rectangle-in-histogram/) (stretch) | Hard | ⬜ |

### Intervals and greedy (lecture 015)

| Problem | Level | Status |
|---|---|---|
| [56 Merge Intervals](https://leetcode.com/problems/merge-intervals/) | Medium | 🟡 redo (July) |
| [57 Insert Interval](https://leetcode.com/problems/insert-interval/) | Medium | ⬜ |
| [435 Non-overlapping Intervals](https://leetcode.com/problems/non-overlapping-intervals/) | Medium | ⬜ |
| [452 Minimum Number of Arrows to Burst Balloons](https://leetcode.com/problems/minimum-number-of-arrows-to-burst-balloons/) | Medium | ⬜ |
| [986 Interval List Intersections](https://leetcode.com/problems/interval-list-intersections/) | Medium | ⬜ |
| [2406 Divide Intervals Into Minimum Number of Groups](https://leetcode.com/problems/divide-intervals-into-minimum-number-of-groups/) | Medium | ⬜ |
| [1094 Car Pooling](https://leetcode.com/problems/car-pooling/) | Medium | ⬜ |
| [55 Jump Game](https://leetcode.com/problems/jump-game/) | Medium | ✅ 2026-10-23 |
| [45 Jump Game II](https://leetcode.com/problems/jump-game-ii/) | Medium | ⬜ |
| [763 Partition Labels](https://leetcode.com/problems/partition-labels/) | Medium | ⬜ |
| [134 Gas Station](https://leetcode.com/problems/gas-station/) (stretch) | Medium | ⬜ |

### Simulation (lecture 018)

| Problem | Level | Status |
|---|---|---|
| [2073 Time Needed to Buy Tickets](https://leetcode.com/problems/time-needed-to-buy-tickets/) | Easy | ⬜ |
| [1041 Robot Bounded In Circle](https://leetcode.com/problems/robot-bounded-in-circle/) | Medium | ⬜ |
| [735 Asteroid Collision](https://leetcode.com/problems/asteroid-collision/) | Medium | ⬜ |
| [6 Zigzag Conversion](https://leetcode.com/problems/zigzag-conversion/) | Medium | ⬜ |
| [1823 Find the Winner of the Circular Game](https://leetcode.com/problems/find-the-winner-of-the-circular-game/) | Medium | ⬜ |
| [7 Reverse Integer](https://leetcode.com/problems/reverse-integer/) | Medium | 🟡 redo (July) |
| [957 Prison Cells After N Days](https://leetcode.com/problems/prison-cells-after-n-days/) | Medium | ⬜ |
| [1599 Maximum Profit of Operating a Centennial Wheel](https://leetcode.com/problems/maximum-profit-of-operating-a-centennial-wheel/) | Medium | ⬜ |
| [2391 Minimum Amount of Time to Collect Garbage](https://leetcode.com/problems/minimum-amount-of-time-to-collect-garbage/) | Medium | ⬜ |
| [68 Text Justification](https://leetcode.com/problems/text-justification/) (stretch) | Hard | ⬜ |

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
| 2026-10-18 | 112 Path Sum | ✅ | — | — | Correct (checked on 3,000 random trees). Leaf check before comparing the sum, as your comment says | examples.py |
| 2026-10-18 | 187 Repeated DNA Sequences | ✅ (after ChatGPT's idea) | long | started a trace; it got too big | First try stuck on the idea. Then `i+10 < len(s)` missed the last window; `i+9 < len(s)` passed. Your reasoning ("the last box I index is i+9") was right | examples.py |
| 2026-10-18 | 643 Maximum Average Subarray I | ✅ (checked on 3,000 random arrays) | — | reasoned with k = 2 | All three bounds right (`i < k`, `i == k-1`, `nums[i-k]`). Slow: "took way too long to reason through" → use the window facts card | examples.py |
| 2026-10-18 | 26 Remove Duplicates | 🟡 | — | — | The array part is always right. But `return k` returns the number of **duplicates** (`k` goes up in the duplicate branch), so `[1,1,2]` returns 1, expected 2. Example 2 passes only by coincidence (5 duplicates, 5 unique values). What does `nums[:writer]` hold, and how many boxes is that? | examples.py |
| 2026-10-20 | 11 Container With Most Water | ✅ | — | yes (2 inputs) | Seen before. Correct (checked on 3,000 random inputs). Your "why move the lower wall" comment stops mid-sentence; finish it as a "ruled out because…" sentence | examples.py |
| 2026-10-20 | 1456 Maximum Number of Vowels | ✅ | — | yes | Logic correct, but the version in `examples.py` has no `i += 1` (it would loop forever), so it isn't the version you submitted | examples.py |
| 2026-10-20 | 739 Daily Temperatures | ✅ | — | yes | Solved **without reading lecture 013**: stack of unresolved days, the decreasing shape, and the equal-temperature case all derived; caught the index-vs-distance bug while tracing, before submitting. The code is right but the trace slipped at day 6 (see notes in chat) | examples.py |
| 2026-10-21 | 21 Merge Two Sorted Lists | ❌ | — | couldn't (no linked-list trace format) | `tail` never moves (no `tail = tail.next`), so each step replaces `dummy.next`; returns `4`. See this week's recap, Entry 1 §1.2–1.3 | examples.py |
| 2026-10-23 | 55 Jump Game | ✅ (checked on 5,000 random inputs) | — | yes (2 inputs) | Caught `nums[i]` → `nums[i] + i` during the walk-through. "No way I'd come up with the trick": see recap §1.7 | examples.py |
| 2026-10-31 | Birthday Chocolate (HackerRank, spaced revisit) | ❌ stuck ~90 min | 90 | — | Box-vs-cut mix in the sliding window: `i` (a box) vs `stop - start` (cuts); `i - m` (box that leaves) vs `i - m + 1` (first box that stays). See attempt review 002 | message |
| | | | | | | |
