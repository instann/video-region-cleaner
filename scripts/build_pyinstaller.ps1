param([string]$Python = (Join-Path $PSScriptRoot '..\.venv\Scripts\python.exe'))

$ErrorActionPreference = 'Stop'
$Project = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$Python = [IO.Path]::GetFullPath($Python)
if (-not (Test-Path -LiteralPath (Join-Path $Project 'vendor\ffmpeg\bin\ffmpeg.exe'))) {
    & (Join-Path $PSScriptRoot 'prepare_ffmpeg.ps1')
}
& $Python -m PyInstaller --noconfirm --clean (Join-Path $Project 'packaging\video_region_cleaner.spec') `
    --distpath (Join-Path $Project 'release\pyinstaller') --workpath (Join-Path $Project 'build\pyinstaller')
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed with exit code $LASTEXITCODE" }
$Release = Join-Path $Project 'release\pyinstaller\VideoRegionCleaner'
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
Write-Host "PyInstaller release: $Release"
