# System Design Gradient Roadmap

> **What this is:** the plan for which system design lectures come next, and why, kept in one place (same role as `../leetcode/000-gradient_roadmap.md`). Created 2026-11-06.
> **Where practice happens:** `practice/` (cases, timer, rubric, reviews). **Every lecture ends by naming the case to attempt next.** A lecture counts as *done* when you've read it **and** attempted its paired case.
> **Map of the subject:** `001-system_design_orientation.md` (five families, the seven-step skeleton, the toolkits). Read it first if you haven't; this series assumes the skeleton.

---

## How this series teaches (and why this way)

You learn fastest from a **causal model**: where something runs, who calls it, and what happens underneath. You also need every rule **derived**, not handed to you as a convention. System design is usually taught the opposite way: a catalogue of components ("here's a cache, here's a queue, here's sharding") and a set of famous designs to memorize. That produces candidates who can name boxes but not justify them, and justifying boxes is exactly what's graded.

So every lecture in this series is built from five ingredients:

| # | Ingredient | What it looks like | Why it's here |
|---|---|---|---|
| 1 | **Forced moves** | Start from the simplest system that could work. Add load or a requirement until something breaks, **with a number**. Add exactly the piece that fixes it, and say what it costs. Repeat. | Every component arrives attached to the problem that forced it. That *is* the interview answer ("this box is here because…"). |
| 2 | **One request, every actor named** | A numbered trace of one request or event through the system, naming the machine, process and layer at each step | Your strongest learning shape (who runs it, who calls it). It also keeps diagrams honest: a box no request passes through is decoration. |
| 3 | **Measure, don't memorize** | A small lab you can run (Python standard library) that produces the numbers the lecture argues from. Predict first, then run. | Interview numbers stop being trivia once you've produced them. Labs have worked well for you (driver lab, YARP repro). |
| 4 | **Named quantities and derivations** | `reads_per_second = reads_per_day / 10⁵`; `avg_latency = t_cache + (1 − h) × t_store`, derived step by step, every symbol defined first | The clicks that have worked for you (name the quantity, write its valid set, derive in small steps) |
| 5 | **A paired practice case** | Each lecture's worked case is *close to* a practice case, but leaves that case's hardest part for you | Worked example → similar problem is the fastest route to transfer. The case attempt is where the lecture turns into skill. |

Two tracks run in parallel and are interleaved, because your target roles need both:

- **Distributed track** (families A and B): one machine → a fleet.
- **Device track** (family D): one event from hardware to an app, on one machine. This builds on what you already have in `windows_internals/` and `concurrency/`; the lectures turn it into a method for any device design question.
- Family C (low-level design) and family E (coding pieces) appear where they pair naturally.

---

## The plan

| # | Lecture | Track | Core question | Practice right after |
|---|---|---|---|---|
| **002** | **The read path: from one server to a read-heavy system** | Distributed | What happens to one request, and which piece does each forced move add (index, separate DB, many stateless servers + load balancer, object storage, cache, replicas)? | `a01` URL shortener · drill 3 · bridge `e02` |
| 003 | The device pipeline: one event from hardware to an app | Device | Which context runs each stage, which may wait, how to size every buffer, what happens when one fills | `d01` (redo) · `e04` |
| 004 | The write path and asynchronous work: queues, workers, retries, idempotency | Distributed | What do you do when the work can't (or shouldn't) happen inside the request? | `a04` · `e03` |
| 005 | Shared state and contention: atomic updates, locks vs atomic operations, unique IDs | Distributed | What happens when two requests change the same thing at the same time, on different machines? | `b01` · `e01` · `a05` (driver claim) |
| 006 | Partitioning and replication: shard keys, hot keys, consistent hashing, quorums | Distributed | What do you do when the data or the write rate doesn't fit on one machine? | `b02` · `a02` |
| 007 | Real-time delivery: polling, long polling, server-sent events, WebSockets, connection routing | Distributed | How does the server reach a client that didn't ask? | `a03` · `a05` |
| 008 | Persistence on a device: power loss, flash, safe updates | Device | How does state survive power loss at any instant? | `d02` · `d04` |
| 009 | Low-level design: entities, state machines, extension points | C | How do you turn use cases into classes that can change without a rewrite? | `c01` · `c02` |
| 010 | Latency pipelines and measurement | Device | Where does time go in a multi-stage pipeline, and how do you measure each stage? | `d05` · `d03` |
| 011 | Reliability: timeouts, retries without storms, backpressure, health checks, what to monitor | Both | How does a system stay up when its parts don't? | Redo the lowest-scoring case so far |

**Order rule:** the default is the table order, alternating tracks. If a practice review shows a specific weakness (for example "deep dives on shared state are always at 1"), the lecture that covers it moves up, the same way the LeetCode gradient works. Write-ups and reviews in `practice/` decide this, not the calendar.

---

## Done

| # | Lecture | Read? | Paired case attempted? |
|---|---|---|---|
| 001 | `001-system_design_orientation.md` (map, skeleton, families) | — | — |
| 002 | `002-the_read_path.md` | — | `a01`: — |
