#!/usr/bin/env python3
"""Remove a user-selected rectangular overlay region from a video."""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import subprocess
import sys
import time

import cv2
import numpy as np


def parse_region(value: str) -> tuple[int, int, int, int]:
    try:
        region = tuple(int(part.strip()) for part in value.split(","))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("region must be x,y,width,height") from exc
    if len(region) != 4 or any(number < 0 for number in region):
        raise argparse.ArgumentTypeError("region must be four non-negative integers")
    if region[2] == 0 or region[3] == 0:
        raise argparse.ArgumentTypeError("region width and height must be positive")
    return region


def build_mask(frame: np.ndarray, region: tuple[int, int, int, int]) -> np.ndarray:
    x, y, width, height = region
    gray = cv2.cvtColor(frame[y:y + height, x:x + width], cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 30, 80)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    dilated = cv2.dilate(edges, kernel, iterations=1)
    count, labels, stats, _ = cv2.connectedComponentsWithStats(dilated)
    clean = np.zeros_like(dilated)
    for index in range(1, count):
        if stats[index, cv2.CC_STAT_AREA] >= 20:
            clean[labels == index] = 255
    if not np.any(clean):
        clean.fill(255)
    mask = np.zeros(frame.shape[:2], dtype=np.uint8)
    mask[y:y + height, x:x + width] = clean
    return mask


def nvenc_available() -> bool:
    if shutil.which("ffmpeg") is None:
        return False
    result = subprocess.run(
        [
            "ffmpeg", "-hide_banner", "-loglevel", "error",
            "-f", "lavfi", "-i", "color=size=256x256:rate=1",
            "-frames:v", "1", "-c:v", "h264_nvenc", "-f", "null", "-",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def process(input_path: Path, output_path: Path, region: tuple[int, int, int, int]) -> None:
    capture = cv2.VideoCapture(str(input_path))
    if not capture.isOpened():
        raise RuntimeError(f"could not open input: {input_path}")
    total = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = float(capture.get(cv2.CAP_PROP_FPS))
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    x, y, region_width, region_height = region
    if x + region_width > width or y + region_height > height:
        capture.release()
        raise RuntimeError(f"region exceeds the {width}x{height} video frame")

    sample_frames = []
    step = max(1, total // 60)
    for index in range(0, total, step):
        capture.set(cv2.CAP_PROP_POS_FRAMES, index)
        ok, frame = capture.read()
        if ok:
            sample_frames.append(frame)
        if len(sample_frames) >= 60:
            break
    if not sample_frames:
        capture.release()
        raise RuntimeError("could not sample video frames")
    mean_frame = np.mean(np.stack(sample_frames), axis=0).astype(np.uint8)
    mask = build_mask(mean_frame, region)

    encoder = (
        ["-c:v", "h264_nvenc", "-preset", "p5", "-rc", "vbr", "-cq", "18", "-b:v", "0"]
        if nvenc_available()
        else ["-c:v", "libx264", "-crf", "18", "-preset", "fast"]
    )
    command = [
        "ffmpeg", "-hide_banner", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "bgr24", "-video_size", f"{width}x{height}",
        "-framerate", f"{fps:.8f}", "-i", "pipe:0", "-i", str(input_path),
        "-map", "0:v:0", "-map", "1:a?", *encoder, "-pix_fmt", "yuv420p",
        "-c:a", "copy", "-movflags", "+faststart", str(output_path), "-y",
    ]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
    written = 0
    started = time.perf_counter()
    try:
        assert ffmpeg.stdin is not None
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            cleaned = cv2.inpaint(frame, mask, 5, cv2.INPAINT_TELEA)
            ffmpeg.stdin.write(cleaned.tobytes())
            written += 1
    finally:
        capture.release()
        if ffmpeg.stdin is not None:
            ffmpeg.stdin.close()
    assert ffmpeg.stderr is not None
    error_text = ffmpeg.stderr.read().decode("utf-8", errors="replace").strip()
    return_code = ffmpeg.wait()
    if return_code != 0:
        raise RuntimeError(error_text or f"ffmpeg failed with code {return_code}")
    elapsed = time.perf_counter() - started
    print(f"Processed {written} frames in {elapsed:.2f} seconds")
    print(f"Output: {output_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Clean a selected rectangular overlay region.")
    parser.add_argument("input", type=Path)
    parser.add_argument("--region", "-r", required=True, type=parse_region)
    parser.add_argument("--output", "-o", type=Path)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    input_path = args.input.expanduser().resolve()
    output_path = (args.output or input_path.with_name(f"{input_path.stem}_clean.mp4")).resolve()
    if not input_path.is_file():
        print(f"Error: input not found: {input_path}", file=sys.stderr)
        return 2
    if input_path == output_path:
        print("Error: output must not overwrite the input", file=sys.stderr)
        return 2
    if output_path.exists() and not args.overwrite:
        print(f"Error: output exists: {output_path}", file=sys.stderr)
        return 2
    if shutil.which("ffmpeg") is None:
        print("Error: ffmpeg is required on PATH", file=sys.stderr)
        return 2
    try:
        process(input_path, output_path, args.region)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
