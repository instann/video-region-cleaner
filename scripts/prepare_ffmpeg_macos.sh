#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT="$(cd "$SCRIPT_DIR/.." && pwd)"
VENDOR_DIR="${1:-$PROJECT/vendor/ffmpeg}"
LOCK_FILE="$PROJECT/packaging/ffmpeg_macos_sources.txt"
BIN_DIR="$VENDOR_DIR/bin"
DOC_DIR="$VENDOR_DIR/doc-macos"
SOURCE_CACHE="${VRC_SOURCE_CACHE:-$VENDOR_DIR/source-cache}"
FFMPEG_TAG="n8.1.2"
FFMPEG_TAG_OBJECT="1c2c67c0b9f7f66ab32c19dcf7f227bcd290aa4c"
FFMPEG_SHA256="464beb5e7bf0c311e68b45ae2f04e9cc2af88851abb4082231742a74d97b524c"
X264_COMMIT="b35605ace3ddf7c1a5d67a2eb553f034aef41d55"
X264_SHA256="6eeb82934e69fd51e043bd8c5b0d152839638d1ce7aa4eea65a3fedcf83ff224"
BUILD_FINGERPRINT="$(
    {
        shasum -a 256 "$LOCK_FILE" "$SCRIPT_DIR/prepare_ffmpeg_macos.sh" \
            "$SCRIPT_DIR/pkg_config_x264.sh"
        uname -m
    } | shasum -a 256 | awk '{print $1}'
)"

if [[ "$(uname -s)" != "Darwin" ]]; then
    echo "This script must run on macOS." >&2
    exit 1
fi
case "$(uname -m)" in
    arm64|x86_64) ;;
    *) echo "Unsupported macOS architecture: $(uname -m)" >&2; exit 1 ;;
esac
for command in curl make clang shasum tar; do
    if ! command -v "$command" >/dev/null 2>&1; then
        echo "Missing build dependency: $command" >&2
        echo "Install Xcode Command Line Tools, then retry." >&2
        exit 1
    fi
done

binary_arch=""
if [[ -x "$BIN_DIR/ffmpeg" ]]; then
    binary_arch="$(/usr/bin/lipo -archs "$BIN_DIR/ffmpeg" 2>/dev/null || true)"
fi
if [[ -x "$BIN_DIR/ffmpeg" && -x "$BIN_DIR/ffprobe" ]] && \
    [[ " $binary_arch " == *" $(uname -m) "* ]] && \
    cmp -s "$LOCK_FILE" "$DOC_DIR/FFMPEG_SOURCE_REVISIONS.txt" && \
    [[ "$(cat "$DOC_DIR/FFMPEG_BUILD_FINGERPRINT.txt" 2>/dev/null || true)" == "$BUILD_FINGERPRINT" ]]; then
    echo "Reusing verified source-built FFmpeg in $BIN_DIR"
    exit 0
fi

BUILD_DIR="$(mktemp -d "${TMPDIR:-/tmp}/vrc-ffmpeg-build.XXXXXX")"
trap 'rm -rf "$BUILD_DIR"' EXIT
PREFIX="$BUILD_DIR/prefix"
JOBS="$(sysctl -n hw.logicalcpu 2>/dev/null || echo 2)"

verify_archive() {
    local expected="$1"
    local archive="$2"
    local actual
    actual="$(shasum -a 256 "$archive" | awk '{print $1}')"
    if [[ "$actual" != "$expected" ]]; then
        echo "Source verification failed for $archive: expected $expected, got $actual" >&2
        exit 1
    fi
}

fetch_sources() {
    local ffmpeg_archive="$SOURCE_CACHE/ffmpeg-8.1.2.tar.xz"
    local x264_archive="$SOURCE_CACHE/x264-$X264_COMMIT.tar.bz2"
    mkdir -p "$SOURCE_CACHE"
    if [[ ! -f "$ffmpeg_archive" ]]; then
        curl --fail --location --retry 5 --retry-all-errors --continue-at - \
            --output "$ffmpeg_archive.partial" \
            "https://ffmpeg.org/releases/ffmpeg-8.1.2.tar.xz"
        mv "$ffmpeg_archive.partial" "$ffmpeg_archive"
    fi
    if [[ ! -f "$x264_archive" ]]; then
        curl --fail --location --retry 5 --retry-all-errors --continue-at - \
            --output "$x264_archive.partial" \
            "https://code.videolan.org/videolan/x264/-/archive/$X264_COMMIT/x264-$X264_COMMIT.tar.bz2"
        mv "$x264_archive.partial" "$x264_archive"
    fi
    verify_archive "$FFMPEG_SHA256" "$ffmpeg_archive"
    verify_archive "$X264_SHA256" "$x264_archive"
    mkdir "$BUILD_DIR/ffmpeg" "$BUILD_DIR/x264"
    tar -xf "$ffmpeg_archive" -C "$BUILD_DIR/ffmpeg" --strip-components=1
    tar -xf "$x264_archive" -C "$BUILD_DIR/x264" --strip-components=1
}

fetch_sources

x264_options=(
    --prefix="$PREFIX"
    --enable-static
    --enable-pic
    --disable-cli
    --disable-opencl
)
if [[ "$(uname -m)" == "x86_64" ]] && \
    ! command -v nasm >/dev/null 2>&1 && \
    ! command -v yasm >/dev/null 2>&1; then
    x264_options+=(--disable-asm)
fi

pushd "$BUILD_DIR/x264" >/dev/null
./configure "${x264_options[@]}"
echo "Building x264 for macOS $(uname -m)..."
make -j "$JOBS" >/dev/null
make install >/dev/null
popd >/dev/null

ffmpeg_options=(
    --prefix=/usr/local
    --disable-shared
    --enable-static
    --enable-gpl
    --enable-version3
    --enable-libx264
    --enable-videotoolbox
    --enable-audiotoolbox
    --disable-doc
    --disable-debug
    --disable-ffplay
    --pkg-config=../pkg-config-x264
    --pkg-config-flags=--static
    --extra-cflags=-I../prefix/include
    --extra-ldflags=-L../prefix/lib
)
if [[ "$(uname -m)" == "x86_64" ]] && ! command -v nasm >/dev/null 2>&1; then
    ffmpeg_options+=(--disable-x86asm)
fi

pushd "$BUILD_DIR/ffmpeg" >/dev/null
echo "Configuring FFmpeg $FFMPEG_TAG..."
install -m 755 "$SCRIPT_DIR/pkg_config_x264.sh" "$BUILD_DIR/pkg-config-x264"
if ! VRC_X264_PREFIX=../prefix ./configure "${ffmpeg_options[@]}" \
    > "$BUILD_DIR/ffmpeg-configure.log"; then
    cat "$BUILD_DIR/ffmpeg-configure.log" >&2
    exit 1
fi
echo "Building FFmpeg and FFprobe..."
make -j "$JOBS" ffmpeg ffprobe >/dev/null
popd >/dev/null

mkdir -p "$BIN_DIR" "$DOC_DIR"
install -m 755 "$BUILD_DIR/ffmpeg/ffmpeg" "$BIN_DIR/ffmpeg"
install -m 755 "$BUILD_DIR/ffmpeg/ffprobe" "$BIN_DIR/ffprobe"
cp "$LOCK_FILE" "$DOC_DIR/FFMPEG_SOURCE_REVISIONS.txt"
echo "$BUILD_FINGERPRINT" > "$DOC_DIR/FFMPEG_BUILD_FINGERPRINT.txt"
cp "$BUILD_DIR/ffmpeg/LICENSE.md" "$DOC_DIR/FFMPEG_BUILD_LICENSE.txt"
{
    echo "FFmpeg source: https://ffmpeg.org/releases/ffmpeg-8.1.2.tar.xz (tag $FFMPEG_TAG; tag object $FFMPEG_TAG_OBJECT; SHA-256 $FFMPEG_SHA256)"
    echo "x264 source: https://code.videolan.org/videolan/x264/-/archive/$X264_COMMIT/x264-$X264_COMMIT.tar.bz2 (SHA-256 $X264_SHA256)"
    echo "Architecture: $(uname -m)"
    echo
    "$BIN_DIR/ffmpeg" -version | head -n 12
} > "$DOC_DIR/FFMPEG_BUILD_README.txt"
cp "$BUILD_DIR/x264/COPYING" "$DOC_DIR/X264_LICENSE.txt"
"$BIN_DIR/ffmpeg" -version | head -n 12 > "$DOC_DIR/FFMPEG_VERSION_AND_CONFIGURATION.txt"

if "$BIN_DIR/ffmpeg" -version | head -n 3 | grep -q -- '--enable-nonfree'; then
    echo "Refusing to package an unredistributable --enable-nonfree FFmpeg build." >&2
    exit 1
fi
echo "Built FFmpeg $FFMPEG_TAG and x264 from pinned source for macOS $(uname -m)"
