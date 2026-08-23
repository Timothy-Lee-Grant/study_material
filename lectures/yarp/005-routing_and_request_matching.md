# Lecture 5: Routing and Request Matching

Series: YARP Learning Series
Builds on: [Lecture 3 §10](003-aspnetcore_request_processing_and_architecture.md) (ASP.NET Core's match/execute routing split), [Lecture 4 §7 and §15](004-reverse_proxies_and_api_gateways.md) (the route → cluster → destination chain, introduced but not yet gone deep).
Prepares you for: reading YARP's `RouteConfig`, `RouteMatch`, `ClusterConfig`, `DestinationConfig`, `IProxyConfigProvider`, and the machinery that turns configuration into live, efficiently-matchable routing behavior.

---

## 1. Learning Objectives

By the end of this lecture you should be able to:

1. Design a routing configuration from simple path-prefix rules up to combined path/host/method/header rules, and predict which rule matches a given request.
2. Explain route **precedence** — what happens when a request could satisfy more than one route — and why it must be a deterministic, predictable resolution rather than "whichever happens to run first."
3. Explain, at a conceptual level, how a routing table is represented internally so that matching is fast, not a linear scan through every rule on every request.
4. Explain the route → cluster → destination separation with enough precision to say exactly what data lives at each layer and why.
5. Explain what happens, mechanically, when routing configuration changes while the proxy is already serving live traffic.
6. Diagnose each of the four failure scenarios (no match, ambiguous match, invalid config, vanished destination) and state the *specific*, different behavior each one produces.
7. Recognize YARP's actual configuration types and provider abstractions on sight, and map them onto the concepts taught here.

---

## 2. Prerequisite Concepts

Lecture 3 §10.1 already gave you the key idea this lecture builds on: ASP.NET Core's routing is split into a **match phase** (decide which endpoint applies, without running it) and an **execute phase** (actually run it). Lecture 4 §7 already introduced route → cluster → destination as three deliberately separate concepts, changing at three different rates. This lecture stays entirely inside the *match phase* — we're going to slow down and look very closely at exactly how "which route applies" gets decided, represented, and kept fast, because that decision is the single most frequently-executed piece of logic in the entire proxy: it runs, without exception, on every request that arrives.

---

## 3. Core Mental Model

```
   Incoming request                     Routing Table                    Selected Route
  (method, path, host,        ──────►  (a set of rules, each      ──────►  (exactly one —
   headers)                              with a MATCH CONDITION               or a clear,
                                          and a TARGET cluster)                 predictable
                                                                                 failure)
```

The one sentence to hold onto: **routing is a function — `(request) → route or failure` — and everything in this lecture is about making that function correct (matches what you actually meant), unambiguous (never silently guesses between two equally-valid answers), and fast (doesn't become the bottleneck as the rule count and request volume both grow).**

---

## 4. Progressive Routing — From Simple to Real

### 4.1 The simplest possible case: path-prefix routing

```
/users   → Users Service
/orders  → Orders Service
/images  → Image Service
```

This is routing in its most stripped-down form: look at the request path, find which prefix it starts with, send it there. As a table:

| Path prefix | Target |
|---|---|
| `/users` | Users Service |
| `/orders` | Orders Service |
| `/images` | Image Service |

```
  GET /users/42        ──► matches "/users"  ──► Users Service
  GET /orders/8891      ──► matches "/orders" ──► Orders Service
  GET /images/logo.png  ──► matches "/images" ──► Image Service
  GET /checkout          ──► matches NOTHING    ──► ??? (§9.1 covers this)
```

Even at this trivial scale, notice something already: the match key is the path, but the actual rule is really "starts with `/users`," not "equals `/users`" — `/users/42` and `/users/42/orders` both need to match the `/users` rule. This "prefix, not exact match" behavior is usually expressed with an explicit wildcard rather than left implicit — see §4.5.

### 4.2 Adding host matching

Real systems often host multiple logical APIs behind the same proxy, distinguished by hostname rather than (or in addition to) path:

```
Host: users.contoso.com    → Users Service
Host: orders.contoso.com   → Orders Service
Host: api.contoso.com AND Path: /images/*  → Image Service
```

Host matching uses the `Host` header from the request (Lecture 1 §4.6) — recall from Lecture 1 §4.5 that the hostname is resolved via DNS *before* any HTTP bytes are sent, but the proxy still needs the `Host` header explicitly, because one IP address/port the proxy listens on can front many different hostnames simultaneously. This is the exact mechanism behind running many logically-separate APIs off a single proxy instance and a single listening port.

### 4.3 Adding HTTP method matching

```
Path: /v1/users/{id}, Method: GET     → Users Service (read path)
Path: /v1/users/{id}, Method: DELETE  → Users Admin Service (a DIFFERENT backend for destructive ops)
```

The same path pattern can route to entirely different destinations depending on the method — a common real pattern is routing mutating methods (`POST`/`PUT`/`DELETE`, recall Lecture 1 §4.4's safety/idempotency table) to a more tightly access-controlled or differently-scaled backend than read-only `GET` traffic.

### 4.4 Adding header matching

```
Path: /v1/users/{id}, Header: X-Api-Version = 2   → Users Service V2
Path: /v1/users/{id}, (no version header, or = 1) → Users Service V1
```

Header-based routing is how systems commonly implement API versioning, canary releases (route 5% of traffic carrying a specific header to a new backend version), or tenant-specific routing (route based on a `X-Tenant-Id` header) — all without changing the path structure clients use at all. This is a direct, practical example of Lecture 4 §6.2's "transformation/routing capability the proxy is well-positioned to provide" — the client doesn't need to know this distinction exists.

### 4.5 Wildcard patterns

Two distinct wildcard shapes show up constantly, and they mean genuinely different things:

- **Single-segment wildcard**: `/v1/users/{id}` — `{id}` matches exactly one path segment (`42`, `abc123`) and captures its value as a named route parameter, usable by the application (or, in YARP's case, by transforms).
- **Catch-all wildcard**: `/v1/users/{**catch-all}` — matches the fixed prefix `/v1/users/` plus *any remaining path*, however many segments deep (`/v1/users/42`, `/v1/users/42/orders/8`, `/v1/users/42/orders/8/items`). This is what actually implements the "prefix routing" behavior from §4.1 precisely, rather than leaving it implicit.

```
Pattern: /v1/users/{id}              Pattern: /v1/users/{**catch-all}

  /v1/users/42          ✓ matches       /v1/users/42                    ✓ matches
  /v1/users/42/orders   ✗ NO match      /v1/users/42/orders              ✓ matches
                                        /v1/users/42/orders/8/items       ✓ matches
```

Getting this distinction wrong is a common, real configuration mistake — using `{id}` when you meant a catch-all silently breaks routing for any deeper path under that prefix, with no error, just requests that don't match when you expected them to.

### 4.6 Route precedence — what happens when more than one rule could match

Suppose both of these are configured simultaneously:

```
Route A: Path = /v1/users/{**catch-all}         → General Users Service
Route B: Path = /v1/users/{id}, Method = DELETE → Users Admin Service
```

A `DELETE /v1/users/42` request satisfies *both* patterns. Which one wins? This cannot be left to chance — a router needs a deterministic **precedence** rule, and the standard, sensible approach is: **more specific rules win over more general ones.** "Specific" is usually measured by things like: fewer wildcard segments, more matching criteria specified (method + header beats path alone), and literal path segments outranking parameterized ones. Route B is more specific (it constrains both path shape *and* method) than Route A (path only, with a catch-all), so Route B should win for this particular request, while Route A continues to correctly handle every other method/path combination under `/v1/users/`.

```
  DELETE /v1/users/42
        │
        ├── satisfies Route A? YES (catch-all matches anything under /v1/users/)
        ├── satisfies Route B? YES (exact segment + method match)
        │
        ▼
  Precedence rule: Route B is MORE SPECIFIC → Route B wins
```

The critical engineering property here: **precedence must be computed the same way every time, independent of registration order, independent of which route "happened" to be checked first.** A router whose behavior depends on incidental ordering is a router that will eventually produce a confusing, hard-to-reproduce bug the moment someone adds a new route in a different position in a config file. (This doesn't mean order is irrelevant to the *config author* — many real systems do let you set an explicit priority/order value precisely so specificity ties can be broken deliberately — but the resolution itself must still be deterministic and documented, never accidental.)

### 4.7 Route conflicts — when specificity can't resolve it

```
Route C: Path = /v1/users/{id}, Header: X-Debug = true → Debug Service
Route D: Path = /v1/users/{id}, Method = GET            → Users Service
```

A `GET /v1/users/42` request with header `X-Debug: true` satisfies both, and neither is strictly more specific than the other by any obvious measure (one constrains on a header, the other on method) — this is a genuine **conflict**, not just an overlap resolvable by "more specific wins." A well-built router should detect this at *configuration load time* (§9.3 covers this) and either reject the configuration outright or apply an explicit, documented tie-breaking rule (like configured priority order) — what it must never do is silently pick one unpredictably per-request, or worse, per-restart.

---

## 5. How Routing Decisions Are Represented Internally

### 5.1 The naive approach, and why it doesn't scale

The simplest possible implementation: a flat list of rules, checked one by one, in order, first match wins.

```csharp
foreach (var route in allRoutes)   // O(N) — checked on EVERY request
{
    if (route.Matches(request))
        return route;
}
```

This works correctly for a handful of routes. It becomes a real performance problem exactly where §6 (Performance) below picks up: at a few thousand routes and meaningful request volume, doing up to N full comparisons *per request* is wasted, repeated work — because the set of routes doesn't change between one request and the next, yet this approach re-derives the answer from scratch every single time.

### 5.2 The better approach: pre-organize once, look up fast repeatedly

The fix follows a pattern you should recognize from Lecture 3 §5's registration-vs-pipeline split and Lecture 4 §7.1's "different rates of change" reasoning: **do the expensive organizing work once, when configuration loads (or changes), and make the per-request operation cheap.**

Concretely, real routers typically build something closer to a **tree keyed by literal path segments**, falling back to parameterized/wildcard branches only where needed:

```
                          root
                           │
                 ┌─────────┼─────────┐
                 ▼         ▼         ▼
              "users"   "orders"  "images"
                 │         │         │
            ┌────┴────┐    ▼         ▼
            ▼         ▼  {**catchall} {**catchall}
        {id} (GET)  {id} (DELETE)  → Orders Svc   → Image Svc
            │           │
            ▼           ▼
       Users Svc   Users Admin Svc
```

Matching a request becomes: walk the tree by literal path segments (fast — direct lookups, like a dictionary/hash lookup at each level, not a scan) until you either hit a literal dead end (fall back to a wildcard branch if one exists at that level) or reach a leaf, then apply any remaining method/header constraints at that leaf. This is conceptually similar to how a compiler's keyword lookup or a DNS resolver's hierarchical lookup works — turn "search through everything" into "follow a small, bounded number of direct steps."

**This is precisely what ASP.NET Core's own routing engine (Lecture 3 §10.1) already does** — it doesn't linearly scan every registered endpoint on every request; it builds an efficient internal matching structure once, when the app starts (or when endpoints change), and reuses it for every subsequent request. YARP doesn't reinvent this — it registers its routes as ordinary ASP.NET Core endpoints and lets that existing, already-optimized matching engine do the work, precedence rules included.

### 5.3 Precedence as a build-time computation, not a per-request one

Directly following from §5.2: the specificity comparison from §4.6 is also computed **once, when the routing structure is built**, not re-evaluated on every incoming request. Each route effectively gets an internal specificity/priority value baked in at build time, so at match time, if the walk in §5.2 surfaces multiple candidates, picking the winner is a cheap comparison of already-computed values — not a repeated, expensive re-derivation of "how specific is this route, again?" for every request.

---

## 6. Routing Architecture — Route, Cluster, Destination, Precisely

Lecture 4 §7 introduced this split and *why* it exists (different rates of change). Here's exactly *what data* lives at each layer, and how they reference each other:

```
┌───────────────────────────────┐
│  ROUTE                          │   changes: rarely (deliberate config edits)
│  - match conditions (§4)          │
│    (path, host, method, headers)   │
│  - transforms to apply (Lec.4 §15.1) │
│  - references EXACTLY ONE ClusterId   │───────┐
└───────────────────────────────┘         │
                                            ▼
                                ┌───────────────────────────────┐
                                │  CLUSTER                        │   changes: occasionally
                                │  - a stable logical NAME           │   (deploy new versions,
                                │  - load-balancing policy (Lec.4 §6.2)│    scale up/down)
                                │  - health-check policy (Lec.4 §6.2)   │
                                │  - references MANY Destinations        │───────┐
                                └───────────────────────────────┘         │
                                                                            ▼
                                                                ┌───────────────────────────────┐
                                                                │  DESTINATION                    │   changes: constantly,
                                                                │  - one specific backend address    │   automatically
                                                                │  - current health state              │   (deploys, autoscale,
                                                                └───────────────────────────────┘         crashes)
```

**A route references exactly one cluster; a cluster contains any number of destinations.** This many-to-one-to-many shape is precisely why the model is useful: many different routes (`/v1/users/*`, `/v1/users/{id}/preferences`) can share the *same* cluster (they're all "the user service," logically), so scaling that service up or down updates its destination set exactly once, and every route pointing at it benefits automatically — no route ever needs to be touched when destinations change.

---

## 7. Dynamic Configuration — What Happens When Routes Change While Running

### 7.1 The naive (and dangerous) approach

Directly mutating a live routing table in place — adding, removing, or editing entries in the exact data structure that's simultaneously being read by every in-flight request's matching lookup — risks classic concurrent-mutation problems: a request's match could observe a routing table in a half-updated, inconsistent state (some new routes present, some old ones not yet removed, or worse, a matching structure like §5.2's tree being read while it's mid-restructure).

### 7.2 The real approach: immutable snapshots and atomic swap

Real proxies (YARP included) instead follow a pattern you should recognize as a recurring, deliberate design choice in infrastructure software: **build an entirely new, complete routing structure off to the side, fully finished and validated, then atomically swap a single pointer/reference so all *future* requests see the new structure instantly and completely, while requests already in flight keep finishing against whichever structure they started with.**

```
   Config change detected (file edited, API call, etc.)
              │
              ▼
   Build a BRAND NEW, complete routing structure
   (§5.2's tree, precedence values, everything)
   — entirely OFF TO THE SIDE, not touching the live one
              │
              ▼
   Validate it fully (§9.3 — catch conflicts/errors HERE,
   before it's ever live)
              │
              ▼
   ATOMIC SWAP: one pointer update — "current routing
   structure" now refers to the new one
              │
              ▼
   Every NEW request from this instant onward matches
   against the new structure. Every request that was
   ALREADY in flight keeps using the old structure it
   already started with, until it finishes — never sees
   a torn, half-updated view.
```

This is exactly the same underlying idea as Lecture 3 §8.2's DI container being finalized once at `builder.Build()` and then used read-only from then on — build a complete, consistent structure first, then only ever hand out fully-formed, immutable views of it, rather than mutating shared live state under concurrent readers. It's also why this kind of reconfiguration can safely happen *without* a restart and *without* any in-flight request being disrupted or observing an inconsistent routing table mid-request.

### 7.3 What triggers a rebuild

Configuration can come from more than one source, and YARP's design deliberately abstracts this — a config *provider* is anything that can supply a routing structure and signal "something changed, please rebuild." A file-based provider watches `appsettings.json` (Lecture 3 §11) for changes; other providers might poll a service-discovery system, or receive push updates from a control plane. The rebuild-and-atomic-swap mechanism from §7.2 is identical regardless of *why* the change happened — this is a deliberate separation between "where configuration comes from" and "how safely it gets applied," letting either be changed independently.

---

## 8. Performance — Why Route Lookup Must Be Efficient

### 8.1 The core constraint: this runs on every single request

Recall from Lecture 3 §17.3's architecture diagram — route matching sits directly on the hot path, before anything backend-related even begins. Every millisecond spent here is pure overhead paid by *every* request, multiplied by total request volume. At the production scales discussed in Lecture 4 §12 (millions to hundreds of millions of requests), even a small per-request inefficiency compounds into a very real aggregate cost — CPU spent matching routes is CPU not available for anything else the proxy needs to do (accepting connections, forwarding data, running transforms).

### 8.2 Why route *count* specifically matters

A single large organization's API gateway can easily have hundreds or thousands of registered routes — one per microservice endpoint pattern, sometimes more with versioning and header-based variants (§4.3–§4.4) multiplying the effective count. The naive linear-scan approach from §5.1 degrades linearly with route count — twice the routes, twice the average work per request. The tree/precomputed-structure approach from §5.2 is specifically designed so that lookup cost depends much more on *path depth* (how many segments deep the URL is) than on *total route count* — meaning it stays fast even as the routing table grows substantially, which is exactly the property a system with a large, evolving set of routes needs.

### 8.3 Why the build-once, reuse-many-times pattern (§5.3, §7.2) is a performance decision, not just a safety one

It's worth explicitly noticing that §7.2's atomic-swap pattern for dynamic config and §5.3's build-once precedence computation are *the same underlying idea*, serving *both* a correctness goal (§7.2 — never expose a half-updated or inconsistent view) and a performance goal (§8.1 — never redo expensive work on the hot per-request path). This dual payoff is a strong, general signal in infrastructure software: when you see "compute once at config-load time, reuse cheaply per request" as a pattern, it's very often solving both problems simultaneously, not just one.

---

## 9. Failure Scenarios

### 9.1 No route matches

The request's method/path/host/headers don't satisfy any registered route. The correct behavior is an explicit `404 Not Found` — this is precisely a case Lecture 1 §4.8's status code taxonomy anticipated: it's not that the *resource* doesn't exist (the backend might have it) — it's that the *proxy itself* has no rule telling it where to even attempt to look, and it must say so plainly rather than guessing or defaulting somewhere unexpected. A well-built router treats "no match" as a definite, first-class outcome of the matching function from §3, not an error condition to be worked around.

### 9.2 Multiple routes match

Covered mechanically in §4.6–§4.7: if precedence rules can deterministically pick a winner (specificity ordering, or an explicit configured priority), that winner is used, silently and correctly, on every single request — this is the *common*, well-handled case, not a failure at all. It only becomes a genuine failure when precedence *cannot* resolve it (§4.7's true conflict) — and the correct behavior there is to catch it at configuration validation time (§9.3), not to let it reach request-matching time and behave unpredictably.

### 9.3 Configuration is invalid

This includes: a route referencing a `ClusterId` that doesn't exist, a genuinely unresolvable route conflict (§4.7), a malformed match pattern, or a cluster with zero destinations. The correct behavior, following directly from §7.2's "validate fully before ever going live" step, is to **reject the new configuration outright and keep serving the last-known-good configuration** — never partially apply a broken config, and never let an invalid configuration take down a currently-working proxy. This is a "fail closed on the *new* config, fail open on continuing to serve the *old*, known-good one" posture — a deliberate, conservative choice appropriate for infrastructure software that's expected to keep serving traffic reliably even when someone made a config mistake.

### 9.4 A destination disappears

This is worth distinguishing carefully from the previous three, because it happens at a **different layer entirely**: routing (this lecture) decided which *cluster* to use; destination selection within that cluster (Lecture 4 §7, §15) is where an individual, now-vanished backend instance would actually be discovered as unreachable — via the connection-level failures from Lecture 2 §10 and Lecture 4 §13.1, at the point the proxy actually tries to forward the request. Routing itself doesn't "fail" when a destination disappears — the *route* still correctly points at the *cluster*; it's health checking and load balancing (Lecture 4 §6.2, §13.6), operating one layer below routing, whose job it is to notice and route around the specific missing destination. Keeping this distinction sharp — "routing picked the right cluster; something below routing then failed to reach a specific instance within it" — is exactly the kind of precise, layered thinking this whole lecture (and Lecture 4 §7.1) has been building toward.

---

## 10. Common Misconceptions

- **"The order routes are written in the config file determines which one wins."** Not for well-designed precedence — §4.6 explicitly requires precedence to be a deterministic function of specificity (or an explicit priority field), independent of incidental file ordering; relying on accidental order is exactly the bug this design avoids.
- **"`{id}` and a catch-all wildcard are basically interchangeable."** Directly contradicted by §4.5 — they match structurally different sets of paths, and confusing them silently breaks matching for nested paths with no error raised anywhere.
- **"Routing is checked linearly against every rule, every time, so more routes always means proportionally slower."** True only of the naive approach (§5.1) — real routers (§5.2) are specifically built so this isn't the case, which is exactly why route-table performance doesn't degrade badly even at large route counts (§8.2).
- **"Changing routing config requires a restart."** Contradicted by §7.2 — the atomic-swap pattern exists specifically to make live reconfiguration safe without a restart or disruption to in-flight requests.
- **"If a destination goes down, that's a routing failure."** §9.4 draws this distinction precisely — routing chose the correct cluster; a missing destination is a lower-layer (health-check/load-balancing/connection) concern, not a routing one.
- **"Ambiguous route conflicts will just pick 'the more likely one' automatically."** §4.7 and §9.3 are explicit: a genuine conflict should be caught and rejected at config-validation time, not silently resolved with a guess at request time.

---

## 11. Production Perspective: 10 → 10,000 → 1,000,000 → 100,000,000 Requests (and Routes)

**~10 routes, low request volume**: the naive linear-scan approach (§5.1) is completely invisible performance-wise — you could build routing this way and never notice a problem, and precedence rules rarely even get exercised because overlaps are unlikely with so few rules.

**~10,000 requests/sec, dozens to low hundreds of routes**: the precomputed matching structure (§5.2) starts to matter measurably, and precedence conflicts (§4.6–§4.7) become genuinely likely to occur as more teams add routes independently — this is roughly the scale where you want configuration validation (§9.3) actively catching conflicts before they ever reach production traffic, rather than hoping they don't arise.

**~1,000,000 requests/sec, potentially thousands of routes (large multi-team organization)**: route lookup performance (§8) is now directly on the critical path of overall system throughput — a slow matching implementation here is indistinguishable, from a systems perspective, from a slow backend, even though no backend is even involved yet. Dynamic configuration (§7) is now a near-constant occurrence rather than a rare event, as many independent teams deploy and update their own services' routes continuously — the atomic-swap safety property (§7.2) stops being a nice-to-have and becomes essential to avoid visible disruption during routine, frequent changes.

**~100,000,000 requests/sec across a large fleet of proxy instances**: route configuration itself needs to be distributed consistently and efficiently to potentially many independent proxy instances (a config *provider*, §7.3, might be backed by a distributed configuration/service-discovery system rather than a single local file) — and the cost of *rebuilding* the routing structure (§5.2, §7.2) on every config change, across every instance, becomes its own capacity-planning concern, not just the per-request lookup cost.

---

## 12. Performance Implications

- **Never scan a flat route list per request at meaningful scale** (§5.1 vs §5.2) — precompute a fast-lookup structure once, at config-load time, and reuse it.
- **Compute precedence/specificity once, at build time**, not per request (§5.3) — this is a config-load-time cost paid once per config change, not a per-request cost paid constantly.
- **Validate configuration fully before it ever goes live** (§7.2, §9.3) — catching a conflict at load time costs nothing on the hot path; catching it at request time (or not at all) is both slower and less safe.
- **Keep the atomic-swap window as small and lock-free as possible** (§7.2) — in-flight requests should never observe a torn or partially-updated routing structure, and readers (request matching) ideally shouldn't need to take a lock at all against a config *writer* that's rare relative to the volume of reads.
- Deep tuning of the specific tree/matching data structure's internals (radix trees, specific hashing strategies) is **not** where your effort belongs yet — ASP.NET Core's routing engine (Lecture 3 §10.1) already implements this well; understanding *that it exists and why it's shaped this way* (§5.2) is the right depth for this series.

---

## 13. YARP Connection

### 13.1 The configuration types you should recognize on sight

- **`RouteConfig`**: the configuration-time representation of a route (§4, §6) — holds the match conditions (`RouteMatch`: path pattern, hosts, methods, headers — directly the criteria from §4.1–§4.4), the `ClusterId` it targets, and any transforms (Lecture 4 §15.1) to apply.
- **`RouteMatch`**: the nested object inside `RouteConfig` holding the actual match criteria (`Path`, `Hosts`, `Methods`, `Headers`, `QueryParameters`) — this is the direct configuration-level expression of everything in §4.
- **`ClusterConfig`**: the configuration-time representation of a cluster (§6) — load-balancing policy, health-check settings, and a dictionary of `DestinationConfig` entries.
- **`DestinationConfig`**: one backend address entry within a cluster (§6) — the volatile, frequently-changing layer.

### 13.2 The internal, "built" representations you should expect to also see

Following §5.2's "build once, reuse cheaply" pattern, expect YARP's internals to maintain both the raw configuration types above *and* separately-built, ready-to-match internal model objects (commonly named along the lines of `RouteModel`, `ClusterState`, `DestinationState` in YARP's actual source) — the configuration types are what you author; the model/state types are what's actually consulted on the hot per-request path, exactly mirroring this lecture's distinction between "configuration" and "the precomputed structure built from it."

### 13.3 The provider abstraction you should expect for dynamic config

Expect an interface along the lines of **`IProxyConfigProvider`**, whose job is exactly §7.3's "supply a routing structure, and signal when it changes" — with a built-in, file/`appsettings.json`-backed implementation (matching Lecture 3 §11.2's configuration system directly) as the common default, and the ability to implement your own provider (backed by a database, a service-discovery system, an internal control plane) via the same DI-based extensibility pattern from Lecture 3 §8.4. Expect to see something like a change-notification mechanism (an `IChangeToken`-style callback, a standard .NET pattern for "notify me when this thing changes") triggering §7.2's rebuild-and-atomic-swap sequence.

### 13.4 Where matching actually happens

Per §5.2's key point — YARP does not reimplement route matching from scratch. Expect to see YARP registering its routes as genuine ASP.NET Core `Endpoint` objects (recall Lecture 3 §10.1's endpoint routing) into the standard ASP.NET Core routing system, meaning the actual match-time work (the fast tree/lookup structure, the precedence resolution) is performed by the framework's own already-optimized routing engine — YARP's job is to correctly *construct* those endpoints from `RouteConfig`/`RouteMatch` (§13.1) at config-build time, and to attach its own forwarding logic as what runs once a given endpoint is selected (Lecture 3 §17.3's diagram). This is a direct, concrete instance of Lecture 3 §17.1's overall thesis — YARP is built *from* ASP.NET Core's own primitives, not alongside them.

### 13.5 Terminology checklist

By now you should be able to recognize, without looking anything up: `RouteConfig`, `RouteMatch`, `ClusterConfig`, `DestinationConfig`, `IProxyConfigProvider`, and some notion of a built/model representation distinct from raw configuration — and you should be able to say, for each one, roughly which section of this lecture explains the concept it implements.

---

## 14. What I Don't Need to Know Yet

- The exact specificity-scoring algorithm ASP.NET Core's routing engine uses internally (precise tie-breaking rules across every possible combination of literals, parameters, and constraints) — §4.6/§5.3's "more specific wins, computed once" is the right depth.
- The precise API shape of `IProxyConfigProvider` (exact method signatures, how to implement one from scratch) — §13.3's conceptual role is sufficient until you're actually writing a custom provider.
- Query-parameter-based matching specifics — a real, supported match criterion in YARP, structurally identical in spirit to header matching (§4.4); not necessary to cover as a separate mechanism here.
- The specific data structure ASP.NET Core's routing engine uses internally (whether it's precisely a trie, a DFA, or something else) — §5.2's conceptual tree is sufficient; the exact implementation is a framework internal, not something you need to reproduce.
- Distributed configuration systems / service discovery integration specifics (§11's "100,000,000" tier) — recognize this as a real concern at large scale; the specific technology choices are a separate, later topic.

---

## 15. Knowledge Check

1. Two routes are configured: `Path = /v1/orders/{**catch-all}` and `Path = /v1/orders/{id}, Method = GET`. A `GET /v1/orders/8891/items` request arrives. Using §4.5's wildcard distinction, explain which route (if either) matches, and why.
2. Explain, using §5.1 vs §5.2, why doubling the number of registered routes in a proxy does *not* necessarily double the average per-request routing cost in a well-built router.
3. A team adds a new route that conflicts irreconcilably with an existing one (§4.7). Using §9.3, explain what should happen at the moment this configuration is loaded, and why that's preferable to catching it only when a real request happens to trigger the ambiguity.
4. Using §7.2, explain why an in-flight request that started matching against the *old* routing configuration is safe to let finish normally, even after a config change has already been applied for all new requests.
5. A backend instance crashes. Using §9.4, explain precisely why this is not a routing failure, and name which two mechanisms (from Lecture 4) are actually responsible for handling it.
6. Using §13.4, explain why understanding Lecture 3 §10.1's endpoint-routing match/execute split was a *necessary* prerequisite for understanding how YARP's routing actually works, rather than just helpful background.

---

## 16. Practical Exercise

Extend the YARP proxy from Lecture 4 §18 to make route precedence and wildcard behavior directly observable.

### Step 1 — Add a second, more specific route

In your Lecture 4 `proxy/appsettings.json`, add a second, more specific route alongside the existing one:

```json
{
  "ReverseProxy": {
    "Routes": {
      "usersGeneral": {
        "ClusterId": "userServiceCluster",
        "Match": { "Path": "/v1/users/{**catch-all}" }
      },
      "usersDeleteAdmin": {
        "ClusterId": "userServiceCluster",
        "Match": { "Path": "/v1/users/{id}", "Methods": [ "DELETE" ] }
      }
    },
    "Clusters": {
      "userServiceCluster": {
        "LoadBalancingPolicy": "RoundRobin",
        "Destinations": {
          "instance1": { "Address": "http://localhost:5001" },
          "instance2": { "Address": "http://localhost:5002" }
        }
      }
    }
  }
}
```

(Both routes point at the same cluster here for simplicity — in a real system `usersDeleteAdmin` would typically point at a different, more restricted cluster; the config above is enough to observe *matching* behavior, which is this lecture's focus.)

### Step 2 — Add a route-identifying endpoint to your backend

So you can see which route actually handled a request, extend `backend/Program.cs`:
```csharp
app.MapMethods("/v1/users/{id}", new[] { "GET", "DELETE", "PUT" }, (int id, HttpContext ctx) =>
    Results.Json(new { id, method = ctx.Request.Method, servedBy = app.Configuration["urls"] }));
```

### Step 3 — Observe wildcard vs. specific matching (§4.5)

```bash
curl http://localhost:5000/v1/users/42                 # matches usersGeneral (catch-all)
curl http://localhost:5000/v1/users/42/orders/8         # matches usersGeneral (catch-all reaches deeper paths)
curl -X DELETE http://localhost:5000/v1/users/42         # should match usersDeleteAdmin — more specific
```

Add logging (`Console.WriteLine` in a transform, or just watch your backend's `method` field in the response) to confirm the `DELETE` request is in fact being distinguished from `GET`/`PUT` at the routing layer, not just handled identically and differentiated later.

### Step 4 — Break precedence deliberately, then fix it

Change `usersDeleteAdmin`'s path to also be a catch-all: `"Path": "/v1/users/{**catch-all}", "Methods": [ "DELETE" ]` — now both routes are catch-alls, differing only by method constraint, which are no longer in a clean "one is strictly more specific" relationship for a `DELETE` request (both would match a `DELETE /v1/users/42`). Restart the proxy and see whether it starts up cleanly or reports a configuration problem — this is §9.3's validation behavior, made directly observable rather than theoretical. Revert the change afterward.

---

## 17. "Ready to Move On" Criteria

Before starting the next lecture, you should be able to explain — out loud, in your own words:

- [ ] How to progressively build up a routing rule from path-only to path+host+method+headers combined, and what each additional criterion narrows.
- [ ] The difference between a single-segment parameter (`{id}`) and a catch-all wildcard, and a concrete case where confusing them breaks matching silently.
- [ ] Why route precedence must be a deterministic function of specificity (or explicit priority), never incidental config-file order.
- [ ] Why a naive linear scan of all routes doesn't scale, and what a precomputed matching structure buys you instead.
- [ ] The route → cluster → destination data shape precisely — what fields live at each layer and why they reference each other the way they do.
- [ ] How dynamic configuration changes are applied safely — the build-off-to-the-side, validate, then atomic-swap pattern — and why in-flight requests are unaffected by a change happening mid-flight.
- [ ] The four distinct failure scenarios (no match, ambiguous match, invalid config, vanished destination) and why "vanished destination" specifically is *not* a routing-layer failure at all.
- [ ] YARP's core configuration types (`RouteConfig`, `RouteMatch`, `ClusterConfig`, `DestinationConfig`) and the role of `IProxyConfigProvider`, well enough to expect to recognize them immediately in the real source.

If these feel solid, you're ready to go deeper into what happens *after* routing picks a cluster — load balancing, health checking, and session affinity — which this lecture deliberately deferred (§14) as the natural next layer down.
