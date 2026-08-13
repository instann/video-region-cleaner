$ErrorActionPreference = 'Stop'
$Project = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$Packages = @(
    @{ Name='PyInstaller'; Exe=(Join-Path $Project 'release\pyinstaller\VideoRegionCleaner\VideoRegionCleaner.exe') },
    @{ Name='Nuitka'; Exe=(Join-Path $Project 'release\nuitka\run_gui.dist\VideoRegionCleaner.exe') }
)
$Records = foreach ($Package in $Packages) {
    $Bytes = [IO.File]::ReadAllBytes($Package.Exe)
    $PeOffset = [BitConverter]::ToInt32($Bytes, 0x3c)
    $Machine = [BitConverter]::ToUInt16($Bytes, $PeOffset + 4)
    $Version = (Get-Item -LiteralPath $Package.Exe).VersionInfo
    $Signature = Get-AuthenticodeSignature -LiteralPath $Package.Exe
    [pscustomobject][ordered]@{
        package = $Package.Name
        executable = "$($Package.Name)/VideoRegionCleaner.exe"
        pe_machine_hex = ('0x{0:X4}' -f $Machine)
        architecture = $(if ($Machine -eq 0x8664) { 'AMD64' } else { 'unexpected' })
        file_version = $Version.FileVersion
        product_version = $Version.ProductVersion
        signature_status = [string]$Signature.Status
    }
}
if ($Records.Where({$_.architecture -ne 'AMD64'}).Count -gt 0) { throw 'A release EXE is not AMD64.' }
$Output = Join-Path $Project 'release\RELEASE_METADATA.json'
$Records | ConvertTo-Json -Depth 3 | Set-Content -Encoding UTF8 -LiteralPath $Output
$Records | Format-Table
Write-Host "Wrote $Output"
