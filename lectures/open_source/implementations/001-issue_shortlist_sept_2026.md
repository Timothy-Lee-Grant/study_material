# Implementation 001 — Issue Shortlist (September 2026)

> **Date researched:** 2026-09-26
> **Repos searched:** `dotnet/iot` (primary), `modelcontextprotocol/csharp-sdk` (backup), `dotnet/yarp` (satellite)
> **Purpose:** a concrete menu of open issues worth solving or studying, each with the problem, a fix approach, and a step-by-step plan.
>
> ⚠️ **Issue status changes fast.** Everything below was open and unclaimed on the date above unless noted otherwise. Before starting any item, open the link, read the latest comments, and confirm nobody has claimed it or opened a PR.

---

## 0. The shortlist at a glance

**Labels** (as of 2026-09-26). **State:** 🟢 open, available · 🟡 open, claimed by someone else · ⚫ closed. **Intent:** 🛠️ Contribute (worth developing a PR, reproduction, or comment) · 📖 Learn (study it; don't try to take it over).

| # | Issue | State · Intent | Repo | Type | Effort | Needs hardware? | Why it's on the list |
|---|---|---|---|---|---|---|---|
| **A** | [#1764 — Doc WebSocket keep-alive requirement](https://github.com/dotnet/yarp/issues/1764) | 🟢 · 🛠️ | YARP (docs live in AspNetCore.Docs) | Docs | ~2–4 h | No | `help wanted`; the maintainer already wrote the technical explanation. Ideal first PR. |
| **B** | [#2297 — Update Pi samples for the new `config.txt` location](https://github.com/dotnet/iot/issues/2297) | 🟢 · 🛠️ | dotnet/iot | Docs / triage | ~2–4 h | Optional | `up-for-grabs`; partly fixed already, so the job is an audit + cleanup. |
| **C** | [#2600 — LibGpiodV2: unchecked null from `gpiod_edge_event_buffer_get_event`](https://github.com/dotnet/iot/issues/2600) | 🟢 · 🛠️ | dotnet/iot | Bug (native interop) | ~6–12 h | Helpful (any Pi) | P/Invoke + native-crash bug with a clear defensive fix. Directly in your interop wheelhouse. |
| **D** | [#2602 — `GpiodException` escapes `GpioDriver.TryCreate`](https://github.com/dotnet/iot/issues/2602) | 🟢 · 🛠️ (ask first) | dotnet/iot | Bug (error handling / design) | ~6–10 h | Helpful | Small code change, but needs a design decision. Touches containers + Generic Host startup. |
| **E** | [#1806 — Flaky OAuth metadata fetch timeout on Windows](https://github.com/modelcontextprotocol/csharp-sdk/issues/1806) | 🟢 · 🛠️ | MCP C# SDK | Test fix | ~4–8 h | No | `help wanted` + `ready for work`; a proven fix pattern already exists (PR #1702). |
| **F** | [#2356 — MPU-6050: `CalibrateGyroscopeAccelerometer` throws on bandwidth readback](https://github.com/dotnet/iot/issues/2356) | 🟢 · 🛠️ | dotnet/iot | Bug (device binding) | ~8–15 h | **Yes** (MPU-6050, ~$5–10) | A register-level bug: datasheet reading is exactly your strength. Strong resume story. |
| **G** | [#2403 — `GpioPin` event handler passes the wrong `sender`](https://github.com/dotnet/iot/issues/2403) | 🟢 · 🛠️ | dotnet/iot | Bug (API behavior) | ~4–8 h | No | Small, testable, and a good lesson in .NET event conventions and compatibility. |
| **H** | [#1781 — Integration tests for Streamable HTTP MCP servers](https://github.com/modelcontextprotocol/csharp-sdk/issues/1781) | 🟢 · 🛠️ | MCP C# SDK | Docs / sample | ~8–12 h | No | `help wanted` + `ready for work`; overlaps with testing skills you want for LLM_Monitor. |
| **I** | [#2847 — LettuceEncrypt is archived](https://github.com/dotnet/yarp/issues/2847) | 🟢 · 🛠️ | YARP (docs) | Docs + research | ~4–8 h | No | `help wanted`; requires evaluating alternatives, which is real engineering judgment. |
| **J** | [#2352 — FT4232H I2C write-read without repeated start](https://github.com/dotnet/iot/issues/2352) | 🟢 · 🛠️ (ask first: assigned to maintainers but still `up-for-grabs`) | dotnet/iot | Bug / feature (protocol) | ~15–30 h | **Yes** (FTDI board + logic analyzer) | Stretch. An I2C repeated-start problem is pure home turf, but it needs specific hardware. |
| **K** | [#275 — Remove Autofac and Moq from tests](https://github.com/dotnet/yarp/issues/275) | 🟢 · 🛠️ | YARP | Test refactor | Incremental | No | `help wanted`; can be done a few files at a time. Good for learning YARP's test suite. |
| **L** | [#2667 — Use the request path for the trace name](https://github.com/dotnet/yarp/issues/2667) + [PR #3031](https://github.com/dotnet/yarp/pull/3031) | 🟡 · 📖 (open PR by another contributor) | YARP | Observability (study + review) | ~4–8 h | No | *You found this one.* An open community PR, and a real design tension with OpenTelemetry conventions. 🧭 Explorer. |
| **M** | [#3008 — Async watch in the Kubernetes controller](https://github.com/dotnet/yarp/issues/3008) + [PR #3024](https://github.com/dotnet/yarp/pull/3024) | ⚫ · 📖 → follow-up #3033 🟢 · 🛠️ | YARP | Async refactor (study) → follow-up [#3033](https://github.com/dotnet/yarp/issues/3033) | ~6–10 h | No | *You found this one.* A completed community PR with 12 review-driven commits: a model for async code and for how review works. 🧭 Explorer. |
| **N** | [OTel .NET #7449 — `Baggage.Current` leaks across async flows](https://github.com/open-telemetry/opentelemetry-dotnet/issues/7449) | 🟡 · 📖 (fix attempts reverted/abandoned; needs a major version) | OpenTelemetry .NET | Context propagation bug (study) | ~4–6 h | No | 📡 Telemetry track. How request context flows *inside* a process, and why getting it wrong is subtle. 🧭 Explorer. |
| **O** | [MCP C# SDK `Diagnostics.cs`](https://github.com/modelcontextprotocol/csharp-sdk/blob/main/src/ModelContextProtocol.Core/Diagnostics.cs) + [SEP-414](https://modelcontextprotocol.io/seps/414-request-meta) | ⚫ (SEP final; code shipped) · 📖 code tour + hands-on | MCP C# SDK | Distributed tracing across a process boundary | ~6–10 h | No | 📡 Telemetry track. One trace spanning an MCP client and server, which is directly relevant to your AI pillar. 🧭 Explorer. |
| **P** | [YARP #3016 — Improve logging and error output in the container image](https://github.com/dotnet/yarp/issues/3016) | 🟢 · 📖 now, 🛠️ only if invited | YARP | Operational logging design | ~3–5 h (study) | No | 📡 Telemetry track. What operators actually need from a proxy's logs, specified by an ASP.NET architect. 🧭 Explorer. |
| **Q** | [OTel .NET Contrib #4473 — InfluxDB exporter backpressure](https://github.com/open-telemetry/opentelemetry-dotnet-contrib/issues/4473) | 🟢 · 🛠️ stretch (`help wanted`; confirm unclaimed) | OpenTelemetry .NET Contrib | Feature: bounded queues / overload | ~15–30 h | No (Docker) | 📡 Telemetry track. Backpressure is a core distributed-systems concept, in a small, bounded component. 🧭 Explorer. |
| **R** | [OTel .NET Contrib #4516 — Expose GC mode/configuration as metrics](https://github.com/open-telemetry/opentelemetry-dotnet-contrib/issues/4516) | 🟢 · 🛠️ (comment first; direction unconfirmed) | OpenTelemetry .NET Contrib | Small metrics feature | ~6–10 h | No | 📡 Telemetry track. Your first *metric* instrument, plus a little runtime/GC knowledge. ⚓/🧭 mix. |

### Recommended order

```
 Week 1        A (or B)                     ← first PR: docs, low risk
 Weeks 2–4     C  (comment on D in parallel) ← first real code PR, in dotnet/iot
               └─ if dotnet/iot is quiet → E (MCP SDK)
 Month 2       F (order the sensor now) or G, then D if the maintainers pick a direction
 Month 3+      K / I in YARP · J if you've bought the FTDI board
```

**One active PR at a time** until two are merged. Comments to claim or ask design questions don't count against that limit, so it's fine to have a question open on D while you work on C.

### 📖 Learn-only picks (🟡 claimed by someone else)

These are worth *reading* because they're in the same code you'd touch, but someone is already working on them:

| Issue | Why study it | Status on 2026-09-26 |
|---|---|---|
| [dotnet/iot #2604](https://github.com/dotnet/iot/issues/2604) — LibGpiod V1 models `time_t` as a C `long` | A textbook P/Invoke struct-layout bug (32-bit platforms with 64-bit `time_t`): 24-byte native struct read into a 12-byte managed one, and rising/falling events swapped by a field-offset error | PR #2605 open by the reporter. **Read the PR and do a "predict the review."** |
| [dotnet/iot #2419](https://github.com/dotnet/iot/issues/2419) — `Thread.Sleep(1)` ×4 in nRF24L01 `Send()` | Timing requirements from a datasheet vs. what the code does | Assigned; PR #2553 open |
| [dotnet/iot #2428](https://github.com/dotnet/iot/issues/2428) — locks vs. `ConcurrentDictionary` in Tca955x | Concurrency design review in a real binding | Assigned; PR #2429 open |
| [MCP #1774](https://github.com/modelcontextprotocol/csharp-sdk/issues/1774) — `server/discover` advertises deprecated `logging` | Capability negotiation and protocol versioning | Assigned to a maintainer |

---

## 1. Before any issue: one-time setup

- [ ] **Employer check.** Items C, D, F, G, and J are GPIO/I2C/device code, close to your day-job domain. Send the short email asking about an open-source policy before you contribute there. Use your own hardware and time only.
- [ ] **dotnet/iot:** fork + clone on the Ubuntu desktop, run `./build.sh` once, confirm a clean build. Device bindings live in `src/devices/<Name>/`, each with its own solution, sample, and tests.
- [ ] **MCP C# SDK:** needs the .NET 10 SDK. `dotnet build` and `dotnet test` from the root. Some tests need Docker. Its CONTRIBUTING.md asks you to discuss your approach on the issue before significant changes and to include tests with bug fixes. Contributions are under Apache 2.0.
- [ ] **YARP docs:** YARP's documentation moved into the `dotnet/AspNetCore.Docs` repo (under `aspnetcore/fundamentals/servers/yarp/`). Docs fixes for YARP issues are PRs to *that* repo, linked back to the YARP issue.
- [ ] Read each repo's CONTRIBUTING.md for its AI-disclosure rule before your first PR there.

---

## 2. The issues in detail

Each entry: **Problem → Why it fits → How to fix it → Steps → Done when → Watch out for.**

---

### A. YARP #1764 — Document the WebSocket keep-alive requirement

> **🟢 Open, available · 🛠️ Contribute.**

> ⚠️ **Update (2026-09-26, see `concept_notes/001-questions_from_the_issue_shortlist.md` Q2):** the core of this is **already documented** on the YARP **Timeouts** page (its WebSockets section, `ms.date` 11/01/2025). The WebSockets page itself still doesn't mention `ActivityTimeout`. **Revised task:** comment on #1764 pointing this out, then either (a) add a short cross-reference sentence to `websockets.md` in `dotnet/AspNetCore.Docs` (the GitHub web editor is fine, no clone needed), or (b) let the maintainers close it as covered. Q2 has the exact steps and a draft comment.

**Link:** https://github.com/dotnet/yarp/issues/1764 · Labels: `Type: Documentation`, `help wanted` · Milestone: Backlog

**Problem.** YARP closes a proxied request that has been idle for **100 seconds** (the default activity timeout). That protects the proxy from leaking resources, but it means an idle WebSocket connection gets dropped. The fix for users is to send keep-alives from the **client or the destination server** (WebSocket-level pings or application-level heartbeats), not from the proxy. The maintainer explained this in the issue, but it never made it into the docs. As of 2026-09-26, the YARP WebSockets page on Microsoft Learn only says that HTTP request timeouts are disabled after the WebSocket handshake. It says nothing about the activity timeout or keep-alives.

**Why it fits.** Low risk and fast review, and it teaches you the docs pipeline. The subject (proxy timeouts, long-lived connections) also sits right inside your `lectures/yarp/` groundwork.

**How to fix it.** Add a short section to the YARP WebSockets doc (and, if appropriate, a cross-link from the Timeouts doc) explaining:
1. The activity timeout exists and defaults to 100 s.
2. Why (resource leaks from abandoned connections).
3. What to do: enable keep-alives on the client or server. In ASP.NET Core that's `WebSocketOptions.KeepAliveInterval` on the destination server. In browsers, application-level heartbeats are the usual approach.
4. Where the timeout is configured per route/cluster (`ActivityTimeout` on the cluster's `HttpRequest` config). **Confirm the exact property name and location against the current Timeouts doc before writing it.**

**Steps.**
- [ ] Re-read the issue thread; confirm it's still open and unclaimed.
- [ ] Read the current pages: [WebSockets](https://learn.microsoft.com/en-us/aspnet/core/fundamentals/servers/yarp/websockets) and the linked Timeouts page. Note exactly where the new text belongs.
- [ ] Comment on the YARP issue: *"I'd like to take this. YARP docs now live in AspNetCore.Docs, so I plan to add a 'Idle connections and keep-alives' section to `yarp/websockets.md` covering the 100 s activity timeout and client/server keep-alives. Does that location work?"*
- [ ] Optional but valuable: verify the behavior yourself. A tiny YARP app + an echo WebSocket server, leave the socket idle >100 s, observe the close, then set `KeepAliveInterval` and observe that it survives. A sentence like "verified on .NET 10 / YARP 2.x" in the PR description builds trust.
- [ ] Fork `dotnet/AspNetCore.Docs`, edit the Markdown, preview it, and open the PR referencing `dotnet/yarp#1764`.

**Done when:** PR merged in AspNetCore.Docs, and the YARP issue is closed (or you've commented with the link so a maintainer can close it).

**Watch out for:** AspNetCore.Docs has its own style rules and a PR template. Follow them exactly. Keep the change to one section.

---

### B. dotnet/iot #2297 — Update Raspberry Pi samples for the new `config.txt` location

> **🟢 Open, available · 🛠️ Contribute (audit may end in a close-it comment).**

**Link:** https://github.com/dotnet/iot/issues/2297 · Labels: `bug`, `Priority:2`, `up-for-grabs` · Opened March 2024 · No assignee

**Problem.** Raspberry Pi OS Bookworm moved the boot config from `/boot/config.txt` to `/boot/firmware/config.txt`. Sample READMEs still told users to edit the old path (the report named the nRF24L01 sample).

**Current state (checked).** The **nRF24L01 README on `main` is already fixed**. It now says `/boot/firmware/config.txt` and explains the pre-Bookworm location. So the issue is partly resolved, and nobody has confirmed whether other samples still use the old path.

**Why it fits.** A triage + docs contribution that closes a two-year-old `up-for-grabs` issue. It forces you to skim many bindings, which is a fast way to map the repo.

**How to fix it.** An audit: find every remaining reference, update the ones that are stale, and close the loop on the issue.

**Steps.**
- [ ] In your clone: `grep -rn "/boot/config.txt" --include=*.md .` and `grep -rn "dtparam=spi" --include=*.md .`
- [ ] For each hit, decide whether to change the path or add the same "before Bookworm / since Bookworm" note the nRF24L01 README now uses. Consistency with that existing wording is what reviewers will want.
- [ ] **If there are no hits:** comment on the issue with your audit results ("searched all READMEs; the nRF24L01 doc was fixed in <commit>; no other references remain; suggest closing"). That's a legitimate triage contribution and maintainers appreciate it.
- [ ] If there are hits: comment first with the list of files, then open one PR that fixes them all, with `Fixes #2297`.

**Done when:** issue closed, via your PR or your audit comment.

**Watch out for:** don't also rewrite unrelated parts of those READMEs. One concern per PR.

---

### C. dotnet/iot #2600 — LibGpiodV2: unchecked null pointer crashes the process ⭐

> **🟢 Open, available · 🛠️ Contribute.**

**Link:** https://github.com/dotnet/iot/issues/2600 · Labels: `untriaged` · Opened 2026-08-19 · No PR linked

**Problem.** In the libgpiod **v2** driver, the edge-event observer loop reads a batch of events and then fetches each one by index:

```csharp
// LibGpiodV2EventObserver.HandleEdgeEventsOfRequestInLoop (simplified)
int numberOfReadEvents = request.ReadEdgeEvents(edgeEventBuffer);
for (int i = 0; i < numberOfReadEvents; i++)
{
    EdgeEvent edgeEvent = edgeEventBuffer.GetEvent((ulong)i);
    HandleEdgeEvent(edgeEvent);
}

// EdgeEventBuffer.GetEvent
using EdgeEventNotFreeable edgeEventHandle = LibgpiodV2.gpiod_edge_event_buffer_get_event(Handle, index);
EdgeEventSafeHandle edgeEventCopyHandle = LibgpiodV2.gpiod_edge_event_copy(edgeEventHandle); // native assert on NULL
```

If `gpiod_edge_event_buffer_get_event` returns **NULL** (for example, when the count returned by the read is larger than what the buffer actually holds), that NULL goes straight into `gpiod_edge_event_copy`. That function **asserts** on its argument, and a native `assert` calls `abort()`. That kills the whole .NET process, and **no managed `try/catch` can stop it**. The reporter saw this on a Pi 2 running Debian trixie, libgpiod 2.2.1, and .NET 10, with no application-side workaround.

**Why it fits.** This is P/Invoke and native-resource-lifetime work, exactly what you did on the job (native callbacks, marshalling, handles). A firmware analogy: it's an unchecked return from a HAL call dereferenced in an ISR.

**How to fix it.** Two layers of defense, both small:
1. **In `EdgeEventBuffer.GetEvent`:** check the returned handle (`IsInvalid`, or compare the pointer to `IntPtr.Zero`, depending on how `EdgeEventNotFreeable` is defined) *before* calling `gpiod_edge_event_copy`, and throw a `GpiodException` instead. A managed exception is recoverable. `abort()` isn't.
2. **In the observer loop:** bound the loop by what the buffer actually contains: `Math.Min(numberOfReadEvents, edgeEventBuffer.GetNumEvents())`. `GetNumEvents()` already exists on `EdgeEventBuffer`.

**Steps.**
- [ ] Read the full issue and any maintainer replies. It's `untriaged`, so a maintainer may not have looked at it yet.
- [ ] Read three files end to end: `Interop/Unix/libgpiod/V2/Proxies/EdgeEventBuffer.cs`, `LibGpiodProxyBase.cs` (what does `CallLibgpiod` do with exceptions?), and `System/Device/Gpio/Drivers/LibGpiodV2EventObserver.cs`. Also read the libgpiod v2 docs for `gpiod_edge_event_buffer_get_event` and `gpiod_line_request_read_edge_events`, especially what each returns.
- [ ] Find how `EdgeEventNotFreeable` is declared (a `SafeHandle` subclass?) so you know the right "is this NULL?" check.
- [ ] Comment: *"I'd like to fix this. Plan: (1) null-check the handle in `EdgeEventBuffer.GetEvent` and throw `GpiodException` before `gpiod_edge_event_copy`; (2) bound the observer loop by `GetNumEvents()`. Would you also like a test? If so, is there an existing seam for faking the libgpiod v2 proxies?"*
- [ ] Implement both changes on a branch. Keep the diff small.
- [ ] Test: run the existing GPIO unit tests. If the maintainers point you to a seam, add a test for the NULL path. If you have a Pi with libgpiod v2 (Raspberry Pi OS trixie ships 2.x), run an edge-event sample for a while as a smoke test and mention it in the PR.
- [ ] Open the PR with `Fixes #2600`.

**Done when:** merged, or a maintainer chooses a different fix and you've adapted to it.

**Watch out for:** the loop's outer `catch` currently logs and **exits** the observer loop. Throwing from `GetEvent` means edge events stop for that request instead of crashing the process. That's better, but mention the trade-off in the PR and ask whether they'd rather skip the bad index and continue.

---

### D. dotnet/iot #2602 — `GpiodException` escapes `GpioDriver.TryCreate`

> **🟢 Open, available · 🛠️ Contribute, after a maintainer picks a direction.**

**Link:** https://github.com/dotnet/iot/issues/2602 · Labels: `untriaged` · Opened 2026-08-23

**Problem.** When `GpioController` picks a driver, it tries candidates through `TryCreate`, which is meant to swallow "this driver can't work here" failures so the next driver gets a chance:

```csharp
catch (Exception x) when (x is PlatformNotSupportedException || x is DllNotFoundException)
{
    driver = null;
    return false;
}
```

But `LibGpiodV2Driver` wraps its failures in `GpiodException` (an `IOException`). So two very normal situations crash startup instead of falling back to another driver:
1. **libgpiod isn't installed.** Common in slim or "chiseled" container images. The `DllNotFoundException` gets wrapped.
2. **`/dev/gpiochip0` isn't mapped into the container**, only `/dev/gpiomem`.

The reporter saw the crash surface from `IHost.StartAsync`.

**Why it fits.** A small change with real users behind it (containers on Pis), and it overlaps with what you know about Docker device mapping and Generic Host startup. It's also a good exercise in **exception design**: which exceptions mean "try another option," and which mean "something is really broken."

**How to fix it.** The reporter lists three options. Here are the trade-offs to raise with the maintainers:

| Option | Change | Pro | Con |
|---|---|---|---|
| 1 | Add `GpiodException` to `TryCreate`'s filter | One line | Also swallows *real* libgpiod errors on a machine where libgpiod is present but misbehaving, so problems get hidden by a silent fallback |
| 2 | Catch `GpiodException` specifically at the driver-selection call site | Scoped to selection | Same masking risk, just in a narrower place |
| 3 | Stop wrapping `DllNotFoundException` in `LibGpiodProxyBase.CallLibgpiod` | Fixes case 1 precisely, keeps real errors loud | Doesn't cover case 2 (missing device node) |

A reasonable proposal: **option 3 for the missing-library case**, plus throwing a more specific exception (or `PlatformNotSupportedException`) when the gpiochip device node doesn't exist, **but let the maintainers choose.** That's why this is a comment-first issue.

**Steps.**
- [ ] Read `GpioDriver.TryCreate`, the driver-selection logic in `GpioController` (and `RaspberryPiXXDriver` if involved), and `LibGpiodProxyBase.CallLibgpiod`.
- [ ] Reproduce case 1 without a Pi if possible: run on an x64 Linux container without libgpiod and see what `new GpioController()` does. Then reproduce case 2 on a Pi with Docker by mapping only `/dev/gpiomem`.
- [ ] Post a comment with your reproduction results and the table above, and ask which direction they prefer.
- [ ] Implement the chosen option, with a unit test that constructs the failing condition (e.g., a factory/driver that throws the wrapped exception) and asserts fallback behavior.

**Done when:** merged with the maintainer-approved approach.

**Watch out for:** don't start coding before a maintainer answers. This one is a design decision.

---

### E. MCP C# SDK #1806 — Flaky OAuth metadata timeout on Windows CI

> **🟢 Open, available · 🛠️ Contribute.**

**Link:** https://github.com/modelcontextprotocol/csharp-sdk/issues/1806 · Labels: `bug`, `area-tests`, `help wanted`, `P3`, `ready for work` · Unassigned · Opened 2026-08-09

**Problem.** Three tests fail intermittently on `windows-latest`: `OAuth.AuthTests.CannotAuthenticate_WithInvalidClientMetadataDocument`, `OAuth.DcrFailureTests.DcrRejection_PropagatesToConsumer_WithStatusBodyAndSentParameters`, and the `auth/offline-access-scope` conformance scenario. The OAuth metadata fetch runs over an **in-memory duplex pipe with a TLS handshake**. On a slow CI agent it hits a short production-default timeout, and the resulting `TaskCanceledException` shows up as a confusing assertion failure.

**Why it fits.** Maintainers explicitly want help, the fix pattern already exists, and it's a test-only change, so it carries no product-behavior risk. It also puts your name in a Microsoft-co-maintained AI repo.

**How to fix it.** Mirror [PR #1702](https://github.com/modelcontextprotocol/csharp-sdk/pull/1702). That PR fixed the same class of flake for the `server/discover` probe: in `tests/ModelContextProtocol.Tests/ClientServerTestBase.cs`, it set `DiscoverProbeTimeout = TestConstants.DefaultTimeout` (60 s) on the client options in the test harness, without touching production defaults. The job is to find the **OAuth metadata fetch's equivalent timeout setting** and raise it the same way in the OAuth test setup.

**Steps.**
- [ ] Read PR #1702's diff and discussion completely. It's your template.
- [ ] Find where the OAuth metadata/discovery request is made in `src/`, and what timeout it uses (search for `Timeout`, `CancelAfter`, and the metadata-fetch method names).
- [ ] Find the shared setup used by the three failing tests (OAuth test base class / conformance harness).
- [ ] Comment: *"I'd like to take this. Following #1702, I plan to set the OAuth metadata fetch timeout to `TestConstants.DefaultTimeout` in the OAuth test harness, leaving production defaults unchanged. Does that match what you had in mind?"*
- [ ] Implement it. Run the three tests in a loop locally (`dotnet test --filter` + a small shell loop, 20–50 runs) to show stability. Ideally also run under CPU stress to simulate a slow agent.
- [ ] If the timeout isn't configurable from tests, **stop and ask** before adding a new public option. That would be an API change.

**Done when:** merged, and the issue closed.

**Watch out for:** if you can only reproduce on Windows and you're on Linux/macOS, say so in the PR and rely on CI runs. That's normal for flaky-test fixes.

---

### F. dotnet/iot #2356 — MPU-6050 calibration throws a bandwidth readback error

> **🟢 Open, available · 🛠️ Contribute (needs the sensor).**

**Link:** https://github.com/dotnet/iot/issues/2356 · Labels: `bug`, `Priority:3` · Opened 2024-10-02 · No assignee, no PR

**Problem.** With an Adafruit MPU-6050 on a Pi (I2C bus 1, address `0x68`), the device initializes and reads valid accelerometer and gyro data. Then `CalibrateGyroscopeAccelerometer()` throws:

> `IOException: Can set GyroscopeBandwidth, desired value Bandwidth0184Hz, stored value Bandwidth0250Hz`

After that, readings return zeros. A Python script talks to the same sensor fine, so the hardware is good.

**Why it fits.** The binding writes a bandwidth setting to a register, reads it back, and the value doesn't match. That's a register-map bug, and datasheet-level debugging is your strongest skill. "Found and fixed a register-map mismatch in the .NET MPU-6050 binding, verified with a logic analyzer" is a strong resume line.

**A hypothesis to test (not a conclusion).** In dotnet/iot the MPU-6050 support is built on the MPU-6500/9250 code. The chips are similar but **not register-identical**:
- On the MPU-6500/9250, `GYRO_CONFIG` bits [1:0] are `FCHOICE_B`, which works together with `CONFIG.DLPF_CFG` to select the gyro bandwidth.
- On the MPU-6050, those `GYRO_CONFIG` bits are **reserved**, the DLPF bandwidth table is different (e.g., 260 Hz rather than 250 Hz at `DLPF_CFG = 0`), and the gyro filter is set only through `CONFIG.DLPF_CFG`.

If the setter writes 6500-style bits and the getter decodes them 6500-style, a 6050 may read back something that decodes as `Bandwidth0250Hz`. **Verify every register detail against both datasheets.** This is a starting point, not an answer.

**Steps.**
- [ ] Buy an MPU-6050 breakout (~$5–10). Use the logic analyzer you're already planning to get (`dotnet/004` §12).
- [ ] Find the binding in your clone (`grep -rn "Can set GyroscopeBandwidth" src/devices`) and read the bandwidth getter/setter and the calibration method.
- [ ] Get the **MPU-6050** register map and the **MPU-6500** register map. Build a side-by-side table for `CONFIG` (0x1A) and `GYRO_CONFIG` (0x1B).
- [ ] Reproduce on your Pi with the issue's code. Capture the I2C write and the readback on the logic analyzer, and decode the bytes by hand.
- [ ] Comment on the issue with the reproduction, the capture, the register table, and your proposed fix (e.g., a 6050-specific override of the bandwidth property, or not writing `FCHOICE_B` on the 6050). Ask how they'd like chip differences handled in this class hierarchy.
- [ ] Implement it, add a unit test using the repo's fake I2C device pattern (other bindings' tests show how), and include hardware verification notes in the PR.

**Done when:** merged. This one is also great material for a public write-up.

**Watch out for:** the fix may change which `Bandwidth` enum values are valid on the 6050. Discuss that with the maintainers, since it affects the public API.

---

### G. dotnet/iot #2403 — `GpioPin` event handlers receive the wrong `sender`

> **🟢 Open, available · 🛠️ Contribute.**

**Link:** https://github.com/dotnet/iot/issues/2403 · Labels: `bug`, `Priority:2` · Opened 2025-07-08 · No assignee, no PR

**Problem.** The .NET event convention is that `sender` is the object that raised the event. For `GpioPin.ValueChanged`, the handler is registered through the controller:

```csharp
public virtual event PinChangeEventHandler ValueChanged
{
    add    => _controller.RegisterCallbackForPinValueChangedEvent(_pinNumber, PinEventTypes.Falling | PinEventTypes.Rising, value);
    remove => _controller.UnregisterCallbackForPinValueChangedEvent(_pinNumber, value);
}
```

So when the event fires, the **driver** invokes the handler with *itself* as `sender`. Code that subscribes to `pin.ValueChanged` and casts `sender` to `GpioPin` gets the internal driver instead. This came from a refactoring (commit `dd8e964`) that moved pin ownership from the driver to the controller.

**Why it fits.** Small and self-contained, with an obvious test (subscribe, fire, assert `sender == pin`). It teaches event wrappers, delegate identity, and backward compatibility.

**How to fix it.** Wrap the user's handler so the pin passes itself as `sender`:

```csharp
// sketch
add
{
    PinChangeEventHandler wrapper = (_, args) => value(this, args);
    _wrappers[value] = wrapper;                 // must remember it...
    _controller.RegisterCallbackForPinValueChangedEvent(_pinNumber, PinEventTypes.Falling | PinEventTypes.Rising, wrapper);
}
remove
{
    if (_wrappers.Remove(value, out var wrapper)) // ...so remove can unregister the same delegate
        _controller.UnregisterCallbackForPinValueChangedEvent(_pinNumber, wrapper);
}
```

The subtle part: `remove` must unregister the **same delegate instance** that was registered, so you need a map from the user's handler to its wrapper. Also think about threading (events can be added from any thread), the same handler subscribed twice, and `VirtualGpioPin`, which overrides this event.

**Steps.**
- [ ] Write a failing unit test first, using the existing mock/virtual GPIO driver in the test project.
- [ ] Comment on the issue: confirm the expected `sender` is the `GpioPin`, and ask whether changing it counts as a breaking change for anyone relying on the current behavior. (It's a behavior change, even though it's a bug fix.)
- [ ] Implement the wrapper approach with a map and a lock (or a concurrent dictionary). Handle `VirtualGpioPin` consistently.
- [ ] PR with the test, `Fixes #2403`.

**Done when:** merged.

**Watch out for:** the double-subscription case. Decide (and test) what happens when the same handler is added twice, then removed once.

---

### H. MCP C# SDK #1781 — Show how to integration-test a Streamable HTTP MCP server

> **🟢 Open, available · 🛠️ Contribute.**

**Link:** https://github.com/modelcontextprotocol/csharp-sdk/issues/1781 · Labels: `documentation`, `help wanted`, `P3`, `ready for work` · Unassigned · Opened 2026-08-02

**Problem.** A user asked how to write end-to-end integration tests for an ASP.NET Core MCP server using the Streamable HTTP transport, the way you'd test an MVC app. There's no doc or sample for it.

**Why it fits.** Maintainers labeled it `ready for work`. Doing it well requires `WebApplicationFactory` / `TestServer`, which is exactly the integration-testing skill you want for LLM_Monitor. And a doc that other developers copy is a visible contribution.

**How to fix it.** A doc page (the SDK has a docs site served with `make serve-docs`), or a sample test project, showing:
1. Hosting the MCP server in-process with `WebApplicationFactory<Program>`.
2. Creating an MCP client whose HTTP transport uses the factory's `HttpClient`/handler (so there's no real network).
3. A test that calls `tools/list` and `tools/call` and asserts on the result.
4. Notes on stateful vs. stateless sessions in tests.

**Steps.**
- [ ] Look at how the SDK's own test project tests the ASP.NET Core transport. The pattern you document should match what the maintainers already do.
- [ ] Comment: propose the shape (doc page vs. sample project, and where it lives) and ask which they prefer.
- [ ] Build it as a working test first, then write the doc around the working code.
- [ ] PR with the doc/sample, linking the issue.

**Done when:** merged, and the issue author confirms it answers the question.

**Watch out for:** don't invent new helper APIs. Document the existing surface.

---

### I. YARP #2847 — LettuceEncrypt is archived

> **🟢 Open, available · 🛠️ Contribute (research first).**

**Link:** https://github.com/dotnet/yarp/issues/2847 · Labels: `Type: Documentation`, `help wanted` · Opened 2025-05-15 · No assignee

**Problem.** The YARP "Let's Encrypt" doc recommends `natemcmaster/LettuceEncrypt`, which was **archived on 2025-04-24**. The docs point users at an unmaintained dependency for TLS certificate automation.

**Why it fits.** Real engineering judgment: evaluate the alternatives (maintained forks such as `LettuceEncrypt-Archon` on NuGet, other ACME libraries, or terminating TLS in front of YARP) and recommend one. It also touches TLS, which is on your backend list.

**How to fix it.** Don't pick a replacement unilaterally. Research the options, summarize them for the maintainers, and let them decide what Microsoft docs should recommend. Then update `aspnetcore/fundamentals/servers/yarp/lets-encrypt.md` in AspNetCore.Docs.

**Steps.**
- [ ] Research 2–4 options: maintenance activity, license, .NET version support, and whether each works with YARP's Kestrel setup.
- [ ] Post a short comparison table on the issue and ask the maintainers which direction they want (recommend a fork, recommend a different approach, or just add an "archived" warning).
- [ ] Update the doc accordingly in AspNetCore.Docs.

**Done when:** merged doc change reflecting the maintainers' choice.

**Watch out for:** Microsoft docs are cautious about endorsing third-party packages. A neutral "archived; here are the options" note may be what they want.

---

### J. dotnet/iot #2352 — FT4232H: write-read without a repeated start (stretch)

> **🟢 Open (assigned to maintainers, still `up-for-grabs`) · 🛠️ Contribute, only after asking.**

**Link:** https://github.com/dotnet/iot/issues/2352 · Labels: `bug`, `Priority:2`, `up-for-grabs` · Opened 2024-09-20 · Assigned to two maintainers, but still `up-for-grabs` with no PR

**Problem.** Many I2C devices require a register read as **write (register address) → repeated START → read**, with no STOP in between. The FT4232H I2C implementation issues a **STOP** between the write and the read, so some target devices lose the register pointer or reject the transaction. Other adapters (the reporter mentions a TI USB-to-GPIO dongle) do it correctly.

**Why it fits.** Repeated start vs. stop-start is exactly the protocol detail you already know, and it relates to your I2C target work.

**How to fix it.** In the FTDI MPSSE command sequence for `WriteRead`, emit the write phase, then a repeated-START sequence instead of STOP + START, then the read phase, then STOP. Check whether the FT232H implementation shares this code (it may have the same problem or already do it right).

**Steps.**
- [ ] Comment on the issue first. It's assigned to two maintainers, so ask whether they'd welcome a PR and whether anyone is working on it.
- [ ] Read the FTDI I2C code in `src/devices/Ft4232H` (and `Ft232H`) and FTDI's MPSSE application notes for I2C.
- [ ] Get hardware: an FT4232H (or confirm with maintainers that FT232H shares the code path and use a cheaper FT232H board), an I2C target that needs repeated start, and the logic analyzer.
- [ ] Capture before/after traces. The logic-analyzer screenshot is the proof in the PR.

**Done when:** merged, with before/after captures in the PR.

**Watch out for:** hardware cost and time. Only take this once C or F is merged.

---

### K. YARP #275 — Remove Autofac and Moq from the tests

> **🟢 Open, available · 🛠️ Contribute (incrementally).**

**Link:** https://github.com/dotnet/yarp/issues/275 · Labels: `Type: Task`, `help wanted` · No assignee, no PR

**Problem.** YARP's tests use Autofac (a DI container) and Moq (a mocking library). The maintainers consider both unnecessary: the built-in DI container and hand-written fakes are just as short and require no extra knowledge.

**Why it fits.** A pure refactor that must keep every test passing, done **a few files per PR**. It's the best way to read YARP's test suite and learn its components, and it exercises DI and test-double design.

**How to fix it.** For each test file: replace Autofac with `ServiceCollection`/`ServiceProvider`, and replace `Mock<T>` with small hand-written fakes (or shared ones if the test project already has them).

**Steps.**
- [ ] Count remaining usages: `grep -rln "Autofac\|Moq" test/`.
- [ ] Comment on the issue: *"I'd like to chip away at this in small PRs, starting with <2–3 files>. Is incremental OK, and is there a preferred pattern for fakes?"*
- [ ] First PR: 2–3 files only, to learn the maintainers' preferences. Scale up once the pattern is agreed.

**Done when:** each small PR merges. The issue closes when the package references are removed.

**Watch out for:** don't change what a test *asserts*, only how its dependencies are built.

---

### L. YARP #2667 + PR #3031 — Name proxy traces by request path 🧭 Explorer

> **🟡 Open, claimed · 📖 Learn.** Another contributor's PR is open. Study it; don't open a competing PR. The optional 🛠️ part is a respectful comment, or a docs PR if maintainers choose that route.

**Links:** [issue #2667](https://github.com/dotnet/yarp/issues/2667) · [PR #3031](https://github.com/dotnet/yarp/pull/3031)
**Status on 2026-09-26:** issue **open** (`Type: Documentation`, `help wanted`, Backlog, opened 2024-11-28). PR **open**, opened 2026-05-22 by a community contributor. **No maintainer review visible yet.**

**Problem.** With YARP + OpenTelemetry + the Aspire dashboard, every proxied request shows up with the same span name (from the route/operation), so you can't tell requests apart without opening each trace. The reporter wants the **actual request path** as the name.

**What PR #3031 does.** A 5-line change in `src/ReverseProxy/Model/ProxyPipelineInitializerMiddleware.cs`, where YARP creates the `proxy.forwarder` activity:

```csharp
var activity = Observability.YarpActivitySource.CreateActivity("proxy.forwarder", ActivityKind.Server);

if (activity is not null && context.Request.Path.Value is { Length: > 0 } path)
{
    activity.DisplayName = path;          // what dashboards show
}                                         // OperationName stays "proxy.forwarder" (what filters match on)
```

It also adds a test (`Invoke_SetsActivityDisplayName_FromRequestPath`) that registers an `ActivityListener`, runs the middleware with path `/api/users/42`, and asserts the display name. The author notes that since the issue is labeled Documentation, a docs-only fix might be preferred.

**The design tension (this is the real lesson).** The [OpenTelemetry HTTP semantic conventions](https://opentelemetry.io/docs/specs/semconv/http/http-spans/) say HTTP span names **should be `{method} {target}`**, where `{target}` for server spans is the **route template** (`http.route`), and that instrumentation **"MUST NOT default to using URI path"** as the target. The reason is **cardinality**. `/api/users/42`, `/api/users/43`, … each become a distinct span name, which breaks aggregation in trace backends and can leak identifiers (user IDs, tokens in paths) into telemetry. So the PR is useful in a local Aspire dashboard, but it goes against the convention as a *default*. That's a likely reason the issue was labeled Documentation, and possibly why the PR hasn't been merged.

**Concepts you'll encounter:** `System.Diagnostics.Activity` / `ActivitySource`; `OperationName` vs. `DisplayName`; OpenTelemetry span naming and semantic conventions; telemetry cardinality and PII; the ASP.NET Core middleware pipeline; testing diagnostics with `ActivityListener`; the Aspire dashboard. (Exposure map: *Observability*, *Networking & proxies*, *Error handling & API compatibility*.)

**Steps.**
- [ ] Read the issue and the PR (description, diff, test). Then read `ProxyPipelineInitializerMiddleware.cs` in full to see where the activity starts and ends.
- [ ] Read the OpenTelemetry HTTP span-naming section linked above, and check what ASP.NET Core's own server activity uses for its name/tags (`http.route`).
- [ ] **Predict the review:** write down what you'd expect a maintainer to say (default-on vs. opt-in? path vs. route template? PII?). Save it in your study log and compare if a review appears.
- [ ] Try it: run a small YARP app with OpenTelemetry + the Aspire dashboard (or the console exporter) and look at the span names before and after applying the PR's change locally.
- [ ] Sketch the **docs-shaped alternative** the label suggests: showing users how to rename the span themselves, e.g., an OpenTelemetry `BaseProcessor<Activity>` that renames `proxy.forwarder` activities to `{method} {route}`, or a small middleware that sets `Activity.Current.DisplayName`. **Verify which approach actually works with YARP's activity before writing anything.**
- [ ] **Etiquette:** don't open a competing PR. If you have a well-researched point (e.g., the semantic-convention concern), a short, respectful comment on the PR or issue is a legitimate contribution. If the PR is later closed in favor of docs, the docs change goes to `dotnet/AspNetCore.Docs` (like item A).

**Done when:** your study-log entry is written. Optionally, a constructive comment posted, or a docs PR if the maintainers choose that route.

---

### M. YARP #3008 + PR #3024 — Async watch in the Kubernetes controller 🧭 Explorer

> **⚫ Closed · 📖 Learn** (the work is done; study it). **Follow-up #3033: 🟢 Open · 🛠️ Contribute** (a research comment).

**Links:** [issue #3008](https://github.com/dotnet/yarp/issues/3008) · [PR #3024](https://github.com/dotnet/yarp/pull/3024) · follow-up [issue #3033](https://github.com/dotnet/yarp/issues/3033)
**Status on 2026-09-26:** issue #3008 **closed via PR #3024** (the PR's commits run from 2026-04-24 to 2026-05-28, reviewed by maintainer MihaZupan). **Confirm the merge on the PR page.** The follow-up #3033 is **open** (`Type: Idea`, Backlog, no assignee).

**Problem.** YARP's Kubernetes ingress controller keeps an in-memory cache of Kubernetes resources (Ingresses, Services, Endpoints, Secrets) using the **list-then-watch ("informer") pattern**: list everything once, then watch for changes from that `resourceVersion`. `ResourceInformer.cs` used the Kubernetes client's **callback-based** watch methods, bridged back to `async` code with a `TaskCompletionSource` (`watcherCompletionSource`). The issue proposed switching to the client's `IAsyncEnumerable` watch methods and consuming them with `await foreach`.

**What PR #3024 did** (12 commits, most driven by review):

```csharp
private sealed class WatchState
{
    public long LastEventStopwatchTimestamp = Stopwatch.GetTimestamp();
}

// inside WatchAsync:
await foreach (var (watchEventType, item) in
    WatchResourceListAsync(_lastResourceVersion, _selector, OnError)
        .WithCancellation(linkedCancellationTokenSource.Token))
{
    Interlocked.Exchange(ref watchState.LastEventStopwatchTimestamp, Stopwatch.GetTimestamp());
    OnEvent(watchEventType, item);
}
```

- **Callbacks → `IAsyncEnumerable`:** the watch becomes a loop that reads like synchronous code, and cancellation flows through `WithCancellation`.
- **Stalled-watch detection:** a timer compares the last-event timestamp to a timeout (about 9.5 minutes) and cancels a watch that went quiet so it reconnects.
- **Review-driven changes worth studying:**
  - `DateTime` ticks → `Stopwatch.GetTimestamp()`/`GetElapsedTime()` (a monotonic clock is correct for measuring elapsed time; wall-clock time can jump).
  - A `CancellationRequested` guard was **removed** after the reviewer pointed out that calling `Cancel()` twice is harmless.
  - A missed parameter pass-through (`resourceVersion`, `fieldSelector`, `onError`) was fixed for the Ingress informer.
  - Smaller style fixes (`==` over `string.Equals(..., Ordinal)`, comment conventions).

**Follow-up you could engage with: #3033.** The same contributor proposes merging the separate list + watch calls into one, using Kubernetes' **streaming list** feature (which the issue describes as beta, introduced around Kubernetes v1.33). The open question is whether YARP should adopt it before it's generally available. A useful, low-risk contribution would be to **research the feature's current status** and summarize it on the issue: stability level, which Kubernetes versions support it, and whether the C# Kubernetes client exposes it.

**Concepts you'll encounter:** the Kubernetes API and the list/watch (informer) pattern; `resourceVersion` and reconnection; `IAsyncEnumerable` and `await foreach`; `WithCancellation` and linked `CancellationTokenSource`s; `TaskCompletionSource` (what it was replacing); `Interlocked`; monotonic vs. wall-clock time; closure-capture warnings; how a community PR evolves through review. (Exposure map: *Concurrency & event dispatch*, *Cloud & distributed systems*, *Containers & deployment*.) It also lines up directly with your *async/await internals* learning focus.

**Steps.**
- [ ] Read issue #3008, then PR #3024's description and **each commit in order** (the `.patch` view shows them). For each commit, write one line: what changed and why.
- [ ] Draw the before/after control flow of `WatchAsync`: callback + `TaskCompletionSource` versus `await foreach`.
- [ ] Do a **predict-the-review on commit 1 only**: write your own review before reading MihaZupan's comments, then compare.
- [ ] Learn the informer pattern at the Kubernetes level (list → watch from `resourceVersion` → handle expiry/relist). The Kubernetes "API concepts" doc covers efficient detection of changes.
- [ ] Optional hands-on: in a Codespace, create a local cluster with `kind` and run a 30-line C# console app that watches Pods with the Kubernetes client's async watch API, then kill and restart the API connection to see reconnection behavior.
- [ ] For #3033: research streaming lists' current status and post a short, sourced summary on the issue if nobody has already.

**Done when:** your study-log entry (with the commit-by-commit notes) is written. Stretch: a research comment on #3033.

---

## 2b. 📡 Telemetry & distributed-systems track (items N–R)

> **Added 2026-09-26** at your request: extra issues chosen to build telemetry and distributed-systems understanding. Together with **L** (trace naming and cardinality) and **P**, they cover the whole telemetry pipeline:

```
 ┌───────────────────────────── one request's journey ─────────────────────────────┐
 │                                                                                  │
 │  INSIDE A PROCESS            ACROSS PROCESSES              OUT TO A BACKEND      │
 │  context flows with async    context rides on the wire     data is exported      │
 │  code (Activity.Current,     (HTTP `traceparent` header,   (OTLP, Prometheus,    │
 │  Baggage.Current)            MCP `params._meta`)            InfluxDB…)           │
 │         N                            O                          Q                │
 │                                                                                  │
 │  WHAT YOU RECORD:  names & attributes (L: cardinality) · metrics (R) · logs (P)  │
 └──────────────────────────────────────────────────────────────────────────────────┘
```

**Suggested order:** O (build the mental model hands-on) → N (the subtle in-process part) → L (naming) → P (logs) → R (first small contribution) → Q (stretch).

**Environment note:** the OpenTelemetry .NET repos are moving to the .NET 11 SDK (an "[Infra] Support .NET 11" PR is in progress). Use **Codespaces** for building them, per the persona's compatibility matrix. Items N and O's experiments run fine on .NET 10 on any of your machines.

---

### N. OpenTelemetry .NET #7449 — `Baggage.Current` leaks across async flows 🧭 Explorer

> **🟡 Open, but effectively claimed/stalled · 📖 Learn.** Labeled `needs-majorversion-bump` (a correct fix changes behavior people may depend on). A proposed fix, [PR #7191](https://github.com/open-telemetry/opentelemetry-dotnet/pull/7191), "gained little traction" and was abandoned. An earlier fix (PR #5208, for [#3257](https://github.com/open-telemetry/opentelemetry-dotnet/issues/3257) from 2022) was **reverted** (PR #5227). Study it; don't try to fix it.

**What baggage is.** Trace context (`traceparent`) identifies *which trace* a request belongs to. **Baggage** carries small *key-value pairs* alongside it (e.g., `tenant=contoso`), so downstream services can read them. Inside a process, the current values live in "ambient" storage that should follow the async flow of each request.

**The bug.** In .NET, "follows the async flow" means `AsyncLocal<T>`: each async flow gets its own view, and a child flow's changes **don't flow back** to its parent. But OpenTelemetry doesn't store the `Baggage` value directly. It stores a **mutable holder object**:

```csharp
// src/OpenTelemetry.Api/Baggage.cs (simplified)
private sealed class BaggageHolder { public Baggage Baggage; }

private static readonly RuntimeContextSlot<BaggageHolder> RuntimeContextSlot =
    RuntimeContext.RegisterSlot<BaggageHolder>("otel.baggage");   // AsyncLocal-backed

public static Baggage Current
{
    get => RuntimeContextSlot.Get()?.Baggage ?? default;
    set => EnsureBaggageHolder().Baggage = value;   // mutates the SHARED holder
}
```

`AsyncLocal` copies the **reference** to the holder into child flows, not the holder itself. So once a holder exists, every parallel task that inherited it points at the **same object**, and setting `Baggage.Current` in one task changes what the parent and sibling tasks see. The 2022 report showed exactly this with `Parallel.ForEach`: messages processed in parallel overwrote each other's baggage.

**Firmware analogy:** each task gets its own copy of a *pointer*, but they all point to one shared global struct. Writes through any copy are visible to all. That's a shared-state bug hiding behind something that looks per-task.

**Why it's hard to fix:** making it truly per-flow changes observable behavior. Some existing code may *rely* on setting baggage in a child and reading it in the parent. That's why the issue needs a major version bump, and why two fix attempts didn't land.

**Concepts you'll encounter:** `AsyncLocal<T>` and `ExecutionContext` flow; reference vs. value semantics in ambient state; W3C Baggage vs. W3C Trace Context; why `Activity.Current` behaves differently; compatibility and semantic versioning as a design constraint. (Exposure map: *Concurrency & event dispatch*, *Observability*, *Error handling & API compatibility*. Also hits your *async/await internals* focus directly.)

**Steps.**
- [ ] Read #3257 (the 2022 report and its repro), then #7449, then skim PR #7191's description and tests.
- [ ] **Experiment (30 min, any machine, .NET 10):** a console app that (1) uses a plain `AsyncLocal<string>`, sets it in two parallel tasks, and shows each task sees its own value while the parent is unaffected; (2) does the same with `AsyncLocal<Holder>` where `Holder` is a class you mutate, and watch the leak appear; (3) repeats it with `Baggage.Current` from the `OpenTelemetry.Api` package.
- [ ] Write down, in your own words, why (2) leaks and (1) doesn't. That one paragraph is the lesson.
- [ ] Optional: read the reviewer comments on PR #7191 and on the reverted PR #5208 to see what reviewers worried about.

**Done when:** your experiment runs and your study-log entry explains the mechanism.

---

### O. MCP C# SDK: distributed tracing across a JSON-RPC boundary (code tour + hands-on) 🧭 Explorer

> **⚫ Done work (SEP-414 is Final; the C# SDK is cited as a reference implementation) · 📖 Learn.** Not an issue. It's a well-built piece of real code to study and run. Possible 🛠️ follow-up at the end.

**The problem it solves.** HTTP services propagate a trace across processes with the `traceparent` header. MCP messages are **JSON-RPC**, which can travel over stdio (no HTTP headers at all) or HTTP. So how does a trace started in an MCP **client** continue in the MCP **server**? The answer ([SEP-414](https://modelcontextprotocol.io/seps/414-request-meta)): put the W3C trace context inside the message itself, in `params._meta`:

```json
{
  "jsonrpc": "2.0", "id": 2, "method": "tools/call",
  "params": {
    "name": "get_weather",
    "arguments": { "location": "New York" },
    "_meta": { "traceparent": "00-0af7651916cd43dd8448eb211c80319c-00f067aa0ba902b7-01" }
  }
}
```

The `traceparent` value is `version-traceid-parentspanid-flags`. The 32-hex-digit **trace ID** is the same across every service in the request, and the **parent span ID** says which span in the caller made this call.

**Where it lives in the C# SDK:** `src/ModelContextProtocol.Core/Diagnostics.cs` defines:
- An `ActivitySource` and a `Meter` (both named `"Experimental.ModelContextProtocol"`): the sources of spans and metrics.
- A duration **histogram** in seconds with explicit bucket boundaries taken from the OpenTelemetry **MCP semantic conventions**.
- `InjectActivityContext(...)`: on the client, uses .NET's `DistributedContextPropagator` to write the current trace context into `params._meta`.
- `ExtractActivityContext(...)`: on the server, reads it back out so the server's span becomes a **child** of the client's span.

**Firmware analogy:** it's like embedding a sequence/correlation number in each frame's header, so a logic analyzer capture from both ends of a link can be lined up message by message.

**Concepts you'll encounter:** W3C Trace Context (`traceparent`/`tracestate`); inject/extract with a propagator; carriers (headers vs. message metadata); parent/child spans; `ActivitySource`/`Meter`; histogram bucket design; semantic conventions for a new protocol. (Exposure map: *Observability*, *Protocols & versioning*, *Cloud & distributed systems*.)

**Steps.**
- [ ] Read SEP-414 (short), then `Diagnostics.cs` top to bottom. Find where the client calls inject and where the server calls extract (search the repo for both method names).
- [ ] **Hands-on (the important part):** build a tiny MCP server and client in C# (stdio is fine), add OpenTelemetry with `AddSource("Experimental.ModelContextProtocol")` on both, and export to the console or the Aspire dashboard. Call one tool. Confirm that both processes' spans share **one trace ID**, and that the server span's parent is the client span.
- [ ] Break it on purpose: strip `_meta` from the message (or disable propagation) and watch the trace split into two unrelated traces. Seeing it break is what makes it stick.
- [ ] Connect it to LLM_Monitor: your planned C#→Python distributed traces work the same way (HTTP headers as the carrier).
- [ ] **🛠️ Possible follow-up:** if the SDK's docs don't show an end-to-end tracing setup, ask in the repo's Discussions whether a doc or sample would be welcome. It pairs naturally with item H.

**Done when:** you have a screenshot of one trace spanning two processes, and a study-log entry.

---

### P. YARP #3016 — Improve logging and error output in the YARP container image 🧭 Explorer

> **🟢 Open · 📖 Learn now, 🛠️ only if invited.** Filed on 2026-04-11 by David Fowler (an ASP.NET Core architect) with the `Container` label. It's a design spec from the core team, not a `help wanted` issue. Treat it as a study of *what good operational logging looks like*. If you want to help, ask whether any piece is open to contributors before writing code.

**The problem.** The YARP container image relies on raw ASP.NET Core framework logging. A failed proxy request produces about **20 lines of stack trace** without the facts an operator needs: which route, which destination, what status, how long it took.

**The proposal (from the issue):**
- A `Log.Level` setting with three modes: `default` (startup banner + warnings/errors), `requests` (one line per request: method, path, handler, status, duration), and `debug` (full framework logs + the resolved configuration dumped as JSON at startup).
- **Condensed errors:** one line with route name, destination address, request path, status code, and error summary, instead of a stack trace.
- Standard `Logging:LogLevel` configuration keeps working.
- It benchmarks the experience against **Caddy** (another reverse proxy), including Caddy's structured JSON error format.

**Why it's worth studying:** it's a senior engineer thinking about telemetry from the **operator's** point of view, which is a different question from "what can the code emit?" The fields chosen (route, destination, status, duration) are the proxy equivalent of the classic **RED metrics** (Rate, Errors, Duration) and the "golden signals." That's exactly the vocabulary distributed-systems interviews use.

**Concepts you'll encounter:** structured vs. unstructured logging; log levels as an operator interface; high-performance logging in .NET (`LoggerMessage` source generator); request-summary ("access log") middleware; configuration dumps for debuggability; comparing against a competitor's UX. (Exposure map: *Observability*, *Containers & deployment*.)

**Steps.**
- [ ] Read the issue in full, then look at how YARP's current container image is built (search the repo for the container project/Dockerfile).
- [ ] Run the YARP container image locally (or in Codespaces) with a misconfigured destination and look at the actual log output. That's the "before."
- [ ] Write your own one-line request log format and one-line error format. Compare them to the issue's proposal and to Caddy's docs.
- [ ] Watch for PRs linked to #3016 and do a predict-the-review when one appears.

**Done when:** study-log entry with your "before" output and your proposed formats.

---

### Q. OpenTelemetry .NET Contrib #4473 — InfluxDB exporter backpressure (stretch) 🧭 Explorer

> **🟢 Open · 🛠️ Contribute, stretch.** Labeled `help wanted` (`comp:exporter.influxdb`, opened 2026-06-08). **Confirm it's unclaimed and that the component owners agree with the design before starting.** Contrib components each have named owners.

**The problem.** When an app produces metrics faster than the InfluxDB exporter can write them, pending batches pile up in memory **without limit**, which can eventually crash or restart the process. The request is a **bounded queue** with a configurable overflow policy:
- **Block** until space frees up
- **Drop** the new batch
- **Evict the oldest** batch to make room

The default behavior must stay unchanged when the option isn't set.

**Why it fits:** backpressure is one of the most important distributed-systems concepts (what happens when a producer outpaces a consumer?), and you already know it from firmware as a **full ring buffer**: do you stall the producer, drop the incoming sample, or overwrite the oldest? The same three choices exist in `System.Threading.Channels` as `BoundedChannelFullMode.Wait`, `DropWrite`, and `DropOldest`, which could be a natural implementation tool here.

**Concepts you'll encounter:** bounded vs. unbounded queues; overload policies and their trade-offs (latency vs. data loss vs. memory); `System.Threading.Channels`; exporter lifecycle (flush/shutdown); testing under load; the OpenTelemetry exporter model. (Exposure map: *Cloud & distributed systems*, *Concurrency & event dispatch*, *Performance*.)

**Steps.**
- [ ] Read the issue, the InfluxDB exporter's source (`src/OpenTelemetry.Exporter.InfluxDB/`), and its component owners (listed in the contrib repo's metadata files).
- [ ] Reproduce the unbounded growth: InfluxDB in Docker (Codespaces), a test app emitting lots of metrics, and a throttled or stopped InfluxDB; watch memory climb.
- [ ] Comment with your reproduction and a design sketch (options API, default, where the bounded queue sits, metrics about dropped batches) and ask the owners to confirm.
- [ ] Implement with tests for each policy.

**Done when:** merged, or your design comment gets a clear decision. Either way, it's a strong learning item.

---

### R. OpenTelemetry .NET Contrib #4516 — Expose .NET GC mode/configuration as metrics ⚓/🧭

> **🟢 Open · 🛠️ Contribute, comment first.** (`comp:instrumentation.runtime`, Feature, opened 2026-06-16.) The maintainers' direction wasn't visible when checked. **Ask before building.**

**The problem.** The runtime instrumentation reports GC *behavior* (heap sizes, collection counts, pause durations) but not GC *configuration* (Workstation vs. Server GC, concurrent/background GC on or off). Without the configuration, the behavior metrics are hard to interpret. Server GC and Workstation GC produce very different heap and pause profiles. The request is a metric, constant for the process lifetime, describing the GC mode.

**Why it fits:** a small, bounded feature that teaches you how a **metric instrument** is defined, named, and tested, plus a bit of .NET runtime knowledge (GC modes) that's useful in performance interviews.

**Design questions to raise (good material for your comment):**
- A constant value as a metric: is it an observable gauge with value 1 and the mode as an attribute, or a resource attribute instead?
- Naming: does it fit the OpenTelemetry **semantic conventions** for .NET runtime metrics (and .NET's newer built-in `System.Runtime` metrics)? The runtime instrumentation may be steered toward those conventions, which could change the answer.
- Where the value comes from: `System.Runtime.GCSettings.IsServerGC` and `GCSettings.LatencyMode`.

**Concepts you'll encounter:** `Meter` and instrument types (counter, histogram, observable gauge); attributes and cardinality; semantic conventions for runtime metrics; .NET GC modes. (Exposure map: *Observability*, *Performance*.)

**Steps.**
- [ ] Read the runtime instrumentation's existing metrics code and its README list of metrics.
- [ ] Read the OpenTelemetry semantic conventions for .NET runtime metrics.
- [ ] Comment with the design questions above and a proposed metric name/shape. Wait for the owners.
- [ ] Implement with a test, following the existing instruments' patterns.

**Done when:** merged, or the owners explain a different direction (log that in your study log).

---

## 3. Progress tracker

Update this table as you go. It's the "status board" for the open_source home base.

| Item | Issue | Status | Comment posted | PR | Merged | Notes |
|---|---|---|---|---|---|---|
| A | yarp#1764 | 🔄 repro built (8 s runs captured) | | | | Next: 100 s runs with client keep-alive off (Q4), then post comment |
| B | iot#2297 | ☐ not started | | | | |
| C | iot#2600 | ☐ not started | | | | |
| D | iot#2602 | ☐ not started | | | | |
| E | mcp#1806 | ☐ not started | | | | |
| F | iot#2356 | ☐ not started | | | | Order MPU-6050 |
| G | iot#2403 | ☐ not started | | | | |
| H | mcp#1781 | ☐ not started | | | | |
| I | yarp#2847 | ☐ not started | | | | |
| J | iot#2352 | ☐ not started | | | | Hardware needed |
| K | yarp#275 | ☐ not started | | | | |
| L | yarp#2667 / PR #3031 | ☐ not started | | | | Study + predict-the-review; no competing PR |
| M | yarp#3008 / PR #3024 → #3033 | ☐ not started | | | | Study; research comment on #3033 |
| N | otel-dotnet#7449 | ☐ not started | | | | Study + AsyncLocal experiment |
| O | MCP `Diagnostics.cs` + SEP-414 | ☐ not started | | | | Hands-on: one trace across client + server |
| P | yarp#3016 | ☐ not started | | | | Study; ask before contributing |
| Q | otel-contrib#4473 | ☐ not started | | | | Stretch; confirm unclaimed |
| R | otel-contrib#4516 | ☐ not started | | | | Comment first |

**Re-run this search monthly** (next: late October 2026) and create `002-issue_shortlist_<month>.md` when the list goes stale. Newer issues labeled `up-for-grabs` (dotnet/iot), `help wanted` + `ready for work` (MCP SDK), and `help wanted` (YARP) are the ones to scan first.

---

## 4. Sources (checked 2026-09-26)

- dotnet/iot issues: [#2297](https://github.com/dotnet/iot/issues/2297) · [#2352](https://github.com/dotnet/iot/issues/2352) · [#2356](https://github.com/dotnet/iot/issues/2356) · [#2403](https://github.com/dotnet/iot/issues/2403) · [#2419](https://github.com/dotnet/iot/issues/2419) · [#2428](https://github.com/dotnet/iot/issues/2428) · [#2600](https://github.com/dotnet/iot/issues/2600) · [#2602](https://github.com/dotnet/iot/issues/2602) · [#2604](https://github.com/dotnet/iot/issues/2604) · [open issues list](https://github.com/dotnet/iot/issues)
- dotnet/iot source on `main`: [`EdgeEventBuffer.cs`](https://github.com/dotnet/iot/blob/main/src/System.Device.Gpio/Interop/Unix/libgpiod/V2/Proxies/EdgeEventBuffer.cs) · [`LibGpiodV2EventObserver.cs`](https://github.com/dotnet/iot/blob/main/src/System.Device.Gpio/System/Device/Gpio/Drivers/LibGpiodV2EventObserver.cs) · [`GpioDriver.cs`](https://github.com/dotnet/iot/blob/main/src/System.Device.Gpio/System/Device/Gpio/GpioDriver.cs) · [`GpioPin.cs`](https://github.com/dotnet/iot/blob/main/src/System.Device.Gpio/System/Device/Gpio/GpioPin.cs) · [nRF24L01 README](https://github.com/dotnet/iot/blob/main/src/devices/Nrf24l01/README.md) · [commit dd8e964](https://github.com/dotnet/iot/commit/dd8e964) · [CONTRIBUTING](https://github.com/dotnet/iot/blob/main/Documentation/CONTRIBUTING.md)
- MCP C# SDK: [open issues](https://github.com/modelcontextprotocol/csharp-sdk/issues) · [#1774](https://github.com/modelcontextprotocol/csharp-sdk/issues/1774) · [#1781](https://github.com/modelcontextprotocol/csharp-sdk/issues/1781) · [#1806](https://github.com/modelcontextprotocol/csharp-sdk/issues/1806) · [PR #1702](https://github.com/modelcontextprotocol/csharp-sdk/pull/1702) · [CONTRIBUTING](https://github.com/modelcontextprotocol/csharp-sdk/blob/main/CONTRIBUTING.md)
- Telemetry track (items N–R): [otel-dotnet #7449](https://github.com/open-telemetry/opentelemetry-dotnet/issues/7449) · [#3257](https://github.com/open-telemetry/opentelemetry-dotnet/issues/3257) · [PR #7191](https://github.com/open-telemetry/opentelemetry-dotnet/pull/7191) · [`Baggage.cs`](https://github.com/open-telemetry/opentelemetry-dotnet/blob/main/src/OpenTelemetry.Api/Baggage.cs) · [SEP-414](https://modelcontextprotocol.io/seps/414-request-meta) · [MCP C# SDK `Diagnostics.cs`](https://github.com/modelcontextprotocol/csharp-sdk/blob/main/src/ModelContextProtocol.Core/Diagnostics.cs) · [SEP-2028 draft (forwarding `_meta` to HTTP headers)](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2028) · [YARP #3016](https://github.com/dotnet/yarp/issues/3016) · [otel-contrib #4473](https://github.com/open-telemetry/opentelemetry-dotnet-contrib/issues/4473) · [otel-contrib #4516](https://github.com/open-telemetry/opentelemetry-dotnet-contrib/issues/4516) · [otel-dotnet PR #6899 (.NET 11 support)](https://github.com/open-telemetry/opentelemetry-dotnet/pull/6899)
- YARP (added items L–M): [#2667](https://github.com/dotnet/yarp/issues/2667) · [PR #3031](https://github.com/dotnet/yarp/pull/3031) · [#3008](https://github.com/dotnet/yarp/issues/3008) · [PR #3024](https://github.com/dotnet/yarp/pull/3024) · [#3033](https://github.com/dotnet/yarp/issues/3033) · [OpenTelemetry HTTP span semantic conventions](https://opentelemetry.io/docs/specs/semconv/http/http-spans/)
- YARP: [#275](https://github.com/dotnet/yarp/issues/275) · [#1764](https://github.com/dotnet/yarp/issues/1764) · [#2847](https://github.com/dotnet/yarp/issues/2847) · [Migrate YARP docs to AspNetCore.Docs (#34650)](https://github.com/dotnet/AspNetCore.Docs/issues/34650) · [YARP WebSockets doc](https://learn.microsoft.com/en-us/aspnet/core/fundamentals/servers/yarp/websockets?view=aspnetcore-10.0) · [lets-encrypt.md in AspNetCore.Docs](https://github.com/dotnet/AspNetCore.Docs/blob/main/aspnetcore/fundamentals/servers/yarp/lets-encrypt.md) · [LettuceEncrypt-Archon on NuGet](https://www.nuget.org/packages/LettuceEncrypt-Archon/)

The MPU-6050 register-level hypothesis in item F comes from general knowledge of the InvenSense datasheets. It hasn't been verified against the dotnet/iot source yet, so confirm it before relying on it.
