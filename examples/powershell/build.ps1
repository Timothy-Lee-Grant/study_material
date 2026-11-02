#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Builds the whole solution and publishes the PowerShell module to ./out/Showcase.
.EXAMPLE
    ./build.ps1
    Import-Module ./out/Showcase/Showcase.psd1
#>
[CmdletBinding()]
param([switch] $Clean)

$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$out  = Join-Path $root 'out/Showcase'

if (Get-Module Showcase) {
    # A .NET assembly can't be unloaded from a running process. The new dll won't be used
    # until you open a fresh pwsh session.
    Write-Warning 'The Showcase module is loaded in this session. Start a new pwsh after building.'
}

if ($Clean -and (Test-Path $out)) { Remove-Item $out -Recurse -Force }

dotnet build (Join-Path $root 'PowerShellShowcase.sln') -c Release
if ($LASTEXITCODE -ne 0) { throw "dotnet build failed ($LASTEXITCODE)" }

# publish = build + copy every runtime dependency (Showcase.Core.dll, Microsoft.Extensions.DependencyInjection*.dll)
# plus the .psd1/.psm1/.ps1xml files into one folder: that folder IS the module.
dotnet publish (Join-Path $root 'src/Showcase.PowerShell/Showcase.PowerShell.csproj') -c Release -o $out --no-build
if ($LASTEXITCODE -ne 0) { throw "dotnet publish failed ($LASTEXITCODE)" }

Write-Host ''
Write-Host "Module published to $out" -ForegroundColor Green
Get-ChildItem $out | Format-Table Name, Length -AutoSize
Write-Host 'Terminal 1:  dotnet run --project src/Showcase.App -c Release'
Write-Host "Terminal 2:  Import-Module $out/Showcase.psd1; Get-ShowcaseDevice"
