using System.Management.Automation;
using Showcase.Core;

namespace Showcase.PowerShell.Cmdlets;

/// <summary>
/// Set-ShowcaseDevice dev-005 -Location Roof -Tag outdoor,video
/// Import-Csv updates.csv | Set-ShowcaseDevice -WhatIf
///     Every CSV column whose header matches a parameter name (or alias) binds to it, and
///     PowerShell converts the text: "Maintenance" becomes DeviceStatus.Maintenance.
///     Empty CSV cells mean "leave unchanged". A "a;b" cell becomes two tags.
/// </summary>
[Cmdlet(VerbsCommon.Set, "ShowcaseDevice", SupportsShouldProcess = true)]
[OutputType(typeof(Device))]
public sealed class SetShowcaseDeviceCommand : ShowcaseCmdlet
{
    [Parameter(Mandatory = true, Position = 0, ValueFromPipelineByPropertyName = true)]
    [Alias("DeviceId")]
    [ArgumentCompleter(typeof(DeviceIdCompleter))]
    public string Id { get; set; } = "";

    [Parameter(ValueFromPipelineByPropertyName = true)]
    public string? Location { get; set; }

    [Parameter(ValueFromPipelineByPropertyName = true)]
    [Alias("Tags")]
    public string[]? Tag { get; set; }

    [Parameter(ValueFromPipelineByPropertyName = true)]
    public DeviceStatus? Status { get; set; }

    [Parameter]
    public SwitchParameter PassThru { get; set; }

    protected override void ProcessRecord()
    {
        var location = Location;
        var status = Status;
        var newTags = Tag?
            .SelectMany(t => t.Split(';', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries))
            .ToList();

        var changes = new List<string>();
        if (!string.IsNullOrWhiteSpace(location)) changes.Add($"Location='{location}'");
        if (newTags is { Count: > 0 }) changes.Add($"Tags=[{string.Join(", ", newTags)}]");
        if (status is not null) changes.Add($"Status={status}");

        if (changes.Count == 0)
        {
            WriteWarning($"{Id}: nothing to change.");
            return;
        }

        var description = "Set " + string.Join(", ", changes);
        if (!ShouldProcess(Id, description))
        {
            return;
        }

        try
        {
            var device = Get<IDeviceCommandService>().Update(Id, d =>
            {
                if (!string.IsNullOrWhiteSpace(location)) d.Location = location;
                if (newTags is { Count: > 0 }) d.Tags = newTags;
                if (status is not null) d.Status = status.Value;
            }, description);

            if (PassThru)
            {
                WriteObject(device);
            }
        }
        catch (DeviceNotFoundException ex)
        {
            WriteNotFound(ex);
        }
    }
}
