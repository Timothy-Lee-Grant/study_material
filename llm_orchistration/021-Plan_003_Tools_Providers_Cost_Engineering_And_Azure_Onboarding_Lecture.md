2026_07_19_18_49-Plan_003_Tools_Providers_Cost_Engineering_And_Azure_Onboarding_Lecture

# Plan 003 Lecture: Tool-Calling Agents, Multi-Provider Routing, Cost Engineering — and Your Azure Onboarding Walkthrough

**Audience:** Timothy Grant, targeting Microsoft SWE2.
**Prerequisites:** Everything through concepts doc 020 (you have them).
**Companion documents:** `AI_Implementation_Plans/003` (the decision log this lecture teaches from), `CONTRACTS.md` §4a (the tier rules this lecture explains).
**Structure:** Part I is the lecture — the concepts plan 003 quietly used, several of which sit squarely in your persona's declared gap areas (async programming, distributed systems, trusting abstractions). Part II is the hands-on walkthrough of everything YOU now need to do (Azure, Groq, `.env`, re-ingestion, Step 8 verification). Read Part I before doing Part II — the walkthrough will make ten times more sense.

---

## Executive Overview: what your system became this week

Before plan 003, LLM_Monitor was a *closed* system: a model, some retrieval, four pipelines, everything running on hardware you owned. After plan 003 it is an *open* system in three separate senses, and each opening is a different engineering discipline:

1. **Open to tools.** Your LangGraph agent can now discover and execute capabilities served by a completely separate codebase (Tool_Box, .NET, a different repo you also wrote) over a network protocol (MCP over streamable HTTP). Adding a tool to Tool_Box adds a capability here with zero code changes — you built a *plugin architecture across a process boundary*.
2. **Open to providers.** The model is no longer "the Ollama container." It's a per-pipeline *binding* resolved through a factory: Azure OpenAI, any OpenAI-compatible endpoint (Groq), or Ollama-when-you-have-hardware-again, with mock overriding everything. Model choice became configuration, then became *routing*.
3. **Open to money.** Every live token now costs real dollars, so the system grew an explicit cost architecture: tiers with contractual call-anatomy, hard caps, sampled off-clock evaluation, and dashboards that price tokens into dollars. Cost stopped being a bill you receive and became a *property you engineer*.

The interview-ready one-liner: *"I turned a single-model local chat service into a tiered, multi-provider, tool-using agent platform with contract-enforced cost anatomy and priced observability."* Every clause in that sentence is something you can now defend with code, tests, and documents. This lecture makes sure you can defend them with *understanding*.

---

## Your Personal Mindset Shift

Your persona says your background leans firmware/hardware integration, that async programming and distributed systems are declared weak spots, and — your own observation — that you hyperfixate: you feel unable to use an abstraction until you've read its source.

Here's the reframe this plan should give you, because plan 003 *practiced* the discipline you said you lack:

**Firmware thinking says:** one binary, one processor, I control the whole stack, correctness comes from knowing every layer.
**This architecture says:** five processes, three languages (Python, C#, PromQL), two network protocols (HTTP/JSON, MCP), one of which you don't control at all (Azure's API), and correctness comes from *contracts at the seams* — not from understanding every layer's internals.

Look at what we actually did with abstractions this week, because it's a middle path between your hyperfixation and blind trust, and it has a name I want you to keep: **verify the seam, trust the interior.**

- We did NOT read the MCP adapter's session-management internals. We DID download the exact wheel and verify the two facts our code depends on: the literal string `"streamable_http"` exists as a transport, and the tools it builds are async-only (`coroutine=` set, no `func=`). Twenty lines of inspection, two load-bearing facts, done.
- We did NOT read AzureChatOpenAI's request pipeline. We DID verify its parameter surface (`azure_deployment`, `api_version`, `max_tokens`) and its env-var contract before pinning the version.

That second fact from the adapter inspection — async-only tools — predicted the exact failure mode (`sync graph.invoke()` would raise) before any code was written, and dictated the design (`ainvoke` at the pipeline boundary). That's the payoff of seam-verification: you get the *load-bearing* knowledge without the three-day source spelunk. When you feel the hyperfixation pull, ask: *"which facts is my code actually standing on?"* Verify those. Trust the rest until it breaks — and build the observability so that when it breaks, it breaks loudly.

---

## Part I — The Lecture

### Module 1: MCP and the anatomy of a tool call

**The why.** An LLM is a text-completion engine. It cannot know your server's current time, and when asked, it will confidently invent one. "Tool calling" (also "function calling") is the mechanism that turns a model from a text generator into an *actor*: the model emits a structured request ("call `current_time` with args `{}`"), the *runtime* executes it, and the result is fed back as a new message for the model to incorporate.

Hold onto that division of labor, because it's the most misunderstood thing in this space: **the model never executes anything.** It only ever emits JSON saying what it *wants* executed. Your graph is the hands; the model is only the intent.

**The theory.** The message trail for one tool interaction is a little state machine:

```
HumanMessage("what time is it on the server?")
AIMessage(content="", tool_calls=[{name: "current_time", args: {}, id: "abc"}])   <- model's INTENT
ToolMessage(content="2026-07-19T18:49:03Z", tool_call_id="abc")                   <- runtime's RESULT
AIMessage("The server time is 18:49 UTC.")                                        <- model's ANSWER
```

The loop (`agent → tools → agent → ...`) is the ReAct pattern (Reason + Act). It terminates when the model emits an AIMessage with *no* tool_calls. Because a model decides termination, a *model* can also fail to terminate — which is why the loop has a mechanical cap (Module 4).

**MCP specifically.** Before the Model Context Protocol, every tool was bespoke glue code inside the agent's own repo. MCP standardizes the *seam*: a server (your ToolBox) advertises tools with names, descriptions, and JSON-Schema argument specs; any client speaking MCP can discover and invoke them. The consequence you engineered for: your agent's capability set is now defined by a *different process's* advertisement, fetched at startup (`discover_tools()`). Add a Git toolset to Tool_Box, rebuild one container, and this repo — untouched — has Git capabilities. That is the plugin architecture pattern: the host defines a discovery contract, plugins define capabilities, and neither compiles against the other.

**The implementation, and the three defenses worth naming.** Look at the `toolbox` stanza in docker-compose:

1. **No `ports:` mapping.** The toolbox is reachable *only* on the compose-internal network. From your host, `curl localhost:8080` fails — and the acceptance script asserts that failure as a PASS. Security posture as a test assertion.
2. **`AllowedHosts=localhost;127.0.0.1;toolbox`.** This is DNS-rebinding defense. A malicious webpage in your browser can't reach `toolbox` directly, but it *can* try to trick the browser: it serves a hostname whose DNS answer is switched to an internal IP after the first lookup, and then makes requests that *arrive* at the internal service carrying the attacker's hostname in the Host header. Host-header validation kills this class: any request whose Host isn't on the list gets a 400 before any handler runs. That's why the service name `toolbox` MUST be in the list — your own langchain_service addresses it by that name, and its requests carry `Host: toolbox:8080`.
3. **`depends_on: condition: service_healthy`.** Startup *ordering* as declared configuration. Your service discovers tools at boot; booting before the toolbox answers `/health` would fail. Rather than retry loops in Python, the orchestrator holds langchain_service back until the toolbox proves itself. Same discipline as pgvector — the pattern is "a dependency isn't 'started', it's *healthy*."

### Module 2: Async Python, finally load-bearing (your declared gap, in production)

**The why.** Plan 003 forced async into the codebase for one precise reason: the MCP adapter's tools only exist as coroutines. Each tool call opens an HTTP session to the toolbox, sends, awaits, cleans up — inherently I/O-bound work, and the adapter's authors chose to expose it async-only. Your graph executes those tools, so your graph must run under an event loop.

**The theory, in four sentences.** A coroutine (`async def`) is a function that can *pause* at `await` points, yielding control to an event loop, which runs other ready coroutines while the paused one waits for I/O. This is cooperative concurrency in ONE thread — no locks, no races on Python objects, because switches only happen at explicit `await`s. `asyncio.run(coro)` creates a fresh event loop, runs the coroutine to completion, and tears the loop down; it is the *bridge* from sync land to async land. The cardinal rule: `asyncio.run()` inside an already-running loop raises — you cannot bridge from async land back into itself.

**The implementation — study the three bridges, they're a map of the whole concept:**

| Where | Bridge | Why it's safe |
|---|---|---|
| `discover_tools()` (startup) | `asyncio.run(get_tools())` | Runs once at import time, in a plain sync process — no loop exists yet. |
| `_run_tool_graph` (request time) | `asyncio.run(graph.ainvoke(...))` | Gunicorn **sync workers**: each request is handled by a plain thread with no running loop, so each request creates a private loop for the graph's lifetime, then discards it. |
| `_spawn_sampled_judge` (post-response) | `threading.Thread(daemon=True)` | The judge is sync code (chain `.invoke`) that must not block the response. A thread — not a coroutine — because the response cycle is already over; there's no loop left to schedule onto. |

Notice what we did NOT do: we did not convert the service to an async framework (uvicorn/ASGI, async Flask). The system is sync-serving with *async islands*, bridged at explicit points. That's a legitimate production architecture, and knowing *why* it works (gunicorn's process/thread model means no ambient event loop) is precisely the async fluency your persona says you're missing. Interview phrasing: "I integrated an async-only client library into a sync WSGI service by bridging with `asyncio.run` at the request boundary — safe because sync workers carry no running loop — rather than rewriting the service as ASGI."

One more async citizen worth respecting: the **daemon** flag on the judge thread. Daemon threads die when the process exits — the judge can never hold a shutdown hostage. The trade: a judge mid-flight at shutdown is lost. For sampled telemetry, that's the correct trade; for money-moving work it would be the wrong one. Being able to articulate *which* is which is the skill.

### Module 3: The provider abstraction — protocol as lingua franca, config as routing

**The why.** You lost your GPU. The naive fix is sed-replacing `ChatOllama` with `AzureChatOpenAI`. The engineered fix recognizes that "which model answers" is not a code property — it's a *deployment* property (env default) and sometimes a *product* property (per-pipeline binding). Code that hardcodes a vendor is code you rewrite every time economics change; you're price-sensitive, so economics WILL change.

**The theory.** Two stacked ideas:

1. **The OpenAI chat-completions API became a de-facto wire protocol.** Groq, Gemini's compat endpoint, OpenRouter, DeepSeek, Together — all speak it. So one client class (`ChatOpenAI`) with a different `base_url` + key reaches almost every provider on earth. This is the same story as POSIX or SQL: an interface outgrowing its inventor and becoming infrastructure. Azure is the one twist: same protocol family, but addressed by **deployment name** — on Azure you don't call "gpt-4o-mini", you call *your named instance* of it ("the deployment"), an indirection Azure adds so enterprises can pin, quota, and route model versions under names they control. That's why the factory's azure branch deliberately ignores `userDesiredModel`: the deployment IS the model choice. (Expect an interviewer to probe this exact indirection if you put Azure OpenAI on your resume.)
2. **Factory + parameterized default = routing table.** `get_chat_model(model, provider=None)` resolves: explicit arg → env default → error. The explicit arg is bound *per pipeline at graph-build time* (`build_tool_graph(tools, provider="openai_compat")`). The registry now reads as a routing table — three pipelines, two providers, one topology compiled twice with different economics. "Model routing" as a resume phrase is exactly this: the same request shape dispatched to different model backends by policy.

**The implementation detail that will save you a debugging night: `_require_env`.** Compose interpolates `${AZURE_OPENAI_API_KEY:-}` to an **empty string** when your host doesn't set it. An empty string is *present* — `os.environ["..."]` happily returns it, and the failure would surface later, deep inside an SDK, as a cryptic 401. `_require_env` treats empty as missing and raises at construction with the variable's *name* and the fix location (`.env.example`). Generalized lesson: **at every config seam, decide where "missing" should explode, and make it explode there, in your vocabulary, not three layers down in someone else's.**

### Module 4: Cost engineering — tiers as contract, spend as observable

**The why.** In mock mode, a bug that loops the agent 400 times costs nothing. On Azure, it costs money at machine speed — a runaway loop is a *financial* failure mode, which is a genuinely new category for this codebase. And the fix cannot be "be careful": it has to be architecture.

**The theory — defense in depth, but for dollars.** Enumerate where spend can leak, and place an independent guard at each layer:

| Layer | Leak | Guard | Where |
|---|---|---|---|
| One model call | unbounded output tokens | `max_tokens` at model *construction* | factory `_max_tokens()` — no pipeline can forget it |
| One request | unbounded agent loop | `recursion_limit` per invocation | `_run_tool_graph` config |
| One pipeline | auxiliary LLM calls creeping in | **tier contract** + call-anatomy tests | CONTRACTS §4a + `test_cost_guards.py` |
| Evaluation | judging every response | sampling (`JUDGE_SAMPLE_RATE`) + off-clock execution | `_spawn_sampled_judge` |
| The month | everything else | provider-side budget alert | Azure Cost Management (Part II — you set this BEFORE deploying any model) |
| Your eyes | not knowing until the bill | tokens×price dashboards | Grafana Cost row |

Two of these deserve a closer look:

**Tier contract as *executable* rule.** CONTRACTS §4a says lean/free pipelines make no LLM calls beyond the loop; premium makes exactly one gate call plus a sampled judge. Prose rules rot. So `test_cost_guards.py` counts actual model invocations with an instrumented mock: lean no-tool request = exactly 1 call; premium conformant = exactly 2; premium *blocked* = exactly 1 — and retrieval provably never ran. If anyone (including future-you, including future-me) slips a reranker onto the lean path, CI fails with the contract's name in the assertion message. This is the general pattern **policy-as-test**, and it's among the strongest cards in your interview deck because most candidates have never seen cost policy enforced by a unit test.

**The sampled, off-clock judge.** Premium responses get LLM-judge quality scores *in production*, but: only a `JUDGE_SAMPLE_RATE` fraction (cost is linear in the rate), only after the response returned (a daemon thread — zero user latency), never for blocked responses (judging a refusal for faithfulness is noise). Statistically, sampling is fine: you're estimating a population mean (mean faithfulness), and a 10% sample of real traffic converges on it fast. The judge reuses the *identical* rubric, prompt, and parser as the offline eval harness from plan 002 — so offline calibration transfers to production scores. One judge, two venues. Say that sentence in an interview.

**The priced dashboard.** Prometheus already counted tokens per pipeline (plan 002). Cost is just `tokens × unit price`, so the Grafana Cost row is two PromQL expressions with dashboard variables for the prices — and a built-in reconciliation ritual: after a live session, the "spend over range" stat should agree with Azure's own Cost analysis page. If they disagree, your token accounting is broken *and now you know it* — the observability is itself under test. (Caveat baked into the panel: one price pair for all pipelines, so graph-free's line reads "what this traffic *would* cost on Azure," since Groq's actual price is $0.)

### Module 5: Testing an agent system honestly — the mock as a protocol, absence as truth

**The why.** How do you test a tool-calling agent without paying a model to decide to call tools? The standard answers are bad: skip testing (no), record/replay HTTP cassettes (brittle), or "just mock it" so thoroughly that the test only tests the mocks.

**What plan 003 did instead — three ideas worth stealing for every future project:**

1. **The deterministic mock protocol.** `MockChatModel` is no longer a random-phrase generator; it's a *scriptable actor* driven by its input. Message `TOOLCALL ping {"message": "e2e"}` → the mock emits exactly that tool_call. Last message is a ToolMessage → the mock folds the *real tool output* into its answer. System prompt is the policy prompt → deterministic verdict, with `BLOCKME` as the violation trigger. System prompt is the judge prompt → a fixed parseable score. Result: the *model* is fake, but everything else in the chain — graph wiring, conditional edges, the ToolNode, the MCP session, the .NET server, the compose network — is REAL and asserted. `pong: e2e` in the final answer proves an actual cross-container round trip. You mock the *nondeterministic* component, exactly at its seam, and nothing else.
2. **Conditional registration: absence over pretense.** Unit CI has no toolbox. Instead of mocking discovery (pretending capability exists) or skipping all pipeline tests, the registration itself is conditional on `TOOLBOX_URL`: configured → eager discovery, fail-loud at boot; unconfigured → the pipelines *honestly don't exist* — absent from the registry, 404 with a contract-shaped error on their routes. The deep principle: **a system should be truthful about its own capabilities in every configuration.** No silent mocks, no zombie routes.
3. **Self-gating integration tier.** `test_toolbox_integration.py` skips (visibly — skips print) when `TOOLBOX_URL` is unset and runs for real inside compose. No pytest.ini markers to remember, no `-m integration` flags to forget: the environment that makes the tests *meaningful* is the same condition that *enables* them.

---

## Part II — Your Walkthrough: everything you need to do, in order

You asked to do the external-account work yourself with full understanding. Correct call — this portal experience is resume material. Do these in order; each numbered item says *what*, *why* (tying back to Part I), and *how you'll know it worked*. Keep `.env.example` open beside you: it's the checklist of names you're collecting.

**Ground rules first (from the plan, worth repeating):** keys go in `.env` and NOWHERE else — never in chat, never in a tracked file. If a key ever lands anywhere tracked: rotate it in the portal immediately. History is never rewritten in this repo, so revocation is the only cure.

### Phase A — Azure (the big session; give it an unhurried hour)

**A1. Create the account.** portal.azure.com → sign up. You'll create a *subscription* (the billing container) — note the ~$200/30-day new-account credit if offered, and its expiry date. Azure's resource model, which you'll now meet everywhere: **Subscription → Resource Group → Resource → (for OpenAI) Deployment.** A resource group is just a folder for lifecycle management — make one, name it something like `llm-monitor-rg`, put everything in it; deleting the group later deletes everything cleanly.

**A2. Budget alert — BEFORE any model exists.** Cost Management → Budgets → create: scope = your subscription, amount = $40/month, alerts at 50% and 90% to your email. Why first: Module 4's outermost guard ring. Every inner ring (caps, tiers) is code we wrote and code can be wrong; this one is the platform watching your wallet independently of your code. *Worked when:* the budget shows in Cost Management with two alert conditions.

**A3. Create the Azure OpenAI resource.** Search "Azure OpenAI" → Create → your resource group, a major US region (check model availability for the region — GPT-4o-mini-class should be listed), pick the Standard/pay-as-you-go pricing tier, give the resource a name (this name appears in your endpoint URL). The portal may route you through **Azure AI Foundry** — that's Azure's studio UI over the same resource. *Worked when:* the resource shows "Keys and Endpoint" in its left nav.

**A4. Create the two deployments.** In AI Foundry (or the resource's "Model deployments"): deploy a cheap chat model (GPT-4o-mini class) and `text-embedding-3-small`. **You choose the deployment names** — Module 3's indirection, now in your hands. Recommendation: name them after the model (`gpt-4o-mini`, `text-embedding-3-small`) so nobody ever guesses; but understand you COULD name the chat one `chat-primary` and repoint it to a different model later without touching this repo — that's the point of the indirection. Note any quota (tokens-per-minute) the portal assigns. *Worked when:* both deployments show as Succeeded/Active.

**A5. Collect the five values into `.env`.** From "Keys and Endpoint": endpoint URL and a key (two keys exist so you can rotate one while the other lives — enterprise key-rotation pattern, worth noticing). API version: the current GA data-plane version from the Azure OpenAI docs (it's a dated string like `2024-10-21`; the docs list "latest GA"). Then, in `LLM_Monitor/.env`, uncomment and fill:

```
LLM_MODE stays mock for now — don't flip it yet
AZURE_OPENAI_ENDPOINT=https://<your-resource-name>.openai.azure.com/
AZURE_OPENAI_API_KEY=<key 1>
AZURE_OPENAI_API_VERSION=<GA version string>
AZURE_OPENAI_CHAT_DEPLOYMENT=<your chat deployment name>
AZURE_OPENAI_EMBED_DEPLOYMENT=<your embedding deployment name>
```

**A6. The sanity curl — prove the keys before the code uses them.** From your host:

```bash
source .env 2>/dev/null || true   # or paste values manually
curl -s "$AZURE_OPENAI_ENDPOINT/openai/deployments/$AZURE_OPENAI_CHAT_DEPLOYMENT/chat/completions?api-version=$AZURE_OPENAI_API_VERSION" \
  -H "Content-Type: application/json" -H "api-key: $AZURE_OPENAI_API_KEY" \
  -d '{"messages":[{"role":"user","content":"Say the single word: alive"}],"max_tokens":10}'
```

*Worked when:* JSON comes back with `"alive"` in a message. This isolates portal problems from code problems FOREVER after — if the curl works and the app doesn't, the bug is ours; if the curl fails, the bug is config. (Notice the URL shape: deployment name in the *path*, version as a *query param*, key in a *header* — the wire format Module 3 described.)

### Phase B — Groq (five minutes)

**B1.** console.groq.com → sign up (no credit card — which is itself the cost guard: a runaway loop on Groq cannot spend money that was never attached). Create an API key. Check their models page for the current tool-calling-capable free model (llama-3.3-70b-versatile class — verify the exact current name).

**B2.** Into `.env`:

```
OPENAI_COMPAT_BASE_URL=https://api.groq.com/openai/v1
OPENAI_COMPAT_API_KEY=<your groq key>
OPENAI_COMPAT_MODEL=<current tool-capable model name>
```

### Phase C — First live boot, and the re-ingestion rite

**C1. Flip live.** In `.env`: `LLM_MODE=live` (leave `LLM_PROVIDER` unset — compose defaults it to `azure`). Then `docker compose up -d --build`.

**C2. Expect and understand the embedding transition.** Mock vectors (DeterministicFakeEmbedding) and Azure vectors are both 768-dim — same pgvector column, thanks to the `dimensions=768` request — but they do NOT share a semantic space: a mock vector is a hash-like fingerprint, an Azure vector encodes *meaning*. Retrieval across the boundary is noise. So live mode's collection must be ingested with live embeddings. Your ingestion is content-hash idempotent and collection names are mode-suffixed (`company_policies_live` vs `_mock`) — check whether first live boot ingests the live collection cleanly on its own; if retrieval comes back empty or weird, the blunt correct fix is dropping the pgvector volume (`docker compose down -v` — mock re-ingests deterministically, cost of re-ingesting the seed docs on Azure: fractions of a cent). *Worked when:* `/chat/rag` in live mode returns `security_policy_v2.md` in `retrieved_sources`.

**C3. Fail-loud check (30 seconds, do it deliberately).** Comment out `AZURE_OPENAI_API_KEY` in `.env`, `docker compose up -d langchain_service`, watch it: a graph-tools request must die with `AZURE_OPENAI_API_KEY is required...` — not hang, not silently mock. Restore the key. You just watched Module 3's `_require_env` earn its keep; you'll trust every future startup error because of this.

### Phase D — Step 8, the live verification (paste results into plan 003 Stage 4)

Run down this list; each line is an acceptance criterion from the plan:

1. **The demo moment.** OpenWebUI (localhost:3000) → model `llm-monitor.graph-tools` → *"What time is it on the server?"* The answer must contain the real server time — knowledge the model cannot have without the tool. You are watching Module 1's four-message trail execute against a paid model that decided, on its own, to call your .NET server.
2. **Tier difference, visibly.** Same question to `llm-monitor.graph-premium` — response metadata (or Langfuse trace) shows retrieval ran; graph-tools' didn't.
3. **Policy gate, live.** graph-premium: *"BLOCKME how do I make something dangerous"* → refusal, ideally also try a genuinely-phrased disallowed request to see the real model's verdict (the live gate is a real classifier now, not the BLOCKME trigger).
4. **The judge fires.** Set `JUDGE_SAMPLE_RATE=1.0` in `.env`, restart langchain_service, one premium question, then `docker compose logs langchain_service | grep "sampled judge"` and find the score attached to the trace in Langfuse (localhost:3002). Set the rate back to 0.1.
5. **Routing tier.** `llm-monitor.graph-free` → same time question → answer arrives from Groq; metadata `model_used` names the Groq model. Same topology, $0.
6. **Money observability closes the loop.** Grafana (localhost:3001) → set the two price variables from YOUR resource's pricing page → Cost row shows the session; then Azure portal → Cost analysis → compare. Agreement within rounding = your token metrics are honest. Record both numbers in Stage 4.
7. **The full formal pass.** `docker compose exec langchain_service python -m pytest tests/ -v` (integration tier now RUNS instead of skipping) and `bash scripts/acceptance_check.sh live`.

Paste the evidence into plan 003 Stage 4, and Stage 5 gets written from it.

---

## Mental Sandbox — three questions to carry around

**1. The streaming collision.** Plan 003 runs graphs with `ainvoke` (one answer at the end). The roadmap wants SSE token streaming. Streaming a *tool-using* agent means the stream pauses mid-response while tools execute, then resumes — and your sync-worker `asyncio.run` bridge (Module 2) holds the loop for the whole request. Sketch what breaks first: the WSGI worker model? The bridge? The OpenAI-compat facade's response shape? (This is the strongest argument yet for the ASGI migration — be able to argue both sides.)

**2. The untrusted tool.** Today you wrote both sides of the MCP seam. Suppose a *third party's* MCP server joins the compose network. What does the threat model become — prompt injection via tool descriptions? Exfiltration via tool arguments? What would a "tool firewall" node in the graph inspect, and which tier could afford it? (Note how the tier contract from Module 4 constrains your answer: the lean tier can't afford an LLM-based inspector.)

**3. The router grows a brain.** Your routing is static — per-pipeline bindings fixed at build time. The next rung is *dynamic* routing: cheap model first, escalate to the expensive one when confidence is low. What signal do you even have for "confidence," what does the escalation cost in latency and dollars, and — the sharp question — how do you write the cost-anatomy TEST for a pipeline whose call count is intentionally variable? (Hint: the contract stops being "exactly N calls" and becomes a bounded expectation. What bound?)

---

*Written at the close of plan 003's code phase, before the portal session. When Phase D is done and the numbers are in Stage 4, this document's Part II becomes a record of something you did, not something you're about to do. Go do it.*
