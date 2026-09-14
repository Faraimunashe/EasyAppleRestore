from pathlib import Path

from easyrestore.backend.device import DeviceMode
from easyrestore.backend.usb import scan_apple_devices


def _usb_node(root: Path, name: str, vendor: str, product: str, title: str = "iPhone") -> None:
    node = root / name
    node.mkdir()
    (node / "idVendor").write_text(vendor)
    (node / "idProduct").write_text(product)
    (node / "product").write_text(title)
    (node / "manufacturer").write_text("Apple Inc.")
    (node / "serial").write_text("ABC123")


def test_scan_ignores_non_apple(tmp_path: Path) -> None:
    _usb_node(tmp_path, "1-1", "1d6b", "0002", "Hub")
    assert scan_apple_devices(tmp_path) == []


def test_scan_finds_recovery_device(tmp_path: Path) -> None:
    _usb_node(tmp_path, "1-2", "05ac", "1281", "Apple Mobile Device (Recovery Mode)")
    devices = scan_apple_devices(tmp_path)
    assert len(devices) == 1
    assert devices[0].mode is DeviceMode.RECOVERY
    assert devices[0].serial == "ABC123"
