2026_11_01_22_52-(The-Power-Of-PowerShell)

# Lecture 006 — The Power of PowerShell: Objects, .NET, and DI Inside a Module

> **For:** Timothy Lee Grant
> **Date:** 2026-11-01
> **Prerequisites:** Lecture 001 §8 (inversion of control, "who calls my code"), §9 (DI and lifetimes), §14 (PowerShell is .NET). `concurrency/002` helps for §8 here (why two processes can't share objects).
> **Why this lecture:** you want to make a YouTube video about three things you found impressive: objects passing through the pipeline, the whole C# library being available, and dependency injection of your own services into your own cmdlets. You asked for a working example solution in `examples/powershell/` and a lecture so your understanding is solid *before* you record. This lecture walks through exactly what was built, why each piece is shaped the way it is, and what to say on camera.
> **Code:** [`examples/powershell/`](../../examples/powershell/README.md). Status: written and reviewed, **not yet compiled** (no .NET SDK was reachable from the session that wrote it). §12 is your first-build checklist.

---

## Core ideas (the answer key)

1. **A PowerShell pipeline is a chain of method calls inside one process.** Each command's `WriteObject` hands a reference to a .NET object to the next command's parameter binder. A bash pipe is a byte stream between separate processes, through a kernel pipe.
2. **Because objects keep their types, downstream commands ask for properties by name** (`Where-Object`, `Sort-Object`, `Group-Object`, `Measure-Object`, `ConvertTo-Json`). Text is produced only at the very end of the pipeline (`Out-Default`), using format views.
3. **Parameter binding is the glue between commands.** Pipeline input binds either **by value** (the whole object, matched by type) or **by property name** (a property whose name or alias matches a parameter). Exact matches are tried before conversions.
4. **`pwsh` is a .NET application, so every .NET type is reachable:** `[Type]::StaticMember`, `[Type]::new()`, `Add-Type` for C# source or for your own `.dll`. The limit is the runtime `pwsh` runs on: a `net8.0` assembly needs PowerShell 7.4 or later.
5. **A binary module is a class library plus a manifest.** The PowerShell engine, not your code, constructs each cmdlet object and calls `BeginProcessing` → `ProcessRecord` (once per input object) → `EndProcessing`, plus `StopProcessing` on Ctrl+C and `Dispose` at the end.
6. **Cmdlets can't use constructor injection, because the engine creates them.** So the module owns its own composition root (a lazily built `ServiceProvider`), and each cmdlet invocation opens its own DI scope.
7. **Lifetimes become visible:** singletons live as long as the module's container (normally the whole `pwsh` session); scoped services live for one command invocation. A service that depends on a scoped service must itself be scoped (the captive-dependency rule).
8. **The app and the module call the same `AddShowcaseCore()`, but they are two processes with two containers.** They share only what's on disk (JSON files guarded by a cross-process lock), never objects.
9. **When objects cross a process boundary** (`pwsh -c { }`, `Export-Clixml`, remoting), they're serialized into property bags (`Deserialized.*`). Data survives; methods and identity don't.
10. **Three production traps:** a loaded assembly can't be unloaded (rebuild → new `pwsh`); all modules share one assembly load context, so dependency versions can conflict; `-WhatIf` does nothing unless your code calls `ShouldProcess`.

---

## Table of Contents

- [0. Your three claims, checked](#0-your-three-claims-checked)
- [1. The map: what runs where](#1-the-map-what-runs-where)
- [2. Tour of the solution](#2-tour-of-the-solution)
- [3. Objects, not text](#3-objects-not-text)
- [4. Parameter binding: how one command feeds the next](#4-parameter-binding-how-one-command-feeds-the-next)
- [5. The whole .NET library is your standard library](#5-the-whole-net-library-is-your-standard-library)
- [6. Anatomy of the binary module](#6-anatomy-of-the-binary-module)
- [7. Dependency injection inside the module](#7-dependency-injection-inside-the-module)
- [8. The running application, and why the two processes share files](#8-the-running-application-and-why-the-two-processes-share-files)
- [9. Crossing a process boundary](#9-crossing-a-process-boundary)
- [10. Traps](#10-traps)
- [11. Run-of-show for the video](#11-run-of-show-for-the-video)
- [12. First build: checklist and predictions](#12-first-build-checklist-and-predictions)
- [Misconceptions](#misconceptions)
- [Interview relevance](#interview-relevance)
- [Self-check questions](#self-check-questions)
- [Sources](#sources)

---

## 0. Your three claims, checked

All three are right. Each one gets more impressive, and more defensible on camera, when you say it precisely.

| You said | Precise version | The nuance to know before a commenter points it out |
|---|---|---|
| "You can pass objects back and forth themselves." | Inside **one** `pwsh` process, commands pass **references to live .NET objects**. The next command receives the same object, with its type, properties and methods. | Across a **process** boundary (a child `pwsh`, a remote machine, a file) objects are serialized and come back as property bags. §9. |
| "You can use all of the C# libraries that have already been written." | Every type in the .NET base class library, plus any `.dll` you load, is callable from the shell. C# is just one language that compiles to .NET; PowerShell is another way to call the same types. | The assembly must target a runtime `pwsh` can run (§5.4), and two modules that need different versions of the same dependency can collide (§10). |
| "You can use dependency injection to inject your own custom services into your commands." | The module builds a `ServiceProvider` with the **same registration method** your app uses, and every command resolves its services from a fresh scope. | It isn't *constructor* injection: the engine creates cmdlets, so they pull services from the container. §7.4 explains why this is the accepted pattern at framework boundaries. |

---

## 1. The map: what runs where

Start with the layers. Two processes run on your Mac. They never share memory; they share two files.

```
 ┌──────────── process A: dotnet Showcase.App ─────────────┐   ┌──────────── process B: pwsh ──────────────────────────────┐
 │                                                         │   │  PowerShell engine (parser, binder, pipeline, formatter) │
 │  Generic Host                                           │   │         │ creates cmdlet objects, calls their methods     │
 │    └─ SimulationWorker (BackgroundService)              │   │         ▼                                                 │
 │          │ resolves services from                       │   │  Showcase.PowerShell.dll  (your cmdlets)                  │
 │          ▼                                              │   │          │ resolves services from                         │
 │  ServiceProvider #1  ← AddShowcaseCore("app")           │   │          ▼                                                │
 │          │                                              │   │  ServiceProvider #2  ← AddShowcaseCore("pwsh")            │
 │          ▼                                              │   │          ▼                                                │
 │  Showcase.Core.dll  (repository, analyzer, log, …)      │   │  Showcase.Core.dll  (the same code, a second copy in RAM) │
 └──────────────┬──────────────────────────────────────────┘   └──────────────┬────────────────────────────────────────────┘
                │ read/write under a file lock                                │
                ▼                                                             ▼
        ~/.powershell-showcase/devices.json    activity.jsonl    .lock
 ─────────────────────────────── .NET runtime (one per process) ───────────────────────────────
 ─────────────────────────────── macOS kernel: processes, files, flock() ──────────────────────
```

The "who runs it, who calls it" table, which is the question that always unlocks a new system for you:

| Piece | Who starts it | Who calls its code | Lifetime |
|---|---|---|---|
| `Showcase.App` | You, with `dotnet run` | The Generic Host calls `SimulationWorker.ExecuteAsync` | Until Ctrl+C |
| `pwsh` | You, in a terminal | (it's the host) | Your shell session |
| `Showcase.PowerShell.dll` | Loaded by `Import-Module` (via the `.psd1`) | The PowerShell engine: it creates cmdlet objects, sets their parameter properties, and calls `BeginProcessing` / `ProcessRecord` / `EndProcessing` | Loaded until `pwsh` exits (assemblies can't be unloaded) |
| `ServiceProvider #2` | The first command that needs it (`ModuleServices.Provider`) | Your cmdlets and the tab-completer | Until `Remove-Module` or `pwsh` exits |
| `Showcase.Core` services | Each container, on first resolution | The host (app) or the cmdlet (module) | Singleton or scoped, per container |
| `devices.json` | Created by whichever process reads first | Both processes, through `JsonFileDeviceRepository` | On disk until you delete it |

Notice the two composition roots, one per process. This is the same pattern as Lecture 001 §14.3 option 1, now built end to end.

---

## 2. Tour of the solution

🟢 = own it (you'll explain it on camera) · 🔵 = know the contract · ⚫ = black box for now

| File | Tag | Responsibility |
|---|---|---|
| `Directory.Build.props` | 🔵 | Settings every project inherits: `net8.0`, nullable, implicit usings |
| `src/Showcase.Core/Models.cs` | 🟢 | `Device`, `HealthReport`, `ActivityEntry`, `DeviceSample`, enums, `DeviceNotFoundException` |
| `src/Showcase.Core/Abstractions.cs` | 🟢 | The interfaces: `IDeviceRepository`, `IDeviceHealthAnalyzer`, `IDeviceCommandService`, `IActivityLog`, `IDeviceSimulator`, `IOperationContext` |
| `src/Showcase.Core/ServiceCollectionExtensions.cs` | 🟢 | `AddShowcaseCore()`: the one registration method both hosts call |
| `src/Showcase.Core/Storage/*` | 🔵 | JSON file repository, JSON Lines log, cross-process lock, seed data |
| `src/Showcase.Core/Services/*` | 🔵 | Health rules, commands (restart/update), simulator, operation context |
| `src/Showcase.App/Program.cs` | 🟢 | Composition root #1: Generic Host + `AddShowcaseCore` + the worker |
| `src/Showcase.App/SimulationWorker.cs` | 🔵 | Every 2 s: advance the simulation, log events through a fresh scope |
| `src/Showcase.PowerShell/ModuleServices.cs` | 🟢 | Composition root #2: lazy container inside `pwsh`; cleanup on `Remove-Module` |
| `src/Showcase.PowerShell/ShowcaseCmdlet.cs` | 🟢 | Base class: one DI scope per command invocation, disposed by `Dispose` |
| `src/Showcase.PowerShell/Cmdlets/*.cs` | 🟢 | Eight cmdlets (README table) |
| `src/Showcase.PowerShell/DeviceIdCompleter.cs` | 🔵 | Tab completion of live device ids |
| `src/Showcase.PowerShell/Showcase.psd1` | 🟢 | The manifest: what the module is made of and what it exports |
| `Showcase.format.ps1xml` / `Showcase.types.ps1xml` | 🔵 | Default table views; extra members added to `Device` and `HealthReport` |
| `Showcase.Functions.psm1` | 🔵 | `Invoke-ShowcaseAutoHeal`: an advanced function written in PowerShell |
| `src/Showcase.PowerShell/Showcase.PowerShell.csproj` `ExcludeAssets="runtime"` details | ⚫ | NuGet asset flags. Know *why* (don't ship PowerShell's own dll); skip the mechanics |
| `demo/01…05` | 🟢 | One script per video chapter |

The data model, which the rest of the lecture uses:

```csharp
public sealed class Device
{
    public string Id { get; set; } = "";              // "dev-002"
    public string Name { get; set; } = "";            // "Kiln thermocouple"
    public DeviceKind Kind { get; set; }              // TemperatureSensor, PressureSensor, Camera, Gateway
    public string Location { get; set; } = "";
    public DeviceStatus Status { get; set; }          // Online, Degraded, Offline, Maintenance
    public double TemperatureC { get; set; }
    public double CpuPercent { get; set; }
    public int RestartCount { get; set; }
    public DateTimeOffset LastSeen { get; set; }
    public List<string> Tags { get; set; } = new();
    // … FirmwareVersion, NominalTemperatureC, MaintenanceTicksRemaining
}
```

It's a plain class with get/set properties. That one choice is why PowerShell can sort, filter, group, show, serialize and bind it with zero extra code: PowerShell reads .NET properties directly.

The simulated "physics" (so you know what you'll see on camera): Online devices drift back toward their nominal temperature; about 1% of ticks, one starts overheating (Degraded, about +0.8 °C per tick); above 98 °C it may shut itself off (Offline, and `LastSeen` stops moving); a restart puts it in Maintenance for 3 ticks, then the app brings it back Online. `dev-002` starts Degraded at 78 °C, so it becomes Critical within about 10 seconds of starting the app: that's your built-in drama.

---

## 3. Objects, not text

### 3.1 What a bash pipe actually is

`ps -Ao pid,rss,comm | sort -k2 -nr | head -5` starts **three processes**. The shell asks the kernel for two pipes (`pipe()`), connects `ps`'s stdout to the first and `sort`'s stdin to its other end, and so on. What travels is **bytes**. `sort` doesn't know there's a "memory" field; it was told "field 2, numeric." The structure lived inside `ps`, was flattened to text, and every downstream tool re-derives it by position. That contract (column 2 = RSS, units = KB, separator = spaces) is written nowhere a compiler can check.

### 3.2 What a PowerShell pipeline actually is

`Get-ShowcaseDevice | Where-Object TemperatureC -gt 60 | Sort-Object TemperatureC` runs in **one process**, `pwsh`. The engine builds a list of three command objects and wires each one's output to the next one's input. When `Get-ShowcaseDevice` calls `WriteObject(device)`, the engine hands **that same object reference** to `Where-Object`, which reads `device.TemperatureC` (a `double`) and compares numbers. No text, no parsing, no column positions.

| | bash pipe | PowerShell pipeline |
|---|---|---|
| Unit that travels | Bytes | .NET object references |
| Commands are | Separate processes | Objects inside one process |
| Connection | Kernel pipe (a byte buffer) | Method calls made by the engine |
| Structure is recovered by | Each tool, by position and parsing | Nobody: it was never lost |
| Types | Everything is text | `double`, `DateTimeOffset`, enums, your classes |
| When text appears | Always | At the end, when the console needs to show something (§3.5) |

### 3.3 Trace one real pipeline

Say this one out loud on camera; it's the heart of the video:

```powershell
Test-ShowcaseDeviceHealth -ProblemsOnly | Where-Object Grade -eq Critical | Restart-ShowcaseDevice -WhatIf
```

1. **The parser** turns the line into three command invocations.
2. **The engine** finds each command: two are your cmdlet classes (from the module), one is built in. It **creates an object** for each (`new TestShowcaseDeviceHealthCommand()`, …) and binds the *command-line* parameters: `ProblemsOnly = true`, `WhatIf = true`.
3. **`BeginProcessing` runs on all three, left to right.** In your two cmdlets that's where the DI scope is created (§7).
4. `Test-ShowcaseDeviceHealth` has no pipeline input, so its **`ProcessRecord` runs once**. It loads devices through `IDeviceRepository`, analyzes each, and calls `WriteObject(report)` for every non-healthy `HealthReport`.
5. **Each `WriteObject` immediately passes that report downstream.** `Where-Object` runs its `ProcessRecord` with `$_` = the report and checks `$_.Grade -eq 'Critical'` (an enum comparison).
6. If it matches, `Where-Object` writes it on. **The binder** looks at the `HealthReport` and at `Restart-ShowcaseDevice`'s parameters: `-Id` accepts pipeline input *by property name*, and has the alias `DeviceId`; the report has a `DeviceId` property. So `Id = report.DeviceId` (§4).
7. `Restart-ShowcaseDevice.ProcessRecord` runs **once for this report**. It calls `ShouldProcess("dev-002", "Restart device")`. Because of `-WhatIf`, that prints `What if: Performing the operation "Restart device" on target "dev-002".` and returns `false`, so nothing changes.
8. Steps 5–7 repeat for each report (**streaming**: report 1 can be fully restarted before report 2 is even computed).
9. **`EndProcessing` runs on all three, left to right**, then the engine calls `Dispose` on each command that implements `IDisposable` (yours do: that's where the scope dies).

### 3.4 Streaming, and stopping upstream

```powershell
Watch-ShowcaseDevice | Where-Object TemperatureC -gt 80 | Select-Object -First 1
```

`Watch-ShowcaseDevice` is an infinite loop: sample, `WriteObject`, sleep 2 s, repeat. It still finishes. When `Select-Object -First 1` has its one object, it tells the engine to stop the commands upstream; the next `WriteObject` inside `Watch` throws an internal "stop" exception, the loop ends, and `Dispose` still runs. In bash, `head -1` closes its pipe and the producer dies of `SIGPIPE` on its next write: similar idea, but done by the kernel with a signal instead of by the engine with an exception.

Ctrl+C is the third way out: the engine calls `StopProcessing()` **on another thread**. That's why `Watch` sleeps with `_stop.Token.WaitHandle.WaitOne(interval)` instead of `Thread.Sleep`: it can be woken immediately.

### 3.5 Text happens at the end

Every pipeline you type at the prompt has an invisible last command, `Out-Default`. Only there does PowerShell decide how an object should look: it checks whether a **format view** exists for the type (`Showcase.format.ps1xml` defines one for `Showcase.Core.Device`), otherwise it picks a table or list of properties. The colors in the Status column are a script in that view; the object's `Status` is still the enum value.

Two consequences worth a sentence each in the video:
- `Get-ShowcaseDevice | Get-Member` shows **all** the properties: the table showing seven columns was only a view.
- `Format-Table` produces formatting objects, not your objects. Put it **last**: `Get-ShowcaseDevice | Format-Table | Sort-Object Name` sorts formatting records, which is nonsense.

---

## 4. Parameter binding: how one command feeds the next

### 4.1 Two ways a piped object can bind

| Mode | Attribute | Meaning | Example in this solution |
|---|---|---|---|
| **By value** | `ValueFromPipeline = true` | "Give me the **whole object**, if its type fits my parameter." | `Get-ShowcaseDevice \| Test-ShowcaseDeviceHealth`: the `Device` binds to `-InputObject` (type `Device`) |
| **By property name** | `ValueFromPipelineByPropertyName = true` | "Look **inside** the object for a property with my name (or one of my aliases) and give me its value." | `HealthReport.DeviceId` → `Restart-ShowcaseDevice -Id` (alias `DeviceId`); a CSV row's `Location` column → `Set-ShowcaseDevice -Location` |

The aliases are the trick that makes different types chain together. Your `Device` calls its key `Id`; your `HealthReport` calls it `DeviceId`. One `[Alias("DeviceId")]` on every `-Id` parameter, and both types flow into every command.

### 4.2 The order the binder tries

For each object arriving from the pipeline, the binder tries, and stops at the first success:

1. **By value, exact type** (no conversion).
2. **By property name, exact type.**
3. **By value, with conversion** (e.g. a string converted to an enum).
4. **By property name, with conversion.**

What each step means in practice: an object that *is* what a parameter wants always wins over an object that merely *contains* something usable. That's why piping a live `Device` into `Test-ShowcaseDeviceHealth` picks `-InputObject` (step 1), while piping a `HealthReport` picks `-Id` through its `DeviceId` (step 2: a `HealthReport` isn't a `Device`).

This also chooses the **parameter set**. `Test-ShowcaseDeviceHealth` has three sets (`All`, `InputObject`, `ById`); the set that can accept the incoming object is the one that runs.

### 4.3 Predict before you run

Write your prediction in the middle column, then run each one with `Trace-Command -Name ParameterBinding -PSHost -Expression { … }` to see the binder narrate its choices.

| Pipeline | Your prediction: which parameter, which step? | Result |
|---|---|---|
| `Get-ShowcaseDevice \| Test-ShowcaseDeviceHealth` | | |
| `Test-ShowcaseDeviceHealth \| Get-ShowcaseDevice` | | |
| `'dev-001','dev-004' \| Get-ShowcaseDevice` | | |
| `Get-ShowcaseDevice dev-002 \| Get-ShowcaseActivity` | | |
| `Import-Csv updates.csv \| Set-ShowcaseDevice -WhatIf` (which columns bind? what converts `"thermal;priority"`?) | | |
| `Import-Clixml fleet.clixml \| Test-ShowcaseDeviceHealth` (these aren't `Device` objects any more, §9) | | |

<details><summary>Answers</summary>

1. `-InputObject`, step 1 (by value, exact type `Device`).
2. `-Id` through alias `DeviceId`, step 2. (`-Id` also takes pipeline input by value, but a `HealthReport` isn't a string; step 2 wins before conversion is tried.)
3. `-Id`, by value: each string is a `string`, and `-Id` is `string[]`, so each string binds as a one-element array.
4. `-DeviceId` through its alias `Id`: the `Device`'s `Id` property, step 2.
5. `Id` → `-Id`, `Location` → `-Location`, `Tags` → `-Tag` (alias `Tags`). The cell is one string; PowerShell wraps it into a one-element `string[]`, and *your* C# code splits it on `;`. Empty cells are treated as "leave unchanged" by your code.
6. Not `-InputObject` by exact type. `Trace-Command` will show whether it lands on `-Id` (by property name) or on `-InputObject` through conversion of the property bag into a new `Device`. Either way it works, which is the point of §9. Record what you see; it's a good on-camera moment.

</details>

---

## 5. The whole .NET library is your standard library

### 5.1 The syntax, in one table

| You want | C# | PowerShell |
|---|---|---|
| A static member | `Math.Sqrt(2)` | `[math]::Sqrt(2)` |
| A new object | `new Queue<int>()` | `[System.Collections.Generic.Queue[int]]::new()` |
| Shorter type names | `using System.Text;` | `using namespace System.Text` (first line of the script) |
| An instance method | `sb.AppendLine("x")` | `$sb.AppendLine('x')` |
| Object initializer | `new Device { Id = "x" }` | `[Showcase.Core.Device]@{ Id = 'x' }` |
| Compile C# right now | (a project) | `Add-Type -TypeDefinition @' … '@` |
| Load a `.dll` | (a reference) | `Add-Type -Path ./Showcase.Core.dll` |

`demo/02-dotnet-everywhere.ps1` walks through each. The one-liners that land well on camera: `[Convert]::ToHexString([System.Security.Cryptography.SHA256]::HashData($bytes))` (a SHA-256 with no tool installed) and `[System.Runtime.InteropServices.RuntimeInformation]::FrameworkDescription` (the shell tells you which .NET it is).

### 5.2 The strongest demo: your business logic with no cmdlets at all

```powershell
Add-Type -Path ./out/Showcase/Showcase.Core.dll
$analyzer = [Showcase.Core.Services.DeviceHealthAnalyzer]::new([Showcase.Core.ShowcaseOptions]::new(), [TimeProvider]::System)
$probe    = [Showcase.Core.Device]@{ Id = 'dev-999'; Name = 'Bench probe'; Status = 'Online'; TemperatureC = 91; LastSeen = [DateTimeOffset]::UtcNow }
$analyzer.Analyze($probe)
```

What happened, step by step:
1. `Add-Type -Path` loads the assembly into the `pwsh` process. Its public types are now resolvable by name.
2. `::new(...)` calls the C# constructor. You did the dependency injection **by hand**: you passed the options and the clock. That's what a container automates.
3. The hashtable cast calls `Device`'s parameterless constructor, then sets each property. `'Online'` is converted to `DeviceStatus.Online`.
4. `Analyze` runs your C# rules and returns a `HealthReport`, which displays through your format view.

This is the moment to say: *a cmdlet is just a convenient front door; the logic was always ordinary .NET.*

### 5.3 How PowerShell "sees" a .NET object: the Extended Type System

PowerShell wraps every object in a `PSObject`. The wrapper exposes the real .NET members and can **add** members that the class doesn't have. `Showcase.types.ps1xml` adds:

```xml
<ScriptProperty>
  <Name>SecondsSinceSeen</Name>
  <GetScriptBlock>[math]::Round(([DateTimeOffset]::UtcNow - $this.LastSeen).TotalSeconds, 1)</GetScriptBlock>
</ScriptProperty>
```

So `Get-ShowcaseDevice | Select-Object Id, SecondsSinceSeen, IsHot` works, although `Device` (C#) has neither property. `Get-Member` lists them as `ScriptProperty`. Meaning: *the shell can extend types it didn't compile.* That's also how built-in types get friendly extras (for example, the extra properties you see on a `FileInfo` from `Get-ChildItem` that the .NET class doesn't define).

### 5.4 The real limit: the runtime inside `pwsh`

Your assembly runs **inside `pwsh`'s .NET runtime**. The solution targets `net8.0` on purpose:

| PowerShell | Runs on | Can load a `net8.0` assembly? |
|---|---|---|
| 7.4 | .NET 8 | Yes |
| 7.5 | .NET 9 | Yes (newer runtime, older target) |
| 7.6 (current LTS, released 2026-03-18) | .NET 10 | Yes |
| Windows PowerShell 5.1 | .NET Framework 4.x | No (that's why the manifest says `CompatiblePSEditions = @('Core')`) |

Target the **oldest** runtime you want to support, never the newest.

---

## 6. Anatomy of the binary module

### 6.1 The manifest is the front door

`Import-Module ./out/Showcase/Showcase.psd1` reads the manifest first. The fields that matter:

| Key | Value here | Meaning |
|---|---|---|
| `RootModule` | `Showcase.PowerShell.dll` | The assembly whose cmdlet classes become commands |
| `RequiredAssemblies` | `Showcase.Core.dll` | Loaded before anything else, so the functions in the `.psm1` can use `[Showcase.Core.HealthGrade]` |
| `NestedModules` | `Showcase.Functions.psm1` | A script module loaded alongside: advanced functions |
| `PowerShellVersion` / `CompatiblePSEditions` | `7.4` / `Core` | Refuse to load where the dll can't run |
| `FormatsToProcess` / `TypesToProcess` | the two `.ps1xml` | Views, and extra members |
| `CmdletsToExport` / `FunctionsToExport` | explicit lists | The public surface; also lets `Get-Command` list commands without loading the dll |

`dotnet publish -o out/Showcase` puts the dll, its dependencies (`Showcase.Core.dll`, `Microsoft.Extensions.DependencyInjection*.dll`) and these text files into **one folder. That folder is the module.**

### 6.2 A cmdlet's life

```
engine: new RestartShowcaseDeviceCommand()      ← parameterless constructor, called by the engine
engine: set Id / PassThru / WhatIf from the command line
engine: BeginProcessing()                       ← once        (your base class: create DI scope)
engine: for each piped object:
            bind pipeline parameters (Id)
            ProcessRecord()                     ← once per input object
engine: EndProcessing()                         ← once, if the pipeline wasn't stopped
engine: StopProcessing()                        ← only on Ctrl+C, from another thread
engine: Dispose()                               ← always, if you implement IDisposable (your base class: dispose scope)
```

The engine is the framework; your class is called (Lecture 001 §8's inversion of control, again).

### 6.3 What you get for free from attributes

| You write | You get |
|---|---|
| `[Cmdlet(VerbsLifecycle.Restart, "ShowcaseDevice", SupportsShouldProcess = true)]` | The name `Restart-ShowcaseDevice`, plus `-WhatIf` and `-Confirm` |
| `[Parameter(Mandatory = true)]` | A prompt if it's missing |
| An enum-typed parameter (`DeviceStatus[]? Status`) | Validation, string conversion and Tab completion of the enum names |
| `[ValidateSet("app","pwsh")]`, `[ValidateRange(1, 100_000)]` | Validation and a clear error before your code runs |
| `[SupportsWildcards]` + `WildcardPattern` | `-Name *cam*` |
| `[ArgumentCompleter(typeof(DeviceIdCompleter))]` | Tab completion computed live from `devices.json` |
| `[Alias("DeviceId")]` | A second name for binding and typing |
| Common parameters | `-Verbose`, `-ErrorAction`, `-ErrorVariable`, `-OutVariable`, … on every cmdlet, with no code |

The verb comes from the approved list (`Get-Verb`). `Watch`, `Restart` and `Test` are all approved.

### 6.4 `-WhatIf` only works if you ask

```csharp
if (!ShouldProcess(id, "Restart device"))
{
    continue;
}
```

`SupportsShouldProcess = true` only *adds* the parameters. `ShouldProcess` is the call that prints "What if: …" or asks "Are you sure?" and returns `false` when you must not act. Forget the call and `-WhatIf` silently does the real thing. That's a common bug in real modules and a good teaching line.

`Invoke-ShowcaseAutoHeal` shows the same thing in PowerShell: `$PSCmdlet.ShouldProcess(...)`, and then `-Confirm:$false` on the inner `Restart-ShowcaseDevice`, so the user isn't asked twice.

### 6.5 Errors are objects too

| Call | Kind | Effect |
|---|---|---|
| `WriteError(new ErrorRecord(ex, "DeviceNotFound", ErrorCategory.ObjectNotFound, id))` | **Non-terminating** | Reports this item and keeps going. `Get-ShowcaseDevice -Id dev-001, nope, dev-003` returns two devices and one error |
| `ThrowTerminatingError(...)` | **Terminating** | Stops this command |

The caller decides: `-ErrorAction Stop` turns non-terminating errors into exceptions, and `catch [Showcase.Core.DeviceNotFoundException]` catches **your C# exception type** by name. `$missing[0].Exception.DeviceId` reads a property you defined on that exception.

---

## 7. Dependency injection inside the module

### 7.1 Why there's no constructor injection

In `Showcase.App`, the Generic Host constructs `SimulationWorker` **through the container**, so its constructor can ask for `IDeviceRepository`, `IServiceScopeFactory` and the rest. In `pwsh`, the **engine** constructs your cmdlets, with a parameterless constructor, and it knows nothing about your container. Nothing calls a constructor with your services. So the direction flips: the cmdlet asks the container.

That leaves two questions, which the next two sections answer in code: *where does the container come from*, and *how do lifetimes stay correct when the cmdlet asks for services itself?*

### 7.2 Composition root #2: `ModuleServices`

```csharp
public static class ModuleServices
{
    private static readonly object Gate = new();
    private static ServiceProvider? _provider;

    public static IServiceProvider Provider
    {
        get { lock (Gate) { return _provider ??= Build(); } }   // built on first use
    }

    private static ServiceProvider Build()
    {
        var services = new ServiceCollection();
        services.AddShowcaseCore(options => options.SourceName = "pwsh");   // same call as the app
        services.AddSingleton<ModuleSession>();                              // module-only service
        return services.BuildServiceProvider(new ServiceProviderOptions
        {
            ValidateScopes = true,   // resolving a scoped service from the root throws
            ValidateOnBuild = true,  // a registration that can't be constructed throws now
        });
    }
}

public sealed class ModuleCleanup : IModuleAssemblyCleanup
{
    public void OnRemove(PSModuleInfo psModuleInfo) => ModuleServices.Reset();   // Remove-Module → dispose the container
}
```

Three decisions to be able to defend:

1. **Lazy, not at import.** Lecture 001 §14.3 mentioned `IModuleAssemblyInitializer.OnImport`. Microsoft's binary-module docs advise using it only when necessary and prefer lazy initialization: import stays fast, and a container problem shows up when a command runs, with a normal error.
2. **The same `AddShowcaseCore()`.** The module doesn't re-implement anything. If you add a service to Core and register it there, both hosts get it.
3. **Validation on.** `ValidateScopes` and `ValidateOnBuild` are on by default in the Generic Host's Development environment; a hand-built container must ask for them.

### 7.3 One scope per command invocation: `ShowcaseCmdlet`

```csharp
public abstract class ShowcaseCmdlet : PSCmdlet, IDisposable
{
    private IServiceScope? _scope;

    protected T Get<T>() where T : notnull => Services.GetRequiredService<T>();

    protected sealed override void BeginProcessing()
    {
        _scope = ModuleServices.Provider.CreateScope();
        var operation = Get<IOperationContext>();
        Get<ModuleSession>().OnCommandStarted(operation.OperationId);
        WriteVerbose($"{MyInvocation.MyCommand.Name}: new DI scope, operation {operation.OperationId}");
        Begin();
    }

    public void Dispose() { Dispose(true); GC.SuppressFinalize(this); }

    protected virtual void Dispose(bool disposing)
    {
        if (disposing) { _scope?.Dispose(); _scope = null; }
    }
}
```

Trace: what happens when you run `Restart-ShowcaseDevice dev-002`:

1. The engine creates `RestartShowcaseDeviceCommand` (parameterless constructor) and sets `Id = ["dev-002"]`.
2. `BeginProcessing` (sealed in the base class) asks `ModuleServices.Provider`. First command of the session? Then the container is built now.
3. `CreateScope()` makes a **new scope**. Resolving `IOperationContext` creates a new `OperationContext` with a new `Guid`.
4. `ModuleSession` (singleton) is resolved: the same instance every time. It records the command.
5. `ProcessRecord` calls `Get<IDeviceCommandService>()`. The scope creates `DeviceCommandService`, which needs `IDeviceRepository` (singleton: reused) and `IActivityLog` (scoped: created now, receiving **this scope's** `IOperationContext`).
6. `Restart` updates `devices.json` under the lock and appends to `activity.jsonl` with `Source = "pwsh"` and this operation's id.
7. The pipeline ends. The engine calls `Dispose`, which disposes the scope and everything scoped that it created.

Why `Dispose` and not `EndProcessing`? `EndProcessing` is skipped when the pipeline stops early (`Select-Object -First`, Ctrl+C, a terminating error). `Dispose` always runs.

### 7.4 Isn't this the service-locator anti-pattern?

Honest answer: the base class *is* a service locator. The anti-pattern is calling a locator from deep inside business code, which hides dependencies and makes classes hard to test. Here the locator appears in exactly **one** place, at a framework boundary where constructor injection is impossible, and everything below it (`DeviceCommandService`, `JsonLinesActivityLog`, …) uses normal constructor injection. ASP.NET Core does the same thing internally when it creates controllers. Say it that way if a commenter raises it.

### 7.5 Lifetimes in this solution

| Service | Lifetime | Why this lifetime | One instance per… |
|---|---|---|---|
| `ShowcaseOptions` | Singleton (instance) | Configuration doesn't change | container |
| `TimeProvider` | Singleton | `TimeProvider.System` is stateless; injecting it lets tests pass a fake clock | container |
| `IDeviceRepository` | Singleton | No per-call state; the file is the state | container |
| `IDeviceHealthAnalyzer`, `IDeviceSimulator` | Singleton | Pure logic | container |
| `IOperationContext` | **Scoped** | "One unit of work" is exactly what a scope means | command invocation (pwsh), logging tick (app) |
| `IActivityLog` | **Scoped** | It depends on `IOperationContext` | same |
| `IDeviceCommandService` | **Scoped** | It depends on `IActivityLog` | same |
| `ModuleSession` | Singleton (module only) | Session-wide counters | container |

The **captive-dependency rule** shaped the bottom half of that table: if `IActivityLog` were a singleton, it would be created once with the first scope's `IOperationContext` and keep that `Guid` forever. Scoped-ness flows upward to everything that depends on a scoped service. With `ValidateScopes = true`, resolving a scoped service from the root container throws instead of silently misbehaving.

`demo/04-dependency-injection.ps1` makes the table visible:

```powershell
Get-ShowcaseSession; Get-ShowcaseDevice | Out-Null; Get-ShowcaseSession
```

`CreatedAt` and `ProcessId` don't change (singleton). `CommandsRun` goes up and `LastOperationId` changes (new scope per command).

This is also the cleanest on-camera proof of your first claim, that the pipeline passes **live objects, not copies**:

```powershell
$first  = Get-ShowcaseSession
Get-ShowcaseDevice | Out-Null
$second = Get-ShowcaseSession
[object]::ReferenceEquals($first, $second)   # True
$first.CommandsRun                           # shows the NEW count
```

`$first` and `$second` are two variables holding a reference to the **same** singleton in the module's container. Contrast with `Get-ShowcaseDevice`, which returns fresh objects each time because the repository deserializes the file on every call (§10, "snapshot surprise"). Whether you get a shared object or a fresh one is decided by the service, not by the pipeline.

And:

```powershell
Get-ShowcaseDevice -Id dev-003, dev-006 | Restart-ShowcaseDevice -Confirm:$false
Get-ShowcaseActivity -Last 4
```

Both restart entries share **one** operation id: one `Restart-ShowcaseDevice` invocation, one scope, two `ProcessRecord` calls.

### 7.6 The one place that uses the root container

`DeviceIdCompleter` runs while you press Tab, **outside** any command invocation, so there's no scope. It resolves only `IDeviceRepository`, a singleton, from the root. Resolving a scoped service there would throw (`ValidateScopes`), which is correct.

---

## 8. The running application, and why the two processes share files

### 8.1 The app is the same pattern in its natural habitat

```csharp
var builder = Host.CreateApplicationBuilder(args);
builder.Services.AddShowcaseCore(options => options.SourceName = "app");
builder.Services.AddHostedService<SimulationWorker>();
using var host = builder.Build();
await host.RunAsync();
```

`SimulationWorker` is a hosted service, which is a **singleton**, so it can't take `IActivityLog` (scoped) in its constructor. It takes `IServiceScopeFactory` and opens a short scope when a tick produces events. A cmdlet opening a scope per invocation and a worker opening a scope per tick are the same idea: **a scope is one unit of work**, and the host decides what a unit is.

### 8.2 Why not just share the objects?

Because the app and `pwsh` are separate processes, each with its own virtual address space (`concurrency/002`). A `Device` object in the app's memory has an address that means nothing in `pwsh`. Two containers, two copies of `Showcase.Core.dll` in RAM, two sets of singletons. The only shared thing is what you deliberately put outside both processes: the files.

Two details in `Showcase.Core/Storage` make the files safe to share:

| Problem | Fix in the code |
|---|---|
| The app's tick and your `Restart` both do read-modify-write: one can overwrite the other's change | `Update(change)` holds a **cross-process lock** for the whole read-modify-write. `CrossProcessLock` opens `.lock` with `FileShare.None`; on macOS/Linux .NET implements that with an advisory `flock()`, so a second .NET process gets an `IOException` and retries |
| A reader might see a half-written file | Write `devices.json.tmp`, then rename it over `devices.json`. A rename within one file system replaces the file in one step |

(A C# `lock` statement wouldn't help: it only coordinates threads inside one process.)

### 8.3 Other ways to connect a shell to a running app (honest sizing)

| Option | How | Good for | Cost |
|---|---|---|---|
| **Shared files + lock** (this solution) | Both load Core and touch the same files | Demos, local tools, small state | Doesn't scale; polling, not push |
| **Thin client** | Cmdlets call the app's HTTP or gRPC API | Real services, remote machines | You maintain an API; cmdlet output is DTOs from the wire |
| **Named pipes / sockets** | Custom protocol between the two | Low-latency local control | You design and version the protocol |
| **Host PowerShell inside the app** | The app references `Microsoft.PowerShell.SDK` and runs scripts in-process, passing its *live* objects in | Scriptable apps, admin consoles | Big dependency; you own the security of running scripts |

For the video, the first option is right: everything is visible in two terminals. Mention the second as "how you'd do it in production," and the fourth as a teaser: it's the only way to get real object-passing between your app and PowerShell, because then they're the same process.

---

## 9. Crossing a process boundary

`demo/05-bonus.ps1` §5.4 shows what happens when objects leave the process:

```powershell
$remote = pwsh -NoProfile -Command { Get-Process -Id $PID | Select-Object Name, Id, StartTime }
$remote.PSObject.TypeNames      # Deserialized.Selected.System.Diagnostics.Process …

Get-ShowcaseDevice | Export-Clixml ./fleet.clixml
(Import-Clixml ./fleet.clixml)[0].PSObject.TypeNames[0]   # Deserialized.Showcase.Core.Device
```

Passing a script block to `pwsh` makes the child serialize its output as CLIXML and the parent rebuild it. The same mechanism carries objects over PowerShell remoting. What comes back:

| Survives | Doesn't survive |
|---|---|
| Property values; primitive types (`int`, `double`, `DateTime`, `Guid`, strings, enums as values); nested objects up to a depth | Methods (no `.Kill()` on a deserialized process); the live connection to the real thing; object identity |
| The original type name, prefixed with `Deserialized.` | Being *the* type: it's now a property bag, not a `Device` |

So the precise version of your claim is: **objects pass natively within a process; between processes, PowerShell still keeps the structure (unlike text), but as data.** That's still far better than text: `Import-Clixml fleet.clixml | Test-ShowcaseDeviceHealth` works because binding by property name doesn't care about the type, only the property names (§4.3, prediction 6).

---

## 10. Traps

| Trap | Symptom | Why | What to do |
|---|---|---|---|
| **Assemblies can't be unloaded** | You rebuild, re-import, and still see old behavior | .NET can't unload an assembly from the default load context; `Import-Module -Force` doesn't replace a loaded dll | New `pwsh` after every build. `build.ps1` warns you |
| **Dependency conflicts** | "Could not load file or assembly 'X, Version=…'" | PowerShell loads all modules into one shared assembly load context: one version of each assembly name per process. Whichever module loads first wins | Pin a version PowerShell already ships, or isolate dependencies in a custom `AssemblyLoadContext` (Microsoft's documented pattern) |
| **Wrong target framework** | The module fails to import on an older `pwsh` | The dll targets a newer runtime than `pwsh` runs on | Target the oldest runtime you support (`net8.0` here) |
| **`-WhatIf` that isn't** | `-WhatIf` performs the action | `SupportsShouldProcess` without a `ShouldProcess` call | Call `ShouldProcess` before every change |
| **Formatting too early** | `… \| Format-Table \| Sort-Object` gives garbage | `Format-*` emits formatting records | `Format-*` last, or not at all |
| **Snapshot surprise** | `$d.Location = 'X'` doesn't change the device | `Get-ShowcaseDevice` returns fresh objects deserialized from disk | Change state through a command (`Set-ShowcaseDevice`) |
| **Scope leaks** | Scoped services never disposed after `Select-Object -First` | `EndProcessing` isn't called when the pipeline stops early | Dispose in `IDisposable.Dispose` (done in the base class) |
| **CSV empty cells** | An empty `Status` cell fails conversion | `""` isn't a valid enum name | Leave columns out instead of blank (the demo CSV has no `Status` column) |

---

## 11. Run-of-show for the video

Two terminals side by side: left = `dotnet run --project src/Showcase.App -c Release`, right = `pwsh`. About 12–15 minutes.

| # | Chapter | Show | The line to say |
|---|---|---|---|
| 1 | Cold open (30 s) | `Test-ShowcaseDeviceHealth -ProblemsOnly \| Restart-ShowcaseDevice`, and the left terminal reacting | "One line in the shell, a real app reacts. Here's why this is possible." |
| 2 | Objects, not text (3 min) | bash `ps \| sort -k2` vs `Get-Process \| Sort-Object WorkingSet64`; `Get-Member`; same objects → table, JSON, CSV | "Bash pipes bytes between processes. PowerShell passes objects between commands in one process." |
| 3 | .NET is the standard library (2 min) | `RuntimeInformation`, SHA-256, `HashSet` with a comparer, `Add-Type` C#; then load `Showcase.Core.dll` and call the analyzer | "A cmdlet is a front door. The logic is ordinary .NET, and the shell can call it directly." |
| 4 | My own commands (3 min) | `Get-ShowcaseDevice`, Tab completion, `Where/Group/Measure` on your objects, `Import-Csv \| Set-ShowcaseDevice -WhatIf`, `Watch … \| Select -First 1` | "Built-in commands work on my types with zero extra code, because they're just properties." |
| 5 | How binding works (2 min) | `Get-ShowcaseDevice \| Test-…` (by value), `Test-… \| Restart-…` (by property name, alias) with `Trace-Command` | "The output of one command *is* the input of the next: by type, or by property name." |
| 6 | DI inside the module (3 min) | `ModuleServices.cs`, `ShowcaseCmdlet.cs`; `Get-ShowcaseServiceRegistration`; `Get-ShowcaseSession` twice; operation ids in the activity log | "The engine creates cmdlets, so each command opens its own DI scope from the module's container, built by the same `AddShowcaseCore()` as the app." |
| 7 | Honest limits (1 min) | `pwsh -c { … }` → `Deserialized.*`; can't unload dlls | "Objects are live inside one process; across processes they travel as data. Still not text." |
| 8 | Close | `Invoke-ShowcaseAutoHeal -WhatIf` | "And PowerShell functions can do everything a compiled cmdlet can." |

Rehearsal tip: run each demo script top to bottom once off camera, because the fleet is random. If `dev-002` has already gone offline by chapter 4, that's fine: it's a better story for `Restart-ShowcaseDevice`. To start fresh: stop the app, `Remove-Item ~/.powershell-showcase -Recurse`, start it again.

---

## 12. First build: checklist and predictions

The code was written without a .NET SDK, so treat the first build as a lab.

**Step 1, prerequisites.** `dotnet --list-sdks` (8.0 or later) and `pwsh --version` (7.4 or later; `brew install --cask powershell` on macOS).

**Step 2, build.** From `examples/powershell`: `pwsh ./build.ps1`. If the compiler complains, the most likely spots (in order of my uncertainty):

| Spot | Why it might complain | Fix |
|---|---|---|
| `Showcase.PowerShell.csproj`: `ExcludeAssets="runtime"` on `System.Management.Automation` | NuGet asset flags | If the build fails or `out/Showcase` lacks something PowerShell-related it needs, remove `ExcludeAssets="runtime"` (extra PowerShell dlls in the folder are harmless) |
| Package versions (`System.Management.Automation 7.4.6`, `Microsoft.Extensions.DependencyInjection 8.0.1`, `…Abstractions 8.0.2`, `Microsoft.Extensions.Hosting 8.0.1`) | A version may be unavailable in your feed | Use the nearest available 7.4.x / 8.0.x |
| Nullable warnings | Warnings, not errors | Ignore, or fix for practice |

**Step 3, predict, then run.** Fill in the middle column first.

| Action | Your prediction | Result |
|---|---|---|
| `Get-ChildItem out/Showcase`: which dlls are there? | | |
| Start the app, wait 20 s, `Test-ShowcaseDeviceHealth`: which devices are not Healthy, and why? | | |
| `Restart-ShowcaseDevice dev-007 -WhatIf`, then `Get-ShowcaseActivity -Last 3`: did anything get logged? | | |
| `Restart-ShowcaseDevice dev-007`, wait 8 s, `Get-ShowcaseDevice dev-007`: status? | | |
| Stop the app, wait 40 s, `Test-ShowcaseDeviceHealth`: what new finding appears? | | |
| `Get-ShowcaseSession` before and after three other commands: what changes? | | |
| Rebuild while the module is imported, re-import, check behavior: old or new code? | | |

<details><summary>Expected results</summary>

1. `Showcase.PowerShell.dll`, `Showcase.Core.dll`, `Microsoft.Extensions.DependencyInjection.dll`, `Microsoft.Extensions.DependencyInjection.Abstractions.dll`, the `.deps.json`, plus `.psd1`, `.psm1`, two `.ps1xml`. Possibly some PowerShell dlls if `ExcludeAssets` didn't apply transitively: harmless.
2. `dev-002` (Degraded, temperature rising past 70 then 85 → Warning then Critical) and `dev-007` (Offline → Critical). Others are Healthy unless the 1% fault fired.
3. Nothing: `ShouldProcess` returned false before `IDeviceCommandService.Restart` was called, so nothing was logged.
4. `Online` (Maintenance for 3 ticks × 2 s, then the app's simulator brings it back) and a `pwsh` "Restart" entry followed by an `app` "Online" entry in the activity log.
5. "No update for …s (is Showcase.App running?)" on every device that isn't Offline (`LastSeen` stopped moving; `StaleAfter` is 30 s).
6. `CommandsRun` +4 (the three, plus the second `Get-ShowcaseSession` itself), new `LastOperationId`; `CreatedAt` and `ProcessId` unchanged.
7. Old code. The loaded assembly stays loaded until `pwsh` exits.

</details>

---

## Misconceptions

| You might think | Reality | Why |
|---|---|---|
| "PowerShell pipes objects the way bash pipes text, through the OS" | Commands in a pipeline are objects in one process; the engine calls them | No kernel pipe is involved between cmdlets |
| "The table I see is the object" | The table is a view chosen at `Out-Default` | `Get-Member` shows the full object |
| "The cmdlet's constructor can take my services" | The engine calls a parameterless constructor | The container doesn't create cmdlets, so they pull from it |
| "One container serves the app and the shell" | Two processes, two containers, same registration code | Containers live in a process's memory |
| "`Import-Module -Force` reloads my new dll" | The old assembly stays loaded | Default load context can't unload |
| "Objects keep their type when they come back from another `pwsh`" | They come back `Deserialized.*` | Serialization keeps data, not behavior |
| "`SupportsShouldProcess` makes `-WhatIf` safe" | Only `ShouldProcess()` does | The attribute adds parameters; the call enforces them |
| "Scoped means per pipeline" | Per command invocation (each command in a pipeline has its own scope) | The scope is created in that command's `BeginProcessing` |

---

## Interview relevance

- **Windows and platform roles use PowerShell daily** for test automation, lab setup and diagnostics. Being able to say *why* objects beat text, and to write a cmdlet with `ShouldProcess`, sets you apart from "I can run scripts."
- **"How would you expose this service to operators?"** is a design question with a good answer here: a binary module reusing the service's registrations, or a thin client over an API. Have §8.3 ready.
- **DI lifetimes and captive dependencies** come up in any .NET interview. This solution gives you a concrete, self-built example of why scopedness flows upward (§7.5).
- **Layer ownership** (a recurring interview probe): the kernel moves bytes for bash; the PowerShell engine moves objects; the .NET runtime loads assemblies; your container owns lifetimes.

---

## Self-check questions

1. What physically travels between `ps` and `sort` in a bash pipeline, and what travels between two cmdlets?
<details><summary>Answer</summary>Bytes through a kernel pipe between two processes. Between cmdlets: a reference to a .NET object, handed from one command object to the next by the engine inside one process.</details>

2. Why does `Get-ShowcaseDevice | Test-ShowcaseDeviceHealth` bind to `-InputObject` and not `-Id`?
<details><summary>Answer</summary>By value with exact type (step 1) is tried before by property name (step 2). The piped object is a `Device` and `-InputObject` is of type `Device`.</details>

3. How does a `HealthReport` reach `Restart-ShowcaseDevice -Id`?
<details><summary>Answer</summary>`-Id` has `ValueFromPipelineByPropertyName` and `[Alias("DeviceId")]`; the report has a `DeviceId` property.</details>

4. Why can't a cmdlet use constructor injection?
<details><summary>Answer</summary>The PowerShell engine creates cmdlet objects with a parameterless constructor; your container is never asked to construct them.</details>

5. Where is the module's container built, and when?
<details><summary>Answer</summary>In `ModuleServices.Build()`, lazily, on the first access to `ModuleServices.Provider` (the first command or Tab completion). Disposed on `Remove-Module` via `IModuleAssemblyCleanup`.</details>

6. Why is the scope disposed in `Dispose` instead of `EndProcessing`?
<details><summary>Answer</summary>`EndProcessing` doesn't run when the pipeline stops early (`Select-Object -First`, Ctrl+C, terminating error). The engine always calls `Dispose` on commands that implement `IDisposable`.</details>

7. Why must `IActivityLog` be scoped?
<details><summary>Answer</summary>It depends on the scoped `IOperationContext`. As a singleton it would capture the first scope's context forever (captive dependency).</details>

8. In `Get-ShowcaseDevice -Id dev-003, dev-006 | Restart-ShowcaseDevice`, how many operation ids appear in the log, and why?
<details><summary>Answer</summary>One: a single `Restart-ShowcaseDevice` invocation has one scope, and both `ProcessRecord` calls use it.</details>

9. The app and the module both register `IDeviceRepository` as a singleton. How many instances exist?
<details><summary>Answer</summary>Two, one per process (one per container). They coordinate only through the file and the lock.</details>

10. Why would a C# `lock` statement not protect `devices.json`?
<details><summary>Answer</summary>It only coordinates threads inside one process. The app and `pwsh` are separate processes; the code uses a file opened with `FileShare.None` (an OS-level advisory lock) instead.</details>

11. What is `Deserialized.Showcase.Core.Device`, and what can't you do with it?
<details><summary>Answer</summary>A property bag rebuilt from serialized data (CLIXML) after crossing a process boundary. It has the data but none of the methods, and it isn't a `Device` instance; it can still bind by property name.</details>

12. You rebuilt the module and re-imported it, but the old behavior persists. Why, and what's the fix?
<details><summary>Answer</summary>The old assembly is still loaded in the process and can't be unloaded. Start a new `pwsh`.</details>

13. A teammate's `Remove-Widget -WhatIf` deleted the widget. What's the likely bug?
<details><summary>Answer</summary>The cmdlet declares `SupportsShouldProcess` but never calls `ShouldProcess` before acting.</details>

14. Which PowerShell versions can load this module, and what in the solution decides that?
<details><summary>Answer</summary>7.4 and later (.NET 8+). `TargetFramework net8.0` in `Directory.Build.props`, enforced by `PowerShellVersion = '7.4'` and `CompatiblePSEditions = @('Core')` in the manifest.</details>

---

## Sources

Checked 2026-11-01:
- [Announcing PowerShell 7.6 (LTS, built on .NET 10; GA 2026-03-18)](https://devblogs.microsoft.com/powershell/announcing-powershell-7-6/)
- [How to write a PowerShell binary module (exports, manifest, initializer/cleanup guidance: prefer lazy initialization)](https://learn.microsoft.com/en-us/powershell/scripting/developer/module/how-to-write-a-powershell-binary-module?view=powershell-7.6)
- [IModuleAssemblyInitializer.OnImport (PowerShell SDK 7.6)](https://learn.microsoft.com/en-gb/dotnet/api/system.management.automation.imoduleassemblyinitializer.onimport?view=powershellsdk-7.6.0)
- [Resolving PowerShell module assembly dependency conflicts (one shared load context; ALC isolation pattern)](https://learn.microsoft.com/en-us/powershell/scripting/dev-cross-plat/resolving-dependency-conflicts)
- [PowerShell ALC samples (daxian-dbw)](https://www.github.com/daxian-dbw/PowerShell-ALC-Samples)

Not re-checked this session (stable reference material):
- about_Pipelines, about_Parameters (`ValueFromPipeline`, `ValueFromPipelineByPropertyName`), about_Functions_CmdletBindingAttribute, about_Types.ps1xml, about_Format.ps1xml, `Trace-Command` (all on learn.microsoft.com, PowerShell docs).
- Dependency injection in .NET: service lifetimes, `ValidateScopes` / `ValidateOnBuild` (learn.microsoft.com, .NET docs).

---

*End of Lecture 006. Next: build it (§12), fill in the prediction tables, then rehearse the §11 run-of-show once. When you've read this, a recall check works well as a dry run of your video narration: explain chapters 2, 5 and 6 out loud.*
