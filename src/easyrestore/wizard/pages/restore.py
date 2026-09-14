from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QCheckBox, QLabel, QPlainTextEdit, QProgressBar, QVBoxLayout

from easyrestore.backend.helper_client import HelperClient
from easyrestore.backend.log_translate import RestorePhase
from easyrestore.backend.restore_job import RestoreState
from easyrestore.session import RestoreAction
from easyrestore.wizard.page import WizardPage


class RestorePage(WizardPage):
    title = "Restore"
    subtitle = "Keep this computer awake. The helper keeps working if this window closes."
    continue_label = "Continue"

    def __init__(self, session, helper: HelperClient, parent=None) -> None:
        super().__init__(session, parent)
        self._helper = helper
        self._started = False
        self._finished = False
        self._log_index = 0
        self._job_id = ""

        layout = QVBoxLayout(self)

        self._phase = QLabel(RestorePhase.PREPARING.value)
        phase_font = self._phase.font()
        phase_font.setWeight(phase_font.Weight.DemiBold)
        phase_font.setPointSize(max(phase_font.pointSize(), 12) + 2)
        self._phase.setFont(phase_font)
        self._phase.setAccessibleName(self.tr("Current restore phase"))
        layout.addWidget(self._phase)

        self._bar = QProgressBar()
        self._bar.setRange(0, 100)
        self._bar.setValue(0)
        self._bar.setAccessibleName(self.tr("Restore progress"))
        layout.addWidget(self._bar)

        self._message = QLabel(self.tr("Waiting to start…"))
        self._message.setObjectName("Muted")
        self._message.setWordWrap(True)
        layout.addWidget(self._message)

        self._toggle = QCheckBox(self.tr("Advanced — view technical log"))
        self._toggle.setChecked(False)
        self._toggle.toggled.connect(self._show_log)
        layout.addWidget(self._toggle)

        self._log = QPlainTextEdit()
        self._log.setObjectName("TechLog")
        self._log.setReadOnly(True)
        self._log.setVisible(False)
        self._log.setAccessibleName(self.tr("Technical restore log"))
        layout.addWidget(self._log, 1)

        self._timer = QTimer(self)
        self._timer.setInterval(500)
        self._timer.timeout.connect(self._poll)

    def on_enter(self) -> None:
        if self._finished:
            self.can_continue_changed.emit(True)
            return
        if not self._started:
            QTimer.singleShot(100, self._begin)
        else:
            self._timer.start()
        self.can_continue_changed.emit(False)

    def on_leave(self) -> bool:
        # Leave the timer running only while on this page; helper keeps the job.
        self._timer.stop()
        return self._finished

    def can_continue(self) -> bool:
        return self._finished

    def _erase(self) -> bool:
        return self.session.action is RestoreAction.ERASE

    def _begin(self) -> None:
        if self._started:
            return
        path = self.session.ipsw_path
        if path is None or not self.session.ipsw_verified:
            self._message.setText(self.tr("No verified IPSW is ready. Go back to Choose firmware."))
            self._message.setObjectName("StatusWait")
            self._message.style().unpolish(self._message)
            self._message.style().polish(self._message)
            self._finished = True
            self.session.restore_succeeded = False
            self.can_continue_changed.emit(True)
            return

        # Reattach if a job is already running (GUI relaunch / revisiting page).
        try:
            status = self._helper.get_restore_status()
        except Exception as exc:  # noqa: BLE001
            self._fail(str(exc))
            return

        if status.state is RestoreState.RUNNING and status.job_id:
            self._started = True
            self._job_id = status.job_id
            self._message.setText(self.tr("Reattached to a restore already in progress."))
            self._timer.start()
            return

        if status.state is RestoreState.SUCCEEDED and status.job_id:
            self._apply_status(status)
            self._drain_log()
            self._complete(True, status.message)
            return

        try:
            self._job_id = self._helper.start_restore(path, erase=self._erase())
        except Exception as exc:  # noqa: BLE001
            self._fail(str(exc))
            return

        self._started = True
        self._message.setText(self.tr("Restore started…"))
        self._timer.start()

    def _poll(self) -> None:
        try:
            status = self._helper.get_restore_status()
            self._drain_log()
        except Exception as exc:  # noqa: BLE001
            self._timer.stop()
            self._fail(str(exc))
            return
        self._apply_status(status)
        if status.state is RestoreState.SUCCEEDED:
            self._timer.stop()
            self._complete(True, status.message)
        elif status.state is RestoreState.FAILED:
            self._timer.stop()
            self._complete(False, status.message)

    def _drain_log(self) -> None:
        next_index, text = self._helper.get_restore_log(self._log_index)
        self._log_index = next_index
        if not text:
            return
        self._log.appendPlainText(text)
        for line in text.splitlines():
            self.session.last_log_lines.append(line)
            if len(self.session.last_log_lines) > 500:
                self.session.last_log_lines = self.session.last_log_lines[-500:]

    def _apply_status(self, status) -> None:
        if status.phase:
            self._phase.setText(status.phase)
        self._bar.setValue(max(0, min(100, int(status.percent))))
        if status.message:
            self._message.setText(status.message)

    def _complete(self, ok: bool, message: str) -> None:
        self._finished = True
        self.session.restore_succeeded = ok
        self._message.setText(message)
        self._message.setObjectName("StatusOk" if ok else "StatusWait")
        self._message.style().unpolish(self._message)
        self._message.style().polish(self._message)
        if ok:
            self._phase.setText(RestorePhase.DONE.value)
            self._bar.setValue(100)
        self.can_continue_changed.emit(True)

    def _fail(self, message: str) -> None:
        self._finished = True
        self.session.restore_succeeded = False
        self._message.setText(message)
        self._message.setObjectName("StatusWait")
        self._message.style().unpolish(self._message)
        self._message.style().polish(self._message)
        self.can_continue_changed.emit(True)

    def _show_log(self, visible: bool) -> None:
        self._log.setVisible(visible)
