# Suggested global documents (outlines only)

> **Status:** proposal, 2026-11-12. Nothing here replaces anything yet.
> **What's in this folder:** one file per proposed global document, named as it would be named at the top level (two exceptions: `root_CLAUDE.md` and `learning_system_README.md`, renamed so they are not picked up as live instructions or confused with this README). Each holds an outline of what the document would contain and where that content would come from. None of them has real content, so the structure can change before anything is rewritten.
> **Step 2 (later):** agree on the structure, then fill each one from the current docs, check for outdated information, and move it out of this folder.

---

## 1. The idea

The global layer answers five questions, with one document for each. Today the same answers are spread over several files (for example, "how to teach me" is written down in five places).

| Question | Proposed document | Who updates it | How often it changes |
|---|---|---|---|
| Where does an AI start? | [`CLAUDE.md`](root_CLAUDE.md) | AI, when a project is added | rarely |
| Who am I and where am I going? | [`persona.md`](persona.md) | AI proposes, you approve | major changes only |
| How do I learn? | [`learning_style.md`](learning_style.md) | AI, from evidence | after any session that shows something general |
| Where do I stand across everything? | [`where_i_stand.md`](where_i_stand.md) | AI, from project trackers | when a project's status changes |
| How does the system work? | [`learning_system/README.md`](learning_system_README.md) | AI, when the system changes | rarely |

Everything specific to one subject (detailed gaps, plans, material) moves down into that project's own folder, in the shape described in `ai_reuseable_components/prompts/setup_targeted_learning_system.md`.

## 2. Where current content would go

| Current file | Proposed |
|---|---|
| `CLAUDE.md` (top half: pointers and non-negotiables) | `CLAUDE.md`, as a short router with a project index |
| `CLAUDE.md` (bottom half: "two folders", `open_source`, `project_ideas` conventions) | `README.md`, and a charter inside each of those folders |
| `persona.md`: mission, background, career objective | `persona.md` (much shorter) |
| `persona.md`: learning style, teaching style, documentation preferences, expectations, AI's observations | `learning_style.md` |
| `persona.md`: confidence map, weaknesses, learning priorities, active projects | `where_i_stand.md` and project trackers |
| `where_i_stand.md` §0–§2, §4–§6, §8 | `where_i_stand.md`, as a rollup with one row per project |
| `where_i_stand.md` §3 (detailed gap tables) | each project's `ai_notes/understanding.md` |
| `where_i_stand.md` §7 (how I learn best) | `learning_style.md` |
| `learning_system/README.md` | rewritten around the general loop and the standard project shape |
| `learning_system/private/learner_profile.md`, `clicks_log.md`, `technique_experiments.md` | `learning_style.md` (see decision 1) |
| `learning_system/private/observation_log.md` | stays: the raw evidence behind `learning_style.md` |
| `learning_system/private/reading_status.md`, `private/understanding/*.md` | split into each project's AI notes (see decision 4) |
| `learning_system/learning_plan.md` | stays, possibly renamed (see decision 3) |
| `lecture_standards.md`, `audio_lecture_standards.md` | stay as they are |
| `recall_protocol.md`, `clarifications_protocol.md` | stay, or merge into one talk-through protocol (see decision 2) |

## 3. Decisions for you

1. **Private or public notes about how you learn.** Your notes say you're no longer worried about looking incompetent. Today the candid material is git-ignored (`learning_system/private/`, `lectures/leetcode/private/`), which also means it exists only on your Mac. Options: (a) keep the split as it is; (b) make everything public except motivation and emotion notes; (c) make everything public. The outlines assume (b). The setup prompt takes this as a per-project setting and defaults to private, because publishing can't be undone.
2. **What happens to `lectures/clarifications/`.** The session prompt now does per-project talk-throughs, which is what clarifications did across all topics. Options: keep it as the project for talk-throughs that span several subjects, or retire it and route each talk-through to its own project. If it stays, `recall_protocol.md` and `clarifications_protocol.md` could merge into one protocol, since they share the claim map and differ only in whether there's an answer key.
3. **A `000-` doc at the top level.** `learning_system/learning_plan.md` is the global "what should I work on" document. Under your rule that `000-` docs are the mutable ones written for you, it could become `000-learning_plan.md` at the repo root.
4. **One reading-status file or one per project.** `reading_status.md` is 34 KB and covers every domain. Per-project trackers would be smaller and would travel with the project. The cost is a one-time split.
5. **The three docs in the claude.ai project** (`claude/where-i-stand.md`, `claude/learning-plan.md`, `claude/learning-system.md`). The first two are full copies that drift: the repo's `where_i_stand.md` was edited on Nov 10 and the copy is from Nov 7. Options: keep only the short pointer doc, or have sessions re-sync the copies whenever the repo files change.
6. **Run the setup prompt on existing folders?** `lectures/leetcode/` and `lectures/windows_os/` have no charter at their top level. LeetCode's instructions are spread over the weakness tracker's header, `problem_deep_dives/CLAUDE.md`, `attempt_reviews/README.md` and `lecture_standards.md` §1. Running the setup prompt on them in "adopt" mode would add a charter that maps the existing files without moving anything.

## 4. Things that look out of date (confirm in step 2)

- **`persona.md`** was last rewritten on 2026-09-25.
  - Its mission is "backend and infrastructure" with .NET as the chosen specialty. `where_i_stand.md` (November) gives the target as systems / platform roles (Windows platform, devices, drivers).
  - "Active Projects" describes LLM_Monitor as in progress. `where_i_stand.md` lists it as parked.
  - The "Fears" section and weakness 4 ("Hidden basic gaps… could badly damage credibility") may no longer describe how you feel.
  - "Learning Style" still asks "who are the characters?" and "Documentation Preferences" still lists analogies. Personified characters and firmware analogies were retired on 2026-10-04.
- **`CLAUDE.md`** (bottom half) says the repo has two folders. It now also has `learning_system/`, `examples/`, `ai_reuseable_components/` and `suggested_global/`.
- **`where_i_stand.md`** (13 lines) and **`learning_plan.md`** (9 lines) point to `windows_internals/…`. That folder is now `lectures/windows_os/lectures/`.
- **`learning_system/recall_protocol.md`** §3 still suggests "a firmware twin if it helps", and §4 uses the personified cast as its example of a technique.
- **`learning_system/private/learner_profile.md`**: the header still says there have been no recall checks yet. Six are on file.
- **`learning_system/private/misconceptions/`** is an empty folder left over from the rename to clarifications.

## 5. What changes in the two prompts if this is adopted

Both prompts were written against today's files so they work now. Only their "get oriented" steps name global files:

- `start_learning_session.md` §1 (the read list) and §4 ("Global files").
- `setup_targeted_learning_system.md` §2 ("Orient"), §4 (where existing evidence lives) and §5 (connecting to the global layer).

Once the new `CLAUDE.md` is a router with a "read order by task" table, those steps can shrink to "read the root `CLAUDE.md` and follow it", and the prompts won't need editing again when files move.
