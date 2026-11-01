2026_11_01_13_30-(DotNet-Thread-Pool-And-Async-What-It-Saves)

# Lecture 003: The .NET Thread Pool and async/await: What Actually Gets Saved (Measured)

> **For:** Timothy · **Date:** 2026-11-01
> **Prerequisites:** lecture 002 (threads, stacks, reserved vs committed, waiting vs running, context switches). Helpful: lecture 001 §3–§6 (the compiler's state-machine transform; read it after this one if you haven't), `windows_internals/014` §5, §8 (a read request parked in a driver; a reader thread and the UI thread).
> **Why this lecture:** you asked a sharp question: if a server handles 5,000 connections with `async`, doesn't it **still** have 5,000 contexts to keep track of, each with its variables and pipeline state? So what does async actually save? **Your reasoning is right: there are still 5,000 contexts.** What changes is what each context **is**: with blocking threads, a context is a whole OS thread (two stacks, a kernel thread object, a scheduler entry); with async, it's a small heap object holding only the variables that are still needed. This lecture measures that difference, corrects two smaller points (the thread pool doesn't create a fixed set of threads at startup, and calling an async method without `await` doesn't skip running it), and traces what's really happening while a read is "awaited": no thread at all is waiting.
> **Format notes:** every number in this lecture comes from running `code/ConcurrencyLab` (.NET 8, Linux x64 container with 2 cores). Run it yourself on your Mac or the VM: the exact numbers will differ, the ratios won't. No firmware analogies.

---

## Core ideas (the answer key)

1. **5,000 concurrent requests always means 5,000 pieces of state.** The question is how big each piece is and what else it holds on to.
2. **Blocking model:** each request holds an OS thread while it waits. That costs a user stack (reserved address space plus the pages actually touched), a kernel stack, a kernel thread object, and time to create and switch threads. Measured: **~27 KB resident per blocked thread**, ~40 GB of address space reserved for 5,000 on Linux, and seconds to create them.
3. **Async model:** a request that awaits something unfinished **returns its thread to the pool**, and its state moves into a heap object (the method's **state machine**) holding only the locals still needed after the `await`. Measured: **~480 bytes per suspended request** (including a 256-byte buffer), 5,000 of them in ~10 ms, no extra threads.
4. **The thread pool is not a fixed set created at startup.** It starts with **zero** threads, creates them **on demand** quickly up to a minimum (by default, the number of processors), and above that adds threads **slowly** (about one every half second to a second when work is stuck). One pool per process.
5. **Blocking a pool thread is the classic async bug ("sync over async").** Blocked pool threads can't run other work; the pool adds threads slowly; requests queue up. Measured: 64 blocked work items on a 2-core machine → 2 threads at once, then only ~1 more per second.
6. **An async method runs synchronously, on the caller's thread, until its first `await` of something not yet finished.** Only then does it return a `Task` to the caller. Without `await`, the caller continues with that `Task` while the operation is still in progress; it didn't skip the work.
7. **While a read is awaited, no thread is waiting for it.** The socket read is started as a non-blocking OS operation (Windows: overlapped I/O with an I/O completion port; Linux: `epoll`). When data arrives, the OS notifies the runtime, and a pool thread runs the rest of your method. The continuation may run on a **different thread** than the one that started it.
8. **ASP.NET Core doesn't create a thread or a process per request.** Kestrel accepts connections and runs each request's middleware pipeline on pool threads, a slice at a time between awaits.
9. **Async saves threads, not CPU work.** CPU-bound work still needs a thread for as long as it computes. Async helps when requests spend most of their time waiting (network, disk, database).

---

## Table of Contents

- [0. Your questions, answered directly](#0-your-questions-answered-directly)
- [1. What "a context" costs in each model](#1-what-a-context-costs-in-each-model)
- [2. Measured: 5,000 blocked threads vs 5,000 suspended async calls](#2-measured-5000-blocked-threads-vs-5000-suspended-async-calls)
- [3. What happens at `await`, step by step](#3-what-happens-at-await-step-by-step)
- [4. Calling an async method without await](#4-calling-an-async-method-without-await)
- [5. The thread pool, accurately](#5-the-thread-pool-accurately)
- [6. "There is no thread": a socket read from the NIC to your continuation](#6-there-is-no-thread-a-socket-read-from-the-nic-to-your-continuation)
- [7. How ASP.NET Core actually runs 5,000 requests](#7-how-aspnet-core-actually-runs-5000-requests)
- [8. When async doesn't help](#8-when-async-doesnt-help)
- [9. Run the lab](#9-run-the-lab)
- [Misconceptions](#misconceptions)
- [Self-check questions](#self-check-questions)
- [Sources](#sources)

---

## 0. Your questions, answered directly

1. **"Doesn't the app still have 5,000 contexts?"** Yes. Async doesn't remove the per-request state; it shrinks it. A suspended async method keeps its live variables in a heap object of a few hundred bytes. A blocked thread keeps a whole thread: tens of KB of committed stack and kernel memory, plus scheduler bookkeeping. §1–§2.
2. **"1 MB per thread × 5,000 runs out of RAM, but the memory has to exist anyway."** Half right on both sides. The 1 MB (8 MB on Linux) is **reserved address space**, mostly never backed by RAM (lecture 002 §6.2). The real RAM cost per blocked thread measured ~27 KB, plus kernel memory. And no, that memory doesn't have to exist anyway: most of it is stack the thread *could* use, kernel structures for a thread that isn't running, and scheduler state. The async version keeps only the variables your method still needs. §2.
3. **"The pool creates a fixed number of OS threads at startup."** No: zero at startup; created on demand; fast up to a minimum (= processor count by default), slow beyond that. §5.
4. **"Async calls return immediately even though the operation didn't occur."** They run synchronously until the first unfinished `await`, then return a `Task`; the operation has **started** and is in progress. §4.
5. **"Does the framework create a thread or a process per request?"** Neither. One process; a pool of threads shared by all requests; each request's code runs on whatever pool thread is free whenever it has work to do. §7.

---

## 1. What "a context" costs in each model

Picture one request handler:

```csharp
async Task HandleAsync(Socket socket)
{
    var buffer = new byte[256];                     // per-request state
    int n = await socket.ReceiveAsync(buffer);      // wait for the client's data
    Process(buffer, n);
}
```

and its blocking twin, run on a dedicated thread:

```csharp
void Handle(Socket socket)
{
    var buffer = new byte[256];
    int n = socket.Receive(buffer);                 // the thread sleeps in the kernel here
    Process(buffer, n);
}
```

**While waiting for data, what exists for one request?**

| | Blocking thread | Suspended async method |
|---|---|---|
| The request's variables (`buffer`, `socket`) | on the thread's stack / heap | fields of the state-machine object on the heap |
| Where execution resumes | the thread's saved instruction pointer, deep inside the kernel's `recv` | an integer **state** field in the state machine ("resume after await #1") |
| User stack | reserved (1 MB Windows / 8 MB Linux address space) + touched pages (tens of KB) | **none** |
| Kernel stack | ~16 KB (in kernel memory) | **none** |
| Kernel thread object | `KTHREAD`/`ETHREAD` or `task_struct`, a few KB | **none** |
| Scheduler | on the socket's wait list; a context switch to wake it | **none**; a callback is registered with the OS |
| The socket and its kernel receive buffer | exists | exists (same) |

Both columns have one "context" per request. The left column's context is a **whole thread**, whose size is set by what a thread *could* need (a deep call stack, kernel calls). The right column's context is **exactly the variables that are alive across the `await`**, chosen by the compiler.

That's the answer to your question. The variables do have to exist; everything else in the left column doesn't.

---

## 2. Measured: 5,000 blocked threads vs 5,000 suspended async calls

`code/ConcurrencyLab/Program.cs`, experiments `threads` and `tasks`. Both create 5,000 "requests". Each allocates a 256-byte buffer, then waits for the same "data arrived" signal. Threads block on a `ManualResetEventSlim`; async methods await a `TaskCompletionSource`'s task.

```
$ dotnet run -c Release -- threads 5000
before                       OS threads:     9   reserved (virtual):   24.5 GB   resident:   28.6 MB   GC heap:  0.11 MB   t=17 ms
5000 threads blocked waiting OS threads:  5010   reserved (virtual):   64.3 GB   resident:  161.0 MB   GC heap:  7.67 MB   t=2376 ms
after all finished           OS threads:    10   reserved (virtual):   25.0 GB   resident:  124.0 MB   GC heap:  0.50 MB   t=4223 ms

$ dotnet run -c Release -- tasks 5000
before                       OS threads:     9   reserved (virtual):   24.3 GB   resident:   28.1 MB   GC heap:  0.11 MB   t=20 ms
5000 async methods suspended OS threads:    10   reserved (virtual):   24.4 GB   resident:   33.7 MB   GC heap:  2.09 MB   t=29 ms
  one suspended method's state machine type: 480 bytes allocated per suspended call (state machine box + its 256-byte buffer + continuation)
after all finished           OS threads:    13   reserved (virtual):   24.6 GB   resident:   32.8 MB   GC heap:  0.21 MB   t=35 ms
```

**Reading the numbers:**

| Per request, while waiting | Blocking threads | Async |
|---|---|---|
| Reserved address space | (64.3 − 24.5) GB / 5,000 ≈ **8 MB** (Linux's default stack reservation) | ≈ 0 |
| Resident memory (process) | (161.0 − 28.6) MB / 5,000 ≈ **27 KB** | (33.7 − 28.1) MB / 5,000 ≈ **1.1 KB** (the 480-byte object plus GC heap overhead) |
| Kernel memory (not in the process's resident number) | + ~16 KB kernel stack + thread structure | none |
| OS threads | 5,000 extra | 1 extra (pool) |
| Time to set up 5,000 | **~2.4 s** | **~9 ms** |

Notes:
- **24 GB reserved before anything happens** is the .NET runtime reserving address space for its GC heap. It's address space, not RAM, which is the same reserve-vs-commit point again.
- **The 8 MB reservation never turned into 40 GB of RAM.** Each thread touched only the few stack pages it used. That's why "1 MB per thread → 5,000 threads = 5 GB of RAM" is wrong as arithmetic, even though threads are still far more expensive than async state.
- **Resident memory stayed high after the threads finished** (124 MB). Freed stack and runtime memory isn't always returned to the OS right away. Not a leak; just how allocators behave.
- **480 bytes** per suspended call includes the 256-byte buffer. The state machine itself plus the bookkeeping for the `await` is about 200 bytes.

At 5,000 requests the blocking version is survivable (roughly 250 MB once kernel memory is counted). The difference becomes decisive at 50,000 or 500,000 connections, and in **creation and switching time**: every wake-up of a blocked thread is a context switch (lecture 002 §5); an async continuation runs on a pool thread that's already running.

---

## 3. What happens at `await`, step by step

The compiler rewrites an `async` method into a **state machine**: a struct (boxed onto the heap if the method actually suspends) whose fields are the method's local variables that are used after an `await`, plus an integer `state`, plus the "builder" that produces the returned `Task`. Lecture 001 §4 shows the transform in detail. Here's the runtime sequence for `int n = await socket.ReceiveAsync(buffer);`:

```
on some thread T (the caller's thread, or a pool thread):
 1. the method runs normally up to the await: allocates buffer, calls socket.ReceiveAsync(buffer)
 2. ReceiveAsync STARTS the read: asks the OS for a non-blocking receive (§6) and returns an
    awaitable that is not yet completed (no data yet)
 3. await checks: completed? → no
 4. the state machine saves what it needs: state = 1 ("resume after the first await"),
    buffer stays in a field; the state machine is moved to the heap (boxed) if it isn't already
 5. it registers a continuation with the awaitable: "when you complete, call my MoveNext()"
 6. the method RETURNS to its caller, giving back the Task (not completed)
 7. thread T is free: if it's a pool thread, it goes back to the pool and runs other work items

... later, data arrives (§6) ...

on some pool thread U (maybe T, maybe not):
 8. the runtime invokes the continuation → MoveNext() on the state machine
 9. MoveNext sees state = 1, jumps to the code after the await, reads the result (n)
10. the method continues: Process(buffer, n); when it returns, its Task completes,
    which in turn runs ITS caller's continuation (the same steps, one level up)
```

**If the awaited thing is already completed** at step 3 (data was already buffered), there's no suspension: the method just continues on thread T, nothing is boxed, and nothing goes back to the pool. Async has almost no cost when it doesn't need to wait.

**Where your code resumes** is decided by the **synchronization context**: in a console app or ASP.NET Core there is none, so continuations run on pool threads. In a UI app (WinUI, WPF), `await` on the UI thread resumes on the **UI thread** by default, so you can touch controls after the await (it's posted to the UI thread's dispatcher queue: lecture `windows_internals/017` §3).

---

## 4. Calling an async method without await

You noticed you can write `Task<int> t = ReadAsync();` without `await`, get a `Task` back, and keep going. That's right; here's what precisely happens, from experiment `order`:

```
Main on thread 1
1) Call without await:
  [A] ReadAsync starts on thread 1 (runs synchronously so far)
  call returned a Task, IsCompleted=False; caller continues on thread 1
  caller does other work here...
  [A] ReadAsync resumes on thread 5 (a thread-pool thread)
  awaited later: result 42, now on thread 5
2) Call with await:
  [B] ReadAsync starts on thread 5 (runs synchronously so far)
  [B] ReadAsync resumes on thread 5 (a thread-pool thread)
  result 42, now on thread 5
```

What this shows:
1. **`ReadAsync` started executing immediately, on the caller's thread (1).** Calling an async method runs its body synchronously up to its first `await` of something unfinished. It didn't skip anything.
2. At that await (`Task.Delay(100)`), it suspended and **returned a `Task` that isn't completed**. Only then did the caller get control back.
3. **The caller continued on thread 1 while the delay was in progress.** That's the "non-blocking" part: the caller wasn't stuck.
4. The method's second half ran later on **thread 5**, a pool thread: whichever thread was free when the timer fired.
5. `await t` later just picked up the already-in-flight operation's result. **After an await, you may be on a different thread** (Main started on 1 and ended on 5).
6. In run 2, B started on thread 5 and happened to resume on 5 too. No guarantee either way.

**Why that's useful:** start several operations, then await them together:

```csharp
Task<string> a = httpClient.GetStringAsync(urlA);   // both requests are now in flight
Task<string> b = httpClient.GetStringAsync(urlB);
string[] both = await Task.WhenAll(a, b);            // total time ≈ the slower one, not the sum
```

**Why it's dangerous when you never await:** an exception inside a never-awaited task is never observed by anyone ("fire and forget"); nobody knows when it finished; and it can outlive the request or object it uses. The compiler warns you (CS4014). If you truly want fire-and-forget, write `_ = DoAsync();` deliberately and handle exceptions inside it.

---

## 5. The thread pool, accurately

**What it is:** one per process, a set of **background** OS threads plus a **queue of work items** (delegates to run: continuations, `Task.Run` bodies, timer callbacks). Each pool thread loops: take a work item, run it, repeat; sleep when there's nothing to do. Reusing threads avoids paying thread creation (~0.5 ms each, measured in §2: 5,000 in 2.4 s) for every small piece of work.

**How many threads, and when:**
- **At startup: none.** Experiment `pool` printed `pool threads at start: 0`.
- **Up to the minimum, on demand, immediately.** The minimum worker-thread count defaults to the **number of processors** (2 in the container; `ThreadPool.GetMinThreads` tells you). When work arrives and all threads are busy, the pool creates threads right away until it reaches the minimum.
- **Above the minimum, slowly.** The pool tunes the thread count to maximize throughput (completed work items per unit of time). If work is stuck in the queue because threads are blocked, it **injects** extra threads gradually, about one every 0.5–1 s.
- **Idle threads retire** after a while, so the count can drop back below the minimum when demand is low.

**Measured: what blocking pool threads does** (64 work items that each block on an event, 2 cores):

```
processors: 2, pool min worker threads: 2
pool threads at start: 0
t=    0 ms  pool threads:   2   queued items waiting for a thread:  62
t= 1002 ms  pool threads:   3   queued items waiting for a thread:  61
t= 2003 ms  pool threads:   4   queued items waiting for a thread:  61
t= 3003 ms  pool threads:   4   queued items waiting for a thread:  60
t= 4003 ms  pool threads:   6   queued items waiting for a thread:  58
t= 5004 ms  pool threads:   7   queued items waiting for a thread:  57
t= 6004 ms  pool threads:   8   queued items waiting for a thread:  56
```

Two threads immediately (the minimum), then roughly one more per second. After 6 seconds, 56 items haven't even **started**. In a web server, those items are requests: this is **thread-pool starvation**, the most common way an async server falls over. The usual cause is **sync over async**: calling `.Result`, `.Wait()` or `GetAwaiter().GetResult()` on a task inside pool code, which blocks the pool thread until the task completes, often waiting for a continuation that itself needs a free pool thread.

The fix is not "raise the minimum" (it hides the problem and makes every thread more expensive), it's **don't block pool threads**: `await` instead of `.Result`, and use async APIs all the way down.

---

## 6. "There is no thread": a socket read from the NIC to your continuation

Lecture `windows_internals/014` showed the driver side: a read request parked in the driver's queue until data arrives, then completed. An async socket read uses that same mechanism, with **no thread waiting on the request**:

```
your code: await socket.ReceiveAsync(buffer)
   │
   ▼ .NET's socket layer
Windows: issues an OVERLAPPED receive (WSARecv) on a socket associated with an I/O completion port.
         The request goes down to the network stack and is PARKED there (a pending IRP).
Linux:   tries a non-blocking recv; no data → registers the socket with epoll and parks the
         operation in the runtime's own list.
   │
   ▼ your method suspends (§3); the pool thread returns to the pool. NO THREAD IS WAITING.
   ...
packet arrives → NIC interrupt → driver ISR/DPC (lecture 005) → TCP/IP stack puts the data in the socket
   │
Windows: the stack completes the pending request (copies into your buffer); the I/O manager queues a
         completion packet on the completion port.
Linux:   epoll marks the socket ready.
   │
   ▼ a runtime thread that waits on the completion port / epoll (one thread handles MANY sockets)
     picks up the notification and queues your continuation as a work item
   │
   ▼ a pool thread runs MoveNext(): your method continues after the await, with n bytes in buffer
```

So during the wait:
- the **kernel** holds the pending request (Windows) or the epoll registration (Linux): a small structure per socket;
- the **runtime** holds your state machine on the heap;
- **no thread** of yours is blocked. A handful of threads wait on the completion port / epoll **for all sockets at once**.

That's the mechanism behind §1's table. Stephen Cleary's well-known post "There Is No Thread" makes the same point in more depth (Sources).

---

## 7. How ASP.NET Core actually runs 5,000 requests

Your description: a worker service or ASP.NET creates "something" per request (a thread? a process?) that runs through the pipeline and calls the components you registered. The real structure:

```
one process (your app)
 ├─ Kestrel (the web server inside your process)
 │    accepts TCP connections with async accepts; for each connection, reads requests asynchronously
 │
 ├─ for each request: an HttpContext object + a call into the middleware pipeline
 │    middleware 1 → middleware 2 → ... → routing → your controller / endpoint (from DI)
 │    executed on a POOL thread until the first await of something unfinished
 │
 └─ the thread pool: a few dozen threads (on a typical machine), shared by ALL requests
```

- **No process per request; no thread per request.** A request's code runs in slices: from one unfinished await to the next, each slice on whatever pool thread is free. Between slices, the request exists only as objects on the heap (`HttpContext`, the state machines of every async method on its call chain, your DI-scoped services).
- **So your "5,000 contexts" is exactly right**, and those contexts are: 5,000 `HttpContext`s + 5,000 chains of small state machines + 5,000 sockets in the kernel. Not 5,000 threads.
- **A `BackgroundService` (worker service)** is different: it's one long-running async loop you write (`ExecuteAsync`), started once by the host, not per request. It also runs on pool threads between awaits.

The number of pool threads busy at any moment ≈ the number of requests that are **computing** right now, not the number that are **in progress**. For a typical web app that waits on the network and databases most of the time, that's a small fraction.

---

## 8. When async doesn't help

- **CPU-bound work.** Compressing a file, resizing an image, parsing a large document: the work needs a CPU the whole time. `await Task.Run(...)` moves it to a pool thread (useful in a UI app, to keep the UI thread free), but it still occupies a thread while it runs. To go faster, parallelize (lecture `windows_internals/015` §5).
- **Few concurrent operations.** A desktop app with three background operations gains nothing measurable in memory from async over threads. It still gains a simpler way to keep the UI thread responsive.
- **Libraries that are secretly synchronous.** An "async" method that internally blocks (calls a synchronous API, or `.Result`) holds a pool thread anyway: §5's starvation.

The rule of thumb: **async for waiting, threads (or parallelism) for computing.**

---

## 9. Run the lab

On your Mac (Apple Silicon, `brew install dotnet` or the installer from dot.net), or in the Windows VM:

```bash
cd lectures/concurrency/code/ConcurrencyLab
dotnet run -c Release -- order
dotnet run -c Release -- threads 5000
dotnet run -c Release -- tasks 5000
dotnet run -c Release -- pool
```

**Predict before you run:**
1. On Windows, how much **reserved** address space per thread will `threads` show? (Hint: lecture 002 §6.2.)
2. On your 4+ core machine, how many pool threads will `pool` show at t=0?
3. Will `order` print the same thread IDs as above?

| Experiment | Your machine | Prediction | Actual |
|---|---|---|---|
| threads: reserved per thread | | | |
| threads: resident per thread | | | |
| tasks: bytes per suspended call | | | |
| pool: threads at t=0 | | | |

(Expect: about 1 MB reserved per thread on Windows; the pool's t=0 count equal to your processor count; different thread IDs, same pattern.)

---

## Misconceptions

| You thought | Reality | Why |
|---|---|---|
| The pool creates a fixed number of OS threads at startup | Zero at startup; on demand; fast up to processor count, slow beyond | It tunes the count to throughput and retires idle threads |
| A thread costs 1 MB of RAM | 1 MB (Windows) / 8 MB (Linux) **reserved**; ~tens of KB resident, plus kernel memory | Reserve vs commit (lecture 002 §6.2) |
| With async there are still 5,000 contexts | ✅ True | Each is a ~0.5 KB heap object instead of a whole thread |
| Calling an async method without await returns before doing anything | It runs synchronously until its first unfinished await, then returns a `Task` | The operation has started; the caller just doesn't wait for it |
| The framework creates a thread (or process) per request | One process; pool threads shared by all requests, a slice at a time | Requests between awaits are just heap objects |
| Someone (a thread) waits for the socket during `await` | No thread waits; the OS holds the request and notifies a completion port / epoll | One notification thread serves many sockets |
| More threads = more throughput | Only while there are CPUs to run them and they aren't blocked | Context switches and memory grow with every thread |

---

## Self-check questions

1. With async, does a server handling 5,000 concurrent requests still keep 5,000 contexts? What does each consist of?
<details><summary>Answer</summary>Yes. Each is the request's heap objects: its HttpContext, the state machines of the async methods on its call chain (holding the locals live across awaits and a state number), and its socket in the kernel. No thread or stack is held while it waits.</details>

2. Why is "1 MB per thread × 5,000 threads = 5 GB of RAM" wrong, and what's the real per-thread cost?
<details><summary>Answer</summary>The 1 MB (8 MB on Linux) is reserved address space; RAM is used only for stack pages actually touched. Measured: ~27 KB resident per blocked thread in the process, plus about 16 KB of kernel stack and a few KB of kernel thread structure. Still roughly 50–100× more than a suspended async call (~0.5 KB).</details>

3. Describe steps 1–10 of what happens at `await socket.ReceiveAsync(buffer)` when no data is available yet.
<details><summary>Answer</summary>The method runs to the await; ReceiveAsync starts a non-blocking OS receive and returns an incomplete awaitable; await sees it's incomplete; the state machine saves the state number and needed locals (boxed to the heap); registers MoveNext as the continuation; returns an incomplete Task to its caller; the thread goes back to the pool. Later the OS reports completion; the runtime queues the continuation; a pool thread runs MoveNext, which jumps to the code after the await and continues; when the method finishes, its Task completes and its caller's continuation runs.</details>

4. `Task<int> t = ReadAsync();` with no await. Has the read started? On which thread did the first part of `ReadAsync` run?
<details><summary>Answer</summary>Yes, it started: the method ran synchronously on the caller's thread up to its first await of something unfinished, then returned the incomplete Task. The caller continues while the operation is in progress.</details>

5. How many threads does the thread pool have at startup, and how does it grow?
<details><summary>Answer</summary>Zero. It creates threads on demand immediately until it reaches the minimum (default: number of processors), then adds more gradually (roughly one per 0.5–1 s) only if queued work isn't completing, aiming for maximum throughput. Idle threads retire.</details>

6. What is thread-pool starvation, and what code pattern usually causes it?
<details><summary>Answer</summary>Work items (requests, continuations) sit in the queue because all pool threads are blocked, and the pool adds threads only slowly. Usually caused by blocking on async code from pool threads: `.Result`, `.Wait()`, `GetAwaiter().GetResult()`, or synchronous I/O inside async code paths.</details>

7. During an awaited socket read on Windows, what in the system is "holding" the operation, and which thread is waiting?
<details><summary>Answer</summary>The network stack holds the pending overlapped request (a parked IRP), the runtime holds the state machine on the heap; no thread is waiting for this particular read. A runtime thread waits on the I/O completion port for completions from all sockets; when this one completes, the continuation is queued to a pool thread.</details>

8. Does ASP.NET Core create a thread per request? What does a request look like while it's waiting on a database call?
<details><summary>Answer</summary>No. While waiting, the request is only heap objects: its HttpContext, the chain of suspended async state machines, its scoped services, plus the database connection's socket in the kernel. Its code runs in slices on whatever pool threads are free.</details>

9. A request handler compresses a 50 MB upload. Does making it `async` reduce the threads it needs? What would?
<details><summary>Answer</summary>No: compression is CPU-bound and needs a thread for the whole time it computes, async or not. Parallelizing the compression across cores (chunks) makes it finish sooner; async only helps the waiting parts (receiving the upload, writing the result).</details>

10. After `await`, can code be on a different thread than before? When is it guaranteed to come back to the same thread?
<details><summary>Answer</summary>Yes, in console apps and ASP.NET Core it resumes on whatever pool thread runs the continuation (the lab showed Main start on thread 1 and finish on thread 5). In UI apps, an await started on the UI thread resumes on the UI thread by default, because the UI synchronization context posts the continuation back to the UI thread's queue.</details>

---

## Sources

- Microsoft Learn, [The managed thread pool](https://learn.microsoft.com/en-us/dotnet/standard/threading/the-managed-thread-pool) (one per process; background threads; threads on demand up to the minimum; creates/destroys threads to optimize throughput; blocked threads prevent tasks from starting). Checked 2026-11-01.
- Microsoft Learn, [ThreadPool.GetMinThreads](https://learn.microsoft.com/en-us/dotnet/api/system.threading.threadpool.getminthreads) / [SetMinThreads](https://learn.microsoft.com/en-us/dotnet/api/system.threading.threadpool.setminthreads). Checked 2026-11-01.
- Microsoft Learn, [Debug thread pool starvation](https://learn.microsoft.com/en-us/dotnet/core/diagnostics/debug-threadpool-starvation) and [ASP.NET Core best practices: avoid blocking calls](https://learn.microsoft.com/en-us/aspnet/core/fundamentals/best-practices). Checked 2026-11-01.
- Microsoft Learn, [Thread Stack Size](https://learn.microsoft.com/en-us/windows/win32/procthread/thread-stack-size) (reserve vs commit). Checked 2026-11-01.
- Microsoft Learn, [I/O Completion Ports](https://learn.microsoft.com/en-us/windows/win32/fileio/i-o-completion-ports). Linux man page [epoll(7)](https://man7.org/linux/man-pages/man7/epoll.7.html). Checked 2026-11-01.
- Stephen Toub, [How Async/Await Really Works in C#](https://devblogs.microsoft.com/dotnet/how-async-await-really-works/) (.NET Blog, March 2023). Checked 2026-11-01.
- Stephen Cleary, [There Is No Thread](https://blog.stephencleary.com/2013/11/there-is-no-thread.html) (2013). Checked 2026-11-01.
- Code: `code/ConcurrencyLab` (.NET 8.0.133 SDK, Linux x64 container, 2 cores), run 2026-11-01.
