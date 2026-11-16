# How a CPU Actually Executes a Program

## A guided lecture on instruction fetching, virtual memory, the MMU, registers, data, and the execution pipeline

------------------------------------------------------------------------

## Learning goals

By the end of this lecture, you should be able to explain:

1.  Why a CPU does **not** need to execute an instruction in order to
    fetch its first instruction.
2.  What the program counter (PC / instruction pointer) actually stores.
3.  How the instruction-fetch hardware, MMU, TLB, caches, memory
    controller, and RAM cooperate.
4.  Why fetching an instruction and reading data are related but
    distinct operations.
5.  Where machine instructions, variables, structs, stacks, and heaps
    live.
6.  How an instruction describes an operation, operands, and sometimes a
    memory address.
7.  Why virtual addresses are normally used by application code.
8.  What "32-bit" and "64-bit" mean---and what they do *not* mean.
9.  Why instruction execution takes multiple stages and does not all
    happen in one clock cycle.
10. How interrupts, exceptions, system calls, and context switches fit
    into this picture.

The goal is not to memorize every hardware detail. It is to build a
reliable mental model of the major components and how information moves
between them.

------------------------------------------------------------------------

# Part 1 --- Start with the central misconception

## 1. The apparent chicken-and-egg problem

Your original reasoning raised a very good question:

> The CPU needs an instruction to do anything. But it needs to do
> something to fetch the instruction. So how can it ever start?

This sounds like a circular dependency, but it comes from one incorrect
assumption:

**Fetching an instruction is not itself an ordinary software instruction
that the CPU must execute.**

A processor is not one indivisible thing that waits for a machine-code
instruction before any part of it can operate. A CPU is a collection of
hardware components connected by control and data paths.

Some components are specifically designed to fetch instructions. Other
components decode them. Other components perform arithmetic, calculate
addresses, access memory, and manage registers.

Those circuits operate because of electrical signals and clocked state
transitions---not because another software instruction tells each
individual circuit how to function.

For example, the instruction-fetch hardware has a job: request the bytes
located at the address indicated by the program counter. It does not
need a software instruction saying "fetch the next instruction." That
behavior is part of the processor's hardware design.

### A useful analogy

Imagine a conveyor belt in a factory.

A box arrives at a scanner. The scanner reads its barcode. A sorting
mechanism then directs the box to the correct location.

The scanner does not need to read a barcode that says "please scan this
barcode" before it can operate. Scanning is the scanner's built-in
function.

Likewise, instruction-fetch hardware does not need to execute a machine
instruction to know that it should fetch instruction bytes.

### Hardware versus software

Keep these two categories separate:

  -----------------------------------------------------------------------
  Hardware                            Software
  ----------------------------------- -----------------------------------
  Physical circuits and state         Instructions and data represented
  elements                            in memory

  Responds to electrical inputs and   Supplies commands and values that
  clock transitions                   hardware processes

  Includes fetch units, decoders,     Includes operating systems,
  ALUs, register files, MMUs, caches  applications, libraries, drivers

  Can perform dedicated operations    Uses the hardware to carry out the
  without running a software routine  program's logic
  for each step                       
  -----------------------------------------------------------------------

A useful qualification: not every hardware component is a purely
combinational circuit. Some components contain state (registers, queues,
caches, counters, and finite-state machines). They are still hardware,
and their behavior is implemented in circuits.

------------------------------------------------------------------------

# Part 2 --- What is physically inside a CPU?

## 2. The CPU is a collection of cooperating components

A simplified modern CPU contains or interacts with components such as:

-   **Program counter (PC):** holds the address associated with the next
    instruction to fetch.
-   **Instruction-fetch logic:** requests instruction bytes and supplies
    them to later stages.
-   **Instruction cache:** stores recently used instruction bytes close
    to the processor.
-   **Instruction decoder:** interprets the instruction encoding.
-   **Register file:** stores architectural registers such as
    general-purpose registers.
-   **Execution units:** perform arithmetic, logical operations, shifts,
    and other work.
-   **Load/store hardware:** handles memory reads and writes requested
    by instructions.
-   **MMU:** supports address translation and memory protection.
-   **TLB:** caches recent address translations.
-   **Control logic:** coordinates the operation of the processor.
-   **Pipelines and buffers:** allow multiple instructions to be in
    different stages of processing at once.

The exact organization differs between processor architectures and
implementations. Some components are integrated into the CPU core;
others, such as parts of the memory controller or system-level cache,
may be elsewhere in the chip or system.

### A conceptual diagram

``` text
                    +----------------------+
                    |     Program Counter  |
                    |          (PC)        |
                    +----------+-----------+
                               |
                               v
                    +----------------------+
                    |   Instruction Fetch  |
                    +----------+-----------+
                               |
                               v
                    +----------------------+
                    |  Address Translation |
                    |      MMU / TLB       |
                    +----------+-----------+
                               |
                               v
                    +----------------------+
                    | Instruction Cache / |
                    | Memory Hierarchy     |
                    +----------+-----------+
                               |
                         instruction bytes
                               |
                               v
                    +----------------------+
                    |  Instruction Decoder |
                    +----------+-----------+
                               |
                       decoded operations
                               |
              +----------------+----------------+
              |                |                |
              v                v                v
        +-----------+    +-----------+    +-------------+
        | Registers |    | ALU /     |    | Load / Store|
        |           |    | Execution |    | Hardware    |
        +-----------+    +-----------+    +------+------+
                                                |
                                                v
                                        MMU / TLB and
                                        memory hierarchy
```

This is a teaching diagram, not a literal chip floorplan. Real CPUs have
more stages, more buffers, multiple execution units, and complex
interconnections.

## 3. What does the clock do?

A CPU clock provides a timing reference. In a synchronous digital
circuit, clock edges are used to coordinate when state elements capture
new values.

A clock cycle is **not** a promise that an entire instruction completes
in one cycle.

Some operations may take one cycle; others take several cycles. A cache
miss or page-table walk can take many cycles. Modern processors also
overlap work from different instructions, so several instructions can be
in progress simultaneously.

Think of the clock as a shared rhythm for coordinating hardware---not as
a rule that one complete instruction must happen per tick.

------------------------------------------------------------------------

# Part 3 --- The first instruction: how does fetching begin?

## 4. The program counter

The program counter (called the **instruction pointer** in x86
terminology) is a CPU register that holds the address used to identify
the next instruction to fetch.

For a normal user-mode process using virtual memory, this is generally a
**virtual address**.

For example, imagine:

``` text
PC = 0x00401000
```

This means that the processor should fetch instruction bytes beginning
at virtual address `0x00401000`.

It does *not* mean that the bytes are necessarily stored at physical RAM
address `0x00401000`.

The virtual address belongs to the process's virtual address space.
Hardware translates it when the memory system needs to access the
corresponding memory.

### Important distinction: the PC is not the instruction

The PC contains an address. The instruction bytes are stored somewhere
in the memory hierarchy.

Conceptually:

``` text
PC register:       0x00401000
                         |
                         | address request
                         v
Virtual address:   0x00401000
                         |
                         | translation
                         v
Physical address:  0x12345000
                         |
                         | retrieve bytes
                         v
Instruction bytes: 48 89 D8 ...
```

The physical address above is illustrative. The translation is
determined by the active address-space mappings.

## 5. Where does the initial PC value come from?

The processor does not spontaneously guess where a program begins.

At system startup, the processor begins from an architecturally defined
reset state and reset location. Firmware and boot software then
initialize the machine and eventually arrange for an operating system to
run.

When the operating system starts a user process, it creates the
process's virtual-memory mappings, loads or maps the executable,
initializes the process's execution state, and arranges for execution to
begin at the program's entry point.

The OS sets up the relevant processor state, including the instruction
pointer and other required registers, as part of transferring control to
the new process.

So there are two related but different starting situations:

-   **Machine boot:** the CPU begins at a hardware-defined reset
    location and firmware starts the boot process.
-   **Starting an application:** the OS prepares the application's
    memory and execution context, then transfers control to its entry
    point.

The CPU's fetch hardware works in both cases. The difference is which
address space and execution state are active.

------------------------------------------------------------------------

# Part 4 --- Virtual addresses and the MMU

## 6. Why virtual memory exists

A program normally uses virtual addresses rather than directly choosing
physical RAM locations.

Virtual memory provides several important benefits:

1.  **Isolation:** one process normally cannot freely read or overwrite
    another process's memory.
2.  **Relocation:** a program can use a consistent virtual address
    layout without needing to know where its data resides in physical
    RAM.
3.  **Protection:** memory pages can have permissions such as readable,
    writable, and executable.
4.  **Sharing:** multiple processes can map the same physical memory
    when appropriate.
5.  **Demand paging:** some pages can be brought into physical memory
    only when needed.

Each process has a virtual address space. The OS and hardware cooperate
to map portions of that address space to physical memory.

## 7. What does the MMU do?

The **Memory Management Unit (MMU)** is hardware that supports address
translation and memory protection.

A simplified translation looks like this:

``` text
Virtual address
      |
      v
+-------------+
|     TLB     |  Is there a cached translation?
+------+------+
       |
       +---- TLB hit ----------------------+
       |                                   |
       v                                   v
  Page-table walk                    Physical address
  (if needed)                              |
       |                                   |
       v                                   v
  Translation found                  Memory access
```

The MMU is not a program that runs through software instructions to
translate every address. The translation mechanism is implemented in
hardware.

However, the operating system is involved in setting up and managing the
page tables. If a translation fails because a page is absent or access
is not permitted, the processor may raise an exception (often called a
page fault), and the OS handles it.

## 8. The TLB: why page tables are not consulted from scratch every time

Page tables are data structures in memory that describe
virtual-to-physical mappings.

Looking up a translation through page tables can require multiple memory
accesses. Doing that from scratch for every instruction fetch and every
data access would be expensive.

Processors therefore use a **Translation Lookaside Buffer (TLB)**.

The TLB is a small, fast cache of recent address translations.

For example:

``` text
Virtual page 0x00401  -> Physical frame 0x12345
Virtual page 0x00402  -> Physical frame 0x98765
Virtual page 0x7FFF0  -> Physical frame 0x45678
```

If the processor needs an address in virtual page `0x00401`, it may find
the translation in the TLB and avoid walking the page tables.

A TLB entry generally maps a virtual page to a physical page frame,
along with permission and other information. The offset within the page
is preserved.

### Page translation: page number plus offset

A virtual address can be thought of as two pieces:

``` text
+----------------------+------------------+
| Virtual page number  | Page offset      |
+----------------------+------------------+
```

The translation changes the page number into a physical frame number.
The offset within the page remains the same.

For example, with a hypothetical 4 KiB page:

-   Page size = 4096 bytes.
-   Offset = 12 bits, because 2\^12 = 4096.
-   The virtual page number identifies which virtual page is being
    accessed.
-   The physical frame number identifies the corresponding physical page
    frame.

The result is a physical address:

``` text
+-----------------------+------------------+
| Physical frame number | Same page offset |
+-----------------------+------------------+
```

## 9. What if the TLB misses?

A TLB miss does not automatically mean the program has an invalid
address.

It simply means the translation was not found in the TLB.

The processor's hardware may perform a **page-table walk** to locate the
mapping in memory. If the mapping exists and permissions allow the
access, the translation can be cached in the TLB.

If the mapping is absent or the access violates permissions, the
processor raises a page fault or another relevant exception. The OS then
decides what to do.

For example, the OS might:

-   Bring a page in from storage.
-   Allocate a new physical page.
-   Copy a page to implement copy-on-write.
-   Reject the access and terminate the process.

The exact behavior depends on the reason for the fault.

------------------------------------------------------------------------

# Part 5 --- How instruction bytes reach the processor

## 10. The instruction does not travel through a magical direct wire from RAM

It is useful to think in terms of **requests, interconnects, caches, and
data transfers**, rather than imagining that a particular RAM block is
directly wired to the CPU.

A simplified instruction-fetch path is:

1.  The PC supplies the virtual address for the next instruction.
2.  Instruction-fetch hardware requests bytes at that address.
3.  Address translation determines the physical location and checks
    permissions.
4.  The memory hierarchy looks for the bytes in a nearby cache.
5.  If necessary, a request travels through the system's memory
    interconnect to the memory controller.
6.  The memory controller coordinates access to DRAM.
7.  The returned bytes travel back through the memory hierarchy to the
    processor.
8.  Instruction bytes are placed in fetch buffers and supplied to the
    decoder.

The details vary by CPU. Translation and cache access can overlap in
some implementations, and the cache organization may include
virtual-address and physical-address stages.

The essential point is that the CPU has dedicated hardware to request
and receive instruction bytes.

## 11. The memory hierarchy

RAM is not the only place from which the CPU can obtain instructions or
data.

A typical hierarchy is:

  -----------------------------------------------------------------------
  Storage                 Approximate location    Typical role
  ----------------------- ----------------------- -----------------------
  Registers               Inside the CPU core     Immediate operands and
                                                  results

  L1 cache                Very close to a core    Very fast
                                                  instruction/data
                                                  storage

  L2 cache                Usually close to a core Larger cache

  L3 / last-level cache   Often shared among      Larger shared cache
                          cores                   

  DRAM                    Main memory modules     Working memory for
                                                  processes

  SSD / other storage     Outside main memory     Persistent files and
                                                  backing storage
  -----------------------------------------------------------------------

Caches hold copies of data from lower levels of the hierarchy. They do
not normally replace RAM as the program's main memory.

A CPU can execute an instruction whose bytes are already in its
instruction cache without fetching those bytes from DRAM at that moment.

Similarly, a load instruction might obtain data from a data cache rather
than main RAM.

### Instruction cache versus data cache

Many processors distinguish between:

-   **Instruction cache (I-cache):** caches instruction bytes.
-   **Data cache (D-cache):** caches data read and written by
    instructions.

This is often called a split L1 cache. Higher levels may be unified,
meaning they hold both instructions and data.

This distinction helps explain how the CPU can keep instruction bytes
available while separately reading or writing data.

------------------------------------------------------------------------

# Part 6 --- Instructions and data are different things

## 12. RAM contains both instructions and data

A process's memory is not just one long list of machine instructions.

It contains different kinds of information, including:

-   Executable machine-code bytes.
-   Global and static variables.
-   Stack memory for function calls and local variables.
-   Heap allocations.
-   Read-only constants.
-   Runtime and library data.
-   Other memory-mapped regions.

The operating system and executable format establish a process memory
layout. The exact layout depends on the OS, executable format, compiler,
runtime, and security features.

A conceptual process address space might look like this:

``` text
Higher virtual addresses
+------------------------------+
| Stack                        |
| Local variables, call frames |
|                              |
|            ...               |
|                              |
| Heap                         |
| Dynamic allocations          |
|                              |
| Global / static data         |
|                              |
| Program code                 |
| Executable instructions      |
+------------------------------+
Lower virtual addresses
```

This is a simplified illustration. Real layouts vary, and the stack and
heap may grow in different directions or be arranged differently.

## 13. What happens to a C struct?

Consider:

``` c
struct Person {
    int age;
    int height;
};

int main(void) {
    struct Person person;

    person.age = 30;
    person.height = 180;

    return person.age;
}
```

The compiler translates the program into machine instructions.

The `person` variable is not necessarily represented as a special
"struct object" that the CPU understands. A C struct is primarily a
language-level description of a memory layout.

For this example, assuming a common implementation where `int` is four
bytes and there is no padding between these members, the object may
occupy eight bytes:

``` text
person:
+----------------------+----------------------+
| age: 30              | height: 180           |
| 4 bytes              | 4 bytes               |
+----------------------+----------------------+
```

The compiler knows the offsets of the members:

-   `age` begins at offset 0.
-   `height` begins at offset 4.

When the program accesses `person.age`, the generated instructions
calculate or use the address of the object's first member.

When it accesses `person.height`, the generated instructions use the
object's base address plus the member offset.

The CPU does not need to understand the word `Person`, the member name
`age`, or the C language's struct abstraction. It executes address
calculations and loads/stores.

### An important nuance: the compiler may optimize

The compiler may keep values in registers instead of storing them in
RAM. It may eliminate the struct's memory representation entirely if the
program's observable behavior does not require it.

So the source-level object does not always correspond to a permanent
block of RAM.

The right mental model is:

-   C defines objects and their semantics.
-   The compiler chooses a machine-level representation.
-   That representation may use memory, registers, or a combination.
-   The CPU operates on machine instructions, addresses, and
    values---not C variable names or types.

## 14. Stack and heap

Two common places for data are the stack and heap.

### Stack

The stack is commonly used for function-call information and local
variables.

For example:

``` c
void calculate(void) {
    int x = 10;
    int y = 20;
}
```

The compiler may reserve stack-frame space for `x` and `y`, or keep them
in registers.

The stack pointer register identifies a location associated with the
current stack. Function calls and returns follow the processor's calling
convention and instruction-set rules.

### Heap

The heap is commonly used for dynamically allocated memory:

``` c
int *values = malloc(100 * sizeof(int));
```

The allocation function requests memory from the runtime or OS
allocator. The returned pointer is a virtual address that the process
can use.

The allocated bytes hold data. The pointer variable itself is also a
value, usually stored in a register or memory.

The heap is not a special physical chip. It is a region or set of
regions in a process's virtual address space managed by software.

------------------------------------------------------------------------

# Part 7 --- What does a machine instruction contain?

## 15. Instructions encode operations and operands

An instruction is represented by bytes. The processor's instruction
decoder interprets those bytes according to the ISA.

Conceptually, an instruction may specify:

-   An operation, such as add, subtract, load, store, or branch.
-   One or more registers.
-   An immediate constant.
-   A memory addressing mode.
-   Conditions or other control information.

For example, in assembly-like notation:

``` asm
ADD EAX, EBX
```

The instruction identifies an addition and two registers.

Another example:

``` asm
MOV EAX, [RBX + 8]
```

This describes a memory read using an address calculated from a base
register plus an offset.

And:

``` asm
ADD EAX, 5
```

uses an immediate value, 5, encoded as part of the instruction.

These are assembly representations, not necessarily the exact bytes
stored in memory.

## 16. The instruction is not necessarily a list of full memory addresses

You were wondering whether an instruction's memory-address field
contains a physical or virtual address.

The answer depends on the instruction and architecture, but for ordinary
application memory accesses, the processor generally calculates an
**effective virtual address**.

For example:

``` asm
MOV EAX, [RBX + 8]
```

Suppose:

``` text
RBX = 0x0000000000402000
Offset = 8
```

The effective address is:

``` text
0x0000000000402000 + 8
= 0x0000000000402008
```

That effective address is normally a virtual address in the current
process's address space.

The load/store hardware requests the data. Address translation maps the
virtual address to a physical address, subject to access permissions.

### Relative addressing

Some instructions use a relative displacement.

For example, a branch instruction might encode a displacement from the
address of the next instruction.

Conceptually:

``` text
Target address = next instruction address + signed displacement
```

This is useful for position-independent code and compact branches.

The resulting target is an instruction address in the current execution
address space. It is not generally a physical RAM address.

### Absolute addressing

Some instruction encodings can represent an address or address component
directly. But even when an instruction contains a numeric address, that
does not automatically make it a physical address.

In normal user-mode execution, ordinary memory operands are interpreted
within the process's virtual-address model.

------------------------------------------------------------------------

# Part 8 --- Fetching an instruction versus executing a load

## 17. These are two separate memory-access situations

This distinction resolves much of the confusion in your original
description.

### Situation A: fetching the instruction

Suppose the PC identifies virtual address `0x00401000`.

The instruction-fetch hardware requests the instruction bytes at that
address.

The MMU and memory hierarchy cooperate to obtain those bytes.

The bytes are delivered to the instruction pipeline and decoded.

### Situation B: executing an instruction that reads data

Now suppose the decoded instruction is:

``` asm
MOV EAX, [RBX]
```

The processor already has the instruction's meaning available in the
pipeline.

The execution hardware calculates the effective address from `RBX`.

The load/store hardware requests the data at that virtual address.

The MMU translates it, and the memory hierarchy returns the data.

The instruction bytes are not replaced by the data bytes. They are
handled by different parts of the processor.

### Two conceptual paths

``` text
INSTRUCTION PATH

PC
 |
 v
Instruction fetch
 |
 v
Address translation
 |
 v
Instruction cache / memory
 |
 v
Instruction bytes
 |
 v
Decoder
 |
 v
Execution


DATA PATH

Decoded load/store instruction
 |
 v
Effective address calculation
 |
 v
Address translation
 |
 v
Data cache / memory
 |
 v
Loaded data
 |
 v
Destination register
```

Both paths use address translation and the memory hierarchy, but they
serve different purposes.

------------------------------------------------------------------------

# Part 9 --- Why everything does not have to fit in one clock cycle

## 18. A memory access can take many cycles

Suppose the CPU wants data from RAM and that data is not in any nearby
cache.

The request may travel through the memory system, reach the memory
controller, access DRAM, and return.

That can take many CPU cycles.

The CPU does not need to freeze the entire processor and do absolutely
nothing during that time.

Modern processors use buffers, caches, out-of-order execution, and other
mechanisms to keep useful work moving.

Some dependent instructions must wait for the data. Independent
instructions may be able to proceed.

## 19. Pipelining

A simplified instruction pipeline has stages such as:

1.  **Fetch:** obtain instruction bytes.
2.  **Decode:** interpret the instruction.
3.  **Execute:** perform an operation or calculate an address.
4.  **Memory:** access data memory if needed.
5.  **Writeback:** write a result to a register.

A simplified example:

  Clock cycle   Instruction A   Instruction B   Instruction C
  ------------- --------------- --------------- ---------------
  1             Fetch                           
  2             Decode          Fetch           
  3             Execute         Decode          Fetch
  4             Memory          Execute         Decode
  5             Writeback       Memory          Execute
  6                             Writeback       Memory

This is an educational model, not a claim that all modern CPUs have
exactly five stages.

The key idea is that multiple instructions can occupy different stages
at the same time.

A pipeline improves **throughput**---how many instructions can be
completed over time. It does not mean every individual instruction takes
only one cycle from start to finish.

## 20. What happens when an instruction must wait?

Suppose an instruction loads a value from memory:

``` asm
MOV EAX, [RBX]
```

And the next instruction is:

``` asm
ADD ECX, EAX
```

The addition depends on the loaded value.

If the load takes a long time because of a cache miss, the dependent
addition cannot complete until the value arrives.

However, the CPU may be able to execute other independent instructions
while waiting.

Modern processors can also execute instructions out of program order
internally, while preserving the required architectural behavior when
results are committed.

This is one reason modern CPU implementations are much more complicated
than a simple fetch-one, execute-one machine.

------------------------------------------------------------------------

# Part 10 --- Registers: where values are held for computation

## 21. What is a register?

A register is a small, very fast storage location inside the processor.

Instructions commonly read values from registers and write results back
to registers.

For example:

``` asm
MOV EAX, 10
MOV EBX, 20
ADD EAX, EBX
```

Conceptually:

1.  Put 10 into EAX.
2.  Put 20 into EBX.
3.  Add EAX and EBX.
4.  Store the result, 30, in EAX.

The ALU does not need to retrieve both values from RAM for this example.
They are already in registers.

### Registers are not the same as RAM

  -----------------------------------------------------------------------
  Register                            RAM
  ----------------------------------- -----------------------------------
  Located inside the processor        Main memory is external to the CPU
                                      core

  Very small amount of storage        Much larger capacity

  Used directly by many instructions  Accessed through the memory system

  Very low access latency             Higher latency than registers and
                                      caches
  -----------------------------------------------------------------------

There are architectural registers visible to software, such as
general-purpose registers, and many internal physical registers used by
modern processors to implement execution efficiently.

## 22. Does everything have to live in registers?

No.

Registers hold values that the processor is actively using or that the
compiler chooses to keep there.

Other values can live in memory.

For example, an array may contain millions of elements. It would not fit
in the CPU's general-purpose registers.

The program can load individual elements into registers when needed,
operate on them, and write results back to memory.

A useful model is:

-   **Memory:** holds the program's larger working data.
-   **Registers:** hold values currently being used by instructions.
-   **Caches:** keep recently or frequently accessed memory contents
    close to the CPU.

------------------------------------------------------------------------

# Part 11 --- The operating system, kernel mode, and context switching

## 23. User mode and kernel mode

Modern processors provide execution privilege levels.

On common operating systems, ordinary applications run in a less
privileged mode (often called user mode), while the operating-system
kernel runs in a more privileged mode (kernel mode).

The processor enforces restrictions on what code can do at each
privilege level.

For example, user-mode code generally cannot directly:

-   Execute privileged instructions.
-   Configure page tables arbitrarily.
-   Access protected kernel memory.
-   Control hardware without going through permitted OS mechanisms.

The exact privilege architecture differs between x86 and ARM, but the
broad idea is similar.

## 24. How does a system call work?

An application sometimes needs the OS to perform a privileged service,
such as reading a file.

The application uses a system-call mechanism.

Conceptually:

1.  The application places system-call arguments in the required
    registers or memory locations.
2.  It executes a special system-call instruction.
3.  The processor performs a controlled transition to a privileged entry
    point.
4.  The processor and OS establish the required kernel execution state.
5.  Kernel code executes.
6.  The kernel returns a result and eventually returns control to user
    mode.

The important point for your earlier concern:

**The CPU does not need the application to execute a long sequence of
ordinary instructions to physically switch privilege modes.**

The architecture defines special mechanisms and hardware behavior for
this transition. The kernel then executes instructions to perform the
requested service.

## 25. What is a context switch?

A context switch occurs when the OS stops one thread from running and
schedules another thread.

A thread's execution context includes architectural state such as:

-   Program counter.
-   Stack pointer.
-   General-purpose registers.
-   Relevant processor status and control state.
-   Other state required by the architecture and OS.

A simplified context switch:

1.  An event causes the kernel to gain control (for example, a timer
    interrupt).
2.  The OS saves the outgoing thread's required state.
3.  The scheduler chooses another runnable thread.
4.  The OS restores the incoming thread's saved state.
5.  The processor resumes execution using the incoming thread's program
    counter and other state.

The OS uses ordinary instructions to save and restore much of this
state. The processor provides the mechanisms for entering the kernel and
handling interrupts and exceptions.

### A context switch is not necessarily a process switch

A process can contain multiple threads.

A context switch may switch: - Between two threads in the same
process. - Between threads belonging to different processes.

When switching between processes, the OS may also need to change the
active address-space mappings. The details depend on the architecture
and OS.

------------------------------------------------------------------------

# Part 12 --- Interrupts and exceptions

## 26. How can the CPU stop what it is doing?

An interrupt is an event that causes the processor to transfer control
to a designated handler.

For example, a hardware device may signal that it needs attention.

The processor has hardware-defined interrupt handling mechanisms. It can
save or establish the required execution state and transfer control to
an interrupt handler.

The handler is software, often part of the OS kernel, that runs after
the hardware transition.

An **exception** is an event associated with instruction execution, such
as:

-   An invalid instruction.
-   A divide error.
-   A page fault.
-   A protection violation.

The processor detects the condition and transfers control through an
architecture-defined exception mechanism.

This is another example of hardware and software cooperating:

-   Hardware detects and initiates the control transfer.
-   OS software handles the event and decides what should happen next.

------------------------------------------------------------------------

# Part 13 --- What does 32-bit or 64-bit mean?

## 27. "64-bit CPU" does not mean every instruction is 64 bits

The phrase "64-bit processor" refers to characteristics of the
processor's architecture, including its support for 64-bit integer
operations and registers.

It is associated with several concepts:

-   The width of general-purpose registers.
-   The width of integer operations supported by the ISA.
-   The size of pointers in a typical 64-bit software environment.
-   The virtual and physical address capabilities of the architecture.

But it does **not** mean:

-   Every instruction is 64 bits long.
-   Every memory transfer is 64 bits.
-   The data bus must be exactly 64 bits wide.
-   Every operation uses 64-bit values.
-   The CPU completes one instruction every 64 bits or cycles.

### Instruction width versus register width

These are different ideas.

For example, x86-64 instructions have variable lengths. An instruction
may be only a few bytes long or considerably longer.

AArch64 instructions are normally fixed at four bytes (32 bits), even
though AArch64 is a 64-bit architecture.

So an architecture can have 64-bit registers and 32-bit instruction
encodings.

### Address width is also distinct

A 64-bit architecture does not necessarily implement or use all 64 bits
as virtual-address bits.

For example, many x86-64 implementations support a virtual-address width
smaller than 64 bits. The architecture defines how addresses are
interpreted and which bits must be valid.

The important takeaway is that "64-bit" describes an architectural
capability, not one universal bus width or instruction size.

------------------------------------------------------------------------

# Part 14 --- A complete walkthrough

## 28. Follow one instruction from beginning to end

Let's put the pieces together with a simplified example.

Imagine a process is running this C code:

``` c
int add_values(int a, int b) {
    int result = a + b;
    return result;
}
```

Assume the compiler generates instructions that add two register values.

### Step 1: The process is prepared

The OS has created the process's virtual address space and mapped the
executable code.

The thread has an execution context, including a program counter
pointing to the function's machine code.

### Step 2: The PC identifies the next instruction

Suppose:

``` text
PC = 0x00401000
```

This is a virtual address in the process's address space.

### Step 3: Instruction-fetch hardware requests bytes

The instruction-fetch unit uses the PC to request instruction bytes.

It does not execute a software instruction to do this. Fetching is a
hardware function.

### Step 4: Address translation occurs

The address is translated using the TLB if possible.

If the TLB does not contain the translation, hardware may walk the page
tables.

The resulting physical address identifies the corresponding location in
the physical memory system.

### Step 5: The instruction bytes are retrieved

The instruction bytes may be found in the instruction cache.

If not, the request proceeds through lower levels of the memory
hierarchy and may eventually require DRAM access.

### Step 6: The decoder interprets the bytes

The decoder determines which operation is represented and which
registers or other operands are involved.

### Step 7: The execution hardware performs the operation

Suppose the instruction adds two registers.

The execution unit receives the operand values and performs the
addition.

The result is written to the appropriate destination register.

### Step 8: The processor continues

The PC or associated next-instruction state identifies the next
instruction to fetch.

The process repeats, with many instructions potentially overlapping in
the pipeline.

### Step 9: What if an instruction reads memory?

If an instruction needs data from memory, the load/store hardware
calculates the effective address, the MMU translates it, and the memory
hierarchy supplies the data.

That data is delivered to the appropriate register or execution path.
The instruction bytes remain separate from the data being loaded.

------------------------------------------------------------------------

# Part 15 --- Correcting the mental model, point by point

Here are the most important corrections to keep.

  -----------------------------------------------------------------------
  Initial mental model                More accurate model
  ----------------------------------- -----------------------------------
  The CPU needs an instruction to     Dedicated instruction-fetch
  fetch an instruction.               hardware retrieves instruction
                                      bytes.

  The CPU is completely idle until an CPU components are hardware
  instruction is loaded.              circuits that perform their
                                      dedicated roles.

  The MMU executes instructions to    Address translation is implemented
  translate addresses.                in hardware; the OS manages the
                                      mappings.

  The MMU must look through page      The TLB caches recent translations;
  tables for every address.           page-table walks are needed on
                                      misses.

  RAM is directly wired to the CPU in Requests travel through a memory
  a simple                            hierarchy and interconnect;
  one-block-to-one-instruction        instructions may be in caches.
  arrangement.                        

  One instruction must be fetched,    These activities take multiple
  translated, decoded, and executed   stages and can overlap across
  in one clock cycle.                 instructions.

  An instruction occupies one         Instruction length depends on the
  fixed-size block of RAM.            ISA; x86 instructions are variable
                                      length, AArch64 instructions are
                                      normally fixed at four bytes.

  All program data becomes machine    Instructions and data are distinct;
  instructions.                       structs and arrays can occupy
                                      memory.

  The CPU understands C structs and   The compiler translates
  variable names.                     language-level operations into
                                      addresses, loads, stores, and
                                      register operations.

  A memory address inside an          Ordinary application memory
  instruction must be physical.       operands normally resolve to
                                      virtual addresses that are
                                      translated by the MMU.

  Fetching data overwrites the        Instruction and data paths use
  instruction in the CPU.             separate buffers and hardware
                                      structures.

  A 64-bit CPU has 64-bit             Register width, instruction length,
  instructions and a 64-bit bus.      address width, and bus width are
                                      separate properties.

  Context switching requires          Hardware provides
  everything to be manually           interrupt/exception entry
  orchestrated while the CPU is       mechanisms; kernel software saves
  inactive.                           and restores thread state.
  -----------------------------------------------------------------------

------------------------------------------------------------------------

# Part 16 --- Test your understanding

Try answering these before reading the explanations. The goal is to test
your mental model, not to memorize terminology.

## Question 1

The program counter contains a virtual address for the next instruction.
Does the CPU need to execute a machine instruction to ask the MMU to
translate that address?

**Answer:** No. The instruction-fetch hardware initiates the fetch, and
the address-translation hardware participates in translating the
address. No ordinary software instruction is needed to start this
process.

## Question 2

The TLB misses. Does that automatically mean the virtual address is
invalid?

**Answer:** No. A TLB miss means the translation was not cached.
Hardware can perform a page-table walk. The address may be perfectly
valid.

## Question 3

The CPU fetches an instruction that says `MOV EAX, [RBX]`. Does the data
read overwrite the instruction?

**Answer:** No. The instruction bytes are held in instruction-related
buffers and pipeline structures. The load uses the data-access path and
returns a separate value.

## Question 4

A C program declares a struct. Does the CPU know what a struct is?

**Answer:** No. The compiler understands the C struct definition and
translates member accesses into machine-level operations such as address
calculations, loads, and stores.

## Question 5

Does every local variable have to occupy a location in RAM?

**Answer:** No. A compiler may keep a variable in a register, place it
in memory, optimize it away, or use different representations at
different points in the program.

## Question 6

Does a 64-bit processor fetch exactly 64 bits for every instruction?

**Answer:** No. Instruction length is determined by the ISA. x86-64 has
variable-length instructions; AArch64 normally uses fixed-width 32-bit
instruction encodings.

## Question 7

If a memory access takes 100 CPU cycles, must the whole CPU do nothing
for those 100 cycles?

**Answer:** No. The dependent instruction may have to wait, but the
processor may continue with independent work. Modern CPUs use caches,
buffers, and out-of-order execution to hide some memory latency.

## Question 8

When the OS switches to another thread, does the new thread need to
fetch its first instruction from physical RAM?

**Answer:** Not necessarily. The instruction may already be in a cache.
The OS restores the thread's execution state, including its instruction
pointer and relevant address-space state, and the fetch hardware
continues from that virtual address.

------------------------------------------------------------------------

# Part 17 --- Suggested next steps

You now have the conceptual foundation. The most useful way to deepen it
is to study the following topics in this order:

1.  **Instruction cycle and CPU datapath:** understand the PC,
    instruction register/buffers, decoder, register file, ALU, and
    control signals.
2.  **Pipelining:** learn fetch, decode, execute, memory, and writeback;
    then understand hazards and stalls.
3.  **Caches:** learn cache lines, cache hits/misses, locality, and
    instruction versus data caches.
4.  **Virtual memory in detail:** learn pages, page tables, page-table
    walks, TLBs, page faults, and permissions.
5.  **Loads and stores:** trace how an instruction calculates an
    effective address and retrieves or writes data.
6.  **Interrupts and exceptions:** understand how hardware transfers
    control to OS handlers.
7.  **Context switching:** trace how the OS saves and restores thread
    state.
8.  **Out-of-order execution:** understand how modern processors execute
    independent instructions while preserving the program's
    architectural behavior.

## A practical exercise

Write a tiny C program:

``` c
int main(void) {
    int a = 10;
    int b = 20;
    int c = a + b;
    return c;
}
```

Compile it without optimization and inspect its assembly output.

On a GCC or Clang toolchain, you can use:

``` bash
gcc -O0 -S -masm=intel example.c -o example.s
```

Then compare with:

``` bash
gcc -O2 -S -masm=intel example.c -o example_optimized.s
```

Look for:

-   Where the compiler places the values.
-   Which instructions load and store memory.
-   Which instructions operate on registers.
-   How the function returns its result.
-   How optimization changes the code.

Do not expect the output to match a particular example exactly. Compiler
version, target architecture, ABI, and optimization settings all affect
the assembly.

------------------------------------------------------------------------

# Final mental model

If you remember only one picture, remember this:

``` text
                    SOFTWARE
       Machine-code instructions and program data
                         |
                         v
+--------------------------------------------------+
|                    CPU                           |
|                                                  |
|  +----------------+       +-------------------+  |
|  | Program        |------>| Instruction Fetch |  |
|  | Counter        |       | Hardware          |  |
|  +----------------+       +---------+---------+  |
|                                     |            |
|                                     v            |
|                              +-------------+     |
|                              | MMU / TLB   |     |
|                              +------+------+     |
|                                     |            |
|                                     v            |
|                         Instruction Cache /      |
|                         Memory Hierarchy         |
|                                     |            |
|                                     v            |
|                              Instruction Bytes   |
|                                     |            |
|                                     v            |
|                              +-------------+     |
|                              | Decoder     |     |
|                              +------+------+     |
|                                     |            |
|                                     v            |
|                         Registers / Execution    |
|                         Units / Load-Store       |
|                                     |            |
+-------------------------------------|------------+
                                      |
                                      v
                             Memory Hierarchy
                                      |
                                      v
                                     RAM
```

The diagram is deliberately simplified: real processors overlap stages,
have multiple caches and execution units, and may translate addresses at
different points in the memory pipeline.

The core principle is:

**The CPU is not a single software-driven machine that must wait for an
instruction before anything can happen. It is hardware made of
specialized components. Those components fetch, translate, decode,
execute, and move information using circuits designed for those jobs.
Software supplies the instructions and data that give the hardware
useful work to perform.**
