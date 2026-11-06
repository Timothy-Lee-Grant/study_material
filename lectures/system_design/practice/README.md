# System Design Practice

This folder is where system design gets **practiced**, not read about. Lecture `../001-system_design_orientation.md` gives the map (five families, one seven-step skeleton). Everything here exists to make you run that skeleton out loud, under a clock, over and over, and see your scores change.

> **The one rule:** an attempt is 45 minutes, timed, spoken out loud, from a blank page, with no references open. Everything else in this folder is support for that.

---

## What's in here

| Path | What it is |
|---|---|
| [`000-practice_queue.md`](000-practice_queue.md) | **Start here.** "Pick one now" list, plus the attempt log you fill in after each attempt |
| [`prompts/`](prompts/) | One file per case: the full problem, what it trains, and **hidden** interviewer notes (clarifying answers and pushback questions) |
| [`practice.py`](practice.py) | Starts an attempt: creates your attempt file, shows the prompt, runs the phase timer |
| [`rubric.md`](rubric.md) | How an attempt is scored (/20), with what 0, 1 and 2 look like for each step |
| [`interviewer_prompt.md`](interviewer_prompt.md) | Paste into a Claude chat or voice conversation to get a live interviewer who answers questions and pushes back |
| [`drills.md`](drills.md) | 5–15 minute drills for one step at a time (requirements, estimation, tracing, "who may wait here?") |
| [`progress.md`](progress.md) | Your scores per step over time, and which toolkit ideas you can explain |
| [`attempts/`](attempts/) | One folder per attempt: your `attempt.md`, a photo of your diagram, and the `review.md` I write |
| [`templates/attempt.md`](templates/attempt.md) | The blank attempt sheet `practice.py` copies |

---

## One practice session (about 80 minutes)

1. **Pick a case** from `000-practice_queue.md` (or run `python3 practice.py random`).
2. **Start it:**
   ```bash
   cd lectures/system_design/practice
   python3 practice.py start a01        # any id prefix works: a01, d01, e03…
   ```
   This creates `attempts/YYYY-MM-DD_<case>/attempt.md` with the prompt and the seven-step sheet, prints the prompt, and starts the timer. The timer tells you when to move to the next step. `Ctrl-C` stops it early.
3. **Attempt (45 min).** Talk out loud the whole time, as if an interviewer were there. Draw on paper, a whiteboard or Excalidraw. Write short notes under each step in `attempt.md`; the diagram can stay on paper.
   - **Clarifying questions:** write them down in step 1 and **give yourself a reasonable answer** (write it next to the question). Don't open the hidden notes. (Or use interviewer mode, below, and ask a real interviewer.)
   - **Stuck on a choice?** Pick one, write the reason in one line, and move on. Being stuck for five minutes on one box costs more than a slightly wrong box.
4. **Save the diagram** in the attempt folder (`diagram.jpg`, or paste an Excalidraw link into `attempt.md`).
5. **Self-review (5 min):** fill in the "Self-review" section at the bottom of `attempt.md` *before* opening anything. Score yourself with `rubric.md`.
6. **Now open the hidden notes** in the case's prompt file. For each pushback question, write a one-line answer in the self-review section. The ones you can't answer are your study list.
7. **Log it:** add one row to the attempt log in `000-practice_queue.md`.
8. **Ask for a review** (optional but recommended): *"review my system design attempt `attempts/2026-11-07_a01_url_shortener`."* I'll write `review.md` in that folder: scores with reasons, what was strong, the top three changes, a reference design to compare against, and the next case.
9. **Next day, on a walk:** explain the design and its biggest trade-off from memory. Send it as a recall if you want it analyzed.

**Bridge pieces:** many cases name a family-E coding problem (token bucket, LRU cache, blocking queue, ring buffer). When a case has one, do that problem in a separate 45-minute session within a few days. It's the coding version of one box in the design.

---

## Interviewer mode (recommended once you've done two solo attempts)

Solo attempts train the skeleton. A real interview also trains **driving a conversation while someone interrupts you**. Open [`interviewer_prompt.md`](interviewer_prompt.md), copy the prompt plus the whole case file into a new Claude chat (voice mode works well), and run the timer at the same time. At the end the interviewer gives you a summary block; paste it into the attempt's `attempt.md`.

---

## The families (from lecture 001 §2)

| Code | Family | Unit of design | Example in `prompts/` |
|---|---|---|---|
| **A** | Product design | Services + databases | A01 URL shortener, A02 news feed |
| **B** | Infrastructure / component design | One component, deeply | B01 distributed rate limiter |
| **C** | Low-level / object-oriented design | Classes and state | C01 parking lot, C02 elevator |
| **D** | Device / systems design | Hardware → driver → app → UI | D01 device FIFO to a GUI |
| **E** | Design-then-code | Data structures + functions, runnable | E01 token bucket, E03 blocking queue |

The timer uses different phases for C and E (they're not run with the seven-step skeleton as is); `practice.py phases` shows them.

---

## Commands

```bash
python3 practice.py list                  # all cases, with how many times you've attempted each
python3 practice.py random                # suggests a least-attempted case
python3 practice.py random --family D     # same, only family D
python3 practice.py start d01             # new attempt + timer (45 min)
python3 practice.py start e02 --no-timer  # new attempt, no timer
python3 practice.py start a02 --minutes 30  # shorter session; phases scale down
python3 practice.py timer --family A      # just the timer, no attempt file
python3 practice.py phases                # print the phase plan for each family
```

Python 3.8+ and nothing else. On a Mac, the timer beeps in Terminal at each phase change.
