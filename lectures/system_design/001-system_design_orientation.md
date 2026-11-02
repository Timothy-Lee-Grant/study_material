2026_11_01_22_50-(System-Design-Orientation)

# Lecture 001: System Design Orientation: The Families of Design Questions, One Skeleton for All of Them, and How to Practice

> **For:** Timothy · **Date:** 2026-11-01
> **Prerequisites:** none for the core. Links where you already have depth: `windows_internals/014` (a full device-to-app design), `leetcode/012` §1 and §4.7 (the data-structure design method and a coding-style rate limiter), `yarp/009` (distributed systems fundamentals), `general_skills/001` (thinking in states).
> **Why this lecture:** you've reached the stage where design questions show up, and you've noticed they come in visibly different shapes: "design Twitter / design Uber"; a device with a buffer that pulls a line low, where you have to get the data up to a GUI while some operations block; and "design this one component". You want (1) a way to **classify** what you're being asked so you can study each family on purpose, (2) the ideas you'd need **if the interview were tomorrow**, (3) a **study method**, and (4) the difference between a **design** rate limiter and a **coding** rate limiter, and how studying one feeds the other.
> **Format notes:** top-down. 🟢 = own it, 🔵 = know the contract (what it does and when to use it), ⚫ = black box for now. Every example problem includes its full statement.

---

## Core ideas (the answer key)

1. **Every design question tests the same thing:** turning a vague need into components, the contracts between them, where the state lives, and how data flows, with every choice **justified by a requirement** and a **trade-off said out loud**. There is no single right answer; the process is what's graded.
2. **Classify a question with three questions:** *What is scarce?* (machines and network vs CPU time, memory and latency on one box) · *What is the unit of design?* (services, one component, classes, or a function) · *Will I write runnable code?*
3. **The five families:** product design (Twitter, Uber) · infrastructure / component design (rate limiter, key-value store, queue) · low-level / object-oriented design (parking lot, elevator) · device / systems design (interrupt, buffer, driver, reader, UI) · design-then-code (implement a rate limiter or LRU cache).
4. **One skeleton works for all five:** requirements → interface → state → one traced flow → components → deep dive on the hardest constraint → failures and trade-offs. Only the vocabulary inside each step changes.
5. **Requirements come first and split in two:** *functional* (what it does) and *non-functional* (how well: latency, throughput, availability, consistency, power). The non-functional ones decide the design.
6. **The same few ideas appear at both scales:** a buffer between a fast producer and a slow consumer (ring buffer ↔ message queue), deferring work out of a hot path (DPC/work item ↔ async worker), refusing work you can't absorb (overflow policy ↔ rate limiting / backpressure), keeping a copy close to the reader (CPU cache ↔ Redis/CDN).
7. **Back-of-envelope numbers are a design tool, not a ritual:** a day is ~10⁵ seconds, so 1 million events per day ≈ 12 per second. Do the math only when it changes a decision.
8. **Blocking is a placement question:** wherever something waits, ask *which thread or context is allowed to wait here, and what else stops while it does?* That question drives both the device design and the "why add a queue" answer in product design.
9. **The design version and the coding version of "rate limiter" ask different things:** design = *where it sits, where its state lives across many servers, what happens when that store fails*; coding = *the exact algorithm and data structure, its invariant, and correct edge cases in runnable code*. The coding answer is one box's deep dive inside the design answer.
10. **You get better by doing timed, spoken, 45-minute attempts and comparing against a reference,** not by reading more designs. One attempt plus one voice recall beats three articles.

---

## Table of Contents

- [0. Direct answers](#0-direct-answers)
- [1. What a design interview actually tests](#1-what-a-design-interview-actually-tests)
- [2. Classifying the question: three questions, five families](#2-classifying-the-question-three-questions-five-families)
- [3. The one skeleton](#3-the-one-skeleton)
- [4. Toolkit A: the distributed-systems building blocks](#4-toolkit-a-the-distributed-systems-building-blocks)
- [5. Toolkit B: the single-machine / device building blocks](#5-toolkit-b-the-single-machine--device-building-blocks)
- [6. Same idea, two scales](#6-same-idea-two-scales)
- [7. The skeleton applied once: a small news feed](#7-the-skeleton-applied-once-a-small-news-feed)
- [8. Rate limiter, two ways](#8-rate-limiter-two-ways)
- [9. How to study and practice](#9-how-to-study-and-practice)
- [Common mistakes](#common-mistakes)
- [Interview relevance](#interview-relevance)
- [Self-check questions](#self-check-questions)
- [Sources](#sources)

---

## 0. Direct answers

1. **Are "design Twitter" and "device → GUI" fundamentally different?** In vocabulary and in what's scarce, yes. In structure, no. Twitter is limited by *many users across many machines* (network, storage, replication). The device problem is limited by *one machine's time and concurrency* (interrupt latency, who may block, buffer overflow). Both are answered by the same steps: requirements, interface, state, flow, components, hardest constraint, failures (§3).
2. **How do I classify what I'm asked?** Ask what's scarce, what the unit of design is, and whether you'll write code (§2). That puts any prompt in one of five families.
3. **"Design one component" is its own family** (infrastructure / component design). The whole 45 minutes go into one building block, such as a rate limiter, a cache or a queue, at much greater depth than it would get as one box in a product design.
4. **If the interview were tomorrow:** memorize the skeleton and its time budget (§3), learn the toolkit for the family your role leans toward (§4 for services, §5 for platform/device roles), and do **one** timed attempt out loud tonight (§9.1). That's the whole plan.
5. **How do I study?** Timed, spoken attempts → compare to a reference → write the delta → voice recall on a walk (§9).
6. **Rate limiter as design vs as coding:** different deliverables (a diagram with justified placement and failure behavior vs working code with an invariant), and they share the algorithm (§8). Studying design tells you *which* algorithm and why. Studying coding makes your deep-dive box precise.

---

## 1. What a design interview actually tests

A coding round asks: *can you produce a correct answer to a fully specified problem?* A design round asks something different: *given an underspecified need, can you decide what matters, build something that works, and explain why it's shaped that way?*

The prompt is deliberately vague ("design Uber"). That vagueness is part of the test. What the interviewer is watching for:

| They're checking | What it looks like from you |
|---|---|
| **Scoping** | You ask what's in and out, and you write it down before drawing anything |
| **A working end-to-end path** | At some point there's a complete flow from input to output, even if it's simple |
| **Justified choices** | "I'm adding a queue *because* writes arrive in bursts and the database can't absorb the peak" |
| **Trade-offs** | You name what each choice costs, not only what it buys |
| **Depth on the hard part** | You find the constraint that actually makes this problem hard and go deep there |
| **Driving** | You lead the conversation and check in; you don't wait to be pulled along |

Two things follow from that table:

- **There's no answer key.** Two strong candidates can draw different systems. What's graded is whether each box exists *for a reason you said*.
- **You're expected to talk the whole time.** Silence hides the reasoning, and reasoning is the thing being graded. (This also fits how you think: your gaps show up when you say things aloud.)

---

## 2. Classifying the question: three questions, five families

### 2.1 The three questions

Ask these in the first minute, silently or out loud:

1. **What is scarce?**
   - *Machines and the network between them* (many users, data bigger than one machine, servers that fail) → distributed toolkit (§4).
   - *Time, memory and concurrency on one machine* (interrupt latency, a thread that must not block, a buffer that can overflow) → single-machine toolkit (§5).
2. **What is the unit of design?** Services and databases · one component · classes and their methods · a function or data structure.
3. **Will I write runnable code?** No (diagram and discussion) · some (pseudocode or interfaces) · yes (it has to run and pass tests).

### 2.2 The five families

| Family | Typical prompts (full statements below) | Scarce | Unit | Code? | What depth means here |
|---|---|---|---|---|---|
| **A. Product design** | Design Twitter; design Uber; design a chat app | Machines, network, storage | Services + databases | No | Data model, read/write paths, scaling the hot path, consistency |
| **B. Infrastructure / component design** | Design a distributed rate limiter; a key-value store; a message queue; a cache | Machines, plus correctness under concurrency | One component, deeply | Rarely | Partitioning, replication, failure modes, the component's internal algorithm |
| **C. Low-level / object-oriented design** | Design a parking lot; an elevator system; a vending machine | Clarity and extensibility | Classes, interfaces, state | Often pseudocode | Entities, responsibilities, state transitions, how it extends |
| **D. Device / systems design** | A device holds a line low while its FIFO has data; get the data to a GUI | Time, concurrency, one machine | Hardware → driver → app → UI | Sometimes sketches | Who runs where, what may block, buffer sizing, overflow, latency |
| **E. Design-then-code** | Implement a rate limiter; LRU cache; a packet parser | Correctness and complexity | Data structures + functions | Yes | Invariant, complexity, edge cases, tests |

Two notes on naming, because interviewers aren't consistent:

- Recruiters often say "system design" for A and B both. Some companies call family B "infrastructure design" and family C "low-level design" or "object-oriented design." **Ask the recruiter what the round is called and what a typical question looks like.** That one email decides what you study for it.
- Family D rarely has a standard name. It shows up in platform, OS, driver, embedded and device roles, often folded into a "technical" or "systems" round. If your target roles are platform-heavy, D is not a side topic; it's likely the main one.

**Honest sizing:** there's also **ML system design** (recommendation pipelines, training/serving). ⚫ Skip it unless a role names it.

### 2.3 The prompts, stated in full

- **A. Design Twitter (a "news feed").** Users can post short text messages. Users can follow other users. Each user has a home timeline showing recent posts from the people they follow, newest first. Assume hundreds of millions of users, many more reads than writes, and a timeline that should load in well under a second.
- **A. Design Uber (ride hailing).** Riders request a ride from their location. Nearby available drivers get offered the ride; one accepts. Both see each other's location update live until drop-off. Assume a large city's worth of drivers sending location every few seconds.
- **B. Design a distributed rate limiter.** A service runs on many servers behind a load balancer. Limit each client (by API key) to N requests per time window across *all* servers combined. Requests over the limit are rejected quickly. The limiter must add very little latency and must not become a single point of failure.
- **C. Design a parking lot.** A lot has several levels with spots of different sizes (motorcycle, compact, large). Vehicles enter, get assigned a fitting spot, and pay on exit based on time parked. Design the classes, their responsibilities and their interactions.
- **D. Device to GUI.** An external device produces data bytes in bursts and stores them in a 64-entry hardware FIFO. While the FIFO is non-empty, the device holds an active-low interrupt line asserted. Reading a byte uses a call that blocks until the transfer completes. Design the path that gets these bytes into a desktop application and displays them in its GUI, without losing data during bursts and without an interrupt storm. (`windows_internals/014` works this one fully.)
- **E. Implement a rate limiter.** Write a class with `allow(key, now) -> bool` that returns `True` if the request from `key` at time `now` (seconds) is allowed under a limit of at most `capacity` requests in a burst refilled at `rate` per second, and `False` otherwise. (Worked in §8.2.)

---

## 3. The one skeleton

Here's the procedure. It's the same seven steps for every family; §3.2 shows what each step looks like in each one.

### 3.1 The steps and the clock (45-minute round)

| # | Step | Time | Output on the board |
|---|---|---|---|
| 1 | **Requirements** | ~5 min | A short list of *functional* requirements (2–4 core features) and *non-functional* ones (latency, scale, availability, consistency, power), plus what's out of scope |
| 2 | **Interface** | ~5 min | The contract with the outside world: API endpoints, function signatures, or the hardware/driver interface |
| 3 | **State** | ~3 min | The core entities and where each piece of state lives (which store, which buffer, which object) and who owns it |
| 4 | **One traced flow** | ~5 min | One request or event followed end to end, naming every component it passes through |
| 5 | **Components** | ~10 min | The boxes-and-arrows diagram that makes step 4 work; simple first |
| 6 | **Deep dive** | ~10 min | The hardest constraint from step 1, solved properly |
| 7 | **Failures and trade-offs** | ~5 min | What breaks, what happens then, and what you'd change at 10× scale |

Some frameworks merge steps 4 and 5 or add a separate estimation step. The order matters more than the exact list: **requirements before boxes, a working path before optimization, depth only on the constraint that matters.**

Why step 4 (one traced flow) is there: it's the step that keeps a diagram honest. A box with no request passing through it is decoration. This is also the question you already ask by reflex: *where does this run, and who calls it?*

### 3.2 The skeleton in each family

| Step | A. Product (Twitter) | B. Component (distributed rate limiter) | C. Low-level (parking lot) | D. Device → GUI | E. Code (rate limiter) |
|---|---|---|---|---|---|
| Requirements | Post, follow, read timeline; read-heavy; <~500 ms timeline | N requests/window per key, across servers; tiny added latency; behavior when the limiter's store is down | Spot sizes, assign, pay on exit; easy to add a spot type | No data loss in bursts; no interrupt storm; GUI never freezes | Burst `capacity`, refill `rate`; per key |
| Interface | `POST /posts`, `POST /follow`, `GET /timeline` | `allow(key) -> allowed, retry_after` called by every server | `enter(vehicle) -> ticket`, `exit(ticket) -> fee` | Interrupt line + blocking read; app gets `read()` or a callback | `allow(key, now) -> bool` |
| State | User, Post, Follow; where timelines are stored | Counters/tokens per key in a shared store | Lot, Level, Spot, Ticket | Hardware FIFO, driver ring buffer, app queue | Dict of key → bucket (tokens, last time) |
| One traced flow | A post going into a follower's timeline | A request: server → limiter store → allow/deny | A car entering then leaving | One byte from the device to a pixel | One call to `allow` |
| Components | Load balancer, app servers, DB, cache, fan-out workers | Gateway/middleware, shared store (e.g. Redis), local fallback | Classes + responsibilities | ISR, deferred worker, buffer, reader thread, UI thread | The class and its methods |
| Deep dive | Fan-out on write vs on read; celebrity accounts | Atomic updates across servers; accuracy vs coordination cost | Assignment strategy; state transitions | Where the blocking read runs; buffer size vs burst | Time math; idle buckets |
| Failures | DB replica lag, cache miss storms | Store down: fail open or closed? | Full lot, lost ticket | Overflow policy; device stops responding | Clock jumps; many keys |

Read the table by row and you'll see the claim from the start of this lecture: **the steps don't change, only the vocabulary inside them does.**

---

## 4. Toolkit A: the distributed-systems building blocks

This is what you need for families A and B. `yarp/009` goes deeper on replication, consistency and CAP.

### 4.1 The standard pieces

| Piece | What it does | Reach for it when | Tag |
|---|---|---|---|
| **Client → load balancer → app servers** | Spreads requests across identical servers | Always, as the starting skeleton | 🟢 |
| **Stateless app servers** | Servers keep no per-user state between requests, so any server can take any request | You need to add servers freely | 🟢 |
| **Relational database (SQL)** | Tables, joins, transactions | Data has relationships and you need correctness (payments, accounts) | 🟢 |
| **Key-value / wide-column / document store (NoSQL)** | Simple lookups by key at huge scale; easier to partition | Access is "get by ID" and volume is enormous | 🔵 |
| **Cache (e.g. Redis, Memcached)** | Keeps hot data in memory close to the app | Reads repeat and the source is slow; you accept data that may be slightly stale | 🟢 |
| **Message queue / log (e.g. Kafka, SQS, RabbitMQ)** | Producers put work in; workers take it out later | Work can be done later; bursts would overwhelm the next stage; you want stages decoupled | 🟢 |
| **Blob/object storage + CDN** | Stores large files; a CDN serves copies near users | Images, video, static files | 🔵 |
| **Replication** | Copies of the same data on several machines | Survive machine failure; spread reads | 🟢 |
| **Partitioning / sharding** | Splits data across machines by a key | One machine can't hold or serve all of it | 🟢 |
| **Consistent hashing** | Assigns keys to machines so adding a machine moves few keys | Sharding where machines come and go | 🔵 |
| **Consistency vs availability (CAP)** | During a network partition, you choose: reject requests, or serve possibly stale data | Any replicated store; say which side you pick and why | 🔵 |
| **Idempotency** | Doing an operation twice has the same effect as once | Retries are possible (they always are): payments, message processing | 🟢 |
| **Leader election, consensus (Raft/Paxos)** | Machines agree on one value or one leader | Family B deep dives (a key-value store) | ⚫ |

### 4.2 Back-of-envelope numbers

Do estimation only when it changes a decision (whether you need sharding, a cache, or a queue). The handful worth knowing:

1. **A day has 86,400 seconds; use ~10⁵.**
2. Name the quantity: `events_per_day`. Then `events_per_second = events_per_day / 10⁵`.
3. Example: 100 million users each reading their timeline 10 times a day → `events_per_day = 10⁹` → `events_per_second ≈ 10⁹ / 10⁵ = 10⁴` (exact: 11,574). Peak is often 2–3× the average.
4. Then ask the decision question: can one database serve 10⁴ reads/second? Roughly, a well-tuned single node can handle thousands of simple queries per second, so this is where a cache or read replicas enter.

Approximate latencies (orders of magnitude; they vary by hardware):

| Operation | Approximate time |
|---|---|
| Main memory reference | ~100 ns |
| SSD random read | ~tens to ~100 µs |
| Round trip inside one datacenter | ~0.5 ms |
| Spinning-disk seek | ~10 ms |
| Round trip across a continent / ocean | ~50–150 ms |

The useful conclusion: **a network hop costs about as much as thousands of memory reads.** That's the whole argument for caches and for doing less per request.

---

## 5. Toolkit B: the single-machine / device building blocks

This is what you need for family D, and it's also what makes your family-E code correct. You've already built much of it in `windows_internals/005`, `008`, `014` and `concurrency/002–003`.

| Piece | What it does | The question it answers | Tag |
|---|---|---|---|
| **Producer–consumer with a buffer** | A producer adds items; a consumer removes them at its own pace | "The producer is bursty and the consumer is slower: what absorbs the difference?" | 🟢 |
| **Ring (circular) buffer** | Fixed-size array with a head and tail index; no allocation per item | "Where do bytes wait between the interrupt path and the reader?" | 🟢 |
| **Blocking vs non-blocking vs async** | Blocking: the caller's thread waits. Non-blocking: returns immediately ("nothing yet"). Async: returns now, completes later | "Which context is allowed to wait here?" | 🟢 |
| **Interrupt vs polling** | The device signals vs software checks on a schedule | "Do I need low latency, or is a periodic check enough and cheaper?" | 🟢 |
| **Level- vs edge-triggered** | Level: asserted as long as the condition holds. Edge: one event per transition | "Why does an unmasked level interrupt fire again immediately?" (storms) | 🟢 |
| **Split interrupt handling** | Do the minimum at interrupt time (acknowledge, mask, schedule); do the rest later in a context that may wait | "Where does the slow or blocking work go?" | 🟢 |
| **Threads and wait queues** | A waiting thread sits on the wait list of what it waits for and costs no CPU | "How does the reader sleep until data arrives?" | 🟢 |
| **Backpressure / overflow policy** | When the buffer is full: drop oldest, drop newest, or stop the producer | "What happens in the worst burst?" | 🟢 |
| **The UI-thread rule** | GUI frameworks let only one thread touch the UI; anything slow runs elsewhere and posts results back | "Why doesn't the window freeze?" | 🟢 |
| **Latency budget** | Add up the worst-case time per stage and compare to how fast the buffer fills | "Is 64 entries enough?" | 🟢 |

Sizing, as a numbered derivation (the shape of `windows_internals/014` §6):

1. Name the quantities: `fill_rate` (bytes/second arriving in a burst), `drain_delay` (worst-case time before the reader starts draining), `fifo_capacity` = 64.
2. Bytes that arrive before draining starts: `arrived = fill_rate × drain_delay`.
3. Valid set: no loss as long as `arrived <= fifo_capacity`.
4. If that fails, you have three levers: drain sooner (lower `drain_delay`), add a bigger software buffer behind the FIFO, or slow the producer.

---

## 6. Same idea, two scales

This is the link you noticed between the two kinds of questions. The ideas below show up in both toolkits under different names. Learning them once, as ideas, is how studying one family speeds up the others.

| Idea | Single machine (family D / E) | Many machines (family A / B) |
|---|---|---|
| **Absorb a burst between a fast producer and a slower consumer** | Hardware FIFO, ring buffer | Message queue (Kafka, SQS) |
| **Do the minimum now, the rest later in a context that can wait** | ISR → deferred procedure / work item / threaded handler | API server enqueues; background workers process |
| **Refuse what you can't absorb** | Overflow policy; mask the interrupt | Rate limiting; load shedding; HTTP 429 |
| **Keep a copy closer to whoever reads it** | CPU caches; a per-thread local copy | Redis cache; CDN; read replicas |
| **Only one writer at a time for shared state** | Lock, spin lock, atomic instruction | A partition owner, a single leader, an atomic `INCR` in the store |
| **Don't let one waiting thing block everyone** | Never block on the UI thread or at raised IRQL | Never make a user request wait on a slow downstream call; go async |
| **Survive a lost or repeated message** | Sequence numbers, checksums (your packet parser) | Idempotency keys, retries, at-least-once delivery |
| **Wake the consumer instead of having it check constantly** | Interrupt + wait queue vs polling | Push (WebSockets, notifications) vs client polling |

A sentence to say in an interview when you see the parallel: *"This is a producer–consumer problem: the producer is bursty, so I need a buffer sized for the worst burst and an explicit policy for when it fills."* That one sentence works for a device FIFO and for a write-heavy service.

---

## 7. The skeleton applied once: a small news feed

The full statement is in §2.3 (Design Twitter). This is a compressed walk-through so you can see the steps produce a design. A real answer spends longer on each.

1. **Requirements.** Functional: post, follow, read home timeline. Non-functional: read-heavy (reads ≫ writes), timeline under ~500 ms, eventual consistency is acceptable (a post may take a few seconds to appear for followers). Out of scope: search, likes, media.
2. **Interface.** `POST /posts {text}` · `POST /follow {target_user_id}` · `GET /timeline?cursor=...` returns posts, newest first, a page at a time.
3. **State.** User, Post (id, author_id, text, created_at), Follow (follower_id, followee_id). Posts in a database partitioned by post id or author; a precomputed timeline per user in a cache (list of post ids).
4. **One traced flow (a post).** Client → load balancer → app server → write Post to the database → put a "new post by author X" event on a queue → a fan-out worker reads X's followers → appends the post id to each follower's cached timeline. Reading: `GET /timeline` → app server → read the cached list of ids → fetch the posts (mostly from cache).
5. **Components.** Load balancer, stateless app servers, posts database, follow graph store, queue, fan-out workers, timeline cache.
6. **Deep dive: fan-out on write vs on read.** Writing each post into every follower's timeline makes reads cheap but writes expensive. For an account with 50 million followers, one post means 50 million appends. Common answer: **hybrid**. Fan out on write for normal accounts; for very large accounts, skip fan-out and merge their recent posts in at read time.
7. **Failures and trade-offs.** If the cache loses a timeline, rebuild it from the follow graph and recent posts (slow but correct). If fan-out workers fall behind, followers see posts late; that was accepted in step 1. At 10×: more partitions for posts, more cache nodes, the hybrid threshold tuned.

Notice that every box in step 5 is there because of a line in steps 1–4. That's the property you're aiming for.

For the device version of this walk-through, read `windows_internals/014` with the §3.2 table next to it and label which section is which step.

---

## 8. Rate limiter, two ways

### 8.1 What changes between the two rounds

| | Design round (family B) | Coding round (family E) |
|---|---|---|
| **The question** | Limit each client to N requests/window across a fleet of servers | Implement `allow(key, now) -> bool` |
| **Graded on** | Placement, shared state, failure behavior, latency, trade-offs | Correct algorithm, invariant, complexity, edge cases, clean runnable code |
| **Output** | A diagram and a spoken argument | Code that runs on examples |
| **Where "time" lives** | Distributed clocks, windows across servers | A `now` parameter you're handed |
| **Concurrency** | Many servers updating one counter at once | Usually single-threaded unless asked |
| **The algorithm** | One box, chosen with reasons | Most of the 45 minutes |

The relationship: **the coding round is the deep dive of one box in the design round.** In the design round you say "I'll use a token bucket because clients may burst briefly but must average N per second" and move on to where the counters live. In the coding round, that sentence is the whole problem.

### 8.2 The coding version

Full problem statement in §2.3 (E). The four standard algorithms:

| Algorithm | State per key | Behavior | Trade-off |
|---|---|---|---|
| **Fixed window counter** | count, window start | At most N per clock window (e.g. per minute) | Simple; allows up to 2N across a window boundary |
| **Sliding window log** | a queue of timestamps | Exactly N in any trailing window | Precise; memory grows with N (`leetcode/012` §4.7 implements this one) |
| **Sliding window counter** | two counts | Weighted estimate of the trailing window | Small memory, approximate |
| **Token bucket** | tokens, last time | Bursts up to `capacity`, long-run `rate` per second | Small memory, allows controlled bursts; very common |

Token bucket, with every name defined before it's used:

- `capacity`: the most tokens the bucket can hold = the largest allowed burst.
- `rate`: tokens added per second = the long-run limit.
- `tokens`: tokens available right now. Valid set: `0 <= tokens <= capacity`.
- `last`: the time `tokens` was last brought up to date.

Derivation of `allow`, one step at a time:

1. Time passed since the last update: `elapsed = now - last`.
2. Tokens earned in that time: `elapsed × rate`.
3. Add them, but stay inside the valid set: `tokens = min(capacity, tokens + elapsed × rate)`.
4. Record the update: `last = now`.
5. A request is allowed when a whole token is available: `tokens >= 1`. If so, spend it (`tokens -= 1`) and return `True`; otherwise return `False`.

The code is in `code/token_bucket.py`:

```python
class TokenBucket:
    def __init__(self, capacity: float, rate: float):
        self.capacity = capacity
        self.rate = rate
        self.tokens = capacity        # start full
        self.last = None

    def allow(self, now: float) -> bool:
        if self.last is not None:
            elapsed = now - self.last
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        self.last = now
        if self.tokens >= 1:
            self.tokens -= 1
            return True
        return False


class RateLimiter:
    def __init__(self, capacity: float, rate: float):
        self.capacity, self.rate = capacity, rate
        self.buckets = {}             # key -> TokenBucket

    def allow(self, key: str, now: float) -> bool:
        if key not in self.buckets:
            self.buckets[key] = TokenBucket(self.capacity, self.rate)
        return self.buckets[key].allow(now)
```

Trace with `capacity = 3`, `rate = 1` per second (from running it on 2026-11-01):

| `now` | tokens before | earned | tokens after refill | allowed? | tokens after |
|---|---|---|---|---|---|
| 0.0 | 3 (start) | 0 | 3 | ✅ | 2 |
| 0.1 | 2 | 0.1 | 2.1 | ✅ | 1.1 |
| 0.2 | 1.1 | 0.1 | 1.2 | ✅ | 0.2 |
| 0.3 | 0.2 | 0.1 | 0.3 | ❌ | 0.3 |
| 0.9 | 0.3 | 0.6 | 0.9 | ❌ | 0.9 |
| 1.3 | 0.9 | 0.4 | 1.3 | ✅ | 0.3 |
| 1.4 | 0.3 | 0.1 | 0.4 | ❌ | 0.4 |
| 5.0 | 0.4 | 3.6 | 3 (capped) | ✅ | 2 |
| 5.0 | 2 | 0 | 2 | ✅ | 1 |
| 5.0 | 1 | 0 | 1 | ✅ | 0 |
| 5.0 | 0 | 0 | 0 | ❌ | 0 |

A separate key (`bob` at 0.3) gets its own full bucket and is allowed. Complexity: O(1) time per call, O(number of keys) memory.

Follow-ups you should expect: *idle keys pile up* (evict buckets not touched for a while, e.g. with an LRU or a periodic sweep); *thread safety* (a lock per bucket, or per key shard); *the clock going backwards* (clamp `elapsed` to `>= 0`).

### 8.3 The design version

Full problem statement in §2.3 (B). Run the skeleton:

1. **Requirements.** Per API key, N requests per window, across all servers. Added latency: about a millisecond or less. Over-limit responses: HTTP 429 with a `Retry-After` header. Decide early: *if the limiter's store is unreachable, do we let traffic through (fail open) or reject it (fail closed)?* Most public APIs fail open (availability beats strictness); a limiter protecting a fragile backend may fail closed.
2. **Interface.** Inside the fleet: `check(key) -> (allowed, retry_after)`. Outside: unchanged API, plus 429 responses and rate-limit headers.
3. **State.** Per key: token count and last-refill time (or a counter per window). It must be **shared**, because a client's requests land on different servers.
4. **Flow.** Request → load balancer → server (or API gateway) → limiter check against the shared store → allowed: handle it; denied: 429.
5. **Components.** Placement options: in an **API gateway** in front of the servers, as **middleware** inside each server, or as a **separate service**. Shared store: an in-memory store like Redis, partitioned by key.
6. **Deep dive: atomicity across servers.** Two servers checking the same key at once can both read "1 token left" and both allow. Fix: make read-check-update **one atomic operation in the store** (an atomic increment, or a small script that runs atomically inside the store). Second deep dive: the extra network hop on every request. Option: each server keeps a local bucket with a slice of the limit and syncs periodically; faster, but less precise. Name it as a trade-off: **precision vs coordination cost**.
7. **Failures.** Store down → the fail-open/closed choice from step 1, plus a local fallback limit. Hot keys (one client hammering) → that key's partition is busy; local pre-filtering helps. Clock differences between servers → use the store's time or token math that doesn't depend on server clocks agreeing.

Notice that step 6's atomicity problem is **the "only one writer at a time" row of §6**, at fleet scale. On one machine you'd use a lock; across machines the store has to provide the atomic operation.

### 8.4 How preparing for one helps the other

- **Design → coding:** the design round forces you to state requirements (burst allowed? exact or approximate?). That's exactly what picks the algorithm in the coding round, and saying it first is the strongest opening move there too.
- **Coding → design:** having written the token bucket, your deep dive is precise ("the state is two numbers per key; refill is computed lazily on each check, so there's no timer per key"), which is the depth interviewers look for in step 6.
- **Shared habit:** both rounds reward writing the interface and one example call with its exact output **before** building anything. In the coding round that's `allow("alice", 0.0) -> True`; in the design round it's the API and one traced request.

Other problems that exist in both forms: LRU cache (cache layer vs `get/put` class), key-value store (distributed store vs an in-memory map with TTL), message queue (Kafka-like system vs a bounded blocking queue), URL shortener (service vs encode/decode functions), logger/telemetry pipeline (fleet ingestion vs a ring-buffer logger).

---

## 9. How to study and practice

### 9.1 If the interview is tomorrow

1. Read §3 until you can write the seven steps and the time budget from memory.
2. Read the toolkit for your round's likely family: §4 for service roles, §5 + `windows_internals/014` for platform/device roles. §6 for both.
3. **Do one timed attempt tonight:** 45 minutes, out loud, on paper. Pick the prompt closest to the role. Use the skeleton literally.
4. In the interview, say the skeleton out loud at the start: *"I'll start with requirements, then the interface and data, trace one request, draw the components, and then go deep on whatever turns out to be the hardest constraint."* It shows structure and buys you a minute to think.

### 9.2 The practice loop (one case per session)

1. **Attempt (45 min, timed, spoken, on paper or a whiteboard tool).** No references. If you're stuck on a choice, pick one, say why, move on.
2. **Compare (20 min)** against one reference solution for that prompt.
3. **Write the delta (10 min)** in a short file: what the reference had that you didn't, what you over-built, which requirement you missed, which toolkit piece you couldn't explain.
4. **Voice recall on a walk** the next day: explain the design and its biggest trade-off from memory. Send it as a recall check if you want it analyzed.
5. **Build the bridge piece** when there is one: if the case contains a component you could code (token bucket, LRU, bounded queue, ring buffer), implement it in ~30 minutes. That's the family-E version for free.

### 9.3 A starting case order

Ordered so each case adds one new idea:

| # | Case | New idea it forces |
|---|---|---|
| 1 | URL shortener | Read-heavy, key-value store, ID generation, caching |
| 2 | Rate limiter (design + code) | Shared state, atomicity, fail open/closed (§8) |
| 3 | News feed / Twitter | Fan-out, precomputed views, read vs write paths |
| 4 | Chat (one-to-one and groups) | Persistent connections, delivery and ordering, offline users |
| 5 | Notification system | Queues, retries, idempotency, fan-out to many channels |
| 6 | Ride hailing / Uber | Location updates at high frequency, geo-indexing, matching |
| 7 | Distributed key-value store | Partitioning, replication, consistency choices (family B) |
| 8 | Parking lot or elevator | Classes, state machines (family C; `general_skills/001`) |
| D-track | Device → GUI (done: `windows_internals/014`), a ring-buffer logger on a device, a telemetry collector from many sensors | Placement of blocking work, sizing, overflow, UI thread |

If your interviews lean platform/device, alternate one A/B case with one D-track case.

### 9.4 Resources, honestly sized (checked 2026-11-01)

| Resource | What it's good for | Sizing |
|---|---|---|
| **Hello Interview, "System Design in a Hurry"** (free sections) | A delivery framework close to §3, core concepts, worked cases with time budgets; also a low-level design track | 🟢 Best first stop |
| **Alex Xu, *System Design Interview* vol. 1 (and ByteByteGo)** | Many classic cases (rate limiter, URL shortener, news feed, chat) walked through | 🟢 Good case library |
| **Martin Kleppmann, *Designing Data-Intensive Applications*** | Why replication, partitioning, transactions and consistency work the way they do | ⚫ Not for tomorrow. Read chapters when a deep dive keeps stopping you |
| **Your own `windows_internals/005`, `008`, `014`; `concurrency/002–003`** | Family D toolkit | 🟢 Already yours; use them as the D-track reference |
| **Mock interviews with a person** | Practicing driving and talking while someone interrupts | 🟢 Once you've done 3–4 solo cases |

**A candid note:** this area has an endless supply of articles and videos, and reading designs feels productive while building almost none of the skill being graded (driving a 45-minute conversation). The first item in your plan is an attempt, not a reading list. Measure progress in attempts done, not pages read.

---

## Common mistakes

| Mistake | Why it hurts | Instead |
|---|---|---|
| Drawing boxes in minute one | Boxes without requirements can't be justified | Requirements first, always, even if brief |
| Naming technology without a reason ("use Kafka") | Sounds memorized; invites "why?" you can't answer | Say the requirement the piece serves, then name it |
| Rabbit-holing on one box | You run out of time without a complete path | Get a working end-to-end design first; deep dive later |
| Designing for scale nobody asked for | Over-engineering is graded as poor judgment | Size the design to the stated requirements; mention what changes at 10× |
| No failure discussion | Real systems fail; interviewers always ask | Reserve the last 5 minutes for "what breaks" |
| Going silent to think | Hides reasoning, the thing being graded | Think out loud, even when unsure: "two options here; I'm leaning toward…" |
| Putting a blocking operation in a context that can't wait | In family D this is a correctness bug, not a style issue | Ask "which context may wait here?" at every arrow |
| In the coding version, coding before fixing the interface | Wrong inputs/outputs waste the round | Write the signature and one example call with its exact output first |

---

## Interview relevance

Sentences that carry well across families:

- *"Before I draw anything, let me pin down what it has to do and what 'good' means: latency, scale, and what happens when something fails."*
- *"This box is here because of [requirement]. The cost is [trade-off]."*
- *"Let me trace one request through what I have so far to check it works end to end."*
- *"The hardest constraint here is [X], so that's where I'd like to go deep."*
- *"This is a producer–consumer problem: bursty producer, slower consumer. I need a buffer sized for the worst burst and a policy for when it fills."*
- *"If the limiter's store goes down, I'd fail open, because availability matters more than strictness for this API; for a fragile backend I'd choose differently."*

---

## Self-check questions

1. What are the three questions that classify a design prompt?
<details><summary>Answer</summary>What is scarce (machines/network vs time/concurrency on one machine)? What is the unit of design (services, one component, classes, a function)? Will I write runnable code?</details>

2. Put each in a family: "design a key-value store", "design an elevator", "implement an LRU cache", "design Instagram", "get sensor data from a device's FIFO into a desktop app".
<details><summary>Answer</summary>B (infrastructure/component), C (low-level), E (design-then-code), A (product), D (device/systems).</details>

3. List the seven skeleton steps in order.
<details><summary>Answer</summary>Requirements → interface → state → one traced flow → components → deep dive on the hardest constraint → failures and trade-offs.</details>

4. Why does the skeleton include "trace one flow" before "components"?
<details><summary>Answer</summary>It forces every box to exist for a reason: a request or event must pass through it. It turns the diagram into a causal model (who calls whom, where it runs) instead of decoration.</details>

5. 50 million events per day: roughly how many per second, and what's the derivation?
<details><summary>Answer</summary>A day is ~10⁵ seconds, so 5×10⁷ / 10⁵ = 500 per second (exact ≈ 579). Peak maybe 2–3× that.</details>

6. Give three ideas from §6 and their single-machine and fleet-scale names.
<details><summary>Answer</summary>Any three, e.g.: burst absorption (ring buffer ↔ message queue); deferral (ISR → deferred work ↔ enqueue → background worker); refusal (overflow policy ↔ rate limiting / 429); caching (CPU cache ↔ Redis/CDN); single writer (lock/atomic ↔ atomic op in the store / partition owner).</details>

7. In the token bucket, what does each of `capacity`, `rate`, `tokens` and `last` stand for, and what is the valid set for `tokens`?
<details><summary>Answer</summary>`capacity` = largest burst; `rate` = tokens added per second (long-run limit); `tokens` = available right now; `last` = when `tokens` was last updated. Valid set: `0 <= tokens <= capacity` (hence the `min` when refilling).</details>

8. Why is a fixed-window counter weaker than a token bucket?
<details><summary>Answer</summary>A client can send N requests at the end of one window and N more at the start of the next, so up to 2N in a short span across the boundary.</details>

9. In the distributed rate limiter, what goes wrong if each server reads the count, checks it, and writes it back separately? What fixes it?
<details><summary>Answer</summary>Two servers can read the same remaining count at once and both allow, exceeding the limit. Fix: make read-check-update a single atomic operation in the shared store.</details>

10. What is "fail open" vs "fail closed", and how do you choose?
<details><summary>Answer</summary>If the limiter can't reach its store: fail open = allow traffic; fail closed = reject it. Choose by what's worse for this system: a brief burst of unlimited traffic (usually acceptable for a public API) or an outage of legitimate traffic (acceptable when the backend must be protected at all costs).</details>

11. In family D, what question do you ask at every arrow in the diagram?
<details><summary>Answer</summary>Which context is allowed to wait here, and what else stops while it does? (E.g. no blocking at interrupt time or on the UI thread.)</details>

12. How does preparing the coding version of a component help in the design version?
<details><summary>Answer</summary>It makes your deep dive precise: you know the exact state per key, the update rule and its cost, so you can explain the box's internals and its trade-offs instead of naming it.</details>

---

## Sources

- Hello Interview, "System Design in a Hurry": interview types (product vs infrastructure design; low-level design as a separate round) and the delivery framework (requirements → core entities → API → high-level design → deep dives, with time budgets). https://www.hellointerview.com/learn/system-design/in-a-hurry and https://www.hellointerview.com/learn/system-design/in-a-hurry/delivery (checked 2026-11-01)
- Hello Interview, "Low-Level Design in a Hurry", delivery framework. https://www.hellointerview.com/learn/low-level-design/in-a-hurry/delivery (checked 2026-11-01)
- Design Gurus, "Types of System Design Interviews: Product, Infrastructure, OOD, and API Design". https://www.designgurus.io/blog/types-of-system-design-interviews (checked 2026-11-01)
- ExplainThis, "System Design Interview Intro: Product and Infra Design". https://www.explainthis.io/en/swe/system-design-intro (checked 2026-11-01)
- Token bucket code: `code/token_bucket.py`, run with Python 3 on 2026-11-01; the §8.2 trace is its actual output.
- Latency figures in §4.2 are widely cited orders of magnitude, not measurements; actual values vary by hardware.
