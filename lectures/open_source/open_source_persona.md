# Open Source Contributor Profile — Timothy Grant

> **What this is:** the living reference for my open-source work. It covers why I contribute, what I bring, how issues are chosen, how I work, and the development environment I work in. It's the first thing to read (for me, or for an AI session helping me) before choosing an issue or planning a contribution.
>
> **Last updated:** 2026-09-26 · **Update it:** after studying an issue, after every merged PR, after every hardware change, and at each monthly issue-shortlist refresh.
>
> **Related:** `implementations/` (actionable plans and issue shortlists) · `concept_notes/` (short, issue-focused concept explanations that unblock the next step) · `private/` (git-ignored candid notes) · the repo-root `persona.md` (broader learning profile)

---

## 1. Summary

Firmware engineer turned .NET engineer, working across the hardware/software boundary. My background is embedded C on bare-metal microcontrollers (I2C, SPI, register-level drivers). More recently I've been on a production .NET team, where I built a Linux background service that ingests hardware telemetry through native interop (P/Invoke, struct marshalling, native callbacks) and feeds a rules engine that drives automated decisions. That work shipped through code review and CI/CD.

In open source, I focus on **.NET libraries where systems knowledge matters**: device and GPIO libraries, native interop, and developer tooling for AI systems (MCP). My goals are sustained, high-quality contributions to Microsoft-maintained .NET repositories, and **steady exposure to technologies and engineering concepts I haven't worked with yet.**

---

## 2. Why open source

| Motivation | What it means in practice |
|---|---|
| 🔭 **Exposure to new technologies and concepts** | The biggest lesson from my time on a production .NET team: much of my growth came from *encountering* things I'd never have met on my own (a new protocol, a hosting model, a build pipeline, an interop pattern) and having a real reason to understand them. Open-source codebases offer that same exposure on demand, across far more technologies than any single job. **This is a primary goal, not a side effect.** |
| 🧠 **Expert code review** | Maintainer review is the best feedback available outside a team: specific, public, and from people who designed the code. |
| 📜 **Public, verifiable work** | Merged contributions in respected repositories are evidence anyone can inspect. |
| 🤝 **Working with strong engineers** | Collaborating with maintainers, many of them at Microsoft, on real problems. |

Because exposure is a primary goal, **studying an issue deeply counts as progress even when I don't end up submitting a PR for it.** Each issue I study should leave behind at least one new concept I can explain (tracked in §7.2).

---

## 3. What I bring

These are the strengths to lead with when choosing issues. An issue that uses two or more of them is a strong fit.

| Strength | What it looks like in practice | Where it applies in open source |
|---|---|---|
| **Register-level hardware debugging** | Reading datasheets, building register maps, checking bus traffic on a logic analyzer, comparing chip variants | Device-binding bugs in dotnet/iot (e.g., a sensor whose readback doesn't match what was written) |
| **Native interop** | P/Invoke, `StructLayout`, marshalling C structs, managed callbacks invoked from native code, handle lifetimes | Interop bugs in `System.Device.Gpio` (libgpiod v1/v2 proxies, native crash paths) |
| **Bus protocols** | I2C and SPI from both sides of the bus: repeated start, clock stretching, framing | Protocol bugs in I2C/SPI adapters and bindings |
| **Embedded Linux** | .NET services on Raspberry Pi, systemd units, device nodes, containers with device mapping | GPIO-in-containers issues, driver selection, permission and device-node problems |
| **Hardware reproductions** | Building a bench setup that reproduces a reported bug on real hardware | The most under-supplied contribution in device repos. Maintainers often can't reproduce hardware reports themselves. |
| **.NET service design** | Generic Host, `BackgroundService`, dependency injection, PowerShell cmdlets | Hosting/startup behavior, samples, docs |
| **AI tooling** | Built an MCP server and an LLM orchestration platform (C# gateway + Python services, RAG, observability) | MCP C# SDK: docs, samples, tests, bug reproductions |
| **Technical writing** | A public repo of long-form technical notes on .NET, networking, concurrency, and systems | Docs PRs, well-structured issue reports, design discussions |

---

## 4. Focus and venues

| Role | Repository | Why |
|---|---|---|
| **Primary** | [`dotnet/iot`](https://github.com/dotnet/iot) | Where my hardware and interop background adds the most value |
| **Secondary** | [`modelcontextprotocol/csharp-sdk`](https://github.com/modelcontextprotocol/csharp-sdk) | AI tooling in .NET; maintained in collaboration with Microsoft |
| **Backend satellite** | [`dotnet/yarp`](https://github.com/dotnet/yarp) (+ its docs in `dotnet/AspNetCore.Docs`) | Reverse proxy / networking. Builds the backend side of my profile. |
| **Telemetry track** | [`open-telemetry/opentelemetry-dotnet`](https://github.com/open-telemetry/opentelemetry-dotnet) and [`-contrib`](https://github.com/open-telemetry/opentelemetry-dotnet-contrib) | Building depth in telemetry and distributed systems. Contrib is organized by component with named owners. |
| **Reading, not contributing yet** | `Microsoft.Extensions.*` in `dotnet/runtime` | Studying DI, Hosting, and Options design in depth |

The current issue plan is in `implementations/001-issue_shortlist_sept_2026.md`.

**Long-term direction:** a library-level contribution in dotnet/iot around **I2C target (slave) mode on Linux**, starting with a published platform survey and a design discussion before any API proposal.

---

## 5. How issues are chosen

Every issue on a shortlist is scored on five dimensions. The first two carry the most weight.

| Dimension | Question | Weight |
|---|---|---|
| **Exposure value** | Which concepts or technologies would I meet that I haven't worked with yet (§7.2)? How transferable are they to backend/cloud/systems work? | High |
| **Strength fit** | Does it use my strengths (§3), so I can contribute something maintainers can't easily get elsewhere? | High |
| **Feasibility** | Can I build, test, and reproduce it with my environment (§8.3) and hardware (§8.5)? | Gate (must pass) |
| **Scope & maintainer signal** | Is it labeled for contributors, unclaimed, and scoped to one area? | Gate (must pass) |
| **Career signal** | Microsoft-maintained repo? A story I could tell in an interview? | Medium |

### 5.1 Two kinds of issues: anchors and explorers

| Kind | Definition | Why both matter |
|---|---|---|
| ⚓ **Anchor** | Mostly in familiar territory (hardware, interop, I2C/SPI). High chance of a quality PR. | Builds a track record and maintainer trust |
| 🧭 **Explorer** | At least one significant concept I haven't worked with before (e.g., OAuth flows, TLS/ACME, protocol versioning, WebSockets, test infrastructure, concurrency design). | Delivers the exposure that drives growth |

**Target mix for each shortlist:** roughly half anchors and half explorers, with **at least two explorers from outside the device domain**. Every shortlist entry must list **"Concepts you'll encounter"** so the exposure value is explicit.

### 5.2 The refinement loop

```
 shortlist ──► study issues ──► log reactions (§10.2) + new concepts (§7.2)
     ▲                                          │
     └──── next shortlist weights toward what ──┘
           was most interesting and useful
```

Each refresh should be better targeted than the last, because it's informed by what I actually found valuable.

### 5.3 Learning picks: closed and claimed issues count too

An issue doesn't have to be available to be worth my time. A closed issue with a well-reviewed PR, or an open issue someone else is already working on, can teach as much as one I solve myself: a real bug, the fix, and the review discussion, all in one place. **Suggestions may include these freely**, including examples chosen at the suggester's discretion ("here's something worth seeing"), as long as each one is clearly labeled.

Every suggested item carries two labels:

| Label | Values | Meaning |
|---|---|---|
| **State** | 🟢 **Open, available** · 🟡 **Open, claimed** (assigned or has someone else's PR) · ⚫ **Closed** (fixed, merged, or declined) | What's actually happening on GitHub, as of the date checked |
| **Intent** | 🛠️ **Contribute**: worth my time to develop a PR, reproduction, or comment · 📖 **Learn**: study it for the concepts, code, and review; don't try to take it over | How I should spend time on it |

For 📖 **Learn** items, the write-up should focus on **what the issue was, what the fix or discussion shows, and the key lessons**. Code excerpts and before/after comparisons are welcome. If a learning item has an open follow-up I could pick up, call that out separately as 🛠️.

---

## 6. How I work (contribution principles)

1. **Comment before code.** For anything bigger than a typo, agree the approach with a maintainer on the issue first.
2. **Small, focused PRs, with tests.** One concern per PR. Bug fixes come with a test that fails before the fix.
3. **Reproduce first.** State environment, versions, and hardware in every issue comment and PR.
4. **Finish what I start.** Respond to review within 48 hours. If I can't continue, say so on the issue and hand it back.
5. **Transparent AI use.** Follow each repo's AI-disclosure policy. I don't submit code I can't explain line by line, and I never let an agent open PRs or post comments for me.
6. **Clean-room separation from my employer.** Personal hardware, personal time, personal accounts. No employer code, designs, or internal details in any contribution.
7. **One active PR at a time** until a repo's review rhythm is familiar. Questions and design comments can run in parallel.

---

## 7. Current learning focus and exposure map

### 7.1 Actively deepening

When an issue touches one of these, it doubles as study:

| Area | Why now | How open source helps |
|---|---|---|
| async/await internals and concurrency | Event loops and observer threads show up in GPIO drivers and network libraries | Issues around edge-event observers, cancellation, and locking |
| MSBuild, packaging, and multi-targeting | Large repos have custom build infrastructure | Building dotnet/iot and the MCP SDK from source |
| Navigating large codebases | Going from "one area" to "several areas" fluently | One context card per repo area (`implementations/`) |
| Distributed systems and networking | Backend career direction | YARP issues and docs |
| .NET API design and review | Needed before proposing any new public API | Reading API review threads; the I2C target discussion |

### 7.2 Exposure map

The concept areas I want exposure to, and where I've encountered each one through open-source work. **Shortlists should prioritize areas that are still empty.**

| Concept area | Examples | Encountered via (issue / PR) | Depth |
|---|---|---|---|
| Native interop & memory layout | P/Invoke, struct layout across architectures, native asserts, `SafeHandle` | | |
| Hardware protocols & drivers | I2C/SPI edge cases, register maps, libgpiod | | |
| Concurrency & event dispatch | Observer threads, locks vs. concurrent collections, event wrappers | | |
| Error handling & API compatibility | Exception design, fallbacks, behavior changes vs. breaking changes | | |
| Networking & proxies | Reverse proxies, WebSockets, timeouts, keep-alives | | |
| Security & identity | OAuth 2.0 / OIDC, TLS, certificate automation (ACME) | | |
| Protocols & versioning | Capability negotiation, spec-driven SDKs (MCP), JSON-RPC | | |
| Testing infrastructure | Flaky tests, CI timing, `WebApplicationFactory`, fakes vs. mocks | | |
| Build, packaging & CI | MSBuild, multi-targeting, NuGet packaging, GitHub Actions / Azure Pipelines | | |
| Containers & deployment | Device access in containers, minimal/chiseled images | | |
| Observability | OpenTelemetry, `Activity`, metrics | | |
| Performance | Benchmarking, allocations, startup (JIT vs. AOT) | | |
| Cloud & distributed systems | Azure SDK patterns, retries/resilience, messaging | | |

**Depth levels:** *Read* (studied the issue/code) → *Reproduced* → *Contributed* (merged PR) → *Can explain* (wrote a note or lecture about it).

---

## 8. Development environment

Open-source work depends on being able to **build and test the repo locally**, so this section is a working constraint for issue selection, not just an inventory. **Check the compatibility matrix (§8.3) before picking an issue.**

### 8.1 Machines

| Machine | Role | Capabilities | Constraints |
|---|---|---|---|
| **Linux desktop** (Ubuntu, x86-64) | Linux builds; driving hardware over the network | Full Linux environment. Runs .NET 10 (LTS, supported until Nov 2028). | **The CPU predates the `x86-64-v2` instruction-set level** (SSE4.2, POPCNT, etc.), which **.NET 11 requires** on x64. .NET 11 won't start on it at all, and repos that move their SDK to 11 won't build there. Limited disk and RAM for large builds. |
| **MacBook Air** (macOS) | Docs, reading, editing, SSH into boards, light builds | Runs .NET 10 and .NET 11 | **~20 GB free disk.** One dotnet/iot clone + build output + NuGet cache + a Docker image or two can use most of that. Not suitable for large repos or heavy Docker use. |
| **Raspberry Pi board(s)** | Hardware targets under test | Arm64 Linux. .NET 11's Arm64 Linux baseline is unchanged (`armv8.0-a`), so .NET 11 runs here. | Target devices, not dev machines. Deploy with `dotnet publish -r linux-arm64` + `rsync`. |
| **Bench equipment** | Hardware reproductions | *(fill in: logic analyzer, sensors, microcontroller boards, breadboard kit)* | *(fill in)* |

> **Check the desktop CPU precisely** (so the constraint is documented, not assumed):
> ```bash
> /lib64/ld-linux-x86-64.so.2 --help | grep x86-64    # lists which x86-64-v2/v3/v4 levels are "supported"
> grep -o -w 'sse4_2\|popcnt\|ssse3\|cx16' /proc/cpuinfo | sort -u   # the key v2 features
> lscpu | grep 'Model name'
> ```
> Record the model name here: *(fill in)*

### 8.2 The .NET version landscape (why this matters now)

| Version | Status (as of 2026-09-26) | Implication |
|---|---|---|
| .NET 8, .NET 9 | **End of support on Nov 10, 2026** | Repos will drop them. Don't target them in new work. |
| **.NET 10** | LTS, supported until Nov 2028 | Runs on **every** machine I own. The safe baseline for personal projects. |
| **.NET 11** | RC1 shipped Sept 8, 2026 (go-live license); GA expected in November; STS (24 months) | Requires `x86-64-v2` on x64. **Runs on the Mac and the Pis, not the desktop.** Repos' `main` branches will move their `global.json` SDK to 11 over the next months. |

### 8.3 Compatibility matrix: where each repo can be built and tested

Re-check each repo's `global.json` before starting. It pins the SDK version, and that pin is what decides whether a machine can build the repo.

| Repo | Linux desktop | MacBook Air | Codespaces (cloud) | Notes |
|---|---|---|---|---|
| **dotnet/iot** | ✅ while the pinned SDK is ≤ 10 (it pinned .NET 9 with roll-forward as of Sept 2026) | ⚠️ builds, but disk-heavy | ✅ | Hardware testing needs the Pis regardless. **Re-check the pin after .NET 11 GA.** |
| **MCP C# SDK** | ✅ requires the .NET 10 SDK | ⚠️ disk; some tests need Docker | ✅ best fit | Docker-based tests are easiest in Codespaces |
| **YARP** | ⚠️ depends on the SDK pin; `main` tends to track the newest .NET | ⚠️ disk | ✅ | |
| **dotnet/AspNetCore.Docs**, **dotnet/docs** | ✅ (Markdown) | ✅ | ✅ | Any machine works. Docs PRs can even be made from the GitHub web editor. |
| **OpenTelemetry .NET / Contrib** | ⚠️ until the repos move to the .NET 11 SDK (in progress as of Sept 2026) | ⚠️ disk | ✅ best fit | Some exporters need Docker (e.g., InfluxDB) |
| **dotnet/runtime** | ❌ too large; SDK will be 11+ | ❌ disk | ⚠️ only with a large machine type | Reading only, for now |

### 8.4 Plan: free options first, then targeted purchases

**Tier 0: no cost (use immediately).**
- **GitHub Codespaces** for the MCP C# SDK and YARP. The GitHub Free plan includes **120 core-hours and 15 GB-month of storage per month** (60 hours of a 2-core machine). Delete codespaces when a PR is done so storage doesn't accumulate.
- **Linux desktop** for dotnet/iot while its SDK pin stays at 10 or lower, and for cross-compiling/deploying to the Pis.
- **MacBook** for docs, reviews, and SSH. Keep at most one repo clone on it, and run `dotnet nuget locals all --clear` and `docker system prune` periodically.

**Tier 1: external SSD for the Mac (~$70–120 for 1 TB USB-C NVMe).**
- Solves the disk constraint immediately: keep git clones, build output, and Docker Desktop's disk image (movable in Docker Desktop's settings) on the SSD.
- Worth it if the Mac becomes the main .NET 11 machine.

**Tier 2: replace the desktop with a modern x86-64 mini PC (~$150–350, used/refurbished business mini PCs are good value; RAM prices have been volatile, so check current listings).**
- **Target spec:** a CPU with `x86-64-v3` support (e.g., Intel 8th gen or newer, AMD Ryzen), **16–32 GB RAM**, **512 GB+ NVMe SSD**, Ubuntu LTS.
- `x86-64-v3` matters, not just v2: .NET 11's precompiled (ReadyToRun) framework code targets v3 on Linux/Windows, so v3 hardware gets the optimized code paths.
- Solves both constraints at once (instruction set + disk), and becomes the main Linux dev box for all three repos.
- The old desktop can stay useful as a .NET 10 build/test machine or a network utility box for the hardware bench.

**Recommendation:** start with Tier 0 now. **Tier 2 is the purchase with the best return.** Make it when either trigger below fires, or sooner if builds on the desktop are slow enough to discourage work. Tier 1 is only worth it if the Mac is going to be the main machine instead.

**Purchase triggers (write the date when one fires):**
- [ ] A target repo's `global.json` moves to the .NET 11 SDK (likely soon after November 2026 GA) → Tier 2
- [ ] Codespaces quota runs out two months in a row → Tier 2
- [ ] The Mac drops below 10 GB free during normal work → Tier 1 (or Tier 2 if not done)

### 8.5 Hardware lab (for reproductions)

| Item | Status | Needed for |
|---|---|---|
| Raspberry Pi 4 / Pi 5 | *(fill in: owned / planned)* | All dotnet/iot hardware work; I2C target research |
| USB logic analyzer (8-ch) + PulseView | *(fill in)* | Every bus-level bug; evidence for PRs |
| Raspberry Pi Pico (×2) | *(fill in)* | I2C controller test rigs |
| MPU-6050 breakout | *(fill in)* | dotnet/iot #2356 |
| FT232H / FT4232H USB-I2C adapter | *(fill in)* | dotnet/iot #2352 (stretch) |
| Breadboard, jumpers, pull-ups, a known-good I2C sensor | *(fill in)* | Baseline bench |

All of this is **personal equipment**, kept separate from anything employer-owned.

---

## 9. Time budget

| Block | Hours / week | Notes |
|---|---|---|
| Open-source contribution | ~3 | Issue study, reproductions, PRs, responding to reviews |
| Reading / "predict the review" | ~1 (from the design-reading block) | One merged PR per week in a focus repo |
| Community | ~0.5 | Issue discussions, answering questions |

---

## 10. Record and feedback

### 10.1 Contribution record

Update after each contribution. This is the source for resume lines and interview stories.

| Date | Repo | Issue / PR | Type | Status | What I learned |
|---|---|---|---|---|---|
| | | | | | |

---

### 10.2 Issue study log (feedback for future shortlists)

After studying an issue from a shortlist, add a row, even if I decide not to work on it. **This is the main input for honing future suggestions.**

| Date | Issue | Anchor / Explorer | Interest (1–5) | Useful for growth (1–5) | New concepts met | Decision (pursue / park / skip) and why |
|---|---|---|---|---|---|---|
| | | | | | | |

### 10.3 Preference signals

Patterns distilled from §10.2. Update at each shortlist refresh.

- **More of:** *(fill in as patterns emerge, e.g., "issues where the root cause crosses the managed/native boundary")*
- **Less of:** *(fill in)*
- **Concepts I want next:** *(fill in; also update §7.2)*

---

## 11. Notes for AI sessions using this profile

**When producing or refreshing an issue shortlist:**

1. **Read §2, §5, §7.2, and §10 first.** They define what "a better issue" means for me, and they change over time.
2. **Score each candidate on §5's dimensions.** Apply the gates (feasibility against §8.3 and §8.5; unclaimed, labeled, scoped) before anything else.
3. **Balance the list:** about half anchors and half explorers, with at least two explorers outside the device domain (§5.1).
   **Include 📖 Learn picks freely** (closed issues, merged PRs, issues someone else has claimed) when they teach something valuable. Suggestions at your own discretion are welcome (§5.3).
   **Label every item with State (🟢 / 🟡 / ⚫) and Intent (🛠️ Contribute / 📖 Learn)**, as of the date checked.
4. **For every issue, include "Concepts you'll encounter"** and mark which §7.2 areas it covers. Prefer areas that are still empty or only at *Read* depth.
5. **Use §10.2 and §10.3.** Weight toward issue types rated high on interest and growth; avoid repeating patterns marked "less of." Don't re-suggest issues already studied unless their status changed.
6. **Ask for feedback** at the end: which issues were most interesting, and what to see more of. Then update §10.3.

**General:**

- Don't recommend work that needs a .NET 11 SDK build on the Linux desktop, or a large clone on the MacBook. Suggest Codespaces or flag the hardware need instead.
- **Keep this document public-safe:** strengths-forward, professional, no employer names, products, or internal details.
- **Update §7.2, §8, and §10** when the user reports new hardware, a purchase, an issue studied, or a merged PR.


---

## Sources (checked 2026-09-26)

- [.NET 11 breaking change: minimum hardware requirements](https://learn.microsoft.com/en-us/dotnet/core/compatibility/jit/11/minimum-hardware-requirements) (x64 JIT/AOT minimum `x86-64-v2`; ReadyToRun targets `x86-64-v3` on Windows/Linux; Arm64 Linux minimum unchanged; older CPUs fail to start)
- [Announcing .NET 11 RC1 (Sept 8, 2026)](https://devblogs.microsoft.com/dotnet/dotnet-11-rc-1/) · [Visual Studio Magazine: RC1 go-live ahead of November launch](https://visualstudiomagazine.com/articles/2026/09/14/net-11-rc1-gets-go-live-support-ahead-of-november-launch.aspx)
- [.NET 8 and .NET 9 end of support on Nov 10, 2026](https://devblogs.microsoft.com/dotnet/dotnet-8-9-end-of-support/) · [.NET STS releases supported for 24 months](https://devblogs.microsoft.com/dotnet/dotnet-sts-releases-supported-for-24-months/) · [.NET support policy](https://dotnet.microsoft.com/en-us/platform/support/policy/dotnet-core)
- [GitHub Codespaces billing and included usage](https://docs.github.com/billing/managing-billing-for-github-codespaces/about-billing-for-github-codespaces)
- Hardware prices are rough estimates; check current listings before buying.
