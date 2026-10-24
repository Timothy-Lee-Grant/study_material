2026_10_24_02_00-(Session-Handoff)

# 011 — Session Handoff: Windows Driver Lab Setup (Session 1)

> **For:** Timothy, and Claude at the start of the next session
> **Session:** 2026-10-23 evening → 2026-10-24 ~02:00
> **Plan this follows:** [`010-lab_setup_work_plan.md`](010-lab_setup_work_plan.md). Its Phases 0–6 still apply, with the changes listed under "Decisions" below.
> **Where we stopped:** Phase 1, Windows first-run setup, at the **"Create a user for this PC"** (local account) screen.

---

## TL;DR for next session

1. Finish Windows first-run setup (local account, security questions, privacy screens), unless it's already done.
2. Install **VMware Tools** (Fusion menu: Virtual Machine → Install VMware Tools → run `setup` on the DVD drive → reboot). This provides the network driver; the VM has **no network** until then.
3. Windows Update → check `msinfo32` shows Secure Boot **Off** → shut down → snapshot `clean-windows`.
4. Phase 2 go/no-go: `bcdedit /set testsigning on` → reboot → "Test Mode" watermark.

---

## Decisions made this session (these override the 010 plan)

| Topic | 010 plan said | Decided |
|---|---|---|
| Hypervisor | Parallels trial first | **VMware Fusion** (free for personal use). Goal: **everything free** |
| VM memory | 8 GB | **4 GB** (the Mac has only 8 GB; 4 GB stays free for macOS) |
| VM location | "larger SSD" | **T7 external SSD** |
| Windows edition | Pro | **Windows 11 Pro, no product key** (unactivated: watermark plus locked personalization, acceptable) |
| Account | Local if offered | **Local account** created with the `start ms-cxh:localonly` bypass |
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

## Where everything is

```
/Volumes/T7/windows_experiment/
├── 010-lab_setup_work_plan.md                       ← master plan (phases 0–6)
├── 011-session_handoff.md                           ← this file
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
- ⚠️ **Open issue:** the user said the password is 8 characters, but the screenshot showed **9 dots** in both password fields. They were told to retype both fields before clicking Next. **Not confirmed that they did.** If login fails tomorrow, this is why (likely a doubled key or a stray space). Recovery: the security questions on the login screen.
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

---

## Remaining steps (in order)

### Finish Phase 1
- [ ] Create the local user (check the 8-vs-9 character password), answer the 3 security questions (write the answers down), turn off all privacy options.
- [ ] **Install VMware Tools:** Fusion → Virtual Machine → **Install VMware Tools** → File Explorer → DVD drive → run `setup` → reboot.
  - If that menu item is greyed out or nothing mounts, Fusion may need the ISO disconnected first (Virtual Machine → CD/DVD → Disconnect), then try again.
- [ ] Check the network: open Edge, load a page.
- [ ] **Windows Update** until up to date (several reboots).
- [ ] `msinfo32` → **Secure Boot State: Off**.
- [ ] Optional: disconnect the ISO from the VM (CD/DVD settings), so "Press any key to boot from CD" stops appearing. **If that prompt appears, don't press a key**; let it time out and boot from the disk.
- [ ] Shut down Windows → Fusion → **Virtual Machine → Snapshots → Take Snapshot** → `clean-windows`.

### Then Phase 2 onward (see 010)
- [ ] **Go/no-go:** admin Command Prompt → `bcdedit /set testsigning on` → reboot → "Test Mode" watermark. If you get "protected by Secure Boot policy", Secure Boot isn't actually off.
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
