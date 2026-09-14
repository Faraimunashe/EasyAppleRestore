from __future__ import annotations

import platform
from pathlib import Path

from easyrestore import __version__
from easyrestore.backend.failures import explain_failure
from easyrestore.backend.identifier import vendor_tool_report
from easyrestore.session import RestoreSession


def build_diagnostic_report(session: RestoreSession, log_lines: list[str] | None = None) -> str:
    lines = log_lines if log_lines is not None else session.last_log_lines
    device = session.device
    tools = vendor_tool_report()
    parts = [
        f"EasyRestore {__version__}",
        f"OS: {platform.platform()}",
        f"Python: {platform.python_version()}",
        f"Action: {session.action.value if session.action else 'none'}",
        f"Device identifier: {session.device_identifier or 'unknown'}",
        f"Device mode: {device.mode.value if device else 'none'}",
        f"Device product: {device.product if device else ''}",
        f"Device serial: {device.serial if device else ''}",
        f"Firmware: {session.selected_version or ''} ({session.selected_build or ''})",
        f"IPSW: {session.ipsw_path or ''}",
        f"IPSW verified: {session.ipsw_verified}",
        f"Restore succeeded: {session.restore_succeeded}",
        "",
        "--- vendor tools ---",
    ]
    for name, path in tools.items():
        parts.append(f"{name}: {path or 'missing'}")
    parts.extend(["", "--- restore log (tail) ---"])
    tail = lines[-200:]
    parts.extend(tail)
    explanation = explain_failure("\n".join(tail))
    if explanation:
        parts.extend(
            [
                "",
                "--- known failure match ---",
                explanation.headline,
                explanation.detail,
            ]
        )
    return "\n".join(parts) + "\n"


def write_diagnostic_report(session: RestoreSession, path: Path) -> Path:
    path.write_text(build_diagnostic_report(session), encoding="utf-8")
    return path
