import os
from pathlib import Path

import pytest

from easyrestore.constants import POLKIT_ACTION_START_RESTORE
from easyrestore.helper.daemon import HelperService
from easyrestore.helper.polkit import (
    NotAuthorizedError,
    check_authorization,
    polkit_enabled,
)


def test_polkit_disabled_on_session_bus(monkeypatch) -> None:
    monkeypatch.delenv("EASYRESTORE_FORCE_POLKIT", raising=False)
    monkeypatch.delenv("EASYRESTORE_SKIP_POLKIT", raising=False)
    monkeypatch.delenv("EASYRESTORE_RESTORE_STUB", raising=False)
    assert polkit_enabled(session_bus=True) is False
    assert polkit_enabled(session_bus=False) is True


def test_polkit_skip_env(monkeypatch) -> None:
    monkeypatch.setenv("EASYRESTORE_SKIP_POLKIT", "1")
    assert polkit_enabled(session_bus=False) is False


def test_check_authorization_allows_missing_sender() -> None:
    check_authorization(POLKIT_ACTION_START_RESTORE, sender=None)


def test_check_authorization_denied(monkeypatch) -> None:
    monkeypatch.setattr(
        "easyrestore.helper.polkit.shutil.which",
        lambda name: "/usr/bin/pkcheck" if name == "pkcheck" else None,
    )

    class Result:
        returncode = 1
        stdout = ""
        stderr = "not authorized"

    monkeypatch.setattr(
        "easyrestore.helper.polkit.subprocess.run",
        lambda *args, **kwargs: Result(),
    )
    with pytest.raises(NotAuthorizedError, match="not authorized"):
        check_authorization(POLKIT_ACTION_START_RESTORE, sender=":1.23")


def test_helper_enforces_polkit_on_start_restore(monkeypatch, tmp_path: Path) -> None:
    service = HelperService(enforce_polkit=True)
    service.last_sender = ":1.99"
    calls: list[str | None] = []

    def fake_require(*, sender=None):
        calls.append(sender)
        raise NotAuthorizedError("nope")

    monkeypatch.setattr("easyrestore.helper.daemon.require_restore", fake_require)
    ipsw = tmp_path / "x.ipsw"
    ipsw.write_bytes(b"data")
    with pytest.raises(NotAuthorizedError):
        service.StartRestore(str(ipsw), True)
    assert calls == [":1.99"]


def test_desktop_and_metainfo_exist() -> None:
    root = Path(__file__).resolve().parents[1]
    desktop = root / "data/desktop/io.easyrestore.EasyRestore.desktop"
    meta = root / "data/metainfo/io.easyrestore.EasyRestore.metainfo.xml"
    assert desktop.is_file()
    assert "Name=EasyRestore" in desktop.read_text(encoding="utf-8")
    assert meta.is_file()
    assert "<id>io.easyrestore.EasyRestore</id>" in meta.read_text(encoding="utf-8")
