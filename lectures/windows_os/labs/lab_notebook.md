2026_11_10_12_00-(Lab-Notebook)

# Lab Notebook — predict, run, conclude

> **Why this exists:** the Phase 5 guide asks for a prediction before every exercise. A prediction only teaches you something when it's written down *before* the result, so you can compare the two honestly. This is where that happens. The idea behind it is lecture 018 §8 (the predict → evidence → one-sentence-conclusion loop).
> **Rule:** fill in **Prediction** before running the command. Never edit a prediction afterward; a wrong prediction is the most useful entry in this file.

---

## Entry template

```markdown
### <lab>.<exercise> — <short title> (YYYY-MM-DD)
**Command:** `...`
**Prediction (before running):** what I expect, and why.
**Result:** what actually came out (paste the key lines).
**Match?** ✅ / ❌ / partly: what was different.
**Conclusion (one sentence):** what this shows about how Windows works.
**Open question:** (optional) what I still don't understand.
```

---

## Phase 5

### 5.1.1 — Is TgCounter loaded, and where? (2026-11-01)
**Command:** `lm m TgCounter`
**Prediction (before running):** _(not recorded at the time)_
**Result:** ``fffff800`66080000 – fffff800`66088000`` (0x8000 = 32 KB, 8 pages). Shown as `(deferred)` at first; after `.reload /f TgCounter.sys` → `(private pdb symbols) c:\lab\lab2\tgcounter\arm64\debug\TgCounter.pdb`. The driver sits ~22 MB below the kernel base ``fffff800`67600000`` (this boot; KASLR changes it every boot).
**Match?** ✅ with the guide: a high kernel-space address and private symbols.
**Conclusion (one sentence):** _(to write)_

### 5.1.2 — The dispatch table
**Command:** `!drvobj \Driver\TgCounter 2`
**Prediction (before running):**
**Result:**
**Match?**
**Conclusion (one sentence):**

### 5.1.3 — The device object
**Command:** `!devobj \Device\TgCounter`
**Prediction (before running):**
**Result:** (write down the `DevExt` address)
**Match?**
**Conclusion (one sentence):**

### 5.1.4 — The counter, read from kernel memory
**Command:** `dt TgCounter!_TG_EXTENSION <DevExt>`, then run `tgclient.exe` and repeat
**Prediction (before running):**
**Result:**
**Match?**
**Conclusion (one sentence):**

### 5.1.5 — The paged allocation
**Command:** `dd poi(TgCounter!g_PagedValue) L1`, `!pool poi(TgCounter!g_PagedValue)`
**Prediction (before running):**
**Result:**
**Match?**
**Conclusion (one sentence):**

### 5.1.6 — Names in the object manager
**Command:** `!object \Device\TgCounter`, `!object \GLOBAL??\TgCounter`
**Prediction (before running):**
**Result:**
**Match?**
**Conclusion (one sentence):**

### 5.1.7 — The dispatch routine as ARM64 instructions
**Command:** `u TgCounter!TgDispatchDeviceControl L20`
**Prediction (before running):**
**Result:**
**Match?**
**Conclusion (one sentence):**

### 5.1.8 — Another device's stack
**Command:** `!devnode 0 1`, then `!devstack <PDO>`
**Prediction (before running):** why TgCounter has no devnode:
**Result:**
**Match?**
**Conclusion (one sentence):**

### 5.2 — Live kernel dump
**Prediction (before opening the dump):** stop code:
**Result:**
**Match?**
**Conclusion (one sentence):**

### 5.3 — Crash on purpose
**Prediction (written before `tgclient crash`):**

| Item | Prediction | Actual |
|---|---|---|
| Stop code | | |
| P1 (address) | | |
| P2 (IRQL) | | |
| P3 (read/write) | | |
| P4 / function `!analyze` names | | |
| Stack shape (`k`) | | |
| Faulting instruction + register | | |
| Build timestamp (`lmv m TgCounter`) | | |

**Conclusion (one sentence):**
**Reflection:** why 0xD1 and not "just a NULL pointer"?

### 5.4 — Driver Verifier
**Without Verifier, prediction for `tgclient paged`:**
**Result (5–10 runs):**

**With Verifier, prediction:** crash? stop code?

| Item | Prediction | Actual |
|---|---|---|
| Stop code | | |
| P1 | | |
| `!pool <P1>` | | |
| `!pte <P1>` | | |
| `!verifier` flags | | |

**Conclusion (one sentence):** what the bug is, why it didn't crash before, why it crashed now.

### 5.5 — WPR trace
**Prediction:** how long a `tgclient.exe` run lasts; which modules run the most DPCs/ISRs in this VM:
**Result:**
**Reflection:** why can't TgCounter's own events be seen in the trace?
