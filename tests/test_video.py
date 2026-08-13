from __future__ import annotations

import numpy as np

from video_region_cleaner.models import Region
from video_region_cleaner.video import build_mask, restore_frame


def test_mask_and_preview_are_limited_to_selected_region():
    frame = np.full((120, 200, 3), 80, dtype=np.uint8)
    frame[20:40, 30:100] = 255
    region = Region(25, 15, 90, 35)
    mask = build_mask(frame, region)
    assert mask.shape == frame.shape[:2]
    assert not mask[:15].any()
    assert not mask[:, :25].any()
    assert not mask[50:].any()
    restored = restore_frame(frame, region, mask)
    assert restored.shape == frame.shape

