param([string]$Python = (Join-Path $PSScriptRoot '..\.venv\Scripts\python.exe'))

$ErrorActionPreference = 'Stop'
$Project = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$Python = [IO.Path]::GetFullPath($Python)
if (-not (Test-Path -LiteralPath (Join-Path $Project 'vendor\ffmpeg\bin\ffmpeg.exe'))) {
    & (Join-Path $PSScriptRoot 'prepare_ffmpeg.ps1')
}
$Output = Join-Path $Project 'release\nuitka'
New-Item -ItemType Directory -Force -Path $Output | Out-Null
Push-Location $Project
try {
    & $Python -m nuitka --standalone --assume-yes-for-downloads --enable-plugin=pyside6 `
        --windows-console-mode=disable --output-filename=VideoRegionCleaner.exe `
        --product-name='Video Region Cleaner' --file-description='Video Region Cleaner desktop application' `
        --product-version=1.0.0 --file-version=1.0.0 --copyright='Copyright (c) 2026 instann' `
        --output-dir=$Output --remove-output --include-package=video_region_cleaner `
        (Join-Path $Project 'run_gui.pyw')
    if ($LASTEXITCODE -ne 0) { throw "Nuitka failed with exit code $LASTEXITCODE" }
} finally { Pop-Location }
$Release = Join-Path $Output 'run_gui.dist'
New-Item -ItemType Directory -Force -Path (Join-Path $Release 'ffmpeg\bin'),(Join-Path $Release 'ffmpeg\doc') | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $Release 'licenses\opencv'),(Join-Path $Release 'licenses\numpy') | Out-Null
Copy-Item -LiteralPath (Join-Path $Project 'vendor\ffmpeg\bin\ffmpeg.exe') -Destination (Join-Path $Release 'ffmpeg\bin') -Force
Copy-Item -LiteralPath (Join-Path $Project 'vendor\ffmpeg\bin\ffprobe.exe') -Destination (Join-Path $Release 'ffmpeg\bin') -Force
Copy-Item -Path (Join-Path $Project 'vendor\ffmpeg\doc\*') -Destination (Join-Path $Release 'ffmpeg\doc') -Force
Copy-Item -LiteralPath (Join-Path $Project 'LICENSE'),(Join-Path $Project 'NOTICE.md'),(Join-Path $Project 'README.md'),(Join-Path $Project 'THIRD_PARTY_NOTICES.md') -Destination $Release -Force
Copy-Item -LiteralPath (Join-Path $Project 'packaging\licenses\LGPL-3.0.txt'),(Join-Path $Project 'packaging\licenses\GPL-3.0.txt') -Destination (Join-Path $Release 'licenses') -Force
$PythonBase = (& $Python -c 'import sys; print(sys.base_prefix)').Trim()
Copy-Item -LiteralPath (Join-Path $PythonBase 'LICENSE_PYTHON.txt') -Destination (Join-Path $Release 'licenses\PYTHON_LICENSE.txt') -Force
Copy-Item -LiteralPath (Join-Path $Project '.venv\Lib\site-packages\cv2\LICENSE.txt'),(Join-Path $Project '.venv\Lib\site-packages\cv2\LICENSE-3RD-PARTY.txt') -Destination (Join-Path $Release 'licenses\opencv') -Force
Copy-Item -Path (Join-Path $Project '.venv\Lib\site-packages\numpy-*.dist-info\licenses\*') -Destination (Join-Path $Release 'licenses\numpy') -Recurse -Force
Write-Host "Nuitka release: $Release"
