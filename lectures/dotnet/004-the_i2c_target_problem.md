2026_09_25_20_09-(The-I2C-Target-Problem)

# Lecture 004 — The I2C Target Problem: Evaluating a Direction, and Mapping Embedded Linux Systems Programming for .NET

> **For:** Timothy Lee Grant
> **Date:** 2026-09-25
> **Prerequisites:** Lecture 001 (the .NET map, P/Invoke in §11), Lecture 003 (layering and "where does this responsibility belong?").
> **Replaces the direction of:** Lecture 002's microcontroller and bare-metal avenues. Your clarification narrows the domain to **embedded Linux**, and this lecture goes deep on exactly that.
>
> **Why this lecture:** You looked back at a problem you once accepted as "just how things are" (C# can't make a Raspberry Pi act as an I2C **target**, so you had to P/Invoke into a C library) and asked *why*, and whether you could fix it. That's the right instinct. This lecture answers your questions honestly: whether it's a good direction, what it actually involves, what it teaches, how it fits the Microsoft goal, and how to start without falling into a rabbit hole.

---

## Table of Contents

- [0. Direct answers first](#0-direct-answers-first)
- [1. What ".NET" actually is, and why `System.Device.*` lives outside dotnet/runtime](#1-what-net-actually-is-and-why-systemdevice-lives-outside-dotnetruntime)
- [2. The real diagnosis: why a Pi can't be an I2C target from C# today](#2-the-real-diagnosis-why-a-pi-cant-be-an-i2c-target-from-c-today)
- [3. Your mental model, checked item by item](#3-your-mental-model-checked-item-by-item)
- [4. The hardware landscape, model by model](#4-the-hardware-landscape-model-by-model)
- [5. The Linux I2C target framework](#5-the-linux-i2c-target-framework)
- [6. Four ways to solve it, and where .NET fits](#6-four-ways-to-solve-it-and-where-net-fits)
- [7. The concept map: everything this domain involves](#7-the-concept-map-everything-this-domain-involves)
- [8. Does this make you a better backend engineer?](#8-does-this-make-you-a-better-backend-engineer)
- [9. Market, career, and the Microsoft question](#9-market-career-and-the-microsoft-question)
- [10. "Why would they need me if AI can fix everything?"](#10-why-would-they-need-me-if-ai-can-fix-everything)
- [11. Your first contribution: getting past the fear](#11-your-first-contribution-getting-past-the-fear)
- [12. Machines and hardware: what you need](#12-machines-and-hardware-what-you-need)
- [13. The project plan: phases, time boxes, exit criteria](#13-the-project-plan-phases-time-boxes-exit-criteria)
- [14. Self-check questions](#14-self-check-questions)
- [15. Sources](#15-sources)

---

## 0. Direct answers first

**"Is my orientation correct?"** — **Mostly yes, with two important corrections.**

✅ Right:
- Embedded **Linux** is a much more useful place to be than microcontroller C# or bare-metal .NET. Lecture 002 over-weighted those. Your instinct to narrow is correct.
- The I2C target problem is **real**, **unsolved in .NET's standard device libraries**, and sits exactly where your experience is: firmware on one side of the bus, .NET on the other, Linux in between.
- Working on it trains skills that matter far beyond I2C (§8).

⚠️ Correction 1: **this isn't a runtime problem.** The .NET runtime (the part that runs your code: JIT, garbage collector, and so on) has nothing to do with it and needs no changes. The gap sits in three other places: the **hardware** (which Pi peripheral can act as a target), the **Linux kernel** (whether a driver exposes it), and a **.NET library** (`System.Device.I2c` in dotnet/iot has no API for it). Section 2 walks through this layer by layer. Seeing it clearly is itself a design lesson straight out of Lecture 003: *put each responsibility in the layer that owns it.*

⚠️ Correction 2: **the market for this specific feature is small.** Relatively few products need a Linux board to be an I2C target. The *domain* (embedded Linux + .NET) is mid-sized, and general backend/cloud engineering is far larger. So treat this as a **depth project**: a bounded, high-learning, high-signal piece of work. It isn't a career lane. Your career lane should stay **backend/cloud .NET engineer with unusual systems depth** (§9).

**"Is it a good direction for my time?"** — **Yes, at the right dose:** about 3 hours a week for 8–10 weeks, in phases that each produce something valuable on their own, with explicit exit criteria (§13). It replaces the generic "write a binding" idea from Lecture 002 as your dotnet/iot contribution vehicle. It doesn't replace LeetCode, design practice, or your backend project.

**"Does it help me become a better backend engineer?"** — **More than you'd expect.** File descriptors, `poll`/`epoll`, syscalls, `strace`, resource lifetimes, API design, and cross-platform abstraction are the same concepts that sit under every .NET web server on Linux (§8).

**"Why are `System.Device.*` packages outside the runtime repo?"** — Because the `System.` prefix is a **naming convention**, not a location. Section 1 fixes this model properly.

**"Why would open source need me, if AI exists?"** — Because the bottleneck in open source was never typing code. It's knowing *what* to build, testing it on real hardware, earning reviewers' trust, and designing APIs that can never be taken back (§10). And your contributions are for *your* learning and signal as much as for the project.

**"Do I need a bigger computer?"** — **No.** Your Ubuntu desktop is the right main dev machine for this, and you won't need to build the .NET runtime. Spend money on a Pi 5, a Pico, and a logic analyzer instead (§12).

---

## 1. What ".NET" actually is, and why `System.Device.*` lives outside dotnet/runtime

Tag: 🟢 **OWN IT**. You found a genuine gap: you assumed "`System.*` = inside the runtime repo." Here's the accurate model.

### 1.1 ".NET" is a product made of many parts

```
 ".NET" (the product you download)
 │
 ├── RUNTIME ENGINES — execute IL                         repo: dotnet/runtime
 │     ├── CoreCLR   (JIT + GC + type system; the normal engine on Windows/Linux/macOS)
 │     ├── Mono      (used for WebAssembly, iOS, Android)
 │     └── NativeAOT (compile-ahead engine)
 │
 ├── BASE CLASS LIBRARIES (BCL) — System.Collections, System.IO, System.Net,
 │     System.Text.Json, System.Threading, Microsoft.Extensions.*       repo: dotnet/runtime
 │
 ├── SDK / TOOLING — dotnet CLI, MSBuild, NuGet client, templates     repo: dotnet/sdk (+ others)
 │     └── Roslyn — the C# compiler                                    repo: dotnet/roslyn
 │
 ├── APP FRAMEWORKS
 │     ├── ASP.NET Core (Kestrel, MVC, Blazor, SignalR)                repo: dotnet/aspnetcore
 │     ├── EF Core                                                     repo: dotnet/efcore
 │     └── WinForms, WPF, MAUI …                                      their own repos
 │
 └── THE WIDER ECOSYSTEM — NuGet packages published by Microsoft, the .NET Foundation, or anyone
       ├── System.Device.Gpio, Iot.Device.Bindings                     repo: dotnet/iot
       ├── Yarp.ReverseProxy                                           repo: dotnet/yarp
       ├── Polly, Serilog, MQTTnet …                                  community repos
```

- **CoreCLR** is the name of the main *runtime engine*: the thing from Lecture 001 §5 that loads assemblies, JIT-compiles IL, and garbage-collects. "CLR" = Common Language Runtime; "Core" distinguishes it from the old Windows-only .NET Framework CLR. It lives inside the `dotnet/runtime` repo, in `src/coreclr/`.
- **The `dotnet/runtime` repo** is named after its main content, but it contains *both* the engines *and* the base class libraries. It was formed in 2019–2020 by merging three older repos (`dotnet/coreclr`, `dotnet/corefx`, and Mono's runtime) into one.
- For each official release, all these repos are combined in a single "virtual monolithic repository" (`dotnet/dotnet`) so the whole product can be built together. You'll rarely need it. Just know it's why the pieces version together.

### 1.2 Two ways code reaches your app: shared framework vs NuGet package

| Delivery | How you get it | Examples |
|---|---|---|
| **Shared framework** ("in the box") | Installed *with the runtime*; nothing to add to your `.csproj` | `System.Collections`, `System.IO`, `System.Text.Json`, `System.Threading.Channels` (`Microsoft.NETCore.App`); ASP.NET Core (`Microsoft.AspNetCore.App`) |
| **NuGet package** | `<PackageReference>` in your `.csproj` | `System.Device.Gpio`, `Iot.Device.Bindings`, `System.IO.Ports`, `Microsoft.Extensions.Hosting` (for a console app), `Yarp.ReverseProxy`, `Polly` |

### 1.3 The naming rule you were missing

**A namespace prefix says who owns the API and how general-purpose it is. It says nothing about which repo builds it or how it's delivered.**

| Name | Repo it's built in | Delivered as |
|---|---|---|
| `System.Collections.Generic` | dotnet/runtime | Shared framework |
| `System.IO.Ports` | dotnet/runtime | **NuGet package** (not in the box!) |
| `System.Text.Json` | dotnet/runtime | Shared framework *and* a NuGet package (for older targets) |
| `Microsoft.Extensions.DependencyInjection` | dotnet/runtime | NuGet package (and inside the ASP.NET Core shared framework) |
| **`System.Device.Gpio`** (incl. `System.Device.I2c`) | **dotnet/iot** | **NuGet package** |
| `Iot.Device.Bindings` | dotnet/iot | NuGet package |

`System.Device.*` got the `System.` prefix because it's a general-purpose, Microsoft-owned API that follows .NET's framework design rules. It lives in its own repo because it ships on its own schedule, for a specialized audience, as a package. **This matters for your project:** changing `System.Device.I2c` means working in **dotnet/iot**, a much smaller, friendlier repo than dotnet/runtime, with its own maintainers and review process.

> **How to check any type yourself:** in your IDE, press F12 on the type and look at the assembly name and path. A path under `~/.nuget/packages/...` means it's a NuGet package. A path under `.../shared/Microsoft.NETCore.App/...` means it's the shared framework. Then search GitHub for the assembly name to find its repo.

---

## 2. The real diagnosis: why a Pi can't be an I2C target from C# today

Tag: 🟢 **OWN IT**. This is the most important section.

### 2.1 First, a myth to retire: "C# needed P/Invoke, so C# was the limitation"

**P/Invoke isn't a workaround. It's how .NET talks to Linux everywhere.** `System.Device.I2c`'s own Linux implementation reaches the kernel by P/Invoking into the C library (`libc`) to call `open` and `ioctl` on `/dev/i2c-N`. (Browse the `Interop` folder of dotnet/iot's `System.Device.Gpio` project to see these declarations.) Even `FileStream` and `Socket` in the base libraries end up in native code (through the `libSystem.Native` shim from Lecture 002 §4.1).

So the question was never "why can't C# do it without P/Invoke?" The real question is: **"what native interface *should* .NET be calling for target mode, and why doesn't a standard one exist?"** That question has a much more interesting answer.

### 2.2 The stack, controller mode vs target mode

```
                  CONTROLLER MODE (works today)            TARGET MODE (the gap)
                  ─────────────────────────────            ─────────────────────
 .NET API         System.Device.I2c.I2cDevice              ❌ no API in System.Device.I2c
                          │                                          │
 .NET → native    P/Invoke: open/ioctl (libc)              (your old code: P/Invoke into pigpio)
                          │                                          │
 USERSPACE        /dev/i2c-1  (the i2c-dev interface)      ❌ no standard userspace interface for
 INTERFACE                │                                   target mode on Linux (see §5)
 ═══════════════ kernel boundary ═══════════════           ═══════════════════════════════════
 KERNEL           i2c-bcm2835 bus driver (controller)      ❌ Pi 0–4: the standard I2C driver has
 DRIVER                   │                                   no target support; the target-capable
                          │                                   BSC slave block has no mainline driver
                          │                                ❓ Pi 5: new I2C controllers (see §4.3)
 HARDWARE         BSC controller peripherals               BSC SLAVE peripheral (Pi 0–4, separate
                                                           block, its own pins); RP1 on Pi 5
```

What pigpio actually does to make target mode work on Pi 0–4 is **skip the kernel entirely**. It memory-maps the chip's peripheral registers into its own process (through `/dev/mem`, which is why it usually needs root), then reads and writes the BSC slave block's registers and FIFO directly from userspace. That's why it works, and it's also why it's fragile: it's bound to specific chips, needs root, conflicts with anything else touching those registers, and **doesn't work on the Pi 5** (whose peripherals moved to a new I/O chip, RP1).

### 2.3 So where is the gap, precisely?

| Layer | Gap | Who "owns" fixing it |
|---|---|---|
| **Hardware** | The target-capable peripheral differs per Pi model, and on Pi 0–4 it's a *separate* block on *different pins* from the normal I2C bus | Nobody; it's physics. Software must adapt per model. |
| **Kernel** | No mainline driver exposes the Pi 0–4 BSC slave block. Linux has a general I2C *target framework* (§5), but it needs a bus driver that supports it, and it offers **no general-purpose userspace interface** | Linux kernel / Raspberry Pi kernel maintainers |
| **Userspace library** | pigpio fills the gap for Pi 0–4 with raw register access; nothing standard for Pi 5 | pigpio (largely unmaintained for new hardware) |
| **.NET API** | `System.Device.I2c` models only the controller role | **dotnet/iot**, which is where you can contribute |
| **Runtime** | **None.** P/Invoke already does everything needed. | — |

The .NET part of the fix is a **library design problem**: defining a clean abstraction for "this machine is an I2C target," with pluggable back ends that use whatever the platform offers. That's squarely in Lecture 003's territory (abstractions, deep modules, ports and adapters), with a systems-programming engine underneath.

---

## 3. Your mental model, checked item by item

You listed what you thought you'd need. Each item, corrected:

| You thought you'd need… | Reality | Why |
|---|---|---|
| "Something in the system of the runtime" | ❌ Not needed | The runtime already provides P/Invoke, threads, and memory access. The gap is in a library and in Linux. |
| "Do the system calls, or use the shims" | ✅ Yes, but via plain P/Invoke to libc | dotnet/iot calls libc directly (`open`, `ioctl`, `read`, `poll`, `mmap`). The runtime's internal shim (`libSystem.Native`) isn't a public extension point. |
| "Figure out the different architectures" | ❌ Not in the CPU sense | You'll handle different *Pi models' peripherals*, not CPU instruction sets. A C# library compiled once runs on ARM32 and ARM64. |
| "Find memory addresses in the Broadcom datasheet" | ⚠️ Only for one back end | Needed *only* if you write a pigpio-style register-level back end. Reading pigpio's source + the BCM2835/BCM2711 peripheral docs is a good *learning* exercise either way. |
| "Set up a follow event and register an interrupt" | ❌ Not from userspace | **Interrupts are handled by the kernel.** A userspace program can't install an interrupt handler. It either **polls** registers (pigpio's approach) or **waits on a file descriptor** that a kernel driver signals (with `poll`/`epoll`). That's the whole reason kernel drivers exist. |
| "Copy what the C code did, or include it as an assembly" | ⚠️ Choose deliberately | Options: (a) P/Invoke into an existing C library (fast, adds a native dependency and its license), (b) port the logic to C# using `mmap`'d registers (no native dependency, but you own the tricky parts), (c) use a kernel interface (the cleanest where it exists). Section 6 compares these. |

That last row is the design decision at the heart of the project. Weighing it well *is* the mid-level skill from Lecture 003.

---

## 4. The hardware landscape, model by model

Tag: 🔵 **CONTRACT**. Details from pigpio's header documentation and issue tracker (§15). Verify on real boards.

### 4.1 Pi 0–3 (BCM2835 / BCM2836 / BCM2837)

- The **BSC slave** peripheral (it does I2C *or* SPI target mode) is separate from the normal I2C controllers.
- pigpio documents its pins as **GPIO 18 (SDA)** and **GPIO 19 (SCL)**. Those are *not* the usual I2C pins (GPIO 2/3), which surprises people.
- The register-level description is in Broadcom's **"BCM2835 ARM Peripherals"** document (BSC slave section): data register, status/flag registers, control register, and a FIFO.
- pigpio exposes it as `bscXfer(bsc_xfer_t*)`, using a struct with a control word, receive count and buffer, and transmit count and buffer (512-byte FIFOs). You already mirrored exactly this kind of struct in C#.

### 4.2 Pi 4 (BCM2711)

- A BSC slave block still exists, but pigpio documents **different pins: GPIO 10 (SDA), GPIO 11 (SCL)**.
- A pigpio issue from 2022 reports that the BCM2711's status/control register layouts differ from the BCM2835 documentation, and that status values read back oddly while data still arrives. That's a classic "works, mostly, on the next chip" situation, and a good reminder that **register-level back ends need per-chip validation.**

### 4.3 Pi 5 (BCM2712 + RP1)

- GPIO and most peripherals moved to **RP1**, Raspberry Pi's own I/O chip. **pigpio refuses to run on a Pi 5** (an open issue since November 2023).
- The Pi 5's I2C controllers are driven by Linux's **`i2c-designware`** driver (you'll see it named in Pi 5 kernel issues). **Mainline Linux includes target-mode support for DesignWare I2C controllers** (`i2c-designware-slave.c`, behind the `CONFIG_I2C_DESIGNWARE_SLAVE` option).
- **Open question, and possibly your most valuable finding:** can the Pi 5's kernel (with the right kernel config and device-tree setup) use the standard Linux I2C target framework on RP1's I2C controllers? Forum threads show people asking exactly this, and I couldn't confirm an answer. If it works, the Pi 5 has a *clean, kernel-supported* target path that the Pi 0–4 never had. That would change the whole design (§6). **Answering this question on a real Pi 5 is Phase 1 of your project.**

---

## 5. The Linux I2C target framework

Tag: 🔵 **CONTRACT**. Linux documentation still calls it the "slave interface" (the I2C specification moved to *controller/target* terminology in 2021, and the kernel has been migrating).

### 5.1 How it works

A target-capable **bus driver** implements two hooks (`reg_slave` and `unreg_slave`). A **backend** driver registers itself as the target at an address and receives **events** from the bus driver's interrupt handler, in kernel space:

| Event | Meaning | Backend's job |
|---|---|---|
| `I2C_SLAVE_WRITE_REQUESTED` | The controller addressed us for writing | Get ready; return ACK/NACK |
| `I2C_SLAVE_WRITE_RECEIVED` | A byte arrived | Store it; return ACK/NACK |
| `I2C_SLAVE_READ_REQUESTED` | The controller wants to read | Provide the first byte |
| `I2C_SLAVE_READ_PROCESSED` | The previous byte was sent | Provide the next byte |
| `I2C_SLAVE_STOP` | STOP condition | Reset the state machine |

That event model is essentially the **interrupt-driven state machine you'd write in MCU firmware** for an I2C target, running inside the kernel. It's familiar territory.

### 5.2 How userspace reaches it (and why this is the crux)

- You instantiate a backend through sysfs, with the address **offset by `0x1000`** to mark it as a target, for example:
  `echo slave-24c02 0x1064 > /sys/bus/i2c/devices/i2c-1/new_device`
- The in-tree backends are special-purpose. The best known is **`slave-eeprom`**, which makes the Linux machine *impersonate an EEPROM*: the controller reads and writes a memory image, and userspace sees that image as a file in sysfs.
- There is **no generic backend** that hands raw transactions ("controller wrote these 3 bytes") to a userspace program through a file descriptor you can `poll()`.

So even where the hardware and bus driver support target mode, **a .NET program's options are to work with an EEPROM-like memory model, or to have someone write a new kernel backend.** That's the real reason no clean .NET API exists: there was never a clean Linux interface underneath it to wrap.

---

## 6. Four ways to solve it, and where .NET fits

Tag: 🟢 **OWN IT**, as a design exercise. This is Lecture 003's "choose the layer and the seam" applied to a real problem.

### 6.1 The solution space

| | Approach | How it works | Pros | Cons | Pi models |
|---|---|---|---|---|---|
| **A** | **Userspace register driver** (the pigpio way) | `mmap` the peripheral registers via `/dev/mem`; poll the BSC slave FIFO from a thread | Works today on Pi 0–4; no kernel work | Needs root; chip-specific; fragile; conflicts with other register users; burns CPU polling; dead on Pi 5 | 0–4 |
| **B** | **Kernel target framework + existing backend** (`slave-eeprom`) | Kernel handles interrupts; your C# reads/writes the EEPROM image file | Standard kernel path; no raw register access | "Looks like an EEPROM" semantics only; needs a target-capable bus driver | Pi 5 *if* §4.3 works out |
| **C** | **Kernel target framework + a new generic backend** | Write a kernel module that exposes target events through a character device you can `read`/`poll` | The "right" long-term Linux answer; clean for every language, not only .NET | Kernel C development and upstreaming: a different world, a different culture, months of work | Any board with a target-capable bus driver |
| **D** | **Change the architecture** | Let a small MCU be the I2C target and talk to the Pi over USB or UART | Robust, cheap, real-time; a very common industry answer | Extra part; doesn't "solve" Linux target mode | All |

**D deserves respect.** A senior engineer's first question is often *"should we solve this at all, or route around it?"* On a real product, D is frequently correct. Being able to say that, with reasons, is part of looking senior in an interview.

### 6.2 Where the .NET library sits in all of this

Whichever of A–C a given platform offers, a .NET developer wants **one API**. That's a textbook **ports-and-adapters** design (Lecture 003 §8.2):

```
   Application code
         │ uses
         ▼
   I2cTarget  (abstract API — the "port")
         │ implemented by
   ┌─────┴──────────────────────────┬───────────────────────────────┐
   ▼                                ▼                               ▼
 BscRegisterBackend            KernelEepromBackend            (future) KernelCharDevBackend
 approach A, Pi 0–4            approach B, e.g. Pi 5?          approach C
 mmap + polling thread         read/write a sysfs file         read/poll a /dev node
```

### 6.3 A design sketch to think with (not a proposal)

This mirrors dotnet/iot's style for `I2cDevice`: an **abstract class** with a static `Create` factory. *Framework Design Guidelines* favors abstract classes over interfaces for extensible framework types, because members can be added later without breaking implementers.

```csharp
// HYPOTHETICAL: a sketch for reasoning about design, not an existing or proposed API.
public sealed record I2cTargetSettings(int BusId, int Address);

public abstract class I2cTarget : IDisposable
{
    /// Chooses a backend that works on this platform, or throws PlatformNotSupportedException.
    public static I2cTarget Create(I2cTargetSettings settings) => throw new NotImplementedException();

    public abstract I2cTargetSettings Settings { get; }

    /// Messages written by the controller, in arrival order.
    public abstract IAsyncEnumerable<ReadOnlyMemory<byte>> ReadWritesAsync(CancellationToken ct = default);

    /// The bytes the controller will receive on its next read.
    public abstract void SetReadResponse(ReadOnlySpan<byte> data);

    public void Dispose() { Dispose(true); GC.SuppressFinalize(this); }
    protected virtual void Dispose(bool disposing) { }
}
```

Now the **real design problem**, the kind maintainers will care about. The back ends have *different semantics*:

- Approach A (a FIFO) naturally gives **messages**: "the controller wrote these 3 bytes."
- Approach B (an EEPROM image) gives a **register map**: "the controller wrote value V at offset O; reads return the memory at the current pointer."

One abstraction can't honestly paper over both without becoming leaky (Lecture 003 §4.3). The options: pick the register-map model as the common denominator (many real I2C targets behave like register maps anyway), offer two abstractions, or expose capabilities. **Bringing this trade-off to the maintainers with evidence from real hardware is exactly what a strong API proposal looks like.** It's also a great design-interview story: *"I found two back ends with incompatible semantics, and here's how I reasoned about the abstraction."*

Other design questions you'd need to answer: Which thread do messages arrive on, and is ordering guaranteed? What happens when the consumer is slow (a bounded channel with drop-oldest, as in Lecture 001 §10.7)? How is a read served *in time*? (The controller won't wait long, so the response must be pre-loaded; that's why `SetReadResponse` exists instead of a "read requested" callback.) What does `Dispose` guarantee about in-flight transfers?

---

## 7. The concept map: everything this domain involves

Tag: this *is* the syllabus. "Need" says how deep to go for this project: 🟢 own it, 🔵 contract level, ⚫ recognize only. "→ Backend" says whether it transfers to general backend work (§8).

### 7.1 Linux userspace (the most transferable block)

| Concept | What it is | Need | → Backend |
|---|---|---|---|
| **File descriptors** | Small integers naming an open resource: a file, device, socket, pipe | 🟢 | ✅✅ Every socket in every web server |
| **Syscalls & `errno`** | The kernel's API: `open`, `read`, `write`, `close`, `ioctl`, `mmap`, `poll`; failures are reported through `errno` | 🟢 | ✅✅ |
| **`ioctl`** | "Device-specific command" syscall: how `/dev/i2c-N` is configured (`I2C_SLAVE = 0x0703`, `I2C_RDWR = 0x0707`) | 🟢 | ✅ |
| **`poll` / `epoll`** | Wait efficiently until one of many fds is ready | 🟢 | ✅✅ .NET sockets on Linux are driven by `epoll` |
| **`mmap`** | Map a file, or device memory, into your address space | 🔵 (🟢 for approach A) | ✅ Memory-mapped files, performance work |
| **`/dev`, sysfs (`/sys`), procfs (`/proc`)** | Linux's "everything is a file" interfaces to devices and kernel state | 🟢 | ✅ Container and production debugging |
| **Users, groups, permissions, udev rules** | Why `/dev/i2c-1` needs the `i2c` group, and how to avoid running as root | 🟢 | ✅ Least privilege in any service |
| **`strace`** | Shows every syscall a process makes | 🟢 | ✅✅ A superpower for debugging any Linux service |
| **systemd** | Services, dependencies, restart, logging | 🔵 | ✅ |

### 7.2 Kernel and drivers

| Concept | What it is | Need | → Backend |
|---|---|---|---|
| **Kernel space vs user space** | Privilege boundary; only the kernel handles interrupts and touches hardware safely | 🟢 | ✅ Understanding performance and isolation |
| **Drivers & modules** | `lsmod`, `modprobe`, `dmesg` | 🔵 | ⚠️ Partial |
| **Device tree & overlays** | How a Pi's kernel learns what hardware exists and how pins are configured (`dtoverlay=` in `config.txt`) | 🔵 | ❌ Embedded-specific |
| **Kernel config** (`CONFIG_I2C_SLAVE`, `CONFIG_I2C_DESIGNWARE_SLAVE`) | Compile-time kernel features. Checking whether they're on is Phase 1 work. | 🔵 | ❌ |
| **Building a Raspberry Pi kernel** (cross-compiled on your desktop) | Only if the Pi 5 path needs a config change | ⚫→🔵 | ❌ |
| **Writing a kernel module** (approach C) | Kernel C, locking, interrupt context, upstreaming | ⚫ | ❌ Out of scope for now |

### 7.3 The I2C protocol, properly

| Concept | Need |
|---|---|
| START, STOP, **repeated START**; 7-bit addressing; R/W bit | 🟢 |
| ACK/NACK, and what a target does with each | 🟢 |
| **Clock stretching** (a target holding SCL low to buy time), and why target implementations depend on it. Some Pi I2C controllers have long-documented problems with targets that stretch the clock. | 🟢 |
| Register-pointer convention ("write the register number, then read"), which is how most sensors behave | 🟢 |
| SMBus vs I2C differences | 🔵 |
| Tools: `i2cdetect`, `i2cget`/`i2cset`, `i2ctransfer`; a logic analyzer with PulseView/sigrok decoding | 🟢 |

You know much of this block already from firmware. It's your head start.

### 7.4 Hardware (only for approach A, and for understanding)

| Concept | Need |
|---|---|
| Memory-mapped I/O; peripheral base addresses differ per model (e.g., 0x20000000 on BCM2835, 0x3F000000 on BCM2836/7, 0xFE000000 on BCM2711, as ARM physical addresses) | 🔵 |
| Reading a peripheral chapter: registers, bit fields, FIFOs, flags | 🔵 (you've done this before) |
| Pin muxing / alternate functions (why the BSC slave uses GPIO 18/19 or 10/11) | 🔵 |
| Volatile access and memory ordering for MMIO from C# (`Volatile.Read/Write`, pointers over `mmap`'d memory) | 🔵 |

### 7.5 .NET interop and library design

| Concept | Need | → Backend |
|---|---|---|
| `LibraryImport`/`DllImport` into `libc`; `SetLastError = true` + `Marshal.GetLastPInvokeError()` for errno | 🟢 | ✅ |
| **`SafeHandle`** to own an fd, so it's closed exactly once, even on exceptions | 🟢 | ✅✅ The same discipline as connections and pooled resources |
| Struct marshalling for kernel structs (`i2c_msg`, `i2c_rdwr_ioctl_data`) | 🔵 | ⚠️ |
| Abstract class vs interface; static `Create` + platform detection; `PlatformNotSupportedException` | 🟢 | ✅ Provider abstractions everywhere |
| Async API shapes: events vs `IAsyncEnumerable<T>` vs callbacks vs `Channel<T>` | 🟢 | ✅✅ |
| Thread-safety and disposal contracts | 🟢 | ✅✅ |
| *Framework Design Guidelines*, API proposals, versioning, binary compatibility | 🔵→🟢 | ✅✅ API design is a core SE II / senior skill |

A taste of the interop layer, the same pattern dotnet/iot uses for controller mode:

```csharp
using System.Runtime.InteropServices;

internal static unsafe partial class Libc
{
    internal const int   O_RDWR    = 2;
    internal const nuint I2C_SLAVE = 0x0703;   // despite the name: sets the address of the device we TALK TO

    [LibraryImport("libc", SetLastError = true, StringMarshalling = StringMarshalling.Utf8)]
    internal static partial int open(string path, int flags);

    [LibraryImport("libc", SetLastError = true)]
    internal static partial int ioctl(int fd, nuint request, nint arg);

    [LibraryImport("libc", SetLastError = true)]
    internal static partial nint read(int fd, byte* buffer, nuint count);

    [LibraryImport("libc", SetLastError = true)]
    internal static partial int close(int fd);
}

// Usage (controller mode, simplified; real code should wrap the fd in a SafeHandle):
int fd = Libc.open("/dev/i2c-1", Libc.O_RDWR);
if (fd < 0) throw new IOException($"open failed, errno={Marshal.GetLastPInvokeError()}");
if (Libc.ioctl(fd, Libc.I2C_SLAVE, 0x40) < 0) throw new IOException($"ioctl failed, errno={Marshal.GetLastPInvokeError()}");
```

**A one-evening exercise that makes this real:** on a Pi, run a tiny C# program that reads a sensor through `System.Device.I2c`, under `strace -f -e trace=openat,ioctl,read,write dotnet YourApp.dll`. You'll watch the managed API turn into exactly these syscalls. After that, "the .NET stack on Linux" stops being abstract, for I2C and for sockets alike.

### 7.6 Testing, tooling, and process

| Concept | Need |
|---|---|
| Unit tests with a **fake backend** (the port/adapter seam pays off) | 🟢 |
| **Hardware-in-the-loop:** a Raspberry Pi Pico running *your C firmware* as the I2C controller that exercises the Pi target, and a logic analyzer to see the truth on the wire | 🟢 |
| Cross-deploying: `dotnet publish -r linux-arm64`, `rsync`/`scp`, VS Code Remote-SSH debugging | 🟢 |
| Licensing: pigpio's public-domain license vs the Linux kernel's **GPL**. Never copy kernel code into an MIT-licensed .NET library. | 🟢 |
| GitHub Discussions/issues, API proposals, the CLA (Lecture 002 §12) | 🟢 |

Notice the Pico's role: **your firmware skill becomes your test equipment.** That's a cheap, practical use of the microcontroller side, without the "C# on MCUs" detour.

---

## 8. Does this make you a better backend engineer?

Yes, and here's the specific mapping, so you can judge it yourself:

| What you'd learn here | Where it shows up in backend work |
|---|---|
| fds, `read`/`write`, `poll`/`epoll` | How Kestrel and `Socket` work on Linux; why async I/O doesn't need a thread per connection (Lecture 001 §10) |
| `strace`, `/proc`, permissions | Debugging a misbehaving service in a Linux container at 2 a.m. |
| `SafeHandle`, deterministic disposal | Connection pools, `HttpClient` lifetimes, leak hunting |
| A callback thread → `Channel<T>` → consumer | Producer/consumer pipelines, backpressure, queue design |
| Designing one API over several back ends with different semantics | Provider abstractions (storage, messaging, cloud SDKs); the classic leaky-abstraction problem |
| Writing an API proposal and defending trade-offs | Design docs and design reviews: the core of SE II and senior work |
| Testing with fakes + hardware-in-the-loop | Test pyramids: unit, integration, end-to-end |
| Working with OSS maintainers on GitHub | How the .NET team itself works: in public, on GitHub |

What *doesn't* transfer: device-tree details, BSC register layouts, kernel config options. That's roughly **20–30% of the effort**, and it's also the part that makes the project *yours* (no one else is positioned to do it).

---

## 9. Market, career, and the Microsoft question

### 9.1 Honest sizing

- **General backend/cloud engineering:** by far the largest market, and the largest share of Microsoft's software engineering roles (Azure services, Microsoft 365, and so on).
- **Embedded Linux + application software:** a solid, steady mid-sized market (industrial, automotive, medical, networking gear, appliances, datacenter hardware), and generally *under-supplied* with people who are good at both sides.
- **"Linux I2C target mode in .NET":** a tiny feature-level niche. Its value to you is **as a vehicle**, not as a market.

A quick exercise to calibrate yourself instead of trusting me: search Microsoft's careers site (and LinkedIn Jobs) for *"C#" + "distributed systems"*, then for *"embedded Linux"*, then for *"firmware"*. Compare the counts, and read five postings from each.

### 9.2 The identity to build (to avoid being pigeonholed)

> **A backend/cloud .NET engineer who understands the whole stack down to the kernel and the hardware.**

- **Core (70–80% of your effort):** backend fundamentals: DSA for the coding gate, system design, .NET services, Azure, testing, design judgment (dotnet/003).
- **Edge (20–30%):** systems depth, where this project lives. It makes you memorable in interviews, gives you a genuine OSS contribution, and qualifies you for the hardware-adjacent teams where your background is a real advantage (datacenter hardware management, edge/IoT, devices).

This shape is hard to pigeonhole: the core keeps you employable anywhere, and the edge makes you stand out where it counts.

### 9.3 How this project helps in a Microsoft interview specifically

| Interview part | What this project gives you |
|---|---|
| **Coding rounds** | Nothing directly. The LeetCode protocol (carreer_path/002) stays non-negotiable. |
| **Design round** | A real example of layered diagnosis, placing responsibilities, and abstraction trade-offs across back ends. SE II placement often hinges on this "scope of thinking." |
| **Hiring manager / behavioral** | Ownership and initiative: "I noticed a gap I'd been working around, diagnosed it across hardware, kernel, and library layers, engaged the maintainers, and shipped a prototype." |
| **The "As Appropriate" round** | Explaining something deep at the right altitude to a stranger. §2's diagram *is* that explanation. |
| **Resume/GitHub** | Merged or in-review work in a `dotnet/` repo, plus a technical write-up. Rare signals. |

---

## 10. "Why would they need me if AI can fix everything?"

A fair question. The answer has two halves.

### 10.1 Why open source still needs people like you

1. **The bottleneck was never typing code.** For a feature like I2C target mode, the hard parts are: knowing it's needed, discovering *which* kernel paths exist on *which* boards, choosing semantics, and committing to an API that can't be changed once shipped (breaking changes are extremely costly in .NET). An AI can draft code for a spec. It can't decide the spec, and it can't *own* the decision.
2. **Physical verification.** No model can put a logic analyzer on a Pi 5's I2C pins. Someone with hardware and the skill to use it has to.
3. **Review bandwidth and trust.** Maintainers' scarcest resource is review time. Several well-known projects have publicly complained about floods of low-quality AI-generated submissions. A contributor who understands the problem, brings evidence, and keeps PRs small *saves* maintainers time. That's why they value people like that.
4. **Maintainers don't have unlimited time or hardware either.** Many dotnet/iot bindings exist because someone who owned the hardware wrote them.

### 10.2 Why *you* doing it is the point anyway

- The contribution is how *you* learn, and how you prove the learning to others. An interviewer will ask *you* about it, without AI help.
- Microsoft interviews test your reasoning live. Work you truly did yourself is work you can defend at any depth.
- Using AI as a **tutor or reviewer** on this personal project is fine: "explain the kernel I2C target events," "what's wrong with this API sketch?" But make every design decision yourself and verify every claim against real docs and hardware. That's also a good habit for working at a company that builds AI tools.

---

## 11. Your first contribution: getting past the fear

You've never made a contribution, and the idea feels big. So make the first one small on purpose, and **separate it from the I2C project**, so the first PR is low-stakes.

### 11.1 The contribution ladder

| Rung | Example | Fear level |
|---|---|---|
| 1 | ⭐ Star and watch dotnet/iot; read 5 recent merged PRs and their discussions | None |
| 2 | Reproduce an open bug on your hardware and comment with the details | Very low |
| 3 | **Fix a documentation gap you personally hit** (a README step, a wrong pin number, a broken link) | Low. **Your first PR.** |
| 4 | Improve a sample, or add a test to an existing binding | Low–medium |
| 5 | Open a well-researched **Discussion**: "I2C target mode: platform survey and design questions" | Medium. Very high value. |
| 6 | A real code change: a bug fix, a binding, or the prototype upstreamed | Medium–high |

Rung 5 is a real contribution even with no code in it. A clear, evidence-based write-up that maintainers can make decisions from is valuable work in any open-source project.

### 11.2 What happens when you open a PR (so there are no surprises)

1. A bot asks you to agree to the Contributor License Agreement. Click through once.
2. CI runs. If it fails for something unrelated to you, say so politely in a comment.
3. A maintainer may request changes. **That isn't rejection. It's the review you've been missing** (carreer_path/003 §0). Thank them, make the changes, and push again.
4. It may take days or weeks. Maintainers are busy. A polite nudge after a week or two is normal.

### 11.3 A first comment you can adapt

> *"Hi! I'd like to help with this. I have a Pi 4 and Pi 5 and can reproduce it. My plan is to [one sentence]. Does that approach sound right before I open a PR?"*

That's all it takes. Commenting first means you never spend effort on something the maintainers would reject.

---

## 12. Machines and hardware: what you need

### 12.1 Computers: no purchase needed

| Machine | Role | Why it works |
|---|---|---|
| **Ubuntu desktop** (.NET 10, lots of disk) | **Main dev machine**: build dotnet/iot, write the library, cross-compile a Pi kernel if Phase 1 needs one | dotnet/iot's `global.json` pins a .NET 9 SDK with *roll-forward to the latest major*, so your .NET 10 SDK satisfies it. Its build scripts can also install the pinned SDK locally. Linux matches the target OS. |
| **MacBook** (~25 GB free) | Reading, writing the lecture notes, light editing, SSH into the Pis | Don't build large repos here |
| **Raspberry Pis** | The targets under test. Deploy published output from the desktop. | `dotnet publish -r linux-arm64` + `rsync`, or debug remotely with VS Code Remote-SSH |

You **don't** need to build `dotnet/runtime` for this project, and that's the only repo in this whole story that needs a big machine (tens of GB and hours of build time). If disk ever gets tight on the desktop, a cheap SSD is a better purchase than a new computer.

**Personal hardware only.** Don't use your employer's Pis or equipment for this (Lecture 002 §12.4).

### 12.2 Hardware shopping list (approximate; prices vary)

| Item | Why | Rough cost |
|---|---|---|
| **Raspberry Pi 5** | Where the open kernel question lives (§4.3), and the future of the platform | ~$60–80 with a power supply |
| **Raspberry Pi 4** (if you don't own one) | Baseline via pigpio's BSC slave path | ~$35–55 |
| **Raspberry Pi Pico** (×2) | I2C *controller* test rigs running your own C firmware (Pico SDK) | ~$5 each |
| **8-channel USB logic analyzer** (a basic 24 MHz one) + PulseView (sigrok) | See the truth on the wire; decode I2C | ~$10–20 |
| Breadboard, jumper wires, 4.7 kΩ pull-ups, a known-good I2C sensor | Basic bench kit | ~$15 |

Roughly **$100–200 total**, depending on what you already own. That's much cheaper than a computer, and far more useful for this.

---

## 13. The project plan: phases, time boxes, exit criteria

This fits into your weekly operating system (carreer_path/003 §8) as the **build block (~3 h/week) for about 10 weeks**. **LeetCode and design practice continue unchanged.** Each phase delivers something valuable even if you stop right after it.

| Phase | Weeks | Work | Output | Exit / decision point |
|---|---|---|---|---|
| **0. Fear-breaker + setup** | 1–2 | Clone and build dotnet/iot on the desktop; read a sensor from a Pi via `System.Device.I2c`; do the `strace` exercise (§7.5); **open your first docs PR** (rung 3), unrelated to target mode | Your first PR; a working toolchain | Done when the PR is open |
| **1. Ground truth** | 2–4 | (a) Pi 4 baseline: minimal C# P/Invoke into pigpio's `bscXfer`, driven by a Pico controller, verified on the logic analyzer. (b) **Pi 5 investigation:** is `CONFIG_I2C_SLAVE` / `CONFIG_I2C_DESIGNWARE_SLAVE` enabled? Can you instantiate `slave-24c02` with the `0x1000` offset on an RP1 I2C bus? Does a Pico see the "EEPROM"? | A findings document with logic-analyzer captures | **Decision:** does the Pi 5 have a kernel target path (yes / no / only with a custom kernel)? |
| **2. Publish + ask** | 5–6 | Turn the findings into a public write-up (Lecture 002's idea I-5). Read nanoFramework's I2C slave API as precedent. Open a **Discussion/issue on dotnet/iot**: platform survey, the §6.3 semantics problem, and "would you be interested in an `I2cTarget` API?" | Write-up + Discussion (rung 5) | **Decision:** maintainers interested → Phase 4 path open; not interested → Phase 3 as your own library only |
| **3. Prototype** | 6–10 | Your own repo: `I2cTarget` abstraction + one or two back ends + fake backend + unit tests + a hardware-in-the-loop sample + README. Optionally publish to NuGet. | A real library you designed, with tests | Done when a Pico ↔ Pi round trip works through your API |
| **4. Upstream** *(only if invited)* | 10+ | API proposal → review → PR in dotnet/iot | A contribution to a `dotnet/` repo | — |

**Kill switches** (when to stop or change course):
- If Phase 1 takes more than 3× its time box, stop, write up what you learned, and move on. The write-up still counts.
- If you notice you're spending more than ~30% of your weekly hours on this, cut back. The coding gate matters more for Microsoft.
- If you're tempted by approach C (writing a kernel module) *before* Phase 3 is done, that's the rabbit hole. Park it in "future work."

**Connecting it to your portfolio:** the Phase 3 library can become the Pi-side ingestion layer of the device-to-cloud project (Lecture 002's I-8): Pico firmware (C) → I2C → Pi (your `I2cTarget` library + a .NET worker) → MQTT → Azure. One coherent story across firmware, Linux, .NET, OSS, and Azure.

---

## 14. Self-check questions

1. Why is "the Pi can't be an I2C target from C#" *not* a runtime problem? (§0, §2)
   <details><summary>Answer</summary>The runtime already provides everything needed (P/Invoke, threads, memory access). The gaps are in the hardware per model, the Linux kernel's drivers and userspace interfaces, and the dotnet/iot library's API.</details>

2. Why does `System.Device.I2c` live in dotnet/iot and not dotnet/runtime? (§1)
   <details><summary>Answer</summary>The <code>System.</code> prefix marks a general-purpose, .NET-owned API, not a repo. <code>System.Device.*</code> ships as a NuGet package on its own schedule from dotnet/iot.</details>

3. What's CoreCLR, and where does it live? (§1.1)
   <details><summary>Answer</summary>The main .NET runtime engine (JIT, GC, type system, interop), in <code>src/coreclr</code> of the dotnet/runtime repo.</details>

4. Is P/Invoke a workaround? (§2.1)
   <details><summary>Answer</summary>No. It's the standard way .NET calls into the OS. dotnet/iot's own Linux I2C support P/Invokes into libc for <code>open</code>/<code>ioctl</code>.</details>

5. Why can't a userspace program register an interrupt handler, and what does it do instead? (§3)
   <details><summary>Answer</summary>Interrupts are handled in kernel mode for safety and isolation. Userspace either polls hardware registers (pigpio) or blocks on a file descriptor that a kernel driver signals (<code>poll</code>/<code>epoll</code>).</details>

6. How does pigpio implement target mode on Pi 0–4, and what are the costs? (§2.2, §6.1)
   <details><summary>Answer</summary>It maps the peripheral registers through <code>/dev/mem</code> and drives the BSC slave block directly from userspace. Costs: needs root, chip-specific, fragile, polling CPU use, doesn't work on the Pi 5.</details>

7. What does the `0x1000` offset mean in `echo slave-24c02 0x1064 > .../new_device`? (§5.2)
   <details><summary>Answer</summary>It marks the address as a target (slave) address, instantiating a target backend at 0x64 rather than a client device.</details>

8. Why is there no clean .NET target API even on hardware that supports target mode in the kernel? (§5.2)
   <details><summary>Answer</summary>Linux offers no generic userspace interface for target-mode transactions. The in-tree backends are special-purpose (e.g. EEPROM emulation), so there's no clean interface to wrap.</details>

9. Name the four solution approaches, and when approach D is the right answer. (§6.1)
   <details><summary>Answer</summary>A: userspace register driver. B: kernel framework + existing backend. C: new kernel backend. D: change the architecture (an MCU as target, with USB/UART to the Pi). D is right when robustness, real-time behavior, and cost matter more than having Linux itself be the target, which is often the case in products.</details>

10. What design problem makes a single `I2cTarget` abstraction hard? (§6.3)
    <details><summary>Answer</summary>The back ends have different semantics: message/FIFO-based vs register-map/EEPROM-based. A single abstraction risks being leaky unless it picks one model deliberately or exposes capabilities.</details>

11. Name three things from this project that transfer directly to backend engineering. (§8)
    <details><summary>Answer</summary>Any three of: fds and <code>epoll</code> (how sockets and Kestrel work), <code>strace</code>/production debugging, <code>SafeHandle</code>/resource lifetimes, producer/consumer with channels, multi-backend API design, design docs and reviews, OSS collaboration.</details>

12. What role does the Raspberry Pi Pico play in this project, and why is that a good use of your firmware skills? (§7.6, §12.2)
    <details><summary>Answer</summary>It's the I2C controller test rig running your own C firmware. It turns your firmware skill into test equipment without detouring into C#-on-MCU work.</details>

---

## 15. Sources

Checked 2026-09-25. Re-verify on real hardware; this area changes with kernel and firmware releases.

- [Linux kernel: I2C slave (target) interface](https://docs.kernel.org/i2c/slave-interface.html)
- [Linux source: `i2c-designware-slave.c`](https://elixir.bootlin.com/linux/v6.13.1/source/drivers/i2c/busses/i2c-designware-slave.c)
- [raspberrypi/linux issue showing `i2c_designware` on the Pi 5](https://github.com/raspberrypi/linux/issues/5784)
- [Raspberry Pi forum: Pi 5 as I2C slave](https://forums.raspberrypi.com/viewtopic.php?t=371115) · [Configuring Pi 5 as an I2C slave](https://forums.raspberrypi.com/viewtopic.php?t=370155) (both returned errors when fetched; they show the question is being asked)
- [pigpio `pigpio.h` (BSC pins, `bsc_xfer_t`, event 31)](https://github.com/joan2937/pigpio/blob/master/pigpio.h) · [pigpio won't run on a Pi 5 (#589)](https://github.com/joan2937/pigpio/issues/589) · [BCM2711 BSC register differences (#511)](https://github.com/joan2937/pigpio/issues/511) · [Pi 4 BSC slave issue (#280)](https://github.com/joan2937/pigpio/issues/280)
- [BCM2835 ARM Peripherals (PDF)](https://wordpress-courses2425.wolfware.ncsu.edu/ece-785-sprg-2025/wp-content/uploads/sites/80/2023/02/BCM2835-ARM-Peripherals.pdf) · [Raspberry Pi processor documentation](https://raspberrypi.com/documentation/hardware/raspberrypi/bcm2711/README.md)
- [dotnet/iot](https://github.com/dotnet/iot) · [dotnet/iot `global.json`](https://github.com/dotnet/iot/blob/main/global.json) · [dotnet/iot libgpiod docs](https://github.com/dotnet/iot/blob/main/Documentation/gpio-linux-libgpiod.md)
- [nanoFramework I2C slave issue (precedent for a target API)](https://github.com/nanoframework/Home/issues/1494)
- [dotnet/runtime API review process](https://github.com/dotnet/runtime/blob/main/docs/project/api-review-process.md)

---

*End of Lecture 004. Next in this folder: 005, "Generic Host & DI, in depth." Before then: Phase 0 (your first PR) and the `strace` exercise.*
