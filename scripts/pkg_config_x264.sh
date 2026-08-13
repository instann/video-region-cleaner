#!/bin/bash
set -euo pipefail

# FFmpeg uses pkg-config only to discover the x264 build created immediately
# before it. Keeping this tiny adapter in-tree avoids making Homebrew a build
# dependency while still exercising FFmpeg's normal library detection checks.
if [[ -z "${VRC_X264_PREFIX:-}" ]]; then
    echo "VRC_X264_PREFIX is required" >&2
    exit 1
fi

mode=""
for argument in "$@"; do
    case "$argument" in
        --version)
            echo "0.29.2"
            exit 0
            ;;
        --atleast-pkgconfig-version*)
            exit 0
            ;;
        --exists|--print-errors|--static|x264|x264\ *)
            ;;
        --cflags)
            mode="cflags"
            ;;
        --libs)
            mode="libs"
            ;;
        --modversion)
            mode="modversion"
            ;;
        --variable=includedir)
            mode="includedir"
            ;;
        --variable=libdir)
            mode="libdir"
            ;;
        *)
            echo "Unsupported pkg-config argument: $argument" >&2
            exit 1
            ;;
    esac
done

case "$mode" in
    cflags) echo "-I$VRC_X264_PREFIX/include" ;;
    libs) echo "-L$VRC_X264_PREFIX/lib -lx264" ;;
    modversion) echo "0.165" ;;
    includedir) echo "$VRC_X264_PREFIX/include" ;;
    libdir) echo "$VRC_X264_PREFIX/lib" ;;
esac
