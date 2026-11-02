# ============================================================================
# Chapter 1: Objects, not text
# Run one block at a time (VS Code: select the lines, press F8).
# Nothing here needs the Showcase module; it's plain PowerShell 7.
# ============================================================================

# --- 1.1 The bash way: text, and column positions nobody wrote down ----------
# ps -Ao pid,rss,comm | sort -k2 -nr | head -5
#   - sort has to know "memory is column 2"
#   - a process name with spaces breaks naive awk
#   - RSS is in KB on macOS ... or is it? You re-check the man page.

# --- 1.2 The PowerShell way: ask for the property by name --------------------
Get-Process |
    Sort-Object WorkingSet64 -Descending |
    Select-Object -First 5 Name, Id, @{ Name = 'MemoryMB'; Expression = { [math]::Round($_.WorkingSet64 / 1MB, 1) } }

# --- 1.3 What did Get-Process actually give us? A .NET object ----------------
$me = Get-Process -Id $PID
$me.GetType().FullName                 # System.Diagnostics.Process
$me | Get-Member -MemberType Property | Select-Object -First 12
$me | Get-Member -MemberType Method   | Select-Object -First 8   # it has METHODS too: Kill(), Refresh(), ...
$me.StartTime                          # a real DateTime, not a string
(Get-Date) - $me.StartTime             # so date math just works: a TimeSpan

# --- 1.4 Same objects, many outputs: no re-parsing ---------------------------
$top = Get-Process | Sort-Object CPU -Descending | Select-Object -First 5 Name, Id, CPU
$top | Format-Table
$top | ConvertTo-Json
$top | ConvertTo-Csv
$top | Export-Csv ./top-processes.csv
Import-Csv ./top-processes.csv          # comes back as objects (with string values)

# --- 1.5 Files are objects too -----------------------------------------------
Get-ChildItem $PSHOME -File |
    Sort-Object Length -Descending |
    Select-Object -First 5 Name, Length, LastWriteTime

Get-ChildItem $PSHOME -File | Group-Object Extension | Sort-Object Count -Descending | Select-Object -First 5 Name, Count
Get-ChildItem $PSHOME -File | Measure-Object Length -Sum -Average -Maximum

# --- 1.6 Structured text in -> objects out -----------------------------------
$pi = '{"name":"pi4","cores":4,"temps":[41.2,43.0,39.8]}' | ConvertFrom-Json
$pi.cores * 2
$pi.temps | Measure-Object -Average -Maximum

# --- 1.7 Wrapping a TEXT tool so the rest of the pipeline gets objects -------
git -C $PSScriptRoot log --oneline -5 |
    ForEach-Object {
        $hash, $message = $_ -split ' ', 2
        [pscustomobject]@{ Hash = $hash; Message = $message }
    } |
    Where-Object Message -match 'lecture'
