from __future__ import annotations

from pathlib import Path

import video_region_cleaner.ffmpeg as ffmpeg_module


def test_application_root_for_pyinstaller(monkeypatch, tmp_path: Path):
    executable = tmp_path / "dist" / "VideoRegionCleaner.exe"
    monkeypatch.setattr(ffmpeg_module.sys, "frozen", True, raising=False)
    monkeypatch.setattr(ffmpeg_module.sys, "executable", str(executable))
    assert ffmpeg_module.application_root() == executable.parent


def test_application_root_for_nuitka(monkeypatch, tmp_path: Path):
    executable = tmp_path / "dist" / "VideoRegionCleaner.exe"
    monkeypatch.delattr(ffmpeg_module.sys, "frozen", raising=False)
    monkeypatch.setitem(ffmpeg_module.__dict__, "__compiled__", object())
    monkeypatch.setattr(ffmpeg_module.sys, "argv", [str(executable)])
    assert ffmpeg_module.application_root() == executable.parent

