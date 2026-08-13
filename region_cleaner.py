#!/usr/bin/env python3
"""Compatibility CLI backed by the desktop application's streaming core."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from video_region_cleaner.errors import readable_error
from video_region_cleaner.exporter import export_video
from video_region_cleaner.ffmpeg import find_tool, probe_media
from video_region_cleaner.models import ExportProgress, Region
from video_region_cleaner.naming import default_output_path


def parse_region(value: str) -> Region:
    try:
        numbers = [int(part.strip()) for part in value.split(",")]
    except ValueError as exc:
        raise argparse.ArgumentTypeError("region must be x,y,width,height") from exc
    if len(numbers) != 4 or numbers[0] < 0 or numbers[1] < 0 or numbers[2] <= 0 or numbers[3] <= 0:
        raise argparse.ArgumentTypeError("region must be x,y,width,height with positive width and height")
    return Region(*numbers)


def main() -> int:
    parser = argparse.ArgumentParser(description="Restore one fixed rectangular video region.")
    parser.add_argument("input", type=Path)
    parser.add_argument("--region", "-r", required=True, type=parse_region)
    parser.add_argument("--output", "-o", type=Path)
    parser.add_argument("--cpu", action="store_true", help="skip the NVENC runtime probe")
    args = parser.parse_args()
    source = args.input.expanduser().resolve()
    if not source.is_file():
        parser.error(f"input not found: {source}")
    ffmpeg = find_tool("ffmpeg")
    ffprobe = find_tool("ffprobe")
    if not ffmpeg or not ffprobe:
        print("Error: FFmpeg/FFprobe not found in vendor/ffmpeg/bin or PATH", file=sys.stderr)
        return 2
    output = (args.output or default_output_path(source)).expanduser().resolve()

    def report(update: ExportProgress) -> None:
        percent = update.frame / update.total * 100 if update.total else 0.0
        print(f"\r{percent:6.2f}%  {update.message}", end="", flush=True)

    try:
        media = probe_media(source, ffprobe)
        result = export_video(media, output, args.region, ffmpeg, ffprobe, progress=report, prefer_nvenc=not args.cpu)
    except BaseException as exc:
        print(f"\nError: {readable_error(exc)}", file=sys.stderr)
        return 1
    print(f"\nProcessed {result.frames_written} frames in {result.elapsed:.2f} seconds")
    print(f"Encoder: {result.encoder}; audio: {'preserved' if result.verification.has_audio else 'none'}")
    print(f"Output: {result.output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
