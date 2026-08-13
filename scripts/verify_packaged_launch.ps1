param(
    [string]$EvidencePath = (Join-Path $PSScriptRoot '..\release\PACKAGED_LAUNCH_EVIDENCE.json')
)

$ErrorActionPreference = 'Stop'
$Project = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$Chinese = "$([char]0x4e2d)$([char]0x6587)"
$Spaces = "$([char]0x7a7a)$([char]0x683c)"
$StageRoot = Join-Path $env:TEMP "VRC clean launch $Chinese $Spaces"
if (Test-Path -LiteralPath $StageRoot) {
    $ResolvedStage = (Resolve-Path -LiteralPath $StageRoot).Path
    $ResolvedTemp = (Resolve-Path -LiteralPath $env:TEMP).Path
    if (-not $ResolvedStage.StartsWith($ResolvedTemp, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Unsafe staging path: $ResolvedStage"
    }
    Remove-Item -LiteralPath $ResolvedStage -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $StageRoot | Out-Null

$Packages = @(
    @{ Name='PyInstaller'; Source=(Join-Path $Project 'release\pyinstaller\VideoRegionCleaner') },
    @{ Name='Nuitka'; Source=(Join-Path $Project 'release\nuitka\run_gui.dist') }
)
$OriginalPath = $env:PATH
$OriginalPythonHome = $env:PYTHONHOME
$OriginalPythonPath = $env:PYTHONPATH
$Evidence = @()
try {
    $env:PATH = 'C:\Windows\System32;C:\Windows'
    Remove-Item Env:PYTHONHOME -ErrorAction SilentlyContinue
    Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
    foreach ($Package in $Packages) {
        $Target = Join-Path $StageRoot $Package.Name
        Copy-Item -LiteralPath $Package.Source -Destination $Target -Recurse
        $Exe = Join-Path $Target 'VideoRegionCleaner.exe'
        $Started = Get-Date
        $Process = Start-Process -FilePath $Exe -WorkingDirectory 'C:\Windows\System32' -PassThru
        $Deadline = (Get-Date).AddSeconds(30)
        do {
            Start-Sleep -Milliseconds 500
            $Process.Refresh()
        } while (-not $Process.HasExited -and $Process.MainWindowHandle -eq 0 -and (Get-Date) -lt $Deadline)
        $ReadySeconds = ((Get-Date) - $Started).TotalSeconds
        $Record = [ordered]@{
            package = $Package.Name
            executable = "%TEMP%/VRC clean launch $Chinese $Spaces/$($Package.Name)/VideoRegionCleaner.exe"
            started_at = $Started.ToString('o')
            alive_when_checked = (-not $Process.HasExited)
            window_ready_seconds = [Math]::Round($ReadySeconds, 3)
            window_title = $Process.MainWindowTitle
            nonzero_window_handle = ($Process.MainWindowHandle -ne 0)
            pythonhome_unset = (-not (Test-Path Env:PYTHONHOME))
            pythonpath_unset = (-not (Test-Path Env:PYTHONPATH))
            minimal_path = $env:PATH
            working_directory = 'C:\Windows\System32'
        }
        $Evidence += [pscustomobject]$Record
        if (-not $Process.HasExited) {
            $null = $Process.CloseMainWindow()
            if (-not $Process.WaitForExit(5000)) { Stop-Process -Id $Process.Id -Force }
        }
        if (-not $Record.alive_when_checked -or -not $Record.nonzero_window_handle) {
            throw "$($Package.Name) packaged launch verification failed"
        }
    }
} finally {
    $env:PATH = $OriginalPath
    if ($null -eq $OriginalPythonHome) { Remove-Item Env:PYTHONHOME -ErrorAction SilentlyContinue } else { $env:PYTHONHOME = $OriginalPythonHome }
    if ($null -eq $OriginalPythonPath) { Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue } else { $env:PYTHONPATH = $OriginalPythonPath }
}
$EvidencePath = [IO.Path]::GetFullPath($EvidencePath)
$Evidence | ConvertTo-Json -Depth 4 | Set-Content -Encoding UTF8 -LiteralPath $EvidencePath
$Evidence | Format-Table
Write-Host "Wrote $EvidencePath"
