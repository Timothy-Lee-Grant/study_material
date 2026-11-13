# Prompt: set up a targeted learning project

> **For Timothy. What this is:** paste this to have an AI agent create (or repair) a learning project in the Studying_Lectures repo. The prompt carries the shape of the system and how I'll use it, so the only thing to write each time is the project itself.
> **How to use:** fill in "This project", then paste everything below the line into a session that has the repo folder connected and can write files.
> **Safe to re-run:** on a project that already exists, it fills in what's missing and reports back. It doesn't overwrite.
> **After setup:** start each talk-through thread with `start_learning_session.md`.
> **Last updated:** 2026-11-12

---

## This project

Stream of consciousness is fine here. The first three matter most.

- **NAME / FOLDER:** `<e.g. concurrency → lectures/concurrency/>`
- **GOAL** (what I want to be able to do):
- **THE BAR** (how we'll both know I'm there):
- **WHY NOW / DEADLINE (optional):**
- **WHERE I AM NOW:** `<what I already know, what I've tried, material that already exists>`
- **HOW I'LL SHOW YOU WHERE I AM:** `<e.g. talk-throughs on walks · problem attempts with my reasoning in comments · lab results · questions>`
- **WHAT MATERIAL HELPS HERE:** `<e.g. lectures only · lectures + worked walkthroughs · practice problems · labs · audio>`
- **AI NOTES:** `private` (git-ignored) or `public`. Default if blank: private.
- **ANYTHING ELSE:**

## What I'm asking for

I'm Timothy. Set up the project described above as a **targeted learning project** in my Studying_Lectures repo: create the folder, the documents and the starting state, so that from now on I can open a chat, talk about what I understand, and have the project keep track of where I am and what I should do next.

Don't write any lectures or other study material during setup. Build the structure, then propose the first piece and wait.

## 1. The system this project plugs into

Every project runs the same feedback loop:

```
 I show you where I am ──► you analyze it ──► you update what you know about me
        ▲                                                  │
        │                                                  ▼
 I study and practise ◄── you tell me what to do next and prepare material for it
```

The specifics change from project to project (what I give as input, what kind of material helps), and the loop stays the same. `lectures/leetcode/` is where this was worked out: I attempt problems with my reasoning in comments, the AI finds what I'm weak on, keeps a prioritized plan, and writes lectures aimed at those weaknesses. `lectures/windows_os/` is a different shape: lectures, walkthroughs and labs, with talk-throughs as the main input. Read both to see the pattern. Don't copy their specifics.

**Two layers:**

| Layer | Lives in | Holds | This setup |
|---|---|---|---|
| Global | repo root, `learning_system/` | who I am, my goals, how I learn, how the system works | reads it; adds one pointer to this project; doesn't restructure it |
| Project | `lectures/<project>/` | this project's goal and bar, where I am in detail, the plan, the material | creates it |

**Four kinds of document.** Every file in a project is one of these, and the kind decides who it's for and whether it may change:

| Kind | For | May it change? | Examples |
|---|---|---|---|
| **`000-` docs** | me | Yes. Rewritten in place, kept short | roadmap, next steps, practice queue |
| **AI notes** | you, and any later AI session | Yes, after every session | charter, understanding tracker, session log, teaching notes |
| **Material** | me | Not after I've read it. Fixes go into future material | lectures, walkthroughs, deep dives |
| **Intakes** | the record | Never. Kept as I said it | talk-through transcripts |

## 2. Before creating anything

**Orient.** Read the root `CLAUDE.md` and what it points to (today: `learning_system/README.md`, `learning_system/lecture_standards.md`, `learning_system/private/learner_profile.md`, `where_i_stand.md`, `persona.md`). If you can't read or write the repo, say so and stop.

**Check what already exists** at `lectures/<project>/`, and pick the case:

| Case | What you find | What to do |
|---|---|---|
| **New** | no folder | Create everything in section 3 |
| **Adopt** | a folder with material but no charter (`CLAUDE.md` with a goal and a file map) | Take an inventory. In the charter's file map, point each role at the existing file that already fills it (an existing roadmap stays where it is). Create only the roles that are missing. Don't rename, move, renumber or edit existing files; list any renames you'd suggest separately, for me to decide |
| **Already set up** | a charter exists | Check the project against section 3, create what's missing, and report. If my description above changes the goal or the bar, update the charter and its changelog and tell me. Otherwise change nothing |

In every case: never overwrite a file that has content, and never delete anything.

**Ask only if you have to.** The goal and the bar can't be guessed. If either is missing or too vague to rank work against, ask me (three questions at most) before creating files. For everything else, choose a sensible default and list it under "Assumptions" in your report.

## 3. The shape to create

**Core (every project):**

```
lectures/<project>/
├── CLAUDE.md              AI notes   the charter: instructions for any AI working here
├── README.md              for people what this folder is, how its loop works, index of material
├── 000-roadmap.md         000- doc   where this is going and in what order
├── 000-next_steps.md      000- doc   what to do now
├── NNN-title.md           material   numbered from 001 in order of creation (none yet)
├── intakes/               intakes    YYYY-MM-DD_topic.md, one per talk-through
└── ai_notes/
    ├── understanding.md   AI notes   where I am, concept by concept, with evidence
    ├── session_log.md     AI notes   one dated entry per session
    └── teaching_notes.md  AI notes   what works for me in this subject; ideas for future material
```

**Optional modules.** Create one only when my description calls for it. No empty folders "in case":

| If the project has… | Add |
|---|---|
| practice problems or exercises | `000-practice_queue.md` (a pick-one list plus an attempt log), and `deep_dives/` for one-problem analyses |
| worked scenarios | `walkthroughs/` |
| hands-on labs | `labs/` with a `lab_progress.md` |
| audio lectures | `audio/` (see `learning_system/audio_lecture_standards.md`) |
| code that goes with the material | `code/` |

**Visibility.** The repo is public. If AI NOTES is private (or blank), add `lectures/<project>/ai_notes/` and `lectures/<project>/intakes/` to `.gitignore`. If it's public, the notes can still be candid, because I'm not worried about looking incompetent. In both cases, no employer, product or interview details in any file.

### What goes in each core file

**`CLAUDE.md`, the charter.** Under about 150 lines. A new AI session should be able to read this one file and know how to work here.

1. **Goal:** one paragraph, in my words.
2. **The bar:** "done means…", as things I can be observed doing.
3. **Scope:** what's in, and what's out. This is what keeps sessions from drifting when I meander.
4. **Shape:** the kinds of input I'll give, and the kinds of material this project uses.
5. **The loop here:** for each input kind, what you do and which files change.
6. **File map:** role → path (charter, tracker, session log, teaching notes, intakes, each `000-` doc, material, optional modules), plus the visibility setting. Session prompts depend on this table, so keep it exact.
7. **Project rules:** anything specific to this subject (language, tools, sources, conventions).
8. **Changelog.**

**`README.md`.** Short and human-facing: what the folder is for, how I use it, and an index table of material that grows over time.

**`000-roadmap.md`.** The goal and the bar in two lines. Then a concept map: the concepts and skills the goal needs, each with a status and the material that covers it (or "none yet"). Then the order to take them in and why: the biggest current weakness that unlocks the most comes first. Then what's done, and what would change the order.

**`000-next_steps.md`.** The file I open when I have time and want to know what to do. "Do this now": the top 1–5 actions, most useful first, one line each. Questions to answer out loud on my next walk. Proposed material that isn't written yet. Recently resolved. Keep it to about one screen.

**`ai_notes/understanding.md`.** The status legend the repo already uses (🟢 solid · 🟡 partial · 🔴 active gap · ⚪ not shown yet · ✔️ resolved). Current targets (top 3). A concept table: concept | status | last evidence (date, my words) | what's missing or wrong | root concept. Open roots, in priority order. Resolved. A parking lot for things outside the goal.

**`ai_notes/session_log.md`.** Append-only. Per entry: date, what the input was, what it covered, what changed, files touched. Summarize older entries when it gets long.

**`ai_notes/teaching_notes.md`.** Explanations that clicked in this subject and ones that didn't; open items to weave into future material; ideas for material. Observations that would hold in *any* subject don't go here. They go in the global learner files.

## 4. Seed the starting state

- **Evidence only.** Fill the tracker from what I wrote above, from `where_i_stand.md`, and from existing trackers that cover this subject (`learning_system/private/understanding/`, `learning_system/private/reading_status.md`, an older tracker inside the folder). Everything else starts at ⚪ not shown yet.
- **Material that exists is not evidence.** A lecture counts for something only if I've said I read it or I've explained it back.
- **Build the first concept map from the goal.** Work backward from the bar to the concepts and skills it needs. Then put my current state on that map.
- **Write the first `000-next_steps.md`** with one to three concrete actions. If I've given you nothing to assess yet, the first action is a baseline: a talk-through or an attempt that shows you where I am.

## 5. Connect it to the global layer

Make these changes and no others:

1. Add one line to the root `CLAUDE.md` pointer list: for work in `lectures/<project>/`, read its `CLAUDE.md` first.
2. Add the project to `where_i_stand.md` per its §8, if it isn't there already.
3. Add the `.gitignore` lines, if the notes are private.
4. Log the setup the way `learning_system/README.md` §3 describes.

Don't reorganize, rename or rewrite any global document. If something there looks out of date or contradicts what I described, tell me in the report.

## 6. Report back

Keep it short:

1. **The tree,** with each file marked *created*, *already existed* or *skipped*.
2. **Assumptions** you made, and anything in the global docs that looked out of date.
3. **The goal and the bar** as you wrote them into the charter, so I can correct them.
4. **The first step** from `000-next_steps.md`, and the first piece of material you'd propose.
5. **How to start a session:** *"Follow `ai_reuseable_components/prompts/start_learning_session.md`. PROJECT: <project>."*
