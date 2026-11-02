# PowerShell Showcase

A small .NET solution that shows off what makes PowerShell different:

1. **The pipeline passes live .NET objects**, not text.
2. **All of .NET is available** from the shell: static methods, `::new()`, generics, `Add-Type`, and your own assemblies.
3. **A binary module can reuse your application's services through dependency injection**: the same `AddShowcaseCore()` call wires up both the running app and the PowerShell commands.

The companion lecture is [`lectures/dotnet/006-the_power_of_powershell.md`](../../lectures/dotnet/006-the_power_of_powershell.md).

## What's in the solution

```
examples/powershell/
├── PowerShellShowcase.sln
├── Directory.Build.props            shared settings (net8.0, nullable, ...)
├── build.ps1                        build + publish the module to ./out/Showcase
├── src/
│   ├── Showcase.Core/               class library: models, interfaces, services, AddShowcaseCore()
│   ├── Showcase.App/                Generic Host console app: simulates a device fleet (the "running application")
│   └── Showcase.PowerShell/         binary module: cmdlets + DI composition root + manifest + format/type files
└── demo/                            one script per video chapter (run block by block)
```

The app and the module are **two processes**. They share state through files in `~/.powershell-showcase/` (`devices.json`, `activity.jsonl`), guarded by a cross-process file lock. Set `SHOWCASE_DATA_DIR` to use another folder.

## Prerequisites

- .NET SDK 8 or later (`dotnet --list-sdks`)
- PowerShell 7.4 or later (`pwsh --version`). On macOS: `brew install --cask powershell`.

## Run it

```bash
# once
cd examples/powershell
pwsh ./build.ps1

# terminal 1: the application
dotnet run --project src/Showcase.App -c Release

# terminal 2: the shell
pwsh
```

```powershell
Import-Module ./out/Showcase/Showcase.psd1
Get-ShowcaseDevice
Test-ShowcaseDeviceHealth -ProblemsOnly | Restart-ShowcaseDevice -WhatIf
```

Then walk through `demo/01-…` to `demo/05-…`.

## Commands

| Command | Shows |
|---|---|
| `Get-ShowcaseDevice` | Objects from your app; wildcards; enum parameters; pipeline input by value and by property name; Tab completion of live ids |
| `Test-ShowcaseDeviceHealth` | Typed `-InputObject` binding; output that feeds the next command |
| `Restart-ShowcaseDevice` | `-WhatIf` / `-Confirm` via `ShouldProcess`; the other process reacts |
| `Set-ShowcaseDevice` | `Import-Csv \| Set-…` bulk edits with type conversion |
| `Watch-ShowcaseDevice` | Streaming; `Select-Object -First` stopping upstream; Ctrl+C via `StopProcessing` |
| `Get-ShowcaseActivity` | A log written by both processes through the same service |
| `Get-ShowcaseSession` | Singleton lifetime, made visible |
| `Get-ShowcaseServiceRegistration` | The module's DI container, as objects |
| `Invoke-ShowcaseAutoHeal` | An advanced function (PowerShell code) composed from the C# cmdlets |

## Things to know

- **Rebuilding:** a loaded `.dll` can't be unloaded. After `./build.ps1`, open a new `pwsh` before importing again.
- **Reset the fleet:** stop the app, then `Remove-Item ~/.powershell-showcase -Recurse`.
- **Status:** written without a .NET SDK available, so it was reviewed but not compiled. The lecture's §12 lists exactly what to check on the first build.
