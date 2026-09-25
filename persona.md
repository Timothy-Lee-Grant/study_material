# Developer Persona: Timothy Grant

> **Last updated:** 2026-09-25 (major rewrite — replaces the July 2026 version, whose "Professional" section was inaccurate).
>
> **Note for any AI reading this:** This repo is public. My day-job project is described here only at the level of *skills and concepts*. Do not add company names, product names, internal class names, or proprietary architecture details to this file or to lectures in this repo.

# Mission

My goal is to become an exceptional backend and infrastructure software engineer capable of working at companies such as Microsoft, Google, Meta, Amazon, TikTok, or similar large-scale technology organizations. My explicit near-term target is **Microsoft Software Engineer 2**.

I am optimizing for long-term engineering excellence rather than quick tutorials or copy-paste solutions. Whenever possible, teach me the underlying principles instead of only solving the immediate problem.

---

# Current Experience

## Professional — the honest version

**Home role:** Embedded/firmware engineer in a *hardware* department. Background is single-core, bare-metal microcontroller firmware in embedded C (superloop, no OS, registers wired to physical components, I2C/SPI to on-board sensors).

**Since ~March 2026 (about six months):** On loan to the company's *software* department, working on a team building a production .NET application. This is my first real software-engineering experience: a multi-project solution, a team of engineers, code review, branching workflow, and CI/CD.

**Important constraint:** My company has a **zero-AI policy**. Everything I did at work was written by hand, with a lot of help from senior engineers. My AI-assisted work happens only in personal projects.

### What the work application is (generic, skill-level description)

A .NET application running on an embedded Linux single-board computer (Raspberry Pi) inside server hardware. It ingests hardware telemetry (power, voltage, current, temperature, fan data), stores it, derives higher-level conditions from it, and — when a condition requires it — orchestrates the graceful shutdown of virtual machines on the servers it protects, so they don't die abruptly. Users administer it over SSH through custom PowerShell cmdlets; there is also a read-only web dashboard.

Rough shape of the system (as I understand it):

| Piece | What it is | My involvement |
|---|---|---|
| Microcontroller firmware | Reads on-board sensors and forwards raw values to the Pi over I2C as small framed messages (1 preamble byte identifying the telemetry type + 2 data bytes) | **Wrote it** (embedded C) |
| Main host process | .NET Generic Host with several `BackgroundService` workers | Wrote the **data-ingestion worker** |
| Data-ingestion worker | Uses **P/Invoke** into a native C GPIO library (`pigpio` `.so`) so the Pi can act as an **I2C slave**; marshals C# structs that mirror the native structs; registers a managed callback the native library invokes on slave events; parses raw hex and logs values through the state service | **Built it** |
| State service (shared library) | State-management API over a SQL database. Data model separates *definitions* from *values*: a state definition (id, name, …) holds no value; value rows reference their state by foreign key and accumulate over time. **Derived states** take other states as inputs (raw → translated → condition, e.g. "needs shutdown") | Worked on **derived-state calculation** and the **hex → double calculator** (signed vs. unsigned interpretation) |
| Derived-state worker | Background worker that periodically triggers derived-state recalculation | Understand it; didn't build it |
| PowerShell cmdlets | Custom cmdlets compiled into DLLs and imported into a PowerShell session over SSH (add state, query values, register hosts/VMs to shut down, etc.) | **Wrote several** |
| Web dashboard | Separate process (own `Program.cs` entry point), read-only view of latest state values, reachable over a direct Ethernet connection at a static IP | Understand it at a high level |
| Shutdown service (shared library) | For each registered VM, creates a shutdown executor that pulls credentials from a credential store, logs on, and issues shutdown via a vendor virtualization SDK (referenced as raw assemblies, not a NuGet/DI-registered service) | Didn't build it — **read the code out of curiosity** |
| Credential store | KeePass-based credential storage | Barely familiar |
| Audit log | Separate component the main process talks to over **gRPC** | Essentially unfamiliar |
| Build / deploy | (1) A PowerShell script builds a Docker "emulator" container shaped like the Pi's filesystem, drops in compiled DLLs, and runs each entry point as a **systemd** unit; (2) the official release is an **Azure DevOps pipeline** that runs unit + integration tests and produces a flashable **OS image** for the Pi | Used the emulator; learned what pipelines/agents are |

### Status update (late Sept 2026)

The loan to the software team is expected to **end within weeks**. The plan for using the remaining time, continuing to grow through open source afterward, and pursuing Microsoft is in `lectures/carreer_path/003-maximizing-learning-rate-and-the-microsoft-path.md`. The design skills I'm targeting next (junior → mid-level) are in `lectures/dotnet/003-seeing_design.md`. Note: AZ-204 was retired on July 31, 2026. The Azure developer certification path is now **AI-200 (Developing AI Cloud Solutions on Azure)**.

### Honest confidence level on the work project

I was at the edge of my knowledge every single day for six months. I can explain how the pieces I built work, but much of it is not rock-solid — I got it working with help, and some of it deserves a second pass to truly own it (see the Knowledge Confidence Map below).

## Personal projects

AI-assisted projects outside work (browser extension, a simple 3D game, LLM_Monitor, an MCP Tool_Box). See **Active Projects**.

---

# Programming Background

## Languages

| Language | Real level |
|---|---|
| **C (embedded)** | Strongest. Bare-metal firmware, registers, I2C/SPI, bit manipulation, memory layout. |
| **C#/.NET** | ~6 months of real team experience, learned from zero. Can build workers, cmdlets, calculators, P/Invoke interop inside an existing architecture. Still building fluency with the language and ecosystem. |
| **Python** | Scripting and LeetCode-style problems; more structured use in LLM_Monitor (Flask, LangChain). |
| **C++** | Limited, mostly C-style. |
| **Bash / PowerShell** | Working knowledge; picked up PowerShell through the work project. |
| **Git** | Previously only "commit to main." Now: feature branches tied to Jira tickets, PRs, collaborating with others, submodules/sub-repos (still somewhat confusing). |

## Important correction to the old persona

The old version said I was "comfortable with OOP, classes, C#." That was not true at the time. **Before this loan I had never used C# and had never really used object-oriented programming** — all my code (C and Python) was linear, top-to-bottom procedural code. OOP, interfaces, dependency injection, and frameworks are things I have been learning under pressure over the last six months.

---

# Knowledge Confidence Map (as of Sept 2026)

Legend: ✅ solid · 🟡 used it, can explain it, needs review · 🟠 seen it / partial · ❌ unfamiliar

| Area | Level | Notes |
|---|---|---|
| I2C / microcontroller firmware | ✅ | Home turf |
| P/Invoke, struct marshalling, native callbacks | 🟡 | Built it; want to deeply review `StructLayout`, delegate lifetime/GC pinning, calling conventions |
| Signed vs. unsigned / two's complement from raw hex | ✅ | Math is a strength |
| .NET Generic Host, `BackgroundService`, `Program.cs` wiring | 🟡 | Finally "clicked" (inversion of control) but still new |
| Dependency injection, service lifetimes | 🟡 | Understand the idea: depend on the interface; lifetimes (singleton/scoped/transient) need review |
| Interfaces as the API of a service | 🟡 | Hard-won insight; still practicing reading code this way |
| Inheritance / polymorphism (e.g. derived type extending base type, factory choosing a concrete calculator) | 🟡 | Used it in the derived-state/calculator work |
| Relational data modeling (definition table vs. value table, foreign keys) | 🟡 | Understand the pattern from the state model |
| ORM / database access layer in .NET | 🟠 | Used it through the state service; not sure how it works underneath |
| async/await, threading in workers | 🟠 | Used; not deeply understood |
| .sln / .csproj / project references / assemblies / NuGet | 🟠 | Used to be completely lost; now navigable. Want a proper mental model of MSBuild and how assemblies are referenced |
| PowerShell cmdlet development (`Cmdlet`/`PSCmdlet`, parameters, module import) | 🟡 | Wrote several |
| JSON / serialization | 🟡 | Learned on the job; easy concept, but embarrassing if missing |
| gRPC / Protocol Buffers | ❌ | Know the audit log uses it; don't know how |
| Credential storage / secrets management | ❌ | |
| Vendor SDKs referenced as raw assemblies vs. NuGet packages | 🟠 | Curious why it's done that way |
| Docker | 🟡 | From LLM_Monitor + the work emulator |
| systemd units | 🟠 | Know each entry-point DLL runs as its own unit |
| CI/CD (Azure DevOps pipelines, agents, artifacts, OS images) | 🟠 | Now know what a pipeline and an agent are; couldn't author one yet |
| Git team workflow (branches, PRs, tickets, submodules) | 🟡 | Big improvement; submodules still fuzzy |
| Unit vs. integration testing in .NET | 🟠 | |

---

# Current Learning Priorities

## Priority 0 — The "core concepts every software engineer assumes" layer

This is now my top priority, above any specific technology. My hypothesis (see AI's Observations) is that engineers who can hop between unrelated domains quickly aren't learning each domain from scratch — they're reusing a shared layer of core concepts that I'm partially missing. I want to explicitly identify and fill that layer:

* Processes, threads, and runtimes (what is actually running, who starts it, where it lives)
* Hosts, frameworks, and inversion of control ("don't call us, we'll call you")
* Interfaces, contracts, and programming against abstractions
* Dependency injection and object lifetimes
* The build chain: source → project → assembly/package → artifact → deployment
* Serialization and wire formats (JSON, protobuf, bytes on the wire)
* Inter-process communication (HTTP/REST, gRPC, message queues, IPC)
* Client vs. server, and where code executes
* Configuration, secrets, and environments
* Persistence (relational modeling, ORMs, transactions)
* Testing strategy (unit vs. integration, fakes/mocks)
* Version control and team workflow
* Everyday developer fluency: shortcuts, terminal, debugger, IDE navigation, reading logs

## Chosen specialty — the .NET ecosystem

As of Sept 2026 I've realized I really enjoy .NET and want it as my primary backend ecosystem (it also aligns with the Microsoft goal). Domain lectures live in `lectures/dotnet/`, starting with `001-the_dotnet_atlas.md` (a top-down map of the ecosystem plus a hands-on lab) and a roadmap of follow-up lectures (002+). When suggesting implementations for new skills, prefer C#/.NET where reasonable. A second focus is **.NET on devices** (embedded Linux, MCUs, device-to-Azure), where my firmware + .NET combination is rare; see `lectures/dotnet/002-dotnet_meets_the_metal.md`. Portfolio plan: LLM_Monitor = AI pillar, a device-to-cloud system = devices pillar.

## Then — backend & infrastructure

1. Backend Engineering
2. Distributed Systems
3. Cloud Infrastructure (especially **Azure** — biggest resume gap)
4. AI Engineering
5. High-performance architecture

Specifically I want to master:

* ASP.NET Core
* REST APIs
* gRPC
* Microservices
* Event-driven architecture
* Message queues
* Redis
* PostgreSQL
* Docker
* Kubernetes
* CI/CD (including authoring pipelines, not just consuming them)
* Observability
* Distributed caching
* Service discovery
* API Gateways
* Authentication
* Authorization
* Horizontal scaling
* Performance optimization
* (Lower priority: Java Spring Boot, MongoDB)

---

# AI Engineering Goals

I want to become an AI-native engineer.

I use coding agents in **personal projects** (not at work — zero-AI policy there) and want to understand:

* Agentic workflows
* MCP servers
* Tool calling
* Vector databases
* Embeddings
* Semantic search
* Retrieval-Augmented Generation (RAG)
* Multi-agent architectures
* Prompt engineering
* Evaluation systems

Do not treat AI as a black box. Explain how systems work internally whenever possible.

Lesson already learned: when I directed AI in a domain I didn't understand (early browser-extension / 3D-game experiments), I couldn't steer it or judge its output, and progress stalled. Once I learned the domain's mental model (e.g. an extension is code the *browser* runs on the *client* machine; how the DOM, HTML, CSS, and JS relate), I could direct the AI effectively. **AI amplifies understanding; it does not replace it.**

---

# Current Weaknesses

## 1. Bottom-up instead of top-down (the biggest one)

My embedded background trained me to understand everything from the bottom up — in embedded C you *can* read every library because there's little abstraction. In application development this breaks down: I try to hold every object, every nested object, and every call in my head at once.

Concrete example: a senior engineer asked me how a state is created in the system, and I answered by describing memory allocation inside a method, instead of "you call the add-state operation on the state service." I had spent so long on the minute details that I couldn't describe or use the system as a whole. That feedback was painful but pivotal.

**What I've learned so far:** A *service* implements an *interface*; that interface is the API I need. When a service is injected into my class, I should read its interface to see what operations it offers — not dive into the whole implementation project and its ever-expanding graph of types.

## 2. Discomfort using things I don't fully understand

If my component needs to call, say, an audit log over gRPC, my instinct is that I must first fully learn gRPC and the audit log before I can do anything. If I don't know what and why, I feel I can't do it correctly — and in the past, using something I didn't understand often *did* break things. I need the skill of using an abstraction correctly through its contract while deferring deep understanding.

## 3. Speed

I am slow, mostly because of #1 and #2. I'm scared of the industry expectation (especially in the AI era) of shipping high-quality work quickly across many unrelated domains and technologies.

## 4. Hidden "basic" gaps

There are small, easy concepts (JSON was one) that nearly every software engineer knows simply from being in that environment. Because my resume shows ~3 years of embedded experience, a gap like this could badly damage credibility at a new job. I want to proactively find and close these.

## 5. Technology fluency

Hardware culture made me slow and "caveman-like" with computers. Six months among software engineers improved this a lot (a hardware coworker was surprised how fast I've become), but I want to keep building shortcut/terminal/IDE fluency deliberately.

## 6. Still-thin areas

* **Distributed systems:** event-driven, pub/sub, Kafka-style, eventual consistency, CAP, distributed transactions, consensus, service coordination
* **Asynchronous programming:** async/await internals, task scheduling, thread pools, non-blocking I/O, synchronization, race conditions, deadlocks, lock-free programming
* **Large system design:** architecture decisions, scalability, reliability, fault tolerance, load balancing, caching, partitioning, decomposition

---

# Learning Style

I learn best when explanations proceed **top-down**:

High-level architecture (what is this system for?)

↓

Major components (who are the characters?)

↓

Contracts / interfaces between them (what can I ask each one to do?)

↓

Control flow (who calls whom, and who calls *me* — the framework?)

↓

Implementation details

↓

Edge cases

↓

Performance considerations

Avoid jumping immediately into code without context. **And actively stop me when I'm going too deep too early** — tell me which layer is safe to treat as a black box for now and what its contract is.

## Reading large codebases

When explaining a project, start with:

* What the system does and why it exists
* The processes / entry points (each `Program.cs`, each host)
* Folder / solution / project organization and dependency relationships
* The key service interfaces
* Control flow

before diving into implementation details. Think like a senior engineer onboarding a new team member.

---

# Preferred Teaching Style

When teaching:

* Explain why something exists.
* Explain what problem it solves.
* Explain alternative designs.
* Explain tradeoffs.
* Explain industry best practices.
* Explain historical context when useful.
* **Connect it to embedded/firmware concepts I already know** (e.g. a native callback ≈ an ISR; a background worker ≈ a task in a superloop; a host ≈ an RTOS scheduler).

Assume I want deep understanding rather than surface familiarity — but label clearly what is "need to know now" vs. "deep dive for later."

Analogies:

* The type of analogies that I like are the ones that personify the concepts which I am struggling with.
* I want to be able to see the different characters of each component, be able to give them a name or a title, understand who they are, what they are trying to accomplish, who they interact with, and their place within the larger ecosystem.

---

# Documentation Preferences

When generating markdown files:

Use:

* Clear headings
* Tables
* Diagrams (ASCII if necessary)
* Examples
* Analogies
* Step-by-step walkthroughs
* Code snippets
* References to source files

Include sections like:

* What problem is being solved?
* Why is this design chosen?
* What should I pay attention to?
* What can I safely treat as a black box?
* Common mistakes
* Interview relevance
* Real-world production usage

---

# Career Objective

My objective is to become a senior-level engineer capable of designing and building large-scale backend systems rather than simply implementing features.

I want to develop strong engineering intuition so that I can reason about unfamiliar systems, contribute to major open-source projects, and perform effectively in highly technical interviews.

**Resume/interview story I now truthfully have:** end-to-end ownership across a hardware/software boundary — firmware that produces telemetry, a .NET worker that ingests it via native interop, a data model that turns raw values into decisions, and admin tooling — on a production team with CI/CD.

---

# Active Projects

## Day job (see "Professional" above)

Hand-written .NET work under a zero-AI policy. Worth revisiting for deep understanding: P/Invoke & marshalling, Generic Host/DI, the derived-state design, gRPC, the build/deploy chain.

## LLM_Monitor (2026, in progress)

A self-built AI orchestration platform. Phase 1 was 100% hand-written code (AI used only for review/mentorship docs). Phase 2 (July 2026, plan 001) introduced a disciplined AI-collaboration workflow: Timothy directs a staged process (design → discussion → plan → step-by-step permissioned implementation → verification), with every decision and deviation logged in Documentation/AI_Implementation_Plans. Microservices: C#/.NET YARP gateway, Python/Flask + LangChain/LangGraph service, pgvector, Ollama — all Docker-composed with mock/live modes.

**Skills demonstrated so far:** Docker Compose profiles/healthchecks/startup-ordering, YARP reverse proxy + ASP.NET middleware pipeline, REST API contract design (single contract doc, snake_case wire convention, contract-shaped errors), pipeline registry pattern for dispatch/growth, LangChain chains + compiled LangGraph graphs sharing components, pgvector RAG with idempotent (content-hash) ingestion and mock-embeddings testability, factory pattern for mock/live models, gunicorn process model, honest pytest suite + CI, directing an AI implementation through explicit staged permissions (strong interview story: found that CI had been green while installing zero dependencies).

**Constraint change (mid-July 2026):** Timothy no longer has access to a machine capable of local model inference (no GPU-class hardware). LLM_Monitor's "live" mode is migrating from local Ollama to hosted APIs. Budget: "cost sensitive" means don't waste money, not $0 — up to ~$40–50/month toward the Microsoft goal is acceptable. Mock mode stays the development default; at least one pipeline is explicitly cost-optimized (no auxiliary LLM calls), while other pipelines may carry per-request LLM overhead (policy gates, sampled judges) when there's a compelling portfolio reason.

**Strategic direction (July 2026, plan 003 onward):** Explicit goal — Microsoft **Software Engineer 2**. Resume-gap analysis found "zero Azure" is the biggest screener ding (resume shows AWS RDS/EC2). Fix in motion: make LLM_Monitor Azure-based — Azure OpenAI for chat + embeddings (plan 003), then deploy the stack to Azure (AKS leaning, ACA fallback) with Key Vault, managed identity, GitHub Actions CD, and budget alerts (planned 004). Target JD language to truthfully cover: "Azure development," "AI-driven features: prompt design, tool calling, eval harnesses," "data pipelines." Future project suggestions should prefer Azure-flavored implementations of new skills.

**Current roadmap (July 2026, see Documentation/AI_Suggestions/006):** OpenWebUI frontend via an OpenAI-compatible API facade with SSE streaming; YARP as a real API gateway; LangGraph state-machine agent (policy check → RAG → tool loop) with Postgres checkpointer memory (short- and long-term); fully local observability (Langfuse + OpenTelemetry/Prometheus/Grafana with C#→Python distributed traces); and an AI evaluation harness (golden dataset, hit@k/MRR, RAGAS, LLM-as-judge, regression-gated CI). Goal: a portfolio project demonstrating AI-engineering operational maturity (observe/evaluate/defend), targeted at Microsoft AI software engineer roles.

---

# Expectations for AI Assistance

When assisting me:

* Do not oversimplify technical concepts.
* Assume I am willing to learn difficult material.
* Prefer depth over brevity — but give me the top-down map first.
* Connect new ideas to existing concepts (especially firmware and my work project's patterns).
* Point out knowledge gaps when appropriate, including "basic" ones — I'd rather hear it from you than in a meeting.
* Recommend additional topics that naturally follow from what I am studying.
* Explain both the "how" and the "why."
* Tell me when I'm over-investigating something that can be a black box right now.

Act as if you are mentoring an engineer who is transitioning from embedded/hardware into software, and who wants to grow into a highly capable systems engineer over the next several years.

---

# My Own Observations About Myself (Timothy)

## Hyperfixation on Details

I have a blockage about being comfortable using frameworks, abstractions, and systems I don't fully understand. I regularly go straight into source code to understand everything (e.g. digging through every LangChain function I called). It's good to dive deep, but it slows me down enormously and I've felt unable to move past it. When I use a component I don't understand, I tend to break things — which tells me there's a real skill to develop here.

## The six-month loan (Mar–Sep 2026)

The hardest, most tumultuous stretch of my career. Starting points: no C#, no OOP, no idea how a solution full of folders and `.csproj` files fit together, no experience with branching/PRs/tickets/sub-repos, never seen a build pipeline or an agent. I leaned heavily on senior engineers and survived day to day.

Breakthroughs, in the order they happened:

1. **Services and interfaces.** The interface is the API; read it instead of the implementation.
2. **Inversion of control.** My code doesn't "run the program." It configures and registers things with a framework/host, and the framework calls my code on events. This felt like taking the "recursion leap of faith" from learning algorithms.
3. **Domain mental models first.** From my personal projects: once I understood *where* code runs and *who* runs it, progress became possible.
4. **Osmosis of software culture.** I'm faster and more fluent with computers than I was.

## Fears

Being hired somewhere as a "mid-level" engineer on the strength of embedded experience and getting exposed by a basic gap. And the AI-era expectation of shipping quickly across many unfamiliar domains at once.

---

# AI's Observations About Me

*(Written 2026-09-25 from Timothy's own account of the last six months. Future sessions: add to this as you notice things.)*

1. **The hypothesis about "core concepts" is very likely correct.** Engineers who move quickly across unrelated domains are mostly re-applying a small set of transferable patterns — process/runtime, host & IoC, interface/contract, DI & lifetimes, serialization, IPC, persistence, build → artifact → deploy, config & secrets, testing seams. A new domain is usually 80% those patterns in new clothes and 20% genuinely new. Timothy is currently learning each domain from the ground up because that shared layer isn't yet automatic. Filling that layer explicitly is the highest-leverage investment available, and it directly addresses the speed fear.

2. **The bottom-up instinct is an asset in the wrong order, not a flaw.** It's what let him write firmware, P/Invoke interop, and signed/unsigned decoding correctly — work many application developers would struggle with. The fix is sequencing: contract first, use it, *then* dig down only where the contract is insufficient or behavior surprises him.

3. **"I need to understand it before I use it" can be reframed as "I need to understand its *contract* before I use it."** That's a much smaller, answerable question: what goes in, what comes out, what can fail, what are its side effects and lifetime. For the audit-log/gRPC example: the contract is "a generated client with typed methods; call it, handle failure." Everything below that is optional depth.

4. **He already has more transferable systems knowledge than he credits himself with.** Framed messages over I2C → wire protocols; ISRs → callbacks/event-driven code; superloop tasks → background workers; register maps → contracts. Explicit translation tables work well for him (see `lectures/firmware/001`).

5. **Six months under a zero-AI policy is a real asset.** He built genuine hand-written fundamentals at the moment most juniors are skipping them. Combined with the lesson recorded in the AI Engineering Goals section, this makes him well suited to *directing* AI rather than depending on it.

6. **Watch for:** answering a system-level question with an implementation-level answer. When asked "how does X work?", he should first answer at the level of the question (which component, which operation), then offer to go deeper.

7. **Suggested study sequence from the work project** (each one is something he touched but doesn't fully own): Generic Host & DI lifetimes → P/Invoke & marshalling (delegate lifetime, GC) → sln/csproj/MSBuild/assemblies/NuGet → gRPC & protobuf → Azure DevOps YAML pipelines → systemd & image-based deployment.
