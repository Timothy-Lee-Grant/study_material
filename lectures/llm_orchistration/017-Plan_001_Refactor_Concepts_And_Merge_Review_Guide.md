2026_07_11_13_33-Plan_001_Refactor_Concepts_And_Merge_Review_Guide

# Plan 001 Refactor: Concepts, Architecture Patterns, and Merge Review Guide

**Audience:** Timothy, acting as the reviewing senior engineer for the plan 001 branch.
**Companion documents:** `Documentation/AI_Implementation_Plans/001-Initial_Project_Cleanup.md` (the chronological log of every step, decision, and deviation) and `CONTRACTS.md` (the wire contract this whole refactor is built around).
**Purpose:** give you everything you need to (1) *understand* what changed and why, (2) *judge* it the way a senior reviewer would, and (3) *merge* it with confidence.

---

## Part 1 — The One-Paragraph Story

Before this refactor, the system was a collection of services that knew *about* each other but had no *agreements* with each other. A rename in one Python file silently broke five others; the gateway had never successfully forwarded a request; CI was green while testing nothing. The refactor's real product is not any single feature — it is the introduction of **contracts and honest verification** at every boundary: a written wire contract, a single dispatch registry, a gateway that actually proxies, tests that actually import your code, and an acceptance script that actually exercises the claims. The features (working RAG, working graphs, working OpenWebUI path) fell out of that discipline.

---

## Part 2 — Architecture: Before and After

### Before

```
OpenWebUI ──────────────► langchain_service (stub reply, hardcoded)
                               │  import * spaghetti
User ────► dotnet controller ──X──► POST /api/chat   (endpoint never existed)
                               │
                          pgvector  (duplicate rows every restart)
                          LangGraph (won't import: dead symbols)
CI: green (installed nothing, tested nothing)
```

### After

```
                 ┌────────────────────── DEV/TEST PATH (:5001, delete-able) ─────────┐
                 │                                                                    ▼
User/OpenWebUI ──► dotnet gateway (:5000)                                    langchain_service
                 │  telemetry middleware                                     ┌──────────────────┐
                 │  [future: auth]                                           │ Flask (create_app)│
                 │  [future: rate limit]                                     │   │ validate      │
                 └─► YARP ── /api/llm/{**} ──strip prefix──────────────────► │   ▼               │
                       └──── /v1/{**} ─────────────────────────────────────► │ REGISTRY          │
                                                                             │  chat-basic ──────┼─► chain
                                                                             │  chat-rag ────────┼─► chain + retriever
                                                                             │  graph-basic ─────┼─► compiled graph
                                                                             │  graph-rag ───────┼─► compiled graph + retrieve node
                                                                             └───────┬───────────┘
                                                                    ModelFactory ────┤ PromptFactory
                                                                                     ▼
                                                              vector_store (pgvector) + Ollama (live) / fakes (mock)
```

The startup order is now *encoded in compose*, not hoped for:
`pgvector healthy → langchain ingests, serves, reports healthy → gateway starts → OpenWebUI starts`.

---

## Part 3 — The New Patterns, Personified

Your learning style asks for characters. Here is the cast this refactor hired.

### 3.1 The Treaty — `CONTRACTS.md` (contract-first design)

**Who:** A diplomat's treaty, signed by both services and posted on the wall.
**Problem it solves:** Your old comment in `LlmController.cs` asked: *"C# names things PascalCase, other languages differ — how do I make this not fragile?"* The answer is that field names are not a code-style question; they are a **treaty term**. The treaty says snake_case on the wire, and each nation (C#, Python) maps its internal customs to the treaty at its own border (C# via `JsonNamingPolicy.SnakeCaseLower`, Python natively).
**The discipline that matters:** changes are *additive only* within v1 — new optional fields, never renames. That single rule is what lets clients keep working while the system grows (`attachments`, `thread_id` are already reserved).
**Interview relevance:** "How do services evolve without breaking each other?" — additive contract evolution is the standard answer (same idea as protobuf field rules).

### 3.2 The Maître d' — the pipeline registry

**Who:** The maître d' of a restaurant. Guests (HTTP routes, OpenWebUI model ids) never walk into the kitchen; they give a name to the maître d', who knows every kitchen station.
**Problem it solves:** Before, routes imported worker functions directly — adding a capability meant touching the API layer, the worker file, and the OpenAI stub. Now: `PIPELINES` is one dict. A route is a shim that says `get_pipeline(id).handler(request)`. `/v1/models` is *generated* from the dict, so registering `agent-rag-v2` instantly makes it selectable in OpenWebUI with zero route changes.
**This answers your scalability questions from Stage 2:** upgrade = register v2 beside v1, A/B, delete a line to retire. New capability (photo parsing) = new registry entry or new graph node. The registry is the growth surface.
**Judge it by:** `app/orchestration/registry.py` (~40 lines). If you can read it in one pass, it's doing its job — dispatch tables should be boring.

### 3.3 The Front Desk — YARP gateway (proxy, not orchestrator)

**Who:** A hotel front desk. It checks you in (telemetry now; auth/rate-limit later) and *directs* you to your room. It does not carry your luggage into the room, unpack it, repack it, and carry it back out — that's what the old controller did (deserialize → transform → re-serialize → forward → wrap), and it's where 4 of its bugs lived.
**Problem it solves:** The old code duplicated the contract inside C# DTOs. The proxy holds *no* copy of the contract — it forwards bytes. Fewer places to be wrong.
**The mental model that matters:** the ASP.NET middleware pipeline order IS the architecture: `telemetry → [auth] → [rate limiter] → YARP forwarder`. Cross-cutting concerns are middleware in front of the proxy step; YARP itself only matches routes (`/api/llm/{**}` with prefix strip, `/v1/{**}` verbatim) and forwards to the `langchain` cluster.
**Config-over-code:** routes live in `appsettings.json`, overridable with double-underscore env vars (`ReverseProxy__Clusters__langchain__Destinations__primary__Address`). That's the idiomatic ASP.NET config layering, not a custom mechanism.
**Interview relevance:** "What does an API gateway actually do?" — you now have a concrete, personal answer with the middleware-order insight.

### 3.4 The Two Doors — one set of endpoints, two network paths

**Who:** A theater with a stage door and a main entrance leading to the same stage.
The four canonical routes exist once, in Flask. `:5001` (compose port mapping) is the stage door — direct, dev-only. `:5000/api/llm/*` is the main entrance — through the front desk. **Production lockdown = deleting one line in docker-compose** (the `5001:5000` mapping). Security posture as configuration, not as a code fork.

### 3.5 The Fingerprint — deterministic IDs and idempotent ingestion

**Who:** A fingerprint. A document's identity IS its content: `id = sha256(page_content)`.
**Problem it solves:** `add_documents` with no ids = new UUIDs every call = duplicate rows every restart (your pgvector had been silently accumulating copies). With content-derived ids, re-ingestion upserts: N restarts, one row per unique document.
**The concept underneath — idempotency:** an operation you can safely run twice. Distributed systems are built out of idempotent operations because *retries are inevitable*. This tiny pattern (derive the key from the content) is the same one used in dedup stores and content-addressable systems (git itself: a blob's hash is its content).
**Interview relevance:** high. "How do you make an ingestion pipeline safe to re-run?" is a real system-design probe.

### 3.6 The Stunt Double — DeterministicFakeEmbeddings (mock mode grows teeth)

**Who:** A stunt double who is the same height and build as the star. `DeterministicFakeEmbeddings(size=768)` — 768 deliberately matches nomic-embed-text, so mock and live rows share one pgvector schema.
**Problem it solves:** Old mock mode short-circuited RAG entirely (`return []`) — the RAG path was untestable without Ollama. Now the ONLY thing mock mode changes is which embedding model the factory returns. pgvector, ingestion, similarity search: all real, all CI-able.
**Companion pattern — per-mode collections** (`company_policies_mock` / `company_policies_live`): both modes share a docker volume, and fake vectors must never be candidates in a live similarity search. Isolation by namespace, not by hope.

### 3.7 The Court Stenographer — LangGraph state and the `add_messages` reducer

**Who:** A stenographer who *appends* to the transcript. Nodes don't rewrite history; they submit additions.
**The concept:** each node returns a *partial* state update. Most fields merge last-write-wins; `messages` is annotated with the `add_messages` **reducer**, so `{"messages": [x]}` appends (deduped by id) instead of overwriting. This is the rail that multi-turn memory will ride on when the checkpointer arrives — the parameter for it is already threaded through `build_graph`.
**Companion pattern — conditional wiring:** RAG vs non-RAG graphs are built by *wiring different edges at build time*, not by a runtime `if` inside a node. The compiled graph contains only the steps it runs. Compare: configuration at construction vs branching at execution — the former is easier to reason about, visualize, and test.
**Concurrency answer (your Stage 2 Q5):** graphs compile once at startup and are shared *statelessly*; every `.invoke()` carries its own state dict. Two users on one graph are two calls to a pure-ish function.

### 3.8 The Factory Rule — `create_app()` and the process model

**Who:** A car factory vs a single hand-built car. `create_app()` builds a fresh, fully-wired Flask app on demand — tests build their own; gunicorn builds one per worker.
**The process model (worth studying — this is real production shape):**

| Process | Runs | Why |
|---|---|---|
| entrypoint.sh (PID 1 → exec gunicorn) | RAG ingestion, once | before any worker exists → no request can race a half-populated store; no per-worker double-ingest |
| each gunicorn worker | `wsgi.py`: `initialize()` + `create_app()` | forked processes must each own their DB connection pool — pools cannot be shared across forks |
| tests | `create_app()` only | app construction never touches the DB, so unit tests need zero containers |

**Your old dockerfile TODO answered:** uvicorn is an ASGI server (async frameworks — FastAPI/Starlette). Flask is WSGI (synchronous). Its production server is gunicorn. `exec gunicorn` makes gunicorn PID 1 so docker's SIGTERM reaches it directly (clean shutdown).

### 3.9 The Honest Scale — tests and CI that measure something

**Who:** A scale that was reading "0 kg" for everything, now calibrated.
**What was wrong:** CI's `if [ -f requirements.txt ]` checked the repo root — no file there — so it installed nothing and "passed" on `assert True`. This is the single best story in the branch: *a green pipeline is a claim, and claims need to be falsifiable.*
**What replaced it:** 18 tests. The technique worth internalizing is in `test_api_contract.py`: retrieval is monkeypatched **on the `vector_store` singleton** — because pipelines, graph nodes, and routes all hold references to that one object, one patch covers every path, making even the RAG routes container-free. Tests are tiered deliberately: unit (no containers, CI) now; integration (real pgvector) belongs to the acceptance script; live semantics to Step 10's live pass.

---

## Part 4 — Complete Change Inventory (the merge diff, file by file)

### langchain_service

| File | Status | What/why |
|---|---|---|
| `app/api/FlaskServer.py` | rewritten | registry-driven routes, contract errors (400/404/502/500), real `/v1/*`, `create_app()` |
| `app/orchestration/contracts.py` | new | dataclass mirrors of CONTRACTS.md §1/§2 |
| `app/orchestration/registry.py` | new | `PIPELINES`, `register`, `get_pipeline`, `UnknownPipelineError` |
| `app/orchestration/pipelines.py` | new | 4 pipelines; shared chain body; graphs compiled once at import |
| `app/orchestration/OrchestrationLogic.py` | deleted | → `old_implementations/OrchestrationLogic_v1.py` |
| `app/rag/vector_store.py` | new | `VectorStoreManager`: explicit init, deterministic ids, `find_similar(score_threshold)` |
| `app/rag/seed_documents.py` | new | data-only seed docs (typo fixed) |
| `app/rag/Ingestion.py` | rewritten | thin: initialize + idempotent upsert (v1 → `old_implementations/Ingestion_v1.py`) |
| `app/models/factory.py` | edited | dead import fixed; `MockChatModel.response_pool`; fake embeddings (768); loud failure on pull error; param bug fixed |
| `app/prompts/MyPromptTemplates.py` | edited | dead `("placeholder", "{message}")` removed |
| `app/graph/state.py` | rewritten | slimmed `ChatState`; `desired_model` typo fix; reducer explained |
| `app/graph/nodes.py` | rewritten | `retrieve`/`agent`/`respond`; policy nodes → `old_implementations/graph_policy_nodes_v1.py` |
| `app/graph/build_graph.py` | rewritten | `build_graph(with_rag, checkpointer=None)`, conditional wiring |
| `main.py` | rewritten | local-dev entry only; ingestion before serve; no debug reloader |
| `wsgi.py`, `entrypoint.sh` | new | per-worker init / once-only ingestion (see 3.8) |
| `dockerfile` | rewritten | python 3.11-slim, layer-cache-friendly, gunicorn CMD |
| `.dockerignore` | new | `.venv` was being copied into every image |
| `requirements.txt` | edited | +gunicorn (exact pinning deferred to lock-file follow-up — see Part 6) |
| `requirements-dev.txt`, `conftest.py`, `tests/*` | new | 18 tests; `test_fake.py` deleted |

### server (gateway)

| File | Status | What/why |
|---|---|---|
| `Program.cs` | rewritten | YARP from config; middleware order documented; `/healthz`; controllers services removed |
| `appsettings.json` | edited | `ReverseProxy` routes/cluster |
| `TelemetryMiddleware.cs` | edited | was an empty skeleton; now logs method/path/status/elapsed_ms |
| `controllers/*` | deleted | → `old_implementations/{LlmController_v1,TestController_v1}.cs` |
| `server.csproj` | edited | `<Compile Remove="old_implementations/**" />` |

### Repo root

| File | Status | What/why |
|---|---|---|
| `CONTRACTS.md` | new | the treaty (Part 3.1) |
| `docker-compose.yaml` | edited | OpenWebUI → gateway; healthchecks; dependency ordering; lockdown comment |
| `scripts/acceptance_check.sh` | new | scripted acceptance pass, criteria 1–4 automated |
| `.github/workflows/ci.yml` | rewritten | honest install + pytest; C# build/test job restored |
| `persona.md` | edited | phase-2 project description + skills |

**Breaking changes to remember:** old `/test/langchain/*` routes are gone (canonical routes replace them); response shape is the contract shape; `user_requested_model` → `requested_model`; the gateway no longer exposes `/api/Llm` or `/api/Test`.

---

## Part 5 — How to Judge This Branch (a senior reviewer's checklist)

Review in *dependency order*, not file order — the same order the plan executed:

1. **Read `CONTRACTS.md` first.** Everything else claims to implement it. As you read each later file, the only question is "does this match the treaty?"
2. **`registry.py` + `contracts.py`** (5 min). These are the load-bearing abstractions. Check: is there any way to reach a pipeline *around* the registry? (There shouldn't be.)
3. **`pipelines.py`**. Check the shared bodies (`_run_assistant_chain`, `_run_graph`) — shared plumbing, distinct intent. Confirm metadata is honest (pipeline_id matches, sources only when retrieval ran).
4. **`vector_store.py`**. Check the three promises: no import-time side effects; ids are content-pure; per-mode collections. These carry acceptance criterion 4.
5. **`FlaskServer.py`**. Thinness test: if you find business logic here, flag it. Error paths: do the §3 codes match the HTTP statuses?
6. **`Program.cs` + `appsettings.json`**. Smallness is the feature. Confirm the middleware order comment matches the code order.
7. **Process model files** (`entrypoint.sh`, `wsgi.py`, `dockerfile`, compose). Trace one worker's lifetime: who ingests, who connects, who serves.
8. **Tests + CI.** Run them. Then do the reviewer's power move: *break something on purpose* (e.g., change a metadata field name in `contracts.py`) and confirm a test fails. A suite that can't fail is decoration.
9. **The Stage 4 log.** Every deviation from the plan is flagged there (placeholders in Step 4, env-var mechanism in Step 7, deferred pinning in Step 9). Judge whether each flagged deviation was reasonable — that's exactly what you'd do to a human teammate's PR description.

**Questions worth asking me (things a reviewer could legitimately push back on):**
- Graph pipelines resolve `model_used` from env/request rather than asking the node's model object (small honesty gap in metadata — defensible, but debatable).
- `RuntimeError → 502` mapping is coarse; a dedicated `UpstreamModelError` exception type would be cleaner.
- The live-mode silent fallback to `MockChatModel` when a chat-model pull fails (pre-existing behavior, deliberately left) — arguably should be a loud 502 like embeddings now are.
- Flask errorhandler for generic `Exception` returns 500 even for programming errors during request parsing — acceptable, but some teams prefer letting those crash in dev.

---

## Part 6 — Merge Procedure

Pre-merge gates (in order; stop at any failure):

1. `cd langchain_service && python -m pytest -v` → 18 green.
2. `cd server && dotnet build` → compiles (my sandbox couldn't run dotnet; this is the one thing I never executed).
3. `./build.sh --mode mock && bash scripts/acceptance_check.sh mock` → summary shows 0 failed.
4. OpenWebUI manual check (criterion 5) — this also settles the `stream: true` watch-item.
5. `./build.sh --mode live && bash scripts/acceptance_check.sh live` → 0 failed; eyeball the RAG vs basic side-by-side.
6. Paste results into Stage 5 of plan 001 (the matrix is scaffolded).

Then merge — per your rules, as a new commit (no history rewriting). A merge commit (`git merge --no-ff`) is a good fit here: it preserves the step-by-step commit story of the branch while marking the integration point.

Post-merge follow-ups (already logged in Stage 5 as deferred, not failures):

| Item | Trigger | Effort |
|---|---|---|
| `requirements.lock` via `pip freeze` from the working container; switch dockerfile + CI to it | after first verified build | one command + 2 one-line edits |
| Single-chunk SSE wrapper for `/v1/chat/completions` | only if OpenWebUI won't render non-streamed replies | ~20 lines |
| Confirm pgvector upsert semantics | criterion 4 output (2 → 2 confirms) | none if green |
| `.gitignore` for `__pycache__` + untrack stale `.pyc` | anytime | trivial |

---

## Part 7 — What You Should Be Able to Explain Afterward (self-test)

If you can answer these cold, you own this branch — and most of them are interview questions in disguise:

1. Why does additive-only contract evolution prevent breaking clients, and what's the protobuf analogy?
2. Why is the registry a dict of handlers rather than an `if/elif` in the route — what specifically gets easier?
3. Trace a request from OpenWebUI to pgvector and back, naming every process boundary it crosses.
4. Why must each gunicorn worker create its own connection pool? What goes wrong if a pool is shared across a fork?
5. Why is `sha256(content)` as a document id idempotent, and where else does content-addressing appear in tools you use daily?
6. What does the `add_messages` reducer change about how state merges, and why does memory depend on it?
7. Why did mock mode get *more* real (fake embeddings + real pgvector) instead of *less* (stub everything)? What does that buy CI?
8. What made the old CI green, and what one YAML line made it honest?
9. Why is deleting the `5001:5000` port mapping a complete production lockdown?
10. In the middleware pipeline, why must the rate limiter sit *before* the YARP forwarder?

---

*Written as part of plan 001 Stage 4/5 handoff. The chronological decision log, including every flagged deviation, lives in `Documentation/AI_Implementation_Plans/001-Initial_Project_Cleanup.md`.*
