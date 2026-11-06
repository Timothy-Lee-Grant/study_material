# FOR AI ASSISTANTS: how the `problem_deep_dives/` folder works

> Read this whole file before analyzing a problem or writing a lecture for this folder. Also follow the repo-wide rules in `/CLAUDE.md` and `learning_system/README.md` (session checklist, privacy).
> Created 2026-11-06 at Timothy's request.

---

## 1. Purpose

Timothy attempts **one** LeetCode (or HackerRank) problem. If it gives him trouble, that's evidence of a **fundamental misunderstanding**, not a one-off slip. He points you at the attempt and says something like *"analyze problem X and generate the lecture."* You:

1. analyze **that attempt** (his code and his comments) to find his shortcomings and logical gaps;
2. trace each gap to the **general concept** behind it (one level up from the problem);
3. write **one lecture per problem** that clears up those general concepts, using the problem as the running example.

The loop is **problem → analysis → lecture → next problem**. Each lecture is named after a problem, but its content is the general concepts the problem exposed.

### How this differs from neighbouring folders

| Folder | Trigger | Scope |
|---|---|---|
| `../` (gradient lectures, `NNN-topic.md`) | "next gradient" / a topic request | a whole topic, taught before he practises it |
| `../attempt_reviews/` | "review my recent attempts" | a **batch** of practice-queue attempts, focused on fluency/speed/confidence |
| `../recaps/` | his explain-back of a lecture he read | gaps from the recall, appended weekly |
| **`problem_deep_dives/`** (here) | "analyze problem X and generate the lecture" | **one** problem he struggled with; the **root misunderstandings** it revealed, taught in depth |

If he asks for a review of several problems, that's `attempt_reviews/`. If he names a single problem for this process, it's here.

---

## 2. Before you analyze: read these

1. **His attempt.** Usually in `../examples.py` or `../001_practice_medium.py` (find it with `GIT_OPTIONAL_LOCKS=0 git log`/`git diff` on those files, or by the date comment above it). Sometimes it's pasted in the message, or the write-up *is* the message (no code). Read **every comment**: he writes his reasoning on purpose so you can see where it breaks.
2. `../private/000-weakness_tracker.md` (weaknesses W1–W20+, bug tags, problem log) and `../private/001-leetcode_profile_and_assessment.md` (root causes R1–R9).
3. `learning_system/private/learner_profile.md` (§2, §7, §7a) and the last ~10 rows of `learning_system/private/observation_log.md`.
4. `learning_system/private/clicks_log.md` (patterns P1–P10: the explanation shapes that work for him).
5. `learning_system/lecture_standards.md`.
6. This folder's `README.md` index, plus `../attempt_reviews/README.md` and the latest `../recaps/` file: **link to what's already been taught instead of repeating it**, unless this attempt shows it didn't land (then say so and teach it differently).

---

## 3. The analysis procedure

Do all of this before writing a word of the lecture.

1. **Restate the problem** in full (paraphrased statement, examples, constraints). If it's from HackerRank or his file only has part of it, reconstruct it and say so.
2. **Run his code exactly as written** (copy it to the scratchpad; never edit his files). Note syntax errors, crashes, infinite loops.
3. **Compare it with a brute-force reference** on a few thousand small random inputs. Record the pass rate and the **smallest failing input**.
4. **Trace that smallest failing input** with a lecture-003-style table to find the **first wrong row**. That row is the bug's location; his comment near it is usually the gap's location.
5. **List every gap**, from his code *and* his comments, and classify each one:

   | Class | Meaning | Example |
   |---|---|---|
   | ❌ wrong model | he believes something false | "`i - m + 1` is the box to kick out" |
   | 🟡 right but unsure / slow | correct, but reasoned for a long time or doubted it | `i + 9 < len(s)` "doesn't feel right" |
   | ⚪ missing tool | no method for a step (no way to trace linked lists, no brute force) | "I don't know how to walk through this" |
   | 🔤 slip | typo, wrong variable (`d` for `m`), `-+` | |

   Tag each with the tracker's bug tags (`CONVENTION`, `TAIL`, `ALIAS`, `VERIFY`, …).
6. **Trace each ❌/⚪ gap to its root**: the general concept one level up that, once fixed, makes the leaf obvious (e.g. "box vs cut", "what a number stands for", "an invariant that holds after every step", "greedy needs a counterexample test"). Several leaves often share one root; group them.
7. **Note his strengths in this attempt** (briefly): the ideas he had right, the checks he did. They go in §0 of the lecture and in the tracker.
8. **Decide what he'll do next with this problem.** If he says he'll retry it, the full solution goes in a collapsed `<details>` block, and the lecture must not give the fix away in the main text (hint with a failing input instead).

---

## 4. The lecture

### 4.1 File name and numbering

`NNN-<problem number>_<problem_slug>.md`, numbered in order of creation, e.g. `001-0643_maximum_average_subarray_i.md`. Use 4-digit LeetCode numbers; for HackerRank use the slug only (`002-hr_birthday_chocolate.md`). If the same problem comes back later with new gaps, it gets a **new** number (`…_retry2`), not an edit.

### 4.2 Required structure

```
# Deep Dive NNN: <Problem name> (<number>): <the root concept(s) in a few words>

> For / Date / Source (where the attempt lives, its date) / Status (attempted, failed, retry planned?)
> Why this lecture: one paragraph, in his words where possible.
> Format notes + verification line (what was run, on how many inputs).

## Core ideas (the answer key)          ← 5–10 lines; the recall answer key
## Table of Contents
## 0. What your attempt showed          ← table: what you wrote | what's right | what tripped you up; strengths first, briefly
## 1. The problem                       ← full paraphrased statement, examples, constraints
## 2. Your attempt, run                 ← what it outputs, the smallest failing input, the first wrong row of the trace
## 3…K. One section per ROOT concept    ← root first, then how it shows up in this problem (the leaf), then 1–2 other places it shows up
## K+1. A solution, derived step by step   ← in <details> if he plans to retry
## K+2. Where else these gaps will bite  ← 3–5 other problems (full statements) that test the same roots
## Drills                               ← numbers first; answers in <details>
## Self-check questions                 ← answers in <details>
## Sources                              ← problems, docs, and the verification note (dated)
```

### 4.3 How to teach in these lectures

- **One canonical model per skill**, with any other framing presented explicitly as a *translation* of it. (Oct 31 lesson: four framings at once competed under pressure.)
- **Numbers before symbols.** Start each derivation with a concrete small array or list (6 boxes, `m = 3`), read the pattern off a table, then write the formula, then two-point check it (two different values, never just one).
- **Name what every symbol stands for before using it** (box or cut? index, count, or steps?). Write state as a table: name | stands for | valid set.
- **Derive, never "by convention."** Every `+1`, every `<` vs `<=`, every sort key, every loop bound gets a numbered derivation.
- **Use his own words.** Quote his comments (briefly) when showing where the reasoning turned; answer the questions he wrote in comments.
- **Full problem statements**, paraphrased (never verbatim from LeetCode). Python only. No firmware analogies, no personified characters.
- **Scope:** only the gaps this attempt evidences. A topic he got right gets one line in §0, not a section.
- **Run every code block**, compare it with a brute force on random inputs, and produce every trace by running the code. Say so in the verification line.

### 4.4 Privacy (this repo is public)

The lecture can describe what his **code and comments** did (that's the material), in neutral, constructive language. Candid evaluation (confidence, frustration, patterns over time, root-cause labels like R1–R9) goes only in `../private/` and `learning_system/private/`. Never reference private file paths or their contents in this folder.

---

## 5. After writing: update everything

1. **This folder's `README.md` index:** a new row (number, problem, date attempted, root concepts, retry status).
2. **`../000-practice_queue.md`:** add the attempt to the Attempt log; update the problem's status in the full list; add the "where else" problems to the full list; re-rank "Pick one now" if the gaps warrant it (keep that table titles-only, reasons in the collapsed block).
3. **`../private/000-weakness_tracker.md`:** a Problem log row (bug tags, what it shows); update the evidence/status of each weakness touched; add a new weakness ID if a new root appeared; re-rank "Current targets."
4. **`learning_system/private/observation_log.md`:** a dated row (what he asked, what the attempt revealed, teaching implication).
5. **`learning_system/private/reading_status.md`:** add the lecture as 📄 generated.
6. **`learning_system/private/clicks_log.md`:** only if he reports something clicking, or surfaces a self-discovered gap worth tracking.
7. **`../000-gradient_roadmap.md`:** only if the gap means a gradient lecture should move up or be added.
8. Commit nothing yourself unless asked; he commits.

### When he retries the problem

- Don't edit the deep dive (he's read it). Record the retry in the README index (status column) and in the tracker.
- If the retry passes cleanly: mark the roots as improving in the tracker.
- If it exposes **new** gaps: write a new deep dive with a new number.
- If it shows the **same** gap again: the lecture's explanation didn't work. Log that in `learning_system/private/technique_experiments.md` and teach it a different way in the next lecture.

---

## 6. Reply to Timothy (in chat)

Short: the file name, the 2–4 root gaps in plain words, the single most important idea, and what to do next (retry? which transfer problem?). Don't paste the lecture into the chat.
