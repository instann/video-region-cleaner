"""Background export worker for Qt."""

from __future__ import annotations

from pathlib import Path
from threading import Event

from PySide6.QtCore import QObject, Signal, Slot

from .errors import CancelledError, readable_error
from .exporter import export_video
from .models import ExportProgress, MediaInfo, Region


class ExportWorker(QObject):
    progress = Signal(object)
    succeeded = Signal(object)
    failed = Signal(str)
    cancelled = Signal()
    completed = Signal()

    def __init__(
        self,
        media: MediaInfo,
        output: Path,
        region: Region,
        ffmpeg: Path,
        ffprobe: Path,
        prefer_nvenc: bool,
    ) -> None:
        super().__init__()
        self._media = media
        self._output = output
        self._region = region
        self._ffmpeg = ffmpeg
        self._ffprobe = ffprobe
        self._prefer_nvenc = prefer_nvenc
        self._cancel = Event()

    @Slot()
    def run(self) -> None:
        try:
            result = export_video(
                self._media, self._output, self._region, self._ffmpeg, self._ffprobe,
                self._cancel, self._emit_progress, self._prefer_nvenc,
            )
            self.succeeded.emit(result)
        except CancelledError:
            self.cancelled.emit()
        except BaseException as exc:
            self.failed.emit(readable_error(exc))
        finally:
            self.completed.emit()

    def _emit_progress(self, update: ExportProgress) -> None:
        self.progress.emit(update)

    @Slot()
    def cancel(self) -> None:
        self._cancel.set()

