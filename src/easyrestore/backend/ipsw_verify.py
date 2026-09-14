from __future__ import annotations

import hashlib
import zipfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class VerifyResult:
    ok: bool
    zip_ok: bool
    sha1_ok: bool | None
    sha1: str
    message: str


def sha1_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha1()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def verify_zip_integrity(path: Path) -> str | None:
    """Return the first bad member name, or None if the archive tests clean."""
    try:
        with zipfile.ZipFile(path) as archive:
            return archive.testzip()
    except zipfile.BadZipFile as exc:
        raise ValueError(f"not a valid zip/IPSW archive: {exc}") from exc


def verify_ipsw(path: Path, expected_sha1: str | None = None) -> VerifyResult:
    """Mandatory pre-restore check: zip CRC plus optional SHA-1 from ipsw.me."""
    if not path.is_file():
        return VerifyResult(False, False, None, "", "Firmware file not found.")

    try:
        bad_member = verify_zip_integrity(path)
    except ValueError as exc:
        return VerifyResult(False, False, None, "", str(exc))

    if bad_member is not None:
        return VerifyResult(
            False,
            False,
            None,
            "",
            f"The firmware file appears corrupted ({bad_member}). Please re-download it.",
        )

    digest = sha1_file(path)
    if expected_sha1:
        sha1_ok = digest.lower() == expected_sha1.lower()
        if not sha1_ok:
            return VerifyResult(
                False,
                True,
                False,
                digest,
                "The firmware file does not match the published SHA-1 checksum.",
            )
        return VerifyResult(True, True, True, digest, "Firmware file verified.")

    return VerifyResult(True, True, None, digest, "Firmware archive integrity looks good.")
