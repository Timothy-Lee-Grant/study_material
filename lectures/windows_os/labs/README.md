2026_11_10_12_00-(Labs-README)

# Labs — Windows Driver Lab (TgCounter on an ARM64 VM)

> **For:** Timothy, and Claude at the start of every lab session
> **What lives here:** the hands-on walkthroughs (how to do each phase), the code you build in the VM, and the trackers we update as we go. The concept lectures these labs rely on are in [`../lectures/`](../lectures/000-roadmap.md).

---

## The documents

### Walkthroughs (what to do)

| File | What it is |
|---|---|
| [`010-lab_setup_work_plan.md`](010-lab_setup_work_plan.md) | The original plan, Phases 0–6: VM → test signing → VS + WDK → build/sign/load TgCounter → inspect/crash/analyze → optional live debugging |
| [`013-phase5_guide_inspect_crash_analyze.md`](013-phase5_guide_inspect_crash_analyze.md) | The detailed Phase 5 guide (5.0–5.5). It replaces 010's Phase 5 |
| [`012-demo_runbook.md`](012-demo_runbook.md) | How to show the lab off live or on a recording |

### Trackers (where we are, what happened)

| File | Answers | Update when |
|---|---|---|
| [`lab_progress.md`](lab_progress.md) | **Where am I right now, and what's next?** A checklist of every phase and exercise, with the current position at the top | Each step is finished (tick it), and at the end of every session (update "Current position") |
| [`lab_notebook.md`](lab_notebook.md) | **What did I predict, what happened, and what did I learn?** One entry per exercise: prediction → command → result → one-sentence conclusion | Before running anything with a prediction step (write the prediction), then right after (write the result) |
| [`issues_and_fixes.md`](issues_and_fixes.md) | **I've seen this error before. What fixed it?** Every error hit in the lab, with its cause and fix | Whenever something fails, even if the fix was quick |
| [`011-session_handoff.md`](011-session_handoff.md) | **The full history.** VM facts (paths, snapshots, certificate, versions), decisions, and a numbered log of every session | End of every session (new "Session N" entries; don't rewrite history) |

How they fit together: `lab_progress.md` is the short "you are here" view. `011` is the long record behind it. The notebook holds your own reasoning, and the issues log turns every error into something you only debug once.

### Code

| Folder | What it is | Used in |
|---|---|---|
| [`code/tgcounter/`](code/tgcounter/) | The original driver, IOCTL header and client | Lecture 009, Phase 4 |
| [`code/tgcounter_phase5/`](code/tgcounter_phase5/) | Phase 5 build: adds the `crash` and `paged` bug IOCTLs and the `(phase 5 build)` load message | Phase 5 (013) |

---

## Session routine

**Start of a session (Claude):**
1. Read `lab_progress.md` → "Current position".
2. Read the newest entries in `011-session_handoff.md` (TL;DR + the last session's log).
3. Skim `issues_and_fixes.md` so known problems aren't debugged twice.
4. Give Timothy the resume checklist and the next step, with a prediction question if the step has one.

**During a session:**
- Before a step with a prediction: Timothy writes the prediction in `lab_notebook.md` (or says it, and Claude records it word for word).
- When an error appears: add a row to `issues_and_fixes.md`.
- When a step is done: tick it in `lab_progress.md`.

**End of a session (Claude):**
1. Update "Current position" and "Last updated" in `lab_progress.md`.
2. Add a "Session N" section to `011-session_handoff.md` (numbered entries, facts, error text, snapshots taken).
3. Per the repo rules: observation log and `reading_status.md` (private), and `where_i_stand.md` at a lab milestone.

---

## Machine facts you'll need every session

These are copied from `011`. If they change, update both places.

- **VM:** VMware Fusion, Windows 11 ARM64, 4 cores / 4 GB, test signing on, Secure Boot off.
- **Shell:** admin **Developer PowerShell for VS 2026**. A plain PowerShell 7 window doesn't have `signtool` on its PATH.
- **Phase 5 build output:** `C:\lab\lab2\TgCounter\ARM64\Debug\TgCounter.sys` and `.pdb`; client `C:\lab\lab2\tgclient\ARM64\Debug\tgclient.exe`. The guide's `C:\lab\TgCounter\…` paths are old.
- **Loaded driver location:** `C:\drivers\TgCounter.sys` (service `TgCounter`, kernel, demand start).
- **Rebuild loop:** build (ARM64/Debug) → `sc.exe stop TgCounter` → `signtool sign /fd sha256 /sm /s My /n TgTest TgCounter.sys` → `copy TgCounter.sys C:\drivers\` → `sc.exe start TgCounter` → check DebugView for `(phase 5 build)`.
