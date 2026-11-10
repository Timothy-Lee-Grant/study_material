# Lecture 016: Battery Life and Energy Efficiency: What Software Does to Power

> **For:** Timothy · **Date:** 2026-10-31
> **Prerequisites:** 005 (interrupts), 007 (S-states, D-states, Modern Standby, DRIPS), 015 (traces, threads running vs waiting).
> **Why this lecture:** on a laptop, performance and battery life are two sides of one question: what the CPU and devices are doing, and for how long. A program can be fast and still drain the battery by waking the CPU thousands of times a second, keeping a device powered, or running background work on the fastest core. This lecture builds the model (energy = power × time, idle states, wake-ups), then the tools Windows gives developers (QoS levels, EcoQoS, coalescable timers, device idle) and the tools for measuring (powercfg, the energy estimation engine, WPR power traces).
> **Format notes:** full problem statement; definitions before use; numbers in examples are illustrative unless a source is given. No firmware analogies (your firmware experience with sleep modes is real, but the lecture teaches the OS mechanisms directly).
> **Verification:** `code/016_ecoqos_and_timers.c` was compile-checked with MinGW-w64 against the Windows headers. API behavior is quoted from Microsoft's documentation (Sources).

---

## Core ideas (the answer key)

1. **Energy = power × time.** Battery capacity is energy (watt-hours). Battery life = capacity / average power. Small differences in **average** power, especially at idle, matter more than short spikes.
2. **Most of a laptop's life is spent idle.** Battery life is mostly decided by how low the platform's power gets when nothing is happening, and how often something interrupts that.
3. **Idle power depends on idle states.** A core that has nothing to do enters a **C-state** (deeper = less power, slower to wake). The whole chip reaches its lowest state only when **every** core and the relevant devices are idle at the same time. On Modern Standby systems the goal is **DRIPS** (lecture 007).
4. **Wake-ups are the enemy of idle.** Every timer expiry, interrupt, or polling loop pulls a core out of its idle state, and the exit, the work and the re-entry all cost energy. Ten thousand tiny wake-ups can cost more than one second of real work.
5. **Running faster costs disproportionately more power.** CPU dynamic power grows roughly with frequency × voltage², and higher frequencies need higher voltage. So the same work done at a lower frequency, or on an efficiency core, can take less energy, even though it takes longer.
6. **But finishing sooner lets everything else sleep sooner ("race to idle").** The best choice depends on whether the user is waiting: work the user is waiting for should finish fast; background work should run efficiently.
7. **Windows expresses this as QoS levels.** The scheduler and power manager assign each thread a level (High, Medium, Low, Utility, **Eco**, Media, Deadline) that decides frequency and which cores it can use. Apps can explicitly tag background work as **EcoQoS** with `SetProcessInformation` / `SetThreadInformation`.
8. **Replace polling with events, and let timers be late.** Wait on events/handles instead of checking in a loop; use coalescable timers (`SetWaitableTimerEx` with a tolerable delay) so Windows can batch wake-ups; avoid raising the system timer resolution (`timeBeginPeriod`) unless you need it.
9. **Drivers matter as much as apps.** A device that stays in D0 (fully on) when idle, or a driver that never lets its device idle, can keep the whole platform out of its lowest power state. KMDF gives drivers idle power-down with a timeout.
10. **Measure, don't guess:** `powercfg /batteryreport` (capacity and history), `/energy` (common problems), `/sleepstudy` (Modern Standby sessions and what kept them awake), `/srumutil` (per-app energy estimates from the energy estimation engine), and WPR traces with power events for detail.

---

## Table of Contents

- [0. The problem](#0-the-problem)
- [1. Energy, power, and battery life](#1-energy-power-and-battery-life)
- [2. Idle states and why wake-ups cost so much](#2-idle-states-and-why-wake-ups-cost-so-much)
- [3. Frequency, voltage, and efficiency cores](#3-frequency-voltage-and-efficiency-cores)
- [4. QoS levels and EcoQoS](#4-qos-levels-and-ecoqos)
- [5. Timers, polling, and timer resolution](#5-timers-polling-and-timer-resolution)
- [6. Devices and drivers](#6-devices-and-drivers)
- [7. Measuring energy](#7-measuring-energy)
- [8. Fixing the background sync agent](#8-fixing-the-background-sync-agent)
- [Common mistakes](#common-mistakes)
- [Self-check questions](#self-check-questions)
- [Sources](#sources)

---

## 0. The problem

**Investigate and fix: a background agent shortens battery life.**

A laptop normally lasts about 12 hours of light use. After installing a file-sync agent, it lasts about 9 hours, and the battery drains noticeably overnight in Modern Standby. The agent:
- checks a folder for changes every 10 ms in a loop (`while (1) { check(); Sleep(10); }`);
- calls `timeBeginPeriod(1)` at startup "so `Sleep(10)` is accurate";
- compresses and uploads changed files as soon as it sees them, on whatever thread is free;
- talks to a USB accessory through a driver that never powers the accessory down.

Explain, with the model in this lecture, why each behavior costs battery; say how you'd confirm it with measurements; and redesign the agent so it does the same job with much less energy.

---

## 1. Energy, power, and battery life

- **Power (watts)** is the rate of energy use at an instant.
- **Energy (watt-hours or joules)** is power accumulated over time: E = ∫ P dt, or average power × time.
- **Battery capacity** is energy. A 60 Wh battery at an average draw of 5 W lasts 12 h.

So the number that decides battery life is **average power**. A quick calculation shows why background behavior matters so much:

```
60 Wh battery, light use averages 5 W   → 12.0 h
+ 1.7 W extra from a misbehaving agent  → 60 / 6.7 = 9.0 h       (−25%)
```

1.7 W is small next to the 30 W a laptop chip can draw when busy, but it's paid **all the time**, while the busy peaks are brief. The same logic applies overnight in Modern Standby, where the whole system should average well under a watt: a background task that keeps waking the system can double or triple that.

---

## 2. Idle states and why wake-ups cost so much

When a core has nothing to run, the OS's idle loop puts it into an **idle state** (C-state):

| State (typical) | What's off | Power | Time to wake |
|---|---|---|---|
| C0 | nothing (running) | highest | 0 |
| C1 | clock stopped | lower | ~1 µs |
| deeper C-states | caches flushed, voltage reduced or removed | much lower | tens to hundreds of µs |

Deeper states save more power but take longer to enter and leave, and entering one is only worth it if the core will stay idle long enough. The OS predicts how long the core will stay idle (largely from the next timer due) and picks the state.

**The whole package** (shared caches, memory controller, fabric) can only go into its deepest state when **all** cores are idle at the same time and the devices allow it. On Modern Standby systems, the platform-wide lowest state is DRIPS (Deepest Runtime Idle Platform State, lecture 007). Time spent in DRIPS is what makes standby last for days.

**Why wake-ups cost more than they look.** Each wake-up pays: exiting the idle state, possibly raising frequency and voltage, refilling caches, doing the (tiny) work, then re-entering idle, during which the core is at higher power. And if the wake-up interval is shorter than the time needed to make a deep state worthwhile, the core never goes deep at all.

```
polling every 10 ms  →  100 wake-ups per second, per thread
each wake-up: maybe 50 µs of real work, but it costs a deep-idle exit + entry
and the core never stays idle long enough to reach the deepest states
```

This is why "it only uses 0.5% CPU" isn't proof a program is battery-friendly. **Wake-up frequency** and **what it keeps from sleeping** are what matter.

---

## 3. Frequency, voltage, and efficiency cores

**Dynamic power** in CMOS logic is approximately:

```
P_dynamic ≈ C × V² × f       (C: switched capacitance, V: voltage, f: clock frequency)
```

Higher frequency needs higher voltage to stay stable, so power rises **faster than linearly** with frequency. Running at half the frequency can need much less than half the power, so the energy for a fixed amount of work (power × time) can go **down** even though the time doubles. This is **DVFS** (dynamic voltage and frequency scaling): Windows' power manager picks performance states (P-states) for each core based on load and policy.

**Static power** (leakage) and the rest of the platform (screen, memory, SoC fabric) are paid as long as the system is awake. That creates the opposite pressure, **race to idle**: finish quickly and let everything sleep.

Which wins depends on the work:

| Work | Better choice | Why |
|---|---|---|
| User is waiting (opening a file, compressing a folder they asked for) | fast: high frequency, performance cores, all cores in parallel | responsiveness; the screen and platform are on anyway, so finishing sooner saves platform energy |
| Background, nobody waiting (indexing, sync, backups) | efficient: low frequency, efficiency cores | lower energy per unit of work; nobody notices the extra time |

**Heterogeneous CPUs.** Modern laptop chips (Arm and x86) combine **performance cores** (fast, power-hungry) and **efficiency cores** (slower, much more energy-efficient per instruction). Which cores a thread can use is decided by the scheduler, guided by the thread's QoS level.

This links to lecture 015: parallelizing the user's compression across all cores is right *because the user is waiting*. The same compression in a nightly background backup should be tagged EcoQoS instead.

---

## 4. QoS levels and EcoQoS

Windows classifies threads into **Quality of Service (QoS) levels** and uses them to choose frequency and cores. From Microsoft's documentation (accessed 2026-10-31):

| Level | Who gets it | Performance and power |
|---|---|---|
| **High** | foreground, in-focus or audible windowed apps; or explicitly tagged | standard high performance |
| **Medium** | visible but not in focus; also the foreground app after a period of user inactivity (on battery) | varies by platform, between High and Low |
| **Low** | windowed apps not visible or audible | on battery: most efficient frequency, efficient cores |
| **Utility** | background services (Windows 11 22H2+) | on battery: most efficient frequency, efficient cores |
| **Eco** | processes/threads **explicitly tagged** with `SetProcessInformation` / `SetThreadInformation` | **always** most efficient frequency, efficient cores |
| **Media** | threads tagged by the Multimedia Class Scheduler Service for batch buffering | reduced frequency for efficient batch processing |
| **Deadline** | audio threads tagged by MMCSS that must meet deadlines | high performance to meet deadlines |

Most levels are assigned automatically from what the user can see and hear. **Eco** is the one an app chooses explicitly, for work it knows is background:

```c
static BOOL SetEcoQoS(BOOL on)
{
    PROCESS_POWER_THROTTLING_STATE s;
    ZeroMemory(&s, sizeof s);
    s.Version     = PROCESS_POWER_THROTTLING_CURRENT_VERSION;
    s.ControlMask = PROCESS_POWER_THROTTLING_EXECUTION_SPEED;     /* "I am deciding this feature" */
    s.StateMask   = on ? PROCESS_POWER_THROTTLING_EXECUTION_SPEED /* set   -> EcoQoS             */
                       : 0;                                       /* clear -> HighQoS             */
    return SetProcessInformation(GetCurrentProcess(), ProcessPowerThrottling, &s, sizeof s);
}
```

- `ControlMask` says which features you're taking control of; `StateMask` says on or off for each.
- `ControlMask = 0` hands the decision back to Windows (the default behavior).
- The per-thread version is the same with `THREAD_POWER_THROTTLING_STATE`, `THREAD_POWER_THROTTLING_EXECUTION_SPEED`, `SetThreadInformation(GetCurrentThread(), ThreadPowerThrottling, ...)`. Use it when one process mixes foreground and background work: tag just the background worker threads.

**Testing note from the same documentation:** Windows may lower the foreground app to Medium QoS after a period without user input, on battery. Automated benchmarks have no user input, so this can skew battery benchmark results; the documented registry value `DisableUserPresenceQos` (under `HKLM\SYSTEM\CurrentControlSet\Control\Power\PowerThrottling`) turns it off for testing.

---

## 5. Timers, polling, and timer resolution

**Polling vs waiting.** `while (1) { check(); Sleep(10); }` wakes 100 times a second whether or not anything changed. An event-driven design wakes **only when something happens**:
- for files: `ReadDirectoryChangesW` (or `FindFirstChangeNotification`) and wait on the handle;
- for devices: a pending read that the driver completes when data arrives (lecture 014);
- for work queues: wait on an event or I/O completion port.

A thread blocked in `WaitForSingleObject` costs **nothing**: it isn't scheduled, and it doesn't hold any core awake.

**Coalescable timers.** When periodic work is genuinely needed, tell Windows how late it may be. `SetWaitableTimerEx` takes a **TolerableDelay** in milliseconds. A timer that can fire up to a second late can be batched with other wake-ups, so the CPU wakes once for several timers instead of once for each. From `code/016_ecoqos_and_timers.c`:

```c
HANDLE timer = CreateWaitableTimerExW(NULL, NULL, 0, TIMER_ALL_ACCESS);
LARGE_INTEGER due;
due.QuadPart = -10LL * 1000 * 1000 * 5;   /* first expiry 5 s from now (negative = relative, 100 ns units) */
SetWaitableTimerEx(timer, &due, 5000 /* period ms */, NULL, NULL, NULL, 1000 /* tolerable delay ms */);

for (;;) {
    WaitForSingleObject(timer, INFINITE);  /* blocked, not spinning: zero CPU */
    DoOneBatchOfBackgroundWork();
}
```

**Timer resolution.** Windows' clock interrupt normally ticks about every 15.6 ms. `timeBeginPeriod(1)` asks for a 1 ms tick so short sleeps are more accurate. Microsoft's documentation says: "High resolutions can also prevent the CPU power management system from entering power-saving modes." Since Windows 10 version 2004 the request affects only the calling process, and since Windows 11, Windows doesn't guarantee the higher resolution for a window-owning process that's minimized, fully covered, or otherwise invisible and inaudible. Still, the rule is: **don't raise timer resolution for background work.** If `Sleep(10)` lands at 15 ms, that's fine for a sync agent.

---

## 6. Devices and drivers

The CPU is only part of the platform. Radios, USB controllers, storage and accessories have their own power states, and **the platform can't reach its lowest state while a device that blocks it is active.**

- **D-states** (lecture 007): D0 is fully on; D3 is off (D3hot: still powered enough to be enumerated; D3cold: power removed). An idle device should leave D0.
- **Idle power-down in KMDF.** A driver can let the framework power the device down after a period with no I/O:

  ```c
  WDF_DEVICE_POWER_POLICY_IDLE_SETTINGS idle;
  WDF_DEVICE_POWER_POLICY_IDLE_SETTINGS_INIT(&idle, IdleCannotWakeFromS0);
  idle.IdleTimeout = 2000;                         /* ms without I/O before powering down */
  WdfDeviceAssignS0IdleSettings(device, &idle);    /* in EvtDriverDeviceAdd */
  ```

  When I/O arrives, the framework brings the device back to D0 (calling `EvtDeviceD0Entry`) before delivering the request. If the device must be able to signal while idle (like the "data ready" line in lecture 014), use `IdleCanWakeFromS0` so it can wake itself.
- **A driver that never idles** (no idle settings, or that keeps a request pending in a way that holds the device in D0) shows up in sleep studies as a top offender, because it keeps the platform out of DRIPS.
- **USB selective suspend** is the same idea for USB devices: the hub can suspend a device's port when it's idle.

---

## 7. Measuring energy

Windows has built-in tools for each level of detail. Run them from an elevated prompt:

| Command | What it gives you |
|---|---|
| `powercfg /batteryreport` | HTML report: design vs full-charge capacity (battery wear), recent usage, battery life estimates |
| `powercfg /energy` | Observes the system for 60 s and reports common problems: processes that raised the timer resolution, devices not entering suspend, power-plan settings |
| `powercfg /sleepstudy` | Modern Standby sessions: how much time was spent in DRIPS, energy drained per session, and the **top offenders** (components and drivers that kept the system active) |
| `powercfg /srumutil` | Exports the System Resource Usage Monitor database, including the **Energy Estimation Engine (E3)** per-app energy estimates (`/srumutil` writes a CSV; check `powercfg /?` on your build for options) |

**E3** estimates each app's energy from usage counters (CPU time at each frequency, network and storage activity, display time) and a power model of the device, without a power meter. It's what Settings → Battery usage per app is built on. Estimates, not measurements, but good for "which app is it?".

**Traces for detail.** `wpr -start Power -start CPU` records power-management events alongside CPU data. In WPA you can see per-core idle-state residency and frequency over time, and match wake-ups to the threads and timers that caused them, using the same Precise (context-switch) data as lecture 015: a thread that becomes ready every 10 ms, readied by a timer, is a polling loop.

**Measurement hygiene:** on battery (not charging), screen brightness fixed, same workload, repeated runs, and remember the user-presence QoS note in §4. For real watts, use the platform's power meter or an external one; E3 numbers are model-based.

---

## 8. Fixing the background sync agent

Back to §0. Each behavior, why it costs energy, and how to see it:

| Behavior | Why it costs energy | How you'd see it |
|---|---|---|
| Polls every 10 ms | 100 wake-ups/s; cores never reach deep idle; blocks DRIPS in standby | Precise CPU data: the thread readied by a timer every ~10–15 ms; sleepstudy offender |
| `timeBeginPeriod(1)` | raises the tick rate; prevents power-saving modes | `powercfg /energy` lists the process under timer resolution |
| Compresses immediately on any thread | background work at High QoS runs on performance cores at high frequency | WPA: the agent's compression on performance cores at high frequency |
| Accessory never powers down | device stays in D0, platform can't reach its lowest state | sleepstudy names the device/driver; `powercfg /energy` reports devices not entering suspend |

**Redesign:**
1. **Event-driven change detection:** `ReadDirectoryChangesW` on the folder; the thread blocks until a change arrives.
2. **Batch the work:** collect changes and process them on a coalescable timer (e.g. every 30 s with 10 s tolerable delay), not instantly. Nobody needs a backup within 10 ms.
3. **Tag the worker as EcoQoS** (`SetThreadInformation` on the compression/upload thread): efficient cores, efficient frequency.
4. **Remove `timeBeginPeriod`.**
5. **Driver:** add S0 idle settings with a timeout so the accessory powers down; use wake-from-S0 if it must signal.
6. **In Modern Standby,** defer non-urgent work until the system is active (or the device is on AC power).
7. **Verify:** same overnight standby sleep study and same battery rundown, before and after.

The agent does the same job, but now it wakes when there's work, does it in batches on the efficient cores, and lets the platform sleep in between.

---

## Common mistakes

1. **Judging battery impact by CPU %.** A low-CPU program that wakes 1,000 times a second can be worse than a busy one that finishes and sleeps.
2. **Polling with short sleeps** instead of waiting on an event or handle.
3. **Raising the timer resolution** for convenience.
4. **Treating all work alike.** User-waiting work: fast and parallel. Background work: EcoQoS, batched, coalesced.
5. **Forgetting devices.** A driver without idle power management can cost more than any app.
6. **Benchmarking battery on AC power,** with changing brightness, or with automated input that triggers user-presence QoS changes.
7. **Treating E3 estimates as exact.** They're model-based; use them to find the culprit, then confirm with traces or a meter.

---

## Self-check questions

1. A 60 Wh laptop averages 5 W. A background app adds an average of 1 W. How many hours of battery does it cost?
<details><summary>Answer</summary>60/5 = 12 h before; 60/6 = 10 h after: 2 hours (about 17%).</details>

2. Why can a program at 0.5% CPU still hurt battery life a lot?
<details><summary>Answer</summary>Because frequent wake-ups (timers, polling) pull cores out of deep idle states over and over, each paying exit/entry costs, and keep the package and platform from reaching their lowest states (DRIPS in standby). Wake-up frequency, not CPU %, is what matters at idle.</details>

3. Explain why the same work can take less energy at a lower frequency, and give the opposite argument.
<details><summary>Answer</summary>Dynamic power ≈ C·V²·f, and higher f needs higher V, so power grows faster than frequency; at lower frequency the work takes longer but the energy (power × time) can be lower. Opposite argument (race to idle): static leakage and the rest of the platform consume power the whole time the system is awake, so finishing sooner and sleeping can save more. Which wins depends on the platform and whether the user is waiting.</details>

4. Which QoS level does an app choose explicitly, and what does it do? Write the key fields of the call.
<details><summary>Answer</summary>EcoQoS: always the most efficient frequency and efficient cores. `PROCESS_POWER_THROTTLING_STATE` with `Version = PROCESS_POWER_THROTTLING_CURRENT_VERSION`, `ControlMask = StateMask = PROCESS_POWER_THROTTLING_EXECUTION_SPEED`, passed to `SetProcessInformation(GetCurrentProcess(), ProcessPowerThrottling, ...)`. (Per thread: the THREAD_ versions with `SetThreadInformation`.)</details>

5. When should you **not** use EcoQoS?
<details><summary>Answer</summary>For work the user is actively waiting for (opening a file, an operation they started and are watching). It would make that work slower on purpose. Use it for background work such as indexing, sync, or scheduled backups.</details>

6. What does the TolerableDelay of `SetWaitableTimerEx` buy you?
<details><summary>Answer</summary>Permission for the timer to fire up to that many milliseconds late, so Windows can coalesce it with other wake-ups and keep the CPU idle longer, instead of waking separately for each timer.</details>

7. Name the powercfg command you'd use for each: (a) battery wear, (b) a process that raised timer resolution, (c) what kept a laptop awake overnight in standby, (d) per-app energy estimates.
<details><summary>Answer</summary>(a) `/batteryreport`, (b) `/energy`, (c) `/sleepstudy`, (d) `/srumutil` (the SRUM database with Energy Estimation Engine data).</details>

8. A USB accessory's driver has no idle power policy. What effect can that have on Modern Standby, and what's the KMDF fix?
<details><summary>Answer</summary>The device stays in D0, which can keep the platform from reaching DRIPS, so standby drains much faster; sleepstudy shows it as a top offender. Fix: `WDF_DEVICE_POWER_POLICY_IDLE_SETTINGS_INIT` + `IdleTimeout` + `WdfDeviceAssignS0IdleSettings` (with `IdleCanWakeFromS0` if the device must signal while idle).</details>

---

## Sources

- Microsoft Learn, [Quality of Service](https://learn.microsoft.com/en-us/windows/win32/procthread/quality-of-service) (QoS level table, EcoQoS APIs, `DisableUserPresenceQos`). Accessed 2026-10-31.
- Microsoft Learn, [SetProcessInformation](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-setprocessinformation) and [SetThreadInformation](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-setthreadinformation). Accessed 2026-10-31.
- Microsoft Learn, [timeBeginPeriod](https://learn.microsoft.com/en-us/windows/win32/api/timeapi/nf-timeapi-timebeginperiod) (power remark; per-process since 2004; Windows 11 occluded/minimized behavior). Accessed 2026-10-31.
- Microsoft Learn, [SetWaitableTimerEx](https://learn.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-setwaitabletimerex) (TolerableDelay). Accessed 2026-10-31.
- Microsoft Learn, [Supporting Idle Power-Down](https://learn.microsoft.com/en-us/windows-hardware/drivers/wdf/supporting-idle-power-down) (KMDF S0 idle settings). Accessed 2026-10-31.
- Microsoft Learn, [Modern Standby](https://learn.microsoft.com/en-us/windows-hardware/design/device-experiences/modern-standby) and [Modern Standby SleepStudy](https://learn.microsoft.com/en-us/windows-hardware/design/device-experiences/modern-standby-sleepstudy). Accessed 2026-10-31.
- Microsoft Learn, [Powercfg command-line options](https://learn.microsoft.com/en-us/windows-hardware/design/device-experiences/powercfg-command-line-options). Accessed 2026-10-31.
- Defrag Tools #157, [Energy Estimation Engine (E3)](https://learn.microsoft.com/en-us/shows/defrag-tools/157-energy-estimation-engine-e3). Accessed 2026-10-31.
- Microsoft Sustainable Software blog, [Measuring Your Application Power and Carbon Impact (Part 1)](https://devblogs.microsoft.com/sustainable-software/measuring-your-application-power-and-carbon-impact-part-1/) (Sept 14, 2020; E3 and `powercfg /srumutil`). Accessed 2026-10-31.
- Winhelponline, [Generate energy usage report per app (E3 dump) using powercfg](https://www.winhelponline.com/blog/generate-energy-usage-report-per-app-energy-estimation-engine-e3-dump-using-powercfg-exe/). Accessed 2026-10-31.
- Code: `code/016_ecoqos_and_timers.c`, compile-checked 2026-10-31 with `x86_64-w64-mingw32-gcc -Wall -Wextra -c`.
