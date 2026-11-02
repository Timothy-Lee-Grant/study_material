namespace Showcase.Core.Services;

/// <summary>
/// The only place that changes devices on behalf of a user. Scoped, because it depends on
/// the scoped IActivityLog (which depends on the scoped IOperationContext).
/// </summary>
public sealed class DeviceCommandService : IDeviceCommandService
{
    private readonly IDeviceRepository _repository;
    private readonly IActivityLog _log;

    public DeviceCommandService(IDeviceRepository repository, IActivityLog log)
    {
        _repository = repository;
        _log = log;
    }

    public Device Restart(string deviceId)
    {
        var device = _repository.Update(devices =>
        {
            var d = FindOrThrow(devices, deviceId);
            d.Status = DeviceStatus.Maintenance;
            d.RestartCount++;
            d.MaintenanceTicksRemaining = 3; // Showcase.App brings it back after 3 ticks.
            return d;
        });

        _log.Record(device.Id, "Restart", $"Restart requested (restart #{device.RestartCount})");
        return device;
    }

    public Device Update(string deviceId, Action<Device> change, string description)
    {
        var device = _repository.Update(devices =>
        {
            var d = FindOrThrow(devices, deviceId);
            change(d);
            return d;
        });

        _log.Record(device.Id, "Update", description);
        return device;
    }

    private static Device FindOrThrow(List<Device> devices, string deviceId) =>
        devices.FirstOrDefault(d => string.Equals(d.Id, deviceId, StringComparison.OrdinalIgnoreCase))
        ?? throw new DeviceNotFoundException(deviceId);
}
