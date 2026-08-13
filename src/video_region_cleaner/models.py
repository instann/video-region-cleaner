"""Shared typed value objects."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Region:
    x: int
    y: int
    width: int
    height: int

    @property
    def right(self) -> int:
        return self.x + self.width

    @property
    def bottom(self) -> int:
        return self.y + self.height

    def validate(self, frame_width: int, frame_height: int) -> "Region":
        if self.x < 0 or self.y < 0 or self.width <= 0 or self.height <= 0:
            raise ValueError("区域必须位于画面内且宽高大于 0")
        if self.right > frame_width or self.bottom > frame_height:
            raise ValueError(f"区域超出 {frame_width}×{frame_height} 视频画面")
        return self


@dataclass(frozen=True, slots=True)
class MediaInfo:
    path: Path
    width: int
    height: int
    fps: float
    frame_count: int
    duration: float
    has_audio: bool = False
    video_codec: str = ""
    audio_codec: str = ""


@dataclass(frozen=True, slots=True)
class ExportProgress:
    frame: int
    total: int
    elapsed: float
    remaining: float | None
    message: str = ""


@dataclass(frozen=True, slots=True)
class ExportResult:
    output_path: Path
    elapsed: float
    frames_written: int
    encoder: str
    used_fallback: bool
    verification: MediaInfo

