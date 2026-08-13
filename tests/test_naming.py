from __future__ import annotations

from pathlib import Path

import pytest

from video_region_cleaner.errors import RegionCleanerError
from video_region_cleaner.naming import default_output_path, validate_output_path


def test_default_output_name_and_collision(tmp_path: Path):
    source = tmp_path / "input video.mov"
    source.touch()
    assert default_output_path(source).name == "input video_clean.mp4"
    (tmp_path / "input video_clean.mp4").touch()
    assert default_output_path(source).name == "input video_clean_2.mp4"


def test_chinese_and_special_character_path_is_preserved(tmp_path: Path):
    folder = tmp_path / "中文 目录 & (样例)"
    folder.mkdir()
    source = folder / "视频.mp4"
    source.touch()
    assert default_output_path(source) == folder / "视频_clean.mp4"


def test_source_file_cannot_be_overwritten(tmp_path: Path):
    source = tmp_path / "source.mp4"
    source.touch()
    with pytest.raises(RegionCleanerError, match="不能覆盖"):
        validate_output_path(source, source)


def test_existing_output_is_rejected(tmp_path: Path):
    source = tmp_path / "source.mp4"
    source.touch()
    output = tmp_path / "existing.mp4"
    output.touch()
    with pytest.raises(RegionCleanerError, match="已存在"):
        validate_output_path(source, output)


def test_existing_output_is_checked_after_mp4_suffix_is_added(tmp_path: Path):
    source = tmp_path / "source.mov"
    source.touch()
    (tmp_path / "result.mp4").touch()
    with pytest.raises(RegionCleanerError, match="已存在"):
        validate_output_path(source, tmp_path / "result")
