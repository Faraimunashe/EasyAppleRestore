"""ipsw.me API v4 client.

Contract taken from the official swagger at https://api.ipsw.me/v4/docs/swagger.json
(fetched 2026-09-12). The docs ask for fair use and mention rate limiting, but
do not publish a numeric quota — keep request volume low and cache responses.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

from easyrestore.backend.http import get_json
from easyrestore.constants import IPSW_API_BASE


@dataclass(frozen=True)
class Firmware:
    identifier: str
    version: str
    buildid: str
    url: str
    filesize: int
    sha1sum: str
    sha256sum: str
    md5sum: str
    signed: bool
    releasedate: str
    uploaddate: str

    @classmethod
    def from_api(cls, payload: dict[str, Any]) -> Firmware:
        return cls(
            identifier=str(payload.get("identifier") or ""),
            version=str(payload.get("version") or ""),
            buildid=str(payload.get("buildid") or ""),
            url=str(payload.get("url") or ""),
            filesize=int(payload.get("filesize") or 0),
            sha1sum=str(payload.get("sha1sum") or ""),
            sha256sum=str(payload.get("sha256sum") or ""),
            md5sum=str(payload.get("md5sum") or ""),
            signed=bool(payload.get("signed")),
            releasedate=str(payload.get("releasedate") or ""),
            uploaddate=str(payload.get("uploaddate") or ""),
        )


@dataclass(frozen=True)
class DeviceBoard:
    bdid: int
    boardconfig: str
    cpid: int
    platform: str


@dataclass(frozen=True)
class DeviceFirmwares:
    identifier: str
    name: str
    boards: tuple[DeviceBoard, ...]
    firmwares: tuple[Firmware, ...]

    def signed_firmwares(self) -> list[Firmware]:
        return [fw for fw in self.firmwares if fw.signed]

    def latest_signed(self) -> Firmware | None:
        signed = self.signed_firmwares()
        return signed[0] if signed else None


def device_ipsws_url(identifier: str) -> str:
    """Official path: GET /v4/ipsw/device/{identifier}."""
    return f"{IPSW_API_BASE}/ipsw/device/{quote(identifier, safe='')}"


def firmware_url(identifier: str, buildid: str) -> str:
    """Official path: GET /v4/ipsw/{identifier}/{buildid}."""
    return (
        f"{IPSW_API_BASE}/ipsw/"
        f"{quote(identifier, safe='')}/{quote(buildid, safe='')}"
    )


def parse_device_firmwares(payload: dict[str, Any]) -> DeviceFirmwares:
    boards = tuple(
        DeviceBoard(
            bdid=int(board.get("bdid") or 0),
            boardconfig=str(board.get("boardconfig") or ""),
            cpid=int(board.get("cpid") or 0),
            platform=str(board.get("platform") or ""),
        )
        for board in payload.get("boards") or []
    )
    firmwares = tuple(Firmware.from_api(item) for item in payload.get("firmwares") or [])
    return DeviceFirmwares(
        identifier=str(payload.get("identifier") or ""),
        name=str(payload.get("name") or ""),
        boards=boards,
        firmwares=firmwares,
    )


class IpswClient:
    """Thin ipsw.me v4 client. Cache responses in the UI layer to stay polite."""

    def __init__(self, *, timeout: float = 30.0) -> None:
        self.timeout = timeout
        self._device_cache: dict[str, DeviceFirmwares] = {}

    def fetch_device_firmwares(self, identifier: str, *, use_cache: bool = True) -> DeviceFirmwares:
        key = identifier.strip()
        if not key:
            raise ValueError("Device identifier is required.")
        if use_cache and key in self._device_cache:
            return self._device_cache[key]
        payload = get_json(device_ipsws_url(key), timeout=self.timeout)
        if not isinstance(payload, dict):
            raise RuntimeError("Unexpected API response for device firmwares.")
        device = parse_device_firmwares(payload)
        self._device_cache[key] = device
        return device

    def clear_cache(self) -> None:
        self._device_cache.clear()
