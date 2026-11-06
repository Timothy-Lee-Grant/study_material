<!-- id: d01_device_fifo_to_gui | family: D | level: core | minutes: 45 | bridge: e04_ring_buffer -->
# D01 · Device FIFO to a GUI

## The prompt

An external device produces data bytes in bursts and stores them in a 64-entry hardware FIFO. While the FIFO is non-empty, the device holds an active-low interrupt line asserted (pulled low) to the computer. Reading one byte from the device uses a `ReadByte()` call over a serial bus that **blocks** until the transfer completes, which takes about 50 µs.

Design the whole path that gets these bytes from the device into a desktop application, which displays them live in its GUI. The design must not lose data during bursts, must not cause an interrupt storm, and the GUI must never freeze. You choose the operating system (Windows or Linux) and you write the driver.

## What this case trains

- **Placing blocking work**: which context runs each stage, and which ones may wait.
- **Level-triggered interrupts**: masking, unmasking, and storms.
- **Sizing** a buffer from named quantities (fill rate, worst drain delay, capacity).
- **Overflow policy** and **loss detection**.
- The **UI-thread rule** on the app side.

Reference material: `../../../windows_internals/014-device_to_app_data_path.md` works this case fully. **Don't open it until after your attempt and self-review.** If you've read it before, that's fine: this is a redo from a blank page.

**Bridge coding piece:** `e04_ring_buffer`.

## Interviewer's notes (open only after your self-review, or give to the interviewer)

<details><summary>Answers to clarifying questions</summary>

- **Burst shape:** bursts of up to 500 bytes arriving at 10,000 bytes/second; quiet for several seconds between bursts.
- **Bus:** a slow serial bus (I2C-like); the controller driver for that bus already exists and provides the blocking `ReadByte()`; you write the driver for this device.
- **GUI:** a scrolling view of the latest values, updated live; humans can't see more than ~60 updates/second.
- **Loss:** must be detected and reported to the user if it ever happens.
- **App not running:** the driver should keep collecting for a while (you decide how long) and then apply your overflow policy.
- **Can the device tell you how many bytes are waiting?** No; only the interrupt line says "non-empty".

</details>

<details><summary>Pushback questions the interviewer will ask</summary>

1. Where exactly does `ReadByte()` run, and why can't it run in the interrupt handler or a DPC / softirq?
2. The line is level-triggered. What happens the instant your interrupt handler returns if you did nothing to the line? What do you do about it, and when do you undo it?
3. With bursts at 10,000 bytes/s, how long until the 64-entry FIFO overflows if nobody drains it? So what's your worst-case allowed delay before draining starts? Derive it.
4. Can one reader draining at one byte per 50 µs keep up with the burst rate? Show the numbers.
5. How does the app get the bytes: a blocking read on a handle, async I/O, an event? Which thread in the app does it, and how do the bytes reach the UI thread?
6. The app is slow or stopped. Where do bytes pile up, what's your overflow policy, and how does the user find out data was dropped?
7. How would you test this design without the real device?

</details>

## After your attempt

- Compare with: `../../../windows_internals/014-device_to_app_data_path.md` (full design, Linux and Windows versions, sizing in §6).
- Ask for a review to get scores and a reference comparison in `review.md`.
