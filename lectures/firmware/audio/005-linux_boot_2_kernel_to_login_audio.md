# The Linux Boot Sequence, Part 2: From the Kernel to the Login Prompt (audio lecture)

This is part two of a two-part series on how a Linux machine boots. Part one followed the chain from power-on, through firmware and the bootloader, to the moment the kernel starts. This part follows what happens next: the kernel bringing itself up, the initial RAM file system finding the real root file system, and systemd starting everything else, until a login prompt appears.

## Why this episode exists

When the bootloader jumps into the kernel, the machine has a memory map, a hardware description, and a command line, and nothing else. No drivers for most devices are loaded, no disks are mounted, and no programs are running. Within a few seconds there's a full system with networking, a desktop or a login prompt, and dozens of services. Timothy wants to understand how that happens: which component starts which, in what order, and how drivers end up loaded for hardware the kernel just discovered. This is also where he can watch it all himself, on his own Raspberry Pi, with a few commands.

## The core ideas

Here are the core ideas for this episode. They're the answer key for the walk questions at the end.

One. The kernel first initializes itself: memory management, interrupts, timers, the scheduler. Then it runs the initialization functions of drivers built into it.

Two. The kernel creates the first user-space process, process I-D one, by running a program called init. Everything else in user space descends from it.

Three. Before the real root file system can be mounted, the kernel often needs drivers or steps that live on that very file system. The initial RAM file system, initramfs, breaks that chicken-and-egg problem: it's a small file system loaded into memory by the bootloader, containing just enough to find and mount the real root.

Four. The initramfs finds the real root, mounts it, and switches to it, replacing itself with the real init program while keeping process I-D one.

Five. On most distributions the real init is systemd. It reads unit files, builds a dependency graph, and starts services in parallel, aiming at a goal state called a target.

Six. Drivers for hardware found during boot are loaded through a pipeline: the kernel announces each device as an event, the udev service matches the device's identity to a driver module, and the module is loaded. Udev also sets up the device's entry in slash dev.

Seven. You can see every stage afterwards: the kernel's log with dmesg, the whole boot's log with journalctl, and timing with systemd-analyze.

## Section one: the kernel wakes up

The bootloader loaded a compressed kernel image; on PCs the file is usually called vmlinuz, and the Z hints at compression. The first code that runs is a small decompressor, which unpacks the real kernel in memory and jumps to it. Then architecture-specific setup code builds the kernel's own page tables, which turns on virtual memory the way the kernel will use it, and sets up a stack. Then it calls the kernel's central start-up function, which is named start underscore kernel.

That function brings the core of the kernel to life, roughly in this order. It records the command line. It initializes memory management using the memory map from the firmware. It sets up interrupt handling and the interrupt controller, the timers, and the scheduler. It starts the console, so messages can be printed. Most of the first lines you see scroll past at boot come from this phase. At this point the kernel can run code, handle interrupts, and allocate memory, but it has no user programs and very few device drivers active.

Next come the initialization functions of everything compiled into the kernel, called initcalls. They run in ordered levels: core subsystems first, then buses, then device drivers, and so on. A driver built into the kernel registers itself with its bus here. Then, when the kernel walks the hardware description, which is the device tree on the Pi or the A-C-P-I tables on a PC, and finds a device whose identity matches, it calls that driver's probe function, which sets up the device. That match between a description and a driver is the same idea as Windows matching hardware identifiers to INF files, done inside the kernel.

Pause here and predict. A driver is built into the kernel, but its device's entry is missing from the device tree. Does the driver's probe function run?

No. The driver registers, but nothing in the hardware description matches it, so the kernel never calls its probe function. The driver sits there unused, and the device never appears. This is one of the most common reasons a device doesn't show up on a new Arm board.

## Section two: the first process

Once the core is up, the kernel creates two special tasks. One becomes process I-D two, called kthreadd, said "k-thread-d", the parent of all the kernel's own background threads. The other becomes process I-D one: it finishes the remaining initialization in the kernel, then executes a user-space program and becomes that program. That program is init.

Process I-D one is special in several ways. Every other user-space process descends from it. When a process's parent dies, the orphan is adopted by init. And if process I-D one ever exits, the kernel panics, because the system has lost its root.

Which program is init? The kernel follows the command line if it says init equals something. Otherwise it tries a short list of standard locations. But before it gets there, there's usually one more stage: the initial RAM file system.

## Section three: the initial RAM file system

Here's the problem it solves. The kernel needs to mount the real root file system, the disk partition holding the operating system. But reaching that disk may require things the kernel doesn't have built in. The storage controller's driver might be a separate module. The disk might be encrypted, so someone has to ask for the passphrase. The root might sit on a logical volume or a software RAID array that has to be assembled first. And all of those tools live, normally, on the root file system itself. You can't read the disk to get the tools that let you read the disk.

The solution is the initramfs. The bootloader loaded it into memory next to the kernel. It's an archive in a simple format called cpio, usually compressed. Early on, the kernel unpacks it into a temporary in-memory file system and runs its slash init program. That program, depending on the distribution, is either a set of scripts or a small copy of systemd, assembled by tools named dracut or initramfs-tools.

The initramfs then does just enough to reach the real root. It starts a small copy of udev, which loads drivers for the hardware the kernel found. It loads the storage modules. It asks for a decryption passphrase if the disk is encrypted. It assembles logical volumes or RAID arrays if they're used. Then it waits for the device named by the root setting on the command line to appear, and mounts it.

The final step is the handoff. The initramfs switches root: the real root file system becomes slash, the temporary in-memory one is emptied to free its memory, and the program running as process I-D one replaces itself, in place, with the real init on the real root, usually slash sbin slash init, which is systemd. The process I-D stays one throughout. Process I-D one has changed programs, but it never stopped existing.

Not every system needs an initramfs. When the kernel has the storage driver built in and the root is a plain partition, the kernel can mount root directly and run init. Many embedded boards boot that way. Recent Raspberry Pi OS releases do load an initramfs by default, controlled by a line in config dot T-X-T called auto initramfs, so on Timothy's Pi it's worth checking which way his boots. The rule is the same either way: the initramfs is only needed when reaching root needs more than the kernel already has.

## Section four: systemd takes over

Systemd is now process I-D one, running from the real root. Its job is to bring the system to a goal state, and it does that by reading unit files. A unit file is a small text configuration file describing one thing systemd manages. A service unit describes a program to run, such as the S-S-H server. A mount unit describes a file system to mount, and systemd generates these automatically from slash etc slash fstab. A socket unit describes a socket that systemd listens on, starting its service only when someone connects. And a target unit is a named group, a milestone.

The goal is a target called default dot target, which is usually linked to either multi-user dot target, meaning a full text-mode system with networking, or graphical dot target, which adds a desktop. Each unit declares its relationships: which units it wants, which it requires, and which it must start after. Systemd builds those relationships into a dependency graph, and then starts everything that has no unmet dependencies at the same time, in parallel. That's why modern Linux boots quickly: services that don't depend on each other don't wait for each other.

Along the way there are milestone targets. Sysinit dot target covers early system setup: mounting the local file systems, starting udev, setting the hostname and the clock. Basic dot target means basic system services are ready. Then the network, the system's services, and finally the getty service, which shows a login prompt on a terminal, or a display manager, which shows a graphical login.

Timothy has already written one of these. In earlier work he set up a dot-NET service on a Pi to run under systemd, configured by a unit file with lines saying what program to run and which target wants it. That's exactly this mechanism: his unit was one node in the dependency graph, started by systemd when its target was being reached.

## Section five: how drivers get loaded for discovered hardware

One question remains: if most drivers are separate modules, how does the right module get loaded for each device? This is a pipeline with four actors, and it's worth knowing step by step.

Step one: the kernel discovers a device. It might be from the device tree, from A-C-P-I, from a P-C-I scan, or from a U-S-B device being plugged in. The kernel creates an entry for it in its internal device model, which appears as a directory under slash sys.

Step two: the kernel announces the device by sending an event to user space, called a uevent. The event includes the device's identity, encoded as a string called its modalias, built from things like the vendor and product numbers, or the compatible string from the device tree.

Step three: udev, the device manager, running as the systemd-udevd service, receives the event. It looks up the modalias in a table built from every installed driver module. Each module declares which device identities it supports, and a tool called depmod builds those declarations into an index. If a module matches, udev loads it, using the same module-loading library that the modprobe command uses.

Step four: the module loads, registers its driver with the bus, the kernel matches it to the waiting device, and the driver's probe function runs. Udev also applies its rules: setting permissions on the device's node in slash dev, which the kernel created in a special file system called devtmpfs, and creating friendly symbolic links, such as stable names for disks.

Here's the Windows parallel, because it's nearly one-to-one. The modalias plays the role of the hardware identifier. The module index plays the role of the INF files in the driver store. Udev plays the role of the Plug and Play manager's matching and loading. And the probe function plays the role of the add-device and start steps.

Pause and predict. A U-S-B serial adapter works when plugged in after boot, but its slash dev entry has the wrong permissions, so your program can't open it without root. Which actor do you adjust?

Udev. A udev rule that matches the adapter's identity can set the permissions, or the group, on its device node, or create a stable symbolic link to it.

## Section six: watching it yourself

Every stage leaves a record, and you can read all of it on the Pi.

The command dmesg prints the kernel's own log, the ring buffer of kernel messages, from the first line after start-up: the command line, memory, each driver's probe, each device it found. On a systemd machine, journalctl dash b shows the whole boot's log, kernel messages and every service's messages, interleaved in time order. And journalctl dash k, with a lowercase k, shows just the kernel's messages for this boot.

For timing, systemd-analyze prints how long the firmware, the loader, the kernel and user space each took. Systemd-analyze blame lists services by how long each took to start. Systemd-analyze critical-chain shows the chain of dependencies that actually decided when the system was ready, which is the path to shorten if you want a faster boot.

For the kernel command line, the file slash proc slash cmdline shows exactly what the kernel received. For drivers, lsmod lists loaded modules, and udevadm monitor shows udev events live: plug in a U-S-B device while it runs, and you'll watch step two and step three of the driver pipeline happen.

## Connections

This connects back to part one: the command line that part one's loader built is the very first thing start-kernel records, and the root setting on it is what the initramfs waits for. It connects to the Windows lectures: the driver pipeline is Linux's version of Plug and Play matching, and the kernel's probe function corresponds to adding and starting a device. And it connects to Timothy's Pi: his systemd service, his gadget-mode modules on the command line, and the device tree overlays from config dot T-X-T all take effect at exactly the points described in these two episodes.

## Recap

The core ideas again, in different words. The kernel decompresses itself, sets up memory, interrupts, timers and the scheduler, and runs the built-in drivers' initcalls, matching them to devices from the hardware description. It creates process I-D one, which becomes init. When reaching the root needs extra drivers or steps, an initramfs loaded by the bootloader provides them, finds and mounts the real root, and switches to it, with process I-D one carrying over to the real init. Systemd reads unit files, builds a dependency graph, and starts units in parallel toward default dot target, through milestones like sysinit and basic, ending in a login prompt. Drivers for discovered hardware load through the uevent, modalias, udev and modprobe pipeline. And dmesg, journalctl and systemd-analyze let you see every stage afterwards.

## Walk questions

Three questions to answer out loud on the next walk.

First: what chicken-and-egg problem does the initramfs solve, and what does switching root do to process I-D one?

Second: describe the four-step pipeline that loads a driver module for a newly discovered device, and give the Windows equivalent of each step.

Third: you want a faster boot on your Pi. Which command shows you where the time actually goes, and why is critical-chain more useful than blame?
