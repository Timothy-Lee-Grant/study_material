using System.Management.Automation;
using Microsoft.Extensions.DependencyInjection;
using Showcase.Core;

namespace Showcase.PowerShell;

/// <summary>
/// Base class for every cmdlet in the module.
///
/// Why no constructor injection? The PowerShell engine, not our container, creates cmdlet
/// objects (with a parameterless constructor) and sets their parameter properties. So the
/// cmdlet asks the container for what it needs. To keep lifetimes correct, each command
/// invocation gets its OWN scope:
///
///   BeginProcessing  -> create scope (new IOperationContext, IActivityLog, ...)
///   ProcessRecord    -> once per pipeline input object, same scope
///   EndProcessing    -> normal end
///   Dispose          -> ALWAYS called by PowerShell, even if the pipeline stopped early
///                       (Select-Object -First, Ctrl+C, an error), so the scope is disposed here.
/// </summary>
public abstract class ShowcaseCmdlet : PSCmdlet, IDisposable
{
    private IServiceScope? _scope;

    protected IServiceProvider Services =>
        _scope?.ServiceProvider ?? throw new InvalidOperationException("Services are available from BeginProcessing onward.");

    protected T Get<T>() where T : notnull => Services.GetRequiredService<T>();

    protected sealed override void BeginProcessing()
    {
        _scope = ModuleServices.Provider.CreateScope();

        var operation = Get<IOperationContext>();
        Get<ModuleSession>().OnCommandStarted(operation.OperationId);
        WriteVerbose($"{MyInvocation.MyCommand.Name}: new DI scope, operation {operation.OperationId}");

        Begin();
    }

    /// <summary>Override instead of BeginProcessing; services are ready here.</summary>
    protected virtual void Begin()
    {
    }

    public void Dispose()
    {
        Dispose(disposing: true);
        GC.SuppressFinalize(this);
    }

    protected virtual void Dispose(bool disposing)
    {
        if (disposing)
        {
            _scope?.Dispose();
            _scope = null;
        }
    }

    /// <summary>Report a missing device as a NON-terminating error: the pipeline keeps going.</summary>
    protected void WriteNotFound(DeviceNotFoundException exception) =>
        WriteError(new ErrorRecord(exception, "DeviceNotFound", ErrorCategory.ObjectNotFound, exception.DeviceId));
}
