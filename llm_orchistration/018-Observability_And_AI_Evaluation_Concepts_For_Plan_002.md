2026_07_11_13_42-Observability_And_AI_Evaluation_Concepts_For_Plan_002

# Observability & AI Evaluation: The Concepts You Need Before Writing Plan 002

**Audience:** Timothy, about to author the Stage 1 design document for the next implementation plan.
**Premise:** The project is now clean, contracted, and testable (plan 001). The next differentiator — especially for a Microsoft AI-engineer role — is proving you can *operate* an AI system: observe it, measure it, evaluate it, and defend it. Companies don't struggle to build LLM demos; they struggle to run them. This lecture gives you the concepts to design that capability yourself.
**How to use it:** read Parts 1–6 to learn, Part 7 to scope, Part 8 to write the design doc. Where a concept lands directly in your codebase, I name the file.

---

## Part 1 — Why Observability Is a Different Problem for AI Systems

Classical observability answers: *"Is the system up, fast, and correct?"* — where "correct" is deterministic (the test either passes or it doesn't).

AI systems break that last assumption. Your `chat-rag` pipeline can be up, fast, and *wrong* — retrieving irrelevant chunks, hallucinating policy text, degrading after a model upgrade — and classical monitoring will show green across the board. So AI observability has **two stacked layers**:

```
Layer 2: QUALITY   "Is it saying good things?"     → evaluation (Part 5)
Layer 1: MECHANICS "Is it up/fast/erroring?"        → telemetry (Parts 2–4)
```

Layer 2 is impossible without Layer 1: you cannot evaluate what you didn't record. That dependency ordering is the spine of your plan 002 architecture — and probably of its implementation steps.

**Interview framing:** "LLM apps need a second observability layer, because correctness is probabilistic. I built both." That sentence, backed by a repo, is rare among candidates.

---

## Part 2 — The Three Pillars, Personified

### 2.1 The Diarist — Logs
Discrete events with context: *"14:02:11 — request abc123 hit /chat/rag, retrieved 2 chunks, 200 in 340ms."* You already have a diarist: `TelemetryMiddleware` writes structured log lines. Note what made them useful — `key=value` structure. Structured logs are queryable; prose is not.

### 2.2 The Accountant — Metrics
The accountant doesn't care about individual events, only aggregates over time: request rate, error rate, p95 latency, tokens per request. Cheap to store (numbers, not text), perfect for dashboards and alerts. The canonical set for a request-serving system is **RED**: **R**ate, **E**rrors, **D**uration. For your system, add the AI dimensions: token counts, cost estimate per request, retrieval hit counts, model/pipeline id as labels.

Key concept — **cardinality**: metrics are aggregated per unique label combination. Labels like `pipeline_id` (4 values) are fine; labels like `user_id` (unbounded) will detonate your metrics store. This is a classic interview trap: *"Why not put user_id as a metric label?"*

### 2.3 The Private Investigator — Traces
The PI follows ONE request across every service and writes down where it spent its time:

```
TRACE abc123 (one user request)
└── SPAN gateway /api/llm/chat/rag ......................... 812ms
    └── SPAN langchain_service /chat/rag ................... 795ms
        ├── SPAN vector_store.find_similar .................  60ms
        ├── SPAN prompt render ..............................  1ms
        └── SPAN ChatOllama.invoke .......................... 700ms  ← the truth
```

A **trace** is the whole tree for one request; a **span** is one timed operation with attributes; spans nest via parent ids. Traces answer the question logs and metrics can't: *"WHERE inside this slow request did the time go?"* For an LLM app the answer is usually "the model call," but proving it — and seeing when it's suddenly the retriever instead — is the job.

**The rule of thumb:** logs = what happened; metrics = how much/how often; traces = where and why slow. You need all three because each is the wrong tool for the other two jobs.

---

## Part 3 — Distributed Tracing: The Concept That Makes It One System

Your request crosses two processes (C# gateway → Python service) — soon more. The magic that stitches spans from different processes into one trace is **context propagation**:

1. The gateway starts a trace, creating a trace id (`abc123`) and a span id.
2. When YARP forwards the request, it injects a header — the W3C standard **`traceparent`**: `00-<trace_id>-<parent_span_id>-01`.
3. Flask middleware on the Python side *extracts* that header and continues the same trace rather than starting a new one.
4. Both services export their spans (independently, asynchronously) to a collector; the backend reassembles the tree by ids.

That header is the entire trick. Everything else is plumbing — which is why **OpenTelemetry (OTel)** exists: it's the vendor-neutral standard (APIs, SDKs, wire protocol OTLP) for generating and exporting all three pillars. ASP.NET Core and YARP have first-class OTel support (largely automatic instrumentation); Python has `opentelemetry-instrumentation-flask` plus manual spans where you want them. OTel is also a Microsoft-invested standard — Azure Monitor speaks it natively. Learn OTel, not a vendor SDK.

**Architecture pattern — the pipeline of pipes:**

```
gateway (OTel SDK) ──OTLP──►┐
                            ├──► OTel Collector ──► trace backend (e.g. Jaeger/Tempo)
langchain (OTel SDK) ─OTLP─►┘                  └──► metrics backend (Prometheus) ──► Grafana
```

The **Collector** is a personified mail-sorting office: services dump everything on it and stay fast; it batches, filters, and routes to backends. Services never know which backends exist — swap Jaeger for Azure Monitor without touching app code. That indirection is the pattern to name in your design doc.

**Design decision you'll face in Stage 1:** where does the trace *begin*? Answer: the outermost edge you control — the gateway. Your `TelemetryMiddleware` then evolves from "logs a line" to "opens the root span" (or gets replaced by ASP.NET's built-in OTel middleware — a legitimate design discussion to have with me in Stage 2).

---

## Part 4 — LLM-Specific Observability

Generic traces treat the model call as one opaque span. LLM observability opens it up. Per pipeline invocation you want recorded:

| Dimension | Why it matters |
|---|---|
| Full prompt (after template render) | debugging "why did it say that" — the #1 use |
| Retrieved chunks + scores | was a bad answer a retrieval failure or a generation failure? |
| Model + parameters (temp, etc.) | reproducibility; regression attribution after upgrades |
| Token counts (prompt/completion) | cost + context-window pressure |
| Latency split (retrieval vs generation) | optimization targets |
| trace_id linkage | jump from a Grafana spike to the exact ugly prompt |
| User feedback signal (even 👍/👎) | ground truth accumulates for evaluation |

Tools like **Langfuse** (self-hostable — fits your local-first setup and is already on your roadmap) are essentially trace backends specialized for this: they understand "generation" spans, render prompts nicely, aggregate cost, and store eval scores next to traces.

**The architecture insight for YOUR system:** plan 001 accidentally built you the perfect instrumentation point. Every pipeline is invoked through the registry with a uniform signature. One wrapper at the dispatch site — or inside `_run_assistant_chain`/`_run_graph` — instruments all four pipelines (and every future one) in one place. No scattering. When you write Stage 1, say this explicitly: *"instrumentation attaches at the registry boundary."* For LangChain/LangGraph internals, callback handlers (Langfuse's or OTel-bridged) get you span-per-node granularity without touching node code.

**Privacy note worth one line in your doc:** full-prompt logging is a data-governance decision (prompts can contain user PII). Locally it's fine; in industry it's a knob (sampling, redaction, retention). Mentioning it signals seniority.

---

## Part 5 — Evaluation: Judging an AI System Like an Engineer

This is the layer most candidates can't speak to. Concepts, bottom-up:

### 5.1 The Exam Bank — golden datasets
A **golden dataset** is a curated set of inputs with known-good expectations: for RAG, *(question → which doc chunks SHOULD be retrieved, and reference answer)*. Start embarrassingly small — 15–30 questions against your seed/policy docs is a real eval harness. Grow it from real failures (every bug becomes a test case — same philosophy as regression tests).

### 5.2 Grading the Librarian — retrieval metrics (deterministic, cheap, run-always)
Retrieval is deterministic given an embedding model, so it gets classical IR metrics:

- **hit@k** — for what fraction of questions does the correct chunk appear in the top k? Brutally simple, catches most regressions.
- **MRR (Mean Reciprocal Rank)** — average of 1/rank of the first correct chunk (1st place = 1.0, 3rd = 0.33). Rewards putting the right chunk *first*, which matters because context order affects generation.
- (Later: precision@k / recall@k when multiple chunks are relevant.)

These are pure functions over (query, retrieved ids, expected ids) — they can run in CI on every commit, using your mock-mode-with-real-pgvector trick from plan 001. **Your `score_threshold` parameter, currently disabled, gets tuned HERE** — with data, not vibes. That closes a loop you opened in Step 3.

### 5.3 Grading the Essay — generation metrics (probabilistic, expensive, run-nightly)
Generated text has no exact-match. The industry answer is **LLM-as-judge**: a (usually stronger) model scores outputs against a rubric. You already stubbed `get_llm_judge_prompt()` in `PromptFactory` months ago — plan 002 is where it becomes real. The RAG-specific rubric trio (formalized by frameworks like **RAGAS**):

- **Faithfulness** — is every claim in the answer supported by the retrieved context? (anti-hallucination — the metric)
- **Answer relevance** — does it actually address the question?
- **Context precision/recall** — was the retrieved context the right context?

**The critical caveat you must write in your design doc:** the judge is itself a model — biased (favors verbose answers, favors its own phrasings), inconsistent, and needing calibration against a handful of human-scored examples. LLM-as-judge is a *scalable approximation of* human judgment, not ground truth. Saying this unprompted is a senior signal; use structured judge output (score + cited evidence), pin the judge model version, and spot-check.

### 5.4 The Tripwire — regression gating
The point of 5.1–5.3 is not dashboards; it's a **gate**: a CI job (or nightly job posting to CI status) that runs the golden set and FAILS if hit@k or faithfulness drops below thresholds. This is how you make "we upgraded the model and quality silently dropped 20%" impossible. Design decision to settle in Stage 2: which evals are per-commit (cheap, deterministic retrieval metrics) vs nightly (LLM-judged, needs Ollama up) — because a per-commit eval that needs a 5-minute model boot will get deleted by future-you.

### 5.5 Where eval data comes from — the flywheel
Traces (Part 4) capture real prompts/responses → interesting/failed ones get promoted into the golden set → evals catch regressions → fixes generate new traces. Observability and evaluation are one system with a feedback loop, not two features. Draw this flywheel in your design doc; it is the single most senior-looking diagram you can put in it.

---

## Part 6 — Security & Defense (the "defend" in observe/evaluate/defend)

Enough to architect for it; a full treatment is its own future plan.

- **Prompt injection** — user input that hijacks instructions (*"ignore previous instructions and…"*). Your future RAG of user-supplied docs makes this **indirect** injection (malicious text inside a retrieved document — the retriever happily hands the attacker a megaphone). Mitigations are layered, none complete: input/output filtering, privilege separation (the LLM's output never executes anything directly), instruction hierarchy in prompts, and — the observability tie-in — **detection**: injection attempts are visible in traces if you're recording full prompts. Your policy-check node (retired in plan 001, prompt preserved in `PromptFactory`) is a policy *input* gate; plan 002's traces are what would let you see attacks; a later plan wires gate + detection together.
- **Output policy** — the `llm_judge`/policy prompts can also score *outputs* (leaked secrets, unsafe content) — same LLM-as-judge machinery, different rubric. Design the eval harness so a rubric is pluggable and you get security scanning nearly free.
- **Resource abuse** — token floods and cost blowups. Detection is a metrics alert (tokens/min per user); enforcement is the rate-limiter middleware slot you already reserved in the gateway pipeline. Notice: every security feature lands in a seam plan 001 built. Say that in interviews.

---

## Part 7 — Scoping Plan 002 (my recommendation, for you to accept or override)

Everything above is too much for one plan. The dependency-honest sequencing:

**In scope for plan 002 (observability foundation + first eval loop):**
1. OTel tracing: gateway root span → traceparent propagation → Flask/registry spans → Collector → local trace backend. (C#→Python distributed trace working = the headline.)
2. Metrics: RED + token/latency counters per pipeline_id, Prometheus + one Grafana dashboard.
3. LLM-layer capture: prompt/chunks/tokens per invocation at the registry boundary (Langfuse, or OTel attributes to start — a genuine Stage 2 discussion: Langfuse now vs OTel-only first).
4. Golden dataset v1 (15–30 items) + retrieval metrics (hit@k, MRR) running in CI mock mode.
5. First LLM-as-judge eval (faithfulness on the golden set), nightly/manual, using your existing judge prompt.

**Explicitly out (name these as non-goals in Stage 1):** alerting/paging, SSE streaming, security gates beyond design notes, checkpointer/memory, RAGAS-the-library (compute the 2–3 metrics yourself first — you'll actually understand them; adopt the library later if wanted).

**Why this order:** 1–3 create the recording; 4–5 create the judgment; the flywheel needs both ends. And each maps cleanly onto acceptance criteria you can script, plan-001-style ("one curl produces one trace visible in the backend containing spans from BOTH services with the SAME trace id" is a beautiful, falsifiable criterion).

---

## Part 8 — Writing the Stage 1 Design Document (apply the plan 001 lessons)

What made plan 001 work, turned into a checklist for your authorship:

1. **Current state, honestly** — including "TelemetryMiddleware logs 4 fields and nothing persists them," "zero visibility into prompts," "score_threshold disabled because no data."
2. **Problems as capabilities you lack**, not solutions you want: "I cannot answer *where did this slow request spend its time*"; "I cannot detect a quality regression after changing a model." (Each capability later becomes an acceptance criterion — that symmetry is the trick.)
3. **Direction** — the two-layer model from Part 1, the flywheel from Part 5.5, instrumentation-at-the-registry from Part 4.
4. **Interfaces & contracts** — last time you wrote "I don't know." This time you can name them: span attribute naming scheme (OTel semantic conventions + `llm.*` custom attributes), golden-dataset file format (contract for eval data!), eval-report format, dashboard panel list. Even rough guesses give Stage 2 something to sharpen.
5. **Acceptance criteria** — falsifiable, scriptable. Drafts: (a) one gateway curl → one trace, both services, same trace id; (b) Grafana shows per-pipeline RED + token metrics from a load of N requests; (c) every `/chat/rag` invocation records prompt + chunks + tokens, findable by trace id; (d) `eval_retrieval.py` outputs hit@3 and MRR on the golden set in CI; (e) judge run produces per-item faithfulness scores + summary; (f) an *induced* regression (swap embedding model or k=0) makes the eval gate fail. Criterion (f) is the plan-001 lesson applied forward: prove the alarm rings by starting a fire.
6. **Non-goals** — Part 7's list. Non-goals are what keep Stage 3 honest.

**Self-test before you write** (interview-grade): Why can't metrics alone tell you which pipeline stage is slow? What breaks if trace context isn't propagated across the YARP hop? Why is user_id acceptable as a *span attribute* but dangerous as a *metric label*? Why must the judge model be pinned and calibrated? Why do retrieval metrics belong in CI but judge metrics in nightly? If you can answer these, you're ready to author Stage 1 — and to defend the design at a whiteboard in Redmond.

---

*Next action when ready: create `Documentation/AI_Implementation_Plans/002-Observability_And_Evaluation.md`, write Stage 1 using Part 8, and open Stage 2 — I'll bring the pushback.*
