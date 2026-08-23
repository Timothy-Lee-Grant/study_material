# Lecture 9: Distributed Systems Fundamentals for a Backend Engineer

Series: YARP Learning Series
Builds on: [Lecture 4 §9](004-reverse_proxies_and_api_gateways.md) (layered architecture, horizontal instances), [Lecture 6 §9](006-load_balancing_and_traffic_distribution.md) (load balancing across many servers, distributed-scale complications), [Lecture 7 §7](007-concurrency_connection_pooling_and_high_throughput_networking.md) (backpressure, tail latency), [Lecture 8](008-failure_resilience_and_partial_failure.md) (independent failure, cascading failure, partial failure).
Scope note, stated up front: this is a **practitioner's map** of distributed systems, not a research foundation. Several genuinely deep topics (consensus algorithms, Byzantine fault tolerance) are explicitly named and explicitly set aside — §18 explains why, rather than silently skipping them.

---

## 1. Learning Objectives

By the end of this lecture you should be able to:

1. Distinguish vertical from horizontal scaling, and stateless from stateful services, and explain why statelessness is what makes horizontal scaling easy.
2. Explain why replication exists, and the difference between what it buys you for availability versus what it costs in consistency.
3. Explain strong vs. eventual consistency with a concrete example you could describe to a colleague without hand-waving.
4. Explain CAP as a real, practical trade-off you'll actually encounter — what a network partition is, and why you can't have everything at once during one.
5. Read and correctly interpret p50/p90/p95/p99/p99.9 latency figures, and explain precisely why an average hides exactly the information that matters most.
6. Distinguish throughput, capacity, saturation, and bottleneck as related but distinct concepts.
7. Explain why queues exist as an explicit architectural component (not just an implementation detail), and what problems they introduce even as they solve others.
8. Explain a service dependency graph and why its shape determines how failures propagate.
9. Explain, at a practical level, how a service actually finds the current address of another service it depends on.
10. Explain why state becomes hard the moment more than one machine is involved, in terms of the actual mechanism (not just "distributed systems are hard").
11. Separate which of these concepts YARP directly embodies versus which are broader context for reasoning about the systems YARP operates inside.

---

## 2. Prerequisite Concepts

This lecture sits on top of a surprising amount you already have. Lecture 4 §9 already showed you a layered, horizontally-scaled architecture. Lecture 6 §9 already showed load balancing breaking down into a genuinely distributed problem once multiple instances are involved. Lecture 7 §7 already taught backpressure and queueing within one component. Lecture 8 already taught independent failure, cascading failure, and partial failure as first-class ideas. What's genuinely new in this lecture: replication and consistency (databases and state haven't been directly addressed yet), CAP as an explicit framework, formal latency-percentile vocabulary, service discovery, and a direct treatment of *why* distributed state is hard, rather than just observing that failures happen.

---

## 3. Core Mental Model

```
   ONE MACHINE:                              MANY MACHINES:

   - shared memory, instant access             - no shared memory — only messages,
   - operations happen in a real,                 sent over a network with real,
     total order                                   nonzero latency (Lecture 2 §9)
   - "the current state" is unambiguous          - each machine only knows its OWN
     (there's only one copy)                       local, possibly-stale view
   - failure is roughly binary                   - failure is partial and continuous
     (running or crashed)                           (Lecture 8 §11)
```

The one sentence for this entire lecture: **almost everything that's "hard" about distributed systems traces back to one root fact — there is no shared memory between machines, only messages sent over an unreliable, non-instantaneous network — and every concept in this lecture is either a consequence of that fact or a strategy for coping with it.**

---

## 4. Horizontal Scaling

### 4.1 Vertical scaling

**Vertical scaling**: make one machine bigger — more CPU, more RAM, faster disks. Simple to reason about (still one machine, still one copy of everything, per §3's left column) but has a hard ceiling: there's a largest machine you can buy or rent, and past a certain point the cost of bigger hardware grows much faster than the capacity it buys you. It also does nothing for §4 of Lecture 8 (Lecture 8 §4.2) — a single, bigger machine is still a single point of failure, and a bigger single point of failure isn't meaningfully safer than a smaller one.

### 4.2 Horizontal scaling

**Horizontal scaling**: add *more* machines, and distribute work across all of them (exactly the load-balanced, multi-destination model from Lecture 6). This is what Lecture 4 §9 and Lecture 4 §4 already showed you, now named precisely: it directly buys both more aggregate capacity (Lecture 4 §4.1) and more reliability (Lecture 4 §4.2, Lecture 8 §11.3's blast-radius argument), because no single machine failing takes down the whole capacity.

### 4.3 Why statelessness is what actually makes horizontal scaling *easy*

Here's the piece that's genuinely new: horizontal scaling is trivial *if any request can be handled by any instance, interchangeably*. A **stateless** service has this property — it doesn't hold onto anything from one request to the next that a *different* instance would need to know about to handle the next request correctly. Lecture 6's whole load-balancing model (§5 there — round robin, least-requests, any of it) implicitly assumes this: it's picking *any* healthy destination, on the premise that it genuinely doesn't matter which one.

A **stateful** service breaks that premise — it holds data (in memory, or on local disk) that's specific to *that instance*, and a request needing that data can only be correctly served by the instance that actually has it. Horizontally scaling a stateful service isn't as simple as "add more instances and load-balance across them," because the load balancer now has to be *aware* of which instance holds which state (this is exactly what session affinity — deliberately deferred across Lectures 4, 5, and 6 — actually is: a mechanism for routing a given client consistently back to the specific instance holding their state) or the state itself has to be moved out of any single instance entirely (into a shared, external store) so that every instance is stateless *with respect to that data*, even if the overall system still has state *somewhere*.

```
   STATELESS service — any instance works:          STATEFUL service — must route to the RIGHT instance:

   Client ──► LB ──► any instance (A, B, or C)      Client ──► LB ──► MUST be instance B specifically
                       all produce the SAME                          (it's the one holding this client's
                       correct result                                  in-memory session/cart/etc.)
```

**Why this matters as a design principle, not just a definition**: systems are frequently, deliberately architected to push state *out* of the horizontally-scaled request-handling tier and into a small number of dedicated, purpose-built stateful stores (a database, a cache) specifically *so that* the request-handling tier itself can stay stateless and trivially horizontally scalable — concentrating the genuinely hard "state at scale" problem (§6, §11 later in this lecture) into as few, well-understood places as possible, rather than smearing it across every service.

---

## 5. Replication

### 5.1 Why replication exists

**Replication** means keeping more than one copy of the same data, on different machines. It exists to solve exactly two problems, and it's worth being precise that they're distinct:

- **Availability**: if the only copy of some data lives on one machine, and that machine fails (Lecture 8 §3's independent failure, applied to data instead of a stateless service), the data is unavailable until it's fixed. A second copy, on a different machine, means the data — and the ability to serve it — survives that one machine's failure.
- **Redundancy as a distinct-but-related benefit**: beyond just surviving failure, multiple copies can also serve read traffic *simultaneously*, spreading load the same way horizontal scaling spreads load for stateless services (§4.2) — except now applied to something that inherently has state.

### 5.2 Primary/replica

The most common shape: one copy is the **primary** (sometimes called "leader" or "master") — it accepts writes, and is the authoritative source of truth at any given moment. One or more **replicas** (or "followers") receive a continuous stream of the primary's changes and keep their own copy up to date.

```
                        WRITES
   Client ──────────────────────────►  Primary
                                          │
                              (changes streamed to replicas)
                                          │
                              ┌───────────┼───────────┐
                              ▼           ▼           ▼
                          Replica 1   Replica 2   Replica 3
                              ▲           ▲           ▲
   Client ─────── READS ──────┴───────────┴───────────┘
```

### 5.3 Read replicas

Because replicas hold a copy of the data, they can serve **read** traffic directly — offloading read load from the primary, letting read capacity scale roughly the way stateless service capacity does (§4.2), even though the underlying data is inherently stateful. This is an extremely common, practical pattern precisely because most real systems are read-heavy (many more reads than writes) — read replicas let you scale the *majority* of traffic (reads) horizontally, while writes still funnel through the single primary, which is a much smaller fraction of total load to have to handle in one place.

### 5.4 The catch — replicas aren't instantly up to date

Recall §3's root fact: there's no shared memory between the primary and its replicas, only messages sent over a network with real, nonzero latency. This means there is *always* some window, however small, where a replica's copy is slightly behind the primary's latest writes — which is the direct, concrete setup for §6's entire discussion of consistency.

---

## 6. Consistency

### 6.1 Strong consistency

**Strong consistency** means: once a write completes, *every subsequent read, from anywhere, sees that write* — there is no window where you can read stale data. This is the intuitive, "obviously correct" behavior most people assume by default, and it's genuinely achievable — but it costs something, which §7 (CAP) makes precise: guaranteeing every read reflects the very latest write typically requires reads (or writes) to wait for coordination across replicas, which costs latency, and can cost availability during a network problem (§7.2).

### 6.2 Eventual consistency

**Eventual consistency** means: after a write, replicas *will* converge to reflect it — **eventually** — but there's no guarantee about exactly when, and a read landing on a not-yet-updated replica in that window sees **stale** data. This sounds worse than strong consistency stated bluntly like that — but it buys real things in exchange: reads don't have to wait for cross-replica coordination (faster, and available even if some replicas are temporarily unreachable, directly connecting to Lecture 8 §3's independent-failure principle — an eventually consistent system can keep serving reads even when a replica is cut off, where a strongly consistent system might have to refuse to answer at all until coordination is possible again).

### 6.3 A concrete example, worked through

Imagine a "like" count on a social media post, replicated across three regions (US, EU, Asia):

```
  t=0:     US replica: 1,000 likes   EU replica: 1,000 likes   Asia replica: 1,000 likes
  t=1:     A user in the US likes the post. Write goes to the US replica (or a primary near it).
  t=1:     US replica: 1,001 likes   EU replica: 1,000 likes   Asia replica: 1,000 likes
                                     (still catching up)        (still catching up)
  t=1.2:   US replica: 1,001 likes   EU replica: 1,001 likes   Asia replica: 1,000 likes
                                     (caught up)                 (still catching up)
  t=1.4:   US replica: 1,001 likes   EU replica: 1,001 likes   Asia replica: 1,001 likes
                                                                  (finally caught up — "eventually" consistent)
```

Between `t=1` and `t=1.4`, a user reading from the Asia replica sees a **stale** count — `1,000`, not the true current `1,001`. For a like counter, this is almost certainly a perfectly acceptable trade-off — nobody's experience is meaningfully harmed by seeing a like count that's a few hundred milliseconds out of date. **Now contrast**: a bank balance, replicated the same way, showing a stale (too-high) value for even a few hundred milliseconds could let someone withdraw money that, from the true, current balance's perspective, they didn't actually have. This is the entire point of walking through a concrete example: **the correct choice between strong and eventual consistency depends entirely on what the data actually means and what happens if it's briefly wrong** — it's not a technical question with one universally correct answer, it's a domain question about acceptable risk.

### 6.4 The trade-off, stated directly

| | Strong consistency | Eventual consistency |
|---|---|---|
| Every read reflects the latest write? | Yes, always | No — there's a window of possible staleness |
| Typical latency cost | Higher (coordination required) | Lower (no coordination wait) |
| Behavior during a network problem between replicas | May have to refuse reads/writes rather than risk inconsistency (§7.2) | Can typically keep serving, using whatever local copy is available |
| Good fit for | Financial balances, inventory counts, anything where staleness causes real harm | Social media counters, view counts, caches, anything where brief staleness is harmless |

---

## 7. CAP Theorem — Conceptually

### 7.1 What a network partition actually is

A **network partition** is exactly what Lecture 2 §10.1–§10.2 already taught you, applied *between two parts of a distributed system that both need to keep working*: some machines can no longer communicate with some other machines — not because either side crashed (§3 of Lecture 8's independent-failure list still applies to each individual machine separately), but because the network connecting them has failed or degraded. Crucially: **from inside a partition, you cannot tell the difference between "the other side crashed" and "the other side is fine, but we can't currently reach it."** This ambiguity is exactly why partitions force a genuine decision, rather than being a solvable annoyance.

### 7.2 The trade-off, stated practically (not as a formal proof)

When a partition happens — some replicas can't currently talk to others — a system serving a request has to choose, in that moment, between two options, and this is the entire practical content of CAP worth internalizing (the formal three-letter theorem itself matters far less than this concrete choice):

- **Refuse to serve the request** (or refuse the write) until the partition heals and replicas can coordinate again — preserving strong consistency (§6.1), at the cost of availability *during the partition*.
- **Serve the request anyway**, using whatever local data is currently reachable — preserving availability, at the cost of potentially serving (or accepting) something that isn't consistent with the other, currently-unreachable side, until the partition heals and things reconcile.

```
              Network partition — US and EU can no longer talk to each other

   ┌───────────┐                                              ┌───────────┐
   │  US replica  │  ✕ ✕ ✕ ✕ (partition) ✕ ✕ ✕ ✕                    │  EU replica  │
   └───────────┘                                              └───────────┘

   A write arrives at the US side during the partition. Two choices:

   CHOOSE CONSISTENCY:  refuse the write (or mark it pending) until      → less available
                         the partition heals and EU can be told too         during the partition

   CHOOSE AVAILABILITY: accept the write on the US side anyway,          → temporarily
                         reconcile with EU once reachable again              inconsistent
```

**You cannot have both simultaneously, during the partition itself** — this is the actual, practical content of CAP: it's not that you must permanently sacrifice one, it's that *during* a partition specifically, you are forced to pick which one you're willing to give up, temporarily, until the partition resolves. Outside of an active partition, most real systems aim to provide both consistency and availability just fine — CAP is specifically about what happens in that narrow, unavoidable window when the network itself is the problem.

### 7.3 Why this matters even though you're not designing a database

You don't need to design a distributed database to need this framework — you need it to correctly reason about *any* system built from multiple replicated or distributed components, including ones YARP sits in front of. When a backend cluster's destinations (Lecture 5 §6) can't all currently reach each other, or a proxy's own configuration source (Lecture 5 §7.3) becomes temporarily unreachable, the exact same practical choice — serve using possibly-stale local information, or refuse until you're sure — is happening, whether or not anyone involved is thinking of it in CAP terms.

---

## 8. Latency Percentiles

### 8.1 Why an average is the wrong summary

Recall Lecture 7 §8.2's introduction of tail latency — this section gives it the formal vocabulary. Suppose 1,000 requests, and 990 of them take 10ms while 10 of them take 2,000ms (a real, plausible shape — a handful of unlucky requests hitting a GC pause, a slow destination, or a queued wait behind a saturated connection pool, per Lecture 7). The **average** is `((990×10) + (10×2000)) / 1000 ≈ 30ms` — a number that describes *none* of the actual requests well: it's not what the typical request experienced (10ms), and it completely buries the fact that 1% of users had an experience 200x worse than typical.

### 8.2 Percentiles, precisely

A **percentile** answers: "what value is this request's latency *below*, for X% of all requests?"

- **p50 (median)**: half of all requests were faster than this, half slower — the "typical" experience.
- **p90**: 90% of requests were faster than this — only the worst 10% were slower.
- **p95**: only the worst 5% of requests were slower than this.
- **p99**: only the worst 1% of requests were slower than this.
- **p99.9**: only the worst 0.1% of requests were slower than this.

```
   1,000 requests, sorted fastest to slowest:

   [fastest ...................................................... slowest]
    │                                    │      │    │  │
   p50                                  p90    p95  p99 p99.9
   (typical)                                              (the worst,
                                                            rarest cases)
```

Using the §8.1 example: p50 would be `10ms` (accurately describing most requests), while p99 would capture something much closer to that `2000ms` tail — telling you something the average of `30ms` actively hid.

### 8.3 Why the tail matters disproportionately for infrastructure like a proxy

Here's the reasoning that makes this genuinely important, not just a statistics footnote: **if a single user's page load involves 20 separate backend calls, and each call has a 1% chance of hitting your p99 latency, the chance that at least one of those 20 calls hits the slow tail is much higher than 1%** (roughly `1 - 0.99^20 ≈ 18%`) — meaning a "rare" p99 event, multiplied across a request that fans out to many dependencies, becomes a *common* experience for real users. This is exactly why infrastructure teams obsess over p99/p99.9, not p50 — a proxy or any shared infrastructure component sits in the path of an enormous number of aggregated calls, and its tail behavior gets amplified by every downstream fan-out that depends on it.

---

## 9. Throughput

### 9.1 Requests/sec, capacity, and the relationship between them

Recall Lecture 1 §10.1's initial definition — throughput is the actual rate of completed work, in requests/sec. **Capacity** is the maximum throughput a system can sustain before something gives way — and it's not a single fixed number for "the system," it's bounded by whichever specific resource runs out first.

### 9.2 Saturation

**Saturation** is the state of a resource being fully utilized — no spare capacity left for that specific resource, even if others still have headroom. A system can be saturated on CPU while its network bandwidth sits mostly idle, or saturated on database connections (Lecture 7 §5.3's pool cap) while CPU is barely used at all. Saturation on any *one* resource caps the system's overall throughput, regardless of how much slack exists elsewhere.

### 9.3 Bottlenecks

A **bottleneck** is whichever saturated resource is currently the limiting factor on overall throughput. Identifying it precisely matters because improving the *wrong* resource does nothing: adding more CPU to a system that's actually bottlenecked on database connection pool size (Lecture 7 §5) won't raise throughput at all — the bottleneck hasn't moved. This is a direct, practical consequence of §9.2: real system tuning is about finding *which* resource is currently saturated, not assuming it's whichever one is easiest to add more of.

```
   Throughput is capped by the SMALLEST capacity along the path,
   not the average or the largest:

   CPU capacity:            ████████████████████████ (plenty of headroom)
   DB connection pool:      ████████ (SATURATED — this is the bottleneck)
   Network bandwidth:       ████████████████ (some headroom)

   Overall throughput ceiling = whatever the DB connection pool allows,
   REGARDLESS of how much spare CPU or bandwidth exists
```

---

## 10. Queues

### 10.1 Why queues exist — recap and formalization

Lecture 7 §7 already taught the mechanics (bounded queues, backpressure) within one component. Here's the broader framing: a **queue** exists wherever the *rate* work arrives can temporarily exceed the *rate* it can be processed — it's the buffer absorbing that mismatch, for however long it's able to. Queues show up in two related but distinct places: **in-process** (Lecture 7 §5.4's connection-pool wait queue, a thread pool's work-item queue) and as an explicit **architectural component** — a dedicated message queue or event stream (technologies like a message broker) deliberately placed *between* two services, specifically so the producer and consumer don't need to process work at the same rate, at the same time, at all — the producer can keep accepting work even while the consumer is temporarily behind, entirely decoupling their respective paces.

### 10.2 Queue buildup

If the arrival rate sustainedly exceeds the processing rate — not just briefly, but for a real stretch of time — a queue doesn't just absorb the mismatch, it **grows without bound** (exactly Lecture 7 §7.2's unbounded-queue danger, restated at the architectural level): every item added faster than items are removed makes the queue longer, which means every *new* item added has to wait behind an ever-growing backlog before it's even reached.

### 10.3 Latency, as a direct consequence of queue depth

This is worth stating as a precise, causal relationship, not just an association: **an item's wait time in a queue is directly proportional to how many items are already ahead of it.** A queue that's usually near-empty adds near-zero latency; the same queue, backed up with thousands of items during sustained overload, adds real, potentially enormous latency to every new arrival — even though the *processing* time for any individual item hasn't changed at all. This is exactly why "the service got slow" during an incident is very often actually "a queue somewhere got long," rather than any single request suddenly taking longer to *process*.

### 10.4 Backpressure, once more, as the answer

Lecture 7 §7.3–§7.5 already gave you the fix in full: bound the queue, and once full, push back — reject, throttle, or signal the producer to slow down — rather than letting it grow without limit. The architectural-queue version of this (a message broker rejecting or slowing publishers once its own capacity is reached) is the identical principle, just operating between two independent services instead of within one process.

---

## 11. Service Dependencies

### 11.1 The dependency graph

Every real system, once it has more than a couple of services, forms a **dependency graph**: nodes are services, edges are "calls" relationships (Service A calls Service B means an edge from A to B). Lecture 8 §10 already walked through a linear chain (A → B → C); real systems are rarely that simple — a single service often has several dependencies (fan-out), and a single dependency is often shared by many callers (fan-in), forming a genuine graph rather than a simple chain.

```
                    Service A
                   /    │     \
                  ▼     ▼      ▼
            Service B  Service C  Service D
                  \      │      /
                   ▼     ▼     ▼
                    Shared Database
```

### 11.2 Why the graph's shape determines failure propagation

Lecture 8 §10 already taught the *mechanism* of propagation (resource exhaustion cascading backward through a chain) — the dependency graph's *shape* determines *how far and how widely* that propagation can spread. A service near the "bottom" of the graph, shared by many callers (like the database in the diagram above), is a **correlated-failure risk** (Lecture 8 §4.3) precisely because of its position: its failure doesn't propagate through one chain, it propagates through *every* chain that touches it simultaneously. Recognizing which nodes in a dependency graph are heavily shared — high fan-in — is exactly how you'd predict, before any incident happens, which single failures carry the largest possible blast radius (Lecture 8 §11.3).

### 11.3 The critical path

Within a graph, the **critical path** for a given request is the specific chain of *synchronous, blocking* dependencies that determine its actual latency — if A calls B and C *in parallel* and waits for both, the critical path is whichever of B or C is slower (not their sum); if A calls B, and only *after* B responds does it call C, the critical path is B's latency *plus* C's latency (their sum). Understanding a request's actual critical path — as opposed to just "everything it happens to touch" — is what tells you which specific dependency's latency (and, per §8.3, tail latency specifically) actually matters for the end-to-end experience, and which dependencies, even if slow, aren't currently on the path determining total latency at all.

---

## 12. Service Discovery

### 12.1 The problem

Recall Lecture 5 §6's point: destinations change constantly — instances come and go via deployment, autoscaling, and crashes. **Service discovery** is the general answer to "how does a service (or a proxy) know the *current* address of another service it needs to call, given that this address is not fixed and not knowable in advance?"

### 12.2 DNS-based discovery

The simplest, most familiar approach: a service is reachable at a hostname (`user-service.internal`), and DNS (Lecture 2 §4, Lecture 4 §4.1) resolves that name to whatever the current set of healthy addresses actually is, updated as instances change. Simple and broadly compatible (any HTTP client already knows how to do DNS resolution), but constrained by DNS's own mechanics — caching/TTL behavior (Lecture 8 §4.1's stale-DNS scenario) can mean a consumer's view of "current" addresses lags slightly behind reality.

### 12.3 Registry-based discovery

A dedicated **service registry** (a system whose entire job is tracking "which instances of which services currently exist and are healthy," updated in something closer to real time) that services actively register with on startup/deregister from on shutdown, and that consumers (or a proxy) query directly, rather than going through DNS's caching-oriented design. This is common in container-orchestration environments (a scheduler that already knows exactly which instances it just started or stopped is a very natural source of this information) and generally offers fresher, more precise information than DNS-based discovery, at the cost of needing a dedicated system to run and depend on (itself now a service with its own availability/consistency trade-offs, per §6–§7 of this very lecture — service discovery systems are themselves distributed systems, subject to everything this lecture teaches).

### 12.4 Client-side vs. server-side discovery

**Client-side**: the caller itself queries the discovery mechanism (DNS or a registry) and picks a destination directly. **Server-side**: the caller sends its request to a fixed, stable address (a load balancer or proxy), and *that* component is the one that actually performs discovery and destination selection on the caller's behalf — this is precisely YARP's position (Lecture 5 §6's route → cluster → destination model): clients calling YARP never perform service discovery themselves at all; YARP does it for them, which is exactly why clients can stay simple and never need to know that backend topology changes constantly in the first place (Lecture 4 §4.2's whole point, restated through the service-discovery lens specifically).

---

## 13. Distributed State — Why It's Genuinely Hard

### 13.1 The mechanism, stated precisely

Return to §3's root fact one more time, now made fully concrete: on one machine, "the current value of X" is unambiguous, because there's exactly one copy, and reading/writing it is effectively instantaneous and atomic from the perspective of other code on that same machine. The moment X is replicated (§5) across multiple machines, **"the current value of X" stops being a single, well-defined thing** — each machine has its *own* local copy, updated via messages that take real, nonzero time to arrive (Lecture 2 §9) and might arrive out of order, be delayed, or be lost entirely (Lecture 2 §10.3). There is no instantaneous way for every machine to agree on "the current value," full stop — only ways to get them to *eventually* agree (§6.2), or to make some of them wait until they can be sure they agree (§6.1), each with the costs already covered in §6–§7.

### 13.2 Why this is the "hard" in "distributed systems are hard"

Nearly everything a working programmer finds surprising or difficult about distributed systems, the first time they encounter it, traces back to this one mechanism: **updates aren't instantaneous everywhere at once, and there's no way to make them be** (this is a physical fact about information needing time to travel, not a solvable engineering shortcoming). Every concept in this lecture — replication's staleness window (§5.4), the strong/eventual consistency choice (§6), CAP's forced trade-off during a partition (§7) — is a different *consequence* or *coping strategy* for this same, single underlying fact.

### 13.3 Why statelessness (§4.3) is the practical escape hatch

This is worth connecting explicitly, as the lecture's closing loop: §4.3 already told you *that* stateless services are easier to scale — now you can see precisely *why*, in terms of this section's mechanism. A stateless service has no local copy of anything that needs to agree with any other copy — there's nothing for §13.1's problem to even apply to, within that service. This is precisely why real architectures work so hard to concentrate unavoidable state into a small number of dedicated, carefully-designed stores (a database handling replication/consistency deliberately and explicitly, per §5–§6) rather than letting every service independently hold its own bit of state — it's not just a scaling convenience, it's a deliberate strategy for minimizing how much of the system has to deal with §13.1's fundamentally hard problem at all.

---

## 14. Common Misconceptions

- **"More machines always means more capacity, automatically."** §4.3 shows this holds cleanly for stateless services but requires real, deliberate design (session affinity, or moving state out entirely) for stateful ones.
- **"Eventual consistency is just a worse, cheaper version of strong consistency."** §6.3's example shows it's a legitimate, often *better* choice for data where brief staleness is harmless — the "right" choice depends on the data's meaning, not a universal quality ranking.
- **"CAP means you permanently give up consistency or availability, forever, as an architectural choice."** §7.2 is explicit: it's about what you're forced to choose *during* an active network partition specifically, not a permanent, all-the-time sacrifice.
- **"Average latency is a reasonable single number to describe system performance."** §8.1–§8.3 directly refute this — the average can look fine while a meaningful fraction of real users experience something far worse, and that fraction matters more than it sounds like it should once you account for request fan-out (§8.3).
- **"Adding more of any resource will fix a throughput problem."** §9.3 is explicit — only adding capacity to the actual bottleneck resource helps; adding capacity anywhere else does nothing.
- **"Queues are just an implementation detail, not something worth reasoning about explicitly."** §10.3 shows queue depth directly and causally determines latency — reasoning about queues explicitly is often the fastest way to correctly diagnose a "the service got slow" incident.
- **"Service discovery is a solved, boring problem."** §12.3's closing point is worth taking seriously — a service registry is itself a distributed system, subject to every trade-off in this lecture, not something exempt from them.

---

## 15. Production Perspective: 10 → 10,000 → 1,000,000 → 100,000,000 Requests

**~10 requests, one instance of everything, no replication**: none of this lecture's trade-offs are visible — there's exactly one copy of any data, so §6's consistency choice and §7's CAP trade-off are simply not in play yet; horizontal scaling (§4) is unnecessary.

**~10,000 requests/sec, a few instances, first read replica introduced**: §5.4's staleness window becomes real and occasionally noticeable — this is roughly the scale where a team first has to consciously decide, for a specific piece of data, whether strong or eventual consistency is acceptable (§6.4's table), often for the first time in the system's life. Service discovery (§12) moves from "a static config file listing two addresses" to something that actually needs to track change.

**~1,000,000 requests/sec, many services, multiple regions**: CAP's forced trade-off (§7.2) stops being a rare, ignorable event — network partitions between regions or availability zones become a real, occasionally-occurring operating condition that the system's behavior during them has to be a deliberate design decision, not an afterthought. p99/p99.9 latency (§8.3) is now actively monitored and treated as a primary reliability signal, specifically because of the fan-out amplification effect at this scale. Dependency graphs (§11) are complex enough that identifying true bottleneck/critical-path/high-fan-in nodes requires deliberate analysis, not intuition.

**~100,000,000 requests/sec**: distributed state (§13) is a first-class, continuously-managed concern across the whole organization, not something confined to "the database team" — caching strategies, replication topology, and consistency choices are made deliberately and differently for different pieces of data, informed by exactly the §6.3-style reasoning ("what actually happens if this is briefly stale") applied systematically across the whole system rather than case by case.

---

## 16. Performance Implications

- **Push state out of horizontally-scaled tiers wherever possible** (§4.3, §13.3) — this is the single highest-leverage architectural decision for making horizontal scaling actually easy rather than a constant fight.
- **Choose consistency level deliberately, per piece of data, based on real consequences of staleness** (§6.3–§6.4) — this is a domain decision, not a technical default to leave unexamined.
- **Watch p99/p99.9, not just average or even p50, for anything with meaningful request fan-out** (§8.3) — this is where tail latency's amplification effect makes the "rare" case common in practice.
- **Identify the actual bottleneck resource before trying to fix a throughput problem** (§9.3) — improving a non-bottleneck resource is wasted effort that won't move the needle.
- **Bound queues and apply backpressure at architectural boundaries between services, not just within one component** (§10.4) — an unbounded queue anywhere in a dependency graph (§11.1) is a latent latency and memory risk, regardless of which service owns it.
- Deep distributed-database internals (specific replication protocols, conflict-resolution algorithms for eventual consistency) are **not** where your effort belongs yet — §18 is explicit about this.

---

## 17. YARP Connection — What's Directly Relevant vs. Background

This lecture covered a genuinely wide span of ideas — worth being explicit and disciplined about which ones YARP itself directly embodies versus which ones are context for reasoning about the *systems* YARP operates inside, since conflating the two would blur exactly the kind of precise understanding this series has been building toward.

### 17.1 Directly relevant to YARP — expect to see these ideas embodied in its actual behavior

- **Horizontal scaling and statelessness (§4)**: YARP itself is designed to be run as a stateless, horizontally-scaled tier (Lecture 8 §4.2's point about the proxy layer needing its own redundancy) — multiple YARP instances behind their own load-balancing layer, each one interchangeable, exactly matching §4.3's stateless model.
- **Latency percentiles (§8)**: YARP sits on the critical path (§11.3) of every request it forwards — its own added latency, and its p99/p99.9 behavior specifically (Lecture 7 §8.2's tail-latency concern, now with full percentile vocabulary), directly affects every request passing through it, amplified by whatever fan-out exists on the client side.
- **Throughput, saturation, and bottlenecks (§9)**: directly Lecture 7's entire territory (connection pools, thread pool, memory) — now correctly framed as "identify YARP's actual bottleneck resource," rather than assuming any one dimension (CPU, connections, memory) is automatically the limiting one.
- **Queues and backpressure (§10)**: YARP's connection-pool wait queue (Lecture 7 §5.4) and any request-level backpressure/rate limiting (Lecture 4 §13.4, Lecture 7 §7.5) are direct, concrete instances of this lecture's queueing/backpressure principles.
- **Service dependencies and the critical path (§11)**: YARP is, by definition, on the critical path (§11.3) between clients and backends — understanding fan-out/fan-in in the dependency graph directly explains why a shared backend cluster's health matters disproportionately (Lecture 6, Lecture 8 §4.3's correlated-failure framing).
- **Service discovery (§12)**: this is close to YARP's core job, precisely stated — YARP performs **server-side discovery** (§12.4) on behalf of every client that talks to it, via its configuration/destination model (Lecture 5 §7's `IProxyConfigProvider`, whether backed by DNS-style resolution or a registry-style dynamic config source) — clients never need to know backend addresses change at all, which is exactly §12.4's point made concrete.

### 17.2 Background — relevant to systems YARP sits in front of, not to YARP itself

- **Replication and consistency (§5–§6)**: YARP itself is stateless (§17.1) and doesn't replicate data — but the *backend services* it forwards to very often do, and reasoning correctly about *their* behavior (a read hitting a stale replica, a write briefly unavailable during a partition) requires this lecture's vocabulary, even though YARP's own code has no direct involvement in it.
- **CAP theorem (§7)**: the same relationship — YARP doesn't make CAP trade-offs itself, but the backends, databases, and config sources it depends on do, and understanding *why* one of those might behave oddly during a network problem requires this framework.
- **Distributed state (§13)**: directly the same pattern — YARP is deliberately built to avoid needing to solve this problem itself (§17.1's statelessness point), which is exactly *why* it doesn't need Paxos/Raft-style mechanisms (§18) — but the systems around it frequently do need to solve it, and you'll need this lecture's framing to understand *their* design choices when you encounter them.

The unifying takeaway: **YARP's own design is, in large part, a deliberate exercise in staying on the "directly relevant" side of this list — statelessness, discovery, and queueing/backpressure — specifically so it never has to take on the "background" side's much harder problems (replication, consistency, CAP) itself.** Recognizing that boundary precisely is exactly what this lecture set out to teach.

---

## 18. What I Don't Need to Know Yet — and Why

- **Consensus algorithms (Paxos, Raft)**: these solve the deep, hard problem of getting multiple machines to agree on a single value despite failures and network unreliability — genuinely foundational to how a primary is elected (§5.2) or how a strongly-consistent distributed store (§6.1) actually achieves its guarantee internally. You don't need this because YARP, per §17.2, deliberately doesn't need to solve this problem itself — it's stateless. If you eventually work on a system that *does* need this (a database, a coordination service), it deserves its own dedicated, careful treatment — it's genuinely one of the harder topics in this entire field, not something to absorb as a footnote.
- **Byzantine fault tolerance**: consensus algorithms robust even against nodes that behave *maliciously* or *arbitrarily incorrectly* (not just crashing cleanly) — relevant to blockchain systems and some high-security distributed systems, essentially never relevant to typical backend/cloud infrastructure work, where you can generally assume nodes fail by crashing or being slow (Lecture 8's failure model), not by lying.
- **Specific conflict-resolution strategies for eventually consistent systems** (last-write-wins, vector clocks, CRDTs) — real, important techniques for *implementing* eventual consistency correctly; recognize they exist (§6.2 told you convergence happens "eventually," these are *how*), not required depth for reasoning about a system that already uses them.
- **The internal mechanics of specific service-registry systems** (etcd, Consul, Kubernetes' internal service discovery) — §12.3's conceptual role is sufficient; the specific technology choices are implementation detail you can pick up if and when you're actually configuring one.
- **Formal proofs or the precise mathematical statement of CAP** — §7's practical framing (the forced choice during a partition) is deliberately the depth this series aims for, per your explicit instruction; the formal theorem is a separate, optional rabbit hole.

---

## 19. Knowledge Check

1. Using §4.3, explain why a stateless service can be trivially load-balanced by any of Lecture 6's algorithms, while a stateful one requires either session affinity or moving the state out entirely — what specifically breaks if you load-balance a stateful service naively?
2. Using §6.3's like-counter vs. bank-balance example, describe a third, different kind of data, and explain which consistency model you'd choose for it and why — justify it in terms of "what actually happens if it's briefly stale," not a general preference.
3. A system's average latency is 40ms, but its p99 is 3 seconds. Using §8.1 and §8.3, explain why this system might feel "fine" on a dashboard showing only averages, but produce genuinely bad experiences for a meaningful fraction of real users — especially ones whose requests fan out to many backend calls.
4. A team adds more application servers to fix a throughput problem, but throughput doesn't improve. Using §9.3, explain what this tells you about where they should have looked instead.
5. Using §12.4, explain precisely why a client talking to YARP never needs to perform service discovery itself, and what YARP is doing on the client's behalf to make that true.
6. Using §17's split, explain why YARP itself doesn't need a consensus algorithm (§18), but a database sitting behind one of YARP's backend clusters plausibly might.

---

## 20. Practical Exercise

This exercise makes replication staleness and the strong-vs-eventual consistency trade-off directly observable, using nothing but two local processes and a plain in-memory "replica."

### Step 1 — A tiny "primary" and "replica" pair

```csharp
// Primary/Program.cs
var builder = WebApplication.CreateBuilder(args);
var app = builder.Build();

int likeCount = 1000;
var replicaClient = new HttpClient();

app.MapPost("/like", async () =>
{
    likeCount++;
    // Simulate real replication lag: fire-and-forget the update to the
    // "replica," with an artificial delay, instead of waiting for it.
    _ = Task.Run(async () =>
    {
        await Task.Delay(1500); // artificial replication lag
        await replicaClient.PostAsJsonAsync("http://localhost:6011/sync", likeCount);
    });
    return Results.Ok(new { likeCount, source = "PRIMARY (always current)" });
});

app.Run("http://localhost:6010");
```

```csharp
// Replica/Program.cs
var builder = WebApplication.CreateBuilder(args);
var app = builder.Build();

int replicatedCount = 1000;

app.MapPost("/sync", (int count) => { replicatedCount = count; return Results.Ok(); });
app.MapGet("/like-count", () => Results.Ok(new { likeCount = replicatedCount, source = "REPLICA (may be stale)" }));

app.Run("http://localhost:6011");
```

### Step 2 — Observe staleness directly

```bash
curl -X POST http://localhost:6010/like     # like it via the primary
curl http://localhost:6011/like-count       # immediately check the replica
```

You should see the replica still reporting the *old* count immediately after the like — real, observable staleness, matching §6.3's worked example. Wait ~2 seconds and repeat the second command; the replica should now show the updated count — §6.2's "eventually" consistent, made concrete with a real stopwatch instead of an abstract diagram.

### Step 3 — Reason about the trade-off explicitly

Modify `Primary/Program.cs`'s `/like` handler to instead **await** the replication call before responding (removing the `Task.Run` fire-and-forget, and awaiting `replicaClient.PostAsJsonAsync` directly, inline). Re-run Step 2's `curl` sequence. The primary's response should now visibly take the full ~1.5 seconds (you've just made it strongly consistent by forcing the write to wait for replication) — directly demonstrating §6.4's latency-cost trade-off with your own stopwatch, not just the comparison table.

---

## 21. "Ready to Move On" Criteria

Before starting the next lecture, you should be able to explain — out loud, in your own words:

- [ ] Why statelessness, not just "having more machines," is what makes horizontal scaling genuinely easy.
- [ ] Why replication exists, and the concrete cost (staleness) it introduces even as it buys availability and read capacity.
- [ ] Strong vs. eventual consistency, with your own concrete example of data suited to each.
- [ ] What a network partition actually is, and the forced choice CAP describes during one — in your own words, without needing the formal theorem statement.
- [ ] Why an average latency figure can look fine while p99 tells a very different, more important story — especially once you factor in request fan-out.
- [ ] The difference between throughput, capacity, saturation, and bottleneck, and why fixing the wrong resource doesn't help.
- [ ] Why queues exist, and why queue depth directly and causally determines added latency.
- [ ] What a service dependency graph's shape (fan-in, fan-out, critical path) tells you about failure propagation risk.
- [ ] How service discovery works in practice, and specifically what YARP does on a client's behalf so the client never needs to do it themselves.
- [ ] Why distributed state is fundamentally hard (the no-shared-memory, real-latency mechanism), and why that's precisely the problem YARP's own stateless design deliberately avoids having to solve.
- [ ] Which of this lecture's concepts are things you should expect to find directly inside YARP's own behavior, and which are context for reasoning about the systems around it.

If these feel solid, you've now built the broad distributed-systems vocabulary and reasoning framework this series has been implicitly relying on since Lecture 4 — everything from here forward can build on this shared foundation explicitly, rather than needing to re-derive it each time a new lecture brushes up against a distributed-systems concern.
