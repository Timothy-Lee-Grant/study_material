# From Bare Metal to an OS, Part 3: Pageable Memory, Blue Screens, and How Linux Compares (audio lecture)

This is the last part of a three-part series. Part one placed every component in a laptop's touchscreen path. Part two followed an interrupt from a wire to a driver's handler and explained IRQL, the per-processor priority level. Part three covers memory: what virtual memory and pages are, what "pageable memory" means, why touching it from the wrong place produces a blue screen, who actually performs that check, and how the same problems look on Linux.

## Why this matters to Timothy

The interview lecture listed two blue-screen codes, hex A and hex D-one, and described them as "touched pageable memory at elevated IRQL." Timothy said he wasn't sure what that phrase meant or who was doing the touching. His guess was that the kernel was verifying a separate process to see whether it was allowed to do something. That's half right, and the half that's wrong is the important half. He also asked how Linux compares. By the end of this episode he should be able to tell the whole story of that crash, from a variable in memory to a blue screen, and translate it into Linux terms.

## The core ideas

Here are today's core ideas. They're the answer key for the walk questions at the end.

One. Code uses virtual addresses. The processor translates them into physical addresses using page tables, in units of four-kilobyte pages.

Two. Pageable memory is memory the memory manager is allowed to move to disk. Nonpaged memory is guaranteed to stay in RAM.

Three. Touching a page that's currently on disk makes the processor raise a page fault. Fixing a page fault means reading the disk, and reading the disk means waiting.

Four. Waiting is impossible at the DISPATCH level or above. So when kernel code at that level touches a page that's on disk, the kernel's own page-fault handler checks the level, finds the rule broken, and stops the machine on purpose. That's bug check hex A, or hex D-one when the code belongs to a driver.

Five. The whole machine stops because kernel drivers share one room with the kernel. There's no wall that could contain the damage, unlike a user process.

Six. Driver Verifier makes this hidden bug show up every time, by pushing pageable memory out whenever a driver raises its level.

Seven. Linux has the same hardware and the same problems. But it never pages kernel memory, and it describes priority as contexts instead of numbers. Its rule is "never sleep in atomic context", and its threaded interrupt is the equivalent of the Windows passive-level handler.

## Section one: virtual memory in plain words

Timothy's ATmega has no virtual memory: an address in his code is a real location in the chip's RAM. A laptop processor adds a translation step. Every address that code uses is a virtual address. The processor converts it to a physical address, a real location in the RAM chips, using lookup structures called page tables, in chunks called pages. On sixty-four-bit Intel and AMD machines a page is four kilobytes.

Each process has its own page tables, which is what gives each process its private room: the same virtual address in two processes leads to two different physical places. Kernel mode has one shared set of page tables, which is the shared kernel room from part one.

Here's the key feature. A page-table entry can say "not present", meaning this page isn't in RAM right now. Why would a page be missing? Because RAM is limited. When memory gets tight, Windows' memory manager picks pages that haven't been used recently, writes their contents to a file on disk called the page file, and gives the RAM to something that needs it more. If the old page is touched again later, its contents are read back in.

That "read back in" is triggered by the processor itself. When code touches a not-present page, the processor stops the instruction and raises an event called a page fault. It goes through the same interrupt descriptor table from part two: slot fourteen. The kernel's memory manager handles it. It finds where the page's contents are in the page file, gets a free physical page, starts a disk read, waits for the read to finish, fixes the page table, and restarts the instruction as if nothing had happened. Application code never notices. It just occasionally runs a little slower.

Notice the word in the middle of that sequence: waits.

## Section two: pageable and nonpaged

Now the phrase from the interview lecture. Pageable memory is memory the memory manager is allowed to move to disk. All user-mode memory is pageable. In the kernel, drivers choose. A driver can allocate from the paged pool, which may be moved to disk, or from the nonpaged pool, which is guaranteed to stay in RAM. A driver can also mark some of its own functions as pageable, so that rarely used code doesn't occupy RAM. Microsoft gives drivers a check, a line called PAGED-underscore-CODE placed at the top of such a function, which in debug builds confirms the function is being called at a low enough level.

Why bother with pageable kernel memory at all? Because RAM is precious, and a laptop has hundreds of drivers. Code that runs once at startup, or only when a setting changes, doesn't need to sit in RAM forever.

## Section three: the crash, step by step

Here's the full story of the crash, one step at a time.

Step one. A driver is running at the DISPATCH level or higher. It might be in its interrupt handler, or a deferred procedure call, or it might be holding a spin lock, which also raises the level.

Step two. It reads a variable that lives in pageable memory. Most of the time that page is in RAM, and nothing happens at all.

Step three. But today the laptop is low on memory, and that page was moved to disk. The processor raises a page fault.

Step four. The page-fault handler would need to wait for the disk. From part two: at DISPATCH or above, waiting is impossible, because the scheduler can't run.

Step five. So the handler checks the current level, sees it's too high, and calls the kernel's deliberate stop function, named K-E-bug-check-E-X. The machine shows a blue screen with stop code hex A, IRQL-not-less-or-equal. When the faulting instruction belongs to a driver, it shows hex D-one, driver-IRQL-not-less-or-equal.

The name reads as the rule that was broken. The level should have been less than or equal to the highest level at which paging is allowed, and it wasn't. The blue screen also carries four numbers: the address that was touched, the level at the time, whether it was a read or a write, and the address of the instruction that did it. Those four numbers are the first thing an engineer on Timothy's interview team would look at.

Pause and predict. Timothy's guess was that the kernel was verifying a separate process. Which part is right, and which part is wrong?

The right part: it is the kernel checking a rule. The wrong part: no separate process is involved. The code that broke the rule is a driver, and a driver is inside the kernel's own shared room. The kernel catches it in the act, through its own page-fault handler. The same two codes also appear when a driver follows a garbage pointer at a high level, because a garbage address faults the same way.

## Section four: why the whole machine stops

When an application touches invalid memory, Windows kills that application with an access violation, and everything else carries on. That works because the application lives in its own room, with its own page tables.

When kernel code breaks a rule, there's no wall. That driver shares memory with the file system, the network stack, and every other driver. Carrying on might write corrupted data to the disk. So the kernel stops everything on purpose and writes a crash dump, a snapshot of memory that an engineer can open later in the debugger, WinDbg (said "win-debug"). A blue screen isn't the computer falling over at random. It's the kernel's self-check firing, and the stop code names the rule.

## Section five: why this bug hides, and how to catch it

This bug has a nasty property. In step two, the page is usually in RAM, so the driver passes every test on a developer's machine with plenty of memory. Then it crashes one customer laptop in a thousand, under memory pressure, apparently at random. That's exactly the kind of "intermittent failure on a new platform" the reliability team gets called about.

The tool that makes it reproducible is Driver Verifier, which is built into Windows. With its IRQL-checking option turned on, whenever a driver raises its level to DISPATCH or higher, or takes a spin lock, Verifier first pushes that driver's pageable code and data out of RAM. The first illegal touch then faults every single time, with a clear stop code pointing at the driver. In an interview, that one sentence shows you know how to turn an intermittent failure into a deterministic one.

## Section six: Linux, same problems, different names

Now Timothy's question about Linux. The hardware underneath is identical: the same interrupt controllers, the same GPIO controllers, the same HID-over-I2C touch chips. Both kernels face the same three problems from part two: waiting needs the scheduler, many drivers share one processor, and memory might need to be fetched. The answers differ in vocabulary, and in one real way.

First, the vocabulary. Linux has no numbered IRQL. It describes where code is running as a context. Hard interrupt context is an interrupt handler. Soft interrupt context is short deferred work, similar to a Windows deferred procedure call. Process context is ordinary thread code, which may sleep. Code that must not sleep (interrupt handlers, soft interrupts, anything holding a spinlock, anything that has disabled preemption) is said to be in "atomic context." So the Windows rule "never wait at DISPATCH or above" becomes the Linux rule "never sleep in atomic context." Same rule, different wording.

Second, registering a handler. On Linux a driver calls a function named request-I-R-Q, passing its handler. On shared lines the handler answers "handled" or "none", just like the Windows true or false from part two. And the Windows passive-level handler from part two has a direct Linux twin: the threaded interrupt. A driver calls request-threaded-I-R-Q with a flag called I-R-Q-F-ONESHOT. That keeps the interrupt line masked until the driver's thread function finishes, so the thread can sleep while it reads the device over I2C. Linux's own HID-over-I2C driver does exactly this. Mask, read in a thread, unmask: the same design reached independently, because the same physics forces it.

Third, the real difference. Linux never pages kernel memory out to disk. Kernel allocations stay in RAM. So the whole category of "touched pageable memory at a high level" doesn't exist for kernel data on Linux. The rule collapses into one: don't sleep in atomic context. What breaks it there? Taking a mutex. Allocating memory with the flag that's allowed to sleep; atomic code must use the atomic flag instead. And copying from user memory, because user memory can be swapped out, so touching it can fault and sleep. That last case is exactly where the Windows rule reappears on Linux. When a Linux driver breaks the rule, a debug-enabled kernel prints "BUG: sleeping function called from invalid context", and the scheduler prints "BUG: scheduling while atomic." Those two messages are Linux's hex D-one.

A few more translations, briefly. Windows has blue screens and crash dumps. Linux has an "oops", which can sometimes continue with the kernel marked as tainted, and a "panic", which stops, plus kdump for saving memory. Windows describes laptop hardware with ACPI tables. Linux uses ACPI on Intel and AMD laptops too, but on most Arm boards, including Timothy's Raspberry Pi, it uses a device tree. And for watching interrupts, Linux has something very convenient: one command prints the file slash-proc-slash-interrupts, which shows how many times each interrupt has fired on each processor. If a touchscreen's count stops climbing while the finger is on the glass, you've found where the chain broke.

Pause and predict. A Linux driver's interrupt handler calls a function that takes a mutex. What does the kernel print, and what's the Windows equivalent?

The answer: "BUG: sleeping function called from invalid context", or, if it actually sleeps, "BUG: scheduling while atomic." The Windows equivalent is a wait at DISPATCH or above, which ends in a bug check.

## Section seven: which to study first

For the Microsoft role, learn the Windows names first, because they're what the interviewer will expect: IRQL, deferred procedure call, work item, the Kernel-Mode Driver Framework, bug check, Driver Verifier, WinDbg. For hands-on practice, Linux on the Raspberry Pi is cheaper and more visible. Timothy could write a fifty-line kernel module with a threaded interrupt, watch the count in slash-proc-slash-interrupts climb, put a logic analyzer on the line, and deliberately reproduce a storm and a missed edge. The concepts transfer one to one, as long as he says the Windows names in the interview.

## Connections

This episode closes the loop on the interview. The I2C-in-an-interrupt-handler question, the blue-screen codes, and the touchscreen-dead-until-reset question all sit on the same three facts: kernel mode is one shared room, the scheduler lives at DISPATCH, and some memory might be on disk. It also connects back to Timothy's earlier Raspberry Pi work, where root access and memory mapping decided what his pigpio program could touch. That was the same idea of rooms and permissions, seen from user mode.

## Recap

The core ideas once more, in different words. Addresses are virtual, translated through page tables in four-kilobyte pages. Pageable memory may be sitting on disk, and touching it then causes a page fault, which can only be fixed by waiting for the disk. Waiting is impossible at DISPATCH and above, so the kernel's page-fault handler, finding kernel code breaking that rule, deliberately stops the machine with hex A or hex D-one. The whole machine stops because drivers share the kernel's room. Driver Verifier turns this rare crash into a certain one. And Linux keeps the same rule in a different form: it never pages kernel memory, it says "atomic context" instead of a number, and its threaded interrupt mirrors Windows' passive-level handler.

## Walk questions

Here are three questions to answer out loud on the next walk.

First: tell the story of bug check hex D-one, from a driver reading a variable to the blue screen, and name who performs the check.

Second: why does a driver bug stop the whole computer, when an application bug only kills the application?

Third: translate the Windows rule "never wait at DISPATCH or above" into Linux terms, and explain why Linux doesn't have the pageable-kernel-memory version of the bug.
