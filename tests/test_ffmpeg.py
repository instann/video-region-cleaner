from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import json

from video_region_cleaner.ffmpeg import encoder_arguments, probe_media, probe_nvenc


def test_encoder_arguments_select_expected_encoder():
    assert "h264_nvenc" in encoder_arguments(True)
    assert "libx264" in encoder_arguments(False)


def test_nvenc_requires_successful_real_output(monkeypatch, tmp_path: Path):
    def unsuccessful(args, timeout=30):
        return SimpleNamespace(returncode=1, stderr="No capable devices found", stdout="")

    monkeypatch.setattr("video_region_cleaner.ffmpeg.run_command", unsuccessful)
    available, detail = probe_nvenc(tmp_path / "ffmpeg.exe")
    assert not available
    assert "No capable" in detail


def test_nvenc_command_is_argument_array_and_runtime_encode(monkeypatch, tmp_path: Path):
    captured = []

    def successful(args, timeout=30):
        captured.extend(args)
        Path(args[-2]).write_bytes(b"encoded")
        return SimpleNamespace(returncode=0, stderr="", stdout="")

    monkeypatch.setattr("video_region_cleaner.ffmpeg.run_command", successful)
    available, _ = probe_nvenc(tmp_path / "ffmpeg.exe")
    assert available
    assert "-f" in captured and "lavfi" in captured
    assert "h264_nvenc" in captured


def test_probe_media_reports_visual_dimensions_for_rotation_metadata(monkeypatch, tmp_path: Path):
    payload = {
        "streams": [{
            "codec_type": "video", "codec_name": "h264", "width": 1920, "height": 1080,
            "avg_frame_rate": "30/1", "duration": "2", "nb_frames": "60",
            "side_data_list": [{"rotation": -90}],
        }],
        "format": {"duration": "2"},
    }
    monkeypatch.setattr(
        "video_region_cleaner.ffmpeg.run_command",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stderr="", stdout=json.dumps(payload)),
    )
    media = probe_media(tmp_path / "portrait.mp4", tmp_path / "ffprobe.exe")
    assert (media.width, media.height) == (1080, 1920)
