# ============================================================================
# Chapter 4: Dependency injection inside the module
# ============================================================================
Import-Module (Join-Path $PSScriptRoot '../out/Showcase/Showcase.psd1')

# --- 4.1 The container's registration table, as objects ---------------------
Get-ShowcaseServiceRegistration
Get-ShowcaseServiceRegistration | Group-Object Lifetime | Select-Object Name, Count

# --- 4.2 Singleton vs scoped, made visible ----------------------------------
Get-ShowcaseSession
Get-ShowcaseDevice | Out-Null
Get-ShowcaseSession
# Predict before you run: which properties changed between the two Get-ShowcaseSession calls, and why?

# --- 4.2b Proof that the pipeline hands out LIVE references, not copies -------
$first = Get-ShowcaseSession
Get-ShowcaseDevice | Out-Null
$second = Get-ShowcaseSession
[object]::ReferenceEquals($first, $second)   # True: the same singleton object, twice
$first.CommandsRun                           # already shows the NEW count: $first is not a snapshot

# --- 4.3 Every command invocation gets its own scope ------------------------
Get-ShowcaseDevice -Verbose | Out-Null
Get-ShowcaseDevice -Verbose | Out-Null        # different operation id

# --- 4.4 One pipeline: each command has ONE scope for all its input objects --
Get-ShowcaseDevice -Id dev-003, dev-006 | Restart-ShowcaseDevice -Confirm:$false
Get-ShowcaseActivity -Last 4 | Format-Table Timestamp, Source, OperationId, DeviceId, Action
# Both restarts share one OperationId (one Restart-ShowcaseDevice invocation = one scope).

# --- 4.5 Two processes, one set of services ----------------------------------
Get-ShowcaseActivity -Last 200 | Group-Object Source | Select-Object Name, Count
# "app"  entries were written by Showcase.App through IActivityLog
# "pwsh" entries were written by this module through the SAME IActivityLog class
