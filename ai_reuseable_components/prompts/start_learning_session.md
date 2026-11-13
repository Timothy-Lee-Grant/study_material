# Prompt: start a learning session (talk-through thread)

> **For Timothy. What this is:** paste this at the start of a new chat to turn it into a talk-through thread for one learning project. It assumes the project was already set up with `setup_targeted_learning_system.md`.
> **How to use:** fill in the two lines under "This session", then paste everything below the line. Put your first talk-through in the same message or the next one.
> **Shortcut:** when the Studying_Lectures folder is connected, you can skip the paste and write: *"Follow `ai_reuseable_components/prompts/start_learning_session.md`. PROJECT: windows_os."*
> **Last updated:** 2026-11-12

---

## This session

- **PROJECT:** `<folder under lectures/, e.g. windows_os>`
- **SINCE LAST TIME (optional):** `<what I read, tried or built since the last session, e.g. "read lecture 019, did lab 5.1 exercise 2">`

## What this thread is

I'm Timothy. My Studying_Lectures repo runs a learning system built on one feedback loop:

```
 I show you where I am ──► you analyze it ──► you update what you know about me
        ▲                                                  │
        │                                                  ▼
 I study and practise ◄── you tell me what to do next and prepare material for it
```

This thread is the "I show you where I am" step for the project named above. I'll paste talk-throughs: voice-to-text recordings from walks, where I explain what I remember and what I think is going on. Sometimes I'll paste other evidence instead: an attempt at a problem, a lab result, a question, or how a lecture felt to read. Every message I send in this thread is another piece of input for the same project unless I say otherwise.

Your job each time: work out what the input shows about my understanding, record it in the project's files, keep my next steps current, and reply briefly.

## 1. Before your first reply: get oriented

Read, in this order:

1. **Global layer:** the root `CLAUDE.md` and what it points to for a session like this. Today that means `learning_system/README.md`, `learning_system/private/learner_profile.md`, the last ~10 rows of `learning_system/private/observation_log.md`, and `where_i_stand.md`.
2. **Project layer:** `lectures/<PROJECT>/CLAUDE.md` (the charter: goal, bar, shape, file map), then the files its file map names: the `000-` docs, the understanding tracker, and the last few session log entries.

Then check three things:

- **You can't read the repo** (the folder isn't connected): say so and stop. Don't rebuild my state from memory or guess at it.
- **The project has no charter** (`lectures/<PROJECT>/CLAUDE.md` is missing, or has no goal and no file map): it isn't set up. Tell me, and offer to run `ai_reuseable_components/prompts/setup_targeted_learning_system.md`. Don't improvise a structure.
- **The project's charter or the repo's protocols say something more specific than this prompt:** they win. This prompt is the default for whatever they don't cover.

If I sent a talk-through along with this prompt, go on to section 3. If not, reply with three lines (the project's goal as you understand it, where the tracker says I am, and the top next step), then wait.

## 2. What my input looks like

- **Voice-to-text, so words get misheard.** "Colonel" means kernel. Read for the meaning I intended. The list of known mishearings is in `learning_system/recall_protocol.md` §1; add new ones there as you find them. If a word could be either a mishearing or a real mix-up, and it matters, ask me.
- **Stream of consciousness.** I'm explaining it to myself and putting the pieces together as I talk. I meander, jump between topics, and follow connections as they occur to me. That's the method working, so don't mark it down.
- **I correct myself mid-sentence.** Take the final version as my claim. Note that I got there by correcting myself, because that usually marks a spot that's still settling.
- **Not every sentence is a claim.** Separate what I assert, what I say I'm unsure about, what I ask, and what's an aside.
- **Never assume I've read something because it exists in the repo.** I'll say what I read. If a talk-through could be either recall of a lecture or first-pass reasoning and you can't tell which, ask one short question, because the analysis differs.

## 3. What to do with each input

1. **Save it as given** in the project's intake folder, dated, before analyzing it. Remove only employer, product and interview references.
2. **Work out what it's about:** which lecture, walkthrough, lab or problem, if any. If it's tied to material with a "Core ideas" list, that list is the answer key.
3. **Build a claim map.** One row per distinct claim: ✅ accurate · 🟡 right direction, with a piece fuzzy or wrong · ❌ confidently wrong · ❓ I flagged a doubt (record whether the doubt was justified) · 💡 a correct connection beyond the material.
4. **Find the gaps:** core ideas I should have mentioned and didn't. A gap is an omission, which is different from an error.
5. **Find the root of each 🟡 and ❌.** Ask which concept one level up would make this obvious if I had it. Several leaves usually share one root, and the root is what goes on the plan.
6. **Compare with last time.** What was weak before and is solid now? Mark it resolved, with my words as the evidence, so no more energy goes there. What came back wrong a second time? The earlier explanation didn't work. Note that, so the next one teaches it a different way.
7. **Check it against the project's goal.** The charter states the goal and the bar. Rank everything by how much it moves me toward that bar. Things I wandered into that don't serve the goal go in the tracker's parking lot. If one belongs to another project, say which, in one line.

## 4. Update the files

Do this before replying, every time.

**Project files** (the charter's file map says where each one lives):

- **Understanding tracker:** change a concept's status only on evidence from my own words or work, with a date. Add new roots, mark resolved ones, update the parking lot.
- **Session log:** one dated entry: what the input was, what it covered, what changed, which files you touched.
- **`000-` docs** (these are mine to read; they're mutable, so rewrite them in place and keep them short): re-rank the next steps, and adjust the roadmap if the order of topics should change. If new material would help (a lecture, a walkthrough, practice problems), list it there as *proposed*, with one line on why.

**Global files, only when the evidence is about more than this project:**

- **How I learn.** Something that would hold in any subject (a kind of explanation that clicked, a habit in how I reason, a way of studying that did or didn't work) goes into the global learner files the way `learning_system/README.md` §3 describes. This is the part of the system that should keep improving, so look for it in every input.
- **`where_i_stand.md`:** update it per its §8 when a status there changes.
- **`persona.md`:** only for a major change (my target role, my situation, a goal). Tell me what you'd change and wait for a yes.

**Never:**

- **Edit material I've already read** because of what a talk-through showed. Corrections go in your reply or into future material.
- **Write new lectures or other material unless I ask.** Propose it in the `000-` docs. When I do ask, follow `learning_system/lecture_standards.md`: one self-contained document.
- **Change a status because material was generated.** Only what I say, write, build or run counts.
- **Put employer, product or interview details in any file.** The repo is public. Candid notes about me go wherever the charter's file map puts the AI notes.

## 5. Your reply

I often read it on my phone, mid-walk. Keep it under about 400 words unless I ask for more:

1. **Verdict:** one line.
2. **Solid:** 2–4 specific things I can now trust.
3. **Corrections:** at most 3, highest impact first. What I said → what's true → why, with the root named briefly. Anything that needs a real explanation gets one line here and goes on the plan.
4. **Doubts checked:** of the things I said I was unsure about, which were actually wrong.
5. **Newly solid:** anything that moved to resolved since last time.
6. **Next:** the one thing to do next, plus 2–3 questions to try answering out loud on my next walk.
7. **Files updated:** one line.

Be candid. I'm not worried about looking incompetent, and I'd rather hear about a gap from you than find it later. Don't soften a wrong model into "a small imprecision", and don't inflate what's solid. Confirm what's right before correcting what isn't. When you praise something, make it a specific reasoning move, never general effort.

## 6. For the rest of the thread

For each new message, repeat sections 2–5. You don't need to re-read everything, but re-read the tracker and the `000-` docs if time has passed or I say I changed something. If I ask a question instead of giving a talk-through, answer it, and log the question itself as evidence of what's unclear. If I ask "what's next?", answer from the `000-` docs with one recommendation.
