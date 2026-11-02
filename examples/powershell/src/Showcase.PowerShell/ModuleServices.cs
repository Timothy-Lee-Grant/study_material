using System.Management.Automation;
using Microsoft.Extensions.DependencyInjection;
using Showcase.Core;

namespace Showcase.PowerShell;

/// <summary>
/// Composition root #2 (inside pwsh). There is no Generic Host in PowerShell, so the module
/// builds its own container. It's built LAZILY, on the first command that needs it (Microsoft's
/// guidance prefers lazy initialization over doing work in IModuleAssemblyInitializer.OnImport).
/// </summary>
public static class ModuleServices
{
    private static readonly object Gate = new();
    private static ServiceProvider? _provider;
    private static IReadOnlyList<ServiceDescriptor> _registrations = Array.Empty<ServiceDescriptor>();

    public static IServiceProvider Provider
    {
        get
        {
            lock (Gate)
            {
                return _provider ??= Build();
            }
        }
    }

    /// <summary>What was registered: shown by Get-ShowcaseServiceRegistration.</summary>
    public static IReadOnlyList<ServiceDescriptor> Registrations
    {
        get
        {
            _ = Provider; // make sure the container exists
            return _registrations;
        }
    }

    private static ServiceProvider Build()
    {
        var services = new ServiceCollection();

        // Exactly the same call Showcase.App makes in Program.cs.
        services.AddShowcaseCore(options => options.SourceName = "pwsh");

        // Module-only services.
        services.AddSingleton<ModuleSession>();

        _registrations = services.ToList();

        return services.BuildServiceProvider(new ServiceProviderOptions
        {
            ValidateScopes = true,  // throw if a scoped service is resolved from the root
            ValidateOnBuild = true, // throw now if any registration can't be constructed
        });
    }

    internal static void Reset()
    {
        lock (Gate)
        {
            _provider?.Dispose();
            _provider = null;
        }
    }
}

/// <summary>PowerShell calls this on Remove-Module. Dispose the container cleanly.</summary>
public sealed class ModuleCleanup : IModuleAssemblyCleanup
{
    public void OnRemove(PSModuleInfo psModuleInfo) => ModuleServices.Reset();
}
