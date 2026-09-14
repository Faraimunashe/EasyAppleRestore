from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout

from easyrestore.backend.device import DeviceMode
from easyrestore.backend.dfu_guides import ModeGuide, guide_for_identifier
from easyrestore.backend.helper_client import HelperClient
from easyrestore.wizard.page import WizardPage
from easyrestore.wizard.widgets import PhoneGlyph


class DeviceModePage(WizardPage):
    title = "Get the device ready"
    subtitle = "Follow the highlighted step. The status updates the moment the mode changes."

    def __init__(self, session, helper: HelperClient, parent=None) -> None:
        super().__init__(session, parent)
        self._helper = helper
        self._step_index = 0
        self._hold_ticks = 0
        self._guide: ModeGuide | None = None
        self._target_recovery = True

        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        hero = QVBoxLayout()
        phone_row = QVBoxLayout()
        phone_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        phone_row.addWidget(PhoneGlyph(), 0, Qt.AlignmentFlag.AlignCenter)
        hero.addLayout(phone_row)

        self._mode = QLabel(self.tr("We detected: looking…"))
        self._mode.setObjectName("StatusWait")
        self._mode.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._mode.setAccessibleName(self.tr("Current device mode"))
        mode_font = self._mode.font()
        mode_font.setWeight(QFont.Weight.DemiBold)
        mode_font.setPointSize(max(mode_font.pointSize(), 12) + 2)
        self._mode.setFont(mode_font)
        hero.addWidget(self._mode)
        layout.addLayout(hero)

        self._guide_title = QLabel("")
        guide_font = self._guide_title.font()
        guide_font.setWeight(QFont.Weight.DemiBold)
        self._guide_title.setFont(guide_font)
        self._guide_title.setWordWrap(True)
        layout.addWidget(self._guide_title)

        self._active = QFrame()
        self._active.setObjectName("Choice")
        self._active.setProperty("selected", True)
        self._active.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        active_layout = QVBoxLayout(self._active)
        active_layout.setContentsMargins(16, 14, 16, 14)
        self._active_label = QLabel("")
        self._active_label.setWordWrap(True)
        self._active_label.setAccessibleName(self.tr("Current button step"))
        active_font = self._active_label.font()
        active_font.setWeight(QFont.Weight.DemiBold)
        active_font.setPointSize(max(active_font.pointSize(), 11) + 1)
        self._active_label.setFont(active_font)
        self._hold = QLabel("")
        self._hold.setObjectName("Muted")
        active_layout.addWidget(self._active_label)
        active_layout.addWidget(self._hold)
        layout.addWidget(self._active)

        self._steps = QLabel("")
        self._steps.setObjectName("Muted")
        self._steps.setWordWrap(True)
        self._steps.setAccessibleName(self.tr("Full button sequence"))
        layout.addWidget(self._steps)

        note = QLabel(
            self.tr(
                "Sequences follow Apple’s public support articles by device family. "
                "They still need per-model verification before we treat them as final."
            )
        )
        note.setObjectName("Muted")
        note.setWordWrap(True)
        layout.addWidget(note)
        layout.addStretch(1)

        self._timer = QTimer(self)
        self._timer.setInterval(900)
        self._timer.timeout.connect(self._tick)

    def on_enter(self) -> None:
        identifier = self.session.device_identifier
        if not identifier and self.session.device:
            identifier = self.session.device.identifier
        self._guide = guide_for_identifier(identifier)
        self._guide_title.setText(self._guide.title)
        self._step_index = 0
        self._hold_ticks = 0
        self._target_recovery = True
        self._render_steps()
        self._tick()
        self._timer.start()

    def on_leave(self) -> bool:
        self._timer.stop()
        return True

    def _sequence(self):
        assert self._guide is not None
        return self._guide.recovery if self._target_recovery else self._guide.dfu

    def _tick(self) -> None:
        device = self._helper.get_device_mode()
        self.session.device = device
        if device is None:
            text = self.tr("We detected: disconnected")
            self._mode.setObjectName("StatusWait")
        else:
            text = self.tr("We detected: {mode}").format(mode=device.mode.value)
            ready = device.mode in {DeviceMode.RECOVERY, DeviceMode.DFU, DeviceMode.RESTORE}
            self._mode.setObjectName("StatusOk" if ready else "StatusWait")
            if device.mode is DeviceMode.DFU:
                self._target_recovery = False
            elif device.mode is DeviceMode.RECOVERY:
                self._target_recovery = True
        self._mode.setText(text)
        self._mode.style().unpolish(self._mode)
        self._mode.style().polish(self._mode)

        steps = self._sequence()
        if not steps:
            return

        current = steps[self._step_index % len(steps)]
        hold = current.hold_seconds
        if hold:
            needed = max(1, int(round(hold / (self._timer.interval() / 1000))))
            self._hold_ticks += 1
            remaining = max(0, hold - self._hold_ticks * (self._timer.interval() / 1000))
            self._hold.setText(
                self.tr("Keep holding… about {seconds:.0f}s left").format(seconds=remaining)
            )
            if self._hold_ticks >= needed:
                self._hold_ticks = 0
                self._step_index = (self._step_index + 1) % len(steps)
        else:
            self._hold.setText(self.tr("Then continue to the next step"))
            self._hold_ticks = 0
            self._step_index = (self._step_index + 1) % len(steps)

        self._render_steps()
        # Pulse selection state so dark/light styles refresh.
        self._active.setProperty("selected", False)
        self._active.style().unpolish(self._active)
        self._active.style().polish(self._active)
        self._active.setProperty("selected", True)
        self._active.style().unpolish(self._active)
        self._active.style().polish(self._active)

    def _render_steps(self) -> None:
        steps = self._sequence()
        if not steps:
            self._active_label.setText(self.tr("Connect your device so we can choose a button guide."))
            self._steps.setText("")
            return
        index = self._step_index % len(steps)
        current = steps[index]
        kind = self.tr("Recovery") if self._target_recovery else self.tr("DFU")
        self._active_label.setText(
            self.tr("{kind} step {n} of {total}: {text}").format(
                kind=kind,
                n=index + 1,
                total=len(steps),
                text=current.instruction,
            )
        )
        lines = []
        for i, step in enumerate(steps):
            mark = "●" if i == index else "○"
            lines.append(f"{mark} {i + 1}. {step.instruction}")
        self._steps.setText("\n".join(lines))
