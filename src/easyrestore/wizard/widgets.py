from __future__ import annotations

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget


class PhoneGlyph(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(88, 140)
        self.setAccessibleName(self.tr("Phone illustration"))

    def paintEvent(self, event) -> None:  # noqa: ANN001
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        body = QRectF(8, 4, 72, 132)
        path = QPainterPath()
        path.addRoundedRect(body, 16, 16)
        painter.fillPath(path, QColor("#1c1c1e"))
        screen = QRectF(16, 18, 56, 96)
        screen_path = QPainterPath()
        screen_path.addRoundedRect(screen, 8, 8)
        painter.fillPath(screen_path, QColor("#f4f5f7"))
        painter.setPen(QPen(QColor("#d2d2d7"), 2))
        painter.drawRoundedRect(QRectF(36, 122, 16, 4), 2, 2)


class StepDots(QWidget):
    def __init__(self, count: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._count = count
        self._index = 0
        self.setFixedHeight(12)
        self.setAccessibleName(self.tr("Wizard progress"))

    def set_index(self, index: int) -> None:
        self._index = index
        self.update()
        self.setAccessibleDescription(
            self.tr("Step {current} of {total}").format(
                current=index + 1, total=self._count
            )
        )

    def paintEvent(self, event) -> None:  # noqa: ANN001
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        spacing = 14
        total_w = self._count * 8 + (self._count - 1) * (spacing - 8)
        x = (self.width() - total_w) / 2
        y = self.height() / 2
        for i in range(self._count):
            if i == self._index:
                color = QColor("#0a84ff")
            else:
                # Readable on both light and dark window chrome.
                color = QColor("#636366")
            painter.setBrush(color)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(int(x), int(y - 4), 8, 8)
            x += spacing


class ChoiceCard(QFrame):
    clicked = Signal()

    def __init__(self, title: str, description: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Choice")
        self.setProperty("selected", False)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        heading = QLabel(title)
        font = QFont(heading.font())
        font.setWeight(QFont.Weight.DemiBold)
        font.setPointSize(max(font.pointSize(), 11) + 1)
        heading.setFont(font)
        body = QLabel(description)
        body.setObjectName("Muted")
        body.setWordWrap(True)
        layout.addWidget(heading)
        layout.addWidget(body)
        self.setAccessibleName(title)
        self.setAccessibleDescription(description)

    def set_selected(self, selected: bool) -> None:
        self.setProperty("selected", selected)
        self.style().unpolish(self)
        self.style().polish(self)

    def mouseReleaseEvent(self, event) -> None:  # noqa: ANN001
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event) -> None:  # noqa: ANN001
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self.clicked.emit()
            return
        super().keyPressEvent(event)


class ChecklistRow(QWidget):
    def __init__(self, label: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 6, 0, 6)
        self._mark = QLabel("•")
        self._mark.setFixedWidth(24)
        self._mark.setObjectName("StatusIdle")
        self._text = QLabel(label)
        self._text.setWordWrap(True)
        layout.addWidget(self._mark, 0, Qt.AlignmentFlag.AlignTop)
        layout.addWidget(self._text, 1)
        self.set_state("pending", self.tr("Waiting"))

    def set_state(self, state: str, detail: str) -> None:
        marks = {"pending": "•", "ok": "✓", "fail": "!", "skip": "–"}
        names = {"pending": "StatusIdle", "ok": "StatusOk", "fail": "StatusWait", "skip": "StatusIdle"}
        self._mark.setText(marks.get(state, "•"))
        self._mark.setObjectName(names.get(state, "StatusIdle"))
        self._mark.style().unpolish(self._mark)
        self._mark.style().polish(self._mark)
        self.setAccessibleName(f"{self._text.text()}: {detail}")
