# OUTLINE ONLY: `learning_system/README.md`

> **Not real content.** This is the proposed structure for `learning_system/README.md`. See `README.md` in this folder. (Named `learning_system_README.md` here so it doesn't collide with this folder's own README.)

**Purpose:** the operating manual: how the learning system works in general, for any project. Today's version describes the lecture-and-recall loop specifically; this one describes the general loop that the LeetCode folder, the talk-throughs and the labs all share.
**Updated by:** the AI, when the system itself changes. Rare.

## Proposed sections

1. **The loop.** Input (evidence of where I am) → analysis → state → next steps and material → I study → input. One diagram, and one paragraph on why it works.
2. **Two layers.** What lives globally and what lives in a project, and which direction updates flow: project evidence feeds the global learning style; the global layer shapes how each project teaches.
3. **Four kinds of document.** `000-` docs (for me, mutable), AI notes (for the AI, mutable), material (immutable once read), intakes (kept as spoken).
4. **The standard project shape.** The core files and the optional modules, matching `setup_targeted_learning_system.md`. A note on keeping the two in sync.
5. **Kinds of input and what each one triggers.** Replaces today's modes A–D with one table: talk-through tied to material I read; free talk-through; attempt at a problem; lab result; question; "what's next?". For each: how to analyze it, which files change, and how long the reply is.
6. **What updates what.** A table: kind of evidence → project tracker / `000-` docs / `learning_style.md` / `where_i_stand.md` / `persona.md`.
7. **Session checklist.** Start and end of a session.
8. **How the system improves itself.** Consolidation points, technique experiments, and telling me what changed.
9. **Stance.** Educator, learning psychologist, senior engineer mentor. Candid; not worried about looking incompetent.
10. **Index.** The standards and protocols (lecture standards, audio standards, talk-through protocol) and the reusable prompts.

## Comes from

- Current `learning_system/README.md` §1–§5.
- The general rules now repeated in `recall_protocol.md`, `clarifications_protocol.md` and `lectures/leetcode/problem_deep_dives/CLAUDE.md` (claim map, roots over leaves, never edit read material).

## To confirm with Timothy before writing

- Decision 2 in the README: merge the recall and clarifications protocols into one talk-through protocol?
- Decision 4: reading status as one global file or one per project?
