"""Interactive video canvas with a source-coordinate selection rectangle."""

from __future__ import annotations

from enum import Enum

import cv2
import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QCursor, QImage, QMouseEvent, QPainter, QPen
from PySide6.QtWidgets import QWidget

from .geometry import RectF, fitted_video_rect, source_region_to_view, view_rect_to_source
from .models import Region


class ViewMode(str, Enum):
    ORIGINAL = "original"
    MARKED = "marked"
    RESTORED = "restored"


class VideoCanvas(QWidget):
    regionChanged = Signal(object)
    fileDropped = Signal(str)

    HANDLE = 9.0
    MIN_REGION = 2

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setMouseTracking(True)
        self.setMinimumSize(480, 320)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._frame: np.ndarray | None = None
        self._image: QImage | None = None
        self._video_width = 0
        self._video_height = 0
        self._region: Region | None = None
        self._mode = ViewMode.MARKED
        self._operation: str | None = None
        self._start_pos = QPointF()
        self._start_region: Region | None = None
        self.setObjectName("videoCanvas")

    @property
    def region(self) -> Region | None:
        return self._region

    @property
    def video_rect(self) -> RectF:
        return fitted_video_rect(self.width(), self.height(), self._video_width, self._video_height)

    def set_frame(self, frame: np.ndarray | None) -> None:
        self._frame = frame
        if frame is None:
            self._image = None
            self._video_width = self._video_height = 0
        else:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            self._video_height, self._video_width = rgb.shape[:2]
            self._image = QImage(
                rgb.data, self._video_width, self._video_height, rgb.strides[0], QImage.Format.Format_RGB888
            ).copy()
        self.update()

    def set_region(self, region: Region | None, emit: bool = False) -> None:
        self._region = region
        self.update()
        if emit:
            self.regionChanged.emit(region)

    def set_view_mode(self, mode: ViewMode) -> None:
        self._mode = mode
        self.update()

    def _region_rect(self) -> QRectF | None:
        if not self._region:
            return None
        rect = source_region_to_view(
            self._region, self.video_rect, self._video_width, self._video_height
        )
        return QRectF(rect.x, rect.y, rect.width, rect.height)

    def paintEvent(self, _event) -> None:  # type: ignore[no-untyped-def]
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#11151b"))
        if not self._image:
            painter.setPen(QColor("#9aa4b2"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "拖放视频到这里\n或点击“打开视频”")
            return
        rect = self.video_rect
        target = QRectF(rect.x, rect.y, rect.width, rect.height)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        painter.drawImage(target, self._image)
        if self._region and self._mode == ViewMode.MARKED:
            selection = self._region_rect()
            assert selection is not None
            painter.fillRect(selection, QColor(36, 169, 255, 42))
            outer = QPen(QColor("#06101a"), 4.0)
            outer.setCosmetic(True)
            painter.setPen(outer)
            painter.drawRect(selection)
            pen = QPen(QColor("#42c8ff"), 2.0)
            pen.setCosmetic(True)
            painter.setPen(pen)
            painter.drawRect(selection)
            painter.setBrush(QColor("#f4fbff"))
            painter.setPen(QPen(QColor("#087ba8"), 1.0))
            for point in self._handle_points(selection).values():
                painter.drawRect(QRectF(point.x() - 4, point.y() - 4, 8, 8))

    def _handle_points(self, rect: QRectF) -> dict[str, QPointF]:
        return {
            "nw": rect.topLeft(), "n": QPointF(rect.center().x(), rect.top()), "ne": rect.topRight(),
            "e": QPointF(rect.right(), rect.center().y()), "se": rect.bottomRight(),
            "s": QPointF(rect.center().x(), rect.bottom()), "sw": rect.bottomLeft(),
            "w": QPointF(rect.left(), rect.center().y()),
        }

    def _hit_operation(self, position: QPointF) -> str:
        rect = self._region_rect()
        if rect:
            for name, point in self._handle_points(rect).items():
                if abs(position.x() - point.x()) <= self.HANDLE and abs(position.y() - point.y()) <= self.HANDLE:
                    return name
            if rect.contains(position):
                return "move"
        return "draw"

    def _inside_video(self, position: QPointF) -> bool:
        rect = self.video_rect
        return rect.x <= position.x() <= rect.right and rect.y <= position.y() <= rect.bottom

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton or not self._image or not self._inside_video(event.position()):
            return
        self._operation = self._hit_operation(event.position())
        self._start_pos = event.position()
        self._start_region = self._region
        if self._operation == "draw":
            self._region = None
        self.set_view_mode(ViewMode.MARKED)
        self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if not self._operation:
            self._set_hover_cursor(self._hit_operation(event.position()) if self._image else "")
            return
        rect = self.video_rect
        if self._operation == "draw":
            candidate = RectF(
                self._start_pos.x(), self._start_pos.y(),
                event.position().x() - self._start_pos.x(), event.position().y() - self._start_pos.y(),
            )
            region = view_rect_to_source(candidate, rect, self._video_width, self._video_height)
        elif self._start_region:
            sx = self._video_width / rect.width
            sy = self._video_height / rect.height
            dx = round((event.position().x() - self._start_pos.x()) * sx)
            dy = round((event.position().y() - self._start_pos.y()) * sy)
            start = self._start_region
            left, top, right, bottom = start.x, start.y, start.right, start.bottom
            if self._operation == "move":
                left = max(0, min(start.x + dx, self._video_width - start.width))
                top = max(0, min(start.y + dy, self._video_height - start.height))
                region = Region(left, top, start.width, start.height)
            else:
                if "w" in self._operation:
                    left = max(0, min(start.x + dx, right - self.MIN_REGION))
                if "e" in self._operation:
                    right = min(self._video_width, max(start.right + dx, left + self.MIN_REGION))
                if "n" in self._operation:
                    top = max(0, min(start.y + dy, bottom - self.MIN_REGION))
                if "s" in self._operation:
                    bottom = min(self._video_height, max(start.bottom + dy, top + self.MIN_REGION))
                region = Region(left, top, right - left, bottom - top)
        else:
            region = None
        if region and region.width >= self.MIN_REGION and region.height >= self.MIN_REGION:
            self._region = region
            self.regionChanged.emit(region)
        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._operation:
            self.mouseMoveEvent(event)
            self._operation = None
            self._start_region = None
            self.regionChanged.emit(self._region)

    def _set_hover_cursor(self, operation: str) -> None:
        cursors = {
            "move": Qt.CursorShape.SizeAllCursor,
            "nw": Qt.CursorShape.SizeFDiagCursor, "se": Qt.CursorShape.SizeFDiagCursor,
            "ne": Qt.CursorShape.SizeBDiagCursor, "sw": Qt.CursorShape.SizeBDiagCursor,
            "n": Qt.CursorShape.SizeVerCursor, "s": Qt.CursorShape.SizeVerCursor,
            "e": Qt.CursorShape.SizeHorCursor, "w": Qt.CursorShape.SizeHorCursor,
            "draw": Qt.CursorShape.CrossCursor,
        }
        self.setCursor(QCursor(cursors.get(operation, Qt.CursorShape.ArrowCursor)))

    def dragEnterEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        if event.mimeData().hasUrls() and any(url.isLocalFile() for url in event.mimeData().urls()):
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        local = next((url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()), "")
        if local:
            self.fileDropped.emit(local)
            event.acceptProposedAction()
