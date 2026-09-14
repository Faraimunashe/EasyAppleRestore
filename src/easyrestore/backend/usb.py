from __future__ import annotations

from pathlib import Path

from easyrestore.backend.device import DeviceSnapshot, mode_from_product_id
from easyrestore.constants import APPLE_VENDOR_ID

DEFAULT_SYSFS_USB = Path("/sys/bus/usb/devices")


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return ""


def _read_hex(path: Path) -> int | None:
    raw = _read_text(path)
    if not raw:
        return None
    try:
        return int(raw, 16)
    except ValueError:
        return None


def scan_apple_devices(sysfs_root: Path | None = None) -> list[DeviceSnapshot]:
    """List Apple USB devices by reading sysfs. No privileges required."""
    root = sysfs_root or DEFAULT_SYSFS_USB
    if not root.is_dir():
        return []

    found: list[DeviceSnapshot] = []
    for entry in sorted(root.iterdir()):
        vendor = _read_hex(entry / "idVendor")
        if vendor != APPLE_VENDOR_ID:
            continue
        product_id = _read_hex(entry / "idProduct")
        if product_id is None:
            continue
        found.append(
            DeviceSnapshot(
                mode=mode_from_product_id(product_id),
                vendor_id=vendor,
                product_id=product_id,
                product=_read_text(entry / "product"),
                manufacturer=_read_text(entry / "manufacturer"),
                serial=_read_text(entry / "serial"),
                sysfs_path=str(entry),
            )
        )
    return found
