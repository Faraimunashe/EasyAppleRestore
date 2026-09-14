import time
from pathlib import Path

import pytest

from easyrestore.backend.restore_job import (
    MANAGER,
    RestoreState,
    build_idevicerestore_command,
)


def test_build_command_erase(tmp_path: Path, monkeypatch) -> None:
    binary = tmp_path / "idevicerestore"
    binary.write_text("#!/bin/sh\n")
    binary.chmod(0o755)
    monkeypatch.setattr(
        "easyrestore.backend.restore_job.vendor_bin",
        lambda name: binary if name == "idevicerestore" else None,
    )
    ipsw = tmp_path / "x.ipsw"
    ipsw.write_bytes(b"ipsw")
    cmd = build_idevicerestore_command(ipsw, erase=True)
    assert cmd == [str(binary), "-y", "-e", str(ipsw)]


def test_stub_restore_succeeds(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("EASYRESTORE_RESTORE_STUB", "1")
    MANAGER.reset_for_tests()
    ipsw = tmp_path / "demo.ipsw"
    ipsw.write_bytes(b"PK\x05\x06" + b"\x00" * 18)
    job = MANAGER.start(ipsw, erase=True)
    deadline = time.time() + 5
    while job.status().state is RestoreState.RUNNING and time.time() < deadline:
        time.sleep(0.05)
    status = job.status()
    assert status.state is RestoreState.SUCCEEDED
    assert status.percent == 100
    _, log_text = job.log_since(0)
    assert "Restore Successful" in log_text
    assert "Sending SystemVolume" in log_text


def test_rejects_second_running_job(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("EASYRESTORE_RESTORE_STUB", "1")
    MANAGER.reset_for_tests()

    def hang_script(ipsw_path, erase):
        return "#!/bin/sh\nsleep 30\n"

    monkeypatch.setattr("easyrestore.backend.restore_job._stub_script", hang_script)
    ipsw = tmp_path / "demo.ipsw"
    ipsw.write_bytes(b"data")
    first = MANAGER.start(ipsw, erase=False)
    try:
        with pytest.raises(RuntimeError, match="already running"):
            MANAGER.start(ipsw, erase=False)
    finally:
        MANAGER.reset_for_tests()
        _ = first
