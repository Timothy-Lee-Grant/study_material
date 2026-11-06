<!-- id: b01_distributed_rate_limiter | family: B | level: core | minutes: 45 | bridge: e01_token_bucket -->
# B01 · Distributed Rate Limiter

## The prompt

A public API runs on 50 servers behind a load balancer. Design a rate limiter that limits each client (identified by API key) to a configured number of requests per time window **across all servers combined**, for example 100 requests per second and 10,000 per day. Requests over the limit are rejected immediately with an error that tells the client when to retry. The limiter must add very little latency to every request (about a millisecond) and must not become a single point of failure.

Assume 200,000 requests per second across the fleet at peak, and 1 million distinct API keys.

## What this case trains

- **Shared state across servers** and keeping concurrent updates correct (atomicity).
- **Placement**: gateway vs middleware vs separate service.
- **Fail open vs fail closed** when the limiter's own store is unreachable.
- Precision vs coordination cost.

Lecture 001 §8.3 walks this case. Attempt it **from a blank page** and aim to go further, especially on multiple limits per key and on the store being slow rather than down.

**Bridge coding piece:** `e01_token_bucket`.

## Interviewer's notes (open only after your self-review, or give to the interviewer)

<details><summary>Answers to clarifying questions</summary>

- **Limits:** configured per plan (free, pro, enterprise); each plan has a per-second and a per-day limit.
- **Precision:** per-second limits may be off by ~10%; per-day limits should be accurate.
- **Response:** HTTP 429 with a `Retry-After` header.
- **When the limiter is broken:** the business prefers to let traffic through (fail open) rather than reject paying customers.
- **Limit changes:** a plan's limits can change and should take effect within a minute.

</details>

<details><summary>Pushback questions the interviewer will ask</summary>

1. Two servers check the same key at the same instant with 1 request left. What stops both from allowing it?
2. Every request now makes a network call to your store. How do you keep the added latency near a millisecond at 200,000 requests/second?
3. Which algorithm do you use for the per-second limit, and which for the per-day limit? Why different (or the same)?
4. The store is not down but slow (50 ms per call). What does your design do?
5. One client sends 30% of all traffic. What happens to the store partition holding their key?
6. How much memory does the store need for 1 million keys?
7. Why not keep a separate counter on each of the 50 servers with 1/50 of the limit each? When does that break?

</details>

## After your attempt

- Compare with: lecture `../../001-system_design_orientation.md` §8.3; Alex Xu vol. 1, "Design a Rate Limiter"; Hello Interview problem breakdowns overview (https://www.hellointerview.com/learn/system-design/problem-breakdowns/overview).
