<!-- id: b02_distributed_kv_store | family: B | level: advanced | minutes: 45 | bridge: e02_lru_cache_with_ttl -->
# B02 · Distributed Key-Value Store

## The prompt

Design a key-value store with three operations: `put(key, value)`, `get(key)` and `delete(key)`. Keys are up to 256 bytes; values up to 1 MB. The total data (about 50 TB) is far more than one machine can hold. The store must keep working when individual machines fail, and operations should complete in a few milliseconds.

Assume 500,000 reads and 100,000 writes per second at peak, spread over many keys.

## What this case trains

- **Partitioning** (which machine owns a key) and **consistent hashing**.
- **Replication** and what happens when replicas disagree.
- **Consistency choices**: quorums (N, R, W), and what each setting buys.
- Failure detection and adding/removing machines.

**Bridge coding piece:** `e02_lru_cache_with_ttl` (the single-node, in-memory version of one partition).

## Interviewer's notes (open only after your self-review, or give to the interviewer)

<details><summary>Answers to clarifying questions</summary>

- **Consistency:** the default should favor availability; a reader may briefly see an old value. Offer a stronger option for callers who ask for it.
- **Durability:** an acknowledged write must survive the loss of any single machine.
- **Transactions across keys:** out of scope.
- **Range scans:** out of scope (point lookups only).
- **Datacenters:** one datacenter (mention what changes with several).

</details>

<details><summary>Pushback questions the interviewer will ask</summary>

1. How does a client know which machine to send `get("user:42")` to?
2. You add 10 machines to a cluster of 100. How much data moves, and why not more?
3. With 3 replicas, what do R and W need to be for a read to always see the latest acknowledged write? Derive it.
4. Two clients write different values to the same key at the same time on different replicas. What does a later read return?
5. How does the cluster decide a machine is dead rather than slow?
6. A machine was down for an hour and comes back. How does it catch up?
7. Where does each write go first on a single machine so it survives a crash (log, memory, disk)?

</details>

## After your attempt

- Compare with: Alex Xu vol. 1, "Design a Key-Value Store"; the Amazon Dynamo paper (DeCandia et al., 2007) for the ideas behind quorums and consistent hashing (⚫ optional depth); `../../../storage/001-crash_consistency.md` for question 7.
