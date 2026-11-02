namespace Showcase.Core;

public enum DeviceKind { TemperatureSensor, PressureSensor, Camera, Gateway }

public enum DeviceStatus { Online, Degraded, Offline, Maintenance }

public enum HealthGrade { Healthy, Warning, Critical }

/// <summary>
/// One device in the simulated fleet. A plain class with public get/set properties:
/// System.Text.Json can store it, and PowerShell can show, sort, filter and bind it
/// without any extra work, because PowerShell reads .NET properties directly.
/// </summary>
public sealed class Device
{
    public string Id { get; set; } = "";
    public string Name { get; set; } = "";
    public DeviceKind Kind { get; set; }
    public string Location { get; set; } = "";
    public DeviceStatus Status { get; set; }
    public string FirmwareVersion { get; set; } = "1.0.0";
    public double TemperatureC { get; set; }
    public double NominalTemperatureC { get; set; }
    public double CpuPercent { get; set; }
    public int RestartCount { get; set; }
    public int MaintenanceTicksRemaining { get; set; }
    public DateTimeOffset LastSeen { get; set; }
    public List<string> Tags { get; set; } = new();

    // Used when PowerShell (or anything else) turns the object into a string.
    public override string ToString() => $"{Id} ({Name})";
}

/// <summary>The result of checking one device against the health thresholds.</summary>
public sealed record HealthReport(
    string DeviceId,
    string DeviceName,
    HealthGrade Grade,
    IReadOnlyList<string> Findings,
    DateTimeOffset CheckedAt);

/// <summary>One line of the shared activity log (written by the app AND by PowerShell).</summary>
public sealed record ActivityEntry(
    DateTimeOffset Timestamp,
    string Source,
    Guid OperationId,
    string DeviceId,
    string Action,
    string Message);

/// <summary>A point-in-time reading, emitted by Watch-ShowcaseDevice.</summary>
public sealed record DeviceSample(
    DateTimeOffset Timestamp,
    string DeviceId,
    string Name,
    DeviceStatus Status,
    double TemperatureC,
    double CpuPercent);

/// <summary>Something noteworthy the simulator did during one tick.</summary>
public sealed record SimulationEvent(string DeviceId, string Action, string Message);

public sealed class DeviceNotFoundException : Exception
{
    public DeviceNotFoundException(string deviceId)
        : base($"No device with Id '{deviceId}'.") => DeviceId = deviceId;

    public string DeviceId { get; }
}
