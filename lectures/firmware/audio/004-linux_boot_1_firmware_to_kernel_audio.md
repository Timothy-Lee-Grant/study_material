# The Linux Boot Sequence, Part 1: From Power-On to the Kernel (audio lecture)

This is part one of a two-part series on how a Linux machine boots. Part one follows the chain from the moment power is applied, through firmware and the bootloader, to the moment the Linux kernel starts running. Part two follows the kernel itself, the initial RAM file system, and systemd, up to the login prompt.

## Why this episode exists

Timothy has been learning how an operating system sits on top of hardware: drivers, interrupts, firmware tables, device stacks. Booting is the one moment when you can watch all of those layers come into existence, one after another, each one building the next. It's also where a lot of real platform work happens: new hardware that won't boot, a kernel that can't find its disk, a driver that loads too late. And Timothy has a Raspberry Pi on his desk, which boots differently from a PC in an interesting way. By the end of this episode, he should be able to describe, step by step, who runs first, what each stage hands to the next, and where the Pi differs from a PC.

## The core ideas

Here are the core ideas for this episode. They're the answer key for the walk questions at the end.

One. Booting is a relay race. Each stage is a small program whose only job is to set up just enough of the machine to load and start the next, bigger stage, and to hand it a few pieces of information.

Two. On a PC, the first code to run is firmware stored in a flash chip on the motherboard. It's UEFI on modern machines. It initializes the processor, trains the memory, finds devices, and then chooses something to boot from a list stored in its settings.

Three. UEFI boots by loading a program file from a small FAT-formatted partition called the EFI System Partition. On Linux, that program is usually a small loader called shim, which loads the GRUB bootloader.

Four. The bootloader's job is to load two files into memory, the compressed kernel and the initial RAM file system, along with a text command line, and then jump into the kernel.

Five. Three things are handed to the kernel: a map of the machine's memory, a description of the hardware (ACPI tables on PCs, a device tree on most Arm boards), and the kernel command line.

Six. With Secure Boot on, each stage checks the signature of the next before running it, forming a chain of trust from the firmware to the kernel.

Seven. On a Raspberry Pi, the graphics processor boots first, not the Arm cores. A boot ROM and its firmware read a configuration file called config dot T-X-T, load the device tree and the kernel, and only then release the Arm cores to run the kernel.

## Section one: the relay race

Here's the one idea to carry through both episodes. At power-on, almost nothing works. The processor is running, but the main memory, the RAM, hasn't even been set up. The disk controller doesn't know there's a disk. There's no file system, no drivers, no operating system. The machine can't load a big program, because there's nowhere to put it and nothing to read it with.

So booting is staged. A tiny program that needs almost nothing sets up a little more of the machine, then loads a bigger program that can use what the first one set up. That one sets up more and loads the next. Each stage hands the next one a small bundle of facts: where the memory is, what hardware exists, what to do next. The first stages run from flash memory on the board, and the later ones are files on a disk. If you remember "each stage prepares the ground and passes the baton", the details fall into place.

## Section two: power-on, and the first instruction

When you press the power button on a PC, the power supply brings its voltages up and signals "power good". The processor comes out of reset, and every processor family defines exactly where it starts executing: a fixed address called the reset vector. The chipset maps that address onto the flash chip on the motherboard that holds the firmware. So the very first instruction comes from that flash chip.

On a modern PC, that firmware is UEFI, the Unified Extensible Firmware Interface, said "you-eff-ee". It's itself a staged system. The earliest part runs with almost no resources. On Intel-style machines, it even uses the processor's cache as temporary memory, because the RAM isn't working yet. Its biggest early job is memory initialization, often called memory training: the memory controller has to measure and tune the timing of the signals to the specific RAM chips installed. Only after that does the machine have usable main memory.

Then the firmware loads its own drivers for the platform's devices: storage controllers, U-S-B, graphics, network. It builds tables describing the hardware for whatever operating system comes next. On PCs these are the A-C-P-I tables, which Timothy met in earlier lectures as the place where a touchscreen's I2C address and interrupt pin are described. And the firmware offers boot-time services that a loader can call: read a disk, allocate memory, draw text on the screen.

Pause here and predict. Why can't the very first firmware code simply load the operating system from the disk?

Because nothing it would need exists yet. RAM hasn't been trained, so there's nowhere to put a large program, and the storage controller hasn't been initialized, so the disk can't be read. The firmware has to build up those capabilities first. That's the relay idea in its purest form.

## Section three: choosing what to boot

UEFI keeps its settings in non-volatile variables stored in flash. One of them, called Boot Order, is a list of boot entries, and each entry says something like "load this file from this partition on this disk". Operating system installers add an entry for themselves; the firmware's setup screen lets you reorder them, or pick one once from a boot menu.

The file it loads lives on the EFI System Partition. That's a small partition, typically a few hundred megabytes, formatted with the FAT file system, because every UEFI firmware knows how to read FAT. The files on it are EFI applications: programs in the same P-E executable format that Windows uses, but meant to run inside the firmware's environment. If no boot entry works, the firmware falls back to a standard path, EFI backslash BOOT backslash BOOT-X-64 dot EFI on a sixty-four-bit Intel or AMD machine, or BOOT-A-A-64 dot EFI on Arm. That's how a U-S-B installer stick boots on a machine that has never seen it.

Older PCs used BIOS instead of UEFI, and booted by reading the first sector of the disk, the master boot record. The idea of staging was the same, but the details were far more cramped. Modern Linux systems on PCs boot through UEFI, so that's what this episode follows.

## Section four: shim, GRUB, and Secure Boot

On a typical Linux PC, the boot entry points at a small EFI program called shim. To understand why shim exists, you need Secure Boot.

With Secure Boot on, the firmware will only run EFI programs signed by a key it trusts. Most PCs ship trusting Microsoft's keys, including a Microsoft key used to sign third-party loaders. Linux distributions don't want every update to their bootloader to go through Microsoft. So they get one small, stable program signed by Microsoft: shim. Shim contains the distribution's own key. The firmware checks shim's Microsoft signature and runs it. Shim then checks the next stage, the GRUB bootloader, against the distribution's key, and runs it. GRUB, in turn, checks that the kernel is signed. That's the chain of trust: each stage verifies the next before handing over control. If any link fails, the chain stops.

GRUB, the Grand Unified Bootloader, is the stage most Linux users have seen, as the menu that sometimes appears at startup. GRUB reads its configuration file, grub dot C-F-G, usually generated automatically when kernels are installed. It shows a menu if one's configured, and then for the chosen entry it does three things. It loads the kernel image into memory. It loads the initial RAM file system image. And it prepares the kernel command line, a single line of text such as "root equals a particular partition, read-only, quiet". Then it jumps into the kernel.

Other loaders exist and do the same job. Systemd-boot is a simpler loader that reads small text entries from the EFI System Partition. And the Linux kernel itself can be built as an EFI program, called the EFI stub, so the firmware can load the kernel directly with no separate bootloader. A newer packaging, the unified kernel image, bundles the kernel, the initial RAM file system and the command line into one signed EFI file.

## Section five: the handoff to the kernel

Just before the kernel takes over, there's a decisive moment. The loader, or the kernel's own EFI stub code, calls a UEFI function named Exit Boot Services. After that call, the firmware's drivers and boot-time services are gone. The operating system owns the hardware completely. Only a few firmware runtime services survive, for things like reading and writing those boot variables and the clock.

What does the kernel receive? Three things, and they're worth naming precisely.

First, a memory map: which ranges of physical memory are usable RAM, which are reserved by firmware, and which belong to devices.

Second, a hardware description. On PCs that's the A-C-P-I tables the firmware built. On most Arm boards, including the Raspberry Pi, it's a device tree: a compact data file, called a D-T-B for device tree blob, that lists the system's devices, their addresses, their interrupts, and which driver each one needs. Linux doesn't discover most built-in devices by probing. It reads this description and trusts it, exactly as Windows trusts the A-C-P-I tables. A wrong entry produces a device that never works, or works badly.

Third, the kernel command line, plus the location in memory of the initial RAM file system.

Pause and predict. A kernel boots on a new board but never finds its storage. Name two earlier-stage causes, from different stages.

One possibility: the hardware description is wrong or missing the storage controller, so the kernel never knows the controller exists. Another: the bootloader passed a command line whose root setting names the wrong partition, or it didn't load an initial RAM file system containing the storage driver. Part two explains why that last one matters.

## Section six: the Raspberry Pi does it differently

The Raspberry Pi is a wonderful contrast, because its boot starts somewhere you might not expect: on the graphics processor, the VideoCore, said "video-core". When power is applied, the Arm cores that will eventually run Linux are held in reset. The VideoCore runs first, starting from a boot ROM built into the chip itself, which can't be changed.

On older Pis, the boot ROM read a file called bootcode dot bin from the SD card. On the Raspberry Pi 4, the next stage lives in a small rewritable flash chip on the board, an E-E-P-R-O-M, said "ee-prom", which holds the bootloader and its settings, like which devices to try booting from. The Pi 5 also uses an E-E-P-R-O-M bootloader, and folds more of the job into it.

Following a Pi 4, the bootloader reads the SD card's first partition, which is formatted FAT, like the PC's EFI System Partition, and loads the VideoCore firmware file, start-four dot E-L-F. That firmware reads config dot T-X-T, the Pi's main boot configuration file. Config dot T-X-T sets things like which kernel file to load, memory and display settings, and device tree overlays. Then the firmware loads the device tree for this Pi model and applies the overlays. An overlay is a small patch to the device tree that enables or changes a device. For example, an overlay called D-W-C-two switches the U-S-B controller into the mode that can act as a U-S-B device instead of a host, which is the first step of U-S-B gadget mode. The firmware also reads cmdline dot T-X-T, the kernel command line as a single line of text, and loads the kernel image, for example kernel-eight dot I-M-G for sixty-four-bit. Finally, it releases the Arm cores, and they start executing the kernel.

Timothy has already touched two pieces of this chain without knowing where they sat. Gadget mode on the Pi is configured by an overlay line in config dot T-X-T and a modules setting in cmdline dot T-X-T, which is the firmware stage and the kernel command line working together. And newer Raspberry Pi OS releases mount that FAT boot partition at slash boot slash firmware instead of slash boot, which is why guides and samples that edit config dot T-X-T at the old path had to be updated.

So the two machines differ in who runs first and what the files are called, but the shape is identical. Something fixed in the chip runs first. It loads configurable firmware. The firmware reads configuration from a FAT partition, loads a hardware description, a kernel and a command line, and hands control to the kernel.

## Connections

This connects to the earlier platform lectures in two ways. The A-C-P-I tables that describe a touchscreen to Windows are built in section two of this boot, by the same firmware that boots Linux on that PC. And the device tree on the Pi plays the same role A-C-P-I plays on a PC: the trusted description of hardware that can't be discovered by probing. It also connects to Secure Boot from the Windows driver-signing lecture: the same firmware signature check that blocks unsigned Windows kernel drivers is what shim exists to satisfy.

## Recap

The core ideas again, in different words. Booting is a relay: each stage prepares just enough of the machine to load the next and passes on a few facts. On a PC, firmware in flash runs first, trains memory, loads its own drivers, builds the A-C-P-I tables, and picks a boot entry from its stored boot order. It loads an EFI program from the FAT-formatted EFI System Partition, typically shim, which loads GRUB. GRUB loads the kernel, the initial RAM file system and the command line, and jumps to the kernel, after which the firmware's boot services are gone. The kernel receives a memory map, a hardware description, and a command line. Secure Boot makes each stage verify the next. And on a Raspberry Pi, the graphics processor boots first, reads config dot T-X-T and cmdline dot T-X-T from a FAT partition, loads the device tree, its overlays and the kernel, then releases the Arm cores.

## Walk questions

Three questions to answer out loud on the next walk.

First: explain the relay-race idea, and why the very first firmware code can't load the operating system directly.

Second: name the three things the kernel receives at handoff, and what each one is for.

Third: walk through a Raspberry Pi 4 boot from power-on to the kernel, naming each file it reads, and say where the U-S-B gadget-mode settings fit in that chain.
