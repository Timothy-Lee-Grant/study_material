using System.Collections;
using System.Management.Automation;
using System.Management.Automation.Language;
using Microsoft.Extensions.DependencyInjection;
using Showcase.Core;

namespace Showcase.PowerShell;

/// <summary>
/// Tab completion for -Id. PowerShell calls this while you type, outside any command
/// invocation, so it uses the root container and only a singleton (the repository).
/// Press Tab or Ctrl+Space after "-Id " to see live device ids from devices.json.
/// </summary>
public sealed class DeviceIdCompleter : IArgumentCompleter
{
    public IEnumerable<CompletionResult> CompleteArgument(
        string commandName,
        string parameterName,
        string wordToComplete,
        CommandAst commandAst,
        IDictionary fakeBoundParameters)
    {
        var repository = ModuleServices.Provider.GetRequiredService<IDeviceRepository>();
        var typed = wordToComplete.Trim('\'', '"');
        var pattern = new WildcardPattern(typed + "*", WildcardOptions.IgnoreCase);

        foreach (var device in repository.GetAll())
        {
            if (pattern.IsMatch(device.Id) || pattern.IsMatch(device.Name))
            {
                yield return new CompletionResult(
                    device.Id,
                    device.Id,
                    CompletionResultType.ParameterValue,
                    $"{device.Name} | {device.Kind} | {device.Status}");
            }
        }
    }
}
