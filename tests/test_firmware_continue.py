from pathlib import Path

from easyrestore.backend.ipsw_api import Firmware
from easyrestore.session import FirmwareSource, RestoreSession
from easyrestore.wizard.pages.firmware import FirmwarePage


def test_verify_success_keeps_continue_enabled(qtbot, tmp_path: Path) -> None:
    session = RestoreSession(firmware_source=FirmwareSource.LOCAL_FILE)
    page = FirmwarePage(session)
    qtbot.addWidget(page)

    path = tmp_path / "local.ipsw"
    path.write_bytes(b"not-needed-for-this-unit")
    session.ipsw_path = path
    session.ipsw_verified = True
    page._local.setChecked(True)

    # Regression: finishing busy work used to call _sync_source and clear verified.
    page._set_busy(True)
    page._set_busy(False)

    assert session.ipsw_verified is True
    assert page.can_continue() is True


def test_switching_to_local_clears_catalog_sha1(qtbot) -> None:
    session = RestoreSession(
        firmware_source=FirmwareSource.LATEST_SIGNED,
        expected_sha1="abc",
        selected_firmware=Firmware(
            identifier="iPhone13,4",
            version="18.0",
            buildid="22A",
            url="https://example.test/a.ipsw",
            filesize=1,
            sha1sum="abc",
            sha256sum="",
            md5sum="",
            signed=True,
            releasedate="",
            uploaddate="",
        ),
    )
    page = FirmwarePage(session)
    qtbot.addWidget(page)
    page._local.setChecked(True)
    assert session.firmware_source is FirmwareSource.LOCAL_FILE
    assert session.expected_sha1 is None
