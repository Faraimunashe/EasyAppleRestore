import zipfile
from pathlib import Path

from easyrestore.backend.ipsw_verify import sha1_file, verify_ipsw


def test_verify_good_zip_without_sha(tmp_path: Path) -> None:
    path = tmp_path / "sample.ipsw"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("Restore.plist", "<plist></plist>")
    result = verify_ipsw(path)
    assert result.ok
    assert result.zip_ok
    assert result.sha1_ok is None
    assert result.sha1 == sha1_file(path)


def test_verify_rejects_sha_mismatch(tmp_path: Path) -> None:
    path = tmp_path / "sample.ipsw"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("Restore.plist", "<plist></plist>")
    result = verify_ipsw(path, expected_sha1="deadbeef")
    assert not result.ok
    assert result.zip_ok
    assert result.sha1_ok is False


def test_verify_rejects_missing_file(tmp_path: Path) -> None:
    result = verify_ipsw(tmp_path / "missing.ipsw")
    assert not result.ok
    assert "not found" in result.message.lower()
