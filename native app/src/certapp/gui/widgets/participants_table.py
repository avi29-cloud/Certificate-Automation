"""Data preview and status table widget for participants."""

import os
from pathlib import Path
from typing import List, Dict, Optional
from PySide6.QtCore import Signal, Qt, QUrl
from PySide6.QtGui import QColor, QDesktopServices
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QHeaderView, QLineEdit, QComboBox,
    QCheckBox, QPushButton
)

from src.certapp.core.models import Participant


class ParticipantsTableWidget(QWidget):
    """Dynamic table widget rendering participants and live generation/send statuses."""

    participant_selection_changed = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.participants: List[Participant] = []
        self.filtered_participants: List[Participant] = []

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)

        # Filter & Search Header Bar
        filter_bar = QHBoxLayout()

        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("🔍 Search by name or email...")
        self.txt_search.textChanged.connect(self.apply_filter)

        self.combo_filter = QComboBox()
        self.combo_filter.addItems([
            "All Rows",
            "Valid Only",
            "Invalid / Duplicates",
            "Certificates Generated",
            "Emails Sent",
            "Pending Emails"
        ])
        self.combo_filter.currentTextChanged.connect(self.apply_filter)

        self.chk_select_all = QCheckBox("Select All Visible")
        self.chk_select_all.setChecked(True)
        self.chk_select_all.stateChanged.connect(self.toggle_select_all)

        self.lbl_count = QLabel("0 participants")
        self.lbl_count.setStyleSheet("color: #888888; font-size: 11px;")

        filter_bar.addWidget(self.txt_search, 2)
        filter_bar.addWidget(self.combo_filter, 1)
        filter_bar.addWidget(self.chk_select_all)
        filter_bar.addWidget(self.lbl_count)

        # Table View
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Select", "#", "Name", "Email", "Validation", "Gen Status", "Send Status", "Certificate File"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.cellDoubleClicked.connect(self.on_cell_double_clicked)

        layout.addLayout(filter_bar)
        layout.addWidget(self.table)

    def set_participants(self, participants: List[Participant]):
        self.participants = participants
        self.apply_filter()

    def apply_filter(self):
        search_kw = self.txt_search.text().lower().strip()
        filter_mode = self.combo_filter.currentText()

        self.filtered_participants.clear()

        for p in self.participants:
            # Keyword filter
            if search_kw and (search_kw not in p.name.lower() and search_kw not in p.email.lower()):
                continue

            # Category filter
            if filter_mode == "Valid Only" and p.validation_status != "valid":
                continue
            elif filter_mode == "Invalid / Duplicates" and p.validation_status == "valid":
                continue
            elif filter_mode == "Certificates Generated" and p.generation_status != "generated":
                continue
            elif filter_mode == "Emails Sent" and p.send_status != "sent":
                continue
            elif filter_mode == "Pending Emails" and p.send_status == "sent":
                continue

            self.filtered_participants.append(p)

        self.render_table()

    def render_table(self):
        self.table.setRowCount(len(self.filtered_participants))
        self.lbl_count.setText(f"{len(self.filtered_participants)} / {len(self.participants)} rows")

        for row_idx, p in enumerate(self.filtered_participants):
            # 0. Checkbox
            chk_item = QTableWidgetItem()
            chk_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            chk_item.setCheckState(Qt.Checked if p.validation_status == "valid" else Qt.Unchecked)
            self.table.setItem(row_idx, 0, chk_item)

            # 1. Row Index
            self.table.setItem(row_idx, 1, QTableWidgetItem(str(p.row_index)))

            # 2. Name
            self.table.setItem(row_idx, 2, QTableWidgetItem(p.name))

            # 3. Email
            self.table.setItem(row_idx, 3, QTableWidgetItem(p.email))

            # 4. Validation Status Badge
            val_item = QTableWidgetItem(p.validation_status)
            if p.validation_status == "valid":
                val_item.setBackground(QColor("#1B4D3E"))
                val_item.setForeground(QColor("#A3E4D7"))
            elif p.validation_status == "duplicate":
                val_item.setBackground(QColor("#5D4037"))
                val_item.setForeground(QColor("#FFE0B2"))
            else:
                val_item.setBackground(QColor("#4A154B"))
                val_item.setForeground(QColor("#FADBD8"))
            self.table.setItem(row_idx, 4, val_item)

            # 5. Generation Status
            gen_item = QTableWidgetItem(p.generation_status)
            if p.generation_status == "generated":
                gen_item.setForeground(QColor("#2ECC71"))
            elif p.generation_status == "failed":
                gen_item.setForeground(QColor("#E74C3C"))
            self.table.setItem(row_idx, 5, gen_item)

            # 6. Send Status
            send_item = QTableWidgetItem(p.send_status)
            if p.send_status == "sent":
                send_item.setForeground(QColor("#2ECC71"))
            elif p.send_status == "failed":
                send_item.setForeground(QColor("#E74C3C"))
            self.table.setItem(row_idx, 6, send_item)

            # 7. Certificate File Path
            path_str = Path(p.certificate_path).name if p.certificate_path else ""
            file_item = QTableWidgetItem(path_str)
            if p.certificate_path:
                file_item.setForeground(QColor("#3A86FF"))
            self.table.setItem(row_idx, 7, file_item)

    def toggle_select_all(self, state: int):
        is_checked = (state == Qt.Checked.value or state == True)
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item:
                item.setCheckState(Qt.Checked if is_checked else Qt.Unchecked)

    def get_selected_participants(self) -> List[Participant]:
        selected: List[Participant] = []
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and item.checkState() == Qt.Checked:
                selected.append(self.filtered_participants[row])
        return selected

    def update_participant_row(self, participant: Participant):
        """Finds participant and updates their table display."""
        for idx, p in enumerate(self.filtered_participants):
            if p.row_index == participant.row_index:
                # Update item statuses
                if self.table.item(idx, 5):
                    self.table.item(idx, 5).setText(p.generation_status)
                if self.table.item(idx, 6):
                    self.table.item(idx, 6).setText(p.send_status)
                if self.table.item(idx, 7) and p.certificate_path:
                    self.table.item(idx, 7).setText(Path(p.certificate_path).name)
                break

    def on_cell_double_clicked(self, row: int, col: int):
        if row < len(self.filtered_participants):
            p = self.filtered_participants[row]
            if p.certificate_path and Path(p.certificate_path).exists():
                QDesktopServices.openUrl(QUrl.fromLocalFile(p.certificate_path))
