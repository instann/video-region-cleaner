"""Export the repository's synthetic sample and print verified evidence."""

from __future__ import annotations

import json
from pathlib import Path
import time

from video_region_cleaner.exporter import export_video
from video_region_cleaner.ffmpeg import find_tool, probe_media
from video_region_cleaner.models import Region


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    ffmpeg = find_tool("ffmpeg", root / "vendor" / "ffmpeg" / "bin" / "ffmpeg.exe")
    ffprobe = find_tool("ffprobe", root / "vendor" / "ffmpeg" / "bin" / "ffprobe.exe")
    if not ffmpeg or not ffprobe:
        raise SystemExit("Prepare FFmpeg first with scripts/prepare_ffmpeg.ps1")
    source = root / "examples" / "demo_overlay.mp4"
    output = root / "release" / "e2e" / "demo_overlay_clean.mp4"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.unlink(missing_ok=True)
    media = probe_media(source, ffprobe)
    started = time.perf_counter()
    result = export_video(media, output, Region(15, 15, 330, 80), ffmpeg, ffprobe, prefer_nvenc=True)
    evidence = {
        "source": source.name,
        "output": str(output.relative_to(root)),
        "wall_seconds": round(time.perf_counter() - started, 3),
        "pipeline_seconds": round(result.elapsed, 3),
        "frames": result.frames_written,
        "encoder": result.encoder,
        "fallback": result.used_fallback,
        "verified": {
            "duration": result.verification.duration,
            "width": result.verification.width,
            "height": result.verification.height,
            "fps": result.verification.fps,
            "has_audio": result.verification.has_audio,
        },
    }
    evidence_path = output.parent / "E2E_RESULT.json"
    evidence_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(evidence, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

