<!-- id: e02_lru_cache_with_ttl | family: E | level: core | minutes: 45 | bridge: pairs with a01_url_shortener, b02_distributed_kv_store -->
# E02 · LRU Cache with Expiry (code)

## The prompt

Write a class `Cache(capacity)` with two methods:

- `put(key, value, ttl, now)`: store `value` under `key`. The entry is valid at any later time `t` with `t < now + ttl`, so it expires at exactly `now + ttl`. Putting an existing key replaces its value and expiry and counts as using it. If the cache already holds `capacity` entries and `key` is new, first remove the **least recently used** entry.
- `get(key, now) -> value or -1`: return the value if `key` is present and not expired at `now` (this counts as using it); otherwise return `-1`. An expired entry found by `get` is removed.

"Used" means put or successfully returned by `get`. `now` is a time in seconds and never decreases between calls. Both methods should run in O(1) average time.

Example with `Cache(capacity=2)`:

| Call | Returns | Why |
|---|---|---|
| `put("a", 1, ttl=10, now=0)` | | `a` expires at 10 |
| `put("b", 2, ttl=5, now=1)` | | `b` expires at 6 |
| `get("a", now=2)` | `1` | `a` is now the most recently used |
| `put("c", 3, ttl=10, now=3)` | | full: evicts `b` (least recently used) |
| `get("b", now=4)` | `-1` | evicted |
| `get("c", now=4)` | `3` | |
| `get("a", now=11)` | `-1` | expired at 10 |

Constraints: `1 <= capacity <= 10^5`, up to `2 × 10^5` calls. The code must run.

This extends LeetCode 146 (*LRU Cache*) with expiry.

## What this case trains

- **Combining two structures** and keeping them in sync (a hash map for lookup + an ordering for recency), the method in `../../../leetcode/012-data_structure_design_problems.md` §1.
- A precise definition of a time boundary (`<` vs `<=` at the expiry instant).
- Lazy vs eager cleanup.

## Interviewer's notes (open only after your self-review, or give to the interviewer)

<details><summary>Answers to clarifying questions</summary>

- **Values:** non-negative integers (so `-1` is never a real value).
- **ttl:** a positive number.
- **Library structures:** using `OrderedDict` is acceptable for a first version; be ready to build the doubly linked list yourself.
- **Expired entries and capacity:** in the base version, expired entries still occupy space until `get` finds them or they're evicted as LRU.

</details>

<details><summary>Pushback questions the interviewer will ask</summary>

1. Implement it without `OrderedDict`: what are your nodes, and why must the list be doubly linked?
2. What does each node store, and why does it need the key as well as the value?
3. With the base rules, the cache can be full of expired entries and evict a live one. Fix it without making `put` slower than O(log n).
4. Is the entry valid at exactly `now == expiry`? Where in your code is that decided?
5. Make it thread-safe. What's the simplest correct version, and what does it cost?
6. How does this single-node cache relate to the cache box in a URL shortener design?

</details>

## After your attempt

- Compare with: `../../../leetcode/012-data_structure_design_problems.md` §3.8 (LRU Cache) and its solution section.
