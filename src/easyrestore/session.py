from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from easyrestore.backend.device import DeviceSnapshot
from easyrestore.backend.ipsw_api import Firmware


class RestoreAction(Enum):
    UPDATE = "update"
    DOWNGRADE = "downgrade"
    ERASE = "erase"
    HELP_ME = "help_me"


class FirmwareSource(Enum):
    LATEST_SIGNED = "latest_signed"
    CHOOSE_VERSION = "choose_version"
    LOCAL_FILE = "local_file"


@dataclass
class RestoreSession:
    """In-memory wizard state. Nothing here is persisted yet."""

    device: DeviceSnapshot | None = None
    device_identifier: str | None = None
    action: RestoreAction | None = None
    firmware_source: FirmwareSource = FirmwareSource.LATEST_SIGNED
    selected_firmware: Firmware | None = None
    selected_version: str | None = None
    selected_build: str | None = None
    expected_sha1: str | None = None
    ipsw_path: Path | None = None
    ipsw_verified: bool = False
    last_log_lines: list[str] = field(default_factory=list)
    restore_succeeded: bool | None = None
