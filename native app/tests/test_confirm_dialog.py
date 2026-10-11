"""Tests for ConfirmSendDialog."""

import pytest
from PySide6.QtCore import Qt
from src.certapp.core.models import Participant
from src.certapp.core.settings import SMTPSettings
from src.certapp.gui.dialogs.confirm_send import ConfirmSendDialog


@pytest.fixture
def sample_data():
    participants = [
        Participant(
            row_index=1,
            name="Alice Smith",
            email="alice@example.com",
            validation_status="valid",
            certificate_path="/tmp/alice.pdf"
        ),
        Participant(
            row_index=2,
            name="Bob Jones",
            email="bob@example.com",
            validation_status="valid",
            certificate_path="/tmp/bob.pdf"
        ),
        Participant(
            row_index=3,
            name="Charlie Brown",
            email="charlie@invalid",
            validation_status="invalid",
            certificate_path=None
        ),
    ]
    settings = SMTPSettings(
        smtp_host="smtp.gmail.com",
        smtp_port=587,
        username="user@gmail.com",
        sender_email="user@gmail.com",
        delay_seconds=1.0
    )
    return participants, settings


def test_confirm_send_dialog_initial_state(qtbot, sample_data):
    participants, settings = sample_data
    dlg = ConfirmSendDialog(participants, settings)
    qtbot.addWidget(dlg)

    # Initial state
    assert not dlg.chk_confirm.isChecked()
    assert not dlg.btn_send.isEnabled()
    assert "2" in dlg.lbl_summary.text()  # 2 valid certs


def test_confirm_send_dialog_toggle_agreement(qtbot, sample_data):
    participants, settings = sample_data
    dlg = ConfirmSendDialog(participants, settings)
    qtbot.addWidget(dlg)

    # Check
    dlg.chk_confirm.setChecked(True)
    assert dlg.chk_confirm.isChecked()
    assert dlg.btn_send.isEnabled()
    assert "#2ECC71" in dlg.card_agree.styleSheet()

    # Uncheck
    dlg.chk_confirm.setChecked(False)
    assert not dlg.chk_confirm.isChecked()
    assert not dlg.btn_send.isEnabled()
    assert "#3A86FF" in dlg.card_agree.styleSheet()
