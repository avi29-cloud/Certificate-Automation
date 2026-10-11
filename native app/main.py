"""Application Entry Point for CertApp."""

import sys
import logging
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFontDatabase, QIcon

from src.certapp.gui.main_window import MainWindow
from src.certapp.gui.theme import DARK_THEME
from src.certapp.core.utils import get_fonts_dir

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("CertApp")
    app.setOrganizationName("CertAppTeam")
    app.setStyleSheet(DARK_THEME)

    # Load bundled fonts if any exist
    fonts_dir = get_fonts_dir()
    if fonts_dir.exists():
        for font_file in fonts_dir.glob("*.[to]tf"):
            QFontDatabase.addApplicationFont(str(font_file))

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
