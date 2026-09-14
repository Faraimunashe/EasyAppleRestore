from __future__ import annotations

import os
import signal
import subprocess
from dataclasses import dataclass
from pathlib import Path

from easyrestore.backend.identifier import vendor_bin
from easyrestore.backend.paths import free_bytes, ipsw_cache_dir

CONFLICT_PROCESS_NAMES = (
    "gvfs-afc-volume-monitor",
    "gvfsd-afc",
)


@dataclass(frozen=True)
class CheckResult:
    key: str
    ok: bool
    message: str
    detail: str = ""
    pids: tuple[int, ...] = ()


def _pgrep_names(names: tuple[str, ...]) -> list[tuple[int, str]]:
    found: list[tuple[int, str]] = []
    try:
        completed = subprocess.run(
            ["ps", "-eo", "pid=,comm="],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return found
    for line in completed.stdout.splitlines():
        parts = line.strip().split(None, 1)
        if len(parts) != 2:
            continue
        try:
            pid = int(parts[0])
        except ValueError:
            continue
        comm = parts[1]
        if comm in names:
            found.append((pid, comm))
    return found


def check_usbmuxd() -> CheckResult:
    bundled = vendor_bin("usbmuxd")
    running = _pgrep_names(("usbmuxd",))
    if running:
        which = "bundled or system"
        return CheckResult(
            "usbmuxd",
            True,
            "usbmuxd is running",
            detail=f"{which}; pids={[pid for pid, _ in running]}",
            pids=tuple(pid for pid, _ in running),
        )
    if bundled is not None:
        return CheckResult(
            "usbmuxd",
            False,
            "usbmuxd is not running",
            detail=f"Bundled binary is available at {bundled}. The helper can start it.",
        )
    return CheckResult(
        "usbmuxd",
        False,
        "usbmuxd is not running and no bundled binary was found",
        detail="Build the vendor stack (./vendor/build.sh) or install usbmuxd.",
    )


def check_conflicts() -> CheckResult:
    found = _pgrep_names(CONFLICT_PROCESS_NAMES)
    if not found:
        return CheckResult(
            "conflicts",
            True,
            "No known conflicting programs are holding the device",
        )
    names = sorted({name for _, name in found})
    return CheckResult(
        "conflicts",
        False,
        "Another program may be holding the device",
        detail=", ".join(names),
        pids=tuple(pid for pid, _ in found),
    )


def check_disk_space(needed_bytes: int, path: Path | None = None) -> CheckResult:
    target = path or ipsw_cache_dir()
    available = free_bytes(target)
    # Extraction/personalization often needs roughly the IPSW size again.
    required = max(needed_bytes * 2, needed_bytes + 2 * 1024 * 1024 * 1024)
    if available >= required:
        return CheckResult(
            "disk",
            True,
            "Enough free disk space for extraction",
            detail=f"available={available} required={required}",
        )
    return CheckResult(
        "disk",
        False,
        "Not enough free disk space for extraction",
        detail=f"available={available} required={required}",
    )


def pause_processes(pids: tuple[int, ...]) -> list[int]:
    paused: list[int] = []
    for pid in pids:
        try:
            os.kill(pid, signal.SIGSTOP)
            paused.append(pid)
        except OSError:
            continue
    return paused


def resume_processes(pids: tuple[int, ...]) -> None:
    for pid in pids:
        try:
            os.kill(pid, signal.SIGCONT)
        except OSError:
            continue


def ensure_usbmuxd() -> CheckResult:
    """Start bundled usbmuxd if nothing is listening yet."""
    current = check_usbmuxd()
    if current.ok:
        return current
    binary = vendor_bin("usbmuxd")
    if binary is None:
        return current
    try:
        subprocess.Popen(  # noqa: S603
            [str(binary), "-v", "-f"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError as exc:
        return CheckResult("usbmuxd", False, "Could not start usbmuxd", detail=str(exc))
    # Re-check quickly; usbmuxd may take a moment.
    again = check_usbmuxd()
    if again.ok:
        return CheckResult("usbmuxd", True, "Started bundled usbmuxd", detail=again.detail)
    return CheckResult(
        "usbmuxd",
        True,
        "Started bundled usbmuxd (still starting)",
        detail=str(binary),
    )
