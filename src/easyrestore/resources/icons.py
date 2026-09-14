from __future__ import annotations

from functools import lru_cache

from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QImage, QPainter

from easyrestore.resources import resource_path


@lru_cache(maxsize=1)
def app_icon() -> QIcon:
    """Build a multi-resolution application icon from the bundled logo."""
    icon = QIcon()
    png = resource_path("easyrestore-logo.png")
    if png.is_file():
        icon.addFile(str(png))
    svg = resource_path("easyrestore-logo.svg")
    if svg.is_file():
        renderer = QSvgRenderer(str(svg))
        if renderer.isValid():
            for size in (16, 24, 32, 48, 64, 128, 256):
                image = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
                image.fill(Qt.GlobalColor.transparent)
                painter = QPainter(image)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                renderer.render(painter)
                painter.end()
                icon.addPixmap(QPixmap.fromImage(image))
    return icon


def logo_pixmap(size: int = 36) -> QPixmap:
    icon = app_icon()
    return icon.pixmap(QSize(size, size))
