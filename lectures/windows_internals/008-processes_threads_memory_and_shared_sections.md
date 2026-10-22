2026_10_21_23_59-(Processes-Threads-Memory-Shared-Sections)

# Lecture 008 — Processes vs Threads, Virtual vs Physical Memory, and Shared Sections with Named Mutexes and Events

> **For:** Timothy · **Date:** 2026-10-21
> **Prerequisites:** the platform validation lecture, Part 5 (shared memory, first pass); 005 §1 (privilege vs IRQL).
> **Why this lecture:** three questions sit under almost every systems conversation: what a process is versus a thread, how an address in code becomes a location in RAM, and how two processes can share memory safely. This lecture answers all three from the mechanism up, and ends with a complete, runnable program that shares a page between two processes through a named section, guarded by a named mutex and signaled with named events.

---

## Core ideas (the answer key)

1. **A process is a container; a thread is what runs.** A process owns an address space (its page tables), a handle table, and a security token. A thread owns CPU state: registers, a user stack and a kernel stack, a priority and a scheduling state. The scheduler runs **threads**, never processes.
2. **Every address code uses is virtual.** The CPU's MMU translates it to a physical address by walking the page tables of the current process, in 4 KB pages. On x64 that's four levels: PML4 → PDPT → PD → PT → page, plus a 12-bit offset. The TLB caches recent translations.
3. **Each process has its own page tables, so the same virtual address means different memory in different processes.** Switching processes switches the page-table root (CR3 on x64). The kernel half of the address space is the same in every process: the "one shared room".
4. **A page-table entry carries more than an address:** present/not-present, writable, no-execute, and **user/supervisor**. The supervisor bit is how *privilege* is enforced in memory.
5. **A page fault is the CPU saying "this translation isn't usable".** The memory manager either fixes it (the page is on disk or not yet created) or raises an access violation (invalid). That's the same mechanism behind pageable memory and 0xD1.
6. **Sharing memory = the kernel mapping the same physical pages into two processes' page tables.** On Windows, the kernel object for shareable memory is a **section object**. Processes agree on it through a **name** in the object manager namespace (`Local\…` per session, `Global\…` machine-wide), or through an inherited or duplicated handle.
7. **Processes synchronize with named kernel objects:** a **named mutex** (mutual exclusion; ownership; `WAIT_ABANDONED` if the owner dies), a **named event** (signaling: "data ready"), a **named semaphore** (counting). Any process can open them by name and wait on them.
8. **Inside shared memory, store data and offsets, never raw pointers.** Each process may map the view at a different virtual address.

---

## Table of Contents

- [1. Processes vs threads](#1-processes-vs-threads)
- [2. Virtual vs physical memory](#2-virtual-vs-physical-memory)
- [3. Page faults, the page file, and "pageable"](#3-page-faults-the-page-file-and-pageable)
- [4. Section objects: how sharing works](#4-section-objects-how-sharing-works)
- [5. Names: the object manager namespace](#5-names-the-object-manager-namespace)
- [6. Synchronizing across processes: mutex, event, semaphore](#6-synchronizing-across-processes-mutex-event-semaphore)
- [7. The complete program](#7-the-complete-program)
- [8. Seeing it in WinDbg](#8-seeing-it-in-windbg)
- [9. Misconceptions](#9-misconceptions)
- [10. Saying it precisely](#10-saying-it-precisely)
- [11. Self-check](#11-self-check)
- [Sources](#sources)

---

## 1. Processes vs threads 🟢

### 1.1 Definitions

| | **Process** | **Thread** |
|---|---|---|
| What it is | A **container** of resources | A **unit of execution**: the thing the scheduler runs |
| Owns | An **address space** (its own page tables); a **handle table** (its open files, events, sections…); a **security token** (who it runs as); one or more threads | **CPU context** (registers, including the instruction pointer); a **user-mode stack** and a **kernel-mode stack**; a **priority**; a **state** (running, ready, waiting…); thread-local storage |
| Kernel structure | `EPROCESS` | `ETHREAD` (with an embedded `KTHREAD`) |
| Shares with siblings | — | All threads in a process share its address space and handles |
| Isolation | Processes are isolated from each other by separate page tables | Threads in one process are **not** isolated from each other |
| Cost to create and switch | Higher: new address space, handle table | Lower: a stack and a context |

**The scheduler runs threads, not processes.** "A process is running" means one or more of its threads are running. A process with zero threads can't do anything.

### 1.2 Why it matters for drivers

- **Kernel drivers have neither.** They're modules in the kernel's shared space (from 003), and their code runs on whatever thread calls them (a dispatch routine on the requesting app's thread), on the interrupted thread (ISRs, DPCs), or on system worker threads.
- **Most of what a thread does in the kernel is on behalf of its process.** When an app calls `ReadFile`, its thread enters kernel mode through a system call and runs the I/O manager and driver dispatch code on its *kernel stack*, still in the context of that process. That's why a driver's dispatch routine can see the calling process's user-mode buffers, and why a DPC can't: it runs in an arbitrary thread's context.

### 1.3 Thread states 🔵

The ones you'll see in `!thread`:
- **Running**: on a processor right now.
- **Ready**: runnable, waiting for a processor.
- **Waiting**: blocked on an object: an event, a mutex, I/O completion…
- **Terminated**: finished.

A hang investigation is mostly about **Waiting** threads: on what, and since when.

---

## 2. Virtual vs physical memory 🟢

### 2.1 Two kinds of address

- A **physical address** names a real location: a byte in a RAM chip, or a device register (memory-mapped I/O).
- A **virtual address** is what every instruction uses. The CPU's **MMU** (memory management unit) translates it to a physical address *on every access*, using the **page tables** of the current process.

Memory is translated in fixed-size chunks called **pages**: 4 KB normally on x64 and Arm64 (with larger pages available as an optimization).

### 2.2 The x64 translation, step by step

A 64-bit virtual address uses its low 48 bits (the top bits must copy bit 47, which is what "canonical" means; a non-canonical pointer is 0x50 subtype 0x4 from lecture 002). Those 48 bits split into five fields:

| Bits | Field | Indexes into |
|---|---|---|
| 47–39 (9 bits) | PML4 index | The top-level table (512 entries) |
| 38–30 (9 bits) | PDPT index | Page-directory-pointer table |
| 29–21 (9 bits) | PD index | Page directory |
| 20–12 (9 bits) | PT index | Page table |
| 11–0 (12 bits) | Offset | The byte within the 4 KB page |

**Worked example:** virtual address `0x00007FF6_12345678`
- PML4 index = bits 47–39 = 255
- PDPT index = 472
- PD index = 145
- PT index = 325
- offset = `0x678`

The walk:
1. Start at the physical address of this process's PML4 table, held in the **CR3** register.
2. Read entry 255 of the PML4 → the physical address of a PDPT.
3. Entry 472 of that → a page directory.
4. Entry 145 of that → a page table.
5. Entry 325 of that → the **page-table entry (PTE)**, which holds the physical page number.
6. Physical address = that page's base + `0x678`.

Four memory reads per translation would be slow, so the CPU caches recent translations in the **TLB** (translation lookaside buffer). Most accesses never walk the tables.

### 2.3 What a PTE contains 🟢

Beyond the physical page number, each entry has bits the CPU enforces on every access:

| Bit | Meaning | Violating it |
|---|---|---|
| **Present (valid)** | The translation is usable right now | Page fault |
| **Writable** | Writes allowed | Page fault (access violation, or copy-on-write handling) |
| **User/Supervisor** | User-mode code may access; if clear, kernel-only | Page fault → access violation for user code |
| **No-execute** | Instructions may not be fetched from here | Page fault |

The User/Supervisor bit is where **privilege meets memory**. Kernel pages are mapped in every process, but marked supervisor-only, so user code faults if it touches them. That's the "one shared room" made physical: the room is in every process's address space, but its door is locked to user mode.

### 2.4 One address space per process, with a shared top half 🟢

- Each process has its own CR3, which means its own page tables. On a **context switch** to a thread of a different process, the kernel loads that process's CR3. That's why the same user address means different memory in different processes, and why threads of the *same* process share everything.
- The **kernel portion** (the upper half of the address space) is mapped identically in every process. A driver's global variable has the same kernel address no matter which process is current.
- `!pte <address>` in WinDbg prints this walk: each level's entry and its flags.

---

## 3. Page faults, the page file, and "pageable" 🟢

When the MMU can't use a translation, the CPU raises a **page fault** (exception vector 14 on x64) and the kernel's memory manager decides what it means:

| Situation | Kind | What happens |
|---|---|---|
| Page was never touched yet (newly allocated) | Demand-zero | Allocate a zeroed physical page, fill in the PTE, retry. No disk |
| Page is still in RAM on a standby or modified list (trimmed but not reused) | **Soft** fault | Re-point the PTE, retry. No disk |
| Page's contents are in the page file (or a mapped file) on disk | **Hard** fault | **Read from disk (a wait)**, fill in the PTE, retry |
| Address isn't valid at all (unmapped, freed, guard page) | Invalid | User mode: access violation exception. Kernel mode: bugcheck (0x50 and relatives) |
| Valid page, wrong access (write to read-only, user access to a kernel page) | Protection | Access violation (or copy-on-write handling for shared pages) |

**Pageable** means "the memory manager is allowed to trim this page and write it out, so touching it later may be a hard fault." Lecture 005 derived the consequence: a hard fault waits, waits need the scheduler, so pageable memory is forbidden at IRQL > APC_LEVEL.

**Working set:** the set of a process's pages currently resident in RAM. Trimming a working set moves pages toward the standby and modified lists; touching them again brings them back (soft or hard fault).

---

## 4. Section objects: how sharing works 🟢

### 4.1 The mechanism

A **section object** is the kernel's object for a region of memory that can be **mapped into address spaces**. It's "backed" either by a file on disk (memory-mapped files, and every `.exe`/`.dll` image) or by the page file (plain shared memory).

Sharing, step by step:
1. Process A creates a section (size N, page-file backed, named).
2. The kernel creates the section object. Its pages don't exist yet.
3. Process A **maps a view** of the section. The kernel reserves a range in A's address space and marks those PTEs as belonging to the section.
4. Process B opens the same section (by name) and maps its own view. The kernel reserves a range in **B's** address space, **possibly at a different virtual address**.
5. When A first touches a page, a demand-zero fault allocates a physical page. When B touches the same offset, its fault resolves to **the same physical page**. (The kernel tracks this with *prototype PTEs* in the section, ⚫ for now.)
6. Now A's write to offset 0x10 is visible to B's read at offset 0x10, because both translations end at the same physical byte.

So "sharing memory" is literally two processes' page tables pointing at the same physical pages, set up by the kernel on request.

### 4.2 The API, in four calls

| Call | Process | Effect |
|---|---|---|
| `CreateFileMappingW(INVALID_HANDLE_VALUE, sa, PAGE_READWRITE, sizeHigh, sizeLow, L"Local\\Name")` | Either | Create, **or open if it already exists** (then `GetLastError() == ERROR_ALREADY_EXISTS`). `INVALID_HANDLE_VALUE` = back it with the page file |
| `OpenFileMappingW(FILE_MAP_ALL_ACCESS, FALSE, L"Local\\Name")` | Opener | Open an existing section by name (fails if it doesn't exist) |
| `MapViewOfFile(h, FILE_MAP_ALL_ACCESS, 0, 0, size)` | Each | Map a view into **this** process; returns this process's virtual address |
| `UnmapViewOfFile(p)` + `CloseHandle(h)` | Each | Remove the view; the section is destroyed when the last handle and the last view are gone |

---

## 5. Names: the object manager namespace 🟢

Windows' kernel has an **object manager** that keeps named kernel objects (sections, mutexes, events, semaphores, devices…) in a single hierarchical namespace, like a file system for kernel objects. A name is the **agreement** between processes: whoever asks for the same name, with sufficient access, gets a handle to the same object.

| Prefix | Scope | Notes |
|---|---|---|
| `Local\Name` | The current logon **session** | The default for desktop apps; two users' sessions don't collide |
| `Global\Name` | Machine-wide, all sessions | Needed for a service (session 0) and a user app to share. Creating global section objects from a non-service process requires a privilege (`SeCreateGlobalPrivilege`) |
| (no prefix) | Same as `Local\` for desktop processes | |

**Security:** named objects have security descriptors. The default lets the creator's user (and administrators, SYSTEM) open them. When a service shares with users, pass an explicit security descriptor that grants what the users need, and no more.

**A subtle risk** (🔵): whoever creates a name first owns the object. A malicious process could pre-create your name with weaker security ("name squatting"). Defenses include private namespaces and checking `ERROR_ALREADY_EXISTS` when you expect to be the creator.

Alternatives to names: start a child process with an **inheritable** handle, or hand a handle across with `DuplicateHandle`. These avoid the namespace entirely.

---

## 6. Synchronizing across processes: mutex, event, semaphore 🟢

A common wrong belief is that locks only work between threads of one process. Kernel synchronization objects are **kernel objects**, so any process that has a handle (for example, by opening the name) can wait on them. They're the same kind of object as the section.

| Object | Create / open | Semantics | Use for |
|---|---|---|---|
| **Mutex** | `CreateMutexW(sa, FALSE, L"Local\\Name")` / `OpenMutexW` | **Ownership.** `WaitForSingleObject` acquires it; only the owner can `ReleaseMutex`. Re-entrant for the owning thread. If the owner exits without releasing it, the next waiter gets **`WAIT_ABANDONED`**: it owns the mutex, but the protected data may be half-written | Guarding shared data (mutual exclusion) |
| **Event** | `CreateEventW(sa, manualReset, initialState, L"Local\\Name")` / `OpenEventW` | A **signal**. `SetEvent` signals it. An **auto-reset** event releases one waiter, then resets itself; a **manual-reset** event stays signaled (releasing all waiters) until `ResetEvent` | "Data is ready", "I'm done", start/stop notifications |
| **Semaphore** | `CreateSemaphoreW(sa, initial, max, L"Local\\Name")` / `OpenSemaphoreW` | A **counter**. Each successful wait takes one; `ReleaseSemaphore` gives back | Counting free or used slots in a ring buffer |

**Waiting doesn't burn CPU:** a thread in `WaitForSingleObject` is in the *Waiting* state, and the scheduler doesn't run it until the object is signaled. This is the same scheduler and waiting mechanism from 005, used from user mode at PASSIVE_LEVEL, where waiting is always allowed.

**Handling `WAIT_ABANDONED` correctly:** treat it as "acquired, but the previous owner crashed mid-update". Validate or repair the shared data, possibly using a sequence number or checksum, before trusting it.

**The lock-free alternative, briefly:** for one producer and one consumer, a ring buffer with atomic head and tail indexes and acquire/release ordering needs no mutex. You still want an event or semaphore so the consumer can *sleep* instead of spinning. Start with the mutex-and-event design below; it's simpler to get right.

---

## 7. The complete program 🟢

`lectures/windows_internals/code/shm_demo.c`: one program, two roles. Run a **reader** and a **writer**; the writer sends three messages through the shared page. A named mutex protects the data, an event `Ready` says "a message is waiting", and an event `Ack` says "it's consumed".

```c
// shm_demo.c - two processes share one page through a named section,
// guard it with a named mutex, and signal each other with named events.
// Build (Visual Studio Developer Prompt):  cl /W4 shm_demo.c
// Build (MinGW):                          x86_64-w64-mingw32-gcc -Wall -o shm_demo.exe shm_demo.c
// Run:  start "reader" shm_demo.exe reader      then      shm_demo.exe writer
#include <windows.h>
#include <stdio.h>
#include <string.h>

#define SECTION_NAME L"Local\\ShmDemoSection"   // the name IS the agreement
#define MUTEX_NAME   L"Local\\ShmDemoLock"
#define READY_NAME   L"Local\\ShmDemoReady"     // writer -> reader: "a message is waiting"
#define ACK_NAME     L"Local\\ShmDemoAck"       // reader -> writer: "I consumed it"

typedef struct {
    LONG sequence;        // which message this is (0 = none yet)
    LONG length;          // bytes used in text[]
    char text[248];       // payload: plain data only, never pointers
} SHARED_BLOCK;           // 256 bytes; the section is one 4 KB page

static void die(const char *what) {
    printf("%s failed, GetLastError=%lu\n", what, GetLastError());
    ExitProcess(1);
}

int main(int argc, char **argv) {
    int isWriter = (argc > 1 && strcmp(argv[1], "writer") == 0);

    // 1. Create the section, or open it if the other process created it first.
    //    INVALID_HANDLE_VALUE = back it with the page file, not a disk file.
    HANDLE section = CreateFileMappingW(INVALID_HANDLE_VALUE, NULL, PAGE_READWRITE,
                                        0, 4096, SECTION_NAME);
    if (!section) die("CreateFileMappingW");
    BOOL alreadyExisted = (GetLastError() == ERROR_ALREADY_EXISTS);

    // 2. Map a view: this is where the kernel edits THIS process's page tables.
    SHARED_BLOCK *block = (SHARED_BLOCK *)MapViewOfFile(section, FILE_MAP_ALL_ACCESS, 0, 0, 4096);
    if (!block) die("MapViewOfFile");

    // 3. Named kernel objects for synchronization. Same naming mechanism as the section.
    HANDLE lock  = CreateMutexW(NULL, FALSE, MUTEX_NAME);          // not owned at creation
    HANDLE ready = CreateEventW(NULL, FALSE, FALSE, READY_NAME);   // auto-reset, starts unsignaled
    HANDLE ack   = CreateEventW(NULL, FALSE, FALSE, ACK_NAME);
    if (!lock || !ready || !ack) die("CreateMutexW/CreateEventW");

    printf("[%s pid %lu] section %s, view mapped at virtual address %p\n",
           isWriter ? "writer" : "reader", GetCurrentProcessId(),
           alreadyExisted ? "opened" : "created", (void *)block);

    for (int i = 1; i <= 3; i++) {
        if (isWriter) {
            WaitForSingleObject(lock, INFINITE);            // enter critical section
            block->sequence = i;
            block->length = sprintf(block->text, "message %d from pid %lu", i, GetCurrentProcessId());
            ReleaseMutex(lock);                             // leave critical section
            SetEvent(ready);                                // wake the reader
            WaitForSingleObject(ack, INFINITE);             // sleep until it's consumed
        } else {
            WaitForSingleObject(ready, INFINITE);           // sleep (no CPU) until signaled
            WaitForSingleObject(lock, INFINITE);
            printf("[reader] seq=%ld text=\"%.*s\"\n", block->sequence, (int)block->length, block->text);
            ReleaseMutex(lock);
            SetEvent(ack);
        }
    }

    // 4. Clean up. The section is destroyed when the LAST handle and view are gone.
    UnmapViewOfFile(block);
    CloseHandle(section); CloseHandle(lock); CloseHandle(ready); CloseHandle(ack);
    return 0;
}
```

### 7.1 Actual output

Compiled with MinGW (`-Wall -Wextra`, no warnings) and run under **Wine** on Linux (not on real Windows) for this lecture:

```
[reader pid 32] section opened, view mapped at virtual address 00007ffffe9d0000
[reader] seq=1 text="message 1 from pid 72"
[reader] seq=2 text="message 2 from pid 72"
[reader] seq=3 text="message 3 from pid 72"
[writer pid 72] section created, view mapped at virtual address 00007ffffe9d0000
```

How to read it:
- **Who created the section:** the writer did, although the reader was launched first, because Wine's first-run setup delayed the reader. The program doesn't care: `CreateFileMappingW` creates *or opens*, and `ERROR_ALREADY_EXISTS` says which happened. Whichever process arrives first creates; the other opens. The same is true for the mutex and events.
- **Same virtual address in both:** a coincidence of how Wine lays out address space. On real Windows, with address space layout randomization (ASLR), the two views often land at **different** addresses. That's why the struct holds only data, and any reference inside shared memory must be an **offset** from the start of the block, never a pointer.
- **Order of lines:** the writer's banner prints last only because each process buffers its own output. The `seq` values show the real order of the handoff.

### 7.2 Walk through one message, step by step

1. Writer: `WaitForSingleObject(lock)` → owns the mutex.
2. Writer: writes `sequence` and `text` into the shared page (the same physical page the reader has mapped).
3. Writer: `ReleaseMutex(lock)`, then `SetEvent(ready)`.
4. Reader (sleeping in `WaitForSingleObject(ready)`): the auto-reset event releases it and resets itself.
5. Reader: takes the mutex, reads, releases it, then `SetEvent(ack)`.
6. Writer (sleeping on `ack`): wakes and goes to message 2.

**Pause and predict:** what goes wrong if both events were **manual-reset** (`CreateEventW(NULL, TRUE, FALSE, …)`) and nobody called `ResetEvent`?

<details><summary>Answer</summary>After the first <code>SetEvent(ready)</code>, the event stays signaled, so the reader's later waits return immediately. It reads the same (or a half-written) message again and again without waiting for the writer, and the handshake breaks. Auto-reset makes each signal release exactly one wait.</details>

**Pause and predict:** the writer crashes while holding the mutex, between writing `sequence` and `length`. What does the reader's `WaitForSingleObject(lock, …)` return, and what should it do?

<details><summary>Answer</summary><code>WAIT_ABANDONED</code>. The reader now owns the mutex, but the data may be inconsistent: a new sequence with an old length. It should validate the data (for example, a checksum or a "complete" flag written last) before trusting it. This program, kept short, doesn't check.</details>

### 7.3 Try it on Windows

```
cl /W4 shm_demo.c
start "reader" shm_demo.exe reader
shm_demo.exe writer
```

Then experiment:
1. Run two readers at once: which one gets each message, and why? (Auto-reset events release one waiter each time.)
2. Print `&block->text` in both processes, and compare it to the base address.
3. Kill the writer with Task Manager mid-run (add a `Sleep` inside the locked region to make it easy) and observe `WAIT_ABANDONED`.

---

## 8. Seeing it in WinDbg 🔵

On a local kernel debugging session (001), while both processes run:

| Command | Shows |
|---|---|
| `!process 0 0 shm_demo.exe` | Both processes, their `EPROCESS` addresses and PIDs |
| `!process <addr> 7` | Each one's threads; the reader's thread in `WAIT` on an event |
| `!handle 0 3 <EPROCESS>` (in that process's context) | Handles to `Section`, `Mutant` (the kernel's name for a mutex) and `Event` objects, with their names |
| `!object \Sessions\<n>\BaseNamedObjects\ShmDemoSection` | The section object by name: `Local\` names live in the session's `BaseNamedObjects` directory |
| `.process /p /r <EPROCESS>` then `!pte <view address>` | That process's page-table walk for the view; repeat in the other process and compare the physical page numbers. **They match.** That's sharing |

That last comparison is the whole lecture in one observation: two processes, different `CR3`s, same physical page.

---

## 9. Misconceptions

| You might think | Reality | Why it matters |
|---|---|---|
| Processes run | Threads run; a process is the container they share | Hangs and scheduling are about threads |
| A driver is a process (or a thread) | Neither: code in the kernel's shared space, run on borrowed or system threads | Which context a routine runs in decides what it can touch |
| Processes can't use locks, only threads can | Named kernel mutexes, events and semaphores work across processes | The standard way to synchronize shared sections |
| The same pointer works in both processes | Views can map at different virtual addresses | Store offsets, never pointers, in shared memory |
| Shared memory is copied between processes | Both page tables point at the same physical pages; nothing is copied | Writes are visible immediately, hence the need for locking |
| IRQL governs user-mode waiting | User code always runs at PASSIVE_LEVEL and may wait freely; IRQL rules are a kernel-mode concern | Keep privilege and IRQL as separate axes |
| A page fault is an error | Most page faults are normal (demand-zero, soft, hard) and resolved transparently; only invalid or forbidden ones are errors | "Pageable" means "may fault, and that's fine at PASSIVE" |

---

## 10. Saying it precisely

- "A process is a container: an address space, handles, a token. A thread is the schedulable unit with registers, stacks and a state. The scheduler only runs threads."
- "Every address is virtual. On x64 the MMU walks four levels of page tables from CR3, caching in the TLB. Each PTE carries present, writable, no-execute and user/supervisor bits, and the supervisor bit is how kernel pages stay off-limits to user code even though they're mapped in every process."
- "Sharing memory means the kernel maps the same physical pages into both processes. On Windows that's a section object: one process creates it with `CreateFileMapping` and a name like `Local\\X`, the other opens it by the same name, and each maps its own view, possibly at a different address, so the shared layout holds offsets, not pointers."
- "For synchronization, I use a named mutex around the data and named auto-reset events to signal 'ready' and 'consumed'. The waiting threads sleep without using CPU, and `WAIT_ABANDONED` tells me the previous owner died mid-update."

---

## 11. Self-check

1. What does a process own, and what does a thread own?
<details><summary>Answer</summary>Process: an address space (page tables), a handle table, a security token, its threads. Thread: CPU context, user and kernel stacks, priority, state, TLS.</details>

2. Which kernel structures represent them, and which commands show them?
<details><summary>Answer</summary>EPROCESS and ETHREAD (with KTHREAD). <code>!process</code> and <code>!thread</code>.</details>

3. Split the virtual address `0x00007FF6_12345678` into its x64 page-walk indices and offset.
<details><summary>Answer</summary>PML4 255, PDPT 472, PD 145, PT 325, offset 0x678.</details>

4. Where does the walk start, and why does a context switch between processes change it?
<details><summary>Answer</summary>At the PML4 whose physical address is in CR3. Each process has its own page tables, so switching to another process's thread loads its CR3.</details>

5. Name four PTE permission bits, and say which one enforces privilege.
<details><summary>Answer</summary>Present, writable, user/supervisor, no-execute. User/supervisor enforces privilege.</details>

6. Distinguish demand-zero, soft and hard page faults.
<details><summary>Answer</summary>Demand-zero: first touch, allocate a zeroed page (no disk). Soft: the page is still in RAM on a standby or modified list, re-point the PTE (no disk). Hard: the contents are on disk, read them back (a wait).</details>

7. Explain step by step how two processes end up sharing a physical page through a section.
<details><summary>Answer</summary>Create the section (named, page-file backed) → each process maps a view (the kernel reserves PTE ranges in each address space) → the first touch allocates the physical page → the other process's touch at the same offset resolves to the same physical page.</details>

8. `Local\` vs `Global\`?
<details><summary>Answer</summary><code>Local\</code> is per logon session (the default for desktop apps). <code>Global\</code> is machine-wide, needed to share between a service in session 0 and user apps; creating global sections needs SeCreateGlobalPrivilege.</details>

9. Why must shared memory hold offsets and not pointers?
<details><summary>Answer</summary>Each process may map the view at a different virtual address, so a pointer valid in one process points elsewhere in the other.</details>

10. Mutex vs auto-reset event vs semaphore: one sentence each.
<details><summary>Answer</summary>Mutex: ownership-based mutual exclusion, released only by its owner, with WAIT_ABANDONED if the owner dies. Auto-reset event: a signal that releases one waiter and resets. Semaphore: a counter of available units.</details>

11. What does `WAIT_ABANDONED` mean, and what should the receiver do?
<details><summary>Answer</summary>The previous owner exited while holding the mutex. The receiver now owns it, but should validate or repair the shared data before trusting it.</details>

12. In WinDbg, how would you *prove* two processes share a physical page?
<details><summary>Answer</summary>Switch to each process's context (<code>.process /p /r</code>), run <code>!pte</code> on each one's view address, and compare the physical page numbers. They match.</details>

---

## Sources

Checked 2026-10-21.

- Microsoft Learn: File mapping / creating named shared memory (`CreateFileMappingW` with `INVALID_HANDLE_VALUE`, `OpenFileMappingW`, `MapViewOfFile`, `Local\` / `Global\` names, `SeCreateGlobalPrivilege`); Kernel object namespaces; Synchronization objects (mutex objects and `WAIT_ABANDONED`, event objects auto- vs manual-reset, semaphore objects).
- *Windows Internals, 7th ed., Part 1*: processes and threads (EPROCESS/ETHREAD, thread states), memory management (x64 4-level paging, PTE bits, page fault types, working sets, section objects and prototype PTEs).
- Intel 64 and IA-32 Architectures Software Developer's Manual, Vol. 3: paging structures, CR3, canonical addresses, TLB.
- Microsoft Learn: debugger reference for `!process`, `!thread`, `!handle`, `!object`, `.process`, `!pte`.

`shm_demo.c` was compiled with MinGW-w64 GCC (`-Wall -Wextra`, no warnings) and run under Wine 9.0 on Linux on 2026-10-21. The output above is real. Behavior on Windows should match; virtual addresses will differ.
