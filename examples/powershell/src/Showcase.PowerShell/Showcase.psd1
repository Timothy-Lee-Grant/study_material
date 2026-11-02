# Module manifest: the "front door" PowerShell reads when you run Import-Module ./Showcase.psd1.
@{
    # The binary module: cmdlet classes live in this assembly.
    RootModule           = 'Showcase.PowerShell.dll'

    # Loaded before anything else, so the Showcase.Core types exist when the functions below are parsed and run.
    RequiredAssemblies   = @('Showcase.Core.dll')

    # A script module loaded alongside it: advanced functions written in PowerShell itself.
    NestedModules        = @('Showcase.Functions.psm1')

    ModuleVersion        = '1.0.0'
    GUID                 = '6f1d2c1e-3b7a-4c55-9a0e-2f4f6d8b9c10'
    Author               = 'Timothy Lee Grant'
    Description          = 'Demo module: the object pipeline, .NET reuse, and dependency injection inside a binary module.'

    # net8.0 assembly -> needs PowerShell 7.4 or later (.NET 8+). "Core" = PowerShell 7, not Windows PowerShell 5.1.
    PowerShellVersion    = '7.4'
    CompatiblePSEditions = @('Core')

    # Extended Type System: how objects LOOK (format) and extra members added at runtime (types).
    FormatsToProcess     = @('Showcase.format.ps1xml')
    TypesToProcess       = @('Showcase.types.ps1xml')

    # Explicit exports: faster discovery (no need to load the dll to list commands) and a clear public surface.
    CmdletsToExport      = @(
        'Get-ShowcaseDevice'
        'Set-ShowcaseDevice'
        'Restart-ShowcaseDevice'
        'Test-ShowcaseDeviceHealth'
        'Watch-ShowcaseDevice'
        'Get-ShowcaseActivity'
        'Get-ShowcaseSession'
        'Get-ShowcaseServiceRegistration'
    )
    FunctionsToExport    = @('Invoke-ShowcaseAutoHeal')
    AliasesToExport      = @()
    VariablesToExport    = @()
}
