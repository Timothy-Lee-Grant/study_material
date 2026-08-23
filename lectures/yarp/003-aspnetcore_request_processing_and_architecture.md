# Lecture 3: ASP.NET Core Request Processing and Application Architecture

Series: YARP Learning Series
Builds on: [Lecture 1 — HTTP](001-http_from_the_wire_to_the_application.md) (the message format Kestrel parses and produces), [Lecture 2 — TCP/IP/Sockets](002-tcp_ip_sockets_and_network_connections.md) (the connection mechanics Kestrel sits directly on top of).
Prepares you for: reading YARP's actual source — `ReverseProxyServiceCollectionExtensions`, `MapReverseProxy`, `HttpForwarder`, cluster/route configuration — and recognizing that YARP is not a separate program bolted onto ASP.NET Core, it *is* an ASP.NET Core application, built entirely from the pieces in this lecture.

---

## 1. Learning Objectives

By the end of this lecture you should be able to:

1. Explain what Kestrel actually is, and place it precisely on the stack from Lecture 2 (it's the code that turns "accepted socket" into "parsed `HttpContext`").
2. Trace a request through the middleware pipeline and correctly predict, for a given ordering, which middleware runs, in what order, and whether/where the pipeline short-circuits.
3. Explain the three DI lifetimes and diagnose a lifetime-mismatch bug ("captive dependency") in a code sample.
4. Explain, mechanically, why `async`/`await` lets one thread serve many concurrent requests, without invoking "it spawns a new thread" as an explanation.
5. Explain what `HttpContext` is and isn't, and how it relates to the raw HTTP message from Lecture 1.
6. Explain endpoint routing as a two-phase process (match, then execute) and why that split exists.
7. Explain how configuration and structured logging are treated as first-class, environment-aware concerns rather than hardcoded values.
8. Place YARP precisely within this architecture: which ASP.NET Core building block does each part of YARP's job, and why building a proxy *as* an ASP.NET Core app (rather than a bespoke standalone program) is a deliberate, load-bearing design choice.

---

## 2. Prerequisite Concepts

You've got professional C# experience, so I won't re-teach classes, interfaces, generics, or `async`/`await` syntax as C# language features. What I will teach, because it's genuinely ASP.NET-specific and not general C# knowledge, is *why* the framework is built the way it is — the architectural reasoning, not the syntax.

Two things from earlier lectures are load-bearing here, so a fast recap:

- **Lecture 2 §7.3**: a server `bind()`s a port, `listen()`s, and `accept()`s a stream of new sockets, one per incoming client connection. Kestrel is the concrete C# implementation of exactly that loop.
- **Lecture 1 §4.3**: an HTTP message is just structured text (or binary frames, in HTTP/2+) — method, path, headers, body. Kestrel's other job is turning the raw bytes arriving on an accepted socket into that structured form your C# code can actually work with — an object called `HttpContext`, which is the spine of this entire lecture.

---

## 3. Core Mental Model

```
   Operating System                  ASP.NET Core Application Process
  ┌──────────────────┐              ┌───────────────────────────────────────────┐
  │  accepted socket   │  ────────►  │  Kestrel: parses bytes into HttpContext     │
  │  (Lecture 2 §7.3)  │              │        │                                    │
  └──────────────────┘              │        ▼                                    │
                                     │  Middleware pipeline (you write this)        │
                                     │        │                                    │
                                     │        ▼                                    │
                                     │  Endpoint (your route handler / controller /  │
                                     │            YARP's forwarding endpoint)         │
                                     │        │                                    │
                                     │        ▼                                    │
                                     │  Response written back onto HttpContext       │
                                     │        │                                    │
                                     │        ▼                                    │
                                     │  Kestrel: serializes HttpContext back to       │
                                     │           bytes on the same socket             │
                                     └───────────────────────────────────────────┘
```

The single sentence to hold onto: **ASP.NET Core is a set of composable building blocks (a server, a pipeline, a DI container, a config system, a logging system) that all revolve around one shared object per request — `HttpContext` — and everything this lecture teaches is really "what is `HttpContext`, who touches it, and in what order."**

---

## 4. Kestrel — The HTTP Server

### 4.1 What Kestrel is, precisely

Kestrel is a **managed, cross-platform HTTP server implementation, written in C#, that runs inside your application's own process.** This is worth pausing on, because it differs from an older, more familiar mental model (a separate program like nginx or IIS sitting in front of your app and forwarding to it): Kestrel *is* your app's networking layer, compiled in — there's no separate process boundary between "the web server" and "your code" by default.

Concretely, Kestrel is responsible for exactly the things from Lecture 2 §7.3 and Lecture 1 §4.3–§4.9, and nothing more:

- Owning the listening socket(s) — `bind()` + `listen()` + `accept()` loop (Lecture 2 §7.3).
- Speaking the actual wire protocol — HTTP/1.1, HTTP/2, or HTTP/3 (Lecture 1 §6–§8) — parsing incoming bytes into a structured request, and serializing an outgoing response back into correctly-framed bytes.
- Managing the TCP/QUIC connection lifecycle underneath each request (Lecture 2 §6, §13) — including keep-alive, multiplexed streams, and connection-level timeouts.
- Handing each parsed request to your application as an `HttpContext` object (§6 below), and taking back whatever your application writes to that object's response, to send it out.

Kestrel is explicitly **not** responsible for: routing decisions, authentication/authorization logic, business logic, or anything about *what* a request means — that's all your application's job, expressed through the pieces in §5 onward. This split matters because it's precisely the same separation-of-concerns idea from Lecture 2 §3 (each layer solves one problem) applied one layer higher: Kestrel solves "get well-formed HTTP messages in and out reliably," and deliberately knows nothing about what those messages *mean*.

### 4.2 Kestrel can optionally sit behind another proxy

In many production deployments, Kestrel doesn't face the public internet directly — it sits behind something like nginx, a cloud load balancer, or (notably, for this series) YARP itself, which terminates the client connection and forwards to Kestrel over its own separate connection (exactly the two-leg topology from Lecture 2 §15.3). This is a deployment choice, not a requirement — Kestrel is fully capable of serving public internet traffic directly, and increasingly does in modern deployments. The key thing to internalize: whether or not something sits in front of it, Kestrel's job within the process is identical either way.

---

## 5. Hosting — How the Process Boots

Before any request can be handled, something has to actually start the process, build the application's configuration, DI container, and pipeline, and start Kestrel listening. This is called **hosting**, and in modern ASP.NET Core it's expressed compactly:

```csharp
var builder = WebApplication.CreateBuilder(args);

// ---- registration phase: describe what the app NEEDS ----
builder.Services.AddControllers();
builder.Services.AddSingleton<IUserRepository, SqlUserRepository>();
builder.Services.AddHttpClient();

var app = builder.Build();   // <- DI container is finalized here

// ---- pipeline phase: describe what happens PER REQUEST, in order ----
app.UseHttpsRedirection();
app.UseAuthentication();
app.UseAuthorization();
app.MapControllers();

app.Run();   // <- starts Kestrel, blocks until shutdown
```

Two distinct phases worth explicitly separating, because conflating them is a common source of confusion when reading unfamiliar `Program.cs` files:

1. **Registration phase** (`builder.Services.Add...`) — declarative: "here is everything this app might need, and how to construct it." Nothing runs yet.
2. **Pipeline phase** (`app.Use...`, `app.Map...`) — also declarative at startup, but it's building the *sequence of steps* that will run for every future incoming request. Still nothing runs yet — you're describing the pipeline, not executing it.

Only `app.Run()` actually starts Kestrel and begins accepting connections — at which point requests start flowing through everything you described above, per-request, repeatedly, for the life of the process. `IHostedService` is the mechanism for running your *own* long-lived background work (not tied to any individual request) alongside request handling in the same process — worth recognizing the name, not something you need depth on for this series.

---

## 6. HttpContext

### 6.1 What it represents

`HttpContext` is a single object, created fresh by Kestrel for each incoming request, that bundles together everything about that one request/response exchange: the parsed request (method, path, headers, body stream, query string), a mutable response object you write status/headers/body to, the connection's metadata (remote IP, TLS info), and — critically — a per-request **DI scope** (§7.2) that request-scoped services live in.

```csharp
// Just enough to make it concrete — this is literally reading the pieces
// from Lecture 1 §4.3's raw message, now as structured C# objects:
string method   = context.Request.Method;              // "GET"
string path     = context.Request.Path;                // "/v1/users/42"
string? auth    = context.Request.Headers["Authorization"];
Stream body     = context.Request.Body;                // readable, potentially STREAMED (Lecture 1 §9)

context.Response.StatusCode = 200;
context.Response.Headers["Content-Type"] = "application/json";
await context.Response.WriteAsync("{\"id\":42}");
```

### 6.2 What it is *not*

`HttpContext` is not the raw bytes, and it's not the TCP connection itself — it's an application-layer abstraction Kestrel constructs *from* those things (per §4.1's separation of concerns). It's also **not durable** — it exists only for the lifetime of that one request; nothing about it is preserved automatically between one request and the next (recall Lecture 1 §4.1 — HTTP itself is stateless; `HttpContext` reflects that faithfully, it doesn't fight it).

### 6.3 Why every piece of this lecture revolves around it

Every concept from here on — middleware, DI scoping, routing, logging — either **reads from** `HttpContext`, **writes to** `HttpContext`, or **governs how long something lives relative to** `HttpContext`'s own (short, per-request) lifetime. Keep it in view; it's the thread connecting the rest of this lecture together, exactly as promised in §3.

---

## 7. Middleware — The Pipeline, Deeply

This is the section you flagged as needing depth, so we'll go slowly and mechanically.

### 7.1 The shape

```
 Request
    │
    ▼
┌─────────────┐
│ Middleware A │──── code before next() ────┐
└─────────────┘                             │
    │                                        ▼
    ▼                                 ┌─────────────┐
┌─────────────┐                       │ Middleware B │──── code before next() ────┐
│ Middleware A │◄──── code after ─────└─────────────┘                             │
│ (continued)  │      next() returns                                              ▼
└─────────────┘                                                            ┌─────────────┐
    │                                                                      │ Middleware C │──── code before next() ────┐
    ▼                                                                      └─────────────┘                             │
 Response                                                                          │                                    ▼
                                                                                    ▼                              ┌──────────┐
                                                                             ┌─────────────┐                       │ Endpoint  │
                                                                             │ Middleware C │◄──── after next() ───└──────────┘
                                                                             │ (continued)  │
                                                                             └─────────────┘
```

That diagram is deliberately busy because it's showing something the flat version you sketched hides: **middleware isn't a one-way conveyor belt — it's nested calls.** Each middleware can run code *before* calling `next()`, and code *after* `next()` returns. The request travels **down** through A→B→C→Endpoint, and the response travels back **up** through C→B→A, in exact reverse order. This is structurally identical to a call stack — because that's literally what it is; each middleware calls the next one as a function, and execution unwinds back through each caller once the callee returns.

### 7.2 A concrete middleware, written out

```csharp
app.Use(async (context, next) =>
{
    // ---- runs on the way DOWN (request processing) ----
    var stopwatch = Stopwatch.StartNew();
    logger.LogInformation("Request started: {Method} {Path}",
        context.Request.Method, context.Request.Path);

    await next(context);   // <- hands control to the NEXT middleware in the pipeline

    // ---- runs on the way UP (response processing) ----
    logger.LogInformation("Request finished: {StatusCode} in {ElapsedMs}ms",
        context.Response.StatusCode, stopwatch.ElapsedMilliseconds);
});
```

Walk through this literally: the logging call *before* `await next(context)` happens as the request is heading toward the endpoint. Everything between that line and the logging call *after* it — every other middleware, and the endpoint itself — runs while this middleware's stack frame is suspended, waiting on `next()`. Once the endpoint finally produces a response and every downstream middleware finishes its own "after `next()`" code, control unwinds back here, `next(context)` returns, and this middleware's *second* log line runs, now knowing the actual status code and elapsed time — because the entire rest of the pipeline has, by this point, already fully executed.

This is exactly why this single middleware, placed *first* in the pipeline, can measure the total time and final status code for the *entire* request — it's not special access to some framework hook, it's simply "the outermost function call in the stack, so its post-`next()` code is the last thing to run before the response actually goes out."

### 7.3 Short-circuiting

A middleware is not obligated to call `next()` at all. If it doesn't, the pipeline stops right there — nothing downstream (no further middleware, no endpoint) ever runs, and whatever the middleware itself wrote to `context.Response` is what goes back to the client.

```csharp
app.Use(async (context, next) =>
{
    if (!context.Request.Headers.ContainsKey("Authorization"))
    {
        context.Response.StatusCode = 401;
        await context.Response.WriteAsync("Missing Authorization header");
        return;   // <- next() is NEVER called. Pipeline stops here.
    }

    await next(context);   // only reached if the check above passed
});
```

This is not an edge case — it's one of the most common and important patterns in the entire framework. Authentication checks, rate limiting, static file serving (if the file exists, serve it and stop — never bother reaching your actual application code), and caching (if there's a valid cached response, return it immediately) are all naturally expressed as "short-circuit if X, otherwise call `next()`." Recognizing "does this middleware unconditionally call `next()`, or is there a code path that returns without it?" is a genuinely important skill for reading pipeline code correctly.

### 7.4 Why ordering matters — a concrete failure

```csharp
// WRONG ORDER — authorization runs before authentication has identified anyone
app.UseAuthorization();
app.UseAuthentication();

// CORRECT ORDER — you must know WHO the caller is before you can decide
// WHAT they're allowed to do
app.UseAuthentication();
app.UseAuthorization();
```

Since middleware executes strictly in registration order on the way down (§7.1), swapping these two lines is a genuine, working-but-wrong bug — `UseAuthorization` would run before `UseAuthentication` has populated `context.User`, so every authorization check would be evaluating against an unauthenticated (or stale) identity. The pipeline doesn't error out — it just silently does the wrong thing, which is precisely why middleware ordering deserves careful, deliberate attention rather than being treated as incidental.

A second, equally common ordering concern: exception-handling middleware (`app.UseExceptionHandler(...)`) must be registered **first**, before everything else, specifically *because* of the call-stack structure from §7.1/§7.2 — being outermost is what lets it catch an exception thrown by *any* middleware or endpoint further down the stack, since a thrown exception unwinds back up through exactly the same nested calls a normal `next()` return does.

### 7.5 Request processing vs. response processing, as one continuous thing

It's tempting to think of "handling the request" and "producing the response" as two separate stages. The nested-call structure from §7.1 shows they're actually one continuous, single pass through the pipeline — there's no separate "response pipeline" that runs afterward; it's the *same* middleware instances, resuming exactly where they left off, once `next()` returns. This is worth internalizing precisely because it explains why a single middleware (like the logging example in §7.2) can meaningfully participate in both "request time" and "response time" behavior without being written twice.

---

## 8. Dependency Injection

### 8.1 The problem DI solves

Without DI, a class that needs a dependency (say, an `HttpClient` for calling a backend, or a logger) has to construct it itself — which hardcodes *which concrete implementation* it uses, makes swapping implementations (e.g., for testing) painful, and scatters "how do I build a properly-configured X" logic throughout the codebase instead of centralizing it. DI inverts this: a class **declares what it needs** (via its constructor), and a central **container** is responsible for constructing and supplying it, based on rules registered once at startup (§5's registration phase).

```csharp
public class UserService
{
    private readonly IUserRepository _repository;
    private readonly ILogger<UserService> _logger;

    // UserService doesn't know or care HOW these are constructed —
    // it just declares that it needs them, and the DI container
    // supplies concrete instances when UserService itself is constructed.
    public UserService(IUserRepository repository, ILogger<UserService> logger)
    {
        _repository = repository;
        _logger = logger;
    }
}
```

### 8.2 Service registration and the three lifetimes

At startup (§5), you tell the container: "when something asks for interface `X`, here's how to build a concrete instance, and here's how long that instance should live":

```csharp
builder.Services.AddSingleton<IConfigCache, ConfigCache>();   // one instance, whole app lifetime
builder.Services.AddScoped<IUserRepository, SqlUserRepository>();  // one instance PER REQUEST
builder.Services.AddTransient<IEmailValidator, EmailValidator>();  // new instance EVERY time it's requested
```

- **Singleton**: exactly one instance exists for the entire application's process lifetime, shared across every request, forever. Use for things that are expensive to build, stateless (or safely thread-shared), and meant to be reused — a connection pool manager is a textbook example.
- **Scoped**: one instance per `HttpContext` (§6) — created the first time something asks for it during a given request, and reused for the rest of *that same request* if asked for again, then discarded once the request completes. Most things that touch per-request state (a database context tracking changes for this request, a "current user" accessor) are scoped.
- **Transient**: a brand-new instance is constructed **every single time** it's requested, even multiple times within the same request. Use for small, cheap, stateless objects where sharing an instance provides no benefit and could even be actively wrong (e.g., if it were to accidentally hold state).

### 8.3 Lifetime problems — the captive dependency

Here's a bug pattern worth understanding precisely, because it's subtle, common, and directly relevant to how a proxy manages backend connections (Lecture 2's whole point about connection reuse):

```csharp
// SINGLETON holding a reference to a SCOPED dependency — this is a bug.
public class BrokenCache // registered as Singleton
{
    private readonly IUserRepository _repo; // registered as Scoped

    public BrokenCache(IUserRepository repo)
    {
        _repo = repo;   // captured ONCE, at singleton construction time
    }
    // every future call through this singleton uses the SAME repo
    // instance, forever — even though IUserRepository was designed
    // to be fresh-per-request (e.g., it wraps a per-request DB
    // connection/transaction).
}
```

Because `BrokenCache` is constructed exactly once (singleton semantics, §8.2), whatever scoped instance the container hands it at that moment gets **captured and held forever** — defeating the entire point of "scoped" (fresh per request) and, depending on what the scoped service actually wraps (a database connection, a request-specific identity), potentially causing real correctness bugs (serving request #500's data using a dependency instance that was actually built for request #1) or resource bugs (holding a connection open indefinitely that was meant to be short-lived). This is called a **captive dependency**, and ASP.NET Core's DI container will, by default, throw an exception at startup if you register a singleton that directly depends on a scoped service in its constructor — precisely *because* this bug class is common and dangerous enough to be worth failing fast on, rather than silently misbehaving in production.

### 8.4 Why infrastructure software leans on DI so heavily

Infrastructure code — exactly the category YARP falls into — has an unusually large number of pluggable, swappable, environment-dependent concerns: which load-balancing algorithm to use, how to discover backend destinations, what HTTP client configuration to use for outbound calls, what logging/metrics backend to report to. DI lets each of these be registered independently, swapped for testing or for different deployment environments, and composed together without any single class needing to know how to construct all its own dependencies by hand. It also means YARP itself can be *extended* by consumers — you can register your *own* implementation of a YARP extensibility interface (a custom load-balancing policy, a custom transform) and the container will wire it in exactly where YARP's own code expects to find one, without YARP's source needing to change at all. This extensibility-via-registration pattern is worth watching for specifically once you start reading YARP's actual configuration code.

---

## 9. Async Programming

### 9.1 What `async`/`await` actually does — and doesn't do

The single most important correction here: **`await` does not create a new thread.** What it actually does: when your code hits an `await` on an operation that isn't finished yet (most commonly, waiting on network I/O — reading from a socket, exactly the kind of operation Lecture 2 described), the current method **returns control to its caller immediately**, freeing up the thread that was running it. The thread goes back to the thread pool and is available to do other work — including running some completely unrelated request's code. When the awaited operation actually completes (data arrives on the socket), the runtime schedules the *rest* of your method to resume — on some available thread from the pool, not necessarily the original one.

```csharp
public async Task<User> GetUserAsync(int id)
{
    // Below this line, if the HTTP call isn't instantly complete,
    // the CURRENT THREAD is released back to the pool. It does NOT
    // sit here blocked, and no new thread is spawned to "wait" either.
    var response = await httpClient.GetAsync($"/v1/users/{id}");

    // Once the response actually arrives, this line resumes —
    // possibly on a DIFFERENT thread than the one that started this method.
    return await response.Content.ReadFromJsonAsync<User>();
}
```

### 9.2 The mechanism, one level deeper

Under the hood, the C# compiler transforms an `async` method into a **state machine** — an object that remembers "which `await` am I currently paused at" and holds onto whatever local state it needs to resume correctly. When you `await` something, you're really registering "call me back (resume this state machine) when this operation finishes" and returning immediately. The underlying I/O itself is handled by the operating system asynchronously — recall Lecture 2 §7.2: a `send()`/`recv()` call doesn't block the calling code waiting for actual network completion; the OS notifies the runtime when data is ready, and the .NET thread pool picks up the "resume this state machine" work at that point. No thread is ever sitting idle, spin-waiting on a socket, for the duration of an `await` on I/O — this is precisely why it's called **asynchronous I/O**, as distinct from a thread that blocks (occupies itself doing nothing) while waiting.

### 9.3 Why this matters for handling many simultaneous requests

Here's the payoff, stated directly: if handling a request required one thread to be **blocked**, dedicated, for the entire duration of that request (including all the time spent waiting on a slow database, a slow backend call, a slow disk read), then the number of requests a server could handle *concurrently* would be hard-capped at its thread pool size — typically a fairly small number relative to real production load, because threads are relatively expensive OS resources (each one needs its own stack memory, and context-switching between many of them isn't free).

With `async`/`await`, a thread is only ever occupied doing *actual CPU work* — parsing, computing, serializing. The moment a request's processing hits an I/O wait (a call to a backend, a database query), that thread is freed to go serve a *completely different* request's CPU work in the meantime. This is exactly how a modestly-sized thread pool can have thousands of requests "in flight" simultaneously, the overwhelming majority of them just sitting suspended waiting on I/O, costing almost nothing while they wait.

```
BLOCKING model (bad):                     ASYNC model (good):

  Thread 1 ─── [stuck on request A's DB call, doing NOTHING] ───
  Thread 2 ─── [stuck on request B's DB call, doing NOTHING] ───
  Thread 3 ─── [stuck on request C's DB call, doing NOTHING] ───
                                                                    Thread 1 ─[A CPU]─[B CPU]─[C CPU]─[A CPU]─...
  ...only as many concurrent requests as                                    (freed during A's DB wait, picks up
     you have threads, and most of them                                      B's work, then C's, then resumes
     are doing nothing useful at all                                         A once A's DB call returns)
```

### 9.4 Cancellation tokens

A `CancellationToken` is how "stop what you're doing" propagates through an async call chain — exactly the mechanism referenced abstractly in Lecture 1 §10.4 and Lecture 2 §15.2. It's passed as a parameter down through every layer of `await`ed calls, and each layer that supports cancellation checks it periodically (or is itself built on lower-level operations that check it, like an HTTP call or a database query).

```csharp
public async Task<User> GetUserAsync(int id, CancellationToken cancellationToken)
{
    // If the caller cancels (e.g., because the original CLIENT
    // disconnected — Lecture 2 §10.6), this call can abort promptly
    // instead of running to completion pointlessly.
    var response = await httpClient.GetAsync($"/v1/users/{id}", cancellationToken);
    return await response.Content.ReadFromJsonAsync<User>(cancellationToken: cancellationToken);
}
```

In ASP.NET Core, `HttpContext.RequestAborted` is a `CancellationToken` that fires automatically when the underlying client connection is closed early — meaning the framework has already wired up exactly the "client disconnected, stop doing wasted work" signal from Lecture 2 §15.2 for you; your job is just to make sure you actually pass that token down through every `await` in your own code so it can take effect.

---

## 10. Routing

### 10.1 The two-phase model

ASP.NET Core's endpoint routing deliberately separates **matching** from **executing**, as two distinct middleware-pipeline stages:

```csharp
app.UseRouting();       // PHASE 1: examine the request, decide WHICH endpoint matches — but don't run it yet
// ... other middleware can run here, now that the match is already known ...
app.UseAuthorization();  //   e.g., authorization can inspect the MATCHED endpoint's metadata
                          //   (like a [RequiresAuth] attribute) to decide whether to allow it through
app.MapGet("/v1/users/{id}", (int id) => ...);   // PHASE 2 (implicit): the endpoint actually executes here,
                                                   // reached via the standard middleware pipeline (§7)
```

`UseRouting()` looks at the request's method and path, matches it against every registered route pattern (`/v1/users/{id}` is a pattern with a route parameter, `{id}`), and stores *which endpoint matched* on `HttpContext` — without invoking it yet. This split exists specifically so that other middleware (authorization being the canonical example) can make decisions based on *which endpoint is about to run* — reading its metadata/attributes — before that endpoint actually executes. Trying to do this without a separate matching phase would mean authorization couldn't know what it's authorizing until the very last moment, which is both awkward and limits what per-endpoint policy metadata can express.

### 10.2 Why this matters for a proxy specifically

YARP registers its proxy routes through exactly this same endpoint-routing system (§15 below) — meaning "which backend cluster should this request go to" is answered by the *same* general-purpose matching mechanism that decides "which controller action handles this request" in an ordinary API. This isn't a coincidence or a simplification for teaching purposes — it's a genuine architectural choice: YARP doesn't invent its own separate routing system, it's built as a consumer of ASP.NET Core's existing one.

---

## 11. Configuration

### 11.1 Separating code from environment-specific values

Hardcoding a database connection string, a backend URL, or a feature flag directly into code means changing it requires a rebuild and redeploy — completely impractical for values that legitimately differ between your laptop, a staging environment, and production. ASP.NET Core's configuration system is built to layer multiple sources, with later sources overriding earlier ones:

```
appsettings.json                    <- base defaults, checked into source control
      │
      ▼ (overridden by)
appsettings.{Environment}.json      <- e.g., appsettings.Development.json,
      │                                 appsettings.Production.json — NOT
      │                                 usually checked in with real secrets
      ▼ (overridden by)
Environment variables               <- set by the deployment platform/container
      │
      ▼ (overridden by)
Command-line arguments              <- highest precedence, useful for local overrides
```

```json
// appsettings.json
{
  "BackendCluster": {
    "Destinations": {
      "primary": { "Address": "http://backend-1:5000" }
    }
  }
}
```

```csharp
// Strongly-typed access via the Options pattern, rather than magic string lookups
// scattered throughout the codebase:
public class BackendClusterOptions
{
    public Dictionary<string, DestinationConfig> Destinations { get; set; } = new();
}

builder.Services.Configure<BackendClusterOptions>(
    builder.Configuration.GetSection("BackendCluster"));
```

### 11.2 Why this matters for YARP specifically

This is directly relevant, not incidental: **YARP's entire routing/cluster configuration — which backends exist, what routes map to which clusters, load-balancing policy, health-check settings — is expressed through this exact configuration system**, typically in `appsettings.json` (or an equivalent config provider). This means YARP's core behavior can be changed by editing configuration and, depending on how it's wired up, even reloaded live, without touching or redeploying code at all — a deliberate design choice for infrastructure software that needs to adapt to changing backend topology without a full redeploy cycle.

---

## 12. Logging

### 12.1 Structured logging, and why it's not just "fancier `Console.WriteLine`"

```csharp
// NOT structured — a flat string, hard to query or filter reliably later
logger.LogInformation($"User {userId} fetched order {orderId} in {elapsedMs}ms");

// STRUCTURED — the template and the values are kept separate
logger.LogInformation("User {UserId} fetched order {OrderId} in {ElapsedMs}ms",
    userId, orderId, elapsedMs);
```

The second form looks almost identical when printed to a console, but it's fundamentally different underneath: the logging framework retains `UserId`, `OrderId`, and `ElapsedMs` as **discrete, named, typed fields** attached to the log event — not just baked irreversibly into one opaque string. A logging backend (many production systems ship logs to something searchable/aggregable, not just a text file) can then let you query "show me every log event where `OrderId = 12345`" or "what's the p99 of `ElapsedMs` across all requests in the last hour" directly — queries that would require fragile string-parsing/regex if all you had was interpolated text.

### 12.2 Why this matters especially for infrastructure software

A single proxy instance might handle enormous volumes of requests, each potentially generating multiple log lines, across many concurrent requests interleaved in the output. Being able to programmatically filter, aggregate, and correlate ("show me every log line associated with *this specific* request, across every middleware that logged something") is the difference between logs being genuinely useful for diagnosing a production incident and being an unusable wall of text. This is also precisely where **log levels** (`Trace`, `Debug`, `Information`, `Warning`, `Error`, `Critical`) earn their keep — infrastructure software typically runs with a fairly quiet default level in production (so you're not drowning in `Trace`-level noise at high request volume) but can have specific loggers turned up when actively diagnosing an issue, without a redeploy — itself enabled by the same layered configuration system from §11.

---

## 13. Common Misconceptions

- **"Kestrel is like IIS or nginx — a separate server program."** No — per §4.1, it's a library, compiled directly into your application's own process. There's no separate process to configure or restart independently.
- **"Middleware runs once, top to bottom, and that's it."** No — per §7.1, it's nested calls; each middleware potentially runs code both before *and* after the rest of the pipeline, meaning it participates in both request and response processing.
- **"`await` blocks the thread until the operation finishes."** The opposite is true, and it's the entire point (§9.1–§9.3) — `await` frees the thread to do other work while waiting.
- **"Singleton services are always safe to share, so lifetime doesn't matter much."** §8.3 shows a specific, real bug class (captive dependency) that arises exactly from careless lifetime mixing — lifetime is a correctness concern, not just a performance tuning knob.
- **"Configuration is just for secrets/connection strings."** §11.2 shows YARP's *entire routing behavior* — not just secrets — is expressed as configuration, precisely so operational topology changes don't require code changes.
- **"Routing decides AND runs the endpoint in one step."** §10.1 explicitly splits these into two phases specifically so other middleware can act on the *decision* before *execution* happens.

---

## 14. Production Perspective: 10 → 10,000 → 1,000,000 → 100,000,000 Requests

**~10 requests**: middleware ordering mistakes (§7.4), DI lifetime bugs (§8.3), and blocking-vs-async choices (§9.3) are all invisible — everything "works" regardless, because there's no real concurrency pressure to expose the difference.

**~10,000 requests (moderate concurrent load)**: a captive-dependency bug (§8.3) starts causing genuinely confusing, hard-to-reproduce data bugs, because now many concurrent requests are actually contending for/sharing a resource that was meant to be per-request. Blocking I/O (ignoring §9.3's guidance) starts visibly capping throughput at roughly your thread-pool size, well before CPU or network capacity is actually exhausted.

**~1,000,000 requests**: structured logging (§12) stops being a nicety and becomes operationally required — plain-text logs at this volume are simply not navigable during an incident. Configuration reload without redeploy (§11.2) becomes operationally important, because redeploying a high-traffic service just to change a backend address is itself a risky, disruptive operation you want to avoid needing.

**~100,000,000 requests**: this is squarely YARP's home turf. Every architectural choice in this lecture is now load-bearing at once, simultaneously: async I/O (§9) is the only reason a modest number of server processes can hold this many concurrent connections/requests in flight at all; DI-based extensibility (§8.4) is what lets large organizations customize proxy behavior (custom load-balancing, custom auth) without forking the codebase; and configuration-driven routing (§11.2) is what lets backend topology change continuously (servers added/removed, deployments rolling) without the proxy itself ever needing a code change or even, ideally, a restart.

---

## 15. Failure Scenarios

- **An unhandled exception inside a middleware or endpoint**: unwinds up through the nested call stack (§7.1) exactly like any C# exception, until caught by exception-handling middleware (§7.4) — if none is registered, or it's registered in the wrong position (not outermost), the connection may be aborted ungracefully instead of producing a clean error response.
- **A captive dependency (§8.3) wrapping a per-request resource like a database connection**: under concurrent load, multiple requests can end up sharing and racing on a resource that was never designed to be shared — producing intermittent, load-dependent corruption or cross-request data leakage that's notoriously hard to reproduce in a low-traffic dev environment.
- **Blocking synchronous I/O called from what should be an async path** (e.g., calling `.Result` on a `Task` instead of `await`ing it): can exhaust the thread pool under load, since threads that should have been freed (§9.3) are instead held blocked — this can manifest as the whole application becoming unresponsive under load that it should easily handle, sometimes described as "thread pool starvation."
- **A cancellation token not propagated through a long `await` chain**: work continues even after the originating client has disconnected (Lecture 2 §10.6), wasting resources on a response nobody will ever receive — directly contradicting the intent of §9.4.
- **Configuration missing or malformed for a given environment**: because configuration is layered (§11.1) and often not validated until something actually tries to use a missing/malformed value at runtime, a misconfigured environment can fail in a way that's only discovered when a specific code path first executes — which is exactly why the Options pattern's validation features (recognize the term, not required depth here) exist.

---

## 16. Performance Implications

- **Never block on async work** (`.Result`, `.Wait()`) in a request-handling path (§9.3, §15) — this is one of the highest-impact mistakes possible in ASP.NET Core code, because its damage compounds under exactly the concurrent load you're trying to survive.
- **Register services with the narrowest correct lifetime**, and be deliberate about singleton dependencies (§8.2–§8.3) — this is a correctness concern first, and a performance one second.
- **Put cheap, request-agnostic short-circuiting middleware early in the pipeline** (§7.3) — e.g., rejecting an unauthenticated request before it reaches expensive downstream work is strictly better than doing that work and discarding the result.
- **Prefer structured logging with appropriate log levels tuned per environment** (§12) — verbose logging has real CPU/IO cost at high request volume; this is a genuine production performance lever, not just a style preference.
- Deep Kestrel-internals tuning (thread pool sizing internals, custom transport layers) is **not** where your effort belongs at this stage — the framework's defaults are well-tuned for the overwhelming majority of cases, and this is specialist territory even among experienced ASP.NET Core engineers.

---

## 17. YARP Connection

### 17.1 The headline fact

**YARP is not a separate technology that happens to run alongside ASP.NET Core — it is an ASP.NET Core application.** Every concept in this lecture is something YARP is either directly built from, or directly extends. This is genuinely different from how you might picture "a reverse proxy" if your mental model was shaped by something like nginx (a standalone, general-purpose binary configured via its own separate config language, unrelated to any particular application framework) — YARP made the deliberate choice to be a *library*, consumed *inside* a normal ASP.NET Core app, precisely so it can be embedded, extended, and combined with ordinary application code using tools .NET developers already know.

### 17.2 Mapping this lecture's pieces onto YARP, directly

**Kestrel (§4)**: YARP doesn't replace Kestrel or reimplement HTTP parsing — it *is* a Kestrel-hosted app. Kestrel accepts the client-facing connection (Lecture 2 §15.3's "leg 1") and produces the `HttpContext` YARP's own code then operates on, exactly like any other ASP.NET Core endpoint would.

**Hosting (§5)**: a YARP app's `Program.cs` looks structurally identical to §5's example — `builder.Services.AddReverseProxy()` in the registration phase (wiring up YARP's own services into the DI container), and `app.MapReverseProxy()` in the pipeline phase (registering YARP's forwarding logic as endpoints, via §10's routing system).

**Middleware (§7)**: YARP's own forwarding logic executes as part of the standard middleware/endpoint pipeline — meaning you can place ordinary ASP.NET Core middleware *before* YARP's endpoint (e.g., your own authentication, rate limiting, or custom logging middleware, exactly as in §7.3–§7.4) and it will run first, potentially short-circuiting the request before it ever reaches YARP's forwarding logic at all. This is a direct, practical consequence of YARP being a normal participant in the pipeline rather than an opaque black box in front of it.

**Endpoint routing (§10)**: YARP's route configuration (which incoming path patterns map to which backend cluster) is expressed as endpoints registered through the *same* endpoint-routing system used for ordinary controllers/minimal APIs. "Which cluster handles this request" is answered by the same match-then-execute mechanism as "which controller action handles this request" (§10.2).

**Dependency injection (§8)**: YARP's internal services — its `HttpMessageInvoker`/`HttpClient` management for outbound backend connections (directly implementing the connection-pooling imperative from Lecture 2 §15.2), its load-balancing policies, its health-check logic — are all registered through, and resolved from, the standard DI container. This is also *how you extend YARP*: implementing and registering your own custom load-balancing policy or request/response transform is just... more DI registration, using the exact mechanism from §8.4.

**Async I/O (§9)**: forwarding a request is fundamentally an I/O-bound operation — read from the client connection, write to the backend connection, read the backend's response, write it back to the client — and YARP does every step of this with `async`/`await` over non-blocking I/O, for precisely the reason §9.3 explained: it's the only way a modest number of threads can have a very large number of concurrent proxied requests in flight simultaneously. `HttpContext.RequestAborted` (§9.4) is exactly how YARP knows to stop forwarding/cancel the backend call when the original client disconnects mid-request (Lecture 2 §15.2's cancellation point).

**Configuration (§11)**: cluster/route/destination definitions are expressed through the standard configuration system (§11.2 already covered this directly) — meaning backend topology can change via config, without a code change, using infrastructure you already understand from this lecture rather than a YARP-specific mechanism.

**Logging (§12)**: YARP emits structured log events through the standard `ILogger` abstraction, meaning it composes with whatever logging backend/aggregation your application already uses — no separate, YARP-specific logging pipeline to learn.

### 17.3 Where YARP sits — the synthesis diagram

```
                        ASP.NET Core Application Process
                       ┌──────────────────────────────────────────────────────┐
  Client ── socket ──► │  Kestrel (§4) — parses request into HttpContext (§6)   │
                       │        │                                              │
                       │        ▼                                              │
                       │  Your OWN middleware, if any (§7)                       │
                       │  (auth, rate limiting, logging — can short-circuit      │
                       │   BEFORE YARP ever sees the request, §17.2)              │
                       │        │                                              │
                       │        ▼                                              │
                       │  Endpoint routing (§10) matches this request to         │
                       │  a YARP-registered proxy route                          │
                       │        │                                              │
                       │        ▼                                              │
                       │  ┌────────────────────────────────────────────┐         │
                       │  │  YARP's forwarding endpoint                  │         │
                       │  │  - resolves cluster/destination via DI (§8)   │         │
                       │  │  - issues outbound request using pooled        │  ── socket ──► Backend
                       │  │    HttpClient (async I/O, §9; connection        │
                       │  │    reuse, Lecture 2 §15.2)                       │
                       │  │  - streams backend response back onto            │
                       │  │    THIS request's HttpContext.Response           │
                       │  │    (Lecture 1 §9)                                 │
                       │  └────────────────────────────────────────────┘         │
                       │        │                                              │
                       │        ▼                                              │
                       │  Response flows back up through any middleware          │
                       │  registered before YARP (§7.1's "way up" phase)          │
                       └──────────────────────────────────────────────────────┘
                                │
  Client ◄── socket ────────────┘
```

Notice this diagram is literally §3's core mental model diagram, with one box — "Endpoint" — expanded to show that, for a YARP app, that endpoint's *entire job* is to become an HTTP client (Lecture 2 §15.1's "dual role") and repeat this whole diagram's request/response journey a second time, against a backend, using the exact same building blocks (async I/O, DI-resolved connection pooling, streaming) it was itself built from a moment earlier.

---

## 18. What I Don't Need to Know Yet

- Kestrel's internal transport implementation (libuv/managed sockets history, low-level buffer management) — §4.1's "it parses HTTP and manages connections" is sufficient depth.
- The full Options pattern feature set (`IOptionsSnapshot`, `IOptionsMonitor`, validation attributes) — recognize that configuration can be strongly-typed and reloadable (§11.2); the specific API surface can wait.
- Custom middleware authored as full classes (`IMiddleware`) versus the inline `app.Use(...)` lambda style shown here — both exist; the lambda form is sufficient to understand the pipeline mechanics taught in this lecture.
- Distributed tracing/correlation IDs across multiple services — mentioned in passing in §12.2, but this deserves its own treatment once you're deeper into how YARP fits into a larger multi-service system; not required yet.
- Health checks, load-balancing policy implementations, and YARP's specific configuration schema in detail — these build directly on §17's foundation and are natural candidates for a dedicated, later YARP-specific lecture, not this one.
- SignalR, gRPC-specific hosting concerns, or minimal API vs. MVC controller stylistic differences — orthogonal to understanding YARP.

---

## 19. Knowledge Check

1. Three middleware are registered in order: `LoggingMiddleware`, `AuthMiddleware`, `CachingMiddleware`, followed by the endpoint. `AuthMiddleware` short-circuits (returns 401 without calling `next()`) for a given request. Using §7.1–§7.3, explain exactly which code runs, in what order, and whether `LoggingMiddleware`'s "after `next()`" code still executes.
2. A singleton service directly constructs and holds a scoped `DbContext` in its constructor. Using §8.2–§8.3, explain the specific bug this causes once the app is handling multiple concurrent requests, and explain why the DI container's default behavior (throwing at startup) exists.
3. A colleague says "we should spawn a background thread to handle each incoming request so we can process more of them at once." Using §9.1–§9.3, explain what's wrong with this framing and what ASP.NET Core actually does instead.
4. Using §10.1, explain concretely why splitting routing into "match" and "execute" phases lets authorization middleware make decisions it otherwise couldn't.
5. Using §17.2, explain why placing your own custom rate-limiting middleware *before* `app.MapReverseProxy()` in the pipeline means a rate-limited request never even reaches YARP's own forwarding logic — and why that's a direct consequence of YARP being built as an ordinary participant in the middleware pipeline rather than a special-cased framework feature.
6. Using §17.3's diagram, explain in your own words why YARP's forwarding endpoint has to independently reproduce almost this entire lecture's concepts (async I/O, connection reuse via DI-resolved clients, streaming) a *second* time, on its outbound side, rather than simply relaying Kestrel's inbound `HttpContext` object directly to the backend.

---

## 20. Practical Exercise

Build a tiny, from-scratch ASP.NET Core app that makes the middleware pipeline and DI lifetimes tangible — no YARP needed yet, just the raw building blocks this lecture covered.

```bash
dotnet new web -o AspNetCoreLectureDemo && cd AspNetCoreLectureDemo
```

Replace `Program.cs` with:

```csharp
var builder = WebApplication.CreateBuilder(args);

// Register one of each lifetime, all implementing the SAME interface,
// each just reporting its own instance ID so you can SEE lifetime
// behavior directly in the response.
builder.Services.AddSingleton<IIdReporter, IdReporter>();
builder.Services.AddScoped<IIdReporter, IdReporter>();
builder.Services.AddTransient<IIdReporter, IdReporter>();

var app = builder.Build();

// Middleware A: logs before AND after next() — watch the ordering in your console.
app.Use(async (context, next) =>
{
    Console.WriteLine("A: before next()");
    await next(context);
    Console.WriteLine("A: after next()  <- runs LAST, once everything below has finished");
});

// Middleware B: SHORT-CIRCUITS if a query string flag is set.
app.Use(async (context, next) =>
{
    if (context.Request.Query.ContainsKey("blocked"))
    {
        context.Response.StatusCode = 403;
        await context.Response.WriteAsync("B: short-circuited, endpoint never reached");
        return; // no next() call
    }
    Console.WriteLine("B: before next()");
    await next(context);
    Console.WriteLine("B: after next()");
});

app.MapGet("/", (
    IIdReporter singleton1, IIdReporter singleton2,   // ask for the SAME interface twice —
    IServiceProvider sp) =>                             // resolve scoped/transient manually
                                                          // to request the same interface
                                                          // multiple times within one request
{
    var scoped1 = sp.GetRequiredService<IIdReporter>();
    var scoped2 = sp.GetRequiredService<IIdReporter>();
    return Results.Text(
        $"singleton1={singleton1.Id} singleton2={singleton2.Id} " +
        $"(same? {singleton1.Id == singleton2.Id})\n" +
        $"resolved1={scoped1.Id} resolved2={scoped2.Id} " +
        $"(same? {scoped1.Id == scoped2.Id})");
});

app.Run();

interface IIdReporter { Guid Id { get; } }
class IdReporter : IIdReporter { public Guid Id { get; } = Guid.NewGuid(); }
```

Run it:
```bash
dotnet run
```

Then, with the app running:

1. `curl http://localhost:5000/` a few times — compare `Id` values across separate requests for whichever lifetime you registered last (only the *last* registration for a given interface wins when resolved directly by interface type, which is itself worth noticing) — but more importantly, watch the console output and confirm the exact A→B→endpoint→B→A ordering from §7.1 happens on every request.
2. `curl "http://localhost:5000/?blocked=1"` — confirm you get a 403, confirm `B: before next()` never prints, and — this is the important check — confirm whether `A: after next()` still prints (it should — work through *why*, using §7.1's nested-call structure, before reading the answer in your own console output).
3. Modify the singleton registration to instead be `AddSingleton<IIdReporter>(sp => sp.GetRequiredService<IIdReporter>())`... actually, simpler: just try changing `AddScoped` to `AddSingleton` for one of the three registrations and observe how the "same? true/false" output changes across multiple requests — this is §8.3's lifetime distinction made directly observable rather than theoretical.

---

## 21. "Ready to Move On" Criteria

Before starting Lecture 4, you should be able to explain — out loud, in your own words:

- [ ] What Kestrel is responsible for, and specifically what it is *not* responsible for.
- [ ] Why middleware execution is better modeled as nested function calls than as a flat conveyor belt, and what that model predicts about ordering.
- [ ] What short-circuiting is, why it's a deliberate and common pattern, and how to spot it in unfamiliar middleware code.
- [ ] The three DI lifetimes, and what specifically goes wrong when a singleton captures a scoped dependency.
- [ ] Why `await` frees a thread rather than blocking it, and why that specific fact is what allows high request concurrency with a modest thread pool.
- [ ] What `HttpContext` represents, and why nearly every other concept in this lecture is best understood in terms of "reads from it, writes to it, or governs something's lifetime relative to it."
- [ ] Why routing is split into a match phase and an execute phase, and what that split enables.
- [ ] Why YARP's cluster/route configuration lives in the same configuration system as any other app setting, rather than a bespoke YARP-only mechanism.
- [ ] The full picture from §17.3: which specific ASP.NET Core building block is responsible for each part of YARP's job, from accepting the client connection through forwarding to the backend and streaming the response back.

If any of these feel shaky, revisit that section — Lecture 4 will assume you can read an unfamiliar `Program.cs` and middleware pipeline and reason confidently about what will execute, in what order, and why.
