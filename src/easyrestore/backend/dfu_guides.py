"""Recovery / DFU button sequences.

These follow Apple's publicly documented button combinations, grouped by
input family — not a per-model hardware-verified table. Sequences differ
across generations; treat this as a starting map that must be confirmed
on-device before we ship guided animations as authoritative.

Apple references (public support articles):
- Face ID iPhone: Volume Up, Volume Down, then Side
- Home-button iPhone with Side button: Side + Home
- Older devices with Top button: Top + Home
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class InputFamily(Enum):
    SIDE_VOLUME = "side_volume"
    HOME_SIDE = "home_side"
    HOME_TOP = "home_top"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class GuideStep:
    instruction: str
    hold_seconds: float | None = None


@dataclass(frozen=True)
class ModeGuide:
    family: InputFamily
    title: str
    recovery: tuple[GuideStep, ...]
    dfu: tuple[GuideStep, ...]
    verified: bool = False


_SIDE_VOLUME = ModeGuide(
    family=InputFamily.SIDE_VOLUME,
    title="Face ID iPhone or iPad (no Home button)",
    recovery=(
        GuideStep("Quickly press and release Volume Up."),
        GuideStep("Quickly press and release Volume Down."),
        GuideStep("Press and hold the Side button until you see the recovery screen.", 10),
    ),
    dfu=(
        GuideStep("Quickly press and release Volume Up."),
        GuideStep("Quickly press and release Volume Down."),
        GuideStep("Press and hold the Side button.", 10),
        GuideStep("Keep holding Side and also hold Volume Down.", 5),
        GuideStep("Release Side, keep holding Volume Down until this app shows DFU."),
    ),
)

_HOME_SIDE = ModeGuide(
    family=InputFamily.HOME_SIDE,
    title="Touch ID device with a Side button",
    recovery=(
        GuideStep("Press and hold the Side button and the Home button together.", 10),
        GuideStep("Keep holding until you see the recovery screen."),
    ),
    dfu=(
        GuideStep("Press and hold the Side button and the Home button together.", 8),
        GuideStep("Release the Side button, keep holding Home until this app shows DFU."),
    ),
)

_HOME_TOP = ModeGuide(
    family=InputFamily.HOME_TOP,
    title="Older device with a Top button",
    recovery=(
        GuideStep("Press and hold the Top button and the Home button together.", 10),
        GuideStep("Keep holding until you see the recovery screen."),
    ),
    dfu=(
        GuideStep("Press and hold the Top button and the Home button together.", 8),
        GuideStep("Release the Top button, keep holding Home until this app shows DFU."),
    ),
)

# Identifier prefixes only — not a complete or verified model matrix.
# More specific identifiers must come first.
_PREFIX_FAMILY: tuple[tuple[str, InputFamily], ...] = (
    ("iPhone14,6", InputFamily.HOME_SIDE),  # iPhone SE (3rd)
    ("iPhone12,8", InputFamily.HOME_SIDE),  # iPhone SE (2nd)
    ("iPhone10,3", InputFamily.SIDE_VOLUME),  # iPhone X
    ("iPhone10,6", InputFamily.SIDE_VOLUME),  # iPhone X
    ("iPhone17", InputFamily.SIDE_VOLUME),
    ("iPhone16", InputFamily.SIDE_VOLUME),
    ("iPhone15", InputFamily.SIDE_VOLUME),
    ("iPhone14", InputFamily.SIDE_VOLUME),
    ("iPhone13", InputFamily.SIDE_VOLUME),
    ("iPhone12", InputFamily.SIDE_VOLUME),
    ("iPhone11", InputFamily.SIDE_VOLUME),
    ("iPhone10,", InputFamily.HOME_SIDE),
    ("iPhone9,", InputFamily.HOME_SIDE),
    ("iPhone8,", InputFamily.HOME_SIDE),
    ("iPad16", InputFamily.SIDE_VOLUME),
    ("iPad15", InputFamily.SIDE_VOLUME),
    ("iPad14", InputFamily.SIDE_VOLUME),
    ("iPad13", InputFamily.SIDE_VOLUME),
)


def family_for_identifier(identifier: str | None) -> InputFamily:
    if not identifier:
        return InputFamily.UNKNOWN
    for prefix, family in _PREFIX_FAMILY:
        if identifier.startswith(prefix):
            return family
    if identifier.startswith("iPhone") or identifier.startswith("iPad"):
        return InputFamily.UNKNOWN
    return InputFamily.UNKNOWN


def guide_for_family(family: InputFamily) -> ModeGuide:
    if family is InputFamily.SIDE_VOLUME:
        return _SIDE_VOLUME
    if family is InputFamily.HOME_SIDE:
        return _HOME_SIDE
    if family is InputFamily.HOME_TOP:
        return _HOME_TOP
    return ModeGuide(
        family=InputFamily.UNKNOWN,
        title="We need your device model to show the right buttons",
        recovery=(GuideStep("Connect the device so we can identify it, or pick your model."),),
        dfu=(GuideStep("Connect the device so we can identify it, or pick your model."),),
    )


def guide_for_identifier(identifier: str | None) -> ModeGuide:
    return guide_for_family(family_for_identifier(identifier))
