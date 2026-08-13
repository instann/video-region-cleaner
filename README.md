# Video Region Cleaner

A local video restoration utility for selecting a fixed rectangular overlay
region and reconstructing the pixels behind it. The repository currently
contains a working command-line baseline and a synthetic demonstration video.

The intended desktop application will let a user:

1. Open a local video.
2. Seek to a representative frame.
3. Draw or resize a rectangle over a fixed overlay.
4. Preview the selected coordinates and restoration result.
5. Export a new video while preserving the source file and audio.

## Scope

This software is intended for editing content that you own or are authorized
to modify, including removal of your own test labels, timestamps, camera
overlays, internal review marks, and similar fixed visual elements. Users are
responsible for complying with applicable law, licenses, contracts, platform
terms, disclosure requirements, and attribution obligations.

This project is independent and is not affiliated with or endorsed by any
platform or trademark owner. It does not provide legal advice and does not
claim that every use of overlay removal is permitted.

## CLI baseline

Requirements: Python 3.9+ and FFmpeg on `PATH`.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe .\region_cleaner.py `
  .\examples\demo_overlay.mp4 `
  --region 15,15,330,80 `
  --output .\examples\demo_overlay_clean.mp4
```

The input file is never overwritten. NVIDIA NVENC is selected when a runtime
probe succeeds; otherwise the exporter uses CPU `libx264`.

## Demo media

`examples/demo_overlay.mp4` is synthetic and was generated locally for this
repository. It contains a generic `DEMO OVERLAY`, not a third-party logo or
platform mark.

## Current limitations

- The baseline is designed for a fixed overlay in one rectangular region.
- OpenCV TELEA works best over simple or moderately textured backgrounds.
- Dynamic subtitles and large moving occlusions need a dedicated video
  inpainting model and are outside the initial desktop application scope.
- The future GUI and packaged Windows executable are not implemented yet.

## License and attribution

MIT. See `LICENSE` and `NOTICE.md`.
