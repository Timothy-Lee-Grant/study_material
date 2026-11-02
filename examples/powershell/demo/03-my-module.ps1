# ============================================================================
# Chapter 3: Your own commands, built on your own services
# Terminal 1 (leave it running):  dotnet run --project src/Showcase.App -c Release
# Terminal 2: this script.
# ============================================================================
Import-Module (Join-Path $PSScriptRoot '../out/Showcase/Showcase.psd1')

# --- 3.1 Discover --------------------------------------------------------------
Get-Command -Module Showcase
Get-Command Restart-ShowcaseDevice -Syntax

# --- 3.2 Objects from YOUR app ---------------------------------------------
Get-ShowcaseDevice
Get-ShowcaseDevice | Get-Member                      # Showcase.Core.Device: your C# class
Get-ShowcaseDevice -Status Degraded, Offline          # enum parameter: try Tab after -Status
Get-ShowcaseDevice -Name *camera*
# Get-ShowcaseDevice -Id <Tab>                        # type this yourself: Tab cycles live ids from devices.json

# --- 3.3 Built-in commands work on your objects, no code needed --------------
Get-ShowcaseDevice | Where-Object TemperatureC -gt 50 | Sort-Object TemperatureC -Descending
Get-ShowcaseDevice | Group-Object Location | Select-Object Name, Count
Get-ShowcaseDevice | Measure-Object TemperatureC -Average -Maximum
Get-ShowcaseDevice | Select-Object Id, Name, SecondsSinceSeen, IsHot   # members added by types.ps1xml
Get-ShowcaseDevice | ConvertTo-Json -Depth 3 | Set-Content ./fleet.json

# --- 3.4 Pipeline binding: one command's output IS the next one's input -------
Get-ShowcaseDevice | Test-ShowcaseDeviceHealth                # Device -> -InputObject (by value)
Test-ShowcaseDeviceHealth -ProblemsOnly                        # HealthReport objects
Test-ShowcaseDeviceHealth -ProblemsOnly | Restart-ShowcaseDevice -WhatIf   # DeviceId -> -Id (alias)
Test-ShowcaseDeviceHealth -ProblemsOnly | Where-Object Grade -eq Critical | Restart-ShowcaseDevice -Confirm

# Watch Terminal 1: the app (another process) picks up the Maintenance status and brings it back.
Get-ShowcaseActivity -Last 10

# --- 3.5 CSV in, bulk edit out ---------------------------------------------
@'
Id,Location,Tags
dev-002,Kiln room,thermal;priority;watch
dev-005,Roof,outdoor;video
'@ | Set-Content ./updates.csv

Import-Csv ./updates.csv | Set-ShowcaseDevice -WhatIf    # column names bind to parameters
Import-Csv ./updates.csv | Set-ShowcaseDevice -PassThru

# --- 3.6 Streaming: objects flow one at a time, and downstream can stop upstream
Watch-ShowcaseDevice dev-00[1-3] | Select-Object -First 6
Watch-ShowcaseDevice | Where-Object TemperatureC -gt 80 | Select-Object -First 1

# --- 3.7 Errors are objects too ----------------------------------------------
Get-ShowcaseDevice -Id dev-001, nope, dev-003 -ErrorVariable missing   # 2 devices + 1 error; keeps going
$missing[0].CategoryInfo
$missing[0].Exception.DeviceId

try {
    Get-ShowcaseDevice -Id nope -ErrorAction Stop
}
catch [Showcase.Core.DeviceNotFoundException] {
    "Caught by C# exception type: $($_.Exception.Message)"
}

# --- 3.8 Snapshot semantics: objects are copies of what was on disk ----------
$d = Get-ShowcaseDevice -Id dev-001
$d.Location = 'The Moon'                         # changes only this object in memory
(Get-ShowcaseDevice -Id dev-001).Location        # unchanged
$d | Set-ShowcaseDevice -WhatIf                  # the object's Id and Location bind by property name

# --- 3.9 An advanced function (PowerShell code) composed from the C# cmdlets
Get-Help Invoke-ShowcaseAutoHeal -Examples
Invoke-ShowcaseAutoHeal -WhatIf
