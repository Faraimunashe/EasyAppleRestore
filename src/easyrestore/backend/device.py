from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from easyrestore.constants import (
    IRECV_DFU_PID,
    IRECV_PORT_DFU_PID,
    IRECV_RECOVERY_PIDS,
    IRECV_WTF_PID,
    NORMAL_MODE_PIDS,
)


class DeviceMode(Enum):
    DISCONNECTED = "Disconnected"
    NORMAL = "Normal"
    RECOVERY = "Recovery"
    DFU = "DFU"
    RESTORE = "Restore"


_MODE_PRIORITY = {
    DeviceMode.DFU: 0,
    DeviceMode.RECOVERY: 1,
    DeviceMode.RESTORE: 2,
    DeviceMode.NORMAL: 3,
    DeviceMode.DISCONNECTED: 4,
}


def mode_from_product_id(product_id: int) -> DeviceMode:
    """Map an Apple USB product ID to a coarse device mode.

    Restore mode is not distinguishable from Normal by PID alone; a later
    lockdown / idevicerestore probe will refine that.
    """
    if product_id in {IRECV_DFU_PID, IRECV_WTF_PID, IRECV_PORT_DFU_PID}:
        return DeviceMode.DFU
    if product_id in IRECV_RECOVERY_PIDS:
        return DeviceMode.RECOVERY
    if product_id in NORMAL_MODE_PIDS:
        return DeviceMode.NORMAL
    # Unknown Apple PID: still treat as a connected device in normal-ish mode.
    return DeviceMode.NORMAL


@dataclass(frozen=True)
class DeviceSnapshot:
    mode: DeviceMode
    vendor_id: int
    product_id: int
    product: str
    manufacturer: str
    serial: str
    sysfs_path: str
    identifier: str | None = None

    @property
    def display_name(self) -> str:
        if self.identifier:
            return self.identifier
        if self.product:
            return self.product
        return f"Apple device ({self.product_id:#06x})"


def pick_primary_device(devices: list[DeviceSnapshot]) -> DeviceSnapshot | None:
    if not devices:
        return None
    return min(devices, key=lambda d: _MODE_PRIORITY[d.mode])
