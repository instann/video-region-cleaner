"""Safe, non-overwriting output naming."""

from __future__ import annotations

from pathlib import Path

from .errors import RegionCleanerError


def default_output_path(source: Path) -> Path:
    source = source.resolve()
    base = source.with_name(f"{source.stem}_clean.mp4")
    if not base.exists():
        return base
    counter = 2
    while True:
        candidate = source.with_name(f"{source.stem}_clean_{counter}.mp4")
        if not candidate.exists():
            return candidate
        counter += 1


def validate_output_path(source: Path, output: Path) -> Path:
    source = source.resolve()
    output = output.expanduser().resolve()
    if output.suffix.lower() != ".mp4":
        output = output.with_suffix(".mp4")
    if source == output:
        raise RegionCleanerError("输出文件不能覆盖源文件")
    if output.exists():
        raise RegionCleanerError(f"输出文件已存在：{output}")
    return output
