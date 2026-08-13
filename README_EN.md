# Video Region Cleaner

[简体中文](README.md) | English

[![Windows x64](https://img.shields.io/badge/Windows-x64-0078D4?logo=windows)](https://github.com/instann/video-region-cleaner/releases/latest)
[![macOS](https://img.shields.io/badge/macOS-Apple%20Silicon%20%7C%20Intel-000000?logo=apple)](https://github.com/instann/video-region-cleaner/releases/latest)
[![Offline](https://img.shields.io/badge/processing-100%25%20offline-2ea44f)](#why-use-it)
[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**Select a fixed region on a representative video frame, preview the restoration locally, and export a new video with its audio preserved.** It is designed for fixed labels, timestamps, camera overlays, and review marks in content you own or are authorized to edit.

No upload, no Python installation, and no source-file overwrite.

![Video Region Cleaner with a selected fixed rectangle](docs/screenshots/04_adjusted_1280x720.png)

## Download and use

> [Download the latest release for Windows x64 or macOS (Apple Silicon / Intel)](https://github.com/instann/video-region-cleaner/releases/latest)

1. Download and **fully extract** the archive for your computer:
   - Windows: `VideoRegionCleaner-*-windows-x64-pyinstaller.zip`
   - Apple Silicon Mac (M1/M2/M3/M4 and later): `VideoRegionCleaner-*-macos-arm64.zip`
   - Intel Mac: `VideoRegionCleaner-*-macos-x86_64.zip`
2. Double-click `VideoRegionCleaner.exe` on Windows or `VideoRegionCleaner.app` on macOS.
3. Click **Open Video**, or drop an MP4, MOV, MKV, or WebM file onto the window.
4. Find a representative frame with the timeline, frame-step buttons, or time input.
5. Drag a rectangle over the fixed area. Move, resize, clear, or redraw it as needed.
6. Compare the original, marked, and restored previews, choose a new output path, and export.

The app reports progress, elapsed time, and ETA, and supports cancellation. When the job finishes, you can open the result or its containing folder. The default output is `<source>_clean.mp4`; an incrementing suffix is added when necessary, so existing files are never overwritten.

Current builds are not developer-signed or Apple-notarized, so Windows SmartScreen or macOS Gatekeeper may warn. On first launch on macOS, Control-click the app in Finder, choose **Open**, and confirm. Download only from this repository's Releases page and verify its SHA-256.

## Why use it

- **Fully offline:** media stays on your computer; the app uploads nothing and sends no telemetry.
- **Preview before export:** seek to any representative frame and switch between original, marked-region, and restored views.
- **Source-pixel accuracy:** the rectangle remains in original video coordinates across letterboxing, window scaling, high DPI, landscape, and portrait media.
- **Desktop-friendly workflow:** drag and drop, timeline seeking, eight resize handles, progress, ETA, cancellation, and actionable errors.
- **Reliable export:** streaming OpenCV TELEA processing preserves audio without caching the full video; Windows genuinely probes NVENC, macOS probes VideoToolbox, and either falls back to `libx264`.
- **Verifiable:** the repository includes unit, GUI interaction, end-to-end, and packaged-launch tests using synthetic media.

## Good fit—and not a good fit

Good fit: a small, fixed-position label, timestamp, camera overlay, or internal review mark over a relatively simple background.

Not a good fit: moving subtitles, tracked objects, large obstructions, complex textures, or tasks that require exact recovery of the original pixels. The current release handles **one fixed rectangle** and does not perform object tracking.

## How it works

The app reads the source frame by frame, applies TELEA inpainting only to the selected rectangle and its processing boundary, then asks FFmpeg to encode a new video and mux the source audio. The native hardware encoder (NVENC on Windows, VideoToolbox on macOS) is enabled only after a real encoding probe succeeds; otherwise the app uses CPU `libx264`. Audio that cannot be copied into MP4 is transcoded to AAC. FFprobe validates resolution, frame rate, duration, and audio after export.

## Run from source

Python 3.11 or newer is required. On Windows, use PowerShell:

```powershell
git clone https://github.com/instann/video-region-cleaner.git
cd video-region-cleaner
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pip install -e . --no-deps
powershell -ExecutionPolicy Bypass -File scripts\prepare_ffmpeg.ps1
.\.venv\Scripts\python.exe run_gui.pyw
```

On macOS 13 or newer, use Terminal. Xcode Command Line Tools are required; the script builds pinned official FFmpeg and x264 sources for the current Apple Silicon or Intel architecture:

```bash
git clone https://github.com/instann/video-region-cleaner.git
cd video-region-cleaner
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pip install -e . --no-deps
scripts/prepare_ffmpeg_macos.sh
.venv/bin/python run_gui.pyw
```

Run the tests:

```bash
# macOS
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q
.venv/bin/python scripts/run_e2e.py
```

The compatibility CLI uses the same processing core:

```bash
.venv/bin/python region_cleaner.py examples/demo_overlay.mp4 \
  --region 15,15,330,80 --output examples/demo_overlay_clean.mp4
```

## Build the macOS `.app`

Run this on a Mac with the target architecture; Apple Silicon and Intel builds must be produced separately:

```bash
scripts/build_macos.sh
```

The script builds redistributable native tools from pinned FFmpeg 8.1.2 and x264 sources, creates and ad-hoc signs the `.app`, runs a packaged end-to-end self-test, and writes `release/VideoRegionCleaner-1.0.0-macos-<architecture>.zip` plus its SHA-256. For release signing, set `CODESIGN_IDENTITY` to a Developer ID Application identity; notarization remains a maintainer release step. The repository's `macOS` GitHub Actions workflow builds both architectures.

## Build the Windows x64 distributions

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_pyinstaller.ps1
powershell -ExecutionPolicy Bypass -File scripts\build_nuitka.ps1
powershell -ExecutionPolicy Bypass -File scripts\write_checksums.ps1
```

- PyInstaller: `release/pyinstaller/VideoRegionCleaner/VideoRegionCleaner.exe`
- Nuitka: `release/nuitka/run_gui.dist/VideoRegionCleaner.exe`
- SHA-256: `release/SHA256SUMS.txt`
- Test and packaging evidence: [docs/VERIFICATION_REPORT.md](docs/VERIFICATION_REPORT.md)
- Public-release audit: [docs/PUBLIC_RELEASE_CHECKLIST.md](docs/PUBLIC_RELEASE_CHECKLIST.md)
- Third-party software and licenses: [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)

The build scripts download a pinned FFmpeg 9.0.1 x64 essentials static build and verify the publisher-provided SHA-256 before extraction. Binary packages include the applicable license text and build information. Public distributors remain responsible for reviewing their FFmpeg GPLv3 obligations and source-availability method.

## Known limitations

- One fixed rectangle only; moving regions are not tracked.
- TELEA may blur or smear large obstructions, complex motion, and high-frequency textures.
- Variable-frame-rate input is normalized to constant frame rate using the detected average rate.
- Output is H.264 `yuv420p` MP4; HDR, high bit depth, and color metadata are not fully preserved.
- CPU encoding is used when the platform hardware encoder is unavailable; runtime depends on duration, resolution, CPU, and region complexity.
- Current builds are unsigned and may trigger Windows SmartScreen.
- macOS builds are not notarized and may trigger Gatekeeper on first launch.

## Authorized use, license, and attribution

Use this tool only with content you own or are authorized to edit. You are responsible for applicable laws, contracts, licenses, platform terms, disclosure duties, and attribution requirements. This project does not provide legal advice and is not endorsed by, sponsored by, or affiliated with any platform or trademark owner.

`examples/demo_overlay.mp4` and every documentation screenshot were generated from synthetic project assets. They contain no third-party platform marks or private content.

The project is available under the [MIT License](LICENSE), with upstream attribution in [NOTICE.md](NOTICE.md). FFmpeg is distributed as a separate process under the GPLv3 terms supplied with its build; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

If this project saves you from repetitive frame-by-frame work, consider giving it a **Star**. Reproducible issue reports and focused pull requests are welcome too.
