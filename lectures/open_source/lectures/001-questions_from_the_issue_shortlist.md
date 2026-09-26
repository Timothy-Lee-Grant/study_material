# Lecture 001 — Questions From the Issue Shortlist

> **What this is:** a running Q&A log. As I read `implementations/001-issue_shortlist_sept_2026.md`, I ask questions about things I don't understand or want to explore, and each answer is **appended** here, newest at the bottom.
> **Started:** 2026-09-26
>
> **Format for each entry:** the question (in my words) → the short answer → the full explanation → what to take away → interview relevance (where it applies).

---

## Index

| # | Question | Related issue | Topic |
|---|---|---|---|
| Q1 | Why do maintainers open an issue for a simple docs fix instead of just doing it? | YARP #1764 (item A) | How open-source projects actually run |
| Q2 | I found `src/TelemetryConsumption/WebSockets/` in YARP, but it's all C#. Where are the docs, and what am I misunderstanding? | YARP #1764 (item A) | Code vs. docs repos; finding a doc's source; verifying before contributing |

---

## Q1. Why open an issue for a simple docs fix instead of just doing it?

**Related:** [YARP #1764](https://github.com/dotnet/yarp/issues/1764), item A in the shortlist · **Asked:** 2026-09-26

### The question

In YARP #1764, the maintainer already explained exactly what the docs should say (the 100-second activity timeout, and that keep-alives must come from the client or server). It's a small documentation change. So why open an issue, describe it in detail, and then leave it for years instead of spending a few minutes to just fix it, especially when Microsoft engineers have AI and powerful internal tools? I'd understand leaving a hard bug open, or something needing special hardware, but this seems like it should take less effort to fix than to write up.

### The short answer

Because **the scarce resource isn't typing. It's a maintainer's attention**, and an issue is the cheapest way to *record* knowledge without *spending* that attention right now. The explanation in the issue took a couple of minutes, as part of answering a user. Turning it into a merged docs change takes a context switch, a different repo, a review, and a publish cycle. That's small in absolute terms, but it competes with bugs, security fixes, and releases, and it **always loses that competition**. Leaving it labeled `help wanted` also serves a second purpose: it's a deliberate entry point for new contributors like you.

### The full explanation

#### 1. The issue is a "bottom half," not a to-do list

Here's a firmware analogy that fits almost exactly.

```
 Firmware                                   Open-source maintainer
 ────────                                   ──────────────────────
 An interrupt fires                    ≈    A user reports "my WebSocket keeps dropping"
 The ISR (top half) does the minimum:  ≈    The maintainer answers the user in 2 minutes:
   acknowledge, capture state, return         "100 s activity timeout; use keep-alives"
 The rest is deferred to a             ≈    The leftover work ("the docs should say this")
   bottom half / work queue                   is deferred to an issue, labeled and queued
 The scheduler runs deferred work      ≈    Someone picks up the issue when priorities
   when higher priorities allow                allow: a maintainer, or the community
```

The maintainer handled the **urgent** part (unblock the user) and **deferred** the non-urgent part (improve the docs) so it wouldn't be forgotten. Writing the issue wasn't "more work than fixing it." It was the cheapest way to **save the knowledge** while going back to higher-priority work.

#### 2. A priority queue without aging starves low-priority work

YARP has a small core team whose members also own other parts of ASP.NET Core networking. Their queue always contains security issues, regressions, release work, customer escalations, and design reviews for new features. A docs clarification is real but **low severity**: nobody's production is down because of it.

In a scheduler with strict priorities and no **aging** (bumping a task's priority the longer it waits), low-priority tasks can wait forever. That's exactly how an issue like #1764 sits in the `Backlog` milestone for years. Nobody decided "we won't do this." It just never rose to the top. The `help wanted` label is the maintainers' way of saying: *"We won't get to this soon, and we'd welcome someone else doing it."*

#### 3. "Simple" changes aren't free for a maintainer

For you, a first docs PR is a learning exercise. For a maintainer, even a small change has fixed costs:

| Cost | For #1764 specifically |
|---|---|
| **Context switch** | Stop current work, reload the docs structure, find the right page |
| **Different repo, different process** | YARP's docs moved into `dotnet/AspNetCore.Docs`, which has its own style guide, PR template, and reviewers from the docs team |
| **Getting it right** | Correct property names, correct version behavior, a code sample that actually works. Docs are read by thousands of people, so a wrong statement is expensive. |
| **Review and publishing** | Someone must review it; the docs build must pass; it must be published |

Maybe 30–90 minutes in total. That's small, but it's 30–90 minutes that isn't spent on a regression, and there are dozens of these in the backlog.

**Ownership diffusion makes it worse.** When the docs moved to a different repository, "who owns this change?" got fuzzier. The YARP engineers own the knowledge, while the docs repo has different owners. Small tasks that fall between two owners are the ones most likely to sit untouched. This happens inside every large company, not just in open source.

#### 4. `help wanted` issues are deliberately left for newcomers

This is the part that's easiest to miss. Healthy projects **intentionally keep a supply of small, well-described tasks** for new contributors:

- **They're the on-ramp.** A newcomer can't start with a subtle proxy bug. They need a task where the answer is known, so they can learn the process (fork, CLA, review, merge) with low risk.
- **Contributors are a long-term investment.** Every person who lands a first docs PR might become a regular, and regulars eventually take real work off the maintainers. That only happens if easy entry points exist. If maintainers fixed every easy thing themselves, the pipeline would dry up.
- **A detailed description is the point.** The maintainer wrote exactly what the docs should say *so that someone without insider knowledge can do it correctly*. That's a well-written ticket, not wasted effort.

So when you see a small, fully-explained `help wanted` issue, read it as: **"This one was left here on purpose, for someone like you."**

#### 5. Why AI and Microsoft's internal tools don't change this

The bottleneck was never producing the text. It's:

- **Deciding** it's worth doing now, over everything else (attention and priority)
- **Verifying** it's correct (judgment)
- **Reviewing and owning** the change after it ships (accountability)

AI speeds up the writing, but a human maintainer still has to decide, verify, review, and own it. Meanwhile, AI has *increased* the review burden across open source: maintainers now receive many low-effort, AI-generated PRs (Hacktoberfest stopped counting PRs in 2026 for exactly this reason). A careful human contribution that's verified and correct is more valuable to maintainers now, not less.

#### 6. To be fair: sometimes it really is just forgotten

Not every old issue is a deliberate on-ramp. Some are simply forgotten, and a maintainer might fix one in five minutes the day someone mentions it. That's fine too. Commenting "I'd like to take this" either gets you the task or prompts the maintainer to close it. Either way, the backlog gets smaller and you've made useful contact with the project.

### What to take away

- An issue is a **cheap way to save knowledge** without spending attention right now. It's a deferred-work queue, not a failure to act.
- Small, low-severity work **starves** in a strict priority queue. That's why good starter issues can stay open for years.
- `help wanted` + a detailed explanation = **an intentional on-ramp**. You taking it is exactly what the maintainer hoped for.
- The cost of software work is mostly **deciding, verifying, reviewing, and owning**, not typing. AI doesn't remove those costs.
- **Implication for item A:** the fact that the fix is already described isn't a reason to skip it. It's the reason it's a good first contribution. Your value is doing it correctly (right page, right property names, verified behavior) so the maintainer only has to review.

### Interview relevance

This question is really about **prioritization and the true cost of work**, which comes up in behavioral and design interviews ("How do you decide what to work on?", "How do you handle a backlog?"). Useful vocabulary:
- **Opportunity cost:** time spent on X isn't spent on something more important.
- **Context-switch cost:** the fixed overhead of starting any task, independent of its size.
- **Triage:** sorting incoming work by severity and impact.
- **Ownership:** a task with no clear owner tends not to get done.
- **Delegation / growing others:** leaving well-scoped work for less-experienced people is a senior-engineer behavior, not laziness. It's how teams scale.

---

## Q2. Where do the WebSockets docs actually live? (I found a WebSockets folder, but it's all C# code)

**Related:** [YARP #1764](https://github.com/dotnet/yarp/issues/1764), item A · **Asked:** 2026-09-26

### The question

Looking for the WebSockets documentation to fix for item A, I found `yarp/src/TelemetryConsumption/WebSockets/` in my local YARP clone. It only contains C# code, no documentation. Big projects seem to have several folders with the same component names, so I suspect I'm misunderstanding something. Where should I be looking, and what exactly should I do?

### The short answer

You're in the right *project* but the wrong *repository*. **YARP's documentation isn't in the YARP repo at all.** It lives in a separate repository, [`dotnet/AspNetCore.Docs`](https://github.com/dotnet/AspNetCore.Docs), at `aspnetcore/fundamentals/servers/yarp/websockets.md`, and it's published to [learn.microsoft.com](https://learn.microsoft.com/en-us/aspnet/core/fundamentals/servers/yarp/websockets). The folder you found is a **library for observing telemetry** about WebSocket connections. Interestingly, it contains code evidence of the exact behavior the doc should describe (see below).

And one new finding, from re-checking the docs while answering this: **most of what #1764 asks for has already been documented**, on the Timeouts page. That changes what item A should be (see "What to do now").

### What you were missing: one feature, many places

In a large project, one feature ("WebSockets") shows up in several places, each doing a different job. They share a name because they're about the same feature, not because they're the same kind of thing:

```
 Feature: "YARP proxies WebSockets"
 │
 ├── PRODUCT CODE         dotnet/yarp  → src/ReverseProxy/...            The proxy itself: forwards the
 │                                                                       HTTP/1.1 Upgrade or HTTP/2 CONNECT,
 │                                                                       then pumps bytes both ways
 │
 ├── TELEMETRY LIBRARY    dotnet/yarp  → src/TelemetryConsumption/       A separate NuGet package
 │                                       WebSockets/   ← you were here   (Yarp.Telemetry.Consumption) that
 │                                                                       lets an app OBSERVE what the proxy did
 │
 ├── TESTS                dotnet/yarp  → test/...                        Proves the behavior
 ├── SAMPLES              dotnet/yarp  → samples/...                     Example apps
 │
 └── DOCUMENTATION        dotnet/AspNetCore.Docs (a DIFFERENT repo)      What users read on learn.microsoft.com
                          → aspnetcore/fundamentals/servers/yarp/
                               websockets.md    ← the page item A was about
                               timeouts.md      ← where ActivityTimeout is documented
```

**The rule to remember:** when a project's docs are published on learn.microsoft.com, the source is usually in a separate `*Docs` repo owned partly by a docs team. YARP's docs used to live inside the YARP repo and were **migrated to AspNetCore.Docs** ([tracking issue #34650](https://github.com/dotnet/AspNetCore.Docs/issues/34650)), which is why older guides and blog posts may point elsewhere.

**The trick that always works:** open the published page on learn.microsoft.com and use its **edit (pencil) link**. It takes you straight to the exact source file on GitHub. That works for any Microsoft Learn page, so you never have to guess which repo or folder.

### The folder you found is still interesting

`src/TelemetryConsumption/WebSockets/` is the **Yarp.Telemetry.Consumption** library. YARP emits runtime telemetry events, and this library lets an application subscribe to them. In that folder is this enum:

```csharp
/// <summary>
/// The reason the WebSocket connection closed.
/// </summary>
public enum WebSocketCloseReason : int
{
    Unknown,
    ClientGracefulClose,
    ServerGracefulClose,
    ClientDisconnect,
    ServerDisconnect,
    ActivityTimeout,     // ← the proxy closed an idle WebSocket
}
```

`ActivityTimeout` is exactly the behavior issue #1764 is about: the proxy closing an idle WebSocket after 100 seconds. So the telemetry library lets an operator *see* when the problem happens. The code, the telemetry, and the docs are three views of one behavior. Connecting them like this is how you build a real map of a codebase. (Firmware analogy: the product code is the peripheral, the telemetry library is the status register that tells you why the link dropped, and the docs are the datasheet.)

### The finding: the Timeouts page already covers it

Here's what the current docs say (checked 2026-09-26):

| Page (in AspNetCore.Docs) | Last updated | What it says about WebSockets |
|---|---|---|
| `yarp/timeouts.md` ([published](https://learn.microsoft.com/en-us/aspnet/core/fundamentals/servers/yarp/timeouts)) | `ms.date: 11/01/2025` | Has a **WebSockets section**: request timeouts are disabled after the handshake, but "`ActivityTimeout` does apply to WebSocket requests. WebSocket keep-alives can be enabled by either the client or server talking to the proxy to keep the connection from becoming idle." Also notes that **WebSocket pings reset the timeout**, while TCP keep-alives and HTTP/2 pings don't. Documents the 100 s default and the per-cluster `HttpRequest.ActivityTimeout` setting. |
| `yarp/websockets.md` ([published](https://learn.microsoft.com/en-us/aspnet/core/fundamentals/servers/yarp/websockets)) | `ms.date: 2/6/2025` | Its "Timeout" section only says HTTP request timeouts are disabled after the handshake, then links to Timeouts. **It doesn't mention `ActivityTimeout` or keep-alives.** |

So the core knowledge from #1764 **is now documented**, just not on the page a WebSocket user would read first. Meanwhile the issue is still open, probably because nobody connected the new Timeouts content back to it. (That's Q1's point about ownership falling between two repos, happening in real life.)

**Lesson:** always re-read the *current* docs and code before starting, even on a well-described issue. The shortlist was written from the issue text, and the issue text was out of date.

### What to do now (the revised item A)

This is now a **triage + tiny docs PR**. Both are real contributions, and it's even lower risk than before.

**Step 1: read both pages yourself (10 min).** Open the two published pages above and confirm the table. Click each page's edit link to see the source Markdown on GitHub.

**Step 2: comment on YARP #1764.** Something like:

> Hi! I'd like to help close this out. It looks like the core of this is now documented in the [Timeouts page's WebSockets section](https://learn.microsoft.com/en-us/aspnet/core/fundamentals/servers/yarp/timeouts) (ActivityTimeout applies to WebSockets; keep-alives from client or server; WebSocket pings reset the timeout). However, the [WebSockets page's Timeout section](https://learn.microsoft.com/en-us/aspnet/core/fundamentals/servers/yarp/websockets) only mentions HTTP request timeouts. Would a short addition there (ActivityTimeout still applies after the handshake, default 100 s, enable keep-alives, link to Timeouts#websockets) resolve this? If so I'm happy to open that PR in dotnet/AspNetCore.Docs. Otherwise, perhaps this can be closed as covered.

**Step 3: if they say yes, make the PR without cloning anything.** AspNetCore.Docs is a very large repo, and your MacBook's disk is tight, so use GitHub's web editor:
1. Go to `aspnetcore/fundamentals/servers/yarp/websockets.md` in `dotnet/AspNetCore.Docs` on GitHub and click the pencil ("Edit this file"). GitHub creates a fork and branch for you automatically.
2. In the "Timeout" section, add a sentence or two along these lines (adjust wording to the page's style):

   > Request timeouts are disabled after a WebSocket handshake, but the cluster's `ActivityTimeout` (default 100 seconds) still applies. To keep idle WebSocket connections open, enable WebSocket keep-alives on the client or the destination server. For details, see [Timeouts](xref:fundamentals/servers/yarp/timeouts#websockets).

   *Check the `uid` in `timeouts.md`'s front matter to get the xref right, and look at how other links on the page are written. Match that style.*
3. Read the repo's contributor guidance for AspNetCore.Docs (linked from its README / the PR template). Among other things, it covers whether to update `ms.date`.
4. Open the PR with a description that says what and why, and links `dotnet/yarp#1764`.

**Step 4: if they say "already covered, closing,"** that's still a successful contribution: you triaged a stale issue and got it resolved.

**Optional hands-on (strengthens the comment or PR):** in your YARP clone, look in `samples/` for a WebSocket example (or write a minimal proxy plus an echo server), leave a socket idle for more than 100 seconds, and watch it close. Then enable `KeepAliveInterval` on the server and watch it survive. If you also wire up `Yarp.Telemetry.Consumption`, you can watch `WebSocketCloseReason.ActivityTimeout` get reported. That uses all three layers from the diagram.

### What to take away

- **One feature, many locations:** product code, telemetry, tests, samples, and docs are separate "characters" that share a feature name. Ask "which *job* am I looking for?" before searching by name.
- **Microsoft Learn docs usually live in a separate `*Docs` repo.** Use the page's edit link to find the source.
- **Verify the current state before you start.** Issues describe the world when they were written. This one had been partly overtaken by later docs changes.
- **Triage is a contribution.** Showing maintainers "this is already covered, here's the remaining gap" saves them time and often closes an issue.
- **Constrained machine?** The GitHub web editor is a legitimate way to make docs PRs.

### Interview relevance

"How do you get up to speed in an unfamiliar codebase?" This is a concrete answer: separate the product code from the telemetry, tests, and docs; find the published artifact and trace it back to its source; verify the current state before changing anything. The ActivityTimeout thread (docs ↔ telemetry enum ↔ proxy behavior) is also a nice example of connecting layers, the top-down thinking design interviews look for.

---
