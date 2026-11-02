using Microsoft.Extensions.DependencyInjection;
using Showcase.Core.Services;
using Showcase.Core.Storage;

namespace Showcase.Core;

public static class ServiceCollectionExtensions
{
    /// <summary>
    /// Registers everything in Showcase.Core. BOTH hosts call this one method:
    /// Showcase.App (from Program.cs) and the PowerShell module (from ModuleServices).
    /// Same registrations, two composition roots, two processes.
    /// </summary>
    public static IServiceCollection AddShowcaseCore(this IServiceCollection services, Action<ShowcaseOptions>? configure = null)
    {
        var options = new ShowcaseOptions();
        configure?.Invoke(options);

        // Singletons: one instance per container (per process), shared by everyone.
        services.AddSingleton(options);
        services.AddSingleton(TimeProvider.System);
        services.AddSingleton<IDeviceRepository, JsonFileDeviceRepository>();
        services.AddSingleton<IDeviceHealthAnalyzer, DeviceHealthAnalyzer>();
        services.AddSingleton<IDeviceSimulator, RandomDeviceSimulator>();

        // Scoped: one instance per scope (per command invocation in PowerShell, per tick in the app).
        services.AddScoped<IOperationContext, OperationContext>();
        services.AddScoped<IActivityLog, JsonLinesActivityLog>();
        services.AddScoped<IDeviceCommandService, DeviceCommandService>();

        return services;
    }
}
