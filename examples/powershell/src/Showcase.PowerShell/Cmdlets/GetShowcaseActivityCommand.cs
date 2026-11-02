using System.Management.Automation;
using Showcase.Core;

namespace Showcase.PowerShell.Cmdlets;

/// <summary>
/// Get-ShowcaseActivity -Last 10
/// Get-ShowcaseActivity -Source app            only what Showcase.App logged
/// Get-ShowcaseDevice dev-002 | Get-ShowcaseActivity   a Device's Id binds to -DeviceId (alias Id)
/// The log is written by BOTH processes through the same IActivityLog implementation.
/// </summary>
[Cmdlet(VerbsCommon.Get, "ShowcaseActivity")]
[OutputType(typeof(ActivityEntry))]
public sealed class GetShowcaseActivityCommand : ShowcaseCmdlet
{
    [Parameter(Position = 0, ValueFromPipelineByPropertyName = true)]
    [Alias("Id")]
    [ArgumentCompleter(typeof(DeviceIdCompleter))]
    public string? DeviceId { get; set; }

    [Parameter]
    [ValidateSet("app", "pwsh")]
    public string? Source { get; set; }

    [Parameter]
    [ValidateRange(1, 100_000)]
    public int Last { get; set; } = 20;

    protected override void ProcessRecord()
    {
        var entries = Get<IActivityLog>().ReadAll()
            .Where(e => DeviceId is null || e.DeviceId.Equals(DeviceId, StringComparison.OrdinalIgnoreCase))
            .Where(e => Source is null || e.Source.Equals(Source, StringComparison.OrdinalIgnoreCase))
            .TakeLast(Last);

        WriteObject(entries, enumerateCollection: true);
    }
}
