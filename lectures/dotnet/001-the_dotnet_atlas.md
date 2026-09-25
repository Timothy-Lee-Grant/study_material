2026_09_25_01_36-(The-DotNet-Atlas)

# Lecture 001 — The .NET Atlas: From `dotnet build` to a Running Host

> **For:** Timothy Lee Grant
> **Date:** 2026-09-25
> **Target platform:** .NET 10 (LTS, released November 2025) and C# 14. Almost everything here also applies to .NET 6–9; where a version matters, it's called out.
>
> **Why this lecture, and why now:** You just spent six months building real .NET software by hand, in the dark, from the bottom up. You now have a pile of hard-won *pieces*: a worker, P/Invoke, a calculator, cmdlets, a state model, a pipeline you watched run. What you don't have yet is the **map** that shows how those pieces fit into one ecosystem, and which parts of that ecosystem you're allowed to treat as a black box. This lecture is that map. It's the top-down view you wished someone had handed you on day one.
>
> **Read time:** This isn't a one-sitting document. Plan on 4–6 sessions for the reading and 2–3 for the lab (§17).

---

## Table of Contents

- [0. Preface: how to use this document](#0-preface-how-to-use-this-document)
- [1. The one-page map](#1-the-one-page-map)
- [2. The cast of characters](#2-the-cast-of-characters)
- [3. Part I — Build time: from source files to an assembly](#3-part-i--build-time-from-source-files-to-an-assembly)
- [4. Part II — Launch time: how a `.dll` becomes a running process](#4-part-ii--launch-time-how-a-dll-becomes-a-running-process)
- [5. Part III — The runtime: CLR, JIT, GC, and the type system](#5-part-iii--the-runtime-clr-jit-gc-and-the-type-system)
- [6. Part IV — C# for a C programmer: the parts you actually meet](#6-part-iv--c-for-a-c-programmer-the-parts-you-actually-meet)
- [7. Part V — Abstraction: interfaces, and how to read a codebase top-down](#7-part-v--abstraction-interfaces-and-how-to-read-a-codebase-top-down)
- [8. Part VI — The Generic Host and inversion of control](#8-part-vi--the-generic-host-and-inversion-of-control)
- [9. Part VII — Dependency injection, configuration, logging](#9-part-vii--dependency-injection-configuration-logging)
- [10. Part VIII — async/await: what a `Task` actually is](#10-part-viii--asyncawait-what-a-task-actually-is)
- [11. Part IX — Native interop: reviewing your own P/Invoke work](#11-part-ix--native-interop-reviewing-your-own-pinvoke-work)
- [12. Part X — Data: EF Core and the relational model](#12-part-x--data-ef-core-and-the-relational-model)
- [13. Part XI — Talking to others: ASP.NET Core, JSON, gRPC](#13-part-xi--talking-to-others-aspnet-core-json-grpc)
- [14. Part XII — PowerShell is .NET: what your cmdlets really are](#14-part-xii--powershell-is-net-what-your-cmdlets-really-are)
- [15. Part XIII — Testing](#15-part-xiii--testing)
- [16. Part XIV — Shipping: publish, containers, systemd, pipelines](#16-part-xiv--shipping-publish-containers-systemd-pipelines)
- [17. The lab: build "Sensor Station" by hand](#17-the-lab-build-sensor-station-by-hand)
- [18. Firmware ↔ .NET translation table](#18-firmware--net-translation-table)
- [19. Tooling fluency: the keyboard is part of the job](#19-tooling-fluency-the-keyboard-is-part-of-the-job)
- [20. Common mistakes](#20-common-mistakes)
- [21. Interview relevance](#21-interview-relevance)
- [22. Self-check questions](#22-self-check-questions)
- [23. Roadmap for this folder](#23-roadmap-for-this-folder)
- [24. Glossary](#24-glossary)

---

## 0. Preface: how to use this document

### 0.1 The one idea to hold onto

Your persona file records a painful moment: someone asked *"how is a state created?"* and you answered with memory allocation inside a method. The right answer was one sentence: *"You call the add-state operation on the state service."*

This whole lecture trains one skill: **answering at the altitude of the question.** .NET is layered on purpose. Each layer has a contract, and each layer lets you *not* think about the layers below it until you need to. Your instinct to understand everything is an asset. It just has to run **top-down**: map first, contract second, internals third, and only where the contract isn't enough.

### 0.2 The black-box legend

Every major section is tagged with one of these. It's permission to stop digging.

| Tag | Meaning | What you should be able to do |
|---|---|---|
| 🟢 **OWN IT** | Core concept. Every .NET engineer knows this cold. Gaps here hurt credibility. | Explain it on a whiteboard, with trade-offs, without notes. |
| 🔵 **CONTRACT** | Know what goes in, what comes out, what can fail, and the lifetime. Internals are optional. | Use it correctly and read code that uses it. |
| ⚫ **BLACK BOX (for now)** | Real and interesting, but not needed to be effective yet. Parked for a later lecture. | Recognize the name and know what problem it solves. |

When you catch yourself three files deep inside a ⚫ topic, that's the signal to climb back up.

### 0.3 Suggested study plan

| Session | Read | Do |
|---|---|---|
| 1 | §0–§2 (map + cast) | Draw the map from memory on paper. Name every character. |
| 2 | §3–§4 (build + launch) | Open any real `.csproj` and `bin/` folder and identify every file. |
| 3 | §5–§6 (runtime + C#) | Self-check Q1–Q10. |
| 4 | §7–§9 (abstraction, host, DI) | Lab steps 1–4. |
| 5 | §10–§11 (async, interop) | Lab steps 5–7. Re-read your old interop code with fresh eyes (at work, not here). |
| 6 | §12–§16 (data, web, PowerShell, tests, shipping) | Lab steps 8–9, then the stretch goals. Self-check Q11–Q31. |
| Later | §18–§24 | Keep §19 and §20 open as references. |

### 0.4 A note on AI and your zero-AI job

Everything in the lab is meant to be **typed by you**. It's the same muscle your job demands. Use AI here the way you'd use a senior engineer: to answer questions *after* you've tried something, not to write the code.

---

## 1. The one-page map

Here's the whole territory. Read it top to bottom. That's the direction you should now think in.

```
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │  YOUR APPLICATION CODE                                                      │
 │  Workers, services, controllers, cmdlets, calculators, models               │
 │  You write this. It is mostly *called by* the layer below it.               │
 ├─────────────────────────────────────────────────────────────────────────────┤
 │  APP MODELS / FRAMEWORKS  (they own the main loop — inversion of control)   │
 │  Generic Host · ASP.NET Core (Kestrel, middleware, MVC, Blazor) · gRPC      │
 │  EF Core · PowerShell SDK · xUnit test runner                               │
 ├─────────────────────────────────────────────────────────────────────────────┤
 │  MICROSOFT.EXTENSIONS.*  (the "glue" libraries every app model shares)      │
 │  DependencyInjection · Configuration · Options · Logging · Hosting · Http   │
 ├─────────────────────────────────────────────────────────────────────────────┤
 │  BCL — Base Class Library  ("the standard library")                         │
 │  System.Collections · System.IO · System.Net · System.Text.Json ·           │
 │  System.Threading(.Tasks/.Channels) · System.Runtime.InteropServices · LINQ │
 ├─────────────────────────────────────────────────────────────────────────────┤
 │  THE RUNTIME (CoreCLR)                                                      │
 │  Type loader · JIT compiler · Garbage collector · Thread pool ·             │
 │  Exception handling · Interop marshaller                                    │
 ├─────────────────────────────────────────────────────────────────────────────┤
 │  OPERATING SYSTEM  (Linux on the Pi / Windows / macOS)                      │
 │  processes · threads · sockets · files · signals (SIGTERM) · .so / .dll     │
 └─────────────────────────────────────────────────────────────────────────────┘

   Beside the stack, at BUILD time (not running in production):
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │  THE SDK / TOOLCHAIN                                                        │
 │  dotnet CLI · MSBuild (the build engine) · Roslyn (the C# compiler) ·       │
 │  NuGet (package manager) · templates (dotnet new) · test host               │
 └─────────────────────────────────────────────────────────────────────────────┘
```

Three sentences to memorize:

1. **The SDK turns C# into IL inside assemblies (`.dll`s).** That's build time.
2. **The runtime loads those assemblies, JIT-compiles IL to machine code, and manages memory.** That's run time.
3. **Frameworks like the Generic Host own the program's control flow and call *your* code.** That's why your code often looks like it's "never called by anything."

### 1.1 Where your six months of work sits on this map

| What you did | Layer |
|---|---|
| Firmware on the microcontroller | Not on the map. A different machine, talking over I2C. |
| The ingestion worker (`BackgroundService`) | Your code, called by the **Generic Host** |
| P/Invoke into a native `.so` | Your code → **BCL interop** → **runtime marshaller** → **OS dynamic loader** |
| State service calls | Your code → a **shared class library** (just more "your code," registered in **DI**) |
| Derived-state calculation / hex calculator | Pure your-code logic. Plus **polymorphism** (§6, §7). |
| PowerShell cmdlets | Your code, called by the **PowerShell engine**, which is itself a .NET app (§14) |
| Emulator container / systemd units | **OS** + deployment (§16) |
| Azure DevOps pipeline | **SDK/toolchain** running on a build agent (§16) |

If you can place any new piece of work on this map in the first five minutes, you'll always know which questions to ask.

---

## 2. The cast of characters

You learn best when components are people. Here's the troupe. Each gets a name, a job, what they want, and who they talk to. Later sections refer back to them.

| # | Character | Real name | Job | Wants | Talks to |
|---|---|---|---|---|---|
| 1 | **The Foreman** | MSBuild | Reads the blueprints (`.csproj`, `.slnx`) and runs the build steps in the right order | Every input declared, every output reproducible | Roslyn, NuGet, the file system |
| 2 | **The Translator** | Roslyn (C# compiler, `csc`) | Turns C# into IL + metadata. Also powers IDE squiggles and analyzers. | Type-correct code | The Foreman gives it source files and references |
| 3 | **The Quartermaster** | NuGet | Fetches versioned packages and resolves the dependency graph | One consistent version of each package | nuget.org / private feeds; hands `.dll`s to the Foreman |
| 4 | **The Gatekeeper** | The `dotnet` host (muxer → hostfxr → hostpolicy) | Starts the process, picks the runtime version, finds your assemblies | A valid `runtimeconfig.json` and `deps.json` | The OS; hands control to the Stage Manager |
| 5 | **The Stage Manager** | CoreCLR (the runtime) | Loads types, runs code, enforces safety | Verifiable IL; nobody touching memory they don't own | Everyone at run time |
| 6 | **The Interpreter-on-demand** | The JIT (RyuJIT) | Compiles each method's IL to machine code the first time it's called, and recompiles hot methods better later | Hot paths it can optimize | Stage Manager |
| 7 | **The Janitor** | The garbage collector | Finds objects nobody references and reclaims their memory, compacting the heap | Short-lived objects; few long-lived giants | Pauses your threads briefly to work |
| 8 | **The Staffing Agency** | The DI container (`IServiceProvider`) | Knows which concrete class fulfills each interface, how long each hire lives, and builds whole object graphs on request | Every dependency registered before the doors open | The Conductor, and every constructor |
| 9 | **The Conductor** | The Generic Host (`IHost`) | Wires config, logging, DI; starts every hosted service; handles Ctrl-C / SIGTERM; stops everything gracefully | A clean start and a clean stop | Staffing Agency, Night-shift Workers, the OS |
| 10 | **The Night-shift Worker** | A `BackgroundService` | Runs a long loop in the background for the life of the app | A `CancellationToken` to know when to go home | Conductor (who hires and dismisses them) |
| 11 | **The Archivist** | `IConfiguration` / Options | Merges settings from JSON files, environment variables, and the command line into one lookup | Settings in known places, in a known priority order | Everyone who needs a setting |
| 12 | **The Scribe** | `ILogger<T>` | Records structured events with levels, categories, and properties | Message templates, not string concatenation | Log sinks (console, journald, files, OpenTelemetry) |
| 13 | **The Doorman** | Kestrel | Accepts TCP connections and parses HTTP | Well-formed requests | The Assembly Line |
| 14 | **The Assembly Line** | ASP.NET Core middleware pipeline | Passes each request through ordered stations (logging, auth, routing, your endpoint) | Stations added in the right order | Doorman, your endpoints |
| 15 | **The Diplomat** | P/Invoke + the interop marshaller | Carries calls across the border between managed (.NET) and native (C) land, translating data layouts | Exact agreement on struct layout and calling convention | Stage Manager, the native `.so` |
| 16 | **The Bookkeeper** | EF Core `DbContext` | Translates LINQ into SQL, tracks changes to objects, and saves them as SQL statements | A short-lived unit of work (one per request/operation) | The database, the Staffing Agency (who hires it per scope) |
| 17 | **The Courier** | gRPC client/server | Delivers strongly typed messages between processes over HTTP/2 using a `.proto` contract | Both sides compiled from the same `.proto` | Kestrel on the server side |
| 18 | **The Inspector** | The test runner (xUnit + test host) | Finds test methods, runs them in isolation, reports pass/fail | Code with seams (interfaces) where fakes can be inserted | Your code, via the Staffing Agency or directly |

A useful exercise: for any bug or task, ask **"which character is involved?"** A "can't resolve service" exception belongs to the Staffing Agency. "Could not load file or assembly" belongs to the Gatekeeper or the Foreman. An `EntryPointNotFoundException` belongs to the Diplomat. Knowing the character tells you which docs to open.

---
## 3. Part I — Build time: from source files to an assembly

Tag: 🟢 **OWN IT**. This part answers the question that confused you most in month one: *"Why are there so many folders and `.csproj` files, and how do they connect?"*

### 3.1 Four words that are NOT synonyms

Most of the early confusion comes from treating these as the same thing. They're four different things that *usually* share a name.

| Word | What it is | Exists at | Analogy |
|---|---|---|---|
| **Solution** (`.sln` / `.slnx`) | A *list of projects* so an IDE or `dotnet build` can open or build them together. Adds nothing to the compiled output. | Dev time only | A workspace or a bookmark folder |
| **Project** (`.csproj`) | A *build recipe*: which source files, which target framework, which references, what kind of output | Build time | A Makefile target |
| **Assembly** (`.dll` / `.exe`) | The *compiled output* of one project: IL + metadata + manifest. The unit of deployment, versioning, and loading. | Run time | A `.o`/`.elf` that's linked at load time instead of build time |
| **Namespace** (`namespace Foo.Bar;`) | A *naming prefix* for types, to avoid collisions. Purely logical. | Source/compile time | A C naming convention like `hal_i2c_*`, but enforced by the compiler |

Key facts:

- One project produces **exactly one** assembly.
- One assembly can contain **many** namespaces, and one namespace can be spread across **many** assemblies. By convention, the project `Acme.Telemetry.State` produces `Acme.Telemetry.State.dll`, which contains the namespace `Acme.Telemetry.State`. That's just a convention.
- A solution is optional. You can `dotnet build path/to/One.csproj` without any solution.
- Folders inside a project usually map to sub-namespaces (`State/Calculators/HexCalculator.cs` → `Acme.Telemetry.State.Calculators`). That's also a convention (the IDE generates it), not a rule.

> **New in .NET 10:** `dotnet new sln` now creates the XML-based **`.slnx`** format instead of the old `.sln` format. Both mean the same thing. `.slnx` is just readable. You'll see both in the wild for years.

### 3.2 Why enterprise solutions have so many projects

You thought the folders were random. They almost never are. **Projects are the tool .NET uses to enforce architecture.** A project can only use types from assemblies it explicitly references, and project references can't form cycles. So splitting code into projects is how a team *physically prevents* the wrong layer from calling the wrong layer.

A typical solution shape (generic, but you'll recognize it):

```
MySystem.slnx
│
├── src/
│   ├── MySystem.Contracts/        ← class library: interfaces + DTOs only. Depends on nothing.
│   ├── MySystem.State/            ← class library: state model + IStateService implementation
│   ├── MySystem.Shutdown/         ← class library: shutdown orchestration
│   ├── MySystem.Data/             ← class library: EF Core DbContext, migrations
│   │
│   ├── MySystem.Worker/           ← EXECUTABLE (entry point): Generic Host + BackgroundServices
│   ├── MySystem.Web/              ← EXECUTABLE (entry point): ASP.NET Core dashboard
│   ├── MySystem.AuditLog/         ← EXECUTABLE (entry point): gRPC service
│   └── MySystem.PowerShell/       ← class library LOADED BY PowerShell (no Main of its own)
│
└── tests/
    ├── MySystem.State.Tests/      ← unit tests for the State library
    └── MySystem.IntegrationTests/ ← spins up real pieces together
```

The dependency graph, as a list (read "→" as "references"):

```
 Worker      → State, Shutdown, Data, Contracts
 Web         → State, Data, Contracts
 AuditLog    → Contracts
 PowerShell  → State, Data, Contracts
 State       → Data, Contracts
 Shutdown    → Contracts
 Data        → Contracts
 Contracts   → (nothing)
 *.Tests     → the project(s) they test
```

And as layers:

```
 Layer 3  EXECUTABLES      Worker     Web     AuditLog     PowerShell module
                              │        │         │               │
                              ▼        ▼         ▼               ▼
 Layer 2  LIBRARIES        State ──► Data      Shutdown
                              │        │          │
                              ▼        ▼          ▼
 Layer 1  CONTRACTS        ─────────── Contracts ───────────

 Arrows only ever point DOWN. The project reference graph makes the upward
 direction impossible to compile, and that's the architecture being enforced.
```

How to read an unfamiliar solution in five minutes:

1. **Find the executables.** Look for `<OutputType>Exe</OutputType>`, or an SDK of `Microsoft.NET.Sdk.Web` / `Microsoft.NET.Sdk.Worker`, or a `Program.cs`. Each one is a separate **process** at run time. That's your list of "who actually runs."
2. **Draw the reference graph.** Open each `.csproj` and look only at `<ProjectReference>` lines. Ten minutes on paper gives you the architecture.
3. **Find the contracts.** Libraries named `*.Contracts`, `*.Abstractions`, or `*.Interfaces`, or `I*.cs` files, are the API surface (§7).
4. **Only now open implementation files.**

### 3.3 Anatomy of a modern (SDK-style) `.csproj`

```xml
<Project Sdk="Microsoft.NET.Sdk.Worker">          <!-- ① which SDK: a bundle of default build logic -->

  <PropertyGroup>                                  <!-- ② properties: scalar settings -->
    <TargetFramework>net10.0</TargetFramework>     <!--    which .NET API surface to compile against -->
    <OutputType>Exe</OutputType>                   <!--    Exe = has an entry point; Library = doesn't -->
    <Nullable>enable</Nullable>                    <!--    nullable reference type warnings (§6.3) -->
    <ImplicitUsings>enable</ImplicitUsings>        <!--    auto-adds common `using` lines -->
    <RootNamespace>MySystem.Worker</RootNamespace>
    <AllowUnsafeBlocks>true</AllowUnsafeBlocks>    <!--    needed for LibraryImport / pointers (§11) -->
  </PropertyGroup>

  <ItemGroup>                                      <!-- ③ items: lists of things -->
    <ProjectReference Include="..\MySystem.State\MySystem.State.csproj" />
    <PackageReference Include="Microsoft.Extensions.Hosting.Systemd" Version="10.0.0" />
    <Reference Include="Vendor.Sdk">               <!--    raw assembly reference (see §3.5) -->
      <HintPath>..\..\lib\Vendor.Sdk.dll</HintPath>
    </Reference>
  </ItemGroup>

  <ItemGroup>
    <None Update="appsettings.json" CopyToOutputDirectory="PreserveNewest" />
  </ItemGroup>

</Project>
```

The things that surprised you, explained:

- **There's no list of `.cs` files.** SDK-style projects glob `**/*.cs` under the project folder automatically. Any `.cs` file you drop in the folder is compiled. (Old-style pre-2017 projects listed every file. You may still meet those in legacy code.)
- **`Sdk="..."`** imports hundreds of lines of default MSBuild logic. `Microsoft.NET.Sdk` is the base; `.Web` adds ASP.NET Core; `.Worker` adds worker-service defaults. The SDK name tells you what kind of app this is at a glance.
- **`TargetFramework`** (TFM) is the contract you compile against: `net10.0`, `net8.0`, `netstandard2.0` (an old "portable" API subset, still used by libraries that must load in many hosts, including older PowerShell).
- **MSBuild is a language.** `PropertyGroup` holds variables, `ItemGroup` holds lists, and *targets* (hidden in the SDK) are functions like `Restore`, `Build`, `Publish`. You'll rarely write targets. You'll often read properties.

Files that sit *above* projects and apply to all of them:

| File | Purpose |
|---|---|
| `Directory.Build.props` | Properties shared by every project below this folder (common `TargetFramework`, `Nullable`, warnings-as-errors) |
| `Directory.Packages.props` | **Central Package Management**: every NuGet version in one place; `.csproj`s list packages without versions |
| `global.json` | Pins which **SDK** version `dotnet` uses in this repo (so CI and your laptop agree) |
| `nuget.config` | Which package feeds to use (e.g., a company Azure Artifacts feed) |

### 3.4 What `dotnet build` actually does

```
 dotnet build
     │
     ▼
 ① RESTORE (Quartermaster)
     Reads every PackageReference, resolves the full transitive graph,
     downloads to ~/.nuget/packages, writes obj/project.assets.json
     │
     ▼
 ② RESOLVE REFERENCES (Foreman)
     Builds referenced projects first (the DAG, bottom-up),
     gathers the list of every .dll this project compiles against
     │
     ▼
 ③ COMPILE (Translator / Roslyn)
     C# source + reference assemblies  ──►  obj/Debug/net10.0/MyApp.dll  (IL + metadata)
     Source generators run here (they write extra C# during compilation — §11 uses one)
     │
     ▼
 ④ COPY TO OUTPUT
     obj/... ──► bin/Debug/net10.0/  plus dependency .dlls, content files,
     MyApp.runtimeconfig.json, MyApp.deps.json, and the native apphost launcher
```

- `obj/` is the scratch workspace. `bin/` is the result. Deleting both is the .NET version of `make clean` and fixes a surprising number of weird build problems.
- **Debug vs Release** (`-c Release`) changes optimization and `#if DEBUG` code. The `.pdb` file is the symbol file, the equivalent of DWARF debug info in your `.elf`.

### 3.5 Three ways to depend on code (and why your vendor SDK looked "strange")

| Mechanism | Syntax | What happens | When it's used |
|---|---|---|---|
| **ProjectReference** | `<ProjectReference Include="..\X\X.csproj"/>` | X is built first; its `.dll` is copied into your output | Code in the same solution |
| **PackageReference** | `<PackageReference Include="Serilog" Version="4.x"/>` | NuGet downloads a versioned `.nupkg` (a zip of `.dll`s + metadata + its own dependencies) | Anything published to a feed. The normal case. |
| **Raw Reference** | `<Reference Include="Vendor"><HintPath>lib/Vendor.dll</HintPath></Reference>` | You point directly at a `.dll` file on disk. No versioning, no dependency graph, no restore. | Vendor SDKs that were never published as NuGet packages. Very common with enterprise and hardware vendors. |

So the vendor virtualization SDK you noticed wasn't strange in principle. It's a .NET assembly distributed as files instead of a package. Two separate ideas were tangled together in your observation:

- **How you *reference* a library** (package vs raw `.dll`) is a build-time concern.
- **Whether it's "a dependency-injected service"** is a design choice *in your code*. Any class from any assembly can be wrapped in your own interface and registered in DI (§9). A good team often does exactly that: `IVmController` (your interface) → `VendorVmController` (your adapter class that calls the raw vendor API). That's the **Adapter pattern**, and it's also what makes the shutdown logic unit-testable without a real hypervisor.

### 3.6 Firmware twin

| Firmware build | .NET build |
|---|---|
| Makefile / CMakeLists | `.csproj` (+ the SDK's hidden targets) |
| `gcc -c` → `.o` | Roslyn → IL inside an assembly |
| Linker resolves symbols → one `.elf` | **No static link.** Each assembly stays separate; references are resolved **at load time** by the runtime |
| Vendor HAL as `.a` + headers | Vendor SDK as `.dll` (metadata *is* the header, so no separate header files are needed) |
| Map file | `deps.json` (what goes with what) + metadata |
| `-O2`, `DEBUG` define | `-c Release`, `#if DEBUG` |

The biggest mental shift: **assemblies are self-describing.** The metadata inside a `.dll` lists every type, method, and field with its signature. That's why C# has no header files, why reflection works, and why your IDE can show you the API of a `.dll` it has never seen the source for.

---

## 4. Part II — Launch time: how a `.dll` becomes a running process

Tag: 🔵 **CONTRACT** (with a few 🟢 facts). This matters for deployment (systemd units that run `dotnet MyApp.dll`) and for the "could not load" class of errors.

### 4.1 What's in `bin/Release/net10.0/`

| File | What it is |
|---|---|
| `MyApp.dll` | **Your code.** Yes, even for an executable, the code lives in a `.dll`. |
| `MyApp` (or `MyApp.exe`) | The **apphost**: a tiny native launcher that does the same thing as `dotnet MyApp.dll` |
| `MyApp.runtimeconfig.json` | Which **shared framework** and version to run on (e.g., `Microsoft.NETCore.App 10.0`, plus `Microsoft.AspNetCore.App` for web apps), and runtime settings like GC mode |
| `MyApp.deps.json` | The full dependency manifest: every assembly (managed and native) this app needs and where to find it |
| `MyApp.pdb` | Debug symbols |
| `Other.dll`, `SomePackage.dll` | Referenced projects and NuGet packages |
| `appsettings.json` | Config, if marked to copy |
| `runtimes/linux-arm64/native/*.so` | Native libraries shipped inside NuGet packages, per platform |

### 4.2 The launch sequence

```
 $ dotnet MyApp.dll          (or ./MyApp, or systemd ExecStart=/usr/bin/dotnet /opt/app/MyApp.dll)
      │
      ▼
 ① Gatekeeper, part 1: the "muxer" (dotnet executable)
      "Is this a command like `build`, or a path to an app?" → an app
      │
      ▼
 ② Gatekeeper, part 2: hostfxr
      Reads MyApp.runtimeconfig.json → "needs Microsoft.NETCore.App 10.0"
      Finds an installed runtime (e.g. /usr/share/dotnet/shared/Microsoft.NETCore.App/10.0.x)
      Applies roll-forward rules (latest patch of 10.0 by default)
      │
      ▼
 ③ Gatekeeper, part 3: hostpolicy
      Reads MyApp.deps.json → builds the list of assemblies the runtime may load
      and the native library search paths
      │
      ▼
 ④ Stage Manager wakes up: CoreCLR initializes
      creates the GC heap, the thread pool, loads System.Private.CoreLib
      │
      ▼
 ⑤ Loads MyApp.dll, finds the entry point
      (top-level statements in Program.cs compile to a hidden static Main)
      │
      ▼
 ⑥ JIT compiles Main → runs it
      Every other assembly is loaded LAZILY, the first time code needs a type from it
```

Point ⑥ explains a classic surprise: a missing `.dll` doesn't fail at startup. It fails **the first time a method that uses it is JIT-compiled**, which could be hours later.

### 4.3 Framework-dependent vs self-contained

| | Framework-dependent (default) | Self-contained |
|---|---|---|
| Command | `dotnet publish -c Release` | `dotnet publish -c Release -r linux-arm64 --self-contained` |
| Needs .NET installed on target? | **Yes** | No. The runtime is copied in. |
| Size | Small (your `.dll`s) | Large (~70 MB+ before trimming) |
| Patching | Update the machine's runtime once, and every app benefits | Rebuild and redeploy each app |
| Typical for | Servers, containers with a .NET base image | Appliances, OS images, machines you don't control |

**RID** (Runtime Identifier) = OS + CPU architecture: `linux-x64`, `linux-arm64` (64-bit Raspberry Pi OS), `linux-arm` (32-bit), `win-x64`, `osx-arm64`. You need one whenever native code or a bundled runtime is involved.

⚫ **BLACK BOX for now:** trimming (removing unused IL), ReadyToRun (pre-compiling to reduce JIT at startup), Native AOT (no JIT at all, a single native binary, with restrictions on reflection). Know the names and what problem each solves: startup time and size.

### 4.4 Firmware twin

The Gatekeeper is your **bootloader + C runtime startup (`crt0`)**. Firmware startup copies `.data`, zeroes `.bss`, sets up the stack, and calls `main`. The .NET host finds the runtime, sets up the managed heap and thread pool, and calls `Main`. Same idea, more layers.

---
## 5. Part III — The runtime: CLR, JIT, GC, and the type system

Tag: 🟢 **OWN IT** for value vs reference types, the basics of GC, and IL/JIT at the one-paragraph level. ⚫ for GC tuning and JIT internals.

### 5.1 IL: the portable assembly language

Roslyn doesn't produce ARM or x64 machine code. It produces **IL** (Intermediate Language, also called CIL or MSIL), a stack-machine bytecode:

```csharp
static int Add(int a, int b) => a + b;
```

```
.method static int32 Add(int32 a, int32 b)
{
    ldarg.0      // push a
    ldarg.1      // push b
    add          // pop two, push sum
    ret          // return top of stack
}
```

You'll almost never read IL. What matters is *why it exists*: **one `.dll` runs on x64 Windows, an ARM64 Raspberry Pi, and an Apple-silicon Mac.** The machine-specific work happens on the target, at run time. That's how you could build on a dev box or a CI agent and drop the same `.dll`s into the emulator container and the Pi. (Only native pieces like `libpigpio.so` are architecture-specific.)

### 5.2 The JIT: compile on first call

The **Interpreter-on-demand** compiles each method the first time it runs. Modern .NET uses **tiered compilation**:

1. **Tier 0:** compile fast with few optimizations, so startup is quick.
2. The runtime counts calls. Hot methods get **re-compiled at Tier 1** with full optimizations, using profile data collected while running (**Dynamic PGO**, on by default since .NET 8).

Consequences you can use:

- The first call to anything is slower. Benchmarks must warm up (that's why BenchmarkDotNet exists).
- Long-running services (like a worker that runs for months) end up *faster* than a naïve compile, because the JIT optimized for the real workload.

### 5.3 Value types vs reference types (the most important 🟢 in this Part)

| | Value type | Reference type |
|---|---|---|
| Declared with | `struct`, `enum`, `record struct`; built-ins like `int`, `double`, `bool`, `byte`, `DateTime`, `Guid` | `class`, `record` (class), `interface`, `delegate`, arrays, `string` |
| A variable holds | **The data itself** | **A reference** (a managed pointer) to an object on the GC heap |
| Assignment `a = b` | **Copies the data** | **Copies the reference.** Both now point at the same object. |
| Where it lives | **Inline wherever it's declared**: on the stack if it's a local, inside the object if it's a field, inside the array if it's an element | Always on the managed heap |
| Can be `null`? | No (unless `int?` = `Nullable<int>`) | Yes |
| Equality | Built-ins (`int`, `double`…) compare values. Your own `struct` has no `==` unless you define it (`Equals` compares fields). `record struct` gets `==` for free. | `==` compares **references** (identity), except `string` and `record`s, which compare contents |

> ⚠️ **Correct the common myth:** "structs live on the stack, classes live on the heap" is only half true. A struct lives *where it's declared*. A `double` field inside a `StateValue` class is on the heap, inline inside that object. The accurate rule is **"value types are stored inline; reference types are stored by reference."**

The C translation:

```c
// C
struct Reading { uint8_t kind; uint16_t raw; };
struct Reading r1 = {1, 0x0ABC};
struct Reading r2 = r1;           // copy      ← like a C# struct
struct Reading *p1 = malloc(...);
struct Reading *p2 = p1;          // alias     ← like a C# class reference
```

```csharp
// C#
public struct ReadingS { public byte Kind; public ushort Raw; }
public class  ReadingC { public byte Kind; public ushort Raw; }

var s1 = new ReadingS { Kind = 1, Raw = 0x0ABC };
var s2 = s1;  s2.Raw = 0;          // s1.Raw is still 0x0ABC (copy)

var c1 = new ReadingC { Kind = 1, Raw = 0x0ABC };
var c2 = c1;  c2.Raw = 0;          // c1.Raw is now 0 (same object)
```

**Boxing:** when a value type is treated as `object` or as an interface, the runtime copies it into a new heap object (a "box"). It's invisible and costs an allocation. Hot loops that box millions of times show up as GC pressure.

**Why this matters to you specifically:** P/Invoke marshalling (§11) works cleanly with structs that contain only primitive value types. Those are **blittable**: their managed layout is bit-for-bit identical to the C layout. That's why the structs you wrote to mirror the native library were `struct`s and not `class`es.

### 5.4 The Janitor: garbage collection

In firmware you had static allocation, maybe a pool, maybe `malloc`/`free`. In .NET you write `new` and **never** free. The GC does it:

```
 Roots: stack locals, CPU registers, static fields, GC handles
   │
   ▼  "mark": follow every reference from the roots
 Every reachable object is alive. Everything else is garbage.
   │
   ▼  "sweep/compact": reclaim garbage and MOVE live objects together
 Update every reference to point at the new addresses
```

**Generations**, based on the observation that *most objects die young*:

| Generation | Holds | Collected |
|---|---|---|
| Gen 0 | Brand-new objects | Very often, very cheap |
| Gen 1 | Survived one collection (a buffer between 0 and 2) | Sometimes |
| Gen 2 | Long-lived objects (singletons, caches) | Rarely, expensive |
| LOH (Large Object Heap) | Objects ≥ 85,000 bytes (big arrays) | With Gen 2; not compacted by default |
| POH (Pinned Object Heap) | Objects allocated as permanently pinned | With Gen 2; never moved |

Two facts that connect directly to your interop work:

1. **The GC moves objects.** If native code holds a raw pointer to a managed array, and the GC compacts, the pointer is now wrong. That's why interop **pins** memory (temporarily forbids moving it) for the duration of a call.
2. **The GC only knows about managed references.** If the *only* thing that remembers a delegate is a native C library, the GC thinks it's garbage (§11.4, the classic callback crash).

**Deterministic cleanup is a separate mechanism:** the GC reclaims *memory*. It doesn't promptly close file handles, sockets, database connections, or native resources. For those, types implement `IDisposable` and you use `using` (§6.7).

⚫ **BLACK BOX for now:** workstation vs server GC, concurrent/background GC, `GCSettings.LatencyMode`, memory dumps. Revisit when you do performance work.

### 5.5 Threads and the thread pool (preview)

- An OS thread in .NET is `System.Threading.Thread`. It's expensive: about 1 MB of stack reserved, and a kernel object.
- The runtime keeps a **thread pool**: a set of reusable worker threads that run short work items. `Task.Run`, timers, and the continuations after `await` usually run on pool threads.
- A `Task` is **not** a thread. It's a promise of a future result (§10).

### 5.6 Firmware twin

| Firmware | .NET runtime |
|---|---|
| No MMU; you own every byte | Managed heap; the GC owns reclamation |
| Static buffers / memory pools | Gen 2 long-lived objects; `ArrayPool<T>` for reuse |
| Hard-fault on a bad pointer | `NullReferenceException` / `AccessViolationException` (the latter usually means an interop bug) |
| Superloop / RTOS scheduler | Thread pool + task scheduler |
| Startup code (`crt0`) | Host + runtime init (§4) |

---

## 6. Part IV — C# for a C programmer: the parts you actually meet

Tag: 🟢 **OWN IT** for everything except where marked. This isn't a full language tour. It's the subset that fills 95% of enterprise C#, ordered by how often it confused you.

### 6.1 The kinds of types

| Keyword | What it is | When to use it | C analogy |
|---|---|---|---|
| `class` | Reference type with identity, fields, methods; supports inheritance | Services, entities, anything with behavior or identity | `struct` + functions taking `struct*` + a vtable |
| `struct` | Value type | Small, immutable-ish data (≤ ~16–24 bytes), interop layouts | Plain C `struct` |
| `record` / `record class` | Reference type with **value-based equality**, a nice `ToString()`, and `with` copies | Messages, DTOs, events: *data you pass around* | — |
| `record struct` | Same idea, value type | Tiny data like `(Kind, Raw)` frames | — |
| `interface` | A **contract**: member signatures, no state | Service boundaries (§7) | A struct of function pointers that a module must fill in |
| `enum` | Named integer constants (with an underlying type you choose) | Preamble codes, modes | `enum` / `#define` table |
| `delegate` | A type-safe function pointer that can also carry a target object | Callbacks | Function pointer + `void* context` |
| `abstract class` | A partially implemented base class that can't be instantiated | Shared behavior across a family (like a base `Calculator`) | — |
| `static class` | Only static members; can't be instantiated | Pure helpers, extension methods | A `.c` file of free functions |

### 6.2 Members

```csharp
public sealed class TemperatureSensor                  // sealed = nobody can inherit from this
{
    private readonly ILogger<TemperatureSensor> _log;  // field; readonly = assign only in constructor
    public const double KelvinOffset = 273.15;          // compile-time constant

    public TemperatureSensor(ILogger<TemperatureSensor> log) => _log = log;   // constructor

    public string Name { get; init; } = "unnamed";      // auto-property; init = settable only at creation
    public double LastCelsius { get; private set; }     // public read, private write

    public double ToKelvin(double c) => c + KelvinOffset;   // expression-bodied method
}

// C# 12 "primary constructor": the parameters are in scope for the whole class
public sealed class FanMonitor(ILogger<FanMonitor> log, IStateService state)
{
    public void Report(int rpm) => log.LogInformation("Fan at {Rpm} rpm", rpm);
}
```

**Properties are methods in disguise.** `Name { get; init; }` compiles to a hidden field plus `get_Name()` and `set_Name()` methods. That's why frameworks (serializers, EF Core, PowerShell) work with properties rather than fields.

### 6.3 Nullable reference types

With `<Nullable>enable</Nullable>`:

```csharp
string  name = "fan";     // promise: never null
string? note = null;      // may be null. The compiler warns if you dereference it without checking.

if (note is not null) Console.WriteLine(note.Length);   // OK: flow analysis knows it's safe
Console.WriteLine(note!.Length);                        // "!" = "trust me". Silences the warning. Avoid.
```

These are **compile-time warnings only**. There's no runtime check. They're the closest thing C# has to a static-analysis tool telling you "this pointer might be NULL."

### 6.4 Generics

```csharp
List<double> readings = [];                      // C# 12 collection expression
Dictionary<Guid, StateDefinition> byId = new();

public interface IRepository<T> where T : class  // constraint: T must be a reference type
{
    T? Find(Guid id);
}
```

Unlike C macros or `void*`, .NET generics are **real at run time** (they're "reified"). `List<int>` stores raw `int`s with no boxing, and reflection can see `T`. Unlike Java, type information isn't erased.

### 6.5 Delegates, lambdas, and closures (the path to your callback)

```csharp
Func<ushort, double>  toVolts = raw => raw * 0.00125;    // takes ushort, returns double
Action<string>        log     = msg => Console.WriteLine(msg);
Predicate<double>     tooHot  = c => c > 85.0;

double scale = 0.00125;
Func<ushort, double> toVolts2 = raw => raw * scale;      // CAPTURES `scale` → a closure
```

The C mental model: a delegate is a **pair (function pointer, target object)**. A closure is the compiler generating a hidden class that holds the captured variables, with the lambda as a method on it. That's the `void* user_data` pattern from C callback APIs, built into the language.

**Events** are delegates with a restricted surface: outsiders can only `+=` (subscribe) and `-=` (unsubscribe), and only the owner can raise them.

```csharp
public event EventHandler<RawFrame>? FrameReceived;
FrameReceived?.Invoke(this, frame);     // raise (the ?. skips it if nobody subscribed)
```

### 6.6 Collections, LINQ, and deferred execution

```csharp
var hot = readings
    .Where(r => r.Celsius > 70)       // nothing runs yet
    .OrderByDescending(r => r.At)     // nothing runs yet
    .Take(10);                        // nothing runs yet

foreach (var r in hot) { ... }        // NOW it runs, when enumerated
var list = hot.ToList();              // runs AGAIN, a second time!
```

- `IEnumerable<T>` is a **lazy sequence**: a recipe, not a result. Each enumeration re-runs the recipe. Call `.ToList()` or `.ToArray()` once when you need a snapshot.
- `IQueryable<T>` (EF Core, §12) looks identical but builds an **expression tree** that gets translated to **SQL**. `Where` on an `IQueryable` runs in the database. On an `IEnumerable` it runs in memory. That's a major performance distinction.
- Common collections: `T[]` (fixed), `List<T>` (growable array), `Dictionary<K,V>` (hash map), `HashSet<T>`, `Queue<T>`, `ConcurrentDictionary<K,V>` (thread-safe).

### 6.7 `IDisposable` and `using`: deterministic cleanup

```csharp
using var file = File.OpenRead("/dev/i2c-1");   // Dispose() runs automatically at end of scope
// ...
// file.Dispose() is called here, even if an exception is thrown
```

This is C's `goto cleanup;` pattern (or C++ RAII), enforced by the compiler. **Rule:** if a type implements `IDisposable` and *you* created it, *you* dispose it. (When DI creates it, the container disposes it. See §9.) `IAsyncDisposable` + `await using` is the async version.

### 6.8 Pattern matching and switch expressions

A clean fit for dispatching on a preamble byte:

```csharp
using System.Buffers.Binary;

public enum TelemetryKind : byte { BusVoltage = 0x01, Current = 0x02, Temperature = 0x03, FanRpm = 0x04 }

public readonly record struct RawFrame(TelemetryKind Kind, ushort Raw);

public static class FrameParser
{
    // [preamble][data hi][data lo]  — 3 bytes, big-endian payload
    public static bool TryParse(ReadOnlySpan<byte> frame, out RawFrame result)
    {
        result = default;
        if (frame.Length != 3) return false;

        var kind = (TelemetryKind)frame[0];
        if (!Enum.IsDefined(kind)) return false;

        ushort raw = BinaryPrimitives.ReadUInt16BigEndian(frame[1..]);
        result = new RawFrame(kind, raw);
        return true;
    }

    public static string Describe(RawFrame f) => f.Kind switch
    {
        TelemetryKind.BusVoltage  => $"bus voltage raw=0x{f.Raw:X4}",
        TelemetryKind.Current     => $"current raw=0x{f.Raw:X4} (signed {unchecked((short)f.Raw)})",
        TelemetryKind.Temperature => $"temperature raw=0x{f.Raw:X4}",
        TelemetryKind.FanRpm      => $"fan raw={f.Raw}",
        _                         => "unknown",
    };
}
```

Notice:

- `ReadOnlySpan<byte>` is a safe, bounds-checked "pointer + length" view over memory, with no copy. `frame[1..]` is a slice. This is the .NET answer to `uint8_t* buf, size_t len`.
- `BinaryPrimitives` does explicit-endian reads, so you never hand-roll `(hi << 8) | lo` again (though it's the same thing).
- `unchecked((short)raw)` reinterprets 16 bits as **two's complement signed**. That's the whole signed/unsigned question from your calculator in one cast. (`unchecked` guarantees no overflow exception, even if a project turns on overflow checking.)

### 6.9 Attributes: how your code talks to frameworks

`[Cmdlet(...)]`, `[Parameter]`, `[DllImport(...)]`, `[StructLayout(...)]`, `[Fact]`, `[HttpGet]`, `[Required]`. Every one of these is **metadata attached to your code** that a *framework* reads (at run time via reflection, or at compile time via a source generator) to decide how to call you.

This is inversion of control again (§8): you don't call PowerShell's parameter binder. You *annotate* your class, and the binder reads the annotations. Once you see attributes as "notes left for the framework," a lot of "magic" code becomes readable.

### 6.10 Exceptions

- `try` / `catch (SpecificException ex) when (condition)` / `finally`.
- Throwing is expensive (it captures a stack trace). **Don't use exceptions for expected control flow.** That's why the BCL has the `TryParse(out ...)` pattern, as in §6.8.
- Catch only what you can handle. A top-level catch belongs at a boundary (a worker loop, a request handler) where you log and decide.
- Rethrow with `throw;`, not `throw ex;` (the latter resets the stack trace).

---
## 7. Part V — Abstraction: interfaces, and how to read a codebase top-down

Tag: 🟢 **OWN IT**. This is the Part written most directly for you. It turns your hard-won insight ("the interface is the API") into a repeatable procedure.

### 7.1 What an interface is *for*

An interface is a **promise with no implementation**:

```csharp
public interface ITelemetrySource
{
    /// Yields raw 3-byte frames as they arrive. Completes when cancelled.
    IAsyncEnumerable<RawFrame> ReadFramesAsync(CancellationToken ct);
}
```

Anyone who *uses* `ITelemetrySource` knows exactly three things: what to call, what comes back, and how to stop it. They don't know (and must not care) whether the frames come from:

- `I2cSlaveTelemetrySource`: the real thing, via P/Invoke into a native library, on a Pi
- `SimulatedTelemetrySource`: generates fake frames, for the emulator container or your laptop
- `ReplayTelemetrySource`: replays a recorded log file to reproduce a bug
- `FakeTelemetrySource`: returns three hard-coded frames, in a unit test

The interface is what makes **all four swappable with one line of DI registration** (§9). That's the payoff, and it's why enterprise code has an `IThing` for almost every `Thing`. It isn't ceremony. It's the seam that makes emulation, testing, and replacement possible.

> **Firmware twin:** a HAL. Your application code calls `hal_i2c_read()`. Which chip-specific driver sits behind it is decided at link time. An interface is a HAL decided at *run time*, by configuration.

### 7.2 Inheritance vs composition, and the polymorphism you already wrote

Your calculator work was polymorphism: *"based on a definition, instantiate a different calculator object."* Here's that pattern in its general form. It's called the **Strategy pattern**, and a **factory** picks the strategy:

```csharp
public interface IValueCalculator
{
    double Calculate(IReadOnlyList<double> inputs);
}

public sealed class UnsignedRawCalculator : IValueCalculator
{
    public double Calculate(IReadOnlyList<double> inputs) => (ushort)inputs[0];
}

public sealed class SignedRawCalculator : IValueCalculator
{
    public double Calculate(IReadOnlyList<double> inputs) => unchecked((short)(ushort)inputs[0]);
}

public sealed class LinearScaleCalculator(double scale, double offset) : IValueCalculator
{
    public double Calculate(IReadOnlyList<double> inputs) => inputs[0] * scale + offset;
}

public enum CalculationKind { UnsignedRaw, SignedRaw, LinearScale }

public static class CalculatorFactory
{
    public static IValueCalculator Create(CalculationKind kind, double scale = 1, double offset = 0) => kind switch
    {
        CalculationKind.UnsignedRaw => new UnsignedRawCalculator(),
        CalculationKind.SignedRaw   => new SignedRawCalculator(),
        CalculationKind.LinearScale => new LinearScaleCalculator(scale, offset),
        _ => throw new ArgumentOutOfRangeException(nameof(kind), kind, "No calculator for this kind"),
    };
}
```

The caller never writes `if (kind == ...)` again. It asks the factory for "the calculator for this definition" and calls `Calculate`. Adding a new kind means adding one class and one line.

**Inheritance** (`class Derived : Base`) says "is-a" and shares *implementation*. **Composition** (a class *holds* an `IValueCalculator`) says "has-a" and shares *behavior through contracts*. Modern .NET code strongly prefers composition + interfaces. Inheritance is still right for genuine families that share data, like "a derived state *is a* state with extra inputs," which is what you saw in your work.

### 7.3 SOLID in one table (the D matters most)

| Letter | Principle | One-line meaning | Where you've seen it |
|---|---|---|---|
| S | Single Responsibility | A class has one reason to change | Parser vs calculator vs store: separate classes |
| O | Open/Closed | Add behavior by adding code, not editing old code | New calculator = new class |
| L | Liskov Substitution | Any implementation can stand in for the interface without surprises | Simulated source behaves like the real one |
| I | Interface Segregation | Small, focused interfaces beat one giant one | `IStateReader` vs `IStateWriter` |
| D | **Dependency Inversion** | High-level code depends on **abstractions**; the concrete class is chosen from outside | Your worker asks for an `IStateService` in its constructor. It never `new`s one. |

### 7.4 The altitude ladder: answering at the level of the question

When someone asks "how does X work?", climb down one rung at a time, and **stop at the rung they asked about**:

| Rung | Question it answers | Example: "How is a sensor definition created?" |
|---|---|---|
| 1. Purpose | Why does this exist? | "Definitions describe each kind of telemetry so values can be stored and interpreted." |
| 2. Component | Who is responsible? | "The state service library owns definitions." |
| 3. **Contract** | What operation do I call? | "**Call `AddDefinitionAsync` on `IStateService` with a name and kind. It returns the new id.**" ← usually the right answer |
| 4. Flow | What happens across components? | "It validates, writes a row through the `DbContext`, logs, and returns." |
| 5. Implementation | How is the code written? | "It maps the DTO to an entity, calls `Add`, then `SaveChangesAsync`…" |
| 6. Runtime | What happens in memory? | "The entity is allocated in Gen 0; the change tracker holds a reference…" |

Six months ago you answered at rung 6. Senior engineers answer at rung 3 and *offer* rung 4. Practice this out loud: pick any class at work and give a rung-1, a rung-3, and a rung-4 answer about it.

### 7.5 The Interface-First Reading Protocol

Use this every time you have to work with an unfamiliar service. It has **stop conditions** built in.

```
 STEP 1  Find where it's REGISTERED (Program.cs / a ServiceCollectionExtensions file)
         → tells you: the interface, the implementation, and the LIFETIME.       [2 min]

 STEP 2  Read the INTERFACE only. Every method name, parameter, return type, XML doc.
         → write a Contract Card (below).                                        [5–10 min]

 STEP 3  Find 2–3 existing CALLERS (IDE: "Find All References" on the interface method).
         → see how the team actually uses it.                                    [5–10 min]

 STEP 4  Write your code against the interface. Build it. Test it.

 STEP 5  Open the IMPLEMENTATION only if:
           (a) behavior surprises you, or
           (b) the Contract Card has a blank you can't fill from docs or callers, or
           (c) you're changing the implementation itself.
         Then read only the ONE method involved. Don't follow every type it touches.

 STOP    If you're 3+ types deep in code you're not changing, climb back up.
         Write down the question you were trying to answer, and ask a teammate.
```

### 7.6 The Contract Card

This is how you use something you don't fully understand *safely*. You don't need its internals. You need these six answers:

| Field | Question |
|---|---|
| **Inputs** | What do I pass? Which values are valid? |
| **Outputs** | What do I get back? Can it be null or empty? |
| **Failures** | What exceptions or error results can happen, and which should I handle? |
| **Side effects** | Does it write to a DB, send a network call, log, or change shared state? |
| **Lifetime & threading** | Singleton or scoped? Thread-safe? Must I dispose it? |
| **Cost** | Is it cheap (in-memory) or expensive (network/disk)? Should I call it in a loop? |

Worked example for something marked ❌ in your persona, a gRPC audit-log client:

| Field | Answer |
|---|---|
| Inputs | An `AuditEvent` message (generated class from a `.proto`), plus an optional deadline and cancellation token |
| Outputs | An acknowledgement message (or nothing, if the RPC returns `Empty`) |
| Failures | `RpcException` with a `StatusCode` (e.g. `Unavailable` if the audit service is down, `DeadlineExceeded`) |
| Side effects | A network call to another process on the same box; the event gets persisted there |
| Lifetime & threading | The generated client is thread-safe and cheap; the underlying channel should be long-lived (register via `AddGrpcClient`) |
| Cost | A local network round trip. Fine per event, but not in a tight inner loop. |

With that card, you can write correct code that calls the audit log **today**, and learn HTTP/2 framing next month.

---

## 8. Part VI — The Generic Host and inversion of control

Tag: 🟢 **OWN IT**. This is the "recursion leap of faith" moment from your persona, made explicit.

### 8.1 Library vs framework

```
   LIBRARY  (you are in charge)                 FRAMEWORK  (it is in charge)
   ─────────────────────────────                ─────────────────────────────
   your main()                                  framework's main loop
      │                                              │
      ├──► call library.Parse()                      ├──► calls YOUR ExecuteAsync()
      ├──► call library.Save()                       ├──► calls YOUR controller action
      └──► exit                                      ├──► calls YOUR ProcessRecord()
                                                     └──► calls YOUR Dispose()
```

**"Don't call us, we'll call you."** (the Hollywood Principle). In a framework, your job is to **register** things and **implement contracts**. The framework decides *when* your code runs.

Firmware already taught you this. You just didn't have the name for it. An **interrupt service routine** is the Hollywood Principle: you write `void TIM2_IRQHandler(void)`, place it in the vector table (registration), and the *hardware* calls it. You never call it yourself. A `BackgroundService` is conceptually an ISR the host "vectors" to at startup.

### 8.2 Who calls this? A lookup table for confusing code

| Your code | Who calls it | When |
|---|---|---|
| Top-level statements in `Program.cs` | The runtime (entry point) | Process start |
| A constructor of a registered service | The **DI container** | The first time something needs it (or per scope, or per request) |
| `BackgroundService.ExecuteAsync` | The **Host** | During host startup |
| `IHostedService.StopAsync` | The **Host** | On SIGTERM / Ctrl+C / `StopApplication()` |
| A minimal-API lambda / controller action | ASP.NET Core **routing middleware** | When a matching HTTP request arrives |
| A gRPC service method | ASP.NET Core + **gRPC framework** | When a matching RPC arrives |
| `Cmdlet.ProcessRecord` | The **PowerShell engine** | Once per pipeline input object |
| A `[Fact]` method | The **xUnit** runner | During `dotnet test` |
| A native callback you registered | The **native library** (through the interop layer) | When the native event fires |
| `Dispose()` | The DI container / `using` | At end of scope / app shutdown |

When you look at a method and think "nothing calls this," check this table.

### 8.3 `Program.cs`, line by line

This is the `dotnet new worker` template, annotated:

```csharp
// ① Create a BUILDER. Nothing is running yet. This is the "configuration phase."
//    It pre-loads defaults: appsettings.json, appsettings.{Environment}.json,
//    environment variables, command-line args, console logging, and the DI container.
var builder = Host.CreateApplicationBuilder(args);

// ② REGISTER things with the Staffing Agency. Still nothing is running.
builder.Services.AddHostedService<Worker>();           // "the host must start Worker"
builder.Services.AddSingleton<IClock, SystemClock>();  // "when someone asks for IClock, give SystemClock"

// ③ BUILD: freezes the registrations and creates the IServiceProvider.
//    After this line you can't register more services.
var host = builder.Build();

// ④ RUN: starts every hosted service, then BLOCKS until shutdown is requested,
//    then stops everything gracefully. This line is where your program "lives."
host.Run();
```

Every .NET app model has this same three-phase shape: **configure → build → run**. ASP.NET Core's `WebApplication.CreateBuilder(args)` → `builder.Build()` → `app.Run()` is the same Conductor with a Doorman attached.

### 8.4 What `host.Run()` actually does

```
 host.Run()
   │
   ├─ START
   │   ├─ for each IHostedService, IN REGISTRATION ORDER:
   │   │     await service.StartAsync(ct)
   │   │       (for a BackgroundService, StartAsync kicks off ExecuteAsync and returns)
   │   └─ fire IHostApplicationLifetime.ApplicationStarted
   │
   ├─ WAIT  … the app does its work (your workers loop, Kestrel serves requests) …
   │         until one of: SIGTERM (systemd stop / docker stop), SIGINT (Ctrl+C),
   │         or code calls IHostApplicationLifetime.StopApplication()
   │
   ├─ STOP
   │   ├─ fire ApplicationStopping
   │   ├─ for each IHostedService, IN REVERSE ORDER:
   │   │     await service.StopAsync(ct)
   │   │       (for a BackgroundService: cancels stoppingToken, waits for ExecuteAsync)
   │   │     … all within HostOptions.ShutdownTimeout (default 30 seconds)
   │   └─ fire ApplicationStopped
   │
   └─ DISPOSE the service provider → every IDisposable singleton gets Dispose() called
```

### 8.5 Writing a correct `BackgroundService`

```csharp
public sealed class IngestionWorker(
    ITelemetrySource source,
    ITelemetryStore store,
    ILogger<IngestionWorker> log) : BackgroundService
{
    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        log.LogInformation("Ingestion starting");

        try
        {
            await foreach (var frame in source.ReadFramesAsync(stoppingToken))
            {
                try
                {
                    await store.AppendAsync(frame, stoppingToken);
                }
                catch (Exception ex) when (ex is not OperationCanceledException)
                {
                    // One bad frame must NOT kill the whole service (see §8.6)
                    log.LogError(ex, "Failed to store frame {Kind}", frame.Kind);
                }
            }
        }
        catch (OperationCanceledException) when (stoppingToken.IsCancellationRequested)
        {
            // Normal shutdown path. Not an error.
        }

        log.LogInformation("Ingestion stopped");
    }
}
```

And the timer-driven shape (like a worker that periodically recalculates derived values):

```csharp
public sealed class RecalculationWorker(IRecalculator recalculator, ILogger<RecalculationWorker> log)
    : BackgroundService
{
    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        using var timer = new PeriodicTimer(TimeSpan.FromSeconds(1));
        while (await timer.WaitForNextTickAsync(stoppingToken))   // throws OperationCanceledException on shutdown;
                                                                  // the host treats that as a normal stop
        {
            try   { await recalculator.RecalculateAllAsync(stoppingToken); }
            catch (Exception ex) when (ex is not OperationCanceledException)
            {     log.LogError(ex, "Recalculation pass failed"); }
        }
    }
}
```

`PeriodicTimer` doesn't drift or overlap. If a pass takes longer than the period, the next tick simply waits.

### 8.6 Three `BackgroundService` facts people learn the hard way

1. **An unhandled exception in `ExecuteAsync` stops the entire host** (since .NET 6; the default `BackgroundServiceExceptionBehavior` is `StopHost`). On an appliance, that means the ingestion crash takes down *everything* in that process. Hence the per-iteration `try/catch` above.
2. **The `stoppingToken` is your "go home" signal.** Pass it to every async call so shutdown is prompt. If you ignore it, the host waits until `ShutdownTimeout` (30 s by default) and then abandons your work.
3. **Startup blocking changed in .NET 10.** Before .NET 10, everything in `ExecuteAsync` *before the first `await`* ran synchronously inside host startup, so a slow synchronous setup blocked every other service from starting. In .NET 10 the whole `ExecuteAsync` runs as a background task. If you work on an older codebase (.NET 8/9), still put an `await` early, or do heavy setup in `StartAsync` deliberately.

### 8.7 The host and systemd

On Linux under systemd:

- `systemctl stop myapp` sends **SIGTERM**. The host translates that into the graceful STOP sequence in §8.4. This is why graceful shutdown "just works" if your workers honor the token.
- The package `Microsoft.Extensions.Hosting.Systemd` (`builder.Services.AddSystemd()`) adds two things: it tells systemd "I'm ready" at the right moment (for `Type=notify` units), and it formats console logs so **journald** understands severity levels.

```ini
# /etc/systemd/system/sensor-worker.service
[Unit]
Description=Sensor ingestion worker
After=network.target

[Service]
Type=notify
WorkingDirectory=/opt/sensor/worker
ExecStart=/usr/bin/dotnet /opt/sensor/worker/SensorStation.Worker.dll
Restart=on-failure
Environment=DOTNET_ENVIRONMENT=Production

[Install]
WantedBy=multi-user.target
```

One unit per entry-point assembly: that's exactly the "one systemd file per component" layout you saw in the emulator.

---
## 9. Part VII — Dependency injection, configuration, logging

Tag: 🟢 **OWN IT**. These three `Microsoft.Extensions.*` libraries are identical across workers, web apps, gRPC services, and tests. Learn them once, use them everywhere. This is one of those "core concepts" your persona says you're missing.

### 9.1 The Staffing Agency: registration vs resolution

Two phases, never mixed:

- **Registration** (before `Build()`): "When someone asks for `ITelemetryStore`, hire an `EfTelemetryStore`, and it lives for the whole app."
- **Resolution** (after `Build()`): the container sees `IngestionWorker` needs `(ITelemetrySource, ITelemetryStore, ILogger<IngestionWorker>)`, builds each of those (recursively building *their* dependencies), and calls the constructor.

```
 Host asks for: IngestionWorker
   └─ needs ITelemetrySource  → registered as I2cSlaveTelemetrySource (singleton)
   │     └─ needs IOptions<I2cOptions> → built from configuration
   │     └─ needs ILogger<I2cSlaveTelemetrySource> → logging provides it
   └─ needs ITelemetryStore   → registered as EfTelemetryStore
   │     └─ needs TelemetryDbContext → registered by AddDbContext (scoped!)  ⚠ see §9.3
   └─ needs ILogger<IngestionWorker>
```

**Nobody writes `new` for services.** Constructors just *declare* what they need. That's what "dependency injected" means, and it's why following `new` through the code led you nowhere: the wiring lives in `Program.cs` and registration extension methods, not in the classes.

### 9.2 Lifetimes

| Lifetime | One instance per… | Typical use | Disposed when |
|---|---|---|---|
| **Singleton** | …application | Stateless services, caches, clients, configuration, **hosted services** | App shutdown |
| **Scoped** | …scope (in ASP.NET Core: one HTTP request) | `DbContext`, unit-of-work objects, per-request state | Scope ends |
| **Transient** | …every time it's requested | Lightweight, stateless helpers | Scope ends (if disposable) |

### 9.3 The captive dependency bug (hits every worker that touches a database)

**Hosted services are singletons.** If a singleton's constructor takes a *scoped* service, that scoped instance is captured and lives forever. For EF Core's `DbContext`, which is **not thread-safe** and accumulates tracked entities, that's a slow-motion disaster.

In the Development environment, the host catches this at startup (`ValidateScopes` is on) with:

```
Cannot consume scoped service 'TelemetryDbContext' from singleton 'IngestionWorker'.
```

The fix: the singleton takes an `IServiceScopeFactory` and creates a **short scope per unit of work**:

```csharp
public sealed class IngestionWorker(
    ITelemetrySource source,
    IServiceScopeFactory scopes,
    ILogger<IngestionWorker> log) : BackgroundService
{
    protected override async Task ExecuteAsync(CancellationToken ct)
    {
        await foreach (var frame in source.ReadFramesAsync(ct))
        {
            await using var scope = scopes.CreateAsyncScope();              // new scope
            var store = scope.ServiceProvider.GetRequiredService<ITelemetryStore>();
            await store.AppendAsync(frame, ct);                             // fresh DbContext
        }                                                                   // scope disposed → DbContext disposed
    }
}
```

(In a high-rate pipeline you'd batch frames and use one scope per batch, not per frame. That's a design decision to make with your team.)

### 9.4 Registration patterns you'll read

```csharp
builder.Services.AddSingleton<ITelemetrySource, I2cSlaveTelemetrySource>();   // interface → class
builder.Services.AddScoped<ITelemetryStore, EfTelemetryStore>();
builder.Services.AddTransient<IValueCalculatorFactory, ValueCalculatorFactory>();

builder.Services.AddSingleton<ITelemetrySource>(sp =>                          // factory lambda
    sp.GetRequiredService<IHostEnvironment>().IsDevelopment()
        ? new SimulatedTelemetrySource()
        : ActivatorUtilities.CreateInstance<I2cSlaveTelemetrySource>(sp));

builder.Services.AddSingleton<IAlarmRule, OverTemperatureRule>();              // several implementations
builder.Services.AddSingleton<IAlarmRule, UnderVoltageRule>();                 //   → inject IEnumerable<IAlarmRule>

builder.Services.AddKeyedSingleton<ITelemetrySource, SimulatedTelemetrySource>("sim");  // keyed (.NET 8+)
// consumer: public Foo([FromKeyedServices("sim")] ITelemetrySource src)
```

**How shared libraries plug in:** by convention, each library exposes one extension method that registers everything it owns:

```csharp
namespace Microsoft.Extensions.DependencyInjection;   // conventional, so it shows up without a `using`

public static class StateServiceCollectionExtensions
{
    public static IServiceCollection AddStateService(this IServiceCollection services)
    {
        services.AddScoped<IStateService, StateService>();
        services.AddSingleton<IValueCalculatorFactory, ValueCalculatorFactory>();
        return services;
    }
}

// Program.cs of each executable that needs it:
builder.Services.AddStateService();
```

When you see `builder.Services.AddSomething()` in `Program.cs`, **that's a whole library plugging itself in.** Press F12 on it (go to definition) to see its registrations. That's Step 1 of the reading protocol.

The most common DI error, decoded:

```
Unable to resolve service for type 'ITelemetryStore' while attempting to activate 'IngestionWorker'.
```

= "Someone needs an `ITelemetryStore` and nobody registered one." Check the `Add…()` calls in *that executable's* `Program.cs`. Each process has its own container.

### 9.5 The Archivist: configuration

Every source becomes one flat key/value dictionary with `:`-separated keys. **Later sources override earlier ones:**

```
 1. appsettings.json                          (checked into git: defaults)
 2. appsettings.{Environment}.json            (Development / Staging / Production)
 3. User secrets                              (Development only; outside the repo)
 4. Environment variables                     (Sensors__PollIntervalMs=250   ← double underscore = ':')
 5. Command-line arguments                    (--Sensors:PollIntervalMs=250)
                                                                    ▲ highest priority
```

The environment name comes from `DOTNET_ENVIRONMENT` (or `ASPNETCORE_ENVIRONMENT` for web apps) and defaults to `Production`.

```json
{
  "Logging": { "LogLevel": { "Default": "Information", "Microsoft": "Warning" } },
  "Sensors": {
    "PollIntervalMs": 500,
    "I2cAddress": 34,
    "ShutdownThresholdVolts": 10.8
  }
}
```

### 9.6 The Options pattern: typed configuration

Don't sprinkle `config["Sensors:PollIntervalMs"]` strings around. Bind a section to a class once:

```csharp
using System.ComponentModel.DataAnnotations;

public sealed class SensorOptions
{
    public const string Section = "Sensors";

    [Range(10, 60_000)] public int    PollIntervalMs { get; init; } = 500;
    [Range(3, 119)]     public int    I2cAddress     { get; init; }
    [Range(0, 60)]      public double ShutdownThresholdVolts { get; init; }
}

// Program.cs  (ValidateDataAnnotations needs the Microsoft.Extensions.Options.DataAnnotations package)
builder.Services.AddOptions<SensorOptions>()
    .Bind(builder.Configuration.GetSection(SensorOptions.Section))
    .ValidateDataAnnotations()
    .ValidateOnStart();          // fail at startup, not at 3 a.m. when first used

// Consumer
public sealed class ThresholdRule(IOptions<SensorOptions> options)
{
    private readonly SensorOptions _o = options.Value;
}
```

| Interface | Reads config | Lifetime | Use when |
|---|---|---|---|
| `IOptions<T>` | Once | Singleton | Settings don't change while running (most cases) |
| `IOptionsSnapshot<T>` | Per scope | Scoped | Web apps that should see file changes per request |
| `IOptionsMonitor<T>` | Live, with change callbacks | Singleton | Long-running workers that should react to config edits |

### 9.7 The Scribe: structured logging

```csharp
log.LogInformation("Fan {FanId} at {Rpm} rpm", fanId, rpm);     // ✅ message TEMPLATE + properties
log.LogInformation($"Fan {fanId} at {rpm} rpm");                  // ❌ string interpolation
```

The first form keeps `FanId` and `Rpm` as **separate, queryable fields**, so a log backend can answer "show every event where Rpm < 1000." The second flattens everything into an opaque string, and it formats the string even when the level is disabled.

- **Category** = the `T` in `ILogger<T>`, usually the class name. Log levels are configured per category (`"Microsoft": "Warning"` silences framework chatter).
- **Levels:** `Trace < Debug < Information < Warning < Error < Critical`.
- **Providers** decide where logs go: console, systemd journal, files (via Serilog/NLog), OpenTelemetry. Your code only ever talks to `ILogger`. That's the interface principle again.
- ⚫ `[LoggerMessage]` source-generated logging: the high-performance form. Recognize it when you see it.

### 9.8 Secrets

Passwords, API keys, and VM credentials **never** go in `appsettings.json` in git. Common homes: user secrets (dev), environment variables, a secrets manager (Azure Key Vault), or an encrypted credential store on the device. The code should depend on an interface like `ICredentialProvider`, so where the secret lives is a deployment decision, not a code change. (That's also why a credential-store component tends to be its own library with its own interface.)

---
## 10. Part VIII — async/await: what a `Task` actually is

Tag: 🟢 **OWN IT** for the model and the rules. ⚫ for the thread-pool injection heuristics and `ValueTask` internals. (A deep dive already exists in `lectures/concurrency/001-async_actually.md`. This section is the .NET-specific map.)

### 10.1 The problem async solves

A thread that waits on I/O (a database round trip, an HTTP call, a socket read) does nothing but hold ~1 MB of stack and a kernel object. A web server with 1,000 concurrent requests would need 1,000 idle threads. Async lets a *handful* of threads serve thousands of in-flight operations, because **no thread is held while waiting**.

Firmware twin: **polling vs interrupts.** Blocking I/O is a busy-wait loop on a status register. Async I/O is "start the DMA transfer, return to the superloop, and handle the completion interrupt later."

### 10.2 A `Task` is a promise, not a thread

`Task<double>` means "a `double` will be available later (or an exception will)." It has a state (`Running`, `RanToCompletion`, `Faulted`, `Canceled`) and a list of continuations to run when it completes. **Most `Task`s have no thread at all while waiting.** Nothing is running. A network card will eventually raise an interrupt, the OS will signal the runtime, and the continuation will be queued to the thread pool.

### 10.3 What `await` compiles into

```csharp
public async Task<double> ReadAverageAsync(CancellationToken ct)
{
    var a = await _store.GetLatestAsync("bus_v", ct);   // (1)
    var b = await _store.GetLatestAsync("aux_v", ct);   // (2)
    return (a + b) / 2;
}
```

The compiler rewrites this method into a **state machine**, a struct with a `state` field and a `MoveNext()` method, roughly:

```
 MoveNext():
   switch (state)
     case 0: start GetLatestAsync(bus_v).
             If already complete → fall through. Else: state = 1, register MoveNext
             as the continuation, RETURN to the caller (the thread is free now).
     case 1: a = result; start GetLatestAsync(aux_v). If incomplete → state = 2, register, RETURN.
     case 2: b = result; complete the Task with (a+b)/2.
```

If you've seen **protothreads** or a hand-written state-machine driver in C (a `switch(state)` that resumes where it left off each time the superloop calls it), that's exactly this. `async` is the compiler writing the protothread for you.

### 10.4 CPU-bound vs I/O-bound

| Work | Right tool | Why |
|---|---|---|
| Waiting on disk, network, DB, timers | `await` the async API | No thread is used while waiting |
| Heavy computation (FFT over a buffer, parsing a huge file) | `await Task.Run(() => Compute())` | Moves CPU work to a pool thread so the caller isn't blocked |
| Tiny computation (the hex→double conversion) | Just call it synchronously | Async has overhead. Don't make pure math `async`. |

### 10.5 Cancellation is cooperative

A `CancellationToken` is a flag plus a callback list. Nothing is ever forcibly killed. Code **checks** the token (`ct.ThrowIfCancellationRequested()`) or **passes it along** to APIs that check it. This is why §8.6 insists you pass `stoppingToken` everywhere: it's the only way shutdown reaches your code.

### 10.6 The rules

1. **Async all the way.** If you call an async method, `await` it, and make your method async too.
2. **Never block on async code** with `.Result`, `.Wait()`, or `.GetAwaiter().GetResult()`. In modern hosts this causes **thread-pool starvation** under load. In UI apps and legacy ASP.NET it causes outright **deadlocks**.
3. **No `async void`**, except event handlers. Exceptions from `async void` can't be caught by the caller and crash the process.
4. **Pass `CancellationToken`** as the last parameter of every async method you write.
5. `ConfigureAwait(false)`: use it in general-purpose *library* code. It matters much less in ASP.NET Core and worker apps, which have no `SynchronizationContext`.
6. `IAsyncEnumerable<T>` + `await foreach` is how you model a **stream** of values arriving over time, like frames from a bus.

### 10.7 Crossing threads safely: `Channel<T>` (your ISR + ring buffer)

This is the most important async pattern for your kind of work. A native callback fires **on a thread the native library owns**, not on the thread pool, and it must return quickly. Doing database work inside it is like doing flash writes inside an ISR.

The .NET answer is exactly the firmware answer: **the ISR pushes into a ring buffer, and the main loop drains it.**

```csharp
using System.Threading.Channels;

public sealed class FrameQueue
{
    private readonly Channel<RawFrame> _channel = Channel.CreateBounded<RawFrame>(
        new BoundedChannelOptions(capacity: 1024)
        {
            FullMode     = BoundedChannelFullMode.DropOldest,  // under overload, keep the NEWEST telemetry
            SingleReader = true,
            SingleWriter = true,
        });

    // Called from the native callback thread: non-blocking, never awaits
    public bool TryEnqueue(RawFrame frame) => _channel.Writer.TryWrite(frame);

    // Called from the BackgroundService
    public IAsyncEnumerable<RawFrame> ReadAllAsync(CancellationToken ct) => _channel.Reader.ReadAllAsync(ct);
}
```

```
  native thread                          thread pool
  ─────────────                          ───────────
  I2C slave event                        IngestionWorker.ExecuteAsync
     │                                        │
     ▼                                        ▼
  OnSlaveEvent (callback) ── TryWrite ──► [ Channel<RawFrame> ] ── ReadAllAsync ──► parse → store
     returns immediately                   bounded, thread-safe          awaits without blocking
```

The other synchronization tools, for reference:

| Tool | Use for | Firmware twin |
|---|---|---|
| `lock (obj) { ... }` | Short critical sections on shared state (never `await` inside) | Disable interrupts around a shared variable |
| `SemaphoreSlim` + `WaitAsync` | Async-friendly mutual exclusion or limiting concurrency | Counting semaphore (RTOS) |
| `Interlocked.Increment` / `CompareExchange` | Single-variable atomic updates | `LDREX`/`STREX`, atomic intrinsics |
| `ConcurrentDictionary`, `ConcurrentQueue` | Thread-safe collections | Lock-free ring buffer |
| `volatile` | Rarely correct on its own. Prefer the above. | `volatile` on an ISR-shared flag |

---

## 11. Part IX — Native interop: reviewing your own P/Invoke work

Tag: 🔵 **CONTRACT**, bordering on 🟢 for you specifically. This is where your embedded background is a genuine *advantage*. Most .NET developers never cross this border. The examples use a made-up native library `libbus.so` so this public document doesn't mirror any real codebase. Map it onto the real library in your head.

### 11.1 The border and the Diplomat's duties

```
      MANAGED LAND (.NET)                      │            NATIVE LAND (C)
  GC-moved objects, type safety,               │   raw pointers, manual lifetimes,
  exceptions, UTF-16 strings                   │   return codes, char* strings
                                               │
  YourCode ──► [ P/Invoke stub ] ──────────────┼──────────► bus_xfer(bus_xfer_t*)
                  the Diplomat:                │
                  1. find & load libbus.so     │
                  2. find the symbol           │
                  3. convert/pin arguments     │
                  4. follow the calling conv.  │
                  5. switch GC mode            │
                  6. convert the return value  │
```

### 11.2 `DllImport` vs `LibraryImport`

```c
/* libbus.h (native side) */
int  bus_open(int address);
int  bus_close(void);
int  bus_xfer(bus_xfer_t *xfer);
```

```csharp
using System.Runtime.InteropServices;

internal static partial class BusNative
{
    private const string Lib = "bus";   // runtime probes libbus.so, bus.so, … on Linux

    // Modern (.NET 7+): source-generated at compile time. Requires `partial`
    // and <AllowUnsafeBlocks>true</AllowUnsafeBlocks>.
    [LibraryImport(Lib, EntryPoint = "bus_open")]
    internal static partial int Open(int address);

    [LibraryImport(Lib, EntryPoint = "bus_close")]
    internal static partial int Close();

    [LibraryImport(Lib, EntryPoint = "bus_xfer")]
    internal static partial int Xfer(ref BusXfer xfer);
}

internal static class BusNativeLegacy
{
    // Classic: the marshalling stub is generated at RUN time by the runtime.
    [DllImport("bus", EntryPoint = "bus_open")]
    internal static extern int Open(int address);
}
```

| | `DllImport` | `LibraryImport` |
|---|---|---|
| Stub generated | At run time, by the runtime | At compile time, by a Roslyn source generator. You can F12 into it and read it. |
| AOT/trimming friendly | Less so | Yes |
| Delegate parameters | Supported | **Not supported.** Use function pointers (§11.4 option B) or `Marshal.GetFunctionPointerForDelegate`. |
| When you'll see it | Everywhere in existing code | New code, and the BCL itself |

### 11.3 Mirroring a C struct

```c
typedef struct {
    uint32_t control;
    int      rxCnt;
    char     rxBuf[512];
    int      txCnt;
    char     txBuf[512];
} bus_xfer_t;
```

```csharp
[StructLayout(LayoutKind.Sequential)]      // fields in declaration order, C alignment rules
internal unsafe struct BusXfer
{
    public uint Control;
    public int  RxCount;
    public fixed byte RxBuf[512];          // inline fixed-size array (needs `unsafe`)
    public int  TxCount;
    public fixed byte TxBuf[512];
}
```

The type-mapping table you need in your head:

| C | C# | Trap |
|---|---|---|
| `int` / `int32_t` | `int` | — |
| `uint32_t` | `uint` | — |
| `uint8_t`, `char` (as bytes) | **`byte`** | C# `char` is **2 bytes** (UTF-16). Using `char` for a C byte buffer silently breaks the layout. |
| `int16_t` / `uint16_t` | `short` / `ushort` | — |
| `long` | `CLong` (or `nint` if the code only ever runs on 64-bit Linux) | 8 bytes on 64-bit Linux, **4 bytes on Windows**. C# `long` is always 8. |
| `size_t` | `nuint` | — |
| `void*`, any pointer | `nint`, `T*` (unsafe), or `ref T` | — |
| `bool` / `_Bool` | `[MarshalAs(UnmanagedType.U1)] bool`, or better, `byte` | .NET's default `bool` marshalling is a 4-byte Win32 `BOOL` |
| `char*` string | `string` + `StringMarshalling = StringMarshalling.Utf8` (`LibraryImport`) | Who frees the returned memory? |

**A cheap safety net:** write a unit test that asserts the managed size matches the C size (compile a tiny C program once to print `sizeof(bus_xfer_t)`):

```csharp
[Fact]
public void BusXfer_matches_native_size() =>
    Assert.Equal(1036, Marshal.SizeOf<BusXfer>());   // 4 + 4 + 512 + 4 + 512
```

A struct made only of blittable fields (primitive numbers, fixed buffers, other blittable structs) is **blittable**. Passing it by `ref` means the marshaller just **pins it and passes a pointer**, with zero copying. That's the fast path, and it's why these structs must be `struct`, not `class`.

### 11.4 Callbacks from native code: the part that bites

```c
typedef void (*bus_event_cb)(int event, uint32_t tick, void *user);
int bus_set_callback(bus_event_cb cb, void *user);
```

**Option A: a delegate (classic, `DllImport`).**

```csharp
[UnmanagedFunctionPointer(CallingConvention.Cdecl)]
internal delegate void BusEventCallback(int evt, uint tick, nint user);

internal static class BusCallbacksLegacy
{
    [DllImport("bus")]
    internal static extern int bus_set_callback(BusEventCallback cb, nint user);
}

public sealed class BusListener
{
    private readonly BusEventCallback _callback;   // ⚠ MUST be a field that lives as long as the registration

    public BusListener()
    {
        _callback = OnEvent;
        BusCallbacksLegacy.bus_set_callback(_callback, 0);
    }

    private void OnEvent(int evt, uint tick, nint user) { /* keep it tiny (§10.7) */ }
}
```

**The classic crash:** if you write `bus_set_callback(OnEvent, 0)` with no field, the runtime creates a temporary delegate and a native thunk pointing at it. Native code keeps the function pointer. The GC sees *no managed reference* to the delegate and collects it. Minutes or hours later, the next event jumps into freed memory, and **the process dies with no managed exception**. It "works on my machine" until a GC happens at the wrong time. `GC.KeepAlive(x)` does *not* fix this. It only keeps `x` alive until that line, not for the lifetime of the registration.

**Option B: `UnmanagedCallersOnly` + function pointer (modern, `LibraryImport`).**

```csharp
using System.Runtime.CompilerServices;
using System.Runtime.InteropServices;

internal static unsafe partial class BusCallbacks
{
    [LibraryImport("bus", EntryPoint = "bus_set_callback")]
    internal static partial int SetCallback(delegate* unmanaged[Cdecl]<int, uint, nint, void> cb, nint user);
}

public sealed unsafe class BusListener : IDisposable
{
    private readonly FrameQueue _queue;
    private GCHandle _self;                                    // lets the static callback find this instance

    public BusListener(FrameQueue queue)
    {
        _queue = queue;
        _self  = GCHandle.Alloc(this);                         // strong handle: keeps `this` alive until Free()
        BusCallbacks.SetCallback(&OnEvent, GCHandle.ToIntPtr(_self));
    }

    [UnmanagedCallersOnly(CallConvs = new[] { typeof(CallConvCdecl) })]
    private static void OnEvent(int evt, uint tick, nint user)
    {
        try
        {
            var self = (BusListener)GCHandle.FromIntPtr(user).Target!;
            // read the frame, then: self._queue.TryEnqueue(frame);
        }
        catch
        {
            // An exception escaping an UnmanagedCallersOnly method terminates the process.
            // Swallow it here and count/log it somewhere cheap.
        }
    }

    public void Dispose()
    {
        BusCallbacks.SetCallback(null, 0);                    // unregister FIRST
        if (_self.IsAllocated) _self.Free();                  // then release the handle
    }
}
```

Why option B is safer: a **static** method has a fixed native entry point, and there's no delegate for the GC to collect. The `GCHandle` passed through `void* user` is the standard way to get from "native gave me a context pointer" back to "my C# object." It's exactly the C `user_data` idiom.

### 11.5 ISR rules apply to native callbacks

| ISR rule you already know | .NET callback equivalent |
|---|---|
| Keep it short | Copy the bytes, `TryWrite` to a channel, return |
| No blocking calls | No `await`, no locks held for long, no DB/network |
| Don't allocate if you can avoid it | Avoid large allocations; reuse buffers |
| Shared data needs protection | Use `Channel<T>`/concurrent types, not bare fields |
| A fault in the ISR kills the system | An exception escaping the callback kills the process |

### 11.6 When the border fails

| Exception | Meaning | Usual cause |
|---|---|---|
| `DllNotFoundException` | Couldn't load the `.so` | Wrong name, not on the search path, wrong architecture (x64 `.so` on ARM), or a missing *dependency* of the `.so` |
| `EntryPointNotFoundException` | Loaded it, but the symbol isn't there | Typo, C++ name mangling (needs `extern "C"`), wrong version |
| `AccessViolationException` / segfault | Native code touched bad memory | Struct layout mismatch, collected delegate, buffer too small, use-after-free |
| Wrong values, no crash | Layout or type mismatch | `char` vs `byte`, `long` size, missing `Pack`, endianness |

Tools: `ldd libbus.so` (its dependencies), `nm -D libbus.so` (exported symbols), `LD_DEBUG=libs dotnet app.dll` (watch the loader search), and `NativeLibrary.SetDllImportResolver` (take control of how a library name maps to a path).

### 11.7 A checklist for re-reading your old interop code (at work)

- [ ] Does every mirrored struct use `byte` (not `char`) for C byte buffers?
- [ ] Is every callback delegate stored in a field whose lifetime ≥ the registration? (Or does it use `UnmanagedCallersOnly`?)
- [ ] Is the callback short, non-blocking, and exception-proof?
- [ ] Does the callback hand off work to another thread (queue/channel) instead of doing it inline?
- [ ] Is the native library initialized once and shut down on host stop (an `IHostedService.StopAsync` or `Dispose`)?
- [ ] Are native return codes checked and turned into meaningful exceptions or logs?
- [ ] Is there a unit test asserting struct sizes?
- [ ] Is the whole native surface hidden behind *one* interface (e.g. `ITelemetrySource`), so the rest of the app, the emulator, and tests never touch `unsafe` code?

---
## 12. Part X — Data: EF Core and the relational model

Tag: 🔵 **CONTRACT** for EF Core. 🟢 for the relational modeling ideas (you already reasoned through one correctly: definitions vs values).

### 12.1 The definition/value pattern, generalized

The data model you worked with, separating *what a thing is* from *the measurements of it*, is a classic and correct relational design. In generic form:

```
 SensorDefinitions                              Readings
 ┌──────────────┬─────────────────────┐         ┌──────────┬───────────────┬─────────────────────┬────────┐
 │ Id (PK, Guid)│ Name                │         │ Id (PK)  │ DefinitionId  │ Timestamp           │ Value  │
 ├──────────────┼─────────────────────┤  1   *  ├──────────┼───────────────┼─────────────────────┼────────┤
 │ 7c1e…        │ raw_bus_voltage     │◄────────│ 1        │ 7c1e… (FK)    │ 2026-09-25 08:00:00 │ 3120   │
 │ 91ab…        │ bus_voltage_volts   │         │ 2        │ 7c1e… (FK)    │ 2026-09-25 08:00:01 │ 3118   │
 │ 04dd…        │ needs_shutdown      │         │ 3        │ 91ab… (FK)    │ 2026-09-25 08:00:01 │ 12.02  │
 └──────────────┴─────────────────────┘         └──────────┴───────────────┴─────────────────────┴────────┘
      small, rarely changes                           grows forever  → needs an index and a retention policy
```

Design questions a senior engineer asks about this shape (good interview material):

- **"What's the most common query?"** Almost certainly *"latest value for definition X."* So there should be an index on `(DefinitionId, Timestamp DESC)`. Without it, that query scans a table that grows every second.
- **"What stops the table from filling the disk?"** A retention/downsampling job. On an appliance with an SD card, this is a real failure mode.
- **"Where do derived definitions keep their inputs?"** In a many-to-many link table (`DefinitionInputs(DerivedId, InputId)`). That's a graph stored in rows, and it must not contain cycles.

### 12.2 EF Core: the Bookkeeper

EF Core is an **ORM** (object-relational mapper): you work with C# objects, and it writes the SQL.

```csharp
public class SensorDefinition
{
    public Guid   Id   { get; set; }
    public required string Name { get; set; }
    public List<Reading> Readings { get; set; } = [];      // navigation property (1 → many)
}

public class DerivedDefinition : SensorDefinition          // inheritance → one table + a "Discriminator" column (TPH)
{
    public List<SensorDefinition> Inputs { get; set; } = [];
    public CalculationKind Calculation { get; set; }
}

public class Reading
{
    public long     Id           { get; set; }
    public Guid     DefinitionId { get; set; }             // foreign key
    public DateTime Timestamp    { get; set; }
    public double   Value        { get; set; }
}

public class TelemetryDbContext(DbContextOptions<TelemetryDbContext> options) : DbContext(options)
{
    public DbSet<SensorDefinition> Definitions => Set<SensorDefinition>();
    public DbSet<Reading>          Readings    => Set<Reading>();

    protected override void OnModelCreating(ModelBuilder b)
    {
        b.Entity<Reading>().HasIndex(r => new { r.DefinitionId, r.Timestamp });
        b.Entity<DerivedDefinition>().HasMany(d => d.Inputs).WithMany();   // link table
    }
}

// Program.cs: registered as SCOPED
builder.Services.AddDbContext<TelemetryDbContext>(o => o.UseSqlite("Data Source=telemetry.db"));
```

A query, and (roughly) the SQL that actually runs:

```csharp
double? latest = await db.Readings
    .Where(r => r.DefinitionId == id)
    .OrderByDescending(r => r.Timestamp)
    .Select(r => (double?)r.Value)
    .FirstOrDefaultAsync(ct);
```

```sql
SELECT r.Value FROM Readings AS r
WHERE r.DefinitionId = @id
ORDER BY r.Timestamp DESC
LIMIT 1
```

Because `db.Readings` is an `IQueryable`, the whole LINQ chain becomes **one SQL statement** (§6.6).

### 12.3 The Contract Card for `DbContext`

| Field | Answer |
|---|---|
| Inputs | LINQ queries; entity objects to `Add`/`Remove`/modify |
| Outputs | Entities (tracked by default) or projections |
| Failures | `DbUpdateException` (constraint violations), `DbUpdateConcurrencyException`, provider exceptions |
| Side effects | **Nothing is written until `SaveChanges(Async)`**. It then writes every tracked change in one transaction. |
| Lifetime & threading | **Scoped, short-lived, NOT thread-safe.** One per request / unit of work. In workers, use a scope (§9.3) or `IDbContextFactory<T>`. |
| Cost | Every query is a round trip. Watch for **N+1** (a query inside a loop); use `.Include()` or a projection. Use `.AsNoTracking()` for read-only queries. |

**Migrations** are version-controlled schema changes, generated from your model:

```
dotnet ef migrations add AddReadingIndex     # generates C# describing the schema change
dotnet ef database update                     # applies pending migrations to the DB
```

⚫ **BLACK BOX for now:** the change-tracker internals, compiled queries, raw SQL / Dapper (a thinner, faster alternative), concurrency tokens.

---

## 13. Part XI — Talking to others: ASP.NET Core, JSON, gRPC

Tag: 🔵 **CONTRACT** for all three. The deep versions are later lectures. (Your `lectures/yarp/` folder already covers HTTP and Kestrel at depth; this section places them on the .NET map.)

### 13.1 ASP.NET Core: the Doorman and the Assembly Line

```
 TCP connection
     │
     ▼
 KESTREL (Doorman): parses HTTP/1.1, HTTP/2, HTTP/3 into an HttpContext
     │
     ▼
 MIDDLEWARE PIPELINE (Assembly Line). ORDER MATTERS; each station can act, pass on, or short-circuit
   ├─ exception handler
   ├─ HTTPS redirection
   ├─ static files        (serves /wwwroot/*.css, *.js directly; may short-circuit)
   ├─ routing             (decides WHICH endpoint matches)
   ├─ authentication      (who are you?)
   ├─ authorization       (are you allowed?)
   └─ ENDPOINT            (your code: minimal API lambda / controller action / Razor page / gRPC method)
     │
     ▼
 response flows back UP through the same stations in reverse
```

A read-only dashboard API, in full:

```csharp
var builder = WebApplication.CreateBuilder(args);          // same Conductor, plus the Doorman
builder.Services.AddDbContext<TelemetryDbContext>(o => o.UseSqlite("Data Source=telemetry.db"));

var app = builder.Build();

app.UseStaticFiles();                                      // middleware

app.MapGet("/api/readings/latest", async (TelemetryDbContext db, CancellationToken ct) =>
{
    var latest = await db.Definitions
        .Select(d => new
        {
            d.Name,
            Value = d.Readings.OrderByDescending(r => r.Timestamp).Select(r => (double?)r.Value).FirstOrDefault(),
        })
        .ToListAsync(ct);
    return Results.Ok(latest);                             // serialized to JSON automatically
});

app.Run();                                                 // listens on the configured URLs
```

Notice: the lambda's **parameters are injected**. `TelemetryDbContext` comes from DI (scoped per request, which is exactly right), and `CancellationToken` fires if the browser disconnects. Same Staffing Agency, same rules.

Binding to a static IP on a device: set `"Urls": "http://0.0.0.0:8080"` in config (or `ASPNETCORE_URLS`, or Kestrel endpoint config). `0.0.0.0` means "every network interface," including the Ethernet port.

| UI technology | What it is | Status for you |
|---|---|---|
| Minimal APIs | Lambdas mapped to routes | 🔵 |
| Controllers (MVC) | Classes with `[HttpGet]` action methods | 🔵. The same pipeline with more structure. |
| Razor Pages / MVC Views | Server-rendered HTML | ⚫ |
| Blazor | C# components for interactive UI (server or WebAssembly) | ⚫ |

### 13.2 JSON and System.Text.Json

The full JSON model (it really is this small): **object** `{ "k": v }`, **array** `[ v, v ]`, **string**, **number**, `true`/`false`, `null`. That's it. Everything else is convention.

```csharp
using System.Text.Json;

var json = JsonSerializer.Serialize(new { Name = "fan1", Rpm = 2400 });
// {"Name":"fan1","Rpm":2400}          ← plain JsonSerializer keeps C# names

var opts = new JsonSerializerOptions(JsonSerializerDefaults.Web);
var web  = JsonSerializer.Serialize(new { Name = "fan1", Rpm = 2400 }, opts);
// {"name":"fan1","rpm":2400}          ← "Web" defaults: camelCase + case-insensitive reading (what ASP.NET Core uses)

var back = JsonSerializer.Deserialize<ReadingDto>(web, opts);
```

Traps: property-name casing differs between contexts (above); deserialization needs a settable/init property or a matching constructor; `[JsonPropertyName("rx_count")]` for snake_case wire formats. ⚫ Source-generated serialization (`JsonSerializerContext`) for AOT and speed.

### 13.3 gRPC: the Courier (closing a ❌ from your persona)

gRPC = **a contract file (`.proto`) + generated code on both sides + HTTP/2 transport + Protocol Buffers binary encoding.**

```proto
// audit.proto  (shared by client and server)
syntax = "proto3";
option csharp_namespace = "SensorStation.Audit";

service AuditLog {
  rpc Record (AuditEvent) returns (RecordReply);
}

message AuditEvent {
  string actor    = 1;     // field NUMBERS (not names) go on the wire, so never reuse or renumber them
  string action   = 2;
  int64  unix_ms  = 3;
}

message RecordReply { bool accepted = 1; }
```

```xml
<!-- server .csproj -->
<ItemGroup>
  <Protobuf Include="Protos\audit.proto" GrpcServices="Server" />   <!-- Grpc.Tools generates C# at build time -->
</ItemGroup>
```

```csharp
// Server (an ASP.NET Core app)
public sealed class AuditLogService(ILogger<AuditLogService> log) : AuditLog.AuditLogBase
{
    public override Task<RecordReply> Record(AuditEvent e, ServerCallContext ctx)
    {
        log.LogInformation("{Actor} did {Action}", e.Actor, e.Action);
        return Task.FromResult(new RecordReply { Accepted = true });
    }
}
// Program.cs:  builder.Services.AddGrpc();   app.MapGrpcService<AuditLogService>();

// Client (any other process), with the Grpc.Net.ClientFactory package:
builder.Services.AddGrpcClient<AuditLog.AuditLogClient>(o => o.Address = new Uri("http://localhost:5100"));
// then inject AuditLog.AuditLogClient and call:
await client.RecordAsync(new AuditEvent { Actor = "admin", Action = "add-host" }, cancellationToken: ct);
```

> **Gotcha:** gRPC needs HTTP/2. Over plain `http://` (no TLS), HTTP/2 can't be negotiated, so the server's Kestrel endpoint must be configured for `Http2` explicitly (e.g. `"Kestrel": { "EndpointDefaults": { "Protocols": "Http2" } }`). "It works over https but not http" is almost always this.

The key idea: **the `.proto` file is the interface (§7), across a process boundary.** Both sides compile it into C#, so a mismatch shows up as a compile error, not a runtime surprise.

| | REST + JSON | gRPC + Protobuf |
|---|---|---|
| Contract | Optional (OpenAPI) | **Required** (`.proto`) |
| Payload | Text, self-describing, human-readable | Binary, compact, needs the schema |
| Transport | HTTP/1.1 or 2 | HTTP/2 |
| Streaming | Awkward | First-class (server, client, bidirectional) |
| Browser-friendly | Yes | Not directly |
| Typical use | Public APIs, browser clients | Service-to-service inside a system |

The firmware twin of this whole idea is **your own 3-byte I2C frame format.** A preamble tells the receiver what the payload means, and both sides must agree on it. A `.proto` is the industrial-strength version: field numbers instead of a preamble byte, generated parsers instead of a hand-written `switch`.

### 13.4 Calling HTTP APIs: `IHttpClientFactory`

Don't `new HttpClient()` per call. It can exhaust sockets and ignores DNS changes. Register a typed client: `builder.Services.AddHttpClient<IWeatherApi, WeatherApi>(c => c.BaseAddress = new("https://…"));` and inject it.

---

## 14. Part XII — PowerShell is .NET: what your cmdlets really are

Tag: 🔵 **CONTRACT**. This connects something you *built* to the rest of the map.

### 14.1 The reveal

PowerShell 7 (`pwsh`) is **a .NET application**. The PowerShell engine is the framework; your cmdlet is a class it calls (§8.2). So:

- A **binary module** = a .NET class library (`.dll`).
- A **cmdlet** = a class deriving from `PSCmdlet` (or `Cmdlet`), annotated with attributes (§6.9).
- `Import-Module /path/Module.dll` = "load this assembly into the PowerShell process and register every cmdlet class in it." (The command is `Import-Module`, not `Import-Command`. Worth getting right in an interview.)
- The PowerShell **pipeline passes .NET objects, not text.** `Get-Thing | Where-Object Value -gt 10` filters real objects by a real property. That's the big difference from bash.

### 14.2 Anatomy of a cmdlet

```csharp
using System.Management.Automation;      // from the PowerShellStandard.Library or Microsoft.PowerShell.SDK package

[Cmdlet(VerbsCommon.Get, "SensorReading")]          // → the command name is Get-SensorReading
[OutputType(typeof(ReadingDto))]
public sealed class GetSensorReadingCommand : PSCmdlet
{
    [Parameter(Mandatory = true, Position = 0, ValueFromPipelineByPropertyName = true)]
    public string Name { get; set; } = "";           // -Name fan1   (or bound from piped objects' Name property)

    [Parameter]
    [ValidateRange(1, 1000)]
    public int Last { get; set; } = 1;               // -Last 20

    private IReadingQuery _query = null!;

    protected override void BeginProcessing()        // once, before any pipeline input
        => _query = ModuleServices.Get<IReadingQuery>();

    protected override void ProcessRecord()          // once PER pipeline input object
    {
        foreach (var r in _query.GetLatest(Name, Last))
            WriteObject(r);                          // emit an OBJECT into the pipeline
    }

    protected override void EndProcessing() { }      // once, at the end
}
```

The verb comes from an approved list (`Get`, `Set`, `Add`, `Remove`, `New`, `Invoke`…). `Get-Verb` shows them all. That's why cmdlets are named `Add-Something`, never `Create-Something`.

### 14.3 Where do a cmdlet's services come from?

There's **no Generic Host inside PowerShell**, so no DI container is handed to you. Teams usually pick one of these:

1. **The module builds its own small container** when it's imported. PowerShell calls `IModuleAssemblyInitializer.OnImport()` when the module loads, so you can create a `ServiceCollection`, register the shared libraries (the same `AddStateService()`-style extension methods from §9.4), and keep the provider in a static `ModuleServices` holder, as above.
2. **The cmdlet is a thin client** that calls the running service over an API (HTTP/gRPC), and the service does the work.
3. **The cmdlet constructs what it needs directly** (fine for tiny modules, hard to test).

Knowing which one your team chose is a rung-3 question (§7.4). Ask it.

### 14.4 Two real traps

- **Runtime compatibility:** the module's `.dll` runs inside *PowerShell's* .NET runtime. A module compiled for `net10.0` won't load into a `pwsh` running on an older .NET. Check `$PSVersionTable` and match the target framework.
- **Dependency conflicts:** if your module needs version X of a package and PowerShell already loaded version Y, loading can fail. ⚫ The advanced fix (`AssemblyLoadContext` isolation) is a later topic. Just recognize the symptom: "Could not load file or assembly … version …".

---
## 15. Part XIII — Testing

Tag: 🟢 **OWN IT** for unit tests and why interfaces enable them. 🔵 for integration-test tooling.

### 15.1 A unit test is just a method the Inspector calls

```csharp
using Xunit;

public class SignedRawCalculatorTests
{
    [Theory]
    [InlineData(0x0000,      0.0)]
    [InlineData(0x7FFF,  32767.0)]      // largest positive
    [InlineData(0x8000, -32768.0)]      // sign bit only → most negative
    [InlineData(0xFFFF,     -1.0)]      // all ones → -1 in two's complement
    public void Interprets_raw_as_twos_complement(int raw, double expected)
    {
        // Arrange
        var calc = new SignedRawCalculator();

        // Act
        var actual = calc.Calculate([raw]);

        // Assert
        Assert.Equal(expected, actual);
    }
}
```

- `[Fact]` = one test. `[Theory]` + `[InlineData]` = the same test over many inputs. Perfect for boundary values like these.
- **Arrange / Act / Assert** is the universal shape.
- Run with `dotnet test`. xUnit is the most common framework in modern .NET (v3 is current). MSTest and NUnit are the other two, and all three look alike.
- A good test name reads like a spec sentence. When it fails, the name tells you what broke.

### 15.2 Why DI and interfaces make testing possible

To test `IngestionWorker`'s logic without an I2C bus, a Pi, or a database, you hand it **fakes** through the same constructor DI would use:

```csharp
public sealed class FakeTelemetrySource(params RawFrame[] frames) : ITelemetrySource
{
    public async IAsyncEnumerable<RawFrame> ReadFramesAsync(
        [EnumeratorCancellation] CancellationToken ct)
    {
        foreach (var f in frames) { yield return f; await Task.Yield(); }
    }
}

public sealed class InMemoryTelemetryStore : ITelemetryStore
{
    public List<RawFrame> Saved { get; } = [];
    public Task AppendAsync(RawFrame f, CancellationToken ct) { Saved.Add(f); return Task.CompletedTask; }
}
```

This is the payoff of §7. **Code that `new`s its dependencies can't be unit-tested. Code that receives interfaces can.** Mocking libraries (NSubstitute, Moq) generate fakes like these automatically. Hand-written fakes are clearer while you learn.

Two more seams worth knowing:

- **Time:** inject `TimeProvider` (built into .NET 8+) instead of calling `DateTime.UtcNow`. Tests use `FakeTimeProvider` to jump time forward instantly.
- **Configuration:** construct options directly with `Options.Create(new SensorOptions { ... })`.

### 15.3 The test pyramid

| Level | Scope | Speed | Tools | Example |
|---|---|---|---|---|
| **Unit** | One class, fakes for the rest | ms | xUnit + fakes | Calculator, frame parser, a rule |
| **Integration** | Several real pieces together | seconds | xUnit + real SQLite / `WebApplicationFactory` / ⚫ Testcontainers | Store + real DB; the HTTP API end to end in memory |
| **End-to-end / system** | The deployed system | minutes | Scripts, emulator container, hardware-in-the-loop | Emulator boots, fake frames arrive, dashboard shows them |

Many fast unit tests, fewer integration tests, very few end-to-end tests. Your CI pipeline runs the bottom two on every commit.

---

## 16. Part XIV — Shipping: publish, containers, systemd, pipelines

Tag: 🔵 **CONTRACT**. The goal is to understand what you watched happen, and to be able to write a simple pipeline yourself.

### 16.1 `dotnet publish`

`build` makes something that runs on *your* machine. `publish` makes a **deployable folder**:

```
dotnet publish src/SensorStation.Worker -c Release -r linux-arm64 --self-contained false -o out/worker
```

Everything in `out/worker/` is what goes onto the device (§4.1). Do it once per entry-point project.

### 16.2 Containers

A multi-stage `Dockerfile` builds with the big SDK image and runs on the small runtime image:

```dockerfile
FROM mcr.microsoft.com/dotnet/sdk:10.0 AS build
WORKDIR /src
COPY . .
RUN dotnet publish src/SensorStation.Worker -c Release -o /app

# (use the aspnet:10.0 image instead for web apps)
FROM mcr.microsoft.com/dotnet/runtime:10.0
WORKDIR /app
COPY --from=build /app .
ENTRYPOINT ["dotnet", "SensorStation.Worker.dll"]
```

The .NET SDK can also build an image with no Dockerfile at all: `dotnet publish -t:PublishContainer`.

An "emulator" container that mimics a device's filesystem and runs each component as a service is the same idea, pushed further: **make the dev environment look like production**, so "works in the emulator" predicts "works on the device."

### 16.3 CI/CD pipelines, demystified

- A **pipeline** is a script of build steps, stored in the repo as YAML, that runs automatically on a trigger (a push, a PR, a schedule).
- An **agent** is the machine that executes it: Microsoft-hosted (a fresh VM each run) or self-hosted (your company's box, possibly with special hardware or tools).
- An **artifact** is a file the pipeline keeps after the run: published folders, packages, or a whole OS image.

```yaml
# azure-pipelines.yml (Azure DevOps)
trigger:
  branches: { include: [ main ] }          # run on pushes to main (PR builds are set by branch policy)

pool:
  vmImage: ubuntu-latest                    # a Microsoft-hosted agent

stages:
- stage: Build
  jobs:
  - job: BuildAndTest
    steps:
    - task: UseDotNet@2
      inputs: { packageType: sdk, useGlobalJson: true }       # respects global.json (§3.3)
    - script: dotnet restore
    - script: dotnet build -c Release --no-restore
    - script: dotnet test  -c Release --no-build --logger trx
    - script: dotnet publish src/SensorStation.Worker -c Release -r linux-arm64 -o $(Build.ArtifactStagingDirectory)/worker
    - task: PublishPipelineArtifact@1
      inputs:
        targetPath: $(Build.ArtifactStagingDirectory)
        artifact: drop

- stage: Package
  dependsOn: Build
  jobs:
  - job: Image
    steps:
    - task: DownloadPipelineArtifact@2
      inputs: { artifact: drop }
    - script: ./build/make-device-image.sh $(Pipeline.Workspace)/drop   # your team's image-building script
```

The same concepts in GitHub Actions (useful for your personal projects):

| Azure DevOps | GitHub Actions |
|---|---|
| `azure-pipelines.yml` | `.github/workflows/*.yml` |
| `trigger` / `pr` | `on: push` / `on: pull_request` |
| `pool` / agent | `runs-on` / runner |
| stage → job → step | workflow → job → step |
| `task: X@N` | `uses: owner/action@vN` |
| Pipeline artifact | `actions/upload-artifact` |

### 16.4 The team workflow around it

```
 Jira ticket ─► feature branch (e.g. feature/ABC-123-frame-parser)
     ─► commits ─► push ─► Pull Request
     ─► PR validation pipeline (build + tests MUST pass) + code review
     ─► merge to main ─► main pipeline ─► artifacts / image ─► release
```

Branch policies make the pipeline a **gate**: code that doesn't build or pass tests can't merge. That's why the pipeline exists, and why it felt like an obstacle at first. It's the team's shared safety net.

---
## 17. The lab: build "Sensor Station" by hand

**Rules:** type every line yourself (no copy-paste, no AI). Build after every step. When something fails, first name the **character** responsible (§2), then fix it. Each step lists the sections it exercises.

> **Honesty note:** this code was carefully written and reviewed, but it hasn't been compiled against a real SDK. If something doesn't build, diagnosing the error is part of the exercise, and a good test of whether you can place the error on the map. Note anything you had to fix; those notes are valuable.

**What you'll build:** a small system that "receives" 3-byte telemetry frames from a simulated bus on its own thread, converts them to engineering units, stores the latest values, exposes them over HTTP with a live web page, and shuts down gracefully. It's a miniature, generic version of the kind of system you now work on.

```
  SimulatedBus (own thread) ──callback──► Channel<RawFrame> ──► IngestionWorker ──► ITelemetryStore
                                                                                        │
                                           Browser ◄── index.html ◄── GET /api/readings/latest
```

### Step 0: Tooling (§3, §19)

```bash
dotnet --version            # want 10.0.xxx. If missing, install the .NET 10 SDK from dot.net
dotnet --list-sdks
dotnet --list-runtimes      # note the shared frameworks: Microsoft.NETCore.App, Microsoft.AspNetCore.App
```

### Step 1: The solution skeleton (§3.1, §3.2)

```bash
mkdir SensorStation && cd SensorStation
git init

dotnet new sln -n SensorStation                                           # → SensorStation.slnx
dotnet new classlib -n SensorStation.Core       -o src/SensorStation.Core
dotnet new worker   -n SensorStation.Worker     -o src/SensorStation.Worker
dotnet new web      -n SensorStation.Web        -o src/SensorStation.Web
dotnet new xunit    -n SensorStation.Core.Tests -o tests/SensorStation.Core.Tests

dotnet sln add src/SensorStation.Core/SensorStation.Core.csproj
dotnet sln add src/SensorStation.Worker/SensorStation.Worker.csproj
dotnet sln add src/SensorStation.Web/SensorStation.Web.csproj
dotnet sln add tests/SensorStation.Core.Tests/SensorStation.Core.Tests.csproj

dotnet add src/SensorStation.Worker/SensorStation.Worker.csproj     reference src/SensorStation.Core/SensorStation.Core.csproj
dotnet add src/SensorStation.Web/SensorStation.Web.csproj           reference src/SensorStation.Core/SensorStation.Core.csproj
dotnet add tests/SensorStation.Core.Tests/SensorStation.Core.Tests.csproj reference src/SensorStation.Core/SensorStation.Core.csproj

dotnet add src/SensorStation.Core package Microsoft.Extensions.Hosting.Abstractions
dotnet add src/SensorStation.Core package Microsoft.Extensions.Logging.Abstractions
dotnet add src/SensorStation.Core package Microsoft.Extensions.Options

rm src/SensorStation.Core/Class1.cs src/SensorStation.Worker/Worker.cs
dotnet build        # the Worker will fail: Program.cs still mentions Worker. Good. Read the error.
```

**Checkpoint:** before fixing anything, open all four `.csproj` files and draw the reference graph on paper. Which projects are executables? (Two: Worker and Web. Tests are a special case: the test host runs them.) Which SDK does each use?

### Step 2: The frame format, test-first (§6.8, §15.1)

Create `src/SensorStation.Core/Frames.cs`. Type the `TelemetryKind`, `RawFrame`, and `FrameParser` code from §6.8, with `namespace SensorStation.Core;` at the top.

Then `tests/SensorStation.Core.Tests/FrameParserTests.cs`:

```csharp
using SensorStation.Core;

namespace SensorStation.Core.Tests;

public class FrameParserTests
{
    [Fact]
    public void Parses_a_valid_temperature_frame()
    {
        byte[] bytes = [0x03, 0x0F, 0x00];

        var ok = FrameParser.TryParse(bytes, out var frame);

        Assert.True(ok);
        Assert.Equal(TelemetryKind.Temperature, frame.Kind);
        Assert.Equal((ushort)0x0F00, frame.Raw);
    }

    [Theory]
    [InlineData(new byte[] { 0x01, 0x00 })]               // too short
    [InlineData(new byte[] { 0x01, 0x00, 0x00, 0x00 })]   // too long
    [InlineData(new byte[] { 0x09, 0x00, 0x00 })]         // unknown preamble
    public void Rejects_malformed_frames(byte[] bytes) =>
        Assert.False(FrameParser.TryParse(bytes, out _));
}
```

```bash
dotnet test tests/SensorStation.Core.Tests
```

**Checkpoint:** all green. Now break `FrameParser` on purpose (read little-endian instead) and watch exactly one test fail. Undo it.

### Step 3: Calculators: strategy + composition (§7.2, §15.1)

Create `src/SensorStation.Core/Calculators.cs` with `IValueCalculator`, `UnsignedRawCalculator`, and `SignedRawCalculator` from §7.2. Then add a calculator that **wraps another one**. That's composition, and this particular shape is called the *Decorator* pattern:

```csharp
public sealed class ScaledCalculator(IValueCalculator inner, double scale) : IValueCalculator
{
    public double Calculate(IReadOnlyList<double> inputs) => inner.Calculate(inputs) * scale;
}
```

And a converter that maps each kind to its calculator:

```csharp
namespace SensorStation.Core;

public sealed class ReadingConverter
{
    private static readonly Dictionary<TelemetryKind, IValueCalculator> Table = new()
    {
        [TelemetryKind.BusVoltage]  = new ScaledCalculator(new UnsignedRawCalculator(), 0.004),       // 4 mV/bit → volts
        [TelemetryKind.Current]     = new ScaledCalculator(new SignedRawCalculator(),   0.001),       // 1 mA/bit → amps
        [TelemetryKind.Temperature] = new ScaledCalculator(new SignedRawCalculator(),   1.0 / 128),   // 1/128 °C/bit
        [TelemetryKind.FanRpm]      = new UnsignedRawCalculator(),
    };

    public double Convert(RawFrame frame) =>
        Table.TryGetValue(frame.Kind, out var calc) ? calc.Calculate([frame.Raw]) : double.NaN;
}
```

Tests to write yourself (no code given, on purpose): the §15.1 signed theory; `0x0F00` temperature → `30.0`; `0xFFFF` current → `-0.001` (use `Assert.Equal(expected, actual, precision: 6)`, and think about *why* doubles need a precision argument).

### Step 4: The ingestion pipeline (§7.1, §8.5, §10.7, §11.5)

`src/SensorStation.Core/Contracts.cs`:

```csharp
namespace SensorStation.Core;

public readonly record struct LatestReading(TelemetryKind Kind, ushort Raw, double Value, DateTimeOffset At);

public interface ITelemetrySource
{
    IAsyncEnumerable<RawFrame> ReadFramesAsync(CancellationToken ct);
}

public interface ITelemetryStore
{
    Task AppendAsync(RawFrame frame, CancellationToken ct);
    IReadOnlyDictionary<TelemetryKind, LatestReading> GetLatest();
}

public sealed class SensorOptions
{
    public const string Section = "Sensors";
    public int    PollIntervalMs        { get; set; } = 250;
    public double UnderVoltageThreshold { get; set; } = 11.8;
}
```

`src/SensorStation.Core/SimulatedBus.cs`. This plays the role of a native library: it owns a thread and calls you back.

```csharp
using Microsoft.Extensions.Options;

namespace SensorStation.Core;

public sealed class SimulatedBus(IOptions<SensorOptions> options) : IDisposable
{
    private Thread? _thread;
    private volatile bool _running;            // a simple stop flag: one of the few legitimate uses of volatile
    private Action<byte[]>? _callback;

    public void Start(Action<byte[]> callback)
    {
        if (_running) throw new InvalidOperationException("Bus already started");
        _callback = callback;
        _running  = true;
        _thread   = new Thread(Loop) { IsBackground = true, Name = "simulated-bus" };
        _thread.Start();
    }

    public void Stop() => _running = false;

    private void Loop()
    {
        var rng   = new Random();
        var kinds = Enum.GetValues<TelemetryKind>();

        while (_running)
        {
            var kind = kinds[rng.Next(kinds.Length)];
            ushort raw = kind switch
            {
                TelemetryKind.BusVoltage  => (ushort)rng.Next(2900, 3100),              // ≈ 11.6–12.4 V
                TelemetryKind.Current     => unchecked((ushort)(short)rng.Next(-200, 2000)),
                TelemetryKind.Temperature => (ushort)(rng.Next(30, 60) * 128),          // 30–60 °C
                TelemetryKind.FanRpm      => (ushort)rng.Next(1800, 2600),
                _                         => (ushort)0,
            };

            byte[] frame = [(byte)kind, (byte)(raw >> 8), (byte)raw];
            _callback?.Invoke(frame);                      // ← we are on the BUS thread here
            Thread.Sleep(options.Value.PollIntervalMs);
        }
    }

    public void Dispose() => Stop();
}
```

`src/SensorStation.Core/SimulatedBusTelemetrySource.cs`. The "ISR → ring buffer" bridge:

```csharp
using System.Threading.Channels;

namespace SensorStation.Core;

public sealed class SimulatedBusTelemetrySource(SimulatedBus bus) : ITelemetrySource
{
    private readonly Channel<RawFrame> _channel = Channel.CreateBounded<RawFrame>(
        new BoundedChannelOptions(1024) { FullMode = BoundedChannelFullMode.DropOldest, SingleReader = true });

    private long _malformed;
    public long MalformedCount => Interlocked.Read(ref _malformed);

    public IAsyncEnumerable<RawFrame> ReadFramesAsync(CancellationToken ct)
    {
        bus.Start(OnBytes);
        ct.Register(bus.Stop);
        return _channel.Reader.ReadAllAsync(ct);
    }

    // "ISR": runs on the bus thread. Short, non-blocking, never throws.
    private void OnBytes(byte[] bytes)
    {
        if (FrameParser.TryParse(bytes, out var frame)) _channel.Writer.TryWrite(frame);
        else Interlocked.Increment(ref _malformed);
    }
}
```

`src/SensorStation.Core/InMemoryTelemetryStore.cs`:

```csharp
using System.Collections.Concurrent;

namespace SensorStation.Core;

public sealed class InMemoryTelemetryStore(ReadingConverter converter, TimeProvider time) : ITelemetryStore
{
    private readonly ConcurrentDictionary<TelemetryKind, LatestReading> _latest = new();

    public Task AppendAsync(RawFrame frame, CancellationToken ct)
    {
        _latest[frame.Kind] = new LatestReading(frame.Kind, frame.Raw, converter.Convert(frame), time.GetUtcNow());
        return Task.CompletedTask;
    }

    public IReadOnlyDictionary<TelemetryKind, LatestReading> GetLatest() =>
        new Dictionary<TelemetryKind, LatestReading>(_latest);     // snapshot, not a live view
}
```

`src/SensorStation.Core/IngestionWorker.cs`: type the `IngestionWorker` from §8.5 (the first version, with `ITelemetrySource`, `ITelemetryStore`, and `ILogger`). Add `using Microsoft.Extensions.Hosting;` and `using Microsoft.Extensions.Logging;`.

`src/SensorStation.Core/ServiceCollectionExtensions.cs`. The library plugs itself in (§9.4):

```csharp
using Microsoft.Extensions.DependencyInjection.Extensions;
using SensorStation.Core;

namespace Microsoft.Extensions.DependencyInjection;

public static class SensorStationServiceCollectionExtensions
{
    public static IServiceCollection AddSensorStation(this IServiceCollection services)
    {
        services.TryAddSingleton(TimeProvider.System);
        services.AddSingleton<ReadingConverter>();
        services.AddSingleton<SimulatedBus>();
        services.AddSingleton<ITelemetrySource, SimulatedBusTelemetrySource>();
        services.AddSingleton<ITelemetryStore, InMemoryTelemetryStore>();
        services.AddHostedService<IngestionWorker>();
        return services;
    }
}
```

`src/SensorStation.Worker/Program.cs`:

```csharp
using SensorStation.Core;

var builder = Host.CreateApplicationBuilder(args);

builder.Services.AddOptions<SensorOptions>()
    .Bind(builder.Configuration.GetSection(SensorOptions.Section))
    .Validate(o => o.PollIntervalMs is >= 10 and <= 60_000, "Sensors:PollIntervalMs must be 10–60000")
    .ValidateOnStart();

builder.Services.AddSensorStation();

var host = builder.Build();
host.Run();
```

Add to `src/SensorStation.Worker/appsettings.json`:

```json
"Sensors": { "PollIntervalMs": 500, "UnderVoltageThreshold": 11.8 }
```

```bash
dotnet run --project src/SensorStation.Worker
```

**Checkpoint:** you see "Ingestion starting," then nothing (the store doesn't log). Add a `LogDebug` in the worker loop and make it visible by setting `"SensorStation": "Debug"` under `Logging:LogLevel`. That's category-based log filtering (§9.7). Then, **in your own words, in a notebook:** list every object the container created, in order, and who called each constructor.

### Step 5: Configuration precedence (§9.5)

Run it three ways and watch the frame rate change:

```bash
dotnet run --project src/SensorStation.Worker                                   # appsettings.json: 500 ms
Sensors__PollIntervalMs=100 dotnet run --project src/SensorStation.Worker       # env var wins: 100 ms
dotnet run --project src/SensorStation.Worker -- --Sensors:PollIntervalMs=2000  # command line wins: 2000 ms
dotnet run --project src/SensorStation.Worker -- --Sensors:PollIntervalMs=1     # validation fails at startup
```

**Checkpoint:** explain the fourth run's failure using the words *Options*, *ValidateOnStart*, and *Conductor*.

### Step 6: Break it on purpose: host lifecycle (§8.4, §8.6)

1. Press Ctrl+C. Read the shutdown log lines in order and match each to the STOP sequence in §8.4.
2. Temporarily put `if (frame.Kind == TelemetryKind.FanRpm) throw new InvalidOperationException("boom");` *outside* the inner `try` in `IngestionWorker`. Run it. The **whole host stops.** Find the log line that says why.
3. Move the throw *inside* the inner `try`. Now the error is logged and ingestion continues. Remove the throw.

### Step 7: A derived condition: "needs shutdown" (§8.5 timer shape, §9.6)

Write a second `BackgroundService`, `PowerWatchdog`, yourself. Requirements:

- Every second (`PeriodicTimer`), read the latest `BusVoltage` from `ITelemetryStore`.
- If it's below `SensorOptions.UnderVoltageThreshold` for **3 consecutive checks**, log a `Critical` "shutdown required," then call `IHostApplicationLifetime.StopApplication()` (inject it). This stands in for "invoke the shutdown service."
- Register it in `AddSensorStation`.
- Test it by running with `--Sensors:UnderVoltageThreshold=12.3`.

**Checkpoint:** this is a *derived state*. Its inputs are other states, and it produces a decision. Where would the "3 consecutive checks" counter live, and why must it not be a `static` field?

### Step 8: Same library, second host: the web dashboard (§8.3, §13.1, §13.2)

`src/SensorStation.Web/Program.cs`:

```csharp
using SensorStation.Core;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddOptions<SensorOptions>()
    .Bind(builder.Configuration.GetSection(SensorOptions.Section))
    .ValidateOnStart();

builder.Services.AddSensorStation();               // the SAME one line as the worker

var app = builder.Build();

app.UseDefaultFiles();                              // "/" → "/index.html"
app.UseStaticFiles();                               // serves files from wwwroot/

app.MapGet("/api/readings/latest", (ITelemetryStore store) =>
    store.GetLatest().Values
        .OrderBy(r => r.Kind)
        .Select(r => new { kind = r.Kind.ToString(), r.Raw, r.Value, r.At }));

app.Run();
```

`src/SensorStation.Web/wwwroot/index.html`:

```html
<!doctype html>
<html>
<head><meta charset="utf-8"><title>Sensor Station</title></head>
<body>
  <h1>Sensor Station</h1>
  <table id="t" border="1" cellpadding="6"></table>
  <script>
    async function refresh() {
      const rows = await (await fetch('/api/readings/latest')).json();
      document.getElementById('t').innerHTML =
        '<tr><th>Kind</th><th>Raw</th><th>Value</th><th>At (UTC)</th></tr>' +
        rows.map(x => `<tr><td>${x.kind}</td><td>0x${x.raw.toString(16).padStart(4, '0')}</td>` +
                      `<td>${x.value.toFixed(3)}</td><td>${x.at}</td></tr>`).join('');
    }
    setInterval(refresh, 1000);
    refresh();
  </script>
</body>
</html>
```

```bash
dotnet run --project src/SensorStation.Web      # open the URL it prints
```

**Checkpoints:**

1. The web app runs its *own* bus, worker, and store, because it's a separate **process** with a separate container. Run the Worker and the Web at the same time: are their values related? Why not? What would they need to share? (Answer: a database or an API. That's Stretch A, and it's exactly why real systems put a DB between an ingestion process and a dashboard process.)
2. Open `/api/readings/latest` directly. Why are the property names camelCase (§13.2)?
3. Using your browser's dev tools (Network tab), find the request, the JSON, and the timing. Recognize that "the dashboard" is just a static HTML page making HTTP requests to your minimal API.

### Step 9: Publish and inspect (§4.1, §16.1)

```bash
dotnet publish src/SensorStation.Worker -c Release -o out/worker
ls out/worker
cat out/worker/SensorStation.Worker.runtimeconfig.json
dotnet out/worker/SensorStation.Worker.dll
```

**Checkpoint:** name every file in `out/worker` and which character (§2) uses it. Then write (don't install) the systemd unit you would use for it (§8.7).

### Stretch A: a real database (§9.3, §12)

Add `Microsoft.EntityFrameworkCore.Sqlite` to Core. Create `SensorDefinition`/`Reading` entities and a `TelemetryDbContext` (§12.2), plus an `EfTelemetryStore : ITelemetryStore` registered as **scoped**.

1. First, inject `ITelemetryStore` directly into `IngestionWorker` and run with `DOTNET_ENVIRONMENT=Development`. Read the captive-dependency error (§9.3). Don't skip this: seeing it once makes it unforgettable.
2. Fix it with `IServiceScopeFactory`.
3. Point both the Worker and the Web at the same `.db` file. Split `AddSensorStation()` into two extension methods, `AddSensorStationIngestion()` (bus, source, worker, watchdog) and `AddSensorStationQueries()` (store, converter), and have the Web call only the second. Now you have the real architecture: **one ingestion process, one read-only dashboard process, a database between them.**

(`GetLatest` becomes a database query. You'll probably want to change the interface to `Task<IReadOnlyDictionary<…>> GetLatestAsync(CancellationToken ct)`. Changing a contract and following the compiler errors to every caller is a skill in itself.)

### Stretch B: a real native library and a callback (§11)

This is your home turf. Write the "native library" in C yourself, then cross the border.

`native/fakebus.c`:

```c
#include <pthread.h>
#include <stdint.h>
#include <stdlib.h>
#include <unistd.h>

typedef void (*frame_cb)(const uint8_t *frame, int len, void *user);

static pthread_t    g_thread;
static volatile int g_running = 0;
static frame_cb     g_cb   = NULL;
static void        *g_user = NULL;

static void *loop(void *arg)
{
    (void)arg;
    while (g_running) {
        uint16_t raw = (uint16_t)(2900 + rand() % 200);               /* bus voltage */
        uint8_t frame[3] = { 0x01, (uint8_t)(raw >> 8), (uint8_t)(raw & 0xFF) };
        if (g_cb) g_cb(frame, 3, g_user);
        usleep(250 * 1000);
    }
    return NULL;
}

int fakebus_start(frame_cb cb, void *user)
{
    if (g_running) return -1;
    g_cb = cb; g_user = user; g_running = 1;
    return pthread_create(&g_thread, NULL, loop, NULL) == 0 ? 0 : -2;
}

int fakebus_stop(void)
{
    if (!g_running) return -1;
    g_running = 0;
    pthread_join(g_thread, NULL);                                     /* no callbacks after this returns */
    g_cb = NULL; g_user = NULL;
    return 0;
}
```

```bash
# macOS (Apple silicon):  produces an arm64 .dylib
clang -shared -fPIC -o src/SensorStation.Worker/libfakebus.dylib native/fakebus.c
# Linux / Raspberry Pi:
gcc   -shared -fPIC -o src/SensorStation.Worker/libfakebus.so    native/fakebus.c -pthread
```

In `SensorStation.Worker.csproj`, add `<AllowUnsafeBlocks>true</AllowUnsafeBlocks>` and copy the library to the output:

```xml
<ItemGroup>
  <None Update="libfakebus.*" CopyToOutputDirectory="PreserveNewest" />   <!-- Update: the file is already a None item via default globbing -->
</ItemGroup>
```

`src/SensorStation.Worker/NativeBusTelemetrySource.cs`:

```csharp
using System.Runtime.CompilerServices;
using System.Runtime.InteropServices;
using System.Threading.Channels;
using SensorStation.Core;

internal static unsafe partial class FakeBusNative
{
    [LibraryImport("fakebus", EntryPoint = "fakebus_start")]
    internal static partial int Start(delegate* unmanaged[Cdecl]<byte*, int, nint, void> cb, nint user);

    [LibraryImport("fakebus", EntryPoint = "fakebus_stop")]
    internal static partial int Stop();
}

public sealed unsafe class NativeBusTelemetrySource : ITelemetrySource, IDisposable
{
    private readonly Channel<RawFrame> _channel = Channel.CreateBounded<RawFrame>(
        new BoundedChannelOptions(1024) { FullMode = BoundedChannelFullMode.DropOldest, SingleReader = true });

    private GCHandle _self;
    private long _malformed;

    public IAsyncEnumerable<RawFrame> ReadFramesAsync(CancellationToken ct)
    {
        _self = GCHandle.Alloc(this);
        int rc = FakeBusNative.Start(&OnFrame, GCHandle.ToIntPtr(_self));
        if (rc != 0) throw new InvalidOperationException($"fakebus_start failed with {rc}");
        return _channel.Reader.ReadAllAsync(ct);
    }

    [UnmanagedCallersOnly(CallConvs = new[] { typeof(CallConvCdecl) })]
    private static void OnFrame(byte* frame, int len, nint user)
    {
        try
        {
            var self = (NativeBusTelemetrySource)GCHandle.FromIntPtr(user).Target!;
            var span = new ReadOnlySpan<byte>(frame, len);   // views NATIVE memory: valid only during this call
            if (FrameParser.TryParse(span, out var f)) self._channel.Writer.TryWrite(f);   // copies the values out
            else Interlocked.Increment(ref self._malformed);
        }
        catch
        {
            // Never let an exception cross into C (§11.4).
        }
    }

    public void Dispose()
    {
        FakeBusNative.Stop();                  // joins the native thread: no callbacks after this
        if (_self.IsAllocated) _self.Free();
        _channel.Writer.TryComplete();
    }
}
```

Now the payoff of the whole lecture. In the Worker's `Program.cs`, **after** `AddSensorStation()`, add one line:

```csharp
builder.Services.AddSingleton<ITelemetrySource, NativeBusTelemetrySource>();   // last registration wins
```

Run it. The ingestion worker, the store, the converter, the watchdog, and the tests are **unchanged**. Only the source of frames moved across the native border. That's what the interface bought you.

**Checkpoints:**

1. Why does DI's "last registration wins" rule let this one line override the simulated source?
2. Who calls `Dispose()` on `NativeBusTelemetrySource`, and when (§8.4, §9.2)? Why must `Stop()` come before `Free()`?
3. Try the *wrong* version on purpose: a `DllImport` with a delegate you *don't* store in a field, plus `GC.Collect()` called every second from another worker. Observe (and then explain) the crash. Doing this once, deliberately, on your laptop is worth it.

### Further exercises (no instructions: design them yourself)

- A PowerShell binary module with `Get-SensorReading` that reads the Stretch A database (§14).
- A gRPC `AuditLog` service; make `PowerWatchdog` record an audit event before stopping the app (§13.3).
- A `Dockerfile` for the Worker (§16.2), and a GitHub Actions workflow that builds and tests the solution on every push (§16.3).

---
## 18. Firmware ↔ .NET translation table

You've been doing many of these concepts by hand for years. This table is the bridge. Reread it whenever a .NET idea feels alien.

| Firmware concept | .NET concept | Section |
|---|---|---|
| Makefile / CMake | `.csproj` + MSBuild | §3 |
| Object files + static linker | Assemblies + load-time binding | §3.6, §4 |
| Vendor HAL (`.a` + headers) | NuGet package / raw assembly reference (metadata = header) | §3.5 |
| Bootloader + `crt0` startup | `dotnet` host (muxer → hostfxr → hostpolicy) + runtime init | §4.2 |
| `.map` file | `deps.json` | §4.1 |
| Compiling for a specific MCU | IL compiled by the JIT on the target; RID for native bits | §5.1 |
| Static allocation / memory pools | GC heap; `ArrayPool<T>` | §5.4 |
| `struct` by value vs pointer | `struct` (value type) vs `class` (reference type) | §5.3 |
| `uint8_t* buf, size_t len` | `Span<byte>` / `ReadOnlySpan<byte>` | §6.8 |
| `(int16_t)raw` reinterpret | `unchecked((short)raw)` | §6.8 |
| Function pointer + `void* user` | Delegate / closure; `GCHandle` through `void* user` | §6.5, §11.4 |
| Interrupt vector table | DI registration + framework callbacks (IoC) | §8.1 |
| ISR | `BackgroundService` "vectored" by the host; native callbacks | §8, §11.5 |
| ISR → ring buffer → main loop | Callback → `Channel<T>` → `await foreach` | §10.7 |
| Superloop task / protothread | `async` state machine | §10.3 |
| DMA + completion interrupt | Async I/O + continuation | §10.1 |
| Disable interrupts (critical section) | `lock` | §10.7 |
| RTOS semaphore | `SemaphoreSlim` | §10.7 |
| HAL interface with swappable drivers | Interface + DI registration | §7.1 |
| `#define` config / EEPROM settings | `IConfiguration` + Options | §9.5 |
| UART debug `printf` | `ILogger<T>` structured logs | §9.7 |
| Watchdog / brown-out detector | A `BackgroundService` evaluating a derived condition | Lab step 7 |
| Framed protocol with a preamble byte | `.proto` messages with field numbers | §13.3 |
| Unit test on a host PC with stubbed HAL | xUnit + fakes through interfaces | §15 |
| Hardware-in-the-loop rig | Integration/system tests; emulator container | §15.3, §16.2 |
| Flashing a firmware image | Writing an OS image built by the pipeline | §16.3 |

---

## 19. Tooling fluency: the keyboard is part of the job

Your persona notes that software engineers live on shortcuts. Here's the minimum set. Drill it until it's reflex. (Shortcuts are for **VS Code with C# Dev Kit on macOS**; Visual Studio on Windows uses the same F-keys with Ctrl instead of Cmd. Rider differs, so check its keymap. Verify any shortcut in your editor's keybinding list.)

### 19.1 Navigation: the Interface-First Reading Protocol, on keys

| Action | VS Code (mac) | Visual Studio (Win) | Why it matters |
|---|---|---|---|
| Go to definition | F12 | F12 | Jump to `AddStateService()` to see registrations |
| **Go to implementation** | Cmd+F12 | Ctrl+F12 | From an interface method straight to the class that implements it |
| Find all references | Shift+F12 (peek) / Shift+Opt+F12 | Shift+F12 | Protocol step 3: find existing callers |
| Peek definition (inline) | Opt+F12 | Alt+F12 | Look without losing your place |
| Navigate back | Ctrl+- | Ctrl+- | Climb back up the stack of jumps |
| Go to symbol in workspace | Cmd+T | Ctrl+T | Find `IngestionWorker` without the file tree |
| Quick open file | Cmd+P | Ctrl+, | Same, for files |
| Command palette | Cmd+Shift+P | Ctrl+Q | Everything else |
| Rename symbol (everywhere) | F2 | Ctrl+R, Ctrl+R | Safe refactoring |
| Quick fix / add `using` | Cmd+. | Ctrl+. | Fix most red squiggles instantly |

### 19.2 Debugger

| Action | Key |
|---|---|
| Start debugging / continue | F5 |
| Toggle breakpoint | F9 |
| Step over / into / out | F10 / F11 / Shift+F11 |

Learn **conditional breakpoints** (break only when `frame.Kind == FanRpm`), **logpoints** (print without editing code), the **Call Stack** window (it answers "who called this?", the question from §8.2), and **exception settings** (break when an exception is *thrown*, not only when it's unhandled).

### 19.3 The `dotnet` CLI cheat sheet

```bash
dotnet new list                         # templates
dotnet new <template> -n Name -o path
dotnet sln add <csproj>                 # solution membership
dotnet add <csproj> reference <csproj>  # project → project
dotnet add <csproj> package <Id>        # project → NuGet
dotnet restore | build | run | test | publish
dotnet run --project <csproj> -- --Key=Value     # args after -- go to YOUR app
dotnet test --filter "FullyQualifiedName~FrameParser"
dotnet list package --outdated          # dependency hygiene
dotnet clean ; rm -rf bin obj           # the .NET "have you tried turning it off and on"
dotnet --info                           # SDKs, runtimes, RID. Paste this in bug reports.
```

⚫ Diagnostics tools to recognize: `dotnet-counters` (live GC/thread-pool/request metrics), `dotnet-trace` (CPU/event traces), `dotnet-dump` (memory dumps). These become 🔵 in the performance lecture.

---

## 20. Common mistakes

| Mistake | Symptom | Fix | Section |
|---|---|---|---|
| Reading the implementation before the interface | Hours lost, no working code | Interface-First Reading Protocol | §7.5 |
| Answering a rung-3 question at rung 6 | Frustrated seniors | Altitude ladder | §7.4 |
| Forgetting to register a service | "Unable to resolve service for type…" | Add the registration in *that process's* `Program.cs` | §9.4 |
| Singleton capturing a scoped `DbContext` | "Cannot consume scoped service…" or random concurrency bugs | `IServiceScopeFactory` / `IDbContextFactory` | §9.3 |
| Unhandled exception in `ExecuteAsync` | Whole app stops | Per-iteration `try/catch` | §8.6 |
| Ignoring `stoppingToken` | Slow shutdown; systemd kills the app after the timeout | Pass the token everywhere | §8.6, §10.5 |
| `.Result` / `.Wait()` on tasks | Thread-pool starvation, deadlocks | Async all the way | §10.6 |
| `async void` | Uncatchable crashes | Return `Task` | §10.6 |
| Heavy work inside a native callback | Dropped events, stalls | Hand off via `Channel<T>` | §10.7, §11.5 |
| Callback delegate not stored in a field | Random crash after a GC | Keep a reference, or use `UnmanagedCallersOnly` | §11.4 |
| `char` for a C byte buffer | Wrong layout, garbage values | `byte` | §11.3 |
| String-interpolated log messages | Unsearchable logs | Message templates | §9.7 |
| Enumerating an `IEnumerable` twice | Work (or queries) run twice | `.ToList()` once | §6.6 |
| `Where` on `IEnumerable` instead of `IQueryable` | Whole table loaded into memory | Keep the chain on the `IQueryable` | §6.6, §12.2 |
| `new HttpClient()` per call | Socket exhaustion | `IHttpClientFactory` | §13.4 |
| Secrets in `appsettings.json` | Credential leak via git | Secret store + interface | §9.8 |
| `throw ex;` | Lost stack trace | `throw;` | §6.10 |
| Stale `bin/obj` | Bizarre build errors | `dotnet clean`, delete `bin`/`obj` | §3.4 |

---

## 21. Interview relevance

These come up constantly in .NET interviews, including Microsoft loops. For each one, practice a **two-minute spoken answer**: rung 3 first, then one level deeper, then a trade-off.

| Question | What a strong answer covers |
|---|---|
| Value type vs reference type? | Copy vs alias; "stored inline" (not "stack vs heap"); boxing; when to choose `struct` |
| How does the GC work? | Roots → mark → compact; generations and why; LOH; `IDisposable` is separate |
| What happens when you `await`? | State machine; no thread blocked; continuation on the pool; `Task` ≠ thread |
| Why not use `.Result`? | Thread-pool starvation; deadlocks with a `SynchronizationContext` |
| Explain DI and the three lifetimes. | Registration vs resolution; singleton/scoped/transient; the captive dependency bug |
| What is the Generic Host? | Configure → build → run; hosted services; graceful shutdown; config/logging/DI in one place |
| `IEnumerable` vs `IQueryable`? | In-memory lazy sequence vs expression tree translated to SQL |
| What is middleware? | An ordered pipeline; each station can short-circuit; why order matters (auth before endpoints) |
| `IDisposable` / `using`? | Deterministic release of non-memory resources; who disposes DI-created objects |
| REST vs gRPC? | Contract, payload, HTTP/2, streaming, where each fits |
| How do you make code testable? | Depend on interfaces, inject dependencies, inject `TimeProvider`, fakes vs mocks |
| **Tell me about a hard technical problem.** | **Your story:** firmware → I2C → a .NET worker using P/Invoke with a native callback, handing frames across threads → a data model that turns raw hex into decisions. Mention the delegate-lifetime and ISR-discipline insights. Very few candidates can tell this story. |

---
## 22. Self-check questions

Answer out loud or on paper **before** opening the answer. If you can't, the section number tells you where to go back.

**Build & launch**

1. What's the difference between a solution, a project, an assembly, and a namespace? (§3.1)
   <details><summary>Answer</summary>Solution = a list of projects (dev-time only). Project = a build recipe. Assembly = the compiled output of one project (IL + metadata). Namespace = a logical naming prefix for types, independent of the other three.</details>

2. Why do enterprise solutions split code into many projects? (§3.2)
   <details><summary>Answer</summary>To enforce architecture physically: a project can only use what it references, and references can't form cycles. Also for separate executables (separate processes) and shared libraries.</details>

3. You add a new `.cs` file to a project folder but never edit the `.csproj`. Is it compiled? (§3.3)
   <details><summary>Answer</summary>Yes. SDK-style projects glob <code>**/*.cs</code> automatically.</details>

4. Name three ways a project can depend on other code, and when each is used. (§3.5)
   <details><summary>Answer</summary>ProjectReference (same solution), PackageReference (NuGet feed), raw Reference with HintPath (a vendor <code>.dll</code> not published as a package).</details>

5. What do `runtimeconfig.json` and `deps.json` each tell the host? (§4.1–4.2)
   <details><summary>Answer</summary>runtimeconfig: which shared framework and version to run on (plus runtime settings). deps: which assemblies and native libraries the app needs and where to find them.</details>

6. A referenced `.dll` is missing from the deploy folder, but the app starts fine and crashes two hours later. Why? (§4.2)
   <details><summary>Answer</summary>Assemblies load lazily, when a method that needs one of their types is first JIT-compiled. The missing assembly wasn't needed until that code path ran.</details>

**Runtime & language**

7. Why can the same `.dll` run on x64 and on a Raspberry Pi? (§5.1)
   <details><summary>Answer</summary>It contains IL, not machine code. The JIT on each target compiles IL to that CPU's instructions at run time.</details>

8. "Structs live on the stack." True? (§5.3)
   <details><summary>Answer</summary>Only partly. Value types are stored inline where declared: on the stack for locals, inside the containing object for fields (which may be on the heap), inside arrays.</details>

9. Why must you pin memory (or use blittable `ref` structs) when passing it to native code? (§5.4, §11.3)
   <details><summary>Answer</summary>The GC compacts the heap and moves objects. A raw pointer held by native code would become invalid if the object moved mid-call.</details>

10. What does `unchecked((short)0xFFFF)` evaluate to, and why? (§6.8)
    <details><summary>Answer</summary>-1. The 16 bits are reinterpreted as two's complement; all ones = -1.</details>

11. You build a LINQ query and loop over it twice. What happens? (§6.6)
    <details><summary>Answer</summary>The query runs twice (deferred execution). For EF Core that's two database round trips. Materialize with <code>.ToList()</code> once.</details>

12. What are attributes for? (§6.9)
    <details><summary>Answer</summary>Metadata attached to code that frameworks read (via reflection or source generators) to decide how to call or treat it: <code>[Cmdlet]</code>, <code>[Parameter]</code>, <code>[LibraryImport]</code>, <code>[Fact]</code>…</details>

**Abstraction, host, DI**

13. Your lead asks "how does the dashboard get its data?" Give a rung-3 answer. (§7.4)
    <details><summary>Answer</summary>Something like: "The web app calls the query service's get-latest operation through its interface, which reads the most recent value rows from the database." Offer rung 4 if they want more.</details>

14. What are the six fields of a Contract Card? (§7.6)
    <details><summary>Answer</summary>Inputs, Outputs, Failures, Side effects, Lifetime & threading, Cost.</details>

15. What are the three phases every .NET app model shares? (§8.3)
    <details><summary>Answer</summary>Configure (builder + registrations) → Build (freeze into a provider/host) → Run (framework owns control flow until shutdown).</details>

16. In what order are hosted services started and stopped? (§8.4)
    <details><summary>Answer</summary>Started in registration order; stopped in reverse order, within the shutdown timeout (30 s by default).</details>

17. What happens if `ExecuteAsync` throws an unhandled exception? (§8.6)
    <details><summary>Answer</summary>By default (since .NET 6) the host logs it and stops the entire application.</details>

18. What does `systemctl stop` do to a .NET host? (§8.7)
    <details><summary>Answer</summary>It sends SIGTERM, which the host turns into the graceful stop sequence: ApplicationStopping, StopAsync on each service (cancelling stoppingTokens), ApplicationStopped, dispose.</details>

19. Explain the captive dependency problem and its fix. (§9.3)
    <details><summary>Answer</summary>A singleton (e.g. a hosted service) that takes a scoped dependency (e.g. a DbContext) keeps it forever, sharing a non-thread-safe, ever-growing object. Fix: inject <code>IServiceScopeFactory</code> (or <code>IDbContextFactory</code>) and create a short scope per unit of work.</details>

20. `appsettings.json` says 500, the environment variable says 100, the command line says 2000. Which wins? How do you write the env var? (§9.5)
    <details><summary>Answer</summary>The command line (2000). The env var is <code>Sensors__PollIntervalMs=100</code>, with a double underscore standing for the colon.</details>

21. Why is `log.LogInformation($"Rpm {rpm}")` worse than `log.LogInformation("Rpm {Rpm}", rpm)`? (§9.7)
    <details><summary>Answer</summary>Interpolation loses the structured property (you can't query by Rpm) and formats the string even when the level is disabled.</details>

**Async & interop**

22. Is a `Task` a thread? (§10.2)
    <details><summary>Answer</summary>No. It's a promise of a future result. While awaiting I/O, usually no thread is involved at all.</details>

23. Why shouldn't a native callback write to the database directly? (§10.7, §11.5)
    <details><summary>Answer</summary>It runs on the native library's thread and must return quickly (ISR rules). Blocking there stalls the native library and risks dropped events. Hand off to a <code>Channel&lt;T&gt;</code> instead.</details>

24. Describe the "collected delegate" crash and two ways to prevent it. (§11.4)
    <details><summary>Answer</summary>Native code keeps a function pointer to a delegate that no managed code references. The GC collects it, and the next callback jumps into freed memory. Prevent it by storing the delegate in a field that lives as long as the registration, or by using a static <code>[UnmanagedCallersOnly]</code> method with a function pointer (and a <code>GCHandle</code> for context).</details>

25. `DllNotFoundException` vs `EntryPointNotFoundException`? (§11.6)
    <details><summary>Answer</summary>The first means the library couldn't be loaded at all (name, path, architecture, or a missing dependency). The second means it loaded but the symbol wasn't found (typo, C++ mangling, version).</details>

**Data, web, PowerShell, testing, shipping**

26. When does EF Core actually write to the database? (§12.3)
    <details><summary>Answer</summary>On <code>SaveChanges</code> / <code>SaveChangesAsync</code>, which writes all tracked changes in a transaction.</details>

27. Why must middleware be added in the right order? (§13.1)
    <details><summary>Answer</summary>Each request flows through stations in order and any station can short-circuit. Authorization after the endpoint would be useless; static files before routing can answer without reaching endpoints.</details>

28. Why can a mismatch between gRPC client and server be caught at compile time? (§13.3)
    <details><summary>Answer</summary>Both sides generate C# from the same <code>.proto</code> contract.</details>

29. What does `Import-Module ./X.dll` actually do? (§14.1)
    <details><summary>Answer</summary>Loads the .NET assembly into the PowerShell process and registers each class marked <code>[Cmdlet]</code> as a command.</details>

30. Why does code that `new`s its own dependencies resist unit testing? (§15.2)
    <details><summary>Answer</summary>There's no seam to substitute a fake. Receiving interfaces through the constructor lets a test pass in-memory fakes.</details>

31. What's the difference between an agent, a pipeline, and an artifact? (§16.3)
    <details><summary>Answer</summary>Pipeline = the YAML-defined sequence of steps and when it triggers. Agent = the machine that executes it. Artifact = the output files kept after the run (published folders, images).</details>

---

## 23. Roadmap for this folder

Each future lecture takes one 🔵 or ⚫ area from this atlas and turns it 🟢. The order is chosen for **your** situation: what pays off at work soonest, then what closes interview and Microsoft-resume gaps.

| # | Working title | Why it's next |
|---|---|---|
| 002 | **Generic Host & DI, in depth**: lifetimes, scopes, `IHostedLifecycleService`, options validation, writing your own `Add…()` extensions | Everything at work sits on this |
| 003 | **Interop in depth**: marshalling rules, `SafeHandle`, strings, arrays, callbacks, `NativeLibrary`, testing native boundaries | Turns your strongest area into expertise |
| 004 | **async in .NET, in depth**: thread pool, `SynchronizationContext`, `ValueTask`, `Channel<T>` patterns, cancellation design | Builds on `concurrency/001` with the .NET specifics |
| 005 | **Data access**: EF Core modeling, migrations, query translation, time-series tables, SQLite on devices, Dapper | The state/value model, generalized |
| 006 | **Testing strategy**: xUnit v3, fakes vs mocks, `WebApplicationFactory`, Testcontainers, testing hosted services and time | Makes you fast *and* safe |
| 007 | **MSBuild, NuGet & solution architecture**: props/targets, Central Package Management, versioning, authoring packages | Removes the last "random folders" mystery |
| 008 | **ASP.NET Core in depth**: middleware authoring, routing, minimal APIs vs controllers, auth, Blazor overview | Connects to `yarp/` |
| 009 | **gRPC & Protocol Buffers**: contract evolution, streaming, deadlines, interceptors | Closes the audit-log ❌ |
| 010 | **Observability in .NET**: `ILogger` → OpenTelemetry, `System.Diagnostics.Metrics`, `ActivitySource` traces | Pairs with `llm_orchistration/018–020` |
| 011 | **Performance**: `Span<T>`, allocations, BenchmarkDotNet, GC modes, `dotnet-counters` / `dotnet-trace` | Senior-level depth |
| 012 | **Shipping on Azure**: Azure DevOps & GitHub Actions YAML, containers, Azure Container Apps / AKS, Key Vault, managed identity | Directly addresses the "zero Azure" resume gap |
| 013 | **PowerShell module engineering**: binary modules, manifests, DI inside modules, dependency isolation | Deepens something you already built |
| 014 | **Architecture patterns in .NET**: layered/clean architecture, vertical slices, CQRS, the Result pattern | For design interviews |

---

## 24. Glossary

| Term | Meaning |
|---|---|
| **apphost** | Native launcher executable next to your `.dll`; equivalent to `dotnet MyApp.dll` |
| **Assembly** | Compiled unit (`.dll`): IL + metadata + manifest |
| **BCL** | Base Class Library: the standard library (`System.*`) |
| **Blittable** | A type whose managed and native memory layouts are identical, so it can be passed without conversion |
| **Boxing** | Copying a value type into a heap object when it's treated as `object` or an interface |
| **Captive dependency** | A longer-lived service holding a shorter-lived one (e.g. singleton → scoped) |
| **CLR / CoreCLR** | The runtime: type loading, JIT, GC, exceptions, interop |
| **Composition root** | The one place where the object graph is wired together: `Program.cs` |
| **Continuation** | The code that runs after an awaited task completes |
| **DI container** | The object (`IServiceProvider`) that creates services and manages their lifetimes |
| **DTO** | Data Transfer Object: a plain data shape for crossing a boundary (API, process, layer) |
| **Entity** | A class EF Core maps to a table row |
| **Generic Host** | `IHost`: the app model providing DI, config, logging, hosted services, and lifetime |
| **Hosted service** | An `IHostedService` the host starts and stops; `BackgroundService` is the common base class |
| **IL / CIL / MSIL** | Intermediate Language: the portable bytecode inside assemblies |
| **IoC (inversion of control)** | The framework owns control flow and calls your code |
| **JIT** | Just-in-time compiler: IL → machine code at run time, per method |
| **Kestrel** | ASP.NET Core's built-in HTTP server |
| **Marshalling** | Converting data between managed and native representations |
| **Middleware** | A component in the ordered ASP.NET Core request pipeline |
| **Migration** | A versioned, generated description of a database schema change (EF Core) |
| **MSBuild** | The build engine that reads `.csproj` files |
| **NuGet** | The .NET package manager and package format (`.nupkg`) |
| **Options pattern** | Binding configuration sections to typed classes (`IOptions<T>`) |
| **ORM** | Object-relational mapper (EF Core) |
| **P/Invoke** | Platform Invocation: calling native functions from .NET |
| **Protobuf** | Protocol Buffers: the binary serialization format used by gRPC |
| **RID** | Runtime Identifier: OS + architecture, e.g. `linux-arm64` |
| **Roslyn** | The C# (and VB) compiler platform |
| **Scope** | A bounded lifetime for scoped services (one per HTTP request, or one you create manually) |
| **SDK-style project** | Modern `.csproj` with `Sdk="…"`, implicit file globbing, and minimal boilerplate |
| **Shared framework** | A runtime-wide set of assemblies installed once (`Microsoft.NETCore.App`, `Microsoft.AspNetCore.App`) |
| **Source generator** | Compiler plugin that writes additional C# during compilation (`LibraryImport`, `LoggerMessage`, JSON) |
| **TFM** | Target Framework Moniker: `net10.0`, `netstandard2.0`… |
| **Thread pool** | The runtime's reusable set of worker threads |
| **Tiered compilation** | Quick Tier-0 JIT first, then optimized Tier-1 for hot methods |
| **Two's complement** | The standard signed-integer encoding: the top bit is negative weight |
| **`UnmanagedCallersOnly`** | Attribute marking a static method as callable directly from native code via a function pointer |

---

*End of Lecture 001. Next: 002, "Generic Host & DI, in depth." Before starting it, finish lab steps 1–8 and be able to answer self-check questions 13–21 without looking.*
