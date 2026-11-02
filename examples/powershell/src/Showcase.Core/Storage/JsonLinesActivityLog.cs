using System.Text.Json;

namespace Showcase.Core.Storage;

/// <summary>
/// One JSON object per line ("JSON Lines"). Appending a line never rewrites old entries.
/// Registered as SCOPED because it depends on IOperationContext, which is scoped:
/// a singleton holding a scoped service would freeze one OperationId forever
/// (a "captive dependency").
/// </summary>
public sealed class JsonLinesActivityLog : IActivityLog
{
    private static readonly TimeSpan LockTimeout = TimeSpan.FromSeconds(5);

    private readonly ShowcaseOptions _options;
    private readonly IOperationContext _operation;
    private readonly TimeProvider _time;

    public JsonLinesActivityLog(ShowcaseOptions options, IOperationContext operation, TimeProvider time)
    {
        _options = options;
        _operation = operation;
        _time = time;
        Directory.CreateDirectory(options.DataDirectory);
    }

    public void Record(string deviceId, string action, string message)
    {
        var entry = new ActivityEntry(_time.GetUtcNow(), _operation.Source, _operation.OperationId, deviceId, action, message);
        var line = JsonSerializer.Serialize(entry, ShowcaseJson.Compact);

        using var _ = CrossProcessLock.Acquire(_options.LockFile, LockTimeout);
        File.AppendAllText(_options.ActivityFile, line + Environment.NewLine);
    }

    public IReadOnlyList<ActivityEntry> ReadAll()
    {
        if (!File.Exists(_options.ActivityFile))
        {
            return Array.Empty<ActivityEntry>();
        }

        string[] lines;
        using (CrossProcessLock.Acquire(_options.LockFile, LockTimeout))
        {
            lines = File.ReadAllLines(_options.ActivityFile);
        }

        var entries = new List<ActivityEntry>(lines.Length);
        foreach (var line in lines)
        {
            if (string.IsNullOrWhiteSpace(line))
            {
                continue;
            }

            var entry = JsonSerializer.Deserialize<ActivityEntry>(line, ShowcaseJson.Compact);
            if (entry is not null)
            {
                entries.Add(entry);
            }
        }

        return entries;
    }
}
