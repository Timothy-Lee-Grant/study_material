using System.Management.Automation;
using Showcase.Core;

namespace Showcase.PowerShell.Cmdlets;

/// <summary>
/// Restart-ShowcaseDevice dev-002
/// Test-ShowcaseDeviceHealth -ProblemsOnly | Restart-ShowcaseDevice -WhatIf
/// SupportsShouldProcess gives this cmdlet -WhatIf and -Confirm for free; ShouldProcess()
/// is where they take effect. Showcase.App (a different process) notices the Maintenance
/// status and brings the device back Online a few seconds later.
/// </summary>
[Cmdlet(VerbsLifecycle.Restart, "ShowcaseDevice", SupportsShouldProcess = true, ConfirmImpact = ConfirmImpact.Medium)]
[OutputType(typeof(Device))]
public sealed class RestartShowcaseDeviceCommand : ShowcaseCmdlet
{
    [Parameter(Mandatory = true, Position = 0, ValueFromPipelineByPropertyName = true)]
    [Alias("DeviceId")]
    [ArgumentCompleter(typeof(DeviceIdCompleter))]
    public string[] Id { get; set; } = Array.Empty<string>();

    /// <summary>Emit the updated Device (by default a "do something" cmdlet emits nothing).</summary>
    [Parameter]
    public SwitchParameter PassThru { get; set; }

    protected override void ProcessRecord()
    {
        var commands = Get<IDeviceCommandService>();

        foreach (var id in Id)
        {
            if (!ShouldProcess(id, "Restart device"))
            {
                continue;
            }

            try
            {
                var device = commands.Restart(id);
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
}
