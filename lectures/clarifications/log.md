# Clarifications Log

> **What this is:** the running log behind the clarification lectures in this folder. Each talk-through I give is saved in `intakes/`, split into claims, and each fuzzy or wrong claim is traced to the higher-level concept that would fix it. The plan in §1 is the queue for the next lecture. Method: `learning_system/clarifications_protocol.md`.
> **Sections:** §1 lecture plan (open queue, grouped by root concept) · §2 intake log (claim maps, append-only) · §3 covered (what each lecture handled) · §4 changelog.
> **Marks:** ✅ accurate · 🟡 imprecise · ❌ wrong model · ❓ flagged doubt (J = the doubt was justified) · 💡 connection or extension.

---

## 1. Lecture plan (open queue)

Ordered so foundations come first. **P1** = a root other groups depend on / would mislead debugging or lab work · **P2** = clears several leaves · **P3** = small. Leaves cite intake dates. Remove a leaf from here only when it moves to §3 (covered) — mark resolved only from his own later words.

### G1. Map of the chip: SoC vs core vs ALU vs MMU vs controllers — **P1 (foundation for G2–G5)**
- **Root:** an SoC is a set of blocks joined by an on-chip interconnect. A *core* = fetch/decode + registers + ALU(s) + load/store unit + its own MMU/TLB + L1 caches. Shared: L2/L3, the interconnect, the memory (DRAM) controller, peripheral controllers (UART, I2C, USB host, PCIe root complex…), interrupt controller. "CPU" is used loosely for core, cluster, or the whole chip.
- Leaves: ❓(J) 11-04 "very little understanding of… what is the actual CPU, the cores, the ALU, and how data is channeled". 🟡 11-04 controllers "inside the CPU, or the IC?" (they're on the SoC, not inside a core). 🟡 11-04 MMU "a component similar to those controllers" (it's inside each core, on the load/store path, not a peripheral you talk to).
- One layer up: who's an *initiator* (cores, DMA-capable controllers) vs a *target* (DRAM, device registers, boot ROM).

### G2. What a physical address is and how an access reaches its target — **P1**
- **Root:** a load/store becomes a **transaction** (read/write + address [+ data]) that the core sends into the interconnect. **Address decoders** route it by the system's **physical address map** (ranges → DRAM, UART registers, boot flash, PCIe window…). The target answers. There's no "direct wire from a CPU register to the device", and there's no CPU register that *is* the address bus. Caches sit in the path for RAM (not for device registers, which are mapped uncached).
- Leaves: ❌ 11-04 "the CPU has a register like the address bus… bits high/low open channels". ❌ 11-04 "100% direct connection between the CPU register and the external location". 🟡 11-04 "hexadecimal address in the register" (address is a number; hex is notation → see G6).
- ✅ 11-04 on-chip controllers = block of registers at a base address + offsets; read/write them by address (MMIO). ✅ base addresses fixed by the manufacturer for on-chip blocks.
- ❓(J) 11-04 "how do we know which controller and offset?" → datasheet / reference manual for bare metal; under an OS, the firmware's description (ACPI on PCs, device tree on many Arm/Linux boards) tells the OS, the OS binds a driver, and the driver maps the physical range into virtual space.
- Note the old-school model he's using (a literal parallel address bus with chip-select lines) is how 8-bit systems and his ATmega era *looked*; the decoding idea survives, the "direct wire" doesn't.

### G3. Plug-in devices: enumeration and the "mediator" — **P1** (resolves his own contradiction)
- **Root:** two kinds of hardware. **Discoverable buses** (PCIe, USB) can be asked "what's there?" → **enumeration**. **Non-discoverable** on-chip blocks must be **described** (ACPI / device tree). The "mediator" he looked for is **configuration of the decoders**: for PCIe, firmware/OS reads each device's BAR to learn how much space it needs, picks a free physical range, **writes it into the device's BAR** (and programs bridge windows). From then on the device answers that range. Rerouting = reprogramming who decodes what.
- Leaves: 💡/❓(J) 11-04 "plug-in devices can't have hardcoded addresses… some orchestrator… but if the address register opens lanes there's no mediator" (excellent contradiction-spotting; the false premise is G2's "direct wire"). ❌ (implied) 11-04 every plug-in device "needs specific memory addresses": **USB devices have no memory address**; only the USB host controller is memory-mapped. USB devices get a 7-bit USB address on the USB bus, talked to via the host controller's descriptor rings.
- One layer up: "addressing" exists at multiple levels (CPU physical address map, PCIe bus/device/function, USB address, I2C 7-bit address) — each bus has its own address space; the host controller translates between them.

### G4. Virtual memory is a mode, applied to every access — **P1**
- **Root:** once the kernel turns paging on (a control-register bit: CR0.PG on x86, SCTLR_EL1.M on Arm), **every** address a core issues is virtual; the core's MMU translates each one (TLB hit = fast; miss = hardware page-table walk). Not chosen per instruction. Physical addresses are used only before paging is on (early boot) and by the MMU walker/devices. Also: the address is usually *computed* (register + offset), not literally stored in the instruction.
- Leaves: ❌ 11-04 "based on the instruction and register state, the address is known to be virtual or physical". 🟡 11-04 "MMU needs to wake up and grab that address" (it's always on the path). 🟡 11-04 MMU "looks at the location in RAM that corresponds to the address" (the virtual address bits *index* a multi-level tree whose root is in CR3/TTBR; it doesn't look up "the location of the address"). ✅ page tables = data structures in RAM. ✅ page fault → CPU jumps to the kernel handler. 🟡 "then it goes back and gets the data": after fixing the mapping the kernel returns and the **faulting instruction re-executes**.
- One layer up: why it exists (isolation, each process its own map, demand paging) — ties to G7's "why IPC".

### G5. Boot: where code comes from, firmware, drivers, and the device tables — **P1/P2**
- **Root A (fetch is a read):** the core always fetches instructions by address through the same transaction path as data. At reset, the PC starts at a fixed **reset vector**; the address map routes it to on-chip boot ROM / memory-mapped SPI flash. Firmware copies itself to RAM, sets up DRAM, then runs from there. The executor and the code are always in different places; caches bring code close.
- **Root B (who reads a table — hardware or software?):** some RAM data structures are read **by hardware** (page tables by the MMU walker, IDT/vector table on interrupt entry, DMA descriptor rings by controllers). Others are read **only by software** (ACPI tables, device tree, the OS's device tree/PnP tree). This is the distinction he reached for at the end ("an abstract data structure like page tables").
- Leaves: 💡 11-04 "this must be how all code runs: code in RAM, executor elsewhere" (✅, self-derived). 🟡 11-04 firmware "hardcoded code in a physical chip" (boot ROM is fixed; UEFI lives in rewritable SPI flash — that's what a firmware update rewrites). ❌ 11-04 firmware "finds devices… loads drivers… then creates the table the OS uses": firmware has **its own UEFI drivers** just for booting; the OS loads its own drivers later and re-enumerates. The **ACPI tables are mostly written by the OEM** in advance and shipped inside the firmware; at boot firmware places them in RAM (patching a few values) and hands the OS a pointer (UEFI config table → RSDP). They describe non-discoverable hardware and power control; PCIe/USB devices are found by enumeration. 🟡 11-04 name: "PC or PCI… something like a table" = **ACPI** (name not recalled). Untangle ACPI (description tables) vs PCI(e) (a bus with config space). ❓(J) 11-04 "where does the table live, physical or abstract?" → plain bytes in RAM (reserved region), read only by software; nothing in hardware "orchestrates" it into an address.
- ❓(J) 11-04 "I don't even know exactly how drivers work" → covered in wi/009 (unread?). Here: one line + pointer.

### G6. Bytes vs hex — **P2** (small but recurring across topics)
- **Root:** data is bits/bytes. Hex, decimal, binary are ways to *write* a number for humans. A socket, a UART, a register doesn't carry "hex values"; it carries bytes. 0xAA = 170 = 10101010 = the same byte.
- Leaves: ❌ 11-04 "socket is streaming hex values", "raw hexadecimal values" (×2). 🟡 11-04 "hexadecimal address in the register".
- One layer up: meaning comes from a format agreement (text encoding, integer width, endianness) → G9.

### G7. IPC: why it's needed and the full family — **P2**
- **Root:** each process has its own virtual address space, so a pointer in one is meaningless in the other; to share, you go through the kernel. Families: **shared memory** (kernel maps the same physical pages into both — fastest, needs sync), **pipes**, **sockets** (incl. Unix domain sockets), plus signals, message queues, Windows named pipes/ALPC.
- Leaves: ✅ 11-04 virtual addresses → can't directly communicate (right reason). 🟡 11-04 "either pipes or sockets" (missing shared memory, which is the same page-table trick as G4). ✅ pipe = FIFO, one writes, one reads, same host. 🟡 missing: the pipe is a **kernel buffer**; anonymous pipes are one-way (two pipes for two-way); byte stream.

### G8. Sockets, TCP, and what `read()` actually does — **P1**
- **Root A:** a socket is an **OS API endpoint**, not a protocol. You pick the protocol: TCP (reliable ordered byte stream), UDP (datagrams), or a Unix domain socket (local, no IP at all). A TCP **connection** is identified by the 4-tuple (+ protocol). The server `listen`s on a port and `accept` returns a new connected socket; the client's port is usually an **ephemeral** port the OS picks.
- **Root B (the data path):** NIC receives a frame → DMAs it into **RAM** buffers → interrupt → kernel network stack (IP, TCP: reorder, ack, retransmit, checksum) → bytes land in the socket's **receive buffer** in kernel memory → your `read(fd, buf, 4096)` **copies** from that kernel buffer into your buffer.
- **Root C (blocking):** blocking is the default. If the receive buffer is empty, `read` puts your thread on that socket's wait queue (it sleeps, no CPU); data arrival wakes it. It returns **whatever is available, ≥1 byte up to 4096**, not necessarily 4096; 0 = peer closed. Non-blocking mode returns immediately with EAGAIN/EWOULDBLOCK; then you use readiness (epoll/kqueue/select) or completion (IOCP, io_uring; .NET async) to know when to try. Same kernel buffer either way; the difference is only what your thread does when it's empty.
- Leaves: ❌ 11-04 "socket uses a protocol called TCP" (could be UDP/Unix). 🟡 11-04 "four numbers… you specify a port for both host and client" (client port usually ephemeral; 4-tuple identifies a connection, isn't 4 things you type). 🟡 11-04 "localhost for same host" (works; Unix domain sockets skip the IP stack). ❌ 11-04 bytes "living inside the network card or one of those controllers" when read. ❓(J) 11-04 "is read blocking or non-blocking, and what's going on lower?" ✅ bidirectional; ✅ TCP = reliable.
- Cross-ref: concurrency/002–003 (wait lists, no thread during I/O).

### G9. TCP is a byte stream: framing and meaning are the app's job — **P2** (💡 connection to his parser)
- **Root:** TCP preserves bytes and order but **not message boundaries**: one `send` of 100 bytes can arrive as 60 + 40, and two sends can arrive glued. So yes, the application protocol needs **framing** (length prefix, delimiter like `\n`, or a self-describing format). Unlike his UART parser, you don't need a checksum for corruption (TCP checks) or a sync byte for resync (no lost bytes mid-stream), though some protocols add magic/version bytes anyway. What arrives is **exactly the bytes the sender wrote**, headers stripped; *interpreting* them (encoding, endianness, serialization: JSON, protobuf, HTTP) is a contract between the two apps.
- Leaves: 💡/❓(J) 11-04 "because it's a stream, do I need parsing like the 0xAA/len/data/checksum serial parser?" (yes for framing; checksum/resync no). ❓(J) 11-04 "is the data what the other side sent, or translated?" (exact bytes; meaning by agreement).
- One layer up: the layer stack (app protocol / TCP / IP / Ethernet) — each layer adds and strips its own header.

---

## 2. Intake log (append-only)

### Intake 1 — 2026-11-04 · CPU addresses, MMU, controllers, IPC/sockets/TCP, boot tables
- Transcript: `intakes/2026-11-04_cpu-addresses-ipc-boot.md` · ~2,100 words · voice-to-text (mishearings: Colonel=kernel, boss=bus, right=write, parlor=parser, link bite=length byte, check some=checksum, PC/PCI≈ACPI).
- Context: self-study day on how addresses become physical; connects to blocking vs non-blocking I/O and an earlier serial packet parser exercise.

| # | Claim (paraphrase) | Mark | Group |
|---|---|---|---|
| 1 | Address in an instruction is virtual or physical depending on the instruction and CPU register state | ❌ (paging is a global mode once on) | G4 |
| 2 | CPU has an "address bus register"; its bits set lines high/low that open channels | ❌ | G2 |
| 3 | A read/write is a 100% direct connection between CPU register and the external location | ❌ | G2 |
| 4 | Controllers are on-chip units for specific tasks (inside CPU or IC?) | ✅/🟡 placement | G1 |
| 5 | Controller = block of registers at base + offsets; read/write them to communicate | ✅ | G2 |
| 6 | On-chip base addresses predetermined by the manufacturer | ✅ | G2 |
| 7 | How do we know which controller/offset to use? | ❓ J | G2/G5 |
| 8 | Plug-in devices need non-conflicting, non-hardcoded addresses → an orchestrator must exist, contradicts "direct lanes" | 💡❓ J (premise: every device has a memory address — false for USB) | G3 |
| 9 | MMU is an on-chip component like the controllers | 🟡 (per core, in the memory path) | G1/G4 |
| 10 | Page tables are data structures in RAM | ✅ | G4 |
| 11 | MMU "wakes up" when an instruction uses a virtual address | 🟡 | G4 |
| 12 | MMU looks in RAM at the location for that address, returns physical address | 🟡 (multi-level walk indexed by VA bits; TLB) | G4 |
| 13 | Page fault → CPU jumps to kernel handler → then gets the data | ✅/🟡 (instruction re-executes) | G4 |
| 14 | Doesn't understand CPU vs cores vs ALU vs controllers, how data flows | ❓ J | G1 |
| 15 | Separate virtual address spaces → processes can't communicate directly → IPC | ✅ | G7 |
| 16 | IPC = pipes or sockets | 🟡 (shared memory etc. missing) | G7 |
| 17 | Pipe = FIFO, same host, one writes one reads | ✅ (kernel buffer, one-way missing) | G7 |
| 18 | Socket = 4 numbers: IPs and ports of host and client, you specify both ports | 🟡 | G8 |
| 19 | Same host via localhost, or remote | ✅ (Unix domain sockets missing) | G8 |
| 20 | Socket is bidirectional | ✅ | G8 |
| 21 | Sockets use TCP | ❌ (API vs protocol) | G8 |
| 22 | Socket streams hex values / raw hexadecimal | ❌ | G6 |
| 23 | On read, OS fetches bytes that live in the NIC / a controller | ❌ (kernel receive buffer in RAM, via DMA) | G8 |
| 24 | Is socket read blocking or non-blocking; what's underneath? | ❓ J | G8 |
| 25 | Stream → do I need packet parsing like the 0xAA/len/data/checksum parser? | 💡❓ J | G9 |
| 26 | Is received data exactly what the sender sent, or translated? | ❓ J | G9 |
| 27 | A boot-time table ("PC/PCI…") defines all connected devices | 🟡 (ACPI; name forgotten again; only non-discoverable devices) | G5 |
| 28 | UEFI firmware searches for connected devices at boot | ✅ (for PCIe/USB) | G5/G3 |
| 29 | Firmware is hardcoded code in a physical chip | 🟡 (SPI flash is rewritable) | G5 |
| 30 | CPU must get firmware code by putting its address on the bus and reading | ✅ shape (via reset vector + address map) | G5 |
| 31 | All code runs this way: code in RAM, executor in the CPU | 💡 ✅ | G5 |
| 32 | Firmware finds devices, loads drivers, then creates the table the OS uses | ❌ (UEFI drivers ≠ OS drivers; ACPI mostly OEM-authored) | G5 |
| 33 | Doesn't know how drivers work | ❓ J | G5 (pointer to wi/009) |
| 34 | Is the table physical, a unit, or an abstract RAM structure like page tables? | ❓ J (RAM, software-read only) | G5 |

**Root concepts surfaced:** transaction + address decoding (G2) is the single biggest lever: claims 2, 3, 8 and part of 30 all follow from the "direct wire" model. Second: "who reads this structure, hardware or software?" (G5 Root B). Third: bytes vs representation (G6).
**Good signs:** two contradictions noticed mid-talk (claim 8: orchestrator vs direct lanes; claim 31: code lives away from the executor), and every flagged doubt pointed at a real gap.
**Related existing lectures:** concurrency/002–003 (blocking, wait lists, no thread during I/O), windows_internals/009 (what a driver is), windows_internals/005–006 (ACPI, setup vs run time).

---

## 3. Covered by cleanup lectures

| Lecture | Date | Groups covered | Leaves deferred |
|---|---|---|---|
| — | | | |

## 4. Changelog

| Date | Change |
|---|---|
| 2026-11-04 | Created. Intake 1 logged (34 claims); plan G1–G9. Moved to the public folder and renamed from "misconceptions" to "clarifications" the same day. |
