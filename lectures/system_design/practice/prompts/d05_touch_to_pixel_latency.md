<!-- id: d05_touch_to_pixel_latency | family: D | level: advanced | minutes: 45 | bridge: none -->
# D05 · Touch-to-Pixel Latency

## The prompt

On a laptop with a touchscreen, a drawing app should feel like ink: when a finger moves, the line under it should appear with as little delay as possible. Today it feels laggy. Design (1) the full path from a finger touching the glass to the changed pixels being visible, naming every stage and which component owns it, (2) a way to **measure** the latency of the whole path and of each stage, and (3) the changes you'd make to get end-to-end latency under 50 ms, without hurting battery life too much.

## What this case trains

- A **pipeline view** across hardware, firmware, kernel, input stack, app and display.
- **Measurement design**: end-to-end (external) vs per-stage (tracing timestamps).
- **Where latency hides**: scan rates, deferred work, message queues, frame pacing and buffering.
- **Latency vs power** trade-offs.

Related reading (after the attempt): `../../../firmware/003-platform_validation.md` (the touch event chain), `../../../windows_internals/015-performance_analysis_cpu_and_waits.md`, `../../../windows_internals/016-battery_life_and_energy_efficiency.md`.

## Interviewer's notes (open only after your self-review, or give to the interviewer)

<details><summary>Answers to clarifying questions</summary>

- **Hardware:** a touch controller on I2C or SPI that signals with an interrupt line; display at 60 Hz.
- **OS:** Windows (but a Linux answer is welcome; the stages are the same idea).
- **Current measurement:** about 90 ms end to end, measured with a high-speed camera.
- **Budget:** you may raise the touch scan rate, but battery life on video playback must not drop.
- **App:** you own the app's code; you don't own the OS compositor.

</details>

<details><summary>Pushback questions the interviewer will ask</summary>

1. List the stages from glass to pixel and give each a rough latency range. Where does most of the 90 ms probably go?
2. How do you measure end-to-end latency without trusting any software timestamp?
3. How do you put per-stage timestamps on one touch event as it moves through the system, and line them up?
4. The touch controller scans at 120 Hz. What's the average and worst-case delay that adds? Derive it.
5. The app redraws on the UI thread right after a slow layout pass. What happens to latency, and what do you change?
6. Why can rendering one frame ahead (or triple buffering) add a whole frame of latency?
7. Raising the scan rate costs power. How do you get the benefit only while the user is drawing?

</details>

## After your attempt

- Compare with the lectures listed above; ask for a review to get a reference pipeline with latency ranges.
