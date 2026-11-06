# Scoring Rubric (/20)

Every attempt gets ten scores of 0, 1 or 2: seven for the steps, three cross-cutting. The point isn't the total; it's seeing **which step** stays at 0 or 1 across attempts. That step is what you practice next (`drills.md`).

**How to score honestly:** score what's *on the page or said out loud*, not what you knew. If you knew the failure modes but ran out of time before saying them, step 7 is a 0. That's the information you need.

---

## Families A, B, D (the seven-step skeleton)

| Step | 0 | 1 | 2 |
|---|---|---|---|
| **1. Requirements** | Started drawing; or no requirements | Functional only, or a long unprioritized list | 2–4 core functional **+** at least 2 non-functional **with numbers** (latency, scale, burst size, power) **+** something stated out of scope |
| **2. Interface** | None | Operations named, no inputs/outputs | Signatures with inputs, outputs and error cases **+** one example call with its exact result |
| **3. State** | None | Entities listed | Entities **+ where each lives + who writes it** |
| **4. Trace one flow** | None | Partial, or skipped components ("then it gets to the app") | One request or event end to end, **every component named**, what each does to it |
| **5. Components** | Boxes with no reasons | A working path, but some boxes unjustified or one stage missing | Every box tied to a requirement; started simple |
| **6. Deep dive** | None, or deep on something that doesn't matter | The right constraint, one option | The right constraint, **two or more options compared**, a choice with its cost |
| **7. Failures and trade-offs** | None | Failures named | Failures **+ what the system does then + what changes at 10×** |

### Family-specific checks (count toward steps 5–7)

- **D (device / systems):**
  - At every arrow: *"which context runs this, and may it wait?"* Interrupt time and the UI thread may never block.
  - Sizing as a derivation with named quantities (`fill_rate`, `drain_delay`, `capacity`), not a guess.
  - An explicit **overflow policy** and a way to **detect** loss.
  - Level- vs edge-triggered interrupts, and when masking/unmasking happens.
- **A / B (distributed):**
  - Estimation only where it decides something (and you say what it decided).
  - A consistency choice stated, with the reason ("eventual is fine because…").
  - Where shared state lives, and how concurrent updates stay correct.

---

## Family C (low-level / object-oriented)

| Step | 0 | 1 | 2 |
|---|---|---|---|
| **1. Requirements** | None | Use cases only | Use cases **+** out of scope **+** what must be easy to extend |
| **2. Entities and relationships** | None | Nouns listed | Nouns **+ ownership + one responsibility each** |
| **3. Class APIs** | None | Method names only | Main classes' public methods with inputs/outputs |
| **4. State and transitions** | None | State listed | A state machine: states, events, transitions, who triggers each |
| **5. Walk one use case** | None | Partial | One use case followed call by call through the classes |
| **6. Extensibility** | None | "It's extensible" without showing it | One new requirement: exactly what changes and what doesn't |
| **7. Edge cases and concurrency** | None | Named | Named **+** handled (what the code does) |

---

## Family E (design-then-code)

| Step | 0 | 1 | 2 |
|---|---|---|---|
| **1. Clarify and interface** | Started coding | Signature only | Signature **+** what each input stands for and its valid range |
| **2. Examples** | None | Examples without exact outputs | One example call with its **exact** output **+** edge examples |
| **3. Approach and invariant** | None | Data structure named | Each field's meaning **+** an invariant that holds after every call |
| **4. Code** | Doesn't run / incomplete | Runs, with a bug | Runs and is correct on the examples; intermediate quantities named |
| **5. Trace and test** | None | Partial trace | A state-table trace of an example **+** one edge case |
| **6. Complexity and follow-ups** | None | Time or space only | Time **and** space **+** at least one follow-up answered (thread safety, memory growth, clocks) |
| **7. Wrap-up** | None | Rambling | Three clear sentences: structure, invariant, cost |

---

## Cross-cutting (all families)

| Item | 0 | 1 | 2 |
|---|---|---|---|
| **X1. Drove and talked aloud** | Long silences; waited to be led | Talked, but didn't announce the plan or check in | Said the plan at the start, narrated choices, checked in at step boundaries |
| **X2. Trade-offs said aloud** | Choices without costs | Some costs named | Every major choice came with what it costs |
| **X3. Time** | Didn't reach step 5 | Reached step 5 or 6 | Reached the last step within the planned time |

**Rough reading of totals:** 0–8 = the skeleton isn't automatic yet (drill steps 1–4) · 9–14 = complete but shallow (drill the deep dive and failures) · 15–20 = interview-ready on this family (move on, come back in two weeks).
