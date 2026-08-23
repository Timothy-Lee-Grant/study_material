# Lecture 12: YARP Architecture — Putting Everything Together

Series: YARP Learning Series (capstone)
Builds on: the entire series — [Lecture 1](001-http_from_the_wire_to_the_application.md) through [Lecture 11](011-performance_engineering_for_high_throughput_services.md).
Source of truth: this lecture's directory layout, class names, and contribution guidance were verified directly against the live `dotnet/yarp` GitHub repository (source tree, `CONTRIBUTING.md`, live issue labels) rather than reconstructed from memory — where something is time-sensitive (e.g., which issues are currently labeled `good first issue`), this lecture says so explicitly rather than presenting it as fixed fact.

---

## 1. Learning Objectives

By the end of this lecture you should be able to:

1. Explain the Client → YARP → Route → Cluster → Destination → Backend chain precisely, in terms you've built up across this entire series.
2. Trace a single request through YARP's actual subsystems, naming which real component handles each of the ten lifecycle stages.
3. For each of YARP's major components, state what problem it solves, why it's a separate component, and what it receives from and hands to its neighbors.
4. Explain how YARP represents routes, clusters, destinations, transforms, and load-balancing policies in actual configuration.
5. Explain which of YARP's design decisions exist specifically because it's built for high-throughput proxying, and connect each one to a specific earlier lecture.
6. Clone the real repository, build it, run its test suite, and navigate its source with a concrete strategy — not memorization.
7. Identify a first-contribution category appropriate to your current background, and explain why a large architectural change would be the wrong place to start.

---

## 2. Prerequisite Concepts

This lecture assumes the entire series so far. Rather than list every dependency, here's the honest test: if you can explain, without looking back, why a reverse proxy is simultaneously an HTTP server and an HTTP client (Lecture 2 §15.1), why route/cluster/destination are three separate concepts changing at three different rates (Lecture 5 §7.1), why health filtering happens *before* load balancing (Lecture 6 §14.5), and why streaming beats buffering at concurrency scale (Lecture 7 §8), you're ready for this lecture to click into place rather than feel like new information.

---

## 3. Core Mental Model — The Big Picture

```
   Client
     │
     ▼
   YARP
     │
     ▼
   Route          "which rule matches this request?"          (Lecture 5)
     │
     ▼
   Cluster        "which named group of backends handles it?"  (Lecture 5 §6)
     │
     ▼
   Destination    "which SPECIFIC instance, right now?"         (Lecture 6)
     │
     ▼
   Backend
```

Precisely, in terms you already have:

- **Route** — a match rule (path/host/method/headers, Lecture 5 §4) plus a reference to exactly one cluster, plus any transforms to apply (Lecture 4 §15.1). Represented in configuration as `RouteConfig`.
- **Cluster** — a stable, named logical group of destinations, holding shared policy: which load-balancing algorithm (Lecture 6 §5), which health-check settings (Lecture 6 §6). Represented as `ClusterConfig`.
- **Destination** — one specific backend address, and its current live health state — the volatile layer, changing constantly (Lecture 5 §6). Represented as `DestinationConfig`.
- **Backend** — the actual service YARP forwards to, entirely outside YARP's own process.

This chain is not a simplification for teaching purposes — it's the literal shape of YARP's configuration model, verified directly against the source. The rest of this lecture fills in exactly how each arrow in that diagram is actually implemented.

---

## 4. Request Lifecycle — Ten Stages, Named Against Real Components

```
 1. Client connection      Kestrel accepts a TCP/QUIC connection            (Lecture 2 §7.3, Lecture 3 §4)
 2. HTTP request           Kestrel parses bytes into HttpContext            (Lecture 1 §4.3, Lecture 3 §6)
 3. ASP.NET Core pipeline  Your own middleware runs first, if any           (Lecture 3 §7, Lecture 4 §17.2)
 4. Route matching         ASP.NET Core's endpoint matcher, against          (Lecture 3 §10, Lecture 5 §5.2)
                            endpoints YARP built from RouteModel
 5. Cluster selection      The matched route's ClusterState is resolved      (Lecture 5 §6)
 6. Destination selection  LoadBalancingMiddleware: filter to healthy,        (Lecture 6 §14.5)
                            then apply the cluster's ILoadBalancingPolicy
 7. Outgoing request       ForwarderMiddleware → HttpForwarder.SendAsync,     (Lecture 2 §15, Lecture 7 §5)
                            via a pooled HttpMessageInvoker
 8. Backend response       Received on the pooled connection                  (Lecture 2 §10, Lecture 4 §13)
 9. Response processing    HttpTransformer applies response transforms;       (Lecture 4 §15.2, Lecture 6 §6.3)
                            PassiveHealthCheckMiddleware observes the outcome
10. Client response        Streamed back onto HttpContext.Response,           (Lecture 1 §9, Lecture 3 §7.1)
                            unwinding back up through any earlier middleware
```

Walking through this once, narratively, ties every earlier lecture together at once: Kestrel (stages 1–2) is doing exactly the accept-loop-plus-HTTP-parsing job Lecture 2 §7.3 and Lecture 3 §4 taught you it does, with zero YARP involvement yet. Stage 3 is Lecture 3's middleware pipeline, and — per Lecture 4 §17.2 — anything you register *before* `MapReverseProxy()` can short-circuit the request before YARP ever sees it. Stage 4 is Lecture 5's entire thesis made concrete: YARP doesn't reimplement matching, it constructs real ASP.NET Core `Endpoint` objects (via `ProxyEndpointFactory`) from its own `RouteModel`, and hands matching to the framework's own optimized engine. Stages 5–6 are Lecture 5 §7 and Lecture 6 §14.5's two-step "resolve the stable cluster, then pick a volatile destination from the currently-healthy subset" sequence, now with real class names: `LoadBalancingMiddleware` does the filtering-then-picking. Stage 7 is Lecture 2 §15's dual-role point made literal — YARP becomes an HTTP *client* here, via `HttpForwarder.SendAsync`, over a connection pooled per Lecture 7 §5. Stages 8–9 are Lecture 4 §13's failure-translation logic and Lecture 6 §6.3's passive health detection, both operating on the same response. Stage 10 is Lecture 1 §9's streaming principle and Lecture 3 §7.1's "way up" unwind, closing the loop back to the client.

---

## 5. Architecture — Major Components

For each component below: what problem it solves, why it's separate, what it receives, what it produces, and what it talks to. Folder names are verified exactly as they appear under `src/ReverseProxy/`.

### 5.1 Configuration/

**Problem solved**: represent what the operator *wrote* — routes, clusters, destinations, as plain, static, serializable DTOs. **Why separate**: this is deliberately just data, with no live behavior attached — exactly Lecture 5 §13.1's `RouteConfig`/`ClusterConfig`/`DestinationConfig`, now confirmed as the real names. **Receives**: raw config from an `IProxyConfigProvider` (commonly bound from `appsettings.json` via `LoadFromConfig(IConfiguration)`, Lecture 3 §11.2). **Produces**: validated `IProxyConfig` snapshots, via `ConfigValidator` — including a hook, `IProxyConfigFilter`, letting you programmatically inspect or mutate configuration after it's loaded but before it takes effect (a real, DI-registered extensibility point, per Lecture 3 §8.4). **Interacts with**: the Model layer (§5.2), which builds the live, matchable structures *from* these DTOs.

### 5.2 Model/

**Problem solved**: hold the *built, ready-to-use* runtime representation — `RouteModel`/`RouteState`, `ClusterModel`/`ClusterState`, `DestinationModel`/`DestinationState` — distinct from Configuration/'s static DTOs. **Why separate**: this is exactly Lecture 5 §5.2–§5.3's build-once-reuse-many-times pattern, and exactly Lecture 5 §13.2's prediction, now fully confirmed by the actual source layout. **Receives**: validated config snapshots from §5.1, rebuilt via the atomic-swap sequence from Lecture 5 §7.2 whenever configuration changes. **Produces**: the structures every other subsystem actually reads on the hot per-request path — including live health state (`DestinationHealth`, `DestinationHealthState`) and `ClusterDestinationsState`, tracked here specifically because health changes far more often than configuration does (Lecture 6 §14.3's exact prediction). **Interacts with**: Routing (§5.3, which builds ASP.NET Core endpoints from `RouteModel`) and LoadBalancing/Health (§5.4–§5.5, which read `ClusterState`/`DestinationState` on every request).

### 5.3 Routing/

**Problem solved**: turn `RouteModel` entries into real, matchable ASP.NET Core endpoints. **Why separate**: so matching itself (Lecture 3 §10.1, Lecture 5 §5.2) is delegated entirely to the framework's own already-optimized routing engine — YARP's job here is only *construction*, not matching logic. **Receives**: `RouteModel` from §5.2. **Produces**: registered `Endpoint` objects (via `ProxyEndpointFactory`), reachable through `MapReverseProxy()` (`ReverseProxyIEndpointRouteBuilderExtensions`, with a `ReverseProxyConventionBuilder` for further customization). Route-specific matching beyond plain path/method — header and query-parameter matching (Lecture 5 §4.3–§4.4) — is implemented as `HeaderMatcherPolicy`/`QueryParameterMatcherPolicy`, plugging directly into ASP.NET Core's own endpoint-matching extensibility, rather than YARP inventing a parallel matching system. **Worth knowing**: a separate, lower-level `DirectForwardingIEndpointRouteBuilderExtensions` API also exists, letting you use `IHttpForwarder` directly against a single fixed destination, entirely bypassing the route/cluster/config model — useful when you want YARP's forwarding mechanics without its full routing layer (the `ReverseProxy.Direct.Sample` demonstrates exactly this). **Interacts with**: the standard ASP.NET Core middleware pipeline (Lecture 3 §7), and LoadBalancing/Forwarder once a route has matched.

### 5.4 LoadBalancing/

**Problem solved**: pick one destination from a cluster's currently-healthy candidates. **Why separate**: exactly Lecture 6's entire thesis — a swappable policy, independent of routing and independent of health tracking. **Receives**: a `ClusterState` and its already-health-filtered destination candidates (from §5.5's filtering step, run first — confirming Lecture 6 §14.5's predicted two-step shape exactly). **Produces**: one chosen `DestinationState`. **The five real policies**, matching Lecture 6 §5 precisely: `RoundRobinLoadBalancingPolicy`, `RandomLoadBalancingPolicy`, `LeastRequestsLoadBalancingPolicy`, `PowerOfTwoChoicesLoadBalancingPolicy` (Lecture 6 §14.2's prediction, confirmed as a real, named policy — not just a conceptual mention), and `FirstLoadBalancingPolicy` (always the first available destination — a simple, deterministic option not covered explicitly in Lecture 6, useful when you specifically want a primary/fallback shape rather than distribution). All run inside `LoadBalancingMiddleware`. **Interacts with**: Health/ (§5.5, upstream of it in the pipeline) and Forwarder/ (§5.6, downstream — receives the chosen destination).

### 5.5 Health/

**Problem solved**: track which destinations are currently usable, via both active and passive checking (Lecture 6 §6). **Why separate**: health state changes continuously and independently of both configuration and routing decisions (Lecture 5 §6, Lecture 6 §14.3). **Receives**: active probe results (`ActiveHealthCheckMonitor` + `IActiveHealthCheckPolicy`, with `DefaultProbingRequestFactory` building the actual probe requests) and passive observations of real traffic (`PassiveHealthCheckMiddleware` + `IPassiveHealthCheckPolicy`). **Two concrete built-in passive policies worth naming**: `ConsecutiveFailuresHealthPolicy` (mark unhealthy after N failures in a row) and `TransportFailureRateHealthPolicy` (mark unhealthy once the failure *rate* over a window crosses a threshold — a subtly different, often more robust signal than a raw consecutive count). **Produces**: updated health state via `IDestinationHealthUpdater`/`IClusterDestinationsUpdater`, feeding directly into §5.2's `DestinationHealthState`. **A genuinely interesting detail**: candidate filtering itself is pluggable too, via `IAvailableDestinationsPolicy` — the default, `HealthyAndUnknownDestinationsPolicy`, includes destinations whose health simply hasn't been determined yet (not yet probed) alongside confirmed-healthy ones, while `HealthyOrPanicDestinationsPolicy` implements a deliberate fallback: if *literally every* destination in a cluster is currently unhealthy, it falls back to routing to them anyway rather than failing every request outright — a direct, concrete instance of Lecture 8 §9.3's "fail closed vs. fail open" tension, resolved here as a configurable policy choice rather than a fixed answer. **Interacts with**: Model/ (writes health state there) and LoadBalancing/ (reads the filtered candidate set from there).

### 5.6 Forwarder/

**Problem solved**: actually send the request to the chosen destination and relay the response — the literal "become an HTTP client" half of Lecture 2 §15.1's dual role. **Why separate**: this is genuinely a distinct concern from *deciding* where to send a request (§5.3–§5.5) — worth noting `IHttpForwarder` is usable entirely standalone, without any routing/cluster machinery at all (§5.3's `DirectForwardingIEndpointRouteBuilderExtensions`, and the `ReverseProxy.Direct.Sample`), which is strong, direct evidence of how cleanly this separation was actually achieved. **Receives**: an `HttpContext` and a chosen destination address, via `ForwarderMiddleware`. **Produces**: the outbound request (built and sent via `HttpForwarder.SendAsync`), and the relayed response written back onto that same `HttpContext`. **A detail worth flagging for Lecture 11's "recognize hot-path code" checklist**: `SendAsync` returns `ValueTask<ForwarderError>`, not `Task`, and communicates proxy-level failure via that returned enum rather than throwing an exception for expected failure modes (a destination being unreachable is an *expected*, routine outcome for a forwarder, not an exceptional one) — a deliberate, hot-path-appropriate performance choice, exactly the kind of signal Lecture 11 §15.2 told you to look for. **Body copying** is handled by `StreamCopier`/`StreamCopyHttpContent`/`StreamCopyResult` — streaming, not buffering, per Lecture 1 §9 and Lecture 4 §15.2. **Header/path/response rewriting** is delegated to `HttpTransformer` (§5.7). **Interacts with**: `IForwarderHttpClientFactory` (§5.8, for the actual pooled connection) and Transforms/ (§5.7).

### 5.7 Transforms/

**Problem solved**: modify the outbound request or inbound response in flight — headers, path, query string — exactly Lecture 4 §6.2's "commonly bundled but optional" capability. **Why separate**: transforms are configured per-route (Lecture 5 §13.1's `RouteConfig`) and are meant to be extensible — `ITransformProvider`/`ITransformFactory` are real, DI-registerable extension points (Lecture 3 §8.4). **Receives**: `RequestTransformContext` (carrying the in-flight request state). **Produces**: a modified outbound request / response. **Confirmed, named, built-in transforms worth recognizing**: `RequestHeaderXForwardedForTransform`, `RequestHeaderXForwardedHostTransform`, `RequestHeaderXForwardedProtoTransform`, `RequestHeaderXForwardedPrefixTransform` — these are the literal implementation of the `X-Forwarded-*` header mechanics Lecture 4 §15.2 described conceptually, now confirmed as first-class, individually named classes, not an ad hoc detail buried in the forwarder. Also `PathStringTransform`, `QueryParameterTransform`, `ResponseHeaderValueTransform`, and `RequestHeaderClientCertTransform` (forwarding client TLS certificate info — relevant to Lecture 2 §2.4's TLS-termination point, when a backend needs to know about a client cert the proxy terminated). **Interacts with**: Forwarder/ (§5.6), which invokes transforms via `HttpTransformer` at the appropriate point in the request/response journey.

### 5.8 Management/

**Problem solved**: the DI wiring that ties every other component together. **Why separate**: this is precisely Lecture 3 §5's registration phase, concentrated in one place — `ReverseProxyServiceCollectionExtensions` is where `AddReverseProxy()`, `LoadFromConfig(IConfiguration)`, `AddTransforms(...)`, `AddTransformFactory<T>()`, `ConfigureHttpClient(...)`, `AddConfigFilter<T>()`, and `AddDnsDestinationResolver(...)` all live, returning a chainable `IReverseProxyBuilder` — the literal DI-based extensibility mechanism Lecture 3 §8.4 and Lecture 4 §17.2 predicted, now with real method names. **Interacts with**: every other component, as the composition root.

### 5.9 Additional subsystems worth recognizing on sight

- **ServiceDiscovery/** — includes a DNS-based destination resolver (`AddDnsDestinationResolver`), a real, concrete implementation of Lecture 9 §12.2's "DNS-based service discovery" concept — confirming destinations don't have to be static configuration entries at all.
- **SessionAffinity/** — a real, present subsystem (not vaporware) implementing the session-affinity mechanism deliberately deferred across Lectures 4, 5, and 6 — routing a given client consistently back to the same destination.
- **Delegation/** — Http.sys kernel-mode queue delegation, a more advanced, niche performance feature (handing off a request at the OS level, below even Kestrel) — recognize the name, no depth needed yet.
- **Limits/** — rate/concurrency limiting, directly Lecture 4 §6.2 and Lecture 7 §7's backpressure/self-protection concerns, given a dedicated home.
- **WebSocketsTelemetry/** — observability specifically for proxied WebSocket connections, a protocol this series hasn't covered in depth (recognize the name; WebSockets were explicitly deferred back in Lecture 1 §16).

---

## 6. Configuration — How Routes, Clusters, Destinations, Transforms, and Policies Are Represented

```json
{
  "ReverseProxy": {
    "Routes": {
      "usersRoute": {
        "ClusterId": "userServiceCluster",
        "Match": { "Path": "/v1/users/{**catch-all}" },
        "Transforms": [ { "RequestHeader": "X-Custom", "Set": "value" } ]
      }
    },
    "Clusters": {
      "userServiceCluster": {
        "LoadBalancingPolicy": "LeastRequests",
        "HealthCheck": {
          "Active": { "Enabled": true, "Interval": "00:00:10", "Path": "/health" },
          "Passive": { "Enabled": true }
        },
        "Destinations": {
          "instance1": { "Address": "http://10.0.4.11:5000" }
        }
      }
    }
  }
}
```

This is exactly Lecture 5 §7.2's example, now grounded in real, verified type names: this JSON is bound to `RouteConfig`/`ClusterConfig`/`DestinationConfig` (§5.1) via `LoadFromConfig(builder.Configuration.GetSection("ReverseProxy"))`, validated by `ConfigValidator`, and rebuilt into `RouteModel`/`ClusterModel`/`DestinationModel` (§5.2) on every config change, via the atomic-swap mechanism Lecture 5 §7.2 taught in the abstract. `LoadBalancingPolicy` and the `HealthCheck` block map directly onto §5.4–§5.5's named policies. Configuration doesn't have to come from `appsettings.json` at all — any `IProxyConfigProvider` works, including `InMemoryConfigProvider` (useful for tests, or for a fully code-driven setup — the `ReverseProxy.Code.Sample` demonstrates exactly this) or a custom provider backed by a service registry (Lecture 9 §12.3).

---

## 7. Routing Architecture

Covered in full in §5.3 — the key fact worth restating plainly here, since it's the single most important architectural fact in the entire system: **YARP does not have its own route-matching engine.** It builds real ASP.NET Core `Endpoint` objects from `RouteModel`, and hands matching entirely to the framework (Lecture 3 §10.1). This is precisely why Lecture 5's whole treatment of endpoint routing as a prerequisite wasn't incidental — it's a direct, load-bearing dependency.

---

## 8. Load Balancing — Destination Selection

Also covered in §5.4–§5.5 — the sequence worth memorizing as one unit, since it's the literal, verified shape of `LoadBalancingMiddleware`'s job: **filter the cluster's destinations to the currently-healthy (or "unknown," or, in panic mode, all-of-them) candidate set, via a configurable `IAvailableDestinationsPolicy` — then apply the cluster's configured `ILoadBalancingPolicy` to that filtered set.** Five built-in policies (§5.4) cover the algorithms Lecture 6 taught, plus the simple deterministic `First` option.

---

## 9. HTTP Forwarding

Covered in §5.6. The three things worth carrying forward as a single mental unit: `IHttpForwarder.SendAsync` is usable standalone (proof of clean separation), returns `ValueTask<ForwarderError>` rather than throwing for expected failures (a deliberate hot-path performance choice), and delegates body copying to `StreamCopier` (streaming, per Lecture 1 §9) and header/path rewriting to `HttpTransformer` (§5.7).

---

## 10. Connection Management

`IForwarderHttpClientFactory`/`ForwarderHttpClientFactory` is where Lecture 2 §15.2 and Lecture 7 §5's entire pooling story lives concretely — building and caching a pooled `HttpMessageInvoker` per cluster, configurable via `HttpClientConfig` (and `WebProxyConfig`, for scenarios where YARP itself needs to reach a backend through *another* upstream proxy — a real, supported, if niche, configuration knob). This is the component directly responsible for avoiding Lecture 2 §5.3's ephemeral-port-exhaustion risk and Lecture 2 §6.5's cold-connection slow-start cost, exactly as Lecture 4 §15.2 predicted before you'd seen a single real class name.

---

## 11. Resilience

Health/ (§5.5) is YARP's primary built-in resilience mechanism — active and passive detection, feeding destination selection, exactly Lecture 8's health-checking material. `ForwarderError`'s distinct failure categories are what let YARP translate connection-layer failures into the correct HTTP status codes from Lecture 4 §13 (unreachable → 502, timeout → 504, no healthy destinations → 503, the last of these directly shaped by §5.5's `IAvailableDestinationsPolicy` choice). Worth being precise and honest about scope here, echoing Lecture 8 §7.3's distinction: YARP's built-in resilience centers on **health-checking and load-balancing**, not a full per-call circuit-breaker state machine (Lecture 8 §7.2) — if your specific scenario needs that additional layer, it's the kind of thing you'd add via YARP's extensibility points (custom transforms, a custom `IProxyConfigFilter`, or wrapping the forwarder call) rather than expecting it out of the box. This is a direct, concrete instance of the CONTRIBUTING.md philosophy §13 covers below: YARP's own maintainers explicitly prefer extensibility over expanding core behavior for exactly this kind of additional-layer concern.

---

## 12. Observability

`ForwarderTelemetry`/`ForwarderStage` provide built-in, structured telemetry for the forwarding pipeline's stages — a direct, concrete implementation of Lecture 10's metrics/tracing story. `ReverseProxyPropagator` handles trace-context propagation specifically — confirmed as a real, named component implementing exactly Lecture 10 §9.3's "trace ID automatically attached to the outbound request" mechanism, so a trace touching a YARP-fronted service correctly connects the client-facing span to the backend-facing one without any manual wiring. The `ReverseProxy.Metrics.Sample` and `Prometheus` samples (§14) demonstrate this concretely, end to end.

---

## 13. Performance — Which Decisions Exist Because of Scale

Pulling together everything §5–§12 already surfaced, through Lecture 11's lens specifically:

- **`ValueTask<ForwarderError>` instead of exceptions for expected failures** (§5.6) — avoiding exception overhead on a hot path handling routine, expected outcomes, exactly Lecture 11 §15.2's "no blocking calls, deliberate control flow" signal, generalized to "deliberate error-handling shape" as well.
- **The Model/ vs. Configuration/ split** (§5.2) — Lecture 5 §5.2–§5.3's build-once-reuse-many-times pattern, now confirmed as a real architectural boundary, not just a teaching simplification.
- **Streaming via `StreamCopier`, not buffering** (§5.6) — Lecture 1 §9 and Lecture 7 §8's memory-at-concurrency-scale argument, implemented directly.
- **Pooled `HttpMessageInvoker` via `IForwarderHttpClientFactory`** (§10) — Lecture 2 §15.2 and Lecture 7 §5's connection-reuse imperative, implemented directly.
- **Delegating route matching to ASP.NET Core's own engine** (§5.3, §7) — avoiding a second, redundant matching implementation, and inheriting the framework's own already-optimized performance characteristics (Lecture 5 §5.2).
- **Health filtering as a genuinely separate, pluggable step before load balancing** (§5.5, §8) — keeping the hot-path selection logic simple and fast, with health-state bookkeeping (the more complex, continuously-updated part) isolated in its own subsystem.

---

## 14. Source-Code Orientation — A Strategy, Not a Memorization Task

### 14.1 Top-level layout

```
dotnet/yarp/
├── src/            product source — ReverseProxy is the core library (see §5)
├── test/           tests — mirrors src/ReverseProxy/'s folder structure almost exactly
├── testassets/      small helper apps used BY tests
├── samples/         14 standalone runnable sample apps (see §14.4)
├── docs/            design notes + ops docs — NOT user/getting-started documentation
├── eng/             build engineering infra — skip this as a newcomer
├── README.md, CONTRIBUTING.md, CODE_OF_CONDUCT.md, SECURITY.md
├── YARP.slnx        the solution file (the newer .slnx format, not classic .sln)
└── global.json      pins the exact .NET SDK version used to build
```

### 14.2 Where the real user documentation actually lives

Worth knowing before you go looking for it: **there is no in-repo getting-started guide.** `docs/README.md` explicitly points to the public documentation at `learn.microsoft.com/aspnet/core/fundamentals/servers/yarp` — the in-repo `docs/` folder contains only `designs/` (design rationale — `config.md`, `route-extensibility.md`, and others, explaining *why* certain patterns were chosen, not how to use them) and `operations/` (release/branching process, not relevant to reading code). There is no single `ARCHITECTURE.md` — the source layout itself, exactly as this lecture has walked through it, *is* the map.

### 14.3 A concrete reading order

1. **`README.md`** — orientation, links to the real docs site.
2. **`samples/BasicYarpSample`** — the smallest possible working example; its `Program.cs` is essentially `AddReverseProxy().LoadFromConfig(...)` + `MapReverseProxy()`, confirming the shape Lecture 4 §18 already had you build by hand.
3. **`docs/designs/config.md` and `docs/designs/route-extensibility.md`** — the closest thing to a written architecture rationale that exists.
4. **`src/ReverseProxy/Configuration/` then `Model/`** — see the DTO-vs-built-representation split from §5.1–§5.2 with your own eyes.
5. **`src/ReverseProxy/Routing/` then `LoadBalancing/` then `Health/`** — follow §4's stages 4–6 in source.
6. **`src/ReverseProxy/Forwarder/`** — stages 7–9, the HTTP-client half of the proxy.
7. **`src/ReverseProxy/Transforms/`** — once the core pipeline makes sense, see how it's extended.

### 14.4 Where tests live, and a genuinely useful navigation trick

`test/ReverseProxy.Tests/` mirrors `src/ReverseProxy/`'s folder structure almost exactly — `Configuration`, `Forwarder`, `Health`, `LoadBalancing`, `Model`, `Routing`, `Transforms`, and so on, each corresponding directly to the source folder of the same name. **This means: if you're reading a specific source file and want to see how its authors expected it to behave — including edge cases — go look at the test file in the same relative path under `test/ReverseProxy.Tests/`.** `test/ReverseProxy.FunctionalTests/` holds separate, end-to-end-style tests exercising the full pipeline rather than one component in isolation — worth reading *after* you've understood a component in isolation, to see how it behaves as part of the whole system.

### 14.5 Where samples live

`samples/` holds 14 standalone apps, each demonstrating one specific thing — beyond `BasicYarpSample` (§14.3), worth knowing: `ReverseProxy.Config.Sample` (every config option in one place), `ReverseProxy.Direct.Sample` (uses `IHttpForwarder` directly, bypassing routing entirely — §5.3, §5.6's separation, demonstrated live), `ReverseProxy.Transforms.Sample`, `ReverseProxy.Code.Sample` (custom config provider and custom middleware, exercising the extensibility points from §5.1 and §5.8), `ReverseProxy.Metrics.Sample` and `Prometheus` (§12's observability story, end to end). **One caveat worth knowing before you go looking**: the samples in the `main` branch track unreleased, in-development code, not the latest published NuGet package — if you install YARP via NuGet, check out the matching `release/latest`-style branch to see samples that actually match what you installed.

### 14.6 Build and test — the actual commands

The SDK version is pinned via `global.json` — you do **not** need that exact SDK installed globally; the repo's own restore step fetches it locally.

```bash
# simplest path — builds the whole solution, fetching the pinned SDK automatically
./build.sh          # or build.cmd on Windows

# build AND run the full test suite
./build.sh -test    # or build.cmd -test

# alternative: restore first, "activate" the local SDK onto PATH for this shell session,
# then use dotnet normally
./restore.sh
source ./activate.sh   # (or . ./activate.ps1)
dotnet build YARP.slnx
dotnet test

# run one specific test method
dotnet build /t:Test /p:XunitMethodName=Yarp.ReverseProxy.SomeNamespace.SomeClassTests.SomeMethod
```

Note the solution file is `YARP.slnx` — the newer XML-based solution format, not the classic `.sln` you may be used to; it works with `dotnet build`/`dotnet test` the same way.

### 14.7 How to trace a request through the code yourself, concretely

Start at `ReverseProxyIEndpointRouteBuilderExtensions.MapReverseProxy` (Routing/) — this is where a request "enters" YARP's own code, after Kestrel and your own middleware (§4, stages 1–3) have already run. From there, follow the call chain forward exactly as §4 laid it out: `ProxyEndpointFactory` (how the matched endpoint was built) → `LoadBalancingMiddleware` (destination selection) → `ForwarderMiddleware` → `HttpForwarder.SendAsync` (Forwarder/). Reading in this order — the same order a real request actually flows — will make far more sense than reading folders alphabetically or top-to-bottom.

---

## 15. First Contribution — What's Actually Appropriate

### 15.1 What CONTRIBUTING.md actually says, verified directly

"Almost all contributions should start with an issue." For a small, well-understood bug: "if you feel confident about the fix, create a Pull Request... Bug PRs should be small and uncontroversial." For anything larger: **discuss and agree on a design in the issue first** — the maintainers explicitly discourage unsolicited large PRs. A one-time, .NET Foundation-wide CLA sign-off (via an automated CLA bot) is required on your first PR.

### 15.2 The extensibility philosophy — worth understanding before you propose anything

CONTRIBUTING.md states this directly, and it matters for calibrating what kind of contribution is even welcome: *"The answer to many feature requests may be that it should be a custom module, rather than a change to the existing feature... we are unlikely to want a PR for the module, but will be very interested in any changes to the core that enable the extensibility."* In other words: if you find yourself wanting to add a new behavior, the maintainers' default expectation is that you build it as a plugin using YARP's existing DI-based extensibility points (§5.1's `IProxyConfigFilter`, §5.7's `ITransformProvider`, §5.4's `ILoadBalancingPolicy`, §5.8's `IReverseProxyBuilder` extension methods) — and they're specifically interested in PRs that make that extensibility *better*, more than PRs that bake a new specific behavior into core.

### 15.3 Live labels, and an honest caveat

`help wanted` and `good first issue` both exist and are actively linked from `CONTRIBUTING.md`. **At the time this lecture's research was conducted, zero issues were labeled `good first issue`** — this is a genuinely time-sensitive fact, not something to treat as permanently true; check the label directly when you're actually ready to look, since the list turns over. `help wanted` currently skews toward support questions and doc requests rather than beginner-scoped code tasks specifically — read each one rather than assuming the label alone guarantees difficulty level.

### 15.4 Contribution categories genuinely appropriate for your background

Based on real, historical, closed `good first issue` examples from the repository (used here as illustrations of *category*, not as currently-open tasks) and the architecture you now understand from §5–§13:

- **Documentation clarification** — e.g., a past real issue simply clarified whether routes are matched in a defined order. You now understand routing precedence (Lecture 5 §4.6) well enough to recognize when a doc's wording is ambiguous or incomplete, and precise enough to fix it correctly.
- **Small correctness bugs in an existing, narrow code path** — e.g., a past issue fixed `Content-Length: 0` not being correctly filtered from responses that shouldn't carry it (Lecture 1 §4.8's status-code-body relationship), or fixed integer parsing being misinterpreted as `TimeSpan` days instead of the intended unit in config binding (§6's configuration layer). These are small, scoped, single-behavior fixes — exactly the shape CONTRIBUTING.md says is fine to send directly as a PR without a prior design discussion.
- **Small behavioral fixes to an existing transform** — e.g., a past issue made a transform's query-parameter matching case-insensitive. Given Lecture 4 §15.2 and §5.7 of this lecture, you now understand exactly what a transform is and where it sits in the pipeline — a focused fix to one transform's specific matching behavior is a well-scoped, learnable-in-isolation task.
- **Test coverage gaps** — §14.4's mirrored `src`/`test` structure makes this genuinely approachable: pick a source file you've read and understood, find its corresponding test file, and look for an edge case (Lecture 8's failure taxonomy is a good source of ideas — what happens on a malformed header, a zero-destination cluster, a race between two concurrent health updates) that isn't yet covered.
- **Build/tooling friction fixes** — e.g., a past issue fixed a specific platform build failure. Not glamorous, but genuinely valuable, and doesn't require deep proxy-domain knowledge to identify or fix — sometimes the most approachable category precisely because it doesn't require you to have absorbed the whole architecture first.
- **Concurrency correctness bugs in narrow, well-isolated code** — e.g., a past issue fixed a thread-safety issue in `StreamCopyHttpContent`'s state check (directly Lecture 7 §6.5's contention/race-condition material). These require the concurrency reasoning this series built up through Lecture 7, applied to one small, specific piece of code — a good fit once that lecture's material feels solid, but appropriately scoped (one field, one check) rather than a broad concurrency redesign.

### 15.5 What to deliberately avoid as a first contribution

Per your own instruction, and per CONTRIBUTING.md's own explicit guidance: **do not start with a new load-balancing algorithm, a new core resilience mechanism, or any change touching the Forwarder/'s hot path's fundamental shape.** Not because you couldn't eventually contribute there — but because §15.2's extensibility philosophy means large, opinionated core changes need a design discussion *first*, in the issue, before any code is written at all, and because a first contribution's real goal is building trust and familiarity with the codebase's norms and review process on genuinely low-risk, well-scoped ground — exactly the categories in §15.4.

---

## 16. Common Misconceptions

- **"YARP has its own route-matching engine."** §5.3, §7 — it deliberately doesn't; it builds real ASP.NET Core endpoints and delegates matching entirely to the framework.
- **"Configuration and the live runtime state are the same objects."** §5.1–§5.2 — they're deliberately separate (`RouteConfig` vs. `RouteModel`, etc.), exactly Lecture 5's build-once pattern, confirmed as a real architectural boundary.
- **"YARP includes a full circuit-breaker system out of the box."** §11 — its built-in resilience centers on health checking and load balancing; a full per-call circuit breaker is the kind of thing you'd add via extensibility, not something baked into core.
- **"The samples on GitHub always match what you get from NuGet."** §14.5 — `main`-branch samples track unreleased code; check the matching release branch if you installed via NuGet.
- **"A `good first issue` label guarantees an easy task is currently available."** §15.3 — the list is live and can be empty; treat the label as a starting filter, not a guarantee.
- **"Any contribution is welcome as long as it's technically correct."** §15.2 — the maintainers have an explicit, stated preference for extensibility-enabling changes over new core behavior; understanding that preference before proposing something will save real back-and-forth.

---

## 17. Knowledge Check

1. Using §4 and §5.2–§5.3, explain why a request's route/cluster resolution (stages 4–5) reads from `RouteModel`/`ClusterState` rather than directly from `RouteConfig`/`ClusterConfig` — what would break if it read the config DTOs directly on every request?
2. Using §5.5, explain the difference between `HealthyAndUnknownDestinationsPolicy` and `HealthyOrPanicDestinationsPolicy`, and connect this directly to a specific tension from Lecture 8.
3. Using §5.6, explain why `HttpForwarder.SendAsync` returning `ValueTask<ForwarderError>` instead of throwing an exception for a failed forwarding attempt is a deliberate performance decision, using Lecture 11's vocabulary.
4. Using §5.3 and the existence of `DirectForwardingIEndpointRouteBuilderExtensions`, explain what this tells you about how cleanly YARP's routing/cluster model is actually separated from its core forwarding mechanics.
5. Using §14.4, describe the specific navigation trick the test-directory structure gives you, and why it's more useful than reading source files in isolation.
6. Using §15.2 and §15.5, explain why proposing a new built-in resilience mechanism would be a poor choice for a first contribution, even if your implementation were technically excellent.

---

## 18. Practical Exercise

This is the exercise the entire series has been building toward — clone, build, test, and read the real repository.

### Step 1 — Clone and build

```bash
git clone https://github.com/dotnet/yarp.git
cd yarp
./build.sh          # fetches the pinned SDK automatically and builds YARP.slnx
```

### Step 2 — Run the test suite

```bash
./build.sh -test
```

While it runs, watch the project names scroll by — you should recognize `ReverseProxy.Tests` and `ReverseProxy.FunctionalTests` directly from §14.4.

### Step 3 — Run a sample locally

```bash
cd samples/BasicYarpSample
dotnet run
```

Read its `Program.cs` and `appsettings.json` before running it — confirm they match §6's shape almost exactly, and confirm you can identify the route, cluster, and destination in the config file without any help.

### Step 4 — Trace one request through the real source

Using §14.7's order, open (in an editor, not necessarily running a debugger yet): `ReverseProxyIEndpointRouteBuilderExtensions.cs` → `ProxyEndpointFactory.cs` → `LoadBalancingMiddleware.cs` → `ForwarderMiddleware.cs` → `HttpForwarder.cs`. At each stop, write one sentence, in your own words, describing what that specific file's job is — then compare your sentences against §5's descriptions. Where they diverge, that's exactly the spot worth re-reading the source more slowly.

### Step 5 — Find one test and read it deliberately

Pick one file you read in Step 4 (e.g. `LoadBalancingMiddleware.cs`), find its corresponding test file under `test/ReverseProxy.Tests/LoadBalancing/`, and read through its test cases. For each one, predict what it's testing *before* reading the test body — this is the same "form a hypothesis, then verify" discipline Lecture 11 §9.1 taught, now applied to reading tests as a way of understanding intended behavior.

### Step 6 (optional, if you want to go further) — Look at the live issue tracker

Visit the repository's issues, filtered to `help wanted` and `good first issue`. Read three or four of them — not to necessarily act on any yet, but to calibrate: does the scope of a real issue match what §15.4 predicted? This is a low-stakes way to build a feel for the codebase's actual current state of open work before you commit to anything.

---

## 19. "Ready to Move On" Criteria

This is the final lecture in the series' core arc. Before considering yourself ready to work in YARP's actual codebase, you should be able to:

- [ ] Draw the Client → YARP → Route → Cluster → Destination → Backend chain from memory, and explain what each node represents in terms of a real YARP type.
- [ ] Name the real component responsible for each of the ten request-lifecycle stages in §4.
- [ ] For at least four of §5's major components, state the problem it solves, why it's separate from its neighbors, and what it hands off to which other component.
- [ ] Explain the Configuration/ vs. Model/ split, and why it exists, using Lecture 5's build-once reasoning.
- [ ] Explain why YARP doesn't implement its own route matcher, and why that was a deliberate architectural choice rather than a missing feature.
- [ ] Clone, build, and run YARP's test suite on your own machine, without needing to re-read this lecture's commands.
- [ ] Navigate to any of §5's subsystems in the real source tree without getting lost, and find its corresponding test file.
- [ ] Describe, specifically, what kind of first contribution fits your current background — and explain, in CONTRIBUTING.md's own terms, why a large architectural change would be the wrong place to start.

You began this series being told to expect that, by its end, you'd be able to open YARP's codebase and say "I understand why this exists," rather than "I recognize the class name but have no idea what problem it solves." Everything in §5 of this lecture was written to be checked against that exact standard — if it reads that way to you now, the series has done its job.
