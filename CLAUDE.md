# FOR AI ASSISTANTS: read `learning_system/README.md` first

This repo runs a **self-improving learning system**. Before generating a lecture or answering a learning question:

1. Read `learning_system/README.md` (how the system works, the three interaction modes, session checklists).
2. Read `learning_system/private/learner_profile.md` and the latest rows of `learning_system/private/observation_log.md` (git-ignored; exists only on Timothy's machine).
3. Before writing a lecture, read `learning_system/lecture_standards.md`. Before responding to any summary Timothy gives (often a voice transcript from a walk), read `learning_system/recall_protocol.md`.

Non-negotiables:
- **Never assume Timothy has read a lecture because it was generated.** He'll say explicitly when he's read something or wants to summarize it.
- **After every substantive interaction**, append evidence to the observation log and update `private/reading_status.md`.
- **Privacy:** this repo is public. Evaluations of Timothy live only in `learning_system/private/` and `lectures/open_source/private/`. Never quote them in public files.
- **Git in agent sessions:** these sessions can't delete files, so use `GIT_OPTIONAL_LOCKS=0 git status` (plain `git status` can leave a stale `.git/index.lock`).

---

The purpose of this project is for me to have a centralized location where I am able to keep lecture notes which were generated during the creation of my other projects, which I’m currently building. I am trying to have a place where I can go through things and be able to really dive into The different concepts found within my projects. 

Within this repo there are two folders.

# lectures

This folder is where I directly copy and paste the lecture notes which I generate inside of my other projects. Each of the sub folders here is a specific project which I have been building and playing around with.

Some sub folders here are **knowledge domains** rather than projects (for example `carreer_path`, `firmware`). These hold lectures about a subject area rather than about a specific codebase. If I ask you to teach me a domain that isn't tied to one of my projects, create or use a domain sub folder here rather than putting it in `project_ideas` — `project_ideas` is only for lectures about projects I want to build. Use the same `(Number)-(title).md` naming convention described below.

## lectures/open_source (open-source home base)

`lectures/open_source/` is different from the other domain folders. It's my working home base for contributing to open-source projects, with this structure:

- `open_source_persona.md`: my contributor profile (strengths, how issues are chosen, dev environment, study log). **Read it before suggesting issues or plans.** It must stay public-safe and strengths-forward.
- `implementations/`: actionable documents such as issue shortlists, with concrete steps, status labels (🟢/🟡/⚫, 🛠️ Contribute / 📖 Learn), and progress trackers. Named `(Number)-(title).md`.
- `concept_notes/`: **short, issue-focused concept explanations** that answer my questions while I work through an implementation document. Each note gives just enough understanding to unblock the next step, plus next steps. **These are not full lectures.** Deep, comprehensive lectures belong in the regular domain folders under `lectures/`. When I ask a question about an issue, append it to the current Q&A file (e.g., `001-questions_from_the_issue_shortlist.md`) and update its index.
- `private/`: git-ignored. Candid observations about me that I copy to a private repo. Never reference its contents in public files.

# project_ideas 

Within this folder, this is where I will have you go and actually generate more documentation. The idea with this folder is I will be able to describe the general idea of a project which I’m having and I want you to go and create a full lecture document outlining all of the important concepts, which I will need to have an understanding of to be able to start implementing this project.

Documents here should be named 

(Number)-(title).md
001-example_title.md

For these documents, you can refer to my `persona.md` (in the repo root) to get an understanding of who I am, my goals, and my current strengths / weaknesses.