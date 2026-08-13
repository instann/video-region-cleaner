# Third-party notices

## Application dependencies

- PySide6 6.11.1 — LGPLv3/GPLv3/commercial dual licensing. The release uses the unmodified dynamically linked Qt libraries produced by the standard PySide6 wheel.
- OpenCV Python headless 4.14.0.94 — Apache License 2.0; used for frame decode and TELEA inpainting.
- NumPy 2.4.6 — BSD-3-Clause; used for image arrays and streaming mean calculation.
- Python 3.11.5 runtime — Python Software Foundation License; embedded in standalone packages.
- PyInstaller 6.22.0 — GPLv2-or-later with a bootloader exception; build-time packager only.
- Nuitka 2.8.10 — Apache License 2.0; build-time compiler only.

The original OpenCV TELEA pipeline attribution remains in `NOTICE.md` and `LICENSE`.

## Bundled FFmpeg build

- Component: FFmpeg 9.0.1 essentials build, Windows x64 static
- Build distributor: Gyan Doshi / `GyanD/codexffmpeg`
- Fixed release asset: `ffmpeg-9.0.1-essentials_build.zip`
- Release: `https://github.com/GyanD/codexffmpeg/releases/tag/9.0.1`
- Upstream source commit recorded by distributor: `FFmpeg/FFmpeg@bf1b838f2a`
- Archive SHA-256: `fec81ae03971d9dd4be3ebe02e263bd2ec1d789483f931bdba5f5715e65da2e9`
- Build license: GPLv3 (because the essentials build includes GPL libraries such as libx264)

The release directory preserves the distributor's complete `LICENSE`, `README.txt`, FFmpeg version/configuration output, and archive hash in `ffmpeg/doc/`. FFmpeg and FFprobe run as separate executables through argument arrays; they are not imported or linked into the Python application.

Each release directory also includes GNU GPLv3/LGPLv3 texts plus OpenCV and NumPy license bundles under `licenses/`.

Before public distribution, the maintainer must confirm the preferred GPLv3 source-offer mechanism and publish the corresponding source/build information alongside the binary release. This file is an engineering record, not legal advice.
