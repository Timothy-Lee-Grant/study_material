2026_09_25_02_01-(DotNet-Meets-The-Metal)

# Lecture 002 — .NET Meets the Metal: A Map of .NET on Devices, and Where You Fit

> **For:** Timothy Lee Grant
> **Date:** 2026-09-25
> **Prerequisite:** Lecture 001 (The .NET Atlas). This lecture reuses its vocabulary: IL, JIT, GC, P/Invoke, the Generic Host, and the 🟢/🔵/⚫ tags.
>
> **Why this lecture:** You noticed something most .NET developers never notice: the runtime has whole sections that exist so .NET can run on many kinds of hardware. You had a hunch that this might be where an embedded engineer who now writes .NET could make an unusual contribution. The hunch is correct, and this lecture is the map for it. It has three jobs:
>
> 1. **Show you the territory.** Every way C# reaches hardware, from a cloud VM down to a microcontroller with 64 KB of RAM, including several you didn't know existed.
> 2. **Teach the connecting concepts.** Why each approach exists, what it costs, and how it links to things you already know from firmware.
> 3. **Analyze your options honestly.** Which avenues fit you, which are dead ends, and concrete ideas you could start on this month.
>
> **Currency warning:** this is a fast-moving niche. Every status claim here was checked in September 2026 and has a source in §16. Re-check anything you plan to build on.

---

## Table of Contents

- [0. The hunch, examined](#0-the-hunch-examined)
- [1. The nervous-system map: where code runs on a device](#1-the-nervous-system-map-where-code-runs-on-a-device)
- [2. Three ways to run C#: JIT, interpreter, AOT](#2-three-ways-to-run-c-jit-interpreter-aot)
- [3. The family tree: every .NET that ever touched hardware](#3-the-family-tree-every-net-that-ever-touched-hardware)
- [4. Inside the runtime: the parts built for portability](#4-inside-the-runtime-the-parts-built-for-portability)
- [5. Avenue A — .NET on embedded Linux](#5-avenue-a--net-on-embedded-linux)
- [6. Avenue B — C# on microcontrollers](#6-avenue-b--c-on-microcontrollers)
- [7. Avenue C — The frontier: C# with no runtime at all](#7-avenue-c--the-frontier-c-with-no-runtime-at-all)
- [8. Avenue D — Connectivity: from the board to the cloud](#8-avenue-d--connectivity-from-the-board-to-the-cloud)
- [9. Avenue E — The hidden market: test and manufacturing automation](#9-avenue-e--the-hidden-market-test-and-manufacturing-automation)
- [10. Where you are uniquely positioned (an honest analysis)](#10-where-you-are-uniquely-positioned-an-honest-analysis)
- [11. The idea catalog](#11-the-idea-catalog)
- [12. How contributing to .NET open source actually works](#12-how-contributing-to-net-open-source-actually-works)
- [13. A recommended path](#13-a-recommended-path)
- [14. Concept connections: firmware ↔ .NET on devices](#14-concept-connections-firmware--net-on-devices)
- [15. Self-check questions](#15-self-check-questions)
- [16. Sources and further reading](#16-sources-and-further-reading)

---

## 0. The hunch, examined

The claim: *"An embedded engineer who writes .NET is unusually well positioned to contribute to .NET on devices."*

Evidence for:

- **The talent pool is split in two.** Most .NET engineers have never read a datasheet, toggled a register, or thought about an ABI. Most firmware engineers have never used C#, DI, or a garbage collector. The work in this lecture sits exactly on the seam between those two groups, and very few people are comfortable on both sides.
- **The hard parts of .NET-on-devices are firmware problems.** Porting a runtime means calling conventions, atomics, memory ordering, stack unwinding, and instruction encoding. Writing a device binding means reading a datasheet and getting the register sequence right. Making a device product work means boot, watchdogs, power loss, and flash wear. .NET engineers find these hard. You find them familiar.
- **You've already shipped one.** Firmware producing framed telemetry, a .NET worker receiving it through native interop and a callback, then turning it into decisions, is a complete, real example of the architecture this whole field is about.

Evidence against (so you go in clear-eyed):

- **It's a niche.** The number of jobs titled ".NET embedded engineer" is small. The value comes from being the rare person who *bridges* two big fields, not from the niche itself being big (§10).
- **Some of the territory is legacy.** Parts of the family tree (§3) are dead or dormant. You need to know which parts are alive before investing.
- **Microcontroller C# is a hobbyist-and-specialist market.** Real, open source, and friendly to contributors, but not where most money is. Embedded **Linux** and **edge-to-cloud** are where most of the demand is.

Verdict: **the hunch is right, with a refinement.** Your strongest positioning isn't "C# on microcontrollers." It's **"the engineer who can own a device system end to end: firmware, embedded Linux, .NET, and the path to the cloud."** The rest of this lecture shows you the pieces.

### 0.1 Tags used in this lecture

Same as Lecture 001, plus one:

| Tag | Meaning |
|---|---|
| 🟢 **OWN IT** | Core concept for this domain |
| 🔵 **CONTRACT** | Know what it does and how to use it |
| ⚫ **BLACK BOX (for now)** | Know it exists and what problem it solves |
| 🧭 **AVENUE** | A direction you could take your career or contributions |

---

## 1. The nervous-system map: where code runs on a device

Tag: 🟢 **OWN IT**. This is the mental model everything else hangs on.

In a person, fast reflexes are handled by the **spinal cord**: no thinking, just a guaranteed quick response. Thinking happens in the **brain**, which is slower but far more capable. Long-term memory and coordination with other people happen **outside** you, in society. Device systems split the same way, for the same reasons.

```
 ┌──────────────────────────────────────────────────────────────────────────────┐
 │ SOCIETY — the cloud / data center                                            │
 │   Fleet management, dashboards, analytics, long-term storage, ML             │
 │   .NET: ASP.NET Core, Azure IoT Hub services, Functions      (Lecture 001)   │
 │   Resources: effectively unlimited · Latency: 10s–100s of ms                 │
 ├────────────────────────────────── network ───────────────────────────────────┤
 │ BRAIN — the edge gateway / embedded Linux SBC (Raspberry Pi, i.MX, …)        │
 │   Decisions, protocols, storage, UI, orchestration, security                 │
 │   .NET: full CoreCLR, System.Device.*, dotnet/iot, Avalonia     (§5)         │
 │   Resources: 512 MB–8 GB RAM, MMU, OS · Latency: ms, NOT guaranteed          │
 ├──────────────────────────── I2C / SPI / UART / CAN ──────────────────────────┤
 │ SPINAL CORD — the microcontroller (STM32, ESP32, RP2040, …)                  │
 │   Hard real-time: sampling, control loops, safety cut-offs, protocols        │
 │   Usually C/C++ (your old job). C# possible: nanoFramework, Meadow  (§6)     │
 │   Resources: 32 KB–1 MB RAM, no MMU · Latency: µs, guaranteed                │
 ├──────────────────────────────── wires / analog ──────────────────────────────┤
 │ NERVES & MUSCLES — sensors, actuators, power stages                          │
 │   ADCs, current/voltage monitors, temperature sensors, fans, relays          │
 └──────────────────────────────────────────────────────────────────────────────┘
```

**The key design rule:** *put each job at the lowest level that can do it, and no lower than it has to be.*

- A safety cut-off that must react in 50 µs **must** live in the spinal cord (MCU). A garbage collection pause in the brain could delay it.
- Deciding *which* VMs to shut down, in what order, with what credentials, **should** live in the brain (Linux + .NET). It needs networking, storage, and complex logic, and a few milliseconds of jitter don't matter.
- Showing a fleet of 10,000 devices on one screen belongs to society (the cloud).

You've already worked inside exactly this architecture. The MCU samples sensors and forwards frames, and the Linux board runs .NET and makes decisions. Now you have the name for it and can see its general shape.

### 1.1 The physical difference between MCU and MPU

This distinction decides which .NET can run where:

| | Microcontroller (MCU) | Microprocessor / SoC (MPU) |
|---|---|---|
| Example | STM32F4, ESP32, RP2040 | Raspberry Pi 4/5 (BCM2711/2712), NXP i.MX 8 |
| Memory | On-chip SRAM, **KB** to a few MB | External DRAM, **hundreds of MB to GB** |
| MMU | No (at most an MPU for protection) | **Yes**: virtual memory, processes |
| OS | None, or an RTOS (FreeRTOS, Zephyr, ChibiOS, ThreadX, NuttX) | Linux (or Windows IoT) |
| Timing | Deterministic | Best-effort (unless using real-time Linux patches) |
| Which .NET | nanoFramework, Meadow, TinyCLR (interpreters or Mono) | **Full .NET (CoreCLR)**, NativeAOT |

The **MMU line** is the big one. Full .NET assumes virtual memory, many threads, a file system, and hundreds of MB of RAM. Below that line you need a completely different runtime design (§2, §6).

---

## 2. Three ways to run C#: JIT, interpreter, AOT

Tag: 🟢 **OWN IT**. Every flavor of .NET on devices is one of these three strategies, or a mix. Once you know the trade-offs, the whole landscape makes sense.

Recall from Lecture 001 §5: C# compiles to **IL**. The question is always *what turns IL into something the CPU can execute, and when?*

```
                        C# source
                            │  Roslyn (at build time)
                            ▼
                       IL in assemblies
            ┌───────────────┼───────────────────────┐
            ▼               ▼                       ▼
     ① JIT (CoreCLR)   ② INTERPRETER         ③ AHEAD-OF-TIME (NativeAOT, bflat)
     IL → machine      a loop that reads     IL → machine code at BUILD time,
     code at RUN       IL opcodes and        linked with a small runtime into
     time, per method  executes them one     one native executable
                       by one (nanoCLR,      (no IL, no JIT on the device)
                       Mono interpreter)
```

| | ① JIT | ② Interpreter | ③ AOT |
|---|---|---|---|
| Startup | Slower (compile on first call) | Fast | **Fastest** |
| Steady-state speed | **Fastest** (optimizes with runtime profile data) | Slowest, often by an order of magnitude or more | Fast (no runtime profile, but no JIT cost) |
| Memory footprint | Largest (JIT + IL + metadata + code) | **Smallest runtime** (but IL must be stored) | Small, and only includes code that's actually used |
| Needs writable + executable memory | **Yes** (it writes machine code at run time) | No | No |
| Reflection / dynamic loading | Full | Mostly | **Restricted** (everything must be known at build time) |
| Where used on devices | Linux SBCs (Pi) | Microcontrollers (nanoFramework), iOS/WASM (Mono) | Linux SBCs for fast start and low memory; experimental bare metal |
| Firmware analogy | A Python-like VM that compiles hot functions | A bytecode VM, like a Forth or Lua interpreter on an MCU | Your normal GCC firmware build |

Three connections worth making:

1. **Why microcontrollers use interpreters:** a JIT needs RAM to hold generated code, and memory it can write to *and then execute*. Many MCUs run code from flash, have tens of KB of SRAM, and have no easy way to execute from RAM. An interpreter only needs the IL (compacted and stored in flash) plus a small engine.
2. **Why iOS and consoles use AOT or interpreters:** those platforms forbid writable+executable memory for security. That's the same constraint for a different reason. (This is why Mono's AOT and interpreter modes exist.)
3. **Why NativeAOT matters for the Pi:** a Pi app that must start in 100 ms at boot, or run in 30 MB of RAM, benefits hugely from AOT. The cost is the reflection restriction, which rules out some libraries (older serializers, some DI tricks).

---

## 3. The family tree: every .NET that ever touched hardware

Tag: 🔵 **CONTRACT**. Knowing the lineage tells you which projects are alive, which are dead, and why things are named the way they are.

```
 2000s                         2010s                              2020s (today)
 ─────                         ─────                              ─────────────
 .NET Micro Framework ─────────┬──► (Microsoft stops active       
 (Microsoft; watches, tiny     │     development, mid-2010s)
  devices; interpreter)        │
                               ├──► .NET nanoFramework (2017, community, ──► ALIVE. .NET Foundation project.
                               │     rewritten/modernized)                    ESP32, STM32, NXP, TI, SiLabs
                               │
                               └──► GHI TinyCLR OS (commercial) ──────────► Alive, commercial, slower pace
                                     (successor to GHI's NETMF boards;
                                      .NET Gadgeteer was an earlier cousin)

 Mono (open-source .NET for Linux, 2004) ──┬──► Xamarin → .NET MAUI (phones)
                                           ├──► Unity game engine scripting
                                           ├──► Blazor WebAssembly
                                           └──► Meadow OS (Wilderness Labs): ─────► Alive, commercial IoT platform
                                                Mono on the NuttX RTOS on               (MCU + Linux + desktop)
                                                an STM32F7 MCU

 .NET Framework (Windows) ──► .NET Core (2016, cross-platform, CoreCLR) ──► .NET 5…10 ──► ALIVE. Runs on Pi.
                                     │                                          │
                                     └── dotnet/iot: System.Device.* ──────────┘  (§5)
                                                                                │
                                              NativeAOT (.NET 7+) ──────────────┤  (§2, §7)
                                              bflat / zerosharp (community) ────┤  bare-metal experiments
                                              Samsung Tizen .NET (TVs, appliances) — major contributor
                                              of ARM32 and RISC-V port work     ─┘
```

Status as of September 2026 (details and sources in §16):

| Project | What it is | Status |
|---|---|---|
| **.NET (CoreCLR)** on Linux ARM | The real .NET on SBCs | ✅ Official. ARM64 and ARM32 Linux supported. **ARMv7 or newer only**, so the original Pi Zero / Pi 1 (ARMv6) can't run it, but the Pi Zero 2 W (ARMv8) can. |
| **dotnet/iot** (`System.Device.Gpio`, `Iot.Device.Bindings`) | GPIO/I2C/SPI/PWM APIs + 100+ device drivers | ✅ Active. v4.x targets .NET 8; libgpiod v2 support graduated from experimental in 4.2 (March 2025). |
| **.NET nanoFramework** | C# interpreter for MCUs | ✅ Active, .NET Foundation member, many daily contributors |
| **Meadow** (Wilderness Labs) | Commercial IoT platform: C# on MCU + Linux + desktop | ✅ Active, commercial |
| **TinyCLR OS** (GHI Electronics) | Commercial NETMF descendant | ⚠️ Alive, commercial; development pace slowed. Check before investing. |
| **.NET Micro Framework** | The original | ❌ Dead. Historical interest only. |
| **NativeAOT** | Official AOT compiler | ✅ Official, active |
| **bflat / zerosharp** | Community C# → bare-metal/UEFI experiments on NativeAOT | 🧪 Experimental, hobby-scale, very instructive |
| **RISC-V port of CoreCLR** | New CPU architecture for .NET | 🧪 Community-driven (largely Samsung engineers, for Tizen devices), "help wanted," not officially supported |
| **Azure Sphere** | Microsoft's secured MCU + Linux IoT platform (apps are written in C, not .NET) | ⚠️ Announced (March 2026) to retire in 2031. Don't build a career on it. |

---
## 4. Inside the runtime: the parts built for portability

Tag: 🔵 **CONTRACT**, with ⚫ internals. This is what you glimpsed: sections of the runtime that exist *only* so .NET can run on different operating systems and CPUs. Your bottom-up instinct is a real asset here. This is one of the few places in software where going to the bottom is the job.

### 4.1 A map of `dotnet/runtime`, by portability role

```
 dotnet/runtime/
 ├── src/coreclr/
 │   ├── vm/          The Virtual Machine: type loader, method calls, interop marshaller, threads.
 │   │                Mostly portable C++, plus small per-architecture assembly "stubs"
 │   ├── jit/         RyuJIT. Shared front/middle end (IL → IR → optimizations) PLUS
 │   │                per-ARCHITECTURE back ends: codegenxarch.cpp, codegenarm64.cpp,
 │   │                codegenarm.cpp, codegenloongarch64.cpp, codegenriscv64.cpp, and matching emitters
 │   ├── gc/          The garbage collector. Portable C++; talks to the OS through an interface
 │   ├── pal/         PAL = Platform Adaptation Layer: a Win32-like API implemented on Linux/macOS,
 │   │                so the VM (born on Windows) can run on Unix without rewriting everything
 │   └── nativeaot/   The small runtime linked into NativeAOT executables
 ├── src/mono/        The Mono runtime (JIT, AOT, and INTERPRETER): used for WebAssembly, iOS, Android
 ├── src/native/      C "shims" such as libSystem.Native: the thin portable layer that the
 │                    base class library calls for POSIX things (files, sockets, signals)
 ├── src/libraries/   The BCL (System.*), including System.Private.CoreLib's shared code
 ├── src/installer/   The host: the dotnet muxer, hostfxr, hostpolicy (Lecture 001 §4)
 └── docs/design/coreclr/botr/   "The Book of the Runtime": design docs written by the runtime team
```

### 4.2 Two kinds of portability

| | **OS portability** ("run on Linux, not just Windows") | **Architecture portability** ("run on RISC-V, not just x64/ARM64") |
|---|---|---|
| The problem | Different system calls, threads, files, signals, exceptions | Different instruction sets, registers, calling conventions, memory ordering |
| Where it lives | PAL, `src/native` shims, `#ifdef TARGET_UNIX` in the BCL | JIT back end + emitter, assembly stubs, unwinding, ABI rules, atomics |
| Firmware analogy | Porting an app from one RTOS to another | Porting a compiler back end or an RTOS kernel to a new CPU core |

### 4.3 What porting .NET to a new CPU actually requires

Read this as a list of **firmware skills in disguise**:

| Piece | What it means | The firmware skill it uses |
|---|---|---|
| **JIT code generator + emitter** | Turn the JIT's IR into real instructions, with the exact bit encodings | Reading an ISA manual; writing assembly |
| **ABI / calling convention** | Which registers hold arguments, how structs are passed, who saves what, and hard-float vs **soft-float** | Mixing C and assembly; `__attribute__((pcs(...)))`-style work |
| **Assembly stubs** | Small hand-written routines: call thunks, P/Invoke transitions, "write barriers" | Startup code, context switch routines |
| **GC write barrier** | Every time a reference is stored into the heap, a tiny routine marks a "card" so the GC knows which old objects might point at new ones. It must be *fast* and exist per CPU. | Tight, cycle-counted assembly |
| **Stack unwinding** | Walking the stack for exceptions and GC, using unwind info (DWARF CFI on Linux) | Hard-fault handlers that walk the stack |
| **Atomics + memory model** | `Interlocked`, `volatile`, and lock implementations. ARM and RISC-V have **weakly ordered** memory, unlike x86. Missing a barrier causes bugs that appear once a week. | `DMB`/`DSB` barriers, `LDREX`/`STREX` |
| **Thread context capture** | Saving and restoring all registers (for suspension, debugging, exceptions) | RTOS context switching |
| **CI on real hardware / QEMU** | Thousands of tests, run on the target | Hardware-in-the-loop test rigs |

This is why "going to the bottom" is an advantage here. Most application developers have never written a context switch or thought about memory barriers. You have.

### 4.4 Case study: the RISC-V port, happening right now

RISC-V is an open instruction set that is spreading fast in microcontrollers and, increasingly, application processors.

- A tracking issue for the CoreCLR RISC-V port has been open since **April 2023**. The main contributors are largely engineers working toward **Tizen** devices (Samsung's Linux-based OS for TVs and appliances, which runs .NET apps).
- Progress reported in the issue: the JIT "bring-up" tests reached a 100% pass rate in Debug mode on QEMU and a StarFive VisionFive 2 board, with the wider test suites passing at roughly 86–91%.
- The issue is labeled **"help wanted"** and **"up-for-grabs"**, and the port is **not officially supported** by Microsoft. A June 2025 SDK issue asking for official RISC-V support was still untriaged when checked.
- **Two days before this lecture was written** (September 23, 2026), a design proposal was filed for a NativeAOT **soft-float** RISC-V target (`lp64`, without the floating-point or atomic extensions). The motivation is zero-knowledge-proof virtual machines, not microcontrollers, but the technical shape of the work (no FPU, no atomics, minimal runtime) is exactly the constraint set of small embedded cores.

**The lesson:** the edge of this map is being drawn *right now*, in public GitHub issues, by a small number of people. That's the definition of a place where a newcomer with the right skills can matter.

### 4.5 Realistic ways to help at this level

You won't port a JIT back end in your spare time next month, and you don't need to. Entry points, in increasing difficulty:

1. **Run the test suites on real ARM or RISC-V boards** and report failures with minimal repros. Maintainers value real-hardware results.
2. **Benchmark on constrained hardware.** Startup time and memory of JIT vs ReadyToRun vs NativeAOT on a Pi (see idea I-3 in §11). Publish the numbers.
3. **Documentation fixes** for building and cross-compiling for ARM/RISC-V. What's obvious to maintainers is often missing for newcomers.
4. **Small, well-scoped fixes** labeled "up-for-grabs" in the areas above.
5. **Read the Book of the Runtime** alongside your fixes. It's the best free systems-programming education around.

---

## 5. Avenue A — .NET on embedded Linux

Tag: 🟢 for the layering model, 🔵 for the APIs. 🧭 **AVENUE: the largest market, and the closest to what you already do.**

### 5.1 How C# reaches a pin on Linux: the full stack

```
 YOUR CODE             var ina = new Ina219(i2cDevice); ina.ReadBusVoltage();
    │
 BINDINGS              Iot.Device.Bindings: 100+ drivers (sensors, displays, motors, CAN…)
    │                  Each one = a datasheet translated into C#
    │
 DEVICE APIs           System.Device.Gpio · System.Device.I2c · System.Device.Spi · System.Device.Pwm
    │                  Abstract classes: GpioController, I2cDevice, SpiDevice …
    │
 DRIVERS (in .NET)     UnixI2cDevice → /dev/i2c-N
    │                  LibGpiodDriver (v1/v2) → libgpiod → /dev/gpiochipN
    │                  (also board-specific drivers that map GPIO registers directly)
    │
 ═════════════════════ user space / kernel boundary (syscalls: open, ioctl, read, write) ════
    │
 LINUX KERNEL          i2c-dev character device, gpiolib, spidev
    │                  Bus drivers: i2c-bcm2835 (Pi's I2C controller), RP1 drivers (Pi 5)
    │                  Configured by the DEVICE TREE (+ overlays in config.txt)
    │
 HARDWARE              I2C controller peripheral → SDA/SCL pins → your sensor
```

Every layer is an interface in the Lecture 001 sense (§7 there). A binding like `Ina219` only depends on the abstract `I2cDevice`, so the same binding works on a Pi, on a USB-to-I2C adapter (dotnet/iot has FTDI FT4232H support, for example), or on a test fake.

### 5.2 What `I2cDevice` does underneath

```csharp
using System.Device.I2c;

var settings = new I2cConnectionSettings(busId: 1, deviceAddress: 0x40);
using I2cDevice dev = I2cDevice.Create(settings);      // opens /dev/i2c-1

Span<byte> reply = stackalloc byte[2];
dev.WriteRead([0x02], reply);                          // "select register 0x02, then read 2 bytes"
ushort raw = System.Buffers.Binary.BinaryPrimitives.ReadUInt16BigEndian(reply);
```

On Linux, the driver roughly does what you'd do in C:

```c
int fd = open("/dev/i2c-1", O_RDWR);
ioctl(fd, I2C_SLAVE, 0x40);          // ← yes, the ioctl that sets the TARGET address is named I2C_SLAVE
// then an I2C_RDWR ioctl with two messages: write {0x02}, read 2 bytes (a repeated-start transaction)
```

That naming is a classic trap: `I2C_SLAVE` in the Linux userspace API means "the address of the device *I'm talking to* as master." It has nothing to do with *being* a slave. This matters in §5.3.

### 5.3 The gap you've already met: Linux I2C **target** (slave) mode

This part is written about you specifically.

- `System.Device.I2c` models the Pi as the **controller** (master) only. There's no public API for the Pi to act as a **target** (slave) that other devices write to. (Worth confirming yourself: search dotnet/iot's issues for "slave" and "target" before proposing anything. My searches found no existing issue.)
- In Linux, target mode lives in the kernel's **I2C slave framework**, with in-kernel "backends" (such as an EEPROM emulator). There's no generic userspace character device for it the way `i2c-dev` exists for controller mode. It also needs a bus driver that supports target mode, and the Pi's standard `i2c-bcm2835` controller driver isn't one.
- On the Pi 0–4, target mode is possible through a **separate peripheral** (the BSC slave block). That's what the `pigpio` C library drives directly, and it's why teams reach for P/Invoke into `pigpio`, as you did.
- **`pigpio` does not run on the Raspberry Pi 5.** The Pi 5 moved GPIO and peripherals to a new I/O chip (RP1). An issue asking for Pi 5 support has been open on the pigpio repo since November 2023. Any product that depends on pigpio has a hardware-refresh problem waiting for it. (Something to raise, carefully, with your team if a Pi 5 is ever on the roadmap.)

**Why this is a real opening for you:** you understand the problem from all four sides. You've written the firmware of the device *acting as controller*, the .NET code *acting as target*, the interop layer between them, and the Linux constraints underneath. A well-researched **write-up** of "I2C target mode on Linux from .NET: options and trade-offs," possibly followed by an **API proposal** for dotnet/iot, is an unusually good fit (ideas I-5 and I-6 in §11). Do it on your own time and hardware, with no employer code (see §12.4).

### 5.4 Real time, garbage collection, and the split architecture

This comes up in every conversation about .NET on devices, so have a crisp answer:

- **.NET on Linux isn't hard real-time.** GC pauses (usually sub-millisecond to a few ms, occasionally more), JIT compilation on first call, and Linux scheduling itself all add jitter.
- **Mitigations** when soft real-time matters: allocation-free hot paths (`Span<T>`, pooling, structs), NativeAOT or ReadyToRun (no JIT jitter), GC configuration (⚫), dedicated threads, and the `PREEMPT_RT` Linux kernel (⚫).
- **The real answer is architecture:** anything with a hard deadline goes to the MCU (§1). The .NET side handles decisions and orchestration, where a few milliseconds don't matter. Your system already works this way, which makes it a good interview example of *choosing where computation lives*.

### 5.5 Turning a Pi app into a *product*

The gap between "runs on my Pi" and "ships in a thousand units" is mostly Linux and firmware knowledge. That's another advantage for you. The topics:

| Topic | What it involves | .NET angle |
|---|---|---|
| **OS image** | Raspberry Pi OS customization, or building a minimal distro with **Yocto** or **Buildroot** | Community Yocto layers exist for including the .NET runtime (e.g. `meta-dotnet-core`, `meta-mono`) |
| **Deployment form** | Shared runtime vs self-contained vs **NativeAOT** single binary | Lecture 001 §4.3. NativeAOT on `linux-arm64` gives fast boot and small RAM use. |
| **Service management** | systemd units, restart policies, watchdogs | `AddSystemd()`, graceful shutdown (Lecture 001 §8.7) |
| **Storage** | SD-card wear, read-only root filesystems, power-loss-safe writes | See `lectures/storage/001-crash_consistency.md`; SQLite journaling modes |
| **Updates** | A/B partitions, OTA (Mender, RAUC, SWUpdate), rollback | Your app must survive being restarted on a new version |
| **Security** | Secure boot, TPM, secrets on device, least-privilege users and groups (`gpio`, `i2c`) | Don't run as root just to reach `/dev/i2c-*`. Use groups and udev rules. |
| **Local UI** | Touchscreen kiosk without a desktop environment | **Avalonia** renders straight to Linux DRM/framebuffer, so a C# UI on a Pi needs no X11 or Wayland. |

---
## 6. Avenue B — C# on microcontrollers

Tag: 🔵 **CONTRACT**. 🧭 **AVENUE: small market, very contributor-friendly, and your firmware C skills are directly needed.**

### 6.1 .NET nanoFramework: how it works

```
 BUILD MACHINE                                  THE MCU (e.g. ESP32, STM32)
 ─────────────                                  ─────────────────────────────────
 C# ──Roslyn──► IL assembly (.dll)              ┌───────────────────────────────┐
                    │                           │ Your app (.pe files: IL)      │ ← deployed over
                    ▼                           │                               │   USB/serial
          Metadata Processor                    ├───────────────────────────────┤
          (shrinks the assembly into a          │ nanoCLR: IL INTERPRETER,      │
           compact ".pe" format for flash)      │ type system, small GC,        │
                    │                           │ threads, debugger agent       │
                    │                           ├───────────────────────────────┤
                    └── deploy + debug ───────► │ PAL / HAL (C/C++): GPIO, I2C, │
                        from Visual Studio or   │ SPI, UART, networking, …      │
                        VS Code (breakpoints    ├───────────────────────────────┤
                        on the real device)     │ RTOS: ESP-IDF/FreeRTOS (ESP32)│
                                                │ ChibiOS (STM32), ThreadX (NXP)│
                                                │ TI SimpleLink (TI)            │
                                                ├───────────────────────────────┤
                                                │ Silicon                       │
                                                └───────────────────────────────┘
```

Things to notice:

- **The firmware (nanoCLR + PAL/HAL + RTOS) is C/C++** and is built with CMake and Kconfig, like any modern embedded project. **Your app is C#.** The two are flashed separately, so you can redeploy the C# without reflashing the firmware.
- **It's an interpreter** (§2): small and portable, but much slower than native C for tight loops. Timing-critical work goes into native code.
- **Native interop is done at firmware build time:** you write C/C++ "interop libraries," compile them *into the firmware image*, and call them from C#. That's the MCU equivalent of P/Invoke, and it requires exactly your skill set.
- The `System.Device.*` API names mirror dotnet/iot, and many device bindings are shared or ported. **I2C *slave* support exists** on nanoFramework (an ESP32 bug in it was reported and fixed in 2024). So the idea of an I2C target API in .NET already has a precedent you can point to (§5.3).
- It's a **.NET Foundation** project with many active contributors, a Discord community, and a large surface of hardware targets. Contributions welcome: new board support, drivers, bug fixes in the C/C++ firmware, bindings in C#.

### 6.2 Meadow (Wilderness Labs)

- A **commercial** platform: C# on its own MCU boards (historically **Mono** running on the **NuttX** RTOS on an STM32F7), plus the same Meadow APIs on Raspberry Pi/Linux and desktop.
- Aimed at *products*, with over-the-air updates, cloud integration, security features, and a reference hardware "Project Lab" board.
- Big difference from nanoFramework: **Mono (with a full .NET Standard API surface)** instead of a tiny custom interpreter. That means a much richer API, but it needs a bigger MCU.
- Its driver library (Meadow.Foundation) is open source, so contributions are possible there too.

### 6.3 Comparison: which C#-on-MCU is which

| | nanoFramework | Meadow | TinyCLR OS |
|---|---|---|---|
| Model | Open source, community (.NET Foundation) | Commercial platform, open-source drivers | Commercial |
| Runtime | Custom IL interpreter (nanoCLR) | Mono | NETMF-descended interpreter |
| Hardware | Many vendors' boards (ESP32, STM32, NXP, TI, SiLabs) | Meadow boards; also Linux/desktop | GHI's own boards/modules |
| API breadth | Subset of .NET, tailored to MCUs | Broad (.NET Standard) | Subset |
| Best for | Learning, contributing, hobby-to-small-product | Commercial IoT products in C# | GHI hardware customers |
| Your contribution fit | ⭐⭐⭐⭐⭐ (C firmware *and* C#) | ⭐⭐⭐ (drivers) | ⭐ |

### 6.4 An honest take on C# on MCUs

- **Where it shines:** teams of C# developers who need a simple device; rapid prototyping; education; products where developer productivity beats per-unit silicon cost.
- **Where C/C++ (or Rust) still wins:** hard real-time, very low power, high volume (where cents of BOM matter), safety certification.
- **For you:** it's a superb **learning and contribution venue**. It's the one place where your firmware work and your .NET work are literally the same codebase. It's less likely to be a main career path on its own.

---

## 7. Avenue C — The frontier: C# with no runtime at all

Tag: ⚫ **BLACK BOX**, with one 🔵 you can use today (§7.3). 🧭 **AVENUE: research and blogging. High signal, low market.**

### 7.1 NativeAOT, pushed to the extreme

NativeAOT (§2) normally links your code with a small runtime: GC, exception handling, type system support. Two community projects showed you can go much further:

- **zerosharp** (Michal Strehovsky, a .NET runtime engineer): C# programs compiled with NativeAOT that run **without the standard runtime at all**, including bootable UEFI programs. You write your own minimal definitions of primitive types (`System.Object`, `System.Int32`, …) instead of using `System.Private.CoreLib`.
- **bflat** (same author): a Go-inspired C# compiler toolchain built from official .NET components. It can target bare metal and UEFI with a tiny standard library ("zerolib"). Executables can be around **4 KB**, versus hundreds of KB with the full runtime. The author has also written up building a **bootable, bare-metal game** in C# with it (December 2023).

What you give up in "zero" mode: **no garbage collector** (you can allocate, but never free), no exceptions, a tiny standard library, and minimal P/Invoke. What remains is C#'s syntax and type system compiled to native code. In other words, **C# used as a better C.**

As recently as December 2025, people were asking in the dotnet/runtime discussions about NativeAOT for bare-metal/UEFI targets. The answer from the community: technically feasible, but you must supply your own primitive-type shim, with zerosharp as the reference. So this is **not supported**, but it is **possible**, and it's an active area of curiosity.

### 7.2 Why this frontier is interesting for you

- It's an experiment only someone with a firmware background can properly evaluate: startup code, linker scripts, memory maps, interrupt vectors, and no allocator.
- Blog posts and talks in this space get read by .NET runtime engineers. For a Microsoft-oriented career, being known as "the person who got C# running on bare Cortex-A / RISC-V and wrote up exactly what broke" is distinctive.
- **Caution:** Cortex-M microcontrollers (Thumb-only instruction set, no MMU) aren't a NativeAOT target. The existing experiments are on UEFI PCs and application-class ARM/x64. Treat anything MCU-shaped as research, not a product plan.

### 7.3 The reverse direction you can use today: C calls C#

NativeAOT can build a **native shared library** (`.so`) whose exported functions are written in C#. C code calls them like any C function, with no .NET installed on the machine:

```csharp
// FrameCodec.csproj:  <PublishAot>true</PublishAot>  <AllowUnsafeBlocks>true</AllowUnsafeBlocks>
using System.Runtime.InteropServices;

public static unsafe class Exports
{
    [UnmanagedCallersOnly(EntryPoint = "frame_decode")]
    public static int FrameDecode(byte* frame, int len, byte* kind, ushort* raw)
    {
        if (frame == null || len != 3) return -1;
        *kind = frame[0];
        *raw  = (ushort)((frame[1] << 8) | frame[2]);
        return 0;
    }
}
```

```bash
dotnet publish -c Release -r linux-arm64 -p:NativeLib=Shared    # → FrameCodec.so
```

```c
/* any C program */
int frame_decode(const uint8_t *frame, int len, uint8_t *kind, uint16_t *raw);
```

Why it matters: it lets **one implementation** of logic (a protocol decoder, a calculation) be shared between C tools and .NET apps. That's a very practical bridge between firmware test tooling and .NET application code. Lecture 001 §11 was .NET calling C. This is C calling .NET, and it completes the picture.

---
## 8. Avenue D — Connectivity: from the board to the cloud

Tag: 🔵 **CONTRACT**. 🧭 **AVENUE: where devices meet Azure. It directly closes the "zero Azure" resume gap from your persona.**

### 8.1 The protocol ladder

Each level of the nervous-system map (§1) has its own protocols. .NET has solid libraries at every rung above the wire:

| Level | Protocols | .NET options |
|---|---|---|
| **On the board** | I2C, SPI, UART, GPIO, 1-Wire | `System.Device.*`, `System.IO.Ports.SerialPort` |
| **In the machine / vehicle** | **CAN** (SocketCAN on Linux) | dotnet/iot `SocketCan` binding (Linux) |
| **On the factory floor** | **Modbus** (RTU/TCP), **OPC UA** | Community Modbus libraries; **the OPC Foundation's official OPC UA reference stack is written in C#** (`UA-.NETStandard`) |
| **Device → cloud** | **MQTT**, HTTPS, AMQP | **MQTTnet** (widely used, .NET Foundation), Azure IoT device SDK |
| **Service ↔ service** | gRPC, REST | Lecture 001 §13 |

Two of these deserve a closer look:

- **MQTT** is *the* device-to-cloud protocol: publish/subscribe through a broker, with topics like `site7/rack3/psu2/voltage`, very small overhead, and quality-of-service levels. If you learn one IoT protocol, learn this one.
- **OPC UA** is the lingua franca of industrial automation (PLCs, SCADA, MES). Its reference implementation being C# makes .NET a first-class citizen in factories, a large and under-appreciated market.

### 8.2 Microsoft's device-to-cloud stack (as of 2026)

| Service | What it does | Status / note |
|---|---|---|
| **Azure IoT Hub** | Managed cloud gateway: device identity, telemetry ingestion, commands, device twins | Core service. A good first target for a portfolio project. |
| **Azure IoT Edge** | Runs cloud-managed **containers ("modules")** on an edge device. .NET worker services are a natural fit. | Established |
| **Azure IoT Operations** | Newer edge platform on **Azure Arc–enabled Kubernetes**, with a built-in **MQTT broker** and data pipelines, for industrial sites | Generally available since late 2024. The strategic direction for industrial edge. |
| **Azure Sphere** | Secured MCU/Linux chip + OS + cloud service | Retiring in 2031 (announced March 2026) |

### 8.3 The shape of a device-to-cloud system you could build

```
 MCU (C)  ──I2C/UART──►  Pi: .NET worker ──MQTT/TLS──► Azure IoT Hub ──► Stream/Functions ──► storage/dashboards
 samples                 validate, derive,            device identity,   (Lecture 001's
 sensors                 buffer offline, act locally  commands back down  ASP.NET/Azure world)
```

The hard, interesting parts are all edge problems you're well equipped for: **offline buffering** when the network drops, **clock sync** (whose timestamp is true?), **backpressure**, **device identity and certificates**, and **safe remote commands** (a cloud message that can shut down a machine had better be authenticated).

---

## 9. Avenue E — The hidden market: test and manufacturing automation

Tag: 🔵 **CONTRACT**. 🧭 **AVENUE: often overlooked, and possibly the most immediately useful to your current employer.**

Every hardware company has a second software world that isn't the product: **the software that tests the product.**

- **Hardware-in-the-loop (HIL) rigs:** a PC or Pi drives a board under test, injects signals, reads responses, and asserts behavior.
- **Manufacturing test stations:** each unit off the line is powered, programmed, calibrated, and checked, with results logged against its serial number.
- **Lab instrument control:** power supplies, electronic loads, oscilloscopes, and DMMs, driven over USB/Ethernet/serial with **SCPI** text commands (`MEAS:VOLT?`), often through a VISA driver layer.

A lot of this is written in C# (sometimes alongside LabVIEW, TestStand, or Python) because it runs on Windows benches and needs UIs, databases, and reliability. It needs **exactly** the combination of skills you now have: understanding the board *and* writing a well-structured .NET application with DI, logging, config, tests, and a Generic Host.

The Lecture 001 ideas map one-to-one:

| Test-station need | Lecture 001 concept |
|---|---|
| Swap a real instrument for a simulator | Interfaces + DI (`IPowerSupply` → `ScpiPowerSupply` / `SimulatedPowerSupply`) |
| Per-station settings (COM ports, limits) | Configuration + Options, with validation on start |
| Traceable results per unit | Structured logging + a database (EF Core) |
| Run a test sequence while the UI stays responsive | async/await, `CancellationToken` for the operator's Abort button |
| Talk to a vendor DLL | P/Invoke / raw assembly references |

If your hardware department runs manual or ad-hoc test procedures, a well-built .NET test tool could be the most visible thing you do there next year. It could also be your strongest bridge between the two departments you've now worked in. (It would be company work, done on company time under company rules. It isn't an open-source idea.)

---
## 10. Where you are uniquely positioned (an honest analysis)

### 10.1 The rare intersection

```
            FIRMWARE / HARDWARE                         .NET APPLICATION ENGINEERING
      (datasheets, I2C/SPI, registers,            (C#, DI, Generic Host, async, EF,
       RTOS, ISRs, memory, ABIs)                    ASP.NET, testing, CI/CD)
                 ╲                                    ╱
                  ╲        ┌──────────────────┐      ╱
                   ╲───────│   YOU ARE HERE   │─────╱
                    ╲      │  (+ Linux, the   │    ╱
                     ╲     │  interop layer   │   ╱
                      ╲    │  between them)   │  ╱
                       ╲   └──────────────────┘ ╱
                        ╲         │            ╱
                         ╲        ▼           ╱
                    Device systems end to end: board → edge → cloud
```

Each side of this diagram is a large population. The overlap is small. Being in a small overlap between two large, valuable groups is the classic recipe for being hard to replace.

### 10.2 Avenue scorecard

Scores are 1–5 (5 = best for you). "Learning cost" is inverted: 5 means cheap for you to learn.

| Avenue | Fit with your skills | Learning cost | Market demand | Value toward Microsoft SE2 | Open-source openings | Main risk |
|---|---|---|---|---|---|---|
| **A. Embedded Linux + .NET** (§5) | 5 | 5 | 4 | 3 | 4 (dotnet/iot) | Low. The closest to your current job. |
| **B. C# on MCUs** (§6) | 5 | 3 | 2 | 2 | 5 (nanoFramework) | Niche; better as a contribution venue than a career |
| **C. No-runtime frontier** (§7) | 4 | 1 | 1 | 4 (visibility with runtime folks) | 3 | Time sink with no product at the end |
| **Runtime ports / ARM & RISC-V quality** (§4) | 4 | 1 | 2 | 5 | 4 ("help wanted") | Steep. Needs sustained time. |
| **D. Device → Azure connectivity** (§8) | 3 | 3 | 5 | 5 | 3 | Low. Mostly learning Azure. |
| **E. Test & manufacturing automation** (§9) | 5 | 5 | 4 | 2 | 1 | Low. Company work, not public portfolio. |
| **F. .NET tooling for embedded devs** (idea I-10) | 4 | 2 | 2 | 3 | 4 | Moderate. Needs a real user base. |

How to read it:

- **A + D together** is the strongest *career* combination: large market, closest to your experience, and it fixes the Azure gap. That's the "device systems end to end" story.
- **B or the runtime row** is the best *public contribution* venue: where your firmware skills are rare and visible. Pick **one**, not both.
- **E** is the best *at-work* opportunity, and it strengthens your standing in both departments.
- **C** is a fascinating weekend project and blog post. Treat it as dessert, not dinner.

### 10.3 An adjacent area worth knowing about (not .NET)

Your current domain (power and telemetry monitoring of server hardware, graceful shutdown) is closely related to a whole industry segment: **datacenter hardware management**. That covers baseboard management controllers (BMCs), rack managers, power shelves, and the open-source **OpenBMC** firmware project (Linux-based, mostly C++). Large cloud providers, Microsoft included, build and run this kind of infrastructure at huge scale. It isn't a .NET avenue, but it's where "firmware + Linux + power telemetry" experience is directly valuable. It's worth knowing the vocabulary for interviews: BMC, IPMI, **Redfish** (the modern REST API for server management), PMBus (the power-supply management bus, built on I2C and SMBus).

### 10.4 Honest cautions

1. **Don't spread across all seven rows.** Your persona already records the fear of being expected to master many unrelated domains at once. The antidote is *choosing*. §13 makes a choice for you. Adjust it, but keep it narrow.
2. **LLM_Monitor is your AI-engineering pillar.** This is your devices pillar. Two pillars is a strong portfolio. Three is usually a distracted one.
3. **Employer IP is real.** Several ideas here are close to your day job's domain. Read §12.4 before starting any public work in this space.

---

## 11. The idea catalog

Each idea has an ID so the roadmap (§13) can refer to it. "Signal" = how much it tells a hiring manager.

### Weekend-sized (1–2 days)

| ID | Idea | You'll learn | Deliverable | Signal | First step |
|---|---|---|---|---|---|
| **I-1** | Read a real sensor on a Pi with a dotnet/iot binding, then read that binding's source side by side with the chip's datasheet | The §5.1 stack, top to bottom | Notes + a small repo | Low (foundation) | `dotnet add package Iot.Device.Bindings` on a Pi you own |
| **I-2** | Build dotnet/iot locally, run a sample, and fix one documentation gap you hit | The contribution workflow (§12) | Your **first merged PR** to a `dotnet/` repo | Medium: "contributor to dotnet/iot" | Clone it; read its `Documentation/` folder |

### Month-sized

| ID | Idea | You'll learn | Deliverable | Signal | First step |
|---|---|---|---|---|---|
| **I-3** | **Benchmark JIT vs ReadyToRun vs NativeAOT on a Raspberry Pi**: startup time, memory (RSS), throughput, GC pause times, for a worker and a small web API | Lecture 001 §4–5 made concrete; measurement discipline; `dotnet-counters` | Blog post + reproducible repo with numbers | **High**: performance data from real hardware is rare and widely shared | Pick a Pi model; write the measurement plan before the code |
| **I-4** | Write a **new device binding** for dotnet/iot, for a chip you know that isn't covered yet | Datasheet → API design; UnitsNet; tests with a fake `I2cDevice` | A merged binding with README, sample, and tests | Medium–high | Check the bindings list; comment on the repo before starting |
| **I-5** | Write "**I2C target (slave) mode from .NET on Linux: the options**": pigpio's BSC peripheral (Pi 0–4), kernel slave backends, using an MCU as a bridge, USB adapters, and what changes on the Pi 5 | Linux I2C internals; framing trade-offs clearly | A technical write-up | High: shows you can map a problem space | Build a demo on your *own* hardware (§12.4) |
| **I-9** | A **frame codec in C#, exported as a C library** with NativeAOT, used both by a C test program and by a .NET app (§7.3) | Reverse interop, NativeAOT constraints | Small repo + write-up | Medium | The §7.3 snippet |

### Quarter-sized

| ID | Idea | You'll learn | Deliverable | Signal | First step |
|---|---|---|---|---|---|
| **I-6** | An **API proposal** for an I2C target abstraction in dotnet/iot, using nanoFramework's API as precedent (§6.1), with a prototype built *outside* the repo first | .NET API design and review (§12.3), cross-platform abstraction | A GitHub API proposal issue, maybe an accepted API | **Very high** if accepted | Open a *discussion* first to test maintainer interest, after I-5 |
| **I-7** | A **nanoFramework** contribution: a driver, a board support fix, or an interop-library tutorial, on an ESP32 | MCU runtime internals; C firmware + C# in one codebase | Merged PRs | Medium–high | Buy an ESP32 dev board; flash with `nanoff` |
| **I-8** | **The end-to-end portfolio system:** C firmware on an RP2040/STM32 → I2C/UART → Pi .NET worker (Generic Host, `Channel<T>`, SQLite offline buffer, derived alarms) → MQTT → **Azure IoT Hub** → small ASP.NET dashboard; infrastructure as code; GitHub Actions CI | Everything in Lecture 001 and §8, plus Azure | A flagship repo + architecture write-up | **Very high**: "device systems end to end, with Azure" | Choose a domain *unrelated to work*: home energy, greenhouse, weather station |
| **I-10** | A **Roslyn source generator** that turns a register-map description (YAML, or CMSIS-SVD files from chip vendors) into typed C# register accessors (and optionally C headers) | Source generators; MSBuild; API design | NuGet package + docs | Medium–high, and genuinely novel | Read the Roslyn source generator cookbook; pick one real chip |
| **I-11** | An **Avalonia touchscreen HMI** on a Pi, rendering directly to DRM with no desktop, showing live telemetry from I-8 | UI in .NET, MVVM, embedded display pipeline | Demo video + repo | Medium | Avalonia's embedded Linux guide |

### Long-term / depth

| ID | Idea | You'll learn | Deliverable | Signal |
|---|---|---|---|---|
| **I-12** | Run dotnet/runtime test suites on real ARM64 and/or RISC-V boards; report failures with minimal repros; take one "up-for-grabs" issue | Runtime internals (§4), the Book of the Runtime | Issues and PRs on `dotnet/runtime` | **Very high** for Microsoft |
| **I-13** | Bare-metal C# with bflat on UEFI/QEMU: what firmware concepts map, what breaks | §7 in practice | A blog series | High (niche, memorable) |
| **I-14** | *At work, with permission:* a .NET hardware test-station framework for your hardware department (§9) | Real users, real requirements | Internal tool | High internally; a strong interview story |
| **I-15** | Turn this lecture series into a public "**firmware engineer's field guide to .NET**" | Teaching = mastery | Blog/series from this repo | Medium, and it compounds |

---
## 12. How contributing to .NET open source actually works

Tag: 🟢 **OWN IT**. The process is the same across most of the repos in this lecture.

### 12.1 The repos that matter for this domain

| Repo | What's there | Language(s) |
|---|---|---|
| `dotnet/runtime` | CoreCLR, JIT, GC, Mono, NativeAOT, the BCL | C++, C#, assembly |
| `dotnet/iot` | `System.Device.*` and `Iot.Device.Bindings` | C# |
| `nanoframework/nf-interpreter` | The nanoCLR firmware, PAL/HAL, target boards | C/C++ |
| `nanoframework/*` (lib-…, System.Device.…) | Class libraries and bindings for nanoFramework | C# |
| `OPCFoundation/UA-.NETStandard` | The OPC UA reference stack | C# |
| MQTTnet | The most widely used .NET MQTT library (.NET Foundation) | C# |

### 12.2 The mechanics

```
 1. Find an issue       labels: "help wanted", "up-for-grabs", "good first issue", "documentation"
        │
 2. COMMENT FIRST       "I'd like to take this. My plan is X." Wait for a maintainer to respond.
        │               (This avoids wasted work on something they'd reject.)
        ▼
 3. Fork → branch → change → build → test locally
        │
 4. Open a PR           Describe what and why; link the issue; keep it small.
        │               On your first PR to a dotnet/ repo, a bot asks you to agree to
        │               a Contributor License Agreement (CLA). It's a one-time step.
        ▼
 5. CI runs             Must be green. On dotnet/runtime, CI is huge; ask when a failure looks unrelated.
        │
 6. Review              Expect change requests. That's normal and a sign of engagement.
        ▼
 7. Merge
```

### 12.3 API proposals: how new public APIs get into .NET

New public APIs don't start as PRs. They start as **proposals**. On `dotnet/runtime` the flow is:

```
 issue using the API-proposal template   (label: api-suggestion)
      → maintainers refine it            (label: api-ready-for-review)
      → API review meeting               (often livestreamed; notes posted to the issue)
      → decision                         (label: api-approved, or back for changes)
      → THEN someone implements it
```

`dotnet/iot` runs a similar, lighter review. A good proposal contains:

1. **Background & motivation:** the real problem (e.g., "Linux SBCs often need to act as I2C targets for MCUs; today this requires P/Invoke into board-specific C libraries").
2. **API shape:** the proposed types and members, as C# signatures.
3. **Usage examples:** how a user would write code with it.
4. **Alternatives considered:** and why they're worse.
5. **Risks:** platform support gaps (e.g., "not implementable on the Pi 5 without X"), breaking changes.

This format is also good practice for design-doc writing at any large company. It's essentially what Microsoft engineers write internally.

### 12.4 Employer considerations (read before any public work)

This isn't legal advice, but these are the questions to answer *before* publishing work near your day-job domain:

- **Your employment agreement:** most have an **IP-assignment clause** (what you create may belong to the employer, sometimes even off-hours if it relates to the business) and sometimes a **moonlighting** or **outside-activities** clause.
- **Open-source policy:** many companies have a process for approving employee open-source contributions. Asking first is normal and usually welcomed.
- **Clean-room discipline:** use your **own hardware, own time, own accounts**. Never reuse company code, internal documents, or product-specific designs. Generic knowledge ("I2C target mode is hard on Linux") is yours. Your employer's specific implementation isn't.
- **Pick domains that don't overlap** for portfolio projects (I-8 suggests home energy or a greenhouse, not server power).
- When in doubt, **ask your manager or legal** in writing. Being the engineer who asked is far better than being the one who didn't.

---

## 13. A recommended path

You asked me to make decisions, so here's one. It's built on §10's conclusion: **A + D as the career core, one contribution venue for public signal, E at work.** Adjust freely, but change one thing at a time.

| When | Focus | Ideas | Outcome by the end |
|---|---|---|---|
| **Now → end of 2026** | Foundations + first contribution | Finish Lecture 001's lab; **I-1**, **I-2**; start **I-3** | First merged PR to a `dotnet/` repo; a Pi running your own .NET code against real sensors |
| **Q1 2027** | Publish + propose | Finish **I-3** (publish the benchmark); **I-5** write-up; **I-4** binding | Two public write-ups; a binding in review |
| **Q2 2027** | The flagship | **I-8** end to end, with Azure IoT Hub | The portfolio centerpiece. The "zero Azure" gap is closed. |
| **Q3 2027** | Choose depth | *Either* **I-12** (runtime) *or* **I-7** (nanoFramework), whichever excited you more in Q1–Q2. Optionally **I-6** if maintainers were receptive to I-5. | Sustained contributions in one venue |
| **Throughout** | At work | Look for an **I-14** opening; ask first | A visible bridge between your two departments |

How it fits your resume story:

> *"Embedded firmware engineer who moved into .NET application development. I build device systems end to end: C firmware, .NET services on embedded Linux with native interop, and cloud connectivity on Azure. Contributor to dotnet/iot, with published performance research on .NET on ARM."*

That sentence is true-able within a year, and it's distinctive.

---

## 14. Concept connections: firmware ↔ .NET on devices

| You already know (firmware) | Its twin in this lecture | Section |
|---|---|---|
| Spinal cord vs brain: interrupt-level vs main-loop work | MCU vs Linux SBC split | §1 |
| No MMU, static memory | Why full .NET can't run on an MCU | §1.1 |
| Bytecode VMs on MCUs (Forth, Lua, MicroPython) | nanoCLR IL interpreter | §2, §6 |
| A GCC cross-compile for a target | NativeAOT for `linux-arm64` | §2, §5.5 |
| Porting an RTOS or compiler to a new core | Porting CoreCLR (JIT back end, stubs, ABI, barriers) | §4.3 |
| RTOS abstraction layers | CoreCLR's PAL; nanoFramework's PAL/HAL | §4.1, §6.1 |
| Memory barriers (`DMB`), `LDREX`/`STREX` | .NET memory model on weakly ordered CPUs | §4.3 |
| Context switch code | Thread context capture in the runtime | §4.3 |
| A vendor HAL + driver for a sensor | A dotnet/iot binding on `I2cDevice` | §5.1 |
| `ioctl` on `/dev/i2c-1` | `UnixI2cDevice` internals | §5.2 |
| Being the I2C slave on an MCU | The missing I2C *target* API on Linux .NET | §5.3 |
| Hard real-time deadlines | GC/JIT jitter and the split architecture | §5.4 |
| Flashing images, A/B bootloaders | OS images, Yocto, OTA | §5.5 |
| Compiling native code into firmware | nanoFramework interop libraries | §6.1 |
| Startup code with no C library | bflat "zero" mode, zerosharp | §7.1 |
| Exporting a C API from a library | NativeAOT `UnmanagedCallersOnly(EntryPoint=…)` | §7.3 |
| A framed serial protocol | MQTT topics, OPC UA nodes, CAN frames | §8.1 |
| Bench test fixtures | .NET HIL and test-station software | §9 |

---

## 15. Self-check questions

1. Where does a 50 µs safety cut-off belong in the nervous-system map, and why can't it live in the .NET app? (§1, §5.4)
   <details><summary>Answer</summary>In the MCU (spinal cord). .NET on Linux has non-deterministic latency (GC pauses, JIT, OS scheduling), so it can't guarantee a microsecond deadline.</details>

2. What single hardware feature best predicts whether full .NET (CoreCLR) can run on a chip? (§1.1)
   <details><summary>Answer</summary>An MMU (together with the RAM and OS support that come with application processors). Without virtual memory and hundreds of MB of RAM, you need an interpreter-style runtime like nanoFramework.</details>

3. Why do microcontroller C# runtimes interpret IL instead of JIT-compiling it? (§2)
   <details><summary>Answer</summary>A JIT needs RAM for generated code and memory that's writable and then executable. MCUs have tiny SRAM and usually execute from flash. An interpreter only needs the IL plus a small engine.</details>

4. What does NativeAOT give up in exchange for fast startup and a small footprint? (§2)
   <details><summary>Answer</summary>Dynamic features: unrestricted reflection, runtime code generation, loading arbitrary assemblies. Everything must be known at build time.</details>

5. Name three parts of the runtime that must be rewritten per CPU architecture. (§4.3)
   <details><summary>Answer</summary>Any three of: JIT code generator/emitter, ABI/calling-convention handling, assembly stubs, GC write barrier, unwinding support, atomics/memory barriers, thread context capture.</details>

6. What's the difference between OS portability and architecture portability in the runtime? (§4.2)
   <details><summary>Answer</summary>OS portability deals with system calls, threads, files, and signals (PAL, native shims). Architecture portability deals with instructions, registers, calling conventions, and memory ordering (JIT back ends, stubs, barriers).</details>

7. What does the Linux `I2C_SLAVE` ioctl actually do? (§5.2)
   <details><summary>Answer</summary>It sets the address of the target device you're talking to *as the controller*. Despite the name, it doesn't make the Linux machine a slave.</details>

8. Why do Pi projects that act as an I2C target often use pigpio, and what's the risk? (§5.3)
   <details><summary>Answer</summary>The standard Linux I2C controller driver on the Pi doesn't do target mode. pigpio drives the separate BSC slave peripheral directly. The risk: pigpio doesn't run on the Pi 5 (new RP1 I/O chip).</details>

9. How does nanoFramework let C# call custom C code? (§6.1)
   <details><summary>Answer</summary>Through interop libraries written in C/C++ and compiled into the firmware image, exposed to C# as methods backed by native implementations.</details>

10. What's the main thing you lose in bflat's "zero" mode? (§7.1)
    <details><summary>Answer</summary>The garbage collector (and exceptions, most of the standard library, and full marshalling). It's essentially C# as a better C.</details>

11. How can a C program call a function written in C#, with no .NET installed? (§7.3)
    <details><summary>Answer</summary>Publish the C# as a NativeAOT shared library, with the function marked <code>[UnmanagedCallersOnly(EntryPoint = "name")]</code>. C links or loads it like any <code>.so</code>.</details>

12. Why is OPC UA relevant to .NET developers in particular? (§8.1)
    <details><summary>Answer</summary>It's the dominant industrial-automation interoperability standard, and the OPC Foundation's reference implementation is a C#/.NET stack.</details>

13. What four things should a good .NET API proposal contain? (§12.3)
    <details><summary>Answer</summary>Background/motivation, the API shape (signatures), usage examples, alternatives considered (plus risks).</details>

14. Before publishing a write-up related to your day-job domain, what should you check? (§12.4)
    <details><summary>Answer</summary>Your employment agreement's IP-assignment and outside-activity clauses, your company's open-source policy, and that you used only your own hardware, time, and generic knowledge. Ask your manager or legal in writing when unsure.</details>

15. According to §10, which avenue combination best serves the career goal, and which serves public contribution? (§10.2)
    <details><summary>Answer</summary>Career: embedded Linux + .NET (A) combined with device-to-Azure connectivity (D). Public contribution: one of nanoFramework (B) or runtime port/quality work, not both.</details>

---

## 16. Sources and further reading

Status claims in this lecture were checked on 2026-09-25 against these sources. Re-check before relying on them.

**.NET on Linux devices**
- [dotnet/iot repository](https://github.com/dotnet/iot) · [releases](https://github.com/dotnet/iot/releases) · [libgpiod v2 support issue](https://github.com/dotnet/iot/issues/2179) · [device bindings list](https://github.com/dotnet/iot/blob/main/src/devices/README.md)
- [.NET IoT documentation (Microsoft Learn)](https://learn.microsoft.com/en-us/dotnet/iot/intro)
- [ARMv6 (Pi Zero / Pi 1) support issue in dotnet/runtime](https://github.com/dotnet/runtime/issues/7764)
- [pigpio: "will not run on a Pi 5" issue](https://github.com/joan2937/pigpio/issues/589)
- [Avalonia on embedded Linux](https://docs.avaloniaui.net/docs/platform-specific-guides/embedded-linux/)
- [Yocto wiki: embedded Linux .NET applications](https://wiki.yoctoproject.org/wiki/Building_and_running_embedded_Linux_.NET_applications_from_first_principles) · [meta-dotnet-core](https://github.com/RDunkley/meta-dotnet-core) · [meta-mono](https://github.com/DynamicDevices/meta-mono)

**Microcontrollers**
- [.NET nanoFramework](https://nanoframework.net/) · [nf-interpreter (nanoCLR, PAL/HAL)](https://github.com/nanoframework/nf-interpreter) · [Class library architecture](https://docs.nanoframework.net/content/architecture/class-libraries.html)
- [nanoFramework I2C slave issue (fixed)](https://github.com/nanoframework/Home/issues/1494)
- [Wilderness Labs / Meadow](https://www.wildernesslabs.co/) · [Meadow.OS on STM32F7: NuttX + Mono](https://www.mail-archive.com/dev@nuttx.apache.org/msg03553.html)
- [GHI Electronics TinyCLR](https://www.ghielectronics.com/tinyclr/) · [.NET Micro Framework (Wikipedia)](https://en.wikipedia.org/wiki/.NET_Micro_Framework)

**Runtime internals and the frontier**
- [CoreCLR RISC-V port tracking issue](https://github.com/dotnet/runtime/issues/84834) · [SDK RISC-V support request](https://github.com/dotnet/sdk/issues/49594) · [NativeAOT soft-float RISC-V design proposal (Sept 2026)](https://github.com/dotnet/runtime/issues/134558) · [RISE project entry](https://github.com/riseproject-dev/language-runtimes-wg/issues/4)
- [zerosharp](https://github.com/MichalStrehovsky/zerosharp/blob/master/README.md) · [bflat](https://github.com/MichalStrehovsky/bflat) · [Bare-metal bootable game in C#](https://migeel.sk/blog/2023/12/08/building-bare-metal-bootable-game-for-raspberry-pi-in-csharp/) · [NativeAOT bare-metal discussion (Dec 2025)](https://github.com/dotnet/runtime/discussions/122661)
- [Native code interop with Native AOT (Microsoft Learn)](https://learn.microsoft.com/en-us/dotnet/core/deploying/native-aot/interop) · [NativeLibrary sample](https://github.com/dotnet/samples/blob/main/core/nativeaot/NativeLibrary/README.md)
- [API review process (dotnet/runtime)](https://github.com/dotnet/runtime/blob/main/docs/project/api-review-process.md)
- The Book of the Runtime: `docs/design/coreclr/botr/` in [dotnet/runtime](https://github.com/dotnet/runtime)

**Connectivity and cloud**
- [OPC UA .NET Standard reference stack](https://github.com/opcfoundation/ua-.netstandard)
- [Azure IoT Operations GA announcement](https://techcommunity.microsoft.com/blog/iotblog/azure-iot-operations-now-generally-available/4282445) · [Azure IoT Operations MQTT broker](https://learn.microsoft.com/en-us/azure/iot-operations/manage-mqtt-broker/overview-broker)
- [Azure Sphere retiring in 2031 (March 2026)](https://techcommunity.microsoft.com/blog/iotblog/azure-sphere-is-retiring-in-2031---what-you-need-to-know/4504225)

---

*End of Lecture 002. Suggested next: pick idea I-1 this weekend, and keep Lecture 001's lab going in parallel. The planned "Generic Host & DI, in depth" lecture moves to 003.*
