# Lecture 4: Reverse Proxies and API Gateways

Series: YARP Learning Series
Builds on: [Lecture 1 — HTTP](001-http_from_the_wire_to_the_application.md), [Lecture 2 — TCP/IP/Sockets](002-tcp_ip_sockets_and_network_connections.md), [Lecture 3 — ASP.NET Core Architecture](003-aspnetcore_request_processing_and_architecture.md).
This lecture is the synthesis point of the series: every prior lecture was building toward the ability to look at YARP and say "I understand why this exists and roughly how it's built," rather than just recognizing class names.

---

## 1. Learning Objectives

By the end of this lecture you should be able to:

1. Explain, from first principles, what problems get solved by inserting a proxy between clients and servers — not as a list of features, but as answers to "what goes wrong without one."
2. Correctly distinguish a forward proxy from a reverse proxy by asking "whose interests does this proxy serve, and who is it hiding?" — and explain precisely why YARP is a reverse proxy.
3. Categorize a reverse proxy's responsibilities into "structurally required" vs. "commonly bundled but optional," and justify the split.
4. Walk a request through the full decision chain — route selection, cluster selection, destination selection — and explain what question each stage is answering.
5. Explain how a proxy handles headers, bodies, streaming, status codes, cancellation, and disconnects, using the mechanisms from Lectures 1–3 rather than new vocabulary.
6. Explain why production systems stack multiple layers of proxies/load balancers rather than using one, and what distinct job each layer does.
7. Describe YARP's internal conceptual architecture (routes, clusters, destinations, transforms, forwarder) well enough that opening the actual source code will feel like meeting expected shapes, not surprises.

---

## 2. Prerequisite Concepts

This lecture leans on all three previous ones directly and constantly:

- From **Lecture 1**: headers, status codes, streaming, and the fact that HTTP versions can differ between two legs of a conversation.
- From **Lecture 2**: a connection is not a request, connection reuse and pooling, and the specific failure modes (timeout, reset, hang) that a proxy has to translate into something coherent.
- From **Lecture 3**: middleware, endpoint routing's match/execute split, DI-based extensibility, and — critically — that a proxy built on ASP.NET Core is itself an HTTP server *and* an HTTP client (Lecture 2 §15.1) implemented using the exact same building blocks as any other app.

If any of those feel shaky, this lecture will expose it quickly, because it deliberately reuses that vocabulary rather than re-explaining it.

---

## 3. Core Mental Model

```
   Client  ──────────────────────►  Server
```
versus
```
   Client  ──────►  Reverse Proxy  ──────►  Server
```

The one-sentence version of this entire lecture: **a reverse proxy exists because "client talks directly to a specific server" stops being a good enough model the moment you have more than one server, or the moment you need to make a decision about the request that the server itself shouldn't have to make.** Everything else in this lecture — routing, load balancing, TLS termination, retries, health checks — is a specific instance of "a decision that got moved out of the server and into a dedicated place in front of it."

---

## 4. The Problem — Why Put a Proxy in the Middle?

### 4.1 Start with the direct model and find where it breaks

`Client → Server` works fine as long as: there's exactly one server, that server's address never changes, that server is never overloaded, that server never needs maintenance without downtime, and the client is trusted to know exactly how to reach it securely. Real systems violate every one of these assumptions almost immediately:

- **More than one server.** The moment you have two servers doing the same job (for capacity or redundancy), *something* has to decide which one a given request goes to. The client itself could do this — but that means every client needs to know about server topology, handle a server going down, and re-implement that logic independently. Centralizing that decision in one place, in front of the servers, is strictly simpler and more consistent.
- **Servers come and go.** Deployments, crashes, scaling up/down — the actual set of healthy servers is constantly shifting. A client that "just remembers an IP" breaks the instant that IP stops being valid. A proxy can track the current healthy set and route accordingly, so clients never need to know it changed at all.
- **Cross-cutting concerns duplicated everywhere.** TLS termination, auth checks, rate limiting, request logging — if every individual backend service has to implement these itself, you get N slightly-different implementations, N places for security bugs to hide, and N places to update when the policy changes. Doing it once, in front of everything, is both simpler and more consistent.
- **You don't want to expose backend topology to the internet.** Real backend addresses (often private IPs, per Lecture 2 §4.3) are an internal implementation detail — exposing them directly to clients is both a security liability and an operational straightjacket (you can never change them without breaking clients).

### 4.2 What the proxy actually buys you, stated plainly

A reverse proxy turns "many servers, each with their own address, health, and concerns" into "one stable address, one place where cross-cutting decisions are made, many servers hidden safely behind it." The client's mental model stays simple (`Client → Server`, from its point of view) even though the truth behind that arrow has become considerably more complex.

```
                    ┌─────────────────────────────────┐
  Client  ────────► │         Reverse Proxy             │
                    │   (this is ALL the client sees)    │
                    └─────────────────────────────────┘
                              │      │      │
                              ▼      ▼      ▼
                          Server1  Server2  Server3
                       (private, unknown to the client,
                        can change at any time without
                        the client ever noticing)
```

---

## 5. Reverse Proxy vs. Forward Proxy

This distinction trips people up constantly, and the fix is to stop thinking about *position in the network diagram* and start asking one question: **whose interests does this proxy serve, and whose identity/existence is it hiding?**

### 5.1 Forward proxy — serves the client side, hides the client

```
   Client A  ─┐
   Client B  ─┼──►  Forward Proxy  ──────►  Internet / any server
   Client C  ─┘     (acts ON BEHALF OF
                      the clients)
```

A forward proxy sits in front of a group of *clients* and makes requests to the wider internet *on their behalf*. From the destination server's point of view, it can't easily tell which specific client (A, B, or C) actually originated a given request — it only sees the proxy. Classic examples: a corporate network's outbound web proxy (so all employee traffic exits through one controlled, monitored point), or a VPN-style anonymizing proxy. The defining trait: **the servers being contacted don't necessarily know or care that a proxy is involved at all, and the proxy is configured/trusted by the client side.**

### 5.2 Reverse proxy — serves the server side, hides the servers

```
   Internet  ──────►  Reverse Proxy  ──┬──►  Server 1
                      (acts ON BEHALF                 │
                       of the servers)                ├──►  Server 2
                                                        │
                                                        └──►  Server 3
```

A reverse proxy sits in front of a group of *servers* and receives requests from clients *on the servers' behalf*, then decides internally which actual server handles each one. From the client's point of view, it can't easily tell which specific backend server actually handled the request — it only sees the proxy (this is exactly the topology from §4.2). The defining trait: **the client doesn't necessarily know or care that a proxy is involved at all, and the proxy is configured/trusted by the server side.**

### 5.3 The comparison, side by side

| | Forward Proxy | Reverse Proxy |
|---|---|---|
| Sits in front of | clients | servers |
| Acts on behalf of | the client side | the server side |
| Hides the identity of | the client, from the server | the server, from the client |
| Configured/deployed by | the client's organization (e.g., corporate IT) | the server's organization (e.g., the API owner) |
| Client is aware it exists? | usually yes (explicitly configured) | usually no (it's transparent — looks like "the server") |

### 5.4 Why YARP is unambiguously a reverse proxy

YARP is deployed and configured by whoever owns the *backend services* — its entire job (as Lecture 2 §15.1 and Lecture 3 §17 already established) is to sit in front of one or more backend servers, present one stable, controlled surface to the outside world, and route incoming client requests to the correct backend, invisibly. The client talking to `api.contoso.com` has no idea, and no need to know, whether YARP is involved at all, how many backend instances exist, or which one actually served their request. Nothing about YARP acts on a client's behalf out into the wider internet the way a forward proxy does — its entire orientation is server-side. This isn't a subtle judgment call; it's the textbook case §5.2 describes.

---

## 6. Core Responsibilities — Required vs. Optional

Here's a genuinely important distinction the master framing for this series asked for explicitly: some of these things are **structurally inherent** to being a reverse proxy at all — you cannot build one without doing them, even in the simplest possible implementation. Others are **commonly bundled capabilities** — extremely common in real deployments, and often exactly why an organization chooses a specific proxy product, but not logically required for something to *be* a reverse proxy.

### 6.1 Structurally required (a proxy cannot avoid doing these)

- **Routing** — deciding *which backend* a given request should go to. Even a proxy in front of exactly one backend is technically "routing" (trivially, always to that one place) — the moment there's more than one possible destination, this becomes an actual decision, not a formality.
- **Connection management** — per Lecture 2 §15, the proxy inherently manages two independent connection lifecycles (client-facing and backend-facing) for every request. There's no way to be a reverse proxy without this; it's the definition of sitting in the middle.
- **Request/response relaying** — reading the incoming request and producing an outgoing one to the backend, then doing the reverse for the response (Lecture 1 §15, Lecture 3 §17.3). Even the most minimal possible proxy does this.

### 6.2 Extremely common, but optional capabilities

Each of these is something a reverse proxy is *well-positioned* to do (because it already sits in the request path for every request to every backend), not something inherent to the definition:

- **Load balancing** — *how* to choose among multiple valid destinations for a route (round-robin, least-connections, etc.). Requires routing (§6.1) to already have narrowed things down to "more than one acceptable backend" — load balancing is the tie-breaker among those.
- **TLS termination** — decrypting client TLS traffic at the proxy, then either forwarding plaintext internally or re-encrypting a separate TLS connection to the backend (Lecture 2 §2.4). A proxy could instead just relay encrypted bytes through untouched ("TLS passthrough") without ever seeing plaintext — meaning termination is a deliberate choice, not an unavoidable proxy behavior.
- **Authentication/authorization** — checking identity/permissions at the edge before forwarding. Entirely optional architecturally — many systems instead leave auth entirely to backend services, or split it (light checks at the proxy, full checks at the backend).
- **Request/response transformation** — rewriting headers, paths, or even bodies in flight (e.g., stripping an internal-only header before it reaches the backend, or adding `X-Forwarded-For`, per Lecture 3 §17.2's mention of proxy-specific headers from Lecture 1 §4.6). A pure "dumb" relay wouldn't do this at all.
- **Retries** — reattempting a failed request against a different backend instance. Requires the idempotency awareness from Lecture 1 §4.4 — genuinely optional, and genuinely dangerous to enable carelessly.
- **Health checking** — actively or passively tracking which backends are currently healthy, so routing/load-balancing decisions can avoid sending traffic to a known-bad destination. A minimal proxy could route blindly and simply let requests to a dead backend fail every time.
- **Observability** — logging, metrics, tracing for every request passing through (a natural fit, per Lecture 3 §12, given the proxy already sees every request) — but not something inherent to forwarding itself.
- **Rate limiting** — capping request volume, whether per-client, per-route, or globally, to protect backends from being overwhelmed.

### 6.3 Why this distinction matters practically

Recognizing "required" vs. "optional" tells you what a proxy *must* get right to function at all, versus what differentiates one proxy product/configuration from another. It also directly explains YARP's own design: YARP ships the required core (§6.1) plus strong, well-integrated support for the most common optional capabilities (§6.2) — but deliberately built as a *library* (Lecture 3 §17.1) specifically so you can add, remove, or replace any of the optional pieces to fit your own needs, rather than being stuck with someone else's fixed bundle.

---

## 7. Request Flow — The Full Decision Chain

```
  Client
     │
     ▼
  Proxy  ──────────────────────────────────────────────────────────┐
     │                                                                │
     ▼                                                                │
  ROUTE SELECTION                                                     │
  "which logical rule matches this request?"                           │
  (based on path, host, headers, method — Lecture 3 §10's                │
   endpoint-routing match phase, applied to proxy rules)                  │
     │                                                                │
     ▼                                                                │
  CLUSTER SELECTION                                                    │
  "which GROUP of backend instances does this route point to?"          │
  (a route maps to exactly one cluster — a cluster is the logical         │
   name for "the user-service backends," say, independent of              │
   exactly how many instances currently exist)                              │
     │                                                                │
     ▼                                                                │
  DESTINATION SELECTION                                                 │
  "which SPECIFIC instance, within that cluster, handles THIS             │
   particular request?" (load balancing policy, §6.2, applied              │
   only among currently-healthy destinations, §6.2's health checking)        │
     │                                                                │
     ▼                                                                │
  Backend                                                              │
     │                                                                │
     ▼                                                                │
  Response  (flows back up through the SAME chain, in reverse,           │
             exactly like Lecture 3 §7.1's middleware "way up" phase)      │
     │                                                                │
     ▼                                                                │
  Client                                                               │
```

### 7.1 Why three separate stages, not one?

This might look like unnecessary ceremony for "pick a server," but each stage answers a genuinely different question, at a genuinely different rate of change:

- **Routes** change when *application-level* rules change — "traffic to `/v1/*` goes to the user-service" is a business/architecture decision, updated relatively rarely.
- **Clusters** are a stable *logical* grouping — "the user-service cluster" doesn't change identity just because you scaled from 3 instances to 8.
- **Destinations** change *constantly and automatically* — instances get added and removed continuously (deployments, autoscaling, crashes), completely independent of the route or cluster definitions above them.

Separating these means a destination coming and going never has to touch routing configuration at all, and a routing-rule change never has to know anything about specific server instances. This mirrors exactly the same instinct from Lecture 3 §10.1's match/execute split — decompose a decision into independently-changeable pieces so each piece can evolve at its own natural pace, without the others needing to know or care.

### 7.2 Concretely, in configuration terms

```json
{
  "ReverseProxy": {
    "Routes": {
      "usersRoute": {
        "ClusterId": "userServiceCluster",
        "Match": { "Path": "/v1/users/{**catch-all}" }
      }
    },
    "Clusters": {
      "userServiceCluster": {
        "LoadBalancingPolicy": "RoundRobin",
        "Destinations": {
          "instance1": { "Address": "http://10.0.4.11:5000" },
          "instance2": { "Address": "http://10.0.4.12:5000" }
        }
      }
    }
  }
}
```

Notice this is literally the same layered, environment-driven configuration model from Lecture 3 §11.2 — routes and clusters are exactly the "code vs. configuration" separation applied to a proxy's core job.

---

## 8. Proxying Data

Everything here is a direct, practical continuation of Lecture 1 and Lecture 2 — nothing new conceptually, just applied specifically to "the proxy is now the thing doing it, on both legs at once."

- **Headers** (Lecture 1 §4.6, Lecture 3 §17.2): the proxy must decide, header by header, whether to relay unchanged, rewrite, add, or strip — connection-specific headers (`Connection`, hop-by-hop headers) must **not** be blindly forwarded to the backend leg (they describe the client-facing connection, which is a different connection entirely, per Lecture 2 §8.3), while application-meaningful headers (`Authorization`, `Content-Type`) generally should be.
- **Bodies** (Lecture 1 §4.7, §9): must be relayed — ideally streamed, not buffered — from the incoming request to the outgoing backend request, and symmetrically for the response, exactly as Lecture 1 §15.2 and Lecture 3 §17.3 already described.
- **Streaming** (Lecture 1 §9): the proxy's biggest architectural constraint — buffering defeats the entire memory/latency benefit of streaming, multiplied across every concurrent request the proxy handles (Lecture 1 §9's "1,000 concurrent 500MB downloads" example applies directly and specifically to a proxy sitting in that path).
- **Status codes** (Lecture 1 §4.8): mostly relayed unchanged from backend to client — except when the proxy itself needs to report something the backend never said, because the backend was never reached at all (§13 below covers this precisely).
- **Cancellation** (Lecture 3 §9.4): `HttpContext.RequestAborted` firing on the client leg should propagate to cancel the in-flight backend call — this is the proxy-specific application of exactly the cancellation-propagation principle from Lecture 2 §15.2.
- **Client disconnects** (Lecture 2 §10.6): the proxy needs to actively notice a disconnected client (rather than passively continuing to wait/work, per Lecture 2 §10.6's point that this isn't automatic) and treat it the same as cancellation above — stopping wasted backend work as early as possible.

---

## 9. Reverse Proxies at Scale — Why So Many Layers?

### 9.1 The layered architecture

```
   Internet
      │
      ▼
    Edge            <- DDoS protection, global anycast routing, CDN/static caching,
      │                 often the FIRST point of TLS termination, geographically distributed
      ▼
Load Balancer        <- distributes traffic across many identical REGIONAL entry points,
      │                 typically operates at a lower level (can be L4/transport-level,
      │                 not necessarily understanding HTTP deeply at all)
      ▼
Reverse Proxy         <- THIS is where YARP-like behavior lives: HTTP-aware routing,
      │                    per-route/per-cluster logic, transforms, retries, auth
      ▼
   Service            <- your actual application/business logic
      │
      ▼
   Database
```

### 9.2 Why not just one layer doing everything?

Each layer exists because it solves a problem *at a different scope and a different level of the stack*, and conflating them would mean every layer has to be as complex, as widely distributed, and as frequently updated as the most demanding one:

- **Edge** operates globally, close to users, and deals with concerns that are almost entirely about the *network* (Lecture 2's territory) — absorbing attack traffic, routing users to the nearest region — largely without needing deep application-level HTTP awareness (Lecture 1's territory).
- **Load balancers** at this tier are often deliberately "dumb" and fast — sometimes operating below full HTTP understanding, just distributing TCP connections (Lecture 2 §6–§7) across a set of regional targets — because doing less work per-packet means handling far more total traffic.
- **Reverse proxies** (YARP's actual home) are where HTTP-aware, business-logic-adjacent decisions belong — the specific route→cluster→destination chain from §7, transforms, auth, retries — because this requires the deep protocol understanding from Lecture 1 and the application-framework integration from Lecture 3, and it changes far more often than edge/network-layer concerns do.
- **Services** hold actual business logic; **databases** hold actual state — neither should be doing networking/routing decisions at all, per the separation-of-concerns theme running through this entire series (Lecture 2 §3, Lecture 3 §4.1).

Put differently: each layer is optimized for a different combination of (how much traffic it must handle) × (how much it needs to understand about that traffic) × (how often its logic changes) — and a single monolithic layer would be forced to compromise on all three simultaneously.

### 9.3 Concretely, why does one request cross so many hops?

A request from a phone on a cellular network to a database write might genuinely cross: the carrier's network → an edge PoP (point of presence) → a regional load balancer → a reverse proxy (YARP) → a specific service instance → a database connection pool → the database itself. Each hop adds some latency (Lecture 2 §9 — every hop is potentially its own round trip cost) — this is a real, deliberate trade-off large systems make: a small amount of added latency per request, in exchange for each layer being independently scalable, independently deployable, and independently replaceable without touching the others.

---

## 10. Where YARP Fits in This Landscape

YARP is purpose-built for the **reverse proxy** layer in §9.1's diagram — not the edge, not the low-level load balancer, and not the service itself. Concretely, this means:

- YARP is deployed *inside* your own infrastructure, close to your services, understanding your specific routing/cluster topology — not a globally-distributed edge network (that's a different category of product, e.g., a CDN).
- YARP operates with full HTTP awareness (Lecture 1, Lecture 3) — it's not a low-level TCP load balancer; it makes decisions based on paths, headers, and application-level routing rules.
- YARP is commonly used as an **internal API gateway** or **ingress controller** — the single, HTTP-aware front door for a set of backend services within an organization's own environment, frequently sitting *behind* an edge/CDN layer and a lower-level load balancer, rather than replacing them.
- Because it's a library embedded in an ASP.NET Core app (Lecture 3 §17.1) rather than a fixed standalone binary, YARP is particularly well-suited to being *customized* for exactly this layer's needs — organizations frequently use it specifically because they need routing/auth/transform logic too specific or too integrated with their own .NET codebase for a generic off-the-shelf proxy product to express cleanly.

---

## 11. Common Misconceptions

- **"A load balancer and a reverse proxy are the same thing."** They overlap heavily but aren't identical — §6.2 frames load balancing as *one optional capability* a reverse proxy commonly provides, and §9.2 shows that some load balancers (especially at the edge/network tier) operate with much less HTTP awareness than a true reverse proxy like YARP does.
- **"A proxy just copies bytes through — it's basically transparent."** Directly contradicted by §6.1/§6.2 and Lecture 1 §15.2/Lecture 3 §17.2 — even a minimal proxy must make active decisions (routing) and manage two independent connections; most real deployments add substantially more active behavior on top.
- **"Forward vs. reverse proxy is about which side of a diagram it's drawn on."** §5's actual test is *whose interests it serves and whose identity it hides* — position alone is a heuristic, not the definition (though in practice they usually align).
- **"More proxy layers just means more latency for no benefit."** §9.2 shows each layer solves a genuinely distinct problem at a genuinely distinct scope — the added latency is a deliberate, bounded trade against independent scalability and replaceability, not accidental waste.
- **"Retries are always safe to add to a proxy."** Directly contradicted by Lecture 1 §4.4 and §6.2 here — retries interact with idempotency, and blind retries against non-idempotent operations can cause real harm (duplicate side effects).
- **"Route, cluster, and destination are just three names for the same concept."** §7.1 explains why they're deliberately separated — they change at different rates and answer different questions; collapsing them loses exactly the flexibility that separation buys.

---

## 12. Production Perspective: 10 → 10,000 → 1,000,000 → 100,000,000 Requests

**~10 requests, single backend**: a reverse proxy is barely distinguishable from "just calling the server directly" — routing is trivial (there's only one destination), load balancing is moot, health checking is unnecessary. You could reasonably skip having one at all.

**~10,000 requests, a handful of backend instances**: routing/cluster/destination separation (§7) starts earning its keep — instances are added/removed as you scale, and you want that to happen without touching routing configuration. Basic load balancing and health checking (§6.2) become genuinely necessary, not just nice-to-have.

**~1,000,000 requests, many services, many instances each**: the layered architecture from §9 becomes close to mandatory — a single reverse proxy tier handling everything (network-level distribution *and* HTTP-level routing *and* auth *and* rate limiting) becomes both a scaling bottleneck and an operational single point of failure. This is the scale where organizations typically formalize distinct edge / load-balancer / reverse-proxy tiers rather than improvising.

**~100,000,000 requests**: the reverse proxy tier itself needs to be horizontally scaled (many YARP instances, likely behind their own load balancer, forming a layer *within* §9.1's "Load Balancer → Reverse Proxy" step rather than being a single instance) — and every optional capability from §6.2 (retries, rate limiting, transforms) has to be implemented with the performance discipline from Lectures 1–3 (streaming, connection pooling, async I/O) or it becomes the bottleneck for the entire system, regardless of how well the actual backend services scale.

---

## 13. Failure Scenarios

This is where §6–§8's concepts become concretely operational — each scenario produces a *specific*, predictable proxy behavior, building directly on Lecture 2 §10's failure taxonomy.

### 13.1 Backend unavailable

The proxy attempts to open a connection to a destination and gets an immediate refusal (Lecture 2 §10.5's connection reset, or an outright "nothing listening there" failure) or can't reach it at all (Lecture 2 §10.1). The proxy's correct response: return `502 Bad Gateway` to the client (Lecture 1 §4.8) — explicitly the proxy speaking about *its own* failure to reach the backend, not something the backend itself ever said. A well-built proxy also feeds this failure into health checking (§6.2), so future requests route around this destination rather than repeating the same failed attempt.

### 13.2 Backend slow

The connection is fine (Lecture 2 §10.4's exact scenario — healthy connection, unresponsive application) but no response arrives within the proxy's configured timeout (Lecture 1 §10.3, Lecture 2 §10.4). The proxy's correct response: return `504 Gateway Timeout`. Critically, per Lecture 2 §10.4, TCP alone will never surface this — it requires the proxy's *own* explicit timeout, independent of whatever timeout the original client might have.

### 13.3 Client disconnects

Covered mechanically in §8 above and Lecture 2 §10.6 — the correct behavior is for the proxy to notice (via `HttpContext.RequestAborted`, Lecture 3 §9.4) and cancel the in-flight backend request, rather than completing pointless work for a response nobody will receive. A proxy that fails to do this wastes backend capacity proportional to how often clients disconnect early — which, at real scale, is a non-trivial, constant fraction of traffic (users closing tabs, mobile apps backgrounding, flaky connections).

### 13.4 Proxy overload

Unlike the previous scenarios, this is a failure *of the proxy itself*, not something happening on either connection leg — the proxy is receiving (or attempting to forward) more concurrent work than it can handle, and its own resources (thread pool, memory, connection pool limits from Lecture 2 §12) become the bottleneck. This is exactly why rate limiting (§6.2) exists as a *self-protective* capability, not just a backend-protective one — and it's part of why proxies are built with async I/O discipline (Lecture 3 §9) as a hard requirement rather than an optimization: a proxy that blocks threads waiting on I/O will hit its own capacity ceiling far earlier than one that doesn't.

### 13.5 Network failure

Could occur on either leg independently — Lecture 2 §10.1/§10.2's scenarios apply identically whether it's the client↔proxy leg or the proxy↔backend leg. The proxy has to correctly attribute which leg failed and respond appropriately: a client-leg network failure typically just means the response never gets delivered (nothing more the proxy can do — the client is unreachable); a backend-leg network failure should be translated into a `502`/`504` as in §13.1/§13.2.

### 13.6 Partial failure

The subtlest and most operationally important category: **some backend instances in a cluster are healthy, others aren't**, or **some requests succeed while others to the same destination fail intermittently**. This is where health checking (§6.2) and load balancing (§6.2, §7) work together as a system — the proxy shouldn't treat "one destination is unhealthy" as "the whole cluster/service is down." A well-designed proxy routes around known-bad destinations automatically, meaning the *client-visible* failure rate for the overall service stays low even while individual backend instances are actively failing — this is, in a real sense, one of the core value propositions of having a reverse proxy layer at all: it absorbs and hides partial failure that would otherwise be entirely the client's problem to handle.

---

## 14. Performance Implications

- **Keep routing/cluster/destination lookups cheap** (§7) — this logic runs on every single request, so it needs to be fast regardless of how large the routing table or destination set grows.
- **Never let optional capabilities (§6.2) defeat streaming** (§8, Lecture 1 §9) — a transform or auth check that requires fully buffering a body to inspect it should be a deliberate, understood trade-off, not an accident.
- **Timeouts and retries must be tuned together, not independently** — a retry policy that doesn't account for how long each attempt's timeout takes can make a single client-facing request take far longer than expected in the failure case (§13.1/§13.2 compounded by naive retries).
- **Rate limiting and self-protection (§13.4) should activate before the proxy's own resources are exhausted**, not after — by the time a proxy is visibly struggling, it's often too late for self-imposed limits to help; they need headroom to actually prevent the overload state, not just react to it.
- Deep performance tuning of the load-balancing algorithm's internals or edge-tier specifics (§9) is **not** where your effort belongs yet — those are genuinely separate specializations from what a reverse-proxy-layer engineer (YARP's actual audience) needs day to day.

---

## 15. YARP Connection — Its Conceptual Architecture, Before You Read the Source

This is the payoff of the entire series so far. Here is YARP's architecture, expressed entirely in terms you already have:

```
                                ┌─────────────────────────────────────────────┐
                                │              YARP (inside an                  │
                                │           ASP.NET Core app, Lec.3 §17)          │
                                │                                                │
   Client ── HTTP request ────►│  Kestrel (Lec.3 §4) parses into HttpContext     │
                                │       │                                        │
                                │       ▼                                        │
                                │  [ optional: your OWN middleware first,          │
                                │    Lec.3 §17.2 — auth, rate limiting, etc. ]        │
                                │       │                                        │
                                │       ▼                                        │
                                │  ROUTES  (§7 of this lecture)                    │
                                │  - matched via ASP.NET Core endpoint routing        │
                                │    (Lec.3 §10)                                     │
                                │  - each route points to exactly one CLUSTER          │
                                │       │                                        │
                                │       ▼                                        │
                                │  TRANSFORMS  (§6.2 of this lecture)              │
                                │  - header/path rewriting, applied here,             │
                                │    registered/extended via DI (Lec.3 §8.4)           │
                                │       │                                        │
                                │       ▼                                        │
                                │  CLUSTERS  (§7 of this lecture)                  │
                                │  - a named group of DESTINATIONS                    │
                                │  - holds load-balancing policy config (§6.2)          │
                                │  - holds health-check config (§6.2)                   │
                                │       │                                        │
                                │       ▼                                        │
                                │  LOAD BALANCING POLICY  (§6.2, §7)               │
                                │  - picks ONE destination from currently-              │
                                │    healthy candidates (health checking             │
                                │    filters the candidate set FIRST)                  │
                                │       │                                        │
                                │       ▼                                        │
                                │  FORWARDER  (the actual HTTP CLIENT role,         │
                                │              Lec.2 §15.1, Lec.3 §17.3)            │
                                │  - pooled HttpMessageInvoker per destination,       │
                                │    reused across requests (Lec.2 §6.5, §15.2)         │
                                │  - async I/O throughout (Lec.3 §9)                    │
                                │  - streams request/response bodies (Lec.1 §9)          │
                                │  - propagates cancellation via RequestAborted           │
                                │    (Lec.3 §9.4)                                        │
                                │  - translates connection-layer failures into            │
                                │    502/503/504 (§13 of this lecture)                    │
                                │       │                                        │
                                └───────┼────────────────────────────────────────┘
                                        ▼
                                     Backend
```

### 15.1 The vocabulary you should now recognize on sight

- **Route**: a match rule (path/host/headers/method) pointing to a cluster — the *policy* layer, changes rarely (§7.1).
- **Cluster**: a named, logical group of destinations, holding shared config like load-balancing policy and health-check settings — the *grouping* layer, stable identity even as membership changes (§7.1).
- **Destination**: one specific backend instance's address within a cluster — the *volatile* layer, changes constantly and automatically (§7.1).
- **Transform**: a deliberate modification applied to the request or response as it passes through (headers, path rewriting) — the extensibility mechanism for the "optional capabilities" from §6.2, registered through DI (Lecture 3 §8.4) so you can supply your own.
- **Load balancing policy**: the tie-breaker logic among currently-healthy destinations within a chosen cluster (§6.2, §7) — itself pluggable via DI, exactly like transforms.
- **Health check**: the mechanism that keeps the "currently healthy" candidate set accurate, so load balancing never routes to a known-bad destination (§6.2, §13.6).
- **Forwarder**: the component that actually plays the "HTTP client" half of YARP's dual role (Lecture 2 §15.1) — opens/reuses pooled connections, streams data, and translates failures into the appropriate status codes.

### 15.2 What you should now expect to see, structurally, when you open YARP's source

- Configuration types that map directly onto Routes/Clusters/Destinations, loaded through the standard `IConfiguration` system (Lecture 3 §11.2).
- DI registration extension methods (`AddReverseProxy()`, `MapReverseProxy()`) mirroring Lecture 3 §17.2's registration/pipeline split exactly.
- Extensibility points expressed as interfaces you can implement and register via DI (custom load-balancing policies, custom transforms) — not configuration flags, but genuine pluggable C# types, exactly matching Lecture 3 §8.4's explanation of *why* infrastructure software leans on DI so heavily.
- Heavy, deliberate use of `async`/`await` and streaming APIs throughout the forwarding path (Lecture 3 §9, Lecture 1 §9) — if you see something that looks like it's buffering a whole body into memory, that should now read to you as a deliberate, notable exception, not the default expectation.
- Explicit `CancellationToken` threading throughout the forwarding call chain (Lecture 3 §9.4), tied to `HttpContext.RequestAborted`.
- Status-code-generating logic specifically for connection-layer failures (§13.1–§13.2) that is clearly distinct from "relay whatever the backend said" logic.

You now have the conceptual map. The remainder of learning YARP from here is filling in specific implementation details onto a structure that should already feel expected, not filling in an entirely unfamiliar shape.

---

## 16. What I Don't Need to Know Yet

- The specific set of built-in load-balancing algorithms YARP ships (round-robin, least-requests, power-of-two-choices, etc.) and their individual trade-offs — recognize that this is a pluggable policy (§15.1); specific algorithm comparison is natural material for a dedicated future lecture once you're customizing YARP directly.
- Session affinity (routing a given client's requests consistently to the same backend instance) — a real, common capability, but an extension of §7's model rather than a new concept; safe to defer.
- The exact transform pipeline API surface (which specific interfaces/methods to implement for a custom transform) — §15.1's conceptual role is sufficient until you're actually writing one.
- Active vs. passive health checking implementation details — recognize both exist (§6.2, §13.6); the specific mechanics are implementation detail, not architecture.
- YARP's specific configuration reload mechanism (how it watches `appsettings.json` for changes without a restart) — a natural extension of Lecture 3 §11.2, but its specific implementation isn't required to understand the architecture.
- Direct comparison against other reverse proxy products (nginx, Envoy, Traefik, cloud-native ingress controllers) — useful context eventually, not required for understanding YARP itself.

---

## 17. Knowledge Check

1. A colleague describes their company's corporate web filter (all outbound employee traffic passes through it before reaching any external website) as "a reverse proxy." Using §5's actual test (whose interests, whose identity hidden), explain why this is a forward proxy, not a reverse proxy.
2. Using §6.1 vs §6.2, explain why a reverse proxy that does absolutely nothing but relay bytes to a single fixed backend is still, technically, doing "routing" — and why that routing decision only becomes operationally interesting once a second backend exists.
3. Using §7.1, explain what would go wrong (in terms of operational friction) if YARP collapsed routes, clusters, and destinations into a single flat concept — "each route directly lists specific backend IP addresses" — instead of the three-layer model.
4. A backend instance is intermittently timing out under load, but three other instances in the same cluster are healthy. Using §13.6, explain what a well-built reverse proxy should do, and contrast that with what would happen if the proxy had no health-checking capability at all.
5. Using §13.2 and Lecture 2 §10.4, explain precisely why a `504 Gateway Timeout` can only be generated by the proxy actively giving up — not by anything TCP itself detects or reports.
6. Using §15's diagram, trace what happens, stage by stage, when a client sends `GET /v1/users/42` to a YARP instance configured with one route matching `/v1/users/{**catch-all}` pointing at a cluster with two healthy destinations — name each stage in order and what decision it makes.

---

## 18. Practical Exercise

Build a minimal, real YARP proxy locally, in front of two backend instances you also run locally — this makes routes/clusters/destinations, load balancing, and failure behavior (§13) directly observable rather than theoretical.

### Step 1 — Two trivial backend instances

```bash
mkdir -p ~/yarp-lecture-demo/backend && cd ~/yarp-lecture-demo/backend
dotnet new web
```

Replace `Program.cs`:
```csharp
var builder = WebApplication.CreateBuilder(args);
var app = builder.Build();
var port = app.Configuration["urls"] ?? "unknown";

app.MapGet("/v1/users/{id}", (int id) =>
    Results.Json(new { id, servedBy = port }));

app.Run();
```

Run two instances, on two different ports, in two terminals:
```bash
dotnet run --urls http://localhost:5001
dotnet run --urls http://localhost:5002
```

### Step 2 — A minimal YARP proxy

```bash
cd ~/yarp-lecture-demo
dotnet new web -o proxy && cd proxy
dotnet add package Yarp.ReverseProxy
```

`appsettings.json` — this is §7.2's example, made real:
```json
{
  "ReverseProxy": {
    "Routes": {
      "usersRoute": {
        "ClusterId": "userServiceCluster",
        "Match": { "Path": "/v1/users/{**catch-all}" }
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

`Program.cs`:
```csharp
var builder = WebApplication.CreateBuilder(args);
builder.Services.AddReverseProxy()
    .LoadFromConfig(builder.Configuration.GetSection("ReverseProxy"));

var app = builder.Build();
app.MapReverseProxy();
app.Run();
```

Run it: `dotnet run --urls http://localhost:5000`

### Step 3 — Observe §7's request flow directly

```bash
curl http://localhost:5000/v1/users/42
curl http://localhost:5000/v1/users/42
curl http://localhost:5000/v1/users/42
curl http://localhost:5000/v1/users/42
```

Watch the `servedBy` field alternate between `5001` and `5002` — that's round-robin load balancing (§6.2, §7) happening in front of your eyes, across the exact route → cluster → destination chain from §7's diagram.

### Step 4 — Observe §13.1's failure behavior directly

Stop instance `5002` (Ctrl+C in its terminal), then repeat the `curl` loop from Step 3. You should now see requests routed to `5002` fail — try it *without* health checking configured first (as above) and notice the proxy still attempts `5002` and the request fails end-to-end. Then, as an optional extension, add:
```json
"HealthCheck": {
  "Active": { "Enabled": true, "Interval": "00:00:05", "Path": "/v1/users/1" }
}
```
under `userServiceCluster`, restart the proxy, stop `5002` again, wait ~10 seconds, and repeat the `curl` loop — now every request should succeed, consistently landing on `5001`, because the proxy has stopped considering `5002` a valid destination at all. That transition — from "the proxy blindly tries a dead destination and fails" to "the proxy routes around it automatically" — *is* §13.6's partial-failure resilience, made concrete.

---

## 19. "Ready to Move On" Criteria

You've now completed the foundational arc of this series. Before considering yourself ready to read YARP's actual source code productively, you should be able to explain — out loud, in your own words:

- [ ] Why a reverse proxy exists, stated as "problems it solves," not just "features it has."
- [ ] The forward vs. reverse proxy distinction, using the "whose interests / whose identity" test rather than diagram position.
- [ ] Which reverse proxy responsibilities are structurally required vs. commonly-bundled-but-optional, and why that distinction is useful.
- [ ] The route → cluster → destination chain, what question each stage answers, and why they're kept separate rather than collapsed.
- [ ] How a proxy handles headers, bodies, streaming, status codes, and cancellation — as direct applications of Lectures 1–3, not new mechanisms.
- [ ] Why production systems use multiple layers of proxies/load balancers rather than one, and what distinct problem each layer solves.
- [ ] The specific, different proxy behavior for each failure scenario in §13 — unavailable, slow, disconnected client, overloaded proxy, network failure, partial failure — and why each produces a *different* observable outcome.
- [ ] YARP's conceptual architecture (routes, clusters, destinations, transforms, load balancing, health checks, forwarder) well enough to predict, before looking, roughly where in the source a given piece of behavior probably lives.

If you can do all of that, you're at the point this whole series was built toward: you can open YARP's actual codebase and reasonably expect to recognize *why* things are shaped the way they are, rather than pattern-matching on unfamiliar class names.
