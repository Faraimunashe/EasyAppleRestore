from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QCheckBox, QLabel, QVBoxLayout

from easyrestore.backend.helper_client import HelperClient
from easyrestore.wizard.page import WizardPage
from easyrestore.wizard.widgets import ChecklistRow


class PreflightPage(WizardPage):
    title = "A few checks first"
    subtitle = "These run automatically. Nothing is changed without your OK."

    def __init__(self, session, helper: HelperClient, parent=None) -> None:
        super().__init__(session, parent)
        self._helper = helper
        self._ready = False
        self._rows = {
            "usbmuxd": ChecklistRow(self.tr("Bundled usbmuxd is running")),
            "conflicts": ChecklistRow(
                self.tr("No other program is holding the device (for example gvfs-afc)")
            ),
            "disk": ChecklistRow(self.tr("Enough free disk space for extraction")),
        }

        layout = QVBoxLayout(self)
        for row in self._rows.values():
            layout.addWidget(row)

        self._pause = QCheckBox(
            self.tr("If needed, temporarily pause programs that are holding the device")
        )
        self._pause.setChecked(True)
        self._pause.setAccessibleName(self.tr("Allow pausing conflicting programs"))
        layout.addWidget(self._pause)

        self._note = QLabel("")
        self._note.setObjectName("Muted")
        self._note.setWordWrap(True)
        layout.addWidget(self._note)
        layout.addStretch(1)

        self._started = False

    def on_enter(self) -> None:
        self._ready = False
        self._started = False
        for row in self._rows.values():
            row.set_state("pending", self.tr("Checking…"))
        self._note.setText(self.tr("Running checks…"))
        self.can_continue_changed.emit(False)
        QTimer.singleShot(50, self._run_checks)

    def can_continue(self) -> bool:
        return self._ready

    def _needed_bytes(self) -> int:
        firmware = self.session.selected_firmware
        if firmware and firmware.filesize:
            return int(firmware.filesize)
        if self.session.ipsw_path and self.session.ipsw_path.is_file():
            return int(self.session.ipsw_path.stat().st_size)
        return 8 * 1024 * 1024 * 1024

    def _run_checks(self) -> None:
        if self._started:
            return
        self._started = True
        try:
            results = self._helper.run_preflight(
                self._needed_bytes(),
                pause_conflicts=self._pause.isChecked(),
            )
        except Exception as exc:  # noqa: BLE001
            self._note.setText(self.tr("Pre-flight failed: {error}").format(error=exc))
            self._note.setObjectName("StatusWait")
            self._note.style().unpolish(self._note)
            self._note.style().polish(self._note)
            self._ready = False
            self.can_continue_changed.emit(False)
            return

        all_ok = True
        for result in results:
            row = self._rows.get(result.key)
            if row is None:
                continue
            if result.ok:
                row.set_state("ok", result.message)
            else:
                all_ok = False
                row.set_state("fail", result.message)

        # Conflicts can be a soft warning if user declined pausing.
        conflict = next((item for item in results if item.key == "conflicts"), None)
        disk = next((item for item in results if item.key == "disk"), None)
        usbmuxd = next((item for item in results if item.key == "usbmuxd"), None)

        hard_fail = False
        if disk and not disk.ok:
            hard_fail = True
        if usbmuxd and not usbmuxd.ok:
            # Still allow continue — restore may work with recovery/DFU only tools,
            # but warn clearly.
            self._note.setText(usbmuxd.message)
        if conflict and not conflict.ok:
            self._note.setText(
                self.tr(
                    "{msg}. You can go back, enable pausing, and run the checks again."
                ).format(msg=conflict.message)
            )

        if hard_fail:
            self._ready = False
            self._note.setText(
                self.tr("Fix the failed checks before continuing. {detail}").format(
                    detail=disk.message if disk else ""
                )
            )
            self._note.setObjectName("StatusWait")
        else:
            self._ready = True
            if all_ok:
                self._note.setText(self.tr("All checks passed. You can continue to restore."))
                self._note.setObjectName("StatusOk")
            else:
                self._note.setObjectName("StatusWait")
        self._note.style().unpolish(self._note)
        self._note.style().polish(self._note)
        self.can_continue_changed.emit(self.can_continue())
