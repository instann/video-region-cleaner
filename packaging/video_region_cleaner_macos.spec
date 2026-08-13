# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

project = Path(SPECPATH).parent
ffmpeg_bin = project / "vendor" / "ffmpeg" / "bin"
ffmpeg_doc = project / "vendor" / "ffmpeg" / "doc-macos"

binaries = [
    (str(ffmpeg_bin / "ffmpeg"), "ffmpeg/bin"),
    (str(ffmpeg_bin / "ffprobe"), "ffmpeg/bin"),
]
datas = [
    (str(project / "LICENSE"), "."),
    (str(project / "NOTICE.md"), "."),
    (str(project / "README.md"), "."),
    (str(project / "README_EN.md"), "."),
    (str(project / "THIRD_PARTY_NOTICES.md"), "."),
    (str(project / "packaging" / "licenses" / "GPL-3.0.txt"), "licenses"),
    (str(project / "packaging" / "licenses" / "LGPL-3.0.txt"), "licenses"),
    (str(ffmpeg_doc / "FFMPEG_BUILD_LICENSE.txt"), "ffmpeg/doc"),
    (str(ffmpeg_doc / "FFMPEG_BUILD_FINGERPRINT.txt"), "ffmpeg/doc"),
    (str(ffmpeg_doc / "FFMPEG_BUILD_README.txt"), "ffmpeg/doc"),
    (str(ffmpeg_doc / "FFMPEG_VERSION_AND_CONFIGURATION.txt"), "ffmpeg/doc"),
    (str(ffmpeg_doc / "FFMPEG_SOURCE_REVISIONS.txt"), "ffmpeg/doc"),
    (str(ffmpeg_doc / "X264_LICENSE.txt"), "ffmpeg/doc"),
]

a = Analysis(
    [str(project / "run_gui.pyw")],
    pathex=[str(project / "src")],
    binaries=binaries,
    datas=datas,
    hiddenimports=["cv2", "numpy"],
    hookspath=[],
    runtime_hooks=[],
    excludes=["PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.QtWebEngineQuick"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="VideoRegionCleaner",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="VideoRegionCleaner",
)
app = BUNDLE(
    coll,
    name="VideoRegionCleaner.app",
    bundle_identifier="com.instann.video-region-cleaner",
    version="1.0.0",
    info_plist={
        "CFBundleDisplayName": "Video Region Cleaner",
        "CFBundleName": "Video Region Cleaner",
        "NSHighResolutionCapable": True,
        "LSMinimumSystemVersion": "13.0",
    },
)
