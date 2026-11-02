namespace Showcase.Core.Services;

/// <summary>
/// Fake physics, used only by Showcase.App:
///   Online      -> temperature drifts back toward nominal; ~1% chance per tick to start overheating
///   Degraded    -> heats up ~0.8 C per tick; above 98 C it may shut itself off (Offline)
///   Maintenance -> cools toward nominal; after N ticks comes back Online
///   Offline     -> nothing happens, and LastSeen stops moving (so health checks see it as silent)
/// </summary>
public sealed class RandomDeviceSimulator : IDeviceSimulator
{
    private readonly Random _random = Random.Shared;

    public List<SimulationEvent> Tick(List<Device> devices, DateTimeOffset now)
    {
        var events = new List<SimulationEvent>();

        foreach (var d in devices)
        {
            switch (d.Status)
            {
                case DeviceStatus.Online:
                    d.TemperatureC += (d.NominalTemperatureC - d.TemperatureC) * 0.2 + Noise(1.0);
                    d.CpuPercent += (NominalCpu(d) - d.CpuPercent) * 0.2 + Noise(5);
                    if (_random.NextDouble() < 0.01)
                    {
                        d.Status = DeviceStatus.Degraded;
                        events.Add(new(d.Id, "Fault", $"{d.Name} started overheating"));
                    }
                    break;

                case DeviceStatus.Degraded:
                    d.TemperatureC += 0.8 + Noise(0.5);
                    d.CpuPercent += 2 + Noise(2);
                    if (d.TemperatureC >= 98 && _random.NextDouble() < 0.3)
                    {
                        d.Status = DeviceStatus.Offline;
                        d.CpuPercent = 0;
                        events.Add(new(d.Id, "Offline", $"{d.Name} went offline (thermal shutdown)"));
                    }
                    break;

                case DeviceStatus.Maintenance:
                    d.TemperatureC += (d.NominalTemperatureC - d.TemperatureC) * 0.5;
                    d.CpuPercent = _random.NextDouble() * 5;
                    d.MaintenanceTicksRemaining--;
                    if (d.MaintenanceTicksRemaining <= 0)
                    {
                        d.Status = DeviceStatus.Online;
                        d.TemperatureC = d.NominalTemperatureC;
                        d.CpuPercent = NominalCpu(d);
                        events.Add(new(d.Id, "Online", $"{d.Name} is back online after restart"));
                    }
                    break;

                case DeviceStatus.Offline:
                    continue; // LastSeen is NOT updated: the device is silent.
            }

            d.TemperatureC = Math.Round(Math.Clamp(d.TemperatureC, -20, 120), 1);
            d.CpuPercent = Math.Round(Math.Clamp(d.CpuPercent, 0, 100), 1);
            d.LastSeen = now;
        }

        return events;
    }

    private double Noise(double amplitude) => (_random.NextDouble() * 2 - 1) * amplitude;

    private static double NominalCpu(Device d) => d.Kind switch
    {
        DeviceKind.Camera => 45,
        DeviceKind.Gateway => 60,
        _ => 10,
    };
}
