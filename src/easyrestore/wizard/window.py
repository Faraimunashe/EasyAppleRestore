from __future__ import annotations

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from easyrestore.backend.helper_client import HelperClient
from easyrestore.constants import APP_NAME, DEVELOPER_MAILTO
from easyrestore.resources.icons import app_icon, logo_pixmap
from easyrestore.session import RestoreSession
from easyrestore.wizard.page import WizardPage
from easyrestore.wizard.pages import (
    ActionPage,
    CompletePage,
    DeviceModePage,
    FirmwarePage,
    PreflightPage,
    RestorePage,
    WelcomePage,
)
from easyrestore.wizard.widgets import StepDots


class WizardWindow(QMainWindow):
    def __init__(self, helper: HelperClient, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.session = RestoreSession()
        self._helper = helper
        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(app_icon())
        self.setMinimumSize(780, 620)
        self.resize(840, 660)

        root = QWidget()
        root.setObjectName("WizardRoot")
        root.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(32, 24, 32, 24)
        outer.setSpacing(18)

        header = QHBoxLayout()
        brand = QHBoxLayout()
        brand.setSpacing(10)
        logo = QLabel()
        logo.setPixmap(logo_pixmap(36))
        logo.setFixedSize(36, 36)
        logo.setScaledContents(True)
        logo.setAccessibleName(self.tr("EasyRestore logo"))
        title = QLabel(APP_NAME.upper())
        title.setObjectName("AppTitle")
        brand.addWidget(logo)
        brand.addWidget(title)
        header.addLayout(brand)
        header.addStretch(1)
        self._dots = StepDots(7)
        header.addWidget(self._dots)
        outer.addLayout(header)

        self._heading = QLabel()
        self._heading.setObjectName("PageTitle")
        self._heading.setWordWrap(True)
        self._sub = QLabel()
        self._sub.setObjectName("PageSubtitle")
        self._sub.setWordWrap(True)
        outer.addWidget(self._heading)
        outer.addWidget(self._sub)

        card = QFrame()
        card.setObjectName("Card")
        card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(28, 24, 28, 24)
        self._stack = QStackedWidget()
        card_layout.addWidget(self._stack, 1)
        outer.addWidget(card, 1)

        footer = QHBoxLayout()
        self._back = QPushButton(self.tr("Back"))
        self._back.setObjectName("Ghost")
        self._back.clicked.connect(self._go_back)
        contact = QPushButton(self.tr("Contact developer"))
        contact.setObjectName("Ghost")
        contact.setAccessibleName(self.tr("Contact developer by email"))
        contact.setToolTip(self.tr("Open your email app to write to the EasyRestore developer"))
        contact.clicked.connect(self._contact_developer)
        self._next = QPushButton(self.tr("Continue"))
        self._next.setObjectName("Primary")
        self._next.setDefault(True)
        self._next.clicked.connect(self._go_next)
        footer.addWidget(self._back)
        footer.addWidget(contact)
        footer.addStretch(1)
        footer.addWidget(self._next)
        outer.addLayout(footer)

        self._pages: list[WizardPage] = [
            WelcomePage(self.session, helper),
            ActionPage(self.session),
            FirmwarePage(self.session),
            DeviceModePage(self.session, helper),
            PreflightPage(self.session, helper),
            RestorePage(self.session, helper),
            CompletePage(self.session),
        ]
        for page in self._pages:
            self._stack.addWidget(page)
            page.can_continue_changed.connect(lambda _: self._refresh_buttons())

        self._show_page(0)

    def _contact_developer(self) -> None:
        QDesktopServices.openUrl(QUrl(DEVELOPER_MAILTO))

    def _current(self) -> WizardPage:
        return self._pages[self._stack.currentIndex()]

    def _show_page(self, index: int) -> None:
        current = self._stack.currentIndex()
        if current != index:
            if not self._pages[current].on_leave():
                return
        self._stack.setCurrentIndex(index)
        page = self._pages[index]
        self._heading.setText(self.tr(page.title))
        self._sub.setText(self.tr(page.subtitle))
        self._dots.set_index(index)
        self._next.setText(self.tr(page.continue_label))
        page.on_enter()
        self._refresh_buttons()
        page.setFocus(Qt.FocusReason.OtherFocusReason)

    def _refresh_buttons(self) -> None:
        index = self._stack.currentIndex()
        self._back.setEnabled(index > 0)
        self._next.setEnabled(self._current().can_continue())
        last = index == len(self._pages) - 1
        self._next.setAccessibleName(self.tr("Close") if last else self.tr("Continue"))

    def _go_back(self) -> None:
        index = self._stack.currentIndex()
        if index > 0:
            self._show_page(index - 1)

    def _go_next(self) -> None:
        if not self._current().can_continue():
            return
        index = self._stack.currentIndex()
        if index >= len(self._pages) - 1:
            self.close()
            return
        self._show_page(index + 1)
