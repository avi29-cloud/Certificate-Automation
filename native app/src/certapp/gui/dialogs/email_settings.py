"""SMTP Email Settings and Credential Configuration Dialog."""

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QPushButton, QTextEdit, QGroupBox, QMessageBox,
    QDoubleSpinBox
)

from src.certapp.core.settings import SettingsManager, SMTPSettings
from src.certapp.core.mailer import SMTPMailer


class EmailSettingsDialog(QDialog):
    """Dialog for editing SMTP configuration and credentials securely."""

    def __init__(self, settings_manager: SettingsManager, parent=None):
        super().__init__(parent)
        self.settings_manager = settings_manager
        self.settings = settings_manager.smtp_settings

        self.setWindowTitle("⚙️ Email & SMTP Settings")
        self.resize(580, 640)

        self.init_ui()
        self.load_values()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # 1. SMTP Server Config
        group_server = QGroupBox("SMTP Server Settings")
        layout_server = QVBoxLayout(group_server)

        # Preset Dropdown
        layout_preset = QHBoxLayout()
        lbl_preset = QLabel("Provider Preset:")
        self.combo_preset = QComboBox()
        self.combo_preset.addItems(["Custom", "Gmail (smtp.gmail.com)", "Outlook / Office365", "Yahoo Mail"])
        self.combo_preset.currentTextChanged.connect(self.on_preset_changed)
        layout_preset.addWidget(lbl_preset)
        layout_preset.addWidget(self.combo_preset)
        layout_server.addLayout(layout_preset)

        # Host & Port
        layout_host = QHBoxLayout()
        lbl_host = QLabel("SMTP Host:")
        self.txt_host = QLineEdit()
        lbl_port = QLabel("Port:")
        self.txt_port = QLineEdit()
        self.txt_port.setFixedWidth(70)

        layout_host.addWidget(lbl_host)
        layout_host.addWidget(self.txt_host, 2)
        layout_host.addWidget(lbl_port)
        layout_host.addWidget(self.txt_port)
        layout_server.addLayout(layout_host)

        # Security Mode
        layout_sec = QHBoxLayout()
        lbl_sec = QLabel("Security Mode:")
        self.combo_sec = QComboBox()
        self.combo_sec.addItems(["STARTTLS", "SSL", "None"])
        self.combo_sec.currentTextChanged.connect(self.on_sec_mode_changed)
        layout_sec.addWidget(lbl_sec)
        layout_sec.addWidget(self.combo_sec)
        layout_server.addLayout(layout_sec)

        layout.addWidget(group_server)

        # 2. Authentication & Credentials
        group_auth = QGroupBox("Credentials & Sender Info")
        layout_auth = QVBoxLayout(group_auth)

        # Username / Email
        layout_user = QHBoxLayout()
        lbl_user = QLabel("Username / Email:")
        self.txt_username = QLineEdit()
        self.txt_username.setPlaceholderText("e.g. yourname@gmail.com")
        self.txt_username.textChanged.connect(self._on_username_changed)
        layout_user.addWidget(lbl_user)
        layout_user.addWidget(self.txt_username)
        layout_auth.addLayout(layout_user)

        # Password
        layout_pwd = QHBoxLayout()
        lbl_pwd = QLabel("Password:")
        self.txt_password = QLineEdit()
        self.txt_password.setEchoMode(QLineEdit.Password)
        self.txt_password.setPlaceholderText("16-character App Password for Gmail")
        self.btn_show_pwd = QPushButton("Show")
        self.btn_show_pwd.setFixedWidth(60)
        self.btn_show_pwd.setCheckable(True)
        self.btn_show_pwd.toggled.connect(self.toggle_show_password)

        layout_pwd.addWidget(lbl_pwd)
        layout_pwd.addWidget(self.txt_password)
        layout_pwd.addWidget(self.btn_show_pwd)
        layout_auth.addLayout(layout_pwd)

        # Gmail App Password Helper Banner
        layout_gmail_tip = QHBoxLayout()
        self.lbl_pwd_hint = QLabel("💡 <b>Gmail Note:</b> Use a 16-character App Password, NOT your personal account password.")
        self.lbl_pwd_hint.setStyleSheet("color: #D29922; font-size: 11px;")
        self.btn_open_app_pwd = QPushButton("🔑 Get App Password")
        self.btn_open_app_pwd.setToolTip("Opens Google Account App Passwords in your browser")
        self.btn_open_app_pwd.setStyleSheet("""
            QPushButton {
                background-color: #1F3A60; color: #58A6FF;
                border: 1px solid #388BFD; border-radius: 4px;
                padding: 3px 8px; font-size: 11px; font-weight: bold;
            }
            QPushButton:hover { background-color: #264A7E; color: #FFFFFF; }
        """)
        self.btn_open_app_pwd.clicked.connect(self.open_app_password_url)
        layout_gmail_tip.addWidget(self.lbl_pwd_hint, 1)
        layout_gmail_tip.addWidget(self.btn_open_app_pwd)
        layout_auth.addLayout(layout_gmail_tip)

        # Sender Name & Email
        layout_sender = QHBoxLayout()
        lbl_sname = QLabel("Sender Name:")
        self.txt_sname = QLineEdit()
        lbl_semail = QLabel("Sender Email:")
        self.txt_semail = QLineEdit()

        layout_sender.addWidget(lbl_sname)
        layout_sender.addWidget(self.txt_sname)
        layout_sender.addWidget(lbl_semail)
        layout_sender.addWidget(self.txt_semail)
        layout_auth.addLayout(layout_sender)

        # Delay Pacing
        layout_delay = QHBoxLayout()
        lbl_delay = QLabel("Sending Pacing Delay (sec):")
        self.spin_delay = QDoubleSpinBox()
        self.spin_delay.setRange(0.0, 30.0)
        self.spin_delay.setSingleStep(0.5)
        self.spin_delay.setValue(1.0)
        layout_delay.addWidget(lbl_delay)
        layout_delay.addWidget(self.spin_delay)
        layout_auth.addLayout(layout_delay)

        layout.addWidget(group_auth)

        # 3. Email Template
        group_template = QGroupBox("Email Subject & Body Template")
        layout_tmpl = QVBoxLayout(group_template)

        lbl_subj = QLabel("Subject:")
        self.txt_subject = QLineEdit()
        layout_tmpl.addWidget(lbl_subj)
        layout_tmpl.addWidget(self.txt_subject)

        lbl_body = QLabel("Body (Supports plain text or HTML):")
        self.txt_body = QTextEdit()
        layout_tmpl.addWidget(lbl_body)
        layout_tmpl.addWidget(self.txt_body)

        # Tag Insert Buttons
        layout_tags = QHBoxLayout()
        lbl_tags = QLabel("Insert Tag:")
        btn_tag_name = QPushButton("{name}")
        btn_tag_email = QPushButton("{email}")

        btn_tag_name.clicked.connect(lambda: self.txt_body.insertPlainText("{name}"))
        btn_tag_email.clicked.connect(lambda: self.txt_body.insertPlainText("{email}"))

        layout_tags.addWidget(lbl_tags)
        layout_tags.addWidget(btn_tag_name)
        layout_tags.addWidget(btn_tag_email)
        layout_tags.addStretch()
        layout_tmpl.addLayout(layout_tags)

        layout.addWidget(group_template)

        # 4. Action Buttons
        layout_actions = QHBoxLayout()
        self.btn_test = QPushButton("🔌 Test Connection")
        self.btn_test.clicked.connect(self.test_connection)

        self.btn_save = QPushButton("💾 Save & Close")
        self.btn_save.clicked.connect(self.save_values)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)

        layout_actions.addWidget(self.btn_test)
        layout_actions.addStretch()
        layout_actions.addWidget(self.btn_cancel)
        layout_actions.addWidget(self.btn_save)

        layout.addLayout(layout_actions)

    def load_values(self):
        s = self.settings
        self.txt_host.setText(s.smtp_host)
        self.txt_port.setText(str(s.smtp_port))
        self.combo_sec.setCurrentText(s.security_mode)
        self.txt_username.setText(s.username)
        self.txt_password.setText(self.settings_manager.get_password())
        self.txt_sname.setText(s.sender_name)
        self.txt_semail.setText(s.sender_email or s.username)
        self.spin_delay.setValue(s.delay_seconds)
        self.txt_subject.setText(s.subject_template)
        self.txt_body.setPlainText(s.body_template)

        # Match preset if applicable
        if "gmail" in s.smtp_host.lower():
            self.combo_preset.setCurrentText("Gmail (smtp.gmail.com)")
        elif "office365" in s.smtp_host.lower():
            self.combo_preset.setCurrentText("Outlook / Office365")
        elif "yahoo" in s.smtp_host.lower():
            self.combo_preset.setCurrentText("Yahoo Mail")

    def _on_username_changed(self, text: str):
        # Auto-fill sender email if empty or matches previous username
        if not self.txt_semail.text() or "@" in text:
            if not self.txt_semail.text():
                self.txt_semail.setText(text)

    def on_preset_changed(self, preset_name: str):
        if "Gmail" in preset_name:
            self.txt_host.setText("smtp.gmail.com")
            self.txt_port.setText("587")
            self.combo_sec.setCurrentText("STARTTLS")
        elif "Outlook" in preset_name:
            self.txt_host.setText("smtp.office365.com")
            self.txt_port.setText("587")
            self.combo_sec.setCurrentText("STARTTLS")
        elif "Yahoo" in preset_name:
            self.txt_host.setText("smtp.mail.yahoo.com")
            self.txt_port.setText("465")
            self.combo_sec.setCurrentText("SSL")

    def on_sec_mode_changed(self, mode: str):
        """Automatically suggest standard port when changing security mode."""
        port = self.txt_port.text().strip()
        if mode == "SSL" and port == "587":
            self.txt_port.setText("465")
        elif mode == "STARTTLS" and port == "465":
            self.txt_port.setText("587")

    def open_app_password_url(self):
        """Opens Google Account App Passwords page in the default web browser."""
        QDesktopServices.openUrl(QUrl("https://myaccount.google.com/apppasswords"))

    def toggle_show_password(self, checked: bool):
        if checked:
            self.txt_password.setEchoMode(QLineEdit.Normal)
            self.btn_show_pwd.setText("Hide")
        else:
            self.txt_password.setEchoMode(QLineEdit.Password)
            self.btn_show_pwd.setText("Show")

    def get_current_settings(self) -> SMTPSettings:
        try:
            port = int(self.txt_port.text().strip())
        except ValueError:
            port = 587

        return SMTPSettings(
            smtp_host=self.txt_host.text().strip(),
            smtp_port=port,
            security_mode=self.combo_sec.currentText(),
            username=self.txt_username.text().strip(),
            sender_name=self.txt_sname.text().strip(),
            sender_email=self.txt_semail.text().strip(),
            subject_template=self.txt_subject.text().strip(),
            body_template=self.txt_body.toPlainText().strip(),
            delay_seconds=self.spin_delay.value()
        )

    def test_connection(self):
        settings = self.get_current_settings()
        password = self.txt_password.text().strip()

        self.btn_test.setEnabled(False)
        self.btn_test.setText("Testing...")

        ok, msg = SMTPMailer.test_connection(settings, password)

        self.btn_test.setEnabled(True)
        self.btn_test.setText("🔌 Test Connection")

        if ok:
            QMessageBox.information(
                self, "Connection Succeeded ✓",
                "Successfully connected and authenticated with the SMTP server!\n\n"
                "Your email configuration is working and ready to send certificates."
            )
        else:
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Warning)
            msg_box.setWindowTitle("Connection Test Failed")
            msg_box.setText(msg)

            if "apppasswords" in msg.lower() or "app password" in msg.lower():
                btn_open = msg_box.addButton("Open Google App Passwords 🌐", QMessageBox.ActionRole)
                btn_close = msg_box.addButton("Close", QMessageBox.RejectRole)
                msg_box.exec()
                if msg_box.clickedButton() == btn_open:
                    self.open_app_password_url()
            else:
                msg_box.exec()

    def save_values(self):
        settings = self.get_current_settings()
        self.settings_manager.smtp_settings = settings
        self.settings_manager.save()

        password = self.txt_password.text().strip()
        if password:
            self.settings_manager.set_password(password)

        self.accept()
