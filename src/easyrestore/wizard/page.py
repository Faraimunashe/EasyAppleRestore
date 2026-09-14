from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget

from easyrestore.session import RestoreSession


class WizardPage(QWidget):
    can_continue_changed = Signal(bool)

    title = ""
    subtitle = ""
    continue_label = "Continue"

    def __init__(self, session: RestoreSession, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.session = session

    def on_enter(self) -> None:
        return None

    def on_leave(self) -> bool:
        return True

    def can_continue(self) -> bool:
        return True
