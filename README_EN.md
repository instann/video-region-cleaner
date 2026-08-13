# Video Region Cleaner

[简体中文](README.md) | English

[![Download Windows x64](https://img.shields.io/badge/Download-Windows%20x64-1686b8?style=for-the-badge&logo=windows&logoColor=white)](https://github.com/instann/video-region-cleaner/releases/latest)
[![Local processing](https://img.shields.io/badge/Video%20processing-100%25%20local-1f9d55?style=for-the-badge)](#your-video-stays-on-your-computer)
[![MIT](https://img.shields.io/badge/License-MIT-5c6bc0?style=for-the-badge)](LICENSE)

> **Select one fixed area in a video, preview the restoration, then export a new video with audio.**
>
> Built for fixed labels, timecodes, camera overlays, and internal review marks in content you own or are authorized to edit. No upload and no source-file overwrite.

![Video Region Cleaner adjusting a fixed rectangle on a video frame](docs/screenshots/04_adjusted_1280x720.png)

![Three-step workflow from local video to exported result](docs/assets/three-step-workflow.svg)

## Download, then start in 3 steps

### 1. Download and extract everything

[Download the latest Windows x64 release](https://github.com/instann/video-region-cleaner/releases/latest) → choose `VideoRegionCleaner-*-windows-x64-pyinstaller.zip`.

Extract the entire ZIP. **Do not move `VideoRegionCleaner.exe` out of its folder**; it needs the runtime components beside it.

> Current Windows releases are unsigned, so SmartScreen may warn on first launch. Download only from this repository's Releases page and verify the archive with `SHA256SUMS.txt` from the same release.

### 2. Double-click to run

Open `VideoRegionCleaner.exe` in the extracted folder. Python and FFmpeg are already included.

### 3. Drop a video, select, and export

Drop an MP4, MOV, MKV, or WebM file onto the window. Find a representative frame, draw the rectangle, check the restored preview, and select **Export New Video**.

The default output is `<source>_clean.mp4`. If that name already exists, the app adds a number instead of overwriting any file.

## What problem does it solve?

When a visual element stays in the same place throughout a video, cleaning it frame by frame is slow and difficult to verify. Video Region Cleaner turns that into one reviewable action:

- Find the area on any frame, then move, resize, clear, or redraw the rectangle.
- Compare original, marked-region, and restored previews before exporting.
- Stream the full video, preserve audio, show progress, elapsed time, and ETA, and cancel safely.

![Local processing: local video enters the desktop app and exits as a new file](docs/assets/local-first.svg)

## Your video stays on your computer

- **No media upload and no telemetry.**
- **The source is never modified.** Every export is a new file.
- **Accurate coordinates.** The region remains in source-video pixels across letterboxing, scaling, high DPI, landscape, and portrait media.
- **Reliable export.** Windows performs a real NVENC probe and falls back to `libx264` when needed. Audio that cannot be remuxed into MP4 falls back to AAC.

## Good fit—and not a good fit

It is a good fit for a small, fixed-position visual area over a relatively simple background.

The current version handles **one fixed rectangle** only. It does not track moving objects or handle dynamic subtitles, and it does not promise original-pixel recovery for large obstructions, complex motion, or high-frequency texture.

## macOS

The source supports Apple Silicon and Intel builds, including VideoToolbox probing. The latest release does not yet include a signed and notarized macOS app. To use it on a Mac now, build from source using the instructions below.

<details>
<summary><strong>Maintainer and source details: run, test, build, and verify</strong></summary>

### Run from source on Windows

```powershell
git clone https://github.com/instann/video-region-cleaner.git
cd video-region-cleaner
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pip install -e . --no-deps
powershell -ExecutionPolicy Bypass -File scripts\prepare_ffmpeg.ps1
.\.venv\Scripts\python.exe run_gui.pyw
```

### Build from source on macOS

macOS 13+, Python 3.11+, and Xcode Command Line Tools are required. Build Apple Silicon and Intel packages separately on their target architecture.

```bash
git clone https://github.com/instann/video-region-cleaner.git
cd video-region-cleaner
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pip install -e . --no-deps
scripts/build_macos.sh
```

### Test and build the Windows distributions

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts\run_e2e.py
powershell -ExecutionPolicy Bypass -File scripts\build_pyinstaller.ps1
powershell -ExecutionPolicy Bypass -File scripts\build_nuitka.ps1
powershell -ExecutionPolicy Bypass -File scripts\write_checksums.ps1
```

See [docs/VERIFICATION_REPORT.md](docs/VERIFICATION_REPORT.md) for test and packaging evidence and [docs/PUBLIC_RELEASE_CHECKLIST.md](docs/PUBLIC_RELEASE_CHECKLIST.md) for the public-release checklist. The SHA-256 values for Windows artifacts are in `SHA256SUMS.txt` in the same release.

Compatibility CLI:

```powershell
.\.venv\Scripts\python.exe region_cleaner.py examples\demo_overlay.mp4 `
  --region 15,15,330,80 --output examples\demo_overlay_clean.mp4
```

</details>

## Contributors and acknowledgement

See [CONTRIBUTORS.md](CONTRIBUTORS.md). [@instann](https://github.com/instann) maintains the project, [@modengsir](https://github.com/modengsir) contributed macOS support, and [OpenAI Codex](https://openai.com/codex/) was used as an AI coding collaborator for implementation, testing, and documentation.

## Authorized use and license

Use this tool only with content you own or are authorized to edit. You are responsible for applicable laws, contracts, licenses, platform terms, disclosure duties, and attribution requirements. This project does not provide legal advice and is not endorsed by, sponsored by, or affiliated with any platform or trademark owner.

The demo video, screenshots, and illustrations in this repository are synthetic or original project assets. They contain no third-party platform marks or private media.

The project is available under the [MIT License](LICENSE), with upstream attribution in [NOTICE.md](NOTICE.md). FFmpeg is distributed as a separate process under the GPLv3 terms supplied with its build; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
