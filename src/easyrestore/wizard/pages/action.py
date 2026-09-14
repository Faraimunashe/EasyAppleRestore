from __future__ import annotations

from PySide6.QtWidgets import QLabel, QVBoxLayout

from easyrestore.session import RestoreAction
from easyrestore.wizard.page import WizardPage
from easyrestore.wizard.widgets import ChoiceCard


class ActionPage(WizardPage):
    title = "What do you want to do?"
    subtitle = "Pick the option that matches your goal. You can change this later."

    def __init__(self, session, parent=None) -> None:
        super().__init__(session, parent)
        self._cards: dict[RestoreAction, ChoiceCard] = {}

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        choices = (
            (
                RestoreAction.UPDATE,
                self.tr("Restore or update"),
                self.tr("Install the latest signed firmware. Your data may be kept if the device allows it."),
            ),
            (
                RestoreAction.DOWNGRADE,
                self.tr("Downgrade"),
                self.tr("Install an older firmware. Apple must still be signing that version."),
            ),
            (
                RestoreAction.ERASE,
                self.tr("Erase and restore"),
                self.tr("Wipe the device and install firmware as new. Everything on the device will be deleted."),
            ),
            (
                RestoreAction.HELP_ME,
                self.tr("I am not sure — help me pick"),
                self.tr("We will recommend a path from a few plain-language questions."),
            ),
        )
        for action, title, description in choices:
            card = ChoiceCard(title, description)
            card.clicked.connect(lambda act=action: self._select(act))
            self._cards[action] = card
            layout.addWidget(card)

        self._explainer = QLabel("")
        self._explainer.setObjectName("Muted")
        self._explainer.setWordWrap(True)
        layout.addWidget(self._explainer)
        layout.addStretch(1)

    def can_continue(self) -> bool:
        return self.session.action is not None

    def _select(self, action: RestoreAction) -> None:
        self.session.action = action
        for key, card in self._cards.items():
            card.set_selected(key is action)
        notes = {
            RestoreAction.UPDATE: self.tr("Best default if the phone already works and you just need a clean install of a signed iOS."),
            RestoreAction.DOWNGRADE: self.tr("Only versions Apple is still signing can be installed. We will check that before downloading."),
            RestoreAction.ERASE: self.tr("Use this for a device you are giving away, selling, or that will not boot normally."),
            RestoreAction.HELP_ME: self.tr("On the next screens we will still let you confirm before anything is erased or installed."),
        }
        self._explainer.setText(notes[action])
        self.can_continue_changed.emit(True)
