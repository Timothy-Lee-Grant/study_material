# FOR AI ASSISTANTS: how `system_design/practice/` works

> Read this whole file before reviewing an attempt, re-ranking the queue, or adding a case. Also follow the repo-wide rules in `/CLAUDE.md` and `learning_system/README.md` (session checklist, privacy).
> Created 2026-11-06 at Timothy's request: a way to actually practice system design, not just read about it.

---

## 1. What this folder is

A practice loop for the five design families in `../001-system_design_orientation.md` §2: **attempt (timed, spoken) → self-review → review → progress update → next case**. Timothy does the attempts; your jobs are the **review** (§3), the **bookkeeping** (§4), and **adding cases** (§5).

| File | Who writes it |
|---|---|
| `prompts/*.md` | You (when adding cases). Format in §5 |
| `attempts/<date>_<case>/attempt.md`, `diagram.*`, `timer_log.txt` | Timothy / `practice.py` |
| `attempts/<date>_<case>/review.md` | You |
| `000-practice_queue.md` "Pick one now" and "Last re-ranked" | You. The **Attempt log** rows are his; don't edit them except to tick "Reviewed?" |
| `progress.md` | You, after each review |
| `rubric.md`, `drills.md`, `interviewer_prompt.md`, `practice.py`, `templates/` | You, only when he asks or a review shows a rubric gap (note it in the changelog, §6) |

---

## 2. Before a review: read these

1. The attempt folder: `attempt.md` (every line, including the self-review), `timer_log.txt`, and the diagram. Diagrams are usually photos: stage the image from the device and **look at it** with Read. If it's unreadable, say so in the review and score from the text.
2. The case file in `prompts/` (prompt **and** hidden notes).
3. `rubric.md` and `progress.md` (earlier scores: is a weak step improving?).
4. `../001-system_design_orientation.md` (the skeleton and toolkits he's been taught; link to its sections instead of re-teaching).
5. The learning-system files listed in `learning_system/README.md` §3 (learner profile §2, §7, §7a; last ~10 observation-log rows; `private/clicks_log.md`), and `learning_system/private/understanding/system_design.md` if it exists. For family D also read `private/understanding/os_internals_and_drivers.md`: D cases often expose the same misconceptions.

---

## 3. The review (`review.md` in the attempt folder)

### 3.1 Procedure (do it before writing)

1. **Score all ten items** with the rubric, each with one line of **evidence quoted or paraphrased from the attempt**. Score what's on the page or reported as said, not what he probably knew.
2. **Apply the family-specific checks** (rubric). For family D, walk every arrow in his diagram and ask "which context runs this, may it wait?" yourself.
3. **Compare with his self-scores.** A gap of 2+ on any item is a calibration note (both directions matter).
4. **Answer every pushback question he marked ❓**, briefly.
5. **Find the wrong models**: statements that are false, not just missing. These go in a "you thought → reality → why" table (it has worked well for him; `lecture_standards.md` §4).
6. **Pick the three changes** that would raise his score most next time. Rank by impact; make each one concrete ("in step 1, write two non-functional requirements with numbers before anything else"), not general ("be more thorough").
7. **Decide the next case** (§4.2).

### 3.2 Structure

```
# Review: <case title> (<date of attempt>)

> Attempt: `attempt.md` · Mode: solo/interviewer · Time used / reached step · Reviewed <date>

## Scores
| Item | Score | Evidence | (Your score) |
... ten rows + total; calibration note if any item differs by 2+

## What was strong
2–4 bullets, specific. Lead with these (he responds to candor delivered with respect).

## The three changes for next time
1. … 2. … 3. … (concrete, ranked)

## You thought → reality → why
(only if there were wrong models)

## Your ❓ questions, answered

## Reference design
The same seven steps (or the C/E phases), compact: ~60–150 lines. It's one strong answer,
not the only one: say where reasonable designs differ. For E cases: a reference solution
that you have RUN, plus a trace table of the prompt's example.

## Bridge
The coding piece this case pairs with, and why it's worth doing now (or "none").

## Tomorrow's recall prompt
One sentence for his walk, e.g. "Explain where the blocking read runs and why, and size the buffer from named quantities."

## Next
The next case from the queue, and any drill from `drills.md` aimed at the weakest step.
```

### 3.3 Rules

- **Teaching style** follows `learning_system/lecture_standards.md`: name every quantity before using it, give its valid set, derive in small numbered steps, state what each symbol stands for, no firmware analogies, no personified characters.
- **Don't re-teach the orientation lecture.** Link to its sections. Teach only what this attempt shows is missing.
- **Honest sizing (T7):** if he went deep on something that doesn't matter for this family, say so and why.
- **Spoilers:** the reference design goes only in `review.md`. Never put reference answers into a case file or the queue.
- **Public repo:** reviews are about the work. No company names, interviewers or specific interviews (his standing preference), and no psychological evaluations. Those go in `learning_system/private/` only.
- If the attempt has no self-review yet, ask him to fill it in first (one line), unless he says to skip it.

---

## 4. Bookkeeping after a review

### 4.1 Always

1. `progress.md`: add the score row; update "Current focus" (weakest step = the lowest step averaged over his last 3 attempts); update toolkit rows the attempt gave evidence for (✅/🟡/❌ with the date).
2. `000-practice_queue.md`: tick "Reviewed?" in his log row; re-rank "Pick one now" (§4.2); update "Last re-ranked".
3. `learning_system/private/understanding/system_design.md`: create it on the first review (same format as `os_internals_and_drivers.md`); add concept statuses and open misconceptions with dates.
4. `learning_system/private/observation_log.md`: one row (what the attempt showed, teaching implication).

### 4.2 Re-ranking rules

- Keep 10–12 cases in "Pick one now". Keep a **mix**: at least one of A/B, one D, one E in the top five. Platform-heavy roles are his target, so D stays well represented.
- A case scored **< 12/20** returns ~10 days later, marked "(redo)". **15+** returns once after ~a month.
- After a design case with a bridge, put the bridge E case in the top three.
- If one step is ≤ 1 in three consecutive attempts, put the matching drill in "Pick one now" as its own row.
- Move cases from "Later" into the list as earlier ones are done; prefer the next level (starter → core → advanced) within a family.

---

## 5. Adding a case

Use when he asks for more cases, or turns a real interview question into one (write it **neutrally**: no company, interviewer or "I was asked").

1. File name: `<family letter><two digits>_<slug>.md` in `prompts/` (next free number in that family).
2. First line, exactly (the script parses it): `<!-- id: <file stem> | family: <A-E> | level: starter|core|advanced | minutes: 45 | bridge: <case id or text or none> -->`
3. Then `# <Id> · <Title>` and these sections, with these exact headings:
   - `## The prompt`: the **full** problem in your own words, with scale numbers (users, rates, sizes, latency targets). For E cases: exact signatures, one example table with **exact outputs you have verified by running code**, and constraints.
   - `## What this case trains`: 3–5 bullets, no answers. Name the bridge.
   - `## Interviewer's notes (open only after your self-review, or give to the interviewer)`: two `<details>` blocks: answers to clarifying questions (5–6), pushback questions (6–7, each one testing a specific idea).
   - `## After your attempt`: where to compare (his own lectures first, then outside references you've checked).
4. Add a row to `prompts/README.md`, and add the case to "Later" in the queue (or rank it).
5. Run `python3 practice.py list` and `python3 practice.py start <id> --no-timer` once to check it parses, then delete the test attempt folder only if he allows deletion (otherwise tell him it's there).

---

## 6. Changelog

| Date | Change |
|---|---|
| 2026-11-06 | Created: 19 cases (A01–A05, B01–B03, C01–C02, D01–D05, E01–E04), practice.py, rubric, drills, interviewer prompt, progress tracker |
