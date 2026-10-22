2026_10_21_22_40-(Driver-Verifier-And-ETW)

# Lecture 004 — Tracing and Verification: Driver Verifier, and ETW Traces with WPR and WPA

> **For:** Timothy · **Date:** 2026-10-21
> **Prerequisites:** 001–003. The mechanisms behind what Verifier checks are in 005 (IRQL, paging) and 006 (IRPs).
> **Why this lecture:** dumps show one moment. Two tools show more. **Driver Verifier** makes a driver's latent bugs crash *immediately and at the scene*, instead of randomly later. **ETW tracing** records *what happened over time*: interrupts, DPCs, context switches, I/O, power, and a driver's own events. Between them they turn "1-in-1,000-units, somewhere" into "this function, this line, every time."

---

## Core ideas (the answer key)

1. **Driver Verifier makes the kernel check specific drivers strictly**, turning a broken rule into an immediate bugcheck (usually 0xC4, with P1 naming the rule) at the moment of the violation. It moves the crash from the victim to the culprit.
2. **Verify few drivers, deliberately, then turn it off.** `verifier /standard /driver x.sys`, reboot, reproduce, analyze, `verifier /reset`. It slows the verified drivers, and on a boot-critical driver it can make the machine unbootable, so use `/bootmode resetonbootfail` as a safety net.
3. **The standard options map to bug classes:** Special Pool → buffer overruns and use-after-free; Force IRQL Checking → paging at high IRQL (it forces pageable memory out, so 0xD1 bugs fire every time); Pool Tracking → leaks; I/O Verification → IRP misuse; Deadlock Detection → lock-order violations; DDI compliance → API rule violations.
4. **ETW has four roles:** *providers* emit events (the kernel, drivers, apps); *sessions* buffer them; *controllers* start and stop sessions (WPR); *consumers* read them (WPA). Events are cheap when enabled, and nearly free when not.
5. **WPR records with profiles.** `wpr -start GeneralProfile` (memory mode, a circular buffer that keeps the last minutes, ideal for "catch it after it happens") or `-filemode` (everything, for long captures); then `wpr -stop trace.etl`. Boot problems use `-boottrace -addboot`.
6. **WPA reads traces as graphs and tables you slice.** The key views for drivers: **DPC/ISR duration by module** (who eats time at high IRQL → 0x133), **CPU Usage (Precise)** (who ran, who waited on what), **Generic Events** (a driver's own provider events), plus device I/O and power views. Load symbols to see stacks.
7. **Verifier finds rule violations; ETW finds timing and sequence problems.** Use Verifier when you suspect corruption, IRQL or IRP misuse. Use ETW when the question is "what took so long", "what happened before it stopped", or "do interrupts still arrive?"

---

## Table of Contents

- [Part A — Driver Verifier](#part-a--driver-verifier)
  - [A1. What it is and how it works](#a1-what-it-is-and-how-it-works)
  - [A2. The standard options and what each catches](#a2-the-standard-options-and-what-each-catches)
  - [A3. Commands and a safe workflow](#a3-commands-and-a-safe-workflow)
  - [A4. Reading a Verifier crash](#a4-reading-a-verifier-crash)
- [Part B — ETW, WPR, WPA](#part-b--etw-wpr-wpa)
  - [B1. ETW's architecture](#b1-etws-architecture)
  - [B2. Recording with WPR](#b2-recording-with-wpr)
  - [B3. Reading with WPA](#b3-reading-with-wpa)
  - [B4. Recipes](#b4-recipes)
  - [B5. A custom profile for your driver](#b5-a-custom-profile-for-your-driver)
- [C. Choosing between them](#c-choosing-between-them)
- [D. Lab](#d-lab)
- [E. Misconceptions](#e-misconceptions)
- [F. Saying it precisely](#f-saying-it-precisely)
- [G. Self-check](#g-self-check)
- [Sources](#sources)

---

# Part A — Driver Verifier

## A1. What it is and how it works 🟢

Driver Verifier is built into Windows (`verifier.exe` plus support inside the kernel). When you name a driver, the kernel **intercepts that driver's calls to kernel functions** and its memory allocations, adding checks and stress around them:
- When the driver allocates memory, Verifier can place the allocation so that one byte past the end is an unmapped page.
- When the driver raises IRQL or takes a spin lock, Verifier can push the driver's pageable memory out first.
- When the driver handles IRPs, Verifier checks it follows the IRP rules.

Why this helps: without Verifier, many driver bugs are **latent**. A buffer overrun scribbles on a neighbor's memory, and the crash comes minutes later in someone else's code. Pageable memory touched at DISPATCH_LEVEL only crashes when that page happens to be on disk. Verifier removes the luck: **the first violation crashes, inside the guilty driver.**

Verifier is a standard tool in driver development and hardware certification. The HLK test suite runs drivers with Verifier on.

## A2. The standard options and what each catches 🟢

`/standard` enables the set Microsoft calls standard: "Special Pool, Force IRQL Checking, Pool Tracking, I/O Verification, Deadlock Detection, DMA Verification, and WDF Verification," plus "Security Checks, Miscellaneous Checks and DDI compliance checking."

| Option | How it works | Bug class it catches | Typical resulting stop |
|---|---|---|---|
| **Special Pool** | Puts each allocation at the end of a page, next to an unmapped guard page; freed memory is kept inaccessible for a while | Buffer overruns, use-after-free | 0xD6 (access beyond the end of an allocation), 0xC1 (corruption detected), 0x50 |
| **Force IRQL Checking** | When the driver raises IRQL to DISPATCH_LEVEL or above, or acquires a spin lock, pageable memory is trimmed out of RAM first | Touching pageable code or data at high IRQL: *every time*, not by luck | 0xD1 / 0xA, or 0xC4 |
| **Pool Tracking** | Records every allocation by the driver | Memory leaks (allocations not freed when the driver unloads) | 0xC4 at unload |
| **I/O Verification** | Checks IRP handling rules | Completing an IRP twice, freeing one still in use, wrong status, bad parameters | 0xC9 (DRIVER_VERIFIER_IOMANAGER_VIOLATION) / 0xC4 |
| **Deadlock Detection** | Tracks the order in which locks are taken | Lock-order inversions that *could* deadlock, even if they haven't yet | 0xC4 |
| **DMA Verification** | Checks use of DMA APIs | DMA misuse | 0xE6 (DRIVER_VERIFIER_DMA_VIOLATION) |
| **WDF Verification** | KMDF/UMDF framework checks | Framework rule violations (wrong IRQL for a WDF call, a request never completed…) | 0x10D (WDF_VIOLATION) |
| **DDI compliance checking** | Checks calls against rules for kernel API usage | Calling a function at the wrong IRQL, unbalanced acquire/release | 0xC4 (P1 = rule ID) |

Non-standard options worth knowing: **Randomized low-resources simulation** (allocations fail at random, to test error paths), and **Force pending I/O requests**.

## A3. Commands and a safe workflow 🟢

```
verifier /standard /driver mydriver.sys     ← standard checks on one driver (after next boot)
verifier /querysettings                     ← what will be verified after the next boot
verifier /query                             ← what is being verified now, and statistics
verifier /reset                             ← turn everything off (after next boot)
verifier /bootmode resetonbootfail          ← safety net: if boot fails, Verifier disables itself
verifier                                    ← with no arguments: opens the graphical Driver Verifier Manager
```

**Workflow:**
1. **Choose** one or two suspect drivers, not `/all`. Every verified driver runs slower, and verifying everything changes timing so much that some bugs hide, and the machine crawls.
2. **Enable a safety net** if the driver loads at boot: `verifier /bootmode resetonbootfail`.
3. **Enable** `/standard` on the suspect driver(s). Reboot.
4. **Reproduce** the scenario: the resume cycle, the idle period, the stress test.
5. **Analyze** the resulting dump: `!analyze -v`. With Verifier on, the stack points much closer to the root cause. `!verifier` in WinDbg shows Verifier's state and statistics.
6. **Reset** with `verifier /reset` and reboot. Don't leave Verifier on by accident.

**Pause and predict:** you suspect a driver touches paged pool in its DPC, but in a week of testing it has crashed only twice. Which single Verifier option makes it reproducible, and why?

<details><summary>Answer</summary>Force IRQL Checking. Every time the driver raises to DISPATCH_LEVEL or takes a spin lock, its pageable memory is pushed out first, so the illegal access faults every time instead of only when the page happens to be on disk.</details>

## A4. Reading a Verifier crash 🔵

- **0xC4 DRIVER_VERIFIER_DETECTED_VIOLATION:** P1 is a code identifying *which rule*. `!analyze -v` translates it into a sentence (for example "A driver has called a function at an IRQL that is too high"). The other parameters are rule-specific: often the address of the offending object, and the IRQL.
- **0xD6 / 0xC1:** Special Pool caught an overrun or corruption. The faulting instruction is the overrun itself.
- **0x10D WDF_VIOLATION:** a KMDF rule. `!wdfkd.wdflogdump <driver>` shows the framework's own explanation in its log.

The habit: after a Verifier crash, the stack's top driver frame is very likely the guilty line, unlike an unverified crash, where it might be a victim.

---

# Part B — ETW, WPR, WPA

## B1. ETW's architecture 🟢

**ETW** (Event Tracing for Windows) is Windows' built-in, high-speed logging system, used by the kernel and by drivers and applications. It has four roles:

| Role | What it is | Examples |
|---|---|---|
| **Provider** | Code that *emits* events, identified by a GUID or name. Each event has an ID, level and keywords, so you can enable subsets | The kernel's system providers (context switches, interrupts, DPCs, disk I/O, page faults, power), driver providers (WPP, TraceLogging, manifest-based), app providers |
| **Session** | A set of in-memory buffers that collect events from the providers enabled on it, and optionally write them to an `.etl` file | One WPR recording = one or more sessions |
| **Controller** | Starts and stops sessions and chooses which providers are enabled | **WPR** (Windows Performance Recorder), `xperf`, `logman`, `tracelog` |
| **Consumer** | Reads events, live or from `.etl` files | **WPA** (Windows Performance Analyzer), `tracerpt`, TraceView |

Why it's suitable for drivers and high IRQL: emitting an event writes into a per-processor buffer, which is safe and fast even at DISPATCH_LEVEL and above. When nobody has enabled a provider, its event calls cost almost nothing, so drivers can leave tracing compiled in permanently.

**Driver-side tracing styles** (🔵): WPP software tracing (classic, with format strings stored in the PDB), TraceLogging (self-describing events), and manifest-based events. KMDF drivers also have the **in-flight recorder** (IFR), a small always-on log per driver that ends up in dumps and is read with `!wdfkd.wdflogdump`.

## B2. Recording with WPR 🟢

WPR is the controller you'll use most. It's part of the **Windows Performance Toolkit** (in the Windows ADK); a basic version is built into Windows (`wpr.exe`). The graphical WPR UI does the same thing.

### Profiles

A **profile** is a named recipe: which providers, at which level, with what buffers. List the built-in ones with:

```
wpr -profiles
```

Commonly used built-in profiles include `GeneralProfile` (a good first pass: CPU, disk, file I/O and more), `CPU`, `DiskIO` and `FileIO`. There are also more specialized ones (power, GPU, and others). Run `-profiles` on your build to see the exact list. Each comes in `.verbose` (default) or `.light`.

### Two logging modes

| Mode | How | When |
|---|---|---|
| **Memory (default)** | Circular in-memory buffers; old events are overwritten | "Catch it after it happens": run for hours, then save the last few minutes as soon as the problem occurs |
| **File** (`-filemode`) | Writes continuously to disk; grows until stopped (or the disk fills) | Bounded scenarios where you need everything from start to finish |

### Commands

```
wpr -start GeneralProfile                    ← start (memory mode)
wpr -start CPU -start DiskIO -filemode       ← several profiles, file mode
wpr -status                                  ← is a recording running? dropped events?
wpr -stop C:\traces\touch_dead.etl "touch stopped after resume"   ← stop, save, with a description
wpr -cancel                                  ← stop and discard
```

**Boot and resume problems** happen before you can log in and start a recording. WPR can register a recording that starts during the next boot:

```
wpr -boottrace -addboot GeneralProfile       ← armed; starts automatically on the next boot
(reboot, reproduce)
wpr -boottrace -stopboot C:\traces\boot.etl "slow boot"
```

Keep traces short and focused: a few minutes of verbose kernel tracing can be hundreds of megabytes.

## B3. Reading with WPA 🟢

Open the `.etl` in WPA. The window is built from **graphs** that you drag in from the **Graph Explorer** (left side), each with a linked **table**. Three skills cover most work:

1. **Load symbols** (Trace → Configure Symbol Paths, then Load Symbols), so stack columns show function names. It's the same symbol server as WinDbg.
2. **Group and sort.** Each table has a gold bar: columns to the *left* of it are grouping keys; columns to the right are aggregated. Dragging *Module* to the left of the gold bar and sorting by duration answers "which driver took the most time?"
3. **Zoom to the moment.** Select a time range in any graph and zoom; every graph follows. Find the moment the problem starts, and look at what *every* graph shows there.

**The views that matter for driver work:**

| Graph (Graph Explorer → section) | Question it answers |
|---|---|
| **DPC/ISR** (Computation) | Which modules' ISRs and DPCs ran, how often, and how long each took. Sort by duration → 0x133 suspects; sort by count → interrupt storms |
| **CPU Usage (Precise)** (Computation) | From context switches: which thread ran when, and for a waiting thread, *who readied it* and how long it waited. The hang and latency workhorse |
| **CPU Usage (Sampled)** (Computation) | Where CPU time was spent by stack (sampled), for "what's this thread doing in a loop?" |
| **Generic Events** (System Activity) | Raw events from any provider, including your driver's own events: the sequence of what the driver logged |
| **Device I/O / Disk Usage** (Storage, System Activity) | I/O requests and their durations |
| Power-related graphs (when the profile captured them) | Device power state changes, idle states; used with lecture 007 |

## B4. Recipes 🟢

**Recipe 1: Who's eating time at high IRQL? (0x133 risk, audio glitches, laggy touch)**
1. Record `wpr -start CPU` (or GeneralProfile) while reproducing, then stop.
2. WPA → DPC/ISR graph → table.
3. Group by **Type** (DPC / ISR) and **Module**; sort by max duration, and separately by count.
4. Long maximum duration → a single slow routine (0x133 P1 = 0 territory). Huge count → a storm (P1 = 1 territory).

**Recipe 2: Is the device still interrupting? (dead touchscreen)**
1. Record while touching the screen, before and after the failure if possible.
2. DPC/ISR table, filtered to the GPIO controller's and the touch driver's modules.
3. Interrupts stop entirely after time T → the device or the line stopped (check the logic analyzer). Interrupts continue but no input reaches apps → look at the driver's Generic Events and the I/O.

**Recipe 3: Why is this thread stuck? (partial hang)**
1. CPU Usage (Precise) → find the thread → look at the waits: *Readying Thread* and *Waits* columns.
2. If it was never readied, follow what it waited on: an event, an I/O… This is the trace version of the `!thread` wait chain.

## B5. A custom profile for your driver 🔵

To capture your own driver's provider, write a `.wprp` profile file. A minimal one:

```xml
<?xml version="1.0" encoding="utf-8"?>
<WindowsPerformanceRecorder Version="1.0">
  <Profiles>
    <EventCollector Id="EC_Driver" Name="Driver Event Collector">
      <BufferSize Value="64"/>
      <Buffers Value="32"/>
    </EventCollector>

    <!-- Name = your provider's GUID (or registered name) -->
    <EventProvider Id="EP_MyDriver" Name="11111111-2222-3333-4444-555555555555"/>

    <!-- Id convention: <Name>.<DetailLevel>.<LoggingMode> -->
    <Profile Id="MyDriver.Verbose.File" Name="MyDriver" Description="My driver's events"
             LoggingMode="File" DetailLevel="Verbose">
      <Collectors>
        <EventCollectorId Value="EC_Driver">
          <EventProviders>
            <EventProviderId Value="EP_MyDriver"/>
          </EventProviders>
        </EventCollectorId>
      </Collectors>
    </Profile>
  </Profiles>
</WindowsPerformanceRecorder>
```

Use it with `wpr -start mydriver.wprp!MyDriver -filemode`, and combine it with a built-in profile (`-start GeneralProfile`) so your driver's events line up against the kernel's in the same timeline. This profile only defines a File-mode variant. Add a matching `.Verbose.Memory` profile if you want memory mode. Verify the schema against the WPR authoring documentation before relying on it.

---

## C. Choosing between them 🟢

| Situation | Tool |
|---|---|
| Random crashes in different places; suspect memory corruption | **Verifier** (Special Pool) |
| Rare 0xD1 | **Verifier** (Force IRQL Checking) |
| Leak suspected (memory grows, especially across unload) | **Verifier** (Pool Tracking), plus pool tag tracing |
| 0x133, audio dropouts, laggy input | **ETW** (DPC/ISR) |
| Partial hang, slow resume, slow boot | **ETW** (CPU Usage Precise; boot trace) |
| Dead device: does it still interrupt? | **ETW** (DPC/ISR) + logic analyzer |
| 0x9F during resume | Dump first (002); then **Verifier** on the holding driver, and an **ETW** trace of resume |

---

## D. Lab

1. **Verifier:**
   - `verifier /bootmode resetonbootfail`, then `verifier /standard /driver myfault.sys` (NotMyFault's driver), and reboot.
   - Run NotMyFault's **buffer overflow** option. Predict which stop code you'll get with Verifier on, versus without. Compare the two dumps' stacks.
   - `verifier /reset`, then reboot.
2. **WPR/WPA:**
   - `wpr -start GeneralProfile`. Open a few apps, copy a large file, then `wpr -stop lab.etl "lab"`.
   - In WPA: load symbols, open the DPC/ISR graph, and group by module. Which module has the longest single DPC? The most ISRs?
3. **Boot trace** (optional): `wpr -boottrace -addboot GeneralProfile`, reboot, log in, then `wpr -boottrace -stopboot boot.etl "boot"`. Find the boot phases in WPA's timeline.

---

## E. Misconceptions

| You might think | Reality | Why it matters |
|---|---|---|
| Verifier fixes or prevents bugs | It makes them crash earlier and closer to the cause | Expect *more* crashes with it on, and that's the point |
| Verify `/all` to be thorough | It slows everything and changes timing; target suspects | Focused verification finds bugs faster |
| A Verifier crash blames a random driver | With Verifier on, the top driver frame is usually the real culprit | Trust its stack more than an unverified one |
| Tracing is too slow for interrupt-level code | ETW writes per-processor buffers, safe and cheap at high IRQL; disabled providers cost almost nothing | Drivers should ship with tracing built in |
| You must start a trace before a rare problem and record forever | Memory mode keeps a rolling window; stop it right after the problem | Leave it running on test machines |
| WPA shows "the answer" | It shows events; you group, sort and zoom to ask questions | The skill is asking a question per view |

---

## F. Saying it precisely

- "Driver Verifier moves the crash to the culprit. Force IRQL Checking pushes pageable memory out whenever the driver raises IRQL, so a rare 0xD1 becomes deterministic, and Special Pool catches overruns at the exact instruction."
- "I verify one or two suspect drivers, with `resetonbootfail` as a safety net, and reset it afterward."
- "For timing problems I record with WPR, in memory mode so I can save right after it happens, and in WPA I group the DPC/ISR table by module: long durations point to 0x133 P1 = 0 suspects, high counts to storms."
- "For a dead device, ETW tells me whether interrupts are still arriving, which splits 'the device or line stopped' from 'the driver stopped processing'."

---

## G. Self-check

1. What does Driver Verifier change about *when* and *where* a bug crashes?
<details><summary>Answer</summary>It crashes at the first violation, inside the guilty driver, instead of later in a victim, or only when luck aligns.</details>

2. How does Force IRQL Checking make a rare 0xD1 reproducible?
<details><summary>Answer</summary>Whenever the driver raises IRQL to ≥ DISPATCH or takes a spin lock, Verifier trims pageable memory out first, so any pageable access at high IRQL faults every time.</details>

3. How does Special Pool catch an overrun at the exact instruction?
<details><summary>Answer</summary>Allocations are placed at the end of a page next to an unmapped guard page, so the first byte past the end faults immediately.</details>

4. Give the full safe workflow, with commands.
<details><summary>Answer</summary><code>verifier /bootmode resetonbootfail</code>; <code>verifier /standard /driver x.sys</code>; reboot; reproduce; analyze the dump (<code>!analyze -v</code>, <code>!verifier</code>); <code>verifier /reset</code>; reboot.</details>

5. Name the four ETW roles, with one example each.
<details><summary>Answer</summary>Provider (the kernel's interrupt/DPC events, a driver's TraceLogging), session (WPR's buffers), controller (WPR), consumer (WPA).</details>

6. Memory mode vs file mode: when do you use each?
<details><summary>Answer</summary>Memory (circular) to catch a rare problem and save the last minutes after it happens. File for bounded scenarios where you need everything.</details>

7. How do you trace a problem that happens during boot?
<details><summary>Answer</summary><code>wpr -boottrace -addboot &lt;profile&gt;</code>, reboot and reproduce, then <code>wpr -boottrace -stopboot file.etl "desc"</code>.</details>

8. In WPA, what does the gold bar do?
<details><summary>Answer</summary>Columns left of it are grouping keys; columns right of it are aggregated. That's how you get per-module totals.</details>

9. Which WPA view and sort tells you a driver's DPC risks 0x133, and what distinguishes a slow DPC from a storm?
<details><summary>Answer</summary>The DPC/ISR table grouped by module. A large max duration means a slow routine; a huge count means a storm.</details>

10. A touchscreen is dead. Which trace observation tells you the device or line stopped, versus the driver stopped processing?
<details><summary>Answer</summary>No ISRs at all for the touch interrupt after the failure → the device or line stopped (or the interrupt was lost). ISRs still occur but no input reaches apps → the driver or upper layers stopped processing.</details>

---

## Sources

Checked 2026-10-21.

- Microsoft Learn: Driver Verifier command syntax (Windows 11 block: `/standard`, `/flags`, `/query`, `/querysettings`, `/reset`, `/bootmode`, `/volatile`, `/rules`; the list of standard options). https://learn.microsoft.com/windows-hardware/drivers/devtest/verifier-command-line
- Microsoft Learn: WPR command-line options (`-profiles`, `-start`, `-filemode`, `-stop`, `-cancel`, `-status`, `-boottrace -addboot / -stopboot`). https://learn.microsoft.com/windows-hardware/test/wpt/wpr-command-line-options
- Microsoft Learn: Bug Check 0x133 (event tracing for the cumulative form), 0xC4, 0x10D reference pages.
- Microsoft Learn: Windows Performance Analyzer documentation (Graph Explorer, the gold bar, symbol loading); WPR recording-profile authoring documentation (`.wprp` schema).

The `.wprp` sample was written from the documented schema and the profile-Id naming convention. It wasn't run here, so test it on your machine first.
