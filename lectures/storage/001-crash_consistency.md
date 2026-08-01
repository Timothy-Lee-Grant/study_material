2026_07_26_19_05-(Crash-Consistency)

# Lecture 001 — Crash Consistency: From Flash to Postgres

One problem, six layers, one set of solutions.

You have debugged a flash write interrupted by a power cut. You have held an oscilloscope on a rail that sagged mid-erase and watched a byte come back as neither the old value nor the new one. That experience is the *entire* conceptual foundation of database durability, and almost nobody arrives at Postgres holding it.

This lecture climbs the stack — flash cells → SSD firmware → filesystem → write-ahead log → LSM tree → replicated cluster — and shows that **every layer solves the same problem with the same four techniques.** By the end you should be able to read Postgres's `full_page_writes` documentation and recognize it as a thing you already understand from a different vantage point.

**Why this one, for you, now:**

- It is the highest-leverage bridge available to you. Most people learn database internals as received wisdom; you can derive them from physics you've touched.
- You run Postgres and pgvector in `LLM_Monitor`, you've built content-hash idempotent ingestion (which is idempotent replay — §10.5), and your LangGraph Postgres checkpointer is a durable state store whose crash semantics you have not yet had to think about. §14 makes that concrete.
- "What does ACID's D actually promise?" and "what is a torn page?" are standard senior interview questions, and the honest answers are narrower and more interesting than most candidates give.

**Stop line:** you can explain what `fsync` guarantees, why a WAL exists, what a torn page is, and how to make a crash-safe update to a file or a flash sector. You do **not** need to read the ARIES paper end to end or the ext4 journal implementation. §15 marks the boundary.

---

## Table of Contents

- [0. The thesis](#0-the-thesis)
- [1. The cast of characters](#1-the-cast-of-characters)
- [2. The stack of liars](#2-the-stack-of-liars)
- [3. Layer 1 — Flash: where you already live](#3-layer-1--flash-where-you-already-live)
- [4. Layer 2 — The SSD is a microcontroller running your algorithms](#4-layer-2--the-ssd-is-a-microcontroller-running-your-algorithms)
- [5. Layer 3 — Filesystems](#5-layer-3--filesystems)
- [6. Layer 4 — The write-ahead log](#6-layer-4--the-write-ahead-log)
- [7. Layer 5 — LSM trees](#7-layer-5--lsm-trees)
- [8. Layer 6 — Durability across machines](#8-layer-6--durability-across-machines)
- [9. The durability spectrum](#9-the-durability-spectrum)
- [10. The universal patterns](#10-the-universal-patterns)
- [11. Testing crash consistency](#11-testing-crash-consistency)
- [12. Common mistakes](#12-common-mistakes)
- [13. Interview relevance](#13-interview-relevance)
- [14. Applied to LLM_Monitor](#14-applied-to-llm_monitor)
- [15. Where the useful part ends](#15-where-the-useful-part-ends)
- [16. Sources](#16-sources)

---

## 0. The thesis

Three sentences carry this entire document.

> **1. Durability is an ordering problem, not a writing problem.** Writing data is easy. Guaranteeing that write A lands before write B, on a stack of components that all reorder and buffer for performance, is the hard part. Every mechanism in this lecture exists to buy an ordering guarantee from hardware that would rather not give you one.

> **2. At every layer there is exactly one atomic primitive, and every larger atomic operation is manufactured by arranging for the *commit* to be that primitive.** In flash it's a single aligned word write. On disk it's (approximately) a sector. In a filesystem it's `rename()`. In a database it's a commit record. You never make a big operation atomic — you make a big operation *staged*, and then flip one small atomic switch.

> **3. Crash consistency is a recovery story, not a prevention story.** You cannot prevent a crash mid-write. What you can do is arrange that **every possible interruption point leaves a state that recovery can unambiguously interpret.** That requirement — *unambiguously interpret* — is where checksums, sequence numbers, and idempotent replay come from.

Everything below is those three ideas at six different scales.

The corollary worth stating early, because it's the thing people get wrong: **"I wrote it" and "it survived" are completely different claims,** and the gap between them is measured in layers of cache, each of which is lying to you for good reasons.

---

## 1. The cast of characters

| Character | Real thing | Personality |
|---|---|---|
| **The Optimist** | `write()` | Returns instantly, says "done!", and has copied your bytes into RAM. Has touched no persistent medium whatsoever. Technically never lied — you assumed |
| **The Hoarder** | OS page cache / device write cache | Holds your data because batching is genuinely faster. Means well. Will hold it for *thirty seconds* if you don't say otherwise |
| **The Liar** | A consumer drive that ACKs FLUSH CACHE early | Reports the flush complete before the data reaches the medium, because benchmarks sell drives. Invalidates every guarantee above it |
| **The Notary** | `fsync()` | The only one who actually walks down and checks. Slow, expensive, hated by benchmarks, and the sole reason durability exists. Powerless if The Liar is downstream |
| **The Stone Tablet** | Flash | Erase before write, wears out, and forgets what it was doing if power drops mid-sentence |
| **The Scribe** | The write-ahead log | Writes down what it is *about* to do before doing it. Sequential, boring, append-only, and the reason recovery is possible at all |
| **The Signature** | The commit record | Tiny, atomic, and the exact instant "did not happen" becomes "happened." The whole system is arranged around making this one write atomic |
| **The Archivist** | Checkpointer | Periodically brings the durable data up to date with the log so the log can be recycled. Unglamorous; without it the Scribe's notes grow forever |
| **The Detective** | Recovery (ARIES) | Arrives after the crash, reads the Scribe's notes, and reconstructs exactly what was in flight and what must be undone |
| **The Shredder** | GC / compaction | Reclaims space by rewriting live data and discarding the dead. Necessary, and the source of write amplification |

**The relationship that matters:** The Optimist reports success, The Hoarder holds the data, and only The Notary can convert "reported" into "survived." Every data-loss incident in this document is someone trusting The Optimist.

---

## 2. The stack of liars

Between your variable and the physical medium sits a tower of components, each of which buffers and reorders for performance. Every one is a place your data can be when the power fails.

```
   your_struct.value = 42;
        │
        ▼  ┌───────────────────────────────────────────────┐
   CPU CACHE (write-back)                                   │  volatile
        │  └───────────────────────────────────────────────┘
        ▼  ┌───────────────────────────────────────────────┐
   write() → OS PAGE CACHE  ◄── The Hoarder                 │  volatile
        │   "dirty pages", flushed by kernel threads        │  (up to ~30s!)
        │   └──────────────────────────────────────────────┘
        ▼   fsync() ─── the ONLY thing that crosses this line
        │  ┌───────────────────────────────────────────────┐
   DEVICE WRITE CACHE (DRAM on the SSD)                     │  volatile
        │  unless the drive has power-loss capacitors       │  (usually)
        │  └───────────────────────────────────────────────┘
        ▼  ┌───────────────────────────────────────────────┐
   THE MEDIUM (NAND cells / platter)                        │  PERSISTENT
           └───────────────────────────────────────────────┘
```

### 2.1 What `write()` actually promises

Almost nothing. `write()` returning success means *the kernel has accepted your bytes*. It does not mean they reached the device, and on Linux dirty pages can sit in the page cache for tens of seconds before writeback. If the machine loses power in that window, the data is simply gone — and `write()` told you it succeeded.

### 2.2 The syscalls that matter

| Call | Guarantees |
|---|---|
| `write()` | Bytes are in the page cache. **Nothing durable.** |
| `fsync(fd)` | Data **and** metadata for that file are flushed to the device, and a cache-flush command was issued to the device |
| `fdatasync(fd)` | Data plus only the metadata needed to read it back. Skips e.g. mtime — measurably faster, and usually what a database wants |
| `O_SYNC` / `O_DSYNC` | Every `write()` behaves as if followed by `fsync`/`fdatasync` |
| `O_DIRECT` | Bypass the page cache. **Not a durability feature** — it skips the Hoarder but not the device cache. Databases use it to manage their own buffering, and still need a flush |
| `fsync(dirfd)` | Persists the *directory entry*. The step everyone forgets — see §5.2 |
| `sync_file_range()` | Hint-level control. **Does not** issue a device cache flush. Not a durability primitive despite the name |

### 2.3 The Liar

`fsync` issues a FLUSH CACHE (ATA) or SYNCHRONIZE CACHE (SCSI) to the device. Historically, and still in cheap hardware, **some drives acknowledge that command before the data is on the medium**, because flush latency looks bad in benchmarks. When that happens, every guarantee above it is void — no amount of correct database code helps.

This is why enterprise SSDs advertise **power-loss protection (PLP)**: onboard capacitors holding enough charge to flush the volatile DRAM cache to NAND after power is cut. That capacitor is, literally, what you are paying the enterprise price for. It's also why "we ran Postgres on consumer NVMe and lost data after a power cut" is a recurring and entirely predictable story.

**The firmware parallel is exact.** You already know that a `write` to a peripheral register may sit in a write buffer, which is why you issue a `DSB` before disabling a clock. `fsync` is `DSB` for storage — a barrier that costs real time and that exists because the layers beneath you reorder aggressively. Same instinct, six orders of magnitude apart in latency.

---

## 3. Layer 1 — Flash: where you already live

Start where your intuition is strongest. Everything above this section is a generalization of what's in it.

### 3.1 The physics that forces the design

| Property | Consequence |
|---|---|
| Erase granularity ≫ write granularity | To change one byte you erase a whole sector (4 KB–128 KB) |
| Erase sets bits to 1; writes only clear 1→0 | You can *add* zeros to an already-written word without erasing. Exploitable |
| Finite endurance (~10⁴–10⁵ erase cycles) | Rewriting one sector in a loop destroys it in weeks |
| Erase is slow (ms) and may stall the bus | Real-time consequences, and a wide window for power loss |
| **Power loss mid-program leaves indeterminate bits** | A word may read back as neither old nor new — **and may read differently on successive reads** |

That last row is the one to sit with. A partially-programmed flash cell can hold a charge level near the read threshold. It isn't "corrupt" in a stable way — it's *unstable*, and a verify pass can pass once and fail later. This is why **a CRC is not optional** and why "it read back fine" is not evidence.

**This is the origin of the term *torn write*,** and you have seen it physically. Hold onto that; §6.3 is the same phenomenon at the database layer.

### 3.2 The one atomic primitive

On virtually all NOR flash and most MCU embedded flash, **a single aligned word write is atomic** — it either happens or it doesn't. (Verify in your part's datasheet; some parts guarantee only a byte, some a double-word, and ECC-protected flash may have a wider minimum programming granularity.)

That single guarantee is the foundation everything else is built on. You have one atomic bit-flip. Now manufacture arbitrary atomic updates from it.

### 3.3 Pattern A — write-then-commit-pointer (shadow paging)

```
   BEFORE                          DURING                         AFTER
 ┌──────────────┐              ┌──────────────┐              ┌──────────────┐
 │ ptr → A      │              │ ptr → A      │              │ ptr → B      │◄ ONE
 ├──────────────┤              ├──────────────┤              ├──────────────┤  atomic
 │ A: old data  │              │ A: old data  │              │ A: garbage   │  word
 │ B: garbage   │              │ B: NEW data  │              │ B: new data  │  write
 └──────────────┘              └──────────────┘              └──────────────┘
                               ▲ power loss here             ▲ power loss here
                                 = still reads A               = reads B, complete
```

Write the new version somewhere else. Verify it (CRC). **Then** flip one pointer. There is no interruption point that yields a mixed state: before the pointer write you get the old version, after it you get the new one, and the pointer write itself is atomic by hardware guarantee.

This is **shadow paging**, and you'll meet it again as btrfs/ZFS copy-on-write (§5.3) and as the A/B firmware slot swap.

### 3.4 Pattern B — two records, sequence numbers, checksums

For metadata that must always be readable, keep **two** copies and alternate:

```c
typedef struct {
    uint32_t seq;        /* monotonic */
    config_t payload;
    uint32_t crc;        /* over seq + payload */
} record_t;

/* Write alternately to slot 0 and slot 1. */
void save(const config_t *c) {
    record_t r = { .seq = current_seq + 1, .payload = *c };
    r.crc = crc32(&r, sizeof(r) - 4);
    flash_erase(slot[next]);           /* the OTHER slot; current stays intact */
    flash_write(slot[next], &r, sizeof r);
    next ^= 1;
}

/* On boot: take the valid record with the higher sequence number. */
const record_t *load(void) {
    record_t *a = read(slot[0]), *b = read(slot[1]);
    bool va = crc_ok(a), vb = crc_ok(b);
    if (va && vb) return seq_gt(a->seq, b->seq) ? a : b;   /* handle wraparound */
    return va ? a : (vb ? b : NULL);                        /* NULL = factory default */
}
```

Every interruption point is interpretable: erase slot 1 → slot 0 still valid. Crash mid-write of slot 1 → its CRC fails, slot 0 wins. Complete → slot 1 has the higher sequence and wins.

**This is a filesystem superblock.** It is also, structurally, a Raft log entry: monotonic sequence, integrity check, and a rule for picking the winner. You will see this exact shape in §5.3, §6, and §8.

### 3.5 Pattern C — append-only log plus compaction

Rewriting one sector repeatedly destroys it. So don't. Append new records to a log region; when it fills, compact the live entries into a fresh region and erase the old one.

```
  [rec1][rec2][rec1'][rec3][rec2'][rec1'']  ──compact──►  [rec1''][rec2'][rec3]
   older versions are simply superseded                    only live versions
```

You get wear leveling and crash safety from the same mechanism: appends never destroy existing data, so a crash mid-append costs you only the partial record (caught by its CRC).

**This is a log-structured store.** §7 is this pattern with a sorted index bolted on and a marketing department.

### 3.6 LittleFS as the worked example

LittleFS — the sane default for MCU flash — is built entirely from the above. Its metadata lives in **copy-on-write metadata pairs**: two blocks per directory, written alternately, each entry checksummed, with a revision count deciding the winner. Recognize it? That's §3.4 exactly. File data is stored in a copy-on-write structure so that no update ever destroys the version being replaced.

The contrast is instructive: **FatFs is not power-fail-safe.** It updates the FAT and the directory entry in place, so a crash between them yields a genuinely inconsistent filesystem. That isn't a bug — FAT was designed for interoperability, not crash safety. Choosing FatFs for an SD card in a device that can lose power is a decision with a known failure mode, and it should be made deliberately.

### 3.7 Testing it

This is the part almost nobody does, and it's cheap:

- Put a relay or MOSFET on the power rail, driven by a spare GPIO or a second board.
- Loop: start a write, cut power at a **randomized** delay, restore, boot, verify the invariant ("config is either the old one or the new one, never garbage").
- Run it ten thousand times overnight.

Randomizing the delay is the whole trick — it samples interruption points uniformly instead of hitting the same one repeatedly. Ten thousand cycles will find the window you didn't think about, and it's the same statistical logic as fuzzing. Keep the harness; you'll want it every time the flash layout changes.

---

## 4. Layer 2 — The SSD is a microcontroller running your algorithms

Here's the reveal that makes the rest of the stack click.

**An SSD is an embedded system.** It has a microcontroller, DRAM, and firmware whose job is to run §3.3–3.5 on your behalf, at scale, and hide it behind an interface that pretends to be a disk with rewritable sectors. That firmware is called the **Flash Translation Layer**.

| FTL job | The §3 pattern it's running |
|---|---|
| Logical→physical block mapping | The pointer from Pattern A |
| Out-of-place writes | Never overwrite; write elsewhere and remap |
| Garbage collection | Pattern C compaction |
| Wear leveling | Pattern C, plus wear-aware block selection |
| Over-provisioning | Spare capacity so GC always has somewhere to write |
| ECC / bad block management | The CRC discipline, in hardware |

Consequences worth carrying upward:

- **Write amplification.** Writing 4 KB may cost far more NAND writes once GC rewrites live data to free a block. WAF is the ratio, and it's why sustained random-write performance collapses after a drive is full and why sequential/append workloads are kind to flash. Note that this makes LSM trees (§7) and flash **structurally compatible** — both prefer large sequential writes.
- **The abstraction leaks under power loss.** The FTL's own mapping tables live in DRAM and must themselves be crash-safe. A cheap drive with a poor FTL and no capacitors can lose or corrupt data *it already acknowledged* — including data written long ago, because GC may have been mid-relocation.
- **Sector atomicity is a convention, not a guarantee.** People assume a 512 B or 4 KB sector write is atomic. In practice it often is; **architecturally, nothing promises it.** Which is exactly why Postgres cannot assume it either (§6.3).

**The reframe:** you are not a firmware engineer learning about databases. Storage systems are firmware all the way down, and the layer everyone treats as a solved abstraction is running the same three patterns you'd write by hand.

---

## 5. Layer 3 — Filesystems

The filesystem must keep its own metadata consistent — a file's data blocks, its inode, the free-space bitmap, and the directory entry must agree — while any of those writes can be interrupted.

### 5.1 Journaling

The insight is the same one that produces the WAL: **describe the change in a small sequential record before applying it.**

```
  1. write the intended metadata change to the JOURNAL   (sequential)
  2. barrier / flush
  3. write the COMMIT record for that transaction        (atomic-sized)
  4. barrier / flush
  5. apply the change to the actual filesystem structures ("checkpoint")
  6. eventually, reclaim the journal space

  Crash before 3 → journal entry incomplete → discard. FS unchanged.
  Crash after  3 → replay the journal on mount. FS completed.
```

ext4 gives you three modes, and the naming causes real confusion:

| Mode | What's journaled | Guarantee |
|---|---|---|
| `journal` | Metadata **and** data | Strongest, slowest — data goes to disk twice |
| `ordered` (default) | Metadata only, but **data is written before the metadata commit** | Metadata always points at valid data. **Not** a guarantee your file contents are current |
| `writeback` | Metadata only, unordered | Fast; after a crash a file's metadata may point at blocks containing stale garbage |

Note what even the default gives you: **the filesystem stays consistent; your file's contents do not.** People conflate these constantly. A journaling filesystem promises *it* won't be corrupt. It promises nothing about whether your last write survived.

### 5.2 The atomic file update recipe

If you take one practical thing from this section, take this. To replace a file's contents atomically:

```c
fd = open("data.tmp", O_CREAT|O_WRONLY|O_TRUNC);
write(fd, buf, len);
fsync(fd);                    /* 1. contents durable BEFORE it's visible */
close(fd);

rename("data.tmp", "data");   /* 2. atomic swap — the commit point */

dirfd = open(".", O_RDONLY);
fsync(dirfd);                 /* 3. persist the DIRECTORY ENTRY itself */
close(dirfd);
```

- `rename()` over an existing path is **atomic** in POSIX: a reader sees either the old file or the new one, never a partial state. **That is this layer's atomic primitive** — the `rename` is playing the role of the single word write in §3.3.
- **Step 1 is mandatory.** Without it, `rename` may become durable before the contents do, and you get a correctly-named file full of garbage or zeros.
- **Step 3 is the one everyone forgets.** The rename is a *directory* modification; without `fsync` on the directory, the old name may resurface after a crash.

### 5.3 Copy-on-write filesystems

btrfs and ZFS take Pattern A (§3.3) and apply it to the whole filesystem: never overwrite a block in place; write a new one, then update the parent to point to it, recursively up to the root. Then flip **one** superblock pointer — atomically, with a sequence number and a checksum, exactly as in §3.4.

ZFS additionally checksums every block and verifies on read, which catches silent corruption the drive didn't report ("bit rot") rather than trusting the device's own ECC. That's a philosophical stance worth noticing: **do not trust the layer below you to report its own failures.** §6.4 is the same lesson learned the hard way.

### 5.4 The ext4 delayed-allocation story

Worth knowing because the lesson generalizes far beyond filesystems.

Many applications updated config files by truncating and rewriting in place, with no `fsync`. On ext3 this was *usually* fine: its default journaling mode flushed data roughly every five seconds, so the window was small. When ext4 arrived with **delayed allocation** — deferring block assignment to improve layout, widening the window to a minute or more — those same applications started producing **zero-length files** after a crash. Users lost configs and desktop state.

The ensuing argument is the interesting part. Application developers said ext4 broke their programs. The filesystem developers said the programs were always broken and had been relying on an *implementation accident* of ext3 rather than any documented guarantee. Both were right about the facts; ext4 ultimately added heuristics to auto-flush in the common rename/truncate patterns, because being technically correct and breaking everyone's desktop is a losing position.

> **The lesson:** *"it works in practice"* and *"it is guaranteed"* are different claims, and the gap between them is invisible right up until an implementation detail changes underneath you. This is the single most transferable idea in the lecture. It is also exactly why you should read what an abstraction *promises* rather than inferring its behaviour from observation — which, notably, is the discipline you're working on generally.

---

## 6. Layer 4 — The write-ahead log

Now the payoff. A database must make a multi-page, multi-index, multi-table change atomic and durable, on a medium where only one small write is atomic. It solves this with **exactly Pattern B from §3.4, generalized**.

### 6.1 The rule

> **Write-Ahead Logging: before any change to a data page is allowed to reach durable storage, a log record describing that change must already be durable.**

Why log first rather than just writing the data? Because you can't make the data write atomic — it's 8 KB across multiple sectors, possibly multiple pages across multiple files. But you *can* make a small sequential append atomic-ish and checksummed, and you can make the **commit record** small enough to be the atomic primitive.

```
   TRANSACTION                              WAL (sequential, append-only)
   UPDATE accounts SET bal=90 WHERE id=1;   ├─ LSN 100: page 7, bal 100→90
   UPDATE accounts SET bal=110 WHERE id=2;  ├─ LSN 101: page 9, bal 100→110
   COMMIT;                                  ├─ LSN 102: COMMIT txn 42   ◄── THE SIGNATURE
                                            └─ fsync() ─────────────────► durable
                                                    │
        ONLY NOW may the client be told "committed"  │
                                                     ▼
   the actual data pages 7 and 9 are still dirty in RAM. They get written
   later, lazily, by the Archivist (checkpointer). If we crash first,
   recovery replays LSN 100 and 101 from the log.
```

The trade that makes this worth it: you turn **many small random writes** (data pages scattered across the heap and indexes) into **one sequential append plus one fsync**. Random I/O is the expensive thing; sequential append is the cheap thing. The WAL is a latency optimization *and* a correctness mechanism, which is why it's ubiquitous.

**Recognize the shape:** §3.4 wrote a record with a sequence number and a CRC, then decided the winner by sequence. A WAL writes records with an **LSN** (Log Sequence Number) and a checksum, and recovery replays by LSN. Identical machine, bigger scale.

### 6.2 Recovery: the three phases (ARIES)

After a crash, The Detective runs:

```
  1. ANALYSIS  — scan forward from the last checkpoint. Determine which
                 transactions were in flight and which pages were dirty.
  2. REDO      — replay ALL logged changes from the checkpoint forward,
                 including those of transactions that never committed.
                 Result: the database is exactly as it was at crash time.
  3. UNDO      — roll back the transactions that had no COMMIT record,
                 using the undo information, writing compensation log
                 records as it goes (so the undo is itself crash-safe).
```

Two design points worth internalizing:

- **Redo is idempotent.** Each page stores the LSN of the last change applied to it, so replaying a record whose LSN is already on the page is skipped. This is what makes recovery safe to interrupt and restart — a crash during recovery is fine. **Idempotent replay is the single most reused idea in this lecture** (see §10.5).
- **"Repeat history, then undo"** — the counterintuitive step. Redo replays *uncommitted* work too, to reconstruct the exact crash-time state, and only then unwinds it. This is what makes fine-grained locking and partial rollbacks tractable.

**Checkpoints** exist so recovery doesn't have to replay the log from the beginning of time. The Archivist periodically flushes dirty pages and records "everything before LSN X is durable in the data files," letting the WAL before X be recycled. Checkpoint tuning is a straight trade: frequent checkpoints mean fast recovery and more steady-state I/O; rare ones mean the opposite.

### 6.3 Torn pages and `full_page_writes` — your flash bug, at database scale

This is the direct parallel, and it's the best single item in the lecture for you.

Postgres uses an 8 KB page. The storage stack below it splits that into 4 KB filesystem blocks and then 512 B sectors. **Nothing guarantees the 8 KB write is atomic.** So a power cut can leave a page that is half old and half new.

That is a **torn page**, and it is precisely the flash phenomenon from §3.1, three layers up.

Why is it fatal? Because Postgres uses **physio-logical logging**: a WAL record says *"on page 7, at offset 120, change this field"* — it identifies the page physically and the change logically. That's compact and fast, but it presumes the page is a *coherent starting point*. Apply a logical delta to a half-and-half page and you get well-formed-looking garbage.

The fix, `full_page_writes` (on by default — **leave it on**):

> The **first** time a page is modified after each checkpoint, write the **entire 8 KB page image** into the WAL, not just the delta. If recovery finds a torn page, it overwrites it wholesale with that known-good image, then applies subsequent deltas.

Costs and consequences:

- WAL volume spikes right after each checkpoint (every page's first touch carries a full image), which is a real and frequently-observed tuning artifact — if you see sawtooth WAL generation, this is why. Spacing checkpoints further apart reduces total full-page-write volume.
- It can only be safely disabled if your storage genuinely guarantees atomic 8 KB writes. Some enterprise arrays and filesystems do. **Your Docker volume does not.**
- MySQL/InnoDB solves the same problem differently, with a **doublewrite buffer**: write every page to a scratch area first, then to its real location. Same idea (shadow paging, §3.3), different placement.

### 6.4 Fsyncgate — when the layer below lies about *failures*

The best story in storage, and it lands especially well for a firmware engineer.

In 2018 it emerged that Postgres's handling of `fsync()` errors risked silent data loss. The mechanism:

1. Linux writeback fails (a transient device error, a thin-provisioned volume filling, a USB disk yanked).
2. The kernel **marks the failed dirty pages clean and drops them**, then flags the error.
3. The error is reported to **whichever file descriptor calls `fsync()` first — once**. Then the flag is cleared.
4. Postgres saw `EIO`, logged it, and **retried the checkpoint**. The retry called `fsync()` again, which now returned **success** — because the error flag had been consumed and the dirty pages no longer existed.
5. Postgres concluded the checkpoint succeeded, recycled the WAL, and the data was gone. No error, no corruption warning.

The root confusion was an assumption everyone shares: Postgres believed `fsync()` success meant *"all writes since the last successful fsync are durable."* What it actually means is *"all writes since the last fsync call are durable"* — and a failed `fsync` consumes the error while destroying the data.

The fix, committed in November 2018 and back-patched to every supported release: **PANIC on `fsync` failure.** Crash the server and recover from the WAL, because after a failed flush the in-memory state can no longer be trusted and replay is the only sound path. The `data_sync_retry` setting exists to restore the old behaviour on platforms that don't drop dirty data. **Leave it at the default.**

Three lessons, all of which transfer:

1. **Error reporting is not necessarily sticky.** You may get exactly one chance to observe a failure. A firmware engineer who has read a clear-on-read status register will recognize this instantly — and will also recognize that reading it twice loses the information.
2. **"Retry the flush" is not a valid recovery strategy** when the failure destroyed the thing you were flushing.
3. **Crashing loudly beats continuing on unverifiable state.** This is a watchdog. The panic-on-fsync-failure fix is precisely the design philosophy of §8.5 in the firmware atlas: bound the damage, don't try to be clever after an unexplained fault.

### 6.5 The Postgres settings that actually matter

| Setting | Meaning | Guidance |
|---|---|---|
| `fsync` | Master switch for flushing at all | **Never** turn off outside a throwaway benchmark. Off = a crash can corrupt the cluster unrecoverably |
| `full_page_writes` | Torn-page protection (§6.3) | Leave on unless your storage guarantees atomic 8 KB writes |
| `synchronous_commit` | How much durability a COMMIT waits for | See below — the one genuinely useful knob |
| `wal_sync_method` | Which syscall is used (`fdatasync`, `open_datasync`, …) | Platform default is usually right; `pg_test_fsync` measures it |
| `data_sync_retry` | Retry vs PANIC on fsync failure (§6.4) | Leave at default (PANIC) |
| `checkpoint_timeout` / `max_wal_size` | Checkpoint frequency | Longer = less full-page-write volume, slower recovery |

`synchronous_commit` is the durability dial, and it's a genuine engineering choice rather than a "more is better" setting:

| Value | COMMIT returns after | Survives |
|---|---|---|
| `off` | WAL is in **memory** | Nothing. Bounded data loss window (a few hundred ms), but **no corruption** — the cluster stays consistent |
| `local` | Local WAL `fsync` | OS crash, power loss on this machine |
| `remote_write` | Standby has *received* it | Primary loss, if the standby's OS survives |
| `on` (default) | Standby has **flushed** it | Primary loss |
| `remote_apply` | Standby has **applied** it | Primary loss, and read-your-writes on the standby |

The `off` row is the interesting one and it's widely misunderstood: it is **not** `fsync=off`. It trades a bounded window of *recent committed transactions* for a large throughput gain, without risking cluster corruption. For something like bulk ingestion of re-derivable data, that's a defensible trade. For anything with money in it, obviously not.

### 6.6 A 2026 note

**PostgreSQL 18** introduced asynchronous I/O — `io_uring` on Linux (kernel 5.1+, built with `--with-liburing`), plus a portable worker-based implementation — configured via `io_method`. It reports large gains (up to ~3×) on read-heavy paths: sequential scans, bitmap heap scans, `VACUUM`.

**Note carefully what did *not* change: writes, including WAL writes, remain synchronous, and the durability guarantees are unchanged.** That's the correct design — the WAL flush is the commit point, and making it asynchronous would mean giving up the guarantee. Knowing that AIO landed *and* that it deliberately left the durability path alone is a good signal in a conversation about the platform.

---

## 7. Layer 5 — LSM trees

Now §3.5 (append-only log plus compaction) at database scale — the structure behind RocksDB, LevelDB, Cassandra, ScyllaDB, TiKV, and the storage engines under a great deal of modern infrastructure.

### 7.1 The structure

```
   WRITE ──► WAL (append, sequential, for crash recovery)
        └──► MEMTABLE (sorted structure in RAM)
                 │  when full, freeze and flush
                 ▼
             SSTable L0   [sorted, IMMUTABLE, checksummed]
                 │  compaction merges + discards superseded/deleted keys
                 ▼
             SSTable L1, L2, ... (progressively larger levels)

   READ ──► memtable → L0 → L1 → ...  (first hit wins; newest level first)
            bloom filters skip levels that certainly lack the key
```

The two properties that define it:

- **SSTables are immutable.** Nothing is ever modified in place — updates and deletes are new records (a delete writes a *tombstone*). Crash safety comes almost free: a file is either completely written and linked in, or it isn't.
- **All writes are sequential appends.** Which, per §4, is exactly what flash wants.

### 7.2 The RUM conjecture

You cannot optimize **R**ead, **U**pdate, and **M**emory/space simultaneously; you pick two and pay in the third.

| | B-tree (Postgres, MySQL/InnoDB) | LSM tree (RocksDB, Cassandra) |
|---|---|---|
| Write path | Update page in place; random I/O | Append; sequential I/O |
| Read path | ~O(log n), one lookup, predictable | May check several levels; bloom filters mitigate |
| Write amplification | Lower per write, but random | Higher (compaction rewrites data repeatedly) |
| Read amplification | Low | Higher |
| Space amplification | Low; some page fragmentation | Higher — superseded versions live until compacted |
| Range scans | Excellent | Good |
| Predictability | Steady | **Compaction causes latency spikes** — the classic operational complaint |
| Best for | Mixed read/write, strong transactional needs | Write-heavy, high ingest |

**Postgres is not an LSM.** It's a heap plus B-tree indexes with MVCC — old row versions live in the heap until `VACUUM` reclaims them. That's worth knowing precisely because MVCC gives Postgres a *different* form of the same space-amplification problem: bloat, and a background reclaimer. Compaction and `VACUUM` are cousins — both are The Shredder, reclaiming space occupied by superseded versions, and both cause the same operational surprises when they fall behind.

### 7.3 The pattern, restated

An LSM tree is: **an append-only log, an in-memory index, immutable checksummed segments, and a background compactor.** That is §3.5 with a sorted index and bloom filters. If you understood the flash version, you understand this one — which is the entire argument for approaching databases from your direction.

---

## 8. Layer 6 — Durability across machines

`fsync` protects you from a process crash and a power cut. It does not protect you from the machine catching fire, the disk failing, or the region going offline. Durability at that scale means **copies on independent failure domains**.

Survey level — this is the entry point to a future distributed systems lecture, not a treatment of it.

| Mechanism | Protects against | Cost |
|---|---|---|
| RAID / mirroring | A single disk failing | Local only; not a backup |
| **Async replication** | Losing the primary machine — **with a data-loss window** | Fast; recent commits may be lost |
| **Sync replication** | Losing the primary, no loss of acknowledged commits | Every commit pays a network round trip |
| Quorum (Raft/Paxos) | Minority node loss, with automatic failover | Complexity; a majority must be reachable |
| Cross-region replication | Losing a datacenter | Latency, egress cost |
| **Backups + PITR** | Operator error, corruption, ransomware, a bad migration | The only thing on this list that protects against *you*. **Replication is not a backup** |

**The key connection:** a Raft log *is* a write-ahead log distributed over a network. Same properties — append-only, monotonic sequence numbers, replay-based recovery, and a commit point (here, "a majority has it durably" rather than "fsync returned"). Consensus algorithms feel exotic until you notice they are §6.1 with the durability requirement redefined as "a quorum acknowledged" instead of "the disk acknowledged." That reframe is the single most useful thing to carry into distributed systems study.

And the sharpest line in this section: **replication protects against hardware failure; it faithfully replicates your `DROP TABLE`.** Only backups with point-in-time recovery protect against the operator, and PITR is itself built on the WAL — take a base backup, archive WAL segments, and replay to any moment.

---

## 9. The durability spectrum

The table to keep. "Is my data safe?" is not a yes/no question; it's "safe against *what*?"

| Your data survives… | …if you have done this |
|---|---|
| The process crashing | `write()` to the OS page cache |
| **The OS crashing / power loss** | `fsync()` **and** a device that doesn't lie about flushes (PLP, or a battery-backed controller) |
| A torn write during that power loss | Full-page images / doublewrite / shadow paging, plus **checksums** |
| A single disk failing | RAID or replication |
| **The whole machine dying** | Synchronous replication to another machine |
| The datacenter dying | Cross-region replication |
| **Somebody running the wrong migration** | Backups + point-in-time recovery |
| Silent bit rot | End-to-end checksums (ZFS-style), verified on read |

Two things to notice. **ACID's "D" only covers row two.** Durability, formally, means *committed transactions survive a crash of the database or the OS*. It says nothing about disk failure, machine loss, or you. Candidates who state that scope correctly stand out, because most recite "committed data is permanent" and can't bound it.

And the chain is only as strong as its weakest link: correct WAL code on a lying drive gives you row one. **Correctness at every layer above is worthless if any layer below defects.**

---

## 10. The universal patterns

The synthesis. Five techniques; everything above is a combination of them.

### 10.1 Shadow paging / copy-on-write
*Write the new version elsewhere; switch one pointer.*
Flash Pattern A · A/B firmware slots · btrfs/ZFS · InnoDB doublewrite · `rename()` · immutable SSTables · blue-green deployment.

### 10.2 Write-ahead logging
*Record the intent durably before performing the act.*
Flash journal · ext4 journal · Postgres WAL · LSM WAL · Raft log · the transactional outbox pattern · event sourcing.

### 10.3 The single atomic switch
*Manufacture large atomicity from one small atomic primitive.*
A single aligned flash word · a sector · `rename()` · the COMMIT record · a superblock pointer · a quorum acknowledgement.

### 10.4 Checksums plus monotonic sequence numbers
*Make "complete" distinguishable from "incomplete," and "newer" from "older."*
Flash record CRC + seq · superblocks · LSN · Raft term/index · ZFS block checksums · ETags and optimistic concurrency.

### 10.5 Idempotent replay
*Make repeating an operation harmless, so recovery can be interrupted and restarted.*
ARIES redo skipping records whose LSN ≤ the page LSN · LSM compaction restart · **your content-hash ingestion in `LLM_Monitor`** · idempotency keys in payment APIs · Kafka consumer offsets · Kubernetes reconciliation loops.

**That last one deserves emphasis.** You already built idempotent ingestion by content hash. That's not a nice convenience — it is the same property that makes database recovery possible, and it's the reason your ingestion pipeline is safe to kill and restart. You implemented a crash-consistency primitive without labelling it. Label it; it's a better story than "I deduplicate documents."

### 10.6 The design procedure

When you next need something crash-safe, this is the algorithm:

1. **Identify your atomic primitive.** What is the largest write that is genuinely all-or-nothing here?
2. **Stage everything else before it.** All the expensive, non-atomic work goes first, and is verifiable.
3. **Make the commit that one primitive.**
4. **Enumerate every interruption point** and ask: *can recovery unambiguously tell what happened?* If any point is ambiguous, you need a checksum or a sequence number there.
5. **Make replay idempotent**, so recovery itself can crash.
6. **Test by actually killing it**, at randomized points, thousands of times.

Step 4 is the one people skip, and it's where the bugs are.

---

## 11. Testing crash consistency

Almost nobody does this. Doing it is a strong differentiator, and it maps directly onto the eval-harness instinct you already have.

| Level | Tool / method |
|---|---|
| Firmware | A relay on the power rail, randomized cut timing, thousands of cycles (§3.7) |
| Filesystem/block | `dm-flakey`, `dm-log-writes` (record the block-level write stream, then replay it to any prefix and check the invariant), `CrashMonkey`, `ALICE` |
| Process | `kill -9` in a loop; container kill; **`docker compose kill` rather than `down`** |
| Database | Fault injection on the volume; verify with `pg_checksums` and `amcheck` |
| Distributed | **Jepsen** — the standard for finding consistency violations under partition and clock skew, and the reason several databases quietly fixed their claims |

The `dm-log-writes` idea is the elegant one and generalizes: **capture the exact sequence of writes, then replay every possible prefix and assert your invariant holds at each.** That's exhaustive testing of interruption points rather than random sampling, and it's the same move as replaying a recorded event log against a state machine.

---

## 12. Common mistakes

1. Believing `write()` returning success means the data is safe. It means the kernel took it.
2. Forgetting the **directory** `fsync` after `rename()`.
3. Skipping the `fsync` on the temp file *before* the rename, producing a correctly-named empty file.
4. Assuming a sector or page write is atomic. Nothing architecturally guarantees it (§4, §6.3).
5. Turning off `fsync` in Postgres to "speed up" a real system. That's corruption, not a tuning knob. (`synchronous_commit=off` is the setting you actually meant.)
6. Turning off `full_page_writes` without storage that guarantees atomic 8 KB writes.
7. Treating replication as a backup. It replicates your mistakes faithfully and instantly.
8. Retrying a failed flush and believing the subsequent success (§6.4).
9. Running a database on a consumer SSD with no power-loss protection and expecting the guarantees.
10. Running a database on a network filesystem or a virtualized bind mount whose flush semantics you haven't verified.
11. Rewriting the same flash sector in a loop and wearing it out.
12. Using FatFs where power can fail, without knowing it isn't power-fail-safe.
13. Assuming a journaling filesystem protects your *file contents*. It protects filesystem metadata (§5.1).
14. No checksums, so you cannot distinguish complete from incomplete records.
15. Non-idempotent recovery, so a crash during recovery makes things worse.
16. Never testing any of it, because crashes are "rare."

---

## 13. Interview relevance

This is unusually strong ground for you, because most candidates have only the database half.

**Questions you should now answer cold:**

- *"What does `fsync` do, and why is it slow?"* → Flushes the file's dirty pages from the OS page cache and issues a cache-flush command to the device. Slow because it's a synchronous barrier all the way to persistent media. And it's only as trustworthy as the device — consumer drives have historically acknowledged flushes early, which is what power-loss-protection capacitors exist to fix.
- *"How does a database guarantee durability?"* → Write-ahead logging. A log record for every change, and a commit record fsynced before the client is told "committed." Data pages are written lazily afterward; recovery replays the log. It converts many random writes into one sequential append plus one fsync, so it's a performance win as well as a correctness mechanism.
- *"What's a torn page?"* → An 8 KB database page partially written when the stack below only guarantees atomicity at ~512 B–4 KB. Postgres handles it with `full_page_writes` — a full page image in the WAL on first touch after a checkpoint; InnoDB uses a doublewrite buffer. **And I've seen the same phenomenon physically, in NAND flash interrupted mid-program.**
- *"What does ACID's D actually promise?"* → That committed transactions survive a crash of the database or OS. **Not** disk failure, not machine loss, not operator error. Those need replication and backups, which are different mechanisms with different failure domains.
- *"B-tree or LSM?"* → RUM conjecture. B-trees favour reads and predictable latency with random in-place writes; LSMs favour write throughput with sequential appends, at the cost of read/space amplification and compaction latency spikes. LSMs also match flash physics better, since flash hates random small writes.
- *"How would you atomically update a file?"* → Temp file, fsync it, rename, fsync the directory. `rename` is the atomic primitive; the two fsyncs are the ordering barriers, and the directory one is the commonly missed step.
- *"Design a crash-safe settings store for an embedded device."* → §3.4, out loud: two slots, monotonic sequence, CRC, alternate writes, pick the valid record with the higher sequence. Then note it's the same shape as a filesystem superblock and a Raft log entry.

**The differentiating move** is to answer a database question and then reach *down*: "the same problem exists in NAND flash, where I've debugged it with a power supply and a scope." That reverses the usual direction — nearly everyone reasons downward from the database and stops at the abstraction. It's a genuinely rare vantage point, and it also gives you a real answer to "tell me about a hard bug."

---

## 14. Applied to LLM_Monitor

Concrete, and mostly quick.

**Postgres in Docker — verify the foundation first**

- [ ] **Check where your data volume actually lives.** A named Docker volume on a Linux host is fine. A bind mount into a virtualized filesystem (Docker Desktop on macOS/Windows) has historically had unreliable flush semantics. For a dev environment that's acceptable — but *know* which one you have, and don't reason about durability as though it's a bare-metal Linux disk.
- [ ] Confirm `fsync=on` and `full_page_writes=on`. They're the defaults; confirm nothing in your compose or tuning turned them off.
- [ ] Run `pg_test_fsync` once. It takes a minute and tells you what your storage stack actually costs per flush — and an implausibly fast number is evidence something in the stack is lying.
- [ ] Use `docker compose kill` (not `down`) to test. `down` shuts Postgres down cleanly, which tests nothing. Then verify the cluster comes back and the data is intact.

**Consider `synchronous_commit`**

- [ ] For **bulk pgvector ingestion of re-derivable content**, `synchronous_commit=off` is a defensible, sizable throughput win: you risk losing a few hundred milliseconds of recent commits, not cluster integrity, and your content-hash ingestion can simply re-ingest. Set it per-session or per-transaction rather than globally, so the rest of the system keeps full durability. **This is a real optimization with an articulable risk argument — good portfolio material.**

**The LangGraph Postgres checkpointer — the part that actually needs thought**

Your checkpointer is a durable state store for in-flight agent runs. That means it inherits every question in this lecture, and a few of its own:

- [ ] **What happens if the process dies between a tool call and its checkpoint write?** On resume, does the agent re-execute the tool? If the tool has side effects, you need idempotency — the same problem as §10.5, and the same problem as retried commands in the browser-agent doc.
- [ ] **Make tool calls idempotent or record intent before acting.** This is write-ahead logging applied to agent actions: persist "I am about to call tool X with args Y" *before* calling it, so recovery can tell the difference between "never started" and "may have completed." That's §10.2, and it's the correct design.
- [ ] Decide the recovery policy explicitly: resume, restart, or fail the run. Undecided means "whatever the framework does," which is not a design.
- [ ] Bound checkpoint growth and have a retention policy. Unbounded state is a slow outage.

**Backups**

- [ ] You do not currently have a backup story. For a portfolio project, `pg_dump` on a schedule is enough — but knowing the difference between a logical dump and a physical base backup plus WAL archiving for PITR is the interview-relevant part. **Replication would not be a backup** (§8).

**The framing to keep:** most people describe a RAG pipeline. Being able to say *"here's my durability model, here's what each layer survives, here's why I chose `synchronous_commit=off` for ingestion specifically, and here's how agent tool calls stay idempotent across a crash"* is an entirely different level of conversation.

---

## 15. Where the useful part ends

**Worth your time:**
- Run the power-cut rig from §3.7 on a board you own. A few hours, and it makes all of this permanent rather than theoretical.
- Read the Postgres docs on WAL configuration and `full_page_writes`. Short, and you'll now understand every sentence.
- Read the fsyncgate thread (§6.4). It's a real engineering argument between excellent engineers and it's more instructive than any textbook chapter.
- Skim the ARIES paper's introduction and recovery-phases section. Don't read all 90 pages.
- Read the LittleFS design document — it's short, clear, and it's §3 written by people who had to ship it.

**Not worth your time right now:**
- The full ARIES paper, including nested top actions.
- ext4's journal implementation (`jbd2`) source.
- RocksDB's compaction-strategy tuning surface.
- NVMe specification internals or FTL research literature.
- Building your own storage engine.

**The rule, same as always:** you need enough to *predict failure and choose correctly*. You do not need the implementation to use it well. If you catch yourself reading `jbd2` source, ask what decision it's informing — if the answer is "none," write the question down and come back to it deliberately.

**Next actions, in order:**
1. Run the four Postgres checks in §14 (thirty minutes, and one of them may surprise you).
2. Decide and write down the checkpointer recovery policy.
3. Build the power-cut rig — it's the piece nobody else will have.

---

## 16. Sources

- [PostgreSQL 18: Asynchronous Commit — official docs](https://www.postgresql.org/docs/current/wal-async-commit.html)
- [PostgreSQL: Non-Durable Settings — official docs](https://www.postgresql.org/docs/current/non-durability.html)
- [Full page writes — PostgreSQL wiki](https://wiki.postgresql.org/wiki/Full_page_writes)
- [On the impact of full-page writes — EDB](https://www.enterprisedb.com/blog/impact-full-page-writes)
- [A tale of two databases: how PostgreSQL and MySQL handle torn pages — Percona](https://www.percona.com/blog/a-tale-of-two-databases-how-postgresql-and-mysql-handle-torn-pages/)
- [Torn write detection and protection — transactional.blog](https://transactional.blog/blog/2025-torn-writes)
- [Fsyncgate: errors on fsync are unrecoverable — Dan Luu (archived thread)](https://danluu.com/fsyncgate/)
- [PostgreSQL's handling of fsync() errors is unsafe — original pgsql-hackers thread](https://www.postgresql.org/message-id/CAMsr+YHh+5Oq4xziwwoEfhoTZgr07vdGG+hu=1adXx59aTeaoQ@mail.gmail.com)
- [PANIC on fsync() failure — the commit](https://www.postgresql.org/message-id/E1gObR6-00023g-5u@gemulon.postgresql.org)
- [All your GUCs in a row: data_sync_retry — The Build](https://thebuild.com/blog/all-your-gucs-in-a-row-datasyncretry/)
- [PostgreSQL 18 asynchronous I/O — Neon](https://neon.com/postgresql/18/asynchronous-io)
- [Waiting for Postgres 18: accelerating disk reads with asynchronous I/O — pganalyze](https://pganalyze.com/blog/postgres-18-async-io)
- [PostgreSQL 18.0 released — Phoronix](https://www.phoronix.com/news/PostgreSQL-18-Released)

Recommended, not consulted: the ARIES paper (Mohan et al., 1992); the LittleFS design document; *Database Internals* (Alex Petrov); *Designing Data-Intensive Applications* ch. 3 (Kleppmann); the Jepsen analyses.

---

## Appendix — The one-paragraph version

Durability is an ordering problem, not a writing problem: every layer between your variable and the physical medium buffers and reorders, so `write()` returning success means only that the kernel took your bytes, and `fsync` is the single barrier that crosses into persistence — assuming the device isn't lying about flushes, which cheap ones historically have. At every layer there is exactly one atomic primitive — a single aligned word in flash, roughly a sector on disk, `rename()` in a filesystem, a commit record in a database, a quorum acknowledgement in a cluster — and every larger atomic operation is manufactured by staging all the expensive work first and then flipping that one small switch. Crash consistency is therefore a *recovery* story: you cannot prevent interruption, so you arrange that every interruption point leaves a state recovery can unambiguously interpret, which is precisely where checksums, monotonic sequence numbers, and idempotent replay come from. Those techniques then repeat, unchanged, at every scale: your two-slot CRC'd config store in flash is a filesystem superblock is a WAL record is a Raft log entry; your append-and-compact wear-levelling scheme is an LSM tree; your A/B slot pointer swap is shadow paging is `rename()` is blue-green deployment. Postgres's `full_page_writes` exists because an 8 KB page can be torn across sectors — the same phenomenon you have already seen in a NAND cell interrupted mid-program, three layers down. And the durability question is never yes/no but "against what": `fsync` survives power loss, replication survives the machine, only backups survive you.
