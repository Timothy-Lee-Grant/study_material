# Where I Stand

> **Owner:** Timothy Grant · **Last updated:** 2026-11-07 · **Next full review:** with the monthly rescore of `learning_system/learning_plan.md` (early December), or sooner after any recall check, lab milestone, or interview round.
> **What this is:** the one place that answers *what am I good at, what's still weak, where does each area stand, and what am I working on right now.* Every claim has a date and a piece of evidence behind it.
> **Use it for:** handing context to another project or AI session (§0 is written to be pasted as-is), and checking progress against myself a month from now.
> **Public by choice.** This file lists skills and evidence only. No employer or product names, and no references to specific interviews. Candid notes about *how* I learn (learning-psychology observations) stay in the git-ignored `learning_system/private/`.
> **Status legend used throughout:** 🟢 solid (explained or done correctly, unprompted) · 🟡 partial (right shape, a piece missing or fuzzy) · 🔴 active gap (a wrong model, or failing in practice) · ⚪ not shown yet (material exists, never explained back or practised) · ❌ not started

---

## 0. Hand-off summary (paste this into another project)

```
WHO: Timothy Grant. Electrical engineer; ~3 years of bare-metal embedded C (I2C/SPI, registers, ATmega-style
MCUs), then ~6 months (Mar–Sep 2026) on a production .NET team: a .NET app on an embedded Linux board that
ingests hardware telemetry and orchestrates VM shutdowns. Built the telemetry firmware, a .NET ingestion worker
using P/Invoke into a native C GPIO library (Pi as I2C target), derived-state calculations, PowerShell cmdlets.
Open-source contributions to YARP and dotnet/iot.

TARGET: systems / platform software engineer (Windows platform, devices, validation & reliability, drivers,
edge/IoT). Named goal: Microsoft Software Engineer 2. Currently interviewing.

STRONG: cross-boundary work (firmware <-> Linux <-> .NET interop); hands-on building (wrote, signed and loaded
his own Windows kernel driver in an Arm VM, called it from user mode, now debugging it in WinDbg); deriving rules
from first principles; well-calibrated doubts; explains his own work in depth; math/bit-level decoding.

STILL BUILDING: OS/hardware mechanisms below the API (how a physical access reaches a device, virtual memory as
a global mode, where blocking work may run, interrupt routing); coding-interview speed and recursion/DP;
system design (no timed attempt yet); retention (much material generated, little recalled yet).

HOW TO TEACH HIM: top-down map first, then who runs it / who calls it, then details. Name every actor (which
driver, which controller), never "the OS". Say what every symbol/number stands for before using it in a formula.
One canonical procedure per skill. No firmware analogies, no personified "characters". One request = one
self-contained document. Mark what is safe to treat as a black box.

FULL DETAIL: where_i_stand.md in his Studying_Lectures repo.
```

---

## 1. Snapshot (Nov 7, 2026)

1. **Background is a real asset for the target roles.** Hardware → firmware → Linux → .NET is a rare combination, and platform/device roles are where it counts most.
2. **The driver lab is the strongest current evidence.** Phases 0–4 done (Oct 23–25): Windows 11 Arm VM, TgCounter driver built, test-signed, loaded, called from user mode. Phase 5 (inspect, crash, analyze) is in progress: local kernel debugging works, lab 5.1 exercise 1 of 8 done.
3. **Coding:** index and boundary derivations are now correct almost every time (since mid-Oct) but slow; recursion/DP and choosing the right pattern from a blank page are the open items.
4. **OS internals:** the event chains (a touch → driver → app; syscall; context switch) are mostly right and partly self-derived. The fuzzy layer is one level lower: physical addresses, the MMU, interrupt wiring, and where blocking work is allowed.
5. **The bottleneck is retention, not coverage.** Of 147 lecture documents, 6 have been recalled and 3 more confirmed read. Nearly every core topic already has material; the hours should go to reading, explaining back, and labs.

---

## 2. Strengths (with evidence)

| Strength | Evidence (date) | How to use it |
|---|---|---|
| **Cross-boundary systems experience** | Production work: MCU firmware sending framed I2C messages → .NET worker with P/Invoke into a native C library (struct marshalling, native callbacks, Pi as I2C target) → derived-state data model → PowerShell cmdlet tooling | Lead with it. It's the story platform and device teams want |
| **Builds things, not just reads about them** | Kernel driver lab from plan to a working driver in about a week (Oct 23–30); QEMU and concurrency labs run; PowerShell showcase solution for a planned video (Nov 1) | Pair every new topic with a lab. Labs are also interview stories |
| **Derives rules from first principles** | Derived the "no waiting at DISPATCH_LEVEL" rule in his own words (Oct 21). Self-derived most of the syscall / thread / scheduler model, incl. "there is no orchestrator, the timer interrupt is the backstop" (Nov 1). Solved 739 Daily Temperatures with a monotonic stack without reading the stack lecture (Oct 20) | Pose the problem before revealing the mechanism |
| **Well-calibrated doubt** | Flagged doubts were justified 3/3 (Oct 21 recall) and 9/9 (Nov 4 talk-through); spotted a contradiction in his own address model unprompted (Nov 4) | When he says "I'm not sure about X", X is usually the real gap. Start there |
| **Applies feedback fast** | Removed 7 of 8 bug classes the same evening he read the first matrix lecture (Oct 3). By Oct 18, every index/boundary derivation in four problems was correct | Short feedback loops pay off quickly |
| **Explains his own work in depth** | P/Invoke pinning and struct layout explained confidently under questioning (late Oct) | Turn more topics into "his own work" via labs |
| **Generates and compares designs** | Browser History: three valid designs (linked list + cursor, array, two stacks), each costed per operation (Oct 17). Independently arrived at exit → action → entry transitions for a state-machine design (Oct 12) | Ask for 2–3 options and their costs before picking |
| **Designs his own learning systems** | Built the recall loop, the clarifications talk-through process, per-problem deep dives, and a system design practice kit (Sep 29 – Nov 6) | The systems exist; the work now is using them |
| **Verification instinct** | Found that a CI pipeline was green while installing zero dependencies (LLM_Monitor); caught stale file writes | A real-world review/validation story |
| **Math and bit-level work** | Signed vs unsigned decoding from raw hex in production | Quantitative framings are safe footholds |
| **Shipped open source** | Contributions to YARP and dotnet/iot; a dotnet/iot device binding started | Résumé evidence; finish the open binding before starting new repos |

---

## 3. Growth areas (with evidence)

### 3.1 Coding interviews

| Gap | Status | Evidence (date) | Next step |
|---|---|---|---|
| **Speed and confidence on derivations he gets right** | 🟡 | Boundaries correct but slow (Oct 18). Stuck ~90 min on a sliding window when two index models (box vs cut) got mixed in one loop (Oct 31) | One canonical model per skill; a time-boxed "stuck protocol" (switch to numbers at 10 min, simplify at 20) |
| **Recursion contract: answers flow up, context flows down; base cases** | 🟡 | Improving: Climbing Stairs written answer-up unaided (Oct 4). Earlier DP attempts carried the answer down as a parameter. DP family barely practised since | Lecture `leetcode/002` (unread), then 70 → 198 → 91 from blank |
| **Choosing the pattern from a blank page** | 🔴 | 46 Permutations: used the subsets (include/exclude) tree, which can't produce orderings (Nov 6). Earlier: relied on the list's label ("I know this is a sliding window problem") | Before coding: one-sentence brute force + "what is decided at each level? how many leaves?". Retry 46 |
| **Tracing linked lists and recursion** | 🔴 | 21 Merge Two Sorted Lists: `tail` never advanced, not caught (Oct 21): "I don't know how to do walk-throughs on linked lists" | Trace table with a column per named pointer; call-tree format for recursion |
| **Tail completeness and name-vs-use** | 🟡 | 26: `return k` returned duplicates, not the kept count (Oct 18). 1456: missing `i += 1` in the saved version (Oct 20) | Two pre-submit checks: run the return line on example 1; every named variable has an update line |
| **Pinning down the interface of a stateful problem under time pressure** | 🔴 | Byte-stream packet parser (preamble / length / data / checksum): couldn't establish inputs and outputs in time (Oct 31) | First move on any design-flavoured coding prompt: write one example call and its exact output. Lecture `leetcode/019` |
| **Python fluency** | 🟡 | Small API slips (`.append()` returns None, `del` vs `.remove`) through Sep | Cheat sheet; cheap fix |

### 3.2 OS and hardware mechanisms (the layer below the API)

The chains are mostly right; the gaps are about **which component does what, at what time**. Details: `lectures/clarifications/log.md` (groups G1–G9).

| Concept | Status | Evidence (date) | Fix lives in |
|---|---|---|---|
| How a load/store reaches DRAM or a device register (transaction + address decoding, not a direct wire) | 🔴 | "a 100% direct connection between the CPU register and the external location" (Nov 4) | Clarifications G1–G3 |
| Virtual memory is a global mode; every access goes through the core's MMU | 🔴 | "based on the instruction, the address is virtual or physical" (Nov 4) | Clarifications G4; `windows_internals/018` |
| Where blocking work may run (ISR → DPC → passive-level work item) | 🔴 | Put a blocking read in the DPC in a device-to-UI design exercise (Oct 31), although the no-wait rule itself was derived correctly (Oct 21) | `windows_internals/014` §DPC; ask "which context may wait here?" |
| IRQL: per-CPU value in a CPU register; priority ≠ privilege | 🔴 | "a specific register in RAM"; ISR at "the highest permissions" (Oct 21) | `windows_internals/005` |
| Interrupt routing (shared lines, pin → GPIO controller → APIC/GIC → core; set up at boot, used at runtime) | 🔴 | "each device gets its own GPIO pin"; ACPI consulted at interrupt time (Oct 21) | `windows_internals/005`, `014` |
| Naming the actor (device driver vs controller driver vs I/O manager) instead of "the OS" | 🟡 | Recurs in Oct 18 and Oct 21 recalls | Habit: one numbered per-event trace naming every actor |
| Sockets: NIC → DMA → kernel receive buffer → `read()` copies; blocking semantics; bytes vs hex | 🔴 | Bytes "living inside the network card"; "streaming hex values" (Nov 4) | Clarifications G6, G8, G9 |
| Thread states and stacks (≤1 running per core; reserved ≠ committed memory) | 🟡 | "1000 threads in the running state"; "1 MB × 5000 = out of RAM" (Nov 1) | `concurrency/002–003` (unread) |
| Shared memory and cross-process synchronization | ⚪ | Not explained back since an earlier claim that processes can't share locks | `windows_internals/008` |

### 3.3 Design

| Gap | Status | Evidence | Next step |
|---|---|---|---|
| **System design under time** | ⚪ | Practice kit built Nov 6 (19 cases, rubric, timer); 0 attempts so far | One timed, spoken attempt per week, scored with `practice/rubric.md` |
| **Choosing and combining data structures with an invariant** | 🟡 | Browser History: good options, but couldn't merge two of them, and was uneasy about arbitrary call orders without an invariant to rely on (Oct 17) | `leetcode/012`, `013`; state the invariant in one sentence before coding |
| **Answering at the altitude of the question** | 🟡 | A senior engineer's feedback: models systems from the implementation up rather than as states (Oct 12). Long answers about past work run over time (Oct 31) | Top-down first sentence; a 2-minute version of each story |

### 3.4 Habits

| Habit | Evidence | Countermeasure |
|---|---|---|
| **Generated ≠ learned** | 147 documents, 6 recalled. Said "I don't know sockets" a month after a sockets lecture was generated (Sep 26) | Generation budget 1–2 lectures a week; recall on walks; labs |
| **Too many open threads** | Coding, system design, OS internals, driver lab, concurrency, emulation, OSS, a video, LLM_Monitor | One build thread at a time (the driver lab); OSS paused at "finish what's open" |
| **Bottom-up default** | Self-reported, and now flagged by a senior engineer (Oct 12) | Contract first, then depth only where the contract isn't enough |

---

## 4. Where I stand, area by area

| Area | Status | Material | Last evidence | Next action |
|---|---|---|---|---|
| **Ring 0: coding interview** | 🟡 | `leetcode/` (gradient, 20 lectures, practice queue, deep dives) | 46 Permutations attempt (Nov 6) | One problem a day through the deep-dive loop; retry 46 |
| **Ring 0: system design** | ⚪ | `system_design/001–002`, `practice/` | Kit built (Nov 6), no attempts | First timed attempt (read path case a01) |
| **Ring 0: explaining my own work** | 🟢/🟡 | `firmware/windows_platform_validation.md` story bank | Strong on P/Invoke (late Oct); runs long | 2-minute versions: work project, P/Invoke + pigpio, driver lab, qualification-script crash |
| Processes, threads, syscalls, scheduling | 🟢/🟡 | `concurrency/002`, `windows_internals/008` | Self-derived model (Nov 1) | Read `concurrency/002`, then recall on a walk |
| Virtual memory and paging | 🔴 | `windows_internals/008`, `018`; clarifications G4 | ~22% recall (Oct 21); Nov 4 talk-through | Clarification lecture for G1–G4 |
| Synchronization (locks, deadlock, spin vs mutex, producer/consumer) | ⚪ | Only inside `windows_internals/008` | — | The one new lecture worth writing |
| Async and the .NET thread pool | 🟡 | `concurrency/001`, `003` + lab | Nov 1 write-up (pool and await details off) | Read `003` and run its lab with predictions |
| Hardware map (SoC, physical addresses, MMIO) | 🔴 | Clarifications G1–G3 | Nov 4 | Clarification lecture |
| Interrupts and deferred work | 🟡 | `firmware/003`, `windows_internals/005`, `014` | ~22–25% recall (Oct 21); recall overdue | Recall `firmware/003`, then read `014` |
| Drivers and device stacks | 🟡 | `windows_internals/006`, `009`; lab Phases 0–4 ✅ | Driver loaded and called (Oct 25) | Finish reading `009` |
| Debugging (WinDbg, dumps, Verifier, ETW/WPA) | 🟡 | `windows_internals/001–004`, `013`, `018` | Local kernel debugging working, 5.1 exercise 1 done (Nov 1) | Lab 5.1 exercise 2 → 5.2 live dump → 5.3 crash |
| Performance and power | ⚪ | `windows_internals/007`, `015`, `016` | — | After the crash labs |
| Linux boot, systemd, udev | ⚪ | `firmware/audio/004–005` | — | Hands-on on the Pi: `dmesg`, `systemd-analyze critical-chain` |
| Emulation (QEMU, injected device inputs) | ⚪ | `emulation/001–002` | — | Optional: run the injection harness on the Mac |
| .NET host, DI, lifetimes | 🟡 | `dotnet/001`, `003` | Used in production | Review lifetimes |
| P/Invoke and marshalling | 🟢/🟡 | `dotnet/002` | Production + explained well (Oct) | Delegate lifetime / GC pinning review |
| PowerShell cmdlets | 🟡 | `dotnet/006`, `examples/powershell` | Wrote several in production; showcase not yet compiled | Build the showcase, then record the video |
| Networking, HTTP, reverse proxies (YARP) | ⚪ | `yarp/001–012`, `dotnet/005` | Contributed to YARP | Parked |
| Distributed systems, cloud/Azure | ❌/⚪ | `yarp/009`, `llm_orchistration/021` | — | Parked (Ring 2 or later) |
| AI engineering (LLM_Monitor) | 🟡 | `llm_orchistration/001–024` | Built phases 1–2 | Parked |

---

## 5. What I'm working on right now

| Thread | State | Next concrete step | Where |
|---|---|---|---|
| **Windows driver lab** | Phase 5.1, exercise 1 of 8 done | Exercise 2 (`!drvobj`, `!devobj`, `dt` of the device extension), then live dump, then crash labs | `windows_internals/011` (handoff), `013`, `018` |
| **LeetCode deep-dive loop** | Deep dive 001 (46 Permutations) written | Retry 46 with the level question and leaf count first | `leetcode/problem_deep_dives/` |
| **System design practice** | Kit ready | First timed spoken attempt | `system_design/practice/` |
| **Clarifications** | 1 talk-through logged (Nov 4), 9 groups queued | Ask for the G1–G4 clarification lecture when ready | `lectures/clarifications/log.md` |
| **Recall checks due** | `firmware/003` + platform lecture (due Oct 23), `leetcode/004`, `001` | One on the next walk | `learning_system/private/reading_status.md` |
| **Interviewing** | Active, systems/platform roles | Interview-active mode in the learning plan when a round is within ~2 weeks | `learning_system/learning_plan.md` §5 |
| **Open source** | Paused at "finish what's open" | Finish the dotnet/iot binding | `lectures/open_source/` |
| **PowerShell video** | Solution written, not compiled | First build | `examples/powershell/`, `dotnet/006` |

---

## 6. Numbers (learning system)

| Measure | Value (Nov 7) | Healthy direction |
|---|---|---|
| Lecture documents generated | 147 (incl. 16 audio) | Grow slowly: 1–2 a week |
| Confirmed read or used | 3 | Up |
| Recalled (explained back, scored) | 6 | Up: this is the number that matters |
| Recall scores so far | 20–70% (best: binary search, 70%) | Up on re-recall |
| LeetCode problems logged | 34 attempts in the tracker | Steady daily |
| System design attempts | 0 | 1 per week |
| Driver lab phases complete | 4 of 6 | 5 by the next review |

---

## 7. How I learn best (for anyone teaching me)

What has evidence behind it:

1. **Top-down map first**, then who runs it and who calls it, then details. Say which layers I can treat as a black box for now.
2. **Name every actor.** A numbered per-event trace ("1. the touch controller pulls ATTN low. 2. …") works better than a story or a diagram alone.
3. **Say what each symbol or number stands for before using it** (place vs amount, box vs cut). That one habit turned "arbitrary ±1s" into obvious ones.
4. **Name the intermediate quantity, define its valid set, state the condition positively,** then derive in small numbered steps.
5. **One canonical procedure per skill.** Other framings are fine, presented as translations of the default.
6. **Let me deduce.** Pose the problem before showing the mechanism; check my model row by row, confirming what's right before correcting what isn't.
7. **Hands-on, predict first:** "what do you expect this command to print?" before running it.
8. **Explaining is how I learn.** Walk-and-talk recalls and written self-explanations are where confusion resolves.
9. **Format:** one request = one self-contained document; a short Core ideas list first; full problem statements, not just names; no firmware analogies; no personified "characters"; framed as concepts, not as prep for a specific interview.

---

## 8. Keeping this file current

**When to update which section:**

| Event | Update |
|---|---|
| A recall check or talk-through | §3 rows it touches (status + dated evidence), §4 status, §6 counts |
| A lab milestone (e.g. a driver-lab phase done) | §1 point 2, §4 row, §5 row, §6 |
| A LeetCode attempt or deep dive | §3.1 only if a gap changes status; §6 count weekly, not per problem |
| A system design attempt | §3.3, §4, §6 |
| An interview round | §3 for anything it exposed (no company or interview details, by choice), §5 |
| A new strength shows up | §2 with a dated example |
| Monthly rescore of the learning plan | Re-read the whole file; refresh §0 and §1; add a changelog row |

**Where the evidence comes from** (read these, don't duplicate them):

| Source | Feeds |
|---|---|
| `learning_system/private/reading_status.md` | §4 statuses, §6 counts |
| `learning_system/private/understanding/*.md` | §3.2 |
| `lectures/clarifications/log.md` | §3.2 |
| `lectures/leetcode/private/000-weakness_tracker.md` | §3.1 |
| `lectures/system_design/practice/progress.md` | §3.3 |
| `lectures/windows_internals/011-session_handoff.md` | §5 driver lab |
| `learning_system/learning_plan.md` | §4 next actions (the plan picks *what to study*; this file says *where I stand*) |

**Rules:**
- Change a status only on evidence: something I said, wrote, built, or ran. A lecture being generated doesn't change a status.
- Every row gets a date. Move a row to 🟢 only when I've shown it unprompted.
- Keep it public-safe: skills and evidence; no employer, product, or interview specifics; no learning-psychology observations (those stay in `learning_system/private/`).
- Keep §0 under ~25 lines so it can be pasted anywhere.
- Rewrite rows in place; don't let the file grow into a log. History goes in the changelog, one line per update.

---

## Changelog

| Date | Change |
|---|---|
| 2026-11-07 | Created from the persona, the learning system's private trackers, the LeetCode weakness tracker, the clarifications log, the driver-lab handoff, and the learning plan |
