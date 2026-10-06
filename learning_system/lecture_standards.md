# Lecture Standards — how to write lectures for Timothy

> Read before generating any lecture, together with `private/clicks_log.md` (what has clicked for him, and why). These standards are **evidence-driven**: each technique has a status in `private/technique_experiments.md`. When recall data supports or refutes a technique, update this file and its changelog (§9).
> **Audio lectures** (for NotebookLM podcasts) follow `audio_lecture_standards.md` instead. Use that only when he explicitly asks for an audio/listening lecture.
> Distilled from the lectures written in Sept 2026 (`lectures/dotnet/001–005`, `lectures/carreer_path/003`) and from `persona.md`.

---

## 1. Where lectures go

| Kind | Location | Naming |
|---|---|---|
| Domain lecture (a subject, not a codebase) | `lectures/<domain>/` (e.g. `dotnet`, `carreer_path`, `firmware`) | `NNN-title.md` (match the folder's existing style: underscores in `dotnet`, hyphens in `carreer_path`) |
| Project lecture | `lectures/<project>/` | same |
| Project idea | `project_ideas/` | same |
| Short issue-focused Q&A | `lectures/open_source/concept_notes/` | append to the current Q&A file (see CLAUDE.md) |

When adding a lecture to a folder with a roadmap (e.g. `lectures/dotnet/001` §23), **update the roadmap and the "next lecture" lines** of neighboring lectures.

## 2. Required structure

```
<timestamp line: YYYY_MM_DD_HH_MM-(Title-With-Dashes)>   (dotnet folder convention)
# Lecture NNN — Title: Subtitle
> For / Date / Prerequisites (link earlier lectures by section) / Why this lecture (tie to HIS words and situation)

## Core ideas (the answer key)        ← REQUIRED (new as of 2026-09-29)
   5–12 numbered one-sentence ideas: what he should be able to explain from memory.
   These are the rubric for recall checks (recall_protocol.md). Put them right after the header.

## Table of Contents
## 0. Direct answers / orientation     ← when he asked specific questions, answer them first, briefly
## 1…N. Body, top-down
## Misconceptions / common mistakes
## Interview relevance
## Self-check questions               ← with <details><summary>Answer</summary>…</details>
## Sources                            ← dated ("checked YYYY-MM-DD")
```

## 3. Teaching techniques (current defaults)

| # | Technique | How | Status (see experiments file) |
|---|---|---|---|
| T1 | **Top-down order** | Map → components → contracts → control flow → implementation → edge cases. Never open with code. | Stated preference; untested by recall |
| T2 | ~~Personified cast of characters~~ | **DO NOT USE** (2026-10-04: "I want to avoid… always trying to fit things into characters") | Retired by his explicit request |
| T3 | ~~Firmware twins~~ | **DO NOT USE** as a teaching device (2026-10-04: "I want to avoid analogies with firmware"). Teach concepts directly: definitions, tests, tables, traces of his own code | Retired by his explicit request |
| T4 | **Black-box tags** | 🟢 OWN IT / 🔵 CONTRACT / ⚫ BLACK BOX (for now): explicit permission to stop digging | Designed for his bottom-up instinct; untested |
| T5 | **Altitude discipline** | Show answers at rung 1–6 (purpose → component → contract → flow → implementation → runtime); rung 3 is usually the answer | Addresses a documented weakness; untested |
| T6 | **Direct answers first** | For long multi-part questions, open with short numbered answers, then teach | Seemed to land (he built on the answers in follow-ups); weak evidence |
| T7 | **Honest sizing and caveats** | Say when something is niche, a rabbit hole, or not worth his time, with reasons | **He explicitly asked to keep this** (2026-09-25) |
| T8 | **Decision tables + a recommendation** | When he's weighing options, give a scored table *and* make the call ("you asked me to decide, so here's one") | He delegates decisions when overloaded; untested |
| T9 | **Hands-on lab with predictions** | Small runnable lab; "predict before you run"; results table for him to fill in | He ran the YARP repro (2026-09-27); positive signal |
| T10 | **Self-check with hidden answers** | 10–15 questions with `<details>` answers | Untested |
| T16 | **Name → valid set → membership test** | For any boundary/index/guard: give the quantity a name (`next_pos`, `nr`, `window_start`), write its valid range explicitly, then test membership positively (no `not`). Teach it as a numbered derivation, then verify with an edge plug-in | His reported click (2026-10-05, private/clicks_log.md C1) |
| T17 | **Derivations in small numbered steps** | Show how to *produce* the answer as a sequence of one-transformation steps, not just a rule to remember or a check to run afterwards | Clicks log P4; leetcode/001 tables |
| T15 | **Lectures built from his own attempts** | Run his code, show real outputs and traces, "you thought X → reality Y", then derive the fix | Strong behavioral signal (leetcode/001: 8 → 1 bugs same evening; he said it "really helped") |

## 4. Content rules

- **Research first.** Verify present-day facts (versions, repo locations, defaults, statuses) with web sources before writing, and date them. This area moves fast. Lectures have already caught stale assumptions (AZ-204 retired, YARP docs moved to AspNetCore.Docs).
- **Verify code.** Compile and run if a .NET SDK is available. If not, say so in the lecture honestly, and review for overload ambiguity (e.g. `byte[]` → `ArraySegment` vs `Memory` overloads).
- **Public-safe.** The repo is public. Never include employer names, product names, internal class names, or proprietary architecture. Describe his work at the skill level ("a .NET worker ingesting telemetry via P/Invoke").
- **Correct his mental model explicitly** when a question reveals one. A table "you thought X → reality Y → why" worked well (dotnet/004 §3).
- **Distinguish the layers** (hardware / kernel / library / runtime / framework / app) whenever responsibility is in question. Misplacing responsibility across layers is one of his recurring confusions (see the private profile).
- **Keep work details generic; keep his fears private.** Lectures may reference his public persona, but not private observations.

## 5. Length (open question, under test)

Recent lectures run 600–3,000 lines. There's **no evidence yet** on how much he reads or retains from lectures this long. Until recall data exists:
- Keep the **Core ideas** list short and put it first, so a partial read still delivers the essentials.
- Prefer one focused lecture over a sprawling one. Split into a series if a lecture would exceed ~1,200 lines.
- Revisit this section after the first 3 recall checks (hypothesis H3 in the experiments file).

## 6. After generating a lecture

1. Add it to `private/reading_status.md` with status **generated**.
2. Make sure its **Core ideas** list exists (retrofit older lectures lazily, when a recall check needs them).
3. Update roadmaps and neighboring "next" lines.
4. Log the request itself in `private/observation_log.md` (what he asked for says what he's curious or confused about).

## 7. What NOT to do

- Don't assume he read it. Don't quiz him on it unprompted, beyond one gentle offer when a recall is due.
- Don't revise already-written lectures after recall checks or questions (he's read them). Put improvements into future lectures.
- Don't generate planning documents as a substitute for action. The private notes flag "planning as a comfort zone." When a request looks like more planning before a pending public action, say so, briefly and kindly, and still help.
- Don't oversimplify ("assume I'm willing to learn difficult material"), but don't bury the core either.

## 8. Voice of the lectures

Direct, warm, candid, second person ("you"). Plain English, short sentences, concrete examples. Explain *why* before *how*.

## 9. Changelog

| Date | Change | Evidence |
|---|---|---|
| 2026-10-05 | Added T16 (name → valid set → membership) and T17 (numbered derivations). Before writing any lecture, also read `private/clicks_log.md`. | His first reported click (C1) |
| 2026-10-04 | Retired T2 (personified characters) and T3 (firmware analogies) at Timothy's explicit request. Added T15: build lectures from his own failed attempts (forensics of his code). | His statement 2026-10-04; leetcode/001 → 8→1 bugs same evening |
| 2026-09-29 | Added pointer to audio lecture standards; rule: never revise existing lectures after recall. |
| 2026-09-29 | Created. Added the required **Core ideas** section as the recall answer key. Length marked as an open question. | Codified from Sept 2026 lectures; recall system started |
