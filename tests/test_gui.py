from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
from pathlib import Path
from PySide6.QtCore import QPoint, Qt

from video_region_cleaner.gui import MainWindow
from video_region_cleaner.models import Region
from video_region_cleaner.canvas import ViewMode


def test_initial_gui_state(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    assert "Video Region Cleaner" in window.windowTitle()
    assert not window.export_button.isEnabled()
    assert "尚未载入" in window.file_value.text()


def test_canvas_draw_move_and_resize(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    window.canvas.resize(800, 450)
    window.canvas.set_frame(np.zeros((720, 1280, 3), dtype=np.uint8))
    qtbot.mousePress(window.canvas, Qt.MouseButton.LeftButton, pos=QPoint(100, 90))
    qtbot.mouseMove(window.canvas, QPoint(300, 190))
    qtbot.mouseRelease(window.canvas, Qt.MouseButton.LeftButton, pos=QPoint(300, 190))
    first = window.canvas.region
    assert first is not None and first.width > 0 and first.height > 0
    center = QPoint(200, 140)
    qtbot.mousePress(window.canvas, Qt.MouseButton.LeftButton, pos=center)
    qtbot.mouseMove(window.canvas, QPoint(240, 165))
    qtbot.mouseRelease(window.canvas, Qt.MouseButton.LeftButton, pos=QPoint(240, 165))
    moved = window.canvas.region
    assert moved is not None and moved.x > first.x and moved.y > first.y
    view = window.canvas._region_rect()
    assert view is not None
    bottom_right = view.bottomRight().toPoint()
    qtbot.mousePress(window.canvas, Qt.MouseButton.LeftButton, pos=bottom_right)
    qtbot.mouseMove(window.canvas, bottom_right + QPoint(25, 20))
    qtbot.mouseRelease(window.canvas, Qt.MouseButton.LeftButton, pos=bottom_right + QPoint(25, 20))
    resized = window.canvas.region
    assert resized is not None and resized.width > moved.width and resized.height > moved.height


def test_coordinate_fields_update_canvas(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    window.canvas.set_frame(np.zeros((1080, 1920, 3), dtype=np.uint8))
    window.media = type("Media", (), {"width": 1920, "height": 1080})()
    window.x_spin.setValue(101)
    window.y_spin.setValue(72)
    window.w_spin.setValue(500)
    window.h_spin.setValue(120)
    assert window.canvas.region == Region(101, 72, 500, 120)


def test_gui_worker_exports_and_reports_success(qtbot, tmp_path: Path):
    root = Path(__file__).resolve().parents[1]
    window = MainWindow()
    qtbot.addWidget(window)
    window.load_video(root / "examples" / "demo_overlay.mp4")
    window.canvas.set_region(Region(15, 15, 330, 80), True)
    output = tmp_path / "gui 中文 output.mp4"
    window.output_edit.setText(str(output))
    window.encoder_check.setChecked(False)
    window.start_export()
    qtbot.waitUntil(lambda: window.export_thread is None, timeout=30_000)
    assert output.is_file()
    assert window.last_output == output
    assert "成功" in window.status_label.text()


def test_gui_worker_cancel_cleans_output(qtbot, tmp_path: Path):
    root = Path(__file__).resolve().parents[1]
    window = MainWindow()
    qtbot.addWidget(window)
    window.load_video(root / "examples" / "demo_overlay.mp4")
    window.canvas.set_region(Region(15, 15, 330, 80), True)
    output = tmp_path / "cancelled.mp4"
    window.output_edit.setText(str(output))
    window.encoder_check.setChecked(False)
    window.start_export()
    window.cancel_export()
    qtbot.waitUntil(lambda: window.export_thread is None, timeout=30_000)
    assert not output.exists()
    assert "取消" in window.status_label.text()


def test_editing_region_clears_stale_restoration_preview(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    original = np.zeros((120, 200, 3), dtype=np.uint8)
    original[20:40, 30:100] = 255
    window.current_frame = original
    window.canvas.set_frame(original)
    window.canvas.set_region(Region(25, 15, 90, 35))
    window.restored_radio.setChecked(True)
    window._set_mode(ViewMode.RESTORED)
    window.canvas.set_region(Region(30, 20, 70, 30), True)
    assert window.marked_radio.isChecked()
    assert not window.restored_radio.isChecked()
    assert np.array_equal(window.canvas._frame, original)
