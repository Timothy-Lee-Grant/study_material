# Lecture 014: Designing a Device-to-App Data Path (Interrupt Line, FIFO, Driver, Reader)

> **For:** Timothy · **Date:** 2026-10-31
> **Prerequisites:** 005 (IRQL, ISR → DPC → work item), 009 (what a driver is, IRPs, the request path from `ReadFile` to a driver). Helpful: `leetcode/019` (parsing the byte stream this path delivers).
> **Why this lecture:** 005 taught the pieces (ISR, DPC, IRQL) one at a time. This lecture puts them together into a **design**: a device signals data with an interrupt line, the host must move the data into a buffer without losing any, and an application with a window must receive it without freezing. That's a very common kind of platform design question, and it has one trap that catches almost everyone: **putting a blocking read in the DPC.** Your understanding tracker notes that this one is still open, so the lecture builds the design step by step and explains exactly why the blocking read can't live there and where it goes instead.
> **Format notes:** the full design problem is given. Linux first (its version is short and shows the shape clearly), then Windows/KMDF. Driver code is a **sketch** to show structure and names, not compiled here; the FIFO sizing model in `code/014_fifo_sizing.py` was run. No firmware analogies.

---

## Core ideas (the answer key)

1. **Draw the path end to end before choosing mechanisms:** device FIFO → interrupt line → host interrupt handler → code that reads the device → driver buffer → read requests from the app → app's reader thread → UI thread. Every arrow is a hand-off that can lose data or block.
2. **A level-triggered line stays asserted as long as the condition is true** ("FIFO not empty"). If the handler returns without masking the line or emptying the FIFO, the interrupt fires again immediately and forever: an **interrupt storm**. The fix is to **mask the line until the FIFO has been drained**, then unmask.
3. **A level-triggered "not empty" line can't miss data at unmask time.** If bytes arrived while you were draining, the line is still asserted when you unmask, and the interrupt simply fires again. (An edge-triggered line would need an explicit re-check.)
4. **A DPC runs at DISPATCH_LEVEL, where the thread can't wait.** A "blocking read" means "put this thread to sleep until the transfer completes", and at DISPATCH_LEVEL there's no thread switch to sleep through. So **a DPC must never call a blocking read.** That's the rule behind the scheduler fact you already know: the scheduler itself runs at DISPATCH_LEVEL, so code at or above it can't be descheduled.
5. **Blocking reads belong at PASSIVE_LEVEL:** in a **passive-level ISR** (KMDF `PassiveHandling = TRUE`, made for devices behind slow buses like I²C or SPI), in a **work item**, or in a dedicated **thread**. Linux's equivalent is a **threaded IRQ** with `IRQF_ONESHOT`.
6. **The driver keeps its own buffer** (a ring buffer, usually much larger than the device FIFO). It decouples "drain the device fast" from "the app reads when it reads".
7. **Apps get data through read requests the driver holds until data exists.** In KMDF: a **manual queue** of pending read requests, completed when bytes arrive. In Linux: `read()` sleeps on a **wait queue** until the buffer isn't empty; `poll()` lets the app wait on several things at once. The I/O manager doesn't move bytes on its own; the driver completes the request and the I/O manager copies the result to the app.
8. **FIFO sizing depends on worst-case latency, not average throughput.** Bytes that arrive between "line asserted" and "first read" must fit in the FIFO. A host that's 5× faster than the device on average can still overflow a 64-byte FIFO if it starts reading 1 ms late.
9. **Decide an overflow policy anyway:** who drops (device or driver), which bytes (newest or oldest), and how it's reported (a sticky overflow flag, a counter, sequence numbers). Silent loss is the one choice that's never acceptable.
10. **The UI thread never calls a blocking read.** A worker thread (or async I/O) reads, parses, and posts batched updates to the UI thread.

---

## Table of Contents

- [0. The design problem](#0-the-design-problem)
- [1. Draw the whole path first](#1-draw-the-whole-path-first)
- [2. The interrupt line: level, masking, storms](#2-the-interrupt-line-level-masking-storms)
- [3. Where the blocking read can run](#3-where-the-blocking-read-can-run)
- [4. Linux version: threaded IRQ, kfifo, wait queue](#4-linux-version-threaded-irq-kfifo-wait-queue)
- [5. Windows version: passive-level interrupt, ring buffer, manual queue](#5-windows-version-passive-level-interrupt-ring-buffer-manual-queue)
- [6. Sizing: bursts, latency, and the 64-entry FIFO](#6-sizing-bursts-latency-and-the-64-entry-fifo)
- [7. Overflow policy](#7-overflow-policy)
- [8. The app side: reader thread and UI thread](#8-the-app-side-reader-thread-and-ui-thread)
- [9. How to present this design](#9-how-to-present-this-design)
- [Common mistakes](#common-mistakes)
- [Self-check questions](#self-check-questions)
- [Sources](#sources)

---

## 0. The design problem

**Design: getting bursty device data to a GUI (paraphrased, in the usual form of this problem).**

An external device produces data bytes and stores them in its own **64-entry FIFO** (first in, first out queue). It connects to a computer through:
- a **dedicated, active-low interrupt line**: the device holds it low **while its FIFO is not empty**, and releases it (high) when the FIFO is empty;
- a data connection the host reads through a provided function `ReadByte()` (or `ReadBuffer()`), which **blocks** until the transfer finishes and returns the oldest byte from the FIFO.

The device sends data in **bursts**. The host must:
- deliver every byte, in order, to an application with a graphical user interface;
- avoid **interrupt storms**;
- keep the system and the UI responsive.

Design the software: which components exist, what runs in each, at what priority, and how data moves between them. State your assumptions (data rates, what happens on overflow).

The first version uses Linux; then do the same on Windows.

---

## 1. Draw the whole path first

```
 ┌──────── device ────────┐           ┌──────────────────────── host ─────────────────────────────┐
 │ producer → [FIFO 64] ──┼── data ──►│ ReadByte() (bus transfer; BLOCKS)                         │
 │         not-empty ─────┼── IRQ ───►│ interrupt controller → handler → reader code              │
 └────────────────────────┘  (low =   │                         │                                 │
                             data)    │                         ▼                                 │
                                      │                driver ring buffer (e.g. 4 KB)             │
                                      │                         │                                 │
                                      │      pending read requests (KMDF manual queue / wait q)   │
                                      │─────────────────────────┼────── kernel / user boundary ───│
                                      │                         ▼                                 │
                                      │      app reader thread: ReadFile / read() → parse         │
                                      │                         │ post batched updates            │
                                      │                         ▼                                 │
                                      │      UI thread: draws                                     │
                                      └───────────────────────────────────────────────────────────┘
```

Then ask four questions at every arrow:
1. **Who runs this, and at what priority (IRQL)?**
2. **Can it block?**
3. **What if the next stage is slow?** (Where does data wait, and how much fits?)
4. **What wakes the next stage?**

The rest of the lecture answers those four questions for each arrow.

---

## 2. The interrupt line: level, masking, storms

**Level-triggered** means the interrupt controller looks at the line's **level**: "low = interrupt pending". **Edge-triggered** means it looks for a **transition**: "went from high to low = one interrupt".

This line is level-triggered by nature: it's low for as long as the FIFO has data. Consequences:

- **Storm:** when the handler returns, the controller checks the line again. If it's still low (FIFO still has data, because you haven't read it yet), the interrupt fires again immediately. The CPU does nothing but enter and leave the handler. That's an interrupt storm. On Windows a storm at DIRQL can also trip the DPC/ISR watchdog (bugcheck 0x133, lecture 002).
- **The fix: mask, drain, unmask.** Mask (disable) the line at the interrupt controller in the first, tiny handler. Do the draining later at a level where it's allowed to block. When the FIFO is empty (the line went high), unmask.
- **Why this can't lose data:** suppose a new byte arrives just after your last read and before you unmask. The line goes low again. When you unmask, the controller sees "low" and fires again. Level-triggering means **the line remembers** for you. With an edge-triggered line, an edge during the masked window could be lost, so you'd have to re-check the status after unmasking.

Your plan to mask the line in the ISR was right, and it's the core of storm prevention. Two refinements make it precise:

1. **Mask where?** You can't clear the cause in the device without reading the FIFO (reading *is* the acknowledgement), and reading blocks. So the mask must be at the **interrupt controller** (or the GPIO controller the line is wired to), not in the device.
2. **Unmask when?** Only after the FIFO is drained, which happens in the passive-level code (§3), not at the end of the ISR.

Both Linux and Windows have a built-in version of exactly this pattern, so you rarely write the mask/unmask yourself (§4, §5).

---

## 3. Where the blocking read can run

Recall the IRQL ladder (lecture 005):

```
DIRQL           ISR                     can't block, can't page-fault, must be microseconds
DISPATCH_LEVEL  DPC, spin-lock holders  can't block, can't page-fault (the scheduler runs here)
APC_LEVEL
PASSIVE_LEVEL   threads, work items,    CAN block, CAN page-fault
                passive-level ISRs
```

**What "blocking" means mechanically.** `ReadByte()` starts a transfer on the bus (for example an SPI or I²C transaction through the bus controller's driver), then waits for it to complete. Waiting means: mark this thread as not runnable, and ask the scheduler to run something else until the completion signals. That only works for code running **in a thread at PASSIVE_LEVEL (or APC_LEVEL)**:

- At **DISPATCH_LEVEL** the scheduler can't switch this CPU to another thread, because the scheduler itself runs at DISPATCH_LEVEL and is masked. A wait with a non-zero timeout there is illegal; it can deadlock the CPU (the completion it's waiting for may need this same CPU) and Driver Verifier flags it.
- A **DPC isn't even a thread.** It borrows whatever thread was running on that CPU when it was queued. There's nothing of its own to put to sleep.

So the design "ISR queues a DPC, and the DPC loops on the blocking `ReadByte()`" fails. The correct chain has one more hop, or skips the DPC entirely:

| Option | Chain | When to use it |
|---|---|---|
| **A. DIRQL ISR + DPC + work item** | ISR masks the line, queues DPC → DPC queues a work item → work item (PASSIVE) drains with blocking reads, unmasks | Device registers are memory-mapped and the ISR can silence the device directly, but some follow-up work needs to block |
| **B. Passive-level ISR** (KMDF `PassiveHandling = TRUE`) | System masks the line and runs your ISR **in a kernel thread at PASSIVE_LEVEL** → ISR drains with blocking reads → system unmasks when the ISR returns | Device sits behind a slow bus (I²C, SPI, UART), so even silencing it needs an I/O request. **This is the designed-for case.** |
| **C. Dedicated thread** | ISR masks + signals an event → your thread wakes, drains, unmasks | Rarely needed on Windows (B covers it); the general fallback |

Option B is what Windows documents for exactly this situation: for a level-triggered line, "the kernel trap handler masks the pending interrupt at the GPIO pin, and then schedules the ISR to run in a passive-level kernel thread... After the ISR returns, the kernel thread unmasks the interrupt." And: "A passive-level ISR can send an I/O request synchronously and, if necessary, block until the request is completed." (Microsoft Learn, *Passive-Level ISRs*.)

**One refinement:** while the passive-level ISR runs, the line stays masked, and other passive-level ISRs may wait. So the ISR should drain the device into the ring buffer and return. Completing app requests (copying to their buffers) goes in a separate work item (KMDF's `EvtInterruptWorkItem`), also because Microsoft says to release the passive-level interrupt lock before completing I/O requests.

**About the I/O manager.** The I/O manager doesn't fetch data from a buffer and hand it to the app by itself. The app's `ReadFile` becomes an IRP (a read request) that the I/O manager delivers to the driver. **The driver** decides when to complete it and with what bytes. On completion, for buffered I/O, the I/O manager copies the bytes from the system buffer to the app's buffer and wakes the app's thread. So the arrow from the driver to the app is "driver completes the app's pending read", not "driver gives data to the I/O manager".

---

## 4. Linux version: threaded IRQ, kfifo, wait queue

Linux has the same split, with different names:

| Concept | Windows | Linux |
|---|---|---|
| Tiny first-level handler | ISR at DIRQL | hard IRQ handler (`handler`) |
| Deferred, can't sleep | DPC | softirq / tasklet |
| Deferred, can sleep | work item, passive-level ISR | **threaded IRQ handler** (`thread_fn`), workqueue |
| Keep line masked until the thread finishes | system does it for passive-level ISRs | **`IRQF_ONESHOT`** |
| Driver buffer | your ring buffer | `kfifo` |
| Hold reads until data exists | manual queue of WDFREQUESTs | wait queue + `wait_event_interruptible` |

`request_threaded_irq(irq, handler, thread_fn, flags, name, dev)`: if `handler` is `NULL`, the kernel installs a default primary handler that just wakes the thread. `IRQF_ONESHOT` is documented as "run `thread_fn` with interrupt line masked". That's mask → drain → unmask, done by the kernel.

**Sketch** (structure and real API names; not compiled here):

```c
struct mydev {
    struct miscdevice misc;              /* creates /dev/mydev */
    DECLARE_KFIFO(fifo, u8, 4096);       /* driver ring buffer, 4 KB */
    wait_queue_head_t readq;             /* readers sleep here */
    unsigned long overflows;
};

/* Runs in a kernel thread: may sleep, so blocking bus reads are fine.
   The line stays masked until this returns (IRQF_ONESHOT). */
static irqreturn_t mydev_irq_thread(int irq, void *dev_id)
{
    struct mydev *d = dev_id;
    u8 b;

    while (mydev_fifo_not_empty(d)) {        /* e.g. read the line's level, or a count register */
        if (mydev_read_byte(d, &b))          /* the blocking ReadByte(): an SPI/I2C transfer */
            break;
        if (!kfifo_put(&d->fifo, b))         /* ring buffer full: count it, don't hide it */
            d->overflows++;
    }
    wake_up_interruptible(&d->readq);        /* wake any reader sleeping in read() / poll() */
    return IRQ_HANDLED;                      /* kernel unmasks the line now */
}

/* probe(): */
INIT_KFIFO(d->fifo);
init_waitqueue_head(&d->readq);
ret = devm_request_threaded_irq(dev, irq, NULL, mydev_irq_thread,
                                IRQF_ONESHOT | IRQF_TRIGGER_LOW, "mydev", d);

/* read(): the app's blocking read sleeps here until data exists */
static ssize_t mydev_read(struct file *f, char __user *buf, size_t count, loff_t *ppos)
{
    struct mydev *d = container_of(f->private_data, struct mydev, misc);
    unsigned int copied;
    int ret;

    if (kfifo_is_empty(&d->fifo)) {
        if (f->f_flags & O_NONBLOCK)
            return -EAGAIN;
        ret = wait_event_interruptible(d->readq, !kfifo_is_empty(&d->fifo));
        if (ret)
            return ret;                      /* interrupted by a signal */
    }
    ret = kfifo_to_user(&d->fifo, buf, count, &copied);
    return ret ? ret : copied;               /* return whatever is available, up to count */
}

/* poll(): lets the app wait on this device and other things at once (select/poll/epoll) */
static __poll_t mydev_poll(struct file *f, poll_table *wait)
{
    struct mydev *d = container_of(f->private_data, struct mydev, misc);
    poll_wait(f, &d->readq, wait);
    return kfifo_is_empty(&d->fifo) ? 0 : (EPOLLIN | EPOLLRDNORM);
}
```

Notes:
- `kfifo` with exactly one writer (the IRQ thread) and one reader (`read`) needs no extra lock. With more than one reader you'd add a mutex around `kfifo_to_user`.
- `read` returns **what's available** (up to `count`), not exactly `count`. That's why the app needs a parser that handles partial data (`leetcode/019`).
- `IRQF_TRIGGER_LOW` says the line is active-low and level-triggered, matching the device. On a Device Tree system this usually comes from the DT `interrupts` property instead.

---

## 5. Windows version: passive-level interrupt, ring buffer, manual queue

Same design in KMDF. Four pieces in `EvtDriverDeviceAdd`:

1. **Interrupt object** with `PassiveHandling = TRUE`, an `EvtInterruptIsr` that drains, and an `EvtInterruptWorkItem` that completes requests.
2. **Ring buffer** in the device context, protected by a `WDFSPINLOCK` (the ISR, the work item and `EvtIoRead` all touch it).
3. **Default queue** (parallel dispatch) with `EvtIoRead`.
4. **Manual queue** `PendingReads`: read requests that arrived when the buffer was empty wait here.

**Sketch** (structure and real KMDF names; not compiled here):

```c
typedef struct _DEVICE_CONTEXT {
    WDFINTERRUPT Interrupt;
    WDFQUEUE     PendingReads;      /* manual queue: reads waiting for data */
    WDFSPINLOCK  RingLock;
    RING_BUFFER  Ring;              /* e.g. 4 KB; your own head/tail/count struct */
    ULONG        Overflows;
} DEVICE_CONTEXT, *PDEVICE_CONTEXT;

/* --- EvtDriverDeviceAdd (excerpt) --- */
WDF_INTERRUPT_CONFIG ic;
WDF_INTERRUPT_CONFIG_INIT(&ic, EvtIsr, NULL);       /* no DPC */
ic.PassiveHandling      = TRUE;                     /* ISR runs at PASSIVE_LEVEL in a kernel thread */
ic.EvtInterruptWorkItem = EvtIsrWorkItem;           /* also PASSIVE_LEVEL, runs after the ISR */
WdfInterruptCreate(device, &ic, WDF_NO_OBJECT_ATTRIBUTES, &ctx->Interrupt);

WDF_IO_QUEUE_CONFIG qc;
WDF_IO_QUEUE_CONFIG_INIT_DEFAULT_QUEUE(&qc, WdfIoQueueDispatchParallel);
qc.EvtIoRead = EvtIoRead;
WdfIoQueueCreate(device, &qc, WDF_NO_OBJECT_ATTRIBUTES, WDF_NO_HANDLE);

WDF_IO_QUEUE_CONFIG_INIT(&qc, WdfIoQueueDispatchManual);
WdfIoQueueCreate(device, &qc, WDF_NO_OBJECT_ATTRIBUTES, &ctx->PendingReads);

/* --- ISR: PASSIVE_LEVEL, line masked by the system until we return --- */
BOOLEAN EvtIsr(WDFINTERRUPT Interrupt, ULONG MessageID)
{
    PDEVICE_CONTEXT ctx = GetDeviceContext(WdfInterruptGetDevice(Interrupt));
    UCHAR b;
    UNREFERENCED_PARAMETER(MessageID);

    while (DeviceFifoNotEmpty(ctx)) {                  /* status read over the bus */
        if (!NT_SUCCESS(ReadByteBlocking(ctx, &b)))    /* synchronous I/O request to the SPB target: blocks */
            break;
        WdfSpinLockAcquire(ctx->RingLock);
        if (!RingPut(&ctx->Ring, b)) ctx->Overflows++;
        WdfSpinLockRelease(ctx->RingLock);
    }
    WdfInterruptQueueWorkItemForIsr(Interrupt);        /* complete requests outside the interrupt lock */
    return TRUE;                                       /* "it was ours"; system unmasks the line */
}

/* --- Work item: hand buffered bytes to waiting reads --- */
VOID EvtIsrWorkItem(WDFINTERRUPT Interrupt, WDFOBJECT Device)
{
    PDEVICE_CONTEXT ctx = GetDeviceContext((WDFDEVICE)Device);
    WDFREQUEST req;
    UNREFERENCED_PARAMETER(Interrupt);

    while (!RingIsEmpty(&ctx->Ring) &&
           NT_SUCCESS(WdfIoQueueRetrieveNextRequest(ctx->PendingReads, &req))) {
        CompleteReadFromRing(ctx, req);
    }
}

/* --- App's ReadFile arrives --- */
VOID EvtIoRead(WDFQUEUE Queue, WDFREQUEST Request, size_t Length)
{
    PDEVICE_CONTEXT ctx = GetDeviceContext(WdfIoQueueGetDevice(Queue));
    UNREFERENCED_PARAMETER(Length);

    if (!RingIsEmpty(&ctx->Ring)) {
        CompleteReadFromRing(ctx, Request);            /* data already here: complete now */
    } else {
        WdfRequestForwardToIoQueue(Request, ctx->PendingReads);  /* park it until data arrives */
    }
}

/* Copy up to the caller's buffer size out of the ring and complete. */
VOID CompleteReadFromRing(PDEVICE_CONTEXT ctx, WDFREQUEST req)
{
    PVOID buf; size_t len; size_t n = 0;
    NTSTATUS st = WdfRequestRetrieveOutputBuffer(req, 1, &buf, &len);
    if (NT_SUCCESS(st)) {
        WdfSpinLockAcquire(ctx->RingLock);
        n = RingRead(&ctx->Ring, buf, len);            /* returns bytes copied, 0..len */
        WdfSpinLockRelease(ctx->RingLock);
    }
    WdfRequestCompleteWithInformation(req, st, n);     /* I/O manager copies to the app, wakes it */
}
```

**Two details worth knowing:**
- **The race between `EvtIoRead` and the work item.** `EvtIoRead` sees an empty ring and is about to park the request; meanwhile the ISR adds bytes and the work item finds no pending request. The request is now parked with data waiting. Fix: after forwarding to `PendingReads`, check the ring once more and, if non-empty, run the same retrieve-and-complete loop. (The pattern: re-check the condition after registering as a waiter. Linux's `wait_event` does this internally.)
- **Cancellation.** A parked read stays pending until data arrives. If the app closes the handle or calls `CancelIoEx`, the framework cancels requests sitting in a queue for you. That's one reason to park requests in a WDF queue instead of your own list.

**The DIRQL alternative (option A), for comparison.** If the device were memory-mapped (PCIe), the ISR would read a status register and silence the device in nanoseconds at DIRQL, queue a DPC, and the DPC would copy from device memory into the ring (no blocking needed) and complete requests. MSI interrupts (PCIe) must use DIRQL handling. The passive-level path exists precisely for devices that can only be reached through slow, blocking bus transfers.

---

## 6. Sizing: bursts, latency, and the 64-entry FIFO

"The host is faster than the device" is about **throughput**. Overflow is about **latency**: how many bytes arrive before the host starts reading.

**Model** (`code/014_fifo_sizing.py`): the device writes one byte every `t_in` µs for a burst of `B` bytes. The line asserts with the first byte; the host starts reading `latency` µs later (interrupt latency + time until the passive-level thread runs + the first bus transfer), then removes a byte every `t_out` µs.

**Rule of thumb when the host is faster (`t_out < t_in`):** the backlog peaks just before the first read:

```
peak ≈ latency / t_in + 1      (bytes that land before the first read)
need:  peak ≤ 64   →   latency ≤ 63 × t_in
```

At 10 µs per byte (100 KB/s), the host must start reading within about 630 µs, every time, including when the system is busy.

**When the host is slower (`t_out > t_in`):** the backlog keeps growing for the whole burst, so the burst length matters too.

Measured with the simulation:

```
 burst  t_in  t_out  latency  peak  formula  fits in 64?
   200    10      2      100    11       11  yes
   200    10      2      600    61       61  yes
   200    10      2     1000   101      101  NO - overflow
   200    10     12      100    42       43  yes
    40    10     12     2000    40       40  yes
```

(The "formula" column is the closed-form estimate; it matches the simulation within one byte.)

Row 3 is the important one: the host reads **5× faster** than the device, and it still overflows, because it started 1 ms late. Row 5 is the opposite: a long delay is fine if the whole burst fits in the FIFO.

**What this means for the design:**
- **Ask for the numbers:** byte rate during a burst, maximum burst length, and the worst-case time between bursts. Without them, nobody can say whether 64 entries is enough.
- **The passive-level thread's start latency is not guaranteed.** It depends on what else runs at higher priority. Measure it (ETW, lecture 004/015) under load, not on an idle system.
- **If the numbers don't fit,** options are: a device with a bigger FIFO or a "half full" interrupt (a watermark: interrupt earlier), DMA (the device writes straight into host memory), a faster bus, or reading in bursts (`ReadBuffer` of N bytes per transfer instead of one byte per transfer, which removes per-transfer overhead).

---

## 7. Overflow policy

Even with good sizing, decide what happens if the FIFO or the driver's ring fills:

| Choice | Effect | Good for |
|---|---|---|
| **Drop newest** (device refuses new bytes when full) | Old data intact, recent data lost | Logs, command streams where order of what you have matters |
| **Drop oldest** (overwrite) | Always have the most recent data | Sensor readings, live displays |
| **Backpressure** (device waits / signals "busy") | Nothing lost, producer slows down | When the producer can wait (flow control: RTS/CTS on UARTs) |

**Whatever you choose, make loss visible:** a sticky overflow bit in the device status, an overflow counter in the driver (the `overflows` / `Overflows` fields above), or a sequence number in each packet so the app can detect gaps. A design that loses data silently can't be debugged in the field.

Two different buffers can overflow, and they need separate answers: the **device FIFO** (64 entries, overflows when the host starts late) and the **driver ring** (overflows when the app doesn't read). The driver ring is usually sized for "the app was busy for a few hundred milliseconds".

---

## 8. The app side: reader thread and UI thread

A GUI framework (WinUI, WPF, Win32) has **one UI thread** that processes input and draws. If it calls a blocking `ReadFile`, the window freezes until data arrives ("Not Responding").

The standard structure:

```
reader thread:                                 UI thread:
  loop:                                          handles input, draws
    n = ReadFile(h, buf, 4096)   (blocks here)
    parser.feed(buf[:n])         (leetcode/019)
    packets = parser.get_all_packets()
    if packets: post them to the UI thread  ──►  update the view (batched)
```

- **Reader thread or async I/O.** Either a dedicated thread with blocking reads (simple), or overlapped I/O / `async` reads that don't hold a thread while waiting. In C#, `FileStream` opened with `useAsync: true` and `await stream.ReadAsync(...)`; in WinUI, post results with `DispatcherQueue.TryEnqueue(...)`.
- **Batch updates.** At 100 KB/s, posting one UI update per byte is 100,000 posts a second. Post per packet group or on a timer (e.g. at most every 16 ms, one display frame).
- **Shutdown.** To stop a reader blocked in `ReadFile`, call `CancelIoEx` on the handle (or close it); the driver's pending request is cancelled and `ReadFile` returns an error the loop treats as "stop".

---

## 9. How to present this design

A good order, which also works as a checklist for any "hardware signals the OS" design:

1. **Restate the hardware contract:** level-triggered, active-low, asserted while non-empty; FIFO depth 64; reads block.
2. **Ask for the numbers:** burst rate, burst length, gap between bursts, acceptable loss.
3. **Draw the path** (§1) and name the four questions at each arrow.
4. **Interrupt handling:** mask in the first handler, drain at PASSIVE_LEVEL, unmask when empty; explain why level-triggering can't miss data.
5. **Where the blocking read runs:** not in the ISR, not in a DPC (DISPATCH_LEVEL can't wait); in a passive-level ISR / work item (Windows) or a threaded IRQ with `IRQF_ONESHOT` (Linux).
6. **Buffering and delivery:** driver ring buffer; reads parked until data exists (manual queue / wait queue); complete with what's available.
7. **Sizing and overflow:** the latency formula, and the policy plus visibility.
8. **App side:** reader thread, parser, batched UI updates.
9. **How you'd verify it:** a test that bursts at max rate while the system is loaded; ETW traces of ISR-to-read latency; overflow counters at zero.

---

## Common mistakes

1. **A blocking read in a DPC** (or in a DIRQL ISR). DISPATCH_LEVEL and above can't wait. Move it to PASSIVE_LEVEL.
2. **Unmasking at the end of the ISR** before the FIFO is drained: the line is still low, so the interrupt fires again immediately (storm).
3. **Trying to "acknowledge" the device in the first-level handler** when acknowledging requires a blocking bus read. Mask at the controller instead.
4. **Treating the I/O manager as the thing that moves data to the app.** The driver completes the app's read request; the I/O manager copies the result.
5. **Sizing by throughput only.** Overflow depends on worst-case start latency and burst length.
6. **No overflow policy, or silent loss.**
7. **Blocking reads on the UI thread.**
8. **Expecting `read`/`ReadFile` to return whole packets.** It returns whatever bytes are available. Parse.

---

## Self-check questions

1. The line is level-triggered and active-low. The ISR returns without masking it and without reading the FIFO. What happens, and why?
<details><summary>Answer</summary>An interrupt storm. When the ISR returns, the controller sees the line still low (the FIFO still has data) and immediately raises the interrupt again, over and over. The CPU spends all its time entering and leaving the ISR. Mask the line until the FIFO is drained.</details>

2. A byte arrives after your last read but before you unmask. Is it lost? Would it be with an edge-triggered line?
<details><summary>Answer</summary>Not lost with level-triggering: the line goes low again, and when you unmask the controller sees the low level and fires again. With edge-triggering, the falling edge happened while masked and may not be latched, so you must re-check the device status after unmasking.</details>

3. Why can't a DPC call a blocking `ReadByte()`? Give the mechanical reason, not just the rule.
<details><summary>Answer</summary>Blocking means putting the current thread to sleep and letting the scheduler run another thread until the transfer completes. A DPC runs at DISPATCH_LEVEL, the level the scheduler itself runs at, so this CPU can't switch threads; and a DPC isn't its own thread anyway, it borrows whatever thread was running. Waiting there would deadlock or bugcheck. Blocking needs PASSIVE_LEVEL (or APC_LEVEL) in a real thread.</details>

4. Name two Windows places the blocking read can run, and say when each fits.
<details><summary>Answer</summary>A passive-level ISR (KMDF `PassiveHandling = TRUE`): the system masks the line, runs the ISR in a kernel thread at PASSIVE_LEVEL, and unmasks after it returns; made for devices behind slow buses that need I/O requests even to silence the interrupt. Or a work item queued from a DPC (DIRQL ISR → DPC → work item): for memory-mapped devices where the ISR can silence the device directly but later work must block. (A dedicated thread is a third option.)</details>

5. What does `IRQF_ONESHOT` do, and which Windows feature plays the same role?
<details><summary>Answer</summary>It keeps the interrupt line masked until the threaded handler (`thread_fn`) returns, so a level-triggered line doesn't refire while the thread drains the device. Windows passive-level ISRs get the same behavior: the line is masked at the GPIO pin until the ISR returns.</details>

6. The app calls `ReadFile` when the driver's ring buffer is empty. Trace what happens until it returns.
<details><summary>Answer</summary>The I/O manager builds a read IRP; KMDF delivers it to `EvtIoRead`; the ring is empty, so the driver forwards it to the manual `PendingReads` queue (and re-checks the ring to avoid the race). The app's thread waits. Later the line asserts; the passive-level ISR drains bytes into the ring and queues the work item; the work item retrieves the pending request, copies available bytes into its buffer, and completes it with the byte count. The I/O manager copies the data to the app's buffer and wakes the thread; `ReadFile` returns with that count.</details>

7. The host drains 5× faster than the device produces. Can the 64-entry FIFO still overflow? Show with numbers.
<details><summary>Answer</summary>Yes. Overflow depends on how many bytes arrive before the first read. At 10 µs per byte, a 1 ms start latency lets about 101 bytes arrive first, more than 64, even though draining is 5× faster afterwards. The limit is latency ≤ about 63 × 10 µs = 630 µs.</details>

8. Give an overflow policy for a live sensor display, and say how loss is made visible.
<details><summary>Answer</summary>Drop oldest (keep the most recent readings), because a display wants current values. Make loss visible with a sticky overflow bit or counter in the device/driver, or sequence numbers in packets so the app can detect and report gaps.</details>

9. Why must the UI thread never call the blocking read, and what replaces it?
<details><summary>Answer</summary>The UI thread processes input and drawing; if it blocks in `ReadFile`, the window freezes until data arrives. A reader thread (or async I/O) does the reads and parsing, and posts batched updates to the UI thread (e.g. `DispatcherQueue.TryEnqueue` in WinUI).</details>

---

## Sources

- Microsoft Learn, [Passive-Level ISRs](https://learn.microsoft.com/en-us/windows-hardware/drivers/gpio/passive-level-isrs) (masking at the GPIO pin until the ISR returns; blocking I/O requests from a passive-level ISR). Accessed 2026-10-31.
- Microsoft Learn, [Supporting Passive-Level Interrupts](https://learn.microsoft.com/en-us/windows-hardware/drivers/wdf/supporting-passive-level-interrupts) (`PassiveHandling`, low-speed buses such as I²C/SPI/UART, MSI must use DIRQL, release the lock before completing requests). Accessed 2026-10-31.
- Microsoft Learn, [WdfInterruptQueueWorkItemForIsr](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdfinterrupt/nf-wdfinterrupt-wdfinterruptqueueworkitemforisr) and [Dispatching methods for I/O requests](https://learn.microsoft.com/en-us/windows-hardware/drivers/wdf/dispatching-methods-for-i-o-requests) (manual queues). Accessed 2026-10-31.
- Linux kernel docs, [Linux generic IRQ handling](https://docs.kernel.org/core-api/genericirq.html) (`request_threaded_irq`, `IRQF_ONESHOT` "run thread_fn with interrupt line masked", level-type flow handling). Accessed 2026-10-31.
- Linux kernel source, `include/linux/kfifo.h` (single reader / single writer needs no extra locking) and `include/linux/wait.h` (`wait_event_interruptible`). Accessed 2026-10-31.
- Lectures 002 (0x133 watchdog), 005 (IRQL ladder), 009 (IRPs and request completion) in this folder.
- Code: `code/014_fifo_sizing.py`, run 2026-10-31.
