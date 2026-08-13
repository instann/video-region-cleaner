"""Cancellable streaming export pipeline."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
from threading import Event
import time
from typing import Callable
from uuid import uuid4

import cv2

from .errors import CancelledError, RegionCleanerError
from .ffmpeg import encoder_arguments, preferred_hardware_encoder, probe_hardware_encoder, verify_output
from .models import ExportProgress, ExportResult, MediaInfo, Region
from .naming import validate_output_path
from .video import build_consensus_mask, open_capture, restore_frame


ProgressCallback = Callable[[ExportProgress], None]


def _temp_output(output: Path) -> Path:
    return output.with_name(f".{output.stem}.{uuid4().hex}.partial.mp4")


def _command(
    ffmpeg: Path,
    media: MediaInfo,
    temp_output: Path,
    encoder: str,
    copy_audio: bool,
) -> list[str]:
    return [
        str(ffmpeg), "-hide_banner", "-loglevel", "error", "-nostdin",
        "-f", "rawvideo", "-pix_fmt", "bgr24",
        "-video_size", f"{media.width}x{media.height}",
        "-framerate", f"{media.fps:.10f}", "-i", "pipe:0", "-i", str(media.path),
        "-map", "0:v:0", "-map", "1:a?", *encoder_arguments(encoder),
        "-pix_fmt", "yuv420p", "-c:a", "copy" if copy_audio else "aac",
        *([] if copy_audio else ["-b:a", "192k"]),
        "-shortest", "-movflags", "+faststart", str(temp_output), "-y",
    ]


def _stop_process(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=3)


def _run_stream(
    media: MediaInfo,
    mask,
    ffmpeg: Path,
    temp_output: Path,
    encoder: str,
    copy_audio: bool,
    cancel: Event,
    progress: ProgressCallback | None,
    started: float,
) -> int:
    capture = open_capture(media.path)
    creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    process = subprocess.Popen(
        _command(ffmpeg, media, temp_output, encoder, copy_audio),
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        shell=False,
        creationflags=creationflags,
    )
    written = 0
    pipe_error: BaseException | None = None
    try:
        if process.stdin is None:
            raise RegionCleanerError("无法启动 FFmpeg 输入管线")
        while True:
            if cancel.is_set():
                raise CancelledError("导出已取消")
            ok, frame = capture.read()
            if not ok or frame is None:
                break
            cleaned = restore_frame(frame, mask=mask)
            try:
                process.stdin.write(cleaned.tobytes())
            except (BrokenPipeError, OSError) as exc:
                pipe_error = exc
                break
            written += 1
            if progress and (written == 1 or written % max(1, round(media.fps / 4)) == 0):
                elapsed = time.perf_counter() - started
                remaining = (elapsed / written * max(0, media.frame_count - written)) if written else None
                progress(ExportProgress(written, media.frame_count, elapsed, remaining, "正在逐帧修复并编码"))
    except CancelledError:
        _stop_process(process)
        raise
    finally:
        capture.release()
        if process.stdin and not process.stdin.closed:
            try:
                process.stdin.close()
            except OSError:
                pass
    stderr = b""
    if process.stderr:
        stderr = process.stderr.read()
    return_code = process.wait()
    if return_code != 0 or pipe_error:
        detail = stderr.decode("utf-8", errors="replace").strip()
        raise RegionCleanerError(detail or f"FFmpeg 编码失败（代码 {return_code}）")
    return written


def export_video(
    media: MediaInfo,
    output: Path,
    region: Region,
    ffmpeg: Path,
    ffprobe: Path,
    cancel: Event | None = None,
    progress: ProgressCallback | None = None,
    prefer_hardware: bool = True,
    *,
    prefer_nvenc: bool | None = None,
) -> ExportResult:
    """Export to a sibling temporary file, verify it, then atomically publish it."""
    # Keep the public 1.0 keyword working while the implementation becomes
    # platform-neutral (VideoToolbox on macOS, NVENC on Windows).
    if prefer_nvenc is not None:
        prefer_hardware = prefer_nvenc
    output = validate_output_path(media.path, output)
    output.parent.mkdir(parents=True, exist_ok=True)
    region.validate(media.width, media.height)
    cancel = cancel or Event()
    started = time.perf_counter()
    if progress:
        progress(ExportProgress(0, media.frame_count, 0.0, None, "正在分析固定区域"))
    mask = build_consensus_mask(media, region, cancel)
    if cancel.is_set():
        raise CancelledError("导出已取消")

    hardware_encoder = preferred_hardware_encoder()
    hardware_ok, _ = (
        probe_hardware_encoder(ffmpeg, encoder=hardware_encoder)
        if prefer_hardware
        else (False, "已选择 CPU 编码")
    )
    initial_encoder = hardware_encoder if hardware_ok else "libx264"
    attempts = [(initial_encoder, True)]
    if media.has_audio:
        attempts.append((initial_encoder, False))
    if hardware_ok:
        attempts.append(("libx264", True))
        if media.has_audio:
            attempts.append(("libx264", False))
    # Preserve order while removing duplicate tuples.
    attempts = list(dict.fromkeys(attempts))
    temp_output = _temp_output(output)
    last_error: BaseException | None = None
    used_fallback = prefer_hardware and not hardware_ok
    try:
        for attempt_index, (encoder, copy_audio) in enumerate(attempts):
            if cancel.is_set():
                raise CancelledError("导出已取消")
            temp_output.unlink(missing_ok=True)
            if attempt_index:
                used_fallback = True
                if progress:
                    detail = "CPU 编码" if encoder == "libx264" else "音频转码"
                    progress(ExportProgress(0, media.frame_count, time.perf_counter() - started, None, f"自动回退：{detail}"))
            try:
                written = _run_stream(
                    media, mask, ffmpeg, temp_output, encoder, copy_audio,
                    cancel, progress, started,
                )
                verification = verify_output(temp_output, media, ffprobe)
                temp_output.replace(output)
                elapsed = time.perf_counter() - started
                if progress:
                    progress(ExportProgress(media.frame_count, media.frame_count, elapsed, 0.0, "导出和媒体校验完成"))
                return ExportResult(
                    output, elapsed, written, encoder,
                    used_fallback, verification,
                )
            except CancelledError:
                raise
            except (OSError, RegionCleanerError) as exc:
                last_error = exc
        raise RegionCleanerError(f"所有编码方案均失败：{last_error}")
    finally:
        temp_output.unlink(missing_ok=True)
