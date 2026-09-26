# Open Source Contributor Profile — Timothy Grant

> **What this is:** the living reference for my open-source work. It covers what I bring, where I'm focusing, how I work, and the development environment I work in. It's the first thing to read (for me, or for an AI session helping me) before choosing an issue or planning a contribution.
>
> **Last updated:** 2026-09-26 · **Update it:** after every merged PR, every hardware change, and at each monthly issue-shortlist refresh.
>
> **Related:** `implementations/` (actionable plans and issue shortlists) · `lectures/` (supporting concepts) · the repo-root `persona.md` (broader learning profile)

---

## 1. Summary

Firmware engineer turned .NET engineer, working across the hardware/software boundary. My background is embedded C on bare-metal microcontrollers (I2C, SPI, register-level drivers). More recently I've been on a production .NET team, where I built a Linux background service that ingests hardware telemetry through native interop (P/Invoke, struct marshalling, native callbacks) and feeds a rules engine that drives automated decisions. That work shipped through code review and CI/CD.

In open source, I focus on **.NET libraries where systems knowledge matters**: device and GPIO libraries, native interop, and developer tooling for AI systems (MCP). My goal is sustained, high-quality contributions to Microsoft-maintained .NET repositories.

---

## 2. What I bring

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

## 3. Focus and venues

| Role | Repository | Why |
|---|---|---|
| **Primary** | [`dotnet/iot`](https://github.com/dotnet/iot) | Where my hardware and interop background adds the most value |
| **Secondary** | [`modelcontextprotocol/csharp-sdk`](https://github.com/modelcontextprotocol/csharp-sdk) | AI tooling in .NET; maintained in collaboration with Microsoft |
| **Backend satellite** | [`dotnet/yarp`](https://github.com/dotnet/yarp) (+ its docs in `dotnet/AspNetCore.Docs`) | Reverse proxy / networking. Builds the backend side of my profile. |
| **Reading, not contributing yet** | `Microsoft.Extensions.*` in `dotnet/runtime` | Studying DI, Hosting, and Options design in depth |

The current issue plan is in `implementations/001-issue_shortlist_sept_2026.md`.

**Long-term direction:** a library-level contribution in dotnet/iot around **I2C target (slave) mode on Linux**, starting with a published platform survey and a design discussion before any API proposal.

---

## 4. How I work (contribution principles)

1. **Comment before code.** For anything bigger than a typo, agree the approach with a maintainer on the issue first.
2. **Small, focused PRs, with tests.** One concern per PR. Bug fixes come with a test that fails before the fix.
3. **Reproduce first.** State environment, versions, and hardware in every issue comment and PR.
4. **Finish what I start.** Respond to review within 48 hours. If I can't continue, say so on the issue and hand it back.
5. **Transparent AI use.** Follow each repo's AI-disclosure policy. I don't submit code I can't explain line by line, and I never let an agent open PRs or post comments for me.
6. **Clean-room separation from my employer.** Personal hardware, personal time, personal accounts. No employer code, designs, or internal details in any contribution.
7. **One active PR at a time** until a repo's review rhythm is familiar. Questions and design comments can run in parallel.

---

## 5. Current learning focus

What I'm actively deepening. When an issue touches one of these, it doubles as study:

| Area | Why now | How open source helps |
|---|---|---|
| async/await internals and concurrency | Event loops and observer threads show up in GPIO drivers and network libraries | Issues around edge-event observers, cancellation, and locking |
| MSBuild, packaging, and multi-targeting | Large repos have custom build infrastructure | Building dotnet/iot and the MCP SDK from source |
| Navigating large codebases | Going from "one area" to "several areas" fluently | One context card per repo area (`implementations/`) |
| Distributed systems and networking | Backend career direction | YARP issues and docs |
| .NET API design and review | Needed before proposing any new public API | Reading API review threads; the I2C target discussion |

---

## 6. Development environment

Open-source work depends on being able to **build and test the repo locally**, so this section is a working constraint for issue selection, not just an inventory. **Check the compatibility matrix (§6.3) before picking an issue.**

### 6.1 Machines

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

### 6.2 The .NET version landscape (why this matters now)

| Version | Status (as of 2026-09-26) | Implication |
|---|---|---|
| .NET 8, .NET 9 | **End of support on Nov 10, 2026** | Repos will drop them. Don't target them in new work. |
| **.NET 10** | LTS, supported until Nov 2028 | Runs on **every** machine I own. The safe baseline for personal projects. |
| **.NET 11** | RC1 shipped Sept 8, 2026 (go-live license); GA expected in November; STS (24 months) | Requires `x86-64-v2` on x64. **Runs on the Mac and the Pis, not the desktop.** Repos' `main` branches will move their `global.json` SDK to 11 over the next months. |

### 6.3 Compatibility matrix: where each repo can be built and tested

Re-check each repo's `global.json` before starting. It pins the SDK version, and that pin is what decides whether a machine can build the repo.

| Repo | Linux desktop | MacBook Air | Codespaces (cloud) | Notes |
|---|---|---|---|---|
| **dotnet/iot** | ✅ while the pinned SDK is ≤ 10 (it pinned .NET 9 with roll-forward as of Sept 2026) | ⚠️ builds, but disk-heavy | ✅ | Hardware testing needs the Pis regardless. **Re-check the pin after .NET 11 GA.** |
| **MCP C# SDK** | ✅ requires the .NET 10 SDK | ⚠️ disk; some tests need Docker | ✅ best fit | Docker-based tests are easiest in Codespaces |
| **YARP** | ⚠️ depends on the SDK pin; `main` tends to track the newest .NET | ⚠️ disk | ✅ | |
| **dotnet/AspNetCore.Docs**, **dotnet/docs** | ✅ (Markdown) | ✅ | ✅ | Any machine works. Docs PRs can even be made from the GitHub web editor. |
| **dotnet/runtime** | ❌ too large; SDK will be 11+ | ❌ disk | ⚠️ only with a large machine type | Reading only, for now |

### 6.4 Plan: free options first, then targeted purchases

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

### 6.5 Hardware lab (for reproductions)

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

## 7. Time budget

| Block | Hours / week | Notes |
|---|---|---|
| Open-source contribution | ~3 | Issue work, reviews, reproductions |
| Reading / "predict the review" | ~1 (from the design-reading block) | One merged PR per week in a focus repo |
| Community | ~0.5 | Issue discussions, answering questions |

---

## 8. Contribution record

Update after each contribution. This is the source for resume lines and interview stories.

| Date | Repo | Issue / PR | Type | Status | What I learned |
|---|---|---|---|---|---|
| | | | | | |

---

## 9. Notes for AI sessions using this profile

- **Check §6.3 before recommending an issue.** Don't recommend work that needs a .NET 11 SDK build on the Linux desktop, or a large clone on the MacBook. Suggest Codespaces or flag the hardware need instead.
- **Prefer issues that use §2 strengths**, especially hardware reproductions and native interop.
- **Keep this document public-safe:** strengths-forward, professional, no employer names, products, or internal details.
- **Update §6 and §8** when the user reports new hardware, a purchase, or a merged PR.

---

## Sources (checked 2026-09-26)

- [.NET 11 breaking change: minimum hardware requirements](https://learn.microsoft.com/en-us/dotnet/core/compatibility/jit/11/minimum-hardware-requirements) (x64 JIT/AOT minimum `x86-64-v2`; ReadyToRun targets `x86-64-v3` on Windows/Linux; Arm64 Linux minimum unchanged; older CPUs fail to start)
- [Announcing .NET 11 RC1 (Sept 8, 2026)](https://devblogs.microsoft.com/dotnet/dotnet-11-rc-1/) · [Visual Studio Magazine: RC1 go-live ahead of November launch](https://visualstudiomagazine.com/articles/2026/09/14/net-11-rc1-gets-go-live-support-ahead-of-november-launch.aspx)
- [.NET 8 and .NET 9 end of support on Nov 10, 2026](https://devblogs.microsoft.com/dotnet/dotnet-8-9-end-of-support/) · [.NET STS releases supported for 24 months](https://devblogs.microsoft.com/dotnet/dotnet-sts-releases-supported-for-24-months/) · [.NET support policy](https://dotnet.microsoft.com/en-us/platform/support/policy/dotnet-core)
- [GitHub Codespaces billing and included usage](https://docs.github.com/billing/managing-billing-for-github-codespaces/about-billing-for-github-codespaces)
- Hardware prices are rough estimates; check current listings before buying.
