2026_10_25_19_42-(Session-Handoff)

# 011 — Session Handoff: Windows Driver Lab Setup (living document)

> **For:** Timothy, and Claude at the start of each new session
> **Sessions covered:** Session 1 (2026-10-23 evening → 2026-10-24 ~02:00); Session 2 (2026-10-24 ~15:00 → ~20:05, ended for a break); Session 3 (2026-10-25, Phase 4)
> **Last updated:** 2026-10-30 01:45
> **Plan this follows:** [`010-lab_setup_work_plan.md`](010-lab_setup_work_plan.md). Its Phases 0–6 still apply, with the changes listed under "Decisions" below.
> **Where we are now:** ✅ **Phases 0–4 complete.** TgCounter (ARM64, signed with CN=TgTest) loads with `sc.exe start TgCounter`, logs to DebugView, and `tgclient.exe` increments the counter. **4 snapshots**, the latest is **`tgcounter-works`**; the VM is **shut down**. A demo runbook exists: [`012-demo_runbook.md`](012-demo_runbook.md). **Next: Phase 5**: follow the dedicated guide [`013-phase5_guide_inspect_crash_analyze.md`](013-phase5_guide_inspect_crash_analyze.md) (it supersedes the Phase 5 notes below).

---

## TL;DR for next session (start here)

**To show off the current state:** follow [`012-demo_runbook.md`](012-demo_runbook.md) (prep → 7 acts → reset).

**To continue the lab: Phase 5 → use [`013`](013-phase5_guide_inspect_crash_analyze.md).** (Older summary kept for reference:)
1. **5.1 Local kernel debugging:** admin prompt → `bcdedit /debug on` → reboot → WinDbg (admin) → File → Attach to kernel → **Local** → `.symfix C:\symbols`, `.sympath+ C:\lab\TgCounter\ARM64\Debug`, `.reload` → with TgCounter started: `lm m TgCounter`, `!drvobj TgCounter 2`, `!devobj \Device\TgCounter`. (Read-only: no breakpoints.)
2. **5.2 Crash on purpose:** add `IOCTL_TGCOUNTER_CRASH` (0x8FF; NULL write at DISPATCH_LEVEL) to the driver + a `crash` argument to the client → rebuild → **re-sign** → `sc.exe stop` → copy → `sc.exe start` → predict the stop code → crash → analyze `C:\Windows\MEMORY.DMP` with `!analyze -v`. **Snapshot first.**
3. 5.3 live dump, 5.4 Driver Verifier, 5.5 WPR trace.

**Still open / unconfirmed:** whether the service is still registered (`sc.exe query TgCounter`); the Phase 4 wrap-up results (second run 4/5/6, WinObj, stop prediction) weren't reported; `certutil -f -addstore TrustedPublisher` (not needed); the installed WDK version (expected 10.0.28000.x); the VM lecture (offered, not confirmed). Shared folder: the `.vmx` has no `sharedFolder` entries even though the source reached `C:\lab\src\`, so how it was transferred isn't confirmed. If the folder is needed, set up Sharing again.

**Snapshots (in order):** `clean-windows-testmode` (10-24 17:56) → `driver-lab-ready` (10-24 18:19) → `toolchain-ready` (10-24 ~20:03) → **`tgcounter-works` (10-25 ~19:35, current)**. All were taken with the VM off.
**Disk:** the VM bundle is **72 GB** on the T7.

## Status board

| Item | Status |
|---|---|
| Fusion installed and permissions granted | ✅ Session 1 |
| VM created (4 cores / 4 GB / 120 GB / vTPM / Secure Boot off) | ✅ Session 1 |
| Windows 11 Pro installed | ✅ Session 1 |
| First-run setup, local account `Timothy` | ✅ Login works, so the 8-vs-9 character password worry is **resolved** |
| Secure Boot Off, confirmed inside Windows (`msinfo32`) | ✅ Session 2 |
| `bcdedit /set testsigning on` + Test Mode watermark | ✅ Session 2: **go/no-go PASSED** |
| VMware Tools / network | ✅ Session 2: Typical install, rebooted, a website loads; the watermark survived the reboot |
| Windows Update | ✅ Session 2: up to date → `winver`: **Version 26H2 (OS Build 26300.9711)**; the Test Mode watermark is still there |
| Snapshot `clean-windows-testmode` | ✅ taken 2026-10-24 17:56 with the VM **off**; renamed (verified in the `.vmsd`) |
| Debug Print Filter `DEFAULT`=0xF | ✅ Session 2 (`reg add`, rebooted) |
| Kernel memory dump (`CrashDumpEnabled`=2) | ✅ Session 2 |
| WinDbg 1.2610.1001.0 | ✅ Session 2 (winget, msstore source; opens as admin, "Debuggee not connected" is expected) |
| Sysinternals Suite 2026-10-15 (ARM64 zip) | ✅ Session 2 (`winget install Microsoft.Sysinternals.Suite`; command aliases such as `dbgview`, `winobj`, `procexp`, `notmyfault` are on PATH) |
| DebugView capture | ✅ Session 2: **user mode proven** (`hello from the VM` via OutputDebugString from PowerShell 7.6.8, PID 8532) and **kernel proven** (`[PlutonQc]pluton::drv::…` DbgPrint lines from PID System, i.e. the Debug Print Filter works) |
| Snapshot `driver-lab-ready` | ✅ 2026-10-24 18:19, VM off (snapshot 2, parent = 1); snapshot 1 renamed `clean-windows-testmode` |
| Phase 3: **VS 2026** + SDK 10.0.28000.2957 + WDK + HelloKmdf ARM64 build | ✅ Session 2: **build succeeded** (~19:58) |
| Snapshot `toolchain-ready` | ✅ ~20:03, VM off (snapshot 3, the current one; verified in the `.vmsd`) |
| Fusion shared folder `/Volumes/T7/windows_experiment/shared` | ⏳ **not set up yet** (no sharing entries in the `.vmx` as of 20:04). The folder exists on the Mac with the tgcounter source |
| Phase 4: TgCounter build/sign/load | ✅ Session 3: loaded, logged, client 1/2/3 (entry 45) |
| Snapshot `tgcounter-works` | ✅ 2026-10-25 ~19:35, VM off (snapshot 4, current; verified in the `.vmsd`) |
| Demo runbook `012-demo_runbook.md` | ✅ written 2026-10-25 |
| Phase 5 (inspect / crash / analyze) | ⏳ next: guide `013` written 2026-10-30; Phase 5 code in `code/tgcounter_phase5/` |
| Phase 6 (optional live debugging) | ⏳ later |

---

## Decisions made this session (these override the 010 plan)

| Topic | 010 plan said | Decided |
|---|---|---|
| Hypervisor | Parallels trial first | **VMware Fusion** (free for personal use). Goal: **everything free** |
| VM memory | 8 GB | **4 GB** (the Mac has only 8 GB; 4 GB stays free for macOS) |
| VM location | "larger SSD" | **T7 external SSD** |
| Windows edition | Pro | **Windows 11 Pro, no product key** (unactivated: watermark plus locked personalization, acceptable) |
| Account | Local if offered | **Local account** created with the `start ms-cxh:localonly` bypass |
| **Visual Studio version** | VS 2022 Community + SDK 10.0.26100 | **VS 2026 Community + the *latest* SDK + the *latest* WDK.** Microsoft's download-the-wdk page (checked 2026-10-24) says "Step 1: Install Visual Studio 2026", with all three links set to "latest". Don't pin versions; the latest SDK and WDK are released as a matched pair |
| Phase 6 (live debugging) | Optional | Only the free options (two VMs over KDNET), if attempted at all |

---

## Hardware and software facts (verified)

**Mac**
- Apple **M2**, **8 GB RAM**, arm64
- macOS **26.3** (build 25D125)
- Internal disk: 228 GB, about 30 GB free (too small for the VM, hence the T7)

**T7 external SSD** (`/Volumes/T7`)
- 932 GB total, about 909 GB free at the start of the session
- Format: **Journaled HFS+** (fine; exFAT would have been a problem)
- Connection: USB, solid state

**VMware Fusion**
- Version **26H1u1** (shows as 26.0.1, build 25689522)
- Installed at `/Applications/VMware Fusion.app` (internal drive, correct)
- Code signature team ID `EG7KH642X6` (VMware, genuine)
- Downloaded from the Broadcom support portal (free account) → VMware Fusion → **26H1**
- macOS permissions: **Accessibility = ON** (this fixed the keyboard not reaching the VM). Input Monitoring: the user was adding Fusion via ⌘⇧G `/Applications/VMware Fusion.app`. It's optional; the outcome isn't confirmed.

---

**Windows guest, as reported by `msinfo32` (Session 2, 2026-10-24 15:00)**

| Item | Value | Notes |
|---|---|---|
| OS | **Microsoft Windows 11 Pro**, version 10.0.**26300** build 26300 | Insider-series build (see Gotchas) |
| HAL | 10.0.26100.1 | The 26100 kernel base, which matches the WDK 10.0.26100 the plan uses |
| Computer name | **DESKTOP-RRMEERP** | |
| User | `DESKTOP-RRMEERP\Timothy` (local account) | |
| System manufacturer / model | VMware, Inc. / **VMware20,1** | Baseboard product VBSA |
| System type | **ARM64-based PC** | Build drivers for the **ARM64** platform |
| Processors | 4 × "Apple silicon, 2000 MHz, 1 core" | The VM's 4 vCPUs |
| BIOS | VMware VMW201.00V.25600138.BA64.2607151225 (7/15/2026), **UEFI** mode | |
| SMBIOS | 3.2 | |
| **Secure Boot State** | **Off** ✅ | Prerequisite for test signing |
| PCR7 configuration | "Elevation Required to View" | msinfo32 wasn't run as admin |
| Boot device | `\Device\HarddiskVolume1` | |
| Locale / time zone | United States / Pacific Daylight Time | |
| RAM | 4.00 GB installed, 3.99 GB total, **1.60 GB available** at idle | Tight; expect Visual Studio to page |
| Virtual memory | 5.37 GB total, 3.29 GB available | |
| Page file | `C:\pagefile.sys`, 1.38 GB | System managed |
| Kernel DMA Protection | Off | Expected in a VM |
| **Virtualization-based security** | **Not enabled** | So HVCI / memory integrity is off; good for a test lab (010 §0) |
| **App Control for Business policy** | **Enforced** | See the note below |
| App Control for Business user mode | Audit | User-mode apps are only logged, not blocked |
| Automatic device encryption | "Elevation Required to View" | Check as admin; BitLocker may turn on (see Gotchas) |
| Hypervisor | "A hypervisor has been detected…" | Normal inside a VM |

**Note on "App Control for Business policy: Enforced":** this is Windows Defender Application Control (WDAC). On a fresh Windows 11 install, an enforced kernel policy is most likely Microsoft's default **vulnerable-driver blocklist**, which blocks known-bad drivers, not test-signed ones in general. It shouldn't stop TgCounter from loading once test signing is on. **If `sc start TgCounter` later fails with error 1275 (or 577 after a correct signature):** check Event Viewer → Applications and Services Logs → Microsoft → Windows → **CodeIntegrity → Operational**; also check Windows Security → App & browser control → **Smart App Control** (turn it **Off** if it blocks the unsigned `tgclient.exe`). Not verified yet; this is a hypothesis to check if something gets blocked.

**Other things visible in the screenshots:** the taskbar network icon shows **no connection** (expected until VMware Tools is installed); the OneDrive icon is crossed out (not signed in, which is fine); the desktop shows the "Learn about this picture" Spotlight icon (harmless); a Command Prompt window was already open on the taskbar.

## Where everything is

```
/Volumes/T7/windows_experiment/
├── 010-lab_setup_work_plan.md                       ← master plan (phases 0–6)
├── 011-session_handoff.md                           ← this file
├── 012-demo_runbook.md                              ← how to showcase TgCounter (prep, 7-act script, troubleshooting)
├── shared/                                          ← Fusion shared folder (Mac ↔ VM file transfer)
│   └── tgcounter/                                   ← copy of the lecture 009 source (tgcounter.c, tgcounter_ioctl.h, tgclient.c)
├── Windows11_Client_arm64_en-us_26300_9457.iso      ← Windows 11 Arm64 ISO, 8.5 GB
│                                                       (volume label CCCOMA_A64FRE_EN-US_DV9)
└── applications/
    ├── VMware-Fusion-26H1u1-25689522_universal.dmg  ← Fusion installer (~500 MB; can delete)
    └── Windows 11 64-bit Arm.vmwarevm/              ← THE VM (bundle)
        ├── Windows 11 64-bit Arm.vmx                ← VM config
        ├── Virtual Disk.vmdk (+ -s001…-s0NN.vmdk)   ← 120 GB growable virtual disk
        ├── Windows 11 64-bit Arm.nvram              ← UEFI settings (Secure Boot state)
        └── vmware.log                               ← useful for diagnosing boot issues
```

- The VM ended up inside `applications/` because that's where the Fusion wizard saved it. That's fine. To move it: shut down, quit Fusion, drag the `.vmwarevm` up one level in Finder, and answer **"I Moved It"** when Fusion asks. (Optional; it hasn't been moved.)
- The installer `.dmg` may still be mounted as **"VMware Fusion"** under Finder → Locations. It's safe to eject.

---

## VM configuration (verified in the `.vmx` and `vmware.log`)

| Setting | Value |
|---|---|
| Guest OS | Windows 11 64-bit Arm |
| CPU | **4 cores** (`numvcpus = "4"`) |
| Memory | **4096 MB** (`memsize = "4096"`) |
| Disk | **120 GB** NVMe, growable (`nvme0:0`); Windows sees C: as 118 GB |
| CD/DVD | `sata0:1` → the ISO above (still attached) |
| Firmware | UEFI (locked because a TPM is present; expected) |
| Secure Boot | **OFF** (unchecked in Settings → Advanced; the log shows `SecureBootModeDisabled`) |
| TPM | **vTPM present**, `vmx.encryptionType = "partial"` (only the TPM files are encrypted) |
| Network | NAT ("Share with my Mac"), adapter **VMXNET3** (Windows has no built-in driver for it; VMware Tools supplies one) |
| Power options | Defaults (Settings → Advanced) |

**Passwords** (deliberately not written here):
- **VMware VM encryption password:** the user said it's the same as the Windows password. ⚠️ Losing it means the VM can't boot (the vTPM is encrypted). Keep it in a password manager. Fusion may also have stored it in the Mac Keychain.
- **Windows local account:** user `Timothy`. The user knows the password.
- ✅ **Resolved (Session 2):** in Session 1 the screenshot showed 9 dots for an 8-character password. The user has since logged in successfully, so the password works as they know it.
- The password was shared in chat; the user was advised not to reuse it anywhere.

---

## What happened this session (chronological)

1. **Assessed the setup.** M2/8 GB Mac; the T7 has plenty of space; the ISO was already downloaded. Chose VMware Fusion for a fully free setup.
2. **Explained memory use.** The VM only uses its 4 GB while running. Shut Windows down (not suspend) and quit Fusion to get all the memory back. Suspending writes RAM to a file on the T7.
3. **Downloaded and installed Fusion 26H1** (chose the newest of 26H1 / 25H2 / 13). Verified it's in `/Applications` and properly signed.
4. **Created the VM** with the wizard → "Install from disc or image" → the ISO. The wizard defaults were 2 cores / 64 GB / 4 GB.
5. **First boot failed:** the VM missed the 3-second "Press any key to boot from CD or DVD" prompt. The log showed `Guest: Status upon boot failure: Time out`.
6. **Fixed the VM settings** while it was shut down: 4 cores, disk enlarged to 120 GB, Secure Boot unchecked. (The user was confused by the Hard Disk "File name" menu, which is just the path breadcrumb T7 → windows_experiment → applications → VM → vmdk. Nothing should be selected there.)
7. **Second boot failed the same way.** Root cause: keystrokes weren't reaching the VM. **Fix:** System Settings → Privacy & Security → **Accessibility → VMware Fusion ON**, quit and reopen Fusion, then boot via **Option + Virtual Machine menu → Power On to Firmware → Boot Manager → EFI VMware Virtual SATA CDROM Drive → Enter → tap space**. Windows Setup then started.
8. **Windows Setup:** selected **Windows 11 Pro**, installed to the 120 GB disk (successful; C: 118 GB, about 100 GB free right after the install).
9. **First-run setup** hit "Let's connect you to a network" (no network driver). The user briefly opened "Install driver" (cancelled; not needed). Used **Shift+F10 → `start ms-cxh:localonly`**, which **worked** and opened "Create a user for this PC".
10. **Stopped at** the create-user screen (name `Timothy`, the password question above).

### Session 2 (2026-10-24 afternoon)

11. The user finished first-run setup and **logged in** as `Timothy` (the password worked).
12. Checked `msinfo32`: **Secure Boot State = Off**. The user shared two msinfo32 screenshots; their details are recorded in "Windows guest, as reported by `msinfo32`" above.
13. **Agreed on the order:** test signing first (an offline go/no-go check), then VMware Tools → updates → snapshot. The user asked for this handoff file to be **kept updated each session** with more context as things progress.
14. **Go/no-go PASSED (~15:05).** Ran `bcdedit /set testsigning on` as admin → restart → the watermark at the bottom right reads:
    ```
    Test Mode
    Windows 11 Pro
    Build 26100.ge_release.240331-1435
    ```
    The watermark shows the **kernel's build tag** (26100, branch `ge_release`, compiled 2024-03-31 14:35), while msinfo32 shows the OS version as 26300. That fits the HAL also reporting 10.0.26100.1: build 26300 runs on the 26100 ("Germanium") kernel base. It may change after Windows Update.
15. **VMware Tools:** installed from the D: drive (VMware Tools disc), **Typical** setup, rebooted. **A website loads**, so the VMXNET3 network driver works. The Test Mode watermark is still there after the reboot.
16. **Windows Update** started.
17. **~17:53: the user reported Windows Update finished.** Next steps given: check the watermark and `winver`, snapshot `clean-windows-testmode`, then the rest of Phase 2 (Debug Print Filter, kernel dump, WinDbg + Sysinternals via winget) → snapshot `driver-lab-ready`.
18. **~17:55: `winver` reports Windows 11 Pro, Version 26H2 (OS Build 26300.9711)**, registered to "Timothy / org name". The Test Mode watermark survived the updates.
19. **First snapshot taken (~17:56) with the VM shut down.** Fusion didn't ask for a name. Verified on disk:
    - `Windows 11 64-bit Arm.vmsd`: `snapshot.numSnapshots = "1"`, `snapshot0.displayName = "Snapshot"`, `snapshot0.filename = "Windows 11 64-bit Arm-Snapshot1.vmsn"`
    - `Windows 11 64-bit Arm-Snapshot1.vmsn` (2.4 MB: config and NVRAM only, no RAM image, because the VM was off)
    - A new delta disk `Virtual Disk-000001.vmdk` (+ `-s001…-s031`). **From now on, all disk writes go into this delta**, and the original `Virtual Disk.vmdk` is frozen as the snapshot's base. Never delete or move individual `.vmdk` files by hand.
    - To rename: Fusion → Virtual Machine → **Snapshots…** → select "Snapshot" → edit the name → `clean-windows-testmode`.
20. **~18:05: rest of Phase 2 done** in an admin Command Prompt (`Microsoft Windows [Version 10.0.26300.9711]`):
    - `reg add "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Debug Print Filter" /v DEFAULT /t REG_DWORD /d 0xF /f` → success
    - `reg add "HKLM\SYSTEM\CurrentControlSet\Control\CrashControl" /v CrashDumpEnabled /t REG_DWORD /d 2 /f` → success (2 = kernel memory dump)
    - `winget install Microsoft.WinDbg` → accepted the msstore source terms → **WinDbg 1.2610.1001.0** installed
    - `winget search Sysinternals` → the correct ID is **`Microsoft.Sysinternals.Suite`** (the 010 plan's `Microsoft.Sysinternals` was wrong). Individual tools also exist (e.g. `Microsoft.Sysinternals.DebugView`).
    - `winget install Microsoft.Sysinternals.Suite` → downloaded `SysinternalsSuite-ARM64.zip` (75.7 MB) → about 56 command aliases added (`Dbgview`, `Winobj`, `procexp`, `Procmon`, `notmyfault`, `sigcheck`, `PsExec`, `handle`, `RAMMap`, `vmmap`, …). The PATH was modified, so a new shell is needed.
    - Rebooted. `bcdedit` `{current}` shows **`testsigning Yes`**, `isolatedcontext Yes`, `allowedinmemorysettings 0x15000075`, `nx OptIn`, `bootmenupolicy Standard`, `recoveryenabled Yes`; `{bootmgr}` timeout 30. Boot manager identifiers: resumeobject `{ac7b820b-cf8f-11f1-90fd-a35bc1c378a0}`, recoverysequence `{ac7b820d-…}`. No `debug` entry yet (Phase 5 adds `bcdedit /debug on`).
21. **~18:09: the user opened WinDbg (as Administrator)** and looked for "Capture". Clarified that **Capture Kernel is in DebugView**, not WinDbg. Launch it with `dbgview` from a new admin prompt → Capture menu → Capture Kernel + Enable Verbose Kernel Output + Capture Events. It stays mostly empty until a driver prints.
22. **~18:13: DebugView running** (title "DebugView on \\DESKTOP-RRMEERP (local)"). The Capture menu shows Win32 ✓, Global Win32 ✗, Kernel ✓, Verbose Kernel Output ✓, Pass-Through ✓, Events ✓, Log Boot ✗. No output, which the user worried was a problem; **it's expected** (a clean Windows install barely uses DbgPrint/OutputDebugString). Suggested an optional user-mode test from PowerShell:
    ```powershell
    Add-Type -Name D -Namespace W -MemberDefinition '[DllImport("kernel32.dll")] public static extern void OutputDebugString(string s);'
    [W.D]::OutputDebugString("hello from the VM")
    ```
    **Result (~18:17): worked.** See entry 23.
23. **~18:17: DebugView verified end to end.** The user ran the test from **PowerShell 7.6.8 (Administrator, `pwsh.exe`, arm64 Store package)**. Output:
    - `hello from the VM` (PID 8532) → **user-mode OutputDebugString capture works**.
    - Many lines from **PID System**: `[PlutonQc]pluton::drv::SpuOps::Ope…`, `pluton::drv::SpuDevice::…`, `QcDrvQuerySpcom(onecore\…`, `QcDrvEvtIoDeviceControl(…`. These are **kernel DbgPrint messages from Microsoft's Pluton security-processor driver (Qualcomm "Qc"/SPU flavour)**, which ships in Windows on Arm and loads even in this VM → **kernel capture plus the Debug Print Filter (DEFAULT=0xF) are proven**. (It's a nice real-world example of a WDF driver's IOCTL handler, `EvtIoDeviceControl`, for later lectures.)
    - Other lines: PID 7720 `[CORE] Subkey 'Software\Polici…'`, PID 6104 `[react-native-xaml] Unhandled call…`, `Couldn't determine flyout target` (shell/UI noise).
24. **~18:19: Windows shut down, snapshot 2 `driver-lab-ready` taken**, and snapshot 1 renamed to `clean-windows-testmode`. Verified in the `.vmsd`: `snapshot.numSnapshots = "2"`, snapshot1.parent = 1, current = 2. Disk chain: `Virtual Disk.vmdk` (base, frozen) → `-000001.vmdk` (frozen, snapshot 2's base) → `-000002.vmdk` (active writes). The VM bundle is **36 GB** on the T7.
25. **Phase 3 instructions given:** first read learn.microsoft.com/windows-hardware/drivers/download-the-wdk to find the **VS version (2022 vs 2026) and SDK version** the current WDK pairs with (the 010 plan assumed VS 2022 + SDK 10.0.26100; this may be outdated by Oct 2026, not verified). Then VS Community → Desktop C++ workload + ARM64/ARM64EC and x64/x86 Spectre libs + matching Windows 11 SDK + Windows Driver Kit component (if listed) → otherwise a standalone WDK + VS extension → HelloKmdf (KMDF Empty) ARM64 build → snapshot `toolchain-ready`. If the build fails, likely MSB8040 (missing Spectre libs).
26. **~18:30: the user read the WDK page.** It lists 3 steps, each linked as "latest": (1) install **Visual Studio 2026**, (2) download the SDK, (3) download the WDK. The user asked whether to pin versions. **Answer: no**; "latest" SDK + WDK is the matched set. **Decision: VS 2026** (this overrides the 010 plan's VS 2022). Told the user to look for a required-components list under Step 1; otherwise: Desktop C++ workload + ARM64/ARM64EC and x64/x86 Spectre-mitigated libs + the Windows Driver Kit component if listed; let the WDK install its VS extension.
27. **Memory clarification (the user's question):** the user thought the VM's 4 GB and the Mac's 4 GB are fully separate. Explained: the 4 GB is the guest's **ceiling**, not a reservation; `vmware-vmx` is a normal macOS process sharing the 8 GB physical RAM with macOS, Fusion overhead and apps; under memory pressure macOS compresses or swaps **including VM memory**, which slows Windows. Also admitted the earlier "close Mac apps" advice mixed this up with a separate **guest-side** problem (only ~1.6 GB free inside Windows → Windows uses its own page file). **Practical rule:** check Activity Monitor → Memory → **Memory Pressure**: green = fine; yellow/red = close Mac apps. (A possible lecture topic.)
28. **~18:50: Visual Studio installer**: **Visual Studio Community 2026 — October 2026 Feature Update (18.11.1)**. The WDK page's Step 1 says driver development is supported in VS 2026 Community/Professional/Enterprise and lists the required Individual Components (verbatim):
    - C++ Spectre-mitigated libraries for x64/x86 (Latest MSVC)
    - C++ Spectre-mitigated libraries for ARM64/ARM64EC (Latest MSVC)
    - C++ ATL with Spectre mitigations for x64/x86 (Latest MSVC)
    - C++ ATL with Spectre mitigations for ARM64/ARM64EC (Latest MSVC)
    - C++ MFC with Spectre mitigations for x64/x86 (Latest MSVC)
    - C++ MFC with Spectre mitigations for ARM64/ARM64EC (Latest MSVC)
    - Windows Driver Kit
    
    The user's selection at this point: the Desktop C++ workload ✓ (defaults include MSVC Build Tools x64/x86 + ARM64/ARM64EC, plain non-Spectre ATL both architectures, **Windows 11 SDK 10.0.26100.9457**, CMake, vcpkg, Copilot, IntelliCode, test adapters) + **only the two Spectre libs** ✓. The installer also offers pinned MSVC **v14.50 / v14.51** variants (use "Latest" instead). **Missing:** the 4 ATL/MFC-with-Spectre components + Windows Driver Kit. Told the user to search `spectre` and `driver kit`, add them, then install; afterwards still run the page's Step 2 (SDK) + Step 3 (WDK) links for the matched pair. Optional: uncheck Copilot, IntelliCode and test adapters to save resources.
29. **~18:55: all 7 required components are selected** (verified in a screenshot of Installation details → Individual components: Spectre libs ARM64 + x64/x86, ATL with Spectre x64/x86 + ARM64, MFC with Spectre x64/x86 + ARM64, **Windows Driver Kit**), plus the Desktop C++ workload and the core editor. Install location `C:\Program Files\Microsoft Visual Studio\18\Community`. **Total space required 17.61 GB.** Mode: "Install while downloading". Installer version 4.11.24.2075 (partly hidden). The user is clicking Install. **After it finishes:** the WDK page's Step 2 (SDK, latest) + Step 3 (WDK, latest; accept the VS extension) → HelloKmdf ARM64 smoke test → snapshot `toolchain-ready`.
30. **~19:35: Visual Studio 2026 (18.11.1) finished installing.** Now installing the **SDK from the WDK page's Step 2: Windows Software Development Kit 10.0.28000.2957** → `C:\Program Files (x86)\Windows Kits\10\` (the common Windows Kits path), 3.6 GB. **C: free space is 67.0 GB** (it was ~100 GB before updates + VS). Notes:
    - SDK **28000** is newer than the guest OS (26300 / 26100 kernel). Fine: the SDK/WDK version is the *build* toolset, and drivers declare their minimum target OS.
    - **The WDK (Step 3) must also be 10.0.28000.x.** The user was told to check the WDK installer title bar.
    - ⚠️ Possible later issue (not verified): a newer WDK may default KMDF projects to a **KMDF version newer than the guest's `Wdf01000.sys`**. A KMDF driver would then build but fail to load. If that happens, lower the KMDF version in Project Properties → Driver Settings → KMDF. **TgCounter is WDM, so this doesn't affect it**; it only matters for KMDF projects like HelloKmdf if they're ever loaded.
31. **~19:47: SDK and WDK installed** (the user said "installed those two"; the WDK version number wasn't reported, so **confirm it's 10.0.28000.x** if anything is odd). VS 2026 opened. Created **HelloKmdf** from the **Kernel Mode Driver, Empty (KMDF)** template. Solution Explorer: References, External Dependencies, Driver Files (holds the INF), Header Files, Resource Files, **Source Files (empty)**. Toolbar: `Debug` | **`x64`** (the default platform) | the run target "Debugging Tools for Windows - Kernel Debugger" (ignore it; that's for Phase 6 live debugging). The user couldn't find "platform": it's the **`x64` dropdown**; switch to **ARM64** (or Configuration Manager → Active solution platform → New → ARM64, copy from x64).
    - **The empty template has no `DriverEntry`**, so it would fail with LNK2019. Gave the user a minimal **`Driver.c`** (must be .c) based on Microsoft's KMDF Hello World tutorial: `DriverEntry` → `WDF_DRIVER_CONFIG_INIT(&config, HelloKmdfEvtDeviceAdd)` → `WdfDriverCreate`; `HelloKmdfEvtDeviceAdd` → `WdfDeviceCreate`; both `KdPrintEx((DPFLTR_IHVDRIVER_ID, DPFLTR_INFO_LEVEL, ...))`.
    - Expected: `Build: 1 succeeded` → `ARM64\Debug\HelloKmdf.sys` + `.pdb` + a package folder. HelloKmdf is a **build-only smoke test**; it won't be loaded.
32. **~19:51: first build FAILED: 0 succeeded, 1 failed (7.5 s)**, platform **ARM64** ✅ (the user found the dropdown). Project path: **`C:\Users\Timothy\source\repos\HelloKmdf\HelloKmdf\Driver.c`**. Cause: **text was lost while pasting** in the second function: line 17 `PWDFDEVICE_INIT DeviceInit` → `PWDFDDeviceInit`; line 20 `UNREFERENCED_PARAMETER(Driver);` → `UNREFERENCED_PARAMETE`; line 23 `WdfDeviceCreate(&DeviceInit, WDF_NO_OBJECT_ATTRIBUTES, &device)` → `WdfDeviceCreatCT_ATTRIBUTES, & device)`. Errors: C2081, C4028, C2065 ×2, C2146 (mentions `DbgPrintEx`, since `KdPrintEx` expands to it in Debug builds), C2059, warning C4047, plus IntelliSense E0141/E0020/E0040/E0065. **The toolchain itself is fine** (the WDK headers resolved; no MSB8040). The user was told to replace the function and check the text, typing by hand if pasting fails again.
    - ⚠️ **Gotcha: pasting from the Mac into the VM may drop chunks of text** (or text was lost while editing). Check pasted code before building. Not confirmed which.
33. **~19:58: HelloKmdf ARM64 Debug build SUCCEEDED** after fixing the paste damage. **Phase 3 is functionally complete.** (`dumpbin` machine check not done; optional.)
34. **Phase 4 prep by Claude (Mac side):** found the TgCounter source at **`~/Desktop/projects/Studying_Lectures/lectures/windows_internals/code/tgcounter/`** (`tgcounter.c` 88 lines, `tgcounter_ioctl.h` 18, `tgclient.c` 35; legacy WDM, `\Device\TgCounter`, link `\??\TgCounter`, user path `\\.\TgCounter`, IOCTLs 0x800 INCREMENT / 0x801 GET, device type 0x8000). **Copied it to `/Volumes/T7/windows_experiment/shared/tgcounter/`** (a copy; the lectures repo stays the source of truth) so it can go into the VM through a **Fusion shared folder** instead of pasting.
35. **Next steps given:** (1) shut down → snapshot `toolchain-ready`; (2) Fusion Settings → Sharing → Enable Shared Folders → add `/Volumes/T7/windows_experiment/shared` (Read & Write) → in Windows `\\vmware-host\Shared Folders\shared\tgcounter` → copy to `C:\lab\tgcounter\`; (3) Phase 4: an **Empty WDM Driver** project `TgCounter` in `C:\lab\` + Add Existing `tgcounter.c` and `tgcounter_ioctl.h` → ARM64 → build (remove the INF if it complains); a **Console App (C++)** `tgclient` → replace the .cpp with `tgclient.c` + the header → ARM64 → build; then the 010 plan's §4.4 signing and §4.5 `sc create/start` + DebugView.
36. **~20:03: the user shut down the VM and took snapshot 3 `toolchain-ready`.** Verified in the `.vmsd`: `numSnapshots = 3`, current = 3, names `clean-windows-testmode` → `driver-lab-ready` → `toolchain-ready`. VM bundle: **63 GB** (was 36 GB before VS/SDK/WDK). T7: 85 GB used / 846 GB free.
37. **~20:05: Session 2 ended; the user is taking a break.** State at the break: VM **off**; the shared folder is **not yet configured** in Fusion; Phase 4 not started. Resume from the TL;DR at the top.

### Session 3 (2026-10-25)

38. **The user asked for the Phase 4 steps.** State check: VM **running**; `.vmx` has **no shared folders configured** yet. Detailed steps given (they refine the TL;DR):
    - **Folder layout (changed):** source in **`C:\lab\src\tgcounter\`**, so it doesn't clash with VS's `C:\lab\TgCounter` (Windows paths ignore case). Projects: `C:\lab\TgCounter\` (Empty WDM Driver) and `C:\lab\tgclient\` (Console App, `tgclient.cpp` deleted, `tgclient.c` added). Files are added with **Add → Existing Item** (linked, not copied).
    - Outputs: `C:\lab\TgCounter\ARM64\Debug\TgCounter.sys/.pdb`, `C:\lab\tgclient\ARM64\Debug\tgclient.exe`. Optional `dumpbin /headers … | findstr /i "machine subsystem"` → `AA64 machine (ARM64)`, `Native`.
    - **Signing in PowerShell instead of certlm.msc:** `New-SelfSignedCertificate -Type CodeSigningCert -Subject "CN=TgTest" -CertStoreLocation Cert:\LocalMachine\My` → `Export-Certificate … C:\lab\TgTest.cer` → `Import-Certificate` into `LocalMachine\Root` + `LocalMachine\TrustedPublisher`. Then (Developer PowerShell, admin) `signtool sign /fd sha256 /sm /s My /n TgTest …TgCounter.sys` + `signtool verify /pa /v`. ⚠️ **VS re-signs every build with WDKTestCert**, so re-run signtool after each rebuild.
    - Load: `C:\drivers\`, `sc create TgCounter type= kernel start= demand binPath= C:\drivers\TgCounter.sys`, `sc start`. Expected DebugView: `TgCounter: loaded from \REGISTRY\MACHINE\SYSTEM\ControlSet001\Services\TgCounter`.
    - **Expected client output (computed from the header):** `IOCTL_TGCOUNTER_INCREMENT = 0x80002000`, `IOCTL_TGCOUNTER_GET = 0x80006004`, then `INCREMENT -> 1/2/3 (4 bytes returned)`; a second run gives 4/5/6.
    - Explore: regedit service key, `winobj` `\Device\TgCounter` + `\GLOBAL??\TgCounter`; predict the output after `sc stop` (expected: CreateFile error 2); cleanup `sc stop` + `sc delete` (DebugView `TgCounter: unloaded`); snapshot `tgcounter-works`.
    - Troubleshooting added: 577 (re-sign/re-copy), 1275 (arch/App Control → CodeIntegrity log), 1073 (service exists), client errors 2/5, Smart App Control blocking tgclient.exe.
    Progress reported in entry 39.
39. **~18:51: TgCounter driver BUILT** (Debug ARM64, toolset `WindowsKernelModeDriver10.0`, target platform **Desktop**). The first build failed on the **INF** → removed it from the project → success (4 s). The build log shows VS auto-signing (`Done Adding Additional Store`, `Successfully signed`, which is WDKTestCert) and `Inf2Cat/DrvCat skipped (no inf)`. Output: **`C:\lab\TgCounter\ARM64\Debug\TgCounter.sys`**.
    - `dumpbin /headers` (VS 2026 Developer PowerShell **v18.11.1**): **`AA64 machine (ARM64)`**, `10.00 subsystem version`, **`1 subsystem (Native)`** ✅
    - tgclient build: the user didn't report it separately (assumed built; confirm `C:\lab\tgclient\ARM64\Debug\tgclient.exe` exists).
40. **~19:05: certificate** (PowerShell 7.6.8, admin): `New-SelfSignedCertificate` CN=TgTest in `LocalMachine\My` ✅ → exported **`C:\lab\TgTest.cer`** (758 bytes) ✅ → imported to **`LocalMachine\Root`** ✅, **thumbprint `1A117A9DBB870ED38274D96324DBD4A19728E77E`**, EKU Code Signing → import to **`LocalMachine\TrustedPublisher` FAILED: `Access is denied. (0x80070005 (E_ACCESSDENIED))`**, even though the Root import (also admin-only) worked. Cause not confirmed. Workaround given: `certutil -addstore TrustedPublisher C:\lab\TgTest.cer` (admin). TrustedPublisher is **not required** for an `sc`-loaded legacy driver in test mode (it mainly affects PnP package installs), so don't let it block. Next: `signtool sign` from **Developer PowerShell run as admin** (the user's dev PS window started in `C:\Program Files\…`, so it was likely not elevated; signtool `/sm` needs admin for the machine key) → `signtool verify /pa /v` → 4.5 load.
41. **TrustedPublisher root cause found:** `certutil -addstore TrustedPublisher C:\lab\TgTest.cer` → `Cannot open existing Cert store. Use -f option to force Cert store creation.` / `0x80070002 ERROR_FILE_NOT_FOUND`. **The TrustedPublisher store doesn't exist yet on this fresh install**, and PowerShell's `Import-Certificate` misreported that as E_ACCESSDENIED. Fix: **`certutil -f -addstore TrustedPublisher C:\lab\TgTest.cer`** (result not yet reported; optional anyway).
42. **signtool `Missing filename`:** the user ran `signtool sign /fd sha256 /sm /s My /n TgTest` **without the .sys path** (the paste into the VM was cut off again, or only part of a wrapped line was copied). Now in **Developer PowerShell as admin** (prompt `C:\WINDOWS\system32`). Gave a shorter form: `cd C:\lab\TgCounter\ARM64\Debug` → `signtool sign /fd sha256 /sm /s My /n TgTest TgCounter.sys` → `signtool verify /pa /v TgCounter.sys`.
    - ⚠️ **Gotcha: in PowerShell, `sc` is an alias for `Set-Content`. Use `sc.exe create/start/stop/delete/query`.** (The 010 plan's `sc` commands assume cmd.exe.)
    - ⚠️ **Recurring: long pasted lines get truncated in the VM.** Prefer short commands (cd first) and check the echoed command.
43. **~19:20: TgCounter.sys signed with TgTest ✅** (this time the user ran the full command; they hadn't noticed the path was part of the same command). `signtool sign … C:\lab\TgCounter\ARM64\Debug\TgCounter.sys` → `Done Adding Additional Store` / `Successfully signed`. `signtool verify /pa /v` → file sha256 `5357B7A1077478E5532501C53BBD9635D3E6DACE989DA31D1CDD6D52232481CF`; chain **Issued to/by: TgTest**, expires **Mon Oct 25 19:14:00 2027**, SHA1 `1A117A9DBB870ED38274D96324DBD4A19728E77E` (= the thumbprint); "File is not timestamped" (fine); **Successfully verified, 0 warnings, 0 errors**. (The file hash changes on every rebuild and re-sign.) TrustedPublisher `certutil -f` result: not reported.
44. The user searched the Start menu for DebugView and found only web results. **winget's Sysinternals install is portable: command aliases only, no Start menu shortcuts.** Launch with `dbgview` from an admin shell (it inherits elevation). Don't download it separately. Next: `mkdir C:\drivers` → copy → `sc.exe create` → `sc.exe start` → DebugView `loaded from` → `tgclient.exe`.
45. **~19:27–19:31: 🎉 PHASE 4 CORE SUCCESS.** In the admin Developer PowerShell: `mkdir C:\drivers` (created 7:27 PM) → `copy …TgCounter.sys C:\drivers\` → `sc.exe create TgCounter type= kernel start= demand binPath= C:\drivers\TgCounter.sys` → **`[SC] CreateService SUCCESS`** → `sc.exe start TgCounter` → **`TYPE : 1 KERNEL_DRIVER`, `STATE : 4 RUNNING (STOPPABLE, NOT_PAUSABLE, IGNORES_SHUTDOWN)`**, exit codes 0, PID 0.
    - **DebugView:** line 1 `TgCounter: loaded from \REGISTRY\M…` (PID System) ✅. After that, periodic lines (~every 5 s) `[0004:xxxx]CcFlushCachePriv: PrePr…` from PID System = **Cache Manager (Cc) informational DbgPrints**, visible because Debug Print Filter `DEFAULT=0xF` lets all components' info messages through (interpretation, not verified). Harmless; filter with Edit → Filter/Highlight → Include `TgCounter`.
    - **`tgclient.exe`:** `IOCTL_TGCOUNTER_INCREMENT = 0x80002000`, `IOCTL_TGCOUNTER_GET = 0x80006004` (exactly as predicted in entry 38), `INCREMENT -> 1/2/3 (4 bytes returned)` ✅. **The TrustedPublisher import was NOT needed** (it wasn't confirmed done, and the driver loaded anyway).
    - Remaining Phase 4 steps given: run again (expect 4/5/6), regedit service key (Type=1, Start=3, ImagePath), WinObj `\Device\TgCounter` + `\GLOBAL??\TgCounter`, predict-then-check after `sc.exe stop` (expected: CreateFile error 2 and `TgCounter: unloaded`; the WinObj entries disappear), **recommend keeping the service registered (no `sc.exe delete`)** for Phase 5 (it's demand-start, so it won't load at boot), shut down → snapshot `tgcounter-works`. **Next: Phase 5** (local kernel debugging, crash IOCTL + dump analysis, live dump, Verifier, WPR).
46. **~19:35–19:40: the user shut down the VM and took snapshot 4 `tgcounter-works`.** Verified in the `.vmsd`: `numSnapshots = 4`, current = 4. VM bundle **72 GB** (was 63 GB). The wrap-up results (2nd run, WinObj, stop prediction, whether the service was deleted) weren't reported.
47. **The user asked for a showcase document.** Wrote **`012-demo_runbook.md`**: a pitch plus a request-flow diagram; Part A prep (T7, Memory Pressure, optional snapshot restore, ⌘⇧5 recording, admin Developer PowerShell + `dbgview`, `sc.exe query` reset handling STOPPED/RUNNING/1060); Part B 7 acts (platform `winver` + `bcdedit`; artifact `dumpbin` + `signtool verify`; "before" client error 2; `sc.exe create/start` + DebugView loaded; client 1-2-3 then 4-5-6; WinObj + stop + error 2 again; optional live edit → build → re-sign → copy → start); Part C reset; Part D troubleshooting (1056, 1073, 577, 1275, file-in-use, error 5, `sc` vs `sc.exe`, …); Part E command cheat sheet; likely audience questions.


### Session 4 (2026-10-30)

48. **The user reported Phase 4 success** ("VM successfully loaded… kernel driver working… saw it going from user space to the kernel driver") and asked for a guide for the next section, like 010. Claude read this handoff in full, plus 012.
49. **Wrote `013-phase5_guide_inspect_crash_analyze.md`**, tailored to this setup (Fusion, VS 2026, ARM64, 4 GB, `sc.exe`, re-sign after build, short commands): 5.0 code via the shared folder + rebuild loop + snapshot `phase5-code-loaded`; 5.1 local KD (`bcdedit /dbgsettings local`, `/debug on`; `!drvobj`, `!devobj`, **`dt TgCounter!_TG_EXTENSION` to read the counter**, `!pool` on the paged allocation, `!object`, ARM64 `u`, `!devnode`/`!devstack`; then `/debug off` before the crash labs); 5.2 live dump (0x161); 5.3 crash IOCTL → predicted 0xD1 (P1 0, P2 2) + an analysis table; 5.4 the paged-pool-under-spin-lock bug: no crash without Verifier, crash with `verifier /standard /driver TgCounter.sys`, proven with `!pte`; 5.5 WPR/WPA. Snapshots: `phase5-code-loaded`, `before-crash-labs`, `phase5-done`.
50. **Phase 5 code written to the repo** at `lectures/windows_internals/code/tgcounter_phase5/` (`tgcounter.c` 137 lines, `tgcounter_ioctl.h` 27, `tgclient.c` 55). New IOCTLs: CRASH fn 0x8FF = `0x800023FC`; PAGED_AT_DISPATCH fn 0x8FE = `0x800023F8`. The load message now says `(phase 5 build)`. Verified on Linux: the driver compiles (MinGW DDK + an `ExAllocatePool2` prototype shim), the client compiles and runs under Wine (error 2 in all modes). The check caught a `send` vs Winsock name clash (renamed `SendIoctl`). `nm` showed `KeRaiseIrql` is inlined (no import) while `KeAcquireSpinLock` imports `KeAcquireSpinLockRaiseToDpc`, which is why bug #2 uses a spin lock (Verifier can intercept it).
51. **Open:** set up the Fusion shared folder (§5.0 A2), still pending since entry 35. Unverified: local KD on ARM64 in Fusion (fallback: live dump), and which stop code Verifier gives for bug #2 (0xD1 vs 0xC4).

---

## Remaining steps (in order)

### Phase 2 go/no-go ✅ PASSED (Session 2)
- [x] Admin Command Prompt → `bcdedit /set testsigning on`
- [x] Restart → the **"Test Mode"** watermark appears at the bottom right

### Finish Phase 1
- [x] Create the local user, security questions, privacy screens (done; the login works).
- [x] **Install VMware Tools** (done in Session 2; a website loads): Fusion → Virtual Machine → **Install VMware Tools** → File Explorer → DVD drive → run `setup` → reboot.
  - If that menu item is greyed out or nothing mounts, Fusion may need the ISO disconnected first (Virtual Machine → CD/DVD → Disconnect), then try again.
- [x] Check the network: open Edge, load a page.
- [x] **Windows Update** until up to date (done in Session 2). Afterward, check the **Test Mode watermark is still there** (an update shouldn't turn off test signing, but check before taking the snapshot).
- [x] `msinfo32` → **Secure Boot State: Off** (confirmed in Session 2).
- [ ] Optional: disconnect the ISO from the VM (CD/DVD settings), so "Press any key to boot from CD" stops appearing. **If that prompt appears, don't press a key**; let it time out and boot from the disk.
- [x] Shut down Windows → Fusion → **Virtual Machine → Snapshots → Take Snapshot** (done 17:56; rename "Snapshot" → `clean-windows-testmode`).

### Then the rest of Phase 2 onward (see 010)
- [ ] Debug Print Filter registry key, kernel memory dump, `winget install Microsoft.WinDbg` and `Microsoft.Sysinternals` → snapshot `driver-lab-ready`.
- [ ] Phase 3: VS 2022 Community + ARM64 Spectre libs + SDK 26100+ + WDK. Expect Visual Studio to be **slow with 4 GB**; close Mac apps while building.

---

## Gotchas learned (keep in mind)

- **"Press any key to boot from CD"** lasts only about 3 seconds. If Windows Setup needs to run again, use **Power On to Firmware** (hold Option in the Virtual Machine menu) instead of trying to catch the prompt.
- **Keyboard not working in the VM** → check that macOS Accessibility permission for Fusion is on, and restart Fusion after changing it.
- **Mac function keys:** Shift+F10 may need **Fn**+Shift+F10.
- **Never unplug or eject the T7** while the VM is running or suspended. Shut Windows down first. Plug the T7 directly into the Mac, not through a hub.
- Optional hygiene: exclude the VM folder from **Spotlight** (System Settings → Spotlight → Search Privacy) and from **Time Machine**.
- **ISO build 26300** looks like a Windows Insider build. It installed fine. Insider builds can expire; if Windows starts warning about expiry, reinstall from the regular release ISO (Microsoft's Windows 11 Arm64 ISO page). The SHA-256 hash hasn't been checked against Microsoft's published value.
- Claude can diagnose VM problems by reading `vmware.log` in the VM bundle (look for `Guest:` lines and `SecureBootMode`).
- **Low guest memory:** only about 1.6 GB is free at idle out of 4 GB. Before Phase 3 (Visual Studio), close Mac apps. If Visual Studio is unbearable, try 5 GB (5120 MB) in Fusion → Processors & Memory, with the VM shut down. Don't go above 5 GB on an 8 GB Mac.
- **BitLocker / device encryption:** Windows 11 may encrypt C: automatically once a TPM is present. If it does, save the **BitLocker recovery key** (Settings → Privacy & security → Device encryption, or `manage-bde -protectors -get C:` as admin) before changing boot settings or Secure Boot, or Windows may ask for it at boot.
- **App Control "Enforced" / Smart App Control:** if a driver or an unsigned test app is blocked, see the msinfo32 note above (CodeIntegrity log, Smart App Control).

## How to keep this file current

The user wants this handoff **updated as we go**, each session, with more context. At the end of each step or session, Claude should: update "Last updated", the status board, the TL;DR, and the session log (add a new "Session N" subsection), tick checkboxes, and record new facts (screenshots, error messages, settings) with dates. Don't rewrite history; add to it.
