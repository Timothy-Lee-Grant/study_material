# Drills

Short exercises for **one step at a time**, for days when 80 minutes isn't available, or for whichever step `progress.md` says is weakest. Answers are collapsed; try first.

| Drill | Time | Trains step |
|---|---|---|
| [1. Classify it](#1-classify-it-5-min) | 5 min | Picking the family and toolkit |
| [2. Requirements only](#2-requirements-only-8-min) | 8 min | S1 |
| [3. Estimation reps](#3-estimation-reps-10-min) | 10 min | S1, S6 |
| [4. Trace one flow](#4-trace-one-flow-10-min) | 10 min | S4 |
| [5. Who may wait here?](#5-who-may-wait-here-10-min) | 10 min | S5–S6 in family D |
| [6. Buys / costs](#6-buys--costs-10-min) | 10 min | X2 |
| [7. The opening two minutes](#7-the-opening-two-minutes-5-min) | 5 min | X1 |

---

## 1. Classify it (5 min)

For each prompt, say the family (A–E) and what's scarce, in one breath each.

1. Design YouTube.
2. Implement a min-heap with `push`, `pop` and `peek`.
3. Design a vending machine's classes.
4. A sensor's DMA engine fills a buffer; design how a Linux app reads it with low CPU use.
5. Design a distributed lock service.
6. Design Google Docs' real-time collaborative editing.
7. Design a logger library for a game engine that never blocks the render thread.
8. Design a chess game (classes, moves, rules).
9. Design a metrics collection system for 100,000 servers.
10. Implement `LRUCache` with `get` and `put` in O(1).

<details><summary>Answers</summary>

1. A (machines, storage, bandwidth). 2. E (correctness and complexity). 3. C (clarity, state). 4. D (CPU time, concurrency on one machine). 5. B (correctness under concurrency and failure across machines). 6. A, with a large B-style deep dive (concurrent edits). 7. D-flavored, probably coded (who may block: the render thread may not). 8. C. 9. A/B (write volume, aggregation, storage). 10. E.

</details>

---

## 2. Requirements only (8 min)

Pick any case file. Set a timer for 5 minutes. Write **only step 1**: 2–4 functional requirements, at least two non-functional ones with numbers, what's out of scope, and the clarifying questions you'd ask (with the answers you'd assume). Then open that case's "Answers to clarifying questions" and compare (3 min). Score it with the rubric's S1 row.

---

## 3. Estimation reps (10 min)

For each: **name the quantity first**, write the formula, then the number. Use 1 day ≈ 10⁵ s.

1. 50 million daily users, 20 requests each per day. Requests per second?
2. A URL shortener creates 100 million links a month; each record is ~500 bytes. Storage after 5 years?
3. How many base-62 characters are needed to give a unique code to all the links in question 2?
4. 500,000 drivers each send a location every 4 seconds. Updates per second?
5. Six sensors at 100 Hz and two at 1 kHz, 2 bytes per sample. Raw bytes per second?
6. A 64-entry FIFO fills at 10,000 bytes per second. How long until it overflows if nobody drains it?
7. A touch controller scans at 120 Hz. Average and worst-case delay it adds?
8. A 1 MB flash log with 4 KB sectors, 20-byte records, 100,000 erases per sector. How long until it wears out at a constant 50 records per second?

<details><summary>Answers</summary>

1. `requests_per_day = 5×10⁷ × 20 = 10⁹`; `requests_per_second ≈ 10⁹ / 10⁵ = 10⁴` (exact ≈ 11,600).
2. `links = 10⁸ × 60 months = 6×10⁹`; `bytes = 6×10⁹ × 500 = 3×10¹² = 3 TB` (before replication).
3. Need `62^L >= 6×10⁹`. `62^5 ≈ 9.2×10⁸` (too few), `62^6 ≈ 5.7×10¹⁰` (enough). So 6 characters; 7 (`≈ 3.5×10¹²`) gives lots of headroom.
4. `500,000 / 4 = 125,000` updates per second.
5. `samples_per_second = 6×100 + 2×1000 = 2,600`; `bytes_per_second = 2,600 × 2 = 5,200` (before framing and timestamps).
6. `time_to_overflow = 64 / 10,000 = 0.0064 s = 6.4 ms`.
7. `scan_period = 1/120 s ≈ 8.3 ms`. A touch lands at a random moment in a period: average wait ≈ half ≈ 4.2 ms, worst ≈ 8.3 ms.
8. `records_per_sector = 4096 / 20 ≈ 204`; `sectors = 1 MB / 4 KB = 256`; `records_per_wrap = 256 × 204 = 52,224`; `seconds_per_wrap = 52,224 / 50 ≈ 1,045 s` (each sector is erased once per wrap); `lifetime = 100,000 × 1,045 s ≈ 1.04×10⁸ s ≈ 3.3 years`. (At one record per minute: about 36 days per wrap, so wear is no concern.)

</details>

---

## 4. Trace one flow (10 min)

Pick a case you've already attempted. Without your notes, write one request or event end to end as a numbered list, one line per component: *component → what it does to the request → what it hands to the next*. Then check: is every box in your diagram on this list? A box that isn't is either unnecessary or you've found a second flow worth tracing.

---

## 5. Who may wait here? (10 min)

For each step, say **which context runs it** and **whether it may block**.

Pipeline 1 (device, Windows): (a) the device asserts its interrupt line → (b) the interrupt service routine → (c) a deferred procedure call (DPC) → (d) a call to the bus driver that waits for a transfer → (e) completing the app's pending read → (f) the app's reader thread → (g) the app's UI update.

Pipeline 2 (service): (a) an HTTP request handler → (b) a call to a payment provider that takes up to 2 seconds → (c) writing an audit record → (d) sending a confirmation email.

<details><summary>Answers</summary>

Pipeline 1: (a) hardware. (b) ISR at device IRQL: may not block; acknowledge/mask and queue a DPC. (c) DPC at DISPATCH_LEVEL: may not block or touch pageable memory; can queue a work item or complete requests. (d) must run at PASSIVE_LEVEL in a thread that may wait: a system worker thread (work item) or a driver-owned thread. (e) the driver completes the I/O request from wherever it has the data (often that thread). (f) the reader thread may block on the read; that's its job. (g) the UI thread may not block; the reader posts data to it (dispatcher queue / message).

Pipeline 2: (a) a request thread (or async continuation): it shouldn't hold a thread while waiting; use async I/O. (b) the slow call: async, with a timeout and an idempotency key. (c) needs to happen reliably but not necessarily inline: write to the database in the same transaction, or enqueue. (d) never inline: put it on a queue for a worker, so a slow email provider can't slow down the request.

</details>

---

## 6. Buys / costs (10 min)

For each choice, say one sentence: *"It buys ___; it costs ___."*

1. Adding a cache in front of the database.
2. Fanning out posts on write.
3. Putting a queue between the API and the workers.
4. Replicating data to 3 machines.
5. Failing open when the rate limiter's store is down.
6. A bigger driver ring buffer.
7. Polling the device every 10 ms instead of using an interrupt.
8. Sharding by user id.

<details><summary>Answers (one reasonable version each)</summary>

1. Buys fast reads and less database load; costs staleness and invalidation complexity, plus cold-start misses.
2. Buys cheap, fast timeline reads; costs heavy writes, especially for accounts with huge follower counts.
3. Buys burst absorption and isolation from slow workers; costs latency until processing, and you now need retries, dedupe and monitoring of the backlog.
4. Buys survival of machine loss and more read capacity; costs 3× storage and either replica lag or slower writes.
5. Buys availability for legitimate clients; costs a window where abusive traffic isn't limited.
6. Buys tolerance of longer consumer delays; costs memory (often non-paged), and data sits longer before display.
7. Buys simplicity and bounded CPU per second; costs up to 10 ms extra latency, wasted wakeups when idle (battery), and missed data if the FIFO fills between polls.
8. Buys spreading load and data across machines with locality per user; costs cross-user queries (fan-in across shards) and hot users becoming hot shards.

</details>

---

## 7. The opening two minutes (5 min)

Record yourself (phone voice memo) answering only the first two minutes of any case: restate the problem in one sentence, announce the plan (the sentence in `000-practice_queue.md`), and ask your first three clarifying questions. Listen back once. Did you start drawing? Did you name non-functional requirements with numbers?
