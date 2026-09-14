from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication


LIGHT = """
* {
    color: #1c1c1e;
}

QMainWindow, QWidget#WizardRoot {
    background: #f4f5f7;
    color: #1c1c1e;
    font-size: 14px;
}

QLabel {
    color: #1c1c1e;
    background: transparent;
}

QLabel#AppTitle {
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 0.4px;
    color: #6e6e73;
}

QLabel#PageTitle {
    font-size: 28px;
    font-weight: 600;
    color: #1c1c1e;
}

QLabel#PageSubtitle, QLabel#Muted {
    font-size: 15px;
    color: #6e6e73;
}

QLabel#StatusOk { color: #248a3d; font-weight: 600; }
QLabel#StatusWait { color: #c93400; font-weight: 600; }
QLabel#StatusIdle { color: #6e6e73; font-weight: 600; }

QFrame#Card {
    background: #ffffff;
    border: 1px solid #d2d2d7;
    border-radius: 16px;
    color: #1c1c1e;
}

QStackedWidget, QWidget {
    background: transparent;
    color: #1c1c1e;
}

QPushButton#Primary {
    background: #0071e3;
    color: #ffffff;
    border: none;
    border-radius: 12px;
    padding: 10px 20px;
    font-weight: 600;
    min-width: 120px;
}
QPushButton#Primary:hover { background: #0077ed; }
QPushButton#Primary:pressed { background: #006edb; }
QPushButton#Primary:disabled { background: #b7d7f5; color: #f2f8ff; }

QPushButton#Ghost {
    background: transparent;
    color: #0071e3;
    border: none;
    padding: 10px 16px;
    font-weight: 600;
}
QPushButton#Ghost:hover { color: #006edb; }
QPushButton#Ghost:disabled { color: #a1a1a6; }

QFrame#Choice {
    background: #ffffff;
    border: 1px solid #d2d2d7;
    border-radius: 14px;
    color: #1c1c1e;
}
QFrame#Choice:hover { border-color: #0071e3; }
QFrame#Choice[selected="true"] {
    border: 2px solid #0071e3;
    background: #f0f7ff;
}

QLineEdit, QComboBox {
    background: #ffffff;
    color: #1c1c1e;
    border: 1px solid #d2d2d7;
    border-radius: 10px;
    padding: 8px 10px;
    selection-background-color: #0071e3;
    selection-color: #ffffff;
}
QLineEdit:disabled, QComboBox:disabled {
    background: #f4f5f7;
    color: #8e8e93;
}
QComboBox QAbstractItemView {
    background: #ffffff;
    color: #1c1c1e;
    selection-background-color: #0071e3;
    selection-color: #ffffff;
}

QRadioButton, QCheckBox {
    color: #1c1c1e;
    spacing: 8px;
    background: transparent;
}
QRadioButton::indicator, QCheckBox::indicator {
    width: 18px;
    height: 18px;
}

QProgressBar {
    border: none;
    background: #e8e8ed;
    border-radius: 6px;
    height: 10px;
    text-align: center;
    color: #1c1c1e;
}
QProgressBar::chunk {
    background: #0071e3;
    border-radius: 6px;
}

QPlainTextEdit#TechLog, QTextEdit#TechLog {
    background: #1c1c1e;
    color: #e8e8ed;
    border-radius: 10px;
    border: 1px solid #3a3a3c;
    font-family: monospace;
    font-size: 12px;
}
"""

DARK = """
* {
    color: #f5f5f7;
}

QMainWindow, QWidget#WizardRoot {
    background: #1c1c1e;
    color: #f5f5f7;
    font-size: 14px;
}

QLabel {
    color: #f5f5f7;
    background: transparent;
}

QLabel#AppTitle {
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 0.4px;
    color: #a1a1a6;
}

QLabel#PageTitle {
    font-size: 28px;
    font-weight: 600;
    color: #f5f5f7;
}

QLabel#PageSubtitle, QLabel#Muted {
    font-size: 15px;
    color: #a1a1a6;
}

QLabel#StatusOk { color: #30d158; font-weight: 600; }
QLabel#StatusWait { color: #ff9f0a; font-weight: 600; }
QLabel#StatusIdle { color: #a1a1a6; font-weight: 600; }

QFrame#Card {
    background: #2c2c2e;
    border: 1px solid #3a3a3c;
    border-radius: 16px;
    color: #f5f5f7;
}

QStackedWidget, QWidget {
    background: transparent;
    color: #f5f5f7;
}

QPushButton#Primary {
    background: #0a84ff;
    color: #ffffff;
    border: none;
    border-radius: 12px;
    padding: 10px 20px;
    font-weight: 600;
    min-width: 120px;
}
QPushButton#Primary:hover { background: #409cff; }
QPushButton#Primary:pressed { background: #0066cc; }
QPushButton#Primary:disabled { background: #3a3a3c; color: #8e8e93; }

QPushButton#Ghost {
    background: transparent;
    color: #0a84ff;
    border: none;
    padding: 10px 16px;
    font-weight: 600;
}
QPushButton#Ghost:hover { color: #409cff; }
QPushButton#Ghost:disabled { color: #636366; }

QFrame#Choice {
    background: #2c2c2e;
    border: 1px solid #3a3a3c;
    border-radius: 14px;
    color: #f5f5f7;
}
QFrame#Choice:hover { border-color: #0a84ff; }
QFrame#Choice[selected="true"] {
    border: 2px solid #0a84ff;
    background: #1c2b3a;
}

QLineEdit, QComboBox {
    background: #1c1c1e;
    color: #f5f5f7;
    border: 1px solid #3a3a3c;
    border-radius: 10px;
    padding: 8px 10px;
    selection-background-color: #0a84ff;
    selection-color: #ffffff;
}
QLineEdit:disabled, QComboBox:disabled {
    background: #2c2c2e;
    color: #636366;
}
QComboBox QAbstractItemView {
    background: #1c1c1e;
    color: #f5f5f7;
    selection-background-color: #0a84ff;
    selection-color: #ffffff;
}

QRadioButton, QCheckBox {
    color: #f5f5f7;
    spacing: 8px;
    background: transparent;
}
QRadioButton::indicator, QCheckBox::indicator {
    width: 18px;
    height: 18px;
}

QProgressBar {
    border: none;
    background: #3a3a3c;
    border-radius: 6px;
    height: 10px;
    text-align: center;
    color: #f5f5f7;
}
QProgressBar::chunk {
    background: #0a84ff;
    border-radius: 6px;
}

QPlainTextEdit#TechLog, QTextEdit#TechLog {
    background: #000000;
    color: #e8e8ed;
    border-radius: 10px;
    border: 1px solid #3a3a3c;
    font-family: monospace;
    font-size: 12px;
}
"""

# Back-compat alias used by older imports.
STYLESHEET = LIGHT


def _system_prefers_dark() -> bool:
    app = QApplication.instance()
    if app is not None:
        hints = app.styleHints()
        scheme = hints.colorScheme()
        if scheme == Qt.ColorScheme.Dark:
            return True
        if scheme == Qt.ColorScheme.Light:
            return False
    # Fallback: inspect the window palette before we override the stylesheet.
    palette = QGuiApplication.palette()
    window = palette.color(palette.ColorRole.Window)
    return window.lightness() < 128


def stylesheet_for_system() -> str:
    return DARK if _system_prefers_dark() else LIGHT
