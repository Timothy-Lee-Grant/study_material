2026_09_25_02_40-(Seeing-Design)

# Lecture 003 — Seeing Design: Responsibilities, Abstractions, Patterns, and How Code Is Organized

> **For:** Timothy Lee Grant
> **Date:** 2026-09-25
> **Prerequisites:** Lecture 001 (especially §7 on interfaces and §9 on DI). Examples reuse the "Sensor Station" lab types.
> **Companion:** `lectures/carreer_path/003-maximizing_learning_rate_and_the_microsoft_path.md` covers *how* to keep growing (open source, feedback, the Microsoft path). This lecture covers *what* to grow: design judgment.
>
> **Why this lecture:** In a code review you watched senior engineers say two things about someone else's code: *"this is trying to do two things at once"* and *"the way this is organized isn't maintainable."* You recognized that they were seeing something you couldn't yet see. This lecture is about learning to see it. That skill is most of the difference between a junior engineer and a mid-level one.

---

## Table of Contents

- [0. What actually changes from junior to mid-level](#0-what-actually-changes-from-junior-to-mid-level)
- [1. The vocabulary seniors are using](#1-the-vocabulary-seniors-are-using)
- [2. A worked code review: "this is doing two things at once"](#2-a-worked-code-review-this-is-doing-two-things-at-once)
- [3. The refactoring, step by step](#3-the-refactoring-step-by-step)
- [4. The design-smell field guide](#4-the-design-smell-field-guide)
- [5. Principles, stated precisely (and their limits)](#5-principles-stated-precisely-and-their-limits)
- [6. Deep modules: the missing half of "use interfaces"](#6-deep-modules-the-missing-half-of-use-interfaces)
- [7. Design patterns you will actually meet in .NET](#7-design-patterns-you-will-actually-meet-in-net)
- [8. How code is organized: architecture styles](#8-how-code-is-organized-architecture-styles)
- [9. Reviewing code like a senior](#9-reviewing-code-like-a-senior)
- [10. Practice regimen](#10-practice-regimen)
- [11. Reading list](#11-reading-list)
- [12. Self-check questions](#12-self-check-questions)

---

## 0. What actually changes from junior to mid-level

| | Junior | Mid-level | Senior |
|---|---|---|---|
| **Main question** | "How do I make it work?" | "How do I make it work **and easy to change**?" | "What should we build, and how will it evolve across teams?" |
| **Scope** | A task, with guidance | A feature, independently | A system or area, across people |
| **Design** | Follows the existing structure (or fights it) | **Chooses** structure inside a feature; notices bad structure | Sets structure across components |
| **Code review** | Receives feedback | **Gives useful feedback**: names the smell and proposes the fix | Uses review to teach and to steer direction |
| **Ambiguity** | Waits for clarification | Clarifies and proceeds | Resolves ambiguity for others |
| **Abstractions** | Either avoids them or over-uses them | Uses them **where they pay** | Designs the ones other people use |

Notice the pattern: the jump to mid-level is almost entirely about **maintainability judgment**, meaning seeing *future change* while looking at *present code*. You don't need more language features for that. You need a vocabulary, a catalog of smells, and a lot of reps. This lecture gives you the first two and a plan for the third.

---

## 1. The vocabulary seniors are using

Tag: 🟢 **OWN IT**. When seniors review code, they're pattern-matching against these ideas, usually without naming them. Once you know the names, you'll hear them everywhere.

| Term | Plain meaning | Question to ask of any code |
|---|---|---|
| **Responsibility** | A job the code does | "What *jobs* does this method or class do? List them." |
| **Reason to change** | A person, requirement, or technology whose change would force an edit here | "Who could ask me to change this, and for what?" |
| **Cohesion** | How much the things inside a unit belong together | "Do all these lines serve one purpose?" High is good. |
| **Coupling** | How much one unit depends on the details of another | "If *that* changes, must *this* change?" Low is good. |
| **Abstraction** | Hiding *how* behind a simpler *what* | "Can I use this without knowing its internals?" |
| **Encapsulation** | Protecting internal state so only the owner can change it | "Can outsiders put this object into an invalid state?" |
| **Level of abstraction** | How close a line is to the problem domain versus the machine | "Are high-level steps mixed with byte-twiddling in one method?" |
| **Boundary** | A line between parts of the system (process, project, layer, module) | "What's allowed to cross this line, and in which direction?" |
| **Side effect** | Anything a function does besides returning a value: I/O, mutation, time, randomness | "Can I call this twice safely? Can I test it without a database?" |

The code-review phrase *"it's trying to do two things at once"* is exactly: **low cohesion, because it has more than one reason to change.** The phrase *"this organization isn't maintainable"* usually means **high coupling across boundaries that are in the wrong place**, so a single change ripples through many files. These are the two fundamental forces of design. Almost everything else in this lecture is a technique for raising cohesion or lowering coupling.

> **Firmware twin:** you already know both forces. An ISR that samples an ADC *and* updates the display *and* writes to flash has low cohesion (a timing change to one breaks the others). A driver that reaches into another module's global variables has high coupling. Same forces, different scale.

---

## 2. A worked code review: "this is doing two things at once"

This code is **invented** and generic, but it's a very common shape. It would pass a "does it work?" test. Read it once, then list every job it does before reading the review below it.

```csharp
public class TelemetryProcessor
{
    private readonly TelemetryDbContext _db;
    private readonly ILogger<TelemetryProcessor> _log;
    private readonly HttpClient _http;
    private int _lowCount;

    public TelemetryProcessor(TelemetryDbContext db, ILogger<TelemetryProcessor> log, HttpClient http)
    {
        _db = db; _log = log; _http = http;
    }

    public async Task<bool> ProcessFrame(byte[] data, bool isSimulated)
    {
        if (data.Length != 3) { _log.LogWarning("bad frame"); return false; }

        var kind = data[0];
        var raw  = (data[1] << 8) | data[2];

        double value;
        if (kind == 1)      value = raw * 0.004;
        else if (kind == 2) value = (short)raw * 0.001;
        else if (kind == 3) value = (short)raw / 128.0;
        else if (kind == 4) value = raw;
        else return false;

        if (!isSimulated)
        {
            _db.Readings.Add(new Reading { Kind = kind, Value = value, Timestamp = DateTime.Now });
            await _db.SaveChangesAsync();
        }

        if (kind == 1 && value < 11.8)
        {
            _lowCount++;
            if (_lowCount >= 3)
            {
                await _http.PostAsync("http://localhost:5100/shutdown", null);
                _lowCount = 0;
            }
        }
        else if (kind == 1) _lowCount = 0;

        _log.LogInformation($"Processed {kind} = {value}");
        return true;
    }
}
```

### 2.1 The jobs (responsibilities)

1. **Validate and parse** a wire frame (protocol knowledge)
2. **Convert** raw values to engineering units (calibration knowledge)
3. **Persist** readings (storage knowledge)
4. **Decide** whether power is too low, with debouncing (policy knowledge)
5. **Act**: trigger a shutdown over HTTP (integration knowledge)
6. **Log** what happened (observability)
7. **Switch behavior** between simulated and real (environment knowledge)

That's seven jobs, and each has a different **reason to change**: the firmware team changes the protocol; hardware changes a sensor's scale; ops changes the database; the product owner changes the threshold; another team changes how shutdown is invoked. **Any of five different people could force an edit to this one method.** That's what "doing two things at once" means, taken to its conclusion.

### 2.2 The review a senior would write

Here are the comments, in the tone of a good review: name the problem, explain the consequence, suggest a direction.

| # | Line(s) | Comment | Smell (§4) |
|---|---|---|---|
| 1 | Whole method | "This mixes parsing, conversion, storage, alarm policy, and shutdown. Could we split it so each piece can change and be tested independently?" | Divergent change / low cohesion |
| 2 | `bool isSimulated` | "A flag parameter that changes behavior usually means two methods or two implementations. Could simulation be a different `ITelemetryStore` registered in DI, instead of a branch here?" | Flag argument |
| 3 | `kind == 1`, `0.004`, `11.8`, `3` | "Magic numbers. What is kind 1? Where does 11.8 come from? These should be named: an enum for kinds, a calibration table, and options for thresholds." | Magic numbers / primitive obsession |
| 4 | `private int _lowCount` + injected `DbContext` | "**Bug risk:** `DbContext` is scoped, so this class will be scoped too, and `_lowCount` resets with every new scope. The debounce silently won't work in production. State with a different lifetime from its dependencies needs its own home." | Lifetime/state mismatch |
| 5 | `DateTime.Now` | "Local time (DST jumps, ambiguous hours) and impossible to control in tests. Use `TimeProvider` and UTC or `DateTimeOffset`." | Static cling / hidden dependency |
| 6 | `return false` twice | "The caller can't tell a malformed frame from an unknown kind. They need different handling and metrics. Return a result type." | Information loss |
| 7 | `_http.PostAsync("http://localhost:5100/shutdown")` | "Hard-coded URL and transport inside business logic. Hide shutdown behind an interface (e.g. `IShutdownTrigger`) so the policy doesn't know *how* shutdown happens." | Wrong abstraction level / coupling |
| 8 | `$"Processed {kind} = {value}"` | "Use a message template so `Kind`/`Value` stay structured. Also, `Information` per frame will flood the logs. `Debug`?" | Logging |
| 9 | No `CancellationToken` | "Pass a token through so shutdown is prompt." | Async hygiene |
| 10 | Testability overall | "To test the alarm logic today I'd need a database and an HTTP server. After a split, the policy could be a pure unit test." | Untestable design |

Comment 4 is the one that separates mid-level from junior. It isn't about style. It's a **real bug** that comes from design: mixing state that must live for the whole app with a dependency that lives per scope. Seniors catch these because they think about **lifetimes and ownership** automatically. You're well placed to learn this, because firmware trained you to ask "where does this variable live, and for how long?"

---

## 3. The refactoring, step by step

Tag: 🟢 **OWN IT**. Watch the *moves*. Every refactoring below is a named, reusable technique.

### Step 1: Extract the pure parts ("functional core")

Parsing and conversion depend on nothing but their inputs, so pull them out as **pure functions**: no I/O, no clock, no state.

```csharp
public enum TelemetryKind : byte { BusVoltage = 1, Current = 2, Temperature = 3, FanRpm = 4 }

public readonly record struct RawFrame(TelemetryKind Kind, ushort Raw);

public sealed record Reading(TelemetryKind Kind, double Value, DateTimeOffset At);

public static class FrameParser                       // job 1: protocol
{
    public static bool TryParse(ReadOnlySpan<byte> bytes, out RawFrame frame) { /* Lecture 001 §6.8 */ }
}

public sealed class ReadingConverter                  // job 2: calibration
{
    private static readonly Dictionary<TelemetryKind, Func<ushort, double>> Scale = new()
    {
        [TelemetryKind.BusVoltage]  = raw => raw * 0.004,                      // 4 mV/bit
        [TelemetryKind.Current]     = raw => unchecked((short)raw) * 0.001,    // signed, 1 mA/bit
        [TelemetryKind.Temperature] = raw => unchecked((short)raw) / 128.0,    // signed, 1/128 °C/bit
        [TelemetryKind.FanRpm]      = raw => raw,
    };

    public Reading? Convert(RawFrame frame, DateTimeOffset at) =>
        Scale.TryGetValue(frame.Kind, out var f) ? new Reading(frame.Kind, f(frame.Raw), at) : null;
}
```

**Moves used:** *Extract Function*, *Replace Magic Number with Named Constant* (the enum), *Replace Conditional with Table/Polymorphism* (the dictionary).

### Step 2: Give the stateful policy its own home, with the right lifetime

```csharp
public sealed class PowerOptions
{
    public double UnderVoltageThreshold    { get; set; } = 11.8;
    public int    ConsecutiveSamplesToTrip { get; set; } = 3;
}

public enum RuleOutcome { NoChange, Trip }

/// Debounced under-voltage detection.
/// Registered as a SINGLETON. Called from a single consumer loop, so it is not thread-safe by design.
public sealed class UnderVoltageRule(IOptions<PowerOptions> options)    // job 4: policy
{
    private int _consecutiveLow;

    public RuleOutcome Evaluate(Reading r)
    {
        if (r.Kind != TelemetryKind.BusVoltage) return RuleOutcome.NoChange;

        var o = options.Value;
        _consecutiveLow = r.Value < o.UnderVoltageThreshold ? _consecutiveLow + 1 : 0;

        if (_consecutiveLow < o.ConsecutiveSamplesToTrip) return RuleOutcome.NoChange;
        _consecutiveLow = 0;
        return RuleOutcome.Trip;
    }
}
```

**Moves used:** *Extract Class*, *Introduce Parameter Object* (options), and **a documented concurrency assumption**. Writing "not thread-safe by design; single consumer" in the doc comment is itself a senior habit: it states the contract that callers rely on.

### Step 3: Put I/O behind interfaces ("imperative shell")

```csharp
public interface ITelemetryStore   { Task AppendAsync(Reading reading, CancellationToken ct); }   // job 3
public interface IShutdownTrigger  { Task RequestAsync(string reason, CancellationToken ct); }    // job 5
```

Implementations: `EfTelemetryStore` (scoped, uses `DbContext`), `NullTelemetryStore` (does nothing, for simulation), and `HttpShutdownTrigger` (wraps the HTTP call, URL from options). The `isSimulated` flag disappears. Simulation is now **a registration choice**, not a branch:

```csharp
if (builder.Environment.IsDevelopment())
    builder.Services.AddSingleton<ITelemetryStore, NullTelemetryStore>();
else
    builder.Services.AddScoped<ITelemetryStore, EfTelemetryStore>();
```

**Moves used:** *Replace Flag Argument with Polymorphism*, *Extract Interface*, *Dependency Inversion*.

### Step 4: What's left is coordination only

```csharp
public enum FrameResult { Ok, Malformed, UnknownKind }

public sealed class TelemetryPipeline(
    ReadingConverter converter,
    ITelemetryStore store,
    UnderVoltageRule rule,
    IShutdownTrigger shutdown,
    TimeProvider time,
    ILogger<TelemetryPipeline> log)
{
    public async Task<FrameResult> HandleAsync(ReadOnlyMemory<byte> bytes, CancellationToken ct)
    {
        if (!FrameParser.TryParse(bytes.Span, out var frame)) return FrameResult.Malformed;

        var reading = converter.Convert(frame, time.GetUtcNow());
        if (reading is null) return FrameResult.UnknownKind;

        await store.AppendAsync(reading, ct);

        if (rule.Evaluate(reading) == RuleOutcome.Trip)
            await shutdown.RequestAsync("Bus voltage below threshold", ct);

        log.LogDebug("Handled {Kind} = {Value}", reading.Kind, reading.Value);
        return FrameResult.Ok;
    }
}
```

Read `HandleAsync` out loud: *parse, convert, store, evaluate, maybe shut down.* Every line sits at the **same level of abstraction**, and the method reads like the requirements. That's the feeling of well-designed code.

One lifetime detail to finish: `TelemetryPipeline` depends on a possibly scoped `ITelemetryStore`, so it should be **scoped**, created per unit of work by the worker (Lecture 001 §9.3). `UnderVoltageRule` is a **singleton**, so its counter survives across scopes. That fixes review comment 4. The state now lives in an object whose lifetime matches the state's.

### Step 5: Judge the result by change scenarios, not by line count

The "after" has more types. Is that better? Don't judge by counting files. **Judge by simulating likely changes:**

| Likely change | Before: what you edit | After: what you edit |
|---|---|---|
| Add a new sensor kind | The god method (risk: break the others) | Enum + one table entry |
| Change the threshold to 11.5 V | Recompile | Config only |
| Require 5 samples instead of 3 | The god method | Config only |
| Switch storage to a time-series DB | The god method + tests that need a DB | A new `ITelemetryStore` class |
| Invoke shutdown over gRPC instead of HTTP | The god method | A new `IShutdownTrigger` class |
| Unit-test the debounce logic | Needs a DB + HTTP server | `new UnderVoltageRule(Options.Create(...))`, feed readings, assert |
| Simulate on a laptop | `isSimulated: true` everywhere | Environment = Development |

**This table is the most important technique in the lecture.** Design quality is not an aesthetic. It's the cost of plausible future changes. When you disagree with someone about design, argue with change scenarios, not opinions.

### Step 6: When NOT to do this

- **One-off scripts and spikes:** the god method is fine if nobody will change it.
- **When you don't know the likely changes yet:** premature splitting guesses the wrong seams (§5, "the wrong abstraction").
- **In the middle of an unrelated PR:** refactor in a separate PR, so reviewers can see behavior didn't change.
- **Without tests:** first write *characterization tests* that pin current behavior, then refactor (§10's Gilded Rose kata trains exactly this).

---

## 4. The design-smell field guide

Tag: 🟢 **OWN IT**. A "smell" is a surface symptom that *often* indicates a deeper design problem. Learn to spot them fast. That's what the seniors in your review were doing.

### 4.1 Smells inside a method

| Smell | Symptom | Why it hurts | Typical fix |
|---|---|---|---|
| **Long method / many jobs** | You need "and" to describe it | Many reasons to change | Extract Function |
| **Mixed levels of abstraction** | `SaveOrder()` next to `buffer[3] << 8` | Hard to read; hides the story | Extract the low-level parts |
| **Flag argument** | `Do(x, true)` | Two behaviors pretending to be one | Two methods, or polymorphism |
| **Magic numbers/strings** | `if (kind == 1)`, `"http://…"` | Meaning is lost; duplicated values drift apart | Named constants, enums, options |
| **Deep nesting** | Arrow-shaped code | Hard to follow every path | Guard clauses and early returns |
| **Hidden side effect** | `GetStatus()` that also writes a row | Callers get surprised | Command–query separation |
| **Static cling** | `DateTime.Now`, `File.ReadAllText`, static singletons inside logic | Untestable, hidden dependency | Inject `TimeProvider` or an interface |
| **Information-losing returns** | `bool` for five different failure modes | Callers can't react correctly | Result type / enum / exceptions for truly exceptional cases |

### 4.2 Smells in a class

| Smell | Symptom | Why it hurts | Typical fix |
|---|---|---|---|
| **God class** | `Manager`, `Helper`, `Processor` with 2,000 lines | Everything couples to it | Split by responsibility |
| **Divergent change** | *One class* changes for many unrelated reasons | Low cohesion | Split by reason to change |
| **Shotgun surgery** | *One change* requires edits in many classes | Scattered responsibility | Gather into one place |
| **Feature envy** | A method mostly uses another object's data | Behavior lives in the wrong place | Move Method to the data's owner |
| **Primitive obsession** | `double voltage`, `string sensorId`, `int status` everywhere | No validation, easy to mix up units | Small types: `record struct Volts(double Value)`, enums |
| **Data clumps** | The same 3 parameters travel together everywhere | A missing concept | Introduce Parameter Object / record |
| **Long parameter list** | Constructors with 12 dependencies | The class does too much | Split the class. Don't hide the problem in a parameter object. |
| **Refused bequest** | A subclass throws `NotSupportedException` for inherited members | Inheritance used wrongly (a Liskov violation) | Composition instead |
| **Speculative generality** | `IFooFactoryProvider` with one implementation "in case" | Complexity without benefit | Delete it until a second case exists (YAGNI) |

### 4.3 Smells in the structure

| Smell | Symptom | Why it hurts | Typical fix |
|---|---|---|---|
| **Wrong dependency direction** | Domain logic references EF Core, HTTP, or UI types | Can't change infrastructure without touching core logic | Dependency inversion; ports and adapters (§8) |
| **Cyclic dependencies** | A uses B and B uses A (namespaces or folders) | Can't understand or test either alone | Extract the shared concept; invert one direction |
| **Leaky abstraction** | Callers must know it's SQL underneath (e.g., catch `SqlException`) | The interface doesn't really hide anything | Translate errors at the boundary |
| **Service locator** | `serviceProvider.GetService<T>()` sprinkled through the code | Hidden dependencies; runtime failures | Constructor injection |
| **Anemic model + fat services** | Entities are property bags; all rules live in `XService` | Rules duplicated across services | Move invariants into the types that own the data |
| **"Utils" dumping ground** | `Common/Utils.cs` with 60 unrelated methods | Nothing belongs anywhere | Place each function with the concept it serves |
| **Organized by technical kind only** | `/Controllers`, `/Services`, `/Repositories` with 80 files each | One feature is spread across 6 folders | Feature folders / vertical slices (§8.3) |

---

## 5. Principles, stated precisely (and their limits)

Tag: 🟢 **OWN IT**. Principles are compressed experience. Each one below comes with its **limit**, because over-applying principles is the classic "junior who just read a design book" mistake.

| Principle | Precise statement | The limit / counter-weight |
|---|---|---|
| **Single Responsibility (SRP)** | A module should have **one reason to change**, i.e. serve one actor or requirement source. It does *not* mean "does one tiny thing." | Splitting by "one thing" too finely creates dozens of shallow classes (§6) |
| **Separation of concerns** | Keep different kinds of knowledge (protocol, policy, storage, UI) in different places | Concerns must be split at *stable* seams |
| **High cohesion / low coupling** | Put things that change together, together; minimize knowledge of each other's details | Zero coupling is impossible and undesirable. Couple to *stable* things. |
| **Dependency Inversion (DIP)** | Policy shouldn't depend on mechanisms; both depend on abstractions owned by the policy side | Don't invert every dependency. Invert at volatile or I/O boundaries. |
| **Open/Closed** | Add behavior by adding code (a new strategy), not by editing working code | Only where variation is real and recurring |
| **Liskov Substitution** | A subtype must honor the base type's contract, with no surprises | If you're tempted to throw `NotSupported`, use composition |
| **Interface Segregation** | Clients shouldn't depend on members they don't use | Don't split every interface into one-method pieces |
| **Command–Query Separation** | A method either **changes state** (command) or **returns data** (query), not both | Some well-known exceptions exist (`Stack.Pop`, `TryDequeue`) |
| **Tell, don't ask** | Tell an object to do something instead of pulling its data out and deciding for it | Pure data-transfer types are fine as data |
| **Law of Demeter** | Talk to your direct collaborators, not their collaborators (`a.B.C.D()`) | Fluent APIs and LINQ are intentional exceptions |
| **Composition over inheritance** | Build behavior by combining objects, not deep class hierarchies | Inheritance is fine for real "is-a" families and framework base classes like `BackgroundService` |
| **DRY** | Every piece of *knowledge* has one authoritative place | **Duplication is far cheaper than the wrong abstraction** (Sandi Metz). Two similar-looking pieces of code that change for different reasons are *not* duplication. |
| **YAGNI** | Don't build for requirements you don't have | But do leave seams where change is *likely* (I/O, third parties) |
| **Make illegal states unrepresentable** | Use types so that invalid combinations can't compile | Don't build a type zoo for trivial data |
| **Functional core, imperative shell** | Pure logic in the middle; I/O at the edges | Some logic is inherently I/O-bound |

The meta-principle underneath all of them: **optimize for the cost of likely change.** Every principle above is a heuristic for that one goal. When two principles conflict (DRY vs SRP happens often), go back to the goal and run change scenarios (§3 Step 5).

---

## 6. Deep modules: the missing half of "use interfaces"

Tag: 🟢 **OWN IT**. This idea comes from John Ousterhout's *A Philosophy of Software Design*, and it corrects a trap that Lecture 001 might have set for you.

Lecture 001 said interfaces are seams and that enterprise code has an `IThing` for almost every `Thing`. True, but incomplete. Ousterhout's insight:

> A module's value = the complexity it **hides** ÷ the complexity of its **interface**.

```
   DEEP MODULE (good)                        SHALLOW MODULE (costly)
   ┌──────────────────────────┐             ┌──────────────────────────────────────┐
   │ small, simple interface  │             │ interface nearly as big as the body  │
   ├──────────────────────────┤             ├──────────────────────────────────────┤
   │                          │             │ a little implementation              │
   │   lots of hidden         │             └──────────────────────────────────────┘
   │   implementation         │
   │                          │             e.g. IUserRepository with 14 methods that each
   │                          │             forward one call to EF Core, adding nothing
   └──────────────────────────┘
   e.g. a Unix file descriptor: open/read/write/close hides disks, caches, file systems, drivers
   e.g. ILogger: one Log method hides sinks, filtering, formatting, batching
```

Why this matters to you specifically:

- Your old discomfort ("I must understand everything underneath") is **exactly what deep modules make unnecessary**. A deep module's whole point is that you *don't* need to look inside. When you felt compelled to read the whole state service, part of the cause may have been that its abstractions were **shallow**: they didn't hide enough, so you had to look underneath to use them correctly. That's a design problem, not only a personal one.
- When *you* design, aim for **few, powerful, simple-to-use interfaces** at the real boundaries: I/O, hardware, third parties, other teams. Don't wrap every class in an interface that mirrors it member for member. That's the "shallow module" smell wearing a best-practice costume.

**Where interfaces pay for themselves**, in priority order:

1. I/O boundaries: database, network, file system, hardware, clock (`TimeProvider`)
2. Third-party or vendor code you don't control (the Adapter pattern)
3. Genuine variation: multiple real implementations (simulated/real, strategy families)
4. Boundaries between teams or components (contracts)

**Where they often don't:** pure logic with one implementation (`ReadingConverter` above has no interface, and doesn't need one, because it's pure and cheap to use directly in tests).

---

## 7. Design patterns you will actually meet in .NET

Tag: 🔵 **CONTRACT** for recognition, 🟢 for the starred ones. Patterns are **names for recurring solutions**. Their biggest value is *communication*: "make it a decorator" is one sentence instead of a whiteboard session. Learn them by the **problem** they solve and the **place you've already seen them**.

| Pattern | Problem it solves | Where you've already met it in .NET | Overuse warning |
|---|---|---|---|
| **Strategy** ★ | Swap an algorithm at run time | `IValueCalculator` (Lecture 001 §7.2); `IComparer<T>` | A strategy with one implementation is ceremony |
| **Factory** ★ | Centralize "which concrete class?" decisions | `CalculatorFactory`; `IHttpClientFactory`; `ILoggerFactory` | Factories of factories |
| **Decorator** ★ | Add behavior around an object without changing it | `ScaledCalculator` (lab); `BufferedStream` wrapping `FileStream`; retry/caching wrappers | Deep stacks of wrappers become hard to debug |
| **Adapter** ★ | Make a foreign API fit your interface | Wrapping a vendor SDK behind `IVmController` (Lecture 001 §3.5) | — |
| **Facade** | One simple entry point over a complex subsystem | `HttpClient` over sockets, TLS, HTTP/2; `WebApplication.CreateBuilder` | A facade that becomes a god class |
| **Template Method** | A base class fixes the algorithm; subclasses fill in steps | **`BackgroundService`**: the base handles start/stop, you override `ExecuteAsync` | Deep inheritance trees |
| **Observer / events** | Notify many listeners of changes | C# `event`s; `IObservable<T>`; `IOptionsMonitor.OnChange` | Memory leaks from never-unsubscribed handlers |
| **Chain of Responsibility / Pipeline** ★ | Pass a request through ordered handlers | **ASP.NET Core middleware**; `DelegatingHandler` in `HttpClient` | Order-dependent bugs |
| **Builder** | Construct complex objects step by step | `HostApplicationBuilder`, `WebApplicationBuilder`, `StringBuilder` | Builders for trivial objects |
| **Options** ★ | Typed, validated configuration | `IOptions<T>` (Lecture 001 §9.6) | — |
| **Repository / Unit of Work** | Abstract data access; commit changes atomically | **`DbSet<T>` is a repository and `DbContext` is a unit of work already** | Wrapping EF Core in a generic repository is usually a *shallow module* (§6) |
| **Mediator** | Decouple senders from handlers via a central dispatcher | MediatR, common in enterprise code (note: commercial licensing since July 2025) | Indirection that hides control flow |
| **Command** | Represent an action as an object (queue it, log it, undo it) | Queued jobs; PowerShell cmdlets are close cousins | — |
| **State machine** | Behavior depends on explicit states and transitions | Protocol handlers; the `async` state machine (Lecture 001 §10.3) | Implicit state spread across booleans (the smell this fixes) |
| **Null Object** | Avoid `if (x != null)` everywhere with a do-nothing implementation | `NullTelemetryStore`; `NullLogger<T>.Instance` | Hiding real errors |
| **Result type** | Return success or a typed failure without exceptions | `FrameResult` above; `TryParse` pattern | Re-implementing exceptions poorly |

**How to learn patterns properly:** don't memorize the list. For each starred pattern, (1) find it in code you already know, (2) write a 20-line example from memory, and (3) write down one situation where using it would be a mistake.

---

## 8. How code is organized: architecture styles

Tag: 🔵 **CONTRACT**, 🟢 for dependency direction. "The organization isn't maintainable" is usually a comment about **where the boundaries are** and **which way dependencies point**.

### 8.1 Layered (N-tier): the classic

```
  Presentation (controllers, cmdlets, UI)
        │ depends on
        ▼
  Business logic (services, rules)
        │ depends on
        ▼
  Data access (EF Core, SQL)
```

Simple and familiar. **Weakness:** business logic depends *downward* on data access, so storage details leak upward, and tests of business logic need the database.

### 8.2 Clean / Onion / Hexagonal ("ports and adapters"): invert the bottom

```
                 ┌────────────────────────────────────────────┐
                 │  ADAPTERS (outer ring): EF store, HTTP     │
                 │  shutdown trigger, I2C source, web API,    │
                 │  PowerShell cmdlets                        │
                 │     ┌─────────────────────────────────┐    │
                 │     │  APPLICATION: use cases,        │    │
                 │     │  pipelines (TelemetryPipeline)  │    │
                 │     │     ┌───────────────────────┐   │    │
                 │     │     │  DOMAIN (core):       │   │    │
                 │     │     │  Reading, rules,      │   │    │
                 │     │     │  converter, PORTS     │   │    │
                 │     │     │  (ITelemetryStore,    │   │    │
                 │     │     │   IShutdownTrigger)   │   │    │
                 │     │     └───────────────────────┘   │    │
                 │     └─────────────────────────────────┘    │
                 └────────────────────────────────────────────┘
        ALL dependencies point INWARD. The core knows nothing about EF, HTTP, or I2C.
```

The core **owns** the interfaces ("ports"); the outer ring **implements** them ("adapters"). That's the dependency inversion principle applied to a whole codebase. Your Lecture 001 refactoring *is* this at small scale. `TelemetryPipeline` depends on `ITelemetryStore`, not on EF Core.

**Weakness:** it can produce lots of ceremony (mapping between identical-looking types in each ring) for simple CRUD apps.

### 8.3 Vertical slices: organize by feature

```
  Features/
  ├── IngestTelemetry/        ← everything for this feature: handler, validation, store access
  ├── GetLatestReadings/
  ├── RegisterShutdownHost/
  └── EvaluatePowerPolicy/
  Shared/                     ← only genuinely shared code
```

Each slice owns its full path from input to output. Changes to one feature touch one folder. It pairs well with small projects and teams. **Weakness:** real cross-cutting logic can end up duplicated. Watch the `Shared/` folder.

### 8.4 Choosing, and "screaming architecture"

| Situation | Good fit |
|---|---|
| Small CRUD app, few rules | Simple layered, or vertical slices |
| Rich domain rules + multiple I/O technologies (hardware, DB, network) | **Ports and adapters** |
| Many independent features, frequent changes per feature | **Vertical slices** (can live *inside* a ports-and-adapters structure) |
| Several deployable processes sharing logic | Shared core libraries + one thin host project per process (Lecture 001 §3.2) |

Robert Martin's phrase **"screaming architecture"**: the top-level folder structure should *scream what the system does* ("Telemetry, Shutdown, Hosts"), not *what framework it uses* ("Controllers, Services, Models"). Open a repo and look at the top-level folders. That's the fastest test of whether its organization will help or fight you.

### 8.5 The rules that matter more than the style

Whatever style a team picks, maintainable organizations share these properties:

1. **Dependencies point toward stability.** Volatile details (UI, database, vendors) depend on stable policy, never the reverse.
2. **No cycles** between projects, namespaces, or folders.
3. **Each boundary has a small, deep interface** (§6).
4. **Things that change together live together.**
5. **The structure is enforced, not just hoped for:** project references, `internal` visibility, and (⚫) architecture tests (NetArchTest, ArchUnitNET) that fail the build when a layer is violated.

---

## 9. Reviewing code like a senior

Tag: 🟢 **OWN IT**. Giving good reviews is one of the most visible mid-level behaviors. Here is a checklist in the order seniors actually think:

```
 1. PURPOSE      Do I understand what this change is for? (If not, ask before reviewing lines.)
 2. DESIGN       Responsibilities: does each unit have one reason to change?
                 Boundaries: do dependencies point the right way? Any new cycles?
                 Lifetimes: does state live in an object with the right lifetime? (§2.2 #4)
 3. CORRECTNESS  Edge cases, error paths, null, empty, overflow, time zones, concurrency, cancellation
 4. CHANGE       Run 2–3 likely change scenarios in your head (§3 Step 5). What would they cost?
 5. TESTS        Do tests cover behavior (not implementation)? Would they catch the obvious regression?
 6. OPERABILITY  Logs useful and structured? Metrics? Would on-call understand a failure at 3 a.m.?
 7. READABILITY  Names, levels of abstraction, comments that explain WHY
 8. NITS         Formatting, style. Prefix with "nit:" and never block on them.
```

How to *phrase* comments so they help:

| Weak comment | Strong comment |
|---|---|
| "This is messy." | "This method parses *and* persists. Splitting them would let us unit-test the parsing without a DB. Thoughts?" |
| "Don't use a bool here." | "The `isSimulated` flag changes behavior in two places. Could we register a `NullTelemetryStore` in Development instead?" |
| "Wrong." | "I think `_lowCount` resets each scope because this class is scoped (via `DbContext`). Is that intended?" |
| "Use a pattern." | "This `if/else` on `kind` will grow with every sensor. A lookup table would keep it to one line per kind." |

The formula: **observation → consequence → suggestion → question.** It's specific, kind, and invites discussion. It also makes *you* look like someone who thinks in consequences, which is what reviewers of *your* promotion case look for.

---

## 10. Practice regimen

Knowing the smells isn't the skill. **Seeing them fast in unfamiliar code** is. That only comes from reps. Pick from these, in this order:

1. **Refactor your own Lecture 001 lab.** Apply §3 to your Sensor Station: extract a `TelemetryPipeline`, move the watchdog's debounce into a rule class, and write the change-scenario table for your own code.
2. **The Gilded Rose refactoring kata (C# version).** A famous exercise: a deliberately horrible method with a requirement to add a feature. You must first write characterization tests, then refactor, then add the feature. It trains exactly the "tests before refactoring" discipline. (Emily Bache maintains versions in many languages, including C#, on GitHub.)
3. **"Predict the review."** Pick a *merged* PR in dotnet/iot, dotnet/runtime's `Microsoft.Extensions.*`, or YARP. Read only the diff, write your own review comments, *then* read the real review thread and compare. Free senior feedback, forever. (The companion career lecture develops this.)
4. **Design journal.** After any review you attend, write down each design comment, name the smell from §4, and write the principle behind it (keep work details generic). In a month you'll have your own field guide.
5. **Re-implement a small, well-designed library from its interface.** For example, write your own minimal `Channel<T>` or options-binding system, then compare with the real one. It teaches you how experts shaped the interface.
6. **Teach it.** Write a short post explaining one smell with a before/after. Teaching forces precision.

---

## 11. Reading list

In priority order for you:

| Book / resource | Why *you* should read it | Priority |
|---|---|---|
| **John Ousterhout, *A Philosophy of Software Design* (2nd ed.)** | Deep modules, information hiding, "complexity is incremental." Directly addresses your abstraction discomfort. Short. | ⭐ Read first |
| **Martin Fowler, *Refactoring* (2nd ed.)** | The catalog of smells and moves used in §3–§4. Its examples are JavaScript, but the ideas are language-neutral. | ⭐ |
| **Steven van Deursen & Mark Seemann, *Dependency Injection: Principles, Practices, and Patterns*** | The definitive DI book, in C#. Covers lifetimes, captive dependencies, and composition roots in depth. | ⭐ For your .NET focus |
| **Krzysztof Cwalina, Jeremy Barton, Brad Abrams, *Framework Design Guidelines* (3rd ed.)** | **Microsoft's own** rules for designing .NET APIs, with commentary from the people who built the BCL. Invaluable before writing an API proposal (Lecture 002 §12.3). | High |
| **Sandi Metz, "The Wrong Abstraction"** (blog post) and talks | The antidote to over-abstraction: when duplication is better | Short, high value |
| ***Head First Design Patterns*** (2nd ed.) | The friendliest intro to the classic patterns (Java, easy to translate) | Optional |
| **Robert C. Martin, *Clean Architecture*** | Dependency rule, ports and adapters, screaming architecture | Optional; read critically |

---

## 12. Self-check questions

1. What does "it's doing two things at once" mean in design vocabulary? (§1)
   <details><summary>Answer</summary>Low cohesion: the unit has more than one reason to change, so changes driven by different people or requirements collide in the same code.</details>

2. Define cohesion and coupling in one sentence each. (§1)
   <details><summary>Answer</summary>Cohesion: how strongly the contents of a unit belong together (high is good). Coupling: how much a unit depends on another unit's details (low is good).</details>

3. In the §2 example, why is `_lowCount` a *bug*, not just a style issue? (§2.2)
   <details><summary>Answer</summary>The class depends on a scoped <code>DbContext</code>, so it's scoped too. It's recreated per scope, and the counter resets, so the debounce never accumulates in production.</details>

4. What replaced the `isSimulated` flag, and why is that better? (§3 Step 3)
   <details><summary>Answer</summary>A different <code>ITelemetryStore</code> registration (a Null Object in Development). Behavior variation moves out of the logic and into composition, so the logic has one path and the variation is chosen in one place.</details>

5. How should you judge whether a refactoring improved a design? (§3 Step 5)
   <details><summary>Answer</summary>By simulating likely changes and comparing the cost (files touched, risk, testability) before and after, not by counting lines or classes.</details>

6. What's the difference between *divergent change* and *shotgun surgery*? (§4.2)
   <details><summary>Answer</summary>Divergent change: one class changes for many unrelated reasons. Shotgun surgery: one change forces edits in many classes. They're opposite failures of grouping.</details>

7. State SRP precisely. What is it NOT? (§5)
   <details><summary>Answer</summary>A module should have one reason to change (one actor or requirement source). It isn't "every class should do one tiny thing."</details>

8. When is duplication better than an abstraction? (§5, DRY)
   <details><summary>Answer</summary>When the similar code changes for different reasons, or when you don't yet know the right abstraction. The wrong abstraction costs more than duplication.</details>

9. What makes a module "deep"? Give a .NET example. (§6)
   <details><summary>Answer</summary>A simple interface hiding a lot of implementation complexity. For example <code>ILogger</code>, <code>HttpClient</code>, <code>Channel&lt;T&gt;</code>, or a Unix file descriptor.</details>

10. Why is a generic repository over EF Core often a shallow module? (§6, §7)
    <details><summary>Answer</summary><code>DbSet</code>/<code>DbContext</code> already implement repository and unit of work. A wrapper that forwards each call hides little, adds an interface to maintain, and often removes useful capabilities (<code>IQueryable</code>, <code>Include</code>).</details>

11. Which pattern is `BackgroundService` an example of? And ASP.NET Core middleware? (§7)
    <details><summary>Answer</summary><code>BackgroundService</code>: Template Method. Middleware: Chain of Responsibility / Pipeline.</details>

12. In ports and adapters, who owns the interfaces, and which way do dependencies point? (§8.2)
    <details><summary>Answer</summary>The core (domain/application) owns the ports. Adapters implement them. All dependencies point inward, toward the core.</details>

13. What is "screaming architecture"? (§8.4)
    <details><summary>Answer</summary>A top-level structure that announces what the system does (its features or domain), not which framework it uses.</details>

14. Give the four-part formula for a strong review comment. (§9)
    <details><summary>Answer</summary>Observation → consequence → suggestion → question.</details>

15. Why write characterization tests before refactoring legacy code? (§3 Step 6, §10)
    <details><summary>Answer</summary>They pin the current behavior (even odd behavior), so you can prove the refactoring changed structure, not behavior.</details>

---

*End of Lecture 003. Next in this folder: 004, "Generic Host & DI, in depth." Keep the companion career lecture open alongside this one. It turns this material into a weekly practice.*
