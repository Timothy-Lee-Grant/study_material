# OUTLINE ONLY: `CLAUDE.md` (repo root)

> **Not real content.** This is the proposed structure for the root `CLAUDE.md`. See `README.md` in this folder. (Named `root_CLAUDE.md` here so no AI session loads it as live instructions.)

**Purpose:** the first file any AI session reads. A router: it says what the repo is, how it's organized, and what to read for the task at hand. It holds no teaching rules of its own.
**Target length:** about 60 lines.
**Updated by:** the AI, when a project is added or a global file moves.

## Proposed sections

1. **What this repo is.** Three lines: a learning system plus the material it has produced; public.
2. **How it's organized.** The two layers (global / project) and the four kinds of document (`000-` docs, AI notes, material, intakes), as one small table each.
3. **What to read, by task.** A table: task → files to read, in order. Rows for: a talk-through or other input for a project; writing a lecture; "what should I work on?"; setting up a project; anything in `open_source/` or `project_ideas/`.
4. **Project index.** A table: project | charter path | goal in one line | active or parked. The setup prompt adds a row here.
5. **Non-negotiables.** Never assume something was read because it was generated. Never edit material that's been read. Statuses change on evidence only. The privacy rule (whatever decision 1 settles). The git-lock note for agent sessions.
6. **Reusable prompts.** A pointer to `ai_reuseable_components/prompts/`.

## Comes from

- The top half of the current `CLAUDE.md` (the numbered pointers and non-negotiables).

## Moves out

- The description of `lectures/`, `project_ideas/` and the naming convention → `README.md`.
- The `lectures/open_source/` rules → a charter inside that folder.
