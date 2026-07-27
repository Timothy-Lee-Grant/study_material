# Lecture 001 — How Production Software Actually Works

> **For:** Timothy Lee Grant
> **Date:** 2026-07-26
> **Why this lecture, and why now:** You have a DSA system, a resume strategy, and a work
> deep-dive map. What you *don't* have anywhere in this repo is the actual content — the
> concepts themselves. `LEARNING/Ghosts_Im_Scared_Of.md` is a list of fears with no answers
> under them. This lecture puts answers under them.
>
> **Read time:** ~45 minutes. **Payback:** this is the vocabulary that separates "I wrote
> code that works" from "I'm an engineer who ships systems." It's what the non-DSA 40% of a
> Microsoft loop tests, and it's the thing you're losing sleep over.

---

## 0. The frame: why your fear is wrong-shaped

Timothy — read this part slowly, because it's the highest-ROI paragraph in the document.

Your anxiety, in your own words, is: *"there is so much that I need to understand and it will
come to get me."* You've modeled the unknown as **infinite**. Infinite threats can't be
prepared for, so your brain runs the threat simulation at 2am forever.

Here's the correction: **it is not infinite. It's about seven ideas.**

Not seven facts — seven *ideas*, each of which shows up over and over wearing different
costumes. Once you have them, new technologies stop being new. Kafka is a queue with
durability. Kubernetes is a scheduler with a reconciliation loop. RDS is a database someone
else babysits. Redis is a hashmap on a socket. You already know what a queue, a scheduler,
a database, and a hashmap are. The "so much to learn" feeling is mostly **vocabulary shock** —
a thousand product names sitting on top of a small set of concepts.

The seven ideas, in the order they'll pay you back:

| # | Idea | Why it pays now |
|---|---|---|
| 1 | **Concurrency** — more than one thing happening at once | Microsoft drills this harder than any other non-DSA topic. It's already in your C# app. |
| 2 | **Failure is normal** — timeouts, retries, idempotency | Your shutdown orchestration *is* this problem. Best system-design story you own. |
| 3 | **Observability** — how you know what your system is doing | Cheapest new skill you can add at work. Nobody will fight you for it. |
| 4 | **Testing** — how you know it works before users do | You named "testing instincts" as a fear. It's ~5 concepts. |
| 5 | **Release & rollout** — how code safely reaches users | You named it. Microsoft invented the vocabulary you'll use. |
| 6 | **The cloud, demystified** — rented primitives, nothing more | Kills the biggest ghost ("you don't know what you don't know"). |
| 7 | **What "good instincts" actually are** — the thing you think others have | Ends the imposter loop with a concrete list. |

Every section below gives you: **the concept → the mechanism → what it looks like in your
actual code at Curtiss-Wright → the interview question it answers → a bounded action.**

One rule before we start: **this does not outrank LeetCode.** Coding at ~30% on mediums is
still the gate to the offer. This lecture wins the other 40% of the loop and makes the
referral compelling. Do it around the reps, not instead of them.

---

## 1. Concurrency — the one Microsoft actually drills

### 1.1 The core idea

Concurrency is when two pieces of code make progress during overlapping time windows. That's
it. The danger isn't the overlap — it's **shared mutable state**. Two threads reading and
writing the same memory with no agreement about who goes first.

The canonical bug, in four lines:

```csharp
// Thread A and Thread B both run this
counter = counter + 1;
```

That single line is really three machine operations: **read** counter, **add** 1, **write**
counter back. If A reads 5, then B reads 5, then both add and both write 6 — you incremented
twice and got one. This is a **race condition**: the result depends on timing, so it's
correct 999 times and wrong once, at 3am, in production, in a way you cannot reproduce.

Three ideas do 90% of the work:

- **Atomicity** — an operation that can't be observed half-done. `Interlocked.Increment(ref
  counter)` is atomic; `counter++` is not.
- **Mutual exclusion** — only one thread in the critical section at a time. That's a `lock`.
- **Visibility / memory model** — even without a torn write, thread B might not *see* thread
  A's write for a while, because CPUs and compilers reorder and cache. `volatile`, `lock`,
  and `Interlocked` all insert memory barriers that force visibility. This is the part most
  candidates have never heard of and where your ECE background is an unfair advantage: you
  already understand caches and store buffers. **Say that out loud in an interview.**

### 1.2 The C# toolkit (your stack — know these cold)

| Tool | Use it for | Gotcha that trips people |
|---|---|---|
| `lock (obj) { }` | Guarding a critical section | Re-entrant (same thread can re-enter). Never `lock` on `this`, a `string`, or a public object — someone else can lock it too and deadlock you. Keep the section *short*. |
| `Interlocked.*` | Counters, compare-and-swap | Lock-free and fast, but only for single variables. |
| `SemaphoreSlim` | Limiting concurrency to N; async-safe locking | **Not** re-entrant. Use `WaitAsync` when you need to lock across an `await` (you cannot `await` inside `lock`). |
| `ConcurrentDictionary` | Shared map | `GetOrAdd`'s value factory **can run more than once** under contention. Don't put side effects in it. |
| `Channel<T>` / `BlockingCollection<T>` | Producer/consumer handoff | The right answer to "how do I get data from a fast producer to a slow consumer" — includes **backpressure** (bounded channel makes the producer wait). |
| `CancellationToken` | Timeouts and shutdown | Should thread through *every* async API you write. This is a code-review tell for senior. |
| `async`/`await` | I/O-bound waiting | **Async is not threads.** It frees the thread while waiting on I/O. It does not make CPU work parallel. `async void` is a landmine — exceptions can't be caught; only use for event handlers. |

**The distinction interviewers listen for:** *concurrency* (structuring work so tasks can
overlap — often on one thread, via async) vs *parallelism* (actually running simultaneously
on multiple cores). Async/await is concurrency. `Parallel.ForEach` is parallelism.

### 1.3 In your actual code — go find these

Your telemetry app is a textbook concurrency system and you may not have noticed: a **native
P/Invoke callback thread** pushing telemetry, while a **web dashboard** and a **live
PowerShell table** both read, with **concurrent SQLite writes** underneath.

Four specific things to go look at Monday morning:

1. **What thread does the P/Invoke callback run on?** It's a thread created by the *native*
   library, not the CLR. It has no `SynchronizationContext`. Anything you touch from it —
   UI state, a `List<T>`, a cached object — is being touched from a thread you didn't
   create and don't control.
2. **Is the managed delegate you handed to native code being kept alive?** If the only
   reference to that delegate is the one you passed across the P/Invoke boundary, the GC
   doesn't see it and can collect it — and then the native callback fires into freed memory
   and the process dies. The fix is holding a static field or a `GCHandle`. **If this bug is
   in your code, finding it is the single most valuable hour you'll spend this month** — it's
   a concurrency + memory-model + interop story in one, and almost no SDE I candidate has one.
3. **How does SQLite handle two writers?** By default it doesn't — you get `SQLITE_BUSY`.
   The real answers are **WAL mode** (one writer, many concurrent readers) plus a
   `busy_timeout`, or funneling all writes through a single writer task fed by a `Channel<T>`.
   Which one is your app doing? If the answer is "nothing, and it hasn't broken yet," that's
   a latent bug and a great thing to fix.
4. **Is the read path consistent?** While the dashboard renders a snapshot, the callback is
   mutating. Do readers ever see a half-updated record?

### 1.4 The interview

The question is almost always: **"Tell me about a concurrency bug you found and fixed."**
It is one of the two or three most-asked engineering behaviorals at Microsoft. Right now you
cannot answer it. After you find a real race in your own code, you can answer it better than
most SDE IIs — because it's *yours*, with a hardware callback in it.

**Structure the answer:** symptom (intermittent, unreproducible — say that word) → how you
narrowed it → the shared state and the interleaving that broke it → the fix → *how you
verified the fix* (this last part is what separates good from great; "it stopped happening"
is not verification).

### 1.5 Your action (bounded — one week)

- [ ] Draw your app's threads on paper: every box that produces or consumes data, every arrow
      between them. Circle every piece of state touched by two arrows. **That circle is your
      bug list.**
- [ ] Answer the four questions in §1.3 in writing.
- [ ] Write it up as STAR story #2 in `LEARNING/interview_prep/behavioral_stories.md`.

---

## 2. Failure is normal — timeouts, retries, idempotency

### 2.1 The mental shift

Junior code assumes calls succeed. Senior code assumes **every call across a network can
fail, hang forever, or succeed in a way you never find out about.** That third one is the
scary one and it's the whole subject.

When you send a request and get no response, you cannot distinguish between:
1. the request never arrived,
2. it arrived and failed,
3. **it arrived, succeeded, and the response got lost.**

There is no message you can send that resolves this ambiguity in general (this is the Two
Generals problem). So you don't solve it — you **design around it**. That's what the
following five tools are.

### 2.2 The five tools

**Timeouts.** Every network call gets one. A call without a timeout isn't a call, it's a
hostage situation — one hung dependency exhausts your thread pool and takes down a service
that was otherwise healthy. Better: propagate a **deadline** end-to-end ("this whole
operation must finish by T"), so downstream calls inherit the remaining budget instead of
each getting a fresh 30 seconds. `CancellationTokenSource(TimeSpan)` is your primitive.

**Retries — with backoff and jitter.** Retrying immediately is how you turn a blip into an
outage: every client retries at once, hammers the recovering service, and knocks it back
down (a *thundering herd*). So:
- **Exponential backoff:** wait 1s, 2s, 4s, 8s.
- **Jitter:** randomize each wait, so clients don't synchronize. Backoff without jitter still
  produces a herd, just a later one. Mentioning jitter unprompted reads as experienced.
- **Retry budget / cap:** bound total attempts, and don't retry at *every* layer of the
  stack — 3 layers × 3 retries = 27 requests.
- **Only retry what's safe to retry** — which brings us to:

**Idempotency.** An operation is idempotent if doing it twice has the same effect as doing it
once. `DELETE /order/42` is idempotent. `POST /charge $100` is not. Since you can't know
whether your lost request succeeded, **the only safe retry is an idempotent one.** Make
operations idempotent by design: use an **idempotency key** (client generates a unique ID; the
server records it and returns the original result on a repeat), or design state transitions to
be "set to X" rather than "add one to X."

For your shutdown system, ask exactly this: *if the battery dies mid-shutdown and we power
back up, can we just run the whole sequence again safely?* If yes, you have a resumable
system. If no, you have a story about why not and what you'd change.

**Delivery semantics.** Three phrases, know which one you're building:
- *At-most-once* — send and don't retry. May lose work. Fine for a metric.
- *At-least-once* — retry until acked. May duplicate. **The default in practice.**
- *Exactly-once* — doesn't exist over an unreliable network. What people mean is at-least-once
  delivery + idempotent processing (dedup on the receiver). Saying this sentence in a system
  design interview is worth real points.

**Circuit breaker + graceful degradation.** If a dependency is failing, stop calling it for a
while — *closed* (normal) → *open* (fail fast, don't even try) → *half-open* (let one probe
through to test recovery). This protects both you and the struggling dependency. In .NET the
library is **Polly**, and it does retries, backoff, jitter, timeouts, and breakers. Know the
name. Then: when a dependency is down, what's the **degraded** behavior? Serving stale cached
data beats a 500. Deciding that *deliberately* is design.

### 2.3 In your actual code

Your power-loss shutdown orchestration is a distributed system with a hard real-time deadline
and a battery-shaped budget. That is a *genuinely good* system design case. The senior
engineers may have built the happy path — **the failure modes are unclaimed, and they're the
interesting 80%.** Go own them:

- What happens if a server doesn't respond? Responds slowly? Responds *after* you gave up?
- What's the shutdown **order**, and what's the dependency reasoning behind it?
- Timeout per node vs. a global deadline — how is the battery budget divided?
- Is the sequence **idempotent / resumable** after a mid-shutdown power loss?
- What if two shutdown triggers fire at once (**re-entrancy** — is there a guard)?
- Confirmation vs fire-and-forget: how do you *know* a node actually shut down?

### 2.4 The interview

This maps to both the behavioral ("tell me about designing for failure / a time you handled
an edge case nobody asked you to") and the system design round. For SDE I, system design is
light, but "what's your timeout and retry policy?" and "is that idempotent?" are asked at
every level, including in code review.

### 2.5 Your action

- [ ] Write the answers to the six questions in §2.3 into
      `LEARNING/interview_prep/system_design.md` as a whiteboard-able case.
- [ ] Find one call in your codebase with no timeout. Add one. That's a real, shippable,
      low-risk improvement and a resume line.

---

## 3. Observability — knowing what your system is doing

### 3.1 The three signals

Not "logging." Three distinct things with different costs and jobs:

- **Logs** — discrete events with detail. High cardinality, expensive at volume. Answer:
  *"what exactly happened in this one case?"*
- **Metrics** — numbers aggregated over time (counters, gauges, histograms). Cheap, always
  on. Answer: *"is the system healthy right now, and is it getting worse?"*
- **Traces** — the causal path of one request across components, with timing per hop.
  Answer: *"where did the 3 seconds go?"*

The classic mistake: trying to make logs do the metrics job (grepping logs to count errors)
or the traces job (correlating by eyeball).

### 3.2 The mechanics that matter

**Structured logging.** Not `$"User {id} failed"` — that's a string you can never query.
Instead `logger.LogWarning("Shutdown failed for {NodeId} after {ElapsedMs}ms", nodeId, ms)`.
The message template stays constant and the fields are queryable. In .NET this is `ILogger<T>`
and it's built in. **This one change is the highest-ROI thing you can do to your telemetry app.**

**Correlation IDs.** One ID attached to everything belonging to a single operation, passed
across every boundary. Without it, distributed debugging is impossible. With it, one query
gives you the whole story. In .NET this is `Activity` / `ActivitySource`, which implements
W3C trace context.

**Cardinality.** A metric labeled with `user_id` creates one time series per user and will
destroy your metrics backend. Labels must be low-cardinality (status code, region, endpoint).
Knowing this is a strong signal you've operated something real.

**What to actually measure.** Two mnemonics, both worth memorizing:
- **RED** (for services): **R**ate, **E**rrors, **D**uration.
- **USE** (for resources): **U**tilization, **S**aturation, **E**rrors.

And measure **latency as percentiles, never averages.** p50/p95/p99. An average hides the
fact that 1% of your users are having a terrible time — and at scale, that 1% is everyone,
eventually, because one slow page has many requests in it.

**OpenTelemetry (OTel)** is the vendor-neutral standard for emitting all three signals;
.NET has first-class support (`System.Diagnostics.Metrics`, `ActivitySource`). Learn the
concept, not a vendor.

### 3.3 In your actual code + your action

Your telemetry app almost certainly has ad-hoc `Console.WriteLine`-grade logging. Adding
structured logging plus three or four health metrics is: low-risk, uncontested, genuinely
useful to your team, a new skill in your target direction, a resume line, and an "I improved
operability" story. That's an absurd return for a couple of afternoons.

- [ ] Convert your app's logging to structured `ILogger` with proper levels.
- [ ] Add a correlation ID to a shutdown operation so you can trace one run end-to-end.
- [ ] Add 3 metrics: telemetry messages/sec, DB write duration, shutdown attempts/failures.

---

## 4. Testing — how you know it works before users do

You named "testing instincts" as a fear. Here is the whole thing, honestly:

**The pyramid.** Many fast **unit** tests (one thing, no I/O, milliseconds) → fewer
**integration** tests (real DB, real file system, real interop) → very few **end-to-end**
tests (slow, flaky, but they're the only ones that prove the whole thing works). If your
pyramid is upside down, your suite is slow and everyone stops trusting it.

**The instinct you're missing is a design instinct, not a testing one.** Untestable code is
code where the logic is welded to the I/O. If a method opens the DB, computes something, and
writes a file, you can't test the computation. You make it testable by introducing **seams**:
pass dependencies in (constructor injection), depend on an interface, and keep the decision
logic in pure functions that take data and return data. So: **"hard to test" is a design
smell, not a testing chore.** That's the sentence you were missing.

**What to test.** Not "everything." Test: the boundaries (empty, one, many, max), the error
paths (the ones nobody writes and everybody hits), the branch conditions, and — most
valuable — **every bug you fix gets a test that would have caught it.** That last habit
is what "testing instincts" mostly means in practice.

**Determinism.** Flaky tests are worse than no tests because they train people to ignore red.
The usual culprits: real clocks (inject an `IClock`), real randomness (inject the seed), real
network, `Thread.Sleep` used as synchronization, and shared state between tests. Testing
concurrent code is genuinely hard — the practical technique is to make the interleaving
*injectable* (a hook you can pause at) rather than hoping a race reproduces.

**Coverage is a diagnostic, not a target.** 100% coverage of code with no assertions proves
nothing. Low coverage on your core logic is a real signal.

- [ ] **Action:** pick the most logic-dense class in your C# app and write 5 unit tests for
      it — the happy path, two boundaries, two error paths. Notice what you had to change to
      make it testable. *That noticing is the skill.*

---

## 5. Release & rollout — how code safely reaches users

Another named fear, and again: it's five ideas.

- **Environments** — dev → test/staging → production. Staging exists to be as close to prod
  as you can afford. It's never close enough; plan for that.
- **Rings / canary** — don't ship to everyone. Ship to 1% (or an internal ring) first, watch
  the metrics from §3, then widen. **Microsoft literally calls these "rings"** — using that
  word in an interview lands well.
- **Feature flags** — decouple *deploying* code from *releasing* behavior. Ship the code dark,
  turn it on for 1% by config, turn it off instantly if the graphs go bad. This is the single
  biggest de-risking tool in modern release engineering.
- **Rollback** — you must be able to go back fast, and "fast" means minutes. Corollary:
  **every change should be reversible, and if it isn't, that's the risky part of the plan.**
- **Backward compatibility** — the hard one. During a rollout, old and new code run *at the
  same time*, against the same data. So schema changes go **expand → migrate → contract**:
  add the new column (both versions work), backfill and move readers/writers over, only then
  remove the old one. Never rename a column in one deploy. Same rule for API contracts: add
  fields, don't remove or repurpose them.

The unifying principle: **make changes small, reversible, and observable.** Big-bang releases
are how you end up debugging at 3am, which is the future you're anxious about.

- [ ] **Action:** write down how software actually gets from your machine to those 3,000+
      units in the field. Where's the review? The test gate? The rollback path? If the answer
      is "there isn't one," *that gap is an opportunity*, and describing it clearly is itself
      a strong interview answer.

---

## 6. The cloud, demystified

Your ghost doc says: *"The entire idea of cloud. You don't know what you don't know."* Let's
kill that one.

**The cloud is rented primitives behind an API.** There are essentially six, and you already
understand all six from your OS and networking courses:

| Primitive | What it is | AWS | Azure |
|---|---|---|---|
| **Compute** | A machine to run code on | EC2, Lambda | VM, Functions, App Service |
| **Storage** | A giant durable bucket of bytes | S3 | Blob Storage |
| **Database** | A managed DB you don't babysit | RDS, DynamoDB | Azure SQL, Cosmos DB |
| **Network** | A virtual network + firewall rules | VPC, subnets, security groups | VNet, subnets, NSGs |
| **Identity** | Who may do what to which resource | IAM roles/policies | Entra ID, RBAC |
| **Messaging** | Queues and event streams | SQS, Kinesis | Service Bus, Event Hubs |

Everything else in the 200-service console is a combination or a convenience on top of these.
**That's the whole map.** You are not missing a secret eighth thing.

**"Managed" — the word that explains the pricing and the fear.** You named RDS specifically,
so: RDS is Postgres/MySQL running on a machine *Amazon* owns. They handle provisioning, OS
and DB patching, automated backups, point-in-time restore, and (if you enable Multi-AZ) a
standby replica in another datacenter with automatic failover. You get a hostname and a port.
What you give up: no OS access, less config control, and you pay a premium for someone else's
on-call rotation. That's the entire trade, and it's the same trade for every "managed"
service. Azure's equivalents are Azure SQL Database and Azure Database for PostgreSQL.

**The networking piece** (your other named fear) is just a firewall diagram: a **VNet/VPC** is
a private address space; **subnets** slice it; **public subnets** have a route to the internet
gateway, **private subnets** don't; **security groups / NSGs** are per-resource allow-rules.
The single most common cloud confusion — "why can't my app reach my database?" — is almost
always one of: wrong subnet, missing security-group rule, or missing DNS/endpoint. Knowing
those three suspects makes you look experienced immediately.

**Since your target is Microsoft: bias every hour of cloud learning to Azure.** Same concepts,
their vocabulary. And when you deploy your flagship project, deploy it on Azure — it converts
your weakest area into a talking point on their home turf.

- [ ] **Action:** for your ad-server project, write one paragraph per AWS service you used
      explaining *what it actually is and why you chose it.* Anything on your resume you
      can't explain in a paragraph is a liability in a resume-walkthrough round — and you
      already flagged this yourself. This exercise deletes that fear permanently.

---

## 7. What "good instincts" actually are

You wrote that you're worried you'll join a real company and fail because you lack the skills
mid-level engineers have. Here is that list, concretely, so it stops being a fog:

1. **They read code before writing it.** They assume the existing system has reasons, and
   they go find them.
2. **They make the change small.** One concern per PR. They know a 40-line diff gets a real
   review and a 2,000-line diff gets a rubber stamp.
3. **They handle the error path first.** Junior code has the happy path and a `TODO`.
4. **They know what they don't know, out loud, early.** The expensive failure mode is silent
   flailing for three days — not asking on day one.
5. **They design for the reader.** Names, boundaries, and a comment explaining *why* (the
   code already says what).
6. **They think about operations.** How will I know this broke? How do I roll it back?
7. **They finish things.** Shipped and slightly imperfect beats elegant and 80% done. *This
   is your named weak spot — your instinct is to over-engineer and not ship. Ship-first is a
   deliberate correction you need to practice, not a compromise.*

Look at that list honestly. You have #1, #4, and #7-when-forced. #3 and #6 are what this
lecture just gave you. **None of it is genius. All of it is habit.**

And the reframe you need: you're comparing your **insides** — every doubt, every gap — to
other engineers' **outsides**, where you only see the confident answer and never the hour of
confusion behind it. The 2026-06-27 diagnostic in your skill tracker says you independently
discovered loop-invariant reasoning and wrong-path detection. Those are senior habits that
nobody taught you. **Your self-rating is the least accurate data in this repo.**

---

## 8. How to actually use this

**Priority reminder, because it matters:** LeetCode mediums 30% → 70% is still the gate.
Nothing here outranks the daily reps. This lecture is what you do *around* them — 30–45
minutes a few evenings a week, and at work where it's free.

**The conversion rule.** A concept you understood but never wrote down is worth ~zero in an
interview. Every section above must end as an artifact:

| Section | Artifact | Goes in |
|---|---|---|
| Concurrency | STAR: "a concurrency bug I found" | `interview_prep/behavioral_stories.md` |
| Failure design | System design case: shutdown under failure | `interview_prep/system_design.md` |
| Observability | STAR: "I improved operability" + a real PR | both + `progress_log.md` |
| Testing | 5 tests + what you had to change | `progress_log.md` |
| Rollout | Written description of your real release path | `interview_prep/system_design.md` |
| Cloud | One paragraph per service on your resume | `PROJECTS/ad-bidding-pipeline/` |

**Suggested order (4 weeks, sustainable):**

- **Week 1** — Concurrency. Draw the thread diagram, answer the four questions, hunt the race.
- **Week 2** — Failure design. Answer the six shutdown questions; add one timeout.
- **Week 3** — Observability. Structured logging + 3 metrics in the telemetry app.
- **Week 4** — Testing + cloud paragraphs. Then update `Ghosts_Im_Scared_Of.md` — go back and
  *cross things off*. Watching that list shrink is the point of the whole exercise.

**Next lectures** (say the word and I'll write them):
- **002** — Concurrency deep-dive in C#: the .NET memory model, async internals, P/Invoke
  threading and GC interaction, with drills.
- **003** — System design from zero: the 8-step framework, the estimation math, and three
  worked cases built from *your* systems.
- **004** — Distributed systems concepts for an SDE loop: replication, partitioning,
  consistency models, consensus, caching — the ideas behind every "at scale" question.

---

## The one-paragraph version

Everything you're afraid of reduces to seven ideas: things happen at once (**concurrency**),
things fail (**timeouts, retries, idempotency**), you need to see inside (**observability**),
you need to know it works (**testing**), it has to reach users safely (**rollout**), the cloud
is six rented primitives, and "good instincts" is a list of seven habits, not a talent. You
already own the hardest prerequisite — you understand how machines actually work, which most
backend candidates don't. What's left is naming things, writing them down, and shipping.

The fog isn't infinite, Timothy. It's a checklist. Start crossing it off.

---
*Lecture 001 — created 2026-07-26. Companions: `LEARNING/Ghosts_Im_Scared_Of.md` (fill in the
answers), `ROADMAP/work_deepdive_strategy.md` (where to spend effort at work),
`LEARNING/dsa/` (the #1 priority — don't let this lecture displace the reps).*
