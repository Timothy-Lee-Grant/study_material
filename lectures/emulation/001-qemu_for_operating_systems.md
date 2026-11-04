2026_11_04_12_00-(QEMU-For-Operating-Systems)

# Lecture 001: QEMU for Operating Systems: Emulating a Whole Machine, Booting a Kernel, and Debugging It

> **For:** Timothy · **Date:** 2026-11-04
> **Prerequisites:** none required; this lecture stands on its own. It's helpful to know what an interrupt and a system call are (if you've read `concurrency/002` or `windows_internals/005`, you'll recognize them here on a different CPU).
> **Why this lecture:** you used QEMU in an operating-systems class to run JOS, a small teaching OS, and want to understand what QEMU actually is and how it lets you run and debug an operating system that doesn't exist on any real hardware you own. This lecture builds that understanding from the bottom: what an emulated machine consists of, how a kernel boots on it, how a write to a device register turns into text on your terminal, and how to stop the whole machine at any instruction with gdb. The hands-on part is a tiny kernel (about 100 lines) that prints, makes a system call and takes timer interrupts on QEMU's RISC-V `virt` machine, the same platform MIT's current teaching OS (xv6) uses.
> **Companion:** `002-emulating_microcontrollers_and_devices.md` covers QEMU (and other tools) for microcontroller firmware and fake inputs. Each lecture can be read alone.
> **Verification:** every command and output in this lecture was run on 2026-11-04 with QEMU 8.2.2 and `riscv64-unknown-elf-gcc` 13.2 on Linux. Code: `code/os/`. No firmware analogies.

---

## Core ideas (the answer key)

1. **QEMU is a program that pretends to be a computer.** It models a CPU, memory, and a set of devices at fixed addresses (a **machine**), then runs unmodified guest code on that model.
2. **Without hardware acceleration, QEMU translates guest instructions into host instructions** (its Tiny Code Generator, TCG), a block at a time, and caches the result. That's how a RISC-V or x86 kernel runs on your Arm Mac.
3. **With an accelerator** (KVM on Linux, HVF on macOS, WHPX on Windows), guest code of the **same** architecture as the host runs directly on the real CPU, and QEMU only handles the devices. That's how fast VMs work.
4. **A machine type is a memory map plus devices.** `-M virt` means "RAM at 0x80000000, a UART at 0x10000000, a timer at 0x02000000, ...". Your kernel talks to those devices by reading and writing those addresses.
5. **Every device is a set of read/write callbacks.** When guest code stores to the UART's address, QEMU calls the UART model's write function, which sends the byte to wherever you connected the serial port (your terminal, a file, a socket).
6. **Booting under QEMU is short and visible:** the CPU starts at a reset address, a few instructions jump to the firmware or straight to your kernel (`-kernel`, `-bios none`), and from there it's your code.
7. **Interrupts and system calls work exactly as on real hardware:** the emulated CPU fills in its trap registers (on RISC-V `mcause` and `mepc`) and jumps to the address your kernel put in the trap vector register (`mtvec`).
8. **QEMU has a built-in gdb server** (`-s -S`): the whole machine freezes at the first instruction, and gdb can step, set breakpoints, and read every register and byte of memory, including in code that runs before any OS exists.
9. **The QEMU monitor** (Ctrl-a c) inspects the machine from outside: registers, the memory map (`info mtree`), physical memory, devices. Logging (`-d int`) shows every interrupt and exception.
10. **Teaching OSes use exactly this setup.** JOS (x86) and xv6 (now RISC-V) are built with a cross-compiler and run with `make qemu`; `make qemu-gdb` plus gdb is how you debug the kernel you're writing.

---

## Table of Contents

- [0. What problem QEMU solves](#0-what-problem-qemu-solves)
- [1. Emulation vs virtualization: TCG and accelerators](#1-emulation-vs-virtualization-tcg-and-accelerators)
- [2. A machine is a memory map plus devices](#2-a-machine-is-a-memory-map-plus-devices)
- [3. How a kernel boots under QEMU](#3-how-a-kernel-boots-under-qemu)
- [4. Lab: a tiny kernel that prints, traps, and takes timer interrupts](#4-lab-a-tiny-kernel-that-prints-traps-and-takes-timer-interrupts)
- [5. How a store instruction becomes text on your terminal](#5-how-a-store-instruction-becomes-text-on-your-terminal)
- [6. Debugging the kernel with gdb](#6-debugging-the-kernel-with-gdb)
- [7. The monitor, logging, and snapshots](#7-the-monitor-logging-and-snapshots)
- [8. JOS and xv6: how teaching OSes use QEMU](#8-jos-and-xv6-how-teaching-oses-use-qemu)
- [9. QEMU and the VMs you already use](#9-qemu-and-the-vms-you-already-use)
- [Misconceptions](#misconceptions)
- [Self-check questions](#self-check-questions)
- [Sources](#sources)

---

## 0. What problem QEMU solves

Writing an operating system on real hardware is slow and opaque: every test means flashing or rebooting a machine, a bug in early boot just shows a frozen screen, and you can't pause the CPU to look at it. A kernel that corrupts memory can take the machine down with no clue why.

QEMU replaces the hardware with a program. Your kernel runs on a **model** of a computer, so:
- a "reboot" is restarting a process (well under a second);
- the whole machine can be frozen at any instruction and inspected;
- every register, every byte of RAM, and every device's state is visible from outside;
- you can run a CPU architecture you don't own (RISC-V on an Arm Mac, x86 on anything);
- a crash just stops the emulator, and you can see exactly where.

That's why OS courses use it, and why OS developers use it daily.

---

## 1. Emulation vs virtualization: TCG and accelerators

QEMU can run guest code in two fundamentally different ways.

**Emulation with TCG (Tiny Code Generator).** QEMU reads the guest's machine code, a **translation block** at a time (a straight run of instructions up to a branch), translates each block into equivalent host machine code, caches it, and runs it. Guest registers live in a C structure in QEMU's memory; a guest `add` becomes a few host instructions that update that structure. The next time the guest reaches that block, the cached translation runs directly.

- Works for **any guest CPU on any host CPU** (RISC-V kernel on an Arm Mac, Arm firmware on an x86 PC).
- Slower than real hardware (often several times slower), but plenty fast for kernels and firmware.
- Every guest instruction is under QEMU's control, which is what makes instruction-level debugging and logging easy.

**Virtualization with an accelerator.** When the guest CPU architecture matches the host (an Arm64 Linux guest on your Arm64 Mac), QEMU can ask the host OS's hypervisor to run guest code **directly on the real CPU**, in a hardware-isolated guest mode:
- **KVM** on Linux, **HVF** (Hypervisor.framework) on macOS, **WHPX** on Windows.
- Near-native speed. QEMU only steps in when the guest touches a device (the CPU exits to QEMU, QEMU runs the device model, then resumes the guest).

```
qemu-system-riscv64 -M virt ...                    # TCG: RISC-V emulated on any host
qemu-system-aarch64 -M virt -accel hvf -cpu host   # HVF: Arm64 guest on an Arm64 Mac, real CPU
```

**System mode vs user mode.** Everything here is **system emulation** (`qemu-system-*`): a whole machine with devices, and you bring the OS. QEMU also has **user-mode emulation** (`qemu-riscv64 ./program`): run a single Linux program built for another architecture, with its system calls translated to the host's Linux. Useful for testing cross-compiled programs, not for kernels.

---

## 2. A machine is a memory map plus devices

When you pick a machine with `-M`, you choose a fixed layout: which CPU, where RAM is, and which devices sit at which physical addresses. For RISC-V's `virt` machine, QEMU's monitor shows it directly (excerpt of `info mtree`):

| Address | What's there | What the kernel does with it |
|---|---|---|
| `0x00001000` | a small reset ROM ("MROM") | the CPU starts here; it jumps to firmware or the kernel |
| `0x00100000` | test/power device ("sifive_test") | write `0x5555` to power off (QEMU exits) |
| `0x02000000` | CLINT: timer (`mtime`, `mtimecmp`) and software interrupts | program timer interrupts |
| `0x0C000000` | PLIC: external interrupt controller | route device interrupts to cores |
| `0x10000000` | NS16550A UART | print characters, read keys |
| `0x10001000`… | virtio devices (disk, network) | block and network I/O |
| `0x80000000` | RAM (default 128 MB) | the kernel is loaded here |

```
qemu-system-riscv64 -M help            # list machine types for this architecture
qemu-system-riscv64 -M virt -device help   # list devices you can add
# inside the monitor (§7):  info mtree     (memory map)   info qtree   (device tree)
```

The `virt` machine is **not a copy of any real board**. It's a clean, made-up machine designed for virtualization and for teaching, with well-documented standard devices. QEMU generates a **device tree** describing it and passes it to the guest (in register `a1` on RISC-V), so a kernel like Linux can discover the layout instead of hard-coding it. A tiny kernel like ours just hard-codes the addresses.

Other machine types model **real** boards (`sifive_u`, Raspberry Pi models `raspi3b` on Arm, many microcontroller boards), with those boards' real addresses and devices. Lecture 002 uses one of those.

---

## 3. How a kernel boots under QEMU

**On the `virt` RISC-V machine with `-bios none -kernel kernel.elf`:**
1. QEMU loads the ELF file's segments into guest RAM at the addresses the ELF says (our linker script puts the kernel at `0x80000000`).
2. Every core ("hart") starts at the reset ROM at `0x1000`. You'll see this in gdb in §6: the first `pc` is `0x1000`.
3. The ROM's few instructions jump to `0x80000000`, in **machine mode** (M-mode), RISC-V's highest privilege level.
4. Our `_start` runs: it checks which core it is (`mhartid`), parks all but core 0, sets up a stack, and calls C.

**With firmware** (the default, without `-bios none`), QEMU first runs **OpenSBI**, a small M-mode firmware that sets up the machine and then starts the kernel in **supervisor mode** (S-mode). That's how Linux and xv6 boot: the firmware owns M-mode, the kernel runs one level below and asks the firmware for some services. Our tiny kernel skips the firmware to keep everything visible in one file.

**On the classic x86 PC machine** (what JOS used): the CPU starts in 16-bit real mode at the top of the first megabyte, runs the BIOS (QEMU ships SeaBIOS), which loads the first 512-byte sector of the disk to `0x7C00` and jumps to it. That boot sector is the OS's own boot loader; it switches to 32-bit protected mode, reads the kernel from disk, and jumps to it. JOS's first lab has you trace exactly this path in gdb.

---

## 4. Lab: a tiny kernel that prints, traps, and takes timer interrupts

Files in `code/os/`: `entry.S` (first instructions and trap entry), `kernel.c`, `link.ld`, `Makefile`, `debug.gdb`.

**What it does:**
1. prints over the UART;
2. installs a trap handler (writes its address to `mtvec`);
3. makes a **system call** with `ecall` → the CPU traps to the handler, which prints and returns past the `ecall`;
4. enables **timer interrupts** and sleeps with `wfi`; each interrupt is handled and the next one scheduled;
5. after three ticks, writes `0x5555` to the test device, and QEMU exits.

**The key parts of `kernel.c`:**

```c
#define UART       ((volatile uint8_t *)0x10000000)
#define MTIMECMP   (*(volatile uint64_t *)0x02004000)
#define MTIME      (*(volatile uint64_t *)0x0200BFF8)
#define POWEROFF   (*(volatile uint32_t *)0x00100000)
#define TICK       5000000ull          /* 0.5 s at the virt CLINT's 10 MHz timebase */

static void putc_(char c) { while ((UART[5] & 0x20) == 0) { } UART[0] = (uint8_t)c; }

void trap_handler(void)
{
    uint64_t cause = csr_read(mcause), epc = csr_read(mepc);
    if (cause >> 63) {                              /* top bit set: an interrupt */
        if ((cause & 0xff) == 7) {                  /* 7 = machine timer interrupt */
            ticks++;
            ...print...
            MTIMECMP = MTIME + TICK;                /* schedule the next one (this also clears it) */
        }
    } else if (cause == 11) {                       /* 11 = ecall from M-mode: a "system call" */
        ...print...
        csr_write(mepc, epc + 4);                   /* resume AFTER the ecall instruction */
    }
}

void kmain(void)
{
    puts_("tiny kernel: hello from M-mode on QEMU virt\n");
    csr_write(mtvec, (uint64_t)trap_entry);         /* where traps go */
    __asm__ volatile("li a7, 64; ecall" ::: "a7");  /* a system call */
    MTIMECMP = MTIME + TICK;
    csr_set(mie, 1u << 7);                          /* enable the timer interrupt source */
    csr_set(mstatus, 1u << 3);                      /* global interrupt enable */
    while (ticks < 3) __asm__ volatile("wfi");      /* sleep until an interrupt */
    csr_clear(mie, 1u << 7);
    POWEROFF = 0x5555;                              /* QEMU exits with status 0 */
}
```

**Build and run:**

```
$ make
$ qemu-system-riscv64 -M virt -bios none -nographic -kernel kernel.elf
tiny kernel: hello from M-mode on QEMU virt
making a system call (ecall)...
  [trap] ecall (call number in a7), mepc = 0x00000000800001ec
back from the system call
  [trap] timer interrupt, tick 1
  [trap] timer interrupt, tick 2
  [trap] timer interrupt, tick 3
3 ticks done; powering off
```

(`-nographic` connects the guest's serial port to your terminal and disables the graphical window; QEMU's exit status was 0.)

**What the trap mechanism is doing.** On any trap, the RISC-V CPU (here, QEMU's model of it) does four things in hardware:
1. saves the address of the trapping (or interrupted) instruction in `mepc`;
2. records the reason in `mcause` (top bit = interrupt vs exception; low bits = which);
3. disables further interrupts (saving the previous enable bit in `mstatus`);
4. jumps to the address in `mtvec`.

Our `trap_entry` (in `entry.S`) then saves the registers C code may change, calls `trap_handler`, restores them, and executes `mret`, which jumps back to `mepc` and restores the interrupt-enable bit. For the `ecall`, the handler adds 4 to `mepc` first, so execution continues **after** the `ecall` instead of repeating it. That's the shape of every system call on every architecture: trap into privileged code, look at a call number (in `a7` here), do the work, return past the instruction.

**The timer.** The CLINT compares a free-running counter `mtime` (10 MHz on `virt`) with `mtimecmp`; when `mtime ≥ mtimecmp`, it raises the machine timer interrupt. Writing a later value to `mtimecmp` both schedules the next interrupt and clears the current one. That's the "tick" an OS scheduler uses to take the CPU back from a running program.

---

## 5. How a store instruction becomes text on your terminal

Follow one character, `'t'`, from `putc_`:

1. The guest executes a store byte instruction to address `0x10000000`.
2. QEMU's translated code for that store looks up the address in the machine's memory map. It isn't RAM; it's the **UART's memory region**.
3. QEMU calls the UART model's **write callback** with (offset 0, value `0x74`). For a 16550 UART, offset 0 is the transmit register.
4. The UART model hands the byte to its **character device backend** (a "chardev"): whatever `-serial` (or `-nographic`) connected it to. Here, QEMU's own standard output.
5. Your terminal shows `t`.

Reading works the same way in reverse: a load from `0x10000005` (the line status register) calls the model's **read callback**, which returns a value saying "ready to send". When you type a key, the chardev delivers it to the UART model, which sets "data ready" and can raise an interrupt line to the PLIC.

That's all a device is in QEMU: **a region of the address space plus read/write callbacks, connected to something outside** (a file, a socket, a host network interface, a disk image). Lecture 002 builds on this to inject fake inputs into a device.

You can redirect where the serial port goes:

```
-serial stdio                         # terminal (what -nographic does)
-serial file:boot.log                 # write the guest's console to a file
-serial tcp:127.0.0.1:5555,server=on  # a TCP socket; connect with nc or a script
-serial pty                           # a pseudo-terminal you can open with screen
```

---

## 6. Debugging the kernel with gdb

QEMU contains a **gdb server** (a "gdb stub"). Two options:
- `-s`: listen for gdb on TCP port 1234;
- `-S`: don't start the CPU; wait, frozen at the first instruction, until gdb says continue.

The debugger talks to the **emulated CPU**, not to a process, so it works before there's any OS at all, and it can read privileged registers like `mcause`.

```
terminal 1:  make debug          # = qemu-system-riscv64 -M virt -bios none -nographic -kernel kernel.elf -s -S
terminal 2:  gdb-multiarch -q -x debug.gdb kernel.elf     # (on a Mac: riscv64-unknown-elf-gdb)
```

`debug.gdb`:

```
target remote :1234
info registers pc
break trap_handler
continue
print/x $mcause
print/x $mepc
x/i $mepc
continue
print/x $mcause
backtrace
```

Actual output (run 2026-11-04):

```
0x0000000000001000 in ?? ()
pc             0x1000	0x1000                     ← frozen at the reset ROM, before our code
Breakpoint 1 at 0x800000f8: file kernel.c, line 28.
Breakpoint 1, trap_handler () at kernel.c:28        ← first trap
$1 = 0xb                                            ← mcause 11: ecall from M-mode
$2 = 0x800001ec                                     ← mepc: the address of the ecall
   0x800001ec <kmain+44>:	ecall                   ← proof: the instruction at mepc
Breakpoint 1, trap_handler () at kernel.c:28        ← second trap
$3 = 0x8000000000000007                             ← top bit set (interrupt), cause 7: timer
#0  trap_handler () at kernel.c:28
#1  0x0000000080000046 in trap_entry () at entry.S:25
```

Things worth noticing:
- **You stopped the machine before it ran a single instruction** of your code (`pc = 0x1000`).
- **gdb reads CSRs** (`$mcause`, `$mepc`) by name, because QEMU's stub exposes them.
- **The backtrace crosses the trap**: `trap_handler` was called from `trap_entry`. Above that, gdb can't unwind (the trap entry isn't a normal call), which is exactly the boundary between "interrupted code" and "trap handler".

Useful gdb commands for kernel work:

| Command | Use |
|---|---|
| `stepi` / `si` | execute one machine instruction |
| `x/10i $pc` | disassemble the next 10 instructions |
| `x/8gx 0x80000000` | dump memory (8 giant words, hex) |
| `info registers` | all general registers |
| `watch ticks` | stop when a variable changes (QEMU supports hardware-style watchpoints) |
| `layout asm` / `layout src` | split-screen views |

---

## 7. The monitor, logging, and snapshots

**The QEMU monitor** is a command console for the machine itself (not the guest). With `-nographic`, press **Ctrl-a c** to switch between the guest's serial console and the monitor (Ctrl-a x quits QEMU). Or run it on its own channel with `-monitor stdio` or `-monitor tcp:...`.

| Monitor command | Shows |
|---|---|
| `info registers` | the CPU's registers right now |
| `info mtree` | the memory map: RAM, ROM, every device's address range |
| `info qtree` / `info qom-tree` | the device tree as QEMU built it |
| `xp /8xw 0x10000000` | read physical memory (a device's registers, or RAM) |
| `stop` / `cont` | pause / resume the whole machine |
| `system_reset` | press the reset button |
| `savevm name` / `loadvm name` | snapshot the whole machine (needs a qcow2 disk) |

A machine-readable version of the monitor, **QMP** (`-qmp`), speaks JSON and is what management tools and test scripts use.

**Logging.** `-d` turns on QEMU's internal logs; `-D file` sends them to a file:

```
-d int               # every interrupt and exception, with cause and PC (great for "why did it trap?")
-d guest_errors      # guest touched an unimplemented device or did something invalid
-d in_asm            # every translation block as it's translated (very verbose)
-d unimp             # accesses to unimplemented device registers
```

When a kernel crashes with no output, `-d int,guest_errors -D qemu.log` usually shows the exact faulting address.

**Record/replay and determinism.** QEMU can record a run (`-icount ... rr=record`) and replay it deterministically, and gdb can then step **backwards** (`reverse-stepi`). This is advanced, but it's worth knowing it exists for bugs that only happen once.

---

## 8. JOS and xv6: how teaching OSes use QEMU

**JOS** was the operating system students built in MIT's 6.828 *Operating System Engineering* course and in courses at other universities that adopted its labs. It targeted **32-bit x86** on QEMU's PC machine. The labs had you write it in stages:
1. **Booting:** trace the BIOS → boot sector → kernel path in gdb;
2. **Memory management:** physical page allocator and page tables;
3. **User environments:** loading and running a user program, and the **trap** and **system call** mechanism;
4. **Preemptive multitasking:** multiple CPUs, scheduling, timer interrupts, inter-process communication, copy-on-write `fork`;
5. **File system** and a shell; 6. **Network driver** (in some years).

The workflow is the one in this lecture: a cross-compiler builds the kernel and a disk image; `make qemu` boots it; `make qemu-gdb` starts QEMU with the gdb stub frozen (`-s -S` equivalent), and `make gdb` attaches. When your page-table code is wrong, the machine faults, and `-d int` / gdb show you the faulting address and instruction.

**xv6** is MIT's other teaching OS: a re-implementation of Unix Version 6 in modern C, small enough to read in full alongside its book. From Fall 2019, MIT's course (renamed 6.S081, now 6.1810) switched to **xv6 for RISC-V** on QEMU's `virt` machine, the same machine as this lecture's lab. If you want to revisit the JOS experience today, xv6-riscv and its labs are the maintained path.

**Running xv6-riscv on your Mac** (from the course's tools page):

```
xcode-select --install
brew tap riscv/riscv && brew install riscv-tools     # RISC-V cross-compiler + gdb
brew install qemu                                    # needs QEMU 7.2 or newer
git clone https://github.com/mit-pdos/xv6-riscv.git
cd xv6-riscv && make qemu                            # boots to an xv6 shell; try `ls`
# Ctrl-a x quits.  make qemu-gdb, then in another terminal riscv64-unknown-elf-gdb, to debug
```

When you boot xv6, map what you see to this lecture: OpenSBI (or the reset ROM), then xv6's `entry.S` sets a stack per core, `start.c` runs in M-mode and arranges timer interrupts, then drops to S-mode for `main`. It's this lab's tiny kernel, grown into a real OS.

---

## 9. QEMU and the VMs you already use

| Tool | What it is | Relationship to QEMU |
|---|---|---|
| **VMware Fusion** (your Windows 11 Arm VM) | a commercial hypervisor using macOS's Hypervisor.framework | separate product; same idea as QEMU + HVF, plus its own device models |
| **UTM** (macOS) | a friendly app for VMs | uses QEMU underneath (and Apple's Virtualization framework for some guests) |
| **KVM + QEMU** (Linux) | the standard Linux virtualization stack | KVM runs the CPU; QEMU provides the machine and devices |
| **QEMU with TCG** | pure emulation | the only option for a different CPU architecture (RISC-V on your Mac) |

Rule of thumb: **same architecture and you want speed** → an accelerator (HVF/KVM/WHPX, or a product like Fusion). **Different architecture, early boot, or instruction-level visibility** → QEMU with TCG.

---

## Misconceptions

| You might think | Reality |
|---|---|
| QEMU runs the guest "on" your CPU | With TCG it translates guest instructions to host instructions; only with an accelerator (same architecture) does guest code run directly on the CPU |
| An emulated machine is a copy of real hardware | Some machine types model real boards; `virt` is a made-up, documented machine designed for this |
| A device in QEMU is hardware simulation at the wire level | It's read/write callbacks on an address range, modeling the register behavior software sees |
| gdb with QEMU debugs a process | It debugs the emulated CPU: works before any OS, sees privileged registers |
| `-kernel` needs a bootloader | QEMU loads the ELF into RAM itself; with `-bios none` the reset ROM jumps straight to it |
| JOS and xv6 are the same | Both MIT teaching OSes; JOS was the x86 lab OS students built up; xv6 is a complete small Unix (now on RISC-V) that the current labs extend |

---

## Self-check questions

1. What's the difference between running a guest with TCG and with HVF/KVM? When can you only use TCG?
<details><summary>Answer</summary>TCG translates guest machine code into host machine code block by block and runs the translation; it works for any guest architecture on any host, slower. An accelerator runs guest code directly on the real CPU in hardware-isolated guest mode, near native speed, with QEMU handling only devices; it requires the guest and host architectures to match. A RISC-V guest on an Arm Mac can only use TCG.</details>

2. What does `-M virt` decide for your kernel?
<details><summary>Answer</summary>The CPU type and the fixed memory map: RAM at 0x80000000, the UART at 0x10000000, the CLINT timer at 0x02000000, the PLIC, virtio devices, the test/power device at 0x100000. The kernel uses those devices by reading/writing those addresses (or reads them from the device tree QEMU passes in).</details>

3. With `-bios none -kernel kernel.elf`, where does the first instruction execute, and how does control reach `_start`?
<details><summary>Answer</summary>At the reset ROM at 0x1000 (gdb shows pc = 0x1000). QEMU has already loaded the ELF into RAM at 0x80000000; the ROM's few instructions jump there, in M-mode, and `_start` is the first instruction of the kernel's `.text.entry` section.</details>

4. Trace what happens in hardware and software when the tiny kernel executes `ecall`.
<details><summary>Answer</summary>Hardware: mepc = address of the ecall, mcause = 11, interrupts disabled with the old enable saved in mstatus, jump to mtvec (trap_entry). Software: trap_entry saves registers, calls trap_handler, which sees cause 11, prints, sets mepc += 4; trap_entry restores registers and executes mret, which jumps to mepc (the instruction after ecall) and restores the interrupt-enable state.</details>

5. Why must the handler add 4 to `mepc` for an `ecall` but not for a timer interrupt?
<details><summary>Answer</summary>For an exception like ecall, mepc points at the trapping instruction itself; returning there would execute ecall again forever. For an interrupt, mepc points at the instruction that hadn't run yet when the interrupt arrived, so returning to it is correct.</details>

6. Follow a byte written by `putc_` from the store instruction to your terminal.
<details><summary>Answer</summary>The guest stores to 0x10000000; QEMU finds the address in the UART's memory region and calls the 16550 model's write callback (offset 0 = transmit register); the model passes the byte to its chardev backend (stdio, because of -nographic); the terminal prints it.</details>

7. What do `-s` and `-S` do, and why does gdb work even before your kernel has set anything up?
<details><summary>Answer</summary>-s opens QEMU's gdb server on port 1234; -S keeps the CPU frozen until gdb continues. gdb is talking to QEMU's model of the CPU, not to an OS process, so it can stop at the reset ROM, read all registers including CSRs, and set breakpoints anywhere.</details>

8. Your kernel hangs with no output. Name two QEMU tools you'd use first and what each tells you.
<details><summary>Answer</summary>`-d int,guest_errors -D qemu.log`: every trap with its cause and PC, plus accesses to bad or unimplemented device addresses. gdb via -s -S: break at the entry point and step to see where it goes wrong. The monitor (`info registers`, `info mtree`, `xp`) shows the current PC and memory/device state.</details>

9. How do JOS and xv6 relate to QEMU and to each other?
<details><summary>Answer</summary>Both are MIT teaching operating systems run on QEMU with `make qemu` and debugged with `make qemu-gdb` + gdb. JOS was the x86 OS students built lab by lab in 6.828; since Fall 2019 the course (6.S081, now 6.1810) uses xv6 for RISC-V on QEMU's virt machine.</details>

---

## Sources

- QEMU documentation: [System emulation overview](https://www.qemu.org/docs/master/system/index.html), [RISC-V `virt` machine](https://www.qemu.org/docs/master/system/riscv/virt.html), [GDB usage](https://www.qemu.org/docs/master/system/gdb.html), [QEMU monitor](https://www.qemu.org/docs/master/system/monitor.html), [TCG and accelerators](https://www.qemu.org/docs/master/devel/index-tcg.html), [Record/replay](https://www.qemu.org/docs/master/devel/replay.html). Checked 2026-11-04.
- RISC-V International, *The RISC-V Instruction Set Manual, Volume II: Privileged Architecture* (machine-mode CSRs `mtvec`, `mepc`, `mcause`, `mstatus`, `mie`; CLINT timer).
- MIT PDOS: [6.828 Fall 2018 (JOS labs on x86)](https://pdos.csail.mit.edu/6.1810/2018/overview.html), [6.S081 Fall 2019 overview (xv6 on RISC-V)](https://pdos.csail.mit.edu/6.828/2019/overview.html), [xv6 page](https://pdos.csail.mit.edu/6.1810/2018/xv6.html), [6.1810 tools (macOS install, QEMU 7.2+)](https://pdos.csail.mit.edu/6.1810/2025/tools.html). Checked 2026-11-04.
- [mit-pdos/xv6-riscv](https://github.com/mit-pdos/xv6-riscv) on GitHub. Checked 2026-11-04.
- Code: `code/os/` (QEMU 8.2.2, riscv64-unknown-elf-gcc 13.2, gdb-multiarch), run 2026-11-04.
