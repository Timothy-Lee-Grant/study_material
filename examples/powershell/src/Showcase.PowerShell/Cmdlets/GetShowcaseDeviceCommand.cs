using System.Management.Automation;
using Showcase.Core;

namespace Showcase.PowerShell.Cmdlets;

/// <summary>
/// Get-ShowcaseDevice                       all devices
/// Get-ShowcaseDevice -Status Degraded      filter (enum: Tab-completes for free)
/// Get-ShowcaseDevice -Name *cam*           wildcards
/// 'dev-001','dev-004' | Get-ShowcaseDevice ids from the pipeline (by value)
/// Test-ShowcaseDeviceHealth | Get-ShowcaseDevice   ids from a DeviceId property (by property name)
/// </summary>
[Cmdlet(VerbsCommon.Get, "ShowcaseDevice", DefaultParameterSetName = FilterSet)]
[OutputType(typeof(Device))]
public sealed class GetShowcaseDeviceCommand : ShowcaseCmdlet
{
    private const string FilterSet = "Filter";
    private const string ByIdSet = "ById";

    [Parameter(ParameterSetName = ByIdSet, Mandatory = true, Position = 0,
        ValueFromPipeline = true, ValueFromPipelineByPropertyName = true)]
    [Alias("DeviceId")]
    [ArgumentCompleter(typeof(DeviceIdCompleter))]
    public string[] Id { get; set; } = Array.Empty<string>();

    [Parameter(ParameterSetName = FilterSet)]
    [SupportsWildcards]
    public string Name { get; set; } = "*";

    [Parameter(ParameterSetName = FilterSet)]
    public DeviceKind[]? Kind { get; set; }

    [Parameter(ParameterSetName = FilterSet)]
    public DeviceStatus[]? Status { get; set; }

    [Parameter(ParameterSetName = FilterSet)]
    public string? Tag { get; set; }

    protected override void ProcessRecord()
    {
        var devices = Get<IDeviceRepository>().GetAll();

        if (ParameterSetName == ByIdSet)
        {
            foreach (var id in Id)
            {
                var device = devices.FirstOrDefault(d => d.Id.Equals(id, StringComparison.OrdinalIgnoreCase));
                if (device is null)
                {
                    WriteNotFound(new DeviceNotFoundException(id));
                }
                else
                {
                    WriteObject(device);
                }
            }

            return;
        }

        var pattern = new WildcardPattern(Name, WildcardOptions.IgnoreCase);
        foreach (var device in devices)
        {
            var matches =
                pattern.IsMatch(device.Name)
                && (Kind is null || Kind.Contains(device.Kind))
                && (Status is null || Status.Contains(device.Status))
                && (Tag is null || device.Tags.Contains(Tag, StringComparer.OrdinalIgnoreCase));

            if (matches)
            {
                WriteObject(device); // one real .NET object at a time into the pipeline
            }
        }
    }
}
