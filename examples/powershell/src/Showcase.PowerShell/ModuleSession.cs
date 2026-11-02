using Showcase.Core;

namespace Showcase.PowerShell;

/// <summary>
/// A SINGLETON that lives as long as the container (normally: the whole pwsh session).
/// Every command bumps CommandsRun and records its scoped OperationId, so
/// Get-ShowcaseSession makes the difference between lifetimes visible.
/// </summary>
public sealed class ModuleSession
{
    private int _commandsRun;

    public ModuleSession(TimeProvider time, ShowcaseOptions options)
    {
        CreatedAt = time.GetUtcNow();
        DataDirectory = options.DataDirectory;
    }

    public DateTimeOffset CreatedAt { get; }

    public int ProcessId { get; } = Environment.ProcessId;

    public string DataDirectory { get; }

    public int CommandsRun => _commandsRun;

    public Guid? LastOperationId { get; private set; }

    internal void OnCommandStarted(Guid operationId)
    {
        Interlocked.Increment(ref _commandsRun);
        LastOperationId = operationId;
    }
}
