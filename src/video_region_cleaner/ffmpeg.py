"""FFmpeg discovery, runtime encoder probing, and media verification."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Sequence

from .errors import RegionCleanerError
from .models import MediaInfo


def application_root() -> Path:
    if getattr(sys, "frozen", False):
        executable = Path(sys.executable).resolve()
        # A PyInstaller macOS bundle keeps data files under Contents/Resources,
        # while sys.executable lives under Contents/MacOS.
        if (
            sys.platform == "darwin"
            and executable.parent.name == "MacOS"
            and executable.parent.parent.name == "Contents"
        ):
            return executable.parent.parent / "Resources"
        return executable.parent
    # Nuitka standalone does not consistently expose sys.frozen, but its
    # module __file__ lives beside the compiled executable in the dist folder.
    if "__compiled__" in globals():
        return Path(sys.argv[0]).resolve().parent
    return Path(__file__).resolve().parents[2]


def bundled_root() -> Path:
    bundle = getattr(sys, "_MEIPASS", None)
    return Path(bundle) if bundle else application_root()


def find_tool(name: str, explicit: Path | None = None) -> Path | None:
    executable = f"{name}.exe" if os.name == "nt" else name
    candidates: list[Path] = []
    if explicit:
        candidates.append(explicit)
    for root in (application_root(), bundled_root()):
        candidates.extend((
            root / "ffmpeg" / "bin" / executable,
            root / "vendor" / "ffmpeg" / "bin" / executable,
            root / "bin" / executable,
            root / executable,
        ))
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    located = shutil.which(name)
    return Path(located).resolve() if located else None


def run_command(args: Sequence[str | Path], timeout: float = 30.0) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(arg) for arg in args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
        shell=False,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )


def ffmpeg_version(ffmpeg_path: Path) -> str:
    result = run_command([ffmpeg_path, "-version"])
    if result.returncode != 0:
        raise RegionCleanerError(result.stderr.strip() or "FFmpeg 无法运行")
    return (result.stdout.splitlines() or ["FFmpeg"])[0]


def _stream(payload: dict[str, Any], kind: str) -> dict[str, Any] | None:
    return next((stream for stream in payload.get("streams", []) if stream.get("codec_type") == kind), None)


def _fraction(value: str | None) -> float:
    if not value or value in {"0/0", "N/A"}:
        return 0.0
    numerator, _, denominator = value.partition("/")
    try:
        return float(numerator) / float(denominator or 1)
    except (ValueError, ZeroDivisionError):
        return 0.0


def probe_media(path: Path, ffprobe_path: Path | None = None) -> MediaInfo:
    probe = ffprobe_path or find_tool("ffprobe")
    if not probe:
        raise RegionCleanerError("未找到 FFprobe。请使用完整发行目录，或安装 FFmpeg 并加入 PATH。")
    result = run_command(
        [probe, "-v", "error", "-show_streams", "-show_format", "-of", "json", path],
        timeout=60.0,
    )
    if result.returncode != 0:
        raise RegionCleanerError(result.stderr.strip() or f"无法读取媒体信息：{path.name}")
    try:
        payload = json.loads(result.stdout)
        video = _stream(payload, "video")
        audio = _stream(payload, "audio")
        if not video:
            raise RegionCleanerError("文件中没有可读取的视频流")
        fps = _fraction(video.get("avg_frame_rate")) or _fraction(video.get("r_frame_rate"))
        duration = float(video.get("duration") or payload.get("format", {}).get("duration") or 0.0)
        count_text = video.get("nb_frames")
        frame_count = int(count_text) if count_text and count_text != "N/A" else max(1, round(duration * fps))
        rotation_value: Any = video.get("tags", {}).get("rotate", 0)
        for side_data in video.get("side_data_list", []):
            if "rotation" in side_data:
                rotation_value = side_data["rotation"]
                break
        try:
            rotated_quarter_turn = round(float(rotation_value) / 90.0) % 2 != 0
        except (TypeError, ValueError):
            rotated_quarter_turn = False
        width, height = int(video["width"]), int(video["height"])
        if rotated_quarter_turn:
            width, height = height, width
        return MediaInfo(
            path=path.resolve(),
            width=width,
            height=height,
            fps=fps,
            frame_count=frame_count,
            duration=duration,
            has_audio=audio is not None,
            video_codec=str(video.get("codec_name") or ""),
            audio_codec=str(audio.get("codec_name") or "") if audio else "",
        )
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise RegionCleanerError("FFprobe 返回了无法识别的媒体信息") from exc


def preferred_hardware_encoder() -> str:
    """Return the native H.264 hardware encoder for the current platform."""
    return "h264_videotoolbox" if sys.platform == "darwin" else "h264_nvenc"


def hardware_encoder_name(encoder: str | None = None) -> str:
    return "VideoToolbox" if (encoder or preferred_hardware_encoder()) == "h264_videotoolbox" else "NVENC"


def probe_hardware_encoder(
    ffmpeg_path: Path,
    timeout: float = 20.0,
    encoder: str | None = None,
) -> tuple[bool, str]:
    """Actually encode a tiny frame; listing the encoder is insufficient."""
    selected = encoder or preferred_hardware_encoder()
    name = hardware_encoder_name(selected)
    encoder_options = (
        ["-c:v", selected, "-allow_sw", "0", "-b:v", "1M"]
        if selected == "h264_videotoolbox"
        else ["-c:v", selected, "-preset", "p5"]
    )
    with tempfile.TemporaryDirectory(prefix="vrc_hardware_encoder_") as folder:
        output = Path(folder) / "probe.mp4"
        result = run_command(
            [
                ffmpeg_path,
                "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
                "color=c=black:s=256x256:r=1:d=1", "-frames:v", "1",
                *encoder_options, "-pix_fmt", "yuv420p", output, "-y",
            ],
            timeout=timeout,
        )
        if result.returncode == 0 and output.is_file() and output.stat().st_size > 0:
            return True, f"{name} 实际编码探测成功"
        detail = result.stderr.strip().splitlines()
        return False, (detail[-1] if detail else f"{name} 实际编码探测失败")


def probe_nvenc(ffmpeg_path: Path, timeout: float = 20.0) -> tuple[bool, str]:
    """Backward-compatible explicit NVENC probe."""
    return probe_hardware_encoder(ffmpeg_path, timeout, "h264_nvenc")


def encoder_arguments(encoder: str | bool) -> list[str]:
    # Preserve the 1.0 bool API: True selected NVENC and False selected x264.
    if isinstance(encoder, bool):
        encoder = "h264_nvenc" if encoder else "libx264"
    if encoder == "h264_nvenc":
        return ["-c:v", "h264_nvenc", "-preset", "p5", "-rc", "vbr", "-cq", "18", "-b:v", "0"]
    if encoder == "h264_videotoolbox":
        return ["-c:v", "h264_videotoolbox", "-b:v", "8M", "-maxrate", "12M", "-bufsize", "16M"]
    return ["-c:v", "libx264", "-crf", "18", "-preset", "fast"]


def verify_output(output: Path, source: MediaInfo, ffprobe_path: Path) -> MediaInfo:
    result = probe_media(output, ffprobe_path)
    errors: list[str] = []
    if (result.width, result.height) != (source.width, source.height):
        errors.append(f"分辨率 {result.width}×{result.height}（应为 {source.width}×{source.height}）")
    duration_tolerance = max(0.25, 2.0 / max(source.fps, 1.0))
    if abs(result.duration - source.duration) > duration_tolerance:
        errors.append(f"时长 {result.duration:.3f}s（源文件 {source.duration:.3f}s）")
    if source.fps > 0 and abs(result.fps - source.fps) > max(0.05, source.fps * 0.005):
        errors.append(f"帧率 {result.fps:.4f}（源文件 {source.fps:.4f}）")
    if source.has_audio and not result.has_audio:
        errors.append("源文件有音频，但输出没有音频流")
    if errors:
        raise RegionCleanerError("输出媒体校验失败：" + "；".join(errors))
    return result
