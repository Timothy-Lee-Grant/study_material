# Windows Internals, Part 4: Driver Verifier and Event Tracing (audio lecture)

This is part four of an eight-part series on Windows internals. Parts one through three covered the debugger, blue-screen codes, and dumps. This part covers two tools that see beyond a single moment: Driver Verifier, which makes hidden driver bugs crash immediately at the scene, and Event Tracing for Windows, which records what happened over time.

## Why this episode exists

A dump is a photograph of one instant. Two very common problems resist photographs. The first is the bug that crashes somewhere else, later, by luck: memory corruption that surfaces minutes afterward in another driver, or pageable memory touched at the wrong time that only fails when that page happens to be on disk. The second is the timing problem: something takes too long, or something stops happening, and you need to see the sequence of events that led up to it. Timothy wants both tools in hand. By the end of this episode he should know when to reach for each, and how to use them.

## The core ideas

Here are today's core ideas. They're the answer key for the walk questions at the end.

One. Driver Verifier makes the kernel check specific drivers strictly, turning a broken rule into an immediate crash at the moment of the violation, inside the guilty driver. It moves the crash from the victim to the culprit.

Two. Verify one or two suspect drivers, deliberately, then turn Verifier off. It slows the verified drivers and changes timing, and on a driver that loads at boot it can stop the machine from booting, so use the reset-on-boot-failure safety setting.

Three. Each standard Verifier option targets a bug class. Special Pool catches buffer overruns and use-after-free. Force IRQL Checking catches pageable memory touched at high priority, every time. Pool Tracking catches leaks. I/O Verification catches misuse of input-output requests. Deadlock Detection catches lock-ordering mistakes.

Four. Event Tracing for Windows, E-T-W, has four roles. Providers emit events. Sessions buffer them. Controllers start and stop sessions. Consumers read them. The recorder W-P-R is a controller, and the analyzer W-P-A is a consumer.

Five. W-P-R records using profiles, in memory mode, a rolling window you save right after something happens, or in file mode, which records everything. Problems during boot use a boot trace.

Six. In W-P-A, the most useful views for drivers are the D-P-C and interrupt duration table grouped by module, the precise CPU usage view that shows who waited on what, and generic events, which show a driver's own logged events.

## Section one: what Driver Verifier does

Driver Verifier is built into Windows. When you name a driver, the kernel intercepts that driver's calls into the kernel and its memory allocations, and adds checks and stress around them. When the driver allocates memory, Verifier can place the allocation so that one byte past its end is an unmapped page. When the driver raises its priority level or takes a lock, Verifier can push the driver's pageable memory out of RAM first. When the driver handles input-output requests, Verifier checks that it follows the rules.

Here's why that matters. Without Verifier, many driver bugs are latent. A buffer overrun silently scribbles on a neighbor's memory, and the crash comes much later in someone else's code, so the blue screen blames an innocent driver. Pageable memory touched at DISPATCH level only crashes when the page happens to be on disk, which might be once a week. Verifier removes the luck. The first violation crashes, inside the guilty driver, at the guilty instruction. Expect more crashes with Verifier on; that's the point.

## Section two: the standard options and what they catch

Microsoft lists the standard options as Special Pool, Force IRQL Checking, Pool Tracking, I/O Verification, Deadlock Detection, DMA Verification and WDF Verification, plus security checks, miscellaneous checks and D-D-I compliance checking. Here are the most important, each with its bug class.

Special Pool places each allocation at the very end of a memory page, right against an unmapped guard page, and keeps freed memory inaccessible for a while. A write one byte past the end, or a read of memory that's already been freed, faults immediately, at the exact instruction.

Force IRQL Checking is the one to remember for D-one crashes. Every time the verified driver raises its priority to DISPATCH or above, or takes a spin lock, Verifier first trims the driver's pageable memory out of RAM. So any access to pageable memory at that level faults every single time, instead of once in a while.

Pool Tracking records every allocation, and catches memory the driver didn't free when it unloaded. I/O Verification checks the rules for input-output requests: completing one twice, freeing one that's still in use, returning the wrong status. Deadlock Detection tracks the order in which locks are taken, and flags orders that could deadlock, even if they haven't yet. D-D-I compliance checks calls into kernel functions against their documented rules, like calling a function at too high a priority level.

When Verifier catches something, the usual stop code is hex C-four, driver verifier detected violation, with parameter one naming which rule. Special Pool catches often show up as hex D-six or hex C-one. Framework rule violations show up as hex one-zero-D.

Pause and predict. A driver seems to touch pageable memory in its D-P-C, but in a week of testing it has crashed only twice. Which single Verifier option makes it reproducible, and why?

Force IRQL Checking. It pushes the driver's pageable memory out every time the driver raises its priority, so the illegal access faults every time instead of only when the page happens to be on disk.

## Section three: a safe Verifier workflow

The command-line tool is called verifier. Here's the workflow, in order.

First, choose one or two suspect drivers. Verifying every driver slows everything down and changes timing so much that some bugs hide.

Second, if the driver loads during boot, set a safety net: the boot-mode option called reset-on-boot-fail, which turns Verifier off by itself if the machine fails to boot.

Third, turn on the standard options for the suspect driver: the verifier command with slash-standard, slash-driver, and the driver's file name. Then reboot, because Verifier settings take effect at the next boot.

Fourth, reproduce the scenario: the resume cycle, the idle period, the stress test.

Fifth, analyze the dump with bang-analyze. With Verifier on, the top driver frame on the stack is very likely the real culprit.

Sixth, turn it off with verifier slash-reset and reboot. Don't leave it on by accident.

## Section four: how event tracing works

Event Tracing for Windows is Windows' built-in, high-speed logging system, used by the kernel itself, by drivers and by applications. It has four roles.

Providers emit events. The kernel provides events for context switches, interrupts, D-P-Cs, disk input-output, page faults and power changes. Drivers can be providers too, using styles called W-P-P, TraceLogging or manifest-based events.

Sessions are sets of in-memory buffers that collect events from the providers enabled on them, and optionally write them to a file with the extension dot E-T-L.

Controllers start and stop sessions and choose which providers are on. The main one you'll use is W-P-R, the Windows Performance Recorder.

Consumers read events. The main one is W-P-A, the Windows Performance Analyzer.

Why is this suitable for drivers, even in interrupt routines? Writing an event goes into a per-processor buffer, which is fast and safe even at high priority. And when no one has enabled a provider, its event calls cost almost nothing, so drivers can leave tracing compiled in permanently. Framework-based drivers also keep a small always-on log of their own, called the in-flight recorder, which ends up in dumps.

## Section five: recording with W-P-R

W-P-R records using profiles: named recipes of which providers to enable, at what detail, with what buffers. The command W-P-R dash-profiles lists the built-in ones. GeneralProfile is a good first pass; there are also CPU, disk and file profiles, and more specialized ones for things like power.

There are two logging modes. Memory mode, the default, keeps a rolling window in memory: old events are overwritten, so you can leave it running for hours and save the last few minutes as soon as the problem happens. File mode writes everything to disk, which suits bounded scenarios where you need the whole story.

The everyday commands are W-P-R dash-start with a profile name to begin, dash-status to check it, dash-stop with a file name and a short description to save, and dash-cancel to discard.

For problems that happen during boot or resume, before you can log in and start anything, W-P-R can arm a boot trace: dash-boottrace with dash-addboot and a profile name. After the next boot you stop it with dash-boottrace dash-stopboot and a file name.

Keep traces short and focused. A few minutes of detailed kernel tracing can be hundreds of megabytes.

## Section six: reading with W-P-A

Open the trace file in W-P-A. The window is built from graphs dragged in from a panel called Graph Explorer, each linked to a table. Three skills cover most of the work.

First, load symbols, so stack columns show function names. It's the same symbol server as WinDbg.

Second, group and sort. Each table has a golden vertical bar. Columns to its left are grouping keys, and columns to its right are added up. Drag the module column to the left of the bar and sort by duration, and you've answered "which driver took the most time?"

Third, zoom to the moment. Select the time range where the problem starts, zoom in, and every graph follows. Then look at what every view shows at that moment.

The views that matter most for drivers are these. The D-P-C and interrupt view shows which modules' routines ran, how often, and how long each took. Sorting by longest duration finds single slow routines, which risk one-three-three with parameter one equal to zero. Sorting by count finds storms, which risk the cumulative form. The precise CPU usage view, built from context switches, shows which thread ran when, and for a waiting thread, who woke it and how long it waited; it's the trace version of following waits with bang-thread. Generic events show raw events from any provider, including your driver's own, in order.

Pause and predict. A touchscreen is dead. In a trace taken while touching the screen, how do you tell "the device or its line stopped" apart from "the driver stopped processing"?

If the touch interrupt's routine stops appearing entirely after the failure, the device or the line stopped, or the interrupt was lost, and the logic analyzer settles which. If the routine keeps running but no input reaches applications, the driver or the layers above it stopped processing.

## Section seven: choosing between them

Use Verifier when you suspect rule violations: random crashes in different places suggesting corruption, a rare D-one, a suspected leak, or misused requests. Use tracing when the question is about time or sequence: a one-three-three, audio dropouts, laggy input, a slow resume, a partial hang, or "does this device still interrupt?" For a nine-F during resume, start with the dump from part two, then put Verifier on the driver holding the request, and trace the resume.

## Connections

This connects to part two: Force IRQL Checking turns rare D-ones into certain ones, and tracing is Microsoft's own suggested tool for the cumulative one-three-three. It connects to part three: these tools fill in the crash and dead-device kits. And it connects to part five, where the interrupt routine, D-P-C and work item that tracing measures are explained in code.

## Recap

The core ideas again, in different words. Verifier makes the first violation crash inside the guilty driver. Use it on a few drivers, with a boot safety net, and reset it afterward. Special Pool catches overruns and use-after-free; Force IRQL Checking makes pageable-at-high-priority bugs deterministic. Event tracing has providers, sessions, controllers and consumers. W-P-R records with profiles, in memory mode for catching things after they happen, in file mode for everything, and with boot traces for startup. W-P-A answers questions when you group, sort and zoom: D-P-C and interrupt durations, waits, and a driver's own events.

## Walk questions

Three questions for the next walk.

First: explain how Force IRQL Checking turns a once-a-week crash into an every-time crash.

Second: name the four roles in event tracing, with one example of each.

Third: in a trace, what would you sort by to find a single slow D-P-C, and what would you sort by to find an interrupt storm?
