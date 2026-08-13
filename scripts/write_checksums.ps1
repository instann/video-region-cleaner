$ErrorActionPreference = 'Stop'
$Project = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$Release = Join-Path $Project 'release'
$Output = Join-Path $Release 'SHA256SUMS.txt'
$Files = @(
    Get-ChildItem -LiteralPath $Release -File -Filter '*.zip'
    Get-Item -LiteralPath (Join-Path $Release 'pyinstaller\VideoRegionCleaner\VideoRegionCleaner.exe')
    Get-Item -LiteralPath (Join-Path $Release 'nuitka\run_gui.dist\VideoRegionCleaner.exe')
)
$Lines = foreach ($File in $Files) {
    $Hash = (Get-FileHash -LiteralPath $File.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
    $Relative = $File.FullName.Substring($Release.Length).TrimStart('\').Replace('\','/')
    "$Hash  $Relative"
}
$Lines | Set-Content -Encoding ascii -LiteralPath $Output
Write-Host "Wrote $Output"
