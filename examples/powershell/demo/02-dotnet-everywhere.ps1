# ============================================================================
# Chapter 2: The whole .NET library is your standard library
# ============================================================================
using namespace System.Text
using namespace System.Collections.Generic
# ("using namespace" must be the first statements in a script.)

# --- 2.1 Static members: [Type]::Member ---------------------------------------
[Environment]::ProcessorCount
[System.Runtime.InteropServices.RuntimeInformation]::OSDescription
[System.Runtime.InteropServices.RuntimeInformation]::FrameworkDescription   # the .NET runtime pwsh runs on
$PSVersionTable.PSVersion
[math]::Sqrt(2)
[guid]::NewGuid()
[datetime]::UtcNow.AddDays(30).DayOfWeek
[System.IO.Path]::Combine($HOME, 'a', 'b.txt')

# --- 2.2 BCL crypto, encoding, regex: no extra tools to install --------------
$bytes = [Encoding]::UTF8.GetBytes('hello powershell')
[Convert]::ToHexString([System.Security.Cryptography.SHA256]::HashData($bytes))

[regex]::Matches('dev-001 dev-042 x-9', 'dev-(\d+)') | ForEach-Object { [int]$_.Groups[1].Value }

# --- 2.3 Constructing objects: ::new() and generics --------------------------
$queue = [Queue[int]]::new()
1..3 | ForEach-Object { $queue.Enqueue($_) }
$queue.Dequeue()        # 1

$names = [HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
$names.Add('Pi')        # True
$names.Add('PI')        # False: same name, ignoring case

$sb = [StringBuilder]::new()
foreach ($i in 1..3) { [void]$sb.AppendLine("line $i") }
$sb.ToString()

# --- 2.4 Compile C# on the fly ------------------------------------------------
Add-Type -TypeDefinition @'
public static class Fibonacci
{
    public static long Nth(int n)
    {
        long a = 0, b = 1;
        for (int i = 0; i < n; i++)
        {
            long next = a + b;
            a = b;
            b = next;
        }
        return a;
    }
}
'@
[Fibonacci]::Nth(90)

# --- 2.5 Load YOUR assembly and drive it with zero cmdlets --------------------
# (Run ../build.ps1 first.) This is the same dll the app and the module use.
Add-Type -Path (Join-Path $PSScriptRoot '../out/Showcase/Showcase.Core.dll')

$options  = [Showcase.Core.ShowcaseOptions]::new()
$options.DevicesFile

$analyzer = [Showcase.Core.Services.DeviceHealthAnalyzer]::new($options, [TimeProvider]::System)

# A hashtable cast to a class: PowerShell calls the parameterless constructor and sets each property.
$probe = [Showcase.Core.Device]@{
    Id           = 'dev-999'
    Name         = 'Bench probe'
    Status       = 'Online'           # string -> DeviceStatus enum, converted for you
    TemperatureC = 91
    CpuPercent   = 12
    LastSeen     = [DateTimeOffset]::UtcNow
}
$analyzer.Analyze($probe)             # your C# business logic, called from the shell
