# Lecture 001 — Questions From the Issue Shortlist

> **What this is:** a running Q&A log. As I read `implementations/001-issue_shortlist_sept_2026.md`, I ask questions about things I don't understand or want to explore, and each answer is **appended** here, newest at the bottom.
> **Started:** 2026-09-26
>
> **Format for each entry:** the question (in my words) → the short answer → the full explanation → what to take away → interview relevance (where it applies).

---

## Index

| # | Question | Related issue | Topic |
|---|---|---|---|
| Q1 | Why do maintainers open an issue for a simple docs fix instead of just doing it? | YARP #1764 (item A) | How open-source projects actually run |

---

## Q1. Why open an issue for a simple docs fix instead of just doing it?

**Related:** [YARP #1764](https://github.com/dotnet/yarp/issues/1764), item A in the shortlist · **Asked:** 2026-09-26

### The question

In YARP #1764, the maintainer already explained exactly what the docs should say (the 100-second activity timeout, and that keep-alives must come from the client or server). It's a small documentation change. So why open an issue, describe it in detail, and then leave it for years instead of spending a few minutes to just fix it, especially when Microsoft engineers have AI and powerful internal tools? I'd understand leaving a hard bug open, or something needing special hardware, but this seems like it should take less effort to fix than to write up.

### The short answer

Because **the scarce resource isn't typing. It's a maintainer's attention**, and an issue is the cheapest way to *record* knowledge without *spending* that attention right now. The explanation in the issue took a couple of minutes, as part of answering a user. Turning it into a merged docs change takes a context switch, a different repo, a review, and a publish cycle. That's small in absolute terms, but it competes with bugs, security fixes, and releases, and it **always loses that competition**. Leaving it labeled `help wanted` also serves a second purpose: it's a deliberate entry point for new contributors like you.

### The full explanation

#### 1. The issue is a "bottom half," not a to-do list

Here's a firmware analogy that fits almost exactly.

```
 Firmware                                   Open-source maintainer
 ────────                                   ──────────────────────
 An interrupt fires                    ≈    A user reports "my WebSocket keeps dropping"
 The ISR (top half) does the minimum:  ≈    The maintainer answers the user in 2 minutes:
   acknowledge, capture state, return         "100 s activity timeout; use keep-alives"
 The rest is deferred to a             ≈    The leftover work ("the docs should say this")
   bottom half / work queue                   is deferred to an issue, labeled and queued
 The scheduler runs deferred work      ≈    Someone picks up the issue when priorities
   when higher priorities allow                allow: a maintainer, or the community
```

The maintainer handled the **urgent** part (unblock the user) and **deferred** the non-urgent part (improve the docs) so it wouldn't be forgotten. Writing the issue wasn't "more work than fixing it." It was the cheapest way to **save the knowledge** while going back to higher-priority work.

#### 2. A priority queue without aging starves low-priority work

YARP has a small core team whose members also own other parts of ASP.NET Core networking. Their queue always contains security issues, regressions, release work, customer escalations, and design reviews for new features. A docs clarification is real but **low severity**: nobody's production is down because of it.

In a scheduler with strict priorities and no **aging** (bumping a task's priority the longer it waits), low-priority tasks can wait forever. That's exactly how an issue like #1764 sits in the `Backlog` milestone for years. Nobody decided "we won't do this." It just never rose to the top. The `help wanted` label is the maintainers' way of saying: *"We won't get to this soon, and we'd welcome someone else doing it."*

#### 3. "Simple" changes aren't free for a maintainer

For you, a first docs PR is a learning exercise. For a maintainer, even a small change has fixed costs:

| Cost | For #1764 specifically |
|---|---|
| **Context switch** | Stop current work, reload the docs structure, find the right page |
| **Different repo, different process** | YARP's docs moved into `dotnet/AspNetCore.Docs`, which has its own style guide, PR template, and reviewers from the docs team |
| **Getting it right** | Correct property names, correct version behavior, a code sample that actually works. Docs are read by thousands of people, so a wrong statement is expensive. |
| **Review and publishing** | Someone must review it; the docs build must pass; it must be published |

Maybe 30–90 minutes in total. That's small, but it's 30–90 minutes that isn't spent on a regression, and there are dozens of these in the backlog.

**Ownership diffusion makes it worse.** When the docs moved to a different repository, "who owns this change?" got fuzzier. The YARP engineers own the knowledge, while the docs repo has different owners. Small tasks that fall between two owners are the ones most likely to sit untouched. This happens inside every large company, not just in open source.

#### 4. `help wanted` issues are deliberately left for newcomers

This is the part that's easiest to miss. Healthy projects **intentionally keep a supply of small, well-described tasks** for new contributors:

- **They're the on-ramp.** A newcomer can't start with a subtle proxy bug. They need a task where the answer is known, so they can learn the process (fork, CLA, review, merge) with low risk.
- **Contributors are a long-term investment.** Every person who lands a first docs PR might become a regular, and regulars eventually take real work off the maintainers. That only happens if easy entry points exist. If maintainers fixed every easy thing themselves, the pipeline would dry up.
- **A detailed description is the point.** The maintainer wrote exactly what the docs should say *so that someone without insider knowledge can do it correctly*. That's a well-written ticket, not wasted effort.

So when you see a small, fully-explained `help wanted` issue, read it as: **"This one was left here on purpose, for someone like you."**

#### 5. Why AI and Microsoft's internal tools don't change this

The bottleneck was never producing the text. It's:

- **Deciding** it's worth doing now, over everything else (attention and priority)
- **Verifying** it's correct (judgment)
- **Reviewing and owning** the change after it ships (accountability)

AI speeds up the writing, but a human maintainer still has to decide, verify, review, and own it. Meanwhile, AI has *increased* the review burden across open source: maintainers now receive many low-effort, AI-generated PRs (Hacktoberfest stopped counting PRs in 2026 for exactly this reason). A careful human contribution that's verified and correct is more valuable to maintainers now, not less.

#### 6. To be fair: sometimes it really is just forgotten

Not every old issue is a deliberate on-ramp. Some are simply forgotten, and a maintainer might fix one in five minutes the day someone mentions it. That's fine too. Commenting "I'd like to take this" either gets you the task or prompts the maintainer to close it. Either way, the backlog gets smaller and you've made useful contact with the project.

### What to take away

- An issue is a **cheap way to save knowledge** without spending attention right now. It's a deferred-work queue, not a failure to act.
- Small, low-severity work **starves** in a strict priority queue. That's why good starter issues can stay open for years.
- `help wanted` + a detailed explanation = **an intentional on-ramp**. You taking it is exactly what the maintainer hoped for.
- The cost of software work is mostly **deciding, verifying, reviewing, and owning**, not typing. AI doesn't remove those costs.
- **Implication for item A:** the fact that the fix is already described isn't a reason to skip it. It's the reason it's a good first contribution. Your value is doing it correctly (right page, right property names, verified behavior) so the maintainer only has to review.

### Interview relevance

This question is really about **prioritization and the true cost of work**, which comes up in behavioral and design interviews ("How do you decide what to work on?", "How do you handle a backlog?"). Useful vocabulary:
- **Opportunity cost:** time spent on X isn't spent on something more important.
- **Context-switch cost:** the fixed overhead of starting any task, independent of its size.
- **Triage:** sorting incoming work by severity and impact.
- **Ownership:** a task with no clear owner tends not to get done.
- **Delegation / growing others:** leaving well-scoped work for less-experienced people is a senior-engineer behavior, not laziness. It's how teams scale.

---
