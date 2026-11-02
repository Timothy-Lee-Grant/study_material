using System.Management.Automation;
using Showcase.Core;

namespace Showcase.PowerShell.Cmdlets;

/// <summary>
/// Watch-ShowcaseDevice                                  samples every device every 2 s, forever (Ctrl+C stops)
/// Watch-ShowcaseDevice dev-00[1-3] | Select-Object -First 6
/// Watch-ShowcaseDevice | Where-Object TemperatureC -gt 80 | Select-Object -First 1
///
/// Shows that the pipeline STREAMS: each sample reaches the next command as soon as it is
/// written, and a downstream command (Select-Object -First) can stop this one early.
/// </summary>
[Cmdlet(VerbsCommon.Watch, "ShowcaseDevice")]
[OutputType(typeof(DeviceSample))]
public sealed class WatchShowcaseDeviceCommand : ShowcaseCmdlet
{
    private readonly CancellationTokenSource _stop = new();

    [Parameter(Position = 0)]
    [SupportsWildcards]
    public string Id { get; set; } = "*";

    [Parameter]
    [ValidateRange(0.2, 60.0)]
    public double IntervalSeconds { get; set; } = 2;

    /// <summary>Stop after this many samples (0 = run until stopped).</summary>
    [Parameter]
    [ValidateRange(0, int.MaxValue)]
    public int Count { get; set; }

    protected override void ProcessRecord()
    {
        var repository = Get<IDeviceRepository>();
        var time = Get<TimeProvider>();
        var pattern = new WildcardPattern(Id, WildcardOptions.IgnoreCase);
        var written = 0;

        while (!_stop.IsCancellationRequested)
        {
            foreach (var d in repository.GetAll().Where(d => pattern.IsMatch(d.Id)))
            {
                WriteObject(new DeviceSample(time.GetUtcNow(), d.Id, d.Name, d.Status, d.TemperatureC, d.CpuPercent));
                written++;
                if (Count > 0 && written >= Count)
                {
                    return;
                }
            }

            // Sleep, but wake immediately if StopProcessing is called.
            _stop.Token.WaitHandle.WaitOne(TimeSpan.FromSeconds(IntervalSeconds));
        }
    }

    /// <summary>Called by PowerShell on another thread when the user presses Ctrl+C.</summary>
    protected override void StopProcessing() => _stop.Cancel();

    protected override void Dispose(bool disposing)
    {
        if (disposing)
        {
            _stop.Dispose();
        }

        base.Dispose(disposing);
    }
}
