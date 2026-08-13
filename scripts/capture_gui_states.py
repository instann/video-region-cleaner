"""Create deterministic GUI QA screenshots using only repository media."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from video_region_cleaner.app import configure_ui_font
from video_region_cleaner.canvas import ViewMode
from video_region_cleaner.gui import MainWindow
from video_region_cleaner.models import ExportProgress, ExportResult, Region


def shot(app: QApplication, window: MainWindow, path: Path) -> None:
    app.processEvents()
    path.parent.mkdir(parents=True, exist_ok=True)
    if not window.grab().save(str(path), "PNG"):
        raise RuntimeError(f"could not save {path}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--high-dpi", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    target = root / "docs" / "screenshots"
    app = QApplication.instance() or QApplication([])
    configure_ui_font(app)
    window = MainWindow()
    if args.high_dpi:
        window.resize(1280, 720)
        prefix = "highdpi_150"
    else:
        window.resize(1280, 720)
        prefix = "1280x720"
    window.show()
    shot(app, window, target / f"01_initial_{prefix}.png")

    window.load_video(root / "examples" / "demo_overlay.mp4")
    window.output_edit.setText(r"C:\Videos\demo_overlay_clean.mp4")
    shot(app, window, target / f"02_loaded_{prefix}.png")
    canvas = window.canvas
    rect = canvas.video_rect
    start = QPoint(round(rect.x + rect.width * 0.02), round(rect.y + rect.height * 0.03))
    end = QPoint(round(rect.x + rect.width * 0.36), round(rect.y + rect.height * 0.18))
    QTest.mousePress(canvas, Qt.MouseButton.LeftButton, pos=start)
    QTest.mouseMove(canvas, end, delay=10)
    QTest.mouseRelease(canvas, Qt.MouseButton.LeftButton, pos=end)
    shot(app, window, target / f"03_selected_{prefix}.png")

    selected = canvas.region or Region(15, 15, 330, 80)
    canvas.set_region(Region(selected.x + 12, selected.y + 8, selected.width + 28, selected.height + 12), True)
    shot(app, window, target / f"04_adjusted_{prefix}.png")

    window.restored_radio.setChecked(True)
    window._set_mode(ViewMode.RESTORED)
    shot(app, window, target / f"05_restored_{prefix}.png")

    window.resize(1920, 1080)
    window._export_progress(ExportProgress(72, 144, 3.2, 3.1, "正在逐帧修复并编码"))
    window.cancel_button.setEnabled(True)
    window.export_button.setEnabled(False)
    shot(app, window, target / f"06_processing_1920x1080_{prefix}.png")

    window.resize(1280, 720)
    window._export_cancelled()
    shot(app, window, target / f"07_cancelled_{prefix}.png")

    media = window.media
    assert media is not None
    result = ExportResult(
        root / "release" / "e2e" / "demo_overlay_clean.mp4", 6.668, 144,
        "libx264", True, media,
    )
    window._export_succeeded(result)
    shot(app, window, target / f"08_success_{prefix}.png")
    window.status_label.setText("失败：输出路径不可写。请选择有写入权限的位置后重试。")
    window.progress.setValue(0)
    shot(app, window, target / f"09_failure_{prefix}.png")
    window.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
