# Lecture 7: Concurrency, Connection Pooling, and High-Throughput Networking

Series: YARP Learning Series
Builds on: [Lecture 1 §9](001-http_from_the_wire_to_the_application.md) (streaming), [Lecture 2 §6, §10.2](002-tcp_ip_sockets_and_network_connections.md) (connection cost and reuse), [Lecture 3 §9](003-aspnetcore_request_processing_and_architecture.md) (async/await, thread pool basics), [Lecture 6 §9](006-load_balancing_and_traffic_distribution.md) (shared state across concurrent operations).
Prepares you for: reading YARP's `HttpMessageInvoker`/`SocketsHttpHandler` configuration, its buffer-pooling code, and reasoning correctly about why a proxy that's individually correct can still fall over under real production concurrency.

---

## 1. Learning Objectives

By the end of this lecture you should be able to:

1. Explain, mechanically, why opening a fresh connection per request is expensive, using the specific cost breakdown from Lecture 2 rather than a vague "it's slow" claim.
2. Explain connection pooling's actual knobs (max size, idle timeout, connection lifetime) and the real trade-off each one balances.
3. Precisely distinguish concurrency from parallelism, and correctly classify a given scenario as one, the other, or both.
4. Explain thread pools, `Task`, synchronization, and contention as a connected story — not four separate vocabulary words.
5. Explain backpressure as a general principle (not a proxy-specific trick), and describe what a system does with excess demand instead of just absorbing it silently.
6. Explain why buffering at high concurrency is a memory problem, not just a latency problem, and what streaming and allocation-conscious code actually buy you.
7. Predict, for a system moving from 10 → 1,000 → 100,000 requests/sec, specifically *what* breaks first and why.
8. Explain why every one of these concerns is simultaneously, unavoidably present in YARP's own forwarding path.

---

## 2. Prerequisite Concepts

This lecture assumes you're comfortable with `async`/`await` syntax (stated in your background) but goes past Lecture 3 §9's "await frees the thread" explanation into the *systemic* consequences of that fact under real concurrent load — thread pool sizing behavior, contention, and what happens when the volume of concurrent work genuinely exceeds what the system can absorb. It also assumes Lecture 2's connection-cost mechanics (three-way handshake, TLS, congestion-control slow start) as settled fact — this lecture is largely about what you build *on top of* those costs to avoid paying them repeatedly.

---

## 3. Core Mental Model

```
   1 request → create connection → send request → close connection   (expensive, repeated per request)
```
versus
```
   many requests → REUSE a small pool of already-open connections   (expensive part paid rarely, amortized)
```

The one sentence for this entire lecture: **every technique here — pooling, async I/O, backpressure, streaming — exists because "handle each unit of work in complete isolation, from scratch" doesn't scale, and the fix is always some version of "share and reuse expensive resources, and explicitly refuse to accept more work than you can actually do."** That second half — refusing excess work deliberately, rather than accepting it and quietly degrading — is the thread connecting concurrency, backpressure, and memory management into one coherent story by the end of this lecture.

---

## 4. The Problem — Per-Request Connections

### 4.1 What "create → send → close" actually costs, itemized

```
  1 request:
     │
     ├─ TCP three-way handshake ──────── 1 RTT           (Lecture 2 §6.2)
     ├─ TLS handshake ────────────────── 1-2 more RTTs    (Lecture 2 §2.4)
     ├─ congestion control starts COLD ── slow start ramp  (Lecture 2 §6.5)
     ├─ [ the actual request/response — the ONLY part      ]
     │  [ that's doing useful work at all                  ]
     └─ connection close ──────────────── 4-way FIN/ACK,   (Lecture 2 §6.6)
                                            TIME_WAIT lingers
```

Every one of the non-bracketed lines above is pure overhead, paid **again** for the very next request if the connection isn't reused. At low volume this is invisible. At real volume, it compounds in two distinct ways you already have vocabulary for: **latency** (every request now pays multiple extra round trips it didn't need to) and **resource exhaustion** (Lecture 2 §5.3's ephemeral port exhaustion and `TIME_WAIT` accumulation — a system doing this constantly can genuinely run out of usable local ports).

### 4.2 The fix, restated precisely

Connection reuse means: after a request/response completes, don't close the connection — return it to a pool, and hand that *same* already-established, already-warmed-up connection to the next request that needs to talk to the same destination. This isn't a minor optimization — Lecture 2 §6.5 already showed that a reused connection is not just cheaper to start using, it's *faster once in use*, because congestion control doesn't have to re-ramp from cold. Everything in §5 is about doing this reuse correctly, safely, and with sensible limits.

---

## 5. Connection Pools

### 5.1 The basic shape

```
                     ┌─────────────────────────────┐
                     │        Connection Pool         │
                     │  (per destination, e.g. per      │
                     │   backend address)                 │
                     │                                    │
   Request A ───────►│  [conn 1: BUSY]  [conn 2: idle]     │───────► Destination
   Request B ───────►│  [conn 3: BUSY]  [conn 4: idle]      │
                     │                                    │
                     └─────────────────────────────┘
```

A pool holds a set of already-established connections to a given destination, tracks which are currently in use vs. idle, hands an idle one to a new request when available, and — critically — decides what to do when none are idle (§5.4). This is a per-*destination* structure: your process typically maintains a separate pool for each distinct backend address it talks to, since a connection to backend A is useless for a request destined for backend B.

### 5.2 Idle connections

A connection sitting idle in the pool (not currently serving a request) is still a real, held resource on *both* ends — an open socket (Lecture 2 §7.1), consuming a file descriptor and some kernel memory, on your machine *and* the destination's. Pools therefore apply an **idle timeout** — if a connection has sat unused longer than some threshold, it gets proactively closed and removed from the pool, rather than held indefinitely "just in case." This is a direct trade-off: too short an idle timeout means you're closing (and later re-opening) connections you'll likely need again soon, re-paying §4.1's cost unnecessarily; too long means holding resources for connections that may never be reused again at all.

### 5.3 Maximum connections

A pool caps how many connections it will maintain to a given destination at once. Without a cap, a sudden burst of concurrent requests to the same destination could each open their own fresh connection simultaneously — defeating the entire purpose of pooling, and potentially overwhelming the *destination* with far more simultaneous connections than it can handle well (recall Lecture 6 §9.3's cascading-overload concern, now at the connection level rather than the request-count level). The cap forces excess concurrent demand for that destination to **queue**, waiting for a connection to free up — which is your first direct encounter with backpressure (§7), applied specifically to connection acquisition.

### 5.4 What happens when the pool is exhausted

```
  All connections BUSY, new request arrives:

     Request C ────► [pool: all connections busy] ────► WAIT in a queue
                                                              │
                                        (a connection frees up)
                                                              │
                                                              ▼
                                                    Request C proceeds
```

This waiting is not free — a request queued waiting for a pooled connection is adding latency that has nothing to do with the destination's actual processing time at all; it's purely an artifact of the pool being temporarily saturated. If this wait exceeds the request's own timeout (Lecture 1 §10.3), the request fails *without ever having reached the destination at all* — an important, easy-to-misdiagnose failure mode: it looks like "the backend is slow," but the backend was never even contacted.

### 5.5 Connection lifetime

Distinct from idle timeout: a **maximum connection lifetime** proactively closes and replaces a connection after some duration, *even if it's still actively being reused successfully*. This seems counterintuitive (why discard something that's working?) until you consider what it protects against: DNS changes (the destination's address may have changed, and an old long-lived connection wouldn't notice — Lecture 4 §7.1's point about destinations changing constantly applies directly here), load-balancer-side rebalancing on the *other* end (if the destination itself sits behind its own load balancer, a connection that never cycles never lets that other layer redistribute it), and simply bounding how much accumulated, possibly-degraded state (buffers, counters) any single long-lived connection can carry. This is a deliberate freshness-vs-reuse trade-off, not a contradiction of the reuse principle from §4.2.

### 5.6 Pooling trade-offs, summarized

| Knob | Too small/short | Too large/long |
|---|---|---|
| Max connections | Requests queue and wait unnecessarily (§5.4), even when the destination has spare capacity | Destination can be overwhelmed by too many simultaneous connections; wastes local resources |
| Idle timeout | Connections closed and re-opened more than needed, re-paying §4.1's cost | Resources held for connections that may never be reused |
| Connection lifetime | Reuse benefit (§4.2) undermined by excessive re-establishment | Stale routing/DNS information persists longer than ideal; other-side rebalancing is slower to take effect |

There is no universally correct setting for any of these — they're tuned against actual observed traffic patterns, exactly the way Lecture 6 §5.5 had no universally correct load-balancing algorithm either.

---

## 6. Concurrency

### 6.1 Concurrency vs. parallelism — the distinction, precisely

These get conflated constantly, and the fix is one clean mental image:

- **Concurrency**: *dealing with* many things at once — making progress on multiple tasks by interleaving them, not necessarily executing more than one at the exact same instant. One chef, juggling five orders — chopping vegetables for order 1 while a pot simmers for order 2, checking the oven for order 3 — never doing two physical actions in the same instant, but *all five orders are in progress simultaneously* from the customer's point of view.
- **Parallelism**: *executing* many things at the exact same instant, using genuinely separate physical resources (multiple CPU cores). Five chefs, each cooking one order, at the literal same moment.

```
   CONCURRENCY (one worker, interleaved):        PARALLELISM (many workers, simultaneous):

   Time ──────────────────────────►                Time ──────────────────────────►
   Worker: [A][B][A][C][B][A][C][B]                Worker1: [A][A][A][A]
                                                    Worker2: [B][B][B][B]
   (only ONE thing physically happening             Worker3: [C][C][C][C]
    at any instant, but A, B, and C are all          (three things physically
    "in progress" over this whole span)               happening at the SAME instant)
```

### 6.2 Where async I/O fits — concurrency without necessarily parallelism

Recall Lecture 3 §9.1–§9.3: `await`ing an I/O operation frees the calling thread rather than blocking it. **This is concurrency, achieved on a single thread**, if you only have one — one thread can have many logically-in-progress requests "live" at once (each suspended at its own `await` point), making genuine progress on all of them over time, without ever running two pieces of code at the literal same instant. In practice, ASP.NET Core (and YARP) get **both**: multiple threads from the thread pool (§6.3), each capable of running actual CPU work in true parallel across multiple cores, *and* each of those threads capable of having many concurrent I/O-bound operations in flight via `await`, without needing a dedicated thread per operation. This combination — parallelism across threads, concurrency within what any given thread's worth of work is juggling — is precisely why a modest number of CPU cores can sustain a very large number of simultaneously in-flight requests, most of which are just waiting on I/O at any given moment (Lecture 3 §9.3's diagram, now formally named).

### 6.3 Threads and the thread pool

An OS thread is a real, relatively expensive resource — its own stack (typically megabytes, reserved even if mostly unused), and every switch between threads running on a core costs real time (a context switch). Creating a fresh OS thread per unit of work, the way you might create a fresh connection per request (§4), has exactly the same shape of problem — expensive setup, repeated unnecessarily.

The **thread pool** is a fixed(-ish), reused set of worker threads that pick up queued work items — including, critically, the "resume this suspended `async` method" work items from Lecture 3 §9.2 — rather than a new thread being created for every one. One subtlety worth knowing precisely because it explains a real production failure mode: the thread pool doesn't grow instantly under a sudden burst of demand — by design, it adds new threads only gradually (a rate-limited "injection rate"), to avoid a burst itself causing an even worse pile of expensive thread creation happening all at once. This means a *sudden* spike in work that genuinely needs more worker threads than currently exist can experience real, measurable delay before enough threads exist to handle it — a phenomenon commonly called **thread pool starvation**, and it's exactly why Lecture 3 §15's warning against blocking synchronous calls in async code matters even more under real load than it seems in a low-traffic dev environment: every thread blocked unnecessarily (§9.3 there) is one fewer thread available, at exactly the moment the pool is already struggling to keep up with genuine new demand.

### 6.4 Task — the abstraction, not the execution unit

Worth stating precisely, because "Task" and "Thread" get used interchangeably by mistake: a `Task` in C# represents *the future result of some operation* — it is not itself a thread, and creating a `Task` does not itself create a thread. An `async` method's `Task` might complete having run entirely on thread-pool threads picked up briefly at each resumption point (§6.3), or, for a pure CPU-bound `Task.Run`, on one dedicated thread-pool thread for its whole duration — but the `Task` object itself is just a handle you can `await`, check for completion, or attach continuations to; it's a coordination abstraction, not a unit of physical execution.

### 6.5 Synchronization and contention

The moment concurrent operations need to read *and* write **shared mutable state**, you have a correctness problem if you don't coordinate access — recall Lecture 6 §5.3's `LeastRequestsBalancer`, which explicitly used `lock` around its shared `_inFlight` dictionary specifically because multiple concurrent requests calling `Start()`/`Finish()` at once, without that lock, could corrupt the count (two threads reading the same value, both incrementing, both writing back the same result — one increment silently lost). This is a **race condition**, and `lock` (or lower-level atomic operations like `Interlocked.Increment`, which Lecture 6 §5.1's round-robin balancer used specifically to avoid needing a full lock for something that simple) is how you prevent it.

But synchronization has a cost of its own, and that cost is called **contention**: when many concurrent operations are all trying to acquire the *same* lock at the *same* time, most of them have to wait their turn — which means threads sitting idle, blocked, unable to do anything useful, which is precisely the "wasted thread" problem Lecture 3 §9.3 and §6.3 above were trying to avoid in the first place, just caused by a different mechanism (lock waiting instead of blocking I/O). A lock that's rarely contended costs almost nothing; the *same* lock, protecting a very hot piece of shared state under high concurrency, can become the single biggest bottleneck in an otherwise well-designed system — this is exactly why Lecture 6 §5's algorithms differ in how much shared state they need (round robin: one counter; least-requests: a whole dictionary needing a lock on every request start *and* finish) and why that difference is a genuine, not incidental, part of each algorithm's trade-off profile.

```
   Low contention (lock rarely held when another thread wants it):

     Thread A: [work][lock+unlock, fast][work]
     Thread B:              [work][lock+unlock, fast][work]

   High contention (many threads competing for the SAME lock constantly):

     Thread A: [work][lock──────HELD──────unlock][work]
     Thread B:        [ ...WAITING, DOING NOTHING... ][lock+unlock][work]
     Thread C:        [ ...WAITING, DOING NOTHING... ][ ...WAITING... ][lock][work]
```

---

## 7. Backpressure

### 7.1 The scenario

`Incoming traffic > system capacity.` This is not a hypothetical edge case for infrastructure software — it's an expected, recurring operating condition that a well-built system must have a deliberate answer for, not just "get slower and eventually fall over in some unplanned way."

### 7.2 The naive failure mode: unbounded absorption

Without any explicit limit, a system's instinct is often to just... accept everything, and queue whatever it can't immediately process. This feels safe (nothing is being rejected!) but is actually the most dangerous option: an unbounded queue under sustained excess demand grows without limit, consuming ever more memory (§8 connects this directly), and every item sitting in that queue is *also* accumulating wait time — meaning by the time work at the back of the queue is finally processed, it may have already exceeded the client's timeout and be pointless, wasted work, done anyway, on top of everything actively straining under the same overload.

### 7.3 Backpressure — the actual principle

**Backpressure is the deliberate propagation of an "I'm at capacity" signal backward through a chain, so upstream producers slow down or stop, instead of a downstream component silently absorbing unlimited excess work.** You've already seen a lower-layer version of exactly this idea: Lecture 2 §6.4's TCP flow control is backpressure — the receiver explicitly tells the sender "I have no more buffer room," and the sender is *required* to respect that and stop sending more, rather than the receiver just trying to buffer everything regardless. Application-level backpressure is the same principle, one layer up.

```
   WITHOUT backpressure:                        WITH backpressure:

   Producer ──(unlimited)──► [ queue grows      Producer ──(signal: "I'm full,      ──► [ bounded queue,
                                without bound,                  slow down / stop")        stays healthy ]
                                eventually OOM ]      ▲                                        │
                                                        └────────────────────────────────────────┘
                                                          producer respects the signal
```

### 7.4 The concrete mechanisms

- **Bounded queues**: a queue with a hard maximum size — once full, it cannot accept more work until something is dequeued, forcing the *next* mechanism to kick in.
- **Limits**: caps on concurrent work in flight (e.g., §5.3's max-connections-per-destination is a specific instance of this general idea, applied to connections) — bound the *amount* of simultaneous work a system will attempt, independent of how much more is being asked of it.
- **Throttling**: deliberately slowing the rate at which new work is accepted or started, rather than an outright hard stop — a softer form of the same signal.
- **Rejection**: explicitly refusing new work once at capacity, immediately, rather than queueing it — this is Lecture 4 §6.2's rate limiting, viewed from the backpressure angle: reject early and cheaply (a fast `503`, Lecture 4 §13.1's family) rather than accepting work you already know you can't complete in time, which is strictly worse for everyone — the client waits longer only to fail anyway, and the system wasted capacity on doomed work instead of spending that same capacity on requests it could actually complete.

### 7.5 Why rejection is often better than acceptance-then-failure

This deserves to be stated plainly because it's counterintuitive the first time you encounter it: **a fast, explicit rejection of excess work is frequently a *better* outcome for overall system health than accepting it and letting it fail later** — an accepted-then-abandoned request has already consumed real resources (a connection, a thread's attention, queue space) for no benefit, while a promptly rejected request costs almost nothing and immediately frees the client to retry elsewhere (Lecture 6 §4.2's "other servers keep working" idea) or back off. This is precisely the reasoning behind Lecture 4 §13.4's proxy self-protection via rate limiting — protecting the proxy's own health is not selfish, it's what keeps the proxy able to serve the requests it *can* actually complete.

---

## 8. Memory

### 8.1 Buffering vs. streaming, at concurrency scale

Lecture 1 §9 already established the single-request version of this: buffering a whole body into memory before forwarding it costs memory proportional to that body's size, while streaming keeps memory roughly constant per request. This lecture adds the concurrency multiplier explicitly: **that cost is per concurrent request, all at once.** A service buffering a 5MB request body, handling 10,000 concurrent such requests, is holding roughly 50GB in flight simultaneously — a number that sounds absurd stated directly, but is exactly what "small per-request cost, multiplied by real concurrency" produces if streaming isn't used.

### 8.2 Allocations and garbage collection, conceptually

.NET (like many managed-memory languages) automatically reclaims memory you're no longer using, via a **garbage collector (GC)** — you don't manually free objects. This is a genuine productivity and safety win, but it isn't free: every allocation (`new byte[8192]`, a new string, a new object) is *work* the runtime has to eventually account for and clean up, and under sustained high allocation rates, the GC has to run more often to keep up, which itself consumes CPU time and — in some cases — can briefly pause application threads while it works (a "GC pause"). At low request volume this is completely invisible. At high concurrent request volume, a proxy or server that allocates freely on every request (a new buffer per read, a new byte array per header, a new string per parsed value) can find that GC overhead becomes a measurable, sometimes significant, fraction of total CPU time and a real source of **tail latency** — occasional requests taking noticeably longer than the typical case, specifically because they happened to be in flight during a GC pause.

### 8.3 Why high-throughput code deliberately minimizes allocations

The practical response, in performance-sensitive .NET infrastructure code (Kestrel, YARP, and similar), is to actively avoid unnecessary allocation on the hot per-request path: **reusing buffers** instead of allocating a fresh one every time (`ArrayPool<byte>` — a shared pool you rent a buffer from and return when done, directly analogous in spirit to §5's connection pool, just for memory instead of connections), and using types like `Span<T>`/`Memory<T>` that let code work with slices of existing memory without copying it into a new allocation at all. You don't need the API details memorized — the concept to hold onto is the *same recurring pattern from this entire lecture*: an expensive resource (here, memory allocation + eventual GC work) is made cheap by pooling and reusing it, rather than creating and discarding it fresh for every request.

### 8.4 The connected story

Notice these three things are the same underlying principle, applied to three different resources, all in this one lecture: **pool and reuse connections (§5) instead of opening fresh ones; pool and reuse threads (§6.3) instead of creating fresh ones; pool and reuse buffers (§8.3) instead of allocating fresh ones.** Once you see this pattern once, the rest of high-throughput systems design reads as "find the expensive per-request resource, and figure out how to reuse it instead," repeated across whatever resource turns out to matter for a given system.

---

## 9. High-Volume Walkthrough — What Breaks, and When

### 9.1 ~10 requests/sec

Nothing in this lecture matters yet, observably. Fresh connections per request (§4) would be wasteful but not *breaking* anything. A single thread handling everything synchronously would still probably keep up. Unbounded queues never grow large enough to matter. Allocation-per-request GC overhead is a rounding error against total system idle time.

### 9.2 ~1,000 requests/sec

- **Connection reuse (§4–§5) stops being optional.** Without pooling, you're now paying full handshake+TLS+slow-start cost, per request, a thousand times a second — this alone can dominate total latency and start exhausting ephemeral ports (Lecture 2 §5.3).
- **Thread pool behavior starts mattering (§6.3).** A sudden burst at this rate can outpace the thread pool's gradual growth, causing brief but real queuing delay (thread pool starvation) even though steady-state capacity would have been fine.
- **Any lock-protected shared state (§6.5) that seemed harmless at low volume starts showing measurable contention** — code that "worked fine in testing" can visibly slow down here purely from threads waiting on each other, with no change to the actual work being done.
- **Backpressure (§7) needs to exist, even if rarely triggered** — at this volume, a genuine traffic spike (not even sustained overload, just a burst) can transiently exceed capacity, and the system needs *some* defined behavior for that moment, rather than none.

### 9.3 ~100,000 requests/sec

- **Every resource-pooling decision (§8.4) is now load-bearing simultaneously** — connection pool sizing, thread pool health, and allocation discipline all have to be right at once; a weakness in any one becomes the bottleneck for the whole system, regardless of how well-tuned the others are.
- **GC overhead (§8.2) becomes a first-class, measured concern** — at this request rate, allocation-heavy code paths generate enough garbage that GC pause frequency/duration shows up directly in tail-latency metrics, not just as an abstract inefficiency.
- **Backpressure and rejection (§7.5) move from "nice safety net" to "actively exercised, regularly, as part of normal operation"** — at this scale, brief bursts genuinely exceeding momentary capacity are routine, not exceptional, and the system's behavior *during* those moments (graceful, fast rejection vs. cascading collapse) is a primary determinant of overall reliability.
- **A single machine/process is very likely no longer sufficient at all** — this is the scale where horizontal scaling (many instances, load-balanced per Lecture 6, behind the layered architecture from Lecture 4 §9) stops being an optimization and becomes a structural requirement, because a single machine's CPU cores, memory, and OS-level connection limits (Lecture 2 §12) have real, physical ceilings that this volume is likely to approach or exceed regardless of how well the software itself is written.

---

## 10. Common Misconceptions

- **"Async code automatically uses multiple threads to go faster."** Directly contradicted by §6.2 — async I/O is fundamentally about *concurrency*, freeing a thread to do other work while waiting; it doesn't by itself create parallelism, and a single thread can be handling many concurrent async operations at once.
- **"A `Task` is a thread."** §6.4 — a `Task` is a handle to a future result; it may or may not correspond to dedicated thread time, and never automatically implies a new OS thread was created.
- **"More locking is always safer, and the cost is negligible."** §6.5 shows contention is a real, sometimes dominant cost — correctness requires synchronization where shared mutable state exists, but the *amount* and *scope* of locking is a genuine performance design decision, not a free safety blanket.
- **"Queueing excess work is always the responsible thing to do — rejecting requests feels wrong."** §7.5 directly argues the opposite in many real cases — fast rejection can be strictly better for overall system health than accepting work you can't actually complete in time.
- **"Garbage collection means memory management is a solved, invisible problem."** §8.2–§8.3 show it's invisible only at low allocation rates; at high throughput, allocation patterns become a genuine, measurable performance concern worth deliberately designing around.
- **"Connection pooling has one obviously correct configuration."** §5.6 is explicit — every pooling knob is a real trade-off tuned against actual traffic, with no universally correct default.

---

## 11. Failure Scenarios

- **Thread pool starvation** (§6.3): a burst of demand outpaces the pool's gradual growth, or synchronous blocking calls (Lecture 3 §15) are unnecessarily holding threads — symptom: the whole application becomes sluggish or unresponsive under load it should handle, even though CPU usage might look deceptively low (threads are waiting, not working).
- **Connection pool exhaustion** (§5.4): all pooled connections to a destination are busy, new requests queue for one, and if that wait exceeds their own timeout, they fail *before ever reaching the destination* — a classic misdiagnosis trap, since it can look identical to "the backend is slow" from a shallow glance at symptoms alone.
- **Unbounded queue growth** (§7.2): without a bound, a sustained overload condition causes memory usage to climb without limit, eventually leading to out-of-memory failure — a self-inflicted outage caused by trying to be "helpful" (never rejecting anything) rather than by the original overload itself.
- **Lock convoy / severe contention** (§6.5): a hot lock under high concurrency causes most threads to spend most of their time waiting rather than working, producing a throughput collapse disproportionate to the actual amount of protected work being done — often surprising precisely because the protected critical section itself might be tiny; it's the *frequency* of contention, not the section's size, that dominates.
- **GC pause-induced tail latency** (§8.2): a small fraction of requests experience a disproportionate latency spike specifically because they were in flight during a GC pause — often invisible in *average* latency metrics and only visible in p99/p999 tail metrics, which is exactly why infrastructure software cares about tail latency specifically, not just averages.

---

## 12. Performance Implications

- **Always pool and reuse connections** (§4–§5) — this is the highest-leverage fix available for anything making repeated calls to the same destination, and its absence is one of the most common real-world causes of unnecessary latency and resource exhaustion.
- **Keep locks narrow in scope and short in duration** (§6.5) — the cost of synchronization scales with contention, not just correctness need; minimize how much work happens *while* a lock is held.
- **Design an explicit backpressure/rejection strategy before you need it** (§7) — deciding this reactively, during an actual overload incident, is far worse than having bounded queues and rejection behavior already in place beforehand.
- **Minimize allocations on hot per-request paths** (§8.3) — pooled buffers and non-copying memory APIs are exactly how high-throughput .NET infrastructure code keeps GC overhead from becoming a bottleneck at scale.
- **Watch tail latency (p99/p999), not just averages** (§8.2, §11) — averages can hide exactly the GC-pause and contention-driven spikes that matter most for a proxy sitting in every request's critical path.
- Deep manual GC tuning (generation sizing, server vs. workstation GC mode internals) is **not** where your effort belongs yet — allocation *discipline* (§8.3) gets you the vast majority of the benefit; GC configuration tuning is a narrower, later specialization.

---

## 13. YARP Connection

Every concept in this lecture is something YARP's forwarding path has to get right **simultaneously**, on every single proxied request, because a proxy sits directly in the highest-concurrency part of the entire system (Lecture 4 §9.2's observation that the reverse-proxy tier handles the full, undifferentiated volume of client traffic before any backend-specific work even begins).

- **Connection management (§4–§5)**: YARP maintains pooled `HttpMessageInvoker`/`SocketsHttpHandler` instances per destination (Lecture 2 §15.2, Lecture 4 §15's forwarder box) — exactly this lecture's connection pool, with exactly these tunable knobs (max connections per destination, idle timeout, connection lifetime), because YARP is simultaneously acting as the *client* for potentially enormous numbers of concurrent outbound requests, per destination, all the time.
- **Async I/O and concurrency (§6)**: YARP's entire forwarding path is built on `async`/`await` over non-blocking I/O specifically because — per §6.2 and Lecture 3 §17.2 — this is the only way a modest thread-pool footprint can sustain the request volumes YARP is designed for; any accidental synchronous blocking call anywhere in that path would directly reproduce §11's thread-pool-starvation failure mode, at proxy scale, affecting *every* request currently being forwarded, not just one.
- **Synchronization and contention (§6.5)**: any shared state YARP maintains across concurrent requests — a destination's in-flight request count (directly Lecture 6 §5.3's `LeastRequestsBalancer`, now understood as genuinely proxy-scale shared state), health-check status (Lecture 6 §6) — has to be synchronized carefully, with contention explicitly in mind, precisely because it's touched on *every* request passing through, at whatever volume the proxy is handling.
- **Backpressure (§7)**: YARP's connection-pool limits (§5.3) are themselves a backpressure mechanism — when a destination's pool is saturated, new requests to it queue rather than the proxy opening unlimited fresh connections and potentially overwhelming that backend (directly connecting to Lecture 4 §13.4's proxy self-protection and Lecture 6 §9.3's cascading-overload risk). A proxy without deliberate backpressure at this layer risks becoming the *cause* of a cascading overload rather than a defense against one.
- **Memory (§8)**: YARP forwards request/response bodies via streaming (Lecture 1 §9, Lecture 4 §8) specifically to avoid §8.1's concurrency-multiplied buffering blowup, and its hot forwarding path is written with allocation discipline in mind (pooled buffers, per §8.3) — because, again, whatever per-request allocation cost exists gets multiplied by the proxy's full concurrent request volume, all the time, by the nature of what a reverse proxy tier actually does.

The unifying point to take from this lecture, specifically as it applies to YARP: **none of these concerns are optional extras layered on top of "a proxy that forwards requests" — they are what makes a proxy able to forward requests at the volumes it's actually built for at all.** A functionally-correct forwarder that ignores pooling, async discipline, contention, backpressure, or allocation cost would still be "correct" at 10 requests/sec (§9.1) and would visibly, predictably fail somewhere in the §9.2–§9.3 range — which is exactly why every one of these topics shows up as deliberate, load-bearing design decisions once you actually look at YARP's source, rather than incidental implementation detail.

---

## 14. What I Don't Need to Know Yet

- The .NET GC's specific generational algorithm internals (gen0/1/2 promotion rules, server vs. workstation GC mode trade-offs in depth) — §8.2's "allocation has a cost, GC pauses exist" is the right depth here.
- `ArrayPool<T>`/`Span<T>`/`Memory<T>`'s exact API surface — §8.3's conceptual role (pooling applied to memory) is sufficient until you're writing allocation-sensitive code directly.
- Lock-free/wait-free concurrent data structure design — recognize that alternatives to plain locks exist for high-contention scenarios; the specific techniques are a deeper, later specialization.
- Thread pool internals beyond §6.3's injection-rate behavior (exact algorithms governing growth/shrinkage) — the practical consequence (bursts can outpace growth) is the load-bearing fact, not the precise formula.
- Distributed backpressure across multiple service instances (as opposed to the single-process version taught here) — a natural extension once you're thinking about the layered, multi-instance architectures from Lecture 4 §9 and Lecture 6 §9.
- Specific benchmarking/profiling tooling for diagnosing allocation hotspots or contention in a real .NET application — valuable, hands-on skill, but a separate, practical topic from this lecture's conceptual foundation.

---

## 15. Knowledge Check

1. A service opens a brand-new HTTP connection for every outbound call to the same downstream API, at 2,000 requests/sec. Using §4.1 and Lecture 2 §5.3, name two distinct categories of problem this causes, and explain why they're different kinds of cost (one about time, one about a finite resource running out).
2. Explain, using §6.1–§6.2, why a system can have very high concurrency but very low (even single-core) parallelism, and give a concrete example of when that's actually the right design, not a limitation.
3. A `LeastRequestsBalancer` (Lecture 6 §5.3) shows unexpectedly poor throughput under high concurrency, even though the actual work it protects (incrementing/decrementing a counter) is trivially fast. Using §6.5, explain what's likely happening and why "the protected work is small" doesn't guarantee the lock is cheap.
4. Using §7.2 vs §7.5, explain why a system that queues absolutely everything, rejecting nothing, can end up serving its clients *worse* overall than one that rejects excess requests promptly once at capacity.
5. Using §8.1, calculate (roughly, conceptually) why buffering full request bodies becomes a fundamentally different kind of problem at 10,000 concurrent requests than it is at 10 — is it the per-request cost that changed, or something else?
6. Using §13, pick any two of YARP's forwarding-path concerns (connection pooling, async I/O, backpressure, memory/allocations) and explain how a failure in just *one* of them, even if the others were perfect, would still degrade the whole proxy under real production load.

---

## 16. Practical Exercise

Build a small, local demonstration that makes thread-pool starvation and connection-pool saturation directly observable — both are easy to describe abstractly and genuinely eye-opening to actually watch happen.

### Part A — Thread pool starvation from blocking calls

```csharp
// StarvationDemo/Program.cs
var builder = WebApplication.CreateBuilder(args);
var app = builder.Build();

// BAD: blocks a thread pool thread synchronously for the whole delay.
app.MapGet("/blocking", () =>
{
    Thread.Sleep(500); // simulates blocking I/O done WRONG
    return Results.Ok("done (blocking)");
});

// GOOD: frees the thread during the wait.
app.MapGet("/async", async () =>
{
    await Task.Delay(500); // simulates the SAME wait, done as real async I/O
    return Results.Ok("done (async)");
});

app.Run();
```

Run it, then hammer each endpoint with real concurrency using a simple parallel loop (or `hey`/`bombardier` if you have a load-testing tool installed; a plain C# client works fine too):

```csharp
// LoadClient/Program.cs — fire 200 concurrent requests, time the whole batch
var client = new HttpClient();
var sw = System.Diagnostics.Stopwatch.StartNew();
var tasks = Enumerable.Range(0, 200)
    .Select(_ => client.GetAsync("http://localhost:5000/blocking")); // then try /async
await Task.WhenAll(tasks);
Console.WriteLine($"Total: {sw.ElapsedMilliseconds}ms");
```

Compare total time for `/blocking` vs `/async` at 200 concurrent requests. You should see `/blocking` take dramatically longer than `200/(concurrent capacity) * 500ms` would suggest — direct evidence of §6.3's thread-pool starvation, since `Thread.Sleep` holds a thread pool thread hostage for the full 500ms doing nothing, while `Task.Delay` frees it immediately.

### Part B — Connection pool saturation

```csharp
// In your client code, explicitly cap the pool small to make saturation easy to trigger:
var handler = new SocketsHttpHandler
{
    MaxConnectionsPerServer = 2 // deliberately tiny, to force queuing (Section 5.4) quickly
};
var client = new HttpClient(handler);

var sw = System.Diagnostics.Stopwatch.StartNew();
var tasks = Enumerable.Range(0, 20)
    .Select(async i =>
    {
        var start = sw.ElapsedMilliseconds;
        await client.GetAsync("http://localhost:5000/async"); // hits your 500ms /async endpoint
        Console.WriteLine($"Request {i}: started waiting at {start}ms, finished at {sw.ElapsedMilliseconds}ms");
    });
await Task.WhenAll(tasks);
```

With only 2 connections allowed and a 500ms-per-request endpoint, watch the console output: requests should visibly complete in *waves* of roughly 2 at a time, roughly 500ms apart — direct, observable evidence of §5.4's queueing behavior, where most of these 20 requests are spending most of their time waiting for a pooled connection to free up, not waiting on the server at all.

---

## 17. "Ready to Move On" Criteria

Before starting the next lecture, you should be able to explain — out loud, in your own words:

- [ ] The specific, itemized cost of opening a fresh connection per request, and why reuse fixes more than one kind of cost at once.
- [ ] The real trade-offs behind connection pool sizing, idle timeout, and connection lifetime — not just that they exist, but what each one is actually balancing.
- [ ] The precise difference between concurrency and parallelism, with your own example of each, and of both together.
- [ ] Why a `Task` is not a thread, and why `await` frees a thread rather than blocking it.
- [ ] Why synchronization is necessary for shared mutable state, and why contention can make even a "small" lock a real bottleneck under high concurrency.
- [ ] Backpressure as a general principle — and why prompt rejection can be a *better* outcome than unlimited, silent acceptance of excess work.
- [ ] Why buffering's memory cost is multiplied by concurrency, and what streaming and allocation-conscious code (pooled buffers) actually buy you as a result.
- [ ] What specifically breaks, and roughly when, as a system scales from 10 to 1,000 to 100,000 requests/sec.
- [ ] Why every concern in this lecture is simultaneously present and load-bearing in YARP's own forwarding path, not an optional refinement layered on top of "basic" proxying.

If these feel solid, you've now covered the full arc from HTTP fundamentals through connection mechanics, ASP.NET Core architecture, reverse proxy concepts, routing, load balancing, and high-throughput systems design — the complete conceptual foundation this series set out to build before opening YARP's actual source code.
