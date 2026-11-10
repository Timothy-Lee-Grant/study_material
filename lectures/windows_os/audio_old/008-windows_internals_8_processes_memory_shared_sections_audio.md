# Windows Internals, Part 8: Processes, Threads, Virtual Memory, and Shared Sections (audio lecture)

This is the last part of an eight-part series on Windows internals. It covers what a process is versus a thread, how an address in code becomes a location in physical memory, and how two processes share memory safely using a named section, a named mutex, and named events.

## Why this episode exists

Three questions sit under almost every systems conversation: what's the difference between a process and a thread, how does a virtual address turn into a physical one, and how can two processes share memory without corrupting it? Timothy has met all three in earlier lectures, but in pieces. By the end of this episode he should be able to explain each one from the mechanism up, and describe a working program in which two processes exchange messages through shared memory.

## The core ideas

Here are today's core ideas. They're the answer key for the walk questions at the end.

One. A process is a container. A thread is what runs. A process owns an address space, a table of handles, and a security identity. A thread owns processor state: registers, stacks, a priority, and a scheduling state. The scheduler runs threads, never processes.

Two. Every address that code uses is virtual. The processor translates it to a physical address by walking the current process's page tables, in four-kilobyte pages. On sixty-four-bit Intel and AMD machines, that's four levels of tables plus an offset, and a cache called the T-L-B remembers recent translations.

Three. Each process has its own page tables, so the same virtual address means different memory in different processes. The kernel's half of the address space is the same in every process.

Four. Each page-table entry holds permission bits: present, writable, no-execute, and user-or-supervisor. The supervisor bit is how privilege is enforced in memory.

Five. Sharing memory means the kernel maps the same physical pages into two processes' page tables. On Windows, the kernel object for shareable memory is a section. Processes agree on it by name, in a per-session or machine-wide namespace.

Six. Processes synchronize with named kernel objects: a mutex for mutual exclusion, an event for signaling, and a semaphore for counting. And inside shared memory, store data and offsets, never pointers.

## Section one: processes versus threads

A process is a container of resources. It owns three main things. An address space, meaning its own page tables. A handle table: the list of everything it has open, like files, events and sections. And a security token, which says who it runs as. It also contains one or more threads.

A thread is a unit of execution, the thing the scheduler actually runs. It owns its processor context, meaning its registers, including where it is in the code. It owns two stacks, one for user mode and one for kernel mode. And it has a priority and a state.

Threads in the same process share everything the process owns, so they aren't isolated from each other. Processes are isolated from each other by having separate page tables. And here's the key sentence: the scheduler runs threads, not processes. "A process is running" means some of its threads are.

In the kernel, a process is represented by a structure called E-PROCESS, and a thread by one called E-THREAD. The debugger commands bang-process and bang-thread show them.

The thread states you'll see most are running, on a processor right now; ready, runnable but waiting for a processor; and waiting, blocked on something like an event, a mutex, or an input-output request. Hang investigations are mostly about the waiting ones: on what, and since when.

How does this relate to drivers? Kernel drivers are neither processes nor threads. They're code in the kernel's shared space, which runs on whatever thread calls it. When an application calls read-file, its own thread crosses into kernel mode through a system call and runs the driver's request handler on its kernel stack, still in that application's process context. That's why a request handler can see the calling application's buffers, and why a D-P-C, running on whatever thread happened to be interrupted, can't.

## Section two: virtual versus physical memory

A physical address names a real location: a byte in a RAM chip, or a device register. A virtual address is what every instruction actually uses. The processor's memory management unit translates virtual to physical on every access, using the current process's page tables, in fixed-size chunks called pages, normally four kilobytes.

On sixty-four-bit Intel and AMD machines, a virtual address uses its lower forty-eight bits, split into five fields. The top nine bits pick an entry in the top-level table, called the P-M-L-four. The next nine bits pick an entry in the second level, the page directory pointer table. The next nine pick an entry in the page directory. The next nine pick an entry in the page table. The last twelve bits are the offset within the four-kilobyte page.

Here's a worked example. Take the virtual address hex seven-F-F-six, one-two-three-four-five-six-seven-eight. Splitting it up gives a top-level index of two hundred fifty-five, a second-level index of four hundred seventy-two, a third-level index of one hundred forty-five, a fourth-level index of three hundred twenty-five, and an offset of hex six-seven-eight.

The walk goes like this. Start at the top-level table, whose physical address is held in a processor register called C-R-three. Read entry two hundred fifty-five, which gives the physical address of the next table. Follow entries four hundred seventy-two, then one hundred forty-five, then three hundred twenty-five. That last one is the page-table entry, which holds the physical page number. Add the offset, six-seven-eight, and you have the physical address. Four memory reads per translation would be slow, so the processor caches recent translations in the translation lookaside buffer, the T-L-B, and most accesses never walk the tables at all.

Each page-table entry carries permission bits that the processor checks on every access. Present says whether the translation is usable right now. Writable says whether writes are allowed. No-execute says whether instructions may be fetched from this page. And user-or-supervisor says whether user-mode code may touch it at all. Kernel pages are mapped into every process's address space, but marked supervisor-only, so user code that touches them faults. That's privilege, enforced in memory: the kernel's shared room is present in every process, but its door is locked to user mode.

Each process has its own C-R-three value, its own page tables. When the scheduler switches to a thread of a different process, it loads that process's C-R-three. That's why the same user address means different memory in different processes, and why threads in the same process share everything.

## Section three: page faults

When the processor can't use a translation, it raises a page fault, and the memory manager decides what it means. If the page was newly allocated and never touched, it's a demand-zero fault: give it a fresh zeroed page, no disk needed. If the page was trimmed from the process but is still in RAM on a standby list, it's a soft fault: just point the entry at it again, no disk needed. If the page's contents are out in the page file, it's a hard fault: read them back from disk, which means waiting. If the address isn't valid at all, user code gets an access violation, and kernel code causes a blue screen like hex fifty. And if the page is valid but the access breaks a permission, like writing to read-only memory, it's an access violation too.

So pageable memory means: the memory manager may trim this page and write it out, so touching it later may be a hard fault. That's fine at PASSIVE level. Part five explained why it's fatal above APC level: a hard fault waits, and waiting needs the scheduler.

## Section four: sections, and how sharing works

A section is the kernel's object for memory that can be mapped into address spaces. It's backed either by a file on disk, which is how memory-mapped files and every program image work, or by the page file, which is plain shared memory.

Here's how sharing happens, step by step. Process A creates a named section, backed by the page file. The kernel creates the section object, though its pages don't exist yet. Process A maps a view of it: the kernel reserves a range in A's address space and marks those page-table entries as belonging to the section. Process B opens the same section by name and maps its own view; the kernel reserves a range in B's address space, possibly at a different virtual address. When A first touches a page, a demand-zero fault creates a physical page. When B touches the same offset, its fault resolves to the same physical page. From then on, A's write at some offset is visible to B's read at that offset, because both translations end at the same physical byte. Nothing is copied. Two page tables simply point at the same memory.

The Windows functions are: create-file-mapping, which creates a section, or opens it if it already exists, and tells you which happened; open-file-mapping, which opens an existing one by name; map-view-of-file, which maps a view into the calling process and returns its address in that process; and unmap-view and close-handle to clean up. The section disappears when the last handle and the last view are gone.

## Section five: names

Windows' kernel keeps named objects, like sections, mutexes, events and semaphores, in one hierarchical namespace managed by its object manager, a bit like a file system for kernel objects. A name is the agreement between processes: whoever asks for the same name, with enough access, gets a handle to the same object.

Names prefixed with Local, backslash, are scoped to the current logon session, which is the default for desktop programs, so two users don't collide. Names prefixed with Global, backslash, are machine-wide, which is needed when a background service and a user's program share an object. Creating a global section from a normal program requires a special privilege.

Named objects carry security descriptors. And because whoever creates a name first owns the object, a careful program checks whether its name already existed when it expected to be the creator. Instead of names, a parent process can also pass a handle to a child it starts, or one process can duplicate a handle into another.

## Section six: synchronizing across processes

It's a common belief that locks only work between threads in one process. But Windows' synchronization objects are kernel objects, so any process that opens them by name can wait on them.

A mutex provides mutual exclusion with ownership. Waiting on it acquires it, and only the owner can release it. If the owner exits while holding it, the next waiter gets a special result called wait-abandoned. That means: you now own it, but the data it protects may be half-written, so check it before trusting it.

An event is a signal. Setting it signals it. An auto-reset event releases exactly one waiter and then resets itself. A manual-reset event stays signaled, releasing every waiter, until someone resets it.

A semaphore is a counter. Each successful wait takes one unit, and releasing gives units back. It's good for counting free or used slots in a ring buffer.

And waiting doesn't burn any processor time. A thread waiting on one of these objects is in the waiting state, and the scheduler doesn't run it until the object is signaled. That's the same scheduler and waiting mechanism from part five, used from user mode, where waiting is always allowed.

## Section seven: the program

The series includes a complete program, called shm-demo, written in C. It runs as two processes, a reader and a writer, which share one four-kilobyte page through a section named Local, backslash, Shm-Demo-Section. The shared page holds a small structure: a sequence number, a length, and a text buffer, plain data with no pointers. A named mutex protects the structure. A named auto-reset event called Ready means "a message is waiting", and another called Ack means "the message was consumed".

Here's one message, step by step. The writer waits on the mutex and acquires it. It writes the sequence number and text into the shared page. It releases the mutex and sets the Ready event. The reader, which was sleeping on Ready, wakes up, and the auto-reset event resets itself. The reader acquires the mutex, reads the message, releases the mutex, and sets Ack. The writer, sleeping on Ack, wakes up and moves on to the next message. Three messages go across this way.

The program was compiled and actually run for this series, under a Windows compatibility layer on Linux. The reader printed all three messages in order. In that run both processes happened to map the view at the same virtual address, but that's a coincidence. On real Windows, address randomization often puts the views at different addresses, which is exactly why the shared structure holds offsets and data, never pointers.

Pause and predict. What breaks if both events were created as manual-reset, and nobody ever reset them?

After the first Ready, the event stays signaled, so every later wait by the reader returns immediately. The reader reads the same or a half-written message over and over without waiting for the writer, and the handshake falls apart. Auto-reset makes each signal release exactly one wait.

Pause and predict. The writer crashes while holding the mutex, halfway through writing a message. What does the reader's wait return, and what should it do?

It returns wait-abandoned. The reader now owns the mutex, but the data may be inconsistent: a new sequence number with an old length. It should validate the data, for example with a completion flag written last or a checksum, before trusting it.

## Section eight: seeing it in the debugger

With local kernel debugging turned on and both processes running, bang-process can find both, and their threads show the reader waiting on an event. Their handle tables list a section, a mutant (which is the kernel's word for a mutex), and events, by name. And here's the observation that sums up the whole episode: switch to each process's context and look up the page-table entry for its view address. The physical page numbers match. Two processes, two different page-table roots, one physical page.

## Connections

This connects to part five: privilege lives in the page-table entries' supervisor bit, while IRQL is a separate axis. It connects to part two: hex fifty is an address that no page-table entry can make valid. And it connects to the earlier shared-memory discussion: processes can absolutely use locks, through named kernel objects.

## Recap

The core ideas once more. A process is a container of an address space, handles and a security identity; a thread is what the scheduler runs. Every address is virtual, translated through four levels of page tables starting from C-R-three, cached in the T-L-B. Page-table entries carry present, writable, no-execute and supervisor bits, and the supervisor bit keeps kernel pages away from user code. Most page faults are normal; only invalid or forbidden ones are errors. Sharing means two page tables pointing at the same physical pages, through a named section. And processes synchronize with named mutexes, events and semaphores, keeping only data and offsets in the shared memory.

## Walk questions

Three questions for the next walk.

First: what does a process own, and what does a thread own, and which one does the scheduler run?

Second: walk through translating a virtual address on a sixty-four-bit Intel or AMD machine, starting from C-R-three, and say what the T-L-B is for.

Third: explain how the shm-demo program passes one message, naming the section, the mutex, and both events, and say why the shared structure contains no pointers.
