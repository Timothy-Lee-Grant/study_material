2026_10_21_23_20-(Device-Stacks-PnP-INF-Signing)

# Lecture 006 — Device Stacks: PnP, PDO/FDO/Filter Drivers, INF Files, and Driver Signing

> **For:** Timothy · **Date:** 2026-10-21
> **Prerequisites:** `lectures/firmware/003-from_bare_metal_to_an_os.md` §2–3 (components; drivers aren't processes; the separate stacks of the touch path). Debugging tie-ins: 001 (`!devnode`, `!devstack`), 002 (0x9F).
> **Why this lecture:** every Windows device investigation ends up on the same map: which drivers are layered on this device, who created each layer, how the device got that driver, and why Windows trusted it. This lecture builds that map from the bottom up and connects each piece to the commands you'll use.

---

## Core ideas (the answer key)

1. **The device tree vs the device stack:** the **device tree** (made of devnodes) records *which devices exist* and their parent/child relationships (a bus and the devices on it). Each devnode has a **device stack**: the drivers layered on *that one device*.
2. **Three roles in a stack, bottom to top:** the **PDO**, created by the *bus driver* that discovered the device; the **FDO**, created by the *function driver* that knows how to run it; and optional **filter** device objects above (upper) or below (lower) the FDO.
3. **The tree grows by enumeration.** A bus driver reports its children → PnP creates a devnode for each child → PnP finds and loads the child's drivers → each driver's `AddDevice` creates its device object and attaches it on top → PnP sends **start** with the device's hardware resources.
4. **Requests travel down the stack as IRPs.** Each layer handles a request, passes it down, or completes it. The `>` in `!irp` shows which layer holds it now, which is the "whose bug is it?" answer.
5. **An INF file is the installation recipe.** It says which hardware IDs the driver supports (the match), which files to copy, how to register the driver as a kernel service, and which filters to add. The PnP manager ranks candidate INFs and installs the best match from the **driver store**.
6. **Hardware IDs come from the bus.** ACPI uses `ACPI\VEN_DEV` or `ACPI\PNPxxxx`; PCI uses `PCI\VEN_xxxx&DEV_xxxx`; USB uses `USB\VID_xxxx&PID_xxxx`; HID uses `HID\VID_…`. This ID is the contract between the hardware's description and the driver.
7. **Kernel drivers must be signed, because kernel code is trusted with everything.** A signed **catalog** (`.cat`) holds the hashes of the package's files. Retail Windows loads kernel drivers signed through Microsoft: **WHCP (HLK-tested)** for production and Windows Update, **attestation signing** for client Windows without HLK testing (not distributable through Windows Update to retail), and **test signing** only on machines put into test mode.

---

## Table of Contents

- [1. Device objects, driver objects, devnodes](#1-device-objects-driver-objects-devnodes)
- [2. PDO, FDO, filters](#2-pdo-fdo-filters)
- [3. How the tree and the stacks get built](#3-how-the-tree-and-the-stacks-get-built)
- [4. IRPs through a stack](#4-irps-through-a-stack)
- [5. The touchscreen, fully mapped](#5-the-touchscreen-fully-mapped)
- [6. Hardware IDs and driver selection](#6-hardware-ids-and-driver-selection)
- [7. Reading an INF file](#7-reading-an-inf-file)
- [8. Installing and inspecting: the driver store and pnputil](#8-installing-and-inspecting-the-driver-store-and-pnputil)
- [9. Driver signing](#9-driver-signing)
- [10. Misconceptions](#10-misconceptions)
- [11. Saying it precisely](#11-saying-it-precisely)
- [12. Self-check](#12-self-check)
- [Sources](#sources)

---

## 1. Device objects, driver objects, devnodes 🟢

Three kernel structures, and what each stands for:

| Structure | One per… | Created by | Represents |
|---|---|---|---|
| **Driver object** (`DRIVER_OBJECT`) | loaded driver | The I/O manager, when the driver loads; passed to `DriverEntry` | *The code*: the driver's dispatch table and callbacks |
| **Device object** (`DEVICE_OBJECT`) | (device × driver layer) | Each driver, for each device it handles | *This driver's role on this device*: its own per-device state lives in its **device extension** |
| **Devnode** (`DEVICE_NODE`) | device | The PnP manager | *The device itself*: identity (instance path), parent and children in the tree, PnP state, problem code, and the device's resources |

One driver object can own many device objects (one driver, three identical sensors). One device has many device objects (one per driver layered on it). In WinDbg: `!drvobj` for driver objects, `!devobj` / `!devstack` for device objects, `!devnode` for devnodes.

---

## 2. PDO, FDO, filters 🟢

A **device stack** is a vertical list of device objects for one device:

```
   upper filter DO        (optional)  e.g. a vendor's value-add filter
   FDO                                 function driver: knows how to RUN the device
   lower filter DO        (optional)  e.g. a bus-specific quirk fixer
   PDO                                 bus driver: knows the device EXISTS on its bus
```

| Role | Created by | Knows | Typical responsibilities |
|---|---|---|---|
| **PDO** (physical device object) | The **bus driver** of the parent bus (ACPI, PCI, USB hub, HID class for HID collections…) | How to talk to the bus, power the slot, and report the device's identity and resources | Report hardware IDs; provide resources; power the device on the bus; complete requests that reach the bottom |
| **FDO** (functional device object) | The **function driver**: the main driver for the device | The device's own registers, protocol and behavior | Implement the device: start, I/O, interrupts, power policy |
| **Filter DO** | A **filter driver** | One specific modification | Add, change or observe requests passing through: logging, quirks, value-add features |

Two things to notice:
- A driver can play **both roles** in different stacks. `hidclass` is the function driver (FDO) for the HID-over-I2C device, *and* the bus driver that creates PDOs for each HID top-level collection it finds (a touch digitizer, a pen). Those child PDOs get their own stacks.
- Filters are added by **registry configuration** (from INF files), not by the filter driver deciding to attach somewhere. That's why an OEM's value-add filter can silently sit in the middle of a stack you didn't expect. `!devstack` shows it.

---

## 3. How the tree and the stacks get built 🟢

Two phases (the tracker's setup-time vs run-time split applies here too):

### Setup time: enumeration and start, numbered

1. **The root of the tree** exists at boot. The ACPI driver loads early and reads the ACPI tables (003).
2. **A bus driver enumerates.** The PnP manager asks the ACPI driver for its children (a PnP request asking for *bus relations*). ACPI answers with a list of PDOs, one per device described in the tables, including the touchscreen (`PNP0C50`) and the I2C and GPIO controllers.
3. **PnP creates a devnode** for each new child and asks the child's PDO for its **hardware IDs** and **compatible IDs**.
4. **PnP finds a driver** (§6): it matches the IDs against INFs in the driver store, and installs the best match if it isn't installed yet.
5. **PnP loads the drivers** for the stack, bottom-up: lower filters, the function driver, upper filters. For each, if it's not already loaded, `DriverEntry` runs once.
6. **Each driver's `AddDevice` runs** (in KMDF: `EvtDriverDeviceAdd`). It creates its device object and **attaches it on top** of the stack so far. The stack now exists, but the device isn't running.
7. **PnP assigns resources** (memory ranges, interrupts, I2C connection IDs, GPIO pins: from ACPI for this device) and sends **start** (`IRP_MN_START_DEVICE`) down the stack. Each layer receives the resources.
   - In KMDF the framework turns start into callbacks: `EvtDevicePrepareHardware` (map registers, open the I2C target) and `EvtDeviceD0Entry` (power on, initialize).
8. If the function driver enumerates children too (`hidclass` finding HID collections), repeat from step 2 one level down.

### Run time

The stacks just exist. Requests flow through them (§4), and PnP intervenes again only on changes: removal, surprise removal (the device vanished), resource rebalancing, disable/enable, or driver update.

**What disable/enable does, in these terms:** PnP sends remove to the stack, the drivers tear down their device objects, and PnP rebuilds the stack from step 5. That's why it fixes stuck driver state, and why it destroys the evidence (003 §3).

**Problem codes** record where this sequence failed. Device Manager shows them, and so does `!devnode`:

| Code | Means | Phase where it failed |
|---|---|---|
| Code 28 | Drivers not installed | Step 4: no INF matched |
| Code 31 / 39 | Driver couldn't be loaded | Step 5 |
| Code 10 | Device cannot start | Step 7: a driver failed start (often hardware not responding, or wrong resources) |
| Code 43 | The device reported a problem | After start: the driver reported failure (common for USB/HID) |
| Code 52 | Windows cannot verify the digital signature | Step 5: the signature was rejected (§9) |

---

## 4. IRPs through a stack 🔵

An **IRP** (I/O request packet) is the kernel's request object. It holds the request type (read, write, device control, PnP, power), the buffers, and **one stack location per layer**, a small slot for that layer's parameters.

How a request moves:
1. A request is sent to the **top** of the stack.
2. Each layer's dispatch routine looks at its stack location and either:
   - **completes** the IRP (done; it travels back up through any completion routines), or
   - **passes it down**: sets up the next stack location and calls the next lower driver (`IoCallDriver`), or
   - **pends** it: keeps it to finish later (waiting for hardware), and returns.
3. When the IRP is finally completed, each layer that registered a **completion routine** gets a callback on the way back up.

In WinDbg, `!irp <addr>` lists the stack locations. The one marked `>` is the **current** location, meaning the layer that holds it now. A request pended forever in a driver is the root of many hangs and of 0x9F (002).

KMDF hides most of this: incoming IRPs become **WDFREQUEST** objects in **queues**, and the framework handles PnP and power IRPs for you, turning them into callbacks. That's why `!wdfkd.wdfdevicequeues` exists alongside `!irp`.

---

## 5. The touchscreen, fully mapped 🟢

Correcting and completing the single-stack picture from the platform validation lecture. There are several separate stacks, linked by enumeration (parent → child), by I/O targets, and by interrupt routing:

```
Device tree (parent → child)                     Device stack of each node (top → bottom)
─────────────────────────────────────────────    ──────────────────────────────────────────────
ACPI (root bus)
 ├─ I2C controller   (ACPI\VEN..)                 [I2C controller driver on SpbCx] / [ACPI PDO]
 ├─ GPIO controller  (ACPI\VEN..)                 [GPIO controller driver on GpioClx] / [ACPI PDO]
 └─ HID-over-I2C touch (ACPI\PNP0C50)             [hidclass FDO + hidi2c minidriver] / [ACPI PDO]
     └─ HID collection: touch digitizer           [HID input/pointer drivers] / [hidclass PDO]
     └─ HID collection: pen (if present)          [...] / [hidclass PDO]

Run-time links (not parent/child):
  hidi2c ──I/O requests──► I2C controller's stack      (via the I2C connection ID resource)
  GPIO pin 35 ──interrupt routing (primary/secondary)──► hidi2c's ISR
```

The questions this map answers:
- **Who created the touch device's PDO?** ACPI, because the ACPI tables described the device.
- **Who is its function driver?** `hidclass`, with `hidi2c` plugged in as the HID-over-I2C minidriver.
- **Who created the digitizer's PDO?** `hidclass`, acting as a bus driver for HID collections.
- **When touch input stops, which stacks could be stuck?** The touch device's stack, the I2C controller's stack (transfers), the GPIO controller's (interrupt routing), and the child collection's stack (input delivery).

---

## 6. Hardware IDs and driver selection 🟢

When a bus driver reports a device, it reports two ordered lists:
- **Hardware IDs**: most specific first, e.g. `ACPI\VEN_ELAN&DEV_2514`, then `ACPI\ELAN2514`.
- **Compatible IDs**: generic class identities, e.g. `ACPI\PNP0C50` (HID over I2C).

Formats by bus (🔵):

| Bus | Example ID |
|---|---|
| ACPI | `ACPI\VEN_ABCD&DEV_0001`, `ACPI\PNP0C50` |
| PCI | `PCI\VEN_8086&DEV_A0E8&SUBSYS_…&REV_…` |
| USB | `USB\VID_045E&PID_07A5&REV_0100` |
| HID collections | `HID\VID_04F3&PID_2514&Col01`, `HID_DEVICE_UP:000D_U:0004` (usage page/usage) |

**Selection:** the PnP manager collects every INF in the driver store whose models list matches any of the device's IDs, then **ranks** them. Roughly in priority order:
1. Better signature trust beats worse.
2. A match on a hardware ID beats a match on a compatible ID, and earlier (more specific) IDs beat later ones.
3. Then a newer driver date and version.

This is how a generic touchscreen "just works": Microsoft's in-box `hidi2c.inf` matches the *compatible* ID `ACPI\PNP0C50`. A vendor can ship an INF matching the *hardware* ID to take priority.

---

## 7. Reading an INF file 🟢

An INF is a text file of `[sections]` and `key = value` lines. Here's a minimal INF for a hypothetical KMDF sensor driver, `TgSensor.sys`, for an ACPI device `ACPI\TGS0001`, with each line explained:

```ini
[Version]
Signature   = "$WINDOWS NT$"                          ; every modern INF has this
Class       = Sensor                                  ; Device Manager category
ClassGuid   = {5175d334-c371-4806-b3ba-71fd53c9258d}  ; the Sensor class's GUID
Provider    = %ProviderName%                          ; who wrote it (from [Strings])
CatalogFile = TgSensor.cat                            ; the signed catalog (§9)
DriverVer   = 10/21/2026,1.0.0.0                      ; date,version — used in ranking
PnpLockdown = 1                                       ; installed files can't be overwritten by other apps

[Manufacturer]
%MfgName% = Models, NTamd64.10.0...16299, NTarm64.10.0...16299   ; per-architecture model lists

[Models.NTamd64.10.0...16299]
%DeviceDesc% = TgSensor_Install, ACPI\TGS0001        ; THE MATCH: this hardware ID → this install section

[Models.NTarm64.10.0...16299]
%DeviceDesc% = TgSensor_Install, ACPI\TGS0001

[TgSensor_Install.NT]
CopyFiles = TgSensor_Files                            ; which files to copy

[TgSensor_Files]
TgSensor.sys

[DestinationDirs]
DefaultDestDir = 13                                   ; 13 = run the driver from the driver store

[SourceDisksNames]
1 = %DiskName%
[SourceDisksFiles]
TgSensor.sys = 1

[TgSensor_Install.NT.Services]
AddService = TgSensor, 0x00000002, TgSensor_Service   ; 0x2 = this service is the function driver

[TgSensor_Service]
DisplayName   = %ServiceName%
ServiceType   = 1                                     ; kernel driver
StartType     = 3                                     ; demand start (PnP starts it when a device appears)
ErrorControl  = 1                                     ; normal
ServiceBinary = %13%\TgSensor.sys

[TgSensor_Install.NT.Wdf]
KmdfService = TgSensor, TgSensor_WdfSect

[TgSensor_WdfSect]
KmdfLibraryVersion = $KMDFVERSION$                    ; filled in by the build tool (stampinf)

[Strings]
ProviderName = "Example"
MfgName      = "Example"
DeviceDesc   = "Example I2C Sensor"
DiskName     = "Example Install Disk"
ServiceName  = "Example Sensor Driver"
```

**Read it as a chain:** hardware ID `ACPI\TGS0001` → `[Models…]` line → install section `TgSensor_Install` → copy `TgSensor.sys` → `.Services` registers a **kernel service** named `TgSensor` as the **function driver** → `.Wdf` binds it to KMDF.

**How filters get added:** an install section can add registry values `UpperFilters` / `LowerFilters` (an `AddReg` line) naming filter services. PnP then loads those services above or below the FDO when building the stack (§3 step 5). To find out where a surprise filter came from, look for the INF that added it.

**The decorations** (`NTamd64.10.0...16299`) mean "this list applies on 64-bit x86 / Arm64, Windows 10 build 16299 or later". Arm laptops need the `NTarm64` section. A driver package without one won't install on them, which is a classic bring-up miss.

---

## 8. Installing and inspecting: the driver store and pnputil 🟢

The **driver store** (`C:\Windows\System32\DriverStore\FileRepository\`) is Windows' trusted repository of driver packages. Installing a package means: verify its signature → copy the whole package into the store (renamed `oemNN.inf`) → install it on matching devices. With `DestinationDirs = 13`, the driver even **runs** from its store folder.

`pnputil` is the built-in command-line tool:

```
pnputil /add-driver TgSensor.inf /install     ← stage into the store and install on matching devices
pnputil /enum-drivers                         ← list third-party packages in the store (oemNN.inf ↔ original name)
pnputil /enum-devices /problem                ← devices with a problem code
pnputil /enum-devices /connected /drivers     ← connected devices with their matching and installed drivers
pnputil /delete-driver oem42.inf /uninstall   ← remove a package (and uninstall it from devices)
pnputil /restart-device "<instance id>"       ← restart a device (newer Windows builds)
```

Device Manager shows the same information graphically. For a device: Properties → Driver → Driver Details (files), Details → Hardware Ids / Compatible Ids / Matching device ID / Inf name, and the Events tab (install history). **"Matching device ID"** tells you *which* ID the installed INF matched on, which settles "why did it pick this driver?"

---

## 9. Driver signing 🟢

### 9.1 Why

Kernel-mode code runs with full privilege, in the shared kernel address space (from 003). A malicious or tampered kernel driver can do anything. So Windows enforces **kernel-mode code integrity**: a kernel driver loads only if its signature chains to a trusted root and its files match the signed hashes.

### 9.2 What actually gets signed

- The package's **catalog file** (`.cat`) lists a cryptographic hash of every file in the package, and **the catalog is signed**. Installing checks the catalog's signature, then each file's hash against it.
- The `.sys` file itself is usually also **embedded-signed**, for boot-start drivers that load before the catalog database is available.

### 9.3 The signing paths

| Path | What it is | Who it's for | Limits |
|---|---|---|---|
| **WHCP / HLK-tested signing** | Run the Hardware Lab Kit tests, submit the results to Microsoft's Partner Center, and Microsoft signs | Production drivers; Windows Update distribution | Microsoft calls it "the recommended method… because it signs a driver for all OS versions" |
| **Attestation signing** | Submit the package (signed with your **EV** certificate) to Partner Center; Microsoft signs it without HLK test results | Client Windows (Windows 10 Desktop and later) when HLK isn't needed | Microsoft: "not Windows Certified"; "can't be published to Windows Update for retail audiences"; not accepted by Windows Server |
| **Preproduction signing** | Partner Center preproduction signature | Partners testing on Secure Boot machines provisioned to trust it | Not trusted on retail machines |
| **Test signing** | Sign with your own test certificate; put the target machine into test mode (`bcdedit /set testsigning on`, which requires Secure Boot off; a desktop watermark appears) | Your own development and lab machines | Never for anything shipped |

### 9.4 What else gates loading

- **Secure Boot** on retail machines: no test mode, and only properly signed kernel code loads.
- **Memory integrity (HVCI)**: the hypervisor enforces code integrity, and drivers must be compatible (for example, no writable-and-executable memory). An incompatible driver blocks turning HVCI on, or fails to load.
- **Microsoft's vulnerable driver blocklist**: specific known-vulnerable signed drivers are blocked even though they're validly signed.

When signing goes wrong, the device shows **Code 52** ("Windows cannot verify the digital signature"), and the Code Integrity event log (Applications and Services → Microsoft → Windows → CodeIntegrity → Operational) explains why.

---

## 10. Misconceptions

| You might think | Reality | Why it matters |
|---|---|---|
| A device has one driver | It has a stack: a PDO from the bus driver, an FDO from the function driver, and possibly filters | Bugs live in a specific layer |
| The I2C and GPIO controller drivers sit under hidi2c | They're separate devices with separate stacks; hidi2c uses them through I/O targets and interrupt routing | Ownership follows the real links |
| A filter driver decides where to attach | INF-installed registry values (`UpperFilters` / `LowerFilters`) put it there | Find surprise filters via INFs |
| Windows picks the newest driver | It ranks signature trust, then ID specificity (hardware ID over compatible ID), then date and version | Explains "why did it pick the old one?" |
| ACPI tables are consulted whenever the device is used | They're read during enumeration and start; afterwards the stack just runs | Setup bugs (wrong IDs, resources) show up as start failures or misbehavior later |
| Attestation-signed = certified | It's signed but not Windows Certified, and not distributable through Windows Update to retail | Production needs WHCP |
| Test signing works anywhere | Only in test mode, which needs Secure Boot off | Retail machines won't load it |

---

## 11. Saying it precisely

- "Each devnode has a device stack: the PDO from the bus driver that found the device, the FDO from the function driver, and optional upper and lower filters that INF registry values put there."
- "PnP builds it in order: the bus enumerates children, PnP matches hardware IDs to INFs in the driver store, loads drivers, each `AddDevice` attaches a device object, then PnP assigns resources and sends start. Problem codes tell you which step failed."
- "For the touchscreen: ACPI creates the PDO, hidclass with hidi2c is the function driver, and hidclass in turn creates PDOs for each HID collection. hidi2c reaches the I2C controller's separate stack through an I/O target."
- "Kernel drivers must chain to Microsoft's signature: WHCP after HLK testing for production and Windows Update, attestation for client Windows without HLK, and test signing only in test mode with Secure Boot off."

---

## 12. Self-check

1. What do a driver object, a device object and a devnode each represent?
<details><summary>Answer</summary>The driver's code (one per loaded driver); one driver's role on one device (one per device per layer); the device itself in the PnP tree (identity, state, resources, parent/child).</details>

2. Who creates the PDO, the FDO and filter device objects?
<details><summary>Answer</summary>The PDO: the parent bus driver. The FDO: the function driver. Filters: filter drivers, placed by INF registry values.</details>

3. List the setup-time steps from enumeration to a started stack.
<details><summary>Answer</summary>Bus enumerates → PnP creates the devnode and gets IDs → matches an INF → loads drivers → each AddDevice attaches → PnP assigns resources → start (KMDF: PrepareHardware, D0Entry).</details>

4. What does the `>` in `!irp` mark, and why does it matter?
<details><summary>Answer</summary>The current stack location, i.e. the layer holding the IRP now. That's which driver owns a stuck request.</details>

5. Name two roles hidclass plays in the touchscreen's tree.
<details><summary>Answer</summary>Function driver (FDO, with hidi2c as minidriver) for the HID-over-I2C device; bus driver creating PDOs for the HID collections.</details>

6. How does Windows choose among several matching INFs?
<details><summary>Answer</summary>It ranks them: signature trust first, then how specific the matched ID is (hardware ID over compatible ID, earlier in the list better), then driver date and version.</details>

7. In an INF, which section creates the match, and which registers the kernel service?
<details><summary>Answer</summary>The match: the models section line (description = install section, hardware ID). The service: <code>[&lt;install&gt;.Services]</code> with <code>AddService</code> (flag 0x2 marks the function driver).</details>

8. Why would a driver package fail to install on an Arm laptop while working on x64?
<details><summary>Answer</summary>Its INF has no <code>NTarm64</code> models section (and/or no Arm64 binary), so nothing matches on that architecture.</details>

9. What does Device Manager's "Matching device ID" tell you?
<details><summary>Answer</summary>Which of the device's IDs the installed INF matched on: why that driver was chosen.</details>

10. What is signed in a driver package, and what's checked at install?
<details><summary>Answer</summary>The catalog (.cat) holding hashes of all the package files is signed; boot-start .sys files are usually embedded-signed too. Install verifies the catalog signature, then each file's hash.</details>

11. Compare WHCP and attestation signing.
<details><summary>Answer</summary>WHCP: HLK-tested, Windows Certified, all OS versions, Windows Update. Attestation: no HLK, EV cert submission, client Windows 10+ only, not certified, not on Windows Update for retail.</details>

12. A device shows Code 52. Where do you look next?
<details><summary>Answer</summary>The CodeIntegrity Operational event log (why the signature was rejected), plus the package's signing path and the machine's Secure Boot / HVCI state.</details>

---

## Sources

Checked 2026-10-21.

- Microsoft Learn: Driver signing offerings (HLK-tested is "recommended… signs a driver for all OS versions"; attestation requires an EV certificate, is "not Windows Certified", "can't be published to Windows Update for retail audiences", "only works on Windows 10 Desktop and later"; preproduction signing). https://learn.microsoft.com/windows-hardware/drivers/dashboard/driver-signing-offerings
- Microsoft Learn: Device nodes and device stacks; Types of WDM drivers (bus, function, filter); Device tree. Windows driver kernel documentation.
- Microsoft Learn: INF file sections and directives (`[Version]`, `[Manufacturer]`, models sections with target-OS decorations, `AddService`, `DestinationDirs` / DIRID 13, `PnpLockdown`, KMDF `.Wdf` section); How Windows ranks drivers; PnPUtil command syntax.
- Microsoft Learn: Device Manager error codes (10, 28, 31, 39, 43, 52).
- *Windows Internals, 7th ed., Part 1*: the I/O system, PnP, and driver loading.

The INF is a teaching example built from the documented sections and the WDK template conventions. `ACPI\TGS0001` and the names are made up. Validate any real INF with the WDK's InfVerif tool.
