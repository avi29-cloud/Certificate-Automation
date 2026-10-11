"""File Drag-and-Drop Zone Widget."""

from pathlib import Path
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QLabel, QPushButton, QFileDialog
)


class DropZoneWidget(QFrame):
    """Interactive drag-and-drop card widget for selecting files."""

    file_selected = Signal(str)

    def __init__(
        self,
        title: str = "Drop File Here",
        subtitle: str = "or click to browse",
        filter_mode: str = "sheet",  # "sheet" or "template"
        parent=None
    ):
        super().__init__(parent)
        self.title_text = title
        self.subtitle_text = subtitle
        self.filter_mode = filter_mode
        self.current_file_path: str = ""

        self.setAcceptDrops(True)
        self.setObjectName("DropZone")

        self.init_ui()

    def init_ui(self):
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        self.setLineWidth(2)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setAlignment(Qt.AlignCenter)

        self.icon_label = QLabel("📄" if self.filter_mode == "sheet" else "🎨")
        self.icon_label.setStyleSheet("font-size: 32px;")
        self.icon_label.setAlignment(Qt.AlignCenter)

        self.title_label = QLabel(self.title_text)
        self.title_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #E0E0E0;")
        self.title_label.setAlignment(Qt.AlignCenter)

        self.sub_label = QLabel(self.subtitle_text)
        self.sub_label.setStyleSheet("font-size: 11px; color: #888888;")
        self.sub_label.setAlignment(Qt.AlignCenter)

        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.setCursor(Qt.PointingHandCursor)
        self.browse_btn.clicked.connect(self.browse_file)

        self.file_name_label = QLabel("")
        self.file_name_label.setStyleSheet("font-size: 12px; color: #4CAF50; font-weight: bold;")
        self.file_name_label.setAlignment(Qt.AlignCenter)
        self.file_name_label.setWordWrap(True)

        layout.addWidget(self.icon_label)
        layout.addWidget(self.title_label)
        layout.addWidget(self.sub_label)
        layout.addWidget(self.browse_btn)
        layout.addWidget(self.file_name_label)

        self.apply_style(hover=False)

    def apply_style(self, hover: bool = False):
        border_color = "#3A86FF" if hover else "#444444"
        bg_color = "#252836" if hover else "#1E1F29"
        self.setStyleSheet(f"""
            QFrame#DropZone {{
                background-color: {bg_color};
                border: 2px dashed {border_color};
                border-radius: 10px;
            }}
            QPushButton {{
                background-color: #2D3047;
                color: #FFFFFF;
                border: 1px solid #4A4D6B;
                border-radius: 5px;
                padding: 6px 14px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #3A86FF;
                border-color: #3A86FF;
            }}
        """)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.apply_style(hover=True)

    def dragLeaveEvent(self, event):
        self.apply_style(hover=False)

    def dropEvent(self, event: QDropEvent):
        self.apply_style(hover=False)
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if self.validate_file(path):
                self.set_file(path)

    def validate_file(self, path: str) -> bool:
        p = Path(path)
        ext = p.suffix.lower()
        if self.filter_mode == "sheet":
            return ext in (".csv", ".xlsx", ".xls", ".tsv", ".txt")
        else:
            return ext in (".png", ".jpg", ".jpeg", ".pdf")

    def browse_file(self):
        if self.filter_mode == "sheet":
            filter_str = "Data Files (*.csv *.xlsx *.xls *.tsv);;All Files (*)"
        else:
            filter_str = "Images & PDF (*.png *.jpg *.jpeg *.pdf);;All Files (*)"

        path, _ = QFileDialog.getOpenFileName(self, "Select File", "", filter_str)
        if path and self.validate_file(path):
            self.set_file(path)

    def set_file(self, path: str):
        self.current_file_path = path
        p = Path(path)
        self.file_name_label.setText(f"✓ {p.name}")
        self.file_selected.emit(path)
