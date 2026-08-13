#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT="$(cd "$SCRIPT_DIR/.." && pwd)"
PYTHON="${1:-$PROJECT/.venv/bin/python3}"
VERSION="1.0.0"

if [[ "$(uname -s)" != "Darwin" ]]; then
    echo "macOS packages must be built on macOS." >&2
    exit 1
fi
if [[ ! -x "$PYTHON" ]]; then
    echo "Python was not found at $PYTHON. Create .venv with Python 3.11+ first." >&2
    exit 1
fi
"$PYTHON" -c 'import sys; assert sys.version_info >= (3, 11), "Python 3.11 or newer is required"'

"$SCRIPT_DIR/prepare_ffmpeg_macos.sh"
PYINSTALLER_CONFIG_DIR="$PROJECT/build/pyinstaller-config" \
"$PYTHON" -m PyInstaller --noconfirm --clean \
    "$PROJECT/packaging/video_region_cleaner_macos.spec" \
    --distpath "$PROJECT/release/macos" \
    --workpath "$PROJECT/build/pyinstaller-macos"

APP="$PROJECT/release/macos/VideoRegionCleaner.app"
if [[ ! -d "$APP" ]]; then
    echo "PyInstaller did not create $APP" >&2
    exit 1
fi

SITE_PACKAGES="$(
    "$PYTHON" -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])'
)"
LICENSE_DIR="$APP/Contents/Resources/licenses"
mkdir -p "$LICENSE_DIR/opencv" "$LICENSE_DIR/numpy"
python_license="$(
    "$PYTHON" -c 'import sys; from pathlib import Path; print(Path(sys.base_prefix) / "lib" / ("python%d.%d" % sys.version_info[:2]) / "LICENSE.txt")'
)"
if [[ ! -f "$python_license" ]]; then
    echo "Python license was not found at $python_license" >&2
    exit 1
fi
cp "$python_license" "$LICENSE_DIR/PYTHON_LICENSE.txt"
cp "$SITE_PACKAGES/cv2/LICENSE.txt" "$LICENSE_DIR/opencv/LICENSE.txt"
cp "$SITE_PACKAGES/cv2/LICENSE-3RD-PARTY.txt" \
    "$LICENSE_DIR/opencv/LICENSE-3RD-PARTY.txt"
numpy_license="$(find "$SITE_PACKAGES" -path '*/numpy-*.dist-info/licenses/LICENSE.txt' -print -quit)"
if [[ -z "$numpy_license" ]]; then
    echo "NumPy license was not found under $SITE_PACKAGES" >&2
    exit 1
fi
cp "$numpy_license" "$LICENSE_DIR/numpy/LICENSE.txt"

IDENTITY="${CODESIGN_IDENTITY:--}"
if [[ "$IDENTITY" == "-" ]]; then
    /usr/bin/codesign --force --deep --sign - "$APP"
else
    /usr/bin/codesign --force --deep --options runtime --timestamp \
        --sign "$IDENTITY" "$APP"
fi
/usr/bin/codesign --verify --deep --strict "$APP"

ARCH="$(uname -m)"
EVIDENCE_DIR="$PROJECT/release/macos-e2e/$ARCH"
mkdir -p "$EVIDENCE_DIR"
SELF_TEST_OUTPUT="$EVIDENCE_DIR/中文 输出.mp4"
SELF_TEST_RESULT="$EVIDENCE_DIR/E2E_RESULT.json"
rm -f "$SELF_TEST_OUTPUT" "$SELF_TEST_RESULT"
"$APP/Contents/MacOS/VideoRegionCleaner" --packaged-self-test \
    "$PROJECT/examples/demo_overlay.mp4" \
    "$SELF_TEST_OUTPUT" \
    "$SELF_TEST_RESULT"

ARCHIVE="$PROJECT/release/VideoRegionCleaner-$VERSION-macos-$ARCH.zip"
/usr/bin/ditto -c -k --sequesterRsrc --keepParent "$APP" "$ARCHIVE"
shasum -a 256 "$ARCHIVE" > "$ARCHIVE.sha256"
echo "macOS release: $ARCHIVE"
