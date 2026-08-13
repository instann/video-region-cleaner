$ErrorActionPreference = 'Stop'
$Project = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$EvidenceRoot = Join-Path $Project 'release\packaged_e2e'
New-Item -ItemType Directory -Force -Path $EvidenceRoot | Out-Null
$InputFile = Join-Path $Project 'examples\demo_overlay.mp4'
$Packages = @(
    @{ Name='pyinstaller'; Exe=(Join-Path $Project 'release\pyinstaller\VideoRegionCleaner\VideoRegionCleaner.exe') },
    @{ Name='nuitka'; Exe=(Join-Path $Project 'release\nuitka\run_gui.dist\VideoRegionCleaner.exe') }
)
$OriginalPath = $env:PATH
$OriginalPythonHome = $env:PYTHONHOME
$OriginalPythonPath = $env:PYTHONPATH
try {
    $env:PATH = 'C:\Windows\System32;C:\Windows'
    Remove-Item Env:PYTHONHOME -ErrorAction SilentlyContinue
    Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
    foreach ($Package in $Packages) {
        $PackageOutputRoot = Join-Path $EvidenceRoot $Package.Name
        New-Item -ItemType Directory -Force -Path $PackageOutputRoot | Out-Null
        Get-ChildItem -LiteralPath $PackageOutputRoot -File -Filter '*.mp4' | Remove-Item -Force
        $Output = Join-Path $PackageOutputRoot '__unicode_output__.mp4'
        $Evidence = Join-Path $EvidenceRoot "$($Package.Name)_E2E_RESULT.json"
        if (Test-Path -LiteralPath $Output) { Remove-Item -LiteralPath $Output -Force }
        if (Test-Path -LiteralPath $Evidence) { Remove-Item -LiteralPath $Evidence -Force }
        $Arguments = @('--packaged-self-test', "`"$InputFile`"", "`"$Output`"", "`"$Evidence`"")
        $Process = Start-Process -FilePath $Package.Exe -ArgumentList $Arguments -WorkingDirectory 'C:\Windows\System32' -PassThru -Wait
        if ($Process.ExitCode -ne 0 -or -not (Test-Path -LiteralPath $Evidence)) {
            throw "$($Package.Name) packaged E2E failed with exit code $($Process.ExitCode)"
        }
        $Result = Get-Content -Raw -LiteralPath $Evidence | ConvertFrom-Json
        if (-not $Result.ok -or -not $Result.has_audio -or $Result.frames -ne 144) {
            throw "$($Package.Name) packaged E2E evidence failed validation"
        }
        $ExpectedUnicodeOutput = Join-Path $PackageOutputRoot "$([char]0x4e2d)$([char]0x6587) $([char]0x8f93)$([char]0x51fa).mp4"
        if (-not (Test-Path -LiteralPath $ExpectedUnicodeOutput)) {
            throw "$($Package.Name) did not create the expected Chinese output path"
        }
        $Result | Format-List
    }
} finally {
    $env:PATH = $OriginalPath
    if ($null -eq $OriginalPythonHome) { Remove-Item Env:PYTHONHOME -ErrorAction SilentlyContinue } else { $env:PYTHONHOME = $OriginalPythonHome }
    if ($null -eq $OriginalPythonPath) { Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue } else { $env:PYTHONPATH = $OriginalPythonPath }
}
