<!-- id: e01_token_bucket | family: E | level: starter | minutes: 45 | bridge: pairs with b01_distributed_rate_limiter -->
# E01 · Token Bucket Rate Limiter (code)

## The prompt

Write a class `RateLimiter(capacity, rate)` with one method, `allow(key, now) -> bool`.

- `key` is a client id (a string). Each key is limited independently.
- `now` is the current time in seconds (a float). Calls arrive with `now` never decreasing.
- A key may make up to `capacity` requests in a quick burst; after that, it earns permission for new requests at `rate` per second, and unused permission builds back up to at most `capacity`.
- `allow` returns `True` if this request is allowed (and counts it), `False` otherwise.

Example with `RateLimiter(capacity=3, rate=1.0)`:

| Call | Returns |
|---|---|
| `allow("alice", 0.0)` | `True` |
| `allow("alice", 0.1)` | `True` |
| `allow("alice", 0.2)` | `True` |
| `allow("alice", 0.3)` | `False` |
| `allow("alice", 1.3)` | `True` |
| `allow("bob", 0.3)` *(asked right after the 0.3 call above)* | `True` |

Constraints: up to 10^5 distinct keys; `allow` should be O(1) per call. The code must run.

## What this case trains

- Writing the **interface and one exact example** before code.
- Naming every quantity (`capacity`, `rate`, `tokens`, `last`) and stating its **valid set** (`0 <= tokens <= capacity`).
- **Lazy refill**: computing state on demand instead of with a timer.

Lecture 001 §8.2 contains a full solution and trace. This is a **redo from a blank page**: don't look at it first. Compare afterwards with `../../code/token_bucket.py`.

## Interviewer's notes (open only after your self-review, or give to the interviewer)

<details><summary>Answers to clarifying questions</summary>

- **Fractional tokens:** allowed internally.
- **A brand-new key:** starts with a full bucket.
- **Memory:** keys that go quiet may stay in memory for now (it's a follow-up).
- **Threads:** single-threaded for the main solution.

</details>

<details><summary>Pushback questions the interviewer will ask</summary>

1. Why is `allow("alice", 1.3)` `True` even though `0.3` was `False`? Walk the numbers.
2. What's the invariant on `tokens`, and which line keeps it?
3. Ten million keys each make one request and never return. What happens to memory, and how do you fix it?
4. Make it safe to call from many threads. Where's the lock, and how big is its scope?
5. Return `retry_after` (seconds until the next request would be allowed) along with the decision. Derive the formula.
6. What changes if `now` can occasionally go backwards (clock adjustment)?

</details>

## After your attempt

- Compare with: `../../code/token_bucket.py` and lecture 001 §8.2.
