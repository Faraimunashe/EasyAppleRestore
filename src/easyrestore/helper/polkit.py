"""Authorize privileged helper methods with PolicyKit.

Uses ``pkcheck`` so the native OS authentication dialog appears without a
terminal prompt. Session-bus / local-helper development skips polkit unless
``EASYRESTORE_FORCE_POLKIT=1``.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess

from easyrestore.constants import (
    POLKIT_ACTION_RUN_PREFLIGHT,
    POLKIT_ACTION_START_RESTORE,
)

log = logging.getLogger("easyrestore.helper.polkit")


class NotAuthorizedError(PermissionError):
    """Caller was not authorized by PolicyKit."""


def polkit_enabled(*, session_bus: bool) -> bool:
    if os.environ.get("EASYRESTORE_SKIP_POLKIT") == "1":
        return False
    if os.environ.get("EASYRESTORE_FORCE_POLKIT") == "1":
        return True
    if session_bus:
        return False
    if os.environ.get("EASYRESTORE_RESTORE_STUB") == "1":
        return False
    return True


def check_authorization(action_id: str, *, sender: str | None) -> None:
    """Raise NotAuthorizedError if the caller may not perform ``action_id``."""
    if not sender:
        # No D-Bus caller identity (unit tests / in-process LocalHelperClient).
        log.debug("polkit skipped: no sender for %s", action_id)
        return

    pkcheck = shutil.which("pkcheck")
    if pkcheck is None:
        raise NotAuthorizedError(
            "PolicyKit (pkcheck) is not available. Install polkit to authorize restores."
        )

    cmd = [
        pkcheck,
        "--action-id",
        action_id,
        "--system-bus-name",
        sender,
        "--allow-user-interaction",
    ]
    log.info("polkit check: %s for %s", action_id, sender)
    completed = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if completed.returncode == 0:
        return

    detail = (completed.stderr or completed.stdout or "").strip()
    message = detail or f"Not authorized for {action_id}"
    log.warning("polkit denied %s for %s: %s", action_id, sender, message)
    raise NotAuthorizedError(message)


def require_preflight(*, sender: str | None) -> None:
    check_authorization(POLKIT_ACTION_RUN_PREFLIGHT, sender=sender)


def require_restore(*, sender: str | None) -> None:
    check_authorization(POLKIT_ACTION_START_RESTORE, sender=sender)
