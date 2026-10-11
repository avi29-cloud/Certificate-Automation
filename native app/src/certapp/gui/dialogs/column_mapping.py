"""Fallback manual column mapping selector dialog."""

from typing import List, Dict
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton
)


class ColumnMappingDialog(QDialog):
    """Dialog allowing user to manually select which CSV columns represent Name and Email."""

    def __init__(self, raw_columns: List[str], current_mapping: Dict[str, str], parent=None):
        super().__init__(parent)
        self.raw_columns = raw_columns
        self.current_mapping = current_mapping

        self.setWindowTitle("📌 Select Sheet Header Mapping")
        self.setFixedWidth(400)

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        lbl_intro = QLabel(
            "Auto-detection needs confirmation. Please select the correct headers from your sheet:"
        )
        lbl_intro.setWordWrap(True)
        layout.addWidget(lbl_intro)

        # Name Column Selector
        layout_name = QHBoxLayout()
        lbl_name = QLabel("Name Column:")
        self.combo_name = QComboBox()
        self.combo_name.addItems(self.raw_columns)
        if self.current_mapping.get("name_col") in self.raw_columns:
            self.combo_name.setCurrentText(self.current_mapping["name_col"])

        layout_name.addWidget(lbl_name)
        layout_name.addWidget(self.combo_name, 1)
        layout.addLayout(layout_name)

        # Email Column Selector
        layout_email = QHBoxLayout()
        lbl_email = QLabel("Email Column:")
        self.combo_email = QComboBox()
        self.combo_email.addItems(self.raw_columns)
        if self.current_mapping.get("email_col") in self.raw_columns:
            self.combo_email.setCurrentText(self.current_mapping["email_col"])

        layout_email.addWidget(lbl_email)
        layout_email.addWidget(self.combo_email, 1)
        layout.addLayout(layout_email)

        # Buttons
        layout_btns = QHBoxLayout()
        btn_ok = QPushButton("Confirm Mapping")
        btn_ok.clicked.connect(self.accept)

        layout_btns.addStretch()
        layout_btns.addWidget(btn_ok)
        layout.addLayout(layout_btns)

    def get_selected_mapping(self) -> Dict[str, str]:
        return {
            "name_col": self.combo_name.currentText(),
            "email_col": self.combo_email.currentText(),
        }
