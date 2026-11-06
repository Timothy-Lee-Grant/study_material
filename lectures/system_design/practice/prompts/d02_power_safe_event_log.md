<!-- id: d02_power_safe_event_log | family: D | level: core | minutes: 45 | bridge: e04_ring_buffer -->
# D02 · Power-Safe Event Log on a Device

## The prompt

A battery-powered device must record events to its own flash memory. Each event is a 4-byte timestamp plus a 16-byte payload. The log region is 1 MB of flash. Flash rules: it's **erased in 4 KB sectors** (erasing sets every bit to 1), **written in 256-byte pages** (writing can only change 1s to 0s), and each sector survives about 100,000 erases. Power can disappear at **any instant**, including in the middle of a write or an erase.

The log must: survive sudden power loss without corrupting earlier events; keep the **newest** events when it's full; let a host app on a PC download the whole log over USB, even while the device keeps logging. Events normally arrive once a minute, with bursts of up to 50 per second.

Design the on-flash layout, the write path, what happens at boot, and the download path.

## What this case trains

- A **ring buffer on flash**: erase-ahead, wrap-around.
- **Record format** for crash safety: sequence numbers, checksums, valid markers.
- **Recovery at boot**: finding the head without a separate index.
- **Wear** and the RAM-buffering vs data-loss trade-off.
- Reading a consistent snapshot while a writer runs.

Related reading (after the attempt): `../../../storage/001-crash_consistency.md`.

**Bridge coding piece:** `e04_ring_buffer`.

## Interviewer's notes (open only after your self-review, or give to the interviewer)

<details><summary>Answers to clarifying questions</summary>

- **Clock:** the device has a real-time clock; timestamps can jump if the user changes the time.
- **Losing the last few events on power loss:** acceptable for at most the last 1 second of events; never acceptable to corrupt older ones.
- **Erase time:** a 4 KB sector erase takes ~50 ms, during which that flash bank can't be written.
- **RAM:** 8 KB available for buffering.
- **Expected life:** 10 years.

</details>

<details><summary>Pushback questions the interviewer will ask</summary>

1. Power fails halfway through writing a page. At the next boot, how do you know that record is garbage, and how do you know the ones before it are fine?
2. After a reboot, how do you find where the newest event is without a separate index (which would itself need to be power-safe)?
3. When do you erase the next sector, and what happens if a burst arrives during the 50 ms erase?
4. How long until the flash wears out at the normal rate? At a constant 50 events/second? Show the derivation.
5. Buffering in RAM saves wear but risks loss on power failure. How big a buffer does the "at most 1 second" rule allow?
6. The host downloads the log while the device writes and wraps around. How does the host get a consistent copy?
7. The user sets the clock back an hour. Does anything in your design depend on timestamps increasing?

</details>

## After your attempt

- Compare with: `../../../storage/001-crash_consistency.md` (torn writes, checksums, ordering); ask for a review to get a reference design.
