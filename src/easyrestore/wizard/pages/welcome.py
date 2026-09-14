from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout

from easyrestore.backend.device import DeviceMode
from easyrestore.backend.helper_client import HelperClient
from easyrestore.backend.identifier import resolve_product_type
from easyrestore.wizard.page import WizardPage
from easyrestore.wizard.widgets import PhoneGlyph


class WelcomePage(WizardPage):
    title = "Connect your iPhone or iPad"
    subtitle = "Use a USB cable. This app will notice the device as soon as it appears."

    def __init__(self, session, helper: HelperClient, parent=None) -> None:
        super().__init__(session, parent)
        self._helper = helper
        self._found = False

        layout = QVBoxLayout(self)
        layout.setSpacing(18)
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(PhoneGlyph())
        row.addStretch(1)
        layout.addLayout(row)

        self._status = QLabel(self.tr("Waiting for a device…"))
        self._status.setObjectName("StatusWait")
        self._status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status.setAccessibleName(self.tr("Device connection status"))
        layout.addWidget(self._status)

        helper_note = QLabel(helper.status().detail)
        helper_note.setObjectName("Muted")
        helper_note.setWordWrap(True)
        helper_note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(helper_note)
        layout.addStretch(1)

        self._timer = QTimer(self)
        self._timer.setInterval(750)
        self._timer.timeout.connect(self._poll)

    def on_enter(self) -> None:
        self._poll()
        self._timer.start()

    def on_leave(self) -> bool:
        self._timer.stop()
        return True

    def can_continue(self) -> bool:
        # The shell is walkable without hardware so later placeholder pages
        # can be reviewed. Restore itself will still require a device.
        return True

    def _poll(self) -> None:
        device = self._helper.get_device_mode()
        self.session.device = device
        found = device is not None and device.mode is not DeviceMode.DISCONNECTED
        if found != self._found:
            self._found = found
            self.can_continue_changed.emit(self.can_continue())
        if device is None:
            self._status.setText(self.tr("Waiting for a device…"))
            self._status.setObjectName("StatusWait")
        else:
            if not self.session.device_identifier:
                product_type = resolve_product_type()
                if product_type:
                    self.session.device_identifier = product_type
            label = self.session.device_identifier or device.display_name
            self._status.setText(
                self.tr("We found {name} — {mode} mode").format(
                    name=label,
                    mode=device.mode.value,
                )
            )
            self._status.setObjectName("StatusOk")
        self._status.style().unpolish(self._status)
        self._status.style().polish(self._status)
