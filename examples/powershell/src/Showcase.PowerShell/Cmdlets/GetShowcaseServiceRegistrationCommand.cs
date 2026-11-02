using System.Management.Automation;
using Microsoft.Extensions.DependencyInjection;

namespace Showcase.PowerShell.Cmdlets;

/// <summary>One row of the DI container's registration table, as an object.</summary>
public sealed record ServiceRegistrationInfo(string ServiceType, ServiceLifetime Lifetime, string Implementation);

/// <summary>
/// Get-ShowcaseServiceRegistration | Group-Object Lifetime
/// The module's own DI container, inspected with ordinary pipeline commands.
/// </summary>
[Cmdlet(VerbsCommon.Get, "ShowcaseServiceRegistration")]
[OutputType(typeof(ServiceRegistrationInfo))]
public sealed class GetShowcaseServiceRegistrationCommand : ShowcaseCmdlet
{
    protected override void EndProcessing()
    {
        foreach (var d in ModuleServices.Registrations)
        {
            var implementation =
                d.ImplementationType?.Name
                ?? (d.ImplementationInstance is not null ? $"{d.ImplementationInstance.GetType().Name} (instance)" : "factory");

            WriteObject(new ServiceRegistrationInfo(d.ServiceType.Name, d.Lifetime, implementation));
        }
    }
}
