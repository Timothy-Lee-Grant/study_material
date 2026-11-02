using System.Management.Automation;

namespace Showcase.PowerShell.Cmdlets;

/// <summary>
/// Get-ShowcaseSession  (run it twice)
/// CreatedAt and ProcessId stay the same: ModuleSession is a singleton.
/// CommandsRun goes up and LastOperationId changes: each command got a new scope.
/// </summary>
[Cmdlet(VerbsCommon.Get, "ShowcaseSession")]
[OutputType(typeof(ModuleSession))]
public sealed class GetShowcaseSessionCommand : ShowcaseCmdlet
{
    protected override void EndProcessing() => WriteObject(Get<ModuleSession>());
}
