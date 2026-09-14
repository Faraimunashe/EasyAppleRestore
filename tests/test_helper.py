from easyrestore.backend.device import DeviceMode, DeviceSnapshot
from easyrestore.backend.helper_client import LocalHelperClient
from easyrestore.helper.daemon import HelperService, snapshot_device_mode


def test_local_helper_reads_sysfs(tmp_path, monkeypatch) -> None:
    node = tmp_path / "2-1"
    node.mkdir()
    (node / "idVendor").write_text("05ac")
    (node / "idProduct").write_text("1227")
    (node / "product").write_text("DFU")
    (node / "manufacturer").write_text("Apple Inc.")
    (node / "serial").write_text("DFU1")
    client = LocalHelperClient(tmp_path)
    device = client.get_device_mode()
    assert device is not None
    assert device.mode is DeviceMode.DFU


def test_helper_service_disconnected(monkeypatch) -> None:
    monkeypatch.setattr("easyrestore.helper.daemon.scan_apple_devices", lambda: [])
    assert snapshot_device_mode() == ("Disconnected", "", "")
    mode, product, serial = HelperService().GetDeviceMode()
    assert mode == "Disconnected"
    assert product == ""
    assert serial == ""


def test_helper_service_reports_device(monkeypatch) -> None:
    device = DeviceSnapshot(DeviceMode.RECOVERY, 0x05AC, 0x1281, "iPhone", "Apple", "S1", "x")
    monkeypatch.setattr("easyrestore.helper.daemon.scan_apple_devices", lambda: [device])
    assert HelperService().GetDeviceMode() == ("Recovery", "iPhone", "S1")
