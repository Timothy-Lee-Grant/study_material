2026_08_01_12_00-(When-Root-Isnt-Enough)

# Lecture 002 — When Root Isn't Enough: Privilege, Peripherals, and Proof on Embedded Linux

You have a C# application on a Compute Module, P/Invoking into `libpigpio.so`, trying to act as an **I2C slave**. No data arrives. You hypothesized "it needs root," set `User=root` in a systemd unit, confirmed with `ps aux` that the process runs as root — and nothing changed.

That is a *good* bug. Not because it's easy, but because it sits exactly on the seam between six different systems, and every one of them is a concept you'll be asked about in a systems interview and will need every day as an infrastructure engineer:

1. The **Linux privilege model** (and why `root` is not a single boolean)
2. **Error surfaces** and how P/Invoke destroys them
3. **pigpio's actual contract** with the kernel and hardware
4. **I2C slave mode** as a hardware peripheral, not a software feature
5. **systemd** as the environment your program lives in
6. **Debugging methodology** — the skill that makes the other five usable

This lecture teaches all six, then hands you an ordered Monday runbook.

I'll also tell you up front: **I think there is a very high probability your permission hypothesis is wrong**, and I'll show you the two specific hardware/platform facts that most likely explain "no data." But the point of the lecture is that you should never take my word for that either — you should be able to *prove* which layer is broken in under twenty minutes.

---

## Table of Contents

- [0. Preface: the real lesson is falsifiability](#0-preface-the-real-lesson-is-falsifiability)
- [1. The cast of characters](#1-the-cast-of-characters)
- [2. The stack, drawn](#2-the-stack-drawn)
- [3. Concept 1 — What "running as root" actually means](#3-concept-1--what-running-as-root-actually-means)
- [4. Concept 2 — Capabilities: root, disassembled](#4-concept-2--capabilities-root-disassembled)
- [5. Concept 3 — systemd can take root's power away](#5-concept-3--systemd-can-take-roots-power-away)
- [6. Concept 4 — The error surface, and how P/Invoke destroys it](#6-concept-4--the-error-surface-and-how-pinvoke-destroys-it)
- [7. Concept 5 — pigpio's real contract](#7-concept-5--pigpios-real-contract)
- [8. Concept 6 — I2C slave mode is hardware, not software](#8-concept-6--i2c-slave-mode-is-hardware-not-software)
- [9. Concept 7 — The two platform facts that most likely explain your bug](#9-concept-7--the-two-platform-facts-that-most-likely-explain-your-bug)
- [10. Concept 8 — systemd as an environment, not a launcher](#10-concept-8--systemd-as-an-environment-not-a-launcher)
- [11. Concept 9 — Debugging methodology: bisect, don't guess](#11-concept-9--debugging-methodology-bisect-dont-guess)
- [12. The failure-mode table](#12-the-failure-mode-table)
- [13. THE MONDAY RUNBOOK](#13-the-monday-runbook)
- [14. Common mistakes and misconceptions](#14-common-mistakes-and-misconceptions)
- [15. Interview relevance and the backend translation](#15-interview-relevance-and-the-backend-translation)
- [16. A note on your hyperfixation](#16-a-note-on-your-hyperfixation)
- [17. Follow-on lectures](#17-follow-on-lectures)
- [18. Sources](#18-sources)

---

## 0. Preface: the real lesson is falsifiability

Let's look at what you actually did, as a scientist would:

> **Hypothesis:** The application isn't receiving I2C data because it lacks permission to access the hardware.
>
> **Experiment:** Run it as root.
>
> **Result:** Still no data.
>
> **Conclusion drawn:** ...?

Here's the problem. **That experiment could not have taught you anything either way.** Consider the two outcomes:

- Data appears → you learn permissions were the issue. Fine.
- No data appears → you learn *nothing*. It could mean permissions weren't the issue, or that permissions were *one of two* issues, or that root didn't actually grant what you thought, or that your change never took effect.

An experiment whose failure mode is uninformative is a **weak experiment**. The fix is to test the *mechanism* rather than the *outcome*.

The permission hypothesis makes a much sharper, more testable prediction than "data will appear":

> If permissions are the problem, then **`gpioInitialise()` returns `PI_INIT_FAILED` (-1)**, and the process fails to open `/dev/mem`, and there is a message on stderr.

That prediction is *directly observable in one line of code*, is independent of every wire on your board, and gives you a clean yes/no. You never needed to reboot the Pi to test it.

**This is the single most valuable habit in this entire document:**

> When you form a hypothesis about a failure, ask: *what is the nearest observable consequence of this hypothesis being true?* Then observe that thing directly — do not test it by observing the far-downstream end-to-end behavior.

The end-to-end behavior ("telemetry appears in my app") is downstream of roughly nine independent things. Using it as your instrument means every measurement has nine confounds.

---

## 1. The cast of characters

You told me you learn best when the components have faces. Here is the ensemble.

| Character | Who they are | What they want | Where they live |
|---|---|---|---|
| **The Kernel** | The building superintendent. Owns every door, every key, every utility line. Nothing physical happens without going through them. | To never let an untrusted tenant touch the wiring | ring 0 |
| **`/dev/mem`** | The **master key to the building's electrical room**. Whoever holds it can reach out and touch *any* physical address — including registers that will hard-lock the SoC. | Nothing. It's a key. That's what makes it terrifying. | `/dev` |
| **`/dev/gpiomem`** | The **polite side door**. Opens onto *only* the GPIO register block. Group-owned by `gpio`, so ordinary users can hold it. Safe. Limited. | To let hobbyists blink LEDs without root | `/dev` |
| **pigpio (the library)** | The **locksmith with a van full of tools**. Doesn't just want GPIO — wants the DMA controller, a hardware timer, the PWM/PCM peripheral, and the BSC. So he demands the *master key*, not the side door. | Microsecond-accurate control of everything | `libpigpio.so`, inside your process |
| **pigpiod (the daemon)** | The locksmith's **dispatch office**. Same van, but he runs as root once, permanently, and you phone in requests over TCP 8888. | To be the *only* locksmith on the job | its own process |
| **P/Invoke / the CLR** | The **embassy translator**. Carries messages between the managed world (GC, exceptions, `string`) and the native world (raw pointers, `errno`, structs with exact byte layouts). Speaks both languages but **does not carry emotion** — a native scream of failure arrives as a polite integer. | Correct marshalling | your .NET runtime |
| **systemd** | **HR and Facilities.** Decides who your process logs in as, what rooms it's allowed into, when it starts, what happens when it dies, and where its voice goes. Can *quietly revoke* privileges HR thinks you don't need. | Reproducible, contained services | PID 1 |
| **The BSC** | The **receptionist**, and the true protagonist. A dedicated hardware block whose entire job is to sit at one specific door, listen for someone knocking with your name, and hold 16 letters in a tray. **She only listens at one door, and which door it is changed between chip generations.** | To be spoken to on the correct two pins | silicon |
| **The I2C Master** | The **visitor with the only watch**. Owns the clock. Nothing on the bus happens unless he ticks. If he never knocks, the receptionist has nothing to report — and she has no way to tell you he didn't. | To be answered fast | your other device |
| **RP1** | The **new annex built on the Pi 5 / CM5**. All the GPIO moved into it. The old master key opens the old building — which is now empty. | (Doesn't know pigpio exists) | BCM2712-era boards only |

The plot of your bug is this: **you have been arguing with the Superintendent about keys, while the question is whether the Receptionist is sitting at the right door — or whether she exists in this building at all.**

---

## 2. The stack, drawn

```
┌──────────────────────────────────────────────────────────────┐
│  YOUR C# APPLICATION                          (managed)      │
│  var rc = Native.gpioInitialise();   ← rc is the whole story │
│  var rc2 = Native.bscXfer(ref xfer); ← and so is this        │
└───────────────┬──────────────────────────────────────────────┘
                │  P/Invoke  — marshalling boundary
                │  ⚠ errno, stderr, and signals live BELOW here
┌───────────────▼──────────────────────────────────────────────┐
│  libpigpio.so                                  (native)      │
│  • open("/dev/mem")  → needs root                            │
│  • mmap() peripheral register blocks                         │
│  • spawns worker threads                                     │
│  • binds TCP :8888 (unless disabled)   ⚠ conflicts w/ pigpiod│
│  • installs signal handlers            ⚠ hazardous for .NET  │
└───────────────┬──────────────────────────────────────────────┘
                │  syscalls
┌───────────────▼──────────────────────────────────────────────┐
│  LINUX KERNEL                                                │
│  • DAC check (uid/gid on /dev/mem)                           │
│  • capability check (CAP_SYS_RAWIO)                          │
│  • device cgroup / systemd DeviceAllow                       │
│  • namespace: does /dev/mem even EXIST in my mount ns?  ⚠    │
└───────────────┬──────────────────────────────────────────────┘
                │  MMIO writes
┌───────────────▼──────────────────────────────────────────────┐
│  SoC PERIPHERALS                                             │
│  • GPIO pad control: which ALT function is each pin in?      │
│  • BSC slave block: enabled? correct address? FIFO state?    │
│     ⚠ which physical pins it is wired to is CHIP-DEPENDENT   │
└───────────────┬──────────────────────────────────────────────┘
                │  volts
┌───────────────▼──────────────────────────────────────────────┐
│  THE PHYSICAL BUS                                            │
│  • pull-up resistors present?  common ground?                │
│  • correct pins wired?  3.3 V logic on both ends?            │
│  • is the master ACTUALLY transmitting?     ⚠                │
└──────────────────────────────────────────────────────────────┘
```

**Six layers. "No data" is the symptom of a fault in any of them.** Your permission theory addresses exactly one. The runbook in §13 walks the stack from the bottom up, because the bottom is cheapest to test and most likely to be wrong.

---

## 3. Concept 1 — What "running as root" actually means

### 3.1 There are four user IDs, not one

Every Linux process carries a set of identities:

| ID | Name | Purpose |
|---|---|---|
| **ruid** | real UID | who *launched* it |
| **euid** | effective UID | who it is *acting as* — **this is what permission checks use** |
| **suid** | saved UID | the identity it's allowed to switch back to |
| **fsuid** | filesystem UID | (Linux-specific) used for file access checks |

`ps aux` shows you the **effective** user by default. So your `ps aux` observation tells you `euid == 0`. That's real information — but it's narrower than you probably read it as. It tells you *who* the process is. It does **not** tell you *what it can reach*.

```bash
# Far more informative than `ps aux`:
cat /proc/$(pgrep -f YourApp.dll)/status | grep -E '^(Uid|Gid|Groups|Cap)'
```

Output looks like:

```
Uid:    0       0       0       0        ← real, effective, saved, fs
Gid:    0       0       0       0
Groups: 
CapInh: 0000000000000000
CapPrm: 000001ffffffffff     ← what root CAN pick up
CapEff: 000001ffffffffff     ← what root currently HAS   ⚠ check this
CapBnd: 000001ffffffffff     ← the ceiling. can never exceed this. ⚠⚠
```

If `CapEff` is `000001ffffffffff` (all bits) you have full root powers. **If it's anything less, you are a root-uid process that has been declawed** — and this is exactly what systemd hardening does. More on that in §5.

### 3.2 Discretionary access control (DAC): the ownership check

The first gate is boring file permissions:

```bash
ls -l /dev/mem /dev/gpiomem
# crw-r-----  1 root kmem 1, 1 ... /dev/mem      ← root-only, effectively
# crw-rw----  1 root gpio ...      /dev/gpiomem  ← group 'gpio' can open
```

This is the gate you were reasoning about. Being uid 0 passes it. **Root bypasses DAC entirely** (via `CAP_DAC_OVERRIDE`).

But notice: DAC is only *one of four* gates.

### 3.3 The four gates, in order

When your process calls `open("/dev/mem", O_RDWR)`, it must pass all of:

```
1. NAMESPACE   Does /dev/mem exist in my mount namespace at all?
               (systemd PrivateDevices=yes → it does not. ENOENT.)
                            ↓
2. DAC         Do my uid/gid satisfy the file mode?
               (root bypasses via CAP_DAC_OVERRIDE. EACCES if not.)
                            ↓
3. CGROUP      Does the device cgroup allow this major:minor?
               (systemd DeviceAllow= / DevicePolicy=closed. EPERM.)
                            ↓
4. CAPABILITY  Do I hold CAP_SYS_RAWIO?  (required for /dev/mem)
               (dropped by CapabilityBoundingSet=. EPERM.)
```

**Every one of these can fail while `ps aux` cheerfully reports `root`.** That is the crux of why your experiment was uninformative: `ps aux` observes gate 2's *input*, not gates 1, 3, and 4's *outcome*.

### 3.4 The concept to internalize

> **"root" is a legacy shorthand for "passes every check."** Modern Linux has decomposed that into namespaces, cgroups, capabilities, and LSMs. A uid-0 process in a hardened container can be *less* capable than an ordinary user on the host.

This generalizes enormously. It is exactly the same reasoning you'll use for:

- Why a Kubernetes pod running as root still can't `mount`
- Why a Docker container needs `--privileged` or `--device=/dev/mem` even as root
- Why `setcap cap_net_bind_service=+ep` lets a non-root binary bind port 80
- Why cloud IAM says "identity ≠ authorization"

---

## 4. Concept 2 — Capabilities: root, disassembled

In 1999 Linux split root's omnipotence into ~40 independent **capabilities** (now ~41). Relevant ones:

| Capability | Grants |
|---|---|
| `CAP_SYS_RAWIO` | `/dev/mem`, `/dev/port`, `ioperm()` — **pigpio needs this** |
| `CAP_DAC_OVERRIDE` | bypass file permission bits |
| `CAP_SYS_NICE` | real-time scheduling priorities — pigpio wants this too |
| `CAP_SYS_MODULE` | load kernel modules |
| `CAP_NET_BIND_SERVICE` | bind ports < 1024 |
| `CAP_SYS_ADMIN` | the junk drawer; ~30% of all privileged operations |

Each process has **five capability sets**:

```
Permitted   (Prm) — the pool you're allowed to draw from
Effective   (Eff) — what's active RIGHT NOW; this is what's checked
Inheritable (Inh) — passed across execve() to non-privileged binaries
Bounding    (Bnd) — hard ceiling; can only ever shrink, never grow ⚠
Ambient     (Amb) — preserved across execve for non-root processes
```

Useful commands:

```bash
getpcaps $(pgrep -f YourApp.dll)   # human-readable caps for a live process
getcap /usr/bin/dotnet             # file capabilities on a binary
capsh --print                      # your shell's caps
```

### The elegant alternative to running as root

If your problem *had* been permissions, the correct production fix is **not** `User=root`. It's:

```ini
[Service]
User=telemetry
AmbientCapabilities=CAP_SYS_RAWIO CAP_SYS_NICE
CapabilityBoundingSet=CAP_SYS_RAWIO CAP_SYS_NICE
```

Now the process runs as an unprivileged user with exactly the two powers it needs, and *nothing else*. If it's compromised, the attacker gets raw memory access but cannot, say, add users or load modules.

**This is a genuinely strong thing to say in an interview.** "We needed raw MMIO for a hardware peripheral, so instead of running the service as root we granted `CAP_SYS_RAWIO` ambiently to a dedicated service account and bounded the capability set" is a sentence that signals you understand least-privilege as an implementation detail, not a slogan.

> ⚠ Caveat worth knowing: `AmbientCapabilities` only survives `execve` cleanly for the direct executable. If your unit's `ExecStart` is a shell wrapper that then launches `dotnet`, ambient caps *do* propagate (that's their purpose, unlike inheritable), but `NoNewPrivileges=yes` combined with certain setups can interfere. Test it, don't assume it.

---

## 5. Concept 3 — systemd can take root's power away

**This is the part I most want you to remember, because it's the one that would make your `User=root` change genuinely useless while still looking correct in `ps aux`.**

systemd has a large set of *hardening directives*. They are applied by many distro-shipped units and by anyone following a security guide. Several of them **strip privileges from a root process**:

| Directive | Effect on a root process |
|---|---|
| `PrivateDevices=yes` | **Triple-kills pigpio.** (1) Mounts a fresh, nearly-empty `/dev` containing only pseudo-devices — **`/dev/mem` does not exist**. (2) Removes `CAP_MKNOD` and **`CAP_SYS_RAWIO`** from the bounding set. (3) Installs a **seccomp filter blocking the `@raw-io` syscall group**. Also implies `NoNewPrivileges` and `DevicePolicy=closed`. |
| `ProtectKernelTunables=yes` | `/proc/sys`, `/sys` read-only |
| `ProtectSystem=strict` | entire filesystem read-only except explicit paths |
| `DevicePolicy=closed` | only a whitelist of device nodes usable |
| `DeviceAllow=` | explicit per-device allowlist |
| `CapabilityBoundingSet=` | hard ceiling on capabilities — **removes them even from root** |
| `NoNewPrivileges=yes` | can never gain privileges via setuid/fscaps |
| `RestrictAddressFamilies=` | can break pigpio's TCP :8888 socket |
| `MemoryDenyWriteExecute=yes` | **breaks .NET's JIT outright** |
| `ProtectHome`, `PrivateTmp` | usually harmless here |

If **`PrivateDevices=yes`** is set on your unit, then your root process opens `/dev/mem` and gets **`ENOENT` — "no such file or directory."** Not `EACCES`. The file genuinely isn't there, because your process is in a mount namespace where a different, sanitized `/dev` is mounted over the real one. `ps aux` says root. `/proc/PID/status` says `Uid: 0`. And it still cannot see the device.

**Check this first thing Monday. It takes five seconds:**

```bash
systemctl cat your-telemetry.service          # the FULL merged unit, incl. drop-ins
systemctl show your-telemetry.service \
  -p User -p Group -p PrivateDevices -p ProtectSystem \
  -p DevicePolicy -p DeviceAllow -p CapabilityBoundingSet \
  -p AmbientCapabilities -p NoNewPrivileges -p MemoryDenyWriteExecute
systemd-analyze security your-telemetry.service   # scored report of every setting
```

And the decisive test — look from *inside* the service's own namespace:

```bash
# Does /dev/mem exist from the service's point of view?
sudo nsenter -t $(systemctl show -p MainPID --value your-telemetry.service) -m ls -l /dev/mem
```

If that says "No such file or directory" but `ls -l /dev/mem` on the host works, **you have found your bug and it is namespace isolation, not permissions.**

### Why `systemctl cat` and not `cat /etc/systemd/system/foo.service`

Because units are **merged from multiple sources**:

```
/lib/systemd/system/foo.service              ← vendor default
/etc/systemd/system/foo.service              ← your override (full replacement)
/etc/systemd/system/foo.service.d/*.conf     ← drop-in fragments  ⚠ easy to miss
/run/systemd/system/foo.service.d/*.conf     ← runtime drop-ins   ⚠ easier to miss
```

You may have edited one file while a drop-in silently overrode you. `systemctl cat` shows the real, effective, merged result with source annotations. **Always use `systemctl cat`.**

### And the classic own-goal

```bash
sudo systemctl daemon-reload   # ← if you skip this, your edit is not loaded
sudo systemctl restart your-telemetry.service
```

You rebooted, so this was handled. But know that `daemon-reload` is the step people forget, and systemd will happily run the *old* cached unit while you stare at the new file.

### The uncomfortable possibility

> For **system** units, if you specify no `User=` at all, the default is already **root**.

So it is entirely possible your `User=root` edit changed *nothing whatsoever* — the service was already running as root before you touched it, and `ps aux` would have shown `root` beforehand too. You never established a baseline. That's the falsifiability problem from §0 in its purest form: **you didn't measure before you changed.**

> **Rule:** measure before, change one thing, measure after. A change with no before-measurement is not an experiment; it's a wish.

---

## 6. Concept 4 — The error surface, and how P/Invoke destroys it

### 6.1 Native code fails by *return value*, not by exception

This is the most important C#-specific concept in the document.

`gpioInitialise()` has this contract:

> Returns the **pigpio version number** on success, or **`PI_INIT_FAILED` (-1)** on failure.

If your C# looks anything like this:

```csharp
[DllImport("pigpio")]
public static extern int gpioInitialise();

// ...
Native.gpioInitialise();     // ⚠⚠⚠ return value discarded
Native.bscXfer(ref xfer);    // ⚠⚠⚠ return value discarded
```

...then **your program cannot distinguish "pigpio never initialised" from "pigpio is running fine and no master is talking to us."** Both look like silence. You have been staring at a symptom that has been deliberately made ambiguous by your own code.

**Every P/Invoke into pigpio must be checked. Non-negotiable.** Write it once, properly:

```csharp
internal static class Pi
{
    private const string Lib = "pigpio";

    [DllImport(Lib, SetLastError = true)] private static extern int gpioInitialise();
    [DllImport(Lib)]                      private static extern void gpioTerminate();
    [DllImport(Lib)] private static extern int gpioCfgInterfaces(int flags);
    [DllImport(Lib)] private static extern int bscXfer(ref BscXfer xfer);

    private const int PI_INIT_FAILED = -1;

    public static void Init()
    {
        // MUST be called BEFORE gpioInitialise. (Values verified in pigpio.h.)
        const int PI_DISABLE_FIFO_IF = 1;
        const int PI_DISABLE_SOCK_IF = 2;
        gpioCfgInterfaces(PI_DISABLE_FIFO_IF | PI_DISABLE_SOCK_IF);

        int rc = gpioInitialise();
        if (rc == PI_INIT_FAILED)
        {
            int err = Marshal.GetLastWin32Error();  // = errno on Linux
            throw new InvalidOperationException(
                $"gpioInitialise failed (rc={rc}, errno={err}). " +
                "Check: running as root? /dev/mem visible? pigpiod already running?");
        }
        Console.WriteLine($"pigpio initialised, version {rc}");
    }
}
```

Two things to notice:

- **`SetLastError = true`** — despite the Windows-flavored name, on Linux this makes the CLR capture `errno` immediately after the call, retrievable via `Marshal.GetLastWin32Error()`. Without it, the value is garbage, because the CLR may make its own syscalls between your P/Invoke returning and your read of `errno`.
- The error message **enumerates the hypotheses**. Future-you gets the differential diagnosis for free.

### 6.2 `errno` is your permission oracle

If `gpioInitialise` fails, `errno` tells you *which* gate from §3.3 rejected you:

| errno | Value | Meaning here |
|---|---|---|
| `EACCES` | 13 | Permission denied — **DAC gate. Genuinely a permissions problem.** |
| `EPERM` | 1 | Operation not permitted — **missing capability or cgroup denial.** |
| `ENOENT` | 2 | No such file — **`/dev/mem` doesn't exist in your namespace. `PrivateDevices=yes`.** |
| `EBUSY` | 16 | Resource busy — something else holds the peripheral |
| `EADDRINUSE` | 98 | **pigpiod is already running and holding port 8888** |

Those five errno values map one-to-one onto five completely different fixes. **This is why discarding return values is not laziness but active self-harm** — you threw away the one signal that would have told you which of six layers to look at.

### 6.3 Where does pigpio's stderr go?

pigpio prints diagnostics to **stderr**, e.g.:

```
2026-08-01 09:14:22 initInitialise: Can't lock /var/run/pigpio.pid
2026-08-01 09:14:22 initCheckPermitted:
+---------------------------------------------------------+
|Sorry, you don't have permission to run this program.     |
|Try running as root, e.g. precede the command with sudo.  |
+---------------------------------------------------------+
```

Under systemd, stderr goes to **journald**, not your terminal:

```bash
journalctl -u your-telemetry.service -b --no-pager     # this boot
journalctl -u your-telemetry.service -f                # follow live
journalctl -u your-telemetry.service -p err            # errors only
```

**If pigpio has been printing that box every boot, it's already in your journal and has been the whole time.** Go read it. This is the single highest-value five seconds of Monday morning.

> **Generalizable rule:** before you theorize about a daemon, read its logs. A shocking fraction of "mysterious" service failures have printed the answer, in English, to a log nobody opened.

### 6.4 The struct marshalling trap

`bscXfer` takes a pointer to a struct that **must byte-for-byte match the C definition**:

```c
typedef struct
{
   uint32_t control;          // Write
   int rxCnt;                 // Read only
   char rxBuf[BSC_FIFO_SIZE]; // Read only
   int txCnt;                 // Write
   char txBuf[BSC_FIFO_SIZE]; // Write
} bsc_xfer_t;
```

The C# equivalent:

```csharp
[StructLayout(LayoutKind.Sequential)]
public struct BscXfer
{
    public uint control;
    public int  rxCnt;
    [MarshalAs(UnmanagedType.ByValArray, SizeConst = 512)] public byte[] rxBuf;
    public int  txCnt;
    [MarshalAs(UnmanagedType.ByValArray, SizeConst = 512)] public byte[] txBuf;
}
```

⚠ **`BSC_FIFO_SIZE` in `pigpio.h` is 512, not 16.** The *hardware* FIFO is 16 bytes deep; the struct buffer is 512. Getting this constant wrong is catastrophic and *silent in the good direction*: too small a struct means pigpio writes past the end of your marshalled buffer, corrupting adjacent memory. You may see nothing, or garbage `rxCnt`, or a crash minutes later in unrelated code. **Open `/usr/local/include/pigpio.h` on the Pi and read the actual value. Do not trust a blog post — including this one.**

```bash
grep -n "BSC_FIFO_SIZE\|bsc_xfer_t" -A 10 /usr/local/include/pigpio.h
```

This is a place where your instinct to go read the source is **exactly right**. §16 discusses when it isn't.

### 6.5 The signal-handler hazard (.NET-specific, and nasty)

pigpio installs its own handlers for a broad range of signals so it can call `gpioTerminate()` on Ctrl-C and avoid leaving DMA running.

The .NET runtime **also** relies on signals for core functionality — `SIGSEGV` for null-reference checks and write barriers, and real-time signals for GC thread suspension. A native library that overwrites those handlers can cause the CLR to hang or die in ways that look nothing like the actual cause.

I want to flag this as a **hazard to verify rather than a confirmed cause** of your bug. If, after fixing everything else, you see nondeterministic hangs or the process dying under load, come back to this. The mitigations are `gpioSetSignalFunc()` to reclaim specific signals, or moving to the daemon architecture (§7.4) where pigpio's signal handling lives in its own process and can't touch your runtime.

> **The general concept — worth more than the specific bug:** the process is a shared global namespace. Signals, `errno`, the FPU control word, `atexit` handlers, and the C locale are all **process-global mutable state**. When you load a native library into a managed runtime, you are putting two systems that each assume they own that state into one address space. This is the deep reason "just P/Invoke it" is riskier than it looks, and the deep argument for the out-of-process daemon design.

---

## 7. Concept 5 — pigpio's real contract

### 7.1 Why pigpio demands root when `gpiozero` doesn't

Understanding this makes the permission question stop being folklore.

| What pigpio wants | Why | Access needed |
|---|---|---|
| Read/write GPIO registers | obvious | `/dev/gpiomem` would suffice |
| **DMA controller** | to stream waveforms with µs precision without CPU involvement | **`/dev/mem`** |
| **PWM or PCM peripheral** | as a precise clock source for its sampling loop | **`/dev/mem`** |
| **Physical memory pages** | DMA needs *bus* addresses, not virtual ones | **`/dev/mem`** |
| **BSC slave block** | your I2C-slave receptionist | **`/dev/mem`** |
| Real-time scheduling | to keep 1 µs sampling honest | `CAP_SYS_NICE` |

`/dev/gpiomem` exposes *only* the GPIO register page — deliberately, so unprivileged users can toggle pins without being able to reach the DMA controller or the memory-management unit. pigpio needs several *other* peripheral blocks, so it must map arbitrary physical addresses, so it must open `/dev/mem`, so it must hold `CAP_SYS_RAWIO`.

**So your instinct that "pigpio needs root" is correct as a fact about pigpio.** The error was assuming it was the *only* unsatisfied precondition, and then not verifying the mechanism.

### 7.2 pigpio also opens a socket — and this bites people constantly

`gpioInitialise()` by default **starts a socket interface on TCP port 8888** and creates FIFOs at `/dev/pigpio`, `/dev/pigout`, `/dev/pigerr`. This exists so `pigs` and remote clients can talk to your process.

Consequences you must know:

- **If `pigpiod` is already running (it's a systemd service and is enabled by default on some images), it owns port 8888. Your `gpioInitialise()` will fail** with a bind error, and you will get exactly zero data — while being root the whole time.
- If your app crashes without calling `gpioTerminate()`, port 8888 can stay bound through `TIME_WAIT`, so an immediate restart fails but a restart a minute later succeeds. **This produces a maddening intermittent bug that correlates with nothing.**
- Two instances of your own app cannot both run.

**Check on Monday:**

```bash
systemctl status pigpiod
sudo ss -lptn 'sport = :8888'      # who holds the port
pgrep -a pigpiod
```

**Fix, if you don't need the socket** (you don't, for a self-contained app):

```csharp
gpioCfgInterfaces(PI_DISABLE_FIFO_IF | PI_DISABLE_SOCK_IF);  // BEFORE gpioInitialise
```

⚠ Ordering matters absolutely: all `gpioCfg*` functions must be called **before** `gpioInitialise()`. Called after, they are ignored — silently.

And if `pigpiod` is running and you don't want it:

```bash
sudo systemctl stop pigpiod && sudo systemctl disable pigpiod
```

> **Note the trap this creates for debugging:** the `pigs` CLI tool *requires* `pigpiod`. So to use `pigs` for hardware testing (§13 Step 6) you must **stop your app first**, and to run your app you must **stop `pigpiod` first**. They are mutually exclusive. Plan your Monday around that — it's a sequencing constraint that catches everyone once.

### 7.3 Lifecycle discipline

```csharp
// gpioTerminate() must run, or you leave DMA channels and the socket dangling.
AppDomain.CurrentDomain.ProcessExit += (_, _) => Native.gpioTerminate();
```

And in the unit file:

```ini
[Service]
ExecStart=/usr/bin/dotnet /opt/telemetry/App.dll
KillSignal=SIGTERM
TimeoutStopSec=10
Restart=on-failure
RestartSec=5
```

A DMA channel left running by a process that died without cleanup can corrupt memory in whatever runs next. This is embedded Linux's version of a leaked file descriptor, with much worse consequences.

### 7.4 The architectural alternative you should seriously consider

| | Direct library (`libpigpio.so`) | Daemon client (`libpigpiod_if2.so` → `pigpiod`) |
|---|---|---|
| Privilege | **your app** must be root | only `pigpiod` is root; your app is unprivileged |
| Signals | pigpio's handlers in **your** process ⚠ | isolated in another process ✅ |
| Crash blast radius | takes DMA state with it | daemon survives; app restarts clean |
| Latency | direct MMIO, ~µs | socket round-trip, ~100 µs–ms ⚠ |
| Debuggability | opaque | `pigs` talks to the same daemon **while your app runs** ✅ |
| Attack surface | large (root .NET app) | small (root C daemon, unprivileged app) |

**The security and operability argument for the daemon is strong**, and it's the architecture a senior engineer would probably reach for: put the privileged, signal-hostile, MMIO-touching code in a small dedicated process and talk to it over an IPC boundary. That is *exactly* the sidecar / privileged-helper pattern you'll meet again in Kubernetes (privileged DaemonSet + unprivileged workload) and in systemd itself.

The counter-argument is **latency**, and for I2C slave mode it is a real one: your BSC FIFO is 16 bytes deep and the master doesn't wait for you. Adding a socket round-trip to every service of that FIFO may be the difference between keeping up and overrunning. See §8.5.

You don't have to decide now. But know that "run the whole app as root" is a choice you made by default, not a requirement, and be able to articulate the trade.

---

## 8. Concept 6 — I2C slave mode is hardware, not software

Here is where I think your actual bug lives. This section is the one to read twice.

### 8.1 Master and slave are not symmetric roles

| | Master | Slave |
|---|---|---|
| Owns the clock (SCL) | ✅ | ❌ |
| Initiates transfers | ✅ | ❌ |
| Has an address | ❌ | ✅ |
| Can be implemented in software (bit-bang) | ✅ easily | ❌ essentially not |
| Knows if the other side is silent | ✅ (NACK) | ❌ **cannot distinguish silence from absence** |

That last row is your whole debugging problem in one line. **A slave that receives nothing has no way to tell you whether the master is broken, the wires are wrong, or its own address is wrong.** Silence is the *only* symptom, and it's produced by every possible cause. You have no discriminating signal from inside the application — which is precisely why you must get one from *outside* it (a second Pi, `i2cdetect`, or a logic analyzer).

Slave mode can't be bit-banged because you'd have to sample SDA on an externally-generated clock edge that can arrive at any microsecond, forever, with no missed edges. So it must be dedicated silicon. On a Pi, that silicon is the **BSC slave peripheral** — a single, fixed block, hard-wired to specific pins.

### 8.2 The BSC, in detail

- One instance. **You can be exactly one I2C slave, at one address.**
- **16-byte** hardware RX FIFO and TX FIFO.
- Hard-wired to two specific GPIOs in **ALT3** mode. *Which two depends on the SoC* — §9.
- Configured through `bscXfer()`'s `control` word.
- Historically under-documented: the BCM2835 datasheet covers it in §11; the BCM2711 datasheet **omits the BSC slave section entirely**, and much of pigpio's Pi 4 support was written against reverse-engineered information.

### 8.3 Decoding the control word

The canonical I2C-slave control word is:

```
control = (slave_address << 16) | 0x305
```

`0x305` = 773 = binary `0b10_0000_0101`. Bits 0–13 are copied unchanged into the BSC `CR` register. Decoded against pigpio's own `BSC_CR_*` defines in `pigpio.h`:

| Bit | Value | Name (`pigpio.h`) | Set? | Meaning |
|---|---|---|---|---|
| 0 | 1 | `BSC_CR_EN` | ✅ | **Enable the BSC peripheral** |
| 1 | 2 | `BSC_CR_SPI` | ❌ | SPI mode off |
| 2 | 4 | `BSC_CR_I2C` | ✅ | **I2C mode on** |
| 3 | 8 | `BSC_CR_CPHA` | ❌ | SPI phase (n/a in I2C) |
| 4 | 16 | `BSC_CR_CPOL` | ❌ | SPI polarity (n/a in I2C) |
| 5 | 32 | `ENSTAT` | ❌ | send status register as first I2C byte |
| 6 | 64 | `ENCTRL` | ❌ | send control register as first I2C byte |
| 7 | 128 | `BSC_CR_BRK` | ❌ | abort operation, clear FIFOs |
| 8 | 256 | `BSC_CR_TXE` | ✅ | **Transmit enable** |
| 9 | 512 | `BSC_CR_RXE` | ✅ | **Receive enable** |
| 10 | 1024 | `INVRXF` | ❌ | invert receive status flags |
| 11 | 2048 | `BSC_CR_TESTFIFO` | ❌ | test FIFO |
| 12 | 4096 | `HOSTCTRLEN` | ❌ | enable host control |
| 13 | 8192 | `INVTXF` | ❌ | invert transmit status flags |
| 16+ | — | slave address | — | 7-bit address, shifted left 16 |

Check the arithmetic yourself — it's a good habit with bitfields:
`EN(1) + I2C(4) + TXE(256) + RXE(512) = 773 = 0x305` ✅

So for address `0x13`: `control = (0x13 << 16) | 0x305 = 0x130305`.

⚠ **Address format.** The `0x13` here is the **7-bit** address. If your master (Arduino `Wire`, most Linux tools) also uses 7-bit, they match. But some datasheets and some drivers quote the **8-bit** form, which is the 7-bit address shifted left by one with the R/W bit in position 0 — so 7-bit `0x13` appears as `0x26` (write) / `0x27` (read). **A one-bit-shift address mismatch is one of the most common I2C bugs in existence, and it produces exactly your symptom: total silence, no error, forever.** Verify which convention *each side* uses. Do not assume.

⚠ **Passing `control = 0` disables the peripheral** and resets the BSC pins to inputs. If any code path in your app writes a zeroed struct — a default-constructed `BscXfer`, a reset routine, a reconnect handler — you will silently switch the receptionist off.

### 8.4 The electrical layer

I2C is an **open-drain** bus. Devices can only pull the line *low*; nothing drives it high. The line returns high only through **pull-up resistors**. No pull-ups → the line never rises → no valid signalling → total silence.

**This is a very likely co-factor in your bug**, for a specific reason:

> On Raspberry Pi boards, **only GPIO 2 and GPIO 3** have on-board 1.8 kΩ pull-up resistors — because those are the designated I2C-1 master pins. **The BSC slave pins (10/11 or 18/19) have no on-board pull-ups.**

pigpio can enable the SoC's *internal* pull-ups (~50 kΩ), but 50 kΩ is far too weak for a real I2C bus at any meaningful speed and bus capacitance. It'll work across two inches of jumper wire at 10 kHz on a good day, and fail on your actual harness.

**You need external pull-ups: 4.7 kΩ to 3.3 V on both SDA and SCL** (2.2 kΩ for 400 kHz or longer traces). And:

- **Common ground.** Both devices must share a ground reference. This is the #1 cause of "it works on the bench with a short wire and fails in the enclosure."
- **3.3 V logic only.** The Pi's GPIO is **not** 5 V tolerant. A 5 V master (a classic Arduino) will damage the pin — or appear to work, briefly, and then not. Use a level shifter.
- Keep the bus short. Total capacitance budget is 400 pF.

### 8.5 The FIFO is 16 bytes and nobody waits for you

The master owns the clock. It transmits at its own pace. Your 16-byte RX FIFO fills, and if you haven't drained it, **new bytes are dropped**. There is no backpressure and no error the master will notice.

pigpio's usual pattern is to register a callback on `EVENT_BSC` and call `bscXfer` from it. Under .NET, that means a native callback crossing into managed code — where you must:

- Keep the delegate **alive** (`GCHandle`, or a static field) or the GC will collect it and the native call will jump into freed memory
- Do **nothing slow** in the handler — no logging to disk, no allocation storms, no `lock` contention with your main loop, no `await`
- Copy bytes out into a queue and return immediately

There's also a documented **one-transaction lag** in the request/response pattern: a master that does `write(x); read()` back-to-back gets the *previous* response, because the Pi hasn't serviced the FIFO and loaded the TX buffer yet. The fix is protocol-level — the master must delay between write and read, or you design a request/response protocol that tolerates the lag (sequence numbers, or a GPIO "data ready" line). **If you eventually get data but it's off by one transaction, this is why. It is not a bug in your code.**

> **The backend translation:** this is a bounded queue with no backpressure, a slow consumer, and lossy overflow — i.e. exactly the Kafka-consumer-lag problem, or an SQS visibility-timeout problem, at 16 bytes and microseconds instead of gigabytes and seconds. Same shape, same failure mode, same three fixes (drain faster, buffer more, or push back on the producer). You have been doing distributed systems with your hands.

---

## 9. Concept 7 — The two platform facts that most likely explain your bug

You told me this is a **Compute Module**. That's the highest-information thing you said, because CM4 and CM5 are entirely different worlds here.

### 9.1 Which SoC am I actually on?

```bash
cat /proc/device-tree/model; echo
cat /proc/cpuinfo | grep -E 'Revision|Model'
```

| Board | SoC | pigpio status |
|---|---|---|
| CM3 / CM3+ | BCM2837 | ✅ works |
| **CM4** | **BCM2711** | ✅ works, **but see 9.2 — the BSC pins moved** |
| **CM5** | **BCM2712 + RP1** | ❌ **pigpio does not work at all** |

### 9.2 FACT ONE — On BCM2711 (CM4/Pi 4), the BSC slave pins are GPIO 10 and 11, not 18 and 19

This is the one I'd bet on.

| SoC | Boards | BSC slave SDA | BSC slave SCL | Mode |
|---|---|---|---|---|
| BCM2835 / 2836 / 2837 | Pi 1, 2, 3, Zero, CM3 | **GPIO 18** | **GPIO 19** | ALT3 |
| **BCM2711** | **Pi 4, CM4** | **GPIO 10** | **GPIO 11** | **ALT3** |

**This is not folklore — it is in pigpio's own header.** From `pigpio.h`:

```c
/* BSC GPIO */
#define BSC_SDA           18
#define BSC_SCL_SCLK      19
#define BSC_MOSI          20
#define BSC_MISO          18
#define BSC_CE_N          21

#define BSC_SDA_2711      10      /* ← BCM2711 = Pi 4 / CM4 */
#define BSC_SCL_SCLK_2711 11      /* ←                       */
#define BSC_MOSI_2711      9
#define BSC_MISO_2711     10
#define BSC_CE_N_2711      8
```

pigpio detects the SoC at runtime and drives whichever pair matches. So on a CM4 it is **enabling the BSC on GPIO 10 and 11**, and doing so correctly and silently.

Nearly every tutorial, blog post, and Stack Exchange answer about "Raspberry Pi as I2C slave" was written for the Pi 3 era and says **GPIO 18 and 19**. On a CM4 those pins are simply not connected to the BSC. If your harness is wired to 18/19, then:

- `gpioInitialise()` succeeds ✅
- `bscXfer()` returns success ✅
- The BSC peripheral is genuinely enabled and listening ✅
- It is listening **on two pins nothing is connected to** ❌
- You receive **nothing, forever, with no error** ❌

Note also that GPIO 10/11 are the SPI0 MOSI/SCLK pins. **If SPI0 is enabled in your `config.txt` (`dtparam=spi=on`), it is contending for those exact pads.** Disable SPI while you test.

**Verify the pin function directly — this is a five-second, decisive test.** With your app running:

```bash
grep -n "BSC_SDA\|BSC_SCL" /usr/local/include/pigpio.h   # what YOUR pigpio believes
raspi-gpio get 10,11
raspi-gpio get 18,19
```

Whichever pair reports `func=ALT3` is the pair the BSC is actually driving. That is ground truth from the silicon, and it beats every blog post including this one.

### 9.3 FACT TWO — If this is a CM5, pigpio cannot work. At all.

The CM5 uses the same BCM2712 + **RP1** southbridge as the Pi 5. On these boards the GPIO registers **are not in the main SoC's address space** — they live in the RP1 chip, reached over PCIe.

pigpio's entire design is "mmap `/dev/mem` at the BCM peripheral base and write registers." On a CM5 that mapping succeeds and points at **nothing relevant**. The library's maintainer has stated pigpio won't work on Pi 5-class hardware, and the project is effectively unmaintained for it.

**And here's the cruel part, which is exactly your symptom:** because the mmap *succeeds*, `gpioInitialise()` may well **return success**. You get no error. You get no data. You could spend a week on permissions and never find it, because there is no permission problem — there is no peripheral.

**If you are on CM5, stop immediately and change libraries.** Your options:

| Library | Notes |
|---|---|
| `lgpio` | The maintainer's own successor to pigpio. C library, works on Pi 5/CM5. Closest API migration path. |
| `libgpiod` v2 | The kernel's official character-device GPIO ABI. The right long-term answer; works everywhere; no root needed for GPIO. |
| **Kernel `i2c-slave-eeprom`** | ⚠ **Consider this seriously regardless of board.** A proper kernel driver for I2C slave mode, exposed through sysfs. No root, no MMIO, no P/Invoke, no signal hazards, and the kernel services the FIFO in interrupt context so you don't drop bytes. Your C# just reads a file. |

That last row deserves emphasis. **You may be solving in userspace, with a root-privileged MMIO library and a foreign-function boundary, a problem the kernel already solves properly.** If your telemetry protocol can be shaped as a register file, `i2c-slave-eeprom` (or a small custom I2C slave driver) removes essentially every failure mode in this document at once. That is what a senior engineer would ask before debugging further: *am I on the right layer at all?*

---

## 10. Concept 8 — systemd as an environment, not a launcher

Even setting aside hardening, a service is not a shell. Things that differ:

| | Interactive shell | systemd service |
|---|---|---|
| `PATH` | full, from your profile | minimal, often `/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin` |
| `HOME`, `USER` | set | may be unset or different |
| Working directory | wherever you were | `/` unless `WorkingDirectory=` |
| stdout/stderr | your terminal | journald |
| TTY | present | absent (breaks anything using terminal I/O) |
| Env vars | your profile | **only** what's in `Environment=`/`EnvironmentFile=` |
| `LD_LIBRARY_PATH` | your profile | **usually empty** ⚠ |
| Locale | your locale | often `C` |

That `LD_LIBRARY_PATH` row matters for you specifically. `[DllImport("pigpio")]` makes the .NET runtime search for `libpigpio.so` using the standard loader path. **If `libpigpio.so` was installed to `/usr/local/lib` and `/etc/ld.so.conf.d/` doesn't include it**, your app works when you run it by hand (because your shell profile sets `LD_LIBRARY_PATH`) and throws `DllNotFoundException` under systemd.

```bash
ldconfig -p | grep pigpio        # is it in the loader cache?
ls -l /usr/local/lib/libpigpio*
sudo ldconfig                    # rebuild the cache after installing
```

Two more concepts worth having:

**Ordering ≠ readiness.** `After=network.target` means "start me after systemd *began* network setup," not "after the network *works*." The equivalent trap here: if your service starts before a device is enumerated or a GPIO overlay is applied, it fails. This is the same distinction as a container's `depends_on` versus a real health check — a lesson you already learned in LLM_Monitor with Docker Compose `healthcheck` and startup ordering. **It's the same concept.** Use `ExecStartPre=` with an actual verification command, or `Restart=on-failure` with a backoff, rather than assuming ordering implies readiness.

**Type= matters.** `Type=simple` (the default) means systemd considers the service "started" the instant it `fork`s — before your code has done anything. So `systemctl status` showing `active (running)` is *not* evidence your app initialised successfully. It's evidence a process exists.

> That's another instance of the §0 lesson: **you have been reading green lights that don't measure what you think they measure.** `ps aux` says root but doesn't measure capabilities. `systemctl status` says active but doesn't measure initialisation. Always ask what a green indicator is *actually* wired to.

---

## 11. Concept 9 — Debugging methodology: bisect, don't guess

### 11.1 The core discipline

You have a six-layer stack and a symptom visible only at the top. Guessing at one layer gives you a 1-in-6 shot and, worse, an uninformative result when you're wrong.

**Instead: binary-search the stack. At each layer, ask a question that has a definite answer independent of the layers above it.**

```
                 ┌─────────────────────────┐
                 │  No data in C# app      │
                 └────────────┬────────────┘
                              │
        ┌─────────────────────▼────────────────────┐
        │ Q: Does gpioInitialise() return >= 0 ?   │
        └────┬──────────────────────────────┬──────┘
             │ NO                           │ YES
             ▼                              ▼
    ┌────────────────────┐    ┌──────────────────────────────────┐
    │ SOFTWARE/PERM SIDE │    │ Q: Does an external master SEE    │
    │ read errno:        │    │    us? (i2cdetect from a 2nd dev) │
    │ EACCES → DAC       │    └────┬──────────────────────┬───────┘
    │ EPERM  → caps      │         │ NO                   │ YES
    │ ENOENT → namespace │         ▼                      ▼
    │ EADDRINUSE→pigpiod │  ┌───────────────────┐  ┌────────────────┐
    └────────────────────┘  │ HARDWARE SIDE     │  │ APP LOGIC SIDE │
                            │ • right pins?     │  │ • callback     │
                            │   raspi-gpio get  │  │   registered?  │
                            │ • ALT3 set?       │  │ • delegate     │
                            │ • pull-ups?       │  │   GC'd?        │
                            │ • common ground?  │  │ • struct       │
                            │ • address match?  │  │   layout?      │
                            │ • is master even  │  │ • rxCnt read   │
                            │   transmitting?   │  │   correctly?   │
                            └───────────────────┘  └────────────────┘
```

**One question. Two branches. Half the search space eliminated per test.** Your `User=root` experiment eliminated approximately zero.

### 11.2 Prove the layer below works, independently of your code

**This is the single most powerful technique in embedded debugging.** Before debugging your application, prove the *hardware* works using a tool that isn't your application. If pigpio's own CLI can act as an I2C slave and a second device can see it, then your hardware, wiring, pins, and pull-ups are all good — and every remaining bug is in your C#. That's a colossal reduction in search space, and it takes about ten minutes.

The pigpio maintainer's own verified test (this exact transcript is from the pigpio issue tracker, confirmed working on Pi 3B+ and Pi 4B) is in the runbook, Step 6.

### 11.3 Your observability toolkit

| Tool | Question it answers |
|---|---|
| `journalctl -u svc -b` | **What did the program actually say?** ← always first |
| `strace -f -e trace=openat,ioctl,mmap -p PID` | Which syscalls, with which errno |
| `raspi-gpio get N` | What ALT function is this pin *really* in |
| `i2cdetect -y 1` | Does anything answer at that address |
| `dmesg -T \| tail -50` | Kernel-level device/driver complaints |
| `ss -lptn 'sport = :8888'` | Who owns pigpio's port |
| `nsenter -t PID -m ls /dev` | What does the service's `/dev` actually contain |
| `getpcaps PID` | What capabilities does it really hold |
| `systemd-analyze security svc` | Which hardening directive is cutting me off |
| **Logic analyzer / scope** | **Is the master transmitting at all?** ← the only ground truth |

That last one is not optional in this class of bug. A $10 8-channel logic analyzer plus PulseView/sigrok has an I2C protocol decoder and will tell you in ten seconds whether the master is clocking, what address it's addressing, and whether anyone ACKs. **Every one of the software-side questions in this document is a proxy for what a logic analyzer measures directly.** If you own one, use it first, not last.

### 11.4 Journal, don't just fix

Keep a running log Monday:

```
09:12  systemctl cat → PrivateDevices not set. Hypothesis A weakened.
09:15  journalctl -b | grep pigpio → no "permission" box. Hypothesis A ~dead.
09:20  Added rc check to gpioInitialise → returns 79. INIT SUCCEEDS.
       ⇒ Permissions were never the problem. Move to hardware branch.
09:31  raspi-gpio get 10,11 → func=ALT3. Wiring is on 18/19. FOUND IT.
```

Two reasons. First, without it you will re-test things you already tested and lose track of what's still live. Second, **this log is the artifact that turns a frustrating day into an interview story.** "I had a system where the failure was silent at every layer, so I built a differential diagnosis and bisected the stack" is a much stronger narrative than "it was the wrong pins."

---

## 12. The failure-mode table

Every distinct reason you see "no data," with the signal that distinguishes it.

| # | Cause | Layer | Distinguishing signal | Fix |
|---|---|---|---|---|
| 1 | Not root / no `CAP_SYS_RAWIO` | perm | `gpioInitialise` = -1, `errno`=EACCES/EPERM | root, or `AmbientCapabilities=CAP_SYS_RAWIO` |
| 2 | `PrivateDevices=yes` hides `/dev/mem` | systemd | `errno`=ENOENT; `nsenter … ls /dev/mem` fails | remove the directive |
| 3 | `CapabilityBoundingSet` drops RAWIO | systemd | `getpcaps` shows missing cap despite uid 0 | fix bounding set |
| 4 | `pigpiod` already holds :8888 | pigpio | `gpioInitialise` = -1; `ss -lptn sport = :8888` | stop pigpiod, or `PI_DISABLE_SOCK_IF` |
| 5 | Stale port from unclean exit | pigpio | fails now, works after ~60 s | call `gpioTerminate` on exit |
| 6 | **CM5/BCM2712 — pigpio can't reach RP1** | platform | `/proc/device-tree/model`; **init may still "succeed"** | switch to `lgpio`/`libgpiod`/kernel driver |
| 7 | **Wired to GPIO 18/19 on a BCM2711** | **hardware** | **`raspi-gpio get 10,11` → ALT3** | **rewire to GPIO 10/11** |
| 8 | SPI0 enabled, contending for GPIO 10/11 | config | `dtparam=spi=on` in `/boot/config.txt` | disable SPI |
| 9 | No external pull-ups | electrical | scope: line never returns high | 4.7 kΩ to 3.3 V on SDA & SCL |
| 10 | No common ground | electrical | scope: garbage / floating levels | tie grounds |
| 11 | 5 V master into 3.3 V pins | electrical | works erratically, then not at all | level shifter |
| 12 | 7-bit vs 8-bit address mismatch | protocol | analyzer shows a different address on the wire | align conventions |
| 13 | Master isn't actually transmitting | external | **analyzer shows no clock at all** | fix the master |
| 14 | `control` word wrong / zeroed | app | `bscXfer` returns oddly; peripheral disabled | `(addr<<16) \| 0x305` |
| 15 | `gpioCfg*` called after `gpioInitialise` | app | silently ignored, no error | reorder |
| 16 | Struct layout mismatch (FIFO size) | P/Invoke | garbage `rxCnt`, heap corruption, delayed crash | match `pigpio.h` exactly |
| 17 | Callback delegate garbage-collected | .NET | crash or silence after some minutes | hold a `GCHandle` / static ref |
| 18 | Return values discarded | app | **you cannot tell 1–17 apart** ← you are here | check every rc |
| 19 | FIFO overrun (slow consumer) | timing | partial/corrupt data, not total silence | drain fast, no work in callback |
| 20 | `libpigpio.so` not on loader path | systemd | `DllNotFoundException` in journal | `ldconfig` |
| 21 | Signal handler conflict pigpio↔CLR | runtime | nondeterministic hangs/deaths | `gpioSetSignalFunc`, or daemon mode |

**#18 is the meta-cause.** Fix it first and the other twenty become distinguishable.

---

## 13. THE MONDAY RUNBOOK

Ordered by *information gained per minute*. Do not skip ahead. Write down each result.

---

### ☐ Step 0 — Read the log you already have (2 min)

```bash
journalctl -u your-telemetry.service -b --no-pager | tail -100
journalctl -u your-telemetry.service -b --no-pager | grep -iE 'pigpio|permission|denied|error|exception|not found'
```

> Looking for pigpio's "Sorry, you don't have permission" box, `DllNotFoundException`, or an unhandled exception. **If the answer is here, you're done in two minutes.**

---

### ☐ Step 1 — Identify the board. This may end the investigation. (1 min)

```bash
cat /proc/device-tree/model; echo
grep -E 'Revision|Model' /proc/cpuinfo
uname -a
```

> - **CM5 / BCM2712 → STOP.** pigpio cannot work. Go to Step 9.
> - **CM4 / BCM2711 → the BSC slave pins are GPIO 10 and 11.** Flag this now; check it at Step 5.
> - CM3 / BCM2837 → GPIO 18/19.

---

### ☐ Step 2 — Find out what systemd is actually doing (3 min)

```bash
systemctl cat your-telemetry.service
systemctl show your-telemetry.service \
  -p User -p Group -p PrivateDevices -p ProtectSystem -p DevicePolicy \
  -p DeviceAllow -p CapabilityBoundingSet -p AmbientCapabilities \
  -p NoNewPrivileges -p MemoryDenyWriteExecute -p Type -p Environment
systemd-analyze security your-telemetry.service
```

> **`PrivateDevices=yes` → that is your bug.** Remove it, `daemon-reload`, restart.
> Also note: if there was no `User=` before your edit, it was *already* root and your change was a no-op.

---

### ☐ Step 3 — Verify privilege from the inside (3 min)

```bash
PID=$(systemctl show -p MainPID --value your-telemetry.service)
echo "PID=$PID"
grep -E '^(Uid|Gid|Cap)' /proc/$PID/status
getpcaps $PID
sudo nsenter -t $PID -m ls -l /dev/mem      # ← the decisive namespace test
```

> `CapEff` should include `cap_sys_rawio`. `/dev/mem` must be visible **from inside the service's namespace**.

---

### ☐ Step 4 — Check for the pigpiod collision (2 min)

```bash
systemctl status pigpiod
pgrep -a pigpiod
sudo ss -lptn 'sport = :8888'
ls -l /var/run/pigpio.pid 2>/dev/null
```

> If `pigpiod` is running, it owns the peripheral **and** the port. Your direct-library app cannot initialise.
> `sudo systemctl stop pigpiod` — but remember you'll need it back for Step 6, and it conflicts with your app. One at a time.

---

### ☐ Step 5 — Add the return-value check and run in the foreground (15 min) ⭐

**The highest-value change you will make all day.**

1. Stop the service: `sudo systemctl stop your-telemetry.service`
2. Add the `Pi.Init()` pattern from §6.1 — check `gpioInitialise`'s rc, capture `errno` with `SetLastError=true`, log both.
3. Also log the rc of every `bscXfer` call and the `rxCnt` you get back.
4. Verify the struct against the header: `grep -n "BSC_FIFO_SIZE" /usr/local/include/pigpio.h`
5. Run it directly, watching stderr:

```bash
sudo dotnet /opt/telemetry/App.dll
```

6. In a second terminal, **with your app running**, confirm the pins:

```bash
raspi-gpio get 10,11
raspi-gpio get 18,19
```

> **Decision point.**
> - `gpioInitialise` returns **-1** → permissions/pigpiod. Read the `errno` against the §6.2 table. Branch left.
> - `gpioInitialise` returns **a version number (e.g. 79)** → **permissions were never the problem.** Branch right, to hardware.
> - **Whichever pin pair shows `func=ALT3` is where the BSC actually is.** If that's not where your harness is wired — **you found it.**

---

### ☐ Step 6 — Prove the hardware independently of your code (15 min) ⭐

Take C# out of the loop entirely. This is the maintainer's own verified test.

```bash
sudo systemctl stop your-telemetry.service    # must not compete for the peripheral
sudo pigpiod                                   # temporarily, for the pigs CLI

# Configure BSC as I2C slave at address 0x13
pigs bscx 0x130305
# expect something like:  1 18

# From a SECOND device (another Pi, an Arduino, a USB-I2C adapter)
# wired to the correct BSC pins with 4.7k pull-ups and a common ground:
i2cdetect -y 1
# expect 0x13 to appear in the grid

# Send bytes from the master, then check the slave FIFO:
pigs bscx 0x130305
# expect:  6 18 90 87 51 9 23      ← count, status, then your bytes
```

> - **Address appears + bytes arrive** → hardware, wiring, pull-ups, pins, and the BSC are all fine. **Every remaining bug is in your C#.** Go to Step 7.
> - **Nothing appears** → hardware/wiring. Go to Step 8.
>
> ⚠ Remember to `sudo systemctl stop pigpiod` before running your direct-library app again.

---

### ☐ Step 7 — If hardware is proven good, audit the C# (30 min)

- [ ] Struct layout matches `pigpio.h` **exactly** (`BSC_FIFO_SIZE`, field order, `LayoutKind.Sequential`)
- [ ] `control = (addr << 16) | 0x305` — and `addr` is the **7-bit** form
- [ ] No code path passes `control = 0` (that disables the peripheral)
- [ ] `gpioCfgInterfaces` is called **before** `gpioInitialise`
- [ ] Callback delegate held in a static field or `GCHandle` — not collected
- [ ] Callback does **no** slow work — copy bytes to a queue and return
- [ ] Every P/Invoke return value checked and logged
- [ ] `gpioTerminate()` runs on exit

---

### ☐ Step 8 — If hardware is not proven, go physical (30 min)

- [ ] Pins: **GPIO 10 = SDA, GPIO 11 = SCL** on CM4 (18/19 only on CM3 and older)
- [ ] `raspi-gpio get` confirms **ALT3** on those pins
- [ ] External **4.7 kΩ pull-ups to 3.3 V** on both lines (internal 50 kΩ is not enough)
- [ ] **Common ground** between both devices
- [ ] Master is **3.3 V logic** (Pi GPIO is not 5 V tolerant)
- [ ] `dtparam=spi=on` **removed** from `/boot/config.txt` (SPI0 contends for GPIO 10/11)
- [ ] Address convention (7-bit vs 8-bit) matches on both sides
- [ ] **Logic analyzer on SDA/SCL: is the master clocking at all? What address is on the wire? Does anyone ACK?**

---

### ☐ Step 9 — If CM5, or if you want the robust answer anyway

```bash
# Kernel-native I2C slave, no root, no MMIO, no P/Invoke:
grep -rn "i2c-slave" /boot/overlays/README 2>/dev/null | head
modinfo i2c-slave-eeprom
```

> pigpio is out. Evaluate `lgpio`, `libgpiod` v2, or — likely best — the kernel `i2c-slave-eeprom` driver. Your C# then reads a sysfs file: no privileges, no signal hazards, no dropped FIFO bytes, and the kernel services the interrupt for you.

---

### The one-line summary of the runbook

> **Steps 0, 1, and 5 will very likely find it. Do those three first: read the journal, identify the SoC, and check `gpioInitialise`'s return value.**

---

## 14. Common mistakes and misconceptions

| Misconception | Reality |
|---|---|
| "`ps aux` shows root, so I have full privileges" | It shows euid. Namespaces, cgroups, and capability bounds all still apply. |
| "root can do anything" | Root is shorthand for a set of capabilities that can be individually revoked. |
| "Setting `User=root` grants privilege" | For system units root is already the default. It may have been a no-op. |
| "`systemctl status` shows active, so it started OK" | With `Type=simple`, "active" means "forked," not "initialised." |
| "The library would throw if it failed" | Native code returns error codes. P/Invoke does not translate them into exceptions. |
| "No exception means it worked" | It means nothing at all if you discard return values. |
| "I2C slave is a software mode" | It is a dedicated hardware block on two fixed pins. |
| "The Pi's I2C slave is on GPIO 18/19" | **True before BCM2711. On Pi 4 / CM4 it is GPIO 10/11.** |
| "pigpio works on any Pi" | **It does not work on Pi 5 / CM5 (RP1).** And may fail *silently*. |
| "Internal pull-ups are fine" | ~50 kΩ. Real buses need 4.7 kΩ external. |
| "It's a logic problem, not an electrical one" | On a physical bus, always rule out volts before you debate bits. |
| "I'll just run everything as root, it's simpler" | It's simpler *and* it hides which privilege you actually needed. Capabilities document your requirements. |

---

## 15. Interview relevance and the backend translation

Per your persona's mission, here is the explicit mapping. This bug is not a detour from backend engineering — it's the same curriculum on different hardware.

| What you're doing here | The backend / distributed-systems twin |
|---|---|
| root vs `CAP_SYS_RAWIO` | IAM least-privilege; K8s `securityContext`; scoped service accounts |
| `PrivateDevices=yes` hiding `/dev/mem` | Container namespace isolation; why a root pod still can't see host devices |
| systemd hardening directives | Pod Security Standards; `seccomp`; AppArmor profiles |
| pigpiod as a privileged helper | Privileged sidecar / DaemonSet + unprivileged workload |
| P/Invoke swallowing `errno` | Error-type erasure across service boundaries; why gRPC status codes matter |
| 16-byte FIFO with no backpressure | Bounded queues, consumer lag, lossy overflow — Kafka, SQS, ring buffers |
| Master owns the clock; slave can't tell silence from absence | **Why you cannot distinguish "slow" from "dead" in a distributed system.** This is the FLP impossibility result and the entire reason heartbeats and failure detectors exist. |
| Callback must not block | Event-loop discipline; never block the reactor thread; `async` all the way down |
| `Type=simple` "active" ≠ ready | Liveness vs readiness probes; `depends_on` vs `healthcheck` |
| Bisecting six silent layers | Distributed tracing; the whole motivation for OpenTelemetry |

**The row I'd single out** is "slave can't tell silence from absence." That is *the* foundational problem of distributed systems, and you are meeting it in its purest possible form: a hardware peripheral with literally no way to distinguish "the master is broken," "the wire is cut," and "the master has nothing to say." Every heartbeat, every timeout, every `Ping` RPC, every phi-accrual failure detector in every distributed database exists because that problem is unsolvable without adding an out-of-band signal.

**When you eventually solve this bug, write it up as a story.** "Silent failure across a managed/native boundary in an embedded Linux telemetry path" is a genuinely strong interview anecdote, and it's *differentiated* — a Microsoft SE2 interviewer has heard a hundred "we had a slow query" stories and approximately zero "I bisected a six-layer stack from voltage to CLR" stories. It demonstrates systems depth, methodology, and the security-model fluency the Azure-facing roles you're targeting care about.

---

## 16. A note on your hyperfixation

Your persona says you struggle to use abstractions you don't fully understand, and that you'll read every function in a library before calling it — and that this slows you down badly.

**This bug is the case where that instinct is correct, and it's worth understanding precisely why**, so you can tell the two situations apart in the future.

The rule is about **whether the abstraction leaks**:

> **Read the source when the abstraction has already failed you or is known-leaky.** Skip it when the abstraction is holding.

Consider the difference:

- **LangChain, when your chain works.** The abstraction is holding. Reading every function costs days and buys you nothing — you already have the behavior you need. This is where your instinct is a tax.
- **pigpio's `bsc_xfer_t`, right now.** The abstraction is *actively lying to you*: the documentation references BCM2835 registers, the BCM2711 datasheet omits the BSC slave section entirely, and the pin assignment silently changed between chips. **You are past the point where trusting the interface is viable.** Reading `pigpio.h` and the datasheet is now the *cheapest* path, not the expensive one.

So the discipline isn't "never go deep." It's:

1. **Use the abstraction first.** Check its return values. Let it tell you whether it's working.
2. **When it fails, go deep — but bounded.** Descend one layer, ask one question, come back up.
3. **Descend to answer a specific question, never to achieve completeness.** "What is `BSC_FIFO_SIZE`?" is a bounded descent. "How does pigpio work?" is not a question, it's a hole.

Notice that the runbook in §13 is built entirely on principle 3: every step is a *bounded descent to answer one question*, and you climb back out immediately. That structure is what lets you go as deep as this bug requires without disappearing for a week. **Steal the structure, not just the answers** — it's transferable to LangChain, to YARP, to the Azure SDK, to any library you'll ever be tempted to read end-to-end.

And principle 1 is where your actual failure was: you never let pigpio tell you whether it was working. You discarded the return value, so the abstraction had no channel to report through, and you were forced into deep speculation when a one-line check would have answered it. **Checking return values is what makes it safe to use code you don't fully understand.** That is the concrete, learnable skill your persona says you're missing, and this bug is where to learn it.

---

## 17. Follow-on lectures

Topics that naturally follow, roughly in order of value to your Microsoft SE2 goal:

1. **Linux capabilities & namespaces in depth** — the direct bridge from this bug to Kubernetes `securityContext` and container security. Highest career leverage of anything here.
2. **The kernel character-device model and `libgpiod` v2** — the modern, correct way to do GPIO; ties into how Linux drivers expose hardware to userspace generally.
3. **Writing a Linux kernel module: an I2C slave driver** — would eliminate this entire class of problem, and is a *phenomenal* portfolio piece.
4. **P/Invoke and the managed/native boundary in depth** — marshalling, blittable types, `GCHandle`, `SafeHandle`, callback lifetime, `DllImportResolver`. Directly applicable to .NET backend work.
5. **systemd for service authors** — socket activation, `sd_notify` readiness protocol, watchdogs, resource control. This is the Linux twin of everything you learned about Docker Compose healthchecks in LLM_Monitor.
6. **Failure detection in distributed systems** — heartbeats, timeouts, phi-accrual, FLP impossibility. The generalization of §15's key row.
7. **Observability for embedded Linux** — structured logging to journald, `perf`, `ftrace`, eBPF. The bare-metal cousin of the OpenTelemetry work on your LLM_Monitor roadmap.

---

## 18. Sources

- [**`pigpio.h` — the source of truth**, verified directly for this lecture: `BSC_SDA_2711 = 10`, `BSC_SCL_SCLK_2711 = 11`, `BSC_FIFO_SIZE = 512`, `PI_DISABLE_FIFO_IF = 1`, `PI_DISABLE_SOCK_IF = 2`, `BSC_CR_*` bit values, and "Returns the pigpio version number if OK, otherwise PI_INIT_FAILED"](https://github.com/joan2937/pigpio/blob/master/pigpio.h)
- [pigpio C interface documentation — `gpioInitialise`, `bscXfer`, `gpioCfgInterfaces`](https://abyz.me.uk/rpi/pigpio/cif.html)
- [pigpio FAQ](https://abyz.me.uk/rpi/pigpio/faq.html)
- [pigpio issue #280 — "The Pi4B has no support for SPI/BSC SLAVE peripheral" (contains the maintainer's verified working Pi 4B test transcript, and the GPIO 10/11 ALT3 finding)](https://github.com/joan2937/pigpio/issues/280)
- [pigpio issue #511 — "bsc_xfer for RPI4B (BCM2711) has different register structures"](https://github.com/joan2937/pigpio/issues/511)
- [pigpio issue #490 — "Python I2C slave issue: use of bsc_xfer and bsc_i2c" (the one-transaction-lag behavior)](https://github.com/joan2937/pigpio/issues/490)
- [pigpio issue #586 — "pigpio probably won't work on Pi5 (or later Pi's)"](https://github.com/joan2937/pigpio/issues/586)
- [systemd.exec(5) — full reference for `PrivateDevices=`, `CapabilityBoundingSet=`, `AmbientCapabilities=`, `DevicePolicy=`](https://manpages.debian.org/bookworm/systemd/systemd.exec.5.en.html)
- [Linux Audit — the `PrivateDevices` setting explained](https://linux-audit.com/systemd/settings/units/privatedevices/)
- [Debian Wiki — Service Sandboxing](https://wiki.debian.org/ServiceSandboxing)
- [systemd issue #14117 — "Can't prune /dev without losing CAP_SYS_RAWIO"](https://github.com/systemd/systemd/issues/14117)
- [Raspberry Pi Compute Module documentation](https://www.raspberrypi.com/documentation/computers/compute-module.html)
- [Raspberry Pi Compute Module 5 datasheet (BCM2712 + RP1)](https://datasheets.raspberrypi.com/cm5/cm5-datasheet.pdf)
- [BCM2711 peripherals datasheet](https://datasheets.raspberrypi.com/bcm2711/bcm2711-peripherals.pdf)
- [BCM2835 ARM peripherals datasheet — §11 covers the SPI/BSC Slave block](https://datasheets.raspberrypi.com/bcm2835/bcm2835-peripherals.pdf)
- [Raspberry Pi white paper — Using I2C on Raspberry Pi SBCs](https://pip-assets.raspberrypi.com/categories/685-app-notes-guides-whitepapers/documents/RP-010076-WP-2-Using%20I2C%20on%20Raspberry%20Pi%20SBCs.pdf)
- [Raspberry Pi 5 GPIO: RPi.GPIO not working — RP1 and alternatives](https://raspberry.tips/en/raspberrypi-tutorials/raspberry-pi-5-gpio-rpigpio-not-working-alternatives)
- [Raspberry Pi Stack Exchange — "Raspberry as an I2C SLAVE"](https://iiab.me/kiwix/content/raspberrypi.stackexchange.com_en_all_2022-11/questions/76109/raspberry-as-an-i2c-slave)
- [Raspberry Pi Forums — "RPi as I2C Slave, a summary (2019/03)"](https://forums.raspberrypi.com/viewtopic.php?t=235740)
- [Raspberry Pi Forums — "I2C slave on Raspberry Pi 4 Model B?"](https://forums.raspberrypi.com/viewtopic.php?t=265832)

---

## Appendix — The one-paragraph version

Your application discards the return value of `gpioInitialise()`, so it cannot distinguish "pigpio failed to start" from "pigpio is fine and nobody is talking to us." Fix that first — it's one line and it collapses twenty possible causes into one observable. Then check `/proc/device-tree/model`: if this is a **CM5**, pigpio cannot work at all because the GPIO lives in the RP1 chip, and it will fail *silently*. If it's a **CM4 (BCM2711)**, the BSC slave peripheral is on **GPIO 10 and 11**, not the GPIO 18/19 that every pre-2019 tutorial tells you — confirm with `raspi-gpio get 10,11` looking for `func=ALT3`. Also confirm `pigpiod` isn't already holding the peripheral and port 8888, that `systemctl cat` doesn't show `PrivateDevices=yes` (which hides `/dev/mem` from even a root process), and that you have external 4.7 kΩ pull-ups and a common ground. The deeper lesson is that you tested a hypothesis by observing an outcome nine layers downstream instead of observing the hypothesis's nearest consequence — and that the reason you had to guess at all is that your code threw away the error channel that would have told you the answer.
