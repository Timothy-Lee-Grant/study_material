2026_10_21_23_40-(Power-Management-And-Modern-Standby)

# Lecture 007 — Power Management: D-States, Sleep, Modern Standby (S0ix), and Resume Bugs

> **For:** Timothy · **Date:** 2026-10-21
> **Prerequisites:** 006 (device stacks, IRPs, PnP start). Debugging tie-ins: 002 §3 (0x9F), 003 §7 (dead device), 004 (ETW).
> **Why this lecture:** sleep, standby and resume are where new laptops break most visibly: they don't wake, a device is dead after waking, the battery drains in the bag, or the machine blue-screens with 0x9F during resume. Modern Standby makes this matter more on Arm laptops, which don't have classic S3 sleep at all. This lecture covers the two sets of power states (system and device), who moves a device between them and how, and a catalog of resume bugs with the evidence for each.

---

## Core ideas (the answer key)

1. **Two separate sets of states.** **System** power states (S0 working, S3 sleep, S4 hibernate, S5 off) describe the whole machine. **Device** power states (D0 fully on … D3 off) describe one device. The system can be in S0 while a device is in D3 (runtime idle).
2. **Modern Standby is S0 low-power idle:** the machine *stays in S0*, the screen is off, devices go to low-power D-states, and the SoC drops into its deepest idle state, called DRIPS, between short bursts of allowed activity. It replaces S3 on machines that support it; you can't switch between the two models with a setting. Arm Windows laptops use Modern Standby.
3. **Power transitions are IRPs sent down device stacks.** The power manager sends a system power IRP; each stack's **power policy owner** (usually the FDO) decides the matching D-state and requests a device power IRP; each layer handles it, and the bus driver (PDO) actually cuts or restores power.
4. **Drivers implement power in KMDF callbacks:** `EvtDeviceD0Exit` (save state, quiet the device before power-down) and `EvtDeviceD0Entry` (restore state and re-initialize after power-up). Most resume bugs are a wrong or missing step in one of these two.
5. **D3cold loses everything.** In D3hot the device keeps power and its registers. In D3cold its power is removed, so on return it's a freshly reset chip: the driver must fully re-initialize it (configuration, interrupt enable, any reset handshake).
6. **Runtime idle** (S0-idle power-down) turns a device off while the system is running, and wakes it on demand. It's great for the battery, and it's the classic cause of "device dies after being left idle".
7. **Resume bugs fall into a few classes**, each with its evidence: a blocked power IRP (0x9F, the parameters point to the IRP); dead after resume (D0Entry didn't fully re-initialize, or the hardware didn't come back); never reaching DRIPS (battery drain: an activator or a device stuck in D0); spurious or missing wake. Tools: `powercfg /sleepstudy`, `/a`, `/requests`, `/lastwake`, ETW traces of the transition, and `!poaction` / `!irp` in dumps.

---

## Table of Contents

- [1. System power states](#1-system-power-states)
- [2. Modern Standby (S0 low-power idle)](#2-modern-standby-s0-low-power-idle)
- [3. Device power states](#3-device-power-states)
- [4. Who decides, and how: power IRPs and the policy owner](#4-who-decides-and-how-power-irps-and-the-policy-owner)
- [5. Power in a KMDF driver](#5-power-in-a-kmdf-driver)
- [6. Runtime idle and wake](#6-runtime-idle-and-wake)
- [7. Resume and standby bugs: a catalog](#7-resume-and-standby-bugs-a-catalog)
- [8. Tools](#8-tools)
- [9. The touchscreen through a standby cycle](#9-the-touchscreen-through-a-standby-cycle)
- [10. Misconceptions](#10-misconceptions)
- [11. Saying it precisely](#11-saying-it-precisely)
- [12. Self-check](#12-self-check)
- [Sources](#sources)

---

## 1. System power states 🟢

| State | Name | What's powered | Resume |
|---|---|---|---|
| **S0** | Working | Everything as needed | — |
| S1, S2 | Light sleep (rare today) | — | — |
| **S3** | Sleep (suspend to RAM) | RAM kept in self-refresh; CPU and most devices off | Seconds; firmware runs a resume path, then Windows restores devices |
| **S4** | Hibernate | Nothing; memory image saved to disk | Like a boot that restores the image |
| **S5** | Soft off | Nothing (except wake circuitry) | Full boot |
| **S0 low-power idle** | **Modern Standby** | See §2 | Sub-second; it never left S0 |

`powercfg /a` lists which states a given machine supports. On a Modern Standby machine it reports "Standby (S0 Low Power Idle)" and lists S3 as unavailable.

---

## 2. Modern Standby (S0 low-power idle) 🟢

### 2.1 What it is

Microsoft describes Modern Standby (which grew out of Windows 8's Connected Standby) as enabling an "instant on / instant off user experience, similar to smartphone power models", where "the system [can] stay connected to the network while in a low power mode."

Mechanically, the machine **never leaves S0**. Instead:
1. The screen turns off: a **Modern Standby session** begins (Microsoft: it "encompasses the entire screen-off to screen-on user scenario").
2. Windows throttles software. Apps are suspended, and only allowed background work runs, "in short, controlled bursts of activity".
3. Devices move to low-power D-states (most to D3).
4. When software is quiet and every device on and off the SoC is in a low-power state, the SoC enters its deepest runtime idle state, **DRIPS** (Deepest Runtime Idle Platform State). DRIPS is where the battery savings come from.
5. A wake event (power button, lid, network packet that matches a pattern, timer) brings the screen back. Microsoft's target is power button to display-on in "less than one second".

### 2.2 Activators and the SoC power engine 🔵

- **Activators** are Windows components "allowed to leave the SoC in the active power state… registered with the power manager as capable of blocking the transition back to the idle power mode." If one stays active, the SoC can't reach DRIPS.
- The **PEP** (Power Engine Plug-in) is SoC-vendor software that translates Windows' idle and device-power decisions into the SoC's actual power rails and clocks. On Arm laptops, the SoC vendor's PEP and firmware are a large part of whether standby works.

### 2.3 Why it's harder than S3, especially on Arm laptops 🟢

| S3 | Modern Standby |
|---|---|
| Everything stops; firmware does much of the save/restore | The OS stays running; every driver must correctly move its device between D-states **while the system is live** |
| One big transition | Many independent device transitions, repeated, often in parallel with background activity |
| A device that doesn't sleep properly wastes a little power for a few seconds | A device stuck in D0 keeps the SoC out of DRIPS **for the whole night**, draining the battery |

Arm Windows laptops are Modern Standby machines (no S3), and their device power often goes through the SoC vendor's PEP and power rails. So driver D-state handling, PEP behavior and firmware power methods are all on the critical path, and resume and standby bugs are a central part of bring-up there.

---

## 3. Device power states 🟢

| State | Device power | Context (registers, configuration) | Return latency |
|---|---|---|---|
| **D0** | Fully on | Kept | — |
| D1, D2 | Intermediate (device-class specific, often unused) | Usually kept | Short |
| **D3hot** | Low power, but still powered (the bus can still see it) | Usually **kept** | Short |
| **D3cold** | **Power removed** | **Lost**: the device is like freshly powered | Longer; needs full re-initialization |

"D3" in logs and IRPs means D3 in general. Whether it ends up hot or cold depends on the platform and the bus: whether the parent can actually cut power, which on ACPI platforms is controlled by the device's ACPI power methods and resources.

**What each symbol means in practice:** D-numbers go *up* as power goes *down*. Moving "into D0" means powering up; "D0Exit" means leaving full power.

---

## 4. Who decides, and how: power IRPs and the policy owner 🔵

The step-by-step flow for a system sleep (or a Modern Standby device power-down, which is similar but per device):

1. The **power manager** decides the system is going to sleep and sends a **system power IRP** (`IRP_MN_SET_POWER`, type SystemPowerState) to each device stack.
2. In each stack, one driver is the **power policy owner**, by default the function driver (FDO). It maps the system state to a device state. That mapping comes from the bus driver's **capabilities**: for each S-state, the deepest D-state the device can be in.
3. The policy owner **requests a device power IRP** (`PoRequestPowerIrp`, `IRP_MN_SET_POWER` with DevicePowerState, e.g. D3) for its own stack.
4. The device power IRP travels down the stack. Each layer prepares for power-down (stops I/O, saves context) and passes it on. At the bottom, the **bus driver (PDO)** actually changes the power: for ACPI devices, by running the device's ACPI power methods.
5. On resume, the mirror image: device power IRPs to **D0** go down; the bus driver restores power first; then each layer above re-initializes on the way back up.

**The rule that creates 0x9F:** every layer must complete or pass on the power IRP within a time limit. A driver that pends a power IRP and never finishes it, for example because it's waiting for a device that will never answer, trips the power manager's watchdog → 0x9F P1 = 3, with P4 = the IRP (002 §3).

**Who owns what**, so you know where to look:

| Responsibility | Owner |
|---|---|
| When to change state, and to which D-state | Power policy owner (usually the FDO / function driver) |
| Saving and restoring the device's own configuration | Function driver |
| Actually cutting or restoring power | Bus driver / PDO (with ACPI firmware methods, PEP on SoCs) |
| Whether a deeper state is even possible | Platform: ACPI tables, firmware, SoC power engine |

---

## 5. Power in a KMDF driver 🟢

KMDF is the power policy owner by default and handles the IRP mechanics. It calls the driver back at the right moments:

| Callback | When | What a correct driver does |
|---|---|---|
| `EvtDevicePrepareHardware` | At start (once) | Map registers, open the I2C target, read static configuration |
| `EvtDeviceD0Entry(Device, PreviousState)` | **Every** entry to D0: at start, and after every power-down | Bring the device fully up from `PreviousState`. **If it was D3cold, assume everything was reset**: re-send configuration, re-enable the device's interrupt output, run any power-on handshake |
| `EvtDeviceD0EntryPostInterruptsEnabled` | After interrupts are connected | Work that needs interrupts on |
| `EvtDeviceD0ExitPreInterruptsDisabled` | Before interrupts are disconnected | Quiesce work that relies on interrupts |
| `EvtDeviceD0Exit(Device, TargetState)` | Every exit from D0 | Stop device activity, save any state needed, put the device into its low-power mode (e.g. send a "sleep" command) |
| `EvtDeviceReleaseHardware` | At stop/remove | Unmap, close |

The framework disconnects the interrupt before D0Exit completes and reconnects it during D0Entry. So the order on power-down is: quiesce, then disconnect the interrupt, then D0Exit. On power-up it's D0Entry, then reconnect the interrupt.

**Pause and predict:** a touch driver sends its device configuration (report rate, enable bits) only in `EvtDevicePrepareHardware`. It works perfectly until the laptop's first Modern Standby cycle, then touch is dead until reboot. Why?

<details><summary>Answer</summary>PrepareHardware runs once at start, while D0Entry runs on every power-up. During standby the device went to D3cold, lost its configuration, and came back in its reset defaults (for example, reporting disabled). The configuration must be re-sent in <code>EvtDeviceD0Entry</code>, at least when <code>PreviousState</code> is D3 (cold).</details>

---

## 6. Runtime idle and wake 🔵

### 6.1 Runtime idle (S0 idle)

A driver can let its device power down **while the system stays in S0** when it's not being used:
- In KMDF: `WdfDeviceAssignS0IdleSettings` with an idle timeout. The framework powers the device down (D0Exit → D3) after the timeout, and back up (D0Entry) when I/O arrives or the driver asks for power.
- The driver must be able to **wake** for the device's own events: a touch must power it back up. For an input device that usually means the device stays able to raise its interrupt (as a wake signal) while in the low-power state.

This is exactly the "fails after being left idle" hypothesis from the touchscreen case study: the idle power-down works, but the way back up doesn't. The causes are a lost configuration, a wake interrupt that isn't armed, or a GPIO pin configuration that wasn't restored.

### 6.2 Wake

- **System wake** sources: power button, lid, keyboard, network patterns, timers, and devices armed for wake.
- A device can wake the system only if it's **armed**: the driver arms wake (KMDF: `EvtDeviceArmWakeFromSx` / `FromS0`), the hardware can signal it, and the platform routes that signal (the ACPI GPIO resource marked wake-capable; the hardware guidelines for touch say the interrupt line "should be capable of (and configured for) waking the SoC").
- `powercfg /lastwake` shows what woke the machine last; `powercfg /devicequery wake_armed` lists armed devices.

---

## 7. Resume and standby bugs: a catalog 🟢

| Class | Symptom | Likely layers | Evidence |
|---|---|---|---|
| **Blocked power IRP** | 0x9F during sleep/resume (or a hang during resume) | The driver holding the IRP; or hardware it's waiting on | Dump: P4 → `!irp` → `!devstack` → `!wdfkd.wdflogdump`, `!poaction` (002 §3) |
| **Dead after resume** | Machine wakes; one device doesn't work until a reboot or disable/enable | `D0Entry` didn't re-initialize (D3cold context loss); the device needs a reset handshake; the GPIO or interrupt configuration wasn't restored; the power rail didn't come back | Live dump; the driver's IFR log; ETW of the resume (D-state transitions, interrupts); a logic analyzer on power, reset and interrupt lines (003 §7) |
| **Dead after idle** | Device stops after sitting unused, while the system is awake | Runtime idle path (§6.1) | Same as above, plus: does disabling idle power-down make it go away? |
| **Battery drain in standby** | Battery drops much faster than expected overnight | An activator keeps the SoC active, or a device stays in D0, so DRIPS isn't reached | `powercfg /sleepstudy` report: DRIPS percentage, top offenders per session |
| **Spurious wake** | Laptop wakes in the bag | A device or timer wake source | `powercfg /lastwake`, `/waketimers`, `/devicequery wake_armed`; the event log (Power-Troubleshooter) |
| **Won't wake** | Pressing keys or the lid does nothing; the power button works (or not) | Wake not armed; the platform didn't route the wake GPIO; firmware | Wake arming, ACPI wake configuration, PEP/firmware logs |
| **Slow resume** | Seconds before the screen or devices respond | A driver doing slow work in D0Entry, serial device bring-up | ETW boot/resume trace: per-device D0 transition durations |

---

## 8. Tools 🟢

| Tool | Gives you |
|---|---|
| `powercfg /a` | Which sleep states this machine supports (S3 vs S0 low-power idle) |
| `powercfg /sleepstudy` | An HTML report of recent Modern Standby sessions: duration, % time in DRIPS, energy drained, and the top activators and devices that kept the system awake |
| `powercfg /requests` | What's currently preventing sleep or display-off (apps, drivers) |
| `powercfg /lastwake`, `/waketimers`, `/devicequery wake_armed` | Wake causes and sources |
| `powercfg /energy` | A short trace-based report of power-efficiency problems |
| WPR trace across a standby/resume cycle (the built-in power-related profile; check `wpr -profiles`), opened in WPA | The timeline of device power transitions, the durations of each D0 entry, interrupts and DPCs during resume |
| Dumps: `!poaction`, `!irp`, `!devstack`, `!wdfkd.wdflogdump` | The state of an in-progress power transition, and the stuck IRP |
| Event Viewer: System log (Kernel-Power, Power-Troubleshooter) | Sleep and wake times, wake sources, failed transitions |

---

## 9. The touchscreen through a standby cycle 🟢

Putting it together as one trace:

**Entering standby:**
1. Screen off; a Modern Standby session starts.
2. The power manager tells the touch device stack to power down. KMDF (the policy owner in the hidclass/hidi2c stack) calls `D0ExitPreInterruptsDisabled`, disconnects the interrupt, then calls `D0Exit`. The driver sends the HID-over-I2C "sleep" power command over I2C.
3. The device power IRP reaches the PDO (ACPI). ACPI runs the device's power-off method, which may cut the touch controller's rail → **D3cold**.
4. All other devices do the same; the SoC's PEP takes the platform into DRIPS.

**Resuming** (or a wake from a touch, if armed):
1. The device power IRP to D0 goes down; ACPI's power-on method restores the rail first.
2. On the way back up, KMDF calls `D0Entry(PreviousState = D3)`. The driver must:
   - treat the controller as **freshly powered**, and wait for it to be ready if the hardware specification requires a delay;
   - send the HID-over-I2C "on" power command (and a reset, if the device needs one);
   - re-send any configuration.
3. KMDF reconnects the interrupt (the GPIO pin's configuration is restored by the GPIO controller's own D0 path).
4. The first touch → interrupt → passive-level ISR → I2C read → report.

**Every step is a failure point, matched to evidence:**

| Failure | Evidence |
|---|---|
| Rail not restored | The controller doesn't ACK on I2C (logic analyzer; I2C errors in the trace) |
| D0Entry doesn't re-send configuration | The device ACKs but never asserts its interrupt |
| GPIO controller didn't restore the pin's interrupt configuration | The line asserts but no ISR runs |
| The driver pends the D0 IRP waiting on the device | 0x9F P1 = 3 with the IRP at hidi2c |

---

## 10. Misconceptions

| You might think | Reality | Why it matters |
|---|---|---|
| Sleep = S3 everywhere | Modern Standby machines (including Arm laptops) stay in S0 low-power idle and have no S3 | Different bugs: device D-state handling is continuous |
| System state and device state move together | Devices go to D3 while the system is in S0 (runtime idle and Modern Standby) | "Dies after idle" without any system sleep |
| D3 always keeps device state | D3hot usually keeps it; **D3cold** loses it | D0Entry must re-initialize after cold |
| The OS cuts device power directly | The bus driver / PDO does, through ACPI methods and the SoC's PEP | Power-rail bugs are platform/firmware, not the function driver |
| 0x9F means Windows' power code is broken | A driver held a power IRP (often waiting on hardware) | Follow P4 to the holder |
| Battery drain in standby is "the OS being busy" | Usually one activator or one device kept the SoC out of DRIPS | `powercfg /sleepstudy` names it |

---

## 11. Saying it precisely

- "System states describe the machine; D-states describe one device. Modern Standby keeps the system in S0 and moves devices to D3 so the SoC can reach DRIPS. Arm Windows laptops use only that model."
- "Power transitions are IRPs: the FDO, as power policy owner, requests device power IRPs for its stack, and the PDO actually changes the power through ACPI and the SoC's power engine."
- "In KMDF, D0Exit quiets and saves, and D0Entry restores. After D3cold the device is freshly reset, so D0Entry has to fully re-initialize it. That missing step is the most common 'dead after resume' bug."
- "For battery drain, I start with `powercfg /sleepstudy` to see DRIPS residency and top offenders. For 0x9F, I follow P4 to the blocked IRP and its holder."

---

## 12. Self-check

1. Name the system states S0, S3, S4, S5 and Modern Standby, and what's powered in each.
<details><summary>Answer</summary>S0: working, everything as needed. S3: RAM in self-refresh, most else off. S4: hibernate, image on disk, nothing powered. S5: soft off. Modern Standby: still S0, screen off, devices in low-power D-states, SoC in DRIPS between bursts.</details>

2. What is DRIPS, and what prevents reaching it?
<details><summary>Answer</summary>The Deepest Runtime Idle Platform State, the SoC's lowest idle state during Modern Standby. An activator staying active, or a device staying in D0, prevents it.</details>

3. Difference between D3hot and D3cold, and the consequence for drivers?
<details><summary>Answer</summary>D3hot keeps power (context usually kept); D3cold removes power (context lost). After D3cold, D0Entry must fully re-initialize the device.</details>

4. Who is the power policy owner, and what does it do?
<details><summary>Answer</summary>Usually the FDO (function driver; KMDF by default). It decides the D-state for each system state, or for idle, and requests the device power IRPs.</details>

5. Who actually cuts or restores a device's power?
<details><summary>Answer</summary>The bus driver / PDO, using the platform: ACPI power methods and resources, and the SoC's PEP.</details>

6. Which KMDF callback runs on every power-up, and why is that the right place for configuration?
<details><summary>Answer</summary>EvtDeviceD0Entry. Configuration may have been lost in D3cold, and PrepareHardware runs only once at start.</details>

7. Explain how runtime idle can cause "dies after being left alone".
<details><summary>Answer</summary>The framework powers the device down after an idle timeout. If the return path fails (configuration not restored, wake interrupt not armed, GPIO configuration not restored, rail not back), the device stays dead while the system is fine.</details>

8. 0x9F P1 = 3 during resume, and the IRP is a SET_POWER to D0 held in hidi2c. Two possible root causes at different layers?
<details><summary>Answer</summary>Driver: hidi2c waiting on a device that doesn't respond yet (no ready delay, no reset handling). Platform: the ACPI power-on method or rail didn't actually power the controller, so I2C commands never complete.</details>

9. Which tool shows why a laptop drained its battery overnight, and what do you look for?
<details><summary>Answer</summary><code>powercfg /sleepstudy</code>: the DRIPS percentage per standby session and the top offending activators or devices.</details>

10. Why are resume bugs especially prominent on Arm Windows laptops?
<details><summary>Answer</summary>They use only Modern Standby (no S3), so every driver must handle repeated live D-state transitions, and device power depends on the SoC vendor's PEP and firmware. Many layers are on the critical path, repeatedly.</details>

---

## Sources

Checked 2026-10-21.

- Microsoft Learn: Modern Standby (S0 low-power idle; "instant on / instant off"; activity bursts; activators "capable of blocking the transition back to the idle power mode"; the session definition; resume under one second; switching between S3 and Modern Standby requires a reinstall; SleepStudy). https://learn.microsoft.com/windows-hardware/design/device-experiences/modern-standby
- Microsoft Learn: Touchscreen device bus connectivity (the interrupt line "should be capable of (and configured for) waking the SoC"). https://learn.microsoft.com/windows-hardware/design/component-guidelines/touchscreen-device-bus-connectivity
- Microsoft Learn: Bug Check 0x9F (parameters and recipe). https://learn.microsoft.com/windows-hardware/drivers/debugger/bug-check-0x9f--driver-power-state-failure
- Microsoft Learn: Device power states (D0–D3, D3hot/D3cold); System power states; Power IRPs and the power policy owner; KMDF power-up/power-down sequences and callbacks (`EvtDeviceD0Entry`, `EvtDeviceD0Exit`, idle settings, wake arming).
- Microsoft Learn: powercfg command-line options.

DRIPS and PEP aren't defined on the Modern Standby overview page itself. They come from Microsoft's Modern Standby hardware-preparation and PEP documentation. Check the exact WPR power-profile name on your build with `wpr -profiles`.
