from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from easyrestore.backend.device import DeviceMode, DeviceSnapshot, pick_primary_device
from easyrestore.backend.preflight import (
    CheckResult,
    check_conflicts,
    check_disk_space,
    check_usbmuxd,
    ensure_usbmuxd,
    pause_processes,
)
from easyrestore.backend.restore_job import MANAGER, RestoreState, RestoreStatus
from easyrestore.backend.usb import scan_apple_devices
from easyrestore.constants import (
    APPLE_VENDOR_ID,
    HELPER_BUS_NAME,
    HELPER_INTERFACE,
    HELPER_OBJECT_PATH,
)


@dataclass(frozen=True)
class HelperStatus:
    connected: bool
    bus: str
    detail: str


def _parse_preflight_triple(raw: str) -> CheckResult:
    key, ok_flag, message = raw.split("|", 2)
    return CheckResult(key=key, ok=ok_flag == "1", message=message)


class HelperClient:
    """Talk to the privileged helper, or fall back to in-process operations."""

    def get_device_mode(self) -> DeviceSnapshot | None:
        raise NotImplementedError

    def status(self) -> HelperStatus:
        raise NotImplementedError

    def run_preflight(
        self, needed_bytes: int, *, pause_conflicts: bool = False
    ) -> list[CheckResult]:
        raise NotImplementedError

    def start_restore(self, ipsw_path: Path, *, erase: bool) -> str:
        raise NotImplementedError

    def get_restore_status(self) -> RestoreStatus:
        raise NotImplementedError

    def get_restore_log(self, since_line: int) -> tuple[int, str]:
        raise NotImplementedError


class LocalHelperClient(HelperClient):
    """In-process helper used when D-Bus is unavailable (development / AppImage)."""

    def __init__(self, sysfs_root=None) -> None:
        self._sysfs_root = sysfs_root
        self._paused_pids: list[int] = []

    def get_device_mode(self) -> DeviceSnapshot | None:
        return pick_primary_device(scan_apple_devices(self._sysfs_root))

    def status(self) -> HelperStatus:
        return HelperStatus(
            connected=True,
            bus="local",
            detail="Using built-in helper (no D-Bus). Restores run in this process.",
        )

    def run_preflight(
        self, needed_bytes: int, *, pause_conflicts: bool = False
    ) -> list[CheckResult]:
        usbmuxd = ensure_usbmuxd() if not check_usbmuxd().ok else check_usbmuxd()
        conflicts = check_conflicts()
        if not conflicts.ok and pause_conflicts and conflicts.pids:
            paused = pause_processes(conflicts.pids)
            self._paused_pids.extend(paused)
            if paused:
                conflicts = CheckResult(
                    key="conflicts",
                    ok=True,
                    message="Paused conflicting programs for this restore",
                    detail=conflicts.detail,
                    pids=tuple(paused),
                )
        disk = check_disk_space(needed_bytes)
        return [usbmuxd, conflicts, disk]

    def start_restore(self, ipsw_path: Path, *, erase: bool) -> str:
        return MANAGER.start(Path(ipsw_path), erase=erase).job_id

    def get_restore_status(self) -> RestoreStatus:
        job = MANAGER.current
        if job is None:
            return RestoreStatus("", RestoreState.IDLE, "", 0, "No restore in progress")
        return job.status()

    def get_restore_log(self, since_line: int) -> tuple[int, str]:
        job = MANAGER.current
        if job is None:
            return 0, ""
        return job.log_since(since_line)


class DBusHelperClient(HelperClient):
    def __init__(self, session_bus: bool = False) -> None:
        from PySide6.QtDBus import QDBusConnection, QDBusInterface

        self._bus_name = "session" if session_bus else "system"
        connection = (
            QDBusConnection.sessionBus() if session_bus else QDBusConnection.systemBus()
        )
        self._iface = QDBusInterface(
            HELPER_BUS_NAME,
            HELPER_OBJECT_PATH,
            HELPER_INTERFACE,
            connection,
        )

    def status(self) -> HelperStatus:
        if not self._iface.isValid():
            error = self._iface.lastError()
            return HelperStatus(
                False,
                self._bus_name,
                error.message() or "Helper is not running.",
            )
        return HelperStatus(True, self._bus_name, "Connected to the EasyRestore helper.")

    def _call(self, method: str, *args):
        if not self._iface.isValid():
            raise RuntimeError(self.status().detail)
        reply = self._iface.call(method, *args)
        if reply.errorName():
            raise RuntimeError(reply.errorMessage())
        return reply.arguments()

    def get_device_mode(self) -> DeviceSnapshot | None:
        args = self._call("GetDeviceMode")
        mode_name, product, serial = str(args[0]), str(args[1]), str(args[2])
        if mode_name == DeviceMode.DISCONNECTED.value:
            return None
        return DeviceSnapshot(
            mode=DeviceMode(mode_name),
            vendor_id=APPLE_VENDOR_ID,
            product_id=0,
            product=product,
            manufacturer="Apple Inc.",
            serial=serial,
            sysfs_path="",
        )

    def run_preflight(
        self, needed_bytes: int, *, pause_conflicts: bool = False
    ) -> list[CheckResult]:
        args = self._call("RunPreflight", needed_bytes, pause_conflicts)
        return [_parse_preflight_triple(str(item)) for item in args[:3]]

    def start_restore(self, ipsw_path: Path, *, erase: bool) -> str:
        args = self._call("StartRestore", str(ipsw_path), erase)
        return str(args[0])

    def get_restore_status(self) -> RestoreStatus:
        args = self._call("GetRestoreStatus")
        job_id, state, phase, percent, message, exit_code = args[:6]
        return RestoreStatus(
            job_id=str(job_id),
            state=RestoreState(str(state)),
            phase=str(phase),
            percent=int(percent),
            message=str(message),
            exit_code=None if int(exit_code) < 0 else int(exit_code),
        )

    def get_restore_log(self, since_line: int) -> tuple[int, str]:
        args = self._call("GetRestoreLog", since_line)
        return int(args[0]), str(args[1])


def connect_helper(prefer_session: bool = False) -> HelperClient:
    """Prefer the D-Bus helper; fall back to local in-process operations."""
    try:
        client = DBusHelperClient(session_bus=prefer_session)
        if client.status().connected:
            return client
        if not prefer_session:
            session_client = DBusHelperClient(session_bus=True)
            if session_client.status().connected:
                return session_client
    except Exception:
        pass
    return LocalHelperClient()
