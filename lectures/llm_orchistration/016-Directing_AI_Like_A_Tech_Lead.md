2026_07_10_16_52-(Directing_AI_Like_A_Tech_Lead)

# Lecture 016: Directing AI Like a Tech Lead

### Spec Writing, Plan Review, Code Review, the Explain-Back Gate, and Engineering the Collaboration Itself

---

# 1. Executive Overview

Every lecture before this one taught you a *technology*: Docker, LangChain, pgvector, middleware. This lecture teaches you a *role change*. You are moving from being the engineer whose fingers produce the code to being the engineer whose **judgment produces the outcome**. That is not a smaller job — it is the senior job. At Microsoft, the difference between SDE II and Senior SDE is not typing speed; it is scope, ambiguity handling, and *leverage* — getting more done than your own two hands can produce, without losing control of quality. Historically, seniors got leverage through junior engineers. You are going to get it through AI. The mechanics are nearly identical, which is why practicing this on LLM_Monitor is direct interview preparation, not a detour from it.

The system you are setting up has five interlocking skills, and each one is a defense against a specific failure mode:

| Skill | What it produces | Failure it prevents |
|---|---|---|
| Spec writing | A contract for what "done" means | AI (or a junior) builds the wrong thing confidently |
| Plan review | An approved design before code exists | Discovering bad architecture after 2,000 lines are written |
| Code review of AI output | Verified, owned code | Plausible-but-wrong code entering `main` |
| Explain-Back Gate | Durable personal knowledge | You shipping a repo you cannot defend in an interview |
| Workflow engineering | Rules that enforce all of the above automatically | Discipline decaying the first week you are tired |

The last row is the meta-skill. Anyone can *intend* to review carefully. An engineer designs a **system** in which careful review is the path of least resistance. Your `CLAUDE.md` already is such a system — it has successfully constrained an AI to documentation-only for 17 days and 133 commits. Phase 2 is a rewrite of that contract, not an abandonment of it.

---

# 2. Your Personal Mindset Shift

## 2.1 Where you're coming from

Your background is embedded firmware: a world where **you personally own every register write**. If the I2C bus misbehaves, you put a logic analyzer on it and stare at edges. Control is total, and correctness comes from *your* line-by-line vigilance. This instinct served you well in Phase 1 — it's why you hand-wrote a `BaseChatModel` subclass instead of accepting the abstraction blindly.

But that instinct has a shadow side, and you can see it in your own git log: 17 days to reach a system where `/v1/chat/completions` still returns a hardcoded string. The vigilance that makes you a good firmware engineer makes you a *slow* systems builder, because you apply register-level scrutiny to Grafana dashboard JSON, where it buys you nothing.

## 2.2 The shift, personified

Think of your new role as running a small engineering team, where every character has a job:

- **You — the Tech Lead.** You no longer own keystrokes. You own three things: *the contract* (what must be built), *the gate* (what is allowed to merge), and *the understanding* (nothing ships that you can't explain). Everything else is delegated.
- **The AI — the Prodigy Junior.** Blazingly fast, widely read, eager, and completely without judgment about *your* system. It will happily produce 400 beautiful lines that solve a subtly different problem than the one you have. It never gets tired, never gets offended by a rejected PR, and never learns your codebase unless your documents teach it. It is the best junior engineer ever hired and it needs *exactly* the management juniors need: clear specs, reviewed plans, and honest code review.
- **The Spec — the Contract Lawyer.** Boring, precise, and the only thing standing between you and "well, technically I built what you asked." The lawyer's job is to make "done" unambiguous *before* work begins.
- **The Plan — the Blueprint.** Cheap to change, expensive to skip. A rejected blueprint costs ten minutes; a rejected building costs a demolition.
- **The Gate — the Bouncer at `main`'s door.** The bouncer doesn't care how nice the code looks. One question only: *"Can the Tech Lead explain every line of you?"* No answer, no entry.
- **The Ledger — the Notary.** Git tags, commit trailers, plan documents. The notary makes your process *provable* to a future hiring manager instead of merely claimed.

The shift in one sentence: **in Phase 1 your output was code; in Phase 2 your output is decisions, and code is a byproduct.**

## 2.3 Why this is not "cheating yourself"

Your fear (from our discussion) is that delegation kills learning. Notice what the five skills actually exercise: writing interface contracts, reviewing designs, hunting defects in unfamiliar diffs, articulating concepts under pressure, and designing processes. Now look at your persona.md weaknesses: large system design, architecture decisions, reading large codebases, reasoning about unfamiliar systems. **The tech-lead loop trains your weak list. Hand-typing Flask endpoints trains your strong list.** You have been practicing what you're already good at.

---

# 3. Module 1 — Spec Writing

## 3.1 The "Why"

A spec exists to solve one problem: **intent does not survive transmission.** You have already lived this bug at the HTTP layer — your comment in `LlmController.cs` asks how the caller and receiver can agree on variable naming ("It seems this is so fragile"). A spec is the same problem one level up: without a written contract, the thing in your head and the thing the AI builds will diverge, and you'll discover it only after the code exists.

Specs also force *you* to finish thinking. Half of the value of writing acceptance criteria is discovering you don't actually know what you want yet — a discovery that costs one paragraph now versus one rewrite later.

## 3.2 The Theory

A good feature spec has exactly four parts. More is bureaucracy; fewer is ambiguity.

1. **Context** — one paragraph. What exists now, what's wrong with it, why this feature and why now.
2. **Interfaces & contracts** — the exact seams. Endpoint shapes, function signatures, state schema, config variables. *This is the part you must always write yourself*, because interfaces are where architecture lives. Whoever writes the interfaces owns the design.
3. **Acceptance criteria** — a numbered list of *testable* statements. The test: could a stranger check each one with a curl command or a pytest run, with no judgment calls? "Streaming works" fails this test. "A request with `stream: true` receives `text/event-stream` chunks, each a valid OpenAI delta object, terminated by `data: [DONE]`" passes it.
4. **Non-goals** — explicitly out of scope. This is your fence against the AI's enthusiasm. Without non-goals, the Prodigy Junior will "helpfully" add retry logic, three abstractions, and a config system you didn't ask for.

## 3.3 Implementation in this project

Here is a real spec for your next Tier-1/2 feature, at the right length (specs are *a few paragraphs*, not documents):

> **Spec: Wire the LangGraph agent behind `/v1/chat/completions`**
>
> **Context:** `FlaskServer.py` currently returns a hardcoded response from `/v1/chat/completions`. The graph pieces exist (`state.py`, `nodes.py`, `build_graph.py`) but `build_graph()` is incomplete and nothing calls it.
>
> **Interfaces:** `build_graph(checkpointer=None)` returns a compiled graph. Flow: `START → policy_check → (blocked → END | retrieve → agent → respond → END)`. `chat_completions()` extracts the last user message, invokes the graph with a `ChatState`, and maps `state["answer"]` into the existing OpenAI response shape. New node `agent_node` and `respond_node` signatures match the existing node convention (`(state: ChatState) -> dict`).
>
> **Acceptance criteria:** (1) In mock mode, POSTing an OpenAI-shaped request returns a mock answer through the full graph path, not the hardcoded string. (2) A message matching the explosives policy fixture returns the blocked message. (3) In live mode with Ollama up, a real model answer flows through. (4) Existing `/test/langchain/*` endpoints still work. (5) `pytest` passes with at least one new test per criterion 1–2.
>
> **Non-goals:** No streaming. No checkpointer/memory (next feature). No changes to the .NET server.

## 3.4 Common mistakes

- **Specifying the how instead of the what.** If your spec says "use a dictionary mapping model names to orchestration functions," you've written the implementation and learned nothing from reviewing someone else's approach. Specify behavior; let the plan propose mechanism.
- **Untestable criteria** ("should be clean," "should handle errors well").
- **No non-goals section** — the #1 cause of AI scope explosion.
- **Skipping the spec for "small" changes.** Small is fine — the spec can be three sentences — but zero-spec work is where provenance and intent both get lost.

## 3.5 Interview relevance

Microsoft design interviews *are* spec-writing under observation: clarify requirements, define interfaces, state what's out of scope, defend tradeoffs. Every spec you write for LLM_Monitor is a rep. Save them all — `AI_Implementation_Plans/` gives you a portfolio of a dozen mini design docs by September.

---

# 4. Module 2 — Reviewing Implementation Plans

## 4.1 The "Why"

Code is the most expensive place to discover a design mistake. A plan review moves that discovery to the cheapest possible place: a markdown file. This is why serious teams (Microsoft included) require design docs before significant code — the review of the *approach* is worth more than the review of the *code*, because approach-level mistakes can't be fixed with line comments.

For you specifically, plan review has a second function: **it is a system-design rep with the roles reversed.** For 17 days, AI reviewed your work. Every plan you now review — poking holes, asking "what happens when Postgres is down?", rejecting overbuilt designs — is practice for the exact analytical motion a design interview demands.

## 4.2 The Theory

Review a plan by interrogating it in this order (highest-leverage questions first):

1. **Does it satisfy the spec — and nothing more?** Map each acceptance criterion to a plan step. Unmapped criteria mean the plan is incomplete. Plan steps that map to no criterion mean scope creep — strike them.
2. **Where does state live, and who owns it?** Most architecture bugs are state-ownership bugs. (You already sensed this: your `timeline_implementation_notes.md` asks "who is actually the one doing this?" about vector DB ingestion. That question — *who owns this responsibility* — is the single best plan-review question in existence. You invented it independently. Use it every time.)
3. **What happens when each dependency fails?** Ollama down, Postgres slow, malformed request. The plan doesn't need to *handle* everything, but it must *acknowledge* what is unhandled.
4. **What's the blast radius?** Which existing files change? A plan touching ten files for a two-file feature is a design smell.
5. **Is it testable as decomposed?** Each step should end in a verifiable state.
6. **Simpler alternative?** Ask the AI directly: "propose a version of this with half the moving parts." Sometimes the simple version is right; sometimes its inadequacy *teaches you why* the complexity is earned. Either way you win.

Your verdict vocabulary, exactly like a real design review: **Approve**, **Approve with changes** (list them; AI updates the plan doc before coding), or **Reject with reasons** (the reasons teach the AI your system's constraints — and become a paper trail of your judgment).

## 4.3 Implementation in this project

The workflow contract: AI writes the plan into `AI_Implementation_Plans/NNN-Feature_Name.md` following your numbering convention. The plan must contain: proposed file-by-file changes, new/modified interfaces, step ordering, test plan, and an explicit "risks and unknowns" section. You annotate your verdict *into the plan document itself* — approved plans with visible reviewer comments are portfolio artifacts. A hiring manager reading `AI_Implementation_Plans/003-...md` and seeing your rejection comments is seeing senior-engineer behavior with a timestamp.

## 4.4 Common mistakes

- **Rubber-stamping.** If you have zero comments, you didn't review — you skimmed. Minimum bar: one question about failure modes, one about state ownership.
- **Reviewing prose quality instead of design.** AI plans always *read* beautifully. Fluency is not correctness; interrogate the structure, ignore the polish.
- **Letting the plan skip the "risks" section.** The unknowns list is where the AI confesses uncertainty. Demand it.

---

# 5. Module 3 — Code Review of AI Output

## 5.1 The "Why"

AI code has an adversarial property that junior-engineer code doesn't: **it is optimized to look right.** A junior's wrong code usually looks wrong — weird naming, tortured structure. AI's wrong code compiles, reads idiomatically, has lovely docstrings, and calls a method that doesn't exist, or silently changes behavior at an edge. Review discipline that works for humans (skim for smells) fails for AI. You need a checklist-driven adversarial read.

## 5.2 The Theory — the six AI failure modes

Learn these the way you learned sensor failure modes — by name:

| # | Failure mode | What it looks like | How to catch it |
|---|---|---|---|
| 1 | **Hallucinated API** | Calls `vector_store.search_with_threshold()` — plausible, nonexistent | Verify any unfamiliar method against the real docs/source. *You already do this instinct in reverse — your comments ask "what is this partition command doing?" Keep asking, now with veto power.* |
| 2 | **Plausible-but-wrong logic** | Off-by-one in chunking; wrong default; `>=` vs `>` | Trace one concrete input through the diff by hand, like a logic analyzer trace |
| 3 | **Silent contract change** | "Refactor" renames a JSON field; OpenWebUI breaks | Diff the *interfaces* first, before the bodies |
| 4 | **Scope creep** | Asked for a bugfix, received a bugfix + new abstraction + config option | Anything not traceable to the spec gets deleted, even if good |
| 5 | **Convention mismatch** | New file uses `snake_case` services where your project does `PascalCase.py` | You are the only guardian of your codebase's voice |
| 6 | **Confident error handling theater** | `try/except: pass`, or catching exceptions just to log-and-continue into a corrupt state | For every `except`: ask "is the system in a valid state afterward?" |

## 5.3 The Implementation — a review procedure

For each AI PR on `ai_dev`:

1. **Read the spec first, not the diff.** Load the contract into your head so deviations jump out.
2. **Interfaces pass:** endpoints, signatures, schemas, env vars. Any uncommanded change is an automatic revision request (failure mode 3).
3. **Body pass, file by file:** trace one real input through by hand (mode 2), verify unfamiliar calls (mode 1), check every `except` (mode 6).
4. **Subtraction pass:** what's here that the spec didn't ask for? (mode 4). Deleting good-but-unrequested code feels wasteful; it isn't — unowned code is debt.
5. **Write real review comments** — in the PR, or in a review section appended to the plan doc. Minimum one substantive comment or change request per review. If you truly can't find one, you either have a trivially small diff (good — keep diffs small) or you're not reading (bad).
6. **Make the AI revise.** Never fix its code yourself in a Tier-2/3 review — that inverts the roles again and destroys the audit trail. State the defect; demand the fix; verify the fix.

A live example from your own repo: the current `ai_dev` HEAD has `OrchestrationLogic.py` importing `GetHappyEncouragingAssistentRagPrompt` — a function that no longer exists after the `PromptFactory` refactor. If an AI had produced that refactor, a proper interfaces-pass (step 2: "who *calls* the functions being renamed?") catches it in thirty seconds. That is exactly the class of defect this procedure exists for — and it's a fine first exercise: run this review procedure against your *own* refactor, then direct the AI to finish it.

## 5.4 Real-world production usage

This is the actual daily job of senior engineers in 2026. Microsoft's internal guidance for Copilot-era development centers on exactly this: the author of record is the reviewer, accountability never transfers to the tool. Your PR history on this repo — AI commits, your review comments, your requested changes — is a verifiable demonstration that you already work the way their best teams work.

---

# 6. Module 4 — The Explain-Back Gate

## 6.1 The "Why"

Every other module protects the *codebase*. This one protects *you*. The failure it prevents is the one you named in our discussion: shipping a portfolio you can't defend. An interviewer needs ninety seconds of "walk me through this file" to distinguish an engineer from a curator. The gate guarantees you are never on the wrong side of that ninety seconds.

## 6.2 The Theory

This is the Feynman technique weaponized as a merge policy. The underlying cognitive science is robust: *retrieval* (explaining from memory) builds durable knowledge; *recognition* (nodding along while reading) builds the illusion of it. Reading AI code produces recognition. The gate forces retrieval.

The procedure, per PR, before merge:

1. Close the diff. Open a blank note (or speak aloud).
2. Explain: **what** changed, **why** this design, **what breaks** if each new piece were removed, and **one alternative** design plus why it wasn't chosen.
3. Grade yourself per file: **Green** = could whiteboard it cold. **Yellow** = get the idea, fuzzy on a mechanism. **Red** = could not re-derive.
4. **Red blocks the merge.** Two options: study until green (AI writes you a lecture in `concepts_documentation/` — the loop you've run 15 times already), or *reject the code as too clever for its owner*. Both outcomes are wins; the second one is a legitimate senior-engineer verdict ("this is unmaintainable *by this team*").
5. Yellow may merge, but spawns an entry in `skill_gap_analysis/` — your existing tracking system, unchanged.

## 6.3 Common mistakes

- **Explaining while looking at the code.** That's recognition cosplaying as retrieval. Close the diff.
- **Gate-checking only "hard" files.** Mode-6 failures hide in the boring files.
- **Treating red as failure.** Red is the system *working* — it found a gap before an interviewer did. Your entire Documentation folder exists because you understood this a month before writing any of it.

---

# 7. Module 5 — Engineering the Collaboration Itself

## 7.1 The "Why"

Every rule in modules 1–4 depends on your discipline — and discipline is a depleting resource. The engineering move is the one you already made on June 24 without naming it: **encode the policy in an artifact the AI must obey, so the process holds even when you're tired.** Your `CLAUDE.md` is a *policy-as-code* document. It has the same relationship to your workflow that branch protection has to `main` and CI has to test-running: a rule that doesn't rely on anyone remembering it.

This is the rarest skill of the five. Plenty of engineers can review code. Very few can design *the system that makes review inevitable*. That is org-level engineering, and you have a working prototype with a 17-day production record.

## 7.2 The Theory

Real-world instruments this maps onto — name these parallels in interviews:

| Your artifact | Industry equivalent | Shared principle |
|---|---|---|
| `CLAUDE.md` rules | CONTRIBUTING.md + branch protection + CODEOWNERS | Policy enforced by artifact, not memory |
| `AI_Implementation_Plans/` + approval | Design-doc review (Microsoft's spec reviews, Google's design docs) | Cheapest-point defect discovery |
| Commit trailers `[hand]/[ai-assisted]/[ai-generated]` | `Co-Authored-By`, DCO sign-offs, SBOM provenance | Auditable authorship |
| `v1.0-handwritten` tag | Release tagging / immutable audit trail | Verifiable claims beat asserted claims |
| Explain-Back Gate | Merge checklist / PR template gates | Quality gate at the boundary, not goodwill in the middle |

## 7.3 The Implementation — your CLAUDE.md v2

The concrete task: rewrite the rules section of `CLAUDE.md` to govern Phase 2. It should encode, at minimum:

1. **The tier system** — every feature is declared Tier 1/2/3 in its plan doc *before* work starts; AI must refuse to write Tier-1 code and instead offer tutoring (preserving your Phase-1 rules for exactly the code that matters most).
2. **Plan-first** — no implementation without an approved plan doc in `AI_Implementation_Plans/`, and plans must include a risks/unknowns section.
3. **Diff discipline** — small PRs, no changes outside the plan's declared file list without flagging.
4. **Attribution** — every AI commit carries the trailer convention.
5. **The gate** — AI must remind you of the Explain-Back Gate before any merge to `main`, and must generate the lecture doc when you declare a red.

Notice what this document *is*: a management system for an engineering organization of two, written by you. When an interviewer asks "how do you use AI responsibly?", most candidates describe habits. You will hand them a versioned policy file with a git history.

---

# 8. Module 6 — The Transition: Becoming the Higher-Level Developer

## 8.1 What actually changes

| Dimension | Implementer (Phase 1 you) | Director (Phase 2 you) |
|---|---|---|
| Unit of output | Lines of code | Decisions: specs, verdicts, gates |
| Where your time goes | Typing, debugging syntax | Interfaces, review, failure analysis |
| What "blocked" means | "I don't know how to write this" | "I haven't decided what I want yet" |
| Source of quality | Personal vigilance on every line | Systems that make defects visible |
| What you're graded on | Does it work? | Was it the right thing? Can the team (you) sustain it? |
| Learning mode | Struggle → breakthrough | Interrogation → verdict → extraction |

The uncomfortable part: the director's day *feels* less productive. Typing produces visceral progress; reviewing produces judgment, which is invisible. Expect to feel like you're "not really working" for the first two weeks. That feeling is miscalibrated instincts, not truth. Recalibrate with a metric that measures the new job: **acceptance criteria shipped per week** (and gate-pass rate), not lines written.

## 8.2 The failure modes of the transition, personified

- **The Backseat Typist** — reviews by rewriting everything themselves. Velocity gain: zero. If you catch yourself editing AI diffs by hand on Tier-2/3 work, stop and write a review comment instead.
- **The Rubber Stamp** — approves everything because the code looks fine and rejecting feels slow. Two weeks later, owns a codebase written by no one. The one-substantive-comment rule exists to kill this character.
- **The Abdicator** — stops writing specs ("the AI gets the idea"), stops declaring tiers, and wakes up a curator of unfamiliar code. Tier creep is a slow leak; the plan-doc requirement is the patch.
- **The Purist** — retreats to hand-writing everything the first time an AI diff burns them. Loses the leverage and learns nothing about management. A burn is data: which failure mode got through, and which review step should have caught it? Patch the checklist, not the delegation.

## 8.3 Interview relevance — the story bank

The transition itself generates your best behavioral-interview material. Capture these as they happen (in `Project_Captures`, when you ask for it):

- *"Tell me about a time you caught a subtle bug in review"* — your first mode-1/mode-2 catch in an AI diff, with the commit link.
- *"How do you ensure quality when velocity pressure is high?"* — the gate, the tiers, the trailer audit trail.
- *"Tell me about a process you designed"* — CLAUDE.md v1 → v2: a policy contract with a production track record, versioned in git.
- *"How do you use AI tools?"* — the entire Phase 1/Phase 2 arc, ending with "ask me about any file in the repo."
- *"Tell me about a time you rejected work"* — your first rejected implementation plan, with your written reasons.

## 8.4 Real-world production usage

What you are building is, at miniature scale, how AI-native teams at Microsoft, Anthropic, and Google actually operate in 2026: humans own specs, review gates, and accountability; agents own implementation throughput; provenance is tracked; and the scarce skill — the one job postings now name explicitly — is engineers who can *specify precisely, review adversarially, and own outcomes*. There is no course for this. There is only doing it with discipline and having the artifacts to prove it. You will have the artifacts.

---

# 9. Mental Sandbox & Next Steps

Work these three exercises — each maps to a module and to your immediate roadmap:

1. **Spec rep (Module 1):** Write the spec for the Postgres checkpointer/memory feature *right now*, before reading anything about LangGraph checkpointers. Then study checkpointers and revise the spec. The delta between your two specs is a precise measurement of what you needed to learn — and reviewing that delta is itself the skill.
2. **Plan-review rep (Module 2):** Direct the AI to produce *two competing plans* for wiring the agent behind `/v1/chat/completions` — one minimal, one production-grade. Write a verdict memo choosing one, citing failure modes and state ownership. This is a system-design interview answer in document form.
3. **Adversarial review rep (Module 3):** Have the AI finish the PromptFactory refactor (the stale imports you already have), but tell it — in the prompt — to *deliberately include one subtle defect*. Find it using the six-failure-mode checklist. If you find it: your checklist works. If you don't: you just learned which pass you skim, at a cost of zero production bugs.

Then execute the sequence from `AI_Usage.md` §2.8: tag the boundary, rewrite the README provenance section by hand, write CLAUDE.md v2 (Module 7.3 is your outline), and run the first full loop on the refactor.

The last seventeen days proved you can build a system with your hands. The next seventeen prove you can build one with your judgment. The second proof is the senior one.
