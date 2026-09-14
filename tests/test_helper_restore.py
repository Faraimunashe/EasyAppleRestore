from pathlib import Path

from easyrestore.backend.diagnostics import build_diagnostic_report
from easyrestore.backend.helper_client import LocalHelperClient
from easyrestore.helper.daemon import HelperService
from easyrestore.session import RestoreAction, RestoreSession


def test_helper_preflight_and_status_idle(monkeypatch) -> None:
    monkeypatch.setattr(
        "easyrestore.helper.daemon.check_usbmuxd",
        lambda: type("R", (), {"ok": True, "key": "usbmuxd", "message": "ok", "detail": "", "pids": ()})(),
    )
    monkeypatch.setattr(
        "easyrestore.helper.daemon.ensure_usbmuxd",
        lambda: type("R", (), {"ok": True, "key": "usbmuxd", "message": "ok", "detail": "", "pids": ()})(),
    )
    monkeypatch.setattr(
        "easyrestore.helper.daemon.check_conflicts",
        lambda: type("R", (), {"ok": True, "key": "conflicts", "message": "ok", "detail": "", "pids": ()})(),
    )
    monkeypatch.setattr(
        "easyrestore.helper.daemon.check_disk_space",
        lambda needed: type("R", (), {"ok": True, "key": "disk", "message": "ok", "detail": "", "pids": ()})(),
    )
    service = HelperService()
    a, b, c = service.RunPreflight(1000, False)
    assert a.startswith("usbmuxd|1|")
    assert b.startswith("conflicts|1|")
    assert c.startswith("disk|1|")
    job_id, state, *_rest = service.GetRestoreStatus()
    assert job_id == ""
    assert state == "idle"


def test_local_helper_stub_restore(tmp_path: Path, monkeypatch) -> None:
    import time

    from easyrestore.backend.restore_job import MANAGER, RestoreState

    monkeypatch.setenv("EASYRESTORE_RESTORE_STUB", "1")
    MANAGER.reset_for_tests()
    client = LocalHelperClient()
    ipsw = tmp_path / "phone.ipsw"
    ipsw.write_bytes(b"ipsw-bytes")
    job_id = client.start_restore(ipsw, erase=True)
    assert job_id
    deadline = time.time() + 5
    while client.get_restore_status().state is RestoreState.RUNNING and time.time() < deadline:
        time.sleep(0.05)
    status = client.get_restore_status()
    assert status.state is RestoreState.SUCCEEDED
    _, log_text = client.get_restore_log(0)
    assert "Restore Successful" in log_text


def test_diagnostic_report_includes_failure_hint() -> None:
    session = RestoreSession(
        action=RestoreAction.ERASE,
        device_identifier="iPhone13,4",
        last_log_lines=["ERROR: Unable to send data to ASR"],
        restore_succeeded=False,
    )
    report = build_diagnostic_report(session)
    assert "Unable to send data to ASR" in report
    assert "USB cable" in report or "cable" in report.lower()
