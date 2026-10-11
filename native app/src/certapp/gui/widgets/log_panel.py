"""In-app logging console widget with color-coded levels."""

import time
from pathlib import Path
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QTextCursor, QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLabel,
    QPushButton, QFileDialog
)


class LogPanelWidget(QWidget):
    """Logging console widget displaying color-coded application log output."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Header bar
        header = QHBoxLayout()
        lbl_title = QLabel("📋 Application Log Console")
        lbl_title.setStyleSheet("font-weight: bold; font-size: 12px; color: #AAAAAA;")

        btn_clear = QPushButton("Clear Log")
        btn_export = QPushButton("Export Log...")

        for btn in (btn_clear, btn_export):
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #2D3047;
                    color: #DDDDDD;
                    border: 1px solid #4A4D6B;
                    border-radius: 3px;
                    padding: 3px 8px;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: #3A86FF;
                }
            """)

        btn_clear.clicked.connect(self.clear_log)
        btn_export.clicked.connect(self.export_log)

        header.addWidget(lbl_title)
        header.addStretch()
        header.addWidget(btn_clear)
        header.addWidget(btn_export)

        # Text Console
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setFont(QFont("Monospace", 9))
        self.text_edit.setStyleSheet("""
            QTextEdit {
                background-color: #12131C;
                color: #D4D4D4;
                border: 1px solid #2E3148;
                border-radius: 4px;
            }
        """)

        layout.addLayout(header)
        layout.addWidget(self.text_edit)

    @Slot(str, str)
    def append_log(self, level: str, message: str):
        timestamp = time.strftime("%H:%M:%S")
        level_upper = level.upper()

        if level_upper in ("ERROR", "FAIL", "CRITICAL"):
            color = "#FF5555"  # Bright Red
        elif level_upper in ("SUCCESS", "OK"):
            color = "#50FA7B"  # Bright Green
        elif level_upper in ("WARNING", "WARN"):
            color = "#FFB86C"  # Orange/Yellow
        else:
            color = "#8BE9FD"  # Cyan/Blue for Info

        html = f'<span style="color: #6272A4;">[{timestamp}]</span> <b style="color: {color};">[{level_upper}]</b> {message}'

        self.text_edit.append(html)
        self.text_edit.moveCursor(QTextCursor.End)

    def info(self, msg: str):
        self.append_log("INFO", msg)

    def success(self, msg: str):
        self.append_log("SUCCESS", msg)

    def warning(self, msg: str):
        self.append_log("WARN", msg)

    def error(self, msg: str):
        self.append_log("ERROR", msg)

    def clear_log(self):
        self.text_edit.clear()

    def export_log(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Log File", "app.log", "Text Files (*.log *.txt)")
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.text_edit.toPlainText())
