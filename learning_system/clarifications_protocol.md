# Clarifications Protocol — free-form talk-throughs → log → clarification lecture

> Read this before handling a **talk-through intake** (Mode D in `README.md`) or generating a lecture in `lectures/clarifications/`.
> **Created:** 2026-11-04, at Timothy's request. Renamed from "misconceptions" the same day (his call: the word felt negative). Everything here is public by his choice: everyone has fuzzy spots, and clearing them up in the open is the point.
> **Why this exists:** Timothy learns by talking through what he *thinks* is true, often by voice on a walk, across many unrelated topics. Unlike a recall check, there's no lecture behind the talk-through and no answer key. The goal is to catch fuzzy or wrong mental models, find the **higher-order concept** each one comes from, and clean them up in a periodic lecture. His own observation: once the root misunderstanding is fixed, the problems that grew out of it become trivially easy. So the lecture fixes roots, not leaves.

---

## 1. The files (all public, in `lectures/clarifications/`)

| File | What it is |
|---|---|
| `README.md` | What the folder is, how the loop works, index of lectures |
| `log.md` | The running log: §1 lecture plan (the queue), §2 intake log (claim maps), §3 what each lecture covered |
| `intakes/YYYY-MM-DD_topic.md` | One file per talk-through: the transcript as spoken |
| `NNN-title.md` | The clarification lectures (format in §4) |

**Public-safe, still:** no employer, product, interview or job-application references (his standing rule; replace such clauses in a transcript with `[…]`). Notes about *how he learns* (patterns, motivation, calibration) go to `learning_system/private/` (observation log, trackers), not here. The log records claims and concepts, neutrally.

## 2. Handling an intake (Mode D)

**Signal:** he pastes a stream-of-consciousness explanation and says it's for the clarifications folder (or describes "talking about my understanding" without naming a lecture he read). If it's about a lecture he read, it's a recall check (Mode C) instead. If unclear, ask.

1. **Save the transcript** in `lectures/clarifications/intakes/` (as spoken, minus any work/interview references).
2. **Read for intended meaning.** Voice-to-text mishears; use the table in `recall_protocol.md` §1 and add new ones.
3. **Claim map** in `lectures/clarifications/log.md` §2, using the same marks as `recall_protocol.md` (✅ 🟡 ❌ ❓ 💡). Group claims by topic. For ❓, record whether the doubt was justified.
4. **Find the root.** For each ❌/🟡/❓, ask: *which higher-order concept, if he had it, would make this obvious?* Write that root as one sentence. Several leaves usually share one root; that's the point.
5. **Update the plan** (`log.md` §1): add or merge into topic groups. Each group lists its root concept, the leaves (with intake dates), and a priority. Foundational roots that other groups depend on go first.
6. **Cross-reference the domain trackers** in `private/understanding/`. If a claim is about a tracked concept, update that tracker row too (same evidence, one line). Learning-pattern observations go there and in the observation log, not in the public log.
7. **Reply briefly (under ~250 words):** the topics logged, the 2–4 root concepts queued, and anything he flagged as a doubt that's a quick one-liner to unblock him. **Don't write the full corrections in the reply.** That's the lecture's job, and he asked to batch it. Correct something immediately only if it would actively mislead his current work or interviews, or if he asks.
8. Append a row to `private/observation_log.md`.

**Never "fix" an intake by editing existing lectures.** Same rule as recall checks.

## 3. When he asks for the lecture

Trigger: "generate a lecture" in this context ("generate the clarifications lecture", "make the next clarification doc").

1. Read `log.md` §1 (the plan) and §3 (what's already been covered).
2. Take every open group (or the highest-priority ones if it would exceed ~1,200 lines; say what was deferred).
3. Research present-day facts as usual (`lecture_standards.md` §4).
4. Write the lecture (§4), add it to the folder README index and to `private/reading_status.md` (📄 generated).
5. In `log.md`: move covered leaves to §3 with the lecture number, keep anything not covered in §1.
6. Mark leaves **resolved** only later, from his own words (a new intake, recall check, or question), never because a lecture was written.

## 4. Clarification lecture format

Breadth over depth. Clear the confusion, give one layer of context above it, and stop. Not a full treatment of any topic.

```
# Clarifications NNN — <short theme>
> For / Date / Built from: talk-throughs of <dates> / How to read: sections are independent; read any order

## Core ideas (the answer key)      ← REQUIRED: one line per root concept fixed
## Topic map                        ← a small table: section → root concept → which of your questions it settles
## 1…N. One section per topic group (unrelated groups stay separate; related groups go next to each other)
   ### The root (one layer up)       ← the higher-order concept, taught directly and briefly
   ### What you said → what's true  ← table: your model (paraphrased, neutral) | what's actually true | why it matters
   ### Your questions, answered      ← his ❓ items, short direct answers
   ### What this makes easy          ← 2–4 things that should now feel obvious (the payoff)
   ### Quick check                   ← 1–3 questions, hidden answers
## What you got right                ← his ✅ and 💡 items, briefly (he builds on confirmed ground)
## Self-check (mixed)                ← a few questions mixing topics (interleaving)
## Sources (dated)
```

Rules:
- **Root first, then leaves.** Each section opens with the higher-order concept, then shows how each of his leaves follows from it.
- **Confirm what's right** before correcting. His self-derived models are often mostly right; say so specifically.
- **Neutral, public-safe paraphrase** of what he said. No quotes of the transcript, no evaluative language about him (the transcript itself is public in `intakes/`, so link it rather than quote at length), no employer or interview references.
- Use the standing techniques in `lecture_standards.md` (top-down, layer stack, named actors, no firmware analogies, no personified characters, small numbered derivations, honest sizing, black-box tags when something isn't worth digging into).
- Sections should stay short: a root paragraph or two, a table, short answers. If a topic needs a real lecture, say so and suggest one in the normal domain folder instead.
