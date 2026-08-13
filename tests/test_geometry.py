from __future__ import annotations

import pytest

from video_region_cleaner.geometry import RectF, fitted_video_rect, source_region_to_view, view_rect_to_source
from video_region_cleaner.models import Region


@pytest.mark.parametrize(
    ("viewport", "video", "expected"),
    [
        ((1000, 700), (1920, 1080), RectF(0, 68.75, 1000, 562.5)),
        ((1000, 700), (1080, 1920), RectF(303.125, 0, 393.75, 700)),
        ((1920, 1080), (1920, 1080), RectF(0, 0, 1920, 1080)),
    ],
)
def test_fitted_video_rect_handles_landscape_portrait_and_bars(viewport, video, expected):
    actual = fitted_video_rect(*viewport, *video)
    assert (actual.x, actual.y, actual.width, actual.height) == pytest.approx(
        (expected.x, expected.y, expected.width, expected.height)
    )


@pytest.mark.parametrize("viewport", [(1000, 700), (1400, 900), (800, 1200), (1920, 1080)])
def test_source_roundtrip_is_stable_across_window_resizes(viewport):
    video_rect = fitted_video_rect(*viewport, 1920, 1080)
    source = Region(137, 83, 619, 227)
    view = source_region_to_view(source, video_rect, 1920, 1080)
    assert view_rect_to_source(view, video_rect, 1920, 1080) == source


def test_high_dpi_uses_logical_pixels_and_is_scale_invariant():
    # Qt mouse coordinates and widget dimensions are DIPs, so the device pixel
    # ratio must not enter this transform. Equivalent DIP geometry maps equally.
    at_100 = fitted_video_rect(960, 540, 1920, 1080)
    at_200 = fitted_video_rect(960, 540, 1920, 1080)
    rect = RectF(96, 54, 240, 108)
    assert view_rect_to_source(rect, at_100, 1920, 1080) == Region(192, 108, 480, 216)
    assert view_rect_to_source(rect, at_200, 1920, 1080) == Region(192, 108, 480, 216)


def test_selection_is_clipped_to_video_not_black_bars():
    video_rect = fitted_video_rect(1000, 700, 1920, 1080)
    source = view_rect_to_source(RectF(-50, 0, 300, 200), video_rect, 1920, 1080)
    assert source == Region(0, 0, 480, 252)


def test_selection_fully_in_black_bar_is_rejected():
    video_rect = fitted_video_rect(1000, 700, 1920, 1080)
    assert view_rect_to_source(RectF(20, 10, 100, 30), video_rect, 1920, 1080) is None


def test_edge_coverage_does_not_drop_partial_source_pixels():
    video_rect = RectF(10.25, 20.5, 333.3, 187.48125)
    mapped = view_rect_to_source(RectF(10.25, 20.5, 333.3, 187.48125), video_rect, 1920, 1080)
    assert mapped == Region(0, 0, 1920, 1080)
