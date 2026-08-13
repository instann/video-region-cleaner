"""PySide6 desktop user interface."""

from __future__ import annotations

import logging
import os
from pathlib import Path
import subprocess

from PySide6.QtCore import QSignalBlocker, QThread, QTimer, Qt, Slot
from PySide6.QtGui import QAction, QCloseEvent, QDesktopServices, QIcon
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import (
    QApplication, QButtonGroup, QCheckBox, QDoubleSpinBox, QFileDialog, QFormLayout,
    QFrame, QGridLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QMainWindow,
    QMessageBox, QProgressBar, QPushButton, QRadioButton, QSlider, QSpinBox,
    QStatusBar, QToolBar, QVBoxLayout, QWidget,
)

from .canvas import VideoCanvas, ViewMode
from .errors import RegionCleanerError, readable_error
from .ffmpeg import ffmpeg_version, find_tool, probe_media, probe_nvenc
from .models import ExportProgress, ExportResult, MediaInfo, Region
from .naming import default_output_path, validate_output_path
from .video import read_frame, restore_frame
from .worker import ExportWorker


LOGGER = logging.getLogger(__name__)
VIDEO_FILTER = "视频文件 (*.mp4 *.mov *.mkv *.webm);;所有文件 (*.*)"


def format_time(seconds: float | None) -> str:
    if seconds is None or seconds < 0:
        return "--:--"
    whole = round(seconds)
    hours, remainder = divmod(whole, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}" if hours else f"{minutes:02d}:{secs:02d}"


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Video Region Cleaner")
        self.resize(1280, 760)
        self.setMinimumSize(1000, 640)
        self.setAcceptDrops(True)
        self.media: MediaInfo | None = None
        self.current_frame_index = 0
        self.current_frame = None
        self.last_output: Path | None = None
        self.ffmpeg = find_tool("ffmpeg")
        self.ffprobe = find_tool("ffprobe")
        self.export_thread: QThread | None = None
        self.export_worker: ExportWorker | None = None
        self._closing = False
        self._build_ui()
        self._connect()
        self._refresh_tool_status()
        self._set_loaded(False)

    def _build_ui(self) -> None:
        toolbar = QToolBar("文件")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        self.open_action = QAction(self.style().standardIcon(self.style().StandardPixmap.SP_DialogOpenButton), "打开视频", self)
        self.open_action.setShortcut("Ctrl+O")
        toolbar.addAction(self.open_action)
        toolbar.addSeparator()
        notice = QLabel("本地处理 · 不上传媒体 · 仅处理自有或获授权内容")
        notice.setObjectName("toolbarNotice")
        toolbar.addWidget(notice)

        root = QWidget()
        layout = QHBoxLayout(root)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(10)
        self.setCentralWidget(root)

        left = QVBoxLayout()
        left.setSpacing(7)
        self.canvas = VideoCanvas()
        left.addWidget(self.canvas, 1)

        mode_bar = QHBoxLayout()
        mode_bar.addWidget(QLabel("查看："))
        self.original_radio = QRadioButton("原帧")
        self.marked_radio = QRadioButton("区域标记")
        self.restored_radio = QRadioButton("修复预览")
        self.marked_radio.setChecked(True)
        self.mode_group = QButtonGroup(self)
        for button in (self.original_radio, self.marked_radio, self.restored_radio):
            self.mode_group.addButton(button)
            mode_bar.addWidget(button)
        mode_bar.addStretch()
        self.clear_button = QPushButton("清除区域")
        self.reset_button = QPushButton("重置视图")
        mode_bar.addWidget(self.clear_button)
        mode_bar.addWidget(self.reset_button)
        left.addLayout(mode_bar)

        seek = QHBoxLayout()
        self.previous_button = QPushButton("◀ 上一帧")
        self.previous_button.setToolTip("加载上一帧")
        self.next_button = QPushButton("下一帧 ▶")
        self.next_button.setToolTip("加载下一帧")
        self.timeline = QSlider(Qt.Orientation.Horizontal)
        self.timeline.setTracking(False)
        self.time_input = QDoubleSpinBox()
        self.time_input.setDecimals(3)
        self.time_input.setSuffix(" 秒")
        self.time_input.setMinimumWidth(105)
        self.frame_label = QLabel("帧 -- / --")
        seek.addWidget(self.previous_button)
        seek.addWidget(self.timeline, 1)
        seek.addWidget(self.next_button)
        seek.addWidget(self.time_input)
        seek.addWidget(self.frame_label)
        left.addLayout(seek)
        layout.addLayout(left, 1)

        panel = QFrame()
        panel.setObjectName("sidePanel")
        panel.setFixedWidth(315)
        side = QVBoxLayout(panel)
        side.setContentsMargins(12, 8, 12, 10)

        media_group = QGroupBox("视频信息")
        media_form = QFormLayout(media_group)
        self.file_value = QLabel("尚未载入")
        self.file_value.setWordWrap(True)
        self.size_value = QLabel("--")
        self.duration_value = QLabel("--")
        self.stream_value = QLabel("--")
        media_form.addRow("文件", self.file_value)
        media_form.addRow("画面", self.size_value)
        media_form.addRow("时长", self.duration_value)
        media_form.addRow("流", self.stream_value)
        side.addWidget(media_group)

        region_group = QGroupBox("原视频区域坐标")
        coordinates = QGridLayout(region_group)
        self.x_spin, self.y_spin, self.w_spin, self.h_spin = (QSpinBox() for _ in range(4))
        for spin in (self.x_spin, self.y_spin, self.w_spin, self.h_spin):
            spin.setRange(0, 99999)
        coordinates.addWidget(QLabel("X"), 0, 0); coordinates.addWidget(self.x_spin, 0, 1)
        coordinates.addWidget(QLabel("Y"), 0, 2); coordinates.addWidget(self.y_spin, 0, 3)
        coordinates.addWidget(QLabel("宽"), 1, 0); coordinates.addWidget(self.w_spin, 1, 1)
        coordinates.addWidget(QLabel("高"), 1, 2); coordinates.addWidget(self.h_spin, 1, 3)
        self.region_hint = QLabel("在视频画面上拖拽创建矩形；可移动并从八个手柄缩放。")
        self.region_hint.setWordWrap(True)
        self.region_hint.setObjectName("hint")
        coordinates.addWidget(self.region_hint, 2, 0, 1, 4)
        side.addWidget(region_group)

        export_group = QGroupBox("导出设置")
        export_form = QFormLayout(export_group)
        output_row = QHBoxLayout()
        self.output_edit = QLineEdit()
        self.browse_output_button = QPushButton("…")
        self.browse_output_button.setFixedWidth(34)
        self.browse_output_button.setToolTip("选择输出文件")
        output_row.addWidget(self.output_edit, 1)
        output_row.addWidget(self.browse_output_button)
        self.encoder_check = QCheckBox("优先使用 NVENC（实际探测失败自动回退）")
        self.encoder_check.setChecked(True)
        self.tool_status = QLabel("正在检测…")
        self.tool_status.setWordWrap(True)
        export_form.addRow("输出", output_row)
        export_form.addRow(self.encoder_check)
        export_form.addRow("编码器", self.tool_status)
        side.addWidget(export_group)

        status_group = QGroupBox("任务状态")
        status_box = QVBoxLayout(status_group)
        self.status_label = QLabel("等待载入视频")
        self.status_label.setWordWrap(True)
        self.progress = QProgressBar()
        self.progress.setRange(0, 1000)
        self.progress.setValue(0)
        timing = QHBoxLayout()
        self.elapsed_label = QLabel("已用 00:00")
        self.remaining_label = QLabel("剩余 --:--")
        timing.addWidget(self.elapsed_label)
        timing.addStretch()
        timing.addWidget(self.remaining_label)
        status_box.addWidget(self.status_label)
        status_box.addWidget(self.progress)
        status_box.addLayout(timing)
        side.addWidget(status_group)

        self.export_button = QPushButton("导出新视频")
        self.export_button.setObjectName("primaryButton")
        self.export_button.setMinimumHeight(42)
        self.cancel_button = QPushButton("取消")
        self.cancel_button.setEnabled(False)
        action_row = QHBoxLayout()
        action_row.addWidget(self.export_button, 1)
        action_row.addWidget(self.cancel_button)
        side.addLayout(action_row)
        completed_row = QHBoxLayout()
        self.open_file_button = QPushButton("打开文件")
        self.open_folder_button = QPushButton("打开所在文件夹")
        completed_row.addWidget(self.open_file_button)
        completed_row.addWidget(self.open_folder_button)
        side.addLayout(completed_row)
        self.scope_note = QLabel("固定矩形区域基线；不适用于动态字幕或复杂移动遮挡。")
        self.scope_note.setWordWrap(True)
        self.scope_note.setObjectName("scopeNote")
        side.addWidget(self.scope_note)
        side.addStretch()
        layout.addWidget(panel)

        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("就绪")
        self._apply_style()

    def _apply_style(self) -> None:
        self.setStyleSheet("""
            QMainWindow, QWidget { background: #1b2027; color: #e8edf3; font-size: 13px; }
            QToolBar { background: #222831; border-bottom: 1px solid #343d49; spacing: 8px; padding: 5px; }
            #toolbarNotice, #hint, #scopeNote { color: #9ca8b7; }
            #sidePanel { background: #20262e; border-left: 1px solid #343d49; }
            QGroupBox { border: 1px solid #39434f; border-radius: 4px; margin-top: 9px; padding-top: 10px; font-weight: 600; }
            QGroupBox::title { subcontrol-origin: margin; left: 9px; padding: 0 4px; }
            QPushButton, QLineEdit, QSpinBox, QDoubleSpinBox { background: #2a323d; border: 1px solid #465261; border-radius: 3px; padding: 5px 7px; }
            QPushButton:hover { border-color: #6a7a8d; background: #303a46; }
            QPushButton:disabled { color: #707a86; background: #252b33; }
            #primaryButton { background: #087ea4; border-color: #18a9d3; font-size: 14px; font-weight: 700; }
            #primaryButton:hover { background: #0a91bc; }
            QProgressBar { border: 1px solid #465261; border-radius: 3px; text-align: center; background: #151a20; }
            QProgressBar::chunk { background: #169cc5; }
            QSlider::groove:horizontal { height: 5px; background: #38434f; }
            QSlider::handle:horizontal { background: #42c8ff; width: 13px; margin: -5px 0; border-radius: 6px; }
            QStatusBar { background: #171c22; color: #aeb8c4; }
        """)

    def _connect(self) -> None:
        self.open_action.triggered.connect(self.choose_video)
        self.canvas.fileDropped.connect(lambda value: self.load_video(Path(value)))
        self.canvas.regionChanged.connect(self._region_from_canvas)
        self.clear_button.clicked.connect(lambda: self.canvas.set_region(None, True))
        self.reset_button.clicked.connect(self.reset_view)
        self.previous_button.clicked.connect(lambda: self.load_frame(self.current_frame_index - 1))
        self.next_button.clicked.connect(lambda: self.load_frame(self.current_frame_index + 1))
        self.timeline.valueChanged.connect(self.load_frame)
        self.time_input.editingFinished.connect(self._seek_time)
        self.original_radio.clicked.connect(lambda: self._set_mode(ViewMode.ORIGINAL))
        self.marked_radio.clicked.connect(lambda: self._set_mode(ViewMode.MARKED))
        self.restored_radio.clicked.connect(lambda: self._set_mode(ViewMode.RESTORED))
        for spin in (self.x_spin, self.y_spin, self.w_spin, self.h_spin):
            spin.valueChanged.connect(self._region_from_fields)
        self.browse_output_button.clicked.connect(self.choose_output)
        self.export_button.clicked.connect(self.start_export)
        self.cancel_button.clicked.connect(self.cancel_export)
        self.open_file_button.clicked.connect(self.open_output_file)
        self.open_folder_button.clicked.connect(self.open_output_folder)

    def _refresh_tool_status(self) -> None:
        if self.ffmpeg and self.ffprobe:
            try:
                self.tool_status.setText(ffmpeg_version(self.ffmpeg) + "\nNVENC 将在导出时实际编码探测")
                return
            except BaseException as exc:
                LOGGER.warning("FFmpeg check failed: %s", exc)
        self.tool_status.setText("未找到完整 FFmpeg。请使用含 ffmpeg 文件夹的发行目录。")

    def _set_loaded(self, loaded: bool) -> None:
        for widget in (
            self.original_radio, self.marked_radio, self.restored_radio, self.clear_button,
            self.reset_button, self.previous_button, self.next_button, self.timeline,
            self.time_input, self.output_edit, self.browse_output_button,
            self.x_spin, self.y_spin, self.w_spin, self.h_spin,
        ):
            widget.setEnabled(loaded)
        self.export_button.setEnabled(loaded and self.canvas.region is not None and self.export_thread is None)
        self.open_file_button.setEnabled(self.last_output is not None)
        self.open_folder_button.setEnabled(self.last_output is not None)

    @Slot()
    def choose_video(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(self, "打开视频", "", VIDEO_FILTER)
        if filename:
            self.load_video(Path(filename))

    def load_video(self, path: Path) -> None:
        try:
            if path.suffix.lower() not in {".mp4", ".mov", ".mkv", ".webm"}:
                raise RegionCleanerError("请选择 MP4、MOV、MKV 或 WebM 视频")
            if not self.ffprobe:
                raise RegionCleanerError("未找到 FFprobe。请使用完整发行目录，或安装 FFmpeg 并加入 PATH。")
            media = probe_media(path.resolve(), self.ffprobe)
            frame = read_frame(media.path, 0)
            self.media = media
            self.current_frame_index = 0
            self.current_frame = frame
            self.canvas.set_region(None)
            self.canvas.set_frame(frame)
            self.timeline.setRange(0, max(0, media.frame_count - 1))
            self.time_input.setRange(0.0, max(0.0, media.duration))
            self.file_value.setText(media.path.name)
            self.file_value.setToolTip(str(media.path))
            self.size_value.setText(f"{media.width} × {media.height} · {media.fps:.3f} fps")
            self.duration_value.setText(f"{format_time(media.duration)} · {media.frame_count} 帧")
            audio = f"音频 {media.audio_codec}" if media.has_audio else "无音频"
            self.stream_value.setText(f"视频 {media.video_codec} · {audio}")
            self.output_edit.setText(str(default_output_path(media.path)))
            self.status_label.setText("视频已载入，请在画面上选择固定矩形区域")
            self.statusBar().showMessage(f"已载入 {media.path.name}")
            self.last_output = None
            self._sync_frame_controls()
            self._set_loaded(True)
        except BaseException as exc:
            self._show_error("无法载入视频", exc)

    def load_frame(self, index: int) -> None:
        if not self.media:
            return
        index = max(0, min(int(index), self.media.frame_count - 1))
        try:
            self.current_frame = read_frame(self.media.path, index)
            self.current_frame_index = index
            self._sync_frame_controls()
            self._set_mode(self._selected_mode())
        except BaseException as exc:
            self._show_error("无法读取视频帧", exc)

    def _sync_frame_controls(self) -> None:
        if not self.media:
            return
        with QSignalBlocker(self.timeline):
            self.timeline.setValue(self.current_frame_index)
        with QSignalBlocker(self.time_input):
            self.time_input.setValue(self.current_frame_index / max(self.media.fps, 1e-9))
        self.frame_label.setText(f"帧 {self.current_frame_index + 1} / {self.media.frame_count}")
        self.previous_button.setEnabled(self.current_frame_index > 0)
        self.next_button.setEnabled(self.current_frame_index < self.media.frame_count - 1)

    def _seek_time(self) -> None:
        if self.media:
            self.load_frame(round(self.time_input.value() * self.media.fps))

    def _selected_mode(self) -> ViewMode:
        if self.original_radio.isChecked():
            return ViewMode.ORIGINAL
        if self.restored_radio.isChecked():
            return ViewMode.RESTORED
        return ViewMode.MARKED

    def _set_mode(self, mode: ViewMode) -> None:
        if self.current_frame is None:
            return
        try:
            if mode == ViewMode.RESTORED:
                if not self.canvas.region:
                    raise RegionCleanerError("请先选择一个矩形区域")
                self.canvas.set_frame(restore_frame(self.current_frame, self.canvas.region))
            else:
                self.canvas.set_frame(self.current_frame)
            self.canvas.set_view_mode(mode)
            self.status_label.setText({
                ViewMode.ORIGINAL: "正在查看原始帧",
                ViewMode.MARKED: "正在查看原视频坐标区域",
                ViewMode.RESTORED: "当前帧 TELEA 修复预览（导出将分析多帧）",
            }[mode])
        except BaseException as exc:
            self.marked_radio.setChecked(True)
            self.canvas.set_frame(self.current_frame)
            self.canvas.set_view_mode(ViewMode.MARKED)
            self._show_error("无法生成修复预览", exc)

    @Slot(object)
    def _region_from_canvas(self, region: Region | None) -> None:
        if self.restored_radio.isChecked() and self.current_frame is not None:
            self.marked_radio.setChecked(True)
            self.canvas.set_frame(self.current_frame)
            self.canvas.set_view_mode(ViewMode.MARKED)
            self.status_label.setText("区域已更改，正在查看原视频坐标区域")
        values = (region.x, region.y, region.width, region.height) if region else (0, 0, 0, 0)
        for spin, value in zip((self.x_spin, self.y_spin, self.w_spin, self.h_spin), values):
            with QSignalBlocker(spin):
                spin.setValue(value)
        self.export_button.setEnabled(region is not None and self.export_thread is None)
        if region:
            self.region_hint.setText(f"原视频像素：x={region.x}, y={region.y}, width={region.width}, height={region.height}")
        else:
            self.region_hint.setText("在视频画面上拖拽创建矩形；可移动并从八个手柄缩放。")

    @Slot()
    def _region_from_fields(self) -> None:
        if not self.media:
            return
        try:
            region = Region(self.x_spin.value(), self.y_spin.value(), self.w_spin.value(), self.h_spin.value())
            region.validate(self.media.width, self.media.height)
            self.canvas.set_region(region)
            self._region_from_canvas(region)
        except ValueError:
            self.export_button.setEnabled(False)

    def reset_view(self) -> None:
        if not self.media:
            return
        self.marked_radio.setChecked(True)
        self.canvas.set_region(None, True)
        self.load_frame(0)

    @Slot()
    def choose_output(self) -> None:
        if not self.media:
            return
        filename, _ = QFileDialog.getSaveFileName(self, "导出新视频", self.output_edit.text(), "MP4 视频 (*.mp4)")
        if filename:
            self.output_edit.setText(filename)

    @Slot()
    def start_export(self) -> None:
        if not self.media or not self.canvas.region:
            self._show_error("无法导出", RegionCleanerError("请先载入视频并选择矩形区域"))
            return
        if not self.ffmpeg or not self.ffprobe:
            self._show_error("缺少 FFmpeg", RegionCleanerError("请使用完整发行目录，或安装 FFmpeg 并加入 PATH。"))
            return
        try:
            if not self.output_edit.text().strip():
                raise RegionCleanerError("请选择输出文件路径")
            output = validate_output_path(self.media.path, Path(self.output_edit.text()))
        except BaseException as exc:
            self._show_error("输出路径不可用", exc)
            return
        self.last_output = None
        self.progress.setValue(0)
        self.status_label.setText("正在准备导出…")
        self.cancel_button.setEnabled(True)
        self.export_button.setEnabled(False)
        self.open_file_button.setEnabled(False)
        self.open_folder_button.setEnabled(False)
        self.export_thread = QThread(self)
        self.export_worker = ExportWorker(
            self.media, output, self.canvas.region, self.ffmpeg, self.ffprobe, self.encoder_check.isChecked()
        )
        self.export_worker.moveToThread(self.export_thread)
        self.export_thread.started.connect(self.export_worker.run)
        self.export_worker.progress.connect(self._export_progress)
        self.export_worker.succeeded.connect(self._export_succeeded)
        self.export_worker.failed.connect(self._export_failed)
        self.export_worker.cancelled.connect(self._export_cancelled)
        self.export_worker.completed.connect(self.export_thread.quit)
        self.export_worker.completed.connect(self.export_worker.deleteLater)
        self.export_thread.finished.connect(self._export_finished)
        self.export_thread.finished.connect(self.export_thread.deleteLater)
        self.export_thread.start()

    @Slot(object)
    def _export_progress(self, update: ExportProgress) -> None:
        value = round(update.frame / update.total * 1000) if update.total else 0
        self.progress.setValue(max(0, min(1000, value)))
        self.elapsed_label.setText(f"已用 {format_time(update.elapsed)}")
        self.remaining_label.setText(f"剩余 {format_time(update.remaining)}")
        self.status_label.setText(update.message)

    @Slot(object)
    def _export_succeeded(self, result: ExportResult) -> None:
        self.last_output = result.output_path
        fallback = "（已自动回退）" if result.used_fallback else ""
        self.status_label.setText(
            f"成功：{result.output_path.name}\n{result.verification.width}×{result.verification.height} · "
            f"{result.verification.fps:.3f} fps · 音频 {'已保留' if result.verification.has_audio else '无'} · "
            f"{result.encoder}{fallback}"
        )
        self.progress.setValue(1000)
        self.statusBar().showMessage(f"导出完成，用时 {result.elapsed:.2f} 秒")

    @Slot(str)
    def _export_failed(self, message: str) -> None:
        self.status_label.setText(f"失败：{message}")
        self.statusBar().showMessage("导出失败")
        QMessageBox.critical(self, "导出失败", message)

    @Slot()
    def _export_cancelled(self) -> None:
        self.status_label.setText("已取消；未生成输出文件，源文件未更改")
        self.statusBar().showMessage("导出已取消")

    @Slot()
    def _export_finished(self) -> None:
        self.export_thread = None
        self.export_worker = None
        self.cancel_button.setEnabled(False)
        self.export_button.setEnabled(self.media is not None and self.canvas.region is not None)
        self.open_file_button.setEnabled(self.last_output is not None)
        self.open_folder_button.setEnabled(self.last_output is not None)
        if self._closing:
            self.close()

    @Slot()
    def cancel_export(self) -> None:
        if self.export_worker:
            self.status_label.setText("正在安全取消…")
            self.cancel_button.setEnabled(False)
            self.export_worker.cancel()

    @Slot()
    def open_output_file(self) -> None:
        if self.last_output:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.last_output)))

    @Slot()
    def open_output_folder(self) -> None:
        if not self.last_output:
            return
        if os.name == "nt":
            subprocess.Popen(["explorer.exe", "/select,", str(self.last_output)], shell=False)
        else:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.last_output.parent)))

    def _show_error(self, title: str, error: BaseException) -> None:
        message = readable_error(error)
        LOGGER.exception(title, exc_info=error)
        self.status_label.setText(f"错误：{message}")
        self.statusBar().showMessage(title)
        QMessageBox.critical(self, title, message)

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.export_thread and self.export_thread.isRunning():
            answer = QMessageBox.question(self, "导出正在进行", "要取消导出并退出吗？")
            if answer == QMessageBox.StandardButton.Yes:
                self._closing = True
                self.cancel_export()
            event.ignore()
            return
        event.accept()
