from __future__ import annotations

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices, QGuiApplication
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QTextEdit, QVBoxLayout

from easyrestore.backend.diagnostics import build_diagnostic_report
from easyrestore.backend.failures import explain_failure
from easyrestore.constants import DEVELOPER_MAILTO
from easyrestore.wizard.page import WizardPage


class CompletePage(WizardPage):
    title = "Finished"
    subtitle = "Here’s what happened, plus a report you can copy for support."
    continue_label = "Close"

    def __init__(self, session, parent=None) -> None:
        super().__init__(session, parent)
        layout = QVBoxLayout(self)

        self._result = QLabel(self.tr("No restore has run yet."))
        self._result.setObjectName("StatusIdle")
        result_font = self._result.font()
        result_font.setWeight(result_font.Weight.DemiBold)
        result_font.setPointSize(max(result_font.pointSize(), 12) + 3)
        self._result.setFont(result_font)
        self._result.setWordWrap(True)
        layout.addWidget(self._result)

        self._detail = QLabel("")
        self._detail.setObjectName("Muted")
        self._detail.setWordWrap(True)
        layout.addWidget(self._detail)

        buttons = QHBoxLayout()
        self._view_log = QPushButton(self.tr("View technical log"))
        self._view_log.setObjectName("Ghost")
        self._view_log.clicked.connect(self._toggle_log)
        self._copy = QPushButton(self.tr("Copy diagnostic report"))
        self._copy.setObjectName("Ghost")
        self._copy.clicked.connect(self._copy_report)
        self._contact = QPushButton(self.tr("Contact developer"))
        self._contact.setObjectName("Ghost")
        self._contact.setAccessibleName(self.tr("Contact developer by email"))
        self._contact.clicked.connect(self._contact_developer)
        buttons.addWidget(self._view_log)
        buttons.addWidget(self._copy)
        buttons.addWidget(self._contact)
        buttons.addStretch(1)
        layout.addLayout(buttons)

        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setVisible(False)
        self._log.setObjectName("TechLog")
        self._log.setAccessibleName(self.tr("Technical restore log"))
        layout.addWidget(self._log, 1)

    def on_enter(self) -> None:
        report = build_diagnostic_report(self.session)
        self._log.setPlainText(report)
        has_log = bool(self.session.last_log_lines)
        self._view_log.setEnabled(has_log or True)
        self._copy.setEnabled(True)

        if self.session.restore_succeeded is True:
            self._result.setText(self.tr("Restore finished successfully."))
            self._result.setObjectName("StatusOk")
            self._detail.setText(
                self.tr("You can unplug the device when it finishes booting.")
            )
        elif self.session.restore_succeeded is False:
            self._result.setText(self.tr("The restore did not finish."))
            self._result.setObjectName("StatusWait")
            explanation = explain_failure("\n".join(self.session.last_log_lines))
            if explanation:
                self._detail.setText(f"{explanation.headline} {explanation.detail}")
            else:
                self._detail.setText(
                    self.tr("Copy the diagnostic report and share it if you need help.")
                )
        else:
            self._result.setText(self.tr("No restore has run yet."))
            self._result.setObjectName("StatusIdle")
            self._detail.setText("")
        self._result.style().unpolish(self._result)
        self._result.style().polish(self._result)

    def _toggle_log(self) -> None:
        self._log.setVisible(not self._log.isVisible())

    def _copy_report(self) -> None:
        text = build_diagnostic_report(self.session)
        QGuiApplication.clipboard().setText(text)
        self._detail.setText(self.tr("Diagnostic report copied to the clipboard."))

    def _contact_developer(self) -> None:
        QDesktopServices.openUrl(QUrl(DEVELOPER_MAILTO))
