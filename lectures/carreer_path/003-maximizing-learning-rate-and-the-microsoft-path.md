# Lecture 003 — Maximizing Your Learning Rate, and the Path to Microsoft

> **For:** Timothy Lee Grant · **Date:** 2026-09-25
> **Companion:** `lectures/dotnet/003-seeing_design.md` teaches *what* mid-level design judgment is. This lecture is about *how* to acquire it fast, with little time left on a software team, and how to turn it into a Microsoft offer.
> **Builds on:** `001-how-production-software-actually-works.md` (the concepts Microsoft drills) and `002-the-leetcode-diagnosis-and-the-solving-protocol.md` (the coding gate).
>
> **Read time:** ~50 minutes. Then keep §10 (the one-page card) somewhere you'll see it weekly.

---

## 0. The headline

**Your learning rate is limited by feedback, not by reading.**

For six months you had the most valuable learning resource there is: senior engineers reviewing your work and reacting to your questions every day. In a few weeks, that goes away. Most people in your position respond by *reading more*: more repos, more books, more tutorials. That feels productive but mostly isn't, because reading without feedback gives you information without correction.

So this lecture has two clocks:

1. **The short clock (the next few weeks):** extract as much feedback, evidence, and relationship value as possible from the team while you're still on it (§1).
2. **The long clock (the next 6–18 months):** build a *feedback-rich* learning system out of open source, so your growth doesn't stop when the team is gone (§2–§6). Then convert it into a Microsoft offer (§7).

---

## 1. The short clock: a harvest plan for your remaining weeks

These are ranked by value. If you do only the first five, you'll have done the important part.

| # | Action | Why it's high-value | How |
|---|---|---|---|
| 1 | **Ask about staying in software** (a permanent transfer, or a continuing part-time role) | A "Software Engineer" title and continued team experience beats anything else in this lecture for your Microsoft goal. Recruiters and leveling both weigh title and recent software experience. | Ask your manager directly. Bring a short case: what you delivered, how fast you ramped, what you'd take on next. The worst answer is "no," which is where you are anyway. |
| 2 | **Ask for direct feedback on your growth** | Seniors see your blind spots, and you won't get this view again soon | To your main senior: *"If you were me, what's the one habit you'd build over the next six months?"* and *"What did I do this quarter that a mid-level engineer would have done differently?"* Write down the answers verbatim. |
| 3 | **Become a reviewer, then get your reviews reviewed** | Reviewing is the fastest design-judgment trainer (dotnet/003 §9) | Ask to be added to 3–5 PRs as a reviewer. Write comments using the observation → consequence → suggestion → question formula. Ask a senior: *"Were these useful? What did I miss?"* |
| 4 | **Write your "brag document" now, while details are fresh** | You'll forget specifics within months, and specifics are what make resume lines and interview stories credible | For each thing you built: what problem, what you did, what was hard, what the outcome was. Keep it free of confidential details. Describe *skills and patterns*, not internal names or designs. |
| 5 | **Secure references and relationships** | Referrals and references are the strongest hiring channels (§7.5) | Ask one or two seniors if they'd be willing to be a reference, and whether you can stay in touch. Connect on LinkedIn. A short written recommendation is gold. |
| 6 | **One guided architecture walkthrough** | Seeing how a senior *explains* the system trains your "altitude" skill | Ask for 30 minutes: they sketch the system top-down while you ask rung-3 questions (dotnet/001 §7.4). Then **you** redraw and explain it back to them and ask what you got wrong. |
| 7 | **Request one small refactoring task** | You get to practice dotnet/003 §3 *with* a senior reviewer | Something like "split this method" or "move this behind an interface," with tests. |
| 8 | **Pair on a debugging session** | Seniors' debugging strategy is mostly invisible unless you sit beside them | Ask to watch the next time something breaks. Notice what they check *first*. |
| 9 | **Keep a design journal** | Every review comment you hear becomes a reusable lesson | After each review: the comment, the smell name (dotnet/003 §4), the principle. Generic wording only. |

> **Confidentiality rule for everything above:** notes you keep personally and anything in this public repo must stay generic. "A method mixed parsing and persistence; the reviewer suggested splitting it" is a lesson. Internal class names, architecture specifics, and product details are not yours to publish.

---

## 2. The learning-rate model

A simple model that explains which activities are worth your time:

```
 learning rate  ≈  reps on real problems  ×  quality & speed of feedback  ×  retention
```

- **Reps on real problems:** problems that are *just beyond* your current ability. Too easy teaches nothing; too hard produces confusion without progress. This is the "zone of proximal development."
- **Feedback:** someone or something that tells you *what was wrong and why*, soon after you did it.
- **Retention:** whether you'll still have it in three months (writing, teaching, spaced review).

Here's how common activities score:

| Activity | Reps | Feedback | Retention | Verdict |
|---|---|---|---|---|
| Reading a random large repo | Low | **None** | Low | ❌ Feels productive, mostly isn't |
| Watching tutorials | Low | None | Low | ❌ Only for orientation |
| Building your own project alone | High | Low (only "does it run?") | Medium | ⚠️ Good, but you can't see your own design flaws |
| Building + getting it reviewed | High | **High** | Medium | ✅ |
| Contributing PRs to a maintained OSS repo | High | **High** (maintainer review) | High | ✅✅ |
| "Predict the review" on merged PRs (§5.3) | Medium | **High** (compare yours to real seniors') | Medium | ✅✅ Cheap and repeatable |
| LeetCode with the Solve Protocol (002) | High | High (the tests are the feedback) | Medium | ✅ Required for the gate |
| Writing a lecture/blog explaining a subsystem | Medium | Medium (gaps become obvious as you write) | **High** | ✅ |
| Katas with tests (Gilded Rose) | High | High | Medium | ✅ |

The winners share one property: **feedback is built in.** That's the filter for everything that follows.

---

## 3. Solving your open-source tension

You named the tension precisely: *high-quality, complex code is in huge repos, but huge repos can't be held in your head.* The resolution has two parts.

### 3.1 The unit of study is a subsystem, not a repository

Nobody holds all of `dotnet/runtime` in their head, including its maintainers. Maintainers own **areas**. Large repos are federations of smaller, well-bounded subsystems, often with their own folder, project, tests, owners, and design docs. That's the unit you study.

A good subsystem for you has:

| Criterion | Target | Why |
|---|---|---|
| **Size** | ~3k–30k lines of source | Big enough to have real design; small enough to fully map in a few weeks |
| **Clear boundary** | Its own folder/project and public API | You can define "done understanding it" |
| **Tests** | Present and runnable | Tests are executable documentation and let you modify safely |
| **Active review culture** | Merged PRs have real review threads | This is your **feedback source** (§5.3) |
| **Design documentation** | Design docs, API proposals, or detailed PR descriptions | You learn *why*, not just *what* |
| **Relevance** | .NET, used by you, valued by Microsoft | Compounding returns: every hour also counts toward your goal |

### 3.2 The portfolio shape: one home, one satellite, short visits

```
   ┌──────────────────────────────┐
   │  HOME (deep, 6+ months)      │  You know it the way a maintainer does.
   │  1 subsystem to READ deeply  │  You can draw it from memory.
   │  1 repo to CONTRIBUTE to     │  You have merged PRs there.
   └──────────────┬───────────────┘
                  │
   ┌──────────────▼───────────────┐
   │  SATELLITE (medium, 2–3 mo)  │  One more codebase, chosen to contrast with home
   └──────────────┬───────────────┘
                  │
   ┌──────────────▼───────────────┐
   │  VISITS (one sitting each)   │  Small, beautiful components read for one idea,
   │                              │  written up as a 1-page note, then left
   └──────────────────────────────┘
```

**Never have more than one home and one satellite active at the same time.** That's the rule that protects your context.

---

## 4. Specific recommendations

### 4.1 Home, reading: `Microsoft.Extensions.*` (inside dotnet/runtime) ⭐

**Folder:** `dotnet/runtime/src/libraries/Microsoft.Extensions.*`. Start with **DependencyInjection**, **Hosting** (+ `.Abstractions`), and **Options**. Then Configuration and Logging.

Why this is the best home for you:

- **You use it every day.** Every concept in dotnet/001 §8–9 (host, DI, lifetimes, options, logging) is implemented here. Studying it makes you better at your current code *immediately*.
- **Top quality with public design history.** These are core .NET libraries. Their APIs went through formal API review, and PRs get reviewed by the people who designed .NET.
- **It's full of dotnet/003's patterns in their natural habitat:** Builder (`HostApplicationBuilder`), Options, Factory (`ILoggerFactory`), Template Method (`BackgroundService`), Decorator-style wrappers, and **deep modules** (`ILogger`: tiny interface, huge machinery).
- **Right-sized:** each library is a bounded subsystem with its own `src/`, `tests/`, and `ref/` folders.

Three concrete traces to do with a debugger (step into the framework source):

1. **`Host.CreateApplicationBuilder(args)` → `Build()` → `Run()`**: find where configuration sources are added, where `IHostedService`s are started in order, and where SIGTERM becomes `StopAsync`. (Look for the host implementation under `Microsoft.Extensions.Hosting/src/Internal/`.)
2. **How `GetRequiredService<T>()` builds an object graph**: the DI library turns registrations into "call sites" (look in `Microsoft.Extensions.DependencyInjection/src/ServiceLookup/`) and then resolves them. Find where scoped-from-singleton validation throws the error you saw in the lab.
3. **How `IOptions<T>` gets its value**: follow `Bind` → options factory → `IConfigureOptions<T>` → validation.

> **Trick:** libraries in dotnet/runtime have a `ref/` folder containing one C# file with the library's **entire public API** as signatures only. Read that first. It's the Interface-First Reading Protocol (dotnet/001 §7.5) applied to a whole library.

### 4.2 Home, contributing: `dotnet/iot`

Covered in dotnet/002 (ideas I-2, I-4). Small, self-contained bindings, friendly to newcomers, and uniquely matched to your firmware background. Reading happens in Microsoft.Extensions; **merged PRs** happen here.

### 4.3 Satellite (pick one, after 2–3 months)

| Candidate | What it teaches | Size / fit |
|---|---|---|
| **YARP** (`dotnet/yarp`, moved from `microsoft/reverse-proxy` in 2025) | A real Microsoft product built on ASP.NET Core: pipelines, config reload, health checks, load balancing, high-performance networking | Medium. You already have a whole `lectures/yarp/` folder of groundwork. **Recommended.** |
| **Polly v8** (`App-vNext/Polly`) | Resilience pipelines: strategy, decorator, and builder done very well. Underpins `Microsoft.Extensions.Http.Resilience`. | Small–medium, very clean |
| **dotnet/eShop** | How a whole multi-service reference application is *organized* (Aspire, services, contracts) | Read for structure (dotnet/003 §8), not line-by-line |

### 4.4 Visits (one sitting each, a one-page note each)

- **`System.Threading.Channels`**: a small, beautifully designed concurrency primitive you already use (the ring buffer from dotnet/001 §10.7)
- **Serilog's core** pipeline: a clean structured-logging design
- **One nanoFramework or dotnet/iot binding** for a chip you know: datasheet → API design
- **The `BackgroundService` source file**: read the whole class. It's short and shows Template Method plus the .NET 10 startup change.

### 4.5 Deliberately *not* now

- **All of `dotnet/aspnetcore` or the runtime VM/JIT:** too big to hold. Visit specific pieces only.
- **Roslyn:** superb, but a world of its own. Save it for when you build a source generator (dotnet/002 I-10).
- **MediatR / AutoMapper** as study targets: popular, but commercially licensed since July 2025 and stylistically debated. Recognize them; don't make them your model.

---

## 5. The codebase dissection protocol

This is the method that turns a subsystem into knowledge you keep. It's your Interface-First Reading Protocol, scaled up.

### 5.1 The five phases

| Phase | Time box | What you do | Output |
|---|---|---|---|
| **1. Map** | ~2 h | README and docs → folder tree → projects and references → the `ref/` public API → the list of test files | A one-page **context card** (§5.2) |
| **2. Trace** | ~3–4 h | Pick one real scenario; run it under the debugger; step through; draw the sequence | A sequence diagram |
| **3. Explain** | ~3 h | Write it up as a lecture: cast of characters, contracts, **design decisions and the patterns they use** (named with dotnet/003) | A note in this repo |
| **4. History** | ~2 h | Read 5–10 merged PRs touching the area, plus the API proposal that created it | "Why it's this way" notes |
| **5. Modify** | open | Make a small local change, run the tests, then look for an issue to take | A PR, eventually |

### 5.2 The context card: how you keep context without holding it

Your worry was losing context across big projects. The answer is to **externalize** it. For each home and satellite, keep a single page:

```
 CONTEXT CARD — <subsystem>                              last refreshed: <date>
 ─────────────────────────────────────────────────────────────────────────────
 PURPOSE (1 line):
 ENTRY POINTS (where execution enters):
 KEY TYPES & THEIR JOB (5–10 lines, "character → job"):
 CORE CONTRACTS (the interfaces that matter):
 DATA FLOW (one ASCII line):   A ──► B ──► C
 PATTERNS USED (named):
 SURPRISES / NON-OBVIOUS DECISIONS (and the PR/issue that explains each):
 HOW TO BUILD + TEST:
 OPEN QUESTIONS:
```

Reloading a codebase from a context card takes 10 minutes instead of a day. This is how maintainers juggle many areas, and it's also how *you* can safely keep two codebases active.

### 5.3 "Predict the review": free senior feedback, forever

This is the single best replacement for the reviews you're about to lose:

1. Find a **merged** PR in your home area that had real discussion.
2. Read **only the diff.** Don't scroll to the comments.
3. Write your own review (dotnet/003 §9 checklist). Commit to it.
4. Now read the actual review thread. Compare:
   - What did they catch that you missed? → a new entry in your design journal
   - What did you catch that they didn't mention? → either a real insight or a sign you misjudged something (ask yourself which)
5. Once a week is enough. In three months you'll have compared yourself against ~12 senior reviews.

The same trick works with **.NET API review sessions**: the team streams many of its API reviews publicly (on the .NET YouTube channel) and posts notes on the GitHub issues. Read a proposal, decide what you'd approve or change, then watch the review.

---

## 6. Replacing the feedback loop: every source, ranked

| Source | Feedback quality | Cost | Notes |
|---|---|---|---|
| Maintainer review on your OSS PRs | ★★★★★ | Slow (days) | The real thing. Small PRs get faster reviews. |
| Predict-the-review (§5.3) | ★★★★ | Free, anytime | Your weekly staple |
| A study partner who swaps code reviews with you | ★★★★ | Coordination | Ideal with someone slightly ahead of you. Meetups and .NET communities are good places to find one. |
| Former teammates (occasional coffee chat) | ★★★★ | Social capital | Ask about design choices in *your personal* projects |
| Katas with test suites | ★★★ | Free | Instant, objective feedback on correctness; less on design |
| AI as a reviewer on **personal** projects | ★★★ | Cheap | Useful for "what smells here?" if you verify its claims against principles. Never for work code (zero-AI policy). |
| Mock interviews | ★★★★ for interview skill | Varies | Essential in the final 6–8 weeks before applying |
| Writing and publishing explanations | ★★★ | Time | Readers and your own gaps both give feedback |

---

## 7. The Microsoft path

### 7.1 How levels map (for orientation)

| Level band | Title | What it signals |
|---|---|---|
| 59–60 | Software Engineer | Early-career fundamentals, coachability |
| **61–62** | **Software Engineer II** | **Independent delivery with emerging design capability** |
| 63–64 | Senior Software Engineer | System ownership, cross-team influence |

Read the SE II line again: *independent delivery with emerging design capability.* That's precisely the junior → mid jump from dotnet/003. The design lecture and this career goal are the same project.

### 7.2 The interview loop (typical in 2026, varies by team)

```
 Referral / application
   → Recruiter screen (~30 min)
   → (sometimes) online assessment
   → Technical phone screen (45–60 min, coding)
   → Loop: 4–5 rounds of 45–60 min
        · 2 × coding
        · 1 × design / architecture      ← often decides SE vs SE II placement
        · 1 × hiring manager (behavioral + technical depth)
        · "As Appropriate" (AA): a senior from outside the team; a calibration check
          mixing coding, design, and "explain your decisions"
   → Decision
```

What that implies for you:

- **Coding rounds:** the gate. Lecture 002's verdict stands: your issue is *verification*, not algorithms. Microsoft interviewers are reported to weigh **edge cases and debugging composure**, which is exactly what the Solve Protocol trains.
- **Design round:** for SE II, it's about scope of thinking, clarifying requirements, rough estimates, and naming your own bottlenecks. Your device-system experience gives you unusual material: an edge-to-cloud telemetry system is a *great* design-interview topic you can speak about from experience.
- **AA round:** tests whether you can explain decisions to a stranger at the right altitude. That's the altitude ladder (dotnet/001 §7.4) under pressure.

### 7.3 Honest positioning: which level to target

- You have ~3 years of embedded experience and ~6 months of team software engineering. Some interviewers will count the embedded years as engineering experience. Others will see "6 months of software."
- **Recommendation:** apply to roles posted as SE or SE II **where your background is a plus** (§7.4), and **let the loop decide the level.** Don't turn down a level-60 offer at a team you want. Level is recalibrated through promotion, and getting inside is the hard part.
- Your differentiator isn't competing with pure web developers on web development. It's being the rare candidate who is credible on **hardware, firmware, Linux, and .NET together**.

### 7.4 Where at Microsoft your profile is strongest

Team names change often, so these are *kinds* of work to search for in postings, not specific teams:

| Kind of work | Why you fit | Keywords to search |
|---|---|---|
| **Cloud/datacenter hardware infrastructure** (server, rack, power, fleet management) | Your current domain, power and telemetry monitoring of server hardware, maps almost directly | "datacenter," "hardware management," "BMC," "rack," "fleet," "Redfish," "firmware" |
| **Devices** (consumer and enterprise hardware) | Firmware + drivers + host software | "firmware," "device," "embedded," "Windows drivers" |
| **Edge / IoT** (Azure IoT, Arc, IoT Operations) | Devices + .NET + cloud | "edge," "IoT," "Arc," "MQTT," "OPC UA" |
| **.NET / developer platform** (runtime, libraries, IoT) | Longer shot, but your dotnet/iot and runtime contributions (dotnet/002) would speak directly to it | ".NET," "runtime," "C#," "developer platform" |
| **General backend / Azure services** | The largest pool; competes on standard backend skills | "C#," "distributed systems," "Azure" |

A realistic door-opening strategy: a firmware/embedded-flavored software role, where you're a strong match, is often an easier first step than a general backend role, where you're an average match. Moving internally later is common at large companies once you're inside.

### 7.5 Referrals: the highest-yield channel

Applications with a referral get far more attention than cold applications. Ethical ways to get one:

- **Former colleagues** who've moved to Microsoft (search LinkedIn for your company + Microsoft).
- **Open-source relationships:** maintainers and contributors of dotnet/iot and dotnet/runtime include Microsoft employees. Do real, useful work in the repo *first*. Referrals follow relationships, not requests.
- **Meetups and conferences:** .NET user groups, embedded/IoT meetups, .NET Conf community events.
- **The specific ask** works better than the vague one: "I'm applying to role #12345 on the edge team; here's why I fit; would you be comfortable referring me?"

### 7.6 Resume

- **One page**, reverse chronological, skills-forward.
- **Title honesty with context:** something like *"Embedded Firmware Engineer, with a 6-month assignment to the software engineering team building a production .NET application."* Then let the bullets prove the software work.
- **Bullets = action + technology + outcome**, generic about the product. For example: *"Built a .NET background service that ingests hardware telemetry via native interop (P/Invoke, native callbacks, thread handoff), feeding a derived-state engine that drives automated safe-shutdown decisions."*
- **Keywords from the posting**, truthfully: C#, .NET, Linux, distributed systems, Azure, CI/CD, testing.
- **Links:** GitHub with LLM_Monitor, the device-to-cloud project (dotnet/002 I-8), and merged OSS PRs. Your public lecture repo can signal depth too, but it's secondary to shipped work.

### 7.7 Certification: an update to your Azure plan

- **AZ-204 (Azure Developer Associate) retired on July 31, 2026.** Its successor is **AI-200: "Developing AI Cloud Solutions on Azure"**, which leads to the *Azure AI Cloud Developer Associate* certification.
- AI-200 keeps core Azure developer topics (Functions, containers, monitoring) and adds Azure OpenAI integration, vector databases, and OpenTelemetry/KQL observability. That overlaps remarkably well with *both* your AI pillar (LLM_Monitor) and your Azure gap.
- **Weight:** a certification is a cheap screener signal, especially for "zero Azure" on a resume. It isn't a substitute for projects. Do it once your Azure project (LLM_Monitor plan 004, or the device project) is underway, so the studying and the building reinforce each other.

### 7.8 Your behavioral story bank

Microsoft's culture language emphasizes a **growth mindset**. You have unusually authentic growth stories. Prepare each in STAR form (Situation, Task, Action, Result), about two minutes each, with work details kept generic:

| # | Story | What it demonstrates |
|---|---|---|
| 1 | Learning C#, OOP, DI, and a large codebase from zero while delivering on a real team | Learning speed, grit |
| 2 | A senior's hard feedback about answering at the wrong level, and how you changed (the altitude ladder) | Receiving feedback, growth mindset |
| 3 | Building telemetry ingestion across the firmware → Linux → .NET boundary with native interop | Technical depth, owning a hard problem |
| 4 | The code review where you saw seniors diagnose "doing two things at once," and what you changed in your own practice | Self-directed improvement |
| 5 | LLM_Monitor: discovering CI was green while installing zero dependencies | Quality ownership, skepticism |
| 6 | Helping a hardware colleague and realizing your tool fluency had changed (cross-team bridging) | Collaboration, impact beyond your role |
| 7 | A time you were wrong or stuck, and how you got unstuck | Honesty, resilience |

---

## 8. Your weekly operating system

Assuming roughly **10–12 personal hours a week** (adjust proportionally):

| Block | Hours | What |
|---|---|---|
| **Coding gate** | 3 | LeetCode with the Solve Protocol (002). Non-negotiable until interviews. |
| **Design & code reading** | 3 | Home subsystem: one dissection phase, *or* one predict-the-review |
| **Building** | 3 | One active project (LLM_Monitor *or* the device project, not both at once) |
| **Writing** | 1 | A context card, a lecture note, or a short post |
| **Network** | 0.5 | One meaningful interaction: comment on an issue, message a former colleague, attend a meetup |
| **Buffer** | 0.5–1.5 | Life happens |

### 8.1 The next 90 days

| Weeks | Focus | Done when |
|---|---|---|
| **Now → end of team assignment** | The §1 harvest plan (it overrides everything else) | Transfer question asked; feedback captured; brag doc written; 2 references secured; 3+ reviews given and critiqued |
| **Weeks 1–4 after** | Home setup: Microsoft.Extensions Map + first Trace; dotnet/iot first docs PR (002 I-2); dotnet/003 practice item 1 (refactor your lab) | Context card for DI + Hosting; first PR opened |
| **Weeks 5–8** | Dissection phases 3–4 on Hosting/DI; weekly predict-the-review; Gilded Rose kata; resume draft | A published write-up; a kata repo; resume v1 reviewed by someone else |
| **Weeks 9–12** | dotnet/iot binding (002 I-4) or benchmark (002 I-3); mock interviews begin; start AI-200 prep if Azure project work is underway | A merged or in-review contribution; 2 mock interviews done |

---

## 9. A wide menu of other accelerators

You asked for variety. Pick **at most two** of these at a time, on top of §8.

**Deliberate practice**
- **Rewrite from memory:** after studying a component (e.g., `BackgroundService`), close the source and re-implement it; then diff against the real one.
- **Katas beyond Gilded Rose:** the Tennis, Trip Service, and Theatrical Players refactoring katas (Emily Bache's collection) each train a different smell.
- **Reproduce open issues:** maintainers love minimal reproductions. Triage is a respected contribution and teaches debugging in unfamiliar code.
- **Write tests for untested areas** in your home repo. It's low-risk, genuinely useful, and forces deep reading.

**Reading that compounds**
- **Stephen Toub's annual "Performance Improvements in .NET" posts** on the .NET Blog: enormous, precise explanations of runtime and library internals. Read one section per week.
- The **Framework Design Guidelines** (dotnet/003 §11) alongside actual API review threads.
- **Design docs** in dotnet/runtime's `docs/design/` folder and the Book of the Runtime (dotnet/002 §4).

**Visibility and relationships**
- **Answer questions** in GitHub Discussions for repos you study. Teaching in public builds reputation and precision together.
- **Give a short talk** at a local .NET or embedded meetup: "What a firmware engineer learned building a .NET telemetry service." Talks create referral relationships.
- **A GitHub profile README** that tells your story in three lines and links your best three repos.
- **.NET Conf** (each November) and community events: watch the talks relevant to your home and satellite repos.

**Interview-specific**
- **Mock interviews** with peers or paid services in the final 6–8 weeks.
- **Design-interview practice** built on *your* domain: "Design a system that monitors power for 10,000 server racks and safely shuts down VMs." You'll be unusually good at it. Practice the altitude discipline.
- **Explain-your-code drills:** take any lab solution and explain it aloud in 2 minutes at rung 3, then 2 more minutes at rung 4. That's AA-round training.

**Tool fluency** (from your persona's goals)
- One keyboard shortcut per week from dotnet/001 §19 until it's reflex.
- Learn your debugger deeply: conditional breakpoints, stepping into framework source with Source Link, the Call Stack as a "who calls this" tool.

---

## 10. Traps to avoid

| Trap | What it looks like | The fix |
|---|---|---|
| **Repo-hopping** | A new exciting codebase every week; nothing understood deeply | One home + one satellite, enforced (§3.2) |
| **Tutorial comfort** | Watching or reading because it feels productive | Filter everything through "where's the feedback?" (§2) |
| **Bottom-up relapse** | Three days inside a JIT detail while the context card is empty | Dissection phases are ordered: Map before Trace before depth |
| **Plan-perfecting** | Refining this plan instead of doing week 1 | The plan is good enough. Start §1 tomorrow. |
| **Pillar sprawl** | LLM_Monitor + device project + OSS + cert + katas all at once | §8's table: one build project at a time |
| **Leaking work details** | Publishing notes that describe your employer's system | The §1 confidentiality rule; ask when unsure |
| **Burnout** | Every evening and weekend | The weekly budget is a ceiling, not a floor |

---

## 11. The one-page card

```
 THE RULE:  Learning rate = reps × FEEDBACK × retention. Choose activities with built-in feedback.

 NEXT FEW WEEKS (on the team):
   1. Ask about staying in software       4. Write the brag doc
   2. Ask seniors for growth feedback     5. Secure references
   3. Review PRs; get reviews reviewed    6. One architecture walkthrough

 OPEN SOURCE:
   HOME-READ:    Microsoft.Extensions.* (DI, Hosting, Options)  → context card + 3 traces
   HOME-CONTRIB: dotnet/iot                                      → docs PR, then a binding
   SATELLITE:    YARP (after 2–3 months)
   WEEKLY:       one "predict the review"

 EACH WEEK (~11 h): 3 coding gate · 3 design/reading · 3 build · 1 write · 0.5 network

 MICROSOFT:
   Target SE/SE II where hardware + .NET is a plus; let the loop decide level.
   Referral via real relationships.  Resume: action + tech + outcome, generic.
   Cert: AZ-204 is retired → AI-200 (once the Azure project is underway).
   Stories: 7 STAR stories ready (§7.8).
```

---

## Sources (checked 2026-09-25)

- [YARP repository move: microsoft/reverse-proxy → dotnet/yarp](https://github.com/dotnet/yarp/issues/2736) · [dotnet/yarp](https://github.com/dotnet/yarp)
- [AutoMapper and MediatR commercial editions launch (July 2, 2025)](https://www.jimmybogard.com/automapper-and-mediatr-commercial-editions-launch-today/)
- [Microsoft interview process, rounds, levels & the AA round (2026)](https://www.amigohelp.ai/blog/microsoft-interview-process-explained/) · [IGotAnOffer: Microsoft SWE interview](https://igotanoffer.com/blogs/tech/microsoft-software-development-engineer-interview) · [SDE II interview experience (Level 61)](https://www.geeksforgeeks.org/interview-experiences/microsoft-interview-experience-for-sde-ii-level-61/)
- [AZ-204 retirement and AI-200](https://viorelbuliga.com/blog/az-204-retirement-ai-200) · [Microsoft Q&A on AZ-204 retiring July 31, 2026](https://learn.microsoft.com/en-us/answers/questions/5893548/will-az-204-still-be-accepted-as-a-prerequisite-fo)
- [dotnet/runtime API review process](https://github.com/dotnet/runtime/blob/main/docs/project/api-review-process.md)

Interview-process details come from third-party guides and vary by team and over time. Treat them as orientation, and ask your recruiter what a specific loop will contain.
