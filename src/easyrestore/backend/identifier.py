from __future__ import annotations

import os
import shutil
import subprocess
from functools import lru_cache
from pathlib import Path

from easyrestore.backend.paths import cache_root


def _looks_like_prefix(path: Path) -> bool:
    return (path / "bin").is_dir() or (path / "sbin").is_dir()


@lru_cache(maxsize=1)
def vendor_prefix() -> Path | None:
    """Resolve the vendored libimobiledevice install prefix, if present."""
    env = os.environ.get("EASYRESTORE_VENDOR_PREFIX")
    if env:
        path = Path(env)
        if _looks_like_prefix(path):
            return path
    # AppImage / portable layout: …/usr/lib/easyrestore/{venv,vendor}
    # When running from the embedded venv, sys.prefix is …/easyrestore/venv.
    try:
        import sys

        portable = Path(sys.prefix).resolve().parent / "vendor"
        if _looks_like_prefix(portable):
            return portable
    except Exception:
        pass
    # src/easyrestore/backend/identifier.py -> repo root is parents[3]
    repo_prefix = Path(__file__).resolve().parents[3] / "vendor" / "prefix"
    if _looks_like_prefix(repo_prefix):
        return repo_prefix
    return None


def ensure_vendor_env() -> Path | None:
    """Export PATH/LD_LIBRARY_PATH for the vendor prefix. Safe to call repeatedly."""
    prefix = vendor_prefix()
    if prefix is None:
        return None
    os.environ.setdefault("EASYRESTORE_VENDOR_PREFIX", str(prefix))
    bin_dir = str(prefix / "bin")
    sbin_dir = str(prefix / "sbin")
    lib_dir = str(prefix / "lib")
    lib64_dir = str(prefix / "lib64")
    path_parts = os.environ.get("PATH", "").split(":")
    for directory in (sbin_dir, bin_dir):
        if directory not in path_parts:
            os.environ["PATH"] = f"{directory}:{os.environ.get('PATH', '')}"
    ld_parts = os.environ.get("LD_LIBRARY_PATH", "").split(":") if os.environ.get("LD_LIBRARY_PATH") else []
    for directory in (lib64_dir, lib_dir):
        if Path(directory).is_dir() and directory not in ld_parts:
            os.environ["LD_LIBRARY_PATH"] = (
                f"{directory}:{os.environ['LD_LIBRARY_PATH']}"
                if os.environ.get("LD_LIBRARY_PATH")
                else directory
            )
    return prefix


def vendor_bin(name: str) -> Path | None:
    ensure_vendor_env()
    prefix = vendor_prefix()
    if prefix is not None:
        for sub in ("bin", "sbin"):
            candidate = prefix / sub / name
            if candidate.is_file() and os.access(candidate, os.X_OK):
                return candidate
    which = shutil.which(name)
    return Path(which) if which else None


def vendor_tool_report() -> dict[str, str | None]:
    """Map critical tool names to resolved paths (or None)."""
    tools = ("idevicerestore", "ideviceinfo", "irecovery", "usbmuxd")
    return {name: str(path) if (path := vendor_bin(name)) else None for name in tools}


def resolve_product_type(timeout: float = 8.0) -> str | None:
    """Ask a connected normal-mode device for ProductType via ideviceinfo."""
    binary = vendor_bin("ideviceinfo")
    if binary is None:
        return None
    try:
        completed = subprocess.run(
            [str(binary), "-k", "ProductType"],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0:
        return None
    value = completed.stdout.strip()
    if not value or " " in value:
        return None
    return value


def identifier_hint_path() -> Path:
    return cache_root() / "last_identifier.txt"
