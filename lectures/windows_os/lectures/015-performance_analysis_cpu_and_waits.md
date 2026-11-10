# Lecture 015: Performance Analysis on Windows: Where the Time Goes (CPU Sampling, Waits, and Using All the Cores)

> **For:** Timothy · **Date:** 2026-10-31
> **Prerequisites:** 004 (ETW, WPR/WPA basics), 008 (processes and threads). Helpful: 013 §6 (your first WPR trace).
> **Why this lecture:** on Windows, "fundamentals" usually means **performance and battery life**: how fast things feel and how long the device lasts. Both are investigated with the same tools: ETW traces, recorded with WPR and read in WPA or Profile Explorer. Lecture 004 showed how to record a trace. This lecture teaches how to **answer a question with one**: is this slow because the CPU is busy, or because something is waiting? And if the CPU is busy, is it using the cores it has? The running example is a classic: a compression routine that's slow on an 8-core Arm laptop because it only uses one core.
> **Format notes:** full problem statement; definitions before use; real tool names and commands. No firmware analogies.
> **Verification:** `code/015_parallel_compress.py` was run (on a 2-core Linux container: 1.76× speedup, which Amdahl's law matches for a job that's about 86% parallel once process start-up is counted). WPA and Profile Explorer details are from Microsoft's documentation and the Profile Explorer README (Sources).

---

## Core ideas (the answer key)

1. **A slow operation is either running or waiting.** Running = a thread is on a CPU executing instructions. Waiting = no thread of yours is on a CPU because it's blocked (disk, network, a lock, a timer) or ready but not scheduled. The first question of any investigation is which one.
2. **Two kinds of ETW data answer that:** **CPU sampling** (every ~1 ms, record which code each CPU is running) shows *where running time goes*. **Context switches** (every time a thread starts or stops running, with who woke it and how long it waited) show *why a thread wasn't running*.
3. **In WPA:** *CPU Usage (Sampled)* = where the CPU time goes, by process, thread, module, function and stack. *CPU Usage (Precise)* = when each thread ran and waited, with **ready thread** (who woke it) and wait time. Use Sampled for "what is hot", Precise for "why is it idle".
4. **"Low total CPU but slow" has two different causes:** waiting (Precise shows long waits), or **serial work** (one thread at 100% of one core while the other cores are idle). On an 8-core machine, one busy core is only 12.5% of total CPU, which looks "low" but is a saturated single thread.
5. **Amdahl's law:** if a fraction *p* of the work can run in parallel on *N* cores, the best speedup is 1 / ((1 − p) + p / N). The serial part sets the ceiling: with p = 0.9, even infinite cores give at most 10×.
6. **To parallelize a sequential algorithm, break the dependency chain.** A single compression stream depends on everything before it. Splitting the input into independent chunks makes the chunks parallel, at a small cost in compression ratio (pigz's approach).
7. **Symbols turn addresses into function names.** Without them, stacks show `module+0x1234`. Set `_NT_SYMBOL_PATH` (Microsoft's symbol server plus your PDBs) before analyzing.
8. **Profile Explorer** is an open-source tool (MIT) for the CPU-sampling side: it opens ETW traces and shows hot functions, flame graphs and call trees, down to the **assembly instructions** that consumed the samples, on x64 and native ARM64. WPA is the broad tool; Profile Explorer is the deep "why is this function slow" tool.
9. **Arm-specific suspects:** an x64 binary running under emulation, and code with hand-tuned x86 SIMD (SSE/AVX) paths but only a slow generic path on Arm. Both show up as "the same code is much slower on Arm".
10. **Measure the fix the same way you found the problem:** same scenario, same trace, compare. And check energy, not just time (lecture 016): using more cores to finish sooner usually also saves energy, but not always.

---

## Table of Contents

- [0. The problem](#0-the-problem)
- [1. Running or waiting](#1-running-or-waiting)
- [2. Recording the trace](#2-recording-the-trace)
- [3. Reading it in WPA](#3-reading-it-in-wpa)
- [4. The single-core diagnosis](#4-the-single-core-diagnosis)
- [5. Amdahl's law and breaking the dependency chain](#5-amdahls-law-and-breaking-the-dependency-chain)
- [6. Going deeper with Profile Explorer](#6-going-deeper-with-profile-explorer)
- [7. Why the same code can be slow on Arm](#7-why-the-same-code-can-be-slow-on-arm)
- [8. Fixing it across a team boundary](#8-fixing-it-across-a-team-boundary)
- [9. A lab you can do in your VM](#9-a-lab-you-can-do-in-your-vm)
- [Common mistakes](#common-mistakes)
- [Self-check questions](#self-check-questions)
- [Sources](#sources)

---

## 0. The problem

**Investigate: compression is slow on an Arm laptop.**

An app compresses a 500 MB folder using a library's compression routine. On an 8-core Arm laptop it takes 40 seconds; users expected it to take a few seconds. Task Manager shows overall CPU around 13% while it runs, so at first glance "the CPU isn't the problem".

Find out:
1. Is the operation running or waiting?
2. If running, where does the time go, and is it using the available cores?
3. What change would make it faster, how much faster can it get, and what does that change cost?

Describe which traces you record, which views you open, and what you expect to see for each possible cause.

---

## 1. Running or waiting

At any instant, each of your threads is in one of three states (lecture 008):

| State | Meaning | How it shows up |
|---|---|---|
| **Running** | on a CPU, executing | CPU samples land in its code |
| **Ready** | wants a CPU, none free (or a higher-priority thread has it) | context-switch data: "ready time" |
| **Waiting** | blocked on something: I/O, a lock, an event, a timer | context-switch data: "wait time", and which thread readied it |

So an operation that takes 40 s with 13% CPU could be:
- **waiting**: e.g. reading files from a slow disk; one thread mostly blocked in `ReadFile`;
- **serial**: one thread running 100% of the time on one of eight cores (1/8 = 12.5%);
- **contended**: several threads, but they spend most of the time waiting for each other on a lock.

These need different fixes (faster I/O or overlapping I/O; parallelism; less locking), so you diagnose before you fix.

---

## 2. Recording the trace

**WPR** (Windows Performance Recorder) turns on ETW providers and saves the events to an `.etl` file. From an elevated prompt:

```
wpr -profiles                     # list built-in profiles
wpr -start CPU -start DiskIO      # CPU sampling + context switches, plus disk I/O
   ... run the compression ...
wpr -stop compress.etl            # stop and save
```

- The **CPU** profile turns on the kernel's sampled profile (a stack sample on each CPU about every millisecond by default) and context-switch / ready-thread events with stacks. That's both kinds of data from §1.
- **DiskIO** (or FileIO) lets you see whether the time went to the disk.
- Keep the trace short and focused: start, reproduce once, stop. CPU traces are large (tens of MB per second on many cores).

The WPR GUI does the same with checkboxes. The `GeneralProfile` is a reasonable default when you don't know yet what you're looking for.

**Symbols.** Set the symbol path before opening the trace, so stacks resolve to function names:

```
set _NT_SYMBOL_PATH=srv*C:\symbols*https://msdl.microsoft.com/download/symbols;C:\path\to\your\pdbs
```

Microsoft's symbol server covers Windows components; your own code needs its `.pdb` files.

---

## 3. Reading it in WPA

**WPA** (Windows Performance Analyzer) opens the `.etl`. In the Graph Explorer, under **Computation**:

**CPU Usage (Sampled):** each sample is "this CPU was running this stack at this moment". Group by `Process → Thread → Stack` and you get a tree of where the running time went. Columns to know:
- **Count / Weight**: samples (≈ ms of CPU time) under that row.
- **% Weight**: share of all CPU time in the selected range.
- **Stack**: expand it to walk from the thread's start function down to the hot leaf function.

**CPU Usage (Precise):** built from context switches. Each row is "thread X was switched in". Columns to know:
- **CPU Usage (ms)**: how long it ran.
- **Waits (µs)**: how long it was waiting before it was switched in.
- **Ready (µs)**: how long it was ready but not running (waiting for a CPU).
- **Readying Process / Thread / Stack**: **who woke it**. For a thread blocked on a lock, this is the thread that released the lock. For one blocked on I/O, it's the I/O completion path.

**The graph view is the fastest first look.** Graph "CPU Usage (Sampled)" by thread, or show the **per-CPU** utilization (the "% Usage by CPU" style graph): a single flat line at one core's worth, with the other cores near zero, is the visual signature of serial work.

**Selecting the time range matters.** Select just the 40 seconds of compression (drag on the timeline, then zoom). Percentages are relative to the selection.

---

## 4. The single-core diagnosis

What you'd expect for each cause, and what the compression trace shows:

| Cause | CPU Usage (Sampled) | CPU Usage (Precise) | Disk I/O |
|---|---|---|---|
| Waiting on disk | few samples in the app | app thread: large **Waits**, readied by the I/O completion path | busy, high latency |
| Lock contention | samples spread over several threads, plus lock code | threads with large **Waits**, readied by **each other** | quiet |
| **Serial CPU work** | **one thread** has nearly all the app's samples, deep in the compression function | that thread: almost no waits; **runs continuously** | quiet |

The compression trace matches the third row: one worker thread holds ~99% of the app's samples, the stack bottoms out in the deflate routine, the thread almost never waits, and the per-CPU graph shows one core at 100% while seven are idle. Task Manager's 13% was exactly 1/8 of the machine.

Conclusion: the routine is **CPU-bound and serial**. A faster disk wouldn't help; more parallelism would.

---

## 5. Amdahl's law and breaking the dependency chain

**Amdahl's law.** Split the work into a part that must run one step after another (fraction 1 − p) and a part that can be divided among cores (fraction p). On N cores, the parallel part takes p/N of the original time and the serial part still takes 1 − p:

```
speedup(N) = 1 / ((1 - p) + p / N)
```

From `code/015_parallel_compress.py`:

```
p= 0.5:  2 cores  1.33x   4 cores  1.60x   8 cores  1.78x  12 cores  1.85x
p= 0.9:  2 cores  1.82x   4 cores  3.08x   8 cores  4.71x  12 cores  5.71x
p=0.95:  2 cores  1.90x   4 cores  3.48x   8 cores  5.93x  12 cores  7.74x
p=0.99:  2 cores  1.98x   4 cores  3.88x   8 cores  7.48x  12 cores 10.81x
```

The ceiling as N → ∞ is 1 / (1 − p). If even 10% stays serial (reading input, writing the archive header, combining results), 8 cores give at most 4.7×.

**Why one compression stream is serial.** A compressor like deflate (zip, gzip) replaces repeated text with back-references to earlier data ("copy 20 bytes from 1,000 bytes ago"). Compressing byte 1,000,000 depends on the window of bytes before it, and the output bit stream is one continuous sequence. That's a **dependency chain**: step i needs the result of step i − 1. You can't hand the second half to another core without changing the format.

**Breaking the chain: independent chunks.** Split the input into chunks (say 1 MiB), compress each chunk as its own stream on its own core, and store them in order. Costs:
- **Slightly worse ratio**: each chunk starts with an empty history, so repeats that span a chunk boundary aren't found. (pigz, a parallel gzip, reduces this by priming each chunk with the previous 32 KB as a dictionary.)
- **Format**: the reader must understand chunked output (gzip allows concatenated members; zip compresses files independently anyway; newer formats such as zstd have multithreading built in).
- **Memory**: one compressor state per worker.

Measured in the container (2 cores, 48 MiB of text):

```
cores: 2, input: 48 MiB in 48 chunks
one stream, one core :   1.76 s  ratio 2.26
chunks, 2 workers    :   1.00 s  ratio 2.25
measured speedup     :   1.76x
```

Solving 1 / ((1 − p) + p/2) = 1.76 gives p ≈ 0.86: starting the worker processes and collecting results is the serial part. The ratio barely moved (2.26 → 2.25) because 1 MiB chunks are large compared with deflate's 32 KB window. On 8 cores, p = 0.86 predicts about 4×; with a bigger input the fixed start-up cost shrinks relative to the work, p rises, and the speedup goes up with it.

**Other kinds of serial bottleneck** follow the same diagnosis: a single-threaded loop over files, a UI thread doing work, one lock that every worker takes. The fix differs (parallel loop; move work off the UI thread; shard the lock), but you find each the same way.

---

## 6. Going deeper with Profile Explorer

WPA tells you *which* function is hot. Sometimes you need to know *why that function* is slow: which loop, which instructions. That's what **Profile Explorer** is for.

From its README (accessed 2026-10-31): it's a tool for "viewing CPU profiling traces collected through Event Tracing for Windows (ETW)", it presents the **slowest parts of the profiled application through an assembly view and various views** that show the hottest functions, call tree and flame graph, a timeline, and source code. It supports x64 and **native ARM64** binaries, is written in C# (WPF, .NET 8), and is MIT-licensed with contributions accepted under Microsoft's CLA.

A typical session:
1. Open the same `.etl` you recorded with WPR, pick the process.
2. **Summary / hot functions**: the compression routine at the top.
3. **Flame graph**: width = time; confirms the routine is reached from one worker thread.
4. Open the function's **assembly view**: each instruction annotated with its sample count, so you see the inner loop (for example a hash-chain search) and whether it uses vector instructions.
5. **Source view** (with symbols and source available): the same samples mapped to source lines.

When to reach for which tool:

| Question | Tool |
|---|---|
| Where did the 40 s go across the whole system? Waiting or running? Which process/thread? | WPA |
| Which instructions in this hot function cost the most? Is the inner loop vectorized? | Profile Explorer |
| Disk, file, power, GPU, memory, custom events | WPA (plus plugins) |

**WPA plugins.** WPA's data-processing runtime is the open-source **Microsoft Performance Toolkit SDK** (MIT). The SDK lets you write plugins that teach WPA to parse new data sources (your own ETW events, a log format) and show them as tables and graphs. Lecture 017 suggests a project that uses it with your TgCounter driver.

---

## 7. Why the same code can be slow on Arm

When a workload is fine on an x64 desktop and slow on an Arm laptop, check these, in order:

1. **Is the process running native ARM64?** An x64 binary runs on Windows on Arm through emulation, which costs performance. Task Manager's *Details* tab can show an **Architecture** column; in a trace, the loaded modules tell you the same thing. A native ARM64 (or ARM64EC) build removes that cost.
2. **Does the hot code have an Arm vector path?** Libraries often have hand-written x86 SIMD (SSE2/AVX2) loops for hashing, checksums and copying, with a plain scalar loop as the fallback. If nobody wrote the Arm NEON version, the Arm build runs the scalar loop: correct, but several times slower. Profile Explorer's assembly view shows this directly (scalar loads and adds where you'd expect vector instructions).
3. **Is it using the cores?** Arm laptops often have many cores, some of them efficiency cores. A serial algorithm that's acceptable on a 4 GHz desktop core can be slow on one laptop core. §4's diagnosis applies.
4. **Is it being scheduled on efficiency cores on purpose?** Background or EcoQoS work (lecture 016) runs on efficient cores at efficient frequencies by design. If a user is actively waiting for the result, the work shouldn't be tagged as background.

---

## 8. Fixing it across a team boundary

Performance problems often sit in code you don't own: the app calls a framework, which calls a library. The trace tells you which module the time is in, which tells you who owns the fix.

A good path:
1. **Reduce it to a minimal repro** (a 20-line program that compresses a file and shows the time) plus the trace.
2. **File it where the owners work.** For open-source components (the .NET runtime, WinUI, compression libraries), that's an issue on their GitHub repo with the repro, the trace evidence ("one thread at 100%; stack in `deflate_slow`"), the machine details, and the expected result.
3. **Propose the fix if you can**, with measurements: before/after time, before/after ratio, and the cost (memory, format compatibility).
4. **Verify the fix** with the same trace and scenario once it ships.

That's the habit to build: start from the user's experience ("this takes 40 seconds and shouldn't"), find the cause with data, and get the fix into whichever component owns it, even when that component belongs to another team.

---

## 9. A lab you can do in your VM

In your Windows 11 Arm VM (lecture 010):

1. Copy `code/015_parallel_compress.py` over the shared folder. Install Python for ARM64 if it isn't there (`winget install Python.Python.3.13`).
2. In an elevated prompt: `wpr -start CPU`, run the script, `wpr -stop compress.etl`.
3. Open the trace in WPA. Select the "one stream" interval: one thread busy, one CPU busy. Select the "chunks" interval: several worker processes busy at once.
4. In *CPU Usage (Sampled)*, group by Process → Thread → Stack, and find `zlib` under the Python process.
5. Install Profile Explorer from its GitHub releases page, open the same trace, and look at the hot functions and the flame graph.
6. Compare the measured speedup with `amdahl(p, N)` for your VM's core count, and estimate p.

---

## Common mistakes

1. **Reading total CPU % as "not CPU-bound".** On N cores, one saturated thread is 100/N %. Look per thread or per CPU.
2. **Looking only at CPU samples when the problem is waiting.** Samples show where time goes *while running*; waits are invisible there. Use the Precise (context-switch) data.
3. **Analyzing without symbols.** `module+0x1234` stacks hide the answer.
4. **Selecting the whole trace** instead of the interval of the slow operation, which dilutes every percentage.
5. **Expecting N cores to give N× speedup.** Amdahl: the serial fraction caps it.
6. **Parallelizing without measuring the cost:** ratio, memory, format compatibility, energy.
7. **Assuming an x64-vs-Arm difference is the CPU's fault** before checking emulation and missing SIMD paths.

---

## Self-check questions

1. Task Manager shows 13% CPU on an 8-core laptop while an operation runs slowly. Give two different explanations and the trace evidence that would distinguish them.
<details><summary>Answer</summary>(a) Serial CPU work: one thread at 100% of one core (1/8 = 12.5%); CPU Usage (Sampled) shows one thread with nearly all samples and Precise shows it rarely waits; per-CPU graph shows one core busy. (b) Waiting (disk, lock): the threads are mostly blocked; Precise shows large Waits, with the readying thread being the I/O path or another thread releasing a lock; few CPU samples.</details>

2. What's the difference between CPU Usage (Sampled) and CPU Usage (Precise) in WPA?
<details><summary>Answer</summary>Sampled comes from periodic stack samples (about every 1 ms per CPU) and shows where running time goes (process, thread, function, stack). Precise comes from context-switch events and shows when each thread ran and why it wasn't running: wait time, ready time, and which thread readied it.</details>

3. 90% of a job parallelizes perfectly. What's the best speedup on 8 cores? On unlimited cores?
<details><summary>Answer</summary>1 / (0.1 + 0.9/8) = 1 / 0.2125 ≈ 4.7× on 8 cores. As N → ∞, 1 / 0.1 = 10×.</details>

4. Why can't a single deflate stream simply be split across cores, and what's the standard workaround with its costs?
<details><summary>Answer</summary>Each part of the output depends on the history before it (back-references into a sliding window) and the output is one continuous bit stream, so it's a dependency chain. Workaround: compress independent chunks in parallel and concatenate. Costs: slightly worse ratio (repeats across chunk boundaries are missed, reducible by priming with the previous 32 KB as pigz does), a format that allows multiple members, and more memory.</details>

5. When do you use Profile Explorer instead of WPA?
<details><summary>Answer</summary>When you already know which function is hot and need to know why: Profile Explorer shows the function's assembly (and source) annotated with sample counts, plus flame graphs and call trees, for x64 and native ARM64. WPA is for the system-wide picture: running vs waiting, which process/thread, disk, power, and many other event types.</details>

6. The same compression is 4× slower on an Arm laptop than on an x64 desktop, even single-threaded. List two Arm-specific causes to check and how you'd see each.
<details><summary>Answer</summary>(a) The process is x64 running under emulation: check the Architecture column in Task Manager's Details tab or the loaded modules in the trace. (b) The hot loop has an x86 SIMD path but only a scalar fallback on Arm: Profile Explorer's assembly view shows scalar instructions in the hot loop. (Also check whether the work is tagged as background/EcoQoS and running on efficiency cores.)</details>

7. Why set `_NT_SYMBOL_PATH` before analyzing, and what should it contain?
<details><summary>Answer</summary>So stack frames resolve to function names instead of module offsets. It should point to Microsoft's symbol server (with a local cache, e.g. `srv*C:\symbols*https://msdl.microsoft.com/download/symbols`) plus the folders with your own PDBs.</details>

---

## Sources

- Microsoft Learn, [Windows Performance Recorder](https://learn.microsoft.com/en-us/windows-hardware/test/wpt/windows-performance-recorder) and [WPR command-line options](https://learn.microsoft.com/en-us/windows-hardware/test/wpt/wpr-command-line-options). Accessed 2026-10-31.
- Microsoft Learn, [Windows Performance Analyzer](https://learn.microsoft.com/en-us/windows-hardware/test/wpt/windows-performance-analyzer) and the CPU analysis guide [CPU Analysis](https://learn.microsoft.com/en-us/windows-hardware/test/wpt/cpu-analysis) (Sampled vs Precise, ready thread). Accessed 2026-10-31.
- [microsoft/profile-explorer](https://github.com/microsoft/profile-explorer) README: ETW CPU profiles, assembly/source views, hot functions, flame graph, timeline, x64 and native ARM64, .NET 8 WPF, MIT, CLA. Accessed 2026-10-31.
- [microsoft/microsoft-performance-toolkit-sdk](https://github.com/microsoft/microsoft-performance-toolkit-sdk): "serves as the runtime of the Windows Performance Analyzer"; plugins; MIT. Accessed 2026-10-31.
- Amdahl, G. M., "Validity of the single processor approach to achieving large scale computing capabilities", AFIPS 1967.
- Mark Adler, [pigz](https://zlib.net/pigz/) (parallel gzip: independent blocks primed with the previous 32 KB). Accessed 2026-10-31.
- Microsoft Learn, [Windows on Arm overview / x64 emulation](https://learn.microsoft.com/en-us/windows/arm/overview) and [ARM64EC](https://learn.microsoft.com/en-us/windows/arm/arm64ec). Accessed 2026-10-31.
- Code: `code/015_parallel_compress.py`, run 2026-10-31.
