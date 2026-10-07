# Lecture 005: Hash Maps and Prefix Sums: Replacing the Inner Loop With a Lookup

> **For:** Timothy · **Date:** 2026-10-07
> **Prerequisites:** none required. Lecture 001 §4 (closed vs half-open) helps for §5. The trace "board" from lecture 003 §5.3 is used throughout.
> **Why this topic, why now:** it's the next step in the gradient plan (lecture 004 §0 ranked it second). It targets three things your tracker shows:
> - **Pattern recognition.** You solved Divisible Sum Pairs with an O(n²) double loop, labeled it "two pointers," and didn't look for the O(n + k) solution.
> - **Complexity checks.** You stated O(n²) correctly but didn't compare it with what's possible.
> - **Python dictionary fluency.** In July, Group Anagrams cost three attempts on `sorted()` returning an unhashable list and on `dict.values()`.
>
> It's also the most common interview family of all. Most "easy" and many "medium" array/string questions are this one idea.
> **Format notes (from your requests):** every example problem includes the full problem, paraphrased, with examples and constraints. Every step is derived, not stated as convention.
> **Verification:** every solution was tested against a brute-force version on 3,000 random inputs. Trace tables were produced by running the code.

---

## Core ideas (the answer key)

1. **Most hash-map solutions start as a double loop.** The inner loop asks a question about *earlier* elements ("is there a j before i such that…?"). A dictionary answers that question in O(1) instead of O(n).
2. **Name what the current element needs from the past** (`need = target - x`), then make that the **key** of the dictionary.
3. **Store exactly what the question asks for:** *whether it exists* → `set`; *how many* → count dict; *where* → index dict; *which ones* → list dict.
4. **Look up first, then insert the current element.** This guarantees `j < i` and stops an element from pairing with itself.
5. **Grouping problems need a canonical key:** one value that's identical for everything in the same group (`tuple(sorted(word))` for anagrams). Keys must be hashable: tuples, strings and ints, not lists.
6. **Prefix sums turn "sum of a range" into "difference of two named numbers":** with `prefix[i]` = sum of `nums[0:i]`, the sum of `nums[l:r]` is `prefix[r] - prefix[l]`.
7. **Prefix sums + a hash map** count subarrays with a property: for each end `r`, count earlier `l` with `prefix[l] == prefix[r] - k`.
8. **The `{0: 1}` initialization is the empty prefix**, `prefix[0] = 0`. It's the same idea as "the answer for the empty problem" from lecture 002.
9. **Remainders need `% k` to stay in their valid set** `0 … k-1`. `need = (k - r) % k`, not `k - r`, because when `r = 0` you need 0, not k.
10. **Complexity check:** n up to about 10⁴–10⁵ means O(n²) is too slow or borderline, which points to O(n) with a dictionary.

---

## Table of Contents

- [0. Your Divisible Sum Pairs, as the starting point](#0-your-divisible-sum-pairs-as-the-starting-point)
- [1. The map: five hash-map patterns](#1-the-map-five-hash-map-patterns)
- [2. The derivation procedure: from double loop to lookup](#2-the-derivation-procedure-from-double-loop-to-lookup)
- [3. Complement lookup (1, Divisible Sum Pairs, 217)](#3-complement-lookup-1-divisible-sum-pairs-217)
- [4. Counting and grouping (242, 49, 128)](#4-counting-and-grouping-242-49-128)
- [5. Prefix sums (definition, derived)](#5-prefix-sums-definition-derived)
- [6. Prefix sums + hash map (560, 974)](#6-prefix-sums--hash-map-560-974)
- [7. Prefix and suffix products (238)](#7-prefix-and-suffix-products-238)
- [8. Python dictionary fluency](#8-python-dictionary-fluency)
- [9. Tracing hash-map code](#9-tracing-hash-map-code)
- [10. Recognizing these problems](#10-recognizing-these-problems)
- [11. Practice ladder](#11-practice-ladder)
- [Common mistakes](#common-mistakes)
- [Interview relevance](#interview-relevance)
- [Self-check questions](#self-check-questions)
- [Sources](#sources)

---

## 0. Your Divisible Sum Pairs, as the starting point

**The problem (HackerRank, paraphrased).** Given an array `ar` of `n` integers and a positive integer `k`, count the pairs of indices `(i, j)` with `i < j` such that `ar[i] + ar[j]` is divisible by `k`.
Example: `n = 6, k = 3, ar = [1, 3, 2, 6, 1, 2]` → `5`. The pairs are values (1,2), (1,2), (3,6), (2,1), (1,2).
Constraints: `2 <= n <= 100`, `1 <= k <= 100`, `1 <= ar[i] <= 100`.

Your solution (Sep 26):

```python
matches = 0
for i in range(len(ar)):
    for j in range(i+1, len(ar)):
        if (ar[i] + ar[j]) % k == 0:
            matches += 1
return matches
```

It's **correct** (I ran it: 5). With `n <= 100`, O(n²) is fine for this problem, and you stated the complexity correctly. Two things to take from it:

1. You called it "two pointers." It isn't: two pointers move toward each other or along the array based on a comparison, usually over sorted data. This is a **double loop over all pairs**. The name matters because the right name suggests the right improvement.
2. If an interviewer asks "can you do better?", this lecture is the answer: **O(n + k)** with a dictionary, derived in §3.2.

---

## 1. The map: five hash-map patterns

| # | Pattern | The question the dictionary answers | Store | Classic problems |
|---|---|---|---|---|
| A | **Complement lookup** | "Has the partner I need appeared before?" | value → index (or count) | 1 Two Sum, Divisible Sum Pairs |
| B | **Frequency counting** | "How many of each?" | value → count | 242 Valid Anagram, 347 Top K Frequent |
| C | **Grouping by canonical key** | "Which items belong together?" | key → list of items | 49 Group Anagrams |
| D | **Membership set** | "Is x present?" (no extra data) | `set` | 217 Contains Duplicate, 128 Longest Consecutive Sequence |
| E | **Prefix sum + lookup** | "How many earlier prefixes make this range work?" | prefix value → count | 560 Subarray Sum Equals K, 974 Subarray Sums Divisible by K |

The single idea underneath all five: **pay O(n) memory to avoid re-scanning.** A dictionary lookup (`key in d`, `d[key]`) takes O(1) on average, so a question that used to take a full inner loop now takes one step.

---

## 2. The derivation procedure: from double loop to lookup

Use this every time. It's the same name → valid set → test shape that's been working for you.

**Step 1: Write the brute force double loop.** (In an interview, say it out loud and state its complexity.)

```python
for i in range(n):
    for j in range(i):          # every earlier element
        if <condition(nums[j], nums[i])>: ...
```

**Step 2: Read the inner loop as a question about the past.** "Among earlier elements, is there one / how many / which one satisfies the condition with `nums[i]`?"

**Step 3: Name what the current element needs.** Solve the condition for the earlier element:

| Condition | Solved for the earlier value | Name |
|---|---|---|
| `nums[j] + nums[i] == target` | `nums[j] == target - nums[i]` | `need = target - x` |
| `(nums[j] + nums[i]) % k == 0` | `nums[j] % k == (k - nums[i] % k) % k` | `need = (k - r) % k` |
| `prefix[i] - prefix[l] == k` | `prefix[l] == prefix[i] - k` | `need = prefix - k` |

**Step 4: Pick what to store, from the question's wording.**

| The question asks… | Store |
|---|---|
| does one exist? | `set` of keys |
| how many? | `dict` key → count |
| where is it? | `dict` key → index |
| which ones? | `dict` key → list |

**Step 5: Look up first, then insert the current element.** The dictionary must hold **only earlier elements** when you look up. That's the inner loop's `j < i`, now enforced by order. Inserting first would let an element pair with itself.

**Step 6: Complexity.** One pass, O(1) per step: O(n) time, O(n) space (or O(k) when keys are remainders).

---

## 3. Complement lookup (1, Divisible Sum Pairs, 217)

### 3.1 Two Sum (1)

**Problem (paraphrased).** Given an integer array `nums` and an integer `target`, return the indices of the two numbers that add up to `target`. Exactly one valid answer exists, and you may not use the same element twice. Return the indices in any order.
Examples: `[2,7,11,15], 9` → `[0,1]`. `[3,2,4], 6` → `[1,2]`. `[3,3], 6` → `[0,1]`.
Constraints: `2 <= len(nums) <= 10^4`; `-10^9 <= nums[i], target <= 10^9`; exactly one solution.

**Derivation:** condition `nums[j] + x == target` → `need = target - x`. The question is "where is it?", so store value → index. Look up, then insert.

```python
def twoSum(nums, target):
    seen = {}                          # value -> index, only for elements BEFORE i
    for i, x in enumerate(nums):
        need = target - x
        if need in seen:
            return [seen[need], i]
        seen[x] = i                    # insert AFTER the lookup
    return []
```

Why look-up-then-insert matters: `[3, 2, 4], target 6`. At `i = 0`, `x = 3`, `need = 3`. If you inserted first, `seen = {3: 0}` and you'd return `[0, 0]`, using 3 twice. Lookup first: `seen` is empty, no match, then insert. And `[3, 3]` still works: at `i = 1`, `need = 3` is found at index 0.

### 3.2 Divisible Sum Pairs in O(n + k)

**Step 3, done carefully.** Divisibility only depends on remainders, so name `r = x % k` (valid set `0 … k-1`). A pair works when the two remainders add up to a multiple of k:

- If `r = 1`, `k = 3`: you need a remainder of `2`, since `1 + 2 = 3`.
- If `r = 0`: you need a remainder of `0`, since `0 + 0 = 0`. **Not 3.**

`k - r` gives 2 for the first case ✓ and **3** for the second ✗. 3 isn't in the valid set `0 … k-1`. Fold it back in with `% k`:

```
need = (k - r) % k          # r = 1 → 2;  r = 0 → 3 % 3 = 0  ✓
```

That's the name → valid set → test method again: the valid set of remainders is `0 … k-1`, so the expression must land inside it.

**Step 4:** the question is "how many?", so store remainder → count.

```python
def divisibleSumPairs(n, k, ar):
    count_by_rem = {}                  # remainder -> how many EARLIER elements have it
    pairs = 0
    for x in ar:
        r = x % k
        need = (k - r) % k
        pairs += count_by_rem.get(need, 0)        # look up first
        count_by_rem[r] = count_by_rem.get(r, 0) + 1   # then insert
    return pairs
```

O(n) time, O(k) space. Trace on `[1, 3, 2, 6, 1, 2], k = 3` (expected 5), using the lecture 003 board:

| i | x | r | need | found (count of need) | pairs | board after (remainder → count) |
|---|---|---|---|---|---|---|
| 0 | 1 | 1 | 2 | 0 | 0 | {1: 1} |
| 1 | 3 | 0 | 0 | 0 | 0 | {0: 1, 1: 1} |
| 2 | 2 | 2 | 1 | 1 | 1 | {0: 1, 1: 1, 2: 1} |
| 3 | 6 | 0 | 0 | 1 | 2 | {0: 2, 1: 1, 2: 1} |
| 4 | 1 | 1 | 2 | 1 | 3 | {0: 2, 1: 2, 2: 1} |
| 5 | 2 | 2 | 1 | 2 | 5 | {0: 2, 1: 2, 2: 2} |

Final 5 ✓. CHECK column idea: at each row, `found` should equal the number of earlier elements whose remainder is `need`, which you can count on the original array.

### 3.3 Contains Duplicate (217): the set version

**Problem (paraphrased).** Return `True` if any value appears at least twice in `nums`, otherwise `False`.
Examples: `[1,2,3,1]` → `True`; `[1,2,3,4]` → `False`.
Constraints: `1 <= len(nums) <= 10^5`; `-10^9 <= nums[i] <= 10^9`.

The question is "have I seen this exact value before?": existence only, so a `set`.

```python
def containsDuplicate(nums):
    seen = set()
    for x in nums:
        if x in seen:                  # look up first
            return True
        seen.add(x)                    # then insert
    return False
```

---

## 4. Counting and grouping (242, 49, 128)

### 4.1 Valid Anagram (242): frequency counting

**Problem (paraphrased).** Given strings `s` and `t`, return `True` if `t` is a rearrangement of the letters of `s`.
Examples: `"anagram", "nagaram"` → `True`; `"rat", "car"` → `False`.
Constraints: lengths 1 to 5·10⁴; lowercase English letters.

Two strings are anagrams exactly when every letter appears the same number of times:

```python
from collections import Counter

def isAnagram(s, t):
    return Counter(s) == Counter(t)
```

`Counter(s)` is a dict of letter → count. Two Counters compare equal when they have the same counts. O(n). (Sorting both strings also works, at O(n log n).)

### 4.2 Group Anagrams (49): the canonical key

**Problem (paraphrased).** Given a list of strings, group together the strings that are anagrams of each other. Return the groups in any order.
Example: `["eat","tea","tan","ate","nat","bat"]` → `[["bat"],["nat","tan"],["ate","eat","tea"]]` (any order).
Constraints: `1 <= len(strs) <= 10^4`; each string 0 to 100 lowercase letters.

**Derivation.** "Which items belong together?" means grouping, so store key → list. The key must be **identical for every word in a group and different between groups**. That's called a *canonical form*. Sorting the letters gives one: `"eat"`, `"tea"` and `"ate"` all sort to `a, e, t`.

```python
from collections import defaultdict

def groupAnagrams(strs):
    groups = defaultdict(list)         # canonical key -> words with that key
    for w in strs:
        key = tuple(sorted(w))         # sorted() returns a LIST; lists can't be dict keys
        groups[key].append(w)
    return list(groups.values())       # .values() is a view; wrap it in list()
```

The two lines with comments are exactly the two problems from your July attempts:

- `sorted(w)` returns a **list**, and lists are **unhashable** (they can change, so they can't be dictionary keys). Use `tuple(sorted(w))` or `"".join(sorted(w))`.
- `groups.values()` returns a **view**, not a list. LeetCode expects `List[List[str]]`, so wrap it: `list(groups.values())`.

### 4.3 Longest Consecutive Sequence (128): a set, plus "only start at starts"

**Problem (paraphrased).** Given an unsorted array of integers, return the length of the longest run of consecutive values (like 1, 2, 3, 4) that can be formed from its elements. The values don't need to be adjacent in the array. Must run in O(n).
Examples: `[100,4,200,1,3,2]` → `4` (1, 2, 3, 4). `[0,3,7,2,5,8,4,6,0,1]` → `9`.
Constraints: `0 <= len(nums) <= 10^5`; `-10^9 <= nums[i] <= 10^9`.

Sorting would be O(n log n), and the problem asks for O(n). Derivation:

1. Put every value in a set, so "is v present?" is O(1).
2. A run **starts** at `x` exactly when `x - 1` is not present. Name it: `x` is a *start*.
3. From each start, count up while `x + length` is present.

```python
def longestConsecutive(nums):
    present = set(nums)
    best = 0
    for x in present:
        if x - 1 in present:           # not a start: some run already covers x
            continue
        length = 1
        while x + length in present:
            length += 1
        best = max(best, length)
    return best
```

**Why it's O(n) even with a `while` inside a `for`:** the `while` only runs from starts, and each value is counted inside exactly one run. Total `while` steps across the whole loop ≤ n. Without the "only start at starts" check, a run of length L would be re-counted from every one of its L values, which is O(n²) on a long run.

---

## 5. Prefix sums (definition, derived)

### 5.1 The problem they solve

"Sum of `nums[l:r]`" by looping costs O(r − l). If you need many range sums (or all of them), that's O(n²) or worse. Prefix sums make each range sum O(1).

### 5.2 Name it, and pick the convention on purpose

```
prefix[i] = sum of nums[0:i]      (half-open: the first i elements)
```

- **Valid set of `i`:** `0 … n`. So `prefix` has **n + 1** entries.
- `prefix[0] = 0`: the sum of zero elements, the empty prefix. (Same idea as "the answer for the empty problem" in lecture 002 §4.2.)
- `prefix[n]` = the sum of the whole array.

```
nums:      3   1   4   1   5
index:   0   1   2   3   4   5          ← prefix positions sit BETWEEN elements
prefix:  0   3   4   8   9  14
```

### 5.3 Range sum as a difference

The sum of `nums[l:r]` (elements `l … r-1`) is the first `r` elements minus the first `l` elements:

```
sum(nums[l:r]) = prefix[r] - prefix[l]          valid for 0 <= l <= r <= n
```

Example: `nums[1:4] = [1, 4, 1]`, sum 6; `prefix[4] - prefix[1] = 9 - 3 = 6` ✓.

**Why half-open:** with `prefix[i]` meaning "the first i elements," there's no `-1` anywhere: no `prefix[l-1]` and no special case for `l = 0`. This is the half-open convention chosen deliberately, the lecture 001 lesson applied on purpose.

```python
prefix = [0] * (len(nums) + 1)
for i, x in enumerate(nums):
    prefix[i + 1] = prefix[i] + x       # first i+1 elements = first i elements + nums[i]
```

---

## 6. Prefix sums + hash map (560, 974)

### 6.1 Subarray Sum Equals K (560)

**Problem (paraphrased).** Given an integer array `nums` and an integer `k`, return the number of contiguous, non-empty subarrays whose sum equals `k`.
Examples: `[1,1,1], k = 2` → `2`. `[1,2,3], k = 3` → `2` (`[1,2]` and `[3]`).
Constraints: `1 <= len(nums) <= 2·10^4`; `-1000 <= nums[i] <= 1000`; `-10^7 <= k <= 10^7`.

**Why not a sliding window?** Values can be **negative**, so growing the window doesn't always increase the sum, and "shrink when too big" stops being valid. With negatives, reach for prefix sums.

**Derivation (the §2 procedure):**

1. **Brute force:** for every end `r` (1 … n) and start `l` (0 … r-1), check `prefix[r] - prefix[l] == k`. O(n²).
2. **The inner question, for a fixed `r`:** how many earlier `l` satisfy it?
3. **Solve for the earlier value:** `prefix[l] == prefix[r] - k`. Name it: `need = prefix - k`.
4. **"How many?"** → store prefix value → count.
5. **Look up, then insert.** The dictionary starts with the empty prefix: `{0: 1}`, which is `prefix[0] = 0`, seen once. Without it, subarrays that start at index 0 (`l = 0`) are never counted.

```python
def subarraySum(nums, k):
    count_of_prefix = {0: 1}           # prefix[0] = 0: the empty prefix, seen once
    prefix = 0                         # running prefix = sum of nums[0:r]
    total = 0
    for x in nums:
        prefix += x
        total += count_of_prefix.get(prefix - k, 0)                  # look up first
        count_of_prefix[prefix] = count_of_prefix.get(prefix, 0) + 1  # then insert
    return total
```

You don't need the whole prefix array, only the running prefix and the counts of earlier ones.

Trace on `[1, 2, 3], k = 3` (expected 2):

| r | x | prefix | need = prefix − 3 | found | total | board after |
|---|---|---|---|---|---|---|
| start | | 0 | | | 0 | {0: 1} |
| 1 | 1 | 1 | -2 | 0 | 0 | {0: 1, 1: 1} |
| 2 | 2 | 3 | 0 | **1** (the empty prefix → subarray `[1,2]`) | 1 | {0: 1, 1: 1, 3: 1} |
| 3 | 3 | 6 | 3 | **1** (prefix 3 → subarray `[3]`) | 2 | {0: 1, 1: 1, 3: 1, 6: 1} |

Final 2 ✓. Row 2 shows exactly why `{0: 1}` is needed: the subarray `[1, 2]` starts at index 0, and its matching "earlier prefix" is the empty one.

### 6.2 Subarray Sums Divisible by K (974): both ideas at once

**Problem (paraphrased).** Given an integer array `nums` and an integer `k`, return the number of non-empty contiguous subarrays whose sum is divisible by `k`.
Example: `[4,5,0,-2,-3,1], k = 5` → `7`. `[5], k = 9` → `0`.
Constraints: `1 <= len(nums) <= 3·10^4`; `-10^4 <= nums[i] <= 10^4`; `2 <= k <= 10^4`.

`prefix[r] - prefix[l]` is divisible by k exactly when the two prefixes have the **same remainder**. So `need` = the current prefix's remainder.

```python
def subarraysDivByK(nums, k):
    count_of_rem = {0: 1}              # the empty prefix has remainder 0
    prefix = 0
    total = 0
    for x in nums:
        prefix += x
        r = prefix % k                 # Python's % with k > 0 is always in 0..k-1, even for negatives
        total += count_of_rem.get(r, 0)
        count_of_rem[r] = count_of_rem.get(r, 0) + 1
    return total
```

Python note: `-7 % 5` is `3` in Python (it's `-2` in C, C# and Java). The remainder lands in the valid set `0 … k-1` automatically. In C# you'd write `((prefix % k) + k) % k`.

This is the capstone of the lecture: remainders (§3.2) + prefix sums (§5) + count lookup (§6.1).

---

## 7. Prefix and suffix products (238)

**Problem (paraphrased).** Given `nums`, return an array `answer` where `answer[i]` is the product of every element except `nums[i]`. You must not use division, and it must run in O(n).
Example: `[1,2,3,4]` → `[24,12,8,6]`. `[-1,1,0,-3,3]` → `[0,0,9,0,0]`.
Constraints: `2 <= len(nums) <= 10^5`; `-30 <= nums[i] <= 30`; every prefix/suffix product fits in a 32-bit integer.

No hash map here, but it's the same "precompute what you'd recompute" idea, and it was on your to-do list.

**Name the two quantities (half-open, as in §5):**

- `left(i)` = product of `nums[0:i]` (everything before i; empty product = 1)
- `right(i)` = product of `nums[i+1:n]` (everything after i; empty product = 1)
- `answer[i] = left(i) * right(i)`

```python
def productExceptSelf(nums):
    n = len(nums)
    answer = [1] * n
    left = 1                           # product of nums[0:i]
    for i in range(n):
        answer[i] = left
        left *= nums[i]                # now product of nums[0:i+1], ready for i+1
    right = 1                          # product of nums[i+1:n]
    for i in range(n - 1, -1, -1):     # i: n-1 → 0, step -1
        answer[i] *= right
        right *= nums[i]
    return answer
```

The order inside each loop is the whole trick: **use the running product first, then include `nums[i]`**. It's the same look-up-then-insert order as §2 step 5, for the same reason: element `i` must not include itself.

The empty product is **1** (multiplying by nothing changes nothing), just as the empty sum is 0.

---

## 8. Python dictionary fluency

| Task | Code | Note |
|---|---|---|
| Count with a default | `d[k] = d.get(k, 0) + 1` | Works on a plain dict |
| Count, shorter | `d = defaultdict(int)`; `d[k] += 1` | `from collections import defaultdict` |
| Group | `d = defaultdict(list)`; `d[k].append(v)` | |
| Count everything at once | `Counter(iterable)` | `.most_common(k)` gives the top k |
| Membership | `k in d`, `x in s` | O(1) average for dict/set; **O(n) for a list** |
| Hashable keys | int, str, tuple of hashables | **list, dict, set are not hashable** |
| Values as a list | `list(d.values())` | `.values()` alone is a view |
| Iterate | `for k, v in d.items():` | insertion order is preserved (Python 3.7+) |

**One `defaultdict` trap:** *reading* a missing key inserts it. `count[need]` on a `defaultdict(int)` adds `need: 0` to the dictionary. It's usually harmless, but it can surprise you while tracing or when you later check `len(d)` or `key in d`. For look-ups, prefer `d.get(need, 0)`. That's why the solutions above use `.get` for the lookup line.

**Complexity honesty:** dictionary operations are O(1) *on average*. In interviews, "O(1) average, so O(n) overall" is the standard phrasing.

---

## 9. Tracing hash-map code

Use the lecture 003 layout: **a table for the scalars, plus a board for the dictionary**, rewritten in full on each changed row (it's usually small).

Columns that work for every problem in this lecture:

```
| i | x | derived key (r / prefix) | need | found | answer so far | board after |
```

The **CHECK** for this family: at each row, `found` should equal what the inner loop of the brute force would have counted. Count it directly on the array prefix to verify.

Good trace inputs:

| Problem | Input that hits every branch |
|---|---|
| Two Sum | `[3, 3], 6` (equal values) and `[3, 2, 4], 6` (self-pairing trap) |
| Divisible pairs | include a multiple of k (remainder 0) |
| Subarray sum | a subarray starting at index 0 (tests `{0: 1}`), plus a negative number |
| Group anagrams | an empty string `""` and a single word |
| Longest consecutive | duplicates `[1, 2, 2, 3]` and an empty array |

---

## 10. Recognizing these problems

| Signal | Pattern |
|---|---|
| "two numbers that add up to / pair with property" on **unsorted** data | Complement lookup (A) |
| Same problem on **sorted** data | Two pointers is also O(n) and uses O(1) space |
| "anagram", "same letters", "permutation of" | Counter, or a canonical key (B/C) |
| "group", "categorize", "bucket by" | Canonical key → list (C) |
| "contains", "duplicate", "seen before", "in O(n)" with no sorting | Set (D) |
| "subarray sum equals / divisible by", **negatives allowed** | Prefix sum + count (E) |
| "subarray sum", **all positive** | Sliding window is also possible (next lecture topic) |
| "product of all except", "range sum queries" | Prefix/suffix precomputation |
| You've written a double loop and the inner loop only *looks backward* | Ask: what does element i need from the past? → dictionary |

**Before coding, write three comment lines** (the same habit as lecture 004 §8):

```python
# brute force: O(n^2), inner loop asks: "how many earlier j with ___?"
# need: <name> = <solve the condition for the earlier value>
# store: <set / count / index / list>, look up BEFORE insert
```

---

## 11. Practice ladder

Each problem adds one thing. Write the three comment lines first, trace the inputs from §9, then submit.

| # | Problem | New idea | Full problem |
|---|---|---|---|
| 1 | 217 Contains Duplicate | set, look up before insert | §3.3 |
| 2 | 1 Two Sum | complement → index | §3.1 |
| 3 | 242 Valid Anagram | Counter | §4.1 |
| 4 | Divisible Sum Pairs (redo, O(n + k)) | remainders, `% k` valid set | §0 |
| 5 | 49 Group Anagrams (redo from July) | canonical key, hashable tuple | §4.2 |
| 6 | 128 Longest Consecutive Sequence | set + "only start at starts" | §4.3 |
| 7 | 238 Product of Array Except Self | prefix/suffix, empty product = 1 | §7 |
| 8 | 560 Subarray Sum Equals K | prefix + count, `{0: 1}` | §6.1 |
| 9 | 974 Subarray Sums Divisible by K | everything combined | §6.2 |

---

## Common mistakes

| Mistake | Symptom | Fix |
|---|---|---|
| Insert before look-up | Element pairs with itself (`[3,2,4], 6` → `[0,0]`) | Look up first, then insert |
| Forgetting `{0: 1}` in prefix counting | Misses subarrays that start at index 0 | Seed the empty prefix |
| `need = k - r` | Remainder-0 elements look for `k`, which never exists | `(k - r) % k`: keep it in `0 … k-1` |
| List as a dict key | `TypeError: unhashable type: 'list'` | `tuple(...)` or `"".join(...)` |
| Returning `d.values()` | Wrong type for LeetCode | `list(d.values())` |
| `x in some_list` inside a loop | Hidden O(n²) | Convert to a set first |
| Sliding window with negative numbers | Wrong counts | Prefix sums + dictionary |
| Inner `while` from every element (128) | O(n²) on long runs | Only start where `x - 1` is absent |
| Including `nums[i]` before using the running product | Every answer includes its own element | Use first, then multiply in |

---

## Interview relevance

- This is the **most common family** in screening rounds. Two Sum is often the warm-up, and how fast and cleanly you go from brute force to lookup is what's being measured.
- **Narrate the derivation:** "Brute force is O(n²). The inner loop asks whether an earlier element equals target − x, so I'll keep a dictionary of values I've seen, looking up before inserting so I never pair an element with itself. That's O(n) time and O(n) space."
- **Expect follow-ups:** "What if the input is sorted?" (two pointers, O(1) space). "What if it doesn't fit in memory?" (sort, or partition by hash). "What about negative numbers?" (prefix sums instead of a sliding window).
- **State the space trade-off out loud.** It's the price of the speedup.

---

## Self-check questions

1. What is the brute-force inner loop of Two Sum asking, and what does that become with a dictionary?
<details><summary>Answer</summary>

"Is there an earlier j with nums[j] == target − nums[i]?" With a dictionary: `need = target - x`, then `need in seen`, with value → index stored for earlier elements.
</details>

2. Why look up before inserting?
<details><summary>Answer</summary>

So the dictionary only holds elements before i (that's the `j < i` of the brute force), which stops an element from pairing with itself.
</details>

3. For divisible pairs with k = 4, what remainder does an element with remainder 0 need? With remainder 1? Why `% k`?
<details><summary>Answer</summary>

0 and 3. `k - r` gives 4 for r = 0, which isn't in the valid set 0 … 3. `(k - r) % k` folds it to 0.
</details>

4. Which data structure for each question: exists / how many / where / which ones?
<details><summary>Answer</summary>

set / dict → count / dict → index / dict → list.
</details>

5. Why does `{0: 1}` appear in Subarray Sum Equals K?
<details><summary>Answer</summary>

It's the empty prefix `prefix[0] = 0`. A subarray starting at index 0 needs an earlier prefix equal to 0, and that empty prefix is it.
</details>

6. Using `prefix[i]` = sum of `nums[0:i]`, write the sum of `nums[2:5]`.
<details><summary>Answer</summary>

`prefix[5] - prefix[2]`.
</details>

7. Why can't Subarray Sum Equals K use a sliding window?
<details><summary>Answer</summary>

Values can be negative, so extending the window can decrease the sum. "Shrink when too big" isn't valid any more.
</details>

8. Why is `tuple(sorted(w))` a valid dictionary key but `sorted(w)` isn't?
<details><summary>Answer</summary>

`sorted` returns a list, which is mutable and therefore unhashable. A tuple is immutable and hashable.
</details>

9. Why is Longest Consecutive Sequence O(n) despite the nested `while`?
<details><summary>Answer</summary>

The `while` only runs from run starts (values whose `x - 1` is absent), and each value is visited inside exactly one run, so total `while` steps ≤ n.
</details>

10. In Product Except Self, why is the running product initialized to 1, and why is `answer[i] = left` before `left *= nums[i]`?
<details><summary>Answer</summary>

1 is the empty product. Assigning first means `answer[i]` gets the product of elements *before* i; multiplying afterwards prepares it for i + 1. The other order would include `nums[i]` itself.
</details>

11. What does `-7 % 5` evaluate to in Python, and why does that matter for 974?
<details><summary>Answer</summary>

3. Python's `%` with a positive divisor always returns 0 … k-1, so negative prefix sums land in the right bucket automatically. (In C#/Java it's -2; you'd need `((p % k) + k) % k`.)
</details>

12. Your double loop's inner loop only looks at indices *after* i. Can you still use this technique?
<details><summary>Answer</summary>

Yes. Every pair (i, j) with j > i is the same as the pair (j, i) with i < j. Iterate once and look backward, or iterate from the right and look forward. The order of the pair doesn't change the count.
</details>

---

## Sources

- Problems: LeetCode 1, 217, 242, 49, 128, 238, 560, 974 and HackerRank "Divisible Sum Pairs". Statements paraphrased; examples and constraints from long-standing problem pages (from my own knowledge, not re-fetched; 2026-10-07).
- Python docs: `collections.Counter`, `collections.defaultdict` (https://docs.python.org/3/library/collections.html); `%` semantics for negative numbers (https://docs.python.org/3/reference/expressions.html#binary-arithmetic-operations); dict operation complexity (https://wiki.python.org/moin/TimeComplexity).
- Verification (2026-10-07): every function tested against brute force on 3,000 random inputs (including negatives and duplicates); trace tables generated by running the code. Your Divisible Sum Pairs (Sep 26) was run and returns 5 on the example.
- Companions: lecture 003 §5.3 (boards), lecture 004 §8 (three comment lines before coding), lecture 002 §4.2 (empty-problem answers).
