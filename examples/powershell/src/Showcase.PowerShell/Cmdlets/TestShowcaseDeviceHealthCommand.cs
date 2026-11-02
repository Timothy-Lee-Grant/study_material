using System.Management.Automation;
using Showcase.Core;

namespace Showcase.PowerShell.Cmdlets;

/// <summary>
/// Test-ShowcaseDeviceHealth                          check every device
/// Get-ShowcaseDevice | Test-ShowcaseDeviceHealth     a live Device object binds to -InputObject (by value)
/// Test-ShowcaseDeviceHealth -Id dev-002              or by id
/// Output: HealthReport objects, which have a DeviceId property, so they can be piped on into
/// Restart-ShowcaseDevice, whose -Id parameter has the alias DeviceId.
/// </summary>
[Cmdlet(VerbsDiagnostic.Test, "ShowcaseDeviceHealth", DefaultParameterSetName = AllSet)]
[OutputType(typeof(HealthReport))]
public sealed class TestShowcaseDeviceHealthCommand : ShowcaseCmdlet
{
    private const string AllSet = "All";
    private const string InputObjectSet = "InputObject";
    private const string ByIdSet = "ById";

    [Parameter(ParameterSetName = InputObjectSet, Mandatory = true, ValueFromPipeline = true)]
    public Device InputObject { get; set; } = null!;

    [Parameter(ParameterSetName = ByIdSet, Mandatory = true, Position = 0, ValueFromPipelineByPropertyName = true)]
    [Alias("DeviceId")]
    [ArgumentCompleter(typeof(DeviceIdCompleter))]
    public string[] Id { get; set; } = Array.Empty<string>();

    /// <summary>Only emit reports whose grade is Warning or Critical.</summary>
    [Parameter]
    public SwitchParameter ProblemsOnly { get; set; }

    private IDeviceHealthAnalyzer _analyzer = null!;

    protected override void Begin() => _analyzer = Get<IDeviceHealthAnalyzer>();

    protected override void ProcessRecord()
    {
        switch (ParameterSetName)
        {
            case InputObjectSet:
                Emit(InputObject);
                break;

            case ByIdSet:
                var repository = Get<IDeviceRepository>();
                foreach (var id in Id)
                {
                    var device = repository.Find(id);
                    if (device is null)
                    {
                        WriteNotFound(new DeviceNotFoundException(id));
                    }
                    else
                    {
                        Emit(device);
                    }
                }

                break;

            default:
                foreach (var device in Get<IDeviceRepository>().GetAll())
                {
                    Emit(device);
                }

                break;
        }
    }

    private void Emit(Device device)
    {
        var report = _analyzer.Analyze(device);
        if (!ProblemsOnly || report.Grade != HealthGrade.Healthy)
        {
            WriteObject(report);
        }
    }
}
