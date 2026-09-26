# Concept Notes 001 — Questions From the Issue Shortlist

> **What this is:** a running Q&A log of *concept notes*. As I read `implementations/001-issue_shortlist_sept_2026.md`, I ask about things I don't understand, and each answer is **appended** here, newest at the bottom.
> **Style:** short and issue-focused. Just enough concept to unblock the next step, then concrete next steps. Not a full lecture; deep dives belong in the repo's top-level `lectures/` domains.
> **Started:** 2026-09-26
>
> **Format for each entry:** the question (in my words) → the short answer → the explanation → what to take away / next steps.

---

## Index

| # | Question | Related issue | Topic |
|---|---|---|---|
| Q1 | Why do maintainers open an issue for a simple docs fix instead of just doing it? | YARP #1764 (item A) | How open-source projects actually run |
| Q2 | I found `src/TelemetryConsumption/WebSockets/` in YARP, but it's all C#. Where are the docs, and what am I misunderstanding? | YARP #1764 (item A) | Code vs. docs repos; finding a doc's source; verifying before contributing |
| Q3 | What are sockets and WebSockets, what does YARP do with them, what is the proxy timeout, and how do keep-alives and browser heartbeats fix it? | YARP #1764 (item A) | Sockets, WebSocket handshake, proxy byte-pumping, idle timeouts, keep-alives |

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

## Q3. Sockets, WebSockets, YARP's role, the idle timeout, and keep-alives

**Related:** [YARP #1764](https://github.com/dotnet/yarp/issues/1764), item A · **Asked:** 2026-09-26

### The question

I'm weak on sockets and WebSockets: what they are, how the connection is established (the handshake), and why they work the way they do. Where does YARP fit in, and what exactly is a "proxy timeout"? My reading of the fix: the **destination server** is the ASP.NET Core app YARP routes to, and it has a `KeepAliveInterval` setting in `WebSocketOptions` that prevents the timeout. And what are "application-level heartbeats" in browsers? How do they work, why are they the usual approach, and what do they cost?

### The short answer

- A **socket** is the OS's handle to one end of a network connection (think: a file descriptor you can read and write bytes on). A **TCP connection** is a reliable two-way byte pipe between two sockets.
- Plain **HTTP** uses that pipe for **request → response**, and the server can't speak unless asked. A **WebSocket** starts as an HTTP request that asks to **"upgrade"**. After the server agrees, the same TCP connection becomes a **full-duplex message channel** where either side can send at any time. That's what chat, live dashboards, and notifications need.
- **YARP** is a **reverse proxy**: clients connect to YARP, and YARP opens its own connection to a **destination** (backend) server. For a WebSocket, YARP forwards the upgrade handshake, then just **pumps bytes in both directions** between the two connections.
- The **activity timeout** (default **100 s**) is YARP's rule: "if no bytes move in either direction for 100 s, close both connections." It protects the proxy from holding dead connections forever.
- **Your understanding of the fix is correct**: the destination server is the ASP.NET Core app behind YARP, and `WebSocketOptions.KeepAliveInterval` makes it send small control frames periodically, so the connection is never idle for 100 s. **One gotcha:** the default `KeepAliveInterval` is **2 minutes**, which is *longer* than YARP's 100 s, so with defaults the proxy still cuts idle sockets. You have to set it below 100 s.
- **Browser JavaScript can't send WebSocket ping frames** (the browser API doesn't expose them), so browser apps send their own tiny "heartbeat" messages on a timer. Libraries like SignalR do this for you.

### The explanation

#### 1. The cast of characters

```
  Browser / client app            YARP (reverse proxy)                Destination server
  ────────────────────            ────────────────────                ──────────────────
  socket A ══ TCP conn #1 ══► socket B      socket C ══ TCP conn #2 ══► socket D
                               (YARP accepts)  (YARP connects)        (your ASP.NET Core app)

  Two separate TCP connections. YARP sits in the middle and relays.
```

| Character | Job |
|---|---|
| **Socket** | The OS's endpoint object for one side of a connection. Your code reads/writes bytes on it; the kernel handles TCP. |
| **TCP connection** | Reliable, ordered byte stream between two sockets. Opened with a handshake (SYN, SYN-ACK, ACK) and stays open until one side closes it. |
| **HTTP** | A conversation *protocol on top of* TCP: the client sends a request, the server sends a response. The server never speaks first. |
| **WebSocket** | A different protocol on top of TCP, entered **via** an HTTP request. Once established, it's message frames both ways, anytime. |
| **YARP** | A reverse proxy: accepts client connections, picks a destination per its routes/clusters, and forwards traffic. |
| **Destination server** | The backend app YARP forwards to. In #1764's scenario, an ASP.NET Core app using WebSockets. |

**Firmware analogy:** a TCP connection is like a UART link that's been set up and stays up. HTTP is a strict **master–slave** protocol on that link (like I2C: the controller always initiates). A WebSocket switches the link to **full-duplex messaging**, where either side can transmit whenever it wants. YARP is a **bridge/repeater** between two links.

#### 2. How a WebSocket is established (the handshake)

It begins as an ordinary HTTP/1.1 request with special headers:

```
Client → Server:
  GET /chat HTTP/1.1
  Host: example.com
  Upgrade: websocket                 ← "I want to switch protocols"
  Connection: Upgrade
  Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==     ← random nonce
  Sec-WebSocket-Version: 13

Server → Client:
  HTTP/1.1 101 Switching Protocols   ← "agreed"
  Upgrade: websocket
  Connection: Upgrade
  Sec-WebSocket-Accept: s3pPLMBiTxaQ9kYGzzhZRbK+xOo=   ← proves the server understood the request
```

After `101`, **HTTP is over on that connection.** The same TCP connection now carries WebSocket **frames**: text/binary data frames, plus **control frames**: `Ping`, `Pong`, and `Close`. (Over HTTP/2 the start is slightly different, an extended `CONNECT`, but the idea is the same. YARP's WebSockets doc covers both.)

**Why start with HTTP?** So WebSockets work through the same ports (80/443), firewalls, TLS, and proxies as normal web traffic. It's a way into full-duplex communication without needing new infrastructure.

#### 3. What YARP does with a WebSocket

1. The client's upgrade request arrives at YARP like any HTTP request, and YARP's routing picks a destination.
2. YARP forwards the upgrade request to the destination.
3. The destination answers `101`, and YARP passes it back to the client.
4. From then on, YARP **doesn't interpret the traffic.** It copies bytes from client→destination and destination→client until one side closes.

So for the life of a WebSocket, YARP is holding **two TCP connections, buffers, and a running copy task**. That's cheap for one socket, but real for 100,000.

#### 4. The activity timeout: why it exists

A connection can die **silently**: a laptop lid closes, Wi-Fi drops, a phone switches networks. No `Close` frame is sent, and TCP won't notice on its own for a very long time. From YARP's side, a dead connection and a quiet-but-alive one look identical: no bytes moving.

YARP's answer is a **watchdog**: `ActivityTimeout` (default **100 seconds**, configured per cluster under `HttpRequest.ActivityTimeout`). Any successful read/write (including WebSocket ping/pong frames) **resets** the timer. If it expires, YARP closes both connections and frees the resources. (Plain TCP keep-alives don't reset it, because they never reach YARP's code.)

**Firmware analogy:** exactly a watchdog timer. The healthy system must "kick" it periodically, and silence is treated as failure. The keep-alive frame is the kick.

The side effect is the problem in #1764: a **legitimately idle** WebSocket (e.g., a chat app where nobody types for two minutes) gets killed too. The fix is to make sure *something* kicks the watchdog.

#### 5. Fix 1: server-side keep-alives (your reading, confirmed)

In the destination server (ASP.NET Core):

```csharp
app.UseWebSockets(new WebSocketOptions
{
    KeepAliveInterval = TimeSpan.FromSeconds(30)   // default is 2 minutes, which is LONGER than YARP's 100 s!
});
```

The server now sends a small control frame every 30 s. It passes through YARP, which counts it as activity, so the watchdog never fires. Browsers answer server `Ping` frames automatically at the protocol level, and no JavaScript is involved. Newer ASP.NET Core versions also have `KeepAliveTimeout`: after sending a ping, if no pong comes back in time, the *server* aborts the connection. That gives the server its own dead-peer detection.

Alternatively, raise YARP's `ActivityTimeout` for that route's cluster (e.g., 10 minutes). That's simpler, but it also lets dead connections linger longer. It's a trade-off between resource cleanup and tolerance for idle connections.

#### 6. Fix 2: application-level heartbeats (the browser side)

The browser's JavaScript `WebSocket` API can `send()` data messages and `close()`, but it **can't send `Ping` frames**. So when the *client* needs to keep the connection alive or detect that the server vanished, the application does it itself:

```js
// Browser: send a tiny app-defined message every 30 s
const ws = new WebSocket("wss://example.com/chat");
setInterval(() => ws.send(JSON.stringify({ type: "ping" })), 30_000);
// Server code recognizes {type:"ping"} and may reply {type:"pong"}.
// If no pong arrives within N seconds, the client closes and reconnects.
```

It's "application-level" because it's an ordinary data message whose meaning the *app* defines, not a protocol control frame.

**Why it's the usual approach:** it works regardless of what's in between (YARP, load balancers, corporate proxies, NAT routers with their own idle timers), and it gives the **client** its own liveness check and reconnect logic. That's why real-time libraries build it in. **SignalR** (ASP.NET Core's real-time library) sends keep-alive messages automatically, and its client treats the server as gone if it hears nothing within a timeout.

**The cost:**
- **Per connection:** a few bytes every N seconds. Negligible.
- **At scale:** 1,000,000 connections × one message per 30 s ≈ **33,000 messages per second** for the server to handle, just for heartbeats. The interval is a tuning knob between responsiveness and load.
- **Mobile:** each heartbeat can wake the radio, which costs battery. This is why mobile apps often use longer intervals or push notifications instead.
- **Rule of thumb:** the heartbeat interval must be **shorter than the smallest idle timeout anywhere on the path** (YARP's 100 s, a cloud load balancer's idle timeout, a NAT's timer).

### What to take away

- Socket = OS endpoint; TCP = reliable byte pipe; HTTP = request/response on the pipe; WebSocket = HTTP that **upgrades** into two-way messaging.
- YARP forwards the upgrade, then **relays bytes** and holds two connections per WebSocket.
- `ActivityTimeout` is a **watchdog** against silently dead connections. Idle-but-alive sockets need something to kick it.
- Keep-alives: server `KeepAliveInterval` (**set it below 100 s**; the default 2 min isn't enough), app-level heartbeats from the client, or a longer `ActivityTimeout`.

### Next steps (for item A)

- [ ] **See it happen (~1 h, .NET 10 on any machine):** create (1) a minimal ASP.NET Core **echo WebSocket server**, (2) a minimal YARP app routing `/ws` to it, and (3) a small console client using `ClientWebSocket` that connects through YARP and then sits idle. Watch the connection drop at about 100 s.
- [ ] Set `KeepAliveInterval = TimeSpan.FromSeconds(30)` on the echo server and confirm the connection now survives. Then try the default (2 min) and confirm it still drops. **That gotcha is worth mentioning in your #1764 comment and in the docs sentence.**
- [ ] Optional: open the connection from a browser (the dev tools console is enough), add a `setInterval` heartbeat, and watch the frames in the browser's Network tab (the WS "Messages" view).
- [ ] Update your draft comment on #1764 (from Q2) with what you observed. A comment with a verified repro is much stronger than one that only cites the docs.

---
