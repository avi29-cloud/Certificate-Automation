"""Pre-send safety confirmation and summary dialog."""

from typing import List
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QCheckBox, QFrame
)

from src.certapp.core.models import Participant
from src.certapp.core.settings import SMTPSettings
from src.certapp.gui.theme import DARK_THEME, BTN_SUCCESS, BTN_SECONDARY


class ConfirmSendDialog(QDialog):
    """Safety dialog summarizing recipient count, email settings, and confirmation guard."""

    def __init__(self, participants: List[Participant], settings: SMTPSettings, parent=None):
        super().__init__(parent)
        self.participants = participants
        self.settings = settings

        self.setWindowTitle("🚀 Confirm Bulk Email Send")
        self.setFixedWidth(540)
        self.setStyleSheet(DARK_THEME)

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(22, 22, 22, 22)

        valid_count = sum(1 for p in self.participants if p.validation_status == "valid" and p.certificate_path)

        lbl_header = QLabel("⚠️ Pre-Send Safety Check")
        lbl_header.setStyleSheet("font-weight: bold; font-size: 17px; color: #FFB86C;")

        self.lbl_summary = QLabel(
            f"You are about to dispatch <b>{valid_count}</b> certificate emails.<br>"
            f"<b>Sender Address:</b> {self.settings.sender_email or self.settings.username}<br>"
            f"<b>SMTP Host:</b> {self.settings.smtp_host}:{self.settings.smtp_port}<br>"
            f"<b>Pacing Delay:</b> {self.settings.delay_seconds} second(s) between emails."
        )
        self.lbl_summary.setWordWrap(True)
        self.lbl_summary.setStyleSheet("color: #CCCCCC; font-size: 12px; line-height: 140%;")

        lbl_recipients_hdr = QLabel("Recipients Sample:")
        lbl_recipients_hdr.setStyleSheet("font-weight: bold; color: #888888; font-size: 11px; text-transform: uppercase;")

        txt_recipients = QTextEdit()
        txt_recipients.setReadOnly(True)
        txt_recipients.setMaximumHeight(95)
        txt_recipients.setStyleSheet("""
            QTextEdit {
                background-color: #14151E;
                border: 1px solid #282A3A;
                border-radius: 6px;
                padding: 6px;
                color: #A0A5BD;
                font-family: monospace;
                font-size: 11px;
            }
        """)

        sample_lines = [f"• {p.name} <{p.email}>" for p in self.participants[:10] if p.certificate_path]
        if len(self.participants) > 10:
            sample_lines.append(f"... and {len(self.participants) - 10} more recipients.")
        txt_recipients.setPlainText("\n".join(sample_lines))

        # Prominent Agreement Callout Box
        self.card_agree = QFrame()
        self.card_agree.setObjectName("AgreementCard")
        self._update_card_style(checked=False)

        lay_card = QVBoxLayout(self.card_agree)
        lay_card.setContentsMargins(14, 12, 14, 12)
        lay_card.setSpacing(4)

        self.chk_confirm = QCheckBox("I agree to send these certificate emails")
        self.chk_confirm.setCursor(Qt.CursorShape.PointingHandCursor)
        self.chk_confirm.setStyleSheet("""
            QCheckBox {
                font-size: 13px;
                font-weight: bold;
                color: #FFFFFF;
                spacing: 10px;
            }
        """)
        self.chk_confirm.stateChanged.connect(self.on_check_changed)

        lbl_sub = QLabel("I verify the recipient list and confirm that all email and SMTP settings are correct.")
        lbl_sub.setStyleSheet("color: #8C92B2; font-size: 11px; margin-left: 28px;")
        lbl_sub.setWordWrap(True)
        lbl_sub.setCursor(Qt.CursorShape.PointingHandCursor)
        lbl_sub.mousePressEvent = lambda e: self.chk_confirm.toggle()

        lay_card.addWidget(self.chk_confirm)
        lay_card.addWidget(lbl_sub)

        layout_btns = QHBoxLayout()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setStyleSheet(BTN_SECONDARY)
        btn_cancel.clicked.connect(self.reject)

        self.btn_send = QPushButton("🚀 Start Sending Emails")
        self.btn_send.setEnabled(False)
        self.btn_send.setStyleSheet(BTN_SUCCESS)
        self.btn_send.clicked.connect(self.accept)

        layout_btns.addStretch()
        layout_btns.addWidget(btn_cancel)
        layout_btns.addWidget(self.btn_send)

        layout.addWidget(lbl_header)
        layout.addWidget(self.lbl_summary)
        layout.addWidget(lbl_recipients_hdr)
        layout.addWidget(txt_recipients)
        layout.addWidget(self.card_agree)
        layout.addLayout(layout_btns)

    def _update_card_style(self, checked: bool):
        border_color = "#2ECC71" if checked else "#3A86FF"
        bg_color = "#14251F" if checked else "#1B2036"
        self.card_agree.setStyleSheet(f"""
            #AgreementCard {{
                background-color: {bg_color};
                border: 2px solid {border_color};
                border-radius: 8px;
            }}
        """)

    def on_check_changed(self, state: int):
        is_checked = self.chk_confirm.isChecked()
        self._update_card_style(is_checked)
        self.btn_send.setEnabled(is_checked)

