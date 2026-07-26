2026_07_26_15_00-Capstone_Lecture_Full_System_Mastery_And_Interview_Showcase

# Capstone Lecture: Full-System Mastery of LLM_Monitor, and How to Showcase It

**Audience:** Timothy Grant, post-Release-1.0.0, preparing to talk about this project in a Microsoft SWE2 interview and in the resume-linked YouTube walkthrough.
**Purpose:** you asked for a full pass to make sure you understand *everything* in this project and know what matters for an interview. You already have 23 deep-dive lectures (`concepts_documentation/001-023`) covering individual subsystems in depth, and a resume-ready facts sheet (`Documentation/Project_Captures/001-Project_State_Captures.md`) written just before release. **This document does not re-teach what those already teach.** It does three things they don't:
1. Walks the *whole system* end-to-end as one continuous story, so the pieces click together into one mental model instead of 23 separate ones.
2. Extracts and organizes the actual *interview-facing* material — pitches, war stories, a Q&A bank, numbers to cite, a demo script — much of it from events that happened **after** the last capture (2026-07-24), so it's current as of the 1.0.0 release.
3. Ends with a self-test: a list of questions you should be able to answer cold, without notes, organized by subsystem — the honest gap-check this whole `concepts_documentation` folder exists for.

Read this straight through once. Then use Part 16 (Q&A bank) and Part 18 (self-test) as flashcards in the days before an interview.

---

## Part 0: The Pitch, at Three Lengths

**10 seconds (the resume line):** *"I built a self-hosted LLM orchestration platform — a C#/.NET gateway, a Python LangGraph agent service with seven pipelines, RAG, MCP tool-calling, and full four-pillar observability — with a disciplined, reviewable AI-collaborative development process."*

**60 seconds (the opener):** *"LLM_Monitor is a multi-service backend I built to go deep on AI orchestration and practice production engineering discipline. A C# gateway fronts a Python service that owns a pipeline registry — plain chat, RAG, and a LangGraph agent that can call real tools over MCP, including one that builds structures in a live 3D voxel world. Every pipeline is contract-first, cost-tiered, and auto-instrumented — logs, distributed traces, metrics, and full LLM-trace capture across four observability tools, correlated by one trace id from the moment a request enters the gateway. It's built in two phases: I hand-wrote the whole system first so I'd understand every piece, then switched to a staged, reviewed AI-collaborative process for everything since — every design discussion and implementation step is preserved in the repo. It just shipped as 1.0.0, with multi-arch published Docker images."*

**5 minutes:** the 60-second version, then walk the architecture diagram in Part 1, name the pipeline registry as the central abstraction (Part 2), pick ONE war story that matches what the interviewer is probing for (Part 13), and close with the process story (Part 12) if they ask about AI-assisted development specifically.

**The one sentence to have ready for "why does this matter for Microsoft":** *"It's not a toy chatbot wrapper — it's a small, complete instance of the same problems production AI platforms have: contract-first service boundaries, cost-tiered request routing, distributed tracing across a polyglot stack, and evals that gate CI instead of trusting vibes."*

---

## Part 1: The Request, End to End — Walk This Diagram From Memory

If you can narrate this diagram, sentence by sentence, without looking at code, you understand the system's spine. Everything else in this document is detail hanging off this skeleton.

```
 User types in OpenWebUI (:3000)
   │
   ▼
 dotnet_server gateway (:5000)
   │  TelemetryMiddleware: starts a Stopwatch, calls _next(), then logs
   │  method/path/status/elapsed_ms/trace_id AFTER the response exists
   │  (Activity.Current — .NET's built-in span, present even without OTel)
   ▼
 YARP reverse proxy (config in appsettings.json, not code)
   │  forwards to langchain_service; if --obs, AddHttpClientInstrumentation
   │  injects the `traceparent` header on this exact hop — the ONE header
   │  that stitches the C# span and the Python span into one Jaeger trace
   ▼
 langchain_service (Flask, gunicorn workers, :5000 in-container / :5001 dev)
   │  FlaskServer.py: validate → build ChatRequest → registry dispatch → jsonify
   ▼
 Pipeline Registry (app/orchestration/registry.py)
   │  looked up by pipeline_id from the URL or by (model id → pipeline_id)
   │  from /v1/chat/completions; EVERY pipeline auto-wrapped in a
   │  "pipeline.dispatch" span + Prometheus counters AT REGISTRATION —
   │  no pipeline author ever writes telemetry code
   ▼
 One of 7 registered pipeline handlers
   │  chat-basic/chat-rag → LangChain chain (prompt | model)
   │  graph-basic/graph-rag → compiled LangGraph, no tools
   │  graph-tools/graph-free/graph-premium → LangGraph WITH a tool loop
   ▼
 ModelFactory.get_chat_model(...)                 vector_store.find_similar(...)
   │  mock → MockChatModel (deterministic)          │  pgvector similarity search
   │  live → Azure / openai_compat / ollama         │  (RAG pipelines only)
   ▼                                                 ▼
 (tool pipelines only) MCP round-trip to `toolbox` (separate .NET/MCP server)
   │  discovered ONCE at startup (asyncio.run), executed per-call over
   │  streamable HTTP; one toolset is a global, shared Voxel world
   ▼
 ChatResponse assembled → jsonify(to_dict()) → back up through YARP → gateway
   → OpenWebUI renders it, telemetry middleware has already logged the line
```

**Two access paths hit the identical handler** (CONTRACTS.md §6): the gateway path (`:5000/api/llm/...`, telemetered, "production") and a direct dev/test path (`:5001/...`, no gateway). **Deleting one port mapping in compose is the entire production-lockdown procedure** — a config change, not a code change. Know this fact; it's a favorite "how would you harden this for production" answer.

---

## Part 2: The Pipeline Registry — the Central Abstraction

Everything in this system is organized around one idea: **a dict from `pipeline_id` to a handler function**, and every other feature is something that happens *at the boundary of that dict*, never inside individual handlers.

```python
PIPELINES: dict[str, Pipeline] = {}
def register(pipeline: Pipeline) -> None:
    PIPELINES[pipeline.id] = replace(pipeline, handler=_instrumented(pipeline.id, pipeline.handler))
```

Consequences worth being able to explain, because each is a small architecture lesson:

- **Adding a capability = one `register()` call.** `/v1/models` is generated by iterating the dict. A new pipeline is instantly an OpenWebUI-selectable model with zero route changes, zero frontend changes.
- **Cross-cutting concerns attach at the boundary, not in the business logic.** `_instrumented()` wraps every handler in a `pipeline.dispatch` span + Prometheus counters *once*, at `register()` time. No pipeline function anywhere calls a metrics or tracing API directly. This is the single most reusable architectural idea in the whole project — if an interviewer asks "how do you avoid instrumentation code sprawling through business logic," this is your answer, with a real citation (`app/orchestration/registry.py`).
- **Conditional capability, honestly represented.** The three tool pipelines only register `if os.getenv("TOOLBOX_URL")`. No toolbox configured → those routes don't exist → they 404 with the contract's real `unknown_pipeline` error, not a silent fallback. "The capability honestly does not exist" is a direct quote from the code's own comment, and it's a good phrase to reuse verbatim — it names a real design principle (never let a missing dependency masquerade as a working-but-empty feature).
- **The registry is a routing table.** Once pipelines can bind to a specific model *provider* (`provider="openai_compat"` for `graph-free`, defaulting to `LLM_PROVIDER` env otherwise), the registry stops being just "which prompt/graph" and becomes "which prompt/graph, running against which economics" — the architectural fact that makes cost-tiering (Part 5) possible at all.

**The seven pipelines**, and the one sentence each that should come out instantly:

| Pipeline | One sentence |
|---|---|
| `chat-basic` | LangChain chain, prompt → model → parser, no retrieval — the floor. |
| `chat-rag` | Same chain shape, pgvector context injected into the prompt template. |
| `graph-basic` | LangGraph version of chat-basic — same behavior, different execution engine, proving the graph and chain paths share components. |
| `graph-rag` | Graph with a `retrieve` node wired in at *compile* time, not gated by a runtime flag. |
| `graph-tools` | **Lean tier** — agent ⇄ MCP tool loop, hard-capped, zero auxiliary LLM calls. |
| `graph-premium` | **Full tier** — policy gate → retrieve → agent ⇄ tools → respond, plus a sampled async LLM-judge after the response. |
| `graph-free` | Identical topology to `graph-tools`, bound to Groq (free `openai_compat` endpoint) instead of Azure at *graph-build* time — same graph, different economics. |

---

## Part 3: The Mock/Live Seam — Why You Can Demo an Agentic Tool Loop for $0

`ModelFactory.get_chat_model(userDesiredModel, provider=None)` is the single chokepoint every pipeline calls to get a model. Read its branching once and you understand the whole cost story:

1. **`LLM_MODE=mock` wins over everything, unconditionally, first line.** Even if `LLM_PROVIDER=azure` is set, mock mode never touches Azure. This is deliberate ordering, not an oversight — mock is the *default development posture*, and nothing should be able to accidentally escape it.
2. **Provider resolution: explicit `provider` arg (the per-pipeline binding) → else `LLM_PROVIDER` env → default `"azure"`.** This one function signature is where "the registry as a routing table" (Part 2) becomes real: `graph-free`'s builder passes `provider="openai_compat"` at compile time; every other tool pipeline passes nothing and inherits the env.
3. **`_require_env` fails loud on empty strings, not just missing keys.** Compose's `${VAR:-}` interpolation passes an *unset host variable* through as an *empty string* — which is "present" to a naive `os.environ["X"]` check but useless as config. `_require_env` treats empty as missing and names the exact variable in the error. This is a real bug class worth being able to explain unprompted: **"present" and "usable" are different properties, and only checking the first one is how silent misconfiguration survives to a customer.**
4. **Azure addresses *deployments*, not model names — `userDesiredModel` is deliberately ignored on that branch.** Know this distinction cold: in Azure OpenAI, you provision a "deployment" (a named instance of a model you chose in Azure AI Foundry) and your code addresses the deployment name, not a raw model string like `gpt-4o-mini`. This is exactly the kind of Azure-specific knowledge worth having ready if an interviewer probes "have you worked with Azure OpenAI specifically."

**The part that makes agentic behavior testable without paying anything: `MockChatModel`'s deterministic protocol**, not just random canned replies:

- A user message starting with `"TOOLCALL <tool_name> <json_args>"` makes the mock emit *exactly that* tool call — the graph then genuinely routes to the real `ToolNode`, which genuinely calls the real MCP tool (even against the real Tool_Box container), and the real result comes back around the loop. **The mock only fakes the model's decision to call a tool; execution is 100% real.**
- The mock also inspects the *system message* to detect which prompt it's serving (`"violates company guidelines"` → policy-checker contract; `"impartial evaluation judge"` → judge contract) and answers in that prompt's exact parseable shape, deterministically — so the policy gate and the LLM-judge are both unit-testable without flakiness from a random pool.
- `bind_tools()` is accept-and-ignore (returns `self`) specifically because `BaseChatModel.bind_tools` raises `NotImplementedError` by default, which would crash `graph-tools` in mock mode at bind time otherwise.

**Interview framing:** *"I built a mock provider that implements the same tool-calling protocol contract as a real model, not just a canned-string stub — so the entire agent loop, policy gate, and LLM-judge are testable, in CI, for free, without flakiness."* That is a strong, specific answer to "how do you test AI systems without spending money on every CI run."

---

## Part 4: RAG — pgvector, Idempotent Ingestion, and the Mock/Live Embedding Split

Three facts, each a small lesson:

1. **Ingestion is idempotent via content-hash IDs.** `deterministic_id(doc) = sha256(doc.page_content)`. Same content → same id → a restart can never duplicate a row, and — more importantly for cost — `add_documents_idempotent` does one `get_by_ids` SELECT to find what's *already* embedded and only calls the (expensive) embed step on what's genuinely new. **The known, accepted limitation:** an *edited* document gets a new id, so its old row becomes an orphan (no delta-sync/deletion yet — that's LangChain's `RecordManager`/indexing API, named as future work, not silently ignored).
2. **Mock and live share the exact same pgvector schema (768 dimensions) on purpose**, so switching modes is never a migration: `DeterministicFakeEmbedding(768)` (mock), `nomic-embed-text`/Ollama (768), Azure `text-embedding-3-small` with `dimensions=768` explicitly requested, and `fastembed`'s `BAAI/bge-base-en-v1.5` (also 768). **Re-ingestion is still required when switching mock↔live** — the *schema* matches, but mock and real vectors don't share a semantic space, so old rows would be nonsense under a new embedding model even though the column type never changes.
3. **Collections are namespaced per mode** (`company_policies_mock` vs `company_policies_live`) specifically so fake-embedding rows can never pollute a live similarity search even though both modes share one Postgres volume.

**The RAG-specific bug this design just barely avoided, and did avoid via testing discipline:** an early version had the RAG worker rendering the *non-RAG* prompt template — LangChain silently ignored the unused `{context}` slot, so the system "worked" (200 OK, plausible-sounding answer) while retrieval had *zero effect* on the output. It was caught only by asking a question the ingested docs alone could answer and noticing the model couldn't. **This is the direct ancestor of the eval harness (Part 8)** — a silent success is more dangerous than a loud failure, and status-code checking doesn't catch it; behavioral verification does.

---

## Part 5: LangGraph — State, Reducers, Conditional Edges, and the Cost-Tier Contract

You already have three dedicated deep-dives on this (007, 009, 010) plus the memory-specific one (023) — this section is the compressed "must recall instantly" version.

- **`ChatState` is a `TypedDict`; `messages` uses the `add_messages` reducer.** Without a reducer, a node returning `{"messages": [x]}` *overwrites* the list; `add_messages` *appends* (and de-duplicates by message id). This is the mechanism that lets a tool loop accumulate `human → ai(tool_calls) → tool → ai → ...` across many graph steps within one request.
- **Graph *topology* is decided at compile time, not request time.** `build_graph(with_rag=True)` compiles a genuinely different graph (a `retrieve` node wired in) from `with_rag=False` (no such node exists in that compiled object at all) — not one graph with an `if rag:` branch inside a node. "The compiled graph only contains the steps it actually runs" is worth saying in exactly those words.
- **The tool loop's one new concept vs. a linear chain: a *conditional* edge decided by the model's own output.** `tools_condition` inspects the last `AIMessage` for `tool_calls`; present → route to `ToolNode`; absent → route to `respond`/`END`. This is what turns a chain into an *agent*.
- **The premium graph adds a second conditional edge, decided by application logic instead of model output**: `_policy_gate` reads a state field (`policy_verdict`) written by an earlier node and routes to `blocked` or forward — fail-open by design (an unparseable verdict is treated as conformant, with the raw text preserved for the trace) because blocking a real user on a classifier hiccup is a worse failure mode than letting one ambiguous message through, in this deployment's risk profile.
- **The cost-tier contract is enforced at model *construction*, not scattered through business logic:** `TOOL_RECURSION_LIMIT` (default 8, rides in the same `config` dict as callbacks, so it needs no graph recompile) bounds the loop; `LLM_MAX_TOKENS` (default 1024) is passed to every paid model constructor. `CONTRACTS.md` §4a states the rule as an actual contract: lean/free tiers may contain **zero** LLM calls beyond the loop itself; premium gets exactly one gate call plus a judge call sampled at `JUDGE_SAMPLE_RATE` (default 0.1) that runs **after the response is returned, on a background thread** — "in the graph would mean on the clock," so it deliberately isn't a node.
- **Token accounting is accumulated, not overwritten, across loop iterations** — every trip around the loop is a real model call and a real cost, so `tool_agent_node`'s return adds to `state.get("prompt_tokens", 0)` rather than replacing it, because the lean tier's whole cost claim depends on the metadata reporting *every* call, not just the last one.

---

## Part 6: MCP Tools and the Voxel World — Memory vs. State Authority

This is the newest, most conceptually subtle part of the system (doc 023 is the full lecture; this is the compression you should be able to give verbally).

- **MCP tool discovery is eager, at startup, not lazy.** `discover_tools()` runs once at pipeline-construction time (`asyncio.run(...)`, safe there because no event loop exists yet at import time). If the toolbox is unreachable, the whole service fails to boot — a deliberate choice matching how pgvector is treated: fail loud at startup, not mid-request.
- **Tool execution is async-only** (`langchain-mcp-adapters` builds `StructuredTool`s with only `coroutine=` set, no sync `func=`) — discovered by inspecting the actual installed wheel rather than assuming, and it's *why* every tool-capable graph runs via `ainvoke`/`asyncio.run` instead of sync `.invoke()`.
- **The Voxel world is a single global singleton inside the separate Tool_Box process — not scoped to a thread, a user, or a request.** This is the fact that makes "does the agent remember what it built" a genuinely interesting question instead of an obvious one: a LangGraph checkpointer (per-`thread_id`, not yet wired in — see below) tracks what a *conversation* believes happened; it cannot and does not track what the *world* currently looks like, because two different conversations can both mutate the same global `Dictionary<Coordinate, Material>`.
- **The correct mental model, worth stating in exactly this shape if asked "how would an agent handle a shared mutable external resource":** *the agent's own memory is advisory; the resource's own state, queried live (`describe_world`/`world_info`), is authoritative — staleness is handled by re-grounding, not by trusting a cached belief.* This generalizes far beyond voxel blocks — it's the same shape as any agent editing a shared database, filesystem, or document another process might also be touching.
- **Conversation memory itself (LangGraph checkpointing) is designed, contract-reserved (`thread_id` in `CONTRACTS.md` §1), but not yet implemented** as of this release — `AI_Implementation_Plans/005` is the staged plan for it, and doc 023 is the concepts lecture. Know the honest state: this is a **named roadmap item you can speak to in depth**, not a shipped feature to claim.

---

## Part 7: Observability — Four Pillars, One Trace ID, Zero Overhead When Off

The thesis of this project's "operational maturity" story: **every request leaves a story**, and that story is optional at zero cost when you don't want it.

- **The API/SDK split is the idea to lead with.** `opentelemetry.trace.get_tracer(...)` is always safe to import and call — with no SDK provider configured, every span it hands out is a **no-op**, nanoseconds of overhead, no network calls, no `if enabled:` checks scattered through `registry.py`/`vector_store.py`. The *provider* (real exporter, real batching) is only constructed inside `init_observability()`, gated on `OBSERVABILITY_ENABLED`. Consequence worth naming explicitly: **the unit test suite exercises the fully-instrumented code paths for free**, because spans are no-ops in that environment rather than something tests have to work around.
- **One header does the cross-service trick.** `AddHttpClientInstrumentation()` on the C# gateway both creates a child span for the outbound proxied call *and* is what injects the `traceparent` header on that hop. On the Python side, `FlaskInstrumentor` extracts that same header, so the Python span **continues** the gateway's trace instead of starting a fresh, disconnected one. One header; one unified trace tree in Jaeger spanning two languages.
- **Push vs. pull, both present and worth distinguishing on sight:** traces are **push** (OTLP exporter → collector → Jaeger); Prometheus metrics are **pull** (`/metrics` sits there; Prometheus scrapes it on its own schedule). Same system, both models, for the reasons each protocol actually fits its own signal shape — traces are events as they happen; metrics are a snapshot you sample periodically.
- **Registry-boundary auto-instrumentation (Part 2) is what makes this scale without discipline debt** — a new pipeline gets a `pipeline.dispatch` span and RED-style Prometheus counters automatically, because instrumentation lives at `register()`, not inside each handler.
- **Langfuse adds the fourth pillar specifically for *LLM* observability** (rendered prompts, actual retrieved chunks, per-node spans inside a chain/graph) that generic APM tools like Jaeger/Prometheus don't capture — `get_langchain_callbacks()` follows the exact same "unconditionally called, returns `[]` when disabled" no-op-by-default pattern as the tracer.
- **The guided tour that proves all four pillars are wired together, not just individually present:** one `docker logs | grep telemetry` line carries a `trace_id`; paste that id into Jaeger for the cross-service span tree; the same window in Grafana shows `llm_requests_total` and token-rate panels; the same request's fully rendered prompt and retrieved chunks are in Langfuse. **Be able to actually run this**, not just describe it, before an interview or the demo video.

---

## Part 8: The Eval Harness — Two Tiers, a Judge You Calibrated, a Gate That Arms Itself

- **Retrieval eval: hit@k / MRR against a golden dataset** — a standard information-retrieval quality measure, applied here to "did pgvector return the document that actually answers this question."
- **LLM-as-judge, in two tiers, same philosophy as everywhere else in this codebase (mock/live):**
  - **`--tier plumbing`**: no containers, no DB, no real model — reference answers judged against their own expected seed docs by `MockChatModel` seeded with a fixed judge response pool. **The scores are meaningless by design; what's actually proven is the *loop*** — rubric loads, prompt renders, judge invokes, verdict parses, aggregation math runs correctly. This is the tier that runs in CI.
  - **`--tier quality`**: real answers from the real `chat-rag` pipeline, judged against what was *actually retrieved* (RAGAS-style faithfulness — grounding measured against retrieved context, not against some idealized "should have retrieved" context) by a real (usually stronger) judge model. Run manually, in-container, in live mode — never in CI, per the same "CI never spends live tokens" rule that governs every paid-API path in this system.
- **Calibration**: the judge also scores a small hand-labeled set (`calibration.jsonl`) and the report computes judge-vs-human exact-match rate and mean absolute difference. The line worth quoting verbatim: *"a judge you haven't calibrated is just a confident stranger."* This is a genuinely senior-level eval-engineering idea — most people build an LLM judge and never check whether it agrees with a human.
- **Verdict parsing is a small, deliberately careful pure function**: `partition(":")` splits on the *first* colon only, so a rationale that itself contains a colon survives intact — the same idiom reused across the policy-gate parser and the judge parser, worth noting as "I noticed I'd need this twice and made it one function" if asked about code reuse instincts.
- **The CI gate self-arms.** Ungated until a baseline file is committed (`eval/baselines/retrieval_plumbing.json` in the release-plan checklist); once committed, regressions against that baseline fail the build. This is a deliberately honest design: an eval gate with no baseline yet is *documented as running ungated*, not silently treated as "protecting" something it isn't protecting yet.

---

## Part 9: The Gateway (C#) — Small, but Everything in It Is Deliberate

`server/Program.cs` and `TelemetryMiddleware.cs` are short files; know them by heart because interviewers can ask you to read code live and this is the shortest, cleanest surface to demonstrate on.

- **YARP config lives in `appsettings.json`, not code** (`AddReverseProxy().LoadFromConfig(...)`), overridable per-environment via double-underscore env-var paths (`ReverseProxy__Clusters__langchain__Destinations__primary__Address`) — the same "config, not code, for the thing that changes per environment" principle as the mock/live seam.
- **`UseTelemetryMiddleware()` is an extension method** — `this IApplicationBuilder builder` is what makes `app.UseTelemetryMiddleware()` valid syntax, registering middleware into the *request pipeline*, distinct from registering a service into *DI* (`AddXxx` calls). Being able to explain this distinction correctly, unprompted, is a real signal of ASP.NET Core fluency.
- **Pipeline order IS the architecture**, stated as a comment in the file itself: `telemetry -> [future: auth] -> [future: rate limiter] -> YARP forwarder`. Middleware order determines what every request experiences and in what sequence — auth before rate limiting before proxying is a deliberate security/cost ordering choice, not arbitrary.
- **`Activity.Current` is .NET's own built-in span representation, created per-request by ASP.NET Core *even with OpenTelemetry entirely absent*.** OTel, when enabled, exports that existing Activity rather than creating a parallel concept — a good example of "the platform already had the primitive; the observability library just gives it somewhere to go."
- **The telemetry middleware logs on the way OUT, after `await _next(context)`**, specifically so `context.Response.StatusCode` is populated — logging before the inner pipeline runs would always show a meaningless default status.

---

## Part 10: Contracts — the Discipline That Makes a Polyglot System Safe to Change

`CONTRACTS.md` is short (155 lines) and you should be able to summarize its rules from memory:

1. **snake_case everywhere on the wire**, even though C# is PascalCase internally — mapped via `JsonNamingPolicy.SnakeCaseLower`, never hand-renamed per field. One convention, two languages, zero drift.
2. **Additive-only within a version.** New fields may be added; nothing may be renamed or removed within v1. `thread_id`/`attachments`/`options` are *reserved* — named in the contract before they're implemented, so a future implementation never has to guess a shape or risk breaking an existing client.
3. **Errors are contract-shaped too**, not ad hoc: a fixed `(http_status, error.code)` table (`invalid_request`/400, `unknown_pipeline`/404, `upstream_model_error`/502, `internal_error`/500) — every failure mode a client might need to branch on is enumerated, not discovered by trial and error.
4. **The cost-tier rules (§4a) are a contract, not a comment** — changing a pipeline's tier, or adding an LLM call to any request path, *requires a new AI_Implementation_Plans entry*, exactly like any other contract change. Cost posture is treated with the same rigor as a wire-shape change, which is the right instinct for a system where "live" literally means "spending money per token."

**Why this matters for an interview:** "contract-first API design" is a real, gradeable claim here, not a slogan — you can point at a single markdown file that both services demonstrably implement exactly, and at the discipline ("changes require a new plan entry") that keeps it from drifting.

---

## Part 11: CI/CD, Release, and Packaging — Condensed (Full Depth in Docs 004 and 022)

You have two long, excellent documents on this already (`AI_Implementation_Plans/004-Release-1.0.md` and `concepts_documentation/022`). Here is what to be able to say without opening either:

- **The honest-CI story is your best single anecdote, full stop.** The original GitHub Actions workflow "passed" — green checkmark — while installing zero dependencies and running a test that imported no application code. You found this, root-caused it, and rebuilt the workflow so the Python job installs real requirements and runs the real pytest suite, plus a separate C# build+test job. **"A green build now means something"** is a sentence worth having ready verbatim.
- **Secrets never entered a public image, verified, not assumed.** Docker build *context* for both services is a subdirectory that structurally cannot see the repo-root `.env` (`context: ./langchain_service`, `.env` lives one level up) — "safe by geometry, not by discipline someone has to remember." Verified further with `git log --all --full-history -- .env` (empty) and a grep of tracked files for key-shaped strings. The one-line audit worth quoting: `docker run --rm <image> env` and `docker history --no-trunc <image>` — neither requires reading a line of source, and it's a portable habit for auditing *anyone's* image, not just your own.
- **A tag is a pointer, not a copy of history — moving/recreating one is not "rewriting history."** You hit this for real: `v1.0.0` was pushed before the multi-arch publish workflow existed, so nothing had consumed it as a built artifact yet, making a version bump (not a force-push) the correct, zero-risk fix. Know the distinction: rebasing/amending a *pushed commit* changes SHAs everyone downstream depends on (that's what CLAUDE.md's "never change git history" rule actually forbids); moving a *tag* touches zero commits.
- **The multi-arch lesson, paid once, now a standing habit:** the very first published `toolbox` image was amd64-only because its publish workflow had no explicit `platforms:` key on the `build-push-action` step — discovered when it broke `docker compose up` on your own Apple Silicon machine. Fixed with `docker/setup-qemu-action` + `platforms: linux/amd64,linux/arm64`, and now written down as "add multi-arch from the first commit of any new publish workflow, not after rediscovering the gap a second time."
- **The Groq live-mode saga is your best "three different bugs that looked like one bug" story** — see Part 13 below; it belongs there because it's genuinely STAR-shaped.
- **Release scope was a deliberate, reasoned, and — importantly — *recorded* trade-off**, not a default: self-hosted docker-compose + Groq free tier for *this* release, Azure OpenAI's code path kept and working but explicitly not the demoed path, Azure *infrastructure* deployment deferred to its own future plan specifically to protect a time-boxed trial-credit window for when it can be spent at real volume. "I know how to defer scope deliberately and write down why" is a real signal, not padding.

---

## Part 12: The Development Process — Your Actual Differentiator

Two phases, and the contrast between them is the point:

1. **Phase 1 (2026-06-23 → 2026-07-09/10): 100% hand-written.** Docker system, C# gateway, Flask/LangChain service — every line personally written, AI used only for review and lecture-writing, specifically *so you'd understand every piece before AI touched code*. This phase produced real, ugly, instructive bugs (Part 13) — that's a feature of doing it by hand, not a cost.
2. **Phase 2 (2026-07-10 → present): staged AI-collaborative development.** A five-stage process, actually followed, actually visible in git: (1) you write design goals, (2) a *dynamic, recorded* discussion with the AI about architecture and tradeoffs — including real pushback and negotiation, not rubber-stamping, (3) the AI produces a step-by-step implementation plan, (4) implementation proceeds one step at a time with your explicit per-step permission, (5) verification. Five plans deep as of this release (001–005, the last being the memory design just drafted).

**Why this is a strong interview answer to "how do you use AI coding tools":** most candidates say "I use Copilot/Claude to write boilerplate faster." You can say: *"I direct AI through a staged process with explicit review gates, the same discipline I'd want from a human collaborator's PRs — and I have the receipts: every design negotiation is preserved in the repo, including the times I pushed back and the plan changed."* Then, if asked to substantiate: open any `AI_Implementation_Plans` doc and point at a real "Timothy —" entry that changed the AI's plan.

---

## Part 13: War Stories, STAR-Ready

Pick ONE that matches what's being probed. Don't recite all of them.

### "Tell me about a bug that was hard to diagnose" → **The honest-CI discovery**
**Situation:** Green CI, every commit, for a while. **Task:** eventually got suspicious enough to actually read the workflow file instead of trusting the checkmark. **Action:** found it looked for `requirements.txt` at the repo root (it lives in `langchain_service/`), installed nothing, ran a test importing no application code. **Result:** rewrote the workflow to install real dependencies and run the real suite, plus added a separate C# build+test job. **Why it matters:** shows you audit infrastructure instead of trusting a status icon — a habit, not a one-time fix.

### "Tell me about debugging a tricky distributed/environment issue" → **The Groq live-mode three-problems saga**
**Situation:** `./build.sh --mode live` against Groq (free tier) needed to work end-to-end for the release. **Task:** get it working, verify it for real, not just in theory. **Action, in order — and the point of this story is that each fix revealed a *different* problem underneath, not the same one recurring:**
1. Container crashed at boot for *every* pipeline, not just RAG — root cause: `entrypoint.sh` always runs RAG ingestion before gunicorn starts, and ingestion always resolves an embeddings provider globally, regardless of which pipeline a request would eventually use; Groq-class endpoints serve no embeddings at all, so that resolution raised and killed the whole container. Fixed by adding CPU-local embeddings (`fastembed`) for that provider so ingestion always succeeds.
2. Stack still wouldn't start — *unrelated* root cause found while verifying fix #1: the `toolbox` image was amd64-only (a gap in a *different* repo's publish workflow), and the dev machine is Apple Silicon. Fixed there, republished multi-arch, bumped the pinned tag here.
3. Stack started but hit Azure, not Groq — root cause: `.env` had the Groq keys but never actually set `LLM_PROVIDER=openai_compat`; compose's documented default (`azure`) correctly took over, and the factory's fail-loud check correctly named the exact missing Azure variable. **Not a bug — the fail-loud design working exactly as intended.** Fixed by setting the one missing line.
**Result:** end-to-end verified, real Groq completion, real non-zero token counts, all five containers healthy. **Result you should say out loud:** "each of the three problems looked like the same symptom (the stack won't start) and I had to prove which layer each one actually lived in before fixing anything — the honest fail-loud error messages this system already had made steps 1 and 3 fast; step 2 needed cross-repo investigation."

### "Tell me about verifying an assumption instead of trusting it" → **The `.env`/secrets audit**
Framed in Part 11 above — use it for "how do you approach security in a project" or "tell me about a time you double-checked something everyone assumes is fine."

### "Tell me about a design decision driven by a real constraint" → **Losing local GPU access**
**Situation:** developed against local Ollama; mid-project, lost access to hardware capable of local inference. **Task:** "live" mode needed a new meaning. **Action:** built a provider abstraction (`ModelFactory`) so provider choice is a config value, not scattered code, added Azure OpenAI (resume-motivated: "zero Azure" was the biggest gap found in a JD-alignment review) *and* a free-tier OpenAI-compatible path (Groq) as a genuine $0 dev loop, and — because live now means paying per token — designed an explicit cost-tier contract (lean/premium/free) rather than a vague "be careful" rule. **Result:** the constraint produced a *better*, more demo-able system (multi-provider routing you can show side-by-side in a demo) than the thing it replaced, not just a workaround.

### "Tell me about a subtle correctness bug in an AI system specifically" → **The silently-ignored RAG context**
Framed in Part 4 — a system that returns 200 OK and a plausible answer while doing nothing useful is a uniquely AI-shaped failure mode (status-code correctness ≠ behavioral correctness), and it's the direct motivation for building an eval harness at all.

---

## Part 14: Cross-System Misconceptions Worth Being Able to Correct on the Spot

- **"Mock mode means untested."** No — mock mode is a *deterministic protocol implementation* (Part 3), and the entire tool loop, policy gate, and judge are exercised by it. Real coverage, zero cost.
- **"The agent needs to remember the world it's building."** No — it needs to remember the *conversation*; the world's own state (queried live) is the authority. Conflating these is the exact mistake doc 023 exists to prevent (Part 6).
- **"Green CI means the feature works."** Only means what the CI steps actually exercise — the honest-CI story (Part 13) and the fact that `ci.yml` runs exclusively in mock mode (Part 8/11) are both instances of this: CI never caught the live-mode config bug in the Groq saga because it was never scoped to catch it, which is a coverage *boundary*, not a failure.
- **"A version tag is basically a label you can move around."** True until the moment something is *published under it* (an image pulled by a real consumer) — after that, moving it breaks a promise, which is the entire point of SemVer (Part 11).
- **"Observability has a performance cost you pay even when you don't use it."** Not in this design — the API/SDK split makes the disabled path a genuine no-op (Part 7), which is worth being able to explain as a specific pattern, not just asserted.

---

## Part 15: Numbers to Know Cold

| Fact | Value |
|---|---|
| Pipelines registered | 7 (`chat-basic`, `chat-rag`, `graph-basic`, `graph-rag`, `graph-tools`, `graph-premium`, `graph-free`) |
| Tool-loop recursion cap (default) | `TOOL_RECURSION_LIMIT=8` |
| Paid-model output cap (default) | `LLM_MAX_TOKENS=1024` |
| Premium judge sample rate (default) | `JUDGE_SAMPLE_RATE=0.1` |
| RAG vector dimensionality (every mode/provider) | 768 |
| Embedding models sharing that dimension | mock `DeterministicFakeEmbedding(768)`, Ollama `nomic-embed-text`, Azure `text-embedding-3-small` (`dimensions=768`), `fastembed` `BAAI/bge-base-en-v1.5` |
| Verified Groq live call (Stage 5, 004) | `openai/gpt-oss-120b`, prompt_tokens≈1609, completion_tokens=23, latency≈1166ms |
| Compose profiles | default(mock), `local-live`, `obs` (+ a `--gpu` override) |
| Observability pillars | 4 — structured logs (trace_id), OpenTelemetry/Jaeger traces, Prometheus/Grafana metrics, Langfuse LLM traces |
| Eval judge score range | 1–5, parsed via first-colon `partition` |
| Project timeline | started 2026-06-23; hand-written phase to ~2026-07-10; plans 001–003 through mid/late July; Release 1.0.0 tagged 2026-07-25/26; this doc post-release |
| AI_Implementation_Plans completed | 001 (cleanup/registry), 002 (observability/evals), 003 (tools + hosted LLM migration), 004 (Release 1.0), 005 (memory — designed, not yet implemented) |
| concepts_documentation lectures | 24 (this one included) |

---

## Part 16: Interview Q&A Bank

**Q: "Walk me through the architecture."**
A: Use Part 1's diagram narration verbatim. Land on the pipeline registry as the one abstraction everything else hangs off.

**Q: "What was the hardest bug you fixed?"**
A: Lead with the Groq three-problems saga (Part 13) if they want depth on debugging methodology; lead with honest-CI if they want a process/quality story instead.

**Q: "How do you test AI/LLM-integrated systems?"**
A: Mock provider implementing the real tool-calling protocol (Part 3) + a two-tier eval harness where the *cheap* tier proves the pipeline and the *expensive* tier proves quality, run separately, never in CI (Part 8) + a calibrated judge, because an uncalibrated judge is "a confident stranger."

**Q: "How would you scale this / what would you change for production?"**
A: Name the honest gaps yourself before being asked (Part 6/9's roadmap notes: no auth/rate-limiting yet, no streaming yet, conversation memory designed but not implemented, no cloud deployment yet) — then say what you'd do about each, and that the production-lockdown story (deleting one port mapping) already proves the dev/test surface is a conscious, reversible exposure, not an oversight.

**Q: "Tell me about a time you had to learn something you didn't know, fast."**
A: The async/sync MCP boundary (Part 6) — discovered by inspecting the actual installed adapter's source rather than assuming, found the load-bearing fact (tools are async-only) before writing code, and designed around it (`ainvoke` at the pipeline boundary) rather than hitting it as a runtime surprise.

**Q: "Have you used Azure?"**
A: Yes, specifically and concretely — Azure OpenAI chat + embeddings, deployment-based addressing (not raw model names), `dimensions=768` on embeddings to avoid a schema migration, fail-loud env validation for every required Azure variable. Also be ready with the honest framing: Azure *infrastructure* deployment (AKS/Container Apps) is a named, deliberately deferred next step, not done yet — and you can explain exactly why you deferred it (protecting a time-boxed trial credit for when it can be spent at real volume).

**Q: "How do you use AI coding assistants in your own workflow?"**
A: The two-phase story (Part 12) — hand-built first for understanding, then a staged, reviewed, five-stage collaborative process with a real paper trail of you pushing back and the plan changing. This is a rare, concrete answer; most candidates don't have receipts.

**Q: "What don't you like about your own design, or what would you do differently?"**
A: Have at least one ready that's real, not performative — good options: (a) the OpenAI-compatible `/v1/chat/completions` route currently reconstructs `ChatRequest` from only the *last* message even though clients send full history, which is exactly the gap the memory plan (doc 023/005) exists to close properly instead of patching around; (b) the Voxel world's global-singleton state (an accepted, documented v1 limitation in the *other* repo) means two concurrent conversations can quietly stomp on each other's build — known, scoped out, not hidden.

---

## Part 17: Live Demo Script (Screen-Share or Video)

Mirrors `004-Release-1.0.md`'s Presentation outline — condensed to what to actually click/type, in order:

1. `./build.sh --mode mock --obs` — narrate the healthcheck-ordered startup while it runs (pgvector → langchain_service → toolbox → gateway → OpenWebUI).
2. OpenWebUI (`:3000`) → pick `llm-monitor.graph-free` → ask a question that needs a tool ("what materials can you build with?" or, with the voxel viewer open in a second tab at `../Tool_Box/viewer/index.html`, "build a small tower of stone at the origin").
3. `docker logs dotnet_server | grep telemetry | tail -1` → copy the `trace_id`.
4. Jaeger (`:16686`) → paste the trace id → show the cross-service span tree (gateway span → langchain_service span → tool-call child span).
5. Grafana (`:3001`) → the per-pipeline RED + token panels, `llm_requests_total`.
6. Langfuse (`:3002`) → the same request's fully rendered prompt and (for a RAG pipeline) retrieved chunks.
7. `curl localhost:5000/v1/models` — point out this list is generated from the registry, live.
8. Close on the process story: open `Documentation/AI_Implementation_Plans/003-...md`, scroll to a real "Timothy —" entry, and say "this is what directing an AI collaborator with review gates actually looks like, not just a description of it."

---

## Part 18: Self-Test — Answer These Cold Before an Interview

Don't write answers here; if any of these make you hesitate, that's a real gap — go re-read the relevant Part above or the cited deep-dive doc.

1. What's the one dict-and-function pattern every pipeline, new or old, goes through, and what three things does that pattern buy you for free?
2. Why does `_require_env` check for an empty string, not just a missing key? What compose behavior makes that necessary?
3. What's the difference between what a LangGraph checkpointer persists and what the Voxel world's own state represents? Why can't the first one substitute for the second?
4. Why is `MockChatModel.bind_tools` accept-and-ignore instead of raising?
5. Name the one HTTP header that makes a single Jaeger trace span both the C# gateway and the Python service. What OTel instrumentation call injects it, and what call extracts it on the other side?
6. Why do mock and live embeddings share a dimension (768) across every provider, and what does that choice NOT save you from having to redo?
7. What's the actual difference between the `plumbing` and `quality` eval-judge tiers, and why does only one of them run in CI?
8. Why was moving/recreating the `v1.0.0` git tag safe, when CLAUDE.md forbids "changing git history"? What's the actual distinction?
9. Walk through, in order, the three genuinely different problems in the Groq live-mode saga. What made each one look like the same symptom at first?
10. What's the cost-tier contract for `graph-tools`/`graph-free`, in one sentence, and where in the codebase is that rule actually enforced (not just documented)?
11. Why does `build_graph(with_rag=True)` produce a structurally different compiled graph rather than one graph with a runtime flag?
12. What does "the capability honestly does not exist" mean concretely, for the tool pipelines, when `TOOLBOX_URL` is unset?

---

## Part 19: What's Honestly Not Done — Say This Plainly, Never Oversell It

- Streaming on the OpenAI-compatible surface (`stream: true` accepted but not honored — always non-streaming).
- Auth and rate-limiting at the gateway (explicit "future middleware" comment in `Program.cs`).
- LangGraph conversation memory (`thread_id` reserved in the contract since v1; designed in depth in doc 023 and `AI_Implementation_Plans/005`; not yet implemented).
- Any real cloud deployment (everything runs via `docker-compose` on a developer machine; Azure AKS/ACA deployment is a named, deliberately deferred future plan).
- The full (non-plumbing-tier) eval suite wired into CI as a real gate against live-model quality regressions — only the deterministic plumbing tier runs in CI today.

Say these the way this document says them: specifically, and as *decisions*, not gaps you forgot about. That framing is itself worth points.

---

## Index — Where to Go Deeper

| Topic | Doc |
|---|---|
| Foundations, AI integration basics | 001, 002 |
| C# gateway / .NET | 003, 011 |
| HTTP contracts, encoding | 004, 014 |
| Docker | 005 |
| LangChain/LangGraph, full depth | 006, 007, 009, 010, 013 |
| Databases | 008 |
| pgvector + RAG | 012 |
| Answers to your own past comments (a great "how far I've come" read) | 015 |
| Directing AI effectively | 016 |
| Plan 001 review guide | 017 |
| Observability + evals, deep | 018, 019, 020 |
| Plan 003 (tools, providers, cost, Azure onboarding) | 021 |
| Release & publishing mechanics | 022 |
| Agent memory & stateful-tool grounding | 023 |
| **This capstone** | **024** |
| Resume-ready facts sheet (structured, reusable verbatim) | `Documentation/Project_Captures/001` |
| Full release saga (Stages 1–5, including the three-problems Groq fix) | `Documentation/AI_Implementation_Plans/004` |
| Memory implementation plan (designed, Stage 3 complete, not yet built) | `Documentation/AI_Implementation_Plans/005` |
