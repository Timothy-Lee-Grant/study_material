# Lecture 020: Hash Tables Under the Hood, and Deleting Nodes Without a Garbage Collector

> **For:** Timothy · **Date:** 2026-10-31
> **Prerequisites:** lecture 005 (hash maps as a tool), lecture 010 (linked lists, `prev`/`cur`, sentinels).
> **Why this lecture:** you already use sets and dicts fluently. Two follow-up questions go one level deeper: *what happens inside the set when keys collide, and is it still O(1)?* and *what changes when there's no garbage collector to clean up deleted nodes?* Your current explanation of collisions is close but not precise: you described a fixed limit on collisions, enforced by adding keys. The real mechanism is the **load factor** and **resizing**, and the precise answer separates **expected** O(1) from **worst-case** O(n). This lecture builds a hash set in C to make each piece concrete, and uses it to solve the linked-list problem with manual memory.
> **Format notes:** full problem statement; every term defined before use; no firmware analogies.
> **Verification:** `code/020_dedupe_list.c` was compiled with `-fsanitize=address,undefined` and passes 5 edge-case tests plus a 100,000-node run with no leaks or invalid accesses. `code/020_hash_table_demo.py` produced every number in §4. CPython details were read from the CPython source (links in Sources).

---

## Core ideas (the answer key)

1. **A hash table is an array of slots plus a hash function.** `hash(key) % capacity` picks a slot. Lookup is fast because you jump straight to one slot instead of scanning.
2. **A collision is two different keys landing in the same slot.** Collisions are normal and unavoidable (more possible keys than slots). The table must store both keys and tell them apart by comparing them with `==`.
3. **Two ways to handle collisions:** **separate chaining** (each slot holds a small list of the keys that landed there; Java's `HashMap`, C++'s `unordered_map`) and **open addressing** (each slot holds one key; on a collision, probe other slots in a fixed order; Python's `dict` and `set`).
4. **The load factor is α = (keys stored) / (slots).** With a good hash, the expected number of keys a lookup compares is about 1 + α for chaining. The table keeps α below a limit (0.75 in Java's `HashMap`, about 0.6 in CPython's `set`, 2/3 in CPython's `dict`) by **growing**: allocate a bigger array (usually 2× or more) and re-insert every key.
5. **Growing costs O(n) once, but it happens rarely enough that the average cost per insert is O(1).** That's **amortized** O(1). Doubling is what makes it work: the total re-insert work over n inserts is at most about 2n.
6. **The precise complexity statement:** insert and lookup are **expected O(1)** (average over keys, assuming the hash spreads them well), **amortized** over resizes, and **worst-case O(n)** for a single operation if many keys collide. Nothing caps the number of collisions in one slot; the load factor caps the *average*.
7. **Worst cases are real.** A bad hash function, or keys chosen by an attacker to collide (**hash flooding**), puts everything in one slot and turns n inserts into O(n²). Defenses: randomized hash seeds (Python randomizes `str` hashes per process), converting long chains to balanced trees (Java 8+ does this at 8 entries in a chain), or a sorted structure with guaranteed O(log n).
8. **Without a garbage collector, removing a node means: save `next`, relink around the node, free it, and only then move on.** Freeing first and reading `node->next` afterwards is a use-after-free.
9. **When you delete `cur`, `prev` does not move.** `prev` is "the last node I kept." Moving it onto a freed node is the classic bug.
10. **Everything you allocate, you free, exactly once:** the removed nodes during the algorithm, the remaining list at the end, and the hash set's entries and bucket array. AddressSanitizer catches the cases you miss.

---

## Table of Contents

- [0. The problem](#0-the-problem)
- [1. The garbage-collected solution](#1-the-garbage-collected-solution)
- [2. How a hash table actually works](#2-how-a-hash-table-actually-works)
- [3. Load factor, growing, and amortized O(1)](#3-load-factor-growing-and-amortized-o1)
- [4. When collisions pile up: measured](#4-when-collisions-pile-up-measured)
- [5. What Python actually does](#5-what-python-actually-does)
- [6. The same problem in C, with manual memory](#6-the-same-problem-in-c-with-manual-memory)
- [7. A precise answer about collisions](#7-a-precise-answer-about-collisions)
- [Common mistakes](#common-mistakes)
- [Self-check questions](#self-check-questions)
- [Sources](#sources)

---

## 0. The problem

**Remove later duplicates from an unsorted linked list (paraphrased; a classic, e.g. *Cracking the Coding Interview* 2.1).**

Given the head of a singly linked list of integers, in no particular order, remove every node whose value already appeared in an **earlier** node. Keep the first occurrence of each value and keep the remaining nodes in their original order. Return the head.

**Examples.**

```
1 → 2 → 1 → 3 → 2 → 4      becomes   1 → 2 → 3 → 4
5 → 5 → 5 → 5              becomes   5
1 → 2 → 3                  becomes   1 → 2 → 3
(empty)                    becomes   (empty)
```

**Constraints (typical):** up to 10⁵ nodes; values fit in a 32-bit int.

**Follow-ups this lecture answers:**
1. In a language without garbage collection (C), what changes?
2. The solution uses a hash set. What happens when keys collide? Is it still O(n)?
3. (Bonus) Without extra memory? Compare each node with all later nodes: O(n²) time, O(1) space.

---

## 1. The garbage-collected solution

Walk the list with `prev` (last node kept) and `cur` (node being examined), and a set of values seen so far.

```python
def remove_later_duplicates(head):
    seen = set()
    prev, cur = None, head
    while cur:
        if cur.val in seen:
            prev.next = cur.next      # bypass cur; prev stays put
        else:
            seen.add(cur.val)
            prev = cur
        cur = cur.next
    return head
```

**Why `prev` is never `None` in the duplicate branch:** the first node can't be a duplicate (nothing came before it), so by the time a duplicate appears, at least one node has been kept and `prev` points at it. That's also why the head never changes and no sentinel is needed.

**Why the bypassed node is fine in Python:** after `prev.next = cur.next`, nothing in the list points at the old `cur`. When the loop moves on, nothing at all refers to it, and Python's reference counting frees it. In C, nobody does that for you.

**Cost:** O(n) time *if set operations are O(1)*, O(n) extra space for the set. The rest of the lecture is about that "if".

---

## 2. How a hash table actually works

A **hash function** turns a key into a big integer, the same integer every time for equal keys. A hash table keeps an array of `m` **slots** (also called buckets) and stores key `k` in slot `hash(k) % m`.

```
keys 12, 7, 33, 20 ; m = 8 ; hash(k) = k (Python ints hash to themselves)

slot:   0     1     2     3     4     5     6     7
              33                12          7
                                20                       ← 20 % 8 = 4 too: a collision
```

A **collision** is two different keys in the same slot: here 12 and 20 (both `% 8 == 4`). There are more possible keys than slots, so collisions are guaranteed to happen (the pigeonhole principle). The table must still store both and find the right one, which is why lookups compare the actual keys with `==`, not just the hashes.

**Separate chaining:** each slot holds a linked list (a "chain") of the keys that landed there. Lookup = go to the slot, walk its chain comparing keys.

```
slot 4:  12 → 20
```

**Open addressing:** each slot holds at most one key. On a collision, try another slot, then another, following a fixed **probe sequence**, until you find the key or an empty slot. The simplest sequence is linear probing (`i, i+1, i+2, ...`). Deleting is trickier: you can't just empty a slot, because that would break the probe chain for keys stored after it, so open-addressing tables mark deleted slots with a "dummy" (tombstone) instead.

```
slot:   0     1     2     3     4     5     6     7
              33                12    20          7     ← 20 wanted slot 4, took 5
```

Both are correct. Chaining is simpler to write and degrades gently; open addressing has better memory locality (no pointers to chase) and is what CPython uses.

---

## 3. Load factor, growing, and amortized O(1)

**Load factor:** α = n / m, the number of keys stored divided by the number of slots. With a good hash, keys spread evenly, so an average chain holds α keys. A lookup for a key that's present compares about 1 + α/2 keys; one for a missing key walks a whole chain, about α. Either way, if α stays below a constant, the expected cost is a constant: **O(1)**.

**Keeping α bounded means growing.** When an insert would push α past the limit, the table allocates a new array (2× is typical), and **re-inserts every key**, because `hash(k) % m` changes when `m` changes. That one insert costs O(n).

**Why the average is still O(1) (amortized):** with doubling, a resize from m to 2m happens only after about m/2 new keys arrived since the last one (with limit 0.75: after the table filled from 0.375 to 0.75). Add up all the re-insert work for n inserts:

```
resizes at sizes ~ n, n/2, n/4, ...   →   total moves ≤ n + n/2 + n/4 + ... < 2n
```

So n inserts cost O(n) total, which is O(1) per insert **on average over the sequence**. This is the same argument as Python's `list.append`. The word "amortized" means exactly this: a few expensive operations, paid for by many cheap ones.

**Growing by a constant amount (say +100 slots) doesn't work:** you'd resize every 75 inserts, each costing O(n), so n inserts cost O(n²/75), which is still O(n²). The growth has to be **proportional** to the current size.

Our C table (`code/020_dedupe_list.c`) grows when `(count + 1) * 4 > nbuckets * 3`, i.e. when α would exceed 0.75:

```c
static void set_add(HashSet *s, int key) {         /* caller has checked it isn't present */
    if ((s->count + 1) * 4 > s->nbuckets * 3)      /* load factor would pass 0.75 -> grow first */
        set_grow(s);
    Entry *e = malloc(sizeof *e);
    size_t i = hash_int(key) & (s->nbuckets - 1);   /* nbuckets is a power of 2: & is % */
    e->key = key; e->next = s->buckets[i]; s->buckets[i] = e;
    s->count++;
}

static void set_grow(HashSet *s) {
    size_t newn = s->nbuckets * 2;
    Entry **nb = calloc(newn, sizeof *nb);
    for (size_t i = 0; i < s->nbuckets; i++) {
        Entry *e = s->buckets[i];
        while (e) {
            Entry *next = e->next;                 /* save before relinking */
            size_t j = hash_int(e->key) & (newn - 1);
            e->next = nb[j]; nb[j] = e;            /* move the entry, don't copy it */
            e = next;
        }
    }
    free(s->buckets);
    s->buckets = nb; s->nbuckets = newn;
}
```

Notice `set_grow` uses the same "save `next` before changing the node" pattern as list deletion: once `e->next` is overwritten to link into the new bucket, the rest of the old chain is only reachable through the saved `next`.

From the 100,000-node run (values 0..9,999):

```
big: kept 10000 distinct, buckets 16384, load 0.61, resizes 11, avg entries compared per lookup 1.19
```

Eleven resizes (8 → 16 → ... → 16,384) for 10,000 keys, and on average a lookup compared 1.19 stored keys. That's what O(1) looks like in practice.

---

## 4. When collisions pile up: measured

"Expected O(1)" assumes the hash spreads keys evenly. `code/020_hash_table_demo.py` inserts the keys `0, 7, 14, ...` into the same chaining table three times, with three hash functions:

```
good hash (Python's hash)          n=  1000 buckets=  2048 resizes= 8 longest chain=    1 compares per add=    0.00
every key -> same bucket           n=  1000 buckets=  2048 resizes= 8 longest chain= 1000 compares per add=  499.50
ignores low bits (k // 1024)       n=  1000 buckets=  2048 resizes= 8 longest chain=  147 compares per add=   71.18
good hash (Python's hash)          n=  4000 buckets=  8192 resizes=10 longest chain=    1 compares per add=    0.00
every key -> same bucket           n=  4000 buckets=  8192 resizes=10 longest chain= 4000 compares per add= 1999.50
ignores low bits (k // 1024)       n=  4000 buckets=  8192 resizes=10 longest chain=  147 compares per add=   72.05
```

Read it row by row:

- **Good hash:** each new key found an empty slot, so `add` compared nothing (0.00). O(1).
- **Every key in one bucket:** the table grew exactly as before (same 8 or 10 resizes, same load factor), **but it didn't help**, because doubling the array doesn't separate keys whose hashes are equal. The i-th insert walks i keys: about n/2 compares per add, n²/2 total. Quadrupling n quadrupled the per-add cost. That's **O(n) per operation**.
- **A hash that ignores the low bits:** keys within the same block of 1,024 collide no matter how big the table gets, so chains stay ~147 long. Resizing can't fix a hash that throws information away.

This is the key correction: **resizing controls the average chain length only when the hash spreads the keys.** It does not put a fixed cap on collisions, and it does not "create more keys". When the hash is bad, or an attacker picks keys that share a hash, the worst case is O(n) per operation.

Defenses real implementations use:
- **Randomized seeds.** Python hashes `str` and `bytes` with SipHash using a random per-process key, so an attacker can't precompute colliding strings. (`PYTHONHASHSEED` fixes it, for reproducibility.)
- **Treeify long chains.** Java 8's `HashMap` converts a chain to a red-black tree once it reaches 8 entries (if the table has at least 64 buckets), making the worst case O(log n) per operation.
- **Use an ordered structure** (a balanced tree, e.g. C++ `std::set`) when you need a guaranteed bound: O(log n) always.

**Python ints are not randomized:** `hash(k) == k` for small non-negative ints (except `hash(-1) == -2`, since -1 is reserved as an error code in CPython's C code, so `hash(-1) == hash(-2)`). That's fine for normal data, and CPython's probe sequence (next section) mixes in the high bits so patterned ints don't pile up.

---

## 5. What Python actually does

Python's `set` and `dict` use **open addressing**, not chaining. From the CPython source (`Objects/setobject.c`, read 2026-10-31):

- **Table size is a power of 2**, so `hash % size` is computed as `hash & mask` (`mask = size - 1`).
- **Probing:** first a short run of up to 9 adjacent slots (`LINEAR_PROBES 9`, good for the CPU cache), then a jump to `i = (i * 5 + 1 + perturb) & mask`, where `perturb` starts as the full hash and is shifted right by 5 bits each round (`PERTURB_SHIFT 5`). That gradually mixes the high bits of the hash into the slot choice, so keys that differ only in high bits still separate.
- **When to grow:** a `set` resizes when `fill * 5 >= mask * 3`, about 60% full (`fill` counts used slots plus deleted-marker slots). The new size is 4× the number of keys (2× above 50,000 keys), rounded up to a power of 2.
- **`dict`** has a similar design with a usable fraction of 2/3, and since Python 3.6 keeps a separate dense array of entries, which is why dicts preserve insertion order.

So the precise statement for Python: `x in s` and `s.add(x)` are **expected O(1), amortized over resizes; worst case O(n)** if many keys share a slot sequence.

---

## 6. The same problem in C, with manual memory

In C, a node removed from the list is still allocated until someone calls `free`. If nobody does, it's a **memory leak**. If someone frees it and then reads it, that's a **use-after-free**, which is undefined behavior: it might work, crash, or silently corrupt something else.

```c
typedef struct Node { int val; struct Node *next; } Node;

/* Keeps the first occurrence of each value, frees every later one. */
static Node *remove_later_duplicates(Node *head, HashSet *seen) {
    Node *prev = NULL;      /* last node we KEPT (NULL before the first node) */
    Node *cur = head;       /* node being examined */
    while (cur) {
        if (set_contains(seen, cur->val)) {
            Node *next = cur->next;   /* 1. save the rest of the list */
            prev->next = next;        /* 2. bypass cur */
            free(cur);                /* 3. nothing points at cur now: safe to free */
            cur = next;               /* 4. move on WITHOUT moving prev */
        } else {
            set_add(seen, cur->val);
            prev = cur;
            cur = cur->next;
        }
    }
    return head;
}
```

**The four steps, and what breaks if you reorder them:**

| Order | What happens |
|---|---|
| save → relink → free → advance | correct |
| free → `cur = cur->next` | **use-after-free:** reads `next` from freed memory |
| relink → `cur = cur->next` → (no free) | correct list, **leak** of one node per duplicate |
| relink → free → `prev = cur` | `prev` now points at freed memory; the next deletion writes `prev->next` into it: **heap corruption** |

**Trace on `1 → 2 → 1 → 3`:**

| step | `cur` | in set? | action | `prev` | list | set |
|---|---|---|---|---|---|---|
| 1 | node(1) | no | add, prev = cur | node(1) | 1→2→1→3 | {1} |
| 2 | node(2) | no | add, prev = cur | node(2) | 1→2→1→3 | {1,2} |
| 3 | node(1)′ | yes | next = node(3); node(2).next = node(3); free(node(1)′); cur = node(3) | node(2) | 1→2→3 | {1,2} |
| 4 | node(3) | no | add, prev = cur | node(3) | 1→2→3 | {1,2,3} |

In step 3, `prev` stays on node(2). It's still the last node kept, and it's the one whose `next` must change if the following node is also a duplicate.

**Who frees what at the end.** `main` frees the remaining list with the same save-then-free loop, and the hash set frees each entry and then its bucket array:

```c
static void free_list(Node *head) {
    while (head) {
        Node *next = head->next;   /* read next BEFORE freeing */
        free(head);
        head = next;
    }
}
```

**Checking it.** Compile with AddressSanitizer, which reports leaks, use-after-free and out-of-bounds accesses at the line where they happen:

```bash
gcc -std=c11 -Wall -Wextra -g -fsanitize=address,undefined code/020_dedupe_list.c -o dedupe && ./dedupe
# mixed                        ok
# all the same                 ok
# no duplicates                ok
# duplicate at the tail        ok
# empty list                   ok
# big: kept 10000 distinct, buckets 16384, load 0.61, resizes 11, avg entries compared per lookup 1.19
```

No ASan report means no leaks and no invalid accesses on these runs. (Try it: swap steps 3 and 4 and rerun. ASan prints `heap-use-after-free` with both the bad read and the earlier `free`.)

**In C++** you'd use `std::unordered_set<int>` (separate chaining, `max_load_factor` 1.0 by default) and `delete` for the nodes, or hold nodes in `std::unique_ptr` so the free happens automatically when the pointer is reassigned. **In the Windows kernel** the same rules apply with `ExAllocatePool2` / `ExFreePool`, and Driver Verifier's special pool catches use-after-free the way ASan does here.

**Why does the hash function multiply by a big constant?** `hash_int` multiplies the key by `0x9E3779B97F4A7C15` (2⁶⁴ divided by the golden ratio) and keeps the high 32 bits. Multiplying spreads every input bit across the high bits of the product. Without it (`hash = key`), keys that are multiples of the table size (0, 16384, 32768, ...) would all land in bucket 0. This is called multiplicative (Fibonacci) hashing.

---

## 7. A precise answer about collisions

When asked "what about collisions in the set?", a precise answer has four parts:

1. **What happens:** two keys hash to the same slot. The table keeps both, either chained in that slot or in other slots found by probing, and tells them apart by comparing keys with `==`.
2. **Why it's still O(1) on average:** the table keeps the load factor below a limit by growing (2× or more) and re-inserting. With a hash that spreads keys evenly, the expected number of comparisons per operation stays constant. Resizes cost O(n) each but happen geometrically less often, so they're O(1) amortized. So the dedupe is O(n) expected.
3. **The worst case:** if many keys share a hash (bad hash function or adversarial input), one slot holds them all and each operation is O(n), making the whole dedupe O(n²). Resizing can't fix equal hashes.
4. **How real systems guard against it:** randomized hash seeds for strings, converting long chains to trees (Java), or a balanced tree when a guaranteed bound is needed.

Compared with "there's a fixed number of collisions allowed and it creates more keys": the right half of the idea was there (the table reacts to crowding by growing), but the mechanism is the load factor across the whole table, not a per-slot limit; growing adds **slots**, not keys; and it's an average, not a guarantee.

---

## Common mistakes

1. **Saying "hash sets are O(1)" with no qualifier.** Say *expected* O(1) (amortized), worst-case O(n).
2. **Thinking resizing bounds every chain.** It bounds the average. Identical hashes stay together at any size.
3. **Growing by a fixed amount.** Growth must be proportional (×2) for amortized O(1).
4. **Freeing a node and then reading `node->next`.** Save `next` first.
5. **Advancing `prev` onto a deleted node.** `prev` moves only when you keep a node.
6. **Forgetting to free the set and the remaining list.** Every `malloc` needs one `free`.
7. **Comparing only hashes.** Equal hashes don't mean equal keys. Compare the keys.

---

## Self-check questions

1. Define load factor. Why does keeping it below 0.75 give expected O(1) lookups?
<details><summary>Answer</summary>α = keys stored / slots. With a hash that spreads keys evenly, an average slot holds α keys, so a lookup compares about 1 + α keys (chaining). If α ≤ 0.75, that's at most a small constant, independent of n.</details>

2. A resize re-inserts all n keys. Why is insertion still called O(1)?
<details><summary>Answer</summary>Because it's amortized: with doubling, resizes happen at sizes ~n, n/2, n/4, ..., so the total re-insert work over n inserts is under 2n. Spread over n inserts, that's O(1) each on average, even though one particular insert costs O(n).</details>

3. Every key in a table has the same hash. The table doubles three times. What's the longest chain now, and what does a lookup cost?
<details><summary>Answer</summary>Still n: equal hashes land in the same slot at every table size, so doubling never separates them. A lookup walks the chain: O(n). The measured run showed exactly this (longest chain 4,000 for 4,000 keys).</details>

4. Name two ways real hash tables defend against many keys colliding.
<details><summary>Answer</summary>Any two of: randomized hash seeds (Python's SipHash for `str`/`bytes`), converting long chains into balanced trees (Java 8+ `HashMap` at 8 entries), or using a balanced-tree set when a guaranteed O(log n) bound matters.</details>

5. Does Python's `set` use chaining? What does it do on a collision?
<details><summary>Answer</summary>No, it uses open addressing: each slot holds at most one entry. On a collision it probes up to 9 adjacent slots, then jumps using `i = (i*5 + 1 + perturb) & mask`, mixing in higher hash bits each round, until it finds the key or an empty slot. It grows at about 60% full.</details>

6. In the C dedupe, what goes wrong with this duplicate branch? `prev->next = cur->next; free(cur); cur = cur->next;`
<details><summary>Answer</summary>`cur = cur->next` reads from `cur` after it's been freed: a use-after-free (undefined behavior). Save `Node *next = cur->next;` before freeing, then `cur = next`.</details>

7. Why doesn't `prev` move in the duplicate branch?
<details><summary>Answer</summary>`prev` means "the last node kept". The removed node isn't kept (and is freed), so `prev` must stay on the previous kept node. If the next node is also a duplicate, `prev->next` is what has to change again.</details>

8. List everything the C program must free before exiting.
<details><summary>Answer</summary>Each removed duplicate node (during the algorithm), every node still in the list (`free_list`), every hash-set entry (`Entry` nodes in each chain), and the bucket array itself. During a resize, the old bucket array is freed too (the entries are moved, not copied).</details>

9. Give the precise one-paragraph answer to "what about collisions?" for this solution.
<details><summary>Answer</summary>Colliding keys are both stored (chained, or placed by probing) and distinguished by `==`. The table keeps its load factor bounded by growing geometrically and re-inserting, so with a well-spread hash each operation is expected O(1), amortized over resizes, and the dedupe is O(n) expected. If many keys share a hash, operations degrade to O(n) and the dedupe to O(n²); real implementations mitigate that with randomized seeds or tree-ified buckets.</details>

---

## Sources

- CPython `Objects/setobject.c` (main branch): `LINEAR_PROBES 9`, `PERTURB_SHIFT 5`, resize at `fill*5 >= mask*3`, growth `used*4` (`used*2` above 50,000). [github.com/python/cpython/blob/main/Objects/setobject.c](https://github.com/python/cpython/blob/main/Objects/setobject.c), read 2026-10-31.
- CPython `Objects/dictobject.c` comments on open addressing, usable fraction 2/3, compact ordered dict (3.6+): [github.com/python/cpython/blob/main/Objects/dictobject.c](https://github.com/python/cpython/blob/main/Objects/dictobject.c). Accessed 2026-10-31.
- [PEP 456, Secure and interchangeable hash algorithm](https://peps.python.org/pep-0456/) (SipHash for `str`/`bytes`, 2013). Accessed 2026-10-31.
- Java `HashMap` documentation (default load factor 0.75; tree bins): [docs.oracle.com, HashMap (Java SE 21)](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/HashMap.html). Accessed 2026-10-31.
- Cormen, Leiserson, Rivest, Stein, *Introduction to Algorithms*, 4th ed. (2022), ch. 11 (hash tables; expected cost 1 + α) and ch. 16 (amortized analysis).
- Code: `code/020_dedupe_list.c` (gcc, ASan + UBSan) and `code/020_hash_table_demo.py`, run 2026-10-31.
