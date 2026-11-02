namespace Showcase.Core.Services;

/// <summary>
/// Pure rules: device in, verdict out. Singleton (no state, no scoped dependencies).
/// TimeProvider is injected instead of calling DateTimeOffset.UtcNow directly, so a test
/// can pass a fake clock.
/// </summary>
public sealed class DeviceHealthAnalyzer : IDeviceHealthAnalyzer
{
    private readonly HealthThresholds _limits;
    private readonly TimeProvider _time;

    public DeviceHealthAnalyzer(ShowcaseOptions options, TimeProvider time)
    {
        _limits = options.Thresholds;
        _time = time;
    }

    public HealthReport Analyze(Device device)
    {
        var findings = new List<string>();
        var grade = HealthGrade.Healthy;

        void Raise(HealthGrade level, string finding)
        {
            findings.Add(finding);
            if (level > grade)
            {
                grade = level;
            }
        }

        switch (device.Status)
        {
            case DeviceStatus.Offline:
                Raise(HealthGrade.Critical, "Device is offline");
                break;
            case DeviceStatus.Degraded:
                Raise(HealthGrade.Warning, "Device reports degraded status");
                break;
            case DeviceStatus.Maintenance:
                Raise(HealthGrade.Warning, "Device is restarting (maintenance)");
                break;
        }

        if (device.TemperatureC >= _limits.CriticalTemperatureC)
        {
            Raise(HealthGrade.Critical, $"Temperature {device.TemperatureC:F1} C >= {_limits.CriticalTemperatureC} C");
        }
        else if (device.TemperatureC >= _limits.WarningTemperatureC)
        {
            Raise(HealthGrade.Warning, $"Temperature {device.TemperatureC:F1} C >= {_limits.WarningTemperatureC} C");
        }

        if (device.CpuPercent >= _limits.CriticalCpuPercent)
        {
            Raise(HealthGrade.Critical, $"CPU {device.CpuPercent:F0}% >= {_limits.CriticalCpuPercent}%");
        }
        else if (device.CpuPercent >= _limits.WarningCpuPercent)
        {
            Raise(HealthGrade.Warning, $"CPU {device.CpuPercent:F0}% >= {_limits.WarningCpuPercent}%");
        }

        var now = _time.GetUtcNow();
        var silence = now - device.LastSeen;
        if (device.Status != DeviceStatus.Offline && silence > _limits.StaleAfter)
        {
            Raise(HealthGrade.Warning, $"No update for {silence.TotalSeconds:F0}s (is Showcase.App running?)");
        }

        return new HealthReport(device.Id, device.Name, grade, findings, now);
    }
}
