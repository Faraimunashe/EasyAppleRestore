from easyrestore.backend.device import DeviceMode, DeviceSnapshot, mode_from_product_id, pick_primary_device


def test_known_irecovery_pids() -> None:
    assert mode_from_product_id(0x1227) is DeviceMode.DFU
    assert mode_from_product_id(0x1222) is DeviceMode.DFU
    assert mode_from_product_id(0xF014) is DeviceMode.DFU
    assert mode_from_product_id(0x1281) is DeviceMode.RECOVERY
    assert mode_from_product_id(0x12A8) is DeviceMode.NORMAL


def test_pick_primary_prefers_dfu() -> None:
    normal = DeviceSnapshot(DeviceMode.NORMAL, 0x05AC, 0x12A8, "iPhone", "Apple", "a", "n")
    dfu = DeviceSnapshot(DeviceMode.DFU, 0x05AC, 0x1227, "DFU", "Apple", "b", "d")
    assert pick_primary_device([]) is None
    assert pick_primary_device([normal, dfu]) is dfu
