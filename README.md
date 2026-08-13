# Video Region Cleaner

简体中文 ｜ [English](README_EN.md)

[![Windows x64](https://img.shields.io/badge/Windows-x64-0078D4?logo=windows)](https://github.com/instann/video-region-cleaner/releases/latest)
[![macOS](https://img.shields.io/badge/macOS-Apple%20Silicon%20%7C%20Intel-000000?logo=apple)](https://github.com/instann/video-region-cleaner/releases/latest)
[![Offline](https://img.shields.io/badge/processing-100%25%20offline-2ea44f)](#为什么选择它)
[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**在视频代表帧上框选固定区域，离线预览修复效果，再导出保留音频的新视频。** 适合处理自有或获授权内容中的固定标签、时间戳、相机叠加层和审阅标记。

无需上传视频，无需预装 Python，源文件永不覆盖。

![Video Region Cleaner 已选择固定矩形区域](docs/screenshots/04_adjusted_1280x720.png)

## 下载与使用

> [下载最新版本（Windows x64、macOS Apple Silicon / Intel）](https://github.com/instann/video-region-cleaner/releases/latest)

1. 下载适合电脑的压缩包，并**完整解压**：
   - Windows：`VideoRegionCleaner-*-windows-x64-pyinstaller.zip`
   - M1/M2/M3/M4 等 Apple Silicon Mac：`VideoRegionCleaner-*-macos-arm64.zip`
   - Intel Mac：`VideoRegionCleaner-*-macos-x86_64.zip`
2. Windows 双击 `VideoRegionCleaner.exe`；macOS 双击 `VideoRegionCleaner.app`。
3. 点击“打开视频”，或把 MP4、MOV、MKV、WebM 拖入窗口。
4. 用时间滑块、逐帧按钮或秒数输入定位代表帧。
5. 在画面上拖出矩形；可移动、缩放、清除或重画。
6. 对比“原帧 / 区域标记 / 修复预览”，确认后选择输出路径并导出。

程序显示进度、耗时和预计剩余时间，支持取消。完成后可直接打开文件或所在文件夹。默认输出名为 `<源文件名>_clean.mp4`；如已存在会自动追加编号，绝不覆盖已有文件。

发行包目前未进行开发者签名或 Apple 公证，Windows SmartScreen 或 macOS Gatekeeper 可能显示提醒。macOS 首次打开可在 Finder 中按住 Control 点击应用，选择“打开”并确认。请仅从本仓库 Releases 下载，并校验同一 Release 提供的 SHA-256。

## 为什么选择它

- **真正离线**：视频不离开电脑，程序不上传媒体，也不发送遥测。
- **所见即所得**：可加载任意代表帧，实时查看原帧、精确选区和单帧修复结果。
- **选区准确**：矩形始终使用原视频像素坐标，兼容黑边、窗口缩放、高 DPI、横屏和竖屏。
- **面向普通用户**：拖放载入、时间轴定位、八方向缩放、进度、ETA、取消与明确错误提示。
- **可靠导出**：流式 OpenCV TELEA 处理，保留音频且不缓存整段视频；Windows 实际探测 NVENC，macOS 实际探测 VideoToolbox，失败自动回退 `libx264`。
- **可复核**：包含单元测试、GUI 交互测试、端到端测试、打包启动证据和合成测试素材。

## 适合与不适合

适合：位置固定、面积较小、背景纹理相对简单的标签、时间戳、相机叠加层或内部审阅标记。

不适合：动态字幕、移动目标、大面积遮挡、复杂纹理或要求逐像素恢复原始内容的场景。当前版本只处理**一个固定矩形区域**，不做目标跟踪。

## 工作原理

应用逐帧读取视频，仅对选定矩形及其修复边界执行 TELEA 图像修复，再通过 FFmpeg 编码新视频并封装原音频。平台原生硬件编码器（Windows NVENC / macOS VideoToolbox）只有在实际试编码成功时启用，否则自动使用 CPU `libx264`。若源音频不能直接封装到 MP4，则转码为 AAC。导出结束后，FFprobe 会核验分辨率、帧率、时长和音频流。

## 从源码运行

需要 Python 3.11 或更高版本。Windows 使用 PowerShell：

```powershell
git clone https://github.com/instann/video-region-cleaner.git
cd video-region-cleaner
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pip install -e . --no-deps
powershell -ExecutionPolicy Bypass -File scripts\prepare_ffmpeg.ps1
.\.venv\Scripts\python.exe run_gui.pyw
```

macOS 13 或更高版本使用终端（需要 Xcode Command Line Tools；FFmpeg 与 x264 会从固定的官方源码版本按当前 Apple Silicon / Intel 架构构建）：

```bash
git clone https://github.com/instann/video-region-cleaner.git
cd video-region-cleaner
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pip install -e . --no-deps
scripts/prepare_ffmpeg_macos.sh
.venv/bin/python run_gui.pyw
```

运行测试：

```bash
# macOS
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q
.venv/bin/python scripts/run_e2e.py
```

CLI 入口复用同一处理核心：

```bash
.venv/bin/python region_cleaner.py examples/demo_overlay.mp4 \
  --region 15,15,330,80 --output examples/demo_overlay_clean.mp4
```

## 构建 macOS `.app`

在目标架构的 Mac 上运行（Apple Silicon 与 Intel 必须分别构建）：

```bash
scripts/build_macos.sh
```

脚本会从固定版本的 FFmpeg 8.1.2 与 x264 源码构建可再分发的原生工具，生成并临时签名 `.app`、运行打包后端到端自测，然后输出 `release/VideoRegionCleaner-1.0.0-macos-<架构>.zip` 及其 SHA-256。若要正式签名，可将 `CODESIGN_IDENTITY` 设为 Developer ID Application 证书名称；Apple 公证仍由发布者完成。仓库中的 `macOS` GitHub Actions 工作流会同时构建 Apple Silicon 和 Intel 产物。

## 构建 Windows x64 发行版

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_pyinstaller.ps1
powershell -ExecutionPolicy Bypass -File scripts\build_nuitka.ps1
powershell -ExecutionPolicy Bypass -File scripts\write_checksums.ps1
```

- PyInstaller：`release/pyinstaller/VideoRegionCleaner/VideoRegionCleaner.exe`
- Nuitka：`release/nuitka/run_gui.dist/VideoRegionCleaner.exe`
- SHA-256：`release/SHA256SUMS.txt`
- 测试与打包验证：[docs/VERIFICATION_REPORT.md](docs/VERIFICATION_REPORT.md)
- 公有发布检查：[docs/PUBLIC_RELEASE_CHECKLIST.md](docs/PUBLIC_RELEASE_CHECKLIST.md)
- 第三方组件与许可证：[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)

构建脚本下载固定版本的 FFmpeg 9.0.1 x64 essentials 静态构建，并在解压前验证发布方 SHA-256。二进制发行包包含相应许可文本和构建信息。公开分发者仍需自行复核 FFmpeg GPLv3 义务及源代码提供方式。

## 已知限制

- 当前仅支持一个固定矩形，不跟踪移动区域。
- TELEA 在大遮挡、复杂运动和高频纹理上可能产生模糊或拖影。
- 可变帧率素材会按探测到的平均帧率输出为常帧率视频。
- 输出为 H.264 `yuv420p` MP4，不完整保留 HDR、高位深和色彩元数据。
- 无可用平台硬件编码器时使用 CPU；耗时取决于视频长度、分辨率、CPU 和选区复杂度。
- 当前发行版未签名，可能触发 Windows SmartScreen。
- macOS 发行版未公证，首次启动可能触发 Gatekeeper；请仅使用仓库 Release 产物。

## 合法使用、许可与署名

本工具仅用于用户自有或已获授权编辑的内容。用户须自行遵守适用法律、合同、许可证、平台条款以及披露和署名义务。本项目不提供法律意见，也不受任何平台或商标所有者认可、赞助或关联。

`examples/demo_overlay.mp4` 和文档截图均由本项目使用合成素材生成，不含第三方平台标识或私人内容。

项目采用 [MIT License](LICENSE)，上游署名见 [NOTICE.md](NOTICE.md)。FFmpeg 作为独立进程随发行包按其构建所附 GPLv3 条款分发，详情见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

如果这个项目帮你省下了重复的逐帧处理，欢迎点一下 **Star**。明确的复现步骤、问题素材和小范围 PR 也都很有价值。
