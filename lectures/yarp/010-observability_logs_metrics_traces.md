# Lecture 10: Observability — Logs, Metrics, Traces, and Production Debugging

Series: YARP Learning Series
Builds on: [Lecture 3 §12](003-aspnetcore_request_processing_and_architecture.md) (structured logging basics), [Lecture 7 §8.2, §12](007-concurrency_connection_pooling_and_high_throughput_networking.md) (tail latency, GC pauses), [Lecture 8](008-failure_resilience_and_partial_failure.md) (the full failure taxonomy — this lecture teaches how you'd actually *see* each of those failures happen), [Lecture 9 §8](009-distributed_systems_fundamentals.md) (latency percentiles — already fully taught; this lecture builds on it rather than re-teaching it).
This lecture has been implicitly promised since Lecture 3 §18, which explicitly deferred distributed tracing/correlation IDs as "a strong candidate for a future, dedicated lecture."

---

## 1. Learning Objectives

By the end of this lecture you should be able to:

1. Explain why debugging a production distributed system is a fundamentally different activity from debugging a local application, not just a harder version of the same thing.
2. Write and evaluate structured log statements, and distinguish a useful log line from a useless one.
3. Explain counters, gauges, and histograms as three genuinely different measurement shapes, and explain specifically why histograms — not averages — are the right tool for latency.
4. Explain spans, traces, trace IDs, and parent/child relationships well enough to read a real trace waterfall and understand what it's telling you.
5. Explain what OpenTelemetry is and why it exists, at a conceptual level, without needing its API surface memorized.
6. Walk through four realistic production incidents and describe, step by step, which observability tool you'd reach for first and why.
7. Describe what a reverse proxy specifically needs to log, measure, and trace, and explain why its position in the request path makes this unusually important.

---

## 2. Prerequisite Concepts

Lecture 3 §12 already gave you structured logging's basic shape (`logger.LogInformation("User {UserId} did X", userId)`) and why it beats string interpolation. Lecture 7 §8.2 already introduced tail latency and GC pauses as a real production concern. Lecture 9 §8 already fully taught latency percentiles (p50 through p99.9) with the fan-out amplification argument — this lecture assumes that's settled and builds new material on top of it (specifically, how percentiles turn into concrete operational decisions). Lecture 8's entire failure taxonomy is the *set of things* this lecture teaches you how to actually detect and diagnose in a live system, rather than reason about abstractly.

---

## 3. Core Mental Model — Three Pillars, Three Different Questions

```
   LOGS                        METRICS                       TRACES
   "What EXACTLY               "What's the AGGREGATE          "What happened to THIS
    happened, in this           behavior of the system          ONE request, across every
    one specific instance?"     over time?"                     service it touched?"

   e.g. "User 42's request      e.g. "p99 latency over the     e.g. "This specific request
   to /v1/orders failed          last 5 minutes was 340ms"       took 800ms: 20ms in YARP,
   with a NullReferenceException"                                 50ms in Service A, 700ms
                                                                    waiting on the database"
```

The one sentence for this entire lecture: **observability exists because, in a production distributed system, you cannot attach a debugger and step through code — the only way to understand what's happening is through the exhaust the system leaves behind as it runs, and logs, metrics, and traces are three different, complementary shapes of that exhaust, each answering a question the other two genuinely cannot.**

---

## 4. Why Observability Exists

### 4.1 Local debugging vs. production debugging

When you're debugging a local application, you have tools that simply don't exist once code is running in production: you can attach a debugger and set a breakpoint, step through execution line by line, inspect any variable's current value, and — critically — **reproduce the problem on demand**, running the exact same input against the exact same code as many times as you need.

None of this holds in production, for reasons directly tied to concepts from earlier in this series:

- **You cannot attach a debugger to a live system serving real user traffic** — pausing execution to inspect state would itself cause the exact latency/timeout failures Lecture 8 §5 taught you to avoid, for every other request sharing that process at that moment (Lecture 7 §6's concurrency model — many requests genuinely in flight simultaneously, not one at a time).
- **You often cannot reproduce the problem on demand** — a race condition under real concurrent load (Lecture 7 §6.5's contention), a specific unlucky combination of a slow destination and a tight timeout (Lecture 8 §5), or a partial failure affecting only some fraction of instances (Lecture 8 §11) may simply not occur again if you retry the same request a moment later against a different destination or a different moment in time.
- **There isn't "one" execution to inspect** — a single logical operation, per Lecture 9 §11's dependency graph, might span many processes, many machines, and many concurrent requests interleaved on each one (Lecture 3 §7.1's middleware pipeline running many times over, concurrently, for many different requests at once).

### 4.2 The consequence: you need the system to tell you what happened, continuously, on its own

Since you can't reach in and inspect live state, the system has to **record**, as it runs, enough information that you can reconstruct what happened *after the fact* — this recorded exhaust is what "observability" actually refers to, and logs/metrics/traces (§3) are the three complementary forms it takes.

---

## 5. Logs

### 5.1 Structured logging, extended

Lecture 3 §12.1 already showed the mechanical shape — named fields (`{UserId}`, `{OrderId}`) instead of a flattened string. The reason to revisit it here: structured fields are exactly what make logs *queryable* at production scale (§5.4), and that queryability is the entire point — a log line nobody can efficiently search through, filter, or aggregate later is barely more useful than no log line at all, once you're dealing with any real volume of traffic.

### 5.2 Log levels, used deliberately

Recall Lecture 3 §12.2's mention — worth being explicit about the actual decision each level represents:

- **Trace/Debug**: extremely detailed, useful while actively developing or actively investigating a specific issue — far too noisy to run at this level in production continuously, at real volume.
- **Information**: normal, expected events worth a permanent record — a request completed, a connection was established — the default "everything is working as intended" narration.
- **Warning**: something unexpected happened, but the system recovered or handled it gracefully — a retry succeeded on its second attempt, a destination was temporarily excluded and later recovered (Lecture 6 §6.5).
- **Error**: an operation failed and the failure was *not* transparently recovered — a request ultimately returned an error to its caller.
- **Critical**: the failure threatens the health of the *system itself*, not just one request — approaching Lecture 8 §8.1's liveness territory.

The practical reason this hierarchy matters: production systems typically run with Information (or even Warning) as the default *persisted* level, specifically because Lecture 7 §12's allocation/GC cost applies directly to log volume too — logging everything at Debug level, continuously, at real request volume, is itself a real performance and storage cost (§14 returns to this).

### 5.3 Contextual information

A log line stating only `"Request failed"` is nearly worthless on its own — useful logs carry **context**: which request, which user, which destination, which specific operation, at minimum. This is exactly what structured fields (§5.1) are for — not stylistic preference, but making sure every log line carries enough attached, queryable context to actually be useful when you're trying to reconstruct what happened later, possibly among millions of other log lines from the same time window.

### 5.4 Correlation IDs — the concept this lecture has been building toward since Lecture 3

Here's the problem structured logging alone doesn't solve: a single logical request, per Lecture 9 §11's dependency graph, generates *many* separate log lines, scattered across *many* different services (Lecture 3's middleware pipeline logs something; YARP logs something; the backend service logs several things; the database layer logs something). Individually, each log line is a fragment. **A correlation ID (commonly, a trace ID — §8 makes this precise) is a single unique value, generated once at the very start of a request, attached to every single log line produced anywhere in the system while handling that request** — letting you later search "give me every log line, from every service, that shares this one ID" and reconstruct the complete story of exactly that one request, from a sea of otherwise-indistinguishable concurrent traffic.

```
   WITHOUT a correlation ID:                     WITH a correlation ID:

   [service A] "request started"                 [service A] "request started" traceId=abc123
   [service B] "processing"                       [service B] "processing" traceId=abc123
   [service A] "request started"  ← is this        [service C] "query failed" traceId=xyz789
                the SAME request as               [service B] "processing" traceId=xyz789
                the one above, or a                [service A] "request completed" traceId=abc123
                DIFFERENT concurrent one?
                                                   Now you can filter to EXACTLY traceId=abc123
   No way to tell them apart reliably              and see only that request's own log lines,
   among thousands of interleaved lines            cleanly separated from every other concurrent
                                                    request's lines
```

```csharp
// Concretely, in C#: attach the correlation/trace ID to EVERY log line
// for the duration of a request, using a logging scope.
using (logger.BeginScope(new Dictionary<string, object> { ["TraceId"] = traceId }))
{
    logger.LogInformation("Forwarding request to {Destination}", destination);
    // every log line written within this scope automatically carries TraceId
}
```

### 5.5 Useful vs. useless logs

| Useless | Useful |
|---|---|
| `"Error occurred"` | `"Request to destination {Destination} failed with {StatusCode} after {ElapsedMs}ms, traceId={TraceId}"` |
| `"Processing..."` (logged on every single request, unconditionally, at Information level) | A single Information-level log per request lifecycle event that actually changed state (started, completed, failed) — not narration of routine, expected internal steps |
| A log line with no identifiers at all connecting it to a specific request/user/destination | A log line with enough structured context (§5.3) to be independently useful even out of surrounding context |
| Logging the same fact twice, at two different points in the same code path, redundantly | One clear log line per meaningful event, placed at the point where the most relevant context is available |

The general test worth internalizing: **would this log line, found in isolation, in a search across millions of lines, actually tell you something actionable?** If not, it's likely noise — and noise has a real cost (§14), not just an annoyance cost.

---

## 6. Metrics

### 6.1 Counters

A **counter** is a value that only ever increases (or resets to zero, typically on process restart) — "how many times has X happened, total." Examples: total requests handled, total errors returned, total connections opened. Counters are queried as **rates** in practice — "requests per second" is a counter's rate of change over some time window, not the counter's raw ever-growing total, which on its own (`14,203,991 requests since the process started`) isn't very actionable by itself.

### 6.2 Gauges

A **gauge** is a value that can go up *or* down, representing a current snapshot state — "how many things are true right now." Examples: current number of open connections, current queue depth (Lecture 9 §10.3's direct latency-driver, now something you can actually *watch*), current memory usage. Unlike a counter, a gauge's raw current value is directly meaningful on its own — "47 connections currently open" doesn't need a rate computed from it to be useful.

### 6.3 Histograms

A **histogram** records the **distribution** of a value across many observations — not just a single number, but a full shape: how many observations fell into each of several value ranges ("buckets"). This is the correct tool for latency specifically (§6.6 explains precisely why), and also useful for anything else where the *shape* of the distribution matters more than a single summary number — request size, batch size, queue wait time.

### 6.4 Rates

A **rate** is a measurement expressed per unit time, almost always derived from a counter (§6.1) — "requests per second," "errors per minute." The raw counter tells you a cumulative total since some starting point; the rate tells you what's happening *right now*, which is almost always the more operationally relevant question during an incident.

### 6.5 Error rates and throughput, named precisely

Two rates worth naming explicitly because they're the two most commonly watched metrics in almost any production system: **throughput** (Lecture 9 §9.1 — successful requests per second, the system's actual delivered work rate) and **error rate** (failed requests per second, or more commonly expressed as a *percentage* of total requests — "0.3% error rate" is more comparable across different traffic volumes than a raw count).

### 6.6 Why histograms are specifically the right tool for latency

This is worth making airtight, because it's a common point of real confusion: **you cannot average a bunch of individually-recorded average latencies and get a correct overall average, let alone a correct percentile** — averages of averages lose information, and percentiles (Lecture 9 §8) genuinely cannot be computed correctly from a pre-averaged value at all, because a percentile needs to know the actual *distribution* of individual values, not a single summary number that's already thrown that information away.

A histogram solves this by recording, for every observation, *which bucket* it fell into (e.g., "0-10ms", "10-50ms", "50-100ms", "100-500ms", "500ms+") — and because bucket counts *can* be correctly combined across many instances/time windows (add up how many observations fell into each bucket, across however many sources), you can compute an accurate p50/p95/p99 *after the fact*, across an entire fleet, without ever having needed to store every single raw latency value forever. This is exactly why production metrics systems universally use histograms (or close mathematical relatives) for latency, rather than trying to track "the average latency" or "the p99 latency" as if either were a single number you could just directly average together across many sources.

```
   Histogram buckets, one time window, aggregated across many instances:

   0-10ms:    ████████████████████████████  (2,840 requests)
   10-50ms:   ████████████████ (1,620 requests)
   50-100ms:  ██████ (610 requests)
   100-500ms: ██ (190 requests)
   500ms+:    ▎ (40 requests)

   From THESE bucket counts, p50/p95/p99 can be correctly computed —
   from a single pre-averaged number, they could not be.
```

---

## 7. Percentiles — From Numbers to Decisions

Lecture 9 §8 already taught you what p50/p95/p99/p99.9 mean and why an average misleads. The piece to add here: **percentiles become operationally useful once they're tied to a concrete decision** — most commonly, a **Service Level Objective (SLO)**, a deliberately chosen target like "p99 latency under 500ms" or "error rate under 0.1%, measured over a rolling 5-minute window." An SLO turns a raw percentile number into an actionable signal: crossing it is what actually triggers an alert, paging someone, or automated action (like Lecture 6 §6.5's health-check-driven exclusion) — the percentile figure itself is just a measurement; the SLO is the decision about what that measurement should mean operationally. This is why teams don't just "look at p99" abstractly — they define, in advance, what p99 value represents acceptable vs. unacceptable user experience for their specific system, and build monitoring around that specific, chosen threshold.

---

## 8. Distributed Tracing

### 8.1 The problem traces solve that logs and metrics don't

Metrics (§6) tell you aggregate system behavior — "p99 is 800ms right now" — but not *why*, for any specific request. Logs (§5), even correlated (§5.4), give you fragments — separate lines from separate services — but reconstructing the actual *timing relationship* between them (did the database call happen before or after the cache check? how much of the total time was actually spent waiting on the database specifically, versus everything else?) from scattered log lines is slow and error-prone. **A trace is a single, structured, timed representation of one request's entire journey across every service it touched — showing not just that each step happened, but exactly how long each step took, and how the steps relate to each other (sequential vs. parallel).**

### 8.2 Spans

A **span** represents one unit of work with a start time and an end time — "YARP forwarded this request to Service A" is a span; "Service A queried the database" is a separate span. A single request typically produces *many* spans, one for each meaningful unit of work performed anywhere along its journey.

### 8.3 Traces

A **trace** is the complete collection of all spans belonging to one single logical request — every span, from every service, that request touched, assembled together. The trace as a whole is what lets you see the complete, end-to-end journey (§8.1's promise), not just one isolated piece of it.

### 8.4 Trace IDs and the parent/child relationship

Every span carries a **trace ID** — exactly §5.4's correlation ID, now formalized as the specific mechanism tracing uses — shared by every span in the same trace, letting a tracing backend group them together correctly. Each span *also* carries its own unique **span ID**, and (except for the very first span in a trace) a **parent span ID**, referencing whichever span *caused* it to start — this is what lets a tracing system reconstruct not just "these spans all belong together" but the actual *shape* of the work: which calls were nested inside which, and which happened in parallel versus in sequence.

### 8.5 Walking through the example, concretely

```
   Request
     │
     ▼
   Proxy (YARP)
     │
     ▼
   Service A
     │
     ▼
   Database
```

As a trace, with real timing (a "waterfall" view — the standard way tracing UIs display this):

```
   trace_id = abc123

   span: "YARP: handle request"           [────────────────────────────────] 0ms → 820ms
     └─ span: "YARP: forward to Service A"     [──────────────────────────] 10ms → 815ms
          └─ span: "Service A: handle /v1/orders"   [──────────────────────] 20ms → 810ms
               └─ span: "Service A: query database"      [────────────────] 40ms → 790ms
```

This single view, at a glance, tells you something logs and metrics alone would take real effort to reconstruct: **total request time was 820ms, and the overwhelming majority of it (750ms out of 820ms) was spent inside the database query specifically** — YARP's own overhead was small (roughly 10ms before forwarding, plus a small amount after), and Service A's own processing (outside the database call) was small too. Without a trace, you'd be looking at separate log lines and separate latency metrics from three different services, and manually reasoning about which parts overlapped in time and which were sequential — the trace does that reconstruction for you, visually, directly.

### 8.6 Parent/child in a fan-out scenario

If Service A had instead called two downstream services *in parallel* rather than one sequentially:

```
   span: "Service A: handle request"                [────────────────────] 20ms → 300ms
     ├─ span: "Service A: call Service X" (parallel)      [──────────────] 30ms → 290ms
     └─ span: "Service A: call Service Y" (parallel)      [──────────]     30ms → 220ms
```

The overlapping time ranges directly show these two child spans ran concurrently (Lecture 9 §11.3's "parallel calls, critical path is the slower of the two" point, now visible directly in the trace) — total time is bounded by whichever child took longer (X, ending at 290ms), not their sum. This is exactly the kind of critical-path reasoning Lecture 9 §11.3 introduced conceptually, now something you can literally *see* in a real trace rather than having to infer from separate metrics.

---

## 9. OpenTelemetry — A Practical Conceptual Introduction

### 9.1 The problem it solves

Before a standard like this existed, every logging/metrics/tracing vendor had its own instrumentation API — meaning code in your application had to be written *against a specific vendor's SDK*, and switching vendors (or, worse, having different services in the same dependency graph instrumented against *different* vendors' incompatible SDKs) made correlating data across services (exactly §5.4/§8.4's whole point) difficult or impossible. **OpenTelemetry (often abbreviated OTel) is a vendor-neutral standard** — a common API and data format for logs, metrics, and traces — so application code can be instrumented once, and the resulting data can be sent to *any* compatible backend, and — critically — data from services written by completely different teams, using completely different backends, can still be correlated together correctly, because they all speak the same trace ID / span ID format underneath.

### 9.2 The pieces, at a conceptual level

```
   Your application code
          │
          ▼
   OpenTelemetry SDK (creates spans, records metrics, attaches trace context)
          │
          ▼
   Exporter (formats and sends the data somewhere)
          │
          ▼
   Some observability backend (could be any vendor's product,
   or a self-hosted open-source one — OTel doesn't care which)
```

You don't need this API's exact method signatures memorized — the concept worth holding onto: **instrumentation (the code that creates spans and records metrics) is decoupled from the backend that eventually stores/displays that data**, via the exporter layer. This is precisely why a library or framework (including, plausibly, ASP.NET Core/YARP itself) can ship *built-in* OpenTelemetry instrumentation, without needing to know or care in advance which specific observability backend any given consumer of that library will eventually choose.

```csharp
// Conceptual shape — you're not expected to memorize this API surface,
// just recognize the pattern: create a span, do work, the span records
// how long it took automatically when disposed.
using var activity = MyActivitySource.StartActivity("ForwardToBackend");
activity?.SetTag("destination", destinationAddress);
// ... do the actual work (e.g., the outbound HTTP call) ...
// span automatically ends, with its duration recorded, when disposed
```

### 9.3 Automatic context propagation — the piece that makes distributed tracing actually work across services

Here's the mechanism that makes §8's cross-service trace assembly possible at all: when Service A makes an outbound call to Service B, the current trace ID (and the calling span's ID, to become the new span's parent) gets **automatically attached to the outgoing request** — typically as an HTTP header (a standardized one, `traceparent`, is part of what OpenTelemetry/W3C Trace Context standardizes) — so that when Service B receives the request and starts its *own* span, it already knows which trace it belongs to and which span caused it, without either service needing to manually pass that information through application-level parameters. This automatic propagation is precisely what turns "every service independently logs a trace ID if someone remembered to thread it through" into "every service participates in the same trace correctly, by default, as a consequence of the underlying HTTP call itself."

---

## 10. Production Debugging — Realistic Scenarios

Each of these walks through the actual investigative sequence: which tool you'd reach for first, what you'd look for, and how you'd narrow down the cause — directly exercising Lecture 8's failure taxonomy through the observability tools this lecture just taught.

### 10.1 "Requests are suddenly slower."

1. **Metrics first**: check the p50/p95/p99 latency histogram (§6.3, §6.6) over the recent time window — has it shifted uniformly (every request somewhat slower) or has the *tail* specifically gotten worse (p50 barely moved, p99 spiked)? These point in very different directions.
2. If it's a tail-specific spike: check **traces** (§8) for a handful of the slowest recent requests — the waterfall view will usually show, directly, which specific span is now taking disproportionately long (a specific downstream service, a specific database query) — exactly §8.5's worked example, now applied diagnostically.
3. Cross-reference with **gauges** (§6.2) for the suspected component — is its connection pool saturated (Lecture 7 §5.4)? Is its queue depth (Lecture 9 §10.3) elevated? These would directly explain added latency without that component's own processing time necessarily having changed at all.
4. Only once a specific suspect is narrowed down do you reach for **logs** (§5) from that specific component, filtered by correlation ID from one of the slow traces, to see the detailed, contextual story of what it was actually doing during that window.

### 10.2 "Errors increased."

1. **Metrics first**: is the error rate (§6.5) increase uniform across all destinations/routes, or concentrated on one specific destination or route? (This maps directly onto Lecture 8 §11.2's per-destination/per-feature health dimensions.)
2. If concentrated on one destination: this strongly suggests Lecture 8 §4's per-instance failure modes (crashed, unhealthy) rather than a systemic issue — check that destination's health-check status (Lecture 6 §6) directly.
3. If uniform across everything: this points toward a shared dependency (Lecture 8 §4.3, Lecture 9 §11.2's high-fan-in node) — check **traces** for a sample of the newly-failing requests to see which specific downstream call is failing across all of them.
4. **Logs**, filtered to Error level and the relevant time window, give you the actual exception/error detail for a specific failing request, once you've narrowed down *which* component to look at.

### 10.3 "One backend is unhealthy."

1. This is often first noticed via a **metric** directly — a per-destination gauge or counter showing that destination's request count drop to zero (Lecture 6 §6.5's exclusion from rotation, made visible) or its own health-check failure counter incrementing.
2. Check **logs** from the health-checking component itself (Lecture 6 §6.2's active probes, or §6.3's passive detection) — what specific condition caused it to be marked unhealthy (probe timeout? Probe returned a non-success status? A run of passive failures?).
3. If the destination is reachable at all, check its *own* logs (if accessible) for what's actually going wrong on that instance specifically — this is where the investigation moves from "the proxy's view of this destination" to "the destination's own view of itself."
4. **Traces** are less central to this specific scenario, since the interesting question — "why is this one instance unhealthy" — is mostly a single-component story rather than a cross-service timing question; they'd become relevant again if you needed to understand what *client-facing* impact this destination's unhealthiness actually had while it was excluded.

### 10.4 "CPU is normal but latency is high."

This is a genuinely interesting, common, and instructive case specifically because it rules out the most obvious hypothesis (raw compute exhaustion) immediately.

1. Normal CPU strongly suggests the bottleneck (Lecture 9 §9.3) isn't compute — so look at *other* saturation candidates: connection pool utilization (Lecture 7 §5.3, a gauge), thread pool queue length (Lecture 7 §6.3 — a burst outpacing thread pool growth would show as elevated latency with *low* CPU, since threads are waiting, not computing), or GC pause frequency/duration (Lecture 7 §8.2 — GC work does consume CPU, but pause-driven tail latency can dominate user-visible latency numbers while *average* CPU utilization still looks unremarkable).
2. **Traces** are extremely valuable here specifically because they distinguish "time spent actually computing" from "time spent waiting" directly, span by span — a span that takes 400ms but represents "waiting for a pooled connection to become available" tells a completely different story than a 400ms span representing actual query execution, even though both would show up identically as "elapsed time" in a naive measurement.
3. This scenario is a strong, concrete illustration of why observability needs more than one pillar (§3) — a CPU metric alone actively misleads here; only cross-referencing metrics (pool/queue gauges), traces (where exactly is time going), and possibly GC-specific metrics together reveals the actual mechanism.

---

## 11. Common Misconceptions

- **"More logging is always better."** §5.5 and §14 both push back on this — noisy, low-context logs have a real cost and can actively make finding the useful signal harder, not easier.
- **"You can compute an accurate average latency by averaging each instance's own reported average."** §6.6 directly refutes this — averages of averages (and, worse, percentiles computed from averages) lose the distributional information needed to be correct.
- **"A trace and a log are basically the same thing, just formatted differently."** §8.1 draws the real distinction — a trace captures *timing and causal structure* across services; a log captures a *point-in-time fact* within one service; neither substitutes for the other.
- **"OpenTelemetry is a specific observability product/vendor."** §9.1 is explicit — it's a vendor-neutral standard for instrumentation; the actual storage/display backend is a separate, swappable choice.
- **"High CPU is the only thing that causes high latency."** §10.4 is a direct, worked counterexample — connection pool waits, thread pool queuing, and GC pauses can all drive latency up with CPU looking completely normal.
- **"Metrics tell you why something is slow, not just that it's slow."** Metrics are excellent at telling you *that* and roughly *where* — but pinpointing the precise causal *why* for one specific request is usually a tracing (or, failing that, a log-correlation) job, not a metrics job.

---

## 12. Production Perspective: 10 → 10,000 → 1,000,000 → 100,000,000 Requests

**~10 requests**: logs alone are completely sufficient — you could plausibly read every single log line by hand, and correlation IDs, metrics, and tracing would all be substantial overkill relative to the actual debugging need.

**~10,000 requests/sec**: reading logs by hand stops being viable — this is roughly the scale where structured logging (§5.1) and correlation IDs (§5.4) become genuinely necessary rather than nice-to-have, and where basic metrics (throughput, error rate, §6.5) become the *first* thing anyone checks during an incident, rather than logs.

**~1,000,000 requests/sec, real dependency graphs**: distributed tracing (§8) moves from "valuable" to close to essential — with enough services in the request path (Lecture 9 §11.1), reconstructing a single request's story from scattered logs alone becomes genuinely impractical, and the specific "which span is slow" diagnostic power of tracing (§10.1, §10.4) becomes the fastest path to root cause. SLOs (§7) become formal, tracked commitments rather than informal targets.

**~100,000,000 requests/sec**: **sampling** becomes an explicit, necessary design decision (§14 covers this directly) — recording a full trace for literally every single request at this volume is often not economically or technically feasible, so systems deliberately trace only a statistically representative subset, while still recording metrics (which aggregate cheaply, §6.6) for every single request regardless. Observability infrastructure itself becomes a significant, deliberately-engineered system in its own right, not an incidental add-on to the "real" system.

---

## 13. Failure Scenarios — When Observability Itself Fails

Worth a dedicated, brief treatment because it's an easy blind spot: the observability system is *also* a distributed system (Lecture 9), subject to the same failure modes as everything else.

- **The logging pipeline itself becomes overwhelmed** under high log volume (often exactly *during* an incident, when everyone dials up logging verbosity to investigate — the worst possible moment for the logging pipeline itself to become a bottleneck) — a system generating unbounded log volume during its own crisis can make the crisis worse (Lecture 7 §7's backpressure principle applies to your own telemetry pipeline too, not just to user-facing request handling).
- **Missing or incomplete traces**, often caused by a service in the chain that isn't instrumented, or that fails to propagate trace context correctly (§9.3) — producing a trace with a confusing, silent gap exactly where the interesting behavior was happening.
- **High-cardinality metrics blowing up cost/storage** — a metric labeled with something like a raw user ID or request ID (rather than a bounded set of values like destination name or status code) creates effectively unlimited distinct metric series, which most metrics backends handle very poorly at scale — a subtle, easy mistake with real operational and cost consequences, worth knowing to avoid deliberately.
- **Sampling bias** (§14) — if trace sampling isn't done carefully, you can systematically under-sample exactly the rare, slow, or failing requests that matter most for debugging, while faithfully capturing plenty of ordinary, uninteresting ones.

---

## 14. Performance Implications

- **Log at the right level, deliberately, and avoid unconditional per-request noise** (§5.2, §5.5) — logging cost is real cost (Lecture 7 §8.3's allocation discipline applies directly to log statements too), multiplied by request volume.
- **Prefer histograms over pre-averaged latency values wherever percentiles matter** (§6.6) — this isn't a style preference, it's a correctness requirement for accurate aggregate percentile computation.
- **Keep metric label/tag cardinality bounded** (§13) — avoid labeling metrics with unbounded values like raw IDs; use bounded categories (route name, status code class, destination name).
- **Sample traces deliberately at high volume rather than tracing every request unconditionally** (§12's 100M tier) — but sample thoughtfully, biasing toward capturing errors and slow outliers rather than uniform random sampling alone, so the traces you *do* keep are disproportionately the interesting ones.
- **Treat your observability pipeline's own capacity as a real, planned-for resource** (§13) — it needs its own backpressure and headroom, especially because incident response itself tends to spike its load right when you need it most reliable.

---

## 15. YARP Connection

Because YARP sits on the critical path (Lecture 9 §11.3) of every proxied request, and because it's precisely the component translating connection-layer failures into HTTP-level outcomes (Lecture 4 §13, Lecture 8 §15), it has a uniquely important observability role — arguably more important, per-request, than most individual backend services, since it's involved in *every* request rather than a subset.

### 15.1 What YARP specifically needs to log

Per-request forwarding events (which route matched, which cluster/destination was selected, final status code, elapsed time) at Information level, with correlation/trace ID (§5.4) attached automatically via the ambient trace context (§9.3) — plus Warning/Error-level logs for the specific failure translations from Lecture 4 §13 (destination unreachable → 502, timeout → 504, no healthy destinations → 503), since these are exactly the events an operator investigating "one backend is unhealthy" (§10.3) or "errors increased" (§10.2) would search for first.

### 15.2 What YARP specifically needs to measure

- **Counters**: total requests forwarded (overall, and per-route/per-cluster/per-destination — bounded cardinality, per §14), total errors by status-code class (502/503/504 specifically distinguishable from backend-originated 4xx/5xx, echoing Lecture 4 §4.8's distinction between "the proxy talking about itself" and "the backend talking").
- **Gauges**: current connection pool utilization per destination (Lecture 7 §5, directly diagnostic for §10.4-style investigations), current count of healthy vs. unhealthy destinations per cluster (Lecture 6 §6, directly the metric behind §10.3's investigation).
- **Histograms**: end-to-end proxied request latency (§6.3, §6.6) — and ideally broken down further into "time spent selecting a route/destination" vs. "time spent actually forwarding to and waiting on the backend," since that split is exactly what separates a YARP-side problem from a backend-side one, mirroring §10.1's diagnostic sequence directly.

### 15.3 What YARP specifically needs to trace

YARP's forwarding step should appear as its own span (§8.2) within the larger trace — parent to whatever span the backend itself creates once it receives the forwarded request (§9.3's automatic propagation making this connection possible without any manual wiring) — meaning a trace touching a YARP-fronted service shows, explicitly and visually, exactly how much of total request time was YARP's own overhead versus the backend's, precisely answering §8.5's worked example's question, but now for real production traffic rather than a lecture illustration. This span-level visibility is also precisely what makes scenarios like §10.4 ("CPU normal, latency high") diagnosable when YARP itself turns out to be the actual source of added latency (a saturated connection pool, Lecture 7 §5.4's queueing) rather than the backend it's forwarding to.

### 15.4 The synthesis

Because YARP is a **stateless**, horizontally-scaled (Lecture 9 §4.3), high-throughput (Lecture 7) component sitting on literally every proxied request's critical path, good observability isn't a nice-to-have layered on top of its core job — it's close to a structural requirement for operating it at all: without it, precisely the kinds of scenarios in §10 (a slow destination, an unhealthy destination, YARP's own resource saturation) would be effectively invisible until they'd already caused significant, hard-to-diagnose, user-visible impact.

---

## 16. What I Don't Need to Know Yet

- Specific observability backend products (Datadog, Grafana/Prometheus, Jaeger, etc.) and their particular query languages/dashboards — the conceptual model (§3, §6, §8) transfers across all of them; specific tool fluency is worth picking up hands-on when you're actually using a particular stack.
- OpenTelemetry's exact API surface (specific class/method names for creating spans, configuring exporters) — §9.2's conceptual shape is sufficient for this series; the specific code is a reference lookup away when you're actually instrumenting something.
- Advanced sampling strategies (tail-based sampling, dynamic sampling rate adjustment) — recognize that sophisticated approaches beyond simple uniform sampling exist (§14); the specific algorithms are a deeper, later topic.
- Log aggregation system internals (how a system like an ELK-style stack or similar actually indexes and searches billions of log lines efficiently) — recognize this is itself a nontrivial distributed system (§13); its internals aren't required to use it effectively as a consumer.
- Formal SRE practices around error budgets and SLO governance in full depth — §7 gave you the core idea (a percentile tied to a decision); the full organizational practice around error budgets is a valuable, related, but distinct topic.

---

## 17. Knowledge Check

1. Using §4.1, explain specifically why "just attach a debugger" isn't a viable strategy for diagnosing a production issue affecting 0.5% of requests under real concurrent load.
2. A dashboard shows average latency as a flat, unremarkable 45ms throughout an incident, but users are filing complaints about slow page loads. Using §6.6 and Lecture 9 §8, explain what's likely being hidden, and what you'd check instead.
3. Using §8.5's worked trace example, explain how you'd know, just from the waterfall diagram, whether YARP's own forwarding logic or the backend's database query was the dominant contributor to total latency — without reading a single log line.
4. Using §9.3, explain why a trace can correctly connect spans from two services written and deployed by completely different teams, with no shared code between them, as long as both use OpenTelemetry.
5. Walk through the "CPU is normal but latency is high" scenario (§10.4) yourself: name three specific, different underlying causes that would all produce this exact symptom, and explain how you'd distinguish between them using the tools from this lecture.
6. Using §15.2's histogram-splitting suggestion (YARP-side time vs. backend-side time), explain why this specific metric design directly speeds up the §10.1 "requests are suddenly slower" investigation for anyone operating a YARP-fronted service.

---

## 18. Practical Exercise

Build a small system with real structured logging, a real latency histogram, and a hand-rolled trace-ID propagation, so all three pillars are directly observable rather than abstract.

### Step 1 — A "proxy" and a "backend," logging with a shared correlation ID

```csharp
// Backend/Program.cs
var builder = WebApplication.CreateBuilder(args);
var app = builder.Build();

app.MapGet("/work", async (HttpContext ctx) =>
{
    var traceId = ctx.Request.Headers["X-Trace-Id"].ToString();
    var sw = System.Diagnostics.Stopwatch.StartNew();
    await Task.Delay(Random.Shared.Next(10, 300)); // simulate variable backend work
    Console.WriteLine($"[Backend] traceId={traceId} elapsedMs={sw.ElapsedMilliseconds} event=work_completed");
    return Results.Ok(new { traceId });
});
app.Run("http://localhost:8001");
```

```csharp
// Proxy/Program.cs
var builder = WebApplication.CreateBuilder(args);
var app = builder.Build();
var client = new HttpClient();

// crude histogram: bucket counts by latency range
var buckets = new Dictionary<string, int> { ["0-10ms"]=0, ["10-50ms"]=0, ["50-100ms"]=0, ["100-500ms"]=0, ["500ms+"]=0 };
object bucketLock = new();

app.MapGet("/proxy", async () =>
{
    var traceId = Guid.NewGuid().ToString("N")[..8]; // generate ONCE, at the entry point
    var sw = System.Diagnostics.Stopwatch.StartNew();

    Console.WriteLine($"[Proxy] traceId={traceId} event=forwarding_started");
    var request = new HttpRequestMessage(HttpMethod.Get, "http://localhost:8001/work");
    request.Headers.Add("X-Trace-Id", traceId); // PROPAGATE the trace ID, exactly like Section 9.3
    await client.SendAsync(request);

    var elapsed = sw.ElapsedMilliseconds;
    var bucket = elapsed switch
    {
        < 10 => "0-10ms", < 50 => "10-50ms", < 100 => "50-100ms", < 500 => "100-500ms", _ => "500ms+"
    };
    lock (bucketLock) { buckets[bucket]++; }

    Console.WriteLine($"[Proxy] traceId={traceId} elapsedMs={elapsed} event=forwarding_completed");
    return Results.Ok(new { traceId, elapsedMs = elapsed });
});

app.MapGet("/histogram", () =>
{
    lock (bucketLock) { return Results.Ok(buckets); }
});

app.Run("http://localhost:8000");
```

### Step 2 — Watch correlated logs directly (Section 5.4)

Run both, then:
```bash
curl http://localhost:8000/proxy
```
Watch both consoles — confirm the *same* `traceId` appears in both the `[Proxy]` and `[Backend]` log lines for that one request, exactly demonstrating §5.4's correlation mechanism, and confirm you could distinguish this request's lines from a different concurrent request's lines purely by that shared ID.

### Step 3 — Build a histogram, then compute a percentile from it (Section 6.6)

```bash
for i in $(seq 1 50); do curl -s http://localhost:8000/proxy > /dev/null; done
curl http://localhost:8000/histogram
```
Look at the resulting bucket counts — by hand, estimate roughly where p50 and p90 fall, purely from the bucket distribution, without ever having stored or looked at all 50 individual latency values together as a raw list. This is precisely §6.6's point, made mechanically real: the histogram's bucket counts alone are sufficient to reason about percentiles, cheaply, even at far larger scale than 50 requests.

### Step 4 (optional extension) — Simulate a slow trace and "diagnose" it

Modify the backend to occasionally (say, 1 in 10 requests) `Task.Delay` for 2000ms instead of the normal range, and re-run Step 2/3's loop. Confirm the `500ms+` bucket picks up these outliers, and pick one specific slow `traceId` from the console output — confirm you can find its matching pair of `[Proxy]`/`[Backend]` log lines and, from their timestamps/elapsed values alone, correctly conclude the backend (not the proxy) was the source of the added latency — a hand-built version of exactly the diagnostic reasoning §10.1 and §10.4 walked through conceptually.

---

## 19. "Ready to Move On" Criteria

Before starting the next lecture, you should be able to explain — out loud, in your own words:

- [ ] Why production debugging fundamentally can't rely on the same tools (breakpoints, step-through debugging, on-demand reproduction) as local debugging.
- [ ] What distinguishes a counter, a gauge, and a histogram, and why latency specifically needs a histogram rather than a single averaged number.
- [ ] What a correlation/trace ID is, why it exists, and how it lets you reconstruct one request's story out of millions of interleaved concurrent log lines.
- [ ] What a span is, what a trace is, and how parent/child relationships let a trace represent both sequential and parallel work correctly.
- [ ] What OpenTelemetry actually is (a vendor-neutral standard) and isn't (a specific product), and why automatic context propagation is the mechanism that makes cross-service tracing work without manual wiring.
- [ ] For each of the four production-debugging scenarios in §10, which observability tool you'd reach for first, and why that ordering makes sense.
- [ ] Why "CPU is normal but latency is high" is a genuinely informative symptom, and at least three distinct underlying causes that could produce it.
- [ ] What a reverse proxy specifically needs to log, measure, and trace, and why its position on the critical path of every request makes this more consequential than for a typical individual service.

If these feel solid, you've now completed the observability foundation this series has been quietly building toward since Lecture 3 — logs, metrics, and traces, together, are what let you actually verify, in production, that everything the rest of this series taught (routing, load balancing, resilience, distributed systems trade-offs) is behaving the way you designed it to.
