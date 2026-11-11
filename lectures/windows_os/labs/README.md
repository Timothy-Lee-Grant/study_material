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

| File | Answers | Updated |
|---|---|---|
| [`lab_progress.md`](lab_progress.md) | **Where am I, and what's next?** A checklist of every phase and step, with the current position at the top | At the end-of-session handoff |
| [`issues_and_fixes.md`](issues_and_fixes.md) | **I've seen this error before. What fixed it?** Every problem hit in the lab, with its cause and fix | At the end-of-session handoff (Claude adds every problem from that session) |
| [`011-session_handoff.md`](011-session_handoff.md) | **The full history.** VM facts (paths, snapshots, certificate, versions), decisions, and a numbered log of every session | At the end-of-session handoff (new "Session N" entries; don't rewrite history) |

`lab_progress.md` is the short "you are here" view, `011` is the long record behind it, and the issues log means a problem only gets debugged once.

### Code

| Folder | What it is | Used in |
|---|---|---|
| [`code/tgcounter/`](code/tgcounter/) | The original driver, IOCTL header and client | Lecture 009, Phase 4 |
| [`code/tgcounter_phase5/`](code/tgcounter_phase5/) | Phase 5 build: adds the `crash` and `paged` bug IOCTLs and the `(phase 5 build)` load message | Phase 5 (013) |

---

## Session routine

**How lab sessions work:** Claude guides, Timothy does. No prediction exercises and no note-taking during the session. Claude gives the next concrete step (exact commands, what output means it worked), explains the result briefly, helps fix whatever breaks, and moves on. All the writing happens once, at the end.

**Start of a session (Claude):**
1. Read `lab_progress.md` → "Current position".
2. Read the newest entries in `011-session_handoff.md` (TL;DR + the last session's log).
3. Skim `issues_and_fixes.md` so known problems aren't debugged twice.
4. Give Timothy the resume steps and the next thing to do.

**During a session (Claude):**
- One step at a time: the commands to run, what success looks like, then a short plain-words explanation of the output once Timothy pastes it.
- When something fails: diagnose it, give the fix, keep going. Don't stop to write documentation.
- Keep the guide's "Expected" results in mind to check the output, but don't ask Timothy to guess them first.

**End of a session — the handoff (Claude, when Timothy says he's stopping):**
1. `011-session_handoff.md`: a "Session N" section listing what was done, the key output, and the state left behind (driver loaded or not, debug mode on or off, Verifier on or off, snapshots taken). Update "Last updated", the status board and the TL;DR.
2. `lab_progress.md`: tick finished steps, rewrite "Current position" and the next action.
3. `issues_and_fixes.md`: one row for every problem hit that session (exact error text, cause, fix).
4. Per the repo rules: observation log and `reading_status.md` (private), and `where_i_stand.md` at a lab milestone.

## Machine facts you'll need every session

These are copied from `011`. If they change, update both places.

- **VM:** VMware Fusion, Windows 11 ARM64, 4 cores / 4 GB, test signing on, Secure Boot off.
- **Shell:** admin **Developer PowerShell for VS 2026**. A plain PowerShell 7 window doesn't have `signtool` on its PATH.
- **Phase 5 build output:** `C:\lab\lab2\TgCounter\ARM64\Debug\TgCounter.sys` and `.pdb`; client `C:\lab\lab2\tgclient\ARM64\Debug\tgclient.exe`. The guide's `C:\lab\TgCounter\…` paths are old.
- **Loaded driver location:** `C:\drivers\TgCounter.sys` (service `TgCounter`, kernel, demand start).
- **Rebuild loop:** build (ARM64/Debug) → `sc.exe stop TgCounter` → `signtool sign /fd sha256 /sm /s My /n TgTest TgCounter.sys` → `copy TgCounter.sys C:\drivers\` → `sc.exe start TgCounter` → check DebugView for `(phase 5 build)`.
