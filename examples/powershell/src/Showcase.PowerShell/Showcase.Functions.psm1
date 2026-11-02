# Advanced functions: PowerShell code that behaves exactly like a compiled cmdlet
# (named parameters, pipeline input, -WhatIf/-Confirm, -Verbose), composed from the C# cmdlets.

function Invoke-ShowcaseAutoHeal {
    <#
    .SYNOPSIS
        Restarts every device whose health grade is at least -MinimumGrade.
    .EXAMPLE
        Invoke-ShowcaseAutoHeal -WhatIf
    .EXAMPLE
        Invoke-ShowcaseAutoHeal -MinimumGrade Warning -Confirm
    #>
    [CmdletBinding(SupportsShouldProcess, ConfirmImpact = 'Medium')]
    [OutputType([Showcase.Core.HealthReport])]
    param(
        [Showcase.Core.HealthGrade] $MinimumGrade = 'Critical'
    )

    $sick = Test-ShowcaseDeviceHealth | Where-Object Grade -ge $MinimumGrade
    Write-Verbose "Found $(@($sick).Count) device(s) at or above $MinimumGrade."

    foreach ($report in $sick) {
        $reason = $report.Findings -join '; '
        if ($PSCmdlet.ShouldProcess("$($report.DeviceId) ($($report.DeviceName))", "Restart because: $reason")) {
            # We already asked (ShouldProcess above), so don't let the cmdlet ask again.
            Restart-ShowcaseDevice -Id $report.DeviceId -Confirm:$false
            $report
        }
    }
}
