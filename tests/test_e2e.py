from __future__ import annotations

from pathlib import Path
from threading import Event

import pytest

from video_region_cleaner.errors import CancelledError
from video_region_cleaner.exporter import export_video
from video_region_cleaner.ffmpeg import find_tool, probe_media, probe_nvenc
from video_region_cleaner.models import Region


def test_synthetic_sample_exports_with_audio_and_source_is_unchanged(tmp_path: Path):
    root = Path(__file__).resolve().parents[1]
    ffmpeg = find_tool("ffmpeg", root / "vendor" / "ffmpeg" / "bin" / "ffmpeg.exe")
    ffprobe = find_tool("ffprobe", root / "vendor" / "ffmpeg" / "bin" / "ffprobe.exe")
    assert ffmpeg and ffprobe
    source = root / "examples" / "demo_overlay.mp4"
    source_hash_before = source.read_bytes()
    media = probe_media(source, ffprobe)
    output = tmp_path / "中文 输出 & sample.mp4"
    result = export_video(media, output, Region(15, 15, 330, 80), ffmpeg, ffprobe, prefer_nvenc=True)
    assert result.frames_written == media.frame_count
    assert result.verification.width == media.width
    assert result.verification.height == media.height
    assert result.verification.has_audio == media.has_audio
    assert source.read_bytes() == source_hash_before
    nvenc, _ = probe_nvenc(ffmpeg)
    if not nvenc:
        assert result.encoder == "libx264"
        assert result.used_fallback


def test_cancelled_export_leaves_no_output_or_partial_file(tmp_path: Path):
    root = Path(__file__).resolve().parents[1]
    ffmpeg = find_tool("ffmpeg", root / "vendor" / "ffmpeg" / "bin" / "ffmpeg.exe")
    ffprobe = find_tool("ffprobe", root / "vendor" / "ffmpeg" / "bin" / "ffprobe.exe")
    assert ffmpeg and ffprobe
    media = probe_media(root / "examples" / "demo_overlay.mp4", ffprobe)
    output = tmp_path / "cancelled.mp4"
    cancel = Event()
    cancel.set()
    with pytest.raises(CancelledError):
        export_video(media, output, Region(15, 15, 330, 80), ffmpeg, ffprobe, cancel=cancel)
    assert not output.exists()
    assert not list(tmp_path.glob("*.partial.mp4"))
