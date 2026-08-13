"""Application entry point and centralized crash logging."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
import json
from pathlib import Path
import sys

from PySide6.QtCore import QStandardPaths
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication, QMessageBox

from . import __version__
from .errors import readable_error
from .exporter import export_video
from .ffmpeg import find_tool, probe_media
from .gui import MainWindow
from .models import Region


def configure_logging() -> Path:
    root = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation))
    root.mkdir(parents=True, exist_ok=True)
    path = root / "video-region-cleaner.log"
    handler = RotatingFileHandler(path, maxBytes=1_000_000, backupCount=2, encoding="utf-8")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[handler],
    )
    return path


def configure_ui_font(app: QApplication) -> None:
    """Select a CJK-capable Windows UI font, including offscreen test runs."""
    candidates = ["Microsoft YaHei UI", "Microsoft YaHei", "SimHei", "Noto Sans CJK SC"]
    families = set(QFontDatabase.families())
    for font_file in (
        Path("C:/Windows/Fonts/msyh.ttc"),
        Path("C:/Windows/Fonts/msyhbd.ttc"),
        Path("C:/Windows/Fonts/simhei.ttf"),
    ):
        if font_file.is_file():
            identifier = QFontDatabase.addApplicationFont(str(font_file))
            if identifier >= 0:
                families.update(QFontDatabase.applicationFontFamilies(identifier))
    family = next((name for name in candidates if name in families), app.font().family())
    app.setFont(QFont(family, 9))


def packaged_self_test(arguments: list[str]) -> int | None:
    """Run an opt-in release QA export without starting the GUI."""
    if "--packaged-self-test" not in arguments:
        return None
    position = arguments.index("--packaged-self-test")
    values = arguments[position + 1:position + 4]
    if len(values) != 3:
        return 2
    source = Path(values[0]).expanduser().resolve()
    output = Path(values[1]).expanduser().resolve()
    evidence = Path(values[2]).expanduser().resolve()
    # ASCII sentinel lets Windows PowerShell 5.1 launch QA cover a genuine
    # Chinese output name without its script/argument encoding changing it.
    if output.name == "__unicode_output__.mp4":
        output = output.with_name("中文 输出.mp4")
    payload: dict[str, object]
    try:
        ffmpeg = find_tool("ffmpeg")
        ffprobe = find_tool("ffprobe")
        if not ffmpeg or not ffprobe:
            raise RuntimeError("bundled FFmpeg/FFprobe was not found")
        media = probe_media(source, ffprobe)
        result = export_video(
            media, output, Region(15, 15, 330, 80), ffmpeg, ffprobe,
            prefer_nvenc=False,
        )
        payload = {
            "ok": True,
            "ffmpeg": "bundled:ffmpeg/bin/ffmpeg.exe",
            "ffprobe": "bundled:ffmpeg/bin/ffprobe.exe",
            "output": result.output_path.name,
            "frames": result.frames_written,
            "encoder": result.encoder,
            "duration": result.verification.duration,
            "width": result.verification.width,
            "height": result.verification.height,
            "fps": result.verification.fps,
            "has_audio": result.verification.has_audio,
        }
        code = 0
    except BaseException as exc:
        payload = {"ok": False, "error": readable_error(exc)}
        code = 1
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return code


def main() -> int:
    self_test_result = packaged_self_test(sys.argv)
    if self_test_result is not None:
        return self_test_result
    app = QApplication(sys.argv)
    app.setApplicationName("Video Region Cleaner")
    app.setApplicationVersion(__version__)
    app.setOrganizationName("Video Region Cleaner")
    configure_ui_font(app)
    log_path = configure_logging()
    try:
        window = MainWindow()
        window.show()
        return app.exec()
    except BaseException as exc:
        logging.getLogger(__name__).exception("Unhandled startup error")
        QMessageBox.critical(None, "启动失败", f"{readable_error(exc)}\n\n日志：{log_path}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
