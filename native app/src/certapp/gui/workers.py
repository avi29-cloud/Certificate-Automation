"""QThread Worker objects for asynchronous background batch operations."""

import threading
from typing import List
from PySide6.QtCore import QThread, Signal

from src.certapp.core.models import Participant, GenerationResult, SendResult
from src.certapp.core.generator import CertificateGenerator
from src.certapp.core.mailer import SMTPMailer, SMTPConnectionError
from src.certapp.core.state_store import ManifestStore


class GenerateWorker(QThread):
    """Asynchronous worker for batch certificate generation."""

    progress_signal = Signal(int, int, str)  # current, total, status
    item_finished_signal = Signal(Participant, bool, str)
    finished_signal = Signal(int, int)  # success_count, fail_count
    log_signal = Signal(str, str)  # level, msg

    def __init__(self, generator: CertificateGenerator, participants: List[Participant], parent=None):
        super().__init__(parent)
        self.generator = generator
        self.participants = participants
        self.stop_event = threading.Event()

    def cancel(self):
        self.stop_event.set()

    def run(self):
        success_count = 0
        fail_count = 0
        total = len(self.participants)

        self.log_signal.emit("INFO", f"Starting batch certificate generation for {total} recipients...")

        def progress_cb(idx: int, tot: int, participant: Participant, result: GenerationResult):
            nonlocal success_count, fail_count
            if result.success:
                success_count += 1
                self.log_signal.emit("SUCCESS", f"[{idx}/{tot}] Generated: {participant.name}")
                self.item_finished_signal.emit(participant, True, result.output_path or "")
            else:
                fail_count += 1
                self.log_signal.emit("ERROR", f"[{idx}/{tot}] Failed: {participant.name} - {result.error}")
                self.item_finished_signal.emit(participant, False, result.error or "Generation failed")

            self.progress_signal.emit(idx, tot, f"Generating {idx}/{tot}: {participant.name}")

        self.generator.generate_batch(
            self.participants,
            progress_callback=progress_cb,
            stop_event=self.stop_event
        )

        self.log_signal.emit(
            "SUCCESS" if fail_count == 0 else "WARN",
            f"Batch generation complete: {success_count} succeeded, {fail_count} failed."
        )
        self.finished_signal.emit(success_count, fail_count)


class SendWorker(QThread):
    """Asynchronous worker for batch email sending."""

    progress_signal = Signal(int, int, str)  # current, total, status
    item_finished_signal = Signal(Participant, bool, str)
    finished_signal = Signal(int, int)  # success_count, fail_count
    log_signal = Signal(str, str)  # level, msg
    connection_error_signal = Signal(str)  # error message for connection failures

    def __init__(
        self,
        mailer: SMTPMailer,
        manifest_store: ManifestStore,
        participants: List[Participant],
        parent=None
    ):
        super().__init__(parent)
        self.mailer = mailer
        self.manifest_store = manifest_store
        self.participants = participants
        self.stop_event = threading.Event()

    def cancel(self):
        self.stop_event.set()

    def run(self):
        success_count = 0
        fail_count = 0
        total = len(self.participants)

        self.log_signal.emit("INFO", f"Starting batch email sending for {total} recipients...")
        self.log_signal.emit("INFO", f"Connecting to SMTP server {self.mailer.settings.smtp_host}:{self.mailer.settings.smtp_port}...")

        def progress_cb(idx: int, tot: int, participant: Participant, result: SendResult):
            nonlocal success_count, fail_count
            if result.success:
                success_count += 1
                self.log_signal.emit("SUCCESS", f"[{idx}/{tot}] Email sent: {participant.email}")
                self.item_finished_signal.emit(participant, True, "Sent")
            else:
                fail_count += 1
                self.log_signal.emit("ERROR", f"[{idx}/{tot}] Email failed: {participant.email} - {result.error}")
                self.item_finished_signal.emit(participant, False, result.error or "Send failed")

            self.progress_signal.emit(idx, tot, f"Sending {idx}/{tot}: {participant.email}")

        try:
            self.mailer.send_batch(
                self.participants,
                self.manifest_store,
                progress_callback=progress_cb,
                stop_event=self.stop_event
            )
        except SMTPConnectionError as e:
            error_msg = str(e)
            self.log_signal.emit("ERROR", f"SMTP Connection Failed: {error_msg}")
            self.connection_error_signal.emit(error_msg)
            fail_count = total
        except Exception as e:
            error_msg = f"Unexpected error during email sending: {type(e).__name__}: {e}"
            self.log_signal.emit("ERROR", error_msg)
            self.connection_error_signal.emit(error_msg)
            fail_count = total

        self.log_signal.emit(
            "SUCCESS" if fail_count == 0 else "WARN",
            f"Batch email send complete: {success_count} succeeded, {fail_count} failed."
        )
        self.finished_signal.emit(success_count, fail_count)
