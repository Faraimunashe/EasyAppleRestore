from pathlib import Path

from easyrestore.backend.preflight import check_conflicts, check_disk_space, check_usbmuxd


def test_disk_space_ok(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("easyrestore.backend.preflight.free_bytes", lambda path=None: 50 * 1024**3)
    result = check_disk_space(4 * 1024**3, path=tmp_path)
    assert result.ok
    assert result.key == "disk"


def test_disk_space_fail(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("easyrestore.backend.preflight.free_bytes", lambda path=None: 100)
    result = check_disk_space(4 * 1024**3, path=tmp_path)
    assert not result.ok


def test_conflicts_when_none(monkeypatch) -> None:
    monkeypatch.setattr("easyrestore.backend.preflight._pgrep_names", lambda names: [])
    assert check_conflicts().ok


def test_conflicts_when_present(monkeypatch) -> None:
    monkeypatch.setattr(
        "easyrestore.backend.preflight._pgrep_names",
        lambda names: [(123, "gvfs-afc-volume-monitor")],
    )
    result = check_conflicts()
    assert not result.ok
    assert result.pids == (123,)


def test_usbmuxd_running(monkeypatch) -> None:
    monkeypatch.setattr("easyrestore.backend.preflight._pgrep_names", lambda names: [(1, "usbmuxd")])
    assert check_usbmuxd().ok
