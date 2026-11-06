# Learning Plan: what to study next, and how to choose

> **For:** Timothy · **Created:** 2026-11-06 · **Revise:** monthly, or when the target role changes
> **Lives at:** `learning_system/learning_plan.md`
> **What this is:** the one place that answers "what should I study now, and why that and not something else?" It sits above the per-domain plans (`lectures/leetcode/000-gradient_roadmap.md`, `lectures/system_design/001…`, `lectures/windows_internals/000-roadmap.md`, `lectures/clarifications/log.md`). They decide *how* to study a topic; this file decides *which topic gets your hours*.
> **For AI assistants:** when Timothy asks "what's the gradient today?" or "what should I work on?", read this file, then `private/reading_status.md`, `private/understanding/`, and `lectures/leetcode/private/000-weakness_tracker.md`, then answer with **one** recommendation using §3's scoring.

---

## Core ideas

1. **You don't need to know the exact job.** The roles you're most likely to get all share one core skill set (Ring 1, §1). Team-specific knowledge (Ring 2) gets learned on the job, and nobody expects you to have it beforehand.
2. **Understanding is the main thing interviews test.** Open source and projects are evidence and stories. They support the understanding; they don't replace it.
3. **Right now your bottleneck is retention, not coverage.** Most Ring 1 topics already have a lecture, but most of those lectures are unread or recalled at 20–40%. The steepest part of the gradient is reading, recalling, and doing labs, not generating new material.
4. **Score candidates; don't trust the feeling of "so much to do."** Value ≈ P(needed) × gap × how much it unlocks ÷ cost (§3). Measure the gap from evidence (recall scores, tracker status), not from how a topic feels.
5. **The driver lab is both learning and a story.** For platform roles, "I wrote a kernel driver, crashed it on purpose, and analyzed the dump in WinDbg" is a stronger interview story than most open-source PRs.
6. **Generation budget:** at most 1–2 new lectures a week, and only when an attempt, recall, or talk-through exposes a specific gap.

---

## 1. The target: three rings

```
 Ring 0  Any software role       coding interview (DS&A, Python) · design method · explaining your own work
 Ring 1  Systems / platform      OS fundamentals · concurrency · interrupts & drivers · debugging · performance & power
 Ring 2  The specific team       their tools, their hardware, their codebase   ← learned on the job
```

Your background (firmware → Linux → .NET, P/Invoke, I2C) makes you a strong match for Ring 1 roles: Windows platform, devices, validation and reliability, drivers, and edge or IoT. Those roles also give you the best interview conversations. **Ring 0 + Ring 1 is the plan.** Ring 2 shows up after an offer, when the team is known.

What Ring 1 contains, concretely:

| Topic | One-line "done means" |
|---|---|
| Processes, threads, syscalls, scheduling | Trace a syscall and a context switch aloud, naming every step |
| Virtual memory and paging | Walk a virtual address to physical; say what a page fault does and when paging is forbidden |
| Synchronization | Explain a race, a lock, a deadlock, spinlock vs mutex, and producer/consumer on shared memory |
| Async and the thread pool (.NET) | Say what an `await` saves and where the thread goes during I/O |
| Hardware map (SoC, physical addresses, MMIO) | Say how a load reaches DRAM vs a device register |
| Interrupts, IRQL, ISR → DPC → work item | Place each piece of work in the context that's allowed to do it, and say why |
| Device stacks, PnP, what a driver is | Trace `DeviceIoControl` to your driver and back |
| Debugging (WinDbg, dumps, Verifier, ETW/WPA) | Analyze a dump you caused yourself |
| Performance and power | Tell running from waiting in a trace; explain why idle wake-ups drain battery |

---

## 2. The scoreboard (current state, 2026-11-06)

Statuses come from `private/reading_status.md`. 📄 = generated, not read · 📖 = read · 🗣️ = recalled (score).

| Ring 1 topic | Material that exists | Status | Next action |
|---|---|---|---|
| Processes, threads, syscalls | `concurrency/002`, `windows_internals/008` | 📄 📄 | Read `concurrency/002`, then recall on a walk |
| Virtual memory | `firmware/003` §memory, `windows_internals/008` | 🗣️ ~22% | Clarification lecture for G2 (`clarifications/log.md`), then recall |
| Synchronization | Part of `windows_internals/008` (mutex/event/semaphore) | **Gap: no dedicated lecture** | The one new lecture worth writing (see §4) |
| Async, thread pool | `concurrency/001`, `003` | 📄 📄 | Read `003` (it has a lab you can run) |
| Hardware map | `clarifications` G1–G2 queue | open | Ask for the G1–G2 clarification lecture |
| Interrupts and deferred work | `firmware/003`, `windows_internals/005`, `014` | 🗣️ ~22–25%, recall overdue since 10-23 | Recall `firmware/003`, then read `014` |
| Drivers and device stacks | `windows_internals/006`, `009`, lab phases 0–4 ✅ | 📖 started | Finish `009` |
| Debugging | `windows_internals/001–004`, `013` | 📄, lab phase 5 next | **Lab phase 5** (crash, dump, Verifier) |
| Performance and power | `windows_internals/007`, `015`, `016` | 📄 | Later; read `015` after the lab |
| Coding (Ring 0) | `leetcode/` gradient + tracker + practice queue | Active | Keep the one-problem loop (`problem_deep_dives/`) |
| Design (Ring 0) | `system_design/001` + `practice/` | 📄 | One timed, spoken attempt per week, graded with `practice/rubric.md` |

**What the board says:** nearly every row already has material. The column that's empty is "read, recalled, labbed." That's where the hours should go.

---

## 3. The gradient: how to choose

For each candidate task, estimate:

| Factor | Question | Low (1) | High (3) |
|---|---|---|---|
| **P(needed)** | How likely is this to come up in interviews or in the first months of the job? | Niche | Asked in almost every systems loop |
| **Gap** | What does the evidence say about your current understanding? | Recalled ≥70% | Never explained back, or recalled <30% |
| **Unlocks** | How many other topics get easier once you have this? | A leaf | A root (e.g. the hardware map, threads) |
| **Cost** | Hours until "done means" is met | Material and lab already exist | Needs new material and new setup |

**Score = P × Gap × Unlocks ÷ Cost.** Do the highest score. Ties go to whatever has built-in feedback (a recall, a lab, a timed attempt), because that's what makes learning stick.

Scores as of today:

| Candidate | P | Gap | Unlocks | Cost | Score |
|---|---|---|---|---|---|
| Recall `firmware/003` (interrupts, memory) on a walk | 3 | 3 | 3 | 1 | **27** |
| Read + recall `concurrency/002` (threads, syscalls) | 3 | 3 | 3 | 1 | **27** |
| New synchronization lecture + its drills | 3 | 3 | 3 | 2 | **13.5** |
| Timed spoken design attempt | 3 | 2 | 2 | 1 | **12** |
| Driver lab phase 5 (crash, dump, Verifier) | 3 | 3 | 2 | 2 | **9** |
| G1–G2 clarification lecture (hardware map, addresses) | 2 | 3 | 3 | 2 | **9** |
| One LeetCode problem through the deep-dive loop | 3 | 2 | 1 | 1 | **6** (daily, so it adds up) |
| Finish the dotnet/iot binding PR | 1 | 1 | 1 | 2 | **0.5** |
| New domains (LLM orchestration, emulation, a new OSS repo) | 1 | — | 1 | 3 | **≈0, parked** |

Rescore whenever a recall check or attempt changes the evidence. The numbers are rough; the ranking is what matters.

---

## 4. The weekly shape

Assume weekdays are short and weekends hold the long blocks. Adjust the hours; keep the proportions.

| When | What | Why it's here |
|---|---|---|
| **Walks** | One recall check: explain a lecture you've read aloud (Mode C), or a talk-through (Mode D) | Retention is the bottleneck, and walks are free hours |
| **Weekday evening, ~30–45 min** | One LeetCode problem, or one lecture section read and then explained with the file closed | Small, daily, feedback built in |
| **Weekend block 1 (~2 h)** | Lab: driver lab phase 5, then the `concurrency/003` lab | Hands-on, and it produces stories |
| **Weekend block 2 (~1–2 h)** | One timed design attempt (spoken, 35 min, rubric) + 1–2 LeetCode problems | Ring 0 practice under realistic conditions |
| **Once a week, 15 min** | Rescore §3 and pick next week's top two | Keeps the gradient honest |

**Rules:**
- **Generation budget:** 1–2 new lectures a week, each triggered by a gap you've seen. The synchronization lecture is the next one to write.
- **One build or contribution thread at a time.** Right now that's the driver lab. Open source is paused at "finish what's open," not "start something new."
- **Something is done when you can explain it aloud and you've done its lab.** Having the file doesn't count.

---

## 5. Two modes

**Interview-active (a round is scheduled within about 2 weeks):**
- Stop all new material except a gap exposed by the last round.
- Spend hours on recall of the Ring 1 rows most likely to come up, 2-minute versions of your stories (work experience, P/Invoke + pigpio, the driver lab, the qualification-script crash), and one timed design attempt every 2–3 days.
- For coding-style prompts, start by writing one example call with its exact output.

**Building (no round soon, or after an offer):**
- Follow §3 and §4 as written.
- Go deeper on Ring 1 (performance, power, Verifier, ETW) and add Ring 2 once the team is known.
- Pick up open source again, ideally at the hardware/OS boundary (a dotnet/iot binding, or a Windows performance-tooling repo from `windows_internals/017`), so it produces stories that match the role.

---

## 6. Where open source fits

- **In interviews,** depth of understanding decides most rounds. Open source helps in two places: résumé screening, and "tell me about something you built." You already have YARP and dotnet/iot work for that.
- **For platform roles,** the driver lab is the better story right now. You built a kernel driver, loaded it, called it from user mode, and will crash it and analyze the dump. That's exactly the job.
- **When it comes back:** one repo at a time, chosen because it makes you practise Ring 1 skills.

---

## 7. How to use this file

1. When unsure what to do, check today's slot in §4, then take the top-scoring item in §3.
2. When a recall check, lab, or interview round produces new evidence, update the §2 row and rescore §3.
3. Once a month (first rescore in early December), check the ratio of lectures generated to lectures recalled. If generation is outpacing recall, the budget in §4 isn't being kept.

## Changelog

| Date | Change |
|---|---|
| 2026-11-06 | Created: rings, scoreboard from reading status, scoring formula, weekly shape, two modes, open-source role |
