2026_10_23_20_00-(Lab-Setup-Work-Plan)

# 010 — Work Plan: A Windows Driver Lab on Your Mac

> **For:** Timothy · **Date:** 2026-10-23
> **Goal:** go from "I have a Mac" to "I built TgCounter (lecture 009), loaded it into a Windows kernel, called it from an app, watched it in WinDbg, and analyzed a crash dump I caused myself."
> **Short answer to your questions:**
> 1. **You don't need a Windows PC.** Your Mac has an Apple-silicon (Arm) chip, so you run **Windows 11 for Arm** inside a virtual machine on the Mac. You don't run a VM inside Windows.
> 2. **Yes, use the larger SSD.** Keep the VM on whichever drive has the most free space. Plan for about 120 GB. The drive your `Studying_Lectures` folder is on showed only about 40 GB free when I checked, which isn't enough.
> 3. **You'll build Arm64 drivers.** That's a bonus: it's the same architecture as Arm Windows laptops (lecture 007).
> 4. **One VM covers almost everything:** building, loading, running, `DbgPrint`, read-only kernel inspection, crash dumps, Driver Verifier and tracing. The one thing it can't do reliably is **live breakpoint debugging** (§Phase 6). That needs a second machine, and it's optional.

---

## What you'll have at the end

| Capability | Phase | Lecture it lets you practice |
|---|---|---|
| A Windows 11 Arm VM, with snapshots to roll back to | 1 | — |
| The VM configured for driver testing (Secure Boot off, test signing, debug output, kernel dumps) | 2 | 006 §9, 003 |
| Visual Studio + WDK building Arm64 drivers | 3 | 009 |
| TgCounter loaded, called, inspected, unloaded | 4 | 009 |
| Read-only kernel inspection (`!drvobj`, `!devstack`, `!process`) | 5 | 001, 008 |
| A crash you caused, its dump analyzed; a live dump; Verifier; a WPR trace | 5 | 002, 003, 004 |
| (Optional) breakpoints and stepping through your driver | 6 | 001 §1, 009 §12 |

Total time, roughly: **one weekend** for Phases 0–4, plus an evening each for Phase 5's labs.

---

## Phase 0 — Check the Mac and choose a hypervisor (30 min)

**0.1 Check what you have** (Apple menu → About This Mac):
- [ ] **Chip:** Apple M-series (it's Arm; that's why you'll install Windows for Arm).
- [ ] **Memory:** you'll give the VM about half. With 16 GB, give it 8 GB. With 8 GB, give it 4–6 GB (it works, but Visual Studio will be slow).
- [ ] **Disk:** pick the drive with **≥ 120 GB free**: about 25 GB for Windows, 30–40 GB for Visual Studio + WDK, plus dumps and snapshots. If the larger SSD is external, use a fast USB-C/Thunderbolt connection and keep it plugged in while the VM runs.

**0.2 Choose the hypervisor.** This is the program that runs the VM. Three realistic choices:

| | **Parallels Desktop** | **VMware Fusion** | **UTM** |
|---|---|---|---|
| Cost | Paid (has a free trial) | Free for personal use | Free, open source |
| Microsoft's position | The **authorized** way to run Windows 11 on Apple-silicon Macs (Microsoft's support page names Parallels Desktop 18–20) | Works; not named by Microsoft | Works; not named by Microsoft |
| Ease | Easiest: it downloads and installs Windows for you | Easy | More manual |
| Turning off Secure Boot (needed for test-signed drivers) | Possible through an advanced VM setting (reported by users, see Phase 2) | A checkbox in VM settings (Advanced) | In the VM's UEFI firmware menu at boot |

**My recommendation:** use **Parallels' free trial** first. It's the path Microsoft supports and the fastest to a working Windows. If Phase 2's go/no-go check (turning on test signing) works, decide then whether to buy it. If you'd rather not pay at all, **VMware Fusion** is the next pick because its Secure Boot setting is a simple checkbox. Don't spend more than an evening choosing: the rest of the plan is identical for all three.

**One limitation to know up front:** Microsoft's support page says nested virtualization isn't supported in these VMs, so **virtualization-based security** (VBS, which includes memory integrity/HVCI) won't be running. That's actually convenient for a test lab. Just remember that a real Arm laptop may have HVCI on (006 §9.4).

---

## Phase 1 — Install Windows 11 for Arm (1–2 h)

- [ ] **Get Windows.**
  - Parallels offers to download and install Windows 11 for you; accept.
  - For VMware Fusion or UTM, download the **Windows 11 Arm64 ISO** from Microsoft (<https://www.microsoft.com/software-download/windows11arm64>). Microsoft says its primary use is creating VMs for development.
- [ ] **Create the VM** with: Windows 11 Arm, **4 CPU cores** (or half your cores), **8 GB RAM** (see 0.1), a **120 GB disk** on the big SSD, **TPM enabled** (Windows 11 setup requires it; the hypervisors provide a virtual TPM), and networking left at the default (shared/NAT).
- [ ] **Install** Windows 11 **Pro**. Create a local account if you're offered the choice.
- [ ] **Install the hypervisor's guest tools** (Parallels Tools / VMware Tools / UTM's SPICE guest tools) for display, clipboard and shared folders.
- [ ] Run **Windows Update** until it says you're up to date.
- [ ] **Take a snapshot** named `clean-windows`. Every later phase can roll back to it.

**Licensing:** Microsoft says each Windows 11 instance needs a Windows 11 Pro license. Windows will install and run without a product key, with an activation watermark and some personalization settings locked, which is fine for trying this out. Get a license if you keep the lab long-term.

**Done when:** you can log in to Windows, browse the web, and copy a file between the Mac and the VM.

---

## Phase 2 — Configure the VM for driver testing (1 h)

This is the **go/no-go** phase: if test signing can't be turned on, nothing later works.

- [ ] **Turn Secure Boot off** (with the VM shut down):
  - **Parallels:** VM configuration → Hardware → Boot Order → *Advanced* → add `vm.efi.secureboot=0`. This comes from a Parallels user-forum answer, not official documentation. Parallels staff suggested a different workaround (remove the TPM, boot, shut down, re-add the TPM). Take a snapshot first, and have the BitLocker recovery key ready in case Windows asks for it.
  - **VMware Fusion:** Settings → Advanced → uncheck *Enable UEFI Secure Boot*.
  - **UTM:** start the VM and press **Esc** at the very beginning to enter the UEFI menu → Device Manager → Secure Boot Configuration → turn off *Attempt Secure Boot* → save and reset.
  - **Check it worked:** in Windows, run `msinfo32` → *Secure Boot State* should say **Off**.
- [ ] **Turn on test signing** (Command Prompt **as administrator**):
  ```
  bcdedit /set testsigning on
  ```
  Reboot. A **"Test Mode"** watermark appears at the bottom right of the desktop. If instead you get *"The value is protected by Secure Boot policy"*, Secure Boot is still on: go back one step. **That's the go/no-go check.**
- [ ] **Let `DbgPrint` messages through.** They're filtered out by default. In `regedit`:
  - create the key `HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\Session Manager\Debug Print Filter`;
  - add a DWORD value named `DEFAULT` = `0xF`;
  - reboot.
- [ ] **Set crash dumps to Kernel memory dump:** System Properties → Advanced → Startup and Recovery → *Kernel memory dump*. Leave "Automatically restart" checked.
- [ ] **Enable a forced-crash key** (lecture 003 §6): add a DWORD `CrashOnCtrlScroll` = `1` under `HKLM\SYSTEM\CurrentControlSet\Services\kbdhid\Parameters`. A Mac keyboard has no Scroll Lock key, so treat this as optional: you'll cause crashes with your own driver instead (Phase 5).
- [ ] **Install the tools:**
  ```
  winget install Microsoft.WinDbg
  winget install Microsoft.Sysinternals
  ```
  You'll use **DebugView** (see `DbgPrint` output), **WinObj** (browse `\Device` and `\GLOBAL??`), **Process Explorer**, and others from the Sysinternals suite. Check that each tool you need has an Arm64 build or runs under emulation.
- [ ] **Snapshot:** `driver-lab-ready`.

**Done when:** the Test Mode watermark shows, `msinfo32` says Secure Boot is off, and WinDbg and DebugView open.

---

## Phase 3 — Install the build tools (1–2 h, mostly downloading)

Microsoft documents that, starting with **WDK 10.0.26100**, the WDK "can be installed and run natively on Arm64 hardware". So you can build Arm64 drivers inside this VM.

- [ ] **Visual Studio 2022 Community** (free): during install, select the **Desktop development with C++** workload. Then, under *Individual components*, add:
  - MSVC v143 – VS 2022 C++ **ARM64/ARM64EC Spectre-mitigated libs** (Latest)
  - MSVC v143 – VS 2022 C++ x64/x86 Spectre-mitigated libs (Latest)
  - C++ ATL and C++ MFC for the latest v143 build tools with Spectre Mitigations (ARM64/ARM64EC, and x86 & x64)
  - **Windows 11 SDK (10.0.26100)** or newer
  - **Windows Driver Kit** (if it's listed as a component; otherwise install the WDK from Microsoft's WDK download page after Visual Studio, and let it install its Visual Studio extension)
- [ ] **Smoke test:** File → New Project → search "driver" → **Kernel Mode Driver, Empty (KMDF)** → name it `HelloKmdf`. Set the platform to **ARM64** (Configuration Manager → Active solution platform → New → ARM64, if it's not already there), then Build. It should build with no errors.
- [ ] **Snapshot:** `toolchain-ready`.

**Done when:** an empty KMDF driver project builds for ARM64 and produces a `.sys` file.

---

## Phase 4 — Build, load and run TgCounter (2–3 h)

This is lecture 009 §13, made concrete for this VM.

**4.1 Get the code into the VM**
- [ ] Copy `lectures/windows_internals/code/tgcounter/` from your repo into the VM, e.g. to `C:\lab\tgcounter\`, through the hypervisor's shared folder or drag-and-drop.

**4.2 Build the driver**
- [ ] New project → **Empty WDM Driver** → name it `TgCounter`. (It's WDM, not KMDF, because 009's driver uses `DriverEntry` and `MajorFunction[]` directly.)
- [ ] Add `tgcounter.c` and `tgcounter_ioctl.h` to the project. The template may add an INF; this legacy driver doesn't need one, so remove the INF from the project if the build complains about it.
- [ ] Platform **ARM64**, configuration **Debug**, then Build. Output: `TgCounter.sys` (and `TgCounter.pdb`, its symbols).
- [ ] **Compare with 009 §2:** open a *Developer Command Prompt* and run `dumpbin /headers /imports TgCounter.sys`. Machine should be ARM64, the subsystem *Native*, and the imports from `ntoskrnl.exe`. Same as the MinGW build, different architecture.

**4.3 Build the client**
- [ ] New project → **Console App (C++)** → name it `tgclient`. Replace its source with `tgclient.c` (you can rename it to `.cpp`; it compiles as C++ too) and add the header. Platform **ARM64**, then Build.

**4.4 Sign the driver with a test certificate** (PowerShell **as administrator**)
- [ ] Create a test certificate:
  ```powershell
  $cert = New-SelfSignedCertificate -Type CodeSigningCert -Subject "CN=TgTest" -CertStoreLocation Cert:\LocalMachine\My
  ```
- [ ] Trust it on this machine:
  - Open `certlm.msc`.
  - Copy the `TgTest` certificate from *Personal → Certificates* into **Trusted Root Certification Authorities** and **Trusted Publishers**.
  - Follow Microsoft's test-signing documentation if anything differs.
- [ ] Sign (Developer Command Prompt as administrator):
  ```
  signtool sign /fd sha256 /sm /s My /n TgTest C:\lab\tgcounter\TgCounter.sys
  ```
  Then `signtool verify /pa /v TgCounter.sys` shows the signature.
  (Visual Studio can also test-sign automatically in the project's *Driver Signing* properties. Either is fine. Doing it by hand once teaches you what's happening.)

**4.5 Load it, use it, unload it** (Command Prompt as administrator; DebugView running as administrator with *Capture → Capture Kernel* checked)
```
mkdir C:\drivers
copy C:\lab\tgcounter\TgCounter.sys C:\drivers\
sc create TgCounter type= kernel start= demand binPath= C:\drivers\TgCounter.sys
sc start TgCounter
```
- [ ] DebugView shows `TgCounter: loaded from \REGISTRY\MACHINE\SYSTEM\...\Services\TgCounter`.
- [ ] Run `tgclient.exe` (as administrator: see the troubleshooting table). Expect `INCREMENT -> 1`, `2`, `3`. Run it again: `4`, `5`, `6`.
- [ ] **Look around:**
  - `regedit` → `HKLM\SYSTEM\CurrentControlSet\Services\TgCounter` (009 §3.1);
  - WinObj → `\Device\TgCounter` and `\GLOBAL??\TgCounter` (009 §7.1).
- [ ] **Predict, then check:** what does `tgclient.exe` print after `sc stop TgCounter`?
- [ ] Clean up: `sc stop TgCounter`, then `sc delete TgCounter`.

**Troubleshooting**

| Symptom | Meaning | Fix |
|---|---|---|
| `sc start` → error **577** ("Windows cannot verify the digital signature") | The driver isn't signed, or the certificate isn't trusted, or test mode is off | Check the watermark; re-run 4.4; `signtool verify` |
| `sc start` → error **1275** ("driver has been blocked from loading") | Wrong architecture (e.g. you built x64) or a policy block | Rebuild as **ARM64**; check the Event Viewer → CodeIntegrity log |
| `bcdedit` → "protected by Secure Boot policy" | Secure Boot still on | Phase 2, first step |
| `tgclient` → error **2** | The driver isn't loaded (no `\??\TgCounter`) | `sc query TgCounter`; `sc start` |
| `tgclient` → error **5** (access denied) | The device's default security restricts who can open it | Run the client as administrator (009 §5 production note) |
| Nothing in DebugView | Print filter, or capture off | Debug Print Filter `DEFAULT` = 0xF and reboot; DebugView as admin with Capture Kernel |
| VM won't boot after a change | — | Restore the last snapshot |

- [ ] **Snapshot:** `tgcounter-works`.

**Done when:** you see the counter go 1, 2, 3 and can point to the service key and the symbolic link.

---

## Phase 5 — Inspect, crash, analyze (an evening per lab)

### 5.1 Read-only kernel inspection (local kernel debugging)
- [ ] `bcdedit /debug on`, then reboot. (This needs Secure Boot off, which you already have.)
- [ ] WinDbg (as admin) → File → *Attach to kernel* → **Local**.
- [ ] `.symfix C:\symbols`, `.sympath+ C:\lab\tgcounter\ARM64\Debug`, `.reload`.
- [ ] With TgCounter loaded, run `lm m TgCounter`, `!drvobj TgCounter 2` (the dispatch table, 009 §12), `!devobj \Device\TgCounter`, `!process 0 0`, and `!devnode 0 1`. Pick a device, then `!devstack` on its PDO (001 §8).
- Local kernel debugging is read-only: no breakpoints and no stepping. Phase 6 covers that.

### 5.2 Cause your own crash, then analyze it (lectures 001, 002)

Add a deliberately bad IOCTL to *your copy* of TgCounter:

```c
// in tgcounter_ioctl.h
#define IOCTL_TGCOUNTER_CRASH \
    CTL_CODE(FILE_DEVICE_TGCOUNTER, 0x8FF, METHOD_BUFFERED, FILE_ANY_ACCESS)

// in TgDispatchDeviceControl, before the code check:
if (code == IOCTL_TGCOUNTER_CRASH) {
    KIRQL old;
    volatile LONG *bad = NULL;
    KeRaiseIrql(DISPATCH_LEVEL, &old);   // now at DISPATCH_LEVEL, like a DPC
    *bad = 1;                            // NULL write at DISPATCH_LEVEL
    KeLowerIrql(old);                    // never reached
}
```

Add a `crash` argument to the client that sends this code. Then:
- [ ] **Predict:** which stop code, and what will P1–P4 be? (Lecture 002 §1.)
- [ ] Run it. The VM blue-screens and reboots. Open `C:\Windows\MEMORY.DMP` in WinDbg.
- [ ] Run lecture 001 §10's first-session steps: symbols, `!analyze -v`, `k` (does the stack show the system-call path from 009 §12?), `!irql`, `ln` on P4, `lmv m TgCounter`.
- [ ] Write the one-sentence conclusion (001 §10).

### 5.3 Live dump (lecture 003)
- [ ] With TgCounter loaded: Task Manager → Details → right-click **System** → *Create live kernel memory dump file* → Kernel stacks. Open it: the code is 0x161, and `!drvobj TgCounter 2` still works. Nothing crashed.

### 5.4 Driver Verifier (lecture 004)
- [ ] `verifier /bootmode resetonbootfail`, then `verifier /standard /driver TgCounter.sys`, then reboot.
- [ ] Load and use TgCounter normally: no violations expected. Then send the crash IOCTL again and compare the stop code and stack with 5.2.
- [ ] `verifier /reset`, then reboot.

### 5.5 A WPR trace (lecture 004)
- [ ] `wpr -start GeneralProfile`, run `tgclient` a few times, then `wpr -stop C:\lab\tg.etl "tgcounter"`. Open it in WPA (Windows Performance Analyzer, installed with the Windows ADK's Performance Toolkit). Find system calls or activity from `tgclient.exe` around that time.

**Done when:** you've written the one-sentence conclusion for your own crash.

---

## Phase 6 — (Optional) live breakpoint debugging

This is the one thing a single VM on your Mac can't do well. Breakpoints in kernel code need **two machines**: a target that stops, and a host running WinDbg that controls it.

| Option | How | Cost | Caveats |
|---|---|---|---|
| **A. Two VMs on the Mac** (debugger VM + target VM, KDNET over the virtual network) | Configure the target with `bcdedit /dbgsettings net hostip:<debugger VM IP> port:50000`, `bcdedit /debug on`; WinDbg on the other VM listens with the key it prints | Free (RAM-heavy: two VMs) | **May not work.** KDNET needs a network adapter it supports, and at least one user has reported KDNET on a Parallels Windows 11 Arm VM connecting but never initializing. Treat it as an experiment, an evening at most |
| **B. A cheap physical Windows PC as the target**, debugged from WinDbg in your Mac's VM over your home network | Target: an inexpensive x64 mini PC or used laptop with a KDNET-supported network adapter; your Mac VM's networking set to *bridged* so both are on the same LAN | One small PC | The **most reliable** option, and it's how real bring-up labs work. Real hardware also gives you real devices (I2C, GPIO, touch) to explore with `!devstack` |
| **C. Cloud VMs** | AWS documents KDNET kernel debugging for Windows EC2 instances (a debugger instance plus a target instance) | Pay per hour | Needs cloud setup; x64 rather than Arm |

**My recommendation:** skip Phase 6 until Phases 1–5 are done. Phase 5 already covers most of what the lectures teach. When you want breakpoints, option **B** is the one that will also serve you longest, and it overlaps with the mini-PC decision you were already considering. You don't need it to finish Phases 1–5.

---

## Snapshot plan (your safety net)

| Snapshot | Taken after | Roll back when |
|---|---|---|
| `clean-windows` | Phase 1 | You want to start over completely |
| `driver-lab-ready` | Phase 2 | A setting broke booting |
| `toolchain-ready` | Phase 3 | Visual Studio / WDK got into a bad state |
| `tgcounter-works` | Phase 4 | A crash lab or Verifier left the VM unusable |

---

## Checklist summary

- [ ] **Phase 0:** chip, memory, ≥ 120 GB on the big SSD; hypervisor chosen (Parallels trial recommended)
- [ ] **Phase 1:** Windows 11 Arm installed, updated, guest tools; snapshot
- [ ] **Phase 2:** Secure Boot **off** → test signing **on** (go/no-go), print filter, kernel dumps, WinDbg + Sysinternals; snapshot
- [ ] **Phase 3:** VS 2022 + ARM64 Spectre libs + SDK 26100 + WDK; empty KMDF builds for ARM64; snapshot
- [ ] **Phase 4:** TgCounter built (ARM64), test-signed, `sc create` / `start`, client prints 1-2-3, registry and WinObj checked, unloaded; snapshot
- [ ] **Phase 5:** local kernel debugging; your own 0xD1 analyzed; a live dump; Verifier; a WPR trace
- [ ] **Phase 6 (optional):** live breakpoints, via a second machine

---

## Sources

Checked 2026-10-23.

- Microsoft Learn: *Download Windows 11 Arm64 ISO* (primary use: creating VMs for development; Apple-silicon Macs supported for Arm64 VMs). https://learn.microsoft.com/windows/arm/iso
- Microsoft Support: *Options for using Windows 11 with Mac computers with Apple M1, M2 and M3 chips* (Parallels Desktop 18–20 authorized; nested virtualization, including VBS, not supported; a Windows 11 Pro license per instance). https://support.microsoft.com/windows/options-for-using-windows-11-with-mac-computers-with-apple-m1-and-m2-chips-cd15fd62-9b34-4b78-b0bc-121baa3c568c
- Microsoft Learn: *Building Arm64 drivers with the WDK* (native Arm64 hosting from WDK 10.0.26100; required VS components; testing on a Windows on Arm device or a Windows 11 Arm64 VM). https://learn.microsoft.com/windows-hardware/drivers/develop/building-arm64-drivers
- Microsoft Learn: the TESTSIGNING boot configuration option; setting up local kernel debugging of a single computer; setting up KDNET network debugging; kernel-mode debugging of a VM via a virtual COM port.
- Parallels forum: disabling Secure Boot for a Windows 11 VM (`vm.efi.secureboot=0`, user-reported; staff TPM workaround). https://forum.parallels.com/posts/946655/
- Parallels forum: a report that KDNET on a Windows 11 Arm VM connects but doesn't initialize (Dec 2025). https://forum.parallels.com/threads/windows-kernel-debugging-unavailable-all-documented-method-dont-work.369021/latest
- AWS documentation: kernel debugging for Windows EC2 instances over the network. https://docs.aws.eu/AWSEC2/latest/UserGuide/troubleshoot-windows-with-kdnet.html

Not verified here: exact menu names in each hypervisor's current version (they change between releases), whether each Sysinternals tool has a native Arm64 build, and whether the WDK appears as a Visual Studio installer component or as a separate download on the day you install. Error codes 577 and 1275 are standard Win32 codes for signature-verification failure and blocked drivers.
