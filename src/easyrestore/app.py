from __future__ import annotations

import argparse
import os
import sys

from easyrestore.backend.helper_client import LocalHelperClient, connect_helper
from easyrestore.backend.identifier import ensure_vendor_env
from easyrestore.constants import APP_ID, APP_NAME
from easyrestore.resources.icons import app_icon
from easyrestore.wizard.style import stylesheet_for_system
from easyrestore.wizard.window import WizardWindow


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=APP_NAME)
    parser.add_argument(
        "--session-helper",
        action="store_true",
        help="Talk to a helper on the session bus instead of the system bus.",
    )
    parser.add_argument(
        "--local-helper",
        action="store_true",
        help="Skip D-Bus and use in-process USB detection only.",
    )
    args = parser.parse_args(argv)

    ensure_vendor_env()

    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv if argv is None else [APP_NAME, *argv])
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("EasyRestore")
    app.setDesktopFileName(APP_ID)
    app.setWindowIcon(app_icon())
    app.setStyleSheet(stylesheet_for_system())

    prefer_session = args.session_helper or os.environ.get("EASYRESTORE_HELPER_BUS") == "session"
    if args.local_helper:
        helper = LocalHelperClient()
    else:
        helper = connect_helper(prefer_session=prefer_session)

    window = WizardWindow(helper)
    window.show()
    return app.exec()
