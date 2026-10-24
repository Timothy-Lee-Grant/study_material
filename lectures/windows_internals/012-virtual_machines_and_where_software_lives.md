2026_10_24_14_00-(Virtual-Machines-And-Where-Software-Lives)

# Lecture 012 — Virtual Machines and Where Software Lives: What You Actually Did Last Night

> **For:** Timothy · **Date:** 2026-10-24
> **Prerequisites:** 008 §(virtual → physical mapping, page faults) helps a lot for Part B. 006 (PnP, hardware IDs, INFs) explains one specific mystery from last night (§B6). 010 and 011 are the plan and handoff this lecture explains.
> **Why this lecture:** while setting up the lab, you realized you couldn't say *where* the things you downloaded actually are, what "installing" did, how an app "on the SSD" can also be "in RAM", how this relates to `apt`, and how a VM works at all ("an application interacting with my hardware… a complete world I don't understand"). Every example below comes from **your own machine**. I read the files on your Mac and the T7 on 2026-10-24 to build it.

---

## Core ideas (the answer key)

1. **A program has two homes.** The *file* lives on a disk (permanent storage). When it runs, the kernel *maps* that file into memory and loads the pieces it needs into RAM. "On the SSD" and "in RAM" are both true, at different times and for different copies.
2. **Download, install and data are three different locations.** Downloading copies bytes from the network into a file wherever the browser is told to save. Installing puts files where the OS and other programs will look for them. A program's data (like your VM) can live somewhere else again.
3. **A file can pretend to be a disk.** A `.dmg`, an `.iso` and a `.vmdk` are all *disk images*: ordinary files that contain a whole filesystem or disk. "Opening" one means mounting it (macOS) or attaching it to a VM.
4. **Installing Fusion was a copy.** Double-clicking the `.dmg` mounted it as a disk. The installer copied `VMware Fusion.app` (a folder) to `/Applications` on your **internal** drive. Only the installer image, the ISO and the VM live on the T7.
5. **A package manager (`apt`, Homebrew, `winget`) is an installer plus a database plus a catalog.** It downloads from trusted repositories, resolves dependencies, puts files in fixed places and remembers what it put where. macOS has no built-in one, which is why installation there feels ad hoc.
6. **A VM is an ordinary process on the host** (`vmware-vmx`) that uses the CPU's virtualization hardware, through the macOS kernel's hypervisor, to make a whole fake computer: CPUs, RAM, firmware, disk, network card, TPM.
7. **The guest's instructions run directly on the M2's cores.** That only works because Windows for Arm and the M2 speak the same instruction set. The hypervisor only steps in when the guest does something it isn't allowed to do directly (a "VM exit").
8. **Guest memory is translated twice.** Windows' page tables map guest-virtual → guest-physical. The hypervisor's stage-2 tables map guest-physical → real physical. Guest "RAM" is just memory owned by the `vmware-vmx` process, which macOS can even swap to your internal SSD.
9. **Virtual devices are software pretending to be hardware registers.** When Windows' NVMe driver writes to its "controller", the access traps, and `vmware-vmx` turns it into a read or write on the `.vmdk` files on the T7.
10. **Paravirtual devices need guest drivers.** VMXNET3 is a device that exists only in VMs, so Windows had no driver for it. That's why the VM had **no network** until VMware Tools: the same PnP "no matching INF" story as lecture 006.
11. **Firmware, Secure Boot and the TPM are virtual too.** The UEFI settings live in the `.nvram` file. The TPM is a program (`tpm2emu`) whose state is encrypted, which is why the VM has a password.

---

## Table of Contents

- §0 Direct answers to your questions
- **Part A — Where software lives**
  - §A1 The map: storage, memory, and the three locations
  - §A2 "It lives on the SSD but runs in RAM": both are true
  - §A3 What downloading actually is
  - §A4 Disk images: a file that pretends to be a disk
  - §A5 What the Fusion installer actually did (forensics on your Mac)
  - §A6 Package managers: `apt`/`dpkg`, Homebrew, `.pkg`, `winget`
  - §A7 Who decides where things go, and why
- **Part B — How a virtual machine works**
  - §B1 The layer stack on your Mac right now
  - §B2 Why Arm Windows: running guest code directly
  - §B3 The run loop: VM entries and VM exits
  - §B4 Memory: two translations
  - §B5 Storage: your 120 GB disk that takes 14 GB
  - §B6 Devices: emulated vs paravirtual (the missing network, explained)
  - §B7 Firmware, Secure Boot, TPM, and the encryption password
  - §B8 Networking: NAT
  - §B9 Snapshots, suspend and shutdown
  - §B10 What VMs can't do here (nested virtualization, live debugging)
  - §B11 Two full traces: "Power On" and "one disk write"
- Misconceptions
- Interview relevance
- Self-check questions
- Sources

---

## 0. Direct answers

1. **"I'm running an application that lives on the SSD, but applications run in RAM."** Both. The `.app` *file* sits on your internal SSD at `/Applications/VMware Fusion.app`. When you launch it, macOS creates a process and maps the program file into that process's address space. Pages are copied into RAM **as they're touched** (demand paging, lecture 008). The file stays on disk the whole time. RAM holds a working copy. (§A2)
2. **"What did I download, and where is it?"** Three things, all now on the T7: the Windows ISO (8.5 GB), the Fusion installer `.dmg` (~500 MB), and, created by Fusion rather than downloaded, the VM folder (14 GB so far). **Fusion itself is not on the T7.** It's on the internal drive (937 MB). (§A5)
3. **"Don't you not get to choose where things download or install?"** You choose the download location (it's just a browser setting, and Chrome saved these where you told it). Installation locations are chosen by convention or by the installer, because other software has to be able to *find* the result. Data locations (like the VM) are usually yours to choose. (§A3, §A7)
4. **"It was a dpkg thing."** It was a **`.dmg`** (Apple *disk image*), not `dpkg` (Debian's *package* tool). The names are close, but they're different ideas: a dmg is a file containing a disk; a `.deb` handled by `dpkg` is an archive plus install instructions. (§A4, §A6)
5. **"Did double-clicking install it to the external drive?"** No. Double-clicking *mounted* the image (it appeared as a disk named "VMware Fusion" and **is still mounted** right now). The installer then copied the app to `/Applications` on the internal drive. (§A5)
6. **"What does an installer do?"** Copies files to known places, and sometimes registers things with the OS (services, drivers, file associations, permissions, uninstall records). Fusion's was nearly a pure copy: no `.pkg` receipt, no kernel extension. (§A5)
7. **"How does a VM interact with my hardware?"** Mostly it *doesn't*, directly. The M2 has hardware built for virtualization. The macOS kernel owns that hardware and offers it to apps through Apple's **Hypervisor framework**. `vmware-vmx` is a normal app that asks the kernel "run this guest code on a CPU core until it does something I need to handle." Real devices (disk, network, keyboard) are reached through ordinary macOS files and APIs, just like any other app. (Part B)

---

# Part A — Where software lives

## §A1 The map 🟢 OWN IT

Two kinds of storage, with opposite properties:

| | **Disk** (SSD, T7) | **RAM** (memory) |
|---|---|---|
| Survives power off | Yes | No |
| Size on your Mac | 228 GB internal + 932 GB T7 | 8 GB |
| Speed | Slower (microseconds) | Fast (nanoseconds) |
| What the CPU can execute from | Nothing directly | Only this |
| Organized as | Files in a filesystem | Pages in address spaces (008) |

Everything in Part A comes back to one question: **which copy, in which of these, are we talking about?**

And three *locations* you kept merging into one:

| Location | What it is | Who chooses | Yours, right now |
|---|---|---|---|
| **Download location** | Where the browser writes the bytes it receives | You (browser setting, or per download) | `/Volumes/T7/windows_experiment/` |
| **Install location** | Where the program's files go so the OS can find and run them | Convention / the installer | `/Applications/VMware Fusion.app` (internal) |
| **Data location** | Files the program creates and uses | Usually you | The `.vmwarevm` folder on the T7 |

## §A2 "It lives on the SSD but runs in RAM" 🟢 OWN IT

> **Predict first (from 008):** when a process touches a page of its program that isn't in RAM yet, what happens? Answer at the end of this section.

Here's the numbered sequence when you double-click Fusion:

1. Finder asks macOS to launch `/Applications/VMware Fusion.app`. An `.app` is a **folder** (a "bundle"); the real executable is inside, under `Contents/MacOS/`.
2. The kernel creates a **process**: a new, empty virtual address space plus a thread (008).
3. The kernel **maps** the executable file into that address space. Mapping means: "these virtual addresses correspond to these parts of this file." Nothing has been copied into RAM yet.
4. The thread starts executing. The first instruction's page isn't in RAM, so it triggers a **page fault**.
5. The kernel reads that page from the SSD into a free RAM page, updates the page table, and resumes the thread.
6. Repeat for every page that's actually used. Pages never touched are never loaded.
7. If RAM gets tight, the kernel can **drop** clean program pages (it can reload them from the file anytime) or **write dirty data pages to swap** (a file on disk) to free RAM.

So the file on the SSD is the **source**; RAM holds a **cache of the parts in use**. That's why you can't delete or eject a disk that a running program's file is on: the kernel may need to read more pages from it at any moment.

**Your Mac is doing step 7 right now.** On 2026-10-24 I ran `sysctl vm.swapusage` and got:

```
vm.swapusage: total = 4096.00M  used = 2857.12M  free = 1238.88M  (encrypted)
```

and the swap files are here, on the **internal** SSD:

```
/System/Volumes/VM/swapfile0   1 GB
/System/Volumes/VM/swapfile1   1 GB
...
```

With 8 GB of RAM, macOS has pushed about 2.8 GB of memory out to the internal disk. Keep this in mind for §B4: when the VM runs, its 4 GB of "RAM" competes for the same 8 GB, and some of it can end up in these swap files too. That's one reason the VM will feel slow, and one reason internal free space still matters even though the VM lives on the T7.

*(Predict answer: the CPU raises a page fault; the kernel finds the page's backing file and offset, reads it into RAM, fixes the page table entry, and re-runs the instruction.)*

## §A3 What downloading actually is 🟢 OWN IT

A download is just: **open a network connection, receive bytes, write them into a new file.** The browser decides the file's path, using the default folder (`~/Downloads`) unless you've told it otherwise. There's nothing special about the result: it's a file like any other, and you can move it.

macOS adds one thing. The browser tags every downloaded file with **extended attributes** (metadata stored next to the file). On your Fusion `.dmg`:

```
$ xattr VMware-Fusion-26H1u1-25689522_universal.dmg
com.apple.metadata:kMDItemWhereFroms     ← the URL it came from (Broadcom's site)
com.apple.quarantine                     ← 0081;…;Chrome;…  "downloaded by Chrome"
```

The **quarantine** flag is what makes macOS run **Gatekeeper** checks the first time you open the thing: "is this code signed by an identified developer, notarized by Apple, and not tampered with?" That's the "are you sure you want to open this?" dialog. The ISO has the same Chrome quarantine tag.

**The bytes on disk, by type** (`file` command):

```
Windows11_Client_arm64_en-us_26300_9457.iso: ISO 9660 CD-ROM filesystem data 'CCCOMA_A64FRE_EN-US_DV9' (bootable)
vmware-vmx: Mach-O universal binary with 2 architectures: [x86_64] [arm64]
```

That second line is why the installer filename says `_universal`: one file containing **both** an Intel and an Arm version of each program. macOS picks the `arm64` half on your M2.

## §A4 Disk images: a file that pretends to be a disk 🟢 OWN IT

This one idea explains three of last night's files.

A **disk** is, to the operating system, just a long array of fixed-size blocks (usually 512 bytes or 4 KB): "give me block 1,048,576." A **filesystem** (APFS, HFS+, NTFS, ISO 9660) is a data structure laid out on those blocks that turns them into folders and files.

A **disk image** is a file whose contents are exactly those blocks. Software can then present the file *as if* it were a disk:

| File | Format | Who presents it as a disk | To whom |
|---|---|---|---|
| `VMware-Fusion-…dmg` | Apple Disk Image (contains HFS+/APFS) | macOS (`hdiutil`, on double-click) | macOS itself → appears in `/Volumes` |
| `Windows11_…iso` | ISO 9660 / UDF (a DVD's layout) | `vmware-vmx` | The Windows VM → appears as a DVD drive |
| `Virtual Disk.vmdk` | VMware virtual disk | `vmware-vmx` | The Windows VM → appears as an NVMe SSD |

You can see the first one still on your Mac (`df -h`, 2026-10-24):

```
/dev/disk4s1     932Gi    37Gi   895Gi     4%   /Volumes/T7               ← a real disk
/dev/disk5s1     1.0Gi   950Mi    80Mi    93%   /Volumes/VMware Fusion    ← a FILE, acting as a disk
```

macOS gave the `.dmg` a device name (`disk5`), exactly as if you'd plugged in a second USB drive. That's what **mounting** means: attaching a filesystem to a folder path so its files become reachable. You can eject it (Finder sidebar ⏏); nothing needs it anymore.

**Why ship software as a disk image?** One download carries a whole folder tree (the `.app` bundle is a folder with thousands of files), a background picture, and a signature, and it can be verified as a unit.

## §A5 What the Fusion installer actually did: forensics on your Mac 🟢 OWN IT

Let's reconstruct last night from the evidence, step by step.

1. **Chrome downloaded** `VMware-Fusion-26H1u1-25689522_universal.dmg` into `/Volumes/T7/windows_experiment/applications/` (quarantine tag: Chrome).
2. **You double-clicked it.** macOS checked its signature and *mounted* it at `/Volumes/VMware Fusion`. Inside: a background image, a volume icon, and `VMware Fusion.app`.
3. **You opened the app on that image** (VMware's image says "double-click to install"). It **copied itself** to `/Applications/VMware Fusion.app` and asked for your password, because `/Applications` is a system-wide folder.
4. **Evidence it was a plain copy:**
   - `/Applications/VMware Fusion.app` exists: **937 MB** on the internal drive.
   - `pkgutil --pkgs | grep -i vmware` prints **nothing**: no macOS Installer package was run, so there's no install receipt.
   - No VMware entry in `/Library/Extensions` (no kernel extension; see §B1 for why it doesn't need one).
5. **First launch** created per-user settings: `~/Library/Preferences/com.vmware.fusion.plist` and `~/Library/Application Support/VMware Fusion/`. That's the third location type (data), chosen by macOS convention.
6. **You granted Accessibility permission** (System Settings). That's a record in a macOS privacy database, not a file next to the app, and it's what let your keystrokes reach the VM.
7. **The New VM wizard created** `Windows 11 64-bit Arm.vmwarevm/` in the folder it was pointing at, which happened to be `applications/` on the T7 (011 noted this).

So, the full inventory:

```
INTERNAL SSD (228 GB, ~33 GB free)
  /Applications/VMware Fusion.app/            ← the program (937 MB)   [install location]
  ~/Library/Preferences/com.vmware.fusion.plist
  ~/Library/Application Support/VMware Fusion/   ← Fusion's own settings [data]
  /System/Volumes/VM/swapfile*                ← macOS swap (can hold VM memory!)

T7 (932 GB, HFS+)
  /Volumes/T7/windows_experiment/
    Windows11_Client_arm64_…iso      8.5 GB   ← downloaded; the "DVD" Windows was installed from
    applications/
      VMware-Fusion-…dmg             0.5 GB   ← downloaded installer; safe to delete now
      Windows 11 64-bit Arm.vmwarevm/  14 GB  ← the VM itself (Part B)    [data location]
```

**What an installer *can* do**, in general, from least to most invasive:

| Action | Example | Fusion? |
|---|---|---|
| Copy files to a standard place | `.app` → `/Applications` | ✅ |
| Create per-user settings | `~/Library/Preferences/…` | ✅ (on first run) |
| Register a background service (launchd daemon) | `/Library/LaunchDaemons/*.plist` | Not found |
| Install a kernel or system extension | `/Library/Extensions/*.kext` | ❌ (not needed) |
| Ask for privacy permissions | Accessibility, Input Monitoring | ✅ (you did this by hand) |
| Record what it did, for uninstall | `pkgutil` receipt | ❌ (it's drag-to-trash uninstall) |

On Windows, the same table holds with different names: `C:\Program Files\`, the registry, services (`sc create` in 010 Phase 4 is exactly "register a service"), drivers, and an uninstall entry under *Apps & features*.

## §A6 Package managers: `apt`/`dpkg`, Homebrew, `.pkg`, `winget` 🟢 OWN IT

On Linux you typed `sudo apt install foo` and never thought about any of this. Here's what `apt` was doing for you, as a numbered list:

1. **Catalog:** look up `foo` in a local index of **repositories** (trusted servers listed in `/etc/apt/sources.list*`), refreshed by `apt update`.
2. **Dependencies:** work out every other package `foo` needs, recursively, and which versions are compatible.
3. **Download + verify:** fetch the `.deb` files and check their cryptographic signatures against the repository's keys.
4. **Unpack + place:** hand each `.deb` to **`dpkg`**, the lower-level tool, which extracts files into **fixed** places (`/usr/bin`, `/usr/lib`, `/etc`) and runs the package's install scripts.
5. **Remember:** record every file it installed in `dpkg`'s database (`/var/lib/dpkg/`), so it can upgrade or remove them cleanly later.

So `apt` = **catalog + dependency solver + downloader + installer + database**. `dpkg` = just the installer + database half.

**The other worlds:**

| | Linux (Debian/Ubuntu) | macOS | Windows |
|---|---|---|---|
| Built-in package manager | `apt` (+ `dpkg`) | **None** for general software (the App Store is the closest) | **`winget`** (010 Phase 2 uses it) |
| Package file | `.deb` | `.pkg` (Installer.app, leaves a receipt) or `.dmg` (just a disk image) | `.msi`, `.msix`, or a `setup.exe` |
| Third-party package manager | — | **Homebrew** (`brew`) | Chocolatey, Scoop |
| Where things go | `/usr/...` | `/Applications`; Homebrew: `/opt/homebrew` | `C:\Program Files\` |
| "What's installed?" | `dpkg -l` | `pkgutil --pkgs` (only `.pkg`s!) / `brew list` | `winget list` |

**You already have the macOS version of `apt`.** Homebrew is installed at `/opt/homebrew` on your Mac, and it holds your AVR and Arm GCC toolchains, `gdb`, `ffmpeg` and more. Its design is a clean picture of every package manager:

```
/opt/homebrew/Cellar/p7zip/17.06/bin/7z      ← the real files, one folder per package+version
/opt/homebrew/bin/7z -> ../Cellar/p7zip/17.06/bin/7z    ← a symlink in ONE folder that's on your PATH
```

Your shell finds `7z` because `/opt/homebrew/bin` is in your `PATH`. Upgrading means installing a new version folder and re-pointing the symlink. Uninstalling means deleting the folder and the link. The fixed place is what makes the bookkeeping possible.

**Why wasn't Fusion installed with a package manager?** It could be (Homebrew has "casks" for GUI apps, and `brew install --cask vmware-fusion` existed for older versions), but Broadcom now requires a login to download it, so you went to the portal by hand. Inside Windows you'll go back to the package-manager world: `winget install Microsoft.WinDbg`.

## §A7 Who decides where things go, and why 🔵 CONTRACT

Your instinct ("you don't really choose where things get installed") is *right for package managers and wrong for downloads.* The rule underneath:

> **A location is fixed when other software has to find the thing without being told. It's flexible when a human or a config file tells software where to look.**

| Thing | Who must find it | Fixed? |
|---|---|---|
| `/usr/bin/gcc`, `/opt/homebrew/bin/7z` | Your shell, via `PATH` | Fixed (by the package manager) |
| A shared library | The dynamic linker, via search paths | Fixed |
| `C:\Windows\System32\drivers\*.sys` | The Windows service manager, via the registry (009 §3) | Path is recorded in the registry. 010 deliberately uses `C:\drivers\` via `binPath=`, which shows the registry is the real authority |
| `/Applications/*.app` | Finder, Launchpad, Spotlight | Convention: macOS apps work from *anywhere*, but `/Applications` is where people and updaters expect them |
| A downloaded `.iso` | Only you (and you'll tell Fusion) | Totally flexible |
| The `.vmwarevm` folder | Fusion's library list (it remembers the path) | Flexible: that's why moving it triggers "I Moved It / I Copied It" (011) |

Notice the `.vmx` file stores the ISO's absolute path:

```
sata0:1.fileName = "/Volumes/T7/windows_experiment/Windows11_Client_arm64_en-us_26300_9457.iso"
```

That's the "config tells software where to look" case. Move the ISO and the VM's DVD drive will come up empty (harmless now that Windows is installed).

---

# Part B — How a virtual machine works

> **The one-sentence version:** a VM is a process that asks the kernel to run another operating system's code directly on real CPU cores, with that code fenced into memory the process owns, and that pretends to be every piece of hardware the guest tries to talk to.

## §B1 The layer stack on your Mac right now 🟢 OWN IT

Lecture standards say: draw the layers and put responsibility on them. Here's who does what while the VM runs.

```
┌────────────────────────────── GUEST (inside the VM) ─────────────────────────────┐
│  Windows apps (Edge, tgclient.exe)                     Arm EL0 (user mode)        │
│  Windows kernel + drivers (ntoskrnl, stornvme, …)      Arm EL1 (kernel mode)      │
│     ↑ believes it owns a real Arm PC: 4 CPUs, 4 GB RAM, NVMe SSD, VMXNET3, TPM    │
└───────────────────────────────────────────────────────────────────────────────────┘
          VM exit ↓   ↑ VM entry        (the hardware switches worlds)
┌────────────────────────────── HOST (macOS) ──────────────────────────────────────┐
│  vmware-vmx process (one per running VM)               EL0, an ordinary app       │
│    • one thread per vCPU, each looping "run guest → handle exit"                  │
│    • virtual devices: NVMe, SATA DVD, VMXNET3, USB, display, vTPM, UEFI firmware  │
│    • guest RAM = 4 GB of its own memory                                           │
│  Apple frameworks it links:  Hypervisor.framework   vmnet.framework               │
│  XNU (macOS kernel) — includes the hypervisor          EL2 (most privileged)      │
│    • programs the virtualization hardware, owns stage-2 page tables               │
│    • schedules vCPU threads like any other threads                                │
│    • file system (HFS+ on T7), USB stack, network stack                           │
└───────────────────────────────────────────────────────────────────────────────────┘
┌────────────────────────────── HARDWARE ──────────────────────────────────────────┐
│  Apple M2: 8 Arm cores with virtualization extensions (EL2, stage-2 translation)  │
│  8 GB RAM · internal SSD · T7 over USB · Wi-Fi                                    │
└───────────────────────────────────────────────────────────────────────────────────┘
```

**Arm exception levels** (the Arm version of the privilege idea from 005's privilege-vs-IRQL table): EL0 = user apps, EL1 = an OS kernel, EL2 = a **hypervisor**, the level that can run whole OS kernels underneath it. On Apple silicon, the macOS kernel itself runs at EL2 so it can host VMs. ⚫ (How Apple arranges that internally is a rabbit hole you can skip.)

**Evidence from your machine** that this is the real structure:

- `otool -L vmware-vmx` shows it links `/System/Library/Frameworks/Hypervisor.framework` and `vmnet.framework`. It uses Apple's API; it doesn't talk to the CPU's virtualization hardware itself.
- Its code signature carries the entitlement `com.apple.security.hypervisor`. Apple requires that entitlement for any process that wants to create VMs.
- No VMware kernel extension is installed (§A5). On older Intel Macs, VMware shipped its own kernel extensions. Now the kernel provides the hypervisor, so VMware doesn't need one.
- `vmware.log` line: `Monitor Mode: ULM`. My reading: "user-level monitor", i.e. VMware's virtual machine monitor runs in user space on top of the OS's hypervisor API rather than in its own kernel driver. (I couldn't find VMware documentation spelling out that log string, so treat the expansion as likely, not verified.)

**Type 1 vs type 2 hypervisors** 🔵 (interview vocabulary): a *type 1* (bare-metal) hypervisor runs directly on the hardware, with every OS as a guest (Hyper-V, ESXi, Xen). A *type 2* (hosted) hypervisor runs as part of a normal OS (Fusion, Parallels, VirtualBox). Your setup is type 2; the `.vmx` even says `virtualHW.productCompatibility = "hosted"`. The line blurs in practice: when Hyper-V is enabled on Windows, the hypervisor loads first and Windows itself becomes a privileged guest (the "root partition").

## §B2 Why Arm Windows: running guest code directly 🟢 OWN IT

> **Predict first:** why couldn't you just use the normal (x64) Windows ISO?

There are two ways to run a guest's code:

| | **Virtualization** (what you have) | **Emulation** |
|---|---|---|
| How | The real CPU executes the guest's instructions itself | A program reads each guest instruction and performs its effect in software (or translates blocks to host instructions) |
| Requirement | Guest and host use the **same instruction set** | None: any CPU can emulate any other |
| Speed | Near native | Typically several times slower for a whole OS |
| Example | Arm Windows on an Arm M2 | x64 Windows on an M2 via QEMU's TCG |

Your M2 decodes Arm64 instructions. An x64 kernel's bytes are meaningless to it. So the only fast option is a guest built for Arm64: **Windows 11 for Arm**. That's the whole reason 010 sent you to the Arm64 ISO, and why you'll build **ARM64** drivers.

**Then how does Windows on Arm run x64 apps?** Inside the guest, at a different layer: Windows has its own emulator, **Prism** (Windows 11 24H2+), which translates x86/x64 *user-mode* app code to Arm64 as it runs. There's no emulation for kernel code: **drivers must be native ARM64**. That's why `sc start` returns error 1275 if you build x64 (010's troubleshooting table).

```
          your M2 executes ↓ natively
Windows ARM64 kernel + ARM64 drivers         ← must be ARM64, no exceptions
Windows ARM64 apps                           ← native
x64 apps → Prism translates → ARM64 code     ← emulated, user mode only
```

## §B3 The run loop: VM entries and VM exits 🟢 OWN IT

This is the heart of it. Each of your 4 vCPUs is **a thread inside `vmware-vmx`**. Each thread runs a loop like this (shape of Apple's Hypervisor API, simplified):

```c
hv_vcpu_create(&vcpu, &exit_info, NULL);       // create a virtual CPU for this thread
set guest registers (PC = firmware entry point, …);

for (;;) {
    hv_vcpu_run(vcpu);       // ① kernel switches this core into the guest; guest code runs
                             //    natively... for microseconds or milliseconds...
                             // ② until something forces an exit; we return here
    switch (exit_info->reason) {
    case DATA_ABORT_AT_DEVICE_ADDRESS:   // guest touched a "register" of a virtual device
        emulate_device_access(…);        // e.g. the NVMe doorbell → go do disk I/O
        break;
    case GUEST_CALLED_HYPERVISOR:        // HVC instruction: explicit request (e.g. power off)
        …
    case TIMER_OR_INTERRUPT:             // host needs the core back, or a virtual timer fired
        …
    }
}                                        // ③ loop: re-enter the guest
```

**Who calls whom** (the question you always want answered):

| Step | Actor | Does |
|---|---|---|
| 1 | `vmware-vmx` vCPU thread | Calls `hv_vcpu_run()` (a library call into Hypervisor.framework) |
| 2 | XNU (EL2) | Saves the host's state, loads the guest's registers and stage-2 tables, and "returns" into the guest at EL1 |
| 3 | M2 core | Executes Windows instructions at full speed. Windows' own page tables, interrupts-off, `KeRaiseIrql`: all real, all on the real core |
| 4 | M2 core | Hits something the hypervisor configured to trap → **VM exit**: hardware jumps to EL2 |
| 5 | XNU | Handles what it can itself (e.g. a timer), otherwise returns from `hv_vcpu_run()` to the thread with an exit reason |
| 6 | `vmware-vmx` | Emulates the effect (device, power, …), updates guest registers, loops to step 1 |

**What traps?** Whatever the hypervisor tells the hardware to trap: accesses to guest-physical addresses that aren't backed by RAM (that's how devices work, §B6), certain system registers, `WFI` (the guest is idle: "wait for interrupt", so give the core back to macOS), and hypervisor calls. Everything else, including nearly all ordinary computation, never exits.

**The performance rule this gives you:** VMs are fast at *computing* and slower at *I/O*, because every device interaction costs exits. That's why paravirtual devices exist (§B6).

**And the scheduling consequence:** to macOS, your 4 vCPUs are 4 threads competing with Safari, Spotlight and everything else for 8 cores. When the guest thinks a CPU is "running", the host may have descheduled that thread. This is one source of guest timing weirdness, and relevant later: a 0x133 DPC_WATCHDOG in a VM can be caused by the *host* starving a vCPU (002).

## §B4 Memory: two translations 🟢 OWN IT

> **Retrieval moment (008):** what does a page table entry map, and who walks the table on every memory access?

In 008 you saw one translation: **virtual → physical**, walked by the CPU's MMU using tables the OS kernel builds. In a VM there are two, and the hardware does both:

```
Windows app pointer           0x00007FF6_1234_5000   guest-virtual (GVA)
        │  stage 1: Windows' page tables (Windows builds them, exactly as in 008)
        ▼
"physical" address Windows   0x0000_0000_8340_2000   guest-physical (GPA)  ← Windows thinks this is RAM
        │  stage 2: the hypervisor's tables (XNU builds them for vmware-vmx)
        ▼
real RAM chip address        0x0000_0008_1F77_C000   host-physical (HPA)
```

(Addresses are illustrative.)

1. **Windows owns stage 1** and never knows stage 2 exists. Its whole "physical memory" (0 to 4 GB, plus device holes) is an illusion.
2. **The hypervisor owns stage 2.** It decides which guest-physical pages are backed by which real pages, and which are not backed at all (device addresses → trap, §B6).
3. **Guest RAM is ordinary process memory.** `vmware-vmx` allocates 4 GB of its own virtual memory and asks the hypervisor to map it into the guest at guest-physical 0…4 GB. To macOS, that's just a big allocation by an app. So:
   - It isn't all in RAM at boot. Pages get real memory when first touched.
   - **macOS can swap guest RAM to the internal SSD** under pressure (§A2's swap files). Windows has no idea; it just sees a slow memory access.
   - When the VM is shut down and Fusion quits, the process exits and all 4 GB is freed. That's the 011 point: "the VM only uses its 4 GB while running."
4. **This is the same trick as 008, one level up.** Windows uses page tables to give each *process* the illusion of its own memory. The hypervisor uses stage-2 tables to give each *VM* the illusion of its own physical memory.

**Why two levels instead of the hypervisor editing Windows' tables?** Older x86 hypervisors did exactly that ("shadow page tables"), and it was slow and complex. Hardware stage-2 (Arm) / EPT (Intel) / NPT (AMD) made the guest's own page tables work untouched. ⚫ You don't need the details.

**Page size side note:** `vm_stat` on your Mac reports `page size of 16384 bytes`: macOS on Apple silicon uses 16 KB pages. Windows inside uses 4 KB pages in its stage-1 tables. Stages can use different granules, so that's fine.

## §B5 Storage: your 120 GB disk that takes 14 GB 🟢 OWN IT

Windows sees a 120 GB NVMe SSD. On the T7, the whole VM folder is **14 GB**. Here's how, from your actual files.

The disk is many files. `Virtual Disk.vmdk` is a 1.8 KB **text** file, the *descriptor*:

```
createType="twoGbMaxExtentSparse"

# Extent description
RW 8323072 SPARSE "Virtual Disk-s001.vmdk"
RW 8323072 SPARSE "Virtual Disk-s002.vmdk"
…
RW 1048576 SPARSE "Virtual Disk-s017.vmdk"
RW 8323072 SPARSE "Virtual Disk-s018.vmdk"
…
RW 917504  SPARSE "Virtual Disk-s032.vmdk"
```

**Decode it, one name at a time:**

1. Each `RW n SPARSE "file"` line is an **extent**: "the next *n* sectors of the virtual disk are stored in this file." A sector here is 512 bytes.
2. `8323072 sectors × 512 bytes = 4,261,412,864 bytes ≈ 3.97 GiB` per full extent. (The format splits the disk into chunks so no file gets huge. The name says "2GbMax" for historical reasons; Fusion now uses ~4 GB chunks.)
3. Total: 30 full extents + one of 1,048,576 + one of 917,504 = **251,658,240 sectors × 512 = 120 GiB**. Matches the disk size you set.
4. **SPARSE** = a chunk only stores the blocks the guest has actually written. Blocks never written read as zeros and cost no space. That's why `s006`–`s030` are each **512 KB** on disk (just headers), while `s001`–`s004` are 2.7–4.2 GB (Windows' files).

**Your files tell a story** (`ls -la`, 2026-10-24):

```
Virtual Disk-s001 … s004    2.7–4.2 GB   ← Windows itself, written at the start of the disk
Virtual Disk-s005             4 MB
Virtual Disk-s006 … s016     0.5 MB each ← never written yet (free space)
Virtual Disk-s017            0.5 MB      ← the odd-sized one: 1,048,576 sectors
Virtual Disk-s018 … s030     0.5 MB each ← never written
Virtual Disk-s031           297 MB       ← something written near the END of the disk
Virtual Disk-s032           468 MB
```

- **Why is `s017` an odd size?** 16 × 8,323,072 + 1,048,576 = 134,217,728 sectors = **exactly 64 GiB**. That was the wizard's default disk size (011 step 4). When you enlarged it to 120 GB, Fusion *appended* extents `s018`–`s032`. The descriptor still shows the seam.
- **Why is there data at the very end?** Windows Setup typically puts a small recovery partition after the main C: partition, and GPT keeps a backup partition table in the last sectors of a disk. That's my best explanation for `s031`/`s032`; I haven't opened the partitions to confirm.

**What "growable" costs you:** the T7 must have room for the disk to grow to 120 GB. Sparse files also never shrink on their own when Windows deletes files (Fusion has a "Clean Up Disk"/compact action for that). ⚫

**The other files in the bundle**, so nothing in there is a mystery:

| File | What it is |
|---|---|
| `Windows 11 64-bit Arm.vmx` | The VM's **configuration**: a text file of `key = "value"` lines (CPUs, memory, which files are which devices) |
| `Virtual Disk*.vmdk` | The virtual NVMe disk (above) |
| `Windows 11 64-bit Arm.nvram` | The virtual motherboard's **UEFI variable storage** (boot order, Secure Boot state) |
| `vmware.log`, `vmware-0/1/2.log` | Logs of this run and the previous three |
| `*.scoreboard`, `mksSandbox*.log` | Runtime bookkeeping and the display/input subprocess's logs ⚫ |
| `.vmsd` | Snapshot list (empty until you take one) |
| `.vmxf`, `.plist` | Fusion library/metadata ⚫ |

## §B6 Devices: emulated vs paravirtual (the missing network, explained) 🟢 OWN IT

> **Retrieval moment (tracker: MMIO under an OS, from your 10-18 question about registers at fixed addresses):** on real hardware, how does a driver talk to a device? (It reads and writes the device's registers, which appear at physical addresses: memory-mapped I/O.)

A guest driver does exactly the same thing. The trick is that **nothing is at those addresses**:

1. Windows enumerates PCI and finds an NVMe controller (lecture 006: the bus driver reports a child with hardware IDs). Its registers are at, say, guest-physical `0xFEB0_0000`.
2. Windows' `stornvme` driver writes a command into a queue in guest RAM, then writes the controller's **doorbell register** at `0xFEB0_1000`.
3. That guest-physical page has **no stage-2 mapping**. The write faults → **VM exit** (§B3).
4. `vmware-vmx` sees "write of value X to address `0xFEB0_1000`", knows that's its virtual NVMe doorbell, reads the command from guest RAM, and performs it as a `read()`/`write()` on the right `.vmdk` file.
5. When done, it writes the result into guest RAM and **injects a virtual interrupt** into the guest (Arm's virtual GIC). Windows' ISR runs → DPC → completes the IRP (005, 009).

So a **virtual device** = a region of guest-physical address space that traps, plus code in `vmware-vmx` that behaves like the hardware would.

**Two styles of virtual device:**

| | **Emulated** | **Paravirtual** |
|---|---|---|
| Pretends to be | A real, standard device (NVMe, SATA, USB xHCI, Intel e1000) | A device designed for VMs, which never existed in hardware (VMXNET3, virtio, VMware SVGA) |
| Guest driver | Already in Windows (inbox) | Must be installed (VMware Tools) |
| Speed | Slower: real hardware interfaces weren't designed to minimize exits | Faster: batches work, few register touches |
| On your VM | `nvme0` (disk), `sata0:1` (DVD) | `ethernet0.virtualDev = "vmxnet3"` |

**Now last night's "Let's connect you to a network" mystery is a 006 story:**

1. Windows' PCI bus driver enumerated a network controller with VMware's VMXNET3 hardware ID.
2. PnP searched the driver store for an INF matching that hardware ID.
3. Windows ships no VMXNET3 driver, so no match → the device sat in Device Manager with no driver → no network adapter → no network.
4. **VMware Tools** is, mostly, a bundle of drivers (VMXNET3, display, mouse, shared folders) plus a guest service. Installing it adds the matching INF; PnP then loads the driver and the network appears.

That's also why "Install driver" was offered on that screen: Windows Setup knew a device lacked a driver.

**Where are the real devices?** The T7 is never visible to Windows as a USB drive. Windows sees an NVMe disk; `vmware-vmx` turns that into file reads on the T7 through **macOS's** file system and USB drivers. The Mac's keyboard reaches the guest the same way: macOS delivers key events to Fusion (which is why Fusion needed **Accessibility** permission), and Fusion injects them into a virtual USB keyboard.

## §B7 Firmware, Secure Boot, TPM, and the encryption password 🔵 CONTRACT

A real PC starts by running **UEFI firmware** from a flash chip on the motherboard (firmware/003). A VM needs the same, so:

- **The firmware is a file Fusion ships** (in `VMware Fusion.app/Contents/Library/roms/`), loaded into the guest's memory at power-on. `firmware = "efi"` in the `.vmx`.
- **Its settings (UEFI variables) live in `Windows 11 64-bit Arm.nvram`** (2.4 MB), the VM's version of the motherboard's flash. Boot order and the **Secure Boot** on/off state are stored there. That's why 010's Secure Boot steps are VM *settings*, and why `vmware.log` reports `SecureBootModeDisabled`.
- **The vTPM** is software too: the app contains `Contents/Library/tpm2emu`, a TPM 2.0 emulator. Windows 11 requires a TPM, and BitLocker and Windows Hello store keys in it.
- **Why the VM has a password:** a TPM's whole point is that its secrets can't be copied off the machine. A *virtual* TPM's secrets are just files, so Fusion **encrypts** them (`vmx.encryptionType = "partial"`: only the TPM-related state, not the whole disk). The key comes from the password you set. Lose the password and the TPM state can't be decrypted, so the VM won't start. That's the 011 warning.

## §B8 Networking: NAT 🔵 CONTRACT

`ethernet0.connectionType = "nat"`: "Share with my Mac."

1. Fusion (via Apple's **vmnet.framework**, the second framework in the `otool` output) creates a small private virtual network containing just the VM and the Mac.
2. A DHCP server on that network gives the VM a private address (something like `192.168.x.y`).
3. When the VM talks to the internet, macOS rewrites the packets to come **from the Mac's own address** (Network Address Translation), the same thing your home router does for every device in your house.
4. Result: the VM can reach out, but other machines on your LAN can't reach in. 010 Phase 6 option B (a physical target PC for KDNET) needs **bridged** mode instead, where the VM appears on your home network as its own device.

The log line `VNET: MacosVmnetVirtApiStartIsolatedInterface: Ethernet0: connect adapter to host` is this step happening at boot.

## §B9 Snapshots, suspend and shutdown 🟢 OWN IT

Now that you know a VM is (config + disk files + nvram + RAM in a process), these three are easy to define precisely:

| Action | What happens to the guest's state | Where it goes | RAM afterwards |
|---|---|---|---|
| **Shut down** (from Windows) | Windows flushes and powers off its virtual hardware; RAM contents discarded | Disk state stays in `.vmdk` | Freed when Fusion/`vmware-vmx` exits |
| **Suspend** | Fusion stops the vCPUs and **writes all 4 GB of guest RAM + device state to files** in the bundle (`.vmss`/`.vmem`) | T7 | Freed. Resume reads it back |
| **Snapshot** | Fusion freezes the current `.vmdk` files as read-only and sends **future writes to new delta files**; with the VM running it also saves RAM | T7, inside the bundle; listed in `.vmsd` | Unchanged |
| **Revert to snapshot** | Throws away the delta files, back to the frozen disk (+ RAM if saved) | — | — |

That's why snapshots are your safety net for driver crashes (010's snapshot plan): a broken boot is just "a delta file you can throw away."

And it's why **unplugging the T7 while the VM is running *or suspended* is dangerous**: the disk, the nvram, and (if suspended) the RAM image are all files on it. Pulling it mid-write is like pulling power from a real PC's SSD mid-write.

## §B10 What VMs can't do here 🔵 CONTRACT (with honest sizing)

**Nested virtualization** = running a hypervisor *inside* the guest. Windows needs that for **VBS/HVCI** (Hyper-V underneath Windows), WSL2 and Windows Sandbox. For a guest to run a hypervisor, the host must let the guest use EL2. Apple's Hypervisor framework only supports that on **M3 or later** with macOS 15+, and VMware/Parallels haven't necessarily exposed it. Your M2 can't. So in this VM: no VBS, no memory integrity, no WSL2. 010 called that "convenient for a test lab", and now you know the mechanism behind the sentence.

**Live kernel debugging** (breakpoints in your driver) needs a debugger that keeps running while the target's kernel is frozen. The target's kernel debug transport (KDNET) needs a network card it supports, and VMXNET3 on Arm may not be one (010 Phase 6 documents a user report of it failing). That's a *device support* limitation, not a VM-concept limitation. ⚫ Not worth your time until Phases 1–5 are done.

## §B11 Two full traces

### Trace 1: what happened when you clicked "Power On" (11 steps)

1. You click Power On. **Fusion's UI** (the app you double-clicked) starts a new **`vmware-vmx`** process for this VM. (UI and VM are separate processes, so a UI crash doesn't kill the VM.)
2. `vmware-vmx` reads the **`.vmx`**: 4 vCPUs, 4096 MB, EFI firmware, NVMe on `Virtual Disk.vmdk`, DVD on the ISO, VMXNET3 on NAT, vTPM.
3. It asks the vTPM password from you or the Keychain, then decrypts the TPM state.
4. It calls **Hypervisor.framework** to create a VM, allocates 4 GB of memory and maps it in as guest-physical RAM (stage 2), leaving holes where virtual devices live.
5. It opens the **`.vmdk`** files and the ISO on the T7, and sets up the NAT interface through vmnet.
6. It loads the **UEFI firmware** into guest memory, plus the `.nvram` variables.
7. It creates **4 vCPU threads**, sets vCPU 0's program counter to the firmware's entry point, and starts the §B3 loop.
8. The **firmware runs on a real M2 core**, enumerates the virtual devices (it sees NVMe, the SATA DVD), reads the boot order from nvram and tries each entry. On your first boots, the boot order put the DVD first and showed "Press any key to boot from CD or DVD" for ~3 seconds; your keystrokes weren't reaching the VM (no Accessibility permission), so it timed out. Your log recorded it: `Guest: Status upon boot failure: Time out`.
9. With the disk installed, the firmware loads **Windows Boot Manager** from the NVMe disk's EFI partition: `Guest: About to do EFI boot: Windows Boot Manager`.
10. Then `Guest: Firmware has transitioned to runtime`: the UEFI `ExitBootServices` moment (firmware/003), where Windows' kernel takes over the (virtual) machine.
11. Windows' PnP enumerates devices, loads `stornvme` for the disk, finds no driver for VMXNET3 (§B6), and boots to the desktop.

### Trace 2: Windows saves a file, all the way down to the T7 (12 steps)

1. Notepad calls `WriteFile` (guest user mode, EL0).
2. Syscall → Windows kernel (EL1) → NTFS → volume manager → `stornvme` (009's IRP path).
3. `stornvme` puts an NVMe write command in a queue in guest RAM and writes the **doorbell** register.
4. No stage-2 mapping there → **VM exit** to XNU (EL2) → returns to the vCPU thread in `vmware-vmx` (EL0 on the host).
5. `vmware-vmx`'s NVMe emulation reads the command: "write these 8 sectors at LBA 12,345,678 from guest-physical buffer B."
6. It computes which extent holds LBA 12,345,678 (12,345,678 ÷ 8,323,072 → extent 2, i.e. `s002`) and the offset in it.
7. It calls `pwrite()` on `Virtual Disk-s002.vmdk`: an ordinary **macOS** system call by an ordinary app.
8. **XNU's HFS+ driver** updates the file on the T7; macOS's **USB mass-storage driver** sends the data over USB to the T7's controller, which writes it to flash.
9. When the write completes, `vmware-vmx` marks the NVMe command done in guest RAM.
10. It **injects a virtual interrupt** into the vCPU.
11. Windows' NVMe ISR runs, queues a DPC, which completes the IRP (005).
12. `WriteFile` returns in Notepad.

The two kernels never talk to each other. Windows thinks it wrote to an SSD. macOS thinks an app wrote to a file. `vmware-vmx` is the translator in the middle.

---

## Misconceptions

| You might think | Reality | Why |
|---|---|---|
| An app is either "on the SSD" or "in RAM" | Its file is on disk; its running copy is pages in RAM, loaded on demand | Demand paging (§A2, 008) |
| You can't choose where downloads go | You can; it's a browser setting | A download is just "write bytes to a file" (§A3) |
| Double-clicking the `.dmg` installed Fusion onto the T7 | It mounted a disk image; the app was copied to `/Applications` on the internal drive | §A5 evidence: 937 MB in `/Applications`, dmg still mounted as `disk5` |
| `.dmg` ≈ `dpkg` | dmg = disk image (a file that is a disk). dpkg = Debian's package installer | §A4, §A6 |
| Install locations are always fixed | Fixed where software must find things without being told; flexible where a config says where to look | §A7 |
| The VM "uses my hardware" directly | It uses virtualization hardware **through the macOS kernel**, and reaches real devices through ordinary macOS files and APIs | §B1, §B6 |
| A VM emulates the CPU | Guest instructions run natively; only exits are handled in software. Emulation is the slow alternative, used for different architectures | §B2 |
| Windows in the VM sees the T7 | It sees a virtual NVMe disk; the T7 is only visible to macOS | §B6, Trace 2 |
| The VM's 4 GB is reserved forever | It's the `vmware-vmx` process's memory: allocated as touched, swappable, freed when the process exits | §B4 |
| No network = a Windows setup problem | A missing **driver** for a paravirtual NIC; VMware Tools supplies it | §B6, lecture 006 |
| The VM password is just a login | It encrypts the virtual TPM's state; without it the VM can't boot | §B7 |
| Windows on Arm can't run x64 code | It can for apps (Prism, user mode). Not for drivers: kernel code must be ARM64 | §B2 |

## Interview relevance

Honest sizing: **high** for a Windows/platform role. Virtualization is everywhere at Microsoft: Hyper-V underneath Windows (VBS, HVCI, Credential Guard), Azure (every VM is a Hyper-V guest), WSL2, Windows Sandbox, Dev Box. Questions you could plausibly get, and can now answer:

- "What's the difference between a type 1 and type 2 hypervisor?" (§B1)
- "Why is a VM fast at compute but slower at I/O?" (§B3, §B6)
- "What is a VM exit?" (§B3)
- "How does memory virtualization work?" (§B4: two-stage translation; mention shadow page tables as the old way)
- "What's paravirtualization and why use it?" (§B6)
- "What is VBS, and why does it need a hypervisor?" (§B10: a short answer is enough; VBS uses Hyper-V to protect memory even from the Windows kernel)
- For a driver role: "Why must drivers be native ARM64 on Windows on Arm?" (§B2)

The Part A material is less likely to be asked directly, but it's the kind of fluency ("where does this file live, who loads it, what registered it") that shows in every debugging conversation.

## Self-check questions

1. Right now, where is the file that becomes the Fusion process, and where is that process's code while it runs?
   <details><summary>Answer</summary>The file is <code>/Applications/VMware Fusion.app/...</code> on the internal SSD. While it runs, the pages actually used are in RAM (loaded on demand by page faults); unused pages stay only on disk, and under pressure clean pages can be dropped and reloaded from the file.</details>
2. Name the three locations (download, install, data) for Fusion and the VM on your machine.
   <details><summary>Answer</summary>Download: <code>/Volumes/T7/windows_experiment/applications/</code> (the .dmg). Install: <code>/Applications/VMware Fusion.app</code> on the internal drive. Data: the <code>.vmwarevm</code> bundle on the T7 (plus Fusion's prefs in <code>~/Library</code>).</details>
3. What is a disk image? Give three from last night and say who mounts or attaches each.
   <details><summary>Answer</summary>A file whose contents are a disk's blocks (with a filesystem inside). The .dmg (macOS mounts it under /Volumes), the .iso (vmware-vmx attaches it to the VM as a DVD), the .vmdk (vmware-vmx attaches it as an NVMe disk).</details>
4. What five jobs does <code>apt</code> do that dragging an <code>.app</code> doesn't? Which of them does <code>dpkg</code> do?
   <details><summary>Answer</summary>Catalog lookup from repositories, dependency resolution, download + signature verification, unpack to fixed locations with install scripts, and a database of installed files. dpkg does only the unpack/place and database parts.</details>
5. Why are some install locations fixed and others flexible? Give one example of each.
   <details><summary>Answer</summary>Fixed when other software must find the thing without being told (/opt/homebrew/bin via PATH, shared libraries via the linker). Flexible when a config records the path (the ISO path in the .vmx, the VM path in Fusion's library, a driver's binPath in the registry).</details>
6. Why does Windows for Arm run fast on your M2 but x64 Windows wouldn't?
   <details><summary>Answer</summary>Same instruction set: the M2 executes Arm64 guest instructions directly, with the hypervisor handling only exits. x64 instructions would have to be emulated in software, which is far slower.</details>
7. Describe a VM exit: what causes one, where does control go, and what happens next?
   <details><summary>Answer</summary>The guest does something the hypervisor configured to trap (touches an unmapped device address, a trapped system register, WFI, HVC). Hardware switches to EL2 (XNU's hypervisor), which either handles it or returns from hv_vcpu_run() to the vmware-vmx vCPU thread with an exit reason. vmware-vmx emulates the effect and re-enters the guest.</details>
8. Draw the two translations a guest app's pointer goes through. Who builds each table?
   <details><summary>Answer</summary>Guest-virtual → guest-physical (stage 1, Windows' page tables) → host-physical (stage 2, built by the hypervisor in XNU on behalf of vmware-vmx). Windows doesn't know stage 2 exists.</details>
9. Your VM folder is 14 GB but Windows sees 120 GB. Explain using the vmdk descriptor.
   <details><summary>Answer</summary>The descriptor lists 32 sparse extents totalling 251,658,240 sectors × 512 B = 120 GiB. Sparse extents only store blocks that were written; never-written regions read as zeros and cost only a header (~512 KB per extent).</details>
10. What does the odd-sized extent <code>s017</code> reveal?
    <details><summary>Answer</summary>16 × 8,323,072 + 1,048,576 sectors = 64 GiB exactly: the original wizard-default disk. Extents s018–s032 were appended when you enlarged it to 120 GB.</details>
11. Why did the VM have no network before VMware Tools? Use lecture 006's vocabulary.
    <details><summary>Answer</summary>The virtual NIC is VMXNET3, a paravirtual device. PCI enumeration reported its hardware ID, but no INF in Windows' driver store matched, so no function driver loaded and no adapter existed. VMware Tools installs the matching driver package.</details>
12. Trace a guest disk write from the NVMe doorbell to the T7 in five steps.
    <details><summary>Answer</summary>Doorbell write → stage-2 fault → VM exit → vmware-vmx decodes the NVMe command and computes the extent/offset → pwrite() on the .vmdk file → macOS HFS+ and USB drivers write it to the T7; then a virtual interrupt completes the guest's I/O.</details>
13. Shut down vs suspend vs snapshot: where does the guest's RAM go in each?
    <details><summary>Answer</summary>Shut down: discarded. Suspend: written to files in the VM bundle on the T7. Snapshot: disk frozen with future writes going to delta files; RAM saved too if the VM was running.</details>
14. Why does the VM need a password, and what happens if you lose it?
    <details><summary>Answer</summary>The virtual TPM's secrets are files, so Fusion encrypts them with a key from that password. Lose it and the TPM state can't be decrypted, so the VM won't start.</details>
15. Why can't this VM run VBS/HVCI or WSL2?
    <details><summary>Answer</summary>They need a hypervisor inside the guest (nested virtualization), which requires the host to give the guest EL2. Apple's framework supports that only on M3+ with macOS 15+, and your Mac is an M2.</details>

## Sources

Checked 2026-10-24.

**Your machine** (read-only commands run on 2026-10-24): `ls -la` and `du -sh` of `/Volumes/T7/windows_experiment/` and the `.vmwarevm` bundle; `Virtual Disk.vmdk` descriptor; `.vmx` keys; `vmware.log` (`Monitor Mode: ULM`, `Guest:` lines, vmnet line); `otool -L` and `codesign -d --entitlements` on `vmware-vmx`; `file` on the ISO and `vmware-vmx`; `xattr` on the downloads; `df -h`; `pkgutil --pkgs`; `sysctl vm.swapusage`; `vm_stat`; `ls /opt/homebrew`.

- Apple Developer: Hypervisor framework (requires the `com.apple.security.hypervisor` entitlement; Apple-silicon virtualization extensions). https://developer.apple.com/documentation/hypervisor
- Apple Developer: Hypervisor on Apple silicon, EL2 / nested virtualization APIs (`hv_vm_config_set_el2_enabled`, `hv_vm_config_get_el2_supported`). https://developer.apple.com/documentation/hypervisor/apple-silicon
- Apple Developer Forums: EL2 enabled but vCPU starts in EL1 (M3 Pro, macOS 15.3.1). https://developer.apple.com/forums/thread/775546
- UTM issue #6700 and LWN discussion: nested virtualization requires macOS 15 and M3 or later (community reports). https://github.com/utmapp/UTM/issues/6700 · https://lwn.net/Articles/1038917
- Broadcom community: nested virtualization with VMware Fusion on Sequoia (not exposed to guests as of the thread). https://community.broadcom.com/vmware-cloud-foundation/question/nested-virtualization-with-vmware-fusion-in-sequoia
- VMware Community: Fusion uses Hypervisor.framework. https://communities.vmware.com/t5/VMware-Fusion-Discussions/VMware-Fusion-12-running-on-Apple-Silicon/m-p/2809642
- Wikipedia: VMware Fusion (Fusion 13 added Arm virtualization on Apple silicon; no x86 guests on Apple silicon). https://en.wikipedia.org/wiki/VMware_Fusion
- Microsoft Learn: How emulation works on Arm (Prism in 24H2; x86/x64 apps; JIT translation with cached results). https://learn.microsoft.com/windows/arm/apps-on-arm-x86-emulation
- Microsoft Learn: Program compatibility troubleshooter on Arm (hide x64 emulation; newer emulated CPU features). https://learn.microsoft.com/windows/arm/apps-on-arm-program-compat-troubleshooter
- Microsoft Support (via lecture 010): nested virtualization, including VBS, isn't supported in Windows 11 VMs on Apple-silicon Macs.

**Not verified here:** the expansion of `ULM` in the log (likely "user-level monitor"); exactly what occupies extents `s031`/`s032` (recovery partition and backup GPT is my best explanation); the suspend file names in Fusion 26 (`.vmss`/`.vmem` are the long-standing names); whether macOS swaps guest RAM in practice under your workload (it *can*: guest RAM is ordinary process memory). The `hv_vcpu_run` loop in §B3 shows the API's shape, not VMware's actual code.
