namespace Showcase.Core;

/// <summary>
/// Settings shared by every host. The app and the PowerShell module must agree on
/// DataDirectory, because the JSON files in it are the only thing the two processes share.
/// </summary>
public sealed class ShowcaseOptions
{
    /// <summary>Folder holding devices.json and activity.jsonl. Override with SHOWCASE_DATA_DIR.</summary>
    public string DataDirectory { get; set; } = DefaultDataDirectory();

    /// <summary>Written into every activity entry: "app" or "pwsh".</summary>
    public string SourceName { get; set; } = "unknown";

    /// <summary>How often Showcase.App advances the simulation.</summary>
    public TimeSpan TickInterval { get; set; } = TimeSpan.FromSeconds(2);

    public HealthThresholds Thresholds { get; set; } = new();

    public string DevicesFile => Path.Combine(DataDirectory, "devices.json");
    public string ActivityFile => Path.Combine(DataDirectory, "activity.jsonl");
    public string LockFile => Path.Combine(DataDirectory, ".lock");

    public static string DefaultDataDirectory()
    {
        var fromEnvironment = Environment.GetEnvironmentVariable("SHOWCASE_DATA_DIR");
        if (!string.IsNullOrWhiteSpace(fromEnvironment))
        {
            return fromEnvironment;
        }

        var home = Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);
        return Path.Combine(home, ".powershell-showcase");
    }
}

public sealed class HealthThresholds
{
    public double WarningTemperatureC { get; set; } = 70;
    public double CriticalTemperatureC { get; set; } = 85;
    public double WarningCpuPercent { get; set; } = 80;
    public double CriticalCpuPercent { get; set; } = 95;
    public TimeSpan StaleAfter { get; set; } = TimeSpan.FromSeconds(30);
}
