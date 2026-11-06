<!-- id: d04_firmware_update_ab | family: D | level: advanced | minutes: 45 | bridge: none -->
# D04 · Fleet Firmware Update That Can't Brick

## The prompt

A company has 1 million deployed devices (each with a microcontroller, 2 MB of flash and a network connection). Design the system that updates their firmware. New firmware images (about 500 KB) are published to a server. Devices must download, verify and install them. **A device must never be left unbootable**, even if power is lost at any moment during download or install, or if the new firmware crashes on startup. The company must be able to roll an update out gradually and stop it if something goes wrong, and know which devices are on which version.

Design both sides: the device (flash layout, boot decision, install steps) and the server (publishing, rollout control, reporting).

## What this case trains

- **A/B slots**, a trial boot and automatic **rollback** (a small state machine on the device).
- **Verification**: signatures, so only genuine images install.
- **Staged rollout** with health signals: the distributed half of the problem.
- Download resume and server bandwidth estimation.

**Bridge coding piece:** none required. Optional: write the bootloader's decision function `choose_slot(state) -> slot` with the states from your design, and test every power-loss point.

## Interviewer's notes (open only after your self-review, or give to the interviewer)

<details><summary>Answers to clarifying questions</summary>

- **Bootloader:** a small, never-updated bootloader exists; you decide what it does.
- **Watchdog:** a hardware watchdog resets the device if firmware stops kicking it.
- **Connectivity:** devices check in once an hour; some are offline for weeks.
- **Security:** images must be signed; the device has the public key in the bootloader.
- **Rollout:** 1% → 10% → 50% → 100%, with automatic stop if failure reports exceed a threshold.

</details>

<details><summary>Pushback questions the interviewer will ask</summary>

1. Draw the device's update states and the bootloader's decision for each. What does the bootloader do after a power loss in each state?
2. The new firmware boots but crashes 5 seconds in, every time. How does the device get back to the old version without help?
3. When does a new image become "confirmed", and who decides?
4. An attacker on the network replaces the image. Where exactly is that caught?
5. Estimate server bandwidth if all 1 million devices download at once. How does your rollout avoid that?
6. A device is offline during versions 5, 6 and 7, then comes back. What does it install?
7. How would you know, while at 1%, that this release should be stopped?

</details>

## After your attempt

- Ask for a review to get a reference design (A/B partitions with trial boot, as used by Android A/B updates and MCU bootloaders such as MCUboot).
