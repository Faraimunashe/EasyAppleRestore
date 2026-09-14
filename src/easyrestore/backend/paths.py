from __future__ import annotations

import os
import shutil
from pathlib import Path

from easyrestore.constants import APP_ID


def cache_root() -> Path:
    xdg = os.environ.get("XDG_CACHE_HOME")
    if xdg:
        return Path(xdg) / "easyrestore"
    return Path.home() / ".cache" / "easyrestore"


def ipsw_cache_dir() -> Path:
    path = cache_root() / "ipsw"
    path.mkdir(parents=True, exist_ok=True)
    return path


def default_ipsw_path(identifier: str, version: str, buildid: str) -> Path:
    safe_id = identifier.replace(",", "_")
    return ipsw_cache_dir() / f"{safe_id}_{version}_{buildid}.ipsw"


def free_bytes(path: Path | None = None) -> int:
    target = path or ipsw_cache_dir()
    usage = shutil.disk_usage(target)
    return int(usage.free)


def app_data_marker() -> str:
    return APP_ID
