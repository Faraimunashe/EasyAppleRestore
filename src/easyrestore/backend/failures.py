from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FailureExplanation:
    key: str
    headline: str
    detail: str


_SIGNATURES: tuple[tuple[str, FailureExplanation], ...] = (
    (
        "Unable to discover device type",
        FailureExplanation(
            "unknown_device",
            "We can't identify your device over USB.",
            "Try a different cable or port, ideally a USB-A port with no hub.",
        ),
    ),
    (
        "Unable to send data to ASR",
        FailureExplanation(
            "asr_transfer",
            "The connection to your device was interrupted during the file transfer.",
            "This is often a USB cable or port issue — try a different port, ideally USB-A, with no hub.",
        ),
    ),
    (
        "Could not read data (-256)",
        FailureExplanation(
            "device_restarting",
            "Your device is restarting to finish the restore.",
            "If the battery is very low, plug into a wall charger and wait a few minutes.",
        ),
    ),
    (
        "CRC",
        FailureExplanation(
            "ipsw_corrupt",
            "The firmware file appears corrupted.",
            "Please re-download it and run the integrity check again.",
        ),
    ),
)


def explain_failure(log_text: str) -> FailureExplanation | None:
    for needle, explanation in _SIGNATURES:
        if needle.lower() in log_text.lower():
            return explanation
    return None
