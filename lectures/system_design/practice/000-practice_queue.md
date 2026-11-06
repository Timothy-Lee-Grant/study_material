# System Design Practice Queue

> **How to use this:** pick **any one** case from "Pick one now" (the top is the most useful next step, but any is fine), run `python3 practice.py start <id>`, do the attempt, and add a row to the **Attempt log** at the bottom. That's all you need to write. When you ask for a review, I read the log and your attempt folder, write the review, update `progress.md`, and re-rank this list.
> **Every attempt:** 45 minutes, timed, out loud, blank page, no references open.
> **Bridge pieces** (family E) are separate 45-minute sessions; do them within a few days of the design case they pair with.
> **Lectures:** each lecture in `../000-gradient_roadmap.md` names the case to attempt right after it. Lecture `002` (the read path) → `a01`.
> Last re-ranked: 2026-11-06 (initial order).

---

## Pick one now

| # | Case | Family | Why it's here |
|---|---|---|---|
| 1 | `a01` URL shortener | A | Pairs with lecture 002 (the read path). The gentlest full run of the seven steps; your deep dive is unique codes across servers |
| 2 | `d01` Device FIFO to a GUI | D | A redo from a blank page of a design you've already studied: does the skeleton make it easier? |
| 3 | `e01` Token bucket (code) | E | Redo from blank; train "interface + one exact example" before code |
| 4 | `b01` Distributed rate limiter | B | Same component at fleet scale; shared state and atomicity |
| 5 | `c01` Parking lot | C | First low-level round; different phases (`practice.py phases`) |
| 6 | `e04` Ring buffer (code) | E | Full vs empty; what each index stands for; overflow policy as code |
| 7 | `a02` News feed | A | Fan-out and the celebrity problem |
| 8 | `d03` Sensor telemetry to a live plot | D | Bandwidth estimation, timestamps, two consumers at different speeds |
| 9 | `e03` Bounded blocking queue (code) | E | Producer–consumer with real threads; why `while` and not `if` |
| 10 | `a04` Notification system | A | Queues, retries, idempotency, priorities |
| 11 | `d02` Power-safe event log | D | Crash consistency on flash; recovery at boot |
| 12 | `c02` Elevator system | C | A state machine per car; mechanism vs policy |

**Later (not yet ranked):** `a03` chat · `a05` ride hailing · `b02` key-value store · `b03` message queue · `d04` firmware update · `d05` touch-to-pixel latency · `e02` LRU cache with expiry.

**Redos:** a case scored under 12/20 comes back into "Pick one now" about 10 days later, from a blank page. A case scored 15+ comes back once after a month.

---

## Before each attempt (the first 30 seconds)

Say this out loud, then start the timer:

> "I'll start with requirements, then the interface and data, trace one request through, draw the components, and then go deep on whatever turns out to be the hardest constraint. I'll finish with failures."

---

## Attempt log

Add one row per attempt. Keep it short; the details live in the attempt folder.

| Date | Case | Mode | Time used | Reached step | Self score /20 | Hardest moment (one line) | Folder | Reviewed? |
|---|---|---|---|---|---|---|---|---|
| | | solo / interviewer | | | | | `attempts/…` | |
