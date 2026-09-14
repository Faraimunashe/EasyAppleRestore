from pathlib import Path

from easyrestore.backend.identifier import (
    ensure_vendor_env,
    vendor_bin,
    vendor_prefix,
    vendor_tool_report,
)
from easyrestore.backend.restore_job import build_idevicerestore_command


def test_vendor_prefix_detects_built_stack() -> None:
    ensure_vendor_env.cache_clear() if hasattr(ensure_vendor_env, "cache_clear") else None
    vendor_prefix.cache_clear()
    prefix = vendor_prefix()
    assert prefix is not None
    assert (prefix / "bin" / "idevicerestore").is_file()
    assert (prefix / "sbin" / "usbmuxd").is_file()


def test_vendor_bin_prefers_prefix_sbin_and_bin() -> None:
    vendor_prefix.cache_clear()
    restore = vendor_bin("idevicerestore")
    mux = vendor_bin("usbmuxd")
    assert restore is not None and restore.name == "idevicerestore"
    assert mux is not None and mux.name == "usbmuxd"
    assert "vendor/prefix" in str(restore)
    assert "vendor/prefix" in str(mux)


def test_build_command_uses_vendored_idevicerestore(tmp_path: Path) -> None:
    vendor_prefix.cache_clear()
    ipsw = tmp_path / "x.ipsw"
    ipsw.write_bytes(b"pk")
    cmd = build_idevicerestore_command(ipsw, erase=True)
    assert cmd[0].endswith("idevicerestore")
    assert "vendor/prefix" in cmd[0]
    assert cmd[1:] == ["-y", "-e", str(ipsw)]


def test_vendor_tool_report_lists_critical_tools() -> None:
    vendor_prefix.cache_clear()
    report = vendor_tool_report()
    assert report["idevicerestore"]
    assert report["usbmuxd"]
    assert report["irecovery"]
    assert report["ideviceinfo"]
