2026_11_10_12_00-(Lab-Progress)

# Lab Progress — where we are in the driver lab

> **Last updated:** 2026-11-10 (Session 5)
> **Detail behind every tick:** [`011-session_handoff.md`](011-session_handoff.md) (entry numbers in brackets, e.g. [54]).
> **Steps come from:** [`010`](010-lab_setup_work_plan.md) (Phases 0–4, 6) and [`013`](013-phase5_guide_inspect_crash_analyze.md) (Phase 5).

---

## Current position

**Phase 5 → lab 5.1 → exercise 2** (`!drvobj \Driver\TgCounter 2`).

**State of the VM (Session 5, 2026-11-10):**
- Rebuild loop rerun in **Developer PowerShell for VS 2026** ✅: stop → `Successfully signed` (TgTest) → copy → **RUNNING**.
- **Next action:** confirm `TgCounter: loaded (phase 5 build)` in DebugView → `tgclient.exe` (1/2/3) → WinDbg Local attach + symbols → exercise 2 (prediction first in `lab_notebook.md`).
- Debug mode: **ON** (`bcdedit /debug on`, from Session 4). Turn it off before 5.3.
- Newest snapshot: **`TgCounter: loaded (phase 5 build)`**. The next one to take is `before-crash-labs` (5.3).

---

## Phases 0–4 ✅

- [x] **Phase 0** — decisions: VMware Fusion, VM on the T7 SSD, 4 GB RAM
- [x] **Phase 1** — Windows 11 ARM64 installed, VMware Tools, updated → snapshot `clean-windows-testmode`
- [x] **Phase 2** — test signing ✅, Debug Print Filter, kernel memory dump, WinDbg, Sysinternals, DebugView kernel capture → snapshot `driver-lab-ready`
- [x] **Phase 3** — VS 2026 + SDK + WDK 10.0.28000, HelloKmdf ARM64 builds → snapshot `toolchain-ready`
- [x] **Phase 4** — TgCounter built, signed with TgTest, loaded; client prints 1/2/3 [45] → snapshot `tgcounter-works`

## Phase 5 — Inspect, crash, analyze ⏳

### 5.0 Get the Phase 5 code in, build, load ✅
- [x] Files into the VM (in `C:\lab\lab2\`) [49]
- [x] Both projects build (ARM64/Debug) [49]
- [x] Re-sign with TgTest, service re-created, start [50–51]
- [x] Smoke test: 1/2/3, `get` → 3 [51]
- [x] Snapshot (named `TgCounter: loaded (phase 5 build)`) [55]

### 5.1 Local kernel debugging ⏳
- [x] `bcdedit /debug on` + reboot [52]
- [x] WinDbg → Attach to kernel → Local → `lkd>` [52]
- [x] Symbols: `.symfix C:\symbols`, `.sympath+ C:\lab\lab2\TgCounter\ARM64\Debug`, `.reload` [53–54]
- [x] **Ex 1** `lm m TgCounter`: kernel address, private symbols [54]
- [ ] **Ex 2** `!drvobj \Driver\TgCounter 2`: the dispatch table
- [ ] **Ex 3** `!devobj \Device\TgCounter`: note `DevExt`
- [ ] **Ex 4** `dt TgCounter!_TG_EXTENSION <DevExt>`: counter = 3, run the client, = 6
- [ ] **Ex 5** `dd poi(TgCounter!g_PagedValue) L1` + `!pool`: 42, Paged, `TgTg`
- [ ] **Ex 6** `!object \Device\TgCounter`, `!object \GLOBAL??\TgCounter`
- [ ] **Ex 7** `u TgCounter!TgDispatchDeviceControl L20`: ARM64 instructions
- [ ] **Ex 8** `!devnode 0 1` → `!devstack` on a VMware device
- [ ] `bcdedit /debug off` + reboot

### 5.2 Live kernel dump
- [ ] Task Manager (admin) → System → Create live kernel memory dump (Full)
- [ ] Open it in WinDbg, predict the stop code → 0x161?
- [ ] Repeat 5.1 exercises 2–5 on the dump (counter frozen)

### 5.3 Crash on purpose
- [ ] Debug mode off confirmed; dump settings confirmed
- [ ] Shut down → snapshot **`before-crash-labs`**
- [ ] Written prediction: stop code, P1–P4, function, stack shape (in the notebook)
- [ ] `tgclient.exe crash` → blue screen → `C:\Windows\MEMORY.DMP` exists
- [ ] Analysis table: `!analyze -v`, `k`, `!irql`, `ln/u/ub <P4>`, `r`, `lmv m TgCounter`, `.frame`/`dv`
- [ ] One-sentence conclusion written

### 5.4 Driver Verifier
- [ ] `tgclient paged` ×5–10 without Verifier (prediction first)
- [ ] `verifier /bootmode resetonbootfail` + `verifier /standard /driver TgCounter.sys` → reboot → `/querysettings`
- [ ] `tgclient paged` under Verifier (prediction first) → crash
- [ ] Analysis: `!analyze -v`, `!pool <P1>`, `!pte <P1>`, `k`, `!verifier`
- [ ] One-sentence conclusion written
- [ ] `verifier /reset` → reboot → confirm nothing is verified

### 5.5 WPR trace
- [ ] `wpr -profiles` works; WPA installed (note which package worked on ARM64)
- [ ] Record `tg.etl` around several client runs
- [ ] Find `tgclient.exe` in CPU Usage (Precise); list the top DPC/ISR modules

### Phase 5 wrap-up
- [ ] Shut down → snapshot **`phase5-done`**
- [ ] Stop codes from 5.3 and 5.4 (with P1–P4) recorded in `011`
- [ ] Recall check: explain 5.4 out loud (paged pool, spin lock, DISPATCH_LEVEL, page fault, Force IRQL checking)

## Phase 6 — Optional live debugging (KDNET) ⏳ later
- [ ] Decide whether to do it (see 010 Phase 6)

---

## Snapshots

| # | Name | Taken | State |
|---|---|---|---|
| 1 | `clean-windows-testmode` | 2026-10-24 17:56 | Windows + test mode |
| 2 | `driver-lab-ready` | 2026-10-24 18:19 | + WinDbg, Sysinternals, dump settings |
| 3 | `toolchain-ready` | 2026-10-24 ~20:03 | + VS 2026 / WDK |
| 4 | `tgcounter-works` | 2026-10-25 ~19:35 | Phase 4 done |
| 5 | `TgCounter: loaded (phase 5 build)` | 2026-11-01 ~01:49 | Phase 5 code loaded (current) |
| — | `before-crash-labs` | to take at 5.3 | |
| — | `phase5-done` | to take at wrap-up | |
