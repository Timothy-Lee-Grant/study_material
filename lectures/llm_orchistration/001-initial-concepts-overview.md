2026_06_25_00_00-initial-concepts-overview

# LLM_Monitor — Concepts & Engineering Guide

> A teaching document written for Timothy Grant.
> Audience assumption (from `persona.md`): strong embedded C/C++/Python/C# background, comfortable with memory, OOP, and reading medium codebases, but newer to cloud backend, distributed systems, async, and AI engineering. This document goes high-level → components → interactions → control flow → implementation → edge cases, the way you said you learn best.

---

## 0. How to read this document

1. **Section 1** — the macro picture: what you are actually building.
2. **Section 2** — a mindset shift from embedded/firmware thinking to distributed-services thinking.
3. **Section 3** — every concrete problem/bug currently in the repo, with the *why* behind each.
4. **Section 4** — deep-dive concept modules (the things you're using and should master).
5. **Section 5** — the full request/response lifecycle and the **shape of every object** as it crosses each boundary.
6. **Section 6** — networking between containers (how they actually find and call each other).
7. **Section 7** — the sustainable build script (no stale containers, no disk clutter).
8. **Section 8** — mental sandbox / next challenges.

---

## 1. Executive Overview — what this system is

You are building an **LLM observability and governance gateway**. Strip away the buzzwords and the job is:

> A user sends a piece of text. It flows through a chain of services. Each service does one job and records *telemetry* about what happened (latency, sentiment, topic, policy violations). The user gets a response back, and you accumulate a rich, queryable record of every interaction.

At a macro level there are **three planes**:

| Plane | Responsibility | In your repo |
|-------|----------------|--------------|
| **Edge / API plane** | Receive the user's HTTP request, validate it, measure it, forward it, shape the final response | `server/` (ASP.NET Core) |
| **Intelligence plane** | Run the actual LLM, classify sentiment/topic, check policy via RAG | `langchain_service/` (Flask + LangChain) |
| **Data / Observability plane** | Store metrics, logs, traces, and semantic records | *Not built yet* (Postgres/pgvector, Prometheus, Grafana planned) |

The thing that makes this a *systems* project and not a script is that these planes are **separate processes that communicate over a network**. That single fact is the source of almost everything you need to learn next.

---

## 2. Your Personal Mindset Shift — from firmware to distributed services

You come from embedded: one binary, deterministic control flow, you own the whole address space, and "communication" means I2C/SPI registers you can reason about exactly. That world has a property this project does **not** have: **a single process where a function call is instantaneous and always succeeds.**

Here is the core reframing:

| Embedded intuition | Distributed-services reality |
|--------------------|------------------------------|
| A function call is free and reliable | A "function call" across services is an **HTTP request** — it has latency, can time out, can fail, can return garbage |
| One process, one memory space | N processes, **no shared memory**; the only thing they share is the *bytes on the wire* (JSON) |
| You control startup order in `main()` | Containers start **concurrently and independently**; "B is up" never means "B is ready" |
| A pointer/reference passes a live object | Crossing a service boundary **serializes** the object to text and **deserializes** a copy on the other side. The object's *shape* is a contract, not a language type |
| Determinism | Partial failure is the default. Your job is to design for "what if the other service is slow/down?" |

> **The single most important sentence in this document:** Inside a process you pass *objects*; across a service boundary you pass *serialized messages*. Every boundary in Section 5 is a place where a C# object becomes JSON text, travels, and is reborn as a Python dict (and vice versa). Most of your bugs right now live exactly at these boundaries.

This maps directly onto your stated weak areas — async, coordination between services, and large-system design. We'll hit each.

---

## 3. Problems currently in the repo (and the concept behind each)

I read every source file. Below is everything that is currently broken or conceptually off. None of this is criticism — it's a map of exactly where the learning is. I have **not** changed any of these; that's your work to do.

### 3.1 Critical — these stop the system from running

**(A) `docker-compose.yaml`: `langchain_service` builds the wrong image.**
```yaml
langchain_service:
  build:
    context: ./server          # ← points at the .NET server
    dockerfile: dockerfile
```
You are telling Docker to build the **.NET server** and call it `langchain_service`. Both of your containers would be the same .NET image. The Python/Flask service never gets built.
*Should be* `context: ./langchain_service`.
**Concept:** a Docker *build context* is the directory tree sent to the builder; `context` + `dockerfile` together decide *what* gets built. (Module 4.5)

**(B) `requirements.txt` is not a valid package list.**
```
langchain_core.language_models
```
That's a *Python import path*, not a *PyPI package name*. `pip install` will fail, so the Flask image build dies. You also never list `flask` itself.
*Should be* something like:
```
flask
langchain-core
```
**Concept:** the difference between an *install name* (`langchain-core`, what pip downloads) and an *import name* (`langchain_core`, what Python uses in code). They often differ by hyphen vs underscore. (Common beginner trap.)

**(C) Flask never starts the dev server when run directly.**
```python
if __name__ == "main":      # ← BUG: never true
    app.run(host="0.0.0.0", port=5000, debug=True)
```
Python sets `__name__` to the string `"__main__"` (with double underscores), not `"main"`. So this block is dead. Separately, your Dockerfile launches via `flask run`, which **ignores** this block entirely *and* doesn't know which file is the app (no `FLASK_APP` set). So today there are two different "start" paths and neither is wired correctly.
**Concept:** `if __name__ == "__main__":` is Python's "am I the entry point or am I being imported?" guard. (Module 4.6)

**(D) `lang.py` returns the wrong thing.**
```python
def invoke_langchain():
    model = FakeListChatModel(responses=["Hello from mock agent"])
    response = model.invoke("what is the wheather like over there?")
    return model.response       # ← wrong: model has `responses`, not `response`
```
You compute `response` but then return `model.response` (an attribute that doesn't exist the way you think). `model.invoke(...)` returns a message object; the text lives in `response.content`. So you should `return response.content`. Right now this raises or returns nonsense.
**Concept:** LangChain's `invoke()` returns an **`AIMessage`** object; `.content` is the string. Knowing the *shape* of what a library hands back is half of using it. (Module 5)

### 3.2 Serious — runtime failures in the .NET server

**(E) `Program.cs` maps controllers that were never registered.**
```csharp
var builder = WebApplication.CreateBuilder(args);
var app = builder.Build();
app.MapControllers();          // needs services registered first
```
`MapControllers()` and `UseAuthentication()/UseAuthorization()` all require their services to be added **before** `builder.Build()`:
```csharp
builder.Services.AddControllers();
builder.Services.AddAuthentication(/* a scheme */);
builder.Services.AddAuthorization();
```
Without `AddControllers()`, `MapControllers()` throws at startup. Without `AddAuthentication(...)`, `UseAuthentication()` has no scheme. You also have **no controller classes**, so even when registered there are no endpoints to hit yet.
**Concept:** ASP.NET Core's two-phase model — **register services** (the DI container) *then* **build the pipeline** (middleware). You can't `Use`/`Map` a capability you didn't `Add`. (Module 4.1)

**(F) Your `TelemetryMiddleware` measures nothing.**
```csharp
public async Task InvokeAsync(HttpContext context)
{
    // Custom logging logic ....
    await _next(context);
    // Custom exit logging ....
}
```
The scaffold is structurally correct (this is the right place for latency capture) but empty. The whole *point* of this project lives in those two comments. (Module 4.2 shows what goes there.)

**(G) The server has no way to call the LangChain service.**
There is no `HttpClient`, no DTO, no endpoint that takes user text and forwards it. The central data path of your architecture — *.NET → Flask* — does not exist yet. This is the biggest *missing* piece, and Section 5 is the blueprint for it.

**(H) YARP is referenced but unused.** `Yarp.ReverseProxy` is in the `.csproj`, but `Program.cs` never calls `AddReverseProxy()` / `MapReverseProxy()`. Dead dependency for now — fine as a placeholder, just know it's not doing anything.

### 3.3 Compose / configuration smells

**(I) Port mapping mismatch.** `dotnet_server` maps `"5000:80"`, but the .NET 8+ runtime image listens on **8080** (your Dockerfile even says `EXPOSE 8080`). Mapping host 5000 → container **80** points at a port nothing is listening on. Should be `"5000:8080"` (or set `ASPNETCORE_HTTP_PORTS=80`). (Module 6 explains the host:container distinction.)

**(J) `depends_on` without a condition only waits for *start*, not *ready*.** A container can be "started" while the app inside is still booting. This is the classic "B is up ≠ B is ready" distributed-systems trap. (Module 4.7)

**(K) `if __name__ == "main"` answer to your inline question** in `Program.cs` (`// do I need to wrap this??`): No, a namespace is optional. File-scoped namespace (`namespace X;`) is fine and modern. You could even delete the class entirely and use *top-level statements*. More in Module 4.1.

### 3.4 Summary table

| # | File | Severity | One-line fix direction |
|---|------|----------|------------------------|
| A | docker-compose.yaml | Critical | `context: ./langchain_service` |
| B | requirements.txt | Critical | real pip names: `flask`, `langchain-core` |
| C | main.py | Critical | `"__main__"` + set `FLASK_APP` / use a proper entrypoint |
| D | lang.py | Critical | `return response.content` |
| E | Program.cs | Serious | `AddControllers()` etc. before `Build()` |
| F | TelemetryMiddleware.cs | Serious (empty) | capture stopwatch + log around `_next` |
| G | server (missing) | Serious | add `HttpClient` + DTO + endpoint to call Flask |
| H | server.csproj/Program.cs | Minor | wire or remove YARP |
| I | docker-compose.yaml | Serious | `"5000:8080"` |
| J | docker-compose.yaml | Smell | add healthchecks + `condition: service_healthy` |

---

## 4. Deep-Dive Concept Modules

Each module: **the Why → the Theory → the Implementation in your code.**

### 4.1 ASP.NET Core: the two-phase host (DI container + middleware pipeline)

**The Why.** A web server must do two completely different things: (1) decide *what capabilities exist* (logging, controllers, auth, an HTTP client to call Flask) and (2) decide *the order requests flow through those capabilities*. Mixing these causes exactly your bug E.

**The Theory.** ASP.NET Core splits startup into two phases:

```
Phase 1: REGISTRATION            Phase 2: PIPELINE
builder.Services.Add___()   →    app.Use___() / app.Map___()
   (the DI container)               (the middleware chain)
        │                                  │
        └──────── builder.Build() ─────────┘
```

- **Dependency Injection (DI)** is the registry of "how to build each service." When your `TelemetryMiddleware` constructor asks for `ILogger<TelemetryMiddleware>`, the framework *injects* it because logging was registered. Coming from embedded, think of DI as a central "driver table": instead of `new`-ing dependencies yourself (tight coupling), you declare what you need and the container wires it. This is what makes services testable and swappable.
- **Middleware pipeline** is a chain of `async` functions, each wrapping the next — a Russian-doll / onion model (Module 4.2).

**The Implementation.** Your `Program.cs` calls `app.MapControllers()` in Phase 2 but never did `builder.Services.AddControllers()` in Phase 1 → crash. The mental rule: *every `Use`/`Map` needs a matching `Add`.*

> **Top-level statements vs. explicit `Main`:** Modern .NET lets `Program.cs` be just the body of `Main` with no class/namespace. You wrote the explicit `public static class Program { Main } ` form — equally valid, slightly more ceremony. Either is fine; your `// do I need to wrap this??` answer is "no, it's a style choice."

### 4.2 Middleware & the onion model (where your telemetry lives)

**The Why.** You want to measure *every* request's latency and context without copy-pasting timing code into every endpoint. Cross-cutting concerns (timing, auth, logging) belong in middleware.

**The Theory.** Each middleware looks like:
```
        ┌────────────── request travels inward ──────────────┐
client →│ Telemetry → Auth → Routing → [ your endpoint ]      │
        └────────────── response travels outward ────────────┘
```
The code `await _next(context)` is the hinge: everything *before* it runs on the way **in**, everything *after* runs on the way **out**. That's why latency timing works — start a stopwatch before `_next`, stop it after, and you've wrapped the entire downstream pipeline including the call to Flask.

**The Implementation.** Conceptually your empty `InvokeAsync` should become (described, not for me to write):
- Before `_next`: record a `Stopwatch.StartNew()`, capture `context.Request.Path`, method, a correlation ID.
- `await _next(context)` — let the request flow to the endpoint that calls Flask.
- After `_next`: stop the stopwatch, read `context.Response.StatusCode`, log `{path, method, status, elapsedMs}`. Later this log line becomes a Prometheus metric.

**Common mistake:** writing to the response body *after* `_next` when the response has already started streaming — you can read status/headers but can't always mutate the body. (Edge case worth remembering.)

### 4.3 Async / await — the concept you flagged as weak

**The Why.** When your .NET server calls Flask, that call might take 2 seconds (an LLM is slow). If the thread *blocks* waiting, it can serve no one else. With 100 users you'd need 100 blocked threads. Async lets **one thread serve many in-flight requests** by parking the work and picking it back up when the network responds.

**The Theory.** This is the part to internalize coming from embedded:

- `await someNetworkCall()` does **not** mean "sleep this thread." It means "**yield** the thread back to the pool; resume this method when the I/O completes." The method is sliced into a **state machine** at each `await`.
- Compare to embedded: it's cooperative yielding, closer to a superloop with non-blocking peripherals than to an RTOS thread per task. There is **no thread sitting in the wait** — that's the whole win (non-blocking I/O).
- **Thread pool**: a small fixed set of OS threads multiplexes thousands of logical operations. Blocking one (e.g., calling `.Result` on a Task) starves the pool — the infamous deadlock you listed as a weak spot.

**Rule of thumb:** for any I/O (network, disk, DB) use `await ...Async(...)` all the way up the call chain. Never `.Result` / `.Wait()` in web code.

**The Implementation.** Your `InvokeAsync` is already `async Task`, and the *future* HttpClient call to Flask must be `await httpClient.PostAsync(...)`. Flask is the slow hop; awaiting it is what keeps your server scalable.

> **Python side:** your Flask app is currently *synchronous* (WSGI). That's fine for learning, but know that one Flask worker handles one request at a time. Production would use multiple workers (gunicorn) or async (ASGI). This asymmetry — async .NET front, sync Python back — is a real design consideration.

### 4.4 The REST / HTTP contract between services

**The Why.** Two processes in different languages can't share objects. They agree on a **contract**: a URL, an HTTP method, and a JSON *shape* for request and response. Get the shape wrong and the boundary silently breaks.

**The Theory.** A clean contract specifies, for each endpoint: method (`POST` for "do something with this data"), path (`/api/chat`), request body shape, response body shape, and status codes (200 ok, 400 bad input, 502 downstream failed). This is the *interface* in OOP terms, but enforced by convention + serialization rather than the compiler. Section 5 defines yours explicitly.

**The Implementation.** Today your Flask exposes only `GET /` that takes **no input** — so the user's text can never actually reach the LLM. You need a `POST` endpoint that accepts `{ "text": ... }`. This is the missing contract.

### 4.5 Containers, images, build context (Docker mental model)

**The Why.** "Works on my machine" dies here: a container packages the app *and its entire userland* (Python version, libs) so it runs identically everywhere. For you, it also means the .NET and Python services can sit on one virtual network and call each other by name.

**The Theory.**

| Term | Embedded analogy | Meaning |
|------|------------------|---------|
| **Image** | A flashed firmware `.bin` | Immutable, built once, read-only template |
| **Container** | A running MCU executing that firmware | A live process started from an image |
| **Build context** | The source folder you compile | The directory tree handed to `docker build` |
| **Dockerfile** | Your build recipe / Makefile | Steps to produce the image |
| **Layer** | — | Each instruction is a cached layer; order them cheap→expensive for cache hits |

Your .NET Dockerfile already demonstrates a **multi-stage build** (build with the heavy SDK image, copy only the published output into a slim runtime image). That's a best practice — smaller, fewer attack surfaces. Good instinct.

**The Implementation.** Bug A is a *build context* error: `langchain_service` points its context at `./server`, so it builds .NET. The fix is conceptual, not cosmetic — you're telling the builder to compile the wrong tree.

### 4.6 Flask as a WSGI app + the `__main__` guard

**The Why.** Flask maps URLs to Python functions. But "run the server" and "import this module" must be distinguishable, or importing your code would accidentally launch a server.

**The Theory.** `if __name__ == "__main__":` is true only when the file is executed directly (`python main.py`), false when imported. Your `"main"` typo makes it never true. Separately, `flask run` is a *different* launch mechanism that finds the app via the `FLASK_APP` env var and ignores `app.run()` entirely. Pick one launch story and make it coherent (e.g., set `FLASK_APP=main.py` and `EXPOSE 5000` in the Dockerfile, or run `python main.py` with the guard fixed).

### 4.7 Service readiness vs. liveness (`depends_on` trap)

**The Why.** Bug J. In distributed systems, "the process started" and "the process can serve requests" are different moments. Your .NET server might fire its first request at Flask before Flask's HTTP server is listening → connection refused.

**The Theory.** Two health signals:
- **Liveness**: is the process alive? (don't kill/restart it)
- **Readiness**: can it accept traffic *right now*? (route to it)

`depends_on: [langchain_service]` only waits for the container to *start*. To wait for *ready*, add a **healthcheck** to Flask and `depends_on: { langchain_service: { condition: service_healthy } }`. Even then, the robust pattern is **retries on the caller side** — the network can drop any time, so your .NET `HttpClient` should retry transient failures (a "resilience policy"). This is the eventually-consistent, design-for-failure thinking you wanted to build.

---

## 5. The Full Request/Response Lifecycle — and the shape of every object

This is the heart of your question. Below is the end-to-end path and **what the data looks like at each hop**. Treat each numbered boundary as a place where an object is serialized to JSON and reconstructed on the other side.

### 5.1 The sequence diagram

```
┌────────┐        ┌────────────────────┐        ┌──────────────────────┐      ┌──────────────┐
│  USER  │        │   .NET SERVER      │        │   FLASK (main.py)    │      │  LANGCHAIN   │
│ (curl/ │        │  (Edge / API)      │        │  (HTTP adapter)      │      │  (lang.py)   │
│  app)  │        │                    │        │                      │      │ in-process   │
└───┬────┘        └─────────┬──────────┘        └──────────┬───────────┘      └──────┬───────┘
    │  (1) HTTP POST /api/chat                              │                          │
    │  { userId, message }                                  │                          │
    │ ───────────────────────▶│                             │                          │
    │                         │  Telemetry middleware       │                          │
    │                         │  starts stopwatch           │                          │
    │                         │                             │                          │
    │                         │  (2) HTTP POST /process     │                          │
    │                         │  { text, conversationId }   │                          │
    │                         │ ───────────────────────────▶│                          │
    │                         │                             │ (3) plain string call    │
    │                         │                             │ invoke_langchain(text)   │
    │                         │                             │ ────────────────────────▶│
    │                         │                             │                          │ LLM runs
    │                         │                             │ (4) AIMessage / str      │◀── returns
    │                         │                             │◀─────────────────────────│
    │                         │  (5) HTTP 200               │                          │
    │                         │  { status, data:{...} }     │                          │
    │                         │◀────────────────────────────│                          │
    │                         │  stopwatch stops;           │                          │
    │                         │  enrich + log telemetry     │                          │
    │  (6) HTTP 200           │                             │                          │
    │  { reply, metadata }    │                             │                          │
    │◀────────────────────────│                             │                          │
```

### 5.2 Object shape at each boundary

Think of each boundary as a **DTO (Data Transfer Object)** — a flat, serializable struct whose only job is to cross the wire. DTOs are deliberately dumb (no behavior), the opposite of rich domain objects.

**Boundary (1) — User → .NET** `POST /api/chat`
```json
{
  "userId": "user-123",
  "message": "What's the weather like over there?"
}
```
- Minimal: who is asking + the raw text. (Add auth via an `Authorization` header, not the body.)
- In C# this deserializes into a record like `ChatRequest(string UserId, string Message)`.

**Boundary (2) — .NET → Flask** `POST http://langchain_service:5000/process`
```json
{
  "text": "What's the weather like over there?",
  "conversationId": "conv-abc-789",
  "requestId": "a1b2c3"
}
```
- The .NET server *unwraps* the user envelope and forwards just what the intelligence plane needs: the **pure text**, plus correlation IDs so a single conversation is traceable across both services. This is exactly the "process the request into the pure text" step you described.
- Note the host is the **service name** `langchain_service`, not `localhost` (Module 6).

**Boundary (3) — Flask → LangChain** (in-process Python call, *not* HTTP)
```python
invoke_langchain(text: str) -> ...
```
- This crossing is cheap: same process, a normal function call passing a `str`. No serialization. Flask's only job here is to be the **HTTP adapter** that turns a JSON request into a Python function call.
- Today your `invoke_langchain()` takes **no argument** and hardcodes the prompt — so the user's text is dropped on the floor. It must accept `text`.

**Boundary (4) — LangChain → Flask** (return value)
```python
# response = model.invoke(text)  → an AIMessage
response.content   # → "Hello from mock agent"   (a plain string)
```
- `invoke()` returns a **message object**, not a string. The text is in `.content`. (Bug D: you returned `model.response`.)
- This is where, in the real version, you'd *also* compute sentiment, topic, and the policy/RAG check — so the function returns a richer dict, not just a string.

**Boundary (5) — Flask → .NET** HTTP 200 response
```json
{
  "status": "success",
  "data": {
    "reply": "Hello from mock agent",
    "sentiment": "neutral",
    "topic": "weather",
    "policyViolation": false,
    "violationReason": null,
    "tokenUsage": { "prompt": 12, "completion": 5 }
  }
}
```
- Flask returns a **standardized envelope**: a top-level `status` + a `data` payload. This is the "standardized format with the LLM response inside it" you intuited. Standardizing the envelope means the .NET side has *one* parsing path for success and one for error.
- Error shape should be symmetrical, e.g. `{ "status": "error", "error": { "code": "MODEL_TIMEOUT", "message": "..." } }`.

**Boundary (6) — .NET → User** HTTP 200 response
```json
{
  "reply": "Hello from mock agent",
  "metadata": {
    "sentiment": "neutral",
    "topic": "weather",
    "policyViolation": false
  },
  "latencyMs": 1840,
  "requestId": "a1b2c3"
}
```
- The .NET server does the final shaping: it strips internal fields the user shouldn't see, attaches the **latency it measured** in the telemetry middleware (the thing Flask *can't* know, because only the edge sees the total round trip), and returns a clean response.
- Simultaneously (this is the project's real purpose) it writes a telemetry record — `{requestId, userId, path, statusCode, latencyMs, sentiment, topic, policyViolation, timestamp}` — to your future datastore.

### 5.3 Why this shape, not a simpler one?

| Design choice | Why | Alternative & tradeoff |
|---------------|-----|------------------------|
| .NET re-wraps instead of proxying raw | The edge owns auth, validation, telemetry, and response shaping; Flask stays a pure LLM worker | A dumb reverse proxy (YARP) — faster, but then *something* still has to do the enrichment |
| Correlation/request IDs on every hop | One conversation is traceable across 2 services and your logs — essential for debugging distributed systems | Omit them — but then a failure is unattributable across services |
| Standardized `{status, data}` envelope | Single success/error parse path; versionable | Return bare data — simpler but brittle when errors happen |
| Latency measured at the edge | Only the edge sees the *total* user-perceived time | Measure in Flask — misses network + queueing time |

**Interview relevance:** being able to draw exactly this diagram and justify each DTO boundary is a standard system-design-interview skill. The phrase to use is "I separate the **edge/API gateway concern** from the **compute/worker concern**, and define explicit DTO contracts at each boundary with correlation IDs for traceability."

---

## 6. How the containers find and call each other

This trips up nearly everyone moving from one process to many. The rules:

**Rule 1 — Same Compose file = same default network.** Docker Compose puts every service on one virtual network and registers each **service name as a DNS hostname**. So from inside the `dotnet_server` container, the URL to reach Flask is:
```
http://langchain_service:5000
```
`langchain_service` resolves to Flask's container IP automatically. You never hardcode IPs.

**Rule 2 — Use the *container* port, not the *host* port.** A mapping `"5001:5000"` means **host:container**. Service-to-service traffic stays *inside* the Docker network, so it uses the **container** port (`5000`), **not** the published host port (`5001`). The host port only matters for *you* hitting it from your laptop (`localhost:5001`).

```
   YOUR LAPTOP                         DOCKER NETWORK "llm_monitor_default"
┌───────────────┐    publish 5000:8080   ┌────────────────────────────────────┐
│ localhost:5000│ ─────────────────────▶ │ dotnet_server  ── http://langchain_│
└───────────────┘                        │                   service:5000 ───┐ │
                                         │                                   ▼ │
                                         │                       langchain_service (Flask :5000)
                                         └────────────────────────────────────┘
```

**Rule 3 — `localhost` inside a container means *that container*, not your laptop.** A frequent bug: .NET code calling `http://localhost:5000` reaches *itself*, not Flask. Always use the service name.

**Rule 4 — Only publish what the outside world needs.** Your databases and the Flask service ideally have **no host port mapping** — only the edge (.NET, or later a YARP gateway) is reachable from your laptop. Everything else talks over the internal network. This is both safer and the more professional topology.

**Applying it to your repo:** once Bug A is fixed (correct build context) and Bug I (`5000:8080`), your .NET server will call `http://langchain_service:5000/process`. Flask's internal port is 5000, which matches.

---

## 7. A sustainable build/run script

You asked specifically: how do I script `docker compose` so that I (a) never run stale containers, (b) don't clutter my disk after repeated runs, and (c) get the services networked and talking. Here's the conceptual toolkit, then a reference script.

### 7.1 The commands and what each guarantees

| Command | What it guarantees | Why you care |
|---------|--------------------|--------------|
| `docker compose down --remove-orphans` | Stops & removes the containers from this project, plus "orphan" containers from services you renamed/deleted | Kills **stale containers** so you never run yesterday's build |
| `docker compose build` *or* `up --build` | Rebuilds images from current source | New code actually ships; `--build` is the fix for "why are my changes not showing?" |
| `docker compose up` | Creates network + starts everything | The network is what makes Rule 1 (service-name DNS) work |
| `--force-recreate` | Recreates containers even if config looks unchanged | Defeats subtle caching of container state |
| `-d` | Detached (background) | Optional; omit it to watch logs live |
| `docker image prune -f` | Deletes **dangling** images (old layers orphaned by `--build`) | This is your **anti-clutter** command — repeated `--build` leaves `<none>` images that eat disk |

**The key insight for "no clutter":** every time you `--build`, the *previous* image for that tag becomes dangling (untagged `<none>`). They pile up. `docker image prune` sweeps them. Build cache also grows; `docker builder prune` reclaims that.

> **Careful with volumes.** `docker compose down -v` (or `--volumes`) **deletes named volumes** too. Once you add Postgres, that flag wipes your database. Use plain `down` for day-to-day; only use `-v` when you deliberately want a clean DB. Know the difference *before* you have data you care about.

### 7.2 Reference script (conceptual — yours to adapt)

```bash
#!/usr/bin/env bash
# build.sh — sustainable rebuild-and-run for LLM_Monitor
set -euo pipefail          # fail fast: -e exit on error, -u undefined vars, -o pipefail

PROJECT="llm_monitor"

echo "▶ Tearing down any previous run (containers + orphans)…"
docker compose -p "$PROJECT" down --remove-orphans

echo "▶ Building images from current source…"
docker compose -p "$PROJECT" build

echo "▶ Starting services on the shared network…"
docker compose -p "$PROJECT" up --force-recreate -d

echo "▶ Reclaiming disk from dangling images…"
docker image prune -f

echo "✔ Up. Tail logs with:  docker compose -p $PROJECT logs -f"
```

Why this is "sustainable":
- **No stale containers:** `down --remove-orphans` first, `--force-recreate` on `up`.
- **No clutter:** `image prune -f` after each build sweeps dangling images; named volumes are preserved (no `-v`).
- **Networked & talking:** `up` (without `-p` collisions) creates one network so service-name DNS works; your services reach each other via `http://<service_name>:<container_port>`.
- **`-p llm_monitor`** pins the project name so you don't accidentally create parallel stacks under different names (another source of clutter).

**Optional graceful-stop pattern** (for a foreground dev script): use a shell `trap` so Ctrl-C runs `docker compose down` automatically:
```bash
trap 'docker compose -p "$PROJECT" down' EXIT
docker compose -p "$PROJECT" up --build --force-recreate   # foreground; Ctrl-C cleans up
```

**Common mistakes this avoids:**
- Running `up` repeatedly without `--build` → old image, "my fix didn't work."
- Never pruning → tens of GB of `<none>` images after a week.
- Using `down -v` habitually → silently wiping your future database.
- Different project names each run → multiple orphaned stacks competing for ports.

---

## 8. Mental Sandbox & Next Steps

Work these in order; each builds the muscle you flagged as weak.

1. **Fix the boundary bugs first (A–D).** Get one real round trip working: `curl` a POST to the .NET server, watch it reach Flask, watch Flask return the mock string. *Goal:* feel the serialize→travel→deserialize cycle once, concretely.

2. **Make the telemetry middleware real.** Add a `Stopwatch` around `_next`, log `{path, status, elapsedMs, requestId}`. *Question to answer for yourself:* why must the stopwatch wrap `_next` rather than sit inside the endpoint? (Answer: only the middleware sees the *whole* downstream cost, including the Flask call.)

3. **Design for failure.** Make Flask `time.sleep(30)` on purpose. What does the user experience? Now add a timeout + one retry to the .NET `HttpClient`. *Concept:* resilience policies, the practical face of "design for partial failure."

4. **Add readiness, not just start order.** Give Flask a `/health` route, add a Compose healthcheck, switch `depends_on` to `condition: service_healthy`. Then ask: *is that enough, or do I still need caller-side retries?* (It isn't; you do. That's the eventually-consistent mindset.)

5. **Introduce the data plane.** Add Postgres to Compose (uncomment + fix), and write one telemetry row per request. Then add `pgvector` and a tiny policy doc → your first RAG check. *Concept:* embeddings + semantic search as the mechanism behind "did this message violate policy?"

6. **Stretch / interview rep:** on a whiteboard, reproduce the Section 5 diagram from memory and defend every DTO field. If you can explain *why the latency is measured at the edge and not in Flask*, you understand the edge/worker split that this entire architecture rests on.

---

### Appendix — concept-to-weakness map (from your `persona.md`)

| Your stated weakness | Where this project exercises it |
|----------------------|--------------------------------|
| Async/await internals | §4.3 — awaiting the slow Flask hop without blocking the thread pool |
| Coordination between services | §4.7, §6 — readiness, retries, service discovery by DNS name |
| Event-driven / eventual consistency | §8.3–8.4 — failure injection, retries, "up ≠ ready" |
| Large system design | §1, §5.3 — three planes, edge/worker split, DTO contracts |
| Reading large codebases | this doc's top-down order: architecture → components → control flow → code |

*End of document. Nothing else in the project was modified.*
