2026_07_26_18_45-(Async-Actually)

# Lecture 001 — Async, Actually: One Mechanism, Three Languages

You have written `async`/`await` in Python and `await` in C#. You have also, without being told, written an async runtime in C — every time you wrote an ISR that sets a flag and a superloop that checks it.

This lecture is about the fact that **those are the same thing**. Not analogous. The same four moving parts, in the same arrangement, with the same failure modes. Once you see the mechanism once, `async` stops being a keyword you trust and becomes a machine you can reason about, debug, and predict.

**Why this lecture, for you, now:**

- It is on your stated weakness list — `async`/`await` internals, task scheduling, thread pools, non-blocking I/O.
- Your two production languages (C# in the YARP gateway, Python in the Flask/LangChain service) have *different* async models, and the seam between them is where your distributed traces and your cancellations are going to break.
- The three worst production bugs in your exact stack — sync-over-async deadlock, thread pool starvation, and blocking the event loop — are all **the same bug** viewed from three runtimes, and all three are invisible until you're under load.
- It is a rare topic where the bottom is genuinely reachable. You can read an entire async executor in an afternoon. Given your instinct to descend, this is a place where the descent *terminates* — which makes it a good place to practice descending on purpose.

**Stop line for this lecture:** you can draw the four organs for any runtime, predict whether a given call suspends or blocks, explain what `.Result` does to a thread, and find the blocking call that's stalling an event loop. You do **not** need to read the CoreCLR scheduler source or CPython's `_asynciomodule.c`. §14 marks where the useful part ends and the hobby begins.

---

## Table of Contents

- [0. The thesis: it is all about who holds the stack](#0-the-thesis-it-is-all-about-who-holds-the-stack)
- [1. Concurrency is not parallelism](#1-concurrency-is-not-parallelism)
- [2. The four organs](#2-the-four-organs)
- [3. Ground truth: build an async runtime in 60 lines of C](#3-ground-truth-build-an-async-runtime-in-60-lines-of-c)
- [4. The compiler transform, precisely](#4-the-compiler-transform-precisely)
- [5. Stackless vs stackful, and function coloring](#5-stackless-vs-stackful-and-function-coloring)
- [6. C# and .NET](#6-c-and-net)
- [7. Python and asyncio](#7-python-and-asyncio)
- [8. The three-column table](#8-the-three-column-table)
- [9. The failure modes](#9-the-failure-modes)
- [10. Diagnosis, and why your traces break](#10-diagnosis-and-why-your-traces-break)
- [11. An audit checklist for LLM_Monitor](#11-an-audit-checklist-for-llm_monitor)
- [12. Common mistakes](#12-common-mistakes)
- [13. Interview relevance](#13-interview-relevance)
- [14. Where the useful part ends](#14-where-the-useful-part-ends)
- [15. Sources](#15-sources)

---

## 0. The thesis: it is all about who holds the stack

Here is the entire lecture in one paragraph. Everything after this is elaboration.

> A blocking call is expensive not because waiting is expensive, but because **the waiting computation is holding an entire OS thread stack hostage** — typically ~1 MB of reserved address space plus a kernel scheduling entity — for the whole duration of a wait in which it does nothing. Async exists to make a suspended computation cost **a struct on the heap** instead of **a stack**. Everything else — the state machine transform, the executor loop, wakers, function coloring, `ConfigureAwait`, the GIL — is a consequence of that one decision.

Look at what a blocking read actually costs:

```
   THREAD-PER-WAIT (blocking)
   ┌──────────────────────────────────────────────────────────┐
   │ Thread 1  [stack 1MB]  ── read() ──► ██ blocked 200ms ██ │
   │ Thread 2  [stack 1MB]  ── read() ──► ██ blocked 200ms ██ │
   │ ...                                                       │
   │ Thread 10000 → 10 GB of reserved stack, kernel scheduler  │
   │ thrashing, context switches dominating useful work        │
   └──────────────────────────────────────────────────────────┘

   ASYNC (suspend, don't block)
   ┌──────────────────────────────────────────────────────────┐
   │ Thread 1  [stack 1MB] ── runs the executor loop ─────────│
   │                                                           │
   │ heap: [task 1: 48 bytes][task 2: 48 bytes] ... × 10000    │
   │       ≈ 500 KB total, all waiting, none holding a stack   │
   └──────────────────────────────────────────────────────────┘
```

This is the **C10K problem** — how do you serve ten thousand concurrent connections? — and async is the answer the industry converged on. Note the shape of the win: it is not throughput and it is not latency. **It is waiting capacity.** Async makes a machine able to have many things *in flight*; it makes nothing go faster.

That distinction has a hard practical consequence you should internalize now: **making a CPU-bound function `async` does nothing.** It doesn't help, it adds overhead, and in Python it actively hurts. Async is a technique for **waiting cheaply**, and if you aren't waiting, it has nothing to offer.

You already know this from firmware, where the point is inescapable: there is no OS, so a "blocking" delay is literally a `for` loop burning cycles. `delay_ms(500)` in a superloop doesn't just waste time — it makes the whole system unresponsive for half a second, because *you only have one stack and it's holding it*. Async on an MCU exists for exactly the same reason it exists in a web server, and there the reason is impossible to hide behind a runtime.

---

## 1. Concurrency is not parallelism

Worth thirty seconds because the confusion produces bad architecture decisions and bad interview answers.

- **Concurrency** is *dealing with* many things at once — a structuring technique. It is about composition and interleaving.
- **Parallelism** is *doing* many things at once — an execution property. It requires multiple cores.

```
  CONCURRENT, NOT PARALLEL      PARALLEL (and concurrent)
  one core                      two cores
  A──┐  ┌──A──┐  ┌──A           A────────────────
     └B─┘     └B─┘              B────────────────
  interleaved at wait points    genuinely simultaneous
```

`async`/`await` is a **concurrency** tool. In Python's default build it gives you *zero* parallelism. In C# it gives you concurrency *and* — because the thread pool is multi-threaded — parallelism as a side effect, which is precisely why C# async has data races and Python async mostly doesn't.

Hold that asymmetry; it explains most of the difference between §6 and §7.

**Note on "mostly."** Single-threaded async does *not* eliminate races — it eliminates *torn memory*. Interleaving still happens at every `await`, so check-then-act across a suspension point is still a race. See §9.7; it catches people who assume single-threaded means safe.

---

## 2. The four organs

Every async system ever built — asyncio, .NET's `Task`, Rust's `Future`, JavaScript's event loop, Embassy on a microcontroller, your superloop — is these four organs. Learn them once and every runtime becomes readable.

| # | Organ | Job | Firmware | C# | Python |
|---|---|---|---|---|---|
| 1 | **The Transform** | Turn a linear function into something resumable | You hand-write a `switch` on a state variable | Compiler emits `IAsyncStateMachine` | Compiler emits a coroutine object |
| 2 | **The Handle** | A referenceable "this will finish later" | Your task struct | `Task` / `ValueTask` | `Future` / `Task` |
| 3 | **The Waker** | The world's way of saying "you can continue" | The ISR sets a flag / pushes to the ready queue | `AwaitUnsafeOnCompleted` continuation | `Future.set_result` → `call_soon` |
| 4 | **The Executor** | A loop that resumes whatever is ready | Your superloop | The thread pool | `loop._run_once()` |
| (+) | **The Reactor** | Asks the OS/hardware what's ready | The NVIC | epoll/kqueue/**IOCP**/io_uring | `selectors` (epoll/kqueue) |

And the cast, since you think better with personalities:

| Character | Real thing | Personality |
|---|---|---|
| **The Bookmark** | The state machine / coroutine object | Remembers exactly which line you stopped on and which locals mattered. Small, cheap, lives on the heap. The whole trick |
| **The Receipt** | `Task` / `Future` / `Promise` | Handed to you *immediately*, worth nothing yet. Redeemable later. Everyone confuses the receipt for the meal |
| **The Doorman** | The waker / continuation | Knows exactly one thing: which Bookmark to wake when a specific event happens. Registered before you leave; forgotten after |
| **The Dispatcher** | The executor / event loop | A tireless clerk pulling ready work off a queue and running it to the next suspension point. **Never blocks.** If you make the Dispatcher wait, the entire system waits |
| **The Switchboard** | epoll / IOCP / the NVIC | Watches thousands of sleeping things and reports, in one call, which ones woke up |
| **The Hostage-Taker** | A blocking call inside async code | Seizes the Dispatcher's thread and refuses to give it back. The villain of this entire document |

**The single most important relationship:** the Dispatcher runs your code *until it suspends*. If your code doesn't suspend — because you called something blocking — the Dispatcher cannot run anything else. Not "runs slower." **Cannot run.** Every disaster in §9 is a variation of this.

---

## 3. Ground truth: build an async runtime in 60 lines of C

Start here, on hardware, where there is no runtime to hide behind. You will build all four organs by hand. Then in §4 you'll discover that the compiler does this mechanically, and everything else is detail.

### 3.1 The problem

You want to write this:

```c
forever {
    await button_pressed();
    led_on();
    await delay_ms(500);
    led_off();
}
```

You can't, in C. `await` doesn't exist and a blocking `delay_ms` would freeze everything. So you write the state machine yourself — and you have probably done exactly this without calling it async.

### 3.2 The Bookmark and the Dispatcher

```c
typedef enum { PENDING, DONE } poll_t;

typedef struct task {
    poll_t (*poll)(struct task *self);   /* resume function */
    uint8_t  state;                      /* WHERE WAS I */
    uint32_t deadline;                   /* a local that survives suspension */
    struct task *next;                   /* ready-queue link */
    bool queued;
} task_t;

/* --- the ready queue: the only shared state --- */
static task_t *ready_head, *ready_tail;

/* THE WAKER. Callable from an ISR. Single-writer discipline. */
void wake(task_t *t) {
    uint32_t p = __get_PRIMASK(); __disable_irq();
    if (!t->queued) {                    /* idempotent: waking twice is harmless */
        t->queued = true;
        t->next = NULL;
        if (ready_tail) ready_tail->next = t; else ready_head = t;
        ready_tail = t;
    }
    __set_PRIMASK(p);
}

/* THE DISPATCHER */
void executor_run(void) {
    for (;;) {
        task_t *t = pop_ready();          /* interrupt-safe pop */
        if (t) {
            t->queued = false;
            t->poll(t);                   /* run until it suspends again */
        } else {
            __WFI();                      /* nothing ready: sleep until an IRQ */
        }
    }
}
```

### 3.3 The Doorman, wired to hardware

```c
static task_t *button_waiter;

void EXTI0_IRQHandler(void) {             /* THE REACTOR */
    clear_pending();
    task_t *t = button_waiter;
    button_waiter = NULL;
    if (t) wake(t);                       /* ← the ISR is the waker */
}
```

### 3.4 The Transform, by hand

```c
poll_t blink_poll(task_t *self) {
    switch (self->state) {

    case 0:                               /* await button_pressed() */
        button_waiter = self;
        self->state = 1;
        return PENDING;                   /* ← SUSPEND. return to the Dispatcher */

    case 1:                               /* resumed by the button ISR */
        led_on();
        timer_wake_at(self, now() + 500);
        self->state = 2;
        return PENDING;                   /* ← SUSPEND again */

    case 2:                               /* resumed by the timer ISR */
        led_off();
        self->state = 0;
        wake(self);                       /* loop around */
        return PENDING;
    }
    return DONE;
}
```

### 3.5 What you just built

Read `blink_poll` next to the `await` code in §3.1 and the transform is completely visible:

| In the source you wanted to write | In the machine you built |
|---|---|
| Each `await` point | A `case` label |
| "Where was I" | `self->state` |
| A local that must survive an `await` | A **field on the task struct** |
| A local that does *not* cross an `await` | Stays a normal C local — it's fine to lose |
| `await X` | Register a waker with X, `return PENDING` |
| Being resumed | The Dispatcher calls `poll` again; the `switch` jumps back |
| The "thread" this task runs on | **There isn't one.** It borrows the Dispatcher's stack, briefly |

That last row is the whole thesis from §0, made concrete. This task is suspended across a 500 ms wait and it is costing you **one struct** — about 20 bytes. Not a stack. There are no threads in this program. There is no OS. And you have a hundred of these running concurrently on 20 KB of RAM.

Two properties worth naming because they carry all the way up to C# and Python:

- **The stack is not preserved across a suspension.** That's why locals must be promoted into the struct. This is the defining property of **stackless** coroutines (§5), and it's the source of `async`'s viral nature.
- **`return PENDING` is the suspension.** There is no magic "pause." The function *returns*, normally, and something later calls it again. Every `await` in every language in this document is exactly this: **a return, plus a promise that someone will call you back.**

**This is Embassy.** Rust's `async fn` compiles to precisely this state machine, `.await` compiles to precisely this poll-and-register-waker, and the executor is precisely this loop. The difference is that the compiler writes `blink_poll` for you, sizes the struct at compile time, and the type system proves you can't wake a task that's already dead.

---

## 4. The compiler transform, precisely

Now the same thing in C#, done by the compiler. You write:

```csharp
async Task<int> GetLengthAsync(string url)
{
    string s = await _http.GetStringAsync(url);
    return s.Length;
}
```

Roslyn emits approximately this (names mangled, simplified but structurally faithful):

```csharp
struct GetLengthStateMachine : IAsyncStateMachine
{
    public int state;
    public AsyncTaskMethodBuilder<int> builder;   // owns the Task you handed back
    public string url;                            // parameter      → field
    public HttpClient http;                       // captured this  → field
    private TaskAwaiter<string> awaiter;          // the pending op → field
    private string s;                             // local crossing await → FIELD

    public void MoveNext()
    {
        try
        {
            if (state != 0)
            {
                awaiter = http.GetStringAsync(url).GetAwaiter();
                if (!awaiter.IsCompleted)
                {
                    state = 0;
                    builder.AwaitUnsafeOnCompleted(ref awaiter, ref this);
                    return;            // ◄── THE SUSPENSION. Thread is released.
                }
            }
            else
            {
                state = -1;            // resumed
            }

            s = awaiter.GetResult();   // throws here if the operation faulted
            builder.SetResult(s.Length);
        }
        catch (Exception e) { state = -2; builder.SetException(e); }
    }
}
```

Compare column by column with §3.4. `state` is `self->state`. `s` was promoted to a field exactly as `deadline` was. `AwaitUnsafeOnCompleted` is registering the Doorman. **`return` is `return PENDING`.** `builder.SetResult` completes the Receipt. Same machine.

Four consequences worth extracting, because each one explains a behaviour that surprises people:

**1. The Receipt is returned immediately, at the first suspension.** `GetLengthAsync` returns a `Task<int>` the instant it hits an incomplete `await`. The caller resumes *while the work is outstanding*. This is why "async makes my method return early" isn't a bug — it's the entire point, and it's why forgetting to `await` is silent.

**2. There is a fast path.** Note `if (!awaiter.IsCompleted)`. If the data was already buffered, no suspension occurs, no state machine gets boxed to the heap, and the method runs synchronously start to finish. In C# the struct is only boxed onto the heap **when it actually suspends** — which is why `async` methods that usually complete synchronously are nearly free, and why `ValueTask` exists to remove the last allocation.

**3. Exceptions are captured, not thrown.** The `catch` stores the exception on the builder. It surfaces when someone awaits the Task. **If nobody awaits it, nobody ever sees it.** That's §9.4.

**4. `await` is not a keyword the runtime understands — it's a pattern.** Anything with `GetAwaiter()` returning something with `IsCompleted`, `OnCompleted`, and `GetResult()` is awaitable. That's why you can await your own types.

### 4.1 A 2026 footnote: runtime async

Since C# 5, the compiler has been solely responsible for this transform. That's changing. **Runtime Async** (experimental in .NET 10, in preview in .NET 11) moves the work into the runtime: instead of emitting a full state machine, the compiler emits a call to `AsyncHelpers.Await(...)`, and the runtime suspends the method, saving only the state actually needed, then resumes it. Reported gains on deep async chains are substantial — roughly 66% less execution time and 60% less allocation in one benchmark — because you stop rebuilding state-machine scaffolding at every layer of the call stack.

**This does not change anything you need to learn.** The mental model is identical; only the implementer moves. But it's worth knowing two things: the compiler-generated state machine is still what you'll see in a decompiler and in most running code today, and if someone asks you about it in an interview, knowing that the transform is migrating into the runtime is a good signal that you follow the platform.

---

## 5. Stackless vs stackful, and function coloring

This is the design axis that explains why C#, Python, Rust, and JavaScript feel the way they do — and why Go and Java feel different.

### 5.1 The two designs

| | **Stackless** (C#, Python, Rust, JS) | **Stackful** (Go, Java virtual threads, Erlang) |
|---|---|---|
| What a suspended task is | A **struct/object** holding promoted locals | A real, small, growable **stack** |
| Cost per task | Tens of bytes, known at compile time in Rust | KBs, grows on demand |
| Where you can suspend | Only in a function explicitly marked `async` | **Anywhere**, at any call depth |
| Do callers need to know? | **Yes** — `async` is viral | **No** — a virtual thread looks like a thread |
| Runtime needed | Almost none | Scheduler + stack management in the runtime |
| Fits a microcontroller? | Yes (Embassy) | No |

### 5.2 Function coloring

The famous complaint ("What Color Is Your Function?") is a direct consequence of stacklessness. In a stackless design:

- An `async` function can only be *awaited* from another `async` function.
- To call async code from sync code you must either block (`.Result`, `asyncio.run`) or fire-and-forget.
- So one `async` leaf turns every caller up the chain `async`. **Async is viral upward.**

This isn't a design failure — it's the price of "a suspended task costs a struct, not a stack." You cannot suspend an arbitrary call stack if you never captured one.

**Go and Java bought the other trade.** A goroutine or a Java virtual thread has a real (small, growable) stack, gets multiplexed onto a few carrier threads by the runtime, and can suspend at any depth. So you write ordinary blocking-looking code, no `async` keyword exists, and there's no coloring — at the cost of a heavier runtime and per-task memory that can't be known at compile time. Java 21 shipped virtual threads and by 2026 they're mature and production-standard; Kotlin, notably, went the *stackless* route with coroutines, so the JVM now hosts both designs side by side.

**Why you should care:** when you interview and someone asks "why is async painful in C# and not in Go," the answer is not "Go is better." It is: *stackless coroutines make a suspended task cost a struct instead of a stack, which is why they run on a microcontroller and why they color your functions; stackful coroutines make the opposite trade.* That's a systems answer, and it's the kind that separates candidates.

### 5.3 The historical ladder

Worth knowing because you'll read code from every rung:

```
  1. Blocking + thread per request     simple, doesn't scale past ~10k
  2. Callbacks                          scales, but "callback hell": inverted
                                        control flow, no exception propagation,
                                        composition is manual
  3. Promises / Futures                 composable, chainable, errors propagate
                                        (.then().catch()) — but still not linear
  4. async/await                        the compiler writes the state machine so
                                        the code READS linear again.
                                        The win is READABILITY over #3, not speed.
  5. Structured concurrency             tasks have scoped lifetimes, cancellation
                                        and errors propagate to a parent
                                        (TaskGroup, CancellationScope)
```

Rung 4's contribution is entirely ergonomic — `await` compiles to roughly what you'd have written with promises. Rung 5 is the current frontier and fixes async's real remaining problem: **orphaned tasks nobody owns**. See §9.4.

---

## 6. C# and .NET

Your YARP gateway lives here. C#'s model is **stackless coroutines on a multi-threaded work-stealing thread pool**, which is a genuinely different beast from Python's, and the difference is the source of most C#-specific pain.

### 6.1 The Dispatcher is the thread pool

There is no single event loop in .NET. When a `Task` completes, its continuation is scheduled onto the **ThreadPool**, and *some* pool thread picks it up.

```
   ┌─────────── ThreadPool ────────────────────────────────┐
   │  global queue  [w][w][w]                              │
   │                                                       │
   │  worker 1  [local deque]  ◄── work-stealing ──┐       │
   │  worker 2  [local deque]  ────────────────────┘       │
   │  worker N  ...                                        │
   │                                                       │
   │  injection: if work is queued and nothing completes,  │
   │  add threads slowly (hill-climbing, ~1-2/second)      │
   └───────────────────────────────────────────────────────┘
   I/O completions arrive via IOCP → queued as continuations
```

Three consequences that matter enormously:

1. **Your code after an `await` may run on a different thread than the code before it.** So `[ThreadStatic]` breaks, thread affinity breaks, and non-thread-safe state shared across an `await` is a **real data race** — unlike Python.
2. **The pool grows slowly on purpose.** Injection is deliberately throttled (roughly one or two threads per second beyond the core count) because thrashing threads is worse than queueing. This throttle is exactly what turns a small blocking problem into an outage — see §6.4.
3. **I/O completions don't need a thread while waiting.** A pending socket read holds an IOCP registration, not a thread. That's the win.

### 6.2 `Task` vs `ValueTask`

| | `Task<T>` | `ValueTask<T>` |
|---|---|---|
| What it is | Reference type, always allocated | Struct — wraps either a result **or** a `Task` |
| Use when | Default. Anything you'll await more than once, combine, or store | Hot paths that usually complete synchronously (cache hits) |
| Rules | Freely awaitable multiple times | **Await exactly once.** Don't store, don't `.Result`, don't await twice |

The point of `ValueTask` is the fast path from §4: if a value is already cached, you shouldn't allocate a `Task` just to say so. Don't reach for it by default — the constraints are real and violating them causes corruption rather than an exception.

### 6.3 `ConfigureAwait(false)` and SynchronizationContext

A `SynchronizationContext` is a policy object saying "resume continuations *here*." WinForms/WPF have one (the UI thread — that's how `await` lets you touch controls afterward). **ASP.NET Core does not have one.** Classic ASP.NET (Framework) did, and that's the origin of most of the folklore.

- `await foo` → capture the current context, resume on it.
- `await foo.ConfigureAwait(false)` → don't capture, resume on any pool thread.

**Practical guidance for your code:** in ASP.NET Core *application* code, `ConfigureAwait(false)` is essentially a no-op — there's no context to capture. In **library** code you write that might be consumed elsewhere, use it, because you don't know your caller's context. It also matters because it's *the* deadlock ingredient in §6.4 for anyone still on Framework or writing a UI.

### 6.4 The two catastrophes

These are the bugs to be able to recognize instantly. They're the highest-value thing in this section.

**Catastrophe 1 — sync-over-async deadlock.**

```csharp
// In a context that HAS a SynchronizationContext (WPF, classic ASP.NET):
public ActionResult Index()
{
    var data = GetDataAsync().Result;   // ☠
    return View(data);
}
```

The mechanism, step by step:
1. `GetDataAsync()` hits an incomplete `await` and returns a `Task`. Its continuation is scheduled *to the captured context* — i.e. "resume on this exact thread."
2. `.Result` **blocks that exact thread** waiting for the Task.
3. The continuation needs that thread. The thread is blocked waiting for the continuation.
4. Deadlock. Forever. No exception, no timeout, no log line.

Adding `ConfigureAwait(false)` all the way down breaks the cycle — which is why that advice exists — but the real fix is **never block on async code.** `async` all the way up.

**Catastrophe 2 — thread pool starvation.** This one *does* hit ASP.NET Core, and it will hit your gateway if you're careless.

```csharp
public async Task<IActionResult> Get()
{
    var r = _http.GetStringAsync(url).Result;   // ☠ blocks a pool thread
    return Ok(r);
}
```

No deadlock here (no context to capture), so it "works" in dev. Under load:

```
  load ↑ → every request blocks a pool thread
        → pool exhausted, work queues up
        → pool injects threads at ~1-2/sec (far slower than arrival rate)
        → queued work waits longer
        → healthchecks time out, latency explodes
        → looks EXACTLY like a downstream outage
```

The signature: **CPU is low, memory is fine, and everything is slow.** That combination is nearly diagnostic. Confirm it with `dotnet-counters monitor System.Runtime` and watch `threadpool-queue-length` (climbing) and `threadpool-thread-count` (climbing slowly). Classic culprits: `.Result` / `.Wait()`, `Task.Run(...).Result`, synchronous file or DB calls in a request path, `lock` held across slow work, and `GetAwaiter().GetResult()` in a "helper."

### 6.5 The pieces you'll actually use in LLM_Monitor

**`IAsyncEnumerable<T>` — this is your SSE streaming primitive.** Your roadmap has an OpenAI-compatible facade with SSE streaming through YARP; this is how you express it without buffering the whole response:

```csharp
public async IAsyncEnumerable<string> StreamAsync(
    [EnumeratorCancellation] CancellationToken ct)
{
    await foreach (var chunk in _upstream.ReadChunksAsync(ct))
        yield return chunk;          // flows to the client as it arrives
}
```

Two things to get right: annotate the token with `[EnumeratorCancellation]` or cancellation silently won't propagate, and make sure nothing between you and the client buffers (response buffering middleware, compression, or a proxy will defeat SSE).

**`Channel<T>` — your ring buffer, in C#.** A bounded producer/consumer queue with async read/write and real backpressure:

```csharp
var ch = Channel.CreateBounded<Job>(new BoundedChannelOptions(100) {
    FullMode = BoundedChannelFullMode.Wait   // ← backpressure, not unbounded growth
});
await ch.Writer.WriteAsync(job, ct);         // suspends if full
await foreach (var job in ch.Reader.ReadAllAsync(ct)) { ... }
```

This is §5.4 of the firmware atlas with a different spelling — single-writer indices, bounded capacity, and an explicit policy for what happens when it's full. Choose the full-mode deliberately: `Wait` is backpressure, `DropOldest` is a lossy telemetry buffer, and there is no correct default.

**`CancellationToken` — cooperative, never preemptive.** Nothing is killed. A token is a flag plus a callback list; code must *check* it (`ct.ThrowIfCancellationRequested()`) or pass it to something that does. Rules: accept one in every async method, pass it to every call you make, and **give every external call a timeout** (`CancellationTokenSource.CreateLinkedTokenSource` + `CancelAfter`). In ASP.NET Core, `HttpContext.RequestAborted` fires when the client disconnects — plumbing that through to your Python service and on to Azure OpenAI is how you stop paying for tokens nobody will read.

---

## 7. Python and asyncio

Your Flask/LangChain service lives here. Python's model is **stackless coroutines on a single-threaded event loop**, which makes it simpler than C# in one way (no data races on ordinary state) and far more fragile in another (**one blocking call stops everything**).

### 7.1 The lineage: `await` is `yield` wearing a suit

This is the fact that makes Python async click, and it's genuinely historical rather than metaphorical. Generators (2001) → `yield from` delegation (PEP 380, 2012) → `async`/`await` as dedicated syntax (PEP 492, 2015). Underneath, it's still the generator machinery.

At the very bottom of every `await` chain is a `Future`, and its `__await__` is essentially:

```python
class Future:
    def __await__(self):
        if not self.done():
            self._asyncio_future_blocking = True
            yield self          # ◄── THE SUSPENSION. A bare yield.
        return self.result()
```

That `yield` is the entire mechanism. It propagates up through every `await` in the chain (each one is effectively a `yield from`) until it reaches the `Task` that's driving the coroutine. The Task sees the yielded Future, registers a done-callback on it, and stops pumping. Later, `future.set_result(...)` schedules that callback, and the Task resumes the coroutine by calling `.send()` on it again.

So: **`await` is a `return PENDING` that propagates**, exactly as in §3.4. Same organ, different spelling.

### 7.2 The event loop

CPython's `_run_once` is short enough to hold in your head, and the shape is worth memorizing:

```python
def _run_once(self):
    # 1. how long may I sleep? 0 if work is ready, else until the next timer
    timeout = 0 if self._ready else (self._scheduled[0]._when - self.time()
                                     if self._scheduled else None)

    # 2. ask the OS which sockets are ready (epoll/kqueue) — THE SWITCHBOARD
    events = self._selector.select(timeout)
    self._process_events(events)          # appends callbacks to self._ready

    # 3. move expired timers into the ready queue
    ...

    # 4. run everything currently ready — snapshot the length first
    for _ in range(len(self._ready)):
        self._ready.popleft()._run()
```

Everything follows from this:

- **It is one thread.** Step 4 runs your callbacks one at a time, to completion.
- **`select(timeout)` is the only place it sleeps.** If a callback in step 4 takes 3 seconds, no I/O is processed, no timer fires, and every other coroutine is frozen for 3 seconds.
- **Fairness comes from snapshotting `len(self._ready)`** — work scheduled during this pass waits for the next one, so a task can't monopolize the loop by rescheduling itself.

### 7.3 The cardinal sin: blocking the loop

The Hostage-Taker, in its native habitat:

```python
async def handler():
    r = requests.get(url)          # ☠ synchronous — blocks the ENTIRE loop
    time.sleep(1)                  # ☠ blocks the ENTIRE loop
    emb = model.encode(texts)      # ☠ CPU-bound — blocks the ENTIRE loop
```

In C# this would consume one pool thread out of many and degrade gracefully-ish. In Python it stops **the whole process**. Every concurrent request, every timer, every heartbeat.

Fixes:

```python
r = await client.get(url)                            # httpx, not requests
await asyncio.sleep(1)                               # not time.sleep
emb = await asyncio.to_thread(model.encode, texts)   # CPU/blocking → thread
```

`asyncio.to_thread` (and `loop.run_in_executor`) hands the work to a thread pool so the loop keeps spinning. For genuinely CPU-bound work in a default (GIL-enabled) build, a *thread* still contends for the GIL — use a **process** pool for real CPU parallelism.

**Enable debug mode in development** and Python will tell you when you've done this: `PYTHONASYNCIODEBUG=1` or `loop.set_debug(True)` logs any callback exceeding 100 ms. This is close to free and it catches the bug class before production does.

### 7.4 The GIL, and what changed by 2026

The Global Interpreter Lock permits one thread to execute Python bytecode at a time. Consequences: threads help for I/O (the GIL is released during I/O waits), threads do **not** help for CPU-bound Python, and async gives concurrency but no parallelism.

That's now qualified. **Python 3.13 shipped an experimental free-threaded build; 3.14 (October 2025) promoted it to officially supported** under PEP 779, with single-threaded overhead down to roughly 5–10%. The GIL is still present in the default build, free-threading is opt-in, and making it the default is a multi-year path.

**What it means for you, honestly:** very little today, and knowing that is the sophisticated position. Your bottleneck is waiting on Azure OpenAI, not Python bytecode. Free-threading helps CPU-bound multithreaded workloads; **async already solved the I/O-bound case, which is yours.** The right take in an interview is: *"the GIL is being removed, it's supported-but-opt-in as of 3.14, and it's largely orthogonal to async — it changes the CPU story, not the I/O story."*

### 7.5 Flask, WSGI, and your actual process model

**This is the most immediately actionable subsection in the lecture for your codebase.**

Flask is a **WSGI** framework, and WSGI is a fundamentally synchronous protocol. Flask 2.0+ lets you write `async def` views, but it runs each one by spinning up an event loop for that request via `asgiref` — so you get `await` syntax with **none of the concurrency benefit**. It is not an async server.

Which means: **your concurrency model is your gunicorn worker configuration, not your `async` keywords.**

| gunicorn worker | Model | Concurrency |
|---|---|---|
| `sync` (default) | One request per worker process at a time | = number of workers. A slow LLM call blocks that entire worker |
| `gthread` | Thread pool per worker | workers × threads. Fine for I/O-bound; GIL released during waits |
| `gevent` / `eventlet` | Greenlets, monkey-patched blocking I/O | High, but monkey-patching interacts badly with some native libraries |
| **uvicorn / ASGI** | A real event loop | High — but requires an ASGI framework (FastAPI, Quart, Starlette) |

With the default `sync` worker and, say, 4 workers, **you can serve exactly 4 concurrent requests**, and every one of them is an LLM call that takes seconds. Your fifth request queues. That's not an async problem; it's a process-model problem, and no amount of `async def` will fix it.

Your realistic options, in ascending order of effort:

1. **Raise concurrency where it is** — `gthread` workers with a sensible thread count. Smallest change, no code rewrite, and correct for an I/O-bound LLM proxy. Start here.
2. **Move to ASGI** — Quart is close to a drop-in for Flask; FastAPI is a rewrite of the routing layer but gives you real async, native SSE streaming, and Pydantic validation. Justified if streaming is central to the roadmap, which it is.
3. **Leave it sync and scale horizontally** — more replicas. Legitimate, and worth naming as a deliberate choice rather than a default.

**Go measure this before you change anything.** Fire 20 concurrent requests at the service and watch what happens; the answer will tell you which option you need, and it's a five-minute experiment.

### 7.6 The rest of the toolkit

```python
# Structured concurrency (3.11+) — PREFER THIS over gather()
async with asyncio.TaskGroup() as tg:          # all tasks owned by this scope
    t1 = tg.create_task(fetch(a))              # one failure cancels siblings
    t2 = tg.create_task(fetch(b))              # nothing outlives the block

# Bounded concurrency — essential against rate-limited APIs
sem = asyncio.Semaphore(10)
async def limited(x):
    async with sem:
        return await call_azure_openai(x)

# Timeouts on EVERYTHING external
async with asyncio.timeout(30):
    result = await call_azure_openai(prompt)
```

`TaskGroup` vs `gather`: `gather` returns exceptions or cancels inconsistently depending on flags and leaves orphans on failure; `TaskGroup` guarantees that when the block exits, every child is finished or cancelled, and it raises an `ExceptionGroup`. It is strictly better — use it.

**`contextvars`** deserves its own mention because it's what makes your tracing work: it's the async-safe replacement for thread-locals, and it's how a request ID or trace context follows a coroutine across `await` boundaries. See §10.

**LangChain/LangGraph:** every runnable has async variants — `ainvoke`, `astream`, `abatch`. Use them, and use `astream` for token streaming. Be aware that some community integrations implement the async method by calling the sync one in a thread — worth verifying for anything on your hot path, since a "supported" `ainvoke` that's secretly blocking is exactly the bug this lecture is about.

---

## 8. The three-column table

The page to keep. Same organ, three spellings.

| Concept | Firmware (Embassy / hand-rolled) | C# / .NET | Python / asyncio |
|---|---|---|---|
| The Bookmark | Task struct with `state` field | Compiler `IAsyncStateMachine` | Coroutine object |
| The Receipt | The task handle | `Task` / `ValueTask` | `Future` / `Task` |
| Suspension | `return PENDING` | `return` from `MoveNext` | `yield` from `Future.__await__` |
| The Doorman | `wake(task)` from an ISR | `AwaitUnsafeOnCompleted` | `future.set_result` → `call_soon` |
| The Dispatcher | Your superloop | **ThreadPool** (multi-threaded) | **Event loop** (single-threaded) |
| The Switchboard | NVIC | IOCP / epoll | `selectors` (epoll/kqueue) |
| Idle behaviour | `__WFI()` — sleep for an IRQ | Pool threads park | `selector.select(timeout)` |
| Parallelism? | No (one core) | **Yes** | **No** (default build) |
| Data races on shared state? | Yes (vs. ISRs) | **Yes** | Only across `await` points (§9.7) |
| Where locals live | Fields in the task struct | Fields in the state machine struct | Coroutine frame |
| Cost per suspended task | ~tens of bytes, compile-time known | ~100+ bytes, heap, on suspension only | ~KB, heap |
| Blocking call impact | Freezes the superloop | Consumes a pool thread → starvation | **Freezes everything** |
| Cancellation | Drop the future / deregister waker | `CancellationToken` (cooperative) | `task.cancel()` → `CancelledError` |
| Bounded queue | Ring buffer | `Channel<T>` bounded | `asyncio.Queue(maxsize=)` |
| Context propagation | N/A | `AsyncLocal<T>` | `contextvars.ContextVar` |
| Sync escape hatch | N/A | `Task.Run` | `asyncio.to_thread` |
| Structured concurrency | Task scopes | `Parallel.ForEachAsync`, linked CTS | `asyncio.TaskGroup` |

---

## 9. The failure modes

Where the value concentrates. Every one of these is silent in development and violent under load.

**9.1 Sync-over-async deadlock (C#).** `.Result` / `.Wait()` / `GetAwaiter().GetResult()` on a context-capturing continuation. Blocks forever, no exception. *Fix: async all the way up.*

**9.2 Thread pool starvation (C#).** Blocking calls consume pool threads faster than the pool injects them. **Signature: low CPU, low memory, everything slow.** *Fix: find the blocking call. Confirm with `threadpool-queue-length`.*

**9.3 Blocking the event loop (Python).** One `requests.get`, `time.sleep`, or CPU-bound encode freezes the process. *Fix: async client, `asyncio.to_thread`, or a process pool. Turn on debug mode to catch it early.*

**9.4 Fire-and-forget / orphaned tasks.**
```python
asyncio.create_task(do_work())   # ☠ no reference kept
```
Two bugs at once: the event loop only holds a **weak** reference, so the task can be garbage-collected mid-flight and simply vanish; and if it raises, the exception surfaces only as a "Task exception was never retrieved" warning at some later GC. In C#, `async void` is the same disease in a worse form — an exception in an `async void` method is thrown on the thread pool and **crashes the process**. *Fix: `TaskGroup` in Python; never `async void` in C# except for event handlers.*

**9.5 Unbounded concurrency.**
```python
await asyncio.gather(*[call_api(x) for x in ten_thousand_items])   # ☠
```
You just opened 10,000 concurrent connections, exhausted your file descriptors, and DDoS'd a rate-limited endpoint that will now 429 you for an hour. *Fix: a semaphore, or a bounded queue with a fixed worker count. This will bite you specifically on Azure OpenAI, which has hard TPM/RPM quotas.*

**9.6 No timeouts.** An `await` with no timeout waits forever. A hung upstream becomes a hung service becomes a cascading failure. *Fix: a timeout on every single external call. No exceptions.*

**9.7 Races in single-threaded async.** The subtle one, and the one that surprises people who think one thread means safe:
```python
async def get_conn(self):
    if self._conn is None:              # check
        self._conn = await connect()    # ◄ SUSPENDS. another coroutine runs here,
    return self._conn                   #   sees None, and connects again.
```
Two connections, one leaked. **Any check-then-act spanning an `await` is a race**, even single-threaded — because `await` is exactly where interleaving happens. It's the same shape as your ISR/main hazard, with the suspension points marked for you. *Fix: `asyncio.Lock`, or set a placeholder Future before awaiting.*

**9.8 Cancellation not propagated.** A token accepted but never passed down means cancelling does nothing and work continues invisibly. *Fix: thread the token everywhere; in C# annotate `IAsyncEnumerable` with `[EnumeratorCancellation]`.*

**9.9 Async in the wrong place.** `async` on a CPU-bound method buys nothing and costs allocation. `async` constructors don't exist for a reason. *Fix: async is for waiting. If you're not waiting, don't.*

**9.10 Assuming `await` resumes on the same thread (C#).** It usually doesn't. Thread-affine state, `[ThreadStatic]`, and non-reentrant locks held across `await` all break. *Fix: `AsyncLocal<T>` for context; never hold a `lock` across an `await` — it won't even compile with `lock`, but `SemaphoreSlim` misuse achieves the same disaster.*

---

## 10. Diagnosis, and why your traces break

You already built Langfuse + OpenTelemetry into `LLM_Monitor` and you want C#→Python distributed traces. Async is the reason distributed tracing is hard, so this section is directly load-bearing for that goal.

### 10.1 The context propagation problem

A trace ID has to follow a logical operation. Before async, "logical operation" = "thread," so a thread-local worked. With async, one logical operation hops threads (C#) or interleaves with a thousand others on one thread (Python). **Thread-locals are simply wrong.**

The fix is a context that flows with the *continuation* rather than the thread:

| Runtime | Mechanism | Note |
|---|---|---|
| C# | `AsyncLocal<T>` | Flows across `await`; captured at the point a task is created |
| Python | `contextvars.ContextVar` | Copied into each `Task` at creation; `asyncio` is context-aware |
| OpenTelemetry | Built on exactly these | `Activity.Current` in .NET; `contextvars` in Python |

**The classic failure:** you set a trace context, then start work with something that doesn't propagate context — a raw `Thread`, a `ProcessPoolExecutor`, a queue consumer picking up a job later — and the trace silently splits into two disconnected halves. If your traces are mysteriously fragmenting, look for a context boundary, not a bug in the tracer.

**For the C#→Python hop specifically:** context does *not* travel by magic. It travels as **HTTP headers** — W3C `traceparent`/`tracestate`. Your gateway must inject them and your Flask service must extract them. Verify by asserting on the header at the boundary; "the tracer should handle it" is how you get two disconnected traces and a confusing dashboard.

### 10.2 Tooling

**C#:**
```
dotnet-counters monitor -p <pid> System.Runtime
    threadpool-queue-length     ← climbing = starvation
    threadpool-thread-count     ← climbing slowly = injection fighting a leak
dotnet-stack report -p <pid>    ← what threads are actually doing
dotnet-dump / dotnet-gcdump     ← for the postmortem
```

**Python:**
```
PYTHONASYNCIODEBUG=1            ← warns on callbacks > 100ms. Use in dev, always.
loop.set_debug(True)
asyncio.all_tasks()             ← what's alive right now
py-spy dump --pid <pid>         ← stack sample without stopping the process
```

**A warning about stack traces.** In async code, a stack trace shows you *the resumption path*, not the logical call chain — the frames that called you are long gone from the stack, because they returned at the suspension. This is why async debugging feels disorienting and why **structured logging with a correlation ID beats stack traces** in async systems. Your instinct to build observability rather than debug interactively is the correct one here; the tooling genuinely is weaker.

---

## 11. An audit checklist for LLM_Monitor

Concrete, ordered by expected payoff. Most of these are an hour each.

**Python service**

- [ ] **Determine your real concurrency.** What gunicorn worker class and how many workers/threads? Fire 20 concurrent requests and measure. If you're on `sync` workers, your concurrency is your worker count — likely 4 — and everything else here is secondary. (§7.5)
- [ ] Grep for `requests.`, `time.sleep`, and any `.encode(`/local model call inside an `async def`. Each is a full-process stall. (§7.3)
- [ ] Turn on `PYTHONASYNCIODEBUG=1` in the dev compose profile. Free bug detection.
- [ ] Check whether the LangChain integrations on your hot path implement real `ainvoke`/`astream` or wrap the sync version in a thread.
- [ ] Put a `Semaphore` in front of Azure OpenAI calls. Its quota is TPM/RPM-based; unbounded `gather` will earn you 429s. (§9.5)
- [ ] `asyncio.timeout(...)` on every outbound call. (§9.6)
- [ ] Replace `gather` with `TaskGroup` where you have sibling tasks. (§7.6)
- [ ] Audit any check-then-act across an `await` — connection/client caching is the usual offender. (§9.7)

**C# gateway**

- [ ] Grep for `.Result`, `.Wait()`, `GetAwaiter().GetResult()`, and `async void`. Each is a latent outage. (§6.4, §9.4)
- [ ] Confirm `HttpContext.RequestAborted` flows through YARP into the Python call and onward to Azure OpenAI. Client disconnects should stop token spend — that's real money on a cost-sensitive project.
- [ ] For the SSE facade: `IAsyncEnumerable` with `[EnumeratorCancellation]`, and verify nothing buffers the response. (§6.5)
- [ ] Use bounded `Channel<T>` for any internal queueing, with an explicit `FullMode`. (§6.5)
- [ ] Baseline `threadpool-queue-length` under load now, so a regression is visible later. (§10.2)

**Both**

- [ ] Assert that `traceparent` is present at the C#→Python boundary. (§10.1)
- [ ] Add a load test — even 50 concurrent requests for 60 seconds. **Every bug in §9 is invisible at concurrency 1.** This is the single highest-value item on the list, because without it none of the others can be verified.

---

## 12. Common mistakes

1. Thinking `async` makes code faster. It makes waiting cheaper. Nothing else.
2. `async` on a CPU-bound method.
3. `.Result` / `.Wait()` anywhere in C# request paths.
4. `async void` (except event handlers) — an unhandled exception crashes the process.
5. `requests` / `time.sleep` / CPU work inside an `async def`.
6. `asyncio.create_task` without keeping a reference — the task can be GC'd mid-flight.
7. `gather` over an unbounded collection with no semaphore.
8. No timeout on an external call.
9. Check-then-act across an `await` (§9.7).
10. Accepting a `CancellationToken` and never passing it down.
11. Assuming single-threaded means race-free.
12. Assuming `await` resumes on the same thread in C#.
13. Holding a lock across an `await`.
14. Using thread-locals for request context in async code — the reason your traces fragment.
15. `ValueTask` awaited twice, or stored. Corruption, not an exception.
16. Believing `async def` in Flask gives you concurrency. It gives you syntax. (§7.5)
17. Testing at concurrency 1 and shipping to concurrency 200.

---

## 13. Interview relevance

This is a favourite senior-level topic because the API is easy and the mechanism separates people.

**Questions you should now answer cold:**

- *"What does `await` actually do?"* → The compiler splits the method into a state machine; locals crossing the await become fields; `await` registers a continuation and **returns**, releasing the thread. Resumption calls back into the state machine and jumps to the saved state. It's a return plus a callback registration — nothing pauses.
- *"Why is async faster?"* → **It isn't.** It's a waiting-capacity technique. A suspended operation costs a heap object instead of a ~1 MB thread stack, so one machine can have far more operations in flight. Throughput per unit of work is unchanged or slightly worse.
- *"What is thread pool starvation and how would you diagnose it?"* → Blocking calls consuming pool threads faster than injection adds them. **Low CPU, low memory, high latency** is the fingerprint. `dotnet-counters` → `threadpool-queue-length`. Fix by removing the blocking call, not by raising `MinThreads` (that's a mitigation that hides the cause).
- *"Why does `.Result` deadlock sometimes but not always?"* → It deadlocks when there's a `SynchronizationContext` demanding resumption on the blocked thread. ASP.NET Core has none, so it starves instead of deadlocking. Different symptom, same root cause.
- *"Is async in Python parallel?"* → No — one thread, concurrency only. Threads don't give CPU parallelism either under the GIL, though free-threaded builds became officially supported in 3.14 and change that story for CPU-bound work. Async was always about I/O, and that's unaffected.
- *"Why does Go not need `async`?"* → Stackful coroutines. A goroutine has a real growable stack multiplexed onto carrier threads, so it can suspend at any call depth and needs no keyword — at the cost of a heavier runtime and per-task memory you can't know at compile time. C#/Python/Rust chose stackless: cheaper and embeddable, but it colors your functions.
- *"Tell me about a hard concurrency bug."* → You have an unusually good answer available: a race between an ISR and a main loop, where the *hardware* preempts mid-instruction and there is no lock primitive at all. Then connect it — that's the same class as check-then-act across an `await`, with the suspension points marked for you.

**The differentiator:** most candidates can describe `await`'s behaviour. Being able to describe the *transform* — locals promoted to fields, the suspension as a return, the waker registration — plus the stackless/stackful trade puts you in a different category. And you can honestly say you've implemented the mechanism by hand on hardware, which almost nobody has.

---

## 14. Where the useful part ends

Your stop line, stated explicitly, because this topic has a very deep floor and you asked for help not falling through it.

**Worth your time (the material above, plus):**
- Decompile one of your own `async` methods in ILSpy or on sharplab.io and read the generated state machine. **One hour, enormous payoff** — it converts everything in §4 from claim to observation.
- Read CPython's `asyncio/base_events.py::_run_once` and `tasks.py::Task.__step`. Genuinely short and readable.
- Stephen Cleary's blog and *Concurrency in C# Cookbook* — the definitive practical source on §6.
- David Beazley's generator/coroutine talks — the best explanation of §7.1 that exists.

**Not worth your time right now:**
- CoreCLR's thread pool implementation or the hill-climbing algorithm's control theory.
- `_asynciomodule.c` (the C reimplementation of asyncio).
- The full `io_uring` interface.
- Rust's `Pin`/`Unpin` and self-referential-struct rules — real, subtle, and only relevant if you're *authoring* futures.
- Writing your own executor for production use.

**The rule:** you need the mechanism to *predict behaviour and diagnose failure*. You do not need the implementation to *use it correctly*. If you catch yourself reading scheduler source to fix a latency bug, stop — the answer is almost certainly a blocking call in your own code, findable in ten minutes with the tooling in §10.2. **Write the question down, run the load test first.**

**Suggested next actions, in order:**
1. Run the load test in §11 (last checkbox). Everything else is hypothesis until you do.
2. Decompile one `async` method and read it.
3. Work the §11 checklist top-down.
4. *Then*, if you want the deep version: build a toy executor in Rust with Embassy, or in C on a board you own — §3 is the design.

---

## 15. Sources

- [How Async/Await Really Works in C# — .NET Blog](https://devblogs.microsoft.com/dotnet/how-async-await-really-works/)
- [Exploring .NET 11 Preview 1 Runtime Async — Laurent Kempé](https://laurentkempe.com/2026/02/14/exploring-net-11-preview-1-runtime-async-a-dive-into-the-future-of-async-in-net/)
- [.NET 11: Runtime Async & the 2026 EOL — architecture guide](https://www.avidclan.com/blog/net-11-the-complete-architecture-guide-runtime-async-2026-eol/)
- [The Async Compiler Transform — in Depth (Async in C#, O'Reilly)](https://www.oreilly.com/library/view/async-in-c/9781449337155/ch14.html)
- [asyncio and free-threaded Python — CPython docs](https://docs.python.org/3/library/asyncio-threading.html)
- [Python support for free threading — CPython docs](https://docs.python.org/3/howto/free-threading-python.html)
- [Python 3.14 free-threading and the JIT — Sean Kim](https://blog.imseankim.com/python-3-14-free-threading-jit-compiler-gil-removal-2026/)
- [Goodbye GIL — exploring free-threaded Python 3.14 — Adarsh Divakaran](https://blog.adarshd.dev/posts/exploring-free-threaded-python-314/)
- [Virtual Threads vs. Coroutines in 2026: Is Java Finally There? — Codemotion](https://www.codemotion.com/magazine/languages/virtual-threads-vs-coroutines-in-2026-codemotion-madrid-2026/)
- [Light-weight concurrency in Java and Kotlin (stackful vs stackless) — Baeldung](https://www.baeldung.com/kotlin/java-kotlin-lightweight-concurrency)
- [Java 25 and the new age of performance: virtual threads and beyond — JavaPro](https://javapro.io/2026/03/05/java-25-and-the-new-age-of-performance-virtual-threads-and-beyond/)

Recommended, not consulted: Stephen Cleary's *Concurrency in C# Cookbook*; Bob Nystrom's *What Color Is Your Function?*; David Beazley's "A Curious Course on Coroutines and Concurrency"; the Embassy book.

---

## Appendix — The one-paragraph version

A blocking call is expensive because a waiting computation holds an entire ~1 MB OS thread stack hostage while doing nothing; async exists to make a suspended computation cost a struct on the heap instead. Everything follows from that. The compiler splits your linear function into a state machine — locals that cross an `await` are promoted to fields, each `await` becomes a case label, and the `await` itself is a plain `return` plus the registration of a callback that will resume you. You have already built this by hand: an ISR that wakes a task and a superloop that polls it is all four organs — transform, handle, waker, executor — with nothing hidden. C# runs those state machines on a **multi-threaded work-stealing pool**, so you get real parallelism and real data races, and blocking a thread with `.Result` either deadlocks you (if a SynchronizationContext demands that exact thread) or starves the pool (in ASP.NET Core, where the fingerprint is low CPU and high latency). Python runs them on a **single-threaded event loop**, so ordinary state is safe but one `requests.get` freezes the entire process — and if your Flask service is on sync gunicorn workers, your real concurrency is your worker count no matter how many `async def`s you write. Both share the failure list: orphaned tasks, unbounded `gather`, missing timeouts, cancellation that never propagates, and check-then-act races across suspension points, which are real even single-threaded because `await` is precisely where interleaving happens. Async is not faster; it is waiting capacity. Measure under real concurrency, because every one of these bugs is invisible at one request at a time.
