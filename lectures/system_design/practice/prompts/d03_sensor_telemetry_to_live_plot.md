<!-- id: d03_sensor_telemetry_to_live_plot | family: D | level: core | minutes: 45 | bridge: leetcode/019 packet parser -->
# D03 · Sensor Telemetry to a Live Plot

## The prompt

Eight sensors sit on an I2C bus attached to a microcontroller. The microcontroller is connected to a PC over USB as a serial port. Six sensors must be sampled at 100 Hz and two at 1 kHz. Each sample is 2 bytes. On the PC, an application shows all eight channels as live scrolling plots and also records every sample to a file for later analysis.

Design the full path from sensor to plot and file. Every sample must carry a timestamp accurate to 1 ms; no sample may be lost without the user being told; and the plot must stay smooth even though the screen can't show 1,000 updates a second.

## What this case trains

- **Who timestamps** a sample, and where time is lost.
- **Bandwidth estimation** across a bus and a link, with named quantities.
- **Framing** a byte stream (see `../../../leetcode/019-byte_stream_packet_parser.md`).
- **Two consumers at different speeds** (recording must be complete; display may decimate).
- Loss detection with **sequence numbers**.

**Bridge coding piece:** the packet parser in `../../../leetcode/019-byte_stream_packet_parser.md` (redo it from a blank page), or `e04_ring_buffer`.

## Interviewer's notes (open only after your self-review, or give to the interviewer)

<details><summary>Answers to clarifying questions</summary>

- **I2C bus speed:** 400 kHz. Reading one sample from a sensor takes about 100 µs including addressing.
- **Microcontroller:** has hardware timers and a DMA engine; 64 KB RAM.
- **USB serial:** in practice ~1 MB/s is available, but the PC may not read for up to 100 ms at a time when busy.
- **Recording:** a session can run for 8 hours.
- **Plot:** shows the last 10 seconds per channel.

</details>

<details><summary>Pushback questions the interviewer will ask</summary>

1. Compute total samples per second and bytes per second including your framing. Does it fit the I2C bus? The USB link?
2. Who puts the timestamp on a sample, and why not the PC when it receives it?
3. How do you schedule the 1 kHz and 100 Hz reads on one bus without jitter piling up?
4. The PC doesn't read for 100 ms. Where do samples wait, and how big must that buffer be?
5. Describe your packet format. How does the PC resynchronize after a corrupted byte?
6. The file writer is slow for a second (disk busy). How do you keep that from making the plot stutter, or vice versa?
7. How does the user find out if a sample was lost, and where was it lost?

</details>

## After your attempt

- Compare with: `../../../windows_internals/014-device_to_app_data_path.md` §6–8 (sizing, overflow, reader thread vs UI thread); ask for a review to get a reference design.
