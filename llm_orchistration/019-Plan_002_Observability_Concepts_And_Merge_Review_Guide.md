2026_07_12_16_46-Plan_002_Observability_Concepts_And_Merge_Review_Guide

# Plan 002 (Observability & Evaluation): Concepts, Patterns, and Merge Review Guide

**Audience:** Timothy, reviewing the plan 002 branch as the senior engineer who will merge it.
**Companions:** `002-Metrics_and_Observability.md` (the decision log — every step, deviation, and known-unknown), `018-Observability_And_AI_Evaluation_Concepts_For_Plan_002.md` (the theory this plan implemented), and `017-...` (the same guide for plan 001, whose patterns this branch builds on).
**Structure:** Part 1 orients; Parts 2–8 teach the concepts you're most likely to struggle with, each anchored to the exact file where it lives; Part 9 is the change inventory; Part 10 the review checklist; Part 11 the merge procedure; Part 12 the self-test.

---

## Part 1 — What This Branch Actually Is

Plan 001 made the system *correct* (contracts, registry, tests). Plan 002 makes it *legible*: every request now leaves a story behind — a trace tree across both services, metrics aggregating into dashboards, the full prompt and retrieved chunks in Langfuse — and two eval harnesses turn "is it good?" from a feeling into a number with a regression gate in front of it.

The single most important architectural sentence: **all instrumentation attaches at seams plan 001 built** — the registry boundary (every pipeline traced+metered by `register()` itself), the middleware pipeline (gateway root span), `find_similar` (retrieval span). No pipeline author ever writes a span. When you add tools or memory in plan 003, they will be observable *before you finish writing them*.

The second most important sentence: **everything heavy is behind `./build.sh --obs`** (compose profile, same mechanism as `live`), and the codebase contains exactly ONE enable/disable check (in `observability.py`). How that single gate can control spans created all over the codebase is Part 2 — the concept most likely to look like magic until it doesn't.

---

## Part 2 — The OTel API/SDK Split (the "no-op tracer" trick)

**File:** `langchain_service/app/observability.py` (the docstring is the canonical explanation), used by `registry.py` and `vector_store.py`.

**The puzzle:** `registry.py` creates a span on *every* dispatch, unconditionally. There's no `if enabled:` anywhere near it. Yet with observability off, there is zero network traffic and effectively zero cost. How?

**The concept:** OpenTelemetry is split into an **API** (always importable, hands out spans) and an **SDK** (the machinery that makes spans real: provider, batch processor, OTLP exporter). If nobody configures a provider, the API hands out **no-op spans** — objects with the right methods that do nothing, costing nanoseconds. `init_observability()` is the only place the SDK is configured, and it only runs when `OBSERVABILITY_ENABLED=true`.

**Personified:** the API is a mailbox bolted to every wall of the building. The SDK is the postal service. With no postal service contracted, dropping a letter in a mailbox is harmless and free — the letters just evaporate. Application code gets to assume mailboxes exist everywhere; ONE contract (the provider) decides whether mail moves.

**Why it matters beyond this repo:** this is the standard pattern for making libraries observable without forcing observability on users — it's why langchain, flask, etc. can be OTel-instrumented internally. Also why our unit tests exercise instrumented code paths for free.

**Common mistake it prevents:** scattering `if os.getenv("OBSERVABILITY_ENABLED")` through business logic — the grep in the Step 3 log proves we have exactly zero of those outside the gate module.

## Part 3 — Distributed Tracing Mechanics: One Header, Two Services

**Files:** `server/Program.cs` (the `AddHttpClientInstrumentation` comment), `app/observability.py` (FlaskInstrumentor), `observability/otel-collector-config.yaml`.

Chain of events for one request, worth tracing by hand once:

```
1. curl hits gateway :5000 ── AspNetCore instrumentation opens ROOT span
                              (trace_id=abc123 is born here)
2. YARP forwards via HttpClient ── HttpClient instrumentation opens a child span
   AND injects header:  traceparent: 00-abc123-<parent_span_id>-01
3. Flask receives ── FlaskInstrumentor EXTRACTS traceparent, so its server span
   says "my parent is <parent_span_id> in trace abc123" — CONTINUING, not starting
4. pipeline.dispatch and rag.retrieve nest under it (same trace)
5. Both services push spans (batched, OTLP) to the collector — independently,
   asynchronously, not knowing about each other
6. Jaeger reassembles the tree from ids alone
```

**The insight people miss:** the two services never coordinate. Nobody "sends the trace" anywhere as a unit. Each process ships its own fragments, and the *ids* are the glue. That's why the failure mode is so specific: if propagation breaks (step 2 or 3), you get two perfectly healthy-looking traces instead of one — everything works except the JOIN.

**Also in this part:**
- **The collector as indirection** (mail-sorting office): services export OTLP and know nothing else; swapping Jaeger→Tempo→Azure Monitor is a change to one YAML file. Note the deliberate ABSENCE of a metrics pipeline in the collector config — see Part 4.
- **Log↔trace join:** `TelemetryMiddleware` logs `trace_id` from `Activity.Current`. Concept: `Activity` is .NET's *built-in* span type — ASP.NET creates one per request even with OTel absent; OTel is "just" the exporter. Grep a slow request in logs → paste the id into Jaeger → land on its span tree. That's the three pillars linked.
- **Proxy tracer detail** (subtle): `observability.py` calls `trace.get_tracer(...)` at import time, *before* any provider exists. It works because the API returns a lazy proxy that binds to whichever provider is set later. Without this, import order would be a minefield.

## Part 4 — Push vs Pull: Two Transport Models, On Purpose

**Files:** `otel-collector-config.yaml` (push side), `observability/prometheus.yml` + `/metrics` endpoints (pull side).

| | Traces (PUSH) | Metrics (PULL) |
|---|---|---|
| Who initiates | The service exports when it has data | Prometheus scrapes on ITS schedule |
| Failure mode | Exporter buffers/drops if collector down | A DOWN target — visible in /targets |
| Why this fits | Spans are bursty, per-request, batched | Metrics are steady-state aggregates |
| Cost when idle | Batch processor overhead (tiny) | literally zero — nobody calls /metrics |

The pull model is why `/metrics` is **never gated**: exposing it costs nothing unless someone scrapes, and only the obs profile runs a scraper. Contrast with spans, which are push and therefore need the provider gate. If you can articulate *why each pillar uses its transport*, you understand both — a genuinely common interview probe ("why does Prometheus pull?").

## Part 5 — Metrics Concepts You'll Hit in This Diff

**Files:** `app/metrics.py` (docstring = canonical), `registry.py` wrapper, `gunicorn.conf.py`, `entrypoint.sh`, the Grafana dashboard JSON.

**5.1 Cardinality (the trap).** A metric with labels is not one time series — it's one series *per unique label combination*. `pipeline_id` (4 values) → 4 series per metric: fine. `user_id` (unbounded) → unbounded series: detonates the store. Hence the rule enforced in this branch: user-level questions belong to TRACES (span attributes are per-request, not per-series), aggregate questions to METRICS. The comment sits in `metrics.py` at exactly the place a future you would be tempted.

**5.2 Histograms and quantiles.** `llm_request_duration_seconds` is a histogram: counters per bucket ("how many requests finished under 0.1s, under 0.5s, ..."). p95 is *computed at query time* by Grafana/Prometheus (`histogram_quantile(0.95, rate(..._bucket[5m]))`) — the service never calculates percentiles. Why buckets instead of storing an average? Averages lie (one 60s outlier hides in a thousand 50ms requests); buckets preserve the distribution's shape cheaply. Our buckets run 10ms→120s because mock answers in milliseconds and live models in tens of seconds — a bucket layout that only fits one mode would blind you in the other.

**5.3 The gunicorn multiprocess problem (the branch's best systems lesson).** Forked workers have separate memory → separate counters → a scrape hits ONE worker and the numbers bounce depending on who answered. This is invisible in dev (single process) and maddening in prod. The fix chain: `PROMETHEUS_MULTIPROC_DIR` (workers write shared mmap files; cleared each boot in `entrypoint.sh` so stale files don't double-count) → `MultiProcessCollector` in the `/metrics` handler (aggregates across files per scrape) → `child_exit` hook in `gunicorn.conf.py` (marks dead workers so their state stops being reported). If you tell this story in an interview — symptom, cause, three-part fix — you sound like someone who has operated Python in production.

**5.4 Why tokens forced a refactor.** `StrOutputParser` returns only the string — it *discards* the `AIMessage` carrying `usage_metadata`. Chains now stop at the model; `.content` is read manually; `extract_usage()` is the single definition of "token count" for chains AND the graph's agent node. Lesson: convenience wrappers can silently throw away the data you'll want next month.

**5.5 First real additive contract evolution.** `metadata.prompt_tokens/completion_tokens` — new optional fields, CONTRACTS.md updated with date and provenance, old clients unaffected, tests assert presence. The v1 additive rule, exercised rather than just stated.

## Part 6 — The Langfuse v3 Stack (why six containers is not bloat)

**File:** the `docker-compose.yaml` Langfuse block.

You chose v3 full stack at the decision point. What each piece is FOR (this is a production event-pipeline in miniature — learn it as such):

| Container | Role | The concept it teaches |
|---|---|---|
| langfuse-web | UI + ingestion API | receives events, writes them to S3 FIRST, queues a reference in Redis, returns fast |
| langfuse-worker | async processor | pulls from queue, ingests into ClickHouse — ingestion spikes never block reads |
| langfuse-postgres | transactional data (users, projects, keys) | OLTP: small rows, many small reads/writes |
| clickhouse | traces/observations/scores | **OLAP**: columnar, built for "aggregate millions of rows" analytics — the same OLTP/OLAP split from your 018 reading, physically visible |
| langfuse-redis | queue + cache | decouples receive-rate from process-rate |
| minio | local S3 | events durably parked BEFORE processing → a crashed worker loses nothing (recoverability by write-ahead) |

That S3-first-then-queue-then-OLAP shape is the standard high-volume event pipeline (same skeleton as analytics systems everywhere). Running it locally, behind a flag, is a better systems education than a diagram of it.

**Three compose techniques in the diff worth knowing:**
- **YAML anchor** (`&langfuse-env` / `*langfuse-env`): web and worker share one env block — one definition, two consumers, drift impossible.
- **Headless initialization** (`LANGFUSE_INIT_*`): org/project/user/API keys exist from boot. This is the OpenWebUI found-issue-3 lesson (env seeds only first boot; volumes remember) applied *proactively* — third time this lesson appears in the repo, now as prevention rather than diagnosis.
- **Deliberate DB separation:** Langfuse gets its own Postgres so its migrations can never touch RAG data. Blast-radius thinking.

**Prompt versioning seed:** every generation records `prompt_version` (`assistant.friendly@1`, `judge.faithfulness@2`). The rule: bump on ANY template text change. This is what makes future eval scores *attributable* — "quality dropped" becomes "quality dropped when assistant.friendly went @2 → @3".

**Your B3 idea, honored:** every generation carries a `thread_id` field (null until memory exists). Schema designed for implicit-feedback mining before the feature exists — say that sentence in interviews.

## Part 7 — The Eval Harness: Tiers, Baselines, Gates, Calibration

**Files:** `eval/` package: `dataset.py`, `eval_retrieval.py`, `eval_judge.py`, `thresholds.json`, `golden/`, `rubric.md`, `calibration.jsonl`.

**7.1 The two-tier principle (one idea, applied twice).** Mock embeddings are deterministic but semantically meaningless; the mock judge returns canned verdicts. So each eval splits: a **plumbing tier** (CI, zero containers) proving the *machinery* — dataset parses, ranking math right, prompt renders, verdict parses, determinism holds — and a **quality tier** (live, manual/nightly) producing *real numbers*. The plumbing tier even prints a disclaimer about its own meaninglessness every run. Knowing which tier answers which question is the whole trick; conflating them is how teams end up trusting fake numbers.

**7.2 The metrics you now own** (hand-rolled, ~10 lines total): `hit@k` — did any expected doc make the top k; `MRR` — mean of 1/rank of the first expected doc (rewards putting the right chunk FIRST, because context order affects generation). g003 in the golden set is the deliberately hard paraphrase row — its gap vs g001 in live mode *is the measurement* of semantic-vs-keyword retrieval.

**7.3 Baselines as contracts.** `--save-baseline` commits a JSON of current scores; `--gate` fails CI if scores drop below baseline−tolerance. The committed baseline is a *quality contract* exactly like CONTRACTS.md is a wire contract. Tolerances differ per tier for documented reasons: plumbing 0.0 (deterministic → any change is a bug), quality 0.05 (live wobble). The CI gate is **self-arming**: ungated until a baseline exists in the repo, enforced automatically forever after — no "remember to turn on the gate" step to forget.

**7.4 Judge calibration (the anti-gullibility device).** The judge is a model: verbose-answer bias, self-phrasing bias, inconsistency. So: the **rubric** (injected into the prompt from `rubric.md` — single source, versioned) tells it how to score; **anchors** (few-shot, IN the prompt) show it; the **calibration set** (held OUT of the prompt, scored by YOU) measures whether judge≈human. The held-out-ness is load-bearing: anchor rows that leak into calibration measure memorization, not agreement. Until exact-match/MAD look decent on rows you scored, judge numbers are opinions.

**7.5 The fire-alarm principle (criterion f).** An alarm you've never tested is decoration — same reasoning that exposed the assert-True CI in plan 001. The acceptance pass *requires* inducing a regression and watching the gate fail. Verification of the verifier.

---

## Part 8 — Smaller Things You'll Trip Over in the Diff

- **Compose profiles compose:** `--profile live --profile obs` is a UNION. `build.sh --obs` just adds a profile flag + exports `OBSERVABILITY_ENABLED` — mechanically identical to how `live` already worked.
- **Floating versions everywhere new:** `Version="*"` (csproj) and unpinned pip lines are the no-guessed-pins policy: resolve against reality, then lock (`RestorePackagesWithLockFile` is already set; `pip freeze` command in the Stage 4 log). Guessing pins from memory breaks builds *immediately*; floating breaks them *eventually*; locks from a resolved environment never do.
- **JSONL + `#` comments:** strict JSONL forbids comments; our loader allows `#` lines so authoring guidance lives next to data. Pragmatic deviation, owned and documented in `dataset.py`.
- **Scrape-noise exclusion:** Flask instrumentation excludes `healthz`/`metrics` — otherwise the 5s probe/scrape traffic drowns real traces. Every observability rollout hits this; ours hit it preemptively.
- **Ports map:** 3000 OpenWebUI · 3001 Grafana · 3002 Langfuse · 9090 Prometheus · 16686 Jaeger · 4317/4318 collector.
- **Eval reports** (`eval/reports/`) are run artifacts — add to `.gitignore`; **baselines** (`eval/baselines/`) are contracts — commit them. The distinction is the point.

---

## Part 9 — Complete Change Inventory

### Infrastructure (repo root)
| File | Status | What |
|---|---|---|
| `docker-compose.yaml` | edited | 10 obs-profile services (collector, Jaeger, Prometheus, Grafana + 6 Langfuse); OBSERVABILITY_ENABLED + LANGFUSE_* env to app services; 5 new volumes |
| `build.sh` | edited | `--obs` flag → profile + env export + UI URL printout |
| `observability/*` | new | collector config, prometheus scrape config, Grafana provisioning + dashboard JSON (versioned files, not click-config) |
| `scripts/observability_check.sh` | new | scripted acceptance pass (criteria a–d automated via Jaeger/Prometheus/Langfuse APIs) |
| `.github/workflows/ci.yml` | edited | eval plumbing steps; self-arming retrieval gate |
| `CONTRACTS.md` | edited | §2 + prompt_tokens/completion_tokens (additive, dated) |

### Gateway (`server/`)
| File | Status | What |
|---|---|---|
| `server.csproj` | edited | 5 OTel packages (floating); lock-file property |
| `Program.cs` | edited | gated OTel: tracing (AspNetCore+HttpClient→OTLP), metrics (Prometheus exporter, /metrics) |
| `TelemetryMiddleware.cs` | edited | trace_id in every log line (log↔trace join) |

### langchain_service
| File | Status | What |
|---|---|---|
| `app/observability.py` | new | THE gate: SDK init, Flask instrumentation, Langfuse callback accessor |
| `app/metrics.py` | new | 3 instruments + multiprocess-aware /metrics payload |
| `app/orchestration/registry.py` | edited | dispatch wrapper = span + all metrics + error path (one boundary, both pillars) |
| `app/orchestration/contracts.py` | edited | token fields + to_dict |
| `app/orchestration/pipelines.py` | edited | usage capture (no StrOutputParser), `_invoke_config` (Langfuse callbacks, tags, prompt_version, thread_id) |
| `app/graph/state.py`, `nodes.py` | edited | token fields through the graph; agent_node raw-message invoke |
| `app/prompts/MyPromptTemplates.py` | edited | version constants; judge prompt @2 (rubric-injected) |
| `app/prompts/mock_prompts.py` | edited | second judge verdict (colon-in-rationale parser case) |
| `app/api/FlaskServer.py` | edited | /metrics route |
| `wsgi.py`, `main.py`, `entrypoint.sh`, `gunicorn.conf.py` | edited/new | per-worker OTel init; multiproc dir lifecycle; child_exit hook |
| `eval/*` | new | dataset loader/validators, golden v1 (3 worked + your slots), rubric, calibration, retrieval + judge runners, thresholds |
| `tests/*` | +6 files' worth | **suite 23 → 39** (metrics, observability gating, datasets, retrieval eval, judge eval, token fields in contract asserts) |
| `requirements.txt` | edited | +otel×3, prometheus-client, langfuse (floating until lock) |

**Breaking changes: none.** Additive contract fields only; default (no `--obs`) behavior is byte-for-byte plan-001 (criterion g exists to prove it).

---

## Part 10 — How to Judge This Branch (review checklist, dependency order)

1. **`app/observability.py` first** — everything claims "the gate lives here." Then run the branch's own honesty check: `grep -rn OBSERVABILITY_ENABLED langchain_service/app/` must hit only this file.
2. **`registry.py` wrapper** — one boundary carrying span + metrics + error accounting. Push-back question: is the error path right? (counter increments, span records, exception re-raises so HTTP mapping stays in the API layer).
3. **`metrics.py` + process files** — trace one worker's lifetime through entrypoint → fork → scrape. If you can explain why the mmap dir is cleared at boot and what `child_exit` prevents, you own 5.3.
4. **Compose obs block** — check profile isolation (nothing new outside `profiles: ["obs"]`), the anchor, the UTC pins, DB separation rationale.
5. **`Program.cs`** — gating symmetric with Python? OTLP endpoint logic identical? (It should mirror.)
6. **`eval/` package** — read `dataset.py` validators as a contract; then the two runners' tier split; then thresholds.json's per-tier reasoning.
7. **Run everything:** 39 tests; both plumbing runners; then the *reviewer's power moves*: (i) fire-alarm drill (criterion f), (ii) corrupt a golden id → schema test names the row, (iii) `--obs` off → assert container set unchanged.
8. **Legitimate push-back items** (ask me, they're defensible but debatable): graph `model_used` derived from env rather than the node's model object; Langfuse push tolerating ALL exceptions (could mask config errors — alternative is failing loudly); `/metrics` unauthenticated (fine on localhost, would need gating at the gateway if ever exposed); quality-tier tolerance 0.05 chosen by judgment, not data (it self-corrects as your golden set grows).

## Part 11 — Merge Procedure

Gates in order (stop at first failure):
1. `cd langchain_service && python -m pytest -v` → 39 green.
2. `cd server && dotnet restore && dotnet build` → resolves floating OTel packages, writes `packages.lock.json` (**commit it**).
3. Push branch → CI green: pytest + retrieval plumbing (ungated notice expected) + judge plumbing.
4. `./build.sh --mode mock --obs && bash scripts/observability_check.sh` → 0 failed.
5. Manual visuals: Grafana panels after traffic; a Langfuse trace showing rendered prompt + nested graph nodes.
6. Live pass: quality baselines saved (+ commit), judge `--calibration` run, fire-alarm drill.
7. `./build.sh --mode mock` control → plan-001 container set, tests green (criterion g).
8. Fill the Stage 5 matrix; merge with `git merge --no-ff` (same convention as plan 001; failures become Stage 5 findings, never silent re-edits).

Post-merge follow-ups (already in Stage 5's deferred list): your golden/calibration/rubric authorship; `requirements.lock` freeze + dockerfile/CI switch; Langfuse push API check; gateway dashboard panel metric name; score_threshold tuning (now unblocked by real data); nightly quality-tier scheduling.

## Part 12 — Self-Test (if you can answer these cold, merge with confidence)

1. Why can `registry.py` create spans unconditionally with no perceptible cost when observability is off? What object makes that safe?
2. Walk the `traceparent` header's journey. What *exactly* do you see in Jaeger if step 3 (extraction) silently fails?
3. Why do traces push but metrics pull? Give one failure-visibility argument for each direction.
4. Your `/metrics` shows a counter going DOWN between two scrapes on a 2-worker gunicorn. What's happening, and which three artifacts in this repo fix it?
5. Why is `user_id` a span attribute but not a metric label? What number explodes if you get this wrong?
6. Why did token counting force the removal of `StrOutputParser`? What general lesson about convenience wrappers?
7. In the Langfuse stack, why write events to S3 *before* processing them? What failure does that survive?
8. What question does the plumbing tier answer that the quality tier can't, and vice versa? Why is running retrieval eval "in CI with mock embeddings" NOT a quality measurement?
9. Why must calibration rows never appear as judge few-shot anchors?
10. What does the self-arming gate do the day you commit `retrieval_plumbing.json`, and why is criterion (f) the only proof it works?
11. Why are baselines committed but reports gitignored?
12. A quality regression appears after a merge. Using ONLY artifacts this branch added, how do you determine whether retrieval or generation is to blame, and which prompt version was involved?

---

*Written at the close of plan 002 Stage 4. The chronological log with every deviation and known-unknown is in `Documentation/AI_Implementation_Plans/002-Metrics_and_Observability.md`; Stage 5's matrix awaits your runs.*
