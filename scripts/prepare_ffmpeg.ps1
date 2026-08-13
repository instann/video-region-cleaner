param(
    [string]$VendorDir = (Join-Path $PSScriptRoot '..\vendor\ffmpeg')
)

$ErrorActionPreference = 'Stop'
$VendorDir = [IO.Path]::GetFullPath($VendorDir)
$Version = '9.0.1'
$AssetName = "ffmpeg-$Version-essentials_build.zip"
$Archive = Join-Path $VendorDir $AssetName
$ChecksumFile = Join-Path $VendorDir "$AssetName.sha256"
$DownloadUrl = "https://github.com/GyanD/codexffmpeg/releases/download/$Version/$AssetName"
$ChecksumUrl = 'https://www.gyan.dev/ffmpeg/builds/packages/ffmpeg-9.0.1-essentials_build.zip.sha256'

New-Item -ItemType Directory -Force -Path $VendorDir | Out-Null
if (-not (Test-Path -LiteralPath $ChecksumFile)) {
    Invoke-WebRequest -Uri $ChecksumUrl -OutFile $ChecksumFile
}
if (-not (Test-Path -LiteralPath $Archive)) {
    Invoke-WebRequest -Uri $DownloadUrl -OutFile $Archive
}
$Expected = (Get-Content -Raw -LiteralPath $ChecksumFile).Trim().Split(' ')[0].ToUpperInvariant()
$Actual = (Get-FileHash -LiteralPath $Archive -Algorithm SHA256).Hash
if ($Actual -ne $Expected) {
    throw "FFmpeg archive checksum mismatch. Expected $Expected, got $Actual"
}

$Extracted = Join-Path $VendorDir 'extracted'
if (Test-Path -LiteralPath $Extracted) {
    $ResolvedExtracted = (Resolve-Path -LiteralPath $Extracted).Path
    if (-not $ResolvedExtracted.StartsWith($VendorDir, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Unsafe FFmpeg extraction path: $ResolvedExtracted"
    }
    Remove-Item -LiteralPath $Extracted -Recurse -Force
}
Expand-Archive -LiteralPath $Archive -DestinationPath $Extracted -Force
$Root = Get-ChildItem -LiteralPath $Extracted -Directory | Select-Object -First 1
if (-not $Root) { throw 'FFmpeg archive layout was not recognized.' }
$Bin = Join-Path $VendorDir 'bin'
$Doc = Join-Path $VendorDir 'doc'
New-Item -ItemType Directory -Force -Path $Bin,$Doc | Out-Null
Copy-Item -LiteralPath (Join-Path $Root.FullName 'bin\ffmpeg.exe') -Destination $Bin -Force
Copy-Item -LiteralPath (Join-Path $Root.FullName 'bin\ffprobe.exe') -Destination $Bin -Force
Copy-Item -LiteralPath (Join-Path $Root.FullName 'LICENSE') -Destination (Join-Path $Doc 'FFMPEG_BUILD_LICENSE.txt') -Force
if (Test-Path -LiteralPath (Join-Path $Root.FullName 'README.txt')) {
    Copy-Item -LiteralPath (Join-Path $Root.FullName 'README.txt') -Destination (Join-Path $Doc 'FFMPEG_BUILD_README.txt') -Force
}
& (Join-Path $Bin 'ffmpeg.exe') -version | Select-Object -First 12 | Set-Content -Encoding UTF8 (Join-Path $Doc 'FFMPEG_VERSION_AND_CONFIGURATION.txt')
$Actual.ToLowerInvariant() | Set-Content -NoNewline -Encoding ascii (Join-Path $Doc 'FFMPEG_ARCHIVE_SHA256.txt')
$ResolvedExtracted = (Resolve-Path -LiteralPath $Extracted).Path
if (-not $ResolvedExtracted.StartsWith($VendorDir, [StringComparison]::OrdinalIgnoreCase)) {
    throw "Unsafe FFmpeg extraction path: $ResolvedExtracted"
}
Remove-Item -LiteralPath $ResolvedExtracted -Recurse -Force
Write-Host "Verified FFmpeg archive and prepared $Bin"
