2026_11_10_12_00-(Issues-And-Fixes)

# Issues and Fixes — every error hit in the driver lab

> **How to use:** search this file for the error code or message before debugging anything. Add a row whenever something fails, even if the fix was quick. Newest first inside each section. Entry numbers in brackets point to [`011-session_handoff.md`](011-session_handoff.md).
> General troubleshooting tables (not specific to this VM) are in [`013`](013-phase5_guide_inspect_crash_analyze.md) §Troubleshooting.

---

## Shell and signing

| Date | Symptom (exact text) | Cause | Fix |
|---|---|---|---|
| 2026-11-10 | `signtool: The term 'signtool' is not recognized as a name of a cmdlet…` | Plain **PowerShell 7** window (prompt in `C:\Windows\System32`), not Developer PowerShell. Only the VS developer shell puts the Windows Kits `bin` folder on PATH | Open admin **Developer PowerShell for VS 2026**. **Confirmed fixed 2026-11-10:** in the dev shell, `Successfully signed: TgCounter.sys` → RUNNING. Or call it by full path: `& (Get-ChildItem "C:\Program Files (x86)\Windows Kits\10\bin\*\arm64\signtool.exe" \| Select-Object -Last 1).FullName sign …` |
| 2026-11-10 | `sc.exe start` → RUNNING even though signing failed in the same run | The `.sys` copied was VS's auto-signed build (WDKTestCert) or an older TgTest-signed one, so which build loaded isn't known | Don't trust RUNNING alone. Check DebugView for `(phase 5 build)` and `dir C:\drivers\TgCounter.sys` timestamps |
| 2026-10-31 | VS log says `Successfully signed`, but that's not enough | VS auto-signs with **WDKTestCert**, not TgTest [49] | Always run `signtool sign /fd sha256 /sm /s My /n TgTest TgCounter.sys` after building |
| 2026-10-25 | `certutil -addstore TrustedPublisher …` → `Cannot open existing Cert store` / `0x80070002` | The TrustedPublisher store doesn't exist on a fresh install [41] | Not needed: TgTest in `LocalMachine\Root` was enough to load [45] |
| 2026-10-25 | `sc` does nothing useful in PowerShell | `sc` is an alias for `Set-Content` | Always type `sc.exe` |

## Service control (`sc.exe`)

| Date | Symptom | Cause | Fix |
|---|---|---|---|
| 2026-11-10 | `sc.exe query TgCounter` → STOPPED, `WIN32_EXIT_CODE : 1077` | `ERROR_SERVICE_NEVER_STARTED`: not started since the last boot. The driver is demand-start, so every reboot leaves it stopped [59] | `sc.exe start TgCounter` after every boot |
| 2026-11-10 | `sc.exe stop TgCounter` → **1062** "The service has not been started" | It was already stopped (normal after a reboot; the driver is demand-start) | Harmless. Carry on with sign → copy → start |
| 2026-10-31 | `sc.exe stop` / `start` → **1060** (service doesn't exist) | The service had been deleted, probably during the 10-27 demo reset (`sc.exe delete`) [50] | `sc.exe create TgCounter type= kernel start= demand binPath= C:\drivers\TgCounter.sys` (space after each `=`) [51] |
| — | `sc.exe start` → **577** | Not re-signed with TgTest, or the old `.sys` was copied | Rebuild loop: sign → copy → start (013 Troubleshooting) |
| — | `sc.exe start` → **1056** | Already running | `sc.exe stop TgCounter` first |
| — | `copy` → "being used by another process" | Driver still loaded | `sc.exe stop TgCounter` first |

## WinDbg

| Date | Symptom | Cause | Fix |
|---|---|---|---|
| 2026-11-10 | `.reload` → `Symbol Loading Error Summary: ntkrnlmp — The system cannot find the file specified`; then `!drvobj` → `Cannot find _OBJECT_DIRECTORY type` | Windows Update installed Insider build **26300.9974**; Microsoft's symbol server returns **404** (`HttpQueryInfo: 800C0194`) for that kernel's `ntkrnlmp.pdb`. Network was fine [60–61] | Diagnose with `!sym noisy` + `.reload /f nt` (look for `800C0194`) and `cmd /c ver`. Fix: restore the last snapshot whose kernel has symbols, then **pause Windows Update**. Or wait for Microsoft to publish the symbols |
| 2026-11-10 | `.reload /f TgCounter.sys` → `"TgCounter.sys" was not found in the image list` | The driver wasn't loaded (stopped since reboot, error 1077) [59–60] | `sc.exe start TgCounter`, then `.reload` again |
| 2026-11-10 | `Syntax error in '.relaod'`; `.reload \f` tries to load a module called `\f`; `lm m TgCountr` lists nothing; `Driver object \Driver\Tgcouter not found` | Typos. WinDbg doesn't suggest corrections, and a misspelled module name just returns an empty list | Copy-paste commands. Options use a **forward** slash (`/f`) |
| 2026-11-01 | `.sympath+ C:\lab\TgCounter\ARM64\Debug` → `0x3 The system cannot find the path specified` | The guide's path is from Phase 4; the Phase 5 build is in `C:\lab\lab2\` [53] | `.symfix C:\symbols` (replaces the path, clearing the bad entry), then `.sympath+ C:\lab\lab2\TgCounter\ARM64\Debug` |
| 2026-11-01 | `lm m TgCounter` shows `(deferred)` | Symbols load lazily | `.reload /f TgCounter.sys` → `(private pdb symbols)` [54] |
| 2026-11-01 | `PEB is paged out (Peb.Ldr = …)` after `.reload` | The local debugger's current process context; user-mode note | Harmless; ignore [54] |

## Windows / PowerShell

| Date | Symptom | Cause | Fix |
|---|---|---|---|
| 2026-11-10 | `Get-Item C:\Windows\System32\ntoskrnl.exe` → "does not exist" in the VS Developer PowerShell window | That window is Windows PowerShell 5.1, probably running as a 32-bit/emulated process, so `System32` is redirected to a folder without the kernel [61] | Use PowerShell 7, or `C:\Windows\Sysnative\ntoskrnl.exe` from that window. `cmd /c ver` gives the build either way |
| 2026-11-10 | Kernel build changed under the lab (26300.9711 → 26300.9974) | Windows Update runs on its own in the VM | Pause updates in the VM (Settings → Windows Update) while a lab phase is in progress |

## Build

| Date | Symptom | Cause | Fix |
|---|---|---|---|
| 2026-10-25 | First TgCounter build failed on the **INF** | Empty WDM project includes an INF the legacy driver doesn't need [39] | Removed the INF from the project (the Phase 5 project kept its INF and built fine) |
| 2026-10-24 | HelloKmdf build failed | Text lost while pasting into `Driver.c` [32] | Re-paste carefully; check the line count after copying files in |

## VM / host

| Date | Symptom | Cause | Fix |
|---|---|---|---|
| 2026-10-24 | Keystrokes don't reach the VM; missed "Press any key to boot from CD" | macOS Accessibility permission off for Fusion [7] | System Settings → Privacy & Security → Accessibility → VMware Fusion ON; restart Fusion. Use **Power On to Firmware** instead of racing the prompt |
| 2026-10-24 | `winget install Microsoft.Sysinternals` not found | Wrong ID in the 010 plan | `winget install Microsoft.Sysinternals.Suite` |
