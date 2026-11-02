namespace Showcase.Core;

// The contracts. Hosts (the app, the PowerShell module) depend on these interfaces;
// the DI container decides which implementation they get.

/// <summary>Reads and writes the device list. Every call sees the current file on disk.</summary>
public interface IDeviceRepository
{
    IReadOnlyList<Device> GetAll();

    Device? Find(string id);

    /// <summary>
    /// Read-modify-write under a cross-process lock, so the app's simulation tick and a
    /// PowerShell command can't overwrite each other's changes.
    /// </summary>
    T Update<T>(Func<List<Device>, T> change);
}

/// <summary>Turns a device into a health verdict. Pure logic: no I/O.</summary>
public interface IDeviceHealthAnalyzer
{
    HealthReport Analyze(Device device);
}

/// <summary>Commands that change devices and leave an audit trail.</summary>
public interface IDeviceCommandService
{
    Device Restart(string deviceId);

    Device Update(string deviceId, Action<Device> change, string description);
}

/// <summary>Append-only audit trail shared by every process.</summary>
public interface IActivityLog
{
    void Record(string deviceId, string action, string message);

    IReadOnlyList<ActivityEntry> ReadAll();
}

/// <summary>Advances the fake physics of the fleet by one step.</summary>
public interface IDeviceSimulator
{
    List<SimulationEvent> Tick(List<Device> devices, DateTimeOffset now);
}

/// <summary>
/// One "unit of work". Scoped: a new one per DI scope. In the module that means one per
/// command invocation; in the app, one per simulation tick that has something to log.
/// </summary>
public interface IOperationContext
{
    Guid OperationId { get; }

    string Source { get; }
}
