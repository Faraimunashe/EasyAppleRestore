from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class RestorePhase(Enum):
    PREPARING = "Preparing firmware"
    COPYING = "Copying system files"
    VERIFYING = "Verifying"
    FINALIZING = "Finalizing"
    DONE = "Done"
    UNKNOWN = "Working"


@dataclass(frozen=True)
class TranslatedLine:
    phase: RestorePhase
    percent: int | None
    headline: str
    raw: str


_PHASE_RULES: tuple[tuple[re.Pattern[str], RestorePhase, str], ...] = (
    (re.compile(r"Extracting|Unzipping|Personaliz", re.I), RestorePhase.PREPARING, "Preparing firmware"),
    (re.compile(r"Sending (SystemVolume|RootFS|filesystem|AppleLogo|KernelCache|iBEC|iBSS|RestoreRamDisk)", re.I), RestorePhase.COPYING, "Copying system files"),
    (re.compile(r"Verifying restore", re.I), RestorePhase.VERIFYING, "Verifying the restore"),
    (re.compile(r"Creating system key bag", re.I), RestorePhase.FINALIZING, "Creating the system key bag"),
    (re.compile(r"Waiting for device to reconnect|Rebooting|Booting", re.I), RestorePhase.FINALIZING, "Finishing up"),
    (re.compile(r"Restore Successful|Succeeded", re.I), RestorePhase.DONE, "Restore finished"),
)

_PERCENT = re.compile(r"\((\d{1,3})\)")


def translate_log_line(line: str) -> TranslatedLine:
    stripped = line.strip()
    percent: int | None = None
    match = _PERCENT.search(stripped)
    if match:
        value = int(match.group(1))
        if 0 <= value <= 100:
            percent = value

    for pattern, phase, headline in _PHASE_RULES:
        if pattern.search(stripped):
            return TranslatedLine(phase, percent, headline, stripped)

    return TranslatedLine(RestorePhase.UNKNOWN, percent, stripped or "Working", stripped)
