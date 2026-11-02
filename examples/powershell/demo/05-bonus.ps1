# ============================================================================
# Chapter 5: More things worth showing off
# ============================================================================
Import-Module (Join-Path $PSScriptRoot '../out/Showcase/Showcase.psd1')

# --- 5.1 Splatting: parameters as a hashtable ------------------------------
$query = @{ Status = 'Online'; Kind = 'Camera' }
Get-ShowcaseDevice @query

# --- 5.2 Your own objects in one line ----------------------------------------
$row = [pscustomobject]@{ Host = 'pi4'; Uptime = (New-TimeSpan -Hours 49); Ok = $true }
$row | Format-List
$row.Uptime.TotalDays

# --- 5.3 Parallelism with real objects ---------------------------------------
$threshold = 50
1..8 | ForEach-Object -Parallel {
    Start-Sleep -Milliseconds (Get-Random -Maximum 300)
    [pscustomobject]@{ Item = $_; Thread = [Environment]::CurrentManagedThreadId; Big = $_ * 10 -gt $using:threshold }
} -ThrottleLimit 4

Measure-Command { 1..8 | ForEach-Object { Start-Sleep -Milliseconds 200 } } | Select-Object TotalMilliseconds
Measure-Command { 1..8 | ForEach-Object -Parallel { Start-Sleep -Milliseconds 200 } -ThrottleLimit 8 } | Select-Object TotalMilliseconds

# --- 5.4 Crossing a PROCESS boundary: objects become property bags -----------
$remote = pwsh -NoProfile -Command { Get-Process -Id $PID | Select-Object Name, Id, StartTime }
$remote.GetType().FullName
$remote.PSObject.TypeNames                  # Deserialized.Selected.System.Diagnostics.Process
$remote.StartTime.GetType().Name            # primitive types survive (DateTime)

Get-ShowcaseDevice | Export-Clixml ./fleet.clixml
$back = Import-Clixml ./fleet.clixml
$back[0].PSObject.TypeNames[0]              # Deserialized.Showcase.Core.Device: data yes, methods no
$back | Test-ShowcaseDeviceHealth           # still works, although these are no longer Device objects
# How did it bind? Ask the binder to narrate:
Trace-Command -Name ParameterBinding -PSHost -Expression { $back[0] | Test-ShowcaseDeviceHealth }

# --- 5.5 Compare two snapshots ----------------------------------------------
$before = Get-ShowcaseDevice
Start-Sleep -Seconds 6
$after = Get-ShowcaseDevice
Compare-Object $before $after -Property Id, Status | Sort-Object Id

# --- 5.6 Make a report -------------------------------------------------------
Test-ShowcaseDeviceHealth |
    Select-Object DeviceId, DeviceName, Grade, Summary |
    ConvertTo-Html -Title 'Fleet health' |
    Set-Content ./fleet-health.html

# --- 5.7 Discoverability ------------------------------------------------------
Get-Verb | Where-Object Verb -in 'Get', 'Set', 'Restart', 'Test', 'Watch' | Format-Table Verb, Group, Description
Get-Command -Noun Process
Get-Help Get-ChildItem -Examples
