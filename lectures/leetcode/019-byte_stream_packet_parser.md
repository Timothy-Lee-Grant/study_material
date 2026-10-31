# Lecture 019: Parsing Packets Out of a Byte Stream (a State Machine That Survives Noise and Split Reads)

> **For:** Timothy · **Date:** 2026-10-31
> **Prerequisites:** lecture 018 (the six-step simulation method: state table, one step, trace), `general_skills/001-thinking_in_states.md` (naming states by what you're waiting for). Helpful: lecture 012 (design problems: a class with methods that keeps state between calls).
> **Why this lecture:** "serial packet parser" problems look like LeetCode but behave like design problems. The problem statement describes a wire format and a class, not an input array and an answer. The hard part is understanding what goes in, what comes out, and what has to be remembered between calls, before writing any code. This lecture teaches that first step explicitly, then builds the parser two ways.
> **Format notes:** the full problem statement is given (paraphrased, in the usual form of this problem). Every name is defined before it's used. No firmware analogies; the bytes are just bytes.
> **Verification:** both parsers in `code/019_packet_parser.py` pass six tests, including 200 random packets split at random points and fed in random-sized chunks. Every trace below was produced by running the code.

---

## Core ideas (the answer key)

1. **A byte stream has no boundaries.** The sender writes packets one after another, but the receiver gets bytes in chunks of any size. One chunk can hold half a packet, three packets, or noise. **Framing** means finding where each packet starts and ends.
2. **The format tells you how to frame:** a **sync byte** (`0xAA`) marks a possible start, a **length byte** says how many data bytes follow, and a **checksum** lets you reject a false start or corrupted bytes.
3. **Bytes before a sync byte are noise and are skipped.** They exist because the receiver can start listening in the middle of a transmission, or the line carries idle bytes like `0x00`.
4. **The parser is a class because it must remember where it is between calls.** `feed(chunk)` may end in the middle of a packet; the next `feed` continues from there. "What do I remember between calls?" is the first design question.
5. **Name the states by what the next byte means:** `WAIT_HEADER`, `READ_LENGTH`, `READ_DATA`, `READ_CHECKSUM`. One step = (state, byte) → next state. Every state must handle every possible byte.
6. **Inside a packet, `0xAA` is just data.** Only in `WAIT_HEADER` does `0xAA` mean "start". The length byte is what tells you where the data ends, not the next header.
7. **A bad checksum means "this wasn't a packet (or it got damaged)."** The simple parser drops it and looks for the next header. A **resyncing** parser rescans from the byte after the false header, so a real packet hidden inside the false one isn't lost.
8. **Edge cases come from the format, not the code:** `LEN = 0`, `0xAA` inside data, a header as the very last byte of a chunk, a chunk of one byte, noise between packets, a corrupted checksum.
9. **Before coding any design-style problem, write one example call and its exact output.** If you can't write `p.feed(bytes([...])); p.get_all_packets() == [...]`, you don't understand the interface yet, and that's the question to ask.

---

## Table of Contents

- [0. The problem](#0-the-problem)
- [1. First, pin down the interface](#1-first-pin-down-the-interface)
- [2. Why a byte stream needs framing](#2-why-a-byte-stream-needs-framing)
- [3. The state table](#3-the-state-table)
- [4. Implementation 1: the byte-at-a-time state machine](#4-implementation-1-the-byte-at-a-time-state-machine)
- [5. Traces](#5-traces)
- [6. Implementation 2: buffer and resync](#6-implementation-2-buffer-and-resync)
- [7. Tests that cover the format](#7-tests-that-cover-the-format)
- [8. Variations you will see](#8-variations-you-will-see)
- [9. Where this runs in a real system](#9-where-this-runs-in-a-real-system)
- [Common mistakes](#common-mistakes)
- [Self-check questions](#self-check-questions)
- [Sources](#sources)

---

## 0. The problem

**Serial packet parser (paraphrased, in the usual form of this problem).**

A device sends packets over a serial link. Each packet has this layout:

| Field | Size | Meaning |
|---|---|---|
| `HEADER` | 1 byte | always `0xAA` |
| `LEN` | 1 byte | number of data bytes, `0` to `255` |
| `DATA` | `LEN` bytes | the payload; any values, including `0xAA` |
| `CHK` | 1 byte | `(LEN + DATA[0] + ... + DATA[LEN-1]) % 256` |

The receiver gets the stream as a sequence of byte chunks. Write a class `PacketParser` with:

- `feed(chunk)`: takes the next chunk of received bytes (a `bytes` object or list of ints, any length, possibly empty).
- `get_all_packets()`: returns a list of the payloads (`DATA` only, as `bytes`) of every **valid** packet completed since the last call, in arrival order, and clears that list.

Rules:
- Bytes that aren't part of a packet (for example leading `0x00` bytes) are ignored.
- A packet may be split across any number of `feed` calls.
- One `feed` call may contain several packets.
- A packet whose checksum doesn't match is discarded.

**Example.**

```python
p = PacketParser()
p.feed(bytes([0x00, 0x00, 0xAA, 0x02, 0x10]))   # noise, then the start of a packet
p.get_all_packets()                              # -> []   (the packet isn't complete yet)
p.feed(bytes([0x20, 0x32, 0xAA, 0x00, 0x00]))   # rest of packet 1, then packet 2 (LEN = 0)
p.get_all_packets()                              # -> [b'\x10\x20', b'']
```

Packet 1: `LEN = 0x02`, `DATA = 0x10 0x20`, `CHK = (2 + 0x10 + 0x20) % 256 = 0x32`. Packet 2: `LEN = 0`, no data, `CHK = 0`.

**Constraints (typical):** total stream up to about 10⁶ bytes; `feed` called many times with small chunks; memory should not grow with the length of the stream.

Different versions of this problem change the details: the checksum might be XOR instead of a sum, it might include the header, `LEN` might be two bytes, or `get_all_packets` might take the whole byte list at once. §8 covers those. The structure of the solution doesn't change.

---

## 1. First, pin down the interface

A LeetCode problem gives you a function signature and an input. A design-style problem gives you a description, and the first job is turning it into a signature. Do this before anything else, and do it out loud:

1. **What are the inputs, exactly?** Here: chunks of bytes, arriving over time, through `feed`. Not one big list. (If the statement only shows a single list, ask: "Is the whole stream given at once, or does it arrive in pieces?" The answer decides whether you need state between calls.)
2. **What is the output, exactly?** A list of payloads. Payload = `DATA` only, without header, length or checksum. As `bytes`, in order.
3. **What has to be remembered between calls?** Anything that can be cut off by the end of a chunk: whether we're inside a packet, the length, the data so far. That's the class's fields.
4. **What's the smallest example?** Write it as code, with the exact expected output, like the example above. Then write one with a split, and one with noise.

If you get stuck on step 1 or 2, that's the moment to ask a clarifying question. "Can I confirm the signature: `feed` takes a chunk and `get_all_packets` returns the payloads completed so far?" is a strong question. It shows you're designing, and it gets you the information you need.

**Where did the `0x00` at the front come from?** A receiver doesn't get to choose when it starts listening. It may power up in the middle of a packet, or the line may send filler bytes when idle. So the parser can never assume the first byte is a header. It must **hunt** for the sync byte. That's all the leading zeros mean: "the stream doesn't start cleanly; prove your parser copes."

---

## 2. Why a byte stream needs framing

A serial link (UART, USB serial, a TCP socket) delivers an ordered stream of bytes. It does **not** deliver messages. The sender wrote "packet, packet, packet"; the receiver's `read` returns whatever bytes have arrived. For example, the two packets above might arrive as:

```
chunk 1: 00 00 AA 02 10        <- noise + first 3 bytes of packet 1
chunk 2: 20 32 AA 00 00        <- last 2 bytes of packet 1 + all of packet 2
```

So the receiver needs rules to find boundaries. This format uses three:

- **Sync byte (`0xAA`):** a candidate start. It's only a *candidate*, because `0xAA` can also appear as noise or as data.
- **Length:** once you trust a start, `LEN` tells you exactly where the packet ends: `1 + 1 + LEN + 1` bytes from the header.
- **Checksum:** confirms the candidate. If you started on a false `0xAA`, the "checksum" byte is almost certainly wrong, and you'll find out.

With a 1-byte additive checksum, a random false start passes the check about 1 time in 256. That's why real protocols use stronger checks (CRC-16, CRC-32) when it matters. For this problem the sum is enough.

---

## 3. The state table

Lecture 018's method, applied.

**Rules in my own words:** skip bytes until `0xAA`. The next byte is the length. Collect that many data bytes. The next byte is the checksum: if it matches, save the data; either way, start skipping again.

**State (every value that changes, and its valid set):**

| Name | Meaning | Valid set |
|---|---|---|
| `state` | what the **next** byte means | `WAIT_HEADER`, `READ_LENGTH`, `READ_DATA`, `READ_CHECKSUM` |
| `length` | `LEN` of the packet being read | `0..255` (meaningful only after `READ_LENGTH`) |
| `data` | data bytes collected so far | `0..length` bytes |
| `completed` | valid payloads not yet returned | list |

**One step: (state, byte) → next state.** Every row must cover every possible byte value.

| State | Byte | Action | Next state |
|---|---|---|---|
| `WAIT_HEADER` | `0xAA` | none | `READ_LENGTH` |
| `WAIT_HEADER` | anything else | ignore (noise) | `WAIT_HEADER` |
| `READ_LENGTH` | any `b` | `length = b`, `data = []` | `READ_CHECKSUM` if `b == 0`, else `READ_DATA` |
| `READ_DATA` | any `b` | append `b` to `data` | `READ_CHECKSUM` if `len(data) == length`, else `READ_DATA` |
| `READ_CHECKSUM` | `b == (length + sum(data)) % 256` | save `data` | `WAIT_HEADER` |
| `READ_CHECKSUM` | any other `b` | drop the packet | `WAIT_HEADER` |

```
                 not 0xAA
                 ┌─────┐
                 ▼     │
            ┌─────────────┐  0xAA   ┌─────────────┐
   ───────► │ WAIT_HEADER │ ──────► │ READ_LENGTH │
            └─────────────┘         └─────────────┘
               ▲                       │ LEN>0     │ LEN=0
               │                       ▼           │
               │                ┌───────────┐      │
               │                │ READ_DATA │◄──┐  │
               │                └───────────┘   │  │
               │                  │  more data ─┘  │
               │                  │ got LEN bytes  │
               │                  ▼                ▼
               │              ┌───────────────┐
               └──────────────│ READ_CHECKSUM │   (save if it matches, drop if not)
                  any byte    └───────────────┘
```

**Stop condition:** the step never "finishes". It runs once per byte, forever. `feed` just runs it for each byte in the chunk and returns. That's why the state lives in the object: when `feed` returns in the middle of `READ_DATA`, the next `feed` continues in `READ_DATA`.

**Edge cases from the format:** `LEN = 0` (go straight to the checksum), `0xAA` inside data (it's data, because we're in `READ_DATA`), a chunk ending right after the header, chunks of one byte, empty chunks, noise between packets, bad checksum.

---

## 4. Implementation 1: the byte-at-a-time state machine

From `code/019_packet_parser.py`:

```python
HEADER = 0xAA

def checksum(length, data):
    """What CHK must equal: the low 8 bits of LEN + every data byte."""
    return (length + sum(data)) % 256

class StateMachineParser:
    # Each name says what the NEXT byte is expected to be.
    WAIT_HEADER, READ_LENGTH, READ_DATA, READ_CHECKSUM = range(4)

    def __init__(self):
        self.state = self.WAIT_HEADER
        self.length = 0            # LEN of the packet being read (0..255)
        self.data = bytearray()    # data bytes collected so far (0..length of them)
        self.completed = []        # valid payloads not yet handed out
        self.dropped = 0           # packets thrown away for a bad checksum

    def feed(self, chunk):
        for byte in chunk:         # iterating over bytes gives ints 0..255
            self._step(byte)

    def _step(self, byte):
        """One step: (state, byte) -> next state. Every state handles every byte."""
        if self.state == self.WAIT_HEADER:
            if byte == HEADER:
                self.state = self.READ_LENGTH
            # any other byte is noise: stay in WAIT_HEADER

        elif self.state == self.READ_LENGTH:
            self.length = byte
            self.data = bytearray()
            # LEN = 0 means "no data": go straight to the checksum
            self.state = self.READ_CHECKSUM if self.length == 0 else self.READ_DATA

        elif self.state == self.READ_DATA:
            self.data.append(byte)             # 0xAA here is DATA, not a header
            if len(self.data) == self.length:  # collected exactly LEN bytes
                self.state = self.READ_CHECKSUM

        elif self.state == self.READ_CHECKSUM:
            if byte == checksum(self.length, self.data):
                self.completed.append(bytes(self.data))
            else:
                self.dropped += 1
            self.state = self.WAIT_HEADER      # either way, look for the next packet

    def get_all_packets(self):
        out, self.completed = self.completed, []
        return out
```

**Name-vs-lines check** (lecture 018, core idea 4): every field has a line that keeps it true inside the step.

| Name | Lines that change it |
|---|---|
| `state` | every branch sets it |
| `length` | `READ_LENGTH` branch |
| `data` | reset in `READ_LENGTH`, appended in `READ_DATA` |
| `completed` | appended in `READ_CHECKSUM`, emptied in `get_all_packets` |

**Cost:** O(1) work per byte, so O(total bytes) overall. Memory: one packet's data (at most 255 bytes) plus the completed list. It doesn't grow with the stream.

**Why `get_all_packets` swaps instead of copying:** `out, self.completed = self.completed, []` hands the caller the existing list and starts a fresh one. Nothing is copied, and the caller can't accidentally modify the parser's internal list.

---

## 5. Traces

**Trace 1: the example from §0.** One row per byte. The columns are the state *before* the step and the fields *after* it.

| chunk | byte | state before | action | length | data | completed |
|---|---|---|---|---|---|---|
| 1 | `00` | WAIT_HEADER | noise | 0 | | |
| 1 | `00` | WAIT_HEADER | noise | 0 | | |
| 1 | `AA` | WAIT_HEADER | → READ_LENGTH | 0 | | |
| 1 | `02` | READ_LENGTH | length = 2 → READ_DATA | 2 | | |
| 1 | `10` | READ_DATA | append | 2 | `10` | |
| *(feed returns here; state = READ_DATA is remembered)* | | | | | | |
| 2 | `20` | READ_DATA | append, have 2 → READ_CHECKSUM | 2 | `10 20` | |
| 2 | `32` | READ_CHECKSUM | 2+16+32 = 50 = `0x32` ✓ save | 2 | `10 20` | `[1020]` |
| 2 | `AA` | WAIT_HEADER | → READ_LENGTH | 2 | `10 20` | `[1020]` |
| 2 | `00` | READ_LENGTH | length = 0 → READ_CHECKSUM | 0 | | `[1020]` |
| 2 | `00` | READ_CHECKSUM | 0 = 0 ✓ save | 0 | | `[1020, —]` |

The row after the first `feed` returns is the whole reason this is a class: the next call picks up in `READ_DATA` with one byte already collected.

**Trace 2: `0xAA` inside data.** Packet `AA 02 AA 10 BC` (data `AA 10`, checksum `2 + 0xAA + 0x10 = 0xBC`). In `READ_DATA`, the second `AA` is appended like any other byte. If you had written "whenever you see `0xAA`, start a new packet", this packet would break in half. The state decides what a byte means, not the byte's value.

**Trace 3: a false header hides a real packet.** Stream `AA 03 | AA 01 05 06`: some noise that happens to be `AA 03`, followed by a real packet `AA 01 05 06` (data `05`, checksum `1 + 5 = 6`). The state machine reads `LEN = 3`, then takes `AA 01 05` as "data" and `06` as the checksum. `3 + 0xAA + 1 + 5 = 0xB3 ≠ 0x06`, so it drops the packet. But it has also consumed the real packet's bytes. Running both parsers on this stream:

```
StateMachineParser   -> []        dropped=1
ResyncingParser      -> [b'\x05'] dropped=1
```

That's the limitation §6 fixes.

---

## 6. Implementation 2: buffer and resync

The idea: keep the unconsumed bytes in a buffer. When a packet fails its checksum, don't throw away all its bytes. Throw away **only the false header**, and scan again from the next byte.

```python
class ResyncingParser:
    """Keeps unconsumed bytes in a buffer; parses whole packets when enough bytes are present."""

    def __init__(self):
        self.buf = bytearray()
        self.completed = []
        self.dropped = 0

    def feed(self, chunk):
        self.buf.extend(chunk)
        self._parse()

    def _parse(self):
        while True:
            start = self.buf.find(HEADER)          # position of the next candidate header
            if start == -1:
                self.buf.clear()                   # all noise: nothing worth keeping
                return
            del self.buf[:start]                   # drop the noise before it; header now at 0
            if len(self.buf) < 2:
                return                             # need LEN before we know the size
            length = self.buf[1]
            total = 1 + 1 + length + 1             # header + LEN + data + CHK
            if len(self.buf) < total:
                return                             # packet not complete yet: wait for more bytes
            data = self.buf[2:2 + length]
            if self.buf[2 + length] == checksum(length, data):
                self.completed.append(bytes(data))
                del self.buf[:total]               # consume the whole packet
            else:
                self.dropped += 1
                del self.buf[:1]                   # NOT the whole thing: drop only the false header
                                                   # and rescan from the very next byte

    def get_all_packets(self):
        out, self.completed = self.completed, []
        return out
```

**What the loop maintains:** at the top of each iteration, `buf` holds every received byte that hasn't been either returned as part of a valid packet or ruled out as a start. Each iteration either removes at least one byte or returns to wait for more input, so the loop ends.

**The three "wait for more" exits** are the split-read cases: no `LEN` yet, or not all of `DATA + CHK` yet. The bytes stay in `buf` for the next `feed`.

**Trade-offs between the two designs:**

| | State machine | Buffer + resync |
|---|---|---|
| Memory | one packet's data | up to one packet plus the unparsed bytes |
| Work per byte | O(1) | O(1) amortized normally; a bad packet makes its bytes get rescanned |
| Recovers a packet hidden in a false one | no | yes |
| Easy to port to C / firmware | very | needs a ring buffer instead of `del buf[:k]` |

**A note on `del self.buf[:k]`:** deleting from the front of a `bytearray` shifts the remaining bytes, which costs O(len(buf)). Here `buf` never holds more than about one packet (258 bytes), so it doesn't matter. In C you'd use a **ring buffer** (a fixed array with a read index and a write index that wrap around) so consuming bytes is just moving an index.

The state machine can also be made to resync: when the checksum fails, re-feed the bytes after the false header through the step function. That's the same idea, done with a small replay buffer.

---

## 7. Tests that cover the format

Each test comes from an edge case in §3, not from the code:

| # | Test | Catches |
|---|---|---|
| 1 | leading `00 00`, then one packet | not hunting for the header |
| 2 | three packets in one chunk with noise between; `0xAA` in data; `LEN = 0` | stopping after one packet; treating `0xAA` as a header inside data; `LEN = 0` going to `READ_DATA` and waiting forever |
| 3 | one packet fed one byte at a time | forgetting state between calls |
| 4 | `get_all_packets()` twice | not clearing the list |
| 5 | bad checksum, then a good packet | not recovering after a drop |
| 6 | 200 random packets, random noise, random chunk sizes 1 to 8 | anything the hand-written tests missed |

```bash
python3 code/019_packet_parser.py
# StateMachineParser: all 6 tests passed
# ResyncingParser: all 6 tests passed
```

Test 6 is the important habit: **generate packets with a helper (`make_packet`), then split the stream randomly.** If the parser returns exactly the payloads you generated, framing is right for every split position.

---

## 8. Variations you will see

The structure (hunt, length, collect, verify) stays the same. Only details change:

- **Different checksum.** XOR of the bytes (`c ^= b`), sum including the header, or the two's complement (`(-sum) % 256`, so that all bytes including `CHK` sum to 0). Only `checksum()` changes. Ask which bytes it covers.
- **CRC instead of a sum.** CRC-16 or CRC-32 catches far more errors (swapped bytes, bursts) than a sum. Same place in the parser; different function.
- **Two-byte length.** Add a state: `READ_LENGTH_HI`, `READ_LENGTH_LO`. Ask the byte order (big-endian: high byte first).
- **A maximum length.** If `LEN` exceeds the maximum the protocol allows, the header was false: resync immediately instead of waiting for 255 bytes that will never form a packet.
- **A type or ID byte.** Another state between length and data, and the output becomes `(type, payload)` pairs.
- **The whole stream given at once:** `get_all_packets(byte_list)`. Then you don't need state between calls, but the same loop works: create a parser, feed the whole list, return the packets.
- **Byte stuffing instead of a length** (protocols like SLIP, HDLC, COBS). The start/end marker can't appear in the data because data bytes that equal it are replaced by an escape sequence. The parser then splits on the marker and un-escapes. Different technique, same goal: unambiguous boundaries.
- **Timeouts.** In a real device, a packet that stops halfway (cable pulled) should be abandoned after some time without bytes. That's an extra transition: any state → `WAIT_HEADER` when the gap exceeds a limit.

---

## 9. Where this runs in a real system

This parser is the layer just above a byte-oriented driver:

```
device ──bytes──► UART / USB-serial driver ──ReadFile / read() chunks──► PacketParser.feed()
                                                                            │
                                                     app logic ◄── get_all_packets()
```

The driver (lecture `windows_internals/014`) moves bytes from the device into a buffer and completes reads with whatever has arrived. It knows nothing about packets. Turning the chunks back into packets is this parser's job, in the app or in a higher-level driver. The chunk boundaries are set by timing (how many bytes arrived before the read completed), which is exactly why the parser can't assume a chunk lines up with a packet.

---

## Common mistakes

1. **Treating `0xAA` as a header anywhere.** It's a header only in `WAIT_HEADER`. Inside data, the length decides.
2. **Assuming one chunk = one packet.** Test with one-byte chunks and with many packets per chunk.
3. **Local variables instead of fields.** If `state` or `data` is a local in `feed`, a packet split across calls is lost.
4. **`LEN = 0` going to `READ_DATA`.** Then the parser waits for a data byte that never belongs to this packet, and swallows the checksum as data.
5. **Returning the header, length or checksum in the payload.** Output is `DATA` only. Confirm with the example.
6. **Forgetting `% 256`.** The checksum is one byte; the sum of the bytes isn't.
7. **Discarding the whole bad packet when resync is required.** Drop just the false header and rescan.
8. **Starting to code before writing one example call and its output.**

---

## Self-check questions

1. Why does a parser for a byte stream need to be a class (or keep state somewhere), rather than a function that takes one chunk?
<details><summary>Answer</summary>Because a packet can be split across chunks. When a chunk ends in the middle of a packet, the parser must remember which part it's in (the state), the length, and the data collected so far, so the next chunk can continue. A pure function of one chunk has nowhere to keep that.</details>

2. What do the leading `0x00` bytes in the example mean, and what must the parser do with them?
<details><summary>Answer</summary>They're bytes that aren't part of any packet: idle filler, or the tail of a packet the receiver started listening in the middle of. The parser stays in `WAIT_HEADER` and ignores every byte until it sees `0xAA`.</details>

3. The packet `AA 02 AA 10 BC` arrives. Trace the states. Why doesn't the second `AA` start a new packet?
<details><summary>Answer</summary>WAIT_HEADER (AA) → READ_LENGTH (02, length 2) → READ_DATA (AA appended) → READ_DATA (10 appended; 2 bytes, go to READ_CHECKSUM) → READ_CHECKSUM (BC = 2 + 0xAA + 0x10 = 0xBC, valid). The second `AA` arrives in `READ_DATA`, where every byte is data. Only `WAIT_HEADER` treats `0xAA` as a start.</details>

4. What goes wrong if `READ_LENGTH` always goes to `READ_DATA`, even when `LEN = 0`?
<details><summary>Answer</summary>The parser takes the checksum byte as the first data byte. Then `len(data) == 1`, which never equals `length == 0`, so it keeps appending forever and swallows every following packet. `LEN = 0` must go straight to `READ_CHECKSUM`.</details>

5. Stream `AA 03 AA 01 05 06`. What does each parser return, and why?
<details><summary>Answer</summary>The state machine returns `[]`: it takes `LEN = 3`, consumes `AA 01 05` as data and `06` as the checksum, which fails, and those bytes are gone. The resyncing parser also fails the first candidate, but deletes only the first `AA`, rescans, finds `AA 01 05 06` (checksum 1 + 5 = 6 ✓) and returns `[b'\x05']`.</details>

6. With a 1-byte additive checksum, roughly how often does a random false start pass? What would you change if that's too often?
<details><summary>Answer</summary>About 1 in 256, since a random byte matches the expected checksum with probability 1/256. Use a stronger check, such as a CRC-16 (about 1 in 65,536 for random data, and it also catches common burst errors), and reject impossible lengths early.</details>

7. The checksum becomes XOR of `LEN` and the data. What changes in the code?
<details><summary>Answer</summary>Only the `checksum()` function: start at `length` and XOR in each data byte. No `% 256` is needed, since XOR of bytes stays in 0..255. The states and the step are unchanged.</details>

8. Before writing code for a problem described in a paragraph, what should you write down first?
<details><summary>Answer</summary>The interface as one concrete example call with its exact output: what the inputs are, in what pieces they arrive, what's returned, and what must be remembered between calls. If you can't write that, ask the clarifying question that would let you.</details>

---

## Sources

- Lecture 018 (this folder) for the simulation method and name-vs-lines check; `general_skills/001-thinking_in_states.md` for naming states.
- Byte stuffing framing: [RFC 1055, SLIP](https://datatracker.ietf.org/doc/html/rfc1055) (1988) and Cheshire & Baker, [Consistent Overhead Byte Stuffing](https://www.stuartcheshire.org/papers/COBSforToN.pdf) (IEEE/ACM ToN, 1999). Accessed 2026-10-31.
- Error-detection strength of checksums vs CRCs: Koopman & Chakravarty, [Cyclic Redundancy Code (CRC) Polynomial Selection for Embedded Networks](https://users.ece.cmu.edu/~koopman/roses/dsn04/koopman04_crc_poly_embedded.pdf) (DSN 2004). Accessed 2026-10-31.
- Code: `code/019_packet_parser.py`, run 2026-10-31 with Python 3.
