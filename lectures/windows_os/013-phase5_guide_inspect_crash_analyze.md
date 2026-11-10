2026_10_30_01_30-(Phase-5-Guide-Inspect-Crash-Analyze)

# 013 — Phase 5 Guide: Inspect, Crash, Analyze (your own driver, your own blue screens)

> **For:** Timothy · **Date:** 2026-10-30
> **Starts from:** snapshot **`tgcounter-works`** (handoff `011` entry 46). Phases 0–4 are done: TgCounter loads, logs to DebugView, and `tgclient.exe` counts 1-2-3.
> **Follows:** plan `010` §Phase 5, made concrete for *your* setup: VMware Fusion, VS 2026, an ARM64 VM with 4 GB, admin Developer PowerShell, `sc.exe`, and re-signing after every build.
> **Goal:** use lectures 001–004 on a real system. Inspect your driver inside the live kernel, read its counter out of kernel memory, crash the machine on purpose and analyze the dump, take a live dump, and watch Driver Verifier turn a "works on my machine" bug into a deterministic crash.

---

## What you'll be able to do after this phase

| Lab | You will… | Lecture it makes real |
|---|---|---|
| 5.0 | Get the Phase 5 code into the VM without pasting, then build, sign and load it | 009 |
| 5.1 | Attach WinDbg to the running kernel and find TgCounter's dispatch table, device object and **counter value in kernel memory** | 001, 006, 009 |
| 5.2 | Take a live kernel dump (the machine keeps running) and read the same things from it | 003 |
| 5.3 | Make TgCounter blue-screen the VM, then analyze `MEMORY.DMP` to the exact line | 001, 002 (0xD1) |
| 5.4 | Show a bug that "works" without Driver Verifier and crashes every time with it | 004, 005 §8 |
| 5.5 | Record a WPR trace of the client calling the driver and find it in WPA | 004 |

Time: roughly one evening per lab. Labs 5.3 and 5.4 crash the VM on purpose. That's safe because of the snapshots, but take them as instructed.

---

## Ground rules (from what you learned in Phases 2–4)

1. **Type short commands, or paste one line at a time and check the echo.** Long pastes have been truncated inside the VM. That's why the Phase 5 code comes as **files** (§5.0), not code to paste.
2. **In PowerShell, use `sc.exe`, never `sc`.** (`sc` there means `Set-Content`.)
3. **Every rebuild means re-sign, then copy.** VS signs with its own `WDKTestCert`. Re-sign with `TgTest`, stop the driver before copying (a loaded `.sys` can't be overwritten), copy to `C:\drivers\`, then start it.
4. **Work from an admin Developer PowerShell for VS 2026.** Launch `dbgview` from it so DebugView inherits admin rights (Capture → Capture Kernel ✓).
5. **Snapshots before anything risky.** Shut Windows down first (not suspend), then Fusion → Virtual Machine → Snapshots → Take Snapshot.
6. **Predict before you run.** Every lab has a prediction step. Write the prediction down; it's what turns this into learning rather than following steps.

The rebuild loop, which you'll use several times:

```
sc.exe stop TgCounter
cd C:\lab\TgCounter\ARM64\Debug
signtool sign /fd sha256 /sm /s My /n TgTest TgCounter.sys
copy TgCounter.sys C:\drivers\
sc.exe start TgCounter
```

(Build first in VS with **ARM64 / Debug** selected. Run `signtool` after every build.)

---

## 5.0 — Get the Phase 5 code into the VM, build, load (1–1.5 h)

### What changed in the code

The Phase 5 versions are in your repo at **`lectures/windows_internals/code/tgcounter_phase5/`**. The originals in `code/tgcounter/` are unchanged.

| File | Change |
|---|---|
| `tgcounter_ioctl.h` | Two **lab-only** IOCTLs: `IOCTL_TGCOUNTER_CRASH` (function `0x8FF` = **`0x800023FC`**) and `IOCTL_TGCOUNTER_PAGED_AT_DISPATCH` (function `0x8FE` = **`0x800023F8`**) |
| `tgcounter.c` | `DriverEntry` also allocates 4 bytes of **paged** pool (value 42, pool tag `TgTg`) and initializes a spin lock. Dispatch is now a `switch`. **Bug #1**: raise to DISPATCH_LEVEL and write through NULL. **Bug #2**: take a spin lock (so DISPATCH_LEVEL) and read the paged value. Unload frees the allocation. The load message now says `(phase 5 build)` so you can tell which build is running |
| `tgclient.c` | Takes an argument: *(none)* = increment ×3, `get`, `crash`, `paged` |

**Verified here (2026-10-30):**
- `tgcounter.c` compiled cleanly (MinGW-w64, `-Wall -Wextra`) against MinGW's DDK headers, plus a two-line stand-in for `ExAllocatePool2`, which those old headers lack and your WDK has.
- `tgclient.c` compiled and ran under Wine. All four modes fail cleanly with error 2 when no driver exists.
- The compile check caught a real bug in my first draft: a helper named `send` collided with Winsock's `send()` from `windows.h`. It's now called `SendIoctl`.
- **Not run here:** loading this driver into Windows. That's what you're about to do.

### Why bug #2 uses a spin lock, not `KeRaiseIrql`

When compiled, `KeRaiseIrql` became **inline code** (a direct write to the IRQL register) and produced **no import at all**. `KeAcquireSpinLock` became an import of `KeAcquireSpinLockRaiseToDpc`, a real call into the kernel. Driver Verifier can only react to calls it can intercept, so bug #2 takes a spin lock. That's also lecture 005 §6's trap in miniature: holding a spin lock *is* being at DISPATCH_LEVEL.

### Steps

**A. Move the files Mac → VM through a shared folder (no pasting).**
1. On the Mac, in Finder, copy the three files from `Studying_Lectures/lectures/windows_internals/code/tgcounter_phase5/` into `/Volumes/T7/windows_experiment/shared/tgcounter_phase5/`.
2. **Set up the Fusion shared folder**, which is still pending from handoff entry 35. With the VM running: Fusion → Virtual Machine → Settings → **Sharing** → turn on Shared Folders → **+** → choose `/Volumes/T7/windows_experiment/shared` → permissions **Read & Write**.
3. In Windows, File Explorer → address bar: `\\vmware-host\Shared Folders\shared\tgcounter_phase5`. You should see the three files.
4. Copy them into the source folder your VS projects already link to, **overwriting** the old ones:
   ```
   copy "\\vmware-host\Shared Folders\shared\tgcounter_phase5\*" C:\lab\src\tgcounter\
   ```
   Your projects used **Add → Existing Item**, which links rather than copies (handoff entry 38), so VS will build the new files automatically. If the UNC path won't open, drag the files from the Mac's Finder into the VM window instead (VMware Tools supports drag-and-drop).
5. **Check nothing got truncated:** `Get-Content C:\lab\src\tgcounter\tgcounter.c | Measure-Object -Line` should report about **137 lines** (and `tgclient.c` about 55, the header about 27).

**B. Build both projects.** VS 2026 → TgCounter project → **ARM64 / Debug** → Build. Then the tgclient project → **ARM64 / Debug** → Build.
- If the build complains about `ExAllocatePool2` or `POOL_FLAG_PAGED`, your WDK is too old for it, which is unlikely with 10.0.28000. Tell me, and we'll switch to the older `ExAllocatePoolWithTag(PagedPool, …)`.
- The `'gTgT'` pool tag is a multi-character constant. MSVC accepts it, and it's the standard way drivers write tags.

**C. Re-sign, copy and start** with the rebuild loop above. DebugView should show `TgCounter: loaded (phase 5 build) from \REGISTRY\…`. If it still says `loaded from` without `(phase 5 build)`, the old `.sys` is running: check the copy step.

**D. Smoke test.** Don't run `crash` or `paged` yet.
```
C:\lab\tgclient\ARM64\Debug\tgclient.exe
C:\lab\tgclient\ARM64\Debug\tgclient.exe get
```
Expect `INCREMENT -> 1, 2, 3`, then `GET -> 3`.

**E. Shut down and take snapshot `phase5-code-loaded`.** Every crash lab rolls back to here if needed.

**Done when:** the `(phase 5 build)` line appears and `get` returns 3.

---

## 5.1 — Look inside the live kernel (local kernel debugging) (1–2 h)

Local kernel debugging gives WinDbg a **read-only** view of the kernel that's running right now. You can't set breakpoints or stop the machine, but you can read any kernel memory: driver objects, device objects, your counter.

### Turn it on (once)

Admin PowerShell:
```
bcdedit /dbgsettings
```
- If it shows `debugtype  Local`, good.
- If it shows a serial or net type, run `bcdedit /dbgsettings local`.

Then:
```
bcdedit /debug on
```
and **reboot**. (Secure Boot is already off, which this requires.)

### Attach

1. Start TgCounter (`sc.exe start TgCounter`) and run `tgclient.exe` once, so the counter is at 3.
2. Open **WinDbg as administrator** → File → **Attach to kernel** → **Local** tab → OK.
   - **If Local attach fails** on this ARM64 VM (it's the one step in this guide I couldn't verify for Arm): skip to 5.2 and do every command below on the **live dump** instead. You get the same information, frozen at one moment.
3. Symbols (type each line):
   ```
   .symfix C:\symbols
   .sympath+ C:\lab\TgCounter\ARM64\Debug
   .reload
   ```
   The first `.reload` downloads Microsoft's kernel symbols and can take a few minutes on this VM.

### The exercises (predict first, then run)

**1. Is it loaded, and where?**
```
lm m TgCounter
```
Predict: a start and end address in **kernel** space (a very high address), with `(private pdb symbols)` because you built it.

**2. The dispatch table: lecture 009 §4.2, made real.**
```
!drvobj \Driver\TgCounter 2
```
Predict: which `IRP_MJ_*` entries point into `TgCounter`, and where all the others point. Expect `IRP_MJ_CREATE`, `IRP_MJ_CLOSE` and `IRP_MJ_DEVICE_CONTROL` → `TgCounter!Tg…`; everything else → `nt!IopInvalidDeviceRequest`. That table **is** "the I/O manager calls the driver".

**3. The device object, and its extension.**
```
!devobj \Device\TgCounter
```
Note the **`DevExt`** address it prints (the device extension, where `Counter` lives).

**4. Your counter, read straight out of kernel memory.**
```
dt TgCounter!_TG_EXTENSION <DevExt address from step 3>
```
Predict the value first. It should be **3** (or whatever `tgclient get` says).

Then, keeping WinDbg open, run `tgclient.exe` again in PowerShell (→ 4, 5, 6) and repeat the `dt`. It now reads **6**. You just watched a user-mode program change kernel memory through an IRP, and read the result from the debugger.

**5. The paged allocation for lab 5.4.**
```
dd poi(TgCounter!g_PagedValue) L1
!pool poi(TgCounter!g_PagedValue)
```
Predict: the `dd` shows `0000002a` (42). `!pool` says **Paged pool** with tag **`TgTg`**. (The source writes `'gTgT'`; the bytes are stored reversed, so tools display `TgTg`.)

**6. Names in the object manager** (lecture 009 §7.1, 008 §5):
```
!object \Device\TgCounter
!object \GLOBAL??\TgCounter
```
The second is the symbolic link; its target should be `\Device\TgCounter`.

**7. Your code, as ARM64 instructions.**
```
u TgCounter!TgDispatchDeviceControl L20
```
These are ARM64 instructions (`ldr`, `str`, `bl`, registers `x0`…`x30`), not x86. `bl` means "branch with link" (a call). In this Debug build, look for `bl` into `TgCounter!CompleteIrp` and the kernel's spin-lock function.

**8. Another device's stack, for comparison** (lecture 001 §8, 006):
```
!devnode 0 1
```
Pick any device (the VMware NVMe or VMXNET3 entries are interesting), then run `!devstack` on its PDO address. You see PDO, FDO, and maybe filters. TgCounter has no devnode, because it's a legacy non-PnP driver: it created its own device object in `DriverEntry` (009 §3).

### Turn debug mode off before the crash labs

Kernel debugging set to "on" can change what happens at a bugcheck: the kernel may look for a debugger instead of simply writing a dump. Keep the crash labs simple:
```
bcdedit /debug off
```
then reboot. (Turn it back on any time you want local debugging again.)

**Done when:** you've read the counter value out of kernel memory with `dt` and watched it change.

---

## 5.2 — Live kernel dump (30–45 min)

A snapshot of kernel memory while Windows keeps running (lecture 003 §3).

1. TgCounter started, counter at some known value (`tgclient get`).
2. Open Task Manager **as administrator**: type `taskmgr` in your admin PowerShell.
3. **Details** tab → right-click **System** → **Create live kernel memory dump file** → **Full live kernel memory dump**.
   - It needs free memory to copy kernel memory. With a 4 GB VM, close VS first. If it aborts because of memory pressure, use **Kernel stacks** instead, which is smaller but can't show the counter.
4. A dialog shows the file location, under `%LocalAppData%\Microsoft\Windows\TaskManager\LiveKernelDumps`.
5. WinDbg (admin) → File → **Open dump file** → that file. Then `.symfix C:\symbols`, `.sympath+ C:\lab\TgCounter\ARM64\Debug`, `.reload`.
6. **Predict:** the stop code shown when the dump opens. Then check with `!analyze -v`, or the first lines of output. It should be **0x161 LIVE_SYSTEM_DUMP**: a label, not a crash.
7. Repeat 5.1 exercises 2–5 on the dump. The counter value is frozen at the moment of capture: run `tgclient` now and the dump doesn't change.

**Done when:** the dump shows 0x161 and your counter value.

---

## 5.3 — Crash it on purpose, then analyze (1.5–2 h)

### Before you crash

1. Confirm the dump settings (they were set in Phase 2): System Properties → Advanced → Startup and Recovery → **Kernel memory dump**, *Automatically restart* ✓.
2. Confirm debug mode is **off** (`bcdedit` → no `debug Yes` line).
3. **Shut down → snapshot `before-crash-labs`.** Start the VM again and log in.
4. Start TgCounter and DebugView.

### Predict, in writing, before you crash

Using lecture 002 §1:
- Which **stop code**?
- **P1** (the address written)?
- **P2** (the IRQL)?
- **P3** (read or write)?
- Which **function** will `!analyze` name?
- What will the bottom of the stack (`k`) look like: which system-call path from lecture 009 §8?

### Crash

```
C:\lab\tgclient\ARM64\Debug\tgclient.exe crash
```

DebugView may flash `TgCounter: CRASH requested…`, then the VM blue-screens, writes the dump, and reboots.

### After the reboot

1. Log in and wait about a minute (Windows finishes copying the dump from the page file into `C:\Windows\MEMORY.DMP` and may show a "recovered from an unexpected shutdown" message).
2. Check that the dump exists:
   ```
   dir C:\Windows\MEMORY.DMP
   ```
   - If it's missing, the page file may be too small for a kernel dump on this 4 GB VM. Switch to **Automatic memory dump** (Startup and Recovery, or `reg add "HKLM\SYSTEM\CurrentControlSet\Control\CrashControl" /v CrashDumpEnabled /t REG_DWORD /d 7 /f`), reboot, and crash again. Check `C:\Windows\Minidump\` too: a small dump there is still enough for steps 3–6.
3. WinDbg (admin) → Open dump file → `C:\Windows\MEMORY.DMP` → symbols as before.

### The analysis (lecture 001 §10, step by step)

| Step | Command | What to record |
|---|---|---|
| 1 | `!analyze -v` | `BUGCHECK_CODE`, P1–P4, `SYMBOL_NAME`, `MODULE_NAME`, `FAILURE_BUCKET_ID` |
| 2 | `k` | Is `TgCounter!TgDispatchDeviceControl` the first driver frame? Below it: `nt!IofCallDriver` → I/O manager → `nt!NtDeviceIoControlFile` → the system-call entry (ARM64 names differ a little from 009 §12's x64 example) |
| 3 | `!irql` | The IRQL at the crash: does it agree with P2? |
| 4 | `ln <P4>` then `u <P4>` and `ub <P4>` | The faulting instruction: an ARM64 **store** (`str …`) to a register holding 0 |
| 5 | `r` | Find the register used as the store's address. It's 0: that's your NULL |
| 6 | `lmv m TgCounter` | Image path `C:\drivers\TgCounter.sys` and timestamp (proves which build crashed) |
| 7 | `.frame` / `dv` (on the TgCounter frame) | With private symbols: local variables like `code` (should be `0x800023fc`) |

**Expected:** **0xD1 DRIVER_IRQL_NOT_LESS_OR_EQUAL**, P1 = `0` (NULL), P2 = `2` (DISPATCH_LEVEL), P3 = a write, P4 inside `TgCounter!TgDispatchDeviceControl`. If you see **0xA** instead, it's the same rule (lecture 002 §1), just not attributed to a driver. Compare everything against your written prediction.

**Write the one-sentence conclusion** (lecture 001 §10), for example:
"`TgCounter!TgDispatchDeviceControl` wrote through a NULL pointer at DISPATCH_LEVEL (P1 = 0, P2 = 2) while handling IOCTL `0x800023FC`; it was raised to DISPATCH by `KeRaiseIrql`; build timestamp X."

**Reflection question for your notes:** why does this crash read as 0xD1 and not "just a NULL pointer"? Lecture 002's answer: the IRQL decided *which* rule caught it; the NULL is the actual bug.

**Done when:** your prediction and the dump are compared line by line, and the sentence is written.

---

## 5.4 — Driver Verifier: the bug that "works" (1.5–2 h)

This is lecture 004's central claim, demonstrated: Verifier turns a latent bug into a deterministic crash.

### Step 1: without Verifier, predict, then run

Driver started (after the 5.3 reboot: `sc.exe start TgCounter`).

**Predict:** what will `tgclient paged` print? Will it crash?
```
C:\lab\tgclient\ARM64\Debug\tgclient.exe paged
```
Most likely `PAGED -> 42`, **no crash**: the page holding the value is resident in RAM, so the illegal read happens to work. Run it 5–10 times. (If it ever does crash without Verifier, that's the bug showing up by luck, which is lecture 004's point from the other side. Analyze that dump instead.)

### Step 2: enable Verifier on TgCounter only

```
verifier /bootmode resetonbootfail
verifier /standard /driver TgCounter.sys
```
Then **reboot** (Verifier settings take effect at boot, and the driver must be loaded after that). Then:
```
verifier /querysettings
sc.exe start TgCounter
C:\lab\tgclient\ARM64\Debug\tgclient.exe
verifier /query
```
- `/querysettings` should list **TgCounter.sys** and the standard flags.
- The normal increments still work (TgCounter's normal path has no bugs).
- `/query` shows TgCounter being verified, with counters.

### Step 3: predict, then trigger the bug under Verifier

**Predict:** does `paged` crash now? Which stop code? (Lecture 004 A2 and A4.)
```
C:\lab\tgclient\ARM64\Debug\tgclient.exe paged
```

**Expected:** a blue screen. Taking the spin lock makes Verifier's *Force IRQL checking* push pageable memory out of RAM. The read of `*g_PagedValue` then page-faults at DISPATCH_LEVEL, every time. The stop code is most likely **0xD1** (paged memory touched at elevated IRQL), possibly **0xC4** with a Verifier rule in P1. Either way, `!analyze -v` should point at `TgCounter!TgDispatchDeviceControl`.

### Step 4: analyze

Open the new `MEMORY.DMP`, then:
1. `!analyze -v`, and compare it with 5.3: same function, different address. P1 is now the **paged-pool address**, not 0.
2. `!pool <P1>` → **Paged pool**, tag **`TgTg`**. This proves it's your allocation from `DriverEntry`.
3. `!pte <P1>` → the page is **not present**. This is the evidence that Verifier trimmed it.
4. `k` → `KeAcquireSpinLock…` isn't on the stack (you were *holding* the lock), but the dispatch routine is.
5. `!verifier` → shows TgCounter was verified, and with which flags.

**One-sentence conclusion** to write: what the bug is, why it didn't crash before, and why it crashed now.

### Step 5: turn Verifier off (don't skip)

```
verifier /reset
```
Reboot. Then `verifier /querysettings` should say no drivers are verified.

**Done when:** you have two dumps from the same function: one that never happened without Verifier and one that always happens with it, and you can explain the difference using `!pte`.

---

## 5.5 — A WPR trace of your driver being called (1 h)

1. **Recorder:** `wpr.exe` is built into Windows. Check with `wpr -profiles`.
2. **Analyzer:** install WPA (Windows Performance Analyzer). Try `winget search "Performance Analyzer"` and pick Microsoft's package. If none is listed, use the **Windows Performance Toolkit** from the Windows ADK installer. I haven't verified which of these provides an ARM64 build today, so check what installs cleanly.
3. **Record:**
   ```
   wpr -start GeneralProfile
   C:\lab\tgclient\ARM64\Debug\tgclient.exe
   C:\lab\tgclient\ARM64\Debug\tgclient.exe get
   wpr -stop C:\lab\tg.etl "tgcounter calls"
   ```
   (Run the client several times to make it easier to find.)
4. **Read** `C:\lab\tg.etl` in WPA → load symbols (Trace → Configure Symbol Paths: Microsoft's server plus `C:\lab\TgCounter\ARM64\Debug`) →
   - **CPU Usage (Precise)**: find the `tgclient.exe` processes. Each one is a short life: a few milliseconds, mostly waiting on or in the system call.
   - **DPC/ISR**: group by module. Which drivers in *this VM* run the most DPCs and ISRs? Expect VMware's virtual devices and storage. TgCounter has none: it never touches hardware, so it has no interrupts (lecture 005).
5. **Reflection:** why can't you see TgCounter's *own* events here? (It doesn't emit any ETW events. Adding TraceLogging to it would make it a provider, a good later stretch goal.)

**Done when:** you've found `tgclient.exe` in the trace and listed the top DPC/ISR modules in your VM.

---

## Wrap-up

- [ ] Shut down → snapshot **`phase5-done`**.
- [ ] Write down, for the handoff: the stop codes you got in 5.3 and 5.4 (with P1–P4), whether local attach worked on ARM64, and anything that surprised you. I'll fold them into `011`.
- [ ] Recall check (your usual walk-and-talk): explain 5.4 out loud. Why did the same line of code work 10 times without Verifier and crash on the first try with it? Use the words *paged pool*, *spin lock*, *DISPATCH_LEVEL*, *page fault*, *Force IRQL checking*.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `sc.exe start` → **577** | Not re-signed after building (still `WDKTestCert`), or the old `.sys` was copied | Rebuild loop: sign → verify → copy → start |
| `sc.exe start` → **1056** | Already running | `sc.exe stop TgCounter` first |
| `copy` → "being used by another process" | Driver still loaded | `sc.exe stop TgCounter` |
| DebugView shows `loaded from` without `(phase 5 build)` | Old binary | Check the copy step and timestamps (`dir C:\drivers`) |
| `tgclient crash` → `DeviceIoControl failed, 1` (invalid function) | Old driver running (it doesn't know the new IOCTL) | Same as above |
| WinDbg Local attach fails | Debug mode off, not elevated, or unsupported here | `bcdedit` shows `debug Yes`? WinDbg run as admin? Otherwise use the live dump (5.2) |
| `dt TgCounter!_TG_EXTENSION` → "symbol not found" | Symbols for TgCounter not loaded | `.sympath+ C:\lab\TgCounter\ARM64\Debug`, `.reload /f TgCounter.sys`, `lmv m TgCounter` |
| No `MEMORY.DMP` after a crash | Page file too small; or debug mode was on | Automatic dump (`CrashDumpEnabled`=7); `bcdedit /debug off`; check `C:\Windows\Minidump\` |
| VM reboot-loops after enabling Verifier | Verifier on a driver that loads at boot | `resetonbootfail` should catch it; otherwise restore snapshot `phase5-code-loaded` |
| Live dump aborts | Not enough free memory (4 GB VM) | Close VS; choose "Kernel stacks"; consider 5 GB VM memory (handoff Gotchas) |
| Truncated text in files or commands | Paste truncation | Use the shared-folder copy (§5.0) and the line-count check |

---

## Sources

Checked against the lectures' sources and Microsoft documentation (2026-10-30):
- Local kernel debugging setup (`bcdedit /debug on`, local `dbgsettings`).
- WinDbg command references: `!drvobj`, `!devobj`, `!object`, `dt`, `!pool`, `!pte`, `!analyze`, `!irql`, `!verifier`.
- Task Manager live dumps (0x161, save location).
- Bug Check 0xD1 and 0xC4.
- Driver Verifier command line (`/standard`, `/driver`, `/bootmode resetonbootfail`, `/query`, `/querysettings`, `/reset`) and Force IRQL Checking ("when the driver requests a spin lock, calls a synchronization function, or raises IRQL to DISPATCH_LEVEL or higher").
- WPR command-line options; `ExAllocatePool2` / `POOL_FLAG_PAGED`; `KeAcquireSpinLock`.

**Not verified:** local kernel debugging on Windows **ARM64** in a Fusion VM (the live-dump fallback covers it), the exact ARM64 kernel function names in your stacks, which stop code (0xD1 or 0xC4) Verifier reports for bug #2 on your build, and the current winget package for WPA on ARM64. Your results will settle each one, and they belong in the handoff.
