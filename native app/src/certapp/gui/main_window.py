"""Main Application — multi-window architecture.

Window 1  (SetupWindow)   : Load sheet, load template, pick output folder → opens Editor
Window 2  (EditorWindow)  : Visual canvas + style panel side-by-side
Window 3  (RunnerWindow)  : Participants table, generate/send buttons, progress, log
"""

import sys
from pathlib import Path
from typing import List, Optional
from PySide6.QtCore import Qt, Slot, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QProgressBar, QPushButton, QLabel, QFileDialog,
    QMessageBox, QSplitter, QApplication
)

from src.certapp.core.models import Participant, LayoutConfig
from src.certapp.core.sheet_loader import load_participants_from_file
from src.certapp.core.generator import CertificateGenerator
from src.certapp.core.mailer import SMTPMailer
from src.certapp.core.state_store import ManifestStore
from src.certapp.core.settings import SettingsManager
from src.certapp.core.utils import get_sample_dir

from src.certapp.gui.widgets.drop_zone import DropZoneWidget
from src.certapp.gui.widgets.template_preview import TemplatePreviewCanvas
from src.certapp.gui.widgets.style_panel import StylePanelWidget
from src.certapp.gui.widgets.participants_table import ParticipantsTableWidget
from src.certapp.gui.widgets.log_panel import LogPanelWidget

from src.certapp.gui.dialogs.email_settings import EmailSettingsDialog
from src.certapp.gui.dialogs.column_mapping import ColumnMappingDialog
from src.certapp.gui.dialogs.confirm_send import ConfirmSendDialog

from src.certapp.gui.workers import GenerateWorker, SendWorker
from src.certapp.gui.theme import (
    DARK_THEME, BTN_PRIMARY, BTN_SUCCESS, BTN_DANGER, BTN_SECONDARY
)


# ═══════════════════════════════════════════════════════════════════════
#  Window 1 — Setup
# ═══════════════════════════════════════════════════════════════════════

class SetupWindow(QMainWindow):
    """First window: load inputs and proceed to editor or runner."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("CertApp — Setup")
        self.resize(600, 620)
        self.setStyleSheet(DARK_THEME)

        self.settings_manager = SettingsManager()
        self.layout_config = LayoutConfig()
        self.participants: List[Participant] = []
        self.output_dir: Path = Path.cwd() / "output"
        self.raw_columns: List[str] = []
        self.column_mapping = {}

        self._editor_win: Optional["EditorWindow"] = None
        self._runner_win: Optional["RunnerWindow"] = None

        self._build_ui()

    def _build_ui(self):
        cw = QWidget()
        self.setCentralWidget(cw)
        lay = QVBoxLayout(cw)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(16)

        title = QLabel("📜 CertApp — Certificate Automation Studio")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #3A86FF;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(title)

        subtitle = QLabel("Step 1: Load your data and template, then open the editor or generate directly.")
        subtitle.setStyleSheet("color: #888; font-size: 12px;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setWordWrap(True)
        lay.addWidget(subtitle)

        # Drop zones
        self.drop_sheet = DropZoneWidget(
            title="Participant Sheet",
            subtitle="Drop .CSV or .XLSX file",
            filter_mode="sheet"
        )
        self.drop_sheet.file_selected.connect(self._on_sheet_loaded)

        self.drop_template = DropZoneWidget(
            title="Certificate Template",
            subtitle="Drop .PNG, .JPG, or .PDF",
            filter_mode="template"
        )
        self.drop_template.file_selected.connect(self._on_template_loaded)

        lay.addWidget(self.drop_sheet)
        lay.addWidget(self.drop_template)

        # Output folder
        row_out = QHBoxLayout()
        row_out.addWidget(QLabel("Output Folder:"))
        self.lbl_out = QLabel(str(self.output_dir))
        self.lbl_out.setStyleSheet("color: #4CAF50; font-weight: bold;")
        btn_out = QPushButton("Select…")
        btn_out.setStyleSheet(BTN_SECONDARY)
        btn_out.clicked.connect(self._pick_output)
        row_out.addWidget(self.lbl_out, 1)
        row_out.addWidget(btn_out)
        lay.addLayout(row_out)

        # Status label
        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet("color: #888; font-size: 11px;")
        self.lbl_status.setWordWrap(True)
        lay.addWidget(self.lbl_status)

        # Action buttons
        row_btns = QHBoxLayout()

        btn_email = QPushButton("⚙️ Email Config")
        btn_email.setStyleSheet(BTN_SECONDARY)
        btn_email.clicked.connect(self._open_email_settings)

        self.btn_editor = QPushButton("🎨 Open Visual Editor")
        self.btn_editor.setStyleSheet(BTN_PRIMARY)
        self.btn_editor.clicked.connect(self._open_editor)

        self.btn_runner = QPushButton("⚙️ Generate & Send")
        self.btn_runner.setStyleSheet(BTN_SUCCESS)
        self.btn_runner.clicked.connect(self._open_runner)

        row_btns.addWidget(btn_email)
        row_btns.addStretch()
        row_btns.addWidget(self.btn_editor)
        row_btns.addWidget(self.btn_runner)
        lay.addLayout(row_btns)

        lay.addStretch()

    # ── callbacks ──

    def _on_sheet_loaded(self, path: str):
        try:
            participants, cols, mapping = load_participants_from_file(path)
            self.participants = participants
            self.raw_columns = cols
            self.column_mapping = mapping

            if not mapping["name_col"] or not mapping["email_col"]:
                dlg = ColumnMappingDialog(cols, mapping, self)
                if dlg.exec():
                    sel = dlg.get_selected_mapping()
                    participants, cols, mapping = load_participants_from_file(
                        path, sel["name_col"], sel["email_col"]
                    )
                    self.participants = participants
                    self.column_mapping = mapping

            valid = sum(1 for p in self.participants if p.validation_status == "valid")
            self.lbl_status.setText(
                f"✓ Loaded {len(self.participants)} rows ({valid} valid) from {Path(path).name}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load sheet:\n{e}")

    def _on_template_loaded(self, path: str):
        self.layout_config.background_path = path
        self.lbl_status.setText(
            f"{self.lbl_status.text()}\n✓ Template: {Path(path).name}"
        )

    def _pick_output(self):
        d = QFileDialog.getExistingDirectory(self, "Select Output Directory", str(self.output_dir))
        if d:
            self.output_dir = Path(d)
            self.lbl_out.setText(str(self.output_dir))

    def _open_email_settings(self):
        EmailSettingsDialog(self.settings_manager, self).exec()

    def _open_editor(self):
        if not self.layout_config.background_path:
            QMessageBox.warning(self, "No Template", "Please load a certificate template image first.")
            return
        self._editor_win = EditorWindow(self.layout_config, self)
        self._editor_win.config_saved.connect(self._on_editor_saved)
        self._editor_win.show()

    def _on_editor_saved(self, cfg: LayoutConfig):
        self.layout_config = cfg

    def _open_runner(self):
        if not self.participants:
            QMessageBox.warning(self, "No Data", "Please load a participant sheet first.")
            return
        if not self.layout_config.background_path:
            QMessageBox.warning(self, "No Template", "Please load a certificate template first.")
            return
        self._runner_win = RunnerWindow(
            self.participants, self.layout_config,
            self.output_dir, self.settings_manager, self
        )
        self._runner_win.show()


# ═══════════════════════════════════════════════════════════════════════
#  Window 2 — Editor (canvas + style panel)
# ═══════════════════════════════════════════════════════════════════════

class EditorWindow(QMainWindow):
    """Canvas on top, all style controls visible at the bottom."""

    config_saved = Signal(LayoutConfig)

    def __init__(self, config: LayoutConfig, parent=None):
        super().__init__(parent)
        self.setWindowTitle("CertApp — Visual Layout Editor")
        self.resize(1280, 800)
        self.setStyleSheet(DARK_THEME)

        self.config = LayoutConfig.from_dict(config.to_dict())  # deep copy

        self._build_ui()

    def _build_ui(self):
        cw = QWidget()
        self.setCentralWidget(cw)
        root = QVBoxLayout(cw)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        # Top: canvas (takes most space)
        self.canvas = TemplatePreviewCanvas()
        self.canvas.set_template(self.config.background_path)
        self.canvas.update_layout_config(self.config)
        root.addWidget(self.canvas, 1)  # stretch factor 1 = takes remaining space

        # Bottom: compact style panel (all options in horizontal rows)
        self.style_panel = StylePanelWidget()
        self.style_panel.set_layout_config(self.config)
        root.addWidget(self.style_panel, 0)  # no stretch = minimal height

        # Wire: style panel → canvas (one-directional when user edits controls)
        self.style_panel.style_changed.connect(self._on_style_changed)
        self.style_panel.sample_text_changed.connect(self._on_sample_changed)

        # Wire: canvas drag → style panel (update position spinboxes)
        self.canvas.layout_changed.connect(self._on_canvas_dragged)

        # Bottom bar — Apply button
        bot = QHBoxLayout()
        btn_apply = QPushButton("✓ Apply & Close")
        btn_apply.setStyleSheet(BTN_SUCCESS)
        btn_apply.clicked.connect(self._apply_close)
        bot.addStretch()
        bot.addWidget(btn_apply)
        root.addLayout(bot)

    def _on_style_changed(self, cfg: LayoutConfig):
        """User changed controls → update canvas."""
        cfg.background_path = self.config.background_path
        self.config = cfg
        self.canvas.update_layout_config(self.config)

    def _on_sample_changed(self, text: str):
        self.canvas.update_layout_config(self.config, text)

    def _on_canvas_dragged(self, cfg: LayoutConfig):
        """User dragged marker → update style panel position spinboxes."""
        self.config = cfg
        self.style_panel.set_layout_config(cfg)   # set_layout_config blocks re-emit

    def _apply_close(self):
        self.config_saved.emit(self.config)
        self.close()


# ═══════════════════════════════════════════════════════════════════════
#  Window 3 — Runner (table, generate, send, log)
# ═══════════════════════════════════════════════════════════════════════

class RunnerWindow(QMainWindow):
    """Batch generation and email dispatch window."""

    def __init__(
        self,
        participants: List[Participant],
        layout_config: LayoutConfig,
        output_dir: Path,
        settings_manager: SettingsManager,
        parent=None
    ):
        super().__init__(parent)
        self.setWindowTitle("CertApp — Generate & Send")
        self.resize(1000, 700)
        self.setStyleSheet(DARK_THEME)

        self.participants = participants
        self.layout_config = layout_config
        self.output_dir = output_dir
        self.settings_manager = settings_manager

        self.gen_worker: Optional[GenerateWorker] = None
        self.send_worker: Optional[SendWorker] = None

        # Sync manifest
        manifest = ManifestStore(self.output_dir)
        manifest.sync_participants(self.participants)

        self._build_ui()

    def _build_ui(self):
        cw = QWidget()
        self.setCentralWidget(cw)
        lay = QVBoxLayout(cw)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(8)

        # Action bar
        row = QHBoxLayout()
        self.btn_gen = QPushButton("⚙️ Generate Certificates")
        self.btn_send = QPushButton("🚀 Send Emails")
        self.btn_cancel = QPushButton("❌ Cancel")
        self.btn_cancel.setEnabled(False)

        btn_open_out = QPushButton("📂 Open Output")
        btn_open_out.setStyleSheet(BTN_SECONDARY)
        btn_open_out.clicked.connect(self._open_output)

        self.btn_gen.setStyleSheet(BTN_PRIMARY)
        self.btn_send.setStyleSheet(BTN_SUCCESS)
        self.btn_cancel.setStyleSheet(BTN_DANGER)

        btn_email_cfg = QPushButton("⚙️ Email Settings")
        btn_email_cfg.setStyleSheet(BTN_SECONDARY)
        btn_email_cfg.clicked.connect(self._open_email_config)

        self.btn_gen.clicked.connect(self._start_gen)
        self.btn_send.clicked.connect(self._start_send)
        self.btn_cancel.clicked.connect(self._cancel)

        row.addWidget(self.btn_gen)
        row.addWidget(self.btn_send)
        row.addWidget(self.btn_cancel)
        row.addStretch()
        row.addWidget(btn_email_cfg)
        row.addWidget(btn_open_out)
        lay.addLayout(row)

        # Progress
        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.progress.setTextVisible(True)
        lay.addWidget(self.progress)

        # Table
        self.table_widget = ParticipantsTableWidget()
        self.table_widget.set_participants(self.participants)

        # Log
        self.log_panel = LogPanelWidget()
        self.log_panel.info(f"Loaded {len(self.participants)} participants. Ready.")

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(self.table_widget)
        splitter.addWidget(self.log_panel)
        splitter.setSizes([450, 200])
        lay.addWidget(splitter)

        self.statusBar().showMessage("Ready.")

    # ── generation ──

    def _start_gen(self):
        selected = self.table_widget.get_selected_participants()
        if not selected:
            QMessageBox.warning(self, "Nothing Selected", "No participants selected.")
            return

        gen = CertificateGenerator(self.layout_config, self.output_dir)
        self._set_running(True)
        self.progress.setValue(0)

        self.gen_worker = GenerateWorker(gen, selected)
        self.gen_worker.progress_signal.connect(self._on_progress)
        self.gen_worker.item_finished_signal.connect(
            lambda p, ok, msg: self.table_widget.update_participant_row(p)
        )
        self.gen_worker.log_signal.connect(self.log_panel.append_log)
        self.gen_worker.finished_signal.connect(self._on_gen_done)
        self.gen_worker.start()

    @Slot(int, int, str)
    def _on_progress(self, cur, total, status):
        self.progress.setValue(int(cur / max(total, 1) * 100))
        self.statusBar().showMessage(status)

    @Slot(int, int)
    def _on_gen_done(self, ok, fail):
        self._set_running(False)
        self.table_widget.apply_filter()  # refresh statuses
        QMessageBox.information(
            self, "Generation Done",
            f"Success: {ok}   Failures: {fail}"
        )

    # ── sending ──

    def _open_email_config(self):
        """Open the Email & SMTP Settings dialog directly from RunnerWindow."""
        dlg = EmailSettingsDialog(self.settings_manager, self)
        dlg.exec()

    def _start_send(self):
        selected = self.table_widget.get_selected_participants()
        valid = [p for p in selected if p.validation_status == "valid" and p.certificate_path]
        if not valid:
            QMessageBox.warning(self, "Nothing to Send", "No valid certificates available to send.")
            return

        # Pre-flight validation
        password = self.settings_manager.get_password()
        smtp = self.settings_manager.smtp_settings

        if not smtp.smtp_host or not smtp.username:
            reply = QMessageBox.question(
                self, "SMTP Not Configured",
                "Email settings are not configured yet.\n\nWould you like to configure Email Settings now?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self._open_email_config()
            return

        if not password:
            reply = QMessageBox.question(
                self, "Password Missing",
                "SMTP password is empty.\n\n"
                "• For Gmail, you must enter a 16-character App Password.\n\n"
                "Would you like to enter your password now in Email Settings?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self._open_email_config()
            return

        dlg = ConfirmSendDialog(valid, smtp, self)
        if not dlg.exec():
            return

        mailer = SMTPMailer(smtp, password)
        manifest = ManifestStore(self.output_dir)
        self._set_running(True)
        self.progress.setValue(0)

        self.send_worker = SendWorker(mailer, manifest, valid)
        self.send_worker.progress_signal.connect(self._on_progress)
        self.send_worker.item_finished_signal.connect(
            lambda p, ok, msg: self.table_widget.update_participant_row(p)
        )
        self.send_worker.log_signal.connect(self.log_panel.append_log)
        self.send_worker.finished_signal.connect(self._on_send_done)
        self.send_worker.connection_error_signal.connect(self._on_smtp_error)
        self.send_worker.start()

    @Slot(str)
    def _on_smtp_error(self, error_msg: str):
        """Handle SMTP connection errors with actionable dialog."""
        self._set_running(False)
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.setWindowTitle("Email Sending Failed")
        msg_box.setText(error_msg)

        if "apppasswords" in error_msg.lower() or "app password" in error_msg.lower():
            btn_open_web = msg_box.addButton("Open Google App Passwords 🌐", QMessageBox.ActionRole)
            btn_settings = msg_box.addButton("⚙️ Open Email Settings", QMessageBox.ActionRole)
            btn_close = msg_box.addButton("Close", QMessageBox.RejectRole)
            msg_box.exec()

            if msg_box.clickedButton() == btn_open_web:
                QDesktopServices.openUrl(QUrl("https://myaccount.google.com/apppasswords"))
            elif msg_box.clickedButton() == btn_settings:
                self._open_email_config()
        else:
            btn_settings = msg_box.addButton("⚙️ Open Email Settings", QMessageBox.ActionRole)
            btn_close = msg_box.addButton("Close", QMessageBox.RejectRole)
            msg_box.exec()
            if msg_box.clickedButton() == btn_settings:
                self._open_email_config()

    @Slot(int, int)
    def _on_send_done(self, ok, fail):
        self._set_running(False)
        self.table_widget.apply_filter()
        if fail == 0:
            QMessageBox.information(
                self, "Sending Complete ✓",
                f"All {ok} emails sent successfully!"
            )
        else:
            QMessageBox.warning(
                self, "Sending Done",
                f"Sent: {ok}   Failed: {fail}\n\n"
                "Check the log panel below for details on failed recipients."
            )

    # ── helpers ──

    def _cancel(self):
        if self.gen_worker and self.gen_worker.isRunning():
            self.gen_worker.cancel()
        if self.send_worker and self.send_worker.isRunning():
            self.send_worker.cancel()
        self._set_running(False)
        self.statusBar().showMessage("Cancelled.")

    def _set_running(self, running: bool):
        self.btn_gen.setEnabled(not running)
        self.btn_send.setEnabled(not running)
        self.btn_cancel.setEnabled(running)

    def _open_output(self):
        self.output_dir.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.output_dir)))


# ═══════════════════════════════════════════════════════════════════════
#  Convenience alias for main.py to keep backward compat
# ═══════════════════════════════════════════════════════════════════════

class MainWindow(SetupWindow):
    """Entry point window — alias for SetupWindow."""
    pass
