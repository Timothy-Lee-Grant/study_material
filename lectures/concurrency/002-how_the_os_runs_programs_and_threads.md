2026_11_01_12_30-(How-The-OS-Runs-Programs-And-Threads)

# Lecture 002: How the OS Actually Runs Programs and Threads (Starting a Program, Entering the Kernel, Switching Threads)

> **For:** Timothy · **Date:** 2026-11-01
> **Prerequisites:** `windows_internals/005` (interrupts, IRQL), `windows_internals/008` §1–2 (process vs thread definitions, virtual → physical translation). Helpful: `firmware/003` (from bare metal to an OS).
> **Why this lecture:** you set out to understand C# concurrency and found that the question underneath it is: *how do processes, threads, the kernel and the physical CPU actually work together?* You wrote out your model in detail: a shell starts your program with `fork`; a CPU register says "kernel mode"; the same thread continues into the kernel; a timer interrupt is what runs the scheduler; there's no "master orchestrator"; and you asked where the context of 1,000 threads lives and how the scheduler finds it. **Most of that model is right.** This lecture confirms each piece, fixes the parts that are off, and fills in the two things you couldn't see: how the CPU gets into the kernel (one entry point and a table, with the hardware switching only a few registers), and how the scheduler finds threads (queues of ready threads, not a scan of all of them).
> **Companion:** lecture 003 uses this one to answer your .NET questions (thread pool, `async`/`await`, "don't 5,000 requests still need 5,000 contexts?").
> **Format notes:** Linux and Windows are shown side by side where they differ; x86-64 and Arm64 where the CPU matters (your Mac and your VM are Arm64). No firmware analogies. 🟢 = own it, 🔵 = know the contract, ⚫ = black box for now.

---

## Core ideas (the answer key)

1. **A process is a container; a thread is what runs.** A process owns an address space (its page tables), open handles/files, and a security identity. A thread owns a set of CPU register values (including its instruction pointer and stack pointer), a user stack, a kernel stack, and scheduling state. The scheduler schedules **threads**.
2. **A shell is a compiled program, and starting your app is two steps on Linux:** `fork` (copy the shell's process) then `execve` (replace the copy's program with yours, same PID). Windows has no fork: `CreateProcess` builds a new process and its first thread directly.
3. **User mode vs kernel mode is a bit of CPU state,** as you guessed: the privilege level in the `CS` register on x86-64 (ring 3 vs ring 0), the exception level in `PSTATE` on Arm64 (EL0 vs EL1). Only certain events can raise it: system calls, interrupts, and exceptions (like page faults).
4. **A system call is a special instruction (`syscall` on x86-64, `svc` on Arm64) that jumps to ONE kernel entry point** set up at boot. The entry code reads the system-call number from a register and looks up the function in a **table**. `fork` itself is a C library function that executes that instruction.
5. **Entering the kernel doesn't change which thread is running.** The same thread continues, now in kernel mode, on **its own kernel stack**. You had this exactly right.
6. **On an interrupt or system call, the hardware switches only a few registers:** the privilege level, the instruction pointer (to the kernel's handler), and the stack pointer (to the kernel stack); it saves the old instruction pointer and flags. The kernel's own code then saves the rest of the registers. That's how "all the kernel's register values" get loaded: most of them are just set by ordinary instructions.
7. **There's no separate orchestrator running above the system.** The kernel is code that runs **on each CPU, inside whatever thread was running**, when an interrupt, exception or system call enters it. The scheduler is a function the kernel calls on those paths, not a thread.
8. **A context switch** = save the current thread's registers into its kernel stack / thread structure, pick the next thread, load its saved stack pointer and registers, and if it belongs to a different process, load that process's page-table root (`CR3` / `TTBR0_EL1`) so the MMU translates with its mappings.
9. **Every thread's saved context lives in kernel memory** (its thread structure and kernel stack). That's real memory per thread, which is exactly why "thousands of threads" has a cost.
10. **The scheduler doesn't scan all threads.** Each CPU has a **run queue** that holds only threads that are **ready**. Threads that are waiting sit on the wait list of the thing they wait for (an event, a socket), and are moved to a run queue when it's signaled. With 1,000 threads on 8 cores, at most 8 are running and usually only a handful are ready.

---

## Table of Contents

- [0. Your model, checked](#0-your-model-checked)
- [1. Processes and threads, precisely](#1-processes-and-threads-precisely)
- [2. Starting your program](#2-starting-your-program)
- [3. User mode, kernel mode, and the system call](#3-user-mode-kernel-mode-and-the-system-call)
- [4. Interrupts: what the hardware does and what the code does](#4-interrupts-what-the-hardware-does-and-what-the-code-does)
- [5. The context switch, step by step](#5-the-context-switch-step-by-step)
- [6. Where 1,000 threads live, and how the scheduler finds them](#6-where-1000-threads-live-and-how-the-scheduler-finds-them)
- [7. "There is no orchestrator", made precise](#7-there-is-no-orchestrator-made-precise)
- [8. One full trace: a key press wakes a thread](#8-one-full-trace-a-key-press-wakes-a-thread)
- [9. See it yourself](#9-see-it-yourself)
- [Misconceptions](#misconceptions)
- [Self-check questions](#self-check-questions)
- [Sources](#sources)

---

## 0. Your model, checked

| You said | Verdict | The precise version |
|---|---|---|
| The terminal process starts my program | ✅ | The shell (a process with a PID) asks the kernel to create a child process and run your executable in it (§2) |
| Commands are bash/PowerShell scripts | ❌ mostly | Most commands are **compiled executables** (`/usr/bin/ls` is an ELF binary). Some are **built into** the shell (`cd`). A few are scripts, run by an interpreter (§2.1) |
| A `fork` machine instruction | ⚠️ | `fork` is a **library function**; the machine instruction is `syscall`/`svc`, with the call's number in a register (§3) |
| A register in the CPU says we're in kernel mode | ✅ | `CS` privilege level (x86-64) / `PSTATE` exception level (Arm64) |
| The transition is the same thread continuing | ✅ | Same thread, switched to its kernel stack |
| The instruction pointer jumps to a fixed address for that kernel function | ⚠️ | It jumps to **one** fixed entry address; the entry code uses the call **number** to index a **table** of functions |
| The new process needs a thread to run the app | ✅ | Its **initial thread** |
| The scheduler considers threads, not processes | ✅ | And the thread's process tells the kernel which page tables (address space) to load |
| A thread has an instruction pointer to the next instruction | ✅ | Saved in its context while it isn't running; in the CPU's `RIP`/`PC` while it is |
| 1,000 threads "in the running state" | ❌ | At most one running **per CPU core**; most are **waiting** (blocked), a few **ready** (§6) |
| No master orchestrator; a timer interrupt runs the scheduler | ✅ (with nuance) | Correct; the timer is one of several ways in. Blocking calls and wake-ups also call the scheduler (§7) |
| An interrupt sets a bit; the CPU checks it, respecting masks | ✅ | Checked between instructions; masked by a flag (`RFLAGS.IF` / `PSTATE.I`) |
| "It needs to get all those kernel register values somehow" | the open question | The hardware switches only mode, instruction pointer and stack pointer; kernel code saves and loads the rest (§4) |
| "How does the scheduler know about all those contexts?" | the open question | Per-CPU run queues of ready threads + wait lists per object (§6) |

Your instinct that "when something seems strange, my understanding is incomplete" was exactly right both times it fired: the two strange-feeling points are the two mechanisms you hadn't seen yet.

---

## 1. Processes and threads, precisely 🟢

Lecture `windows_internals/008` §1 defined them; here's the list of what each one **owns**, because "where is the context stored" depends on it.

| A **process** owns | A **thread** owns |
|---|---|
| an **address space**: its page tables (the MMU's map from virtual to physical) | its **register values**: instruction pointer, stack pointer, general registers, flags, floating-point/vector registers |
| **handles / file descriptors**: open files, sockets, events | a **user stack** (in its process's address space) |
| a **security identity** (Windows token / Linux credentials) | a **kernel stack** (in kernel memory) |
| an ID (PID), a parent, an exit code | **scheduling state**: running / ready / waiting, priority, which CPU, time used |
| one or more threads | an ID (TID), and a pointer to its process |

A process with no threads doesn't run. It's the **threads** that execute instructions; they do it in their process's address space, with its handles and its identity. So your phrasing, "the process is more of settings and configurations, which the resulting threads will use", is a good way to say it.

**In the kernel's data structures:**
- **Windows:** a process is an `EPROCESS` (with a `KPROCESS` inside it holding the page-table root); a thread is an `ETHREAD` (with a `KTHREAD` inside it holding the scheduling state and saved stack pointer). You can see them with `!process` and `!thread` in WinDbg.
- **Linux:** both are a `task_struct`. Threads of one process are tasks that **share** the same memory descriptor (`mm_struct`), file table, and so on. A "process" is a group of tasks sharing these.

---

## 2. Starting your program 🟢

### 2.1 What the shell is

A shell (`bash`, `zsh`, PowerShell, `cmd`) is an ordinary compiled program, running as a process with one main thread. It reads your line, and then:
- **Built-in command** (`cd`, `export`, `echo` in bash): the shell does it itself, no new process. (`cd` *must* be built in: a child process changing its own directory wouldn't change the shell's.)
- **External command** (`ls`, `dotnet`, `./MyApp`): the shell finds the file (searching `PATH`) and asks the kernel to run it in a **new process**.

Most external commands are compiled executables: ELF files on Linux, PE (`.exe`) files on Windows, Mach-O on macOS. Some are scripts: a text file whose first line is `#!/bin/sh` (or similar). For those, the kernel runs the named interpreter and passes it the script. So "a command is a script" is true for a few, but the usual case is machine code that's already compiled.

### 2.2 Linux: `fork`, then `execve`

```
shell (PID 1200)
   │  fork()                    ← kernel duplicates the process: new PID 1201, same program,
   │                              same memory contents (copy-on-write), one thread
   ├──► child (PID 1201): still running the shell's code
   │       execve("/usr/bin/dotnet", ["dotnet", "MyApp.dll"], env)
   │                            ← kernel REPLACES the program in 1201: discards the copied memory,
   │                              maps the new executable, new stack with argv/env, same PID
   │       → starts at the dynamic linker (ld.so), which loads libc etc., then calls main
   │
   └── shell: waitpid(1201) ... (sleeps until the child exits, unless you used &)
```

- **`fork`** copies the calling process. It doesn't really copy all the memory: both processes share the pages, marked read-only, and a page is copied only when one side writes to it (**copy-on-write**). Modern libraries implement `fork` with the more general `clone` system call.
- **`execve`** doesn't create a process. It **replaces the program running in the current one**: same PID, same parent, new code, new memory. The kernel's ELF loader maps the executable's segments into the address space, builds the initial stack (argument strings, environment, auxiliary values), and sets the thread's instruction pointer to the program's entry point (for a dynamically linked program, the dynamic linker `ld.so`).
- The two steps are separate so the child can adjust things in between (redirect output to a file for `>`, set up pipes for `|`) while it's still running shell code.

### 2.3 Windows: `CreateProcess`

Windows has no `fork`. The shell calls `CreateProcessW("MyApp.exe", ...)`, which goes to the kernel (`NtCreateUserProcess`). The kernel:
1. creates the process object (`EPROCESS`) and a new, empty address space;
2. maps the executable image and `ntdll.dll` into it;
3. creates the **initial thread** (`ETHREAD`) with its stacks, pointing it at a start routine in `ntdll`;
4. makes the thread ready.

When the initial thread first runs, `ntdll`'s loader maps and initializes the DLLs the program needs (`kernel32.dll`, the C runtime, ...), then calls the executable's entry point. The new process records the shell as its parent.

### 2.4 Then .NET starts

Your .NET app's executable (`MyApp.exe`, or `MyApp` on Linux/macOS) is a small native **host** program. Its initial thread loads `hostfxr`, which finds the right runtime version, which loads the runtime itself (`coreclr`). The runtime initializes the garbage-collected heap and starts several **helper threads of its own** (for example the finalizer thread, plus others depending on version and OS), then JIT-compiles your `Main` and calls it **on the initial thread**.

The lab in lecture 003 prints the thread count before your code does anything: **9 OS threads** for an empty .NET 8 console app on Linux. You haven't created any; the runtime did.

---

## 3. User mode, kernel mode, and the system call 🟢

### 3.1 The mode is CPU state

Your guess was right: there is a piece of CPU state that says which privilege level is executing.

| | x86-64 | Arm64 |
|---|---|---|
| Where the level lives | low 2 bits of the `CS` register: the **current privilege level** (CPL) | `PSTATE.EL`: the **current exception level** |
| User | ring 3 | EL0 |
| Kernel | ring 0 | EL1 |
| (Hypervisor, lecture `windows_internals/012`) | VMX root mode | EL2 |

What the level controls: kernel-only instructions (loading page tables, masking interrupts, talking to the interrupt controller) fault in user mode, and page-table entries can mark pages **kernel-only**, so user-mode code can't read kernel memory even though it's mapped in the same address space.

User code can't just write "kernel" into that state. The only ways **up** are controlled entries: a system-call instruction, an interrupt, or an exception (a page fault, a divide by zero). Each one jumps to an address **the kernel chose at boot**. That's the whole security model: you can enter the kernel, but only at its front doors.

### 3.2 What a system call is

`fork()`, `read()`, `ReadFile()` are **library functions**. Somewhere inside them, a few instructions do the actual system call. For `fork` on Linux x86-64, it looks like:

```asm
mov  eax, 57        ; system-call NUMBER for fork (on x86-64 Linux; on Arm64 the number goes in x8)
syscall             ; enter the kernel
                    ; ...execution continues here when the kernel returns; result in rax
```

On Arm64 the instruction is `svc #0`, with the number in register `x8`. On Windows, `ntdll.dll` contains one small stub per system call that does the same (`mov eax, <number>; syscall`). Windows changes the numbers between builds, which is why programs always call `ntdll`/`kernel32` instead of issuing `syscall` themselves.

### 3.3 What `syscall` does, in hardware

At boot, the kernel wrote **one** entry address into a CPU register (`LSTAR` on x86-64, the vector table base `VBAR_EL1` on Arm64). When `syscall` executes, the CPU:
1. saves the return address (the next user instruction) and the flags;
2. switches the privilege level to kernel;
3. jumps to the kernel's single entry address.

The kernel's entry code then:
4. switches to **this thread's kernel stack** and saves the user registers on it;
5. reads the **number** (57) and looks up entry 57 in the **system-call table**, an array of function pointers;
6. calls that function (for fork, the kernel's process-cloning function);
7. on return, restores the user registers and executes `sysret` (Arm64: `eret`), which drops back to user mode at the saved address.

So your picture "the instruction pointer goes to a fixed known address in RAM for that kernel function" needs one adjustment: the fixed address is the **single entry point**, and the specific function comes from the **table**. That's why adding a new system call means adding a table entry, not a new CPU feature.

### 3.4 Same thread, different stack

Throughout steps 1–7, **it's the same thread**: same TID, same scheduling entry. Only the mode and the stack changed. Every thread has two stacks:
- its **user stack**, in the process's address space (what your C# methods' frames live on);
- its **kernel stack**, a small fixed-size stack in kernel memory (about 16 KB on Linux x86-64/Arm64; Windows uses a similar fixed size), used whenever this thread runs kernel code.

The kernel needs its own stack because it can't trust the user stack (user code could point the stack pointer anywhere). And if the system call has to **wait** (for disk data, say), it's this thread that goes to sleep, in the middle of its kernel stack, and the scheduler runs something else (§5).

---

## 4. Interrupts: what the hardware does and what the code does 🟢

You wrote: "a pin goes high or there's an edge, a bit is set in a register, and on each cycle, based on the mask configuration and the global enable, the CPU will not execute the next instruction but jump to a fixed address", and then: "it needs to get all of those register values for switching into kernel mode somehow." Here's the full sequence.

**Getting to the CPU** (lecture `windows_internals/005` §3): the device signals the **interrupt controller** (the APIC on x86-64, the GIC on Arm64). The controller decides which CPU should take it and with what **vector** (a number identifying the interrupt), and raises that CPU's interrupt input.

**The check:** the CPU checks for a pending interrupt **between instructions** (not in the middle of one). It takes the interrupt only if interrupts are enabled: the `IF` flag in `RFLAGS` on x86-64, the `I` mask bit in `PSTATE` on Arm64. (Priority-based masking, like IRQL, is done in the interrupt controller: lecture 005.)

**What the hardware does, by itself, when it takes the interrupt:**

| Step | x86-64 | Arm64 |
|---|---|---|
| Find the handler | read entry `vector` of the **IDT** (table address in the `IDTR` register, set at boot) | jump to `VBAR_EL1` + a fixed offset for "IRQ from EL0" or "IRQ from EL1" |
| Switch privilege | to ring 0 | to EL1 |
| Switch stack | if coming from user mode: load the kernel stack pointer for this thread from the **TSS** (`RSP0`), which the kernel updates on every context switch | use `SP_EL1`, the kernel's stack pointer register |
| Save where it was | push old `SS`, `RSP`, `RFLAGS`, `CS`, `RIP` onto the kernel stack | old `PC` into `ELR_EL1`, old `PSTATE` into `SPSR_EL1` |
| Mask further interrupts | (interrupt gate clears `IF`) | sets `PSTATE.I` |
| Continue at | the handler address | the vector address |

That's all the hardware does: **mode, instruction pointer, stack pointer, and the few values needed to return.** Everything else is software:

**What the kernel's code does next:**
1. pushes the remaining general-purpose registers onto the kernel stack (now the interrupted code's whole register state is saved there);
2. loads whatever the kernel needs (for example a per-CPU data pointer) with ordinary instructions;
3. acknowledges the interrupt at the controller and calls the driver's ISR for that vector;
4. on the way out: maybe calls the scheduler (§5); then pops the registers and executes `iretq` (x86-64) / `eret` (Arm64), which restores the saved instruction pointer, flags and mode in one step.

So the answer to "how does it get all those register values" is: **it doesn't need to get them from anywhere special.** The hardware gives it a known stack and a known instruction pointer; from there it's just kernel code saving the old values and loading new ones, instruction by instruction.

**Exceptions** (page fault, divide by zero, invalid instruction) use the same mechanism with different vectors, raised by the CPU itself instead of a device. A page fault is how the kernel gets control when a thread touches a page that isn't mapped yet (lecture `windows_internals/008` §3), and it's how stacks grow (§6.2 and lecture 003).

---

## 5. The context switch, step by step 🟢

A context switch is the kernel, running on some CPU inside thread A, deciding that thread B should run on this CPU instead. It happens in kernel mode, on A's kernel stack, triggered by one of:

- **A blocks:** A made a system call that has to wait (read from an empty socket, wait on an event, `Sleep`). A marks itself *waiting* and calls the scheduler.
- **A's time slice ran out:** the timer interrupt's handler updated A's run time and decided another ready thread deserves the CPU; the switch happens on the way out of the interrupt.
- **B was woken with higher priority:** an interrupt or another thread signaled what B was waiting for, and B should run now.

The switch itself (on both OSes; details differ):

```
running in kernel mode, in thread A, on A's kernel stack:
 1. A's user-mode registers are already saved at the top of A's kernel stack (from the syscall/interrupt entry)
 2. schedule(): pick the next thread B from this CPU's run queue                       (§6)
 3. save A's remaining kernel registers and A's kernel stack pointer into A's thread structure
 4. if B's process ≠ A's process:
        load B's page-table root into CR3 (x86-64) / TTBR0_EL1 (Arm64)
        → from now on, the MMU translates user addresses using B's process's page tables
 5. load B's kernel stack pointer from B's thread structure          ← "now we are B"
    (and update the TSS / per-CPU data so the next interrupt uses B's kernel stack)
 6. restore B's kernel registers; return along B's kernel stack — which leads back to wherever B
    entered the kernel (its own syscall or interrupt, maybe seconds ago)
 7. B's exit path pops B's saved user registers and iretq/sysret/eret to B's saved user instruction pointer
```

Step 5 is the moment the CPU "becomes" B. Step 6 is the neat part: B returns from the very function it was in when **it** got switched out. From B's point of view, its `read()` system call just returned.

Step 4 is exactly what you described: "when the thread starts running, the context can be known by looking at the thread's associated process. This is what will tell us what the virtual memory is." Precisely: the thread structure points to its process; the process structure holds the page-table root; the switch loads it into the MMU's base register. Switching between two threads **of the same process** skips step 4, which is one reason thread switches are cheaper than process switches.

---

## 6. Where 1,000 threads live, and how the scheduler finds them 🟢

### 6.1 Where the context is stored

For a thread that isn't running, its context is:
- its **saved registers**, at the top of its kernel stack and in its thread structure;
- its **thread structure** (`KTHREAD`/`ETHREAD` on Windows, `task_struct` on Linux: a few KB);
- its **kernel stack** (about 16 KB on Linux; similar on Windows);
- its **user stack**, in its process's address space.

The first three are in **kernel memory**. Your intuition was right: all of it has to be stored somewhere, and it is, per thread. That's the per-thread cost lecture 003 measures. (Windows can page out the kernel stack of a thread that has waited a long time in user mode, a detail you can ignore for now. ⚫)

### 6.2 How big is a thread's user stack, really?

You read "a thread has 1 MB". That's the **reserved** size: a range of virtual addresses set aside so the stack can grow. Physical memory is used only for pages the thread actually touches:

- **Reserved** = address space only. No RAM.
- **Committed / resident** = pages that have been touched, backed by RAM.

When the stack grows into a new page, the CPU raises a page fault (§4), the kernel maps a fresh zeroed page there, and the thread continues. A thread that only ever uses a few KB of stack costs a few KB of RAM, not 1 MB.

On Windows the default reservation comes from the executable's header (the linker default is 1 MB). On Linux it's usually 8 MB. Lecture 003 measures 5,000 blocked threads: about 40 GB **reserved** but only about 130 MB **resident**.

### 6.3 Thread states

| State | Meaning | Where the thread is |
|---|---|---|
| **Running** | executing on a CPU right now | it's the current thread of that CPU |
| **Ready** | could run, waiting for a CPU | in a CPU's **run queue** |
| **Waiting** (blocked) | can't run until something happens | on the **wait list** of the thing it waits for |

There can be at most **one running thread per CPU core** (per hardware thread with SMT). With 1,000 threads on an 8-core machine, at most 8 are running. Most of the rest are waiting: for input, for a timer, for a network packet, for a lock. Open Task Manager's Performance tab: it shows a few thousand threads and a CPU at a few percent. Nearly all of those threads are waiting.

### 6.4 How the scheduler finds them

The scheduler never scans all threads. It only ever looks at **ready** threads, and those are kept in fast structures per CPU:

- **Windows:** each CPU has **ready queues by priority** (32 priority levels, one list per level) plus a bitmask of which lists are non-empty. "Pick the next thread" = find the highest set bit, take the first thread from that list.
- **Linux:** each CPU has a run queue. For normal threads it's a red-black tree ordered by how much CPU time each thread has received (weighted by priority); the next thread is the one that's had the least.

And the **waiting** threads:
- each waitable thing (an event, a mutex, a socket, a pipe) has a **wait list** of the threads waiting on it;
- when it's signaled (data arrives, an event is set), the kernel takes the waiting thread(s) off that list, marks them **ready**, and puts them on a run queue; if a CPU is idle, it sends that CPU an inter-processor interrupt to wake it up.

So a waiting thread costs memory but **no scheduler time**. It just sits on one list until the event it waits for moves it.

### 6.5 Multiple CPUs

Each CPU runs the scheduler for itself, on its own queues. A background part of the scheduler balances load (moving ready threads from a busy CPU's queue to an idle one), and wake-ups pick a CPU, preferring one where the thread ran recently (its data may still be in that CPU's cache).

---

## 7. "There is no orchestrator", made precise 🟢

You wrote: "There is no master orchestrator that is overseeing it... there is some timer which overflows and causes an interrupt... this is how the orchestration actually happens." That's the key insight, and it's correct. Made precise:

1. **The kernel is not a separate running program.** It's code and data mapped into every address space (kernel-only pages). It runs **on whichever CPU entered it, inside whichever thread was current**, on that thread's kernel stack.
2. **There are exactly three ways in:** system calls (a thread asks), exceptions (a thread's instruction faulted), and interrupts (a device or timer signaled).
3. **The scheduler is a function called on those paths:** when a thread blocks inside a system call, when a wake-up readies a higher-priority thread, and when the timer interrupt finds the current thread's time slice is used up. The timer is the **backstop** that guarantees the kernel gets control even if a thread never makes a system call (an infinite loop in user code).
4. **Kernel threads exist too** (Windows' System process threads, Linux's `kworker` threads), for work that should run independently of any user thread, such as the work items of lecture `windows_internals/005`. They're scheduled exactly like your threads; they aren't an orchestrator either.
5. **Modern kernels don't even need a periodic tick when idle:** an idle CPU programs its timer for the next actual deadline and sleeps (lecture `windows_internals/016` §2: this is why wake-ups cost battery).

So the "orchestra" is: every CPU runs threads; control enters the kernel only through those doors; while in the kernel, the CPU may switch which thread it runs. The coordination between CPUs is through shared kernel data (the queues, protected by spin locks: the DISPATCH_LEVEL rules from lecture 005) and inter-processor interrupts.

---

## 8. One full trace: a key press wakes a thread

Your editor's UI thread is waiting for input; your C# program's thread is computing on the same CPU. You press a key.

| # | What happens | Mode | Thread on this CPU |
|---|---|---|---|
| 1 | Your C# thread runs a loop | user | C# thread |
| 2 | Keyboard controller → interrupt controller → this CPU's interrupt input | | |
| 3 | CPU finishes the current instruction; interrupts enabled → takes it: kernel mode, C# thread's kernel stack, save `RIP`/flags, jump via the vector table | kernel | **C# thread** (still!) |
| 4 | Kernel entry saves the rest of the registers; keyboard driver's ISR reads the key, queues deferred work | kernel | C# thread |
| 5 | Deferred work delivers the key to the input system, which signals the editor's UI thread's wait → UI thread moves from its wait list to a run queue; it's higher priority (foreground input boost) | kernel | C# thread |
| 6 | On interrupt exit, the scheduler sees a higher-priority ready thread → context switch (§5) | kernel | C# thread → **UI thread** |
| 7 | The UI thread returns from its own earlier wait call (it entered the kernel minutes ago) back to user mode; it handles the key | user | UI thread |
| 8 | UI thread finishes, waits for the next message → blocks → scheduler picks the C# thread → it resumes its loop exactly where it was | user | C# thread |

Notice rows 3–6: the kernel ran **inside your C# thread** to handle an interrupt that had nothing to do with it. That's the "no orchestrator" model in action.

---

## 9. See it yourself

**Linux (your Pi, or a Linux VM):**
```bash
ps -o pid,ppid,nlwp,cmd -p $$          # your shell: its PID, its parent, number of threads (nlwp)
sleep 100 &                            # start a child
ps -o pid,ppid,stat,cmd --ppid $$      # the child: PPID = your shell; STAT S = sleeping (waiting)
strace -f -e trace=clone,execve bash -c '/bin/ls > /dev/null'   # watch fork (clone) then execve
cat /proc/$$/status | grep -E 'Threads|voluntary_ctxt'          # context-switch counts for your shell
ls /proc/$(pgrep -n dotnet)/task       # one directory per thread of a running .NET app
```

**Windows (your VM):**
- Task Manager → Details → add the **Threads** column: every process, its thread count.
- Process Explorer (Sysinternals): a process's **Threads** tab shows each thread's start address, state and context switches.
- WinDbg on a dump or local kernel debugging (lecture `windows_internals/013`): `!process 0 0` lists processes; `!thread <addr>` shows a thread's state (WAIT, READY, RUNNING), what it waits on, and its kernel stack.
- WPA's CPU Usage (Precise) (lecture `windows_internals/015`): every context switch, with who woke whom.

---

## Misconceptions

| You might think | Reality | Why it matters |
|---|---|---|
| Shell commands are scripts | Mostly compiled executables; some built-ins; some scripts with `#!` | Explains why `cd` is special, and what `execve` loads |
| `fork` is an instruction | A library function that executes `syscall`/`svc` | The kernel has one entry point and a table |
| Entering the kernel switches to a kernel thread | Same thread, its kernel stack | Why a blocking system call puts **your** thread to sleep |
| The kernel is a separate program watching everything | Code that runs inside threads on each CPU when entered | There's no extra "OS thread" doing the scheduling |
| Many threads are "running" | ≤ one per core; most are waiting | Waiting threads cost memory, not CPU |
| A thread costs its full stack size in RAM | Reserved ≠ committed; RAM only for touched pages | Lecture 003's thread-vs-async comparison depends on this |
| The scheduler loops over all threads | Picks from per-CPU ready queues; waiting threads sit on wait lists | Why thousands of idle threads don't slow scheduling |

---

## Self-check questions

1. What does a process own, and what does a thread own? Which one does the scheduler schedule?
<details><summary>Answer</summary>Process: address space (page tables), handles/file descriptors, security identity, PID. Thread: register state (IP, SP, general registers), user stack, kernel stack, scheduling state, TID, and a pointer to its process. The scheduler schedules threads.</details>

2. You type `ls > out.txt` in bash. Describe the system calls, in order, and why there are two steps.
<details><summary>Answer</summary>The shell calls fork (via clone): a child copy of the shell with a new PID. The child, still running shell code, opens out.txt and makes it its standard output, then calls execve("/usr/bin/ls", ...), which replaces its program with ls (same PID). The parent waits for the child. Two steps so the child can set up redirections and pipes before the new program starts.</details>

3. How does Windows start a program differently?
<details><summary>Answer</summary>No fork: CreateProcess → NtCreateUserProcess creates a new process object and address space, maps the executable and ntdll, and creates the initial thread directly. That thread runs ntdll's loader, which loads DLLs and calls the program's entry point.</details>

4. Where is "user mode vs kernel mode" stored on x86-64 and on Arm64?
<details><summary>Answer</summary>x86-64: the current privilege level, the low 2 bits of the CS register (ring 3 user, ring 0 kernel). Arm64: the current exception level in PSTATE (EL0 user, EL1 kernel).</details>

5. What exactly happens when user code executes `syscall`? How does the kernel know which function to run?
<details><summary>Answer</summary>The CPU saves the return address and flags, switches to kernel mode, and jumps to the single entry address the kernel stored in a CPU register (LSTAR) at boot. The entry code switches to the thread's kernel stack, saves user registers, reads the system-call number from a register (rax / x8), and calls the function at that index of the system-call table. It returns with sysret/eret.</details>

6. When a thread makes a system call, does a different thread run the kernel code?
<details><summary>Answer</summary>No. The same thread continues in kernel mode, on its own kernel stack. If the call must wait, that same thread goes to sleep and the scheduler runs another thread.</details>

7. On an interrupt, which registers does the hardware switch by itself, and who saves the rest?
<details><summary>Answer</summary>The hardware switches the privilege level, the instruction pointer (to the handler from the IDT / vector table) and the stack pointer (to the kernel stack), and saves the old instruction pointer and flags (plus old SS/RSP on x86-64; ELR/SPSR on Arm64). The kernel's entry code saves all the other registers with ordinary instructions.</details>

8. List the steps of a context switch from thread A to thread B in a different process. Which step changes how the MMU translates addresses?
<details><summary>Answer</summary>A's user registers are already saved on its kernel stack; the scheduler picks B from the run queue; save A's kernel registers and kernel stack pointer in A's thread structure; load B's process's page-table root into CR3 / TTBR0_EL1 (this changes the MMU translation); load B's kernel stack pointer; restore B's registers and return along B's kernel stack to where B entered the kernel; return to user mode at B's saved instruction pointer.</details>

9. A machine has 1,500 threads and 8 cores. How many can be running? Where are the others, and what does the scheduler look at when picking the next thread?
<details><summary>Answer</summary>At most 8 running. Most others are waiting, each on the wait list of the event/socket/timer it waits for; a few are ready, in per-CPU run queues. The scheduler only looks at its CPU's ready queue (priority lists + bitmap on Windows; a tree ordered by received CPU time on Linux), never at waiting threads.</details>

10. A thread has a 1 MB stack. How much RAM does it use for that stack?
<details><summary>Answer</summary>Only the pages it has actually touched (often a few KB to tens of KB). The 1 MB is a reservation of virtual addresses; pages are committed and given RAM on first touch, via a page fault.</details>

11. Is the scheduler a thread? What runs it?
<details><summary>Answer</summary>No. It's a kernel function, called in kernel mode by whatever thread is current on that CPU, on the paths where a decision is needed: when a thread blocks, when a wake-up readies a higher-priority thread, and on timer interrupts when a time slice expires.</details>

---

## Sources

- Linux man pages: [fork(2)](https://man7.org/linux/man-pages/man2/fork.2.html), [execve(2)](https://man7.org/linux/man-pages/man2/execve.2.html), [syscall(2)](https://man7.org/linux/man-pages/man2/syscall.2.html) (per-architecture instruction and number register: `syscall`/`rax` on x86-64, `svc #0`/`x8` on arm64). Checked 2026-11-01.
- Linux kernel docs, [Kernel stacks on x86-64](https://docs.kernel.org/arch/x86/kernel-stacks.html) and [CFS / EEVDF scheduler design](https://docs.kernel.org/scheduler/sched-design-CFS.html). Checked 2026-11-01.
- Microsoft Learn, [Creating processes](https://learn.microsoft.com/en-us/windows/win32/procthread/creating-processes) and [Thread Stack Size](https://learn.microsoft.com/en-us/windows/win32/procthread/thread-stack-size) (reserve vs commit; 1 MB linker default). Checked 2026-11-01.
- Microsoft Learn, [Scheduling Priorities](https://learn.microsoft.com/en-us/windows/win32/procthread/scheduling-priorities) (32 levels). Checked 2026-11-01.
- Intel® 64 and IA-32 Architectures Software Developer's Manual, Vol. 3A: ch. 5 (protection, CPL), ch. 6 (interrupt and exception handling, IDT, stack switching via TSS); `SYSCALL`/`SYSRET` in Vol. 2.
- Arm Architecture Reference Manual for A-profile: exception levels, `SVC`, `VBAR_EL1`, `ELR_EL1`/`SPSR_EL1`, `TTBR0_EL1`.
- Yosifovich, Ionescu, Russinovich, Solomon, *Windows Internals, Part 1*, 7th ed. (2017), ch. 3 (processes, `CreateProcess` flow) and ch. 4 (threads, scheduling, ready queues, context switching).
- Lab numbers (9 runtime threads; 5,000 threads reserved vs resident): `code/ConcurrencyLab`, run 2026-11-01 (see lecture 003).
