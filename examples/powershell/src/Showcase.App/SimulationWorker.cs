using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
using Showcase.Core;

namespace Showcase.App;

/// <summary>
/// A hosted service is a SINGLETON, so it may not take scoped services (IActivityLog) in its
/// constructor. Instead it takes IServiceScopeFactory and opens a short scope whenever it has
/// something to log: exactly what each PowerShell command does in the module.
/// </summary>
public sealed class SimulationWorker : BackgroundService
{
    private readonly IDeviceRepository _repository;
    private readonly IDeviceSimulator _simulator;
    private readonly IServiceScopeFactory _scopes;
    private readonly ShowcaseOptions _options;
    private readonly TimeProvider _time;
    private readonly ILogger<SimulationWorker> _logger;

    public SimulationWorker(
        IDeviceRepository repository,
        IDeviceSimulator simulator,
        IServiceScopeFactory scopes,
        ShowcaseOptions options,
        TimeProvider time,
        ILogger<SimulationWorker> logger)
    {
        _repository = repository;
        _simulator = simulator;
        _scopes = scopes;
        _options = options;
        _time = time;
        _logger = logger;
    }

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        _logger.LogInformation("Simulating devices every {Interval}. Data directory: {Directory}",
            _options.TickInterval, _options.DataDirectory);
        _logger.LogInformation("In another terminal: Import-Module ./out/Showcase/Showcase.psd1; Get-ShowcaseDevice");

        using var timer = new PeriodicTimer(_options.TickInterval);
        var tick = 0;

        do
        {
            tick++;
            var events = _repository.Update(devices => _simulator.Tick(devices, _time.GetUtcNow()));

            if (events.Count > 0)
            {
                using var scope = _scopes.CreateScope();
                var log = scope.ServiceProvider.GetRequiredService<IActivityLog>();
                foreach (var e in events)
                {
                    log.Record(e.DeviceId, e.Action, e.Message);
                    _logger.LogWarning("{DeviceId}: {Message}", e.DeviceId, e.Message);
                }
            }

            if (tick % 5 == 0)
            {
                var summary = _repository.GetAll()
                    .GroupBy(d => d.Status)
                    .OrderBy(g => g.Key)
                    .Select(g => $"{g.Count()} {g.Key}");
                _logger.LogInformation("Fleet: {Summary}", string.Join(", ", summary));
            }
        }
        while (await timer.WaitForNextTickAsync(stoppingToken));
    }
}
