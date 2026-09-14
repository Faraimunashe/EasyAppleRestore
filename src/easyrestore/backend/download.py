"""Resumable HTTP download for large IPSW files."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from easyrestore.constants import IPSW_API_USER_AGENT

ProgressCallback = Callable[[int, int | None], None]
CancelCallback = Callable[[], bool]


@dataclass(frozen=True)
class DownloadResult:
    path: Path
    bytes_written: int
    resumed: bool
    total_size: int | None


class DownloadError(RuntimeError):
    pass


class DownloadCancelled(DownloadError):
    pass


def download_file(
    url: str,
    destination: Path,
    *,
    expected_size: int | None = None,
    chunk_size: int = 1024 * 1024,
    user_agent: str = IPSW_API_USER_AGENT,
    timeout: float = 60.0,
    on_progress: ProgressCallback | None = None,
    should_cancel: CancelCallback | None = None,
) -> DownloadResult:
    """Download to ``destination``, resuming via HTTP Range when a partial file exists."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(destination.suffix + ".partial")
    existing = partial.stat().st_size if partial.is_file() else 0
    resumed = existing > 0

    headers = {
        "User-Agent": user_agent,
        "Accept": "*/*",
    }
    if existing > 0:
        headers["Range"] = f"bytes={existing}-"

    request = Request(url, headers=headers, method="GET")
    try:
        response = urlopen(request, timeout=timeout)
    except HTTPError as exc:
        if existing > 0 and exc.code == 416:
            # Already complete according to the server; promote the partial file.
            partial.replace(destination)
            if on_progress:
                on_progress(existing, existing)
            return DownloadResult(destination, existing, True, existing)
        raise DownloadError(f"Download failed (HTTP {exc.code})") from exc
    except URLError as exc:
        raise DownloadError(f"Download failed: {exc.reason}") from exc

    with response:
        status = getattr(response, "status", None) or response.getcode()
        content_range = response.headers.get("Content-Range", "")
        content_length = response.headers.get("Content-Length")

        if existing > 0 and status == 200:
            # Server ignored Range — restart cleanly.
            existing = 0
            resumed = False
            partial.unlink(missing_ok=True)

        total: int | None = expected_size
        if content_range.startswith("bytes ") and "/" in content_range:
            try:
                total = int(content_range.rsplit("/", 1)[1])
            except ValueError:
                total = expected_size
        elif content_length and status == 200:
            try:
                total = int(content_length)
            except ValueError:
                total = expected_size
        elif content_length and status == 206 and existing > 0:
            try:
                total = existing + int(content_length)
            except ValueError:
                total = expected_size

        mode = "ab" if existing > 0 else "wb"
        written = existing
        if on_progress:
            on_progress(written, total)

        with partial.open(mode) as fh:
            while True:
                if should_cancel and should_cancel():
                    raise DownloadCancelled("Download cancelled.")
                chunk = response.read(chunk_size)
                if not chunk:
                    break
                fh.write(chunk)
                written += len(chunk)
                if on_progress:
                    on_progress(written, total)

    if total is not None and written != total:
        raise DownloadError(
            f"Download incomplete: got {written} bytes, expected {total}."
        )

    partial.replace(destination)
    return DownloadResult(destination, written, resumed, total)
