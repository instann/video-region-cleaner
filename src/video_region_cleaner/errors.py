"""Application exceptions and user-facing error formatting."""

from __future__ import annotations


class RegionCleanerError(RuntimeError):
    """Expected application error that can be shown to a user."""


class CancelledError(RegionCleanerError):
    """Raised when an export is cancelled by the user."""


def readable_error(error: BaseException) -> str:
    """Return a compact message without exposing an internal traceback."""
    if isinstance(error, FileNotFoundError):
        return f"找不到文件：{error.filename or error}"
    message = str(error).strip()
    return message or error.__class__.__name__

