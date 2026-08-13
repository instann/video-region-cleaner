# Verification report — 1.0.0

Date: 2026-08-13 (Asia/Shanghai)  
Host: Windows x64, Python 3.11.5 for development only

## macOS compatibility verification

Date: 2026-08-14 (Asia/Shanghai)
Host: Apple Silicon arm64, macOS 26.2, Python 3.12.13 for development only

- `QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q`: `36 passed`.
- Pinned FFmpeg 8.1.2 and x264 sources were SHA-256 verified and compiled as native arm64 binaries with VideoToolbox and `libx264`; the build rejects `--enable-nonfree`.
- `scripts/run_e2e.py` processed all 144 frames and FFprobe verified 960×540, 24 fps, 6 seconds, and an audio stream. VideoToolbox was unavailable in this session, and the tested runtime fallback selected `libx264`.
- `scripts/build_macos.sh` generated and ad-hoc signed `VideoRegionCleaner.app`; `codesign --verify --deep --strict` passed and both the app executable and bundled FFmpeg report arm64.
- The packaged executable independently processed the synthetic sample to a Chinese output path, preserved audio, and wrote a successful `E2E_RESULT.json` without invoking the development Python executable.

The GitHub Actions matrix repeats the same tests and package self-test on Apple Silicon and Intel runners. Clean-machine Gatekeeper testing, Developer ID signing, notarization, and stapling remain maintainer release steps.

## Automated tests

Command:

```powershell
$env:QT_QPA_PLATFORM='offscreen'
.\.venv\Scripts\python.exe -m pytest -q
```

Result: `31 passed` after the final source changes. Coverage includes landscape and portrait aspect ratios, preview letterboxing, rotation metadata, resize, 150% High-DPI logical-coordinate behavior, clipping, source-coordinate round trips, output collision/source protection, Chinese and special-character paths, PyInstaller/Nuitka application-root resolution, actual NVENC probe semantics, OpenCV preview, GUI draw/move/eight-handle resize and preview-state consistency, real background-worker export/cancellation cleanup, and synthetic end-to-end export.

## Synthetic end-to-end export

Input: repository-owned `examples/demo_overlay.mp4`  
Region: `x=15,y=15,width=330,height=80`  
Command: `.\.venv\Scripts\python.exe scripts\run_e2e.py`

- Frames: 144
- Wall time: 6.038 seconds
- Pipeline time: 6.038 seconds
- Runtime NVENC result: unavailable on this host; automatic CPU fallback selected `libx264`
- Verified output: 960×540, 24.000 fps, 6.000 seconds, audio stream present
- Evidence: `release/e2e/E2E_RESULT.json`

The E2E pytest repeats export to a Chinese/special-character path, checks source bytes are unchanged, and validates fallback state.

## GUI automation and visual inspection

`scripts/capture_gui_states.py` generated and visual inspection checked these states using only the repository's synthetic media:

- initial blank, loaded video, dragged selection, adjusted selection
- current-frame restoration preview
- processing with progress/ETA, cancelled, success, readable failure
- 1280×720, 1920×1080 processing layout, and 150% High-DPI scaling

Evidence is under `docs/screenshots/`. A CJK-capable Windows UI font is explicitly selected so Chinese text remains readable in offscreen and standard Windows sessions.

## Packaging and launch evidence

PyInstaller 6.22.0 and Nuitka 2.8.10 both produced Windows x64 standalone directories. Each contains an EXE, Python/Qt/OpenCV runtime files, verified FFmpeg/FFprobe, project LICENSE/NOTICE/README, and FFmpeg license/configuration records.

Direct host launch checks started each EXE without Python on its command line, waited, and verified a live top-level window:

| Package | Process alive | Window title | Nonzero window handle |
|---|---:|---|---:|
| PyInstaller | yes | Video Region Cleaner | yes |
| Nuitka | yes | Video Region Cleaner | yes |

An additional packaged-runtime check copied each complete release to a temporary path containing Chinese characters and spaces, cleared `PYTHONHOME`/`PYTHONPATH`, reduced `PATH` to Windows system directories, used `C:\Windows\System32` as the working directory, launched each EXE, and polled up to 30 seconds for a live titled window. Machine-readable evidence, including actual window-ready time, is in `release/PACKAGED_LAUNCH_EVIDENCE.json`.

Both packaged EXEs also ran their opt-in release self-test under the same cleared Python environment and minimal PATH. Each independently located its own bundled FFmpeg/FFprobe, processed all 144 synthetic frames with `libx264`, and verified 960×540, 24.000 fps, 6.000 seconds, and an audio stream. Evidence is in `release/packaged_e2e/*_E2E_RESULT.json`.

PE metadata inspection verified both final executables use machine type `0x8664` (AMD64) and embed product/file version 1.0.0. Both are intentionally unsigned in this engineering build; see `release/RELEASE_METADATA.json` and the signing decision below.

The app's bundled-runtime resolution was also exercised by these launches. The current host does not expose Windows Sandbox/Hyper-V without elevation, so a disposable clean Windows VM could not be launched automatically in this session. This is the one acceptance item that still requires a maintainer-run clean Windows VM before public release; the public checklist records it as open rather than claiming success.

## FFmpeg provenance

The fixed 9.0.1 x64 essentials ZIP was downloaded from its signed GitHub Release. Its locally computed SHA-256 exactly matched the distributor value:

`fec81ae03971d9dd4be3ebe02e263bd2ec1d789483f931bdba5f5715e65da2e9`

The archive and extraction staging directory are ignored; only the needed binaries and provenance/license records are used for local release builds.

## Known limitations and release decisions

See README for technical limitations. Human decisions still required before a public release:

1. Run both release directories in a genuinely clean Windows 10/11 x64 VM and archive screenshots/logs.
2. Choose and apply Authenticode signing, or consciously publish unsigned with SmartScreen guidance.
3. Complete antivirus scanning and record engine/date/results.
4. Confirm the GPLv3 source-offer/source-bundle mechanism for the exact FFmpeg build.
5. Review repository history and final release assets for sensitive data immediately before making the repository public.
