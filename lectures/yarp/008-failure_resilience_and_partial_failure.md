# Lecture 8: Failure, Resilience, and Partial Failure in Distributed Systems

Series: YARP Learning Series
Builds on: [Lecture 2 §10](002-tcp_ip_sockets_and_network_connections.md) (connection-level failure taxonomy), [Lecture 4 §13](004-reverse_proxies_and_api_gateways.md) (proxy-level failure scenarios), [Lecture 6 §6, §9](006-load_balancing_and_traffic_distribution.md) (health checking, distributed-scale complications), [Lecture 7 §7](007-concurrency_connection_pooling_and_high_throughput_networking.md) (backpressure within one component).
This lecture assembles those pieces into a systems-level view of failure, and adds several genuinely new ideas: deadlines vs. timeouts, retry storms, circuit breakers, liveness vs. readiness, cascading failure, and — as the major focus — why "is the system up" stops being a meaningful question at real scale.

---

## 1. Learning Objectives

By the end of this lecture you should be able to:

1. State and apply the principle "things fail independently" to concrete scenarios, and explain why it's the foundational fact everything else in this lecture responds to.
2. Distinguish nine specific failure modes and state the different observable symptom and correct response for each.
3. Explain the difference between a timeout and a deadline, and why naive per-hop timeouts compound badly across a call chain.
4. Explain when retries help, when they actively make things worse, and how exponential backoff with jitter specifically prevents retry storms.
5. Explain what a circuit breaker does and why it's a different mechanism from a health check, even though both stop traffic to a failing destination.
6. Distinguish liveness from readiness, and active health checking from passive failure detection.
7. Trace how a failure at one layer of a service chain propagates and amplifies through the layers above it.
8. Explain, with concrete numeric reasoning, why "the system is up" is often not a meaningful binary state in a real distributed system.
9. Walk through specific YARP scenarios — a slow destination, an unhealthy destination, an overloaded proxy — and state exactly what YARP should do in each.

---

## 2. Prerequisite Concepts

You've already met most of the raw material this lecture organizes: Lecture 2 §10 taught what happens mechanically when a connection fails in various ways; Lecture 4 §13 applied that to a single reverse proxy's behavior; Lecture 6 §6 taught health checking, and Lecture 6 §9 already opened the door to distributed-scale complications (thundering herd, cascading overload) within the load-balancing context specifically. This lecture generalizes those ideas beyond one component: what happens when failure and overload propagate *between* independent services in a chain, and what a system does architecturally to keep a local failure from becoming a global one.

---

## 3. Core Mental Model — Things Fail Independently

> **In a distributed system, things fail independently.**

This is the single fact everything in this lecture responds to, so it's worth sitting with concrete examples before moving on:

- A server crashes because of a hardware fault. The server next to it, in the same rack, keeps running — nothing about one machine's failure obligates any other machine to fail too.
- A network link between two data centers degrades. Traffic *within* either data center is completely unaffected.
- A specific backend instance runs out of memory and becomes unresponsive. The load balancer in front of it, the client behind it, and every *other* backend instance are all still working exactly as before.
- A client's Wi-Fi drops. The server it was talking to has no idea anything happened at all, and continues operating normally.

The reason this deserves to be a "fundamental principle" rather than an obvious throwaway line: **a system built with the unconscious assumption that failure is all-or-nothing — "the system is either working or it's down" — is structurally unprepared for the actual, default behavior of distributed systems, which is that some parts fail while other parts keep working, constantly, as an ordinary condition rather than a rare edge case.** Every mechanism in this lecture — timeouts, retries, circuit breakers, health checks, backpressure — exists specifically to let a system keep functioning *given* that some of its parts will, independently and unpredictably, stop working some of the time.

---

## 4. Failures — The Full Catalog

Each of these produces a genuinely different symptom and demands a genuinely different response. Several were covered mechanically in Lecture 2 §10 and Lecture 4 §13 — here they're gathered as one complete, systems-level checklist, with the previously-uncovered ones (DNS failure, proxy crash, database unavailability) taught in full.

| Failure | Symptom | Correct response |
|---|---|---|
| Server crashes | Connection refused/reset (Lecture 2 §10.5) | Health check marks it unhealthy (Lecture 6 §6); load balancer routes around it |
| Server becomes slow | Connection healthy, response delayed (Lecture 2 §10.4) | Request timeout (§5); possibly a circuit breaker (§7) if sustained |
| Network fails | Timeout, no response at all (Lecture 2 §10.1–§10.2) | Timeout + retry against a different path/destination if safe (§6) |
| Packets disappear | Usually invisible — TCP retransmits (Lecture 2 §10.3) | Nothing needed at the application layer; this is the *expected*, self-healing case |
| DNS fails | See §4.1 below | Cached/stale results, fallback resolvers, or fail the connection attempt outright |
| Connections reset | Immediate, explicit error (Lecture 2 §10.5) | Fast failure detection; route around the destination |
| Client disconnects | Server should notice and cancel work (Lecture 2 §10.6, Lecture 3 §9.4) | Cancellation propagation, not continued wasted work |
| Proxy crashes | See §4.2 below | Multiple proxy instances behind their own load-balancing layer |
| Database becomes unavailable | See §4.3 below | Often a *shared*, correlated failure — breaks the independence assumption |

### 4.1 DNS failure — a new case

Recall Lecture 1 §5 and Lecture 2 §4: DNS resolution happens *before* any HTTP or even TCP activity — it's a separate system entirely, translating a hostname into an IP address. If DNS fails, three distinct sub-cases matter:

- **The DNS server itself is unreachable**: name resolution can't complete at all — the connection attempt fails before a socket is even opened (Lecture 2 §6.2 never gets a chance to start).
- **DNS returns a stale result**: a cached record still points at an IP address for a server that's since been decommissioned or replaced — this is especially relevant for systems using DNS-based service discovery (resolving a backend's address dynamically, rather than a static configured IP, per Lecture 5 §6's "destinations change constantly" point) — the connection attempt proceeds normally but lands on a dead or wrong destination.
- **DNS resolution is slow**: adds pure, invisible latency to connection setup, on top of Lecture 2 §6.2's handshake cost, before any of this lecture's other mechanisms even get involved.

This matters specifically for infrastructure like a reverse proxy because destinations are frequently *not* static IPs — they're resolved, cached, and re-resolved on some schedule, meaning DNS becomes a genuine, independent failure surface sitting entirely outside the HTTP/TCP mechanics covered so far in this series.

### 4.2 Proxy crashes — the proxy is not exempt from §3's principle

It's tempting to think of "the proxy" as the reliable thing sitting in front of the potentially-unreliable backends — but the proxy is itself a process, on a machine, subject to exactly the same independent-failure principle as everything else. If a single proxy instance is the *only* thing between clients and backends, it is a single point of failure for the entire system, regardless of how well-architected the backends behind it are (Lecture 4 §4.2's reliability argument, applied recursively one layer up). This is exactly why real deployments run **multiple proxy instances**, themselves behind a lower-level load-balancing layer (Lecture 4 §9.1's "Load Balancer → Reverse Proxy" stacking) — the proxy tier needs the same redundancy reasoning applied to it that it applies to the backends it protects.

### 4.3 Database becomes unavailable — a correlated failure

This case deserves special attention because it violates §3's independence assumption in an important way: if many otherwise-independent services all depend on the *same* database, that database becoming unavailable causes all of them to fail **simultaneously and for the same underlying reason** — not independently at all. This is called a **correlated failure**, and it's a genuinely different risk profile than the independent failures in the rest of this table: instead of "some fraction of many independent things are down at once, by chance," you get "everything sharing this one dependency is down at once, together, because of it." Recognizing shared dependencies (a database, a shared cache, a common upstream service) as correlated-failure risk — rather than reasoning about every component's reliability as if it were fully independent — is a genuinely important, easy-to-miss piece of real systems design, and it's the natural bridge into this lecture's cascading-failure section (§10).

---

## 5. Timeouts

### 5.1 Why timeouts are necessary — restated precisely

Recall Lecture 2 §10.4's exact point: TCP alone can never tell you the *application* on the other end is stuck — a connection can be perfectly healthy while nothing useful is happening. Without an explicit, application-level timeout, a caller waiting on a hung dependency waits **forever** — no error, no signal, just indefinite consumption of whatever resource (a thread, per Lecture 7 §6.3; a pooled connection, per Lecture 7 §5.4) that wait is holding. A timeout is the caller unilaterally deciding "I am no longer willing to wait past this point" — it's not something the failing side does *to* you; it's a defensive limit you impose on yourself.

### 5.2 Connection timeout vs. request timeout

These are genuinely different waits, and conflating them is a common source of confusing configuration:

- **Connection timeout**: how long to wait for the TCP (and TLS) handshake itself (Lecture 2 §6.2) to complete. A connection timeout firing means you never even got as far as sending your actual request.
- **Request timeout**: how long to wait, *after* a connection is established and the request has been sent, for a complete response. A request timeout firing means the request was sent, but no (complete) answer came back in time.

These often warrant different values — connection establishment is usually expected to be fast and consistent (a handshake is a fixed, small amount of work), while actual request processing time can legitimately vary a lot depending on what the request is asking for.

### 5.3 Cancellation, revisited

Lecture 3 §9.4 already gave you the C# mechanism (`CancellationToken`); here's the systems framing: cancellation is how a timeout (or a client disconnect, Lecture 2 §10.6) actually stops ongoing work, rather than merely making the *caller* stop waiting while the callee keeps working pointlessly in the background. A timeout without cancellation propagation still protects the caller's own resources, but does nothing to stop wasted work happening downstream — a real, meaningful gap worth noticing (this is precisely what Lecture 4 §13.3 already flagged as a proxy-specific concern).

### 5.4 Deadlines — a genuinely different, more sophisticated idea

Here's the piece not yet covered in this series, and it matters a lot for any multi-hop call chain (exactly what a reverse proxy sits inside):

A **timeout** is local — "how long am I, this one component, willing to wait for this one call." A **deadline** is global — "the absolute point in time by which the *entire end-to-end operation*, across every hop it touches, must be finished" — and it's meant to be **propagated** along the whole call chain, so every hop can compute its own *remaining* budget from the same shared deadline, rather than each hop independently applying its own full timeout.

Here's why the distinction matters concretely:

```
   NAIVE per-hop timeouts, each hop applying its OWN full 5s timeout independently:

   Client ──(up to 5s)──► A ──(up to 5s)──► B ──(up to 5s)──► C

   WORST CASE: Client could end up waiting up to 15s total, even though
   it only actually wanted to wait 5s for the whole thing — because each
   hop's timeout is measured from ITS OWN start, not from the client's.


   DEADLINE propagated through the chain (client sets an ABSOLUTE deadline,
   e.g. "5s from now," and passes it along):

   Client sets deadline = now + 5s
        │
        ▼
   A receives deadline, computes: "I have (deadline - now) remaining" ≈ 5s,
   passes the SAME absolute deadline to B
        │
        ▼
   B receives the SAME deadline, computes remaining ≈ 4.7s (some time
   already elapsed getting here), passes it to C
        │
        ▼
   C receives the SAME deadline, computes remaining ≈ 4.4s

   WORST CASE: bounded by the ORIGINAL 5s, because every hop is
   racing against the SAME finish line, not restarting its own clock.
```

Deadline propagation is a meaningfully more advanced technique than independent per-hop timeouts, and not every system implements it — but understanding *why* it exists (bounding total end-to-end latency across a multi-hop chain, rather than letting per-hop timeouts compound) is exactly the kind of thing that will make sense of certain header/context-passing code you might encounter in more sophisticated distributed systems (and in YARP's own request context, §11).

---

## 6. Retries

### 6.1 Why retries help

Recall Lecture 2 §10.3: most packet loss is transient and self-healing at the TCP layer already, invisibly. But some failures are transient at a *higher* level — a backend instance was momentarily overloaded and rejected one request but is fine a moment later, or a load balancer happened to route to an instance that was just about to be marked unhealthy. A well-placed retry, especially against a **different destination** (Lecture 6's whole point of having multiple destinations at all), can turn a would-be failure into a successful response the client never even notices was troubled.

### 6.2 Why retries can hurt

Retrying is not free, and it's actively dangerous in two distinct ways:

- **Non-idempotent operations** (Lecture 1 §4.4): retrying a `POST /charge-card` that actually succeeded server-side, but whose *response* was lost or delayed, can cause the operation to happen twice. This is why retry logic must respect the safety/idempotency distinction from Lecture 1 §4.4, or use an explicit **idempotency key** (a unique token the client generates and sends with the request, letting the server recognize and safely no-op a duplicate attempt of the *same* logical operation) when retrying something that isn't naturally idempotent.
- **Retrying into an already-overloaded system makes the overload worse, right when it can least afford it.** If a backend is failing *because* it's overloaded, every retry against it (or against its siblings in the same cluster) adds more load precisely at the moment capacity is already insufficient — retries meant to help the client can directly work against the system's ability to recover at all.

### 6.3 Retry storms

This is §6.2's second danger, at scale: if **many independent clients** experience the same failure at roughly the same time (a shared dependency briefly failing, §4.3's correlated-failure case) and all retry using the same fixed delay, their retries arrive **synchronized**, as a sudden spike, rather than spread out — a direct structural cousin of Lecture 6 §9.2's thundering herd, but now caused by client-side retry behavior instead of load-balancer recovery behavior.

```
   Many independent clients hit a shared failure at t=0, all retry after
   exactly 1 second, with no variation:

   t=0:  [failure across many clients simultaneously]
   t=1s: [ALL clients retry AT ONCE]  ──► sudden spike, possibly re-triggering
                                            the SAME overload that caused the
                                            original failure, now worse
   t=2s: [ALL clients retry AGAIN, together]  ──► repeats, potentially forever
```

This is a genuinely dangerous, self-sustaining failure pattern — a system can be kept perpetually unable to recover purely by synchronized retry pressure, even after whatever originally caused the problem would otherwise have resolved on its own.

### 6.4 Exponential backoff

**Idea**: each successive retry waits longer than the last, growing exponentially (1s, 2s, 4s, 8s, ...) rather than retrying at a fixed interval. This directly reduces sustained pressure on a struggling dependency — instead of hammering it at a constant rate, retry pressure tapers off the longer a failure persists, giving the dependency more room to actually recover rather than being continuously re-overwhelmed by retry attempts arriving at a steady, undiminished rate.

### 6.5 Jitter

**Idea**: add randomness to each backoff delay, so retries from many independent clients — even ones all using the *same* exponential backoff schedule — don't land at the exact same moments. This is the direct, specific fix for §6.3's retry storm: without jitter, exponential backoff alone still leaves every client synchronized (they all wait exactly 1s, then exactly 2s, then exactly 4s, together) — jitter spreads that same population of retries out over a window of time instead of a single instant, turning a sharp, dangerous spike into a smoother, much more manageable trickle.

```
   WITHOUT jitter (synchronized, even with backoff):        WITH jitter (spread out):

   retry attempts, all clients:                              retry attempts, all clients:
   │███████                                                  │▁▂▃█▄▂▁
   │        (1s later) ███████                                │      ▂▃▄█▅▃▂
   └───────────────────────────► time                        └───────────────────────────► time
   (still a sharp spike each round,                          (smoothed into a manageable
    just further apart)                                        trickle, no synchronized spike)
```

### 6.6 The full, correct retry policy — assembled

A well-built retry mechanism combines all of the above: **retry only when safe (idempotent, or protected by an idempotency key, §6.2); retry against a different destination when possible (Lecture 6); use exponential backoff (§6.4) with jitter (§6.5); and cap the total number of attempts** (an unbounded retry loop is its own resource-exhaustion risk, tying directly back to Lecture 7 §7's backpressure principle — a retry that never gives up is functionally identical to an unbounded queue that never rejects work).

---

## 7. Circuit Breakers

### 7.1 The problem a circuit breaker solves

Retries (§6) and health checks (§8 below) both react *after* a failure — a request is attempted, it fails, and *then* something responds. A circuit breaker is about **stopping yourself from even attempting calls to a dependency you already have strong evidence is currently broken** — protecting your *own* resources (threads, connections, per Lecture 7) from being wasted on calls you can predict will fail, and — just as importantly — protecting the *struggling dependency itself* from continuing to receive load while it's trying to recover, which is precisely §6.2's "retrying into overload makes it worse" problem, addressed proactively rather than reactively.

### 7.2 The three states

```
        failures exceed threshold
   CLOSED ──────────────────────────► OPEN
   (normal: requests flow,             (fail FAST, without even
    failures are tracked)               attempting the call, for
      ▲                                 a cooldown period)
      │                                        │
      │ success                                │ cooldown elapses
      │                                        ▼
      └──────────────────── HALF-OPEN
                             (cautiously let a SMALL number of
                              requests through as a real-world
                              test — success? → CLOSED.
                              failure? → back to OPEN)
```

- **Closed**: the normal state — requests pass through freely, while the circuit breaker quietly tracks the failure rate.
- **Open**: once failures cross a configured threshold, the breaker "trips" — every subsequent call fails **immediately, locally, without ever attempting the network call at all** — this is the key mechanical difference from a plain timeout: a timeout still pays the cost of waiting; an open circuit breaker skips the attempt entirely.
- **Half-open**: after a cooldown period, the breaker cautiously allows a small number of real requests through as a live test of whether the dependency has actually recovered — succeeding moves back to closed; failing sends it straight back to open, without a full flood of traffic resuming in either direction. This cautious, limited re-test is conceptually the same instinct as Lecture 6 §6.5's gradual recovery reintroduction, applied at the level of "should I even try calling this dependency" rather than "how much traffic should this destination receive."

### 7.3 Circuit breaker vs. health check — genuinely different mechanisms

Worth being precise about this, because they can look similar from a distance: a **health check** (Lecture 6 §6) is typically the *load balancer's* (or proxy's) own assessment of a *destination's* health, used to filter which destinations are even candidates for selection. A **circuit breaker** is typically a *caller's* (or a specific dependency-relationship's) protective mechanism, and can exist even without any load-balancing layer involved at all — a single service calling a single downstream dependency directly can still benefit from a circuit breaker, entirely independent of whether there's a proxy or load balancer anywhere in the picture. They're complementary, often used together, and solve overlapping but distinct problems: one is about *routing decisions among many candidates*; the other is about *whether to even attempt a call to one specific dependency at all*.

---

## 8. Health Checks

### 8.1 Liveness vs. readiness — a distinction this series hasn't made yet

These answer genuinely different questions, and conflating them leads to genuinely wrong operational responses:

- **Liveness**: "is this process alive and functioning at all — or is it deadlocked, crashed, or otherwise stuck in a state it will never recover from on its own?" A liveness failure calls for a **restart** — there's no reason to expect the process to fix itself.
- **Readiness**: "is this instance *currently* able to serve traffic well — even though the process itself is alive and fine?" A readiness failure calls for **temporarily removing it from traffic rotation**, not restarting it — common causes include: still warming up after starting, a dependency it needs (like §4.3's database) is itself temporarily unavailable, or it's intentionally shedding load under its own backpressure (Lecture 7 §7).

```
   Process is ALIVE but NOT READY:                Process is NOT ALIVE (liveness failure):

   ┌─────────────────────┐                        ┌─────────────────────┐
   │  still running fine,   │                        │  deadlocked / crashed  │
   │  just warming up or       │  → keep the process,     │                        │  → RESTART it,
   │  waiting on a dependency   │    stop sending it        │  will never recover      │    don't just
   │                            │    traffic for now         │  on its own                │    wait for it
   └─────────────────────┘                        └─────────────────────┘
```

Treating a readiness problem as a liveness problem (restarting a perfectly healthy process just because it's temporarily not ready) is wasteful and can even make recovery slower (a fresh restart re-triggers warm-up, §4.2-style, right when you least want more disruption). Treating a liveness problem as a readiness problem (leaving a genuinely stuck process running, just excluded from traffic, hoping it'll sort itself out) leaves a dead process consuming resources indefinitely for no benefit.

### 8.2 Active health checks and passive failure detection, revisited

Lecture 6 §6.2–§6.3 already taught these mechanically — the systems-level framing to add here: **active checks answer the liveness/readiness question proactively, on a schedule, independent of real traffic; passive detection answers it reactively, by observing real request outcomes.** Both remain valuable together (Lecture 6 §6.4's reasoning is unchanged) — this lecture's addition is simply that "health," once you have the liveness/readiness split, is itself not one single question either check needs to answer, but two, and a mature health-check implementation typically answers both separately (a `/healthz/live` and a `/healthz/ready` endpoint, for instance, is a common real convention reflecting exactly this split).

---

## 9. Backpressure, at the Multi-Service Level

Lecture 7 §7 taught backpressure within a single component (a queue, a connection pool). Here's the same principle, one level up: **when Service B is under backpressure and starts rejecting or shedding excess load, that protects Service C (B's downstream) from being overwhelmed by B's own accumulated backlog or panicked retries, and it protects Service A (B's caller) from waiting indefinitely on a B that's already lost the ability to make timely progress.** Backpressure isn't just self-protective for the component applying it — propagated correctly through a chain, it's what prevents the specific failure pattern §10 covers next: one component's overload silently becoming every other component's problem too.

---

## 10. Cascading Failures

### 10.1 The chain

```
   Service A  ──►  Service B  ──►  Service C
```

### 10.2 How one failure propagates — the mechanism, precisely

Suppose C becomes slow (not down — slow, per §4's "server becomes slow" row, exactly Lecture 2 §10.4's scenario). Trace what happens without any of this lecture's mitigations in place:

1. **B's calls to C take much longer than usual.** Every request B is currently handling that needs C is now holding onto whatever resource it's using to wait — a thread (Lecture 7 §6.3), a pooled connection (Lecture 7 §5.4) — for far longer than normal.
2. **B's own resources start filling up** with requests stuck waiting on C. B has a finite thread pool, a finite connection pool to C — and all of it is now tied up waiting, not doing useful work.
3. **B itself becomes slow to A** — not because anything is wrong with B's own code, but purely because B has run out of the resources it needs to promptly handle *new* incoming requests from A, all of which are queued behind the backlog created in step 2.
4. **A now experiences B as slow/unresponsive**, and if A has no protection of its own, the exact same pattern repeats one level up: A's resources start filling up waiting on B, and *A* becomes slow to whatever is calling *it*.

The failure that started as "C is slow" has, within a few hops, become "A is slow" — even though A never made a single call to C directly, and nothing about A's own code or infrastructure is actually broken. **This is resource-exhaustion propagating backward through a call chain, one hop at a time, and it's the concrete mechanism behind the phrase "cascading failure."**

### 10.3 Retry amplification — the same cascade, made worse

Layer §6's retries on top of the same scenario, without backoff/jitter discipline: if A retries failed/slow calls to B up to 3 times, and B *itself* retries failed/slow calls to C up to 3 times, then a single original request from a client can generate up to **9 actual attempts landing on C** (3 retries from A, each triggering up to 3 retries from B) — exactly when C is already struggling and least able to absorb *more* load. This is a precise, numeric illustration of §6.2's warning: retries, applied at multiple layers of a chain without coordination, don't just fail to help — they can actively multiply the load hitting the already-struggling root cause.

### 10.4 What actually breaks the cascade

Every mechanism taught earlier in this lecture is, from this angle, a specific defense against cascading failure: **timeouts** (§5) bound how long any one hop waits, limiting how much resource gets tied up per stuck request; **circuit breakers** (§7) stop a struggling caller from even attempting calls to a dependency it already knows is failing, preventing step 1–2 above from ever starting; **backpressure** (§9) lets B explicitly refuse new work once it's saturated, rather than silently accepting it and making step 2 worse; and **careful retry policy** (§6.4–§6.6) prevents the specific multiplication in §10.3. No single one of these is sufficient alone — a well-built distributed system layers several of them together, specifically because cascading failure has multiple distinct mechanisms (resource exhaustion, retry amplification) that each need their own defense.

---

## 11. Partial Failure — The Major Focus

### 11.1 Why "the system is up" is the wrong question

Here's the claim this section exists to make concrete, with real numbers: suppose a service runs 20 backend instances. At any given moment, 19 are healthy and 1 has just crashed. Is "the system" up or down?

- From the perspective of the ~5% of requests that happened to be routed to the crashed instance before health checking caught it (Lecture 6 §6's detection isn't instantaneous): **down.**
- From the perspective of the ~95% of requests routed to one of the 19 healthy instances: **up**, and they likely never notice anything happened at all.
- From the perspective of an operator looking at an aggregate dashboard: probably a small, brief blip in an error-rate graph — arguably "basically fine."

**All three of these are correct descriptions, of the same moment, and they don't agree — because "up or down" was never the right shape of question to ask about a distributed system in the first place.** A single machine genuinely has something close to a binary state (running or crashed). A distributed system, made of many independently-failing parts (§3), does not — its "health" is a *continuous*, *multi-dimensional* quantity (what fraction of requests succeed, split by which instance/region/feature/tenant they touched), not a single bit.

### 11.2 Multiple, independent dimensions of "health"

Real systems are healthy or unhealthy along several genuinely separate axes simultaneously, and a failure in one doesn't imply failure in the others:

- **Per-destination**: some backend instances in a cluster healthy, others not (exactly §11.1's example, and Lecture 4 §13.6/Lecture 6 §6.5's territory).
- **Per-feature**: a specific downstream dependency (say, a recommendations service) is down, but the features that don't depend on it (say, checkout) work completely normally — the *product* is partially degraded, not down, and treating it as "the system is down" would be a significant overstatement of actual user impact.
- **Per-region**: a failure confined to one geographic deployment, while every other region continues serving normally.
- **Per-tenant**: in a multi-tenant system, an issue affecting one customer's data/configuration while every other tenant is completely unaffected.

A mature operational mindset asks "**what fraction of what, is failing, along which of these dimensions, and how badly**" — not "is it up." This reframing directly explains why production monitoring is built around continuous metrics (error *rate*, latency *percentiles*, per-dimension breakdowns) rather than a single boolean "up" signal — the boolean literally cannot represent the real state of the system, at any meaningful level of detail, most of the time.

### 11.3 Blast radius

**Blast radius** is the useful, concrete way to reason about partial failure: given that *some* failure has occurred, how much of the system/traffic/users does it actually affect? A well-architected system deliberately works to keep blast radius small — per-instance health checking (Lecture 6) confines a single crashed instance's blast radius to roughly `1/N` of that cluster's traffic, briefly, rather than 100% of it; the layered proxy architecture (Lecture 4 §9) confines a regional failure to that region rather than globally; per-tenant isolation confines one customer's issue to that customer. Every architectural pattern in this entire series that involves *multiplicity* — many destinations, many proxy instances, many regions — is, from this angle, fundamentally a blast-radius-limiting strategy: turning what would otherwise be one single point of total failure into many independent points of small, partial, contained failure.

### 11.4 Why partial failure is fundamentally, structurally unavoidable

This is worth stating plainly, tying directly back to §3: no single machine or process in a distributed system can instantaneously observe the true, complete state of every other machine — each node only ever has its own local, and possibly already-stale, view (a health check result from moments ago; a load-balancer's last-known destination list). This isn't a solvable engineering gap that better tooling eventually eliminates — it's a structural consequence of physically separate machines, connected by a network with real, nonzero latency (Lecture 2 §9), each doing its own independent thing. **"Is the system up" presumes a single, instantaneously-knowable global truth that a distributed system, by its very nature, does not have** — which is precisely why "things fail independently" (§3) and "partial failure is the normal condition, not the exception" are really the same insight, stated at the beginning and the end of this lecture.

---

## 12. Common Misconceptions

- **"A working system means nothing is currently failing."** §11 directly refutes this — real, healthy-looking production systems have small, ongoing, partial failures essentially all the time; the goal is containing and tolerating them, not eliminating them entirely.
- **"Retries are a strictly positive safety net — more retrying is always safer."** §6.2–§6.3 show retries can actively worsen an overload condition and synchronize into a self-sustaining storm.
- **"A timeout at each hop is sufficient to bound total request latency."** §5.4 shows independent per-hop timeouts can compound to a worst case far worse than any single hop's configured value — deadline propagation exists specifically to fix this.
- **"Circuit breakers and health checks are redundant with each other."** §7.3 draws the real distinction — different actor (caller vs. router), different question (should I even try vs. which candidate should be chosen).
- **"If a process is technically running, it's healthy."** §8.1's liveness/readiness split shows a perfectly alive process can be entirely unready to serve traffic, and treating those as the same thing produces the wrong operational response either direction.
- **"Cascading failure is caused by one big bug."** §10.2–§10.3 show it's typically an emergent property of resource exhaustion and retry amplification propagating through a chain — no single hop needs to be "broken" in isolation for the whole chain to degrade.

---

## 13. Production Perspective: 10 → 10,000 → 1,000,000 → 100,000,000 Requests

**~10 requests, one instance of each service**: §3's principle is true but invisible — with so little concurrency and so few components, independent failures are rare enough events that ad hoc handling (a human noticing and restarting something) is often good enough in practice.

**~10,000 requests/sec, several instances per service**: timeouts (§5) and basic retries (§6) become necessary just to avoid individual slow/failed calls degrading user-visible latency; this is roughly the scale where a genuinely slow dependency (not down, just slow) starts being distinguishable, operationally, from an outright failure, and needs to be handled differently (§4's table).

**~1,000,000 requests/sec, many services in a real dependency chain**: cascading failure (§10) stops being a theoretical concern — with enough hops and enough concurrency, resource-exhaustion propagation happens fast and visibly, and circuit breakers (§7) plus disciplined backpressure (§9) move from "good practice" to close to mandatory for chain stability. Correlated failures (§4.3, shared dependencies) become a real, explicit item in capacity/reliability planning rather than an afterthought.

**~100,000,000 requests/sec, many regions, many tenants, deep service graphs**: §11's multi-dimensional partial-failure framing isn't optional philosophy at this scale — it's literally how the system's health is monitored and reasoned about, because a single "up/down" signal genuinely cannot represent what's happening across that many independent regions/tenants/instances at once. Blast-radius minimization (§11.3) becomes an explicit, deliberate design goal for new architecture decisions, not an incidental side effect of having multiple instances.

---

## 14. Performance Implications

- **Set timeouts deliberately at every hop, and consider deadline propagation for deep call chains** (§5) — bounding worst-case latency is a design decision, not something that happens automatically.
- **Never retry blindly — respect idempotency, use backoff and jitter, and cap total attempts** (§6) — an undisciplined retry policy can be actively worse than no retries at all under real overload.
- **Use circuit breakers for dependencies you call directly and repeatedly** (§7) — failing fast protects both your own resources and the struggling dependency's ability to recover.
- **Separate liveness from readiness explicitly in health-check design** (§8.1) — conflating them produces operationally wrong responses (unnecessary restarts, or leaving dead processes running).
- **Design for small blast radius from the start** (§11.3) — multiplicity (many instances, many regions) is a deliberate failure-containment strategy, not just a capacity one.
- Deep formal distributed-systems theory (consensus algorithms, formal proofs about failure models) is **not** where your effort belongs yet — the practical, mechanism-level understanding in this lecture is the right depth for working with (and eventually contributing to) production infrastructure like YARP.

---

## 15. YARP Connection — Concrete Scenarios

### 15.1 Scenario: a destination becomes slow (not down)

A specific backend instance behind YARP starts responding slowly — connections are fine (Lecture 2 §10.4), but responses take far longer than normal. Without a request timeout, YARP would wait indefinitely, tying up its own thread and pooled-connection resources (Lecture 7 §5.4, §6.3) for every request unlucky enough to land there — directly risking §10.2's cascading pattern, with YARP itself as the component whose resources start filling up. **The correct behavior**: YARP applies its own request timeout (§5.2) to the backend call, independent of whatever timeout the original client used, and returns `504 Gateway Timeout` (Lecture 4 §13.2) once it's exceeded — bounding the damage to "this request fails a bit late" rather than "YARP's own capacity slowly degrades because too many requests are stuck waiting on one slow destination."

### 15.2 Scenario: a destination becomes unhealthy

Health checking (Lecture 6 §6, §8 of this lecture) detects the failure — via active probing, passive failure observation, or both — and marks the destination unhealthy. **The correct behavior**: load balancing (Lecture 6 §5) simply stops selecting it, per Lecture 5 §9.4 and Lecture 6 §14.5's "filter to healthy, then balance" layering — meaning this specific destination's failure, on its own, produces §11.3's small blast radius: some fraction of requests briefly affected during detection, the rest routed to the remaining healthy destinations without disruption. This is, concretely, §11.1's "up for 95%, down for 5%, briefly" scenario, made real.

### 15.3 Scenario: whether to retry

A request to one destination fails. **The correct behavior depends entirely on the request's method** (Lecture 1 §4.4, §6.2 of this lecture): a `GET` failing is generally safe to retry against a *different* healthy destination in the same cluster — the client is very unlikely to notice anything happened. A `POST` failing is a genuinely harder case — retrying blindly risks the double-execution problem from §6.2 unless the request carries an idempotency key or the specific failure mode (e.g., connection refused before any bytes were sent, Lecture 2 §10.5) gives strong evidence the backend never actually processed it. This is exactly why a reverse proxy's retry policy has to be method-aware, not a blanket "retry on any failure" rule.

### 15.4 Scenario: YARP itself becomes overloaded

Per §4.2, YARP is not exempt from failure — under enough concurrent load, YARP's own resources (Lecture 7 §6.3's thread pool, §5.3's connection pools) can become the bottleneck, independent of backend health entirely. **The correct behavior**: backpressure and self-protective limits (Lecture 4 §13.4, Lecture 7 §7.5) — rejecting excess requests promptly (a fast, cheap response) rather than accepting them and slowly degrading into the exact cascading pattern §10.2 describes, with YARP now playing the role of the overwhelmed "Service B" propagating trouble both upstream (to clients) and, if unchecked, downstream (retried/redirected load hitting backends even harder).

### 15.5 The synthesis — YARP as an active participant in blast-radius containment

Pulling §15.1–§15.4 together: **YARP is not a passive pipe that either works or doesn't — it is an active participant in exactly the resilience mechanisms this entire lecture taught, running continuously, on every request.** Its timeout handling, health-check-informed routing, retry policy, and self-protective backpressure are collectively *why* a single backend instance crashing, or going slow, typically shows up as a brief, small, contained blip rather than a full outage. This is the concrete, mechanical answer to §11.3's blast-radius question, specifically for the reverse-proxy layer: a well-configured YARP instance is one of the main reasons a distributed system's inevitable partial failures (§11.4) stay partial, instead of cascading (§10) into something much larger.

---

## 16. What I Don't Need to Know Yet

- Formal distributed-systems failure models (crash-stop vs. crash-recovery vs. Byzantine failure models) — recognize that formal theory exists here; the practical, mechanism-level treatment in this lecture is the right depth for this series.
- Consensus algorithms (Raft, Paxos) — relevant to systems that need strict agreement across nodes despite failures; not required for understanding a reverse proxy's own resilience mechanisms.
- Specific circuit-breaker library implementations (e.g., Polly in .NET) — recognize that mature, off-the-shelf implementations of §7's pattern exist; the conceptual state machine taught here is what matters for reading and reasoning about them.
- Chaos engineering practices (deliberately injecting failures in production to test resilience) — a valuable, real practice built directly on this lecture's concepts, but a distinct operational discipline, not a prerequisite concept.
- Distributed tracing across a multi-service call chain (correlating one logical request across every hop it touched) — directly relevant to *observing* the cascading-failure scenarios in this lecture, and a strong candidate for a future, dedicated lecture, but not required to understand the failure mechanisms themselves.

---

## 17. Knowledge Check

1. Using §3 and §4.3, explain why a database outage is a fundamentally different kind of risk than a single backend instance crashing, even though both are technically "failures."
2. A client-facing operation calls Service A, which calls Service B, which calls Service C. Each service independently applies its own 4-second timeout to its downstream call. Using §5.4, calculate the worst-case total latency the original client could experience, and explain how deadline propagation would change that number.
3. Using §6.2–§6.5, explain why "retry three times with a fixed 1-second delay" is a worse policy than "retry up to three times with exponential backoff and jitter" — name the two distinct failure modes the better policy avoids.
4. Using §7.3, explain a scenario where a circuit breaker would provide protection that a load balancer's health check alone would not.
5. A process is running, accepting TCP connections, and responding to liveness checks — but every request it handles is failing because a database it depends on is unreachable. Using §8.1, explain whether this is a liveness or readiness problem, and what the wrong response would look like if you got that classification backwards.
6. Using §11.1's 20-instance example and §11.3, explain why "5% of requests failed for 30 seconds" is a more useful incident description than "the system was down," and what specific engineering decisions (elsewhere in this series) are responsible for that 5% figure being 5% and not 100%.

---

## 18. Practical Exercise

Build a small local system that demonstrates a cascading failure directly, then fix it with a circuit breaker — this is the single most convincing way to actually *feel* §10's mechanism rather than just read about it.

### Step 1 — Three services in a chain, C deliberately made slow

```csharp
// ServiceC/Program.cs — the root cause: artificially slow
var builder = WebApplication.CreateBuilder(args);
var app = builder.Build();
app.MapGet("/work", async () =>
{
    await Task.Delay(4000); // simulate C being badly overloaded/slow
    return Results.Ok("C done");
});
app.Run("http://localhost:7003");
```

```csharp
// ServiceB/Program.cs — calls C, WITHOUT any timeout or circuit breaker (yet)
var builder = WebApplication.CreateBuilder(args);
builder.Services.AddHttpClient("C", c => c.BaseAddress = new Uri("http://localhost:7003"));
var app = builder.Build();
app.MapGet("/work", async (IHttpClientFactory factory) =>
{
    var client = factory.CreateClient("C");
    var response = await client.GetAsync("/work"); // no timeout — inherits whatever C does
    return Results.Ok("B done, via C");
});
app.Run("http://localhost:7002");
```

```csharp
// ServiceA/Program.cs — calls B
var builder = WebApplication.CreateBuilder(args);
builder.Services.AddHttpClient("B", c => c.BaseAddress = new Uri("http://localhost:7002"));
var app = builder.Build();
app.MapGet("/work", async (IHttpClientFactory factory) =>
{
    var client = factory.CreateClient("B");
    var response = await client.GetAsync("/work");
    return Results.Ok("A done, via B, via C");
});
app.Run("http://localhost:7001");
```

### Step 2 — Observe the cascade under concurrent load

Run all three, then fire 50 concurrent requests at A:
```csharp
var client = new HttpClient();
var sw = System.Diagnostics.Stopwatch.StartNew();
var tasks = Enumerable.Range(0, 50).Select(_ => client.GetAsync("http://localhost:7001/work"));
await Task.WhenAll(tasks);
Console.WriteLine($"All 50 done in {sw.ElapsedMilliseconds}ms");
```
Watch how long this takes, and — if you have a way to observe it (Task Manager/Activity Monitor, or simple console logging of concurrent-request counts in A and B) — notice that A and B are both now effectively "slow," purely because of C, exactly as §10.2 predicted, even though neither A nor B's own code has any actual defect.

### Step 3 — Add a timeout to B's call to C

```csharp
var response = await client.GetAsync("/work", new CancellationTokenSource(TimeSpan.FromSeconds(1)).Token);
```
Re-run the same 50-concurrent-request test. B now fails fast against C (after 1s instead of 4s) — better, but notice A is *still* affected, because B is still spending real time (1s per request) failing, and that's still eating into B's own capacity to serve A promptly under 50 concurrent requests.

### Step 4 — Add a simple circuit breaker in B

```csharp
// crude, illustrative circuit breaker — not production code
int consecutiveFailures = 0;
DateTime? openedAt = null;
var failureThreshold = 5;
var cooldown = TimeSpan.FromSeconds(10);

app.MapGet("/work", async (IHttpClientFactory factory) =>
{
    if (openedAt is not null && DateTime.UtcNow - openedAt < cooldown)
        return Results.StatusCode(503); // OPEN: fail fast, don't even call C

    var client = factory.CreateClient("C");
    try
    {
        var response = await client.GetAsync("/work", new CancellationTokenSource(TimeSpan.FromSeconds(1)).Token);
        consecutiveFailures = 0;
        openedAt = null; // success closes the circuit again
        return Results.Ok("B done, via C");
    }
    catch
    {
        consecutiveFailures++;
        if (consecutiveFailures >= failureThreshold) openedAt = DateTime.UtcNow; // TRIP to open
        return Results.StatusCode(503);
    }
});
```
Re-run the 50-concurrent-request test one more time. After the first handful of failures trip the breaker, subsequent requests to B should fail **instantly** (no 1-second wait, no call to C attempted at all) — confirming §7.2's key mechanical distinction from a plain timeout, and directly protecting both B's own capacity to serve A promptly, and C's ability to recover without continued incoming load.

---

## 19. "Ready to Move On" Criteria

Before starting the next lecture, you should be able to explain — out loud, in your own words:

- [ ] Why "things fail independently" is the foundational assumption behind every mechanism in this lecture, with your own concrete example.
- [ ] The specific, different symptom and correct response for at least five of the nine failure types in §4's table.
- [ ] The difference between a timeout and a deadline, and why naive per-hop timeouts can compound across a call chain.
- [ ] Why retries can help and can also actively worsen a failure, and how exponential backoff with jitter specifically prevents a retry storm.
- [ ] The mechanical difference between a circuit breaker and a health check, even though both stop traffic to a failing destination.
- [ ] The difference between liveness and readiness, and a scenario where confusing them produces the wrong operational response.
- [ ] How resource exhaustion propagates backward through a service chain to produce a cascading failure, with a concrete step-by-step trace.
- [ ] Why "is the system up" is not a meaningful question in a real distributed system, using at least two distinct dimensions of partial health from §11.2.
- [ ] How YARP's timeout handling, health-check-informed routing, method-aware retry behavior, and self-protective backpressure together keep a backend failure's blast radius small rather than letting it cascade.

If these feel solid, you've now covered failure and resilience as a systems-level discipline — a natural and deliberately-deferred-until-now complement to the architecture, routing, and load-balancing lectures earlier in this series, and genuinely close to the last major conceptual pillar before YARP's source code should read as an implementation of ideas you already understand, rather than a source of new ones.
