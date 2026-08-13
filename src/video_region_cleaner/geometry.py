"""DPI-independent preview and source-coordinate transforms."""

from __future__ import annotations

import math
from dataclasses import dataclass

from .models import Region


@dataclass(frozen=True, slots=True)
class RectF:
    x: float
    y: float
    width: float
    height: float

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def bottom(self) -> float:
        return self.y + self.height


def fitted_video_rect(
    viewport_width: float,
    viewport_height: float,
    video_width: int,
    video_height: int,
) -> RectF:
    """Return the aspect-fit video rectangle in Qt logical pixels (DIPs)."""
    if min(viewport_width, viewport_height, video_width, video_height) <= 0:
        return RectF(0.0, 0.0, 0.0, 0.0)
    scale = min(viewport_width / video_width, viewport_height / video_height)
    width = video_width * scale
    height = video_height * scale
    return RectF(
        (viewport_width - width) / 2.0,
        (viewport_height - height) / 2.0,
        width,
        height,
    )


def source_region_to_view(region: Region, video_rect: RectF, video_width: int, video_height: int) -> RectF:
    if video_rect.width <= 0 or video_rect.height <= 0:
        return RectF(video_rect.x, video_rect.y, 0.0, 0.0)
    sx = video_rect.width / video_width
    sy = video_rect.height / video_height
    return RectF(
        video_rect.x + region.x * sx,
        video_rect.y + region.y * sy,
        region.width * sx,
        region.height * sy,
    )


def view_rect_to_source(rect: RectF, video_rect: RectF, video_width: int, video_height: int) -> Region | None:
    """Map a logical-pixel rectangle to clipped source pixels using edge coverage."""
    if video_rect.width <= 0 or video_rect.height <= 0 or video_width <= 0 or video_height <= 0:
        return None
    left = max(video_rect.x, min(rect.x, rect.right))
    top = max(video_rect.y, min(rect.y, rect.bottom))
    right = min(video_rect.right, max(rect.x, rect.right))
    bottom = min(video_rect.bottom, max(rect.y, rect.bottom))
    if right <= left or bottom <= top:
        return None
    sx = video_width / video_rect.width
    sy = video_height / video_rect.height
    x1 = max(0, min(video_width, math.floor((left - video_rect.x) * sx + 1e-9)))
    y1 = max(0, min(video_height, math.floor((top - video_rect.y) * sy + 1e-9)))
    x2 = max(0, min(video_width, math.ceil((right - video_rect.x) * sx - 1e-9)))
    y2 = max(0, min(video_height, math.ceil((bottom - video_rect.y) * sy - 1e-9)))
    if x2 <= x1 or y2 <= y1:
        return None
    return Region(x1, y1, x2 - x1, y2 - y1)


def clamp_region(region: Region, video_width: int, video_height: int, minimum: int = 1) -> Region:
    x = max(0, min(region.x, max(0, video_width - minimum)))
    y = max(0, min(region.y, max(0, video_height - minimum)))
    right = max(x + minimum, min(region.right, video_width))
    bottom = max(y + minimum, min(region.bottom, video_height))
    return Region(x, y, right - x, bottom - y)


def move_region(region: Region, dx: int, dy: int, video_width: int, video_height: int) -> Region:
    x = max(0, min(region.x + dx, video_width - region.width))
    y = max(0, min(region.y + dy, video_height - region.height))
    return Region(x, y, region.width, region.height)

