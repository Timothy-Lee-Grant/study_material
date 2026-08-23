# Lecture 6: Load Balancing and Traffic Distribution

Series: YARP Learning Series
Builds on: [Lecture 4 §6.2, §7, §15](004-reverse_proxies_and_api_gateways.md) (load balancing as an optional capability, destination selection as a stage), [Lecture 5 §6, §9.4, §14](005-routing_and_request_matching.md) (routing picks a *cluster*; this lecture is entirely about what happens *after* that — picking one *destination* within it).
Prepares you for: reading YARP's `ILoadBalancingPolicy` implementations, `DestinationHealthState`, and the health-checking subsystem, and reasoning correctly about capacity, traffic distribution, and failure at the destination-selection layer.

---

## 1. Learning Objectives

By the end of this lecture you should be able to:

1. Explain, concretely, why a single server stops being sufficient, in terms of both capacity and reliability.
2. Compare round robin, random, least-requests, and weighted load-balancing algorithms, and pick the right one for a stated scenario with a justified trade-off, not a guess.
3. Explain the difference between active and passive health checking, and why a real system typically wants both.
4. Explain what breaks when a load balancer treats heterogeneous servers as identical, and how weighting fixes it.
5. Explain uneven traffic, bursts, hot spots, and connection imbalance as *distinct* problems, each with different causes and different mitigations.
6. Explain why load balancing gets structurally harder — not just "harder in degree" — once you have many load balancer instances instead of one.
7. Place YARP's cluster/destination model precisely within this lecture's vocabulary, and recognize its load-balancing policy architecture on sight.
8. Implement a small, working round-robin and least-connections load balancer in C# against real local servers.

---

## 2. Prerequisite Concepts

Lecture 5 §6 already gave you the exact seam this lecture picks up from: a **route** points to exactly one **cluster**; a **cluster** contains many **destinations**. Lecture 5 §9.4 was explicit that routing itself never fails when a destination disappears — that's a lower-layer concern. This lecture *is* that lower layer: **given a cluster with several currently-known destinations, which one, specifically, handles this particular request?** Everything here assumes routing (Lecture 5) has already run and already committed to a cluster — load balancing never reconsiders that choice, it only chooses *within* it.

---

## 3. Core Mental Model

```
   Client
     │
     ▼
   Server
```
versus
```
   Client
     │
     ▼
  Load Balancer
     │
     ├──────► Server A
     ├──────► Server B
     └──────► Server C
```

The one sentence for this entire lecture: **load balancing is the ongoing, repeated decision of "which of these several currently-usable servers should handle this one request," made fresh (or at least reconsidered) for every request, using a policy that tries to keep total capacity well-used and no single server overwhelmed, while actively excluding servers that aren't currently usable at all.**

---

## 4. The Problem — Why One Server Isn't Enough

### 4.1 Capacity

A single server has a hard ceiling on how much work it can do concurrently — CPU cores, memory, thread pool size (Lecture 3 §9.3), open connection limits (Lecture 2 §12). Once incoming demand exceeds that ceiling, requests don't get *slower* gracefully forever — they queue, then time out, then start failing outright. Adding a second, third, and fourth server, and *distributing* load across all of them, raises the effective ceiling roughly in proportion to how many servers you add (with real-world caveats covered in §9).

### 4.2 Reliability

Even a perfectly-sized single server is a **single point of failure** — if it crashes, gets redeployed, or its host machine dies, every client is affected until it comes back. With multiple servers behind a load balancer, one instance failing (Lecture 4 §13.1, §13.6) means the *others* keep serving traffic, and the failure is partially or fully invisible to clients — this is a direct, concrete instance of Lecture 4 §13.6's partial-failure resilience, now examined specifically from the load-balancing angle.

### 4.3 Both problems, solved by the same mechanism

It's worth noticing explicitly: capacity and reliability are *different* problems (one is about "not enough total power," the other about "any single piece can vanish"), but a load balancer distributing traffic across multiple servers addresses both simultaneously, with the same underlying mechanism — this dual payoff is exactly why "just add more servers behind a load balancer" is such a foundational, recurring pattern in production infrastructure, rather than two separate solutions bolted together.

```
                    ┌─────────────────┐
   Client  ───────► │  Load Balancer    │
                    └─────────────────┘
                       │      │      │
                       ▼      ▼      ▼
                  Server A  Server B  Server C
                  (if A crashes, B and C keep the
                   service running — clients notice
                   nothing more than momentarily
                   reduced total capacity, not an outage)
```

---

## 5. Algorithms

Every algorithm below answers the same question — "which destination gets this request?" — using different information and different assumptions. None is universally "best"; each is a different trade-off, and picking one is a design decision, not a default to leave unexamined.

### 5.1 Round robin

**Idea**: cycle through destinations in a fixed order, one after another, wrapping back to the start.

```csharp
class RoundRobinBalancer
{
    private readonly List<string> _destinations;
    private int _index = -1;

    public RoundRobinBalancer(List<string> destinations) => _destinations = destinations;

    public string Next()
    {
        var i = Interlocked.Increment(ref _index);
        return _destinations[i % _destinations.Count];
    }
}
```

```
requests:  1    2    3    4    5    6
           │    │    │    │    │    │
           ▼    ▼    ▼    ▼    ▼    ▼
           A    B    C    A    B    C
```

**Trade-off**: extremely simple, requires no ongoing state about *how busy* each server actually is, and guarantees a genuinely even *count* of requests per destination over time. Its blind spot is exactly that last clause — it balances **request count**, not **actual load**. If one request takes 5ms and the next takes 5 seconds, round robin has no way to know or care; it will happily send the *next* request to whichever server it's currently that busy server's "turn" to receive, even if that server is still working through a slow request from moments ago.

### 5.2 Random

**Idea**: pick a destination uniformly at random for each request.

```csharp
class RandomBalancer
{
    private readonly List<string> _destinations;
    private readonly Random _random = new();

    public RandomBalancer(List<string> destinations) => _destinations = destinations;

    public string Next() => _destinations[_random.Next(_destinations.Count)];
}
```

**Trade-off**: even simpler than round robin, and — perhaps counter-intuitively — statistically converges to roughly the same even distribution as round robin *over a large number of requests*, without needing any shared counter state at all (relevant once you have *many* load balancer instances each making decisions independently, which round robin's shared `_index` doesn't naturally extend to — see §9). Its weakness: over any *small* number of requests, randomness can produce noticeably uneven short-term bursts to one destination purely by chance, in a way round robin's strict cycling never would.

### 5.3 Least requests (a.k.a. least connections)

**Idea**: track how many requests are *currently in flight* to each destination, and send the next request to whichever destination currently has the fewest.

```csharp
class LeastRequestsBalancer
{
    private readonly Dictionary<string, int> _inFlight;

    public LeastRequestsBalancer(List<string> destinations) =>
        _inFlight = destinations.ToDictionary(d => d, _ => 0);

    public string Start()
    {
        lock (_inFlight)
        {
            var chosen = _inFlight.MinBy(kv => kv.Value).Key;
            _inFlight[chosen]++;
            return chosen;
        }
    }

    public void Finish(string destination)
    {
        lock (_inFlight)
        {
            _inFlight[destination]--;
        }
    }
}
```

**Trade-off**: this directly fixes round robin's blind spot from §5.1 — it's reacting to *actual current load*, not just historical turn-taking, so a destination stuck processing several slow requests naturally receives fewer *new* ones until it catches up. The cost: it requires shared, continuously-updated state (`_inFlight`, incremented on request start and decremented on completion, exactly matching the request lifecycle from Lecture 3's `HttpContext`), which is more bookkeeping than round robin/random need, and — same caveat as round robin — that state is local to *one* load balancer instance unless something synchronizes it across many (§9).

### 5.4 Weighted approaches

**Idea**: assign each destination a weight reflecting its relative capacity or desired share of traffic, and bias selection proportionally.

```csharp
class WeightedRandomBalancer
{
    private readonly List<(string Destination, int Weight)> _destinations;
    private readonly int _totalWeight;
    private readonly Random _random = new();

    public WeightedRandomBalancer(List<(string, int)> destinations)
    {
        _destinations = destinations;
        _totalWeight = destinations.Sum(d => d.Item2);
    }

    public string Next()
    {
        var roll = _random.Next(_totalWeight);
        var cumulative = 0;
        foreach (var (destination, weight) in _destinations)
        {
            cumulative += weight;
            if (roll < cumulative) return destination;
        }
        return _destinations[^1].Destination; // unreachable in practice, satisfies the compiler
    }
}
```

```
Weights:  A=1   B=1   C=4          (C gets ~4x the traffic of A or B)

  roll 0..5:   0│1│2│3│4│5
                A  B  C  C  C  C
```

**Trade-off**: this isn't a competing algorithm to round robin/random/least-requests so much as a *modifier* applied on top of one — "round robin, but visit the weight-4 destination four times as often" or "random, but biased by weight" are both coherent, common combinations. Weighting is what makes heterogeneous capacity (§7) and gradual rollouts (send 5% of traffic to a new version) expressible at all — none of §5.1–§5.3 as described has any concept of "this destination deserves more traffic than that one," and weighting is precisely the mechanism that adds it.

### 5.5 Choosing among them — no universal answer

| Algorithm | Reacts to real-time load? | Needs shared state? | Good fit when |
|---|---|---|---|
| Round robin | No | Minimal (a counter) | Requests are roughly uniform in cost, destinations are roughly equal capacity |
| Random | No | None | Many independent balancer instances, simplicity valued over precision |
| Least requests | Yes | Yes (in-flight counts) | Request costs vary significantly, want to actively avoid piling onto a slow destination |
| Weighted (any base) | Depends on base | Depends on base | Destinations have unequal capacity (§7), or you want deliberate traffic-share control (canary rollouts) |

---

## 6. Health — Why a Load Balancer Must Know What's Actually Usable

### 6.1 The problem without health awareness

Every algorithm in §5 assumes every destination in its list is currently able to serve traffic. Without health awareness, a load balancer will cheerfully keep sending some fraction of traffic to a destination that's crashed, hanging (Lecture 2 §10.4), or mid-deployment-restart — meaning some fraction of *all* client requests fail, continuously, until someone notices and manually intervenes. This directly undermines §4.2's reliability argument: multiple servers only protect you from one failing *if the load balancer actually stops sending it traffic once it has*.

### 6.2 Active health checks

**Idea**: the load balancer proactively, on its own schedule, sends dedicated probe requests to each destination (e.g., `GET /health` every 10 seconds) *independent of real client traffic*, and marks a destination unhealthy if enough probes fail or time out.

```
  Load Balancer                          Destination
       │──── GET /health (every 10s) ─────────►│
       │<─────────── 200 OK ────────────────────│    healthy, keep routing to it
       
       │──── GET /health ─────────────────────►│
       │              (timeout)                  │    mark UNHEALTHY, stop routing
       │──── GET /health ─────────────────────►│      to it until it recovers
       │              (timeout)                  │
```

**Trade-off**: catches a failing destination even during periods of *low or zero* real traffic to it (important — without active checks, an already-unhealthy destination that simply isn't currently receiving requests would look indistinguishable from a healthy, idle one). Costs: extra request volume (usually trivial), and a detection delay bounded by the probe interval — a destination that just failed won't be marked unhealthy until the *next* scheduled probe notices.

### 6.3 Passive health checks

**Idea**: instead of (or in addition to) dedicated probes, observe the outcomes of *real* client requests as they naturally flow through — if requests to a given destination start failing or timing out at an elevated rate, mark it unhealthy based on that observed pattern, without any separate probe traffic at all.

**Trade-off**: zero extra traffic overhead, and reacts using the exact same conditions real clients are experiencing (no risk of a health-check endpoint behaving differently from the actual request path it's meant to represent). Cost: by definition, it needs *some* real requests to actually fail first before it can react — meaning at least a few real clients experience the failure before passive checking responds, whereas active checking (§6.2) can potentially catch the problem with zero real client impact if the probe interval is short enough.

### 6.4 Why real systems commonly use both together

Active and passive checking cover each other's blind spots precisely: active checking catches failures during low-traffic periods and reacts independent of real request patterns; passive checking reacts using zero extra overhead and captures failure modes that might not manifest identically on a dedicated health-check endpoint versus real traffic patterns. Using both is not redundant — it's covering two genuinely different detection gaps.

### 6.5 Unhealthy destinations and recovery

Once marked unhealthy, a destination is excluded from the candidate set that §5's algorithms choose among — this is exactly the layering Lecture 5 §9.4 pointed at: health state filters the candidates *before* the load-balancing algorithm ever runs, so "least requests" or "round robin" are always operating only over the currently-healthy subset. Recovery mirrors detection: continued *successful* active probes (§6.2) typically move a destination back to healthy after some threshold (often deliberately more cautious than the failure threshold — recovering too eagerly risks flapping a genuinely still-unstable destination back into rotation prematurely). Some systems also implement a gradual "slow start" on recovery — sending a newly-recovered destination a small, ramping trickle of traffic rather than its full normal share immediately, precisely to avoid overwhelming a server that's still warming up (recall Lecture 2 §6.5's TCP slow-start — this is the same underlying instinct applied at the application/load-balancing layer instead of the transport layer).

```
   HEALTHY ──[active probes fail / passive failures observed]──► UNHEALTHY
      ▲                                                                │
      │                                                                │
      └──────[sustained successful probes, often SLOWER to trust]──────┘
```

---

## 7. Capacity — Heterogeneous Servers

### 7.1 The problem

```
Server A = 2 CPUs        Server B = 16 CPUs
```

Any of §5.1–§5.3's *unweighted* algorithms treat A and B as interchangeable — round robin sends them equal request counts, least-requests sends them equal in-flight counts. But A has one-eighth of B's compute capacity — an equal *count* of requests can mean radically unequal *actual load*, especially if the requests are at all CPU-intensive. The practical outcome without weighting: server A becomes the bottleneck (queuing, slowing down, potentially failing health checks under load, §6) long before B is meaningfully utilized at all — the *aggregate* capacity gain from having two servers (§4.1) is squandered because the weaker one is artificially treated as an equal.

### 7.2 The fix — weighting proportional to real capacity

Applying §5.4's weighted approach with weights reflecting actual capacity (e.g., weight 2 for A, weight 16 for B, or some normalized ratio) means each server receives a traffic *share* proportional to what it can actually handle, rather than an equal share regardless of capability. This is why weighting isn't just "one more algorithm option" — it's the specific mechanism that makes heterogeneous infrastructure viable at all under load balancing; without it, mixing server sizes actively works against you rather than helping.

### 7.3 A subtlety: static weight vs. real-time capacity

Static weights (set once, in configuration) capture *known, fixed* capacity differences well, but they don't automatically account for a server's *current* load from other sources (e.g., background jobs also running on it, or a temporary degradation) — this is exactly why least-requests-style dynamic reaction (§5.3) and static capacity weighting (§5.4/§7.2) solve genuinely different problems and are often combined (a "weighted least requests" policy) rather than treated as mutually exclusive choices.

---

## 8. Traffic Patterns

Each of these is a distinct phenomenon with a distinct cause — worth keeping conceptually separate rather than lumping together as "traffic problems."

- **Uneven traffic**: not every client, region, or time of day generates the same request volume — a load balancer that's perfectly correct in its algorithm can still observe wildly uneven *absolute* load across destinations simply because total incoming demand itself isn't uniform over time. This isn't a load-balancer bug; it's an accurate reflection of genuinely uneven real-world demand.
- **Bursts**: a sudden, sharp spike in request rate (a marketing campaign goes live, a client retries aggressively after a transient failure) — the load balancer's job during a burst is to keep distributing evenly across *currently healthy* destinations, but a burst large enough can overwhelm total capacity regardless of how evenly it's spread, which is where rate limiting (Lecture 4 §6.2) becomes the actual mitigating capability, not load balancing itself.
- **Hot spots**: a *specific* destination (or small subset) receiving disproportionate load relative to the rest — can be caused by session affinity (a later topic, deferred per §14) pinning too many clients to one destination, by a load-balancing algorithm blind spot (§5.1's round-robin-ignoring-actual-load problem), or by uneven request *cost* rather than count (some endpoints are simply more expensive, and if they happen to cluster onto fewer destinations by chance under round robin, that destination runs hotter than the others despite an equal request count).
- **Overloaded destinations**: the end state when the above go unmitigated — a destination whose actual load has exceeded its real capacity, typically manifesting as rising latency first, then outright failures/timeouts (Lecture 2 §10.4, Lecture 4 §13.2), and eventually tripping health checks (§6) and being excluded from rotation — at which point its load gets redistributed onto the *remaining* healthy destinations, which can itself trigger a cascade if the remaining capacity wasn't sufficient to begin with (a real, important failure mode — see §12).
- **Connection imbalance**: specific to protocols with persistent/reused connections (Lecture 2 §6.1, §8) — because a connection, once established to a specific destination, is often reused for multiple subsequent requests (especially under HTTP/2 multiplexing, Lecture 1 §7), a load-balancing decision made *once*, at connection-establishment time, can end up governing many requests' worth of traffic, potentially skewing distribution away from what a purely per-request algorithm would have produced, if connection lifetimes vary significantly across destinations.

---

## 9. Distributed Systems Implications — Why This Gets Structurally Harder at Scale

### 9.1 The core issue: state that used to be simple becomes shared and inconsistent

Every algorithm in §5 (except pure random) relies on some piece of state — round robin's counter, least-requests' in-flight tracking, health status (§6) — that's trivially consistent when there's exactly **one** load-balancer instance holding it in memory. The moment you need *multiple* load-balancer instances (because the load balancer itself needs to scale, exactly as Lecture 4 §12's "100,000,000 requests" tier described), that state either has to be:

- **kept fully local to each instance** (each load balancer makes decisions using only its own view) — simple, but now "least requests" only reflects requests *that instance* has sent, not the destination's true total in-flight count across *all* load-balancer instances combined, which can meaningfully undermine the algorithm's whole premise; or
- **synchronized across instances** — accurate, but now you've introduced a genuinely new distributed-systems problem (keeping shared state consistent across multiple machines, with all the latency/consistency trade-offs that implies) just to make load balancing work correctly.

```
   ONE load balancer:                      MANY load balancer instances:

   ┌─────────────┐                        ┌──────┐  ┌──────┐  ┌──────┐
   │ LB (1 copy of │                        │ LB #1  │  │ LB #2  │  │ LB #3  │
   │ all state)     │                        │(own view)│  │(own view)│  │(own view)│
   └─────────────┘                        └──────┘  └──────┘  └──────┘
          │                                     │           │           │
          ▼                                     └───────────┼───────────┘
     Server A/B/C                                            ▼
   (state is trivially                              Server A/B/C
    consistent — there's                    (each LB instance's "least requests"
    only one copy of it)                     count might now be WRONG relative to
                                              the destination's TRUE total load)
```

### 9.2 Thundering herd on recovery

If many load-balancer instances (or many clients) simultaneously detect a destination has recovered (§6.5) and all immediately resume sending it full-share traffic at once, that destination can be instantly overwhelmed by the *combined* weight of every independent decision-maker's traffic hitting it at the same moment — even though no single decision-maker did anything wrong in isolation. This is exactly why the "slow start on recovery" idea from §6.5 matters more, not less, at scale — a single load balancer easing a destination back in gently is a mild optimization; many independent load balancers *each* easing it back in gently is what prevents a coordinated pile-on that none of them individually intended.

### 9.3 Cascading overload

Following directly from §8's "overloaded destinations" point: when one destination is excluded from rotation, its share of traffic gets redistributed onto the remaining healthy ones. If the remaining destinations were already running close to their own capacity, this redistribution can push *them* over their limits too, causing them to also start failing health checks — which redistributes their load onto whatever's left, potentially cascading through an entire cluster in a short span. This is a genuinely distributed-systems-scale failure mode — it doesn't really exist (or matters far less) with only two or three destinations and modest load, but becomes a serious operational risk with many destinations under sustained high utilization, which is precisely the regime large-scale systems operate in.

### 9.4 What this means practically

None of §9.1–§9.3 mean per-instance load balancing is broken or wrong — they mean that, at scale, load-balancing correctness stops being a purely local, single-machine algorithm question and becomes a genuinely distributed-systems question, with the same fundamental tensions (consistency vs. latency vs. availability) that show up everywhere else in distributed systems design. Recognizing *that this shift happens*, and roughly *why*, is the right depth for this lecture — the specific advanced techniques used to address it (e.g., consistent hashing for stable distribution, gossip-based health state sharing) are deliberately deferred (§14).

---

## 10. Common Misconceptions

- **"Round robin guarantees even load."** §5.1 is explicit: it guarantees an even *count*, not even actual load — request cost variance breaks this assumption easily.
- **"A load balancer that isn't reacting to real-time load is broken."** Not necessarily — §5.5's comparison table shows this is a deliberate trade-off (simplicity/statelessness vs. responsiveness), not a defect; round robin and random are legitimate, common choices for the right scenarios.
- **"Passive health checking is strictly worse than active, since it needs real failures first."** §6.4 shows they solve different problems and are commonly combined, not ranked against each other.
- **"More servers always means proportionally more capacity."** §7.1 shows this only holds if capacity differences are accounted for (weighting) — otherwise the weakest server becomes a bottleneck well before the strongest is utilized.
- **"Load balancing is a solved, purely local algorithm problem."** §9 directly contradicts this at scale — it becomes a genuinely distributed-systems concern once many load-balancer instances are involved.
- **"An unhealthy destination recovering should immediately get its full normal traffic share back."** §6.5 and §9.2 show gradual reintroduction is often deliberately preferred, specifically to avoid re-overwhelming a destination that's still stabilizing, and to avoid a coordinated pile-on from many independent decision-makers.

---

## 11. Production Perspective: 10 → 10,000 → 1,000,000 → 100,000,000 Requests

**~10 requests, 2-3 servers**: round robin or even random is completely adequate — request cost variance and capacity differences rarely matter enough to notice, and a single load-balancer instance holding all its own state (§9.1) is trivially correct.

**~10,000 requests/sec, a handful of servers, possibly heterogeneous**: request cost variance (§5.1's blind spot) and capacity differences (§7) start to matter — this is roughly where teams move from "round robin because it's the default" to deliberately choosing least-requests and/or weighting based on observed behavior, and where both active and passive health checking (§6.4) become worth running together rather than picking just one.

**~1,000,000 requests/sec, many servers, likely multiple load-balancer instances**: §9.1's shared-state problem becomes real and unavoidable — a single load balancer instance can no longer handle this volume alone (Lecture 4 §12's own observation), so per-instance-local state (each load balancer's own view of "least requests") starts diverging from ground truth, and the organization has to make a deliberate choice about how much of that inconsistency is acceptable versus worth the cost of synchronizing state across instances.

**~100,000,000 requests/sec**: cascading overload (§9.3) is a genuine, planned-for operational risk, not a theoretical edge case — capacity planning explicitly has to account for "what happens if N% of destinations fail simultaneously, and can the survivors actually absorb that redistributed load without cascading further." Thundering-herd-on-recovery (§9.2) mitigations (gradual reintroduction, jittered/staggered health-check timing across independent load-balancer instances) move from "nice engineering hygiene" to "required to avoid a self-inflicted outage during ordinary recovery from a partial failure."

---

## 12. Failure Scenarios

- **All destinations become unhealthy simultaneously** (a bad deploy, a shared dependency like a database going down): the load balancer has no viable candidate — the correct behavior is the same `503 Service Unavailable` from Lecture 4 §13.1's family, explicitly distinct from `502`/`504`, because the proxy is saying "I have zero healthy destinations to even attempt," not "I tried one and it failed."
- **Health checks themselves are unreliable** (the health-check *path* is flaky or slow, independent of the actual service): can produce false-positive unhealthy markings, needlessly shrinking the healthy candidate set and concentrating load on fewer destinations (§8's overloaded-destination risk) even though nothing is actually wrong — a reminder that the health-check mechanism itself is part of the system's reliability surface, not a free, risk-free add-on.
- **A destination is healthy but slow** (distinct from unhealthy): §5.3's least-requests naturally de-prioritizes it without needing health checking to intervene at all — worth noticing this as a case where the *algorithm choice* itself (not health checking) is what protects the system.
- **Thundering herd on recovery** (§9.2): a recovered destination gets instantly overwhelmed by simultaneous full-share traffic from many independent decision-makers, potentially flapping it back to unhealthy immediately — the correct mitigation is gradual reintroduction, not immediate full trust.
- **Cascading overload** (§9.3): one destination's failure overloads the survivors, which then also fail, in a chain — correct mitigation requires capacity headroom (never running so close to full utilization that losing one destination guarantees overloading the rest) combined with the redistribution mechanics themselves being reasonably paced rather than instantaneous and total.

---

## 13. Performance Implications

- **Match the algorithm to actual request-cost variance** (§5.5) — round robin/random are cheap and sufficient when costs are roughly uniform; least-requests earns its extra bookkeeping cost specifically when they aren't.
- **Weight destinations by real capacity, not by count** (§7.2) — an unweighted mix of heterogeneous servers actively wastes the stronger servers' capacity while bottlenecking on the weaker ones.
- **Combine active and passive health checking** (§6.4) rather than picking one, to minimize both detection latency and unnecessary probe overhead.
- **Plan capacity headroom explicitly around destination-loss scenarios** (§9.3, §12) — the question "can the survivors absorb this destination's load" needs a deliberate answer before it's tested by a real failure, not discovered during one.
- **Prefer gradual reintroduction over instant full trust on recovery** (§6.5, §9.2) — this is a small implementation cost that prevents a meaningfully worse outcome (flapping, thundering herd) at scale.
- Deep distributed-consensus mechanisms for perfectly synchronized cross-instance load state, and advanced techniques like consistent hashing, are **not** where your effort belongs yet (§14) — recognizing that §9's problem exists, and roughly why, is the right depth for this series.

---

## 14. YARP Connection

### 14.1 Cluster and destination, precisely in this lecture's terms

Recall Lecture 5 §6: a **cluster** is the stable logical grouping; a **destination** is one specific, volatile backend address within it. This lecture fills in exactly what happens *inside* that cluster, every time a route (Lecture 5) has already selected it: the cluster's configured **load-balancing policy** (§5 of this lecture) chooses one destination from among the currently-**healthy** (§6) subset, optionally informed by **weights** (§7) if capacity differs across destinations.

### 14.2 YARP's load-balancing policies, mapped onto §5

Expect YARP's configuration to offer a `LoadBalancingPolicy` setting on each cluster, with built-in options mapping directly onto this lecture's algorithms: something equivalent to round robin (§5.1), random (§5.2), least-requests (§5.3, commonly the most broadly recommended default precisely because of the blind spot §5.1 has), and a power-of-two-choices-style variant (a refinement worth recognizing by name even though its internals are deferred, §16 — conceptually, it randomly samples a couple of candidates and picks the less-loaded of *those*, cheaper than tracking full global state while still reacting to load far better than pure random).

### 14.3 Health checking, mapped onto §6

Expect explicit, separate configuration sections for active health checks (probe path, interval, failure/success thresholds — directly configuring §6.2's mechanism) and passive health checks (thresholds derived from real observed request outcomes — directly configuring §6.3's mechanism) on each cluster, exactly matching §6.4's "use both" guidance as the natural default posture. Expect a destination's live health state to be tracked as part of the built, ready-to-use `DestinationState` model (Lecture 5 §13.2) — not the static `DestinationConfig` you author — precisely because health state changes constantly and independently of configuration (Lecture 5 §6's "destinations change constantly" point, now specifically about *health*, not just *existence*).

### 14.4 Weighting, mapped onto §7

Expect a per-destination weight field usable alongside the load-balancing policy, letting a cluster mixing heterogeneous backend capacity (§7.1's `2 CPU` vs `16 CPU` example) express that difference directly in configuration rather than requiring a custom policy.

### 14.5 The layering you should now expect to see clearly in the source

Following directly from Lecture 5 §9.4 and §6.5 of this lecture: expect the actual destination-selection code path to visibly perform **two distinct steps in order** — first, filter the cluster's destinations down to the currently-healthy subset; second, *only then* hand that filtered subset to the configured load-balancing policy to make the final pick. Seeing this two-step shape confirms directly, in real code, the "health state filters candidates *before* the algorithm runs" layering this lecture has been building toward — if you instead saw a load-balancing policy directly examining raw configuration destinations with no separate health-filtering step, that would be a sign you'd misunderstood the architecture, not a sign YARP works differently than taught here.

---

## 15. What I Don't Need to Know Yet

- Consistent hashing and other techniques for keeping load distribution stable as the destination set changes (relevant to session affinity and to minimizing cache-invalidation-style churn) — recognize the term; the mechanism is a natural next-level topic once you're customizing load-balancing behavior directly.
- The exact internals of power-of-two-choices or any other specific advanced algorithm beyond §14.2's conceptual sketch.
- Distributed state synchronization techniques for cross-instance load awareness (§9.1) — gossip protocols, shared external state stores — recognize this is a real, hard problem at scale; the specific solutions are their own deep topic.
- Session affinity (routing a given client consistently to the same destination) — deliberately deferred again here, same as Lecture 4 §16 and Lecture 5 §14 — it interacts with load balancing but is a distinct mechanism layered on top, better suited to its own focused treatment.
- Circuit breaker patterns and outlier detection algorithms beyond the basic active/passive health-check model taught here — a real, deeper topic in resilient system design, not required at this stage.

---

## 16. Knowledge Check

1. A cluster has two destinations: one handles requests that typically take 10ms, the other regularly handles requests that take 2 seconds (due to a slower dependent operation), but both receive requests in roughly equal proportion. Using §5.1 vs §5.3, explain why round robin could leave the slow-request destination effectively more loaded than the fast one, and how least-requests would behave differently.
2. Explain, using §6.2 vs §6.3, a specific scenario where only active health checking would catch a problem in time, and a separate scenario where only passive health checking would catch one that active checking would miss.
3. A cluster has three destinations with equal weight, but one runs on hardware with a quarter of the CPU capacity of the other two. Using §7, explain what will happen under sustained load if weighting is not configured, and how to fix it.
4. Using §9.1, explain concretely why "least requests" becomes less accurate (not just "harder to implement") once traffic is spread across multiple independent load-balancer instances, rather than one.
5. A destination that was marked unhealthy recovers, and every load-balancer instance in the fleet detects this within the same few seconds. Using §9.2, explain the risk of immediately resuming full traffic to it, and what mitigation addresses that risk specifically.
6. Using §14.5, explain why seeing "filter to healthy destinations first, then apply the load-balancing algorithm" as two separate steps in YARP's source code is exactly what this lecture predicted, rather than an implementation detail you'd need to discover from scratch.

---

## 17. Practical Exercise

Build a small, real load balancer in C# against three actual local servers — round robin first, then least-connections, so you can directly compare their behavior under uneven request costs.

### Step 1 — Three local "backend" servers with deliberately uneven cost

```bash
mkdir -p ~/lb-lecture-demo/backend && cd ~/lb-lecture-demo/backend
dotnet new web
```

```csharp
var builder = WebApplication.CreateBuilder(args);
var app = builder.Build();
var port = args.Length > 0 ? args[0] : "unknown";
var delayMs = args.Length > 1 ? int.Parse(args[1]) : 0;

app.MapGet("/work", async () =>
{
    await Task.Delay(delayMs); // simulate variable request cost
    return Results.Json(new { servedBy = port, delayMs });
});

app.Run($"http://localhost:{port}");
```

Run three instances with deliberately different simulated costs:
```bash
dotnet run -- 6001 50     # fast
dotnet run -- 6002 50     # fast
dotnet run -- 6003 800    # slow — simulates a genuinely more expensive backend
```

### Step 2 — A tiny console app implementing both balancers from §5.1 and §5.3

```csharp
// Program.cs
var destinations = new List<string> { "http://localhost:6001", "http://localhost:6002", "http://localhost:6003" };
var httpClient = new HttpClient();

async Task RunTrial(string label, Func<string> pickDestination, Action<string>? onStart = null, Action<string>? onFinish = null)
{
    Console.WriteLine($"\n--- {label} ---");
    var counts = destinations.ToDictionary(d => d, _ => 0);
    var tasks = new List<Task>();

    for (int i = 0; i < 30; i++)
    {
        var dest = pickDestination();
        counts[dest]++;
        onStart?.Invoke(dest);
        tasks.Add(Task.Run(async () =>
        {
            await httpClient.GetAsync($"{dest}/work");
            onFinish?.Invoke(dest);
        }));
        await Task.Delay(20); // stagger request starts slightly, like real traffic
    }

    await Task.WhenAll(tasks);
    foreach (var (dest, count) in counts)
        Console.WriteLine($"{dest}: {count} requests assigned");
}

// --- Round robin (Section 5.1) ---
int rrIndex = -1;
string RoundRobin() => destinations[Interlocked.Increment(ref rrIndex) % destinations.Count];
await RunTrial("Round Robin", RoundRobin);

// --- Least requests (Section 5.3) ---
var inFlight = destinations.ToDictionary(d => d, _ => 0);
string LeastRequests()
{
    lock (inFlight) { return inFlight.MinBy(kv => kv.Value).Key; }
}
void OnStart(string d) { lock (inFlight) { inFlight[d]++; } }
void OnFinish(string d) { lock (inFlight) { inFlight[d]--; } }
await RunTrial("Least Requests", LeastRequests, OnStart, OnFinish);
```

### Step 3 — Observe the difference §5.1 vs §5.3 predicted

Run it against your three backends (two fast, one deliberately slow). Round robin will assign an equal count (10/10/10) to all three destinations, *including* the slow one — meaning the slow destination accumulates a growing backlog of concurrent in-flight requests over the trial, since it can't keep up with the rate new work is being assigned to it. Least-requests should visibly assign fewer requests to the slow destination over the course of the trial, once its in-flight count starts staying elevated — confirming, with real numbers from your own run, exactly the blind spot and fix described in §5.1/§5.3 and worked through in Knowledge Check question 1.

### Step 4 (optional extension) — Add a crude health check

Add a loop that periodically checks `GET /work` against each destination with a short timeout, and excludes any destination that fails from `destinations` before either balancer picks from it — kill one backend process mid-run and observe both balancers correctly stop sending it traffic, directly reproducing §6's healthy-candidate-filtering behavior yourself.

---

## 18. "Ready to Move On" Criteria

Before starting the next lecture, you should be able to explain — out loud, in your own words:

- [ ] Why a single server is both a capacity ceiling and a reliability risk, and why load balancing addresses both with one mechanism.
- [ ] Round robin, random, least-requests, and weighted approaches — the mechanism of each, and a concrete scenario where each is the right (or wrong) choice.
- [ ] Why active and passive health checking catch different failure patterns, and why real systems commonly run both.
- [ ] What goes wrong when heterogeneous-capacity servers are load-balanced without weighting, and how weighting fixes it.
- [ ] The distinct causes of uneven traffic, bursts, hot spots, overloaded destinations, and connection imbalance — as separate phenomena, not one blurry "traffic problems" bucket.
- [ ] Why load balancing becomes a genuinely distributed-systems problem — not just "the same problem, more of it" — once multiple load-balancer instances are involved.
- [ ] The two-step "filter to healthy, then apply the algorithm" shape you should expect to see directly in YARP's destination-selection code.

If these feel solid, you're well-positioned for the next natural layer in this stack — session affinity and how it interacts with (and sometimes works against) everything taught in this lecture — which has now been deliberately deferred three lectures in a row and is a strong candidate for where this series goes next.
