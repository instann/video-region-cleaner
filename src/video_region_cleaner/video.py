"""Frame access and OpenCV TELEA restoration primitives."""

from __future__ import annotations

from pathlib import Path
from threading import Event
from typing import Callable

import cv2
import numpy as np

from .errors import CancelledError, RegionCleanerError
from .models import MediaInfo, Region


def open_capture(path: Path) -> cv2.VideoCapture:
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        capture.release()
        raise RegionCleanerError(f"无法打开视频：{path.name}")
    orientation_auto = getattr(cv2, "CAP_PROP_ORIENTATION_AUTO", None)
    if orientation_auto is not None:
        capture.set(orientation_auto, 1)
    return capture


def read_frame(path: Path, frame_index: int) -> np.ndarray:
    capture = open_capture(path)
    try:
        capture.set(cv2.CAP_PROP_POS_FRAMES, max(0, frame_index))
        ok, frame = capture.read()
        if not ok or frame is None:
            raise RegionCleanerError(f"无法读取第 {frame_index + 1} 帧")
        return frame
    finally:
        capture.release()


def build_mask(frame: np.ndarray, region: Region) -> np.ndarray:
    region.validate(frame.shape[1], frame.shape[0])
    crop = frame[region.y:region.bottom, region.x:region.right]
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 30, 80)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    dilated = cv2.dilate(edges, kernel, iterations=1)
    count, labels, stats, _ = cv2.connectedComponentsWithStats(dilated)
    clean = np.zeros_like(dilated)
    for index in range(1, count):
        if stats[index, cv2.CC_STAT_AREA] >= 20:
            clean[labels == index] = 255
    if not np.any(clean):
        clean.fill(255)
    mask = np.zeros(frame.shape[:2], dtype=np.uint8)
    mask[region.y:region.bottom, region.x:region.right] = clean
    return mask


def restore_frame(frame: np.ndarray, region: Region | None = None, mask: np.ndarray | None = None) -> np.ndarray:
    if mask is None:
        if region is None:
            raise ValueError("region is required when a precomputed mask is not provided")
        mask = build_mask(frame, region)
    return cv2.inpaint(frame, mask, 5, cv2.INPAINT_TELEA)


def build_consensus_mask(
    media: MediaInfo,
    region: Region,
    cancel: Event | None = None,
    progress: Callable[[int, int], None] | None = None,
    samples: int = 60,
) -> np.ndarray:
    capture = open_capture(media.path)
    mean_frame: np.ndarray | None = None
    accepted = 0
    target = min(samples, max(1, media.frame_count))
    indices = np.linspace(0, max(0, media.frame_count - 1), target, dtype=np.int64)
    try:
        for position, index in enumerate(indices, 1):
            if cancel and cancel.is_set():
                raise CancelledError("导出已取消")
            capture.set(cv2.CAP_PROP_POS_FRAMES, int(index))
            ok, frame = capture.read()
            if ok and frame is not None:
                accepted += 1
                if mean_frame is None:
                    mean_frame = frame.astype(np.float32)
                else:
                    mean_frame += (frame.astype(np.float32) - mean_frame) / accepted
            if progress:
                progress(position, target)
    finally:
        capture.release()
    if mean_frame is None:
        raise RegionCleanerError("无法采样视频帧")
    return build_mask(mean_frame.astype(np.uint8), region)
