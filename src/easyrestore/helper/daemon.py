from __future__ import annotations

import logging
from pathlib import Path

from easyrestore.backend.device import DeviceMode, pick_primary_device
from easyrestore.backend.preflight import (
    check_conflicts,
    check_disk_space,
    check_usbmuxd,
    ensure_usbmuxd,
    pause_processes,
)
from easyrestore.backend.restore_job import MANAGER, RestoreState
from easyrestore.backend.usb import scan_apple_devices
from easyrestore.constants import (
    HELPER_BUS_NAME,
    HELPER_INTERFACE,
    HELPER_OBJECT_PATH,
)
from easyrestore.helper.polkit import (
    NotAuthorizedError,
    polkit_enabled,
    require_preflight,
    require_restore,
)

log = logging.getLogger("easyrestore.helper")


def snapshot_device_mode() -> tuple[str, str, str]:
    """Return (mode, product, serial) for the primary connected Apple device."""
    device = pick_primary_device(scan_apple_devices())
    if device is None:
        return DeviceMode.DISCONNECTED.value, "", ""
    return device.mode.value, device.product, device.serial


class HelperService:
    """Privileged helper. Restore jobs keep running if the GUI disconnects."""

    def __init__(self, *, enforce_polkit: bool = False) -> None:
        self._paused_pids: list[int] = []
        self.enforce_polkit = enforce_polkit
        self.last_sender: str | None = None

    def GetDeviceMode(self) -> tuple[str, str, str]:
        mode, product, serial = snapshot_device_mode()
        log.info("GetDeviceMode -> %s (%s)", mode, product or "none")
        return mode, product, serial

    def RunPreflight(self, needed_bytes: int, pause_conflicts: bool) -> tuple[str, str, str]:
        """Return three `key|ok|message` strings for usbmuxd, conflicts, and disk."""
        if self.enforce_polkit:
            require_preflight(sender=self.last_sender)
        usbmuxd = ensure_usbmuxd() if not check_usbmuxd().ok else check_usbmuxd()
        conflicts = check_conflicts()
        if not conflicts.ok and pause_conflicts and conflicts.pids:
            paused = pause_processes(conflicts.pids)
            self._paused_pids.extend(paused)
            if paused:
                conflicts = type(conflicts)(
                    key="conflicts",
                    ok=True,
                    message="Paused conflicting programs for this restore",
                    detail=conflicts.detail,
                    pids=tuple(paused),
                )
        disk = check_disk_space(int(needed_bytes))

        def fmt(result) -> str:
            return f"{result.key}|{'1' if result.ok else '0'}|{result.message}"

        return fmt(usbmuxd), fmt(conflicts), fmt(disk)

    def StartRestore(self, ipsw_path: str, erase: bool) -> str:
        if self.enforce_polkit:
            require_restore(sender=self.last_sender)
        job = MANAGER.start(Path(ipsw_path), erase=bool(erase))
        log.info("StartRestore job=%s erase=%s path=%s", job.job_id, erase, ipsw_path)
        return job.job_id

    def GetRestoreStatus(self) -> tuple[str, str, str, int, str, int]:
        job = MANAGER.current
        if job is None:
            return "", RestoreState.IDLE.value, "", 0, "No restore in progress", -1
        status = job.status()
        return (
            status.job_id,
            status.state.value,
            status.phase,
            int(status.percent),
            status.message,
            -1 if status.exit_code is None else int(status.exit_code),
        )

    def GetRestoreLog(self, since_line: int) -> tuple[int, str]:
        job = MANAGER.current
        if job is None:
            return 0, ""
        return job.log_since(int(since_line))


async def run_helper(session_bus: bool = False) -> None:
    from dbus_next.aio import MessageBus
    from dbus_next.constants import BusType, MessageType
    from dbus_next.errors import DBusError
    from dbus_next.service import ServiceInterface, method

    enforce = polkit_enabled(session_bus=session_bus)
    service = HelperService(enforce_polkit=enforce)

    class DBusHelper(ServiceInterface):
        def __init__(self, impl: HelperService) -> None:
            super().__init__(HELPER_INTERFACE)
            self._impl = impl

        @method()
        def GetDeviceMode(self) -> "sss":  # type: ignore[name-defined]
            return list(self._impl.GetDeviceMode())

        @method()
        def RunPreflight(self, needed_bytes: "x", pause_conflicts: "b") -> "sss":  # type: ignore[name-defined]
            try:
                return list(self._impl.RunPreflight(int(needed_bytes), bool(pause_conflicts)))
            except NotAuthorizedError as exc:
                raise DBusError("org.freedesktop.DBus.Error.AccessDenied", str(exc)) from exc

        @method()
        def StartRestore(self, ipsw_path: "s", erase: "b") -> "s":  # type: ignore[name-defined]
            try:
                return self._impl.StartRestore(ipsw_path, erase)
            except NotAuthorizedError as exc:
                raise DBusError("org.freedesktop.DBus.Error.AccessDenied", str(exc)) from exc

        @method()
        def GetRestoreStatus(self) -> "sssisi":  # type: ignore[name-defined]
            return list(self._impl.GetRestoreStatus())

        @method()
        def GetRestoreLog(self, since_line: "i") -> "is":  # type: ignore[name-defined]
            return list(self._impl.GetRestoreLog(int(since_line)))

    bus_type = BusType.SESSION if session_bus else BusType.SYSTEM
    bus = await MessageBus(bus_type=bus_type).connect()

    def _capture_sender(message):
        if (
            message.message_type is MessageType.METHOD_CALL
            and message.path == HELPER_OBJECT_PATH
            and message.interface == HELPER_INTERFACE
        ):
            service.last_sender = message.sender
        return False

    bus.add_message_handler(_capture_sender)
    bus.export(HELPER_OBJECT_PATH, DBusHelper(service))
    await bus.request_name(HELPER_BUS_NAME)
    log.info(
        "Listening on %s bus as %s (polkit=%s)",
        bus_type.name.lower(),
        HELPER_BUS_NAME,
        enforce,
    )
    await bus.wait_for_disconnect()
