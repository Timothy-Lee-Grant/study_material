# Windows Internals, Part 7: Power Management, Modern Standby, and Resume Bugs (audio lecture)

This is part seven of an eight-part series on Windows internals. Part six covered device stacks. This part covers power: the system's sleep states, the device power states, Modern Standby, how Windows moves a device between power states, and the most common resume and standby bugs, with the evidence for each.

## Why this episode exists

Sleep, standby and resume are where new laptops break most visibly. The machine won't wake. One device is dead after waking. The battery drains overnight in a bag. Or the machine shows a blue screen during resume. Modern Standby makes this matter even more on Arm Windows laptops, which don't have the classic sleep state at all. Timothy wants to understand how power transitions actually work, so that when one fails, he knows which layer to suspect and what evidence to collect.

## The core ideas

Here are today's core ideas. They're the answer key for the walk questions at the end.

One. There are two separate sets of states. System power states, S-zero working through S-five off, describe the whole machine. Device power states, D-zero fully on through D-three off, describe one device. The system can be working while a device is off.

Two. Modern Standby is S-zero low-power idle. The machine stays in S-zero, the screen is off, devices go to low-power states, and the chip drops into its deepest idle state, called DRIPS, between short bursts of allowed activity. Arm Windows laptops use Modern Standby.

Three. Power transitions are requests sent down device stacks. Each stack's power policy owner, usually the function driver, decides the device's state and requests it. The bus driver at the bottom actually cuts or restores power.

Four. A driver handles power in two callbacks: D-zero-exit, to quiet and save before power-down, and D-zero-entry, to restore and re-initialize on every power-up.

Five. D-three-cold loses everything. In D-three-hot the device keeps power and its settings. In D-three-cold its power is removed, so when it comes back, it's a freshly reset chip, and the driver must fully re-initialize it.

Six. Resume bugs fall into a few classes: a stuck power request (blue screen nine-F), a device dead after resume or after idle, a machine that never reaches DRIPS and drains its battery, and wakes that happen when they shouldn't or don't happen when they should. Each has its own evidence and tools.

## Section one: system power states

S-zero is working: everything powered as needed. S-one and S-two are light sleep states that are rare today. S-three is classic sleep, suspend to RAM: memory is kept refreshed, while the processor and most devices are off, and resuming takes a few seconds. S-four is hibernate: memory is saved to disk and nothing is powered. S-five is soft off. And then there's S-zero low-power idle, which is Modern Standby. The command powercfg slash-A lists which states a machine supports. On a Modern Standby machine it reports standby as S-zero low power idle, and lists S-three as unavailable.

## Section two: Modern Standby

Microsoft describes Modern Standby as an instant-on, instant-off experience, similar to a smartphone, where the system can stay connected to the network while in a low-power mode. Mechanically, the machine never leaves S-zero. Here's the sequence.

First, the screen turns off, and a Modern Standby session begins. Microsoft defines the session as the whole span from screen-off to screen-on. Second, Windows throttles software: apps are suspended, and only allowed background work runs, in short, controlled bursts. Third, devices move to low-power states, most of them to D-three. Fourth, when software is quiet and every device on and off the chip is in a low-power state, the chip enters its deepest runtime idle state, DRIPS, which stands for deepest runtime idle platform state. That's where the battery savings come from. Fifth, a wake event, like the power button, opening the lid, a matching network packet, or a timer, brings the screen back. Microsoft's target from power button to display is under one second.

Two more terms. Activators are Windows components allowed to keep the chip active; if one stays active, the chip can't reach DRIPS. The power engine plug-in, P-E-P, is software from the chip vendor that translates Windows' power decisions into the chip's actual power rails and clocks. On Arm laptops, the P-E-P and firmware are a big part of whether standby works.

Why is Modern Standby harder than S-three? With S-three, everything stops in one big transition, and firmware handles much of the saving and restoring. With Modern Standby, the operating system keeps running, and every driver must move its device between power states correctly while the system is live, over and over. And the stakes are higher: a device that doesn't power down in S-three wastes a little power for a few seconds, but a device stuck on during Modern Standby keeps the chip out of DRIPS for the whole night.

## Section three: device power states

D-zero is fully on. D-one and D-two are intermediate states, often unused. D-three-hot is low power while still powered; the bus can still see the device, and it usually keeps its settings. D-three-cold means power is removed; the device's settings are lost, and coming back takes longer, with a full re-initialization. Logs often just say D-three; whether it ends up hot or cold depends on whether the platform can actually cut the device's power, which on A-C-P-I machines is controlled by the device's firmware power methods.

A note on direction: the numbers go up as power goes down. Moving into D-zero means powering up. D-zero-exit means leaving full power.

## Section four: who decides, and how

Here's the flow for a system going to sleep, step by step.

First, the power manager decides the system is going to sleep, and sends a system power request to each device stack.

Second, in each stack, one driver is the power policy owner, by default the function driver. It maps the system state to a device state, using the bus driver's reported capabilities, which say the deepest device state allowed for each system state.

Third, the policy owner requests a device power request for its own stack, for example to D-three.

Fourth, that request travels down the stack. Each layer stops its input-output, saves what it needs, and passes it on. At the bottom, the bus driver actually changes the power, for A-C-P-I devices by running the device's firmware power methods.

Fifth, on resume, the mirror image: a request to D-zero goes down, the bus driver restores power first, and on the way back up each layer re-initializes.

Every layer must finish or pass on a power request within a time limit. A driver that holds one forever, perhaps waiting for a device that never answers, trips the power manager's watchdog, and that's the blue screen nine-F with parameter one equal to three, where parameter four is the stuck request.

Here's who owns what. When to change state, and to which D-state: the power policy owner. Saving and restoring the device's own settings: the function driver. Actually cutting and restoring power: the bus driver, with the firmware and the chip's power engine. Whether a deeper state is even possible: the platform.

## Section five: power in a framework driver

In the Kernel-Mode Driver Framework, the framework is the policy owner by default and handles the request mechanics. It calls the driver back at the right moments. Prepare-hardware runs once at start: map registers, open the bus connection, read fixed configuration. D-zero-entry runs on every entry to full power: at start, and after every power-down, and it tells the driver which state the device is coming from. D-zero-exit runs on every exit from full power, and tells the driver which state it's going to. Release-hardware runs at stop or removal. The framework disconnects the interrupt before D-zero-exit and reconnects it after D-zero-entry.

A correct driver does this. In D-zero-exit: stop device activity, save what it needs, and put the device into its low-power mode, for example by sending a sleep command. In D-zero-entry: bring the device fully up, and if it's coming back from D-three-cold, assume everything was reset, so re-send its configuration, re-enable its interrupt output, and do any power-on handshake the hardware needs.

Pause and predict. A touch driver sends its device configuration, like report rate and enable bits, only in prepare-hardware. It works perfectly until the laptop's first Modern Standby cycle, and then touch is dead until reboot. Why?

Prepare-hardware runs once, at start. D-zero-entry runs on every power-up. During standby the device went to D-three-cold, lost its configuration, and came back with its reset defaults, maybe with reporting disabled. The configuration must be sent again in D-zero-entry.

## Section six: runtime idle and wake

A driver can let its device power down while the system stays in S-zero, whenever the device isn't being used. That's runtime idle. In the framework, the driver sets an idle timeout. After the timeout, the framework powers the device down through D-zero-exit, and powers it back up through D-zero-entry when input-output arrives or the driver asks. For an input device like a touchscreen, the device must still be able to signal while it's in low power, so that a touch brings it back.

This is exactly the "touchscreen fails after being left idle" scenario. The power-down works, but the way back up fails: the configuration was lost, the wake signal wasn't armed, the G-P-I-O pin's interrupt configuration wasn't restored, or the power rail didn't come back.

As for waking the whole system: a device can only wake the machine if it's armed. The driver arms wake, the hardware can signal it, and the platform routes the signal; for touchscreens, Microsoft's hardware guidance says the interrupt line should be capable of, and configured for, waking the chip. The command powercfg slash-lastwake shows what woke the machine last, and another powercfg option lists which devices are armed to wake it.

## Section seven: the bug catalog

Here are the classes, with the evidence for each.

A blocked power request shows up as blue screen nine-F during sleep or resume, or as a hang during resume. The suspects are the driver holding the request, or the hardware it's waiting for. The evidence is in the dump: follow parameter four to the request, see which layer holds it, list the stack, and read the framework's log for that driver.

Dead after resume means the machine wakes but one device doesn't work until reboot, or until it's disabled and re-enabled. The suspects are a D-zero-entry that didn't fully re-initialize after D-three-cold, a device that needs a reset handshake, an interrupt configuration that wasn't restored, or a power rail that didn't come back. The evidence is a live dump, the driver's log, a trace of the resume showing power transitions and interrupts, and a logic analyzer on the power, reset and interrupt lines.

Dead after idle is the same, but for runtime idle, with one extra test: if turning off the device's idle power-down makes the problem disappear, you've found the path.

Battery drain in standby means the battery drops much faster than it should overnight. Usually one activator kept the chip awake, or one device stayed on, so the chip never reached DRIPS. The tool is powercfg slash-sleepstudy, which produces a report of recent standby sessions, showing what percentage of each session was spent in DRIPS and the top offenders.

A spurious wake is a laptop that wakes up in a bag. The tools are powercfg's last-wake and wake-timers options, the list of armed devices, and the power troubleshooter entries in the event log.

Won't wake means the wake signal isn't armed, isn't routed by the platform, or the firmware isn't handling it. Slow resume means a driver doing slow work in D-zero-entry, or devices brought up one at a time; a trace of the resume shows each device's power-up duration.

## Section eight: the touchscreen through a standby cycle

Here's one full cycle, entering and leaving.

Entering standby: the screen turns off and a session starts. The power manager tells the touch device's stack to power down. The framework quiets the work that depends on interrupts, disconnects the interrupt, and calls D-zero-exit, where the driver sends the HID-over-I2C sleep command over the bus. The device power request reaches the A-C-P-I layer at the bottom, which runs the device's power-off method, possibly cutting the touch controller's power, so it's now in D-three-cold. Every other device does the same, and the chip's power engine takes the platform into DRIPS.

Resuming: a request to D-zero goes down the stack, and the A-C-P-I power-on method restores the controller's power first. On the way back up, the framework calls D-zero-entry, telling the driver the device was in D-three. The driver treats the controller as freshly powered, waits for it to be ready if the hardware requires a delay, sends the HID-over-I2C power-on command and a reset if needed, and re-sends its configuration. The framework reconnects the interrupt, and the G-P-I-O controller's own power-up path restores the pin's interrupt settings. The first touch then raises the interrupt, the passive-level routine reads the report, and touch is back.

Each step is a failure point with its own evidence. If the power wasn't restored, the controller won't acknowledge on the I2C bus. If the configuration wasn't re-sent, the controller acknowledges but never raises its interrupt. If the pin's interrupt settings weren't restored, the line goes active but no interrupt routine runs. And if the driver waits forever for the controller, you get nine-F with the request held by the touch driver.

## Connections

This connects to part two: nine-F is a power request held too long. It connects to part three: dead-after-resume uses the dead-device kit. It connects to part five: the interrupt is disconnected and reconnected around every power change. And it connects to part six: the bus driver at the bottom of the stack is the layer that actually switches power.

## Recap

The core ideas again, in different words. System states describe the machine, and device states describe one device. Modern Standby keeps the machine in S-zero and moves devices to D-three so the chip can reach DRIPS, and Arm Windows laptops rely on it. Power changes are requests: the function driver usually decides, and the bus driver switches the power. D-zero-exit saves and quiets, and D-zero-entry restores, fully, after D-three-cold. Runtime idle powers devices down while the system runs, and it's a classic source of "dies after idle". The bug classes each have their evidence: the stuck request for nine-F, live dumps and traces for dead devices, sleep study for battery drain, and last-wake for spurious wakes.

## Walk questions

Three questions for the next walk.

First: explain the difference between system and device power states, and how Modern Standby uses them.

Second: why must a touch driver re-send its configuration in D-zero-entry rather than prepare-hardware?

Third: a laptop drains its battery overnight in standby. What tool do you run, and what are you looking for in its report?
