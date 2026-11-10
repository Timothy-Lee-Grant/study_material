2026_10_25_19_45-(Demo-Runbook)

# 012 — Demo Runbook: Showcasing TgCounter, a Kernel Driver Built on a Mac

> **For:** Timothy, to present the lab live or record it
> **State this demo needs:** the VM at or after snapshot **`tgcounter-works`** (taken 2026-10-25). See [`011-session_handoff.md`](011-session_handoff.md) for how everything was built.
> **Length:** ~10 minutes for the core demo (Acts 1–6), ~15 with the optional "change the code live" act.

---

## What you're showing (the one-minute pitch)

> "This is an Apple-silicon Mac (M2, 8 GB). It runs Windows 11 for Arm in VMware Fusion, all free tools. Inside it I wrote a **Windows kernel-mode driver** in C, compiled it for **ARM64** with Visual Studio 2026 and the Windows Driver Kit, signed it with a certificate I made myself, and loaded it **into the running Windows kernel**. A normal program then sends it requests, and the driver keeps a counter in kernel memory."

What happens when the client runs, in the order you'll demonstrate it:

```
 tgclient.exe (user mode)                        TgCounter.sys (kernel mode)
 ─────────────────────────                       ───────────────────────────
 CreateFileW("\\.\TgCounter")  ──IRP_MJ_CREATE──▶  TgDispatchCreateClose → success
 DeviceIoControl(0x80002000)   ──IRP_MJ_DEVICE_CONTROL──▶  TgDispatchDeviceControl
                                                     InterlockedIncrement(&Counter)
        ◀── 4 bytes copied back (METHOD_BUFFERED) ── *(LONG*)SystemBuffer = value
 CloseHandle                   ──IRP_MJ_CLOSE───▶  TgDispatchCreateClose
```

The names connecting the two sides: `\\.\TgCounter` (what the app opens) → `\GLOBAL??\TgCounter` (symbolic link) → `\Device\TgCounter` (the device object `DriverEntry` created).

---

## Part A: Preparation (do this 10–15 minutes before)

### A1. Mac side
- [ ] Plug the **T7 directly** into the Mac (no hub). Keep it plugged in for the whole demo.
- [ ] Close heavy Mac apps. Check **Activity Monitor → Memory → Memory Pressure** is green.
- [ ] Optional: **Fusion → Virtual Machine → Snapshots → `tgcounter-works` → Restore** for a guaranteed known-good starting point. (Restoring discards any changes made since that snapshot.)
- [ ] Start the VM and log in as `Timothy`.
- [ ] Optional, for recording: macOS **⌘⇧5** → Record Selected Portion (around the Fusion window) → Options → Microphone if you'll narrate.

### A2. Windows side
- [ ] Confirm the **"Test Mode"** watermark at the bottom right.
- [ ] Open **Developer PowerShell for VS 2026 → Run as administrator** (the prompt should start at `C:\WINDOWS\system32`). Enlarge the text with **Ctrl + mouse wheel** so the audience can read it.
- [ ] From that window, run `dbgview`. In DebugView: **Capture → Capture Kernel** ✓, **Ctrl+X** to clear.
  - Optional: **Edit → Filter/Highlight → Include:** `TgCounter` to hide the Cache Manager `CcFlushCachePriv` noise. (Or leave it unfiltered and point out that the kernel itself also logs.)
- [ ] Arrange the windows: **PowerShell on the left, DebugView on the right**. Fusion full screen (⌃⌘F) helps.
- [ ] **Reset the driver to "not running"** (so the demo starts from zero):
  ```
  sc.exe query TgCounter
  ```
  - `STATE : 1 STOPPED` → good, it's registered but not loaded. In Act 3 you'll only *start* it.
  - `STATE : 4 RUNNING` → run `sc.exe stop TgCounter` now.
  - `FAILED 1060` (the service doesn't exist) → good too. In Act 3 you'll *create* and then start it.
- [ ] Check the files exist:
  ```
  dir C:\drivers\TgCounter.sys, C:\lab\tgclient\ARM64\Debug\tgclient.exe
  ```

> ⚠️ **Type the commands, or paste one line at a time and check the echo.** Long pasted lines have been cut off inside the VM before. In PowerShell always write **`sc.exe`**, because plain `sc` there means `Set-Content`.

---

## Part B: The demo script

Each act: **do** → **expect** → **say**.

### Act 1: The platform (1 min)
**Do:**
```
winver
bcdedit | findstr /i testsigning
```
**Expect:** Windows 11 Pro **26H2**, build **26300.9711**; `testsigning Yes`.
**Say:** "Windows on Arm in a VM on an M2 Mac. **Test signing** is on, which is why you see the Test Mode watermark: Windows only loads drivers signed by Microsoft, *unless* the machine is put in test mode, where it accepts a developer's own test certificate. That's the standard setup for driver development."

### Act 2: The artifact (2 min)
**Do:**
```
cd C:\lab\TgCounter\ARM64\Debug
dumpbin /headers TgCounter.sys | findstr /i "machine subsystem"
signtool verify /pa TgCounter.sys
```
Optionally open `C:\lab\src\tgcounter\tgcounter.c` in VS and scroll to `DriverEntry`.

**Expect:** `AA64 machine (ARM64)`, `1 subsystem (Native)`; `Successfully verified`.
**Say:** "It's an ARM64 file whose subsystem is **Native**, meaning it isn't an app; it runs inside the kernel. It's signed with my own certificate, `CN=TgTest`. The whole driver is about 90 lines: `DriverEntry` creates a device object, gives it a name user mode can open, and fills in a dispatch table of which function handles which kind of request."

### Act 3: Before: prove nothing is there (1 min)
**Do:**
```
C:\lab\tgclient\ARM64\Debug\tgclient.exe
```
Optionally run `winobj`, open **`\GLOBAL??`**, and show that there's no `TgCounter`.

**Expect:**
```
IOCTL_TGCOUNTER_INCREMENT = 0x80002000
IOCTL_TGCOUNTER_GET       = 0x80006004
CreateFile failed, GetLastError=2 (2 = no such name: is the driver loaded?)
```
**Say:** "The app asks Windows to open `\\.\TgCounter`, and Windows says that name doesn't exist (error 2). Remember those two hex numbers: they're the request codes, built from a device type, a function number and an access level."

### Act 4: Load the driver into the kernel (2 min)
**Do:** (skip `create` if `sc.exe query` showed STOPPED in prep)
```
sc.exe create TgCounter type= kernel start= demand binPath= C:\drivers\TgCounter.sys
sc.exe start TgCounter
```
**Expect:**
- `[SC] CreateService SUCCESS`
- `TYPE : 1 KERNEL_DRIVER` / `STATE : 4 RUNNING (STOPPABLE, …)`
- **DebugView:** `TgCounter: loaded from \REGISTRY\MACHINE\SYSTEM\…\Services\TgCounter`

**Say:** "`sc create` registers the driver as a kernel service in the registry. `sc start` asks the kernel to load the file, check its signature, and call my `DriverEntry`. **That line in DebugView is my code, printing from inside the Windows kernel.** It says where the kernel found the registry key it loaded me from."

Optionally show `regedit` → `HKLM\SYSTEM\CurrentControlSet\Services\TgCounter` (`Type`=1 kernel driver, `Start`=3 demand, `ImagePath`).

### Act 5: Talk to it (2 min)
**Do:**
```
C:\lab\tgclient\ARM64\Debug\tgclient.exe
C:\lab\tgclient\ARM64\Debug\tgclient.exe
```
**Expect:** the first run prints `INCREMENT -> 1`, `2`, `3`; the second prints **`4`, `5`, `6`**.
**Say:** "Each line is one round trip into the kernel: `DeviceIoControl` → the I/O manager builds a request packet (an IRP) → my dispatch routine increments the counter → the value is copied back. **The second run continues at 4**, because the counter doesn't live in the program; it lives in kernel memory, in my device object, and outlives every process that talks to it."

### Act 6: Inspect, then unload (2 min)
**Do:**
1. `winobj` → **`\Device`** → find **`TgCounter`**; **`\GLOBAL??`** → **`TgCounter`** → it points to `\Device\TgCounter`.
2. Ask the audience: *"What will the app print once I stop the driver?"*
3. Then:
```
sc.exe stop TgCounter
C:\lab\tgclient\ARM64\Debug\tgclient.exe
```
4. Refresh WinObj (F5).

**Expect:** `STATE : 1 STOPPED`; DebugView **`TgCounter: unloaded`**; the client is back to **`GetLastError=2`**; the WinObj entries are gone.
**Say:** "Stopping calls my unload routine, which deletes the symbolic link and the device object, exactly undoing `DriverEntry`. The name is gone, so the app is back to 'no such name'. Load it again and the counter restarts at 1, because the memory it lived in was freed."

### Act 7 (optional): Change the code live (5 min)
Shows the real development loop.
1. The driver must be **stopped** (Act 6); you can't overwrite a loaded `.sys`.
2. In VS, change the message in `DriverEntry`, e.g. `"TgCounter: hello from the demo, loaded from %wZ\n"`. Save.
3. **Build → Build Solution** (platform **ARM64**).
4. Re-sign (building replaces your signature with VS's WDKTestCert), then copy and start:
```
cd C:\lab\TgCounter\ARM64\Debug
signtool sign /fd sha256 /sm /s My /n TgTest TgCounter.sys
copy TgCounter.sys C:\drivers\
sc.exe start TgCounter
```
**Expect:** DebugView shows your **new** message.
**Say:** "Edit, build, sign, copy, start: that's the loop driver developers work in."

---

## Part C: After the demo

- `sc.exe stop TgCounter` (keep the service registered; Phase 5 uses it).
- If you changed the code in Act 7 and don't want to keep it: either undo the edit, rebuild, re-sign and copy, **or** shut down and restore snapshot `tgcounter-works`.
- **Shut down Windows** (Start → Power → Shut down) before unplugging the T7.

---

## Part D: If something goes wrong mid-demo

| Symptom | Likely cause | Quick fix |
|---|---|---|
| `sc.exe start` → **1056** "already running" | The driver was left loaded | Fine: carry on with Act 5, or `sc.exe stop` and start again |
| `sc.exe create` → **1073** "already exists" | It's still registered from before | Skip straight to `sc.exe start` |
| `sc.exe start` → **577** | Signature missing (rebuilt without re-signing) | `signtool sign …` → copy → start |
| `sc.exe start` → **1275** | Blocked (wrong architecture or policy) | Make sure you built **ARM64**. Event Viewer → Microsoft → Windows → CodeIntegrity → Operational |
| `copy` → "being used by another process" | The driver is loaded | `sc.exe stop TgCounter` first |
| Client → error **5** | The window isn't elevated | Use the **admin** PowerShell |
| Nothing in DebugView | DebugView isn't elevated, or Capture Kernel is off, or the filter hides it | Launch `dbgview` from the admin window; check the Capture menu; clear the filter |
| `sc` does nothing, or a file named `create` appears | You typed `sc` in PowerShell (that's `Set-Content`) | Use **`sc.exe`**; delete the stray file |
| `dbgview`/`winobj` "not recognized" | An old window that predates the PATH change | Open a new admin window |
| VM is slow or stutters | Mac memory pressure | Close Mac apps; keep the demo to PowerShell + DebugView |
| Anything stranger | — | Shut down → restore snapshot `tgcounter-works` → Part A |

---

## Part E: Command cheat sheet (in demo order)

```
:: prep (admin Developer PowerShell)
dbgview
sc.exe query TgCounter

:: Act 1
winver
bcdedit | findstr /i testsigning

:: Act 2
cd C:\lab\TgCounter\ARM64\Debug
dumpbin /headers TgCounter.sys | findstr /i "machine subsystem"
signtool verify /pa TgCounter.sys

:: Act 3
C:\lab\tgclient\ARM64\Debug\tgclient.exe

:: Act 4
sc.exe create TgCounter type= kernel start= demand binPath= C:\drivers\TgCounter.sys
sc.exe start TgCounter

:: Act 5
C:\lab\tgclient\ARM64\Debug\tgclient.exe
C:\lab\tgclient\ARM64\Debug\tgclient.exe

:: Act 6
winobj
sc.exe stop TgCounter
C:\lab\tgclient\ARM64\Debug\tgclient.exe
```

## Likely audience questions (short answers)

- **"Is this safe?"** It's an isolated VM with snapshots. A bug in kernel code crashes the whole OS (a blue screen), which is exactly why driver work happens in a VM, and why Phase 5 deliberately crashes it on purpose to practice analysis.
- **"Why ARM64?"** The Mac's M2 is an Arm chip, so Windows for Arm runs natively; the driver has to match the kernel's architecture. It's the same architecture as Windows on Arm laptops.
- **"Why does it need test mode?"** Production drivers must be signed through Microsoft. Test mode lets a developer's own certificate through on this machine only.
- **"Why is it called a 'legacy' driver?"** It's started by name with `sc`, not attached to a hardware device by Plug and Play. That's the simplest way to get code into the kernel and learn the I/O path. Real hardware drivers use PnP and usually the KMDF framework.
- **"What did it cost?"** Nothing: VMware Fusion (free for personal use), unactivated Windows 11, VS 2026 Community, the SDK and WDK, Sysinternals.
