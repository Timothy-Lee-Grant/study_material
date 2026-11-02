namespace Showcase.Core.Storage;

/// <summary>The fleet written to devices.json the first time anyone reads it.</summary>
internal static class DeviceSeed
{
    public static List<Device> Create(DateTimeOffset now) =>
    [
        Make("dev-001", "Boiler room probe", DeviceKind.TemperatureSensor, "Plant 1", DeviceStatus.Online, 42, 42, 12, now, "thermal"),
        Make("dev-002", "Kiln thermocouple", DeviceKind.TemperatureSensor, "Plant 1", DeviceStatus.Degraded, 78, 60, 35, now, "thermal", "priority"),
        Make("dev-003", "Line 3 pressure", DeviceKind.PressureSensor, "Plant 1", DeviceStatus.Online, 37, 37, 8, now),
        Make("dev-004", "Dock camera", DeviceKind.Camera, "Warehouse", DeviceStatus.Online, 55, 55, 46, now, "video"),
        Make("dev-005", "Yard camera", DeviceKind.Camera, "Yard", DeviceStatus.Online, 51, 51, 40, now, "video", "outdoor"),
        Make("dev-006", "Edge gateway A", DeviceKind.Gateway, "Plant 1", DeviceStatus.Online, 49, 49, 63, now, "network"),
        Make("dev-007", "Edge gateway B", DeviceKind.Gateway, "Warehouse", DeviceStatus.Offline, 47, 49, 0, now.AddMinutes(-10), "network"),
        Make("dev-008", "Cold store probe", DeviceKind.TemperatureSensor, "Warehouse", DeviceStatus.Online, 4, 4, 9, now, "thermal", "food-safety"),
    ];

    private static Device Make(
        string id, string name, DeviceKind kind, string location, DeviceStatus status,
        double temperature, double nominal, double cpu, DateTimeOffset lastSeen, params string[] tags) =>
        new()
        {
            Id = id,
            Name = name,
            Kind = kind,
            Location = location,
            Status = status,
            FirmwareVersion = kind == DeviceKind.Gateway ? "2.4.1" : "1.8.0",
            TemperatureC = temperature,
            NominalTemperatureC = nominal,
            CpuPercent = cpu,
            LastSeen = lastSeen,
            Tags = tags.ToList(),
        };
}
