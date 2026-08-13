from __future__ import annotations

import inspect

from video_region_cleaner.exporter import export_video


def test_legacy_prefer_nvenc_keyword_remains_supported():
    assert "prefer_nvenc" in inspect.signature(export_video).parameters
