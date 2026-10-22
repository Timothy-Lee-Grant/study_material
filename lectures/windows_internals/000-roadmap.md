2026_10_21_21_30-(Windows-Internals-Roadmap)

# Windows Internals — Series Roadmap

> **For:** Timothy · **Date:** 2026-10-21
> **What this series is:** a focused path to being comfortable debugging Windows at the kernel level, and understanding the mechanics underneath it. It builds on `lectures/firmware/windows_platform_validation.md` and `lectures/firmware/003-from_bare_metal_to_an_os.md`.

---

## The lectures

| # | Lecture | Group | What you'll be able to do after it |
|---|---|---|---|
| 001 | `001-windbg_essentials.md` | Debugging | Set up symbols; use `!analyze -v`, `k`, `lm`, `!thread`, `!irql`, `!devnode`, `!devstack` and read what they print |
| 002 | `002-bugchecks_decoded.md` | Debugging | Read 0xD1, 0x133, 0x9F, 0x50, 0x7E from their parameters, and run each one's investigation recipe |
| 003 | `003-dumps_and_failure_types.md` | Debugging | Choose minidump / kernel / complete / active / live dumps, and collect the right data for a crash, a hang, or a dead device |
| 004 | `004-driver_verifier_and_etw.md` | Debugging | Run Driver Verifier safely; record traces with WPR and find a slow DPC or a stuck device in WPA |
| 005 | `005-interrupts_irql_and_deferred_work.md` | Kernel mechanics | Explain IRQL, the ISR → DPC → work item chain, and why paging is forbidden at DISPATCH_LEVEL, in code |
| 006 | `006-device_stacks_pnp_inf_signing.md` | Kernel mechanics | Explain PDO/FDO/filters, how PnP builds and starts a stack, read an INF, and explain driver signing |
| 007 | `007-power_management_and_modern_standby.md` | Kernel mechanics | Explain S-states, D-states and Modern Standby, and debug a resume or standby bug |
| 008 | `008-processes_threads_memory_and_shared_sections.md` | Kernel mechanics | Explain processes vs threads and virtual → physical mapping, and share memory across processes with named sections, mutexes and events (runnable code) |
| 009 | `009-what_a_driver_actually_is.md` | Kernel mechanics | Explain what's inside a `.sys` file, what configuration loads it, what `DriverEntry` registers, every hop from `DeviceIoControl` to the driver and back, and how drivers call drivers and the kernel (WDM + KMDF, real build) |

Code: `code/shm_demo.c` (used in 008); `code/tgcounter/` (driver, IOCTL header, client; used in 009).

## Reading order

The numbering follows your priority (debugging first). The debugging lectures are written to stand on their own: wherever they need a mechanism, they give a short "just enough" box and point to the full lecture. Two orders both work:

- **Priority order (recommended):** 001 → 002 → 003 → 004, then 005 → 006 → 007 → 008.
- **Foundations first:** if a debugging lecture's "just enough" box feels thin, read 005 and 006 first. `!devstack` in 001 and 0x9F in 002 make more sense after 006 and 007.

## How the pieces connect

```
           005 IRQL / ISR / DPC / paging  ──►  002 0xD1, 0x133      ──►  004 Verifier "Force IRQL checking"
           006 device stacks / PnP        ──►  001 !devnode, !devstack ──► 002 0x9F (whose IRP is stuck?)
           007 power / D-states           ──►  002 0x9F             ──►  003 "dead after resume" data collection
           008 processes / threads / VM   ──►  001 !thread, !process ──► 002 0x50 (which address, which space?)
```

## Hands-on setup (once, for the labs)

All the labs need a Windows machine. A Windows 11 Arm virtual machine on your Mac is enough to:
- install WinDbg (`winget install Microsoft.WinDbg`), the Windows Performance Toolkit (part of the Windows ADK) and Sysinternals (NotMyFault, LiveKD),
- create and analyze crash dumps and live dumps,
- run Driver Verifier and WPR/WPA,
- compile and run `code/shm_demo.c`.

**Live kernel debugging** of a second machine or VM (KDNET) is optional. Setup depends on the hypervisor, so treat it as a later step. Dumps give you 90% of the practice without it.

## Done means

Each lecture ends with self-check questions. A lecture is "done" when you can answer them without looking **and** you've done its lab at least once on a real Windows install.
