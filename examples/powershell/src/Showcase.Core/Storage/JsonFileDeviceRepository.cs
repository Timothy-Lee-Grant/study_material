using System.Text.Json;

namespace Showcase.Core.Storage;

/// <summary>
/// Stores the fleet in one JSON file. Every read deserializes a FRESH list of Device objects,
/// so callers get snapshots: changing a returned object changes nothing on disk. To change a
/// device, go through Update() (which IDeviceCommandService does).
/// </summary>
public sealed class JsonFileDeviceRepository : IDeviceRepository
{
    private static readonly TimeSpan LockTimeout = TimeSpan.FromSeconds(5);

    private readonly ShowcaseOptions _options;
    private readonly TimeProvider _time;

    public JsonFileDeviceRepository(ShowcaseOptions options, TimeProvider time)
    {
        _options = options;
        _time = time;
        Directory.CreateDirectory(options.DataDirectory);
    }

    public IReadOnlyList<Device> GetAll()
    {
        using var _ = CrossProcessLock.Acquire(_options.LockFile, LockTimeout);
        return LoadOrSeed();
    }

    public Device? Find(string id) =>
        GetAll().FirstOrDefault(d => string.Equals(d.Id, id, StringComparison.OrdinalIgnoreCase));

    public T Update<T>(Func<List<Device>, T> change)
    {
        using var _ = CrossProcessLock.Acquire(_options.LockFile, LockTimeout);
        var devices = LoadOrSeed();
        var result = change(devices);
        Save(devices);
        return result;
    }

    private List<Device> LoadOrSeed()
    {
        if (!File.Exists(_options.DevicesFile))
        {
            var seed = DeviceSeed.Create(_time.GetUtcNow());
            Save(seed);
            return seed;
        }

        var json = File.ReadAllText(_options.DevicesFile);
        return JsonSerializer.Deserialize<List<Device>>(json, ShowcaseJson.Indented) ?? new List<Device>();
    }

    private void Save(List<Device> devices)
    {
        // Write to a temp file, then rename over the real one: a reader never sees half a file.
        var temp = _options.DevicesFile + ".tmp";
        File.WriteAllText(temp, JsonSerializer.Serialize(devices, ShowcaseJson.Indented));
        File.Move(temp, _options.DevicesFile, overwrite: true);
    }
}
